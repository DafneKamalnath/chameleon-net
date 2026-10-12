"""Dashboard API and WebSocket streaming service for ChameleonNet."""
import asyncio
import json
import time
from pathlib import Path
from typing import List, Dict, Any, Optional
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse

from core.models import Event, Session, ServiceType, FidelityMode
from telemetry.engine import telemetry_engine
from core.pipeline import pipeline

STATIC_DIR = Path(__file__).resolve().parent / "static"

dashboard_app = FastAPI(title="ChameleonNet Operations Dashboard", version="1.0.0")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)

    def disconnect(self, websocket: WebSocket):
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)

    async def broadcast(self, message: Dict[str, Any]):
        data = json.dumps(message)
        dead_connections = []
        for connection in self.active_connections:
            try:
                await connection.send_text(data)
            except Exception:
                dead_connections.append(connection)
        for dc in dead_connections:
            self.disconnect(dc)

ws_manager = ConnectionManager()

# Hook telemetry subscriber to broadcast on WebSocket
def on_telemetry_event(event: Event, session: Session):
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            asyncio.create_task(
                ws_manager.broadcast({
                    "type": "NEW_EVENT",
                    "event": event.model_dump(),
                    "session": session.model_dump(),
                    "pipeline_state": pipeline.last_pipeline_state,
                    "stats": telemetry_engine.db.get_stats(),
                })
            )
    except Exception:
        pass

telemetry_engine.subscribe(on_telemetry_event)

@dashboard_app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        # Send initial snapshot
        initial_data = {
            "type": "INITIAL_SNAPSHOT",
            "stats": telemetry_engine.db.get_stats(),
            "sessions": [s.model_dump() for s in telemetry_engine.db.list_sessions(30)],
            "events": [e.model_dump() for e in telemetry_engine.db.list_events(limit=50)],
            "pipeline_state": pipeline.last_pipeline_state,
        }
        await websocket.send_text(json.dumps(initial_data))
        while True:
            # Keep connection alive
            msg = await websocket.receive_text()
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)

@dashboard_app.get("/api/stats")
async def get_stats():
    return JSONResponse(telemetry_engine.db.get_stats())

@dashboard_app.get("/api/sessions")
async def get_sessions(limit: int = 50):
    sessions = telemetry_engine.db.list_sessions(limit)
    return JSONResponse([s.model_dump() for s in sessions])

@dashboard_app.get("/api/events")
async def get_events(session_id: Optional[str] = None, limit: int = 100):
    events = telemetry_engine.db.list_events(session_id, limit)
    return JSONResponse([e.model_dump() for e in events])

@dashboard_app.get("/api/pipeline/state")
async def get_pipeline_state():
    return JSONResponse(pipeline.last_pipeline_state)

@dashboard_app.post("/api/benchmark/run")
async def run_benchmark():
    """
    Executes a side-by-side benchmark comparison:
    Scripted recon sequence run against Static Honeypot vs ChameleonNet.
    Returns dwell time, unique artifacts revealed, and attacker deception depth.
    """
    from simulator.benchmark import execute_comparison_benchmark
    results = await execute_comparison_benchmark()
    return JSONResponse(results)

@dashboard_app.post("/api/simulate")
async def trigger_simulation(scenario: str = "ssh_recon"):
    """
    Triggers the automated benign attacker simulator for interactive demo viewing.
    """
    from simulator.attacker_sim import run_simulated_attack
    asyncio.create_task(run_simulated_attack(scenario))
    return JSONResponse({"status": "Simulation initiated", "scenario": scenario})

# Mount static files for dashboard frontend
dashboard_app.mount("/", StaticFiles(directory=str(STATIC_DIR), html=True), name="static")
