"""SQLite database storage and query manager for ChameleonNet."""
import sqlite3
import json
import asyncio
from typing import List, Optional, Dict, Any
from pathlib import Path
from core.config import settings
from core.models import Event, Session, ServiceType, FidelityMode

SCHEMA_SQL = """
PRAGMA journal_mode=WAL;
PRAGMA synchronous=NORMAL;

CREATE TABLE IF NOT EXISTS sessions (
    session_id TEXT PRIMARY KEY,
    service TEXT NOT NULL,
    source_ip TEXT NOT NULL,
    start_time REAL NOT NULL,
    last_activity REAL NOT NULL,
    dwell_seconds REAL DEFAULT 0.0,
    command_count INTEGER DEFAULT 0,
    skill_score REAL DEFAULT 1.0,
    current_profile TEXT NOT NULL,
    current_fidelity TEXT NOT NULL,
    decoys_revealed TEXT DEFAULT '[]',
    technique_counts TEXT DEFAULT '{}',
    is_active INTEGER DEFAULT 1
);

CREATE TABLE IF NOT EXISTS events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    session_id TEXT NOT NULL,
    timestamp REAL NOT NULL,
    source_ip TEXT NOT NULL,
    service TEXT NOT NULL,
    raw_input TEXT NOT NULL,
    response_summary TEXT DEFAULT '',
    latency_ms REAL DEFAULT 0.0,
    technique_tags TEXT DEFAULT '[]',
    fidelity_mode TEXT NOT NULL,
    metadata TEXT DEFAULT '{}',
    FOREIGN KEY(session_id) REFERENCES sessions(session_id)
);

CREATE INDEX IF NOT EXISTS idx_events_session ON events(session_id);
CREATE INDEX IF NOT EXISTS idx_events_timestamp ON events(timestamp);
CREATE INDEX IF NOT EXISTS idx_sessions_active ON sessions(is_active);
"""

class Database:
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or settings.DB_PATH
        self._lock = asyncio.Lock()
        self.init_db()

    def get_connection(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path), check_same_thread=False)
        conn.row_factory = sqlite3.Row
        return conn

    def init_db(self):
        """Initialize SQLite tables and WAL mode."""
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        with self.get_connection() as conn:
            conn.executescript(SCHEMA_SQL)
            conn.commit()

    def upsert_session(self, session: Session):
        """Insert or update session state."""
        with self.get_connection() as conn:
            conn.execute(
                """
                INSERT INTO sessions (
                    session_id, service, source_ip, start_time, last_activity,
                    dwell_seconds, command_count, skill_score, current_profile,
                    current_fidelity, decoys_revealed, technique_counts, is_active
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(session_id) DO UPDATE SET
                    last_activity = excluded.last_activity,
                    dwell_seconds = excluded.dwell_seconds,
                    command_count = excluded.command_count,
                    skill_score = excluded.skill_score,
                    current_profile = excluded.current_profile,
                    current_fidelity = excluded.current_fidelity,
                    decoys_revealed = excluded.decoys_revealed,
                    technique_counts = excluded.technique_counts,
                    is_active = excluded.is_active
                """,
                (
                    session.session_id,
                    session.service.value,
                    session.source_ip,
                    session.start_time,
                    session.last_activity,
                    session.dwell_seconds,
                    session.command_count,
                    session.skill_score,
                    session.current_profile,
                    session.current_fidelity.value,
                    json.dumps(session.decoys_revealed),
                    json.dumps(session.technique_counts),
                    1 if session.is_active else 0,
                ),
            )
            conn.commit()

    def insert_event(self, event: Event) -> int:
        """Insert a telemetry event and return its ID."""
        with self.get_connection() as conn:
            cursor = conn.execute(
                """
                INSERT INTO events (
                    session_id, timestamp, source_ip, service,
                    raw_input, response_summary, latency_ms,
                    technique_tags, fidelity_mode, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    event.session_id,
                    event.timestamp,
                    event.source_ip,
                    event.service.value,
                    event.raw_input,
                    event.response_summary,
                    event.latency_ms,
                    json.dumps(event.technique_tags),
                    event.fidelity_mode.value,
                    json.dumps(event.metadata),
                ),
            )
            conn.commit()
            return cursor.lastrowid

    def get_session(self, session_id: str) -> Optional[Session]:
        with self.get_connection() as conn:
            row = conn.execute("SELECT * FROM sessions WHERE session_id = ?", (session_id,)).fetchone()
            if not row:
                return None
            return Session(
                session_id=row["session_id"],
                service=ServiceType(row["service"]),
                source_ip=row["source_ip"],
                start_time=row["start_time"],
                last_activity=row["last_activity"],
                dwell_seconds=row["dwell_seconds"],
                command_count=row["command_count"],
                skill_score=row["skill_score"],
                current_profile=row["current_profile"],
                current_fidelity=FidelityMode(row["current_fidelity"]),
                decoys_revealed=json.loads(row["decoys_revealed"] or "[]"),
                technique_counts=json.loads(row["technique_counts"] or "{}"),
                is_active=bool(row["is_active"]),
            )

    def list_sessions(self, limit: int = 50) -> List[Session]:
        with self.get_connection() as conn:
            rows = conn.execute("SELECT * FROM sessions ORDER BY last_activity DESC LIMIT ?", (limit,)).fetchall()
            return [
                Session(
                    session_id=row["session_id"],
                    service=ServiceType(row["service"]),
                    source_ip=row["source_ip"],
                    start_time=row["start_time"],
                    last_activity=row["last_activity"],
                    dwell_seconds=row["dwell_seconds"],
                    command_count=row["command_count"],
                    skill_score=row["skill_score"],
                    current_profile=row["current_profile"],
                    current_fidelity=FidelityMode(row["current_fidelity"]),
                    decoys_revealed=json.loads(row["decoys_revealed"] or "[]"),
                    technique_counts=json.loads(row["technique_counts"] or "{}"),
                    is_active=bool(row["is_active"]),
                )
                for row in rows
            ]

    def list_events(self, session_id: Optional[str] = None, limit: int = 100) -> List[Event]:
        with self.get_connection() as conn:
            if session_id:
                rows = conn.execute(
                    "SELECT * FROM events WHERE session_id = ? ORDER BY timestamp DESC LIMIT ?",
                    (session_id, limit),
                ).fetchall()
            else:
                rows = conn.execute(
                    "SELECT * FROM events ORDER BY timestamp DESC LIMIT ?",
                    (limit,),
                ).fetchall()
            return [
                Event(
                    id=row["id"],
                    session_id=row["session_id"],
                    timestamp=row["timestamp"],
                    source_ip=row["source_ip"],
                    service=ServiceType(row["service"]),
                    raw_input=row["raw_input"],
                    response_summary=row["response_summary"],
                    latency_ms=row["latency_ms"],
                    technique_tags=json.loads(row["technique_tags"] or "[]"),
                    fidelity_mode=FidelityMode(row["fidelity_mode"]),
                    metadata=json.loads(row["metadata"] or "{}"),
                )
                for row in rows
            ]

    def get_stats(self) -> Dict[str, Any]:
        with self.get_connection() as conn:
            total_sessions = conn.execute("SELECT COUNT(*) FROM sessions").fetchone()[0]
            active_sessions = conn.execute("SELECT COUNT(*) FROM sessions WHERE is_active = 1").fetchone()[0]
            total_events = conn.execute("SELECT COUNT(*) FROM events").fetchone()[0]
            avg_dwell = conn.execute("SELECT AVG(dwell_seconds) FROM sessions").fetchone()[0] or 0.0

            # Aggregate technique counts
            technique_dist: Dict[str, int] = {}
            for row in conn.execute("SELECT technique_counts FROM sessions").fetchall():
                counts = json.loads(row[0] or "{}")
                for tech, c in counts.items():
                    technique_dist[tech] = technique_dist.get(tech, 0) + c

            # Aggregate skill distribution
            skill_dist = {"Novice (1-3)": 0, "Intermediate (4-6)": 0, "Advanced (7-10)": 0}
            for row in conn.execute("SELECT skill_score FROM sessions").fetchall():
                score = row[0]
                if score <= 3.5:
                    skill_dist["Novice (1-3)"] += 1
                elif score <= 6.5:
                    skill_dist["Intermediate (4-6)"] += 1
                else:
                    skill_dist["Advanced (7-10)"] += 1

            # Fidelity distribution
            fidelity_dist = {"low": 0, "medium": 0, "high": 0}
            for row in conn.execute("SELECT current_fidelity FROM sessions").fetchall():
                mode = row[0]
                if mode in fidelity_dist:
                    fidelity_dist[mode] += 1

            return {
                "total_sessions": total_sessions,
                "active_sessions": active_sessions,
                "total_events": total_events,
                "avg_dwell_seconds": round(avg_dwell, 1),
                "technique_distribution": technique_dist,
                "skill_distribution": skill_dist,
                "fidelity_distribution": fidelity_dist,
            }

db = Database()
