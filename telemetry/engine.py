"""Telemetry ingestion, dwell-time calculation, and attacker skill scoring."""
import time
import asyncio
from typing import List, Dict, Optional, Callable
from core.models import Event, Session, ServiceType, FidelityMode
from telemetry.database import Database, db
from telemetry.mitre_tags import classify_techniques, TECHNIQUE_RULES

class TelemetryEngine:
    def __init__(self, database: Optional[Database] = None):
        self.db = database or db
        self.subscribers: List[Callable[[Event, Session], None]] = []

    def subscribe(self, callback: Callable[[Event, Session], None]):
        """Register a callback for real-time telemetry streaming (e.g. WebSocket)."""
        self.subscribers.append(callback)

    def unsubscribe(self, callback: Callable[[Event, Session], None]):
        if callback in self.subscribers:
            self.subscribers.remove(callback)

    def notify_subscribers(self, event: Event, session: Session):
        for callback in self.subscribers:
            try:
                callback(event, session)
            except Exception:
                pass

    def get_or_create_session(
        self,
        session_id: str,
        service: ServiceType,
        source_ip: str,
        profile: str = "ubuntu_web_server",
        initial_fidelity: FidelityMode = FidelityMode.MEDIUM
    ) -> Session:
        existing = self.db.get_session(session_id)
        if existing:
            return existing
        now = time.time()
        new_session = Session(
            session_id=session_id,
            service=service,
            source_ip=source_ip,
            start_time=now,
            last_activity=now,
            dwell_seconds=0.0,
            command_count=0,
            skill_score=1.0,
            current_profile=profile,
            current_fidelity=initial_fidelity,
            decoys_revealed=[],
            technique_counts={},
            is_active=True,
        )
        self.db.upsert_session(new_session)
        return new_session

    def calculate_skill_score(self, session: Session, recent_input: str) -> float:
        """
        Calculates an attacker skill score on a 1.0 - 10.0 scale.
        Factors:
        - Technique variety (unique MITRE tactics used)
        - Sophistication weights of techniques (PrivEsc, Credential Harvesting, SQLi)
        - Command complexity (pipes, redirects, advanced regex, find setuid)
        - Velocity/pacing
        """
        score = 1.0

        # Factor 1: Technique variety and weighted scores
        technique_weights_total = 0.0
        for tech, count in session.technique_counts.items():
            rule_info = TECHNIQUE_RULES.get(tech, {})
            w = rule_info.get("weight", 1.0)
            # Logarithmic dampening on repeat use of same technique
            technique_weights_total += w * (1.0 + 0.3 * min(count - 1, 5))

        score += min(technique_weights_total * 0.7, 5.0)

        # Factor 2: Command syntax complexity in recent input
        complexity_bonus = 0.0
        if any(token in recent_input for token in ["|", "&&", ";", "`", "$("]):
            complexity_bonus += 0.8
        if any(flag in recent_input for flag in ["-perm -4000", "-perm /4000", "-exec", "awk", "sed", "base64"]):
            complexity_bonus += 1.5
        if any(sqli in recent_input.lower() for sqli in ["union select", "1=1", "information_schema", "sleep("]):
            complexity_bonus += 1.2
        if any(probe in recent_input for probe in [".ssh", "/proc/", "/etc/shadow", "id_rsa"]):
            complexity_bonus += 0.8

        score += complexity_bonus

        # Factor 3: Dwell and interaction persistence
        if session.command_count >= 8:
            score += 0.8
        elif session.command_count >= 4:
            score += 0.4

        # Bound to 1.0 - 10.0
        return round(min(max(score, 1.0), 10.0), 2)

    def record_interaction(
        self,
        session_id: str,
        service: ServiceType,
        source_ip: str,
        raw_input: str,
        response_summary: str = "",
        latency_ms: float = 0.0,
        fidelity_mode: Optional[FidelityMode] = None,
        profile: str = "ubuntu_web_server",
        metadata: Optional[Dict] = None
    ) -> Event:
        """
        Main pipeline entry for interaction logging and telemetry analysis.
        """
        now = time.time()
        session = self.get_or_create_session(
            session_id=session_id,
            service=service,
            source_ip=source_ip,
            profile=profile,
            initial_fidelity=fidelity_mode or FidelityMode.MEDIUM
        )

        # 1. Classify techniques
        techniques = classify_techniques(raw_input)

        # 2. Update session state
        session.last_activity = now
        session.dwell_seconds = round(now - session.start_time, 2)
        session.command_count += 1
        if fidelity_mode:
            session.current_fidelity = fidelity_mode

        for tech in techniques:
            session.technique_counts[tech] = session.technique_counts.get(tech, 0) + 1

        # 3. Calculate skill score
        session.skill_score = self.calculate_skill_score(session, raw_input)

        # 4. Save session updates
        self.db.upsert_session(session)

        # 5. Insert event record
        event = Event(
            session_id=session_id,
            timestamp=now,
            source_ip=source_ip,
            service=service,
            raw_input=raw_input,
            response_summary=response_summary[:200] if response_summary else "",
            latency_ms=latency_ms,
            technique_tags=techniques,
            fidelity_mode=session.current_fidelity,
            metadata=metadata or {},
        )
        event_id = self.db.insert_event(event)
        event.id = event_id

        # 6. Notify real-time subscribers
        self.notify_subscribers(event, session)

        return event

telemetry_engine = TelemetryEngine()
