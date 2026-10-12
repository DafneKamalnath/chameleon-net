"""Fake internal admin portal web emulator built with FastAPI."""
import time
import uuid
from typing import Optional
from fastapi import FastAPI, Request, Response, Form
from fastapi.responses import HTMLResponse, JSONResponse

from core.models import ServiceType, FidelityMode
from telemetry.engine import telemetry_engine
from orchestrator.engine import orchestrator_engine

def create_web_app() -> FastAPI:
    app = FastAPI(title="ApexCloud Internal Admin Portal", version="4.2.1")

    LOGIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ApexCloud | Internal Admin Gateway</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; display: flex; align-items: center; justify-content: center; height: 100vh; margin: 0; }
        .card { background: #1e293b; padding: 2.5rem; border-radius: 12px; width: 380px; box-shadow: 0 10px 25px rgba(0,0,0,0.5); border: 1px solid #334155; }
        .logo { font-size: 1.4rem; font-weight: 700; color: #38bdf8; margin-bottom: 0.5rem; }
        .subtitle { font-size: 0.85rem; color: #94a3b8; margin-bottom: 1.5rem; }
        .input-group { margin-bottom: 1.2rem; }
        label { display: block; font-size: 0.8rem; font-weight: 600; color: #cbd5e1; margin-bottom: 0.4rem; }
        input { width: 100%; box-sizing: border-box; padding: 0.65rem; border-radius: 6px; border: 1px solid #475569; background: #0f172a; color: #fff; font-size: 0.9rem; }
        input:focus { outline: none; border-color: #38bdf8; }
        button { width: 100%; padding: 0.75rem; background: #0284c7; border: none; border-radius: 6px; color: #fff; font-weight: 600; cursor: pointer; transition: background 0.2s; }
        button:hover { background: #0369a1; }
        .notice { font-size: 0.75rem; color: #64748b; margin-top: 1.5rem; text-align: center; }
        .error { color: #f87171; font-size: 0.8rem; margin-bottom: 1rem; }
    </style>
</head>
<body>
    <div class="card">
        <div class="logo">ApexCloud Operations</div>
        <div class="subtitle">Internal Production Control Gateway v4.2</div>
        <form method="POST" action="/login">
            <div class="input-group">
                <label>Corporate SSO Username</label>
                <input type="text" name="username" placeholder="user@internal-apex.corp" required />
            </div>
            <div class="input-group">
                <label>Security Key / Token</label>
                <input type="password" name="password" placeholder="••••••••••••" required />
            </div>
            <button type="submit">Authenticate to Cluster</button>
        </form>
        <div class="notice">Authorized Access Only. Internal corporate telemetry actively audited.</div>
    </div>
</body>
</html>"""

    ADMIN_HTML = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>ApexCloud | Operations Control</title>
    <style>
        body { font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif; background: #0f172a; color: #f8fafc; margin: 0; padding: 2rem; }
        .header { display: flex; justify-content: space-between; align-items: center; border-bottom: 1px solid #334155; padding-bottom: 1rem; }
        .title { font-size: 1.3rem; font-weight: 700; color: #38bdf8; }
        .grid { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1.5rem; margin-top: 2rem; }
        .card { background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155; }
        .stat { font-size: 1.8rem; font-weight: 700; color: #34d399; margin-top: 0.5rem; }
        .badge { display: inline-block; padding: 0.2rem 0.6rem; border-radius: 4px; font-size: 0.75rem; font-weight: 600; background: #0369a1; color: #e0f2fe; }
        .endpoints { margin-top: 2rem; background: #1e293b; padding: 1.5rem; border-radius: 8px; border: 1px solid #334155; }
        code { background: #0f172a; padding: 0.2rem 0.5rem; border-radius: 4px; color: #f59e0b; font-family: monospace; }
    </style>
</head>
<body>
    <div class="header">
        <div class="title">ApexCloud Internal Gateway & Cluster Manager</div>
        <div class="badge">ENVIRONMENT: STAGING (eu-west-1)</div>
    </div>
    <div class="grid">
        <div class="card">
            <div>Active Microservices</div>
            <div class="stat">18 Pods</div>
        </div>
        <div class="card">
            <div>Database Health</div>
            <div class="stat">Connected</div>
        </div>
        <div class="card">
            <div>Auth Realm</div>
            <div class="stat">Keycloak SSO</div>
        </div>
    </div>
    <div class="endpoints">
        <h3>Available Internal Endpoints</h3>
        <ul>
            <li><code>/api/users</code> — Internal staff directory & service credentials</li>
            <li><code>/api/config</code> — Staging database configuration and secrets</li>
            <li><code>/api/status</code> — System health metrics</li>
        </ul>
    </div>
</body>
</html>"""

    def _get_or_create_session(request: Request, response: Response) -> str:
        cookie_sess = request.cookies.get("chameleon_session")
        if cookie_sess:
            return cookie_sess
        new_sess = f"web-{uuid.uuid4().hex[:8]}"
        response.set_cookie("chameleon_session", new_sess, httponly=True)
        return new_sess

    @app.middleware("http")
    async def telemetry_middleware(request: Request, call_next):
        t0 = time.time()
        client_ip = request.client.host if request.client else "127.0.0.1"

        # Determine or preserve session id
        cookie_sess = request.cookies.get("chameleon_session")
        session_id = cookie_sess or f"web-{uuid.uuid4().hex[:8]}"

        response = await call_next(request)

        if not cookie_sess:
            response.set_cookie("chameleon_session", session_id, httponly=True)

        latency = (time.time() - t0) * 1000.0

        # Log event into telemetry
        path_query = str(request.url.path)
        if request.url.query:
            path_query += f"?{request.url.query}"

        raw_input = f"{request.method} {path_query}"

        telemetry_engine.record_interaction(
            session_id=session_id,
            service=ServiceType.WEB,
            source_ip=client_ip,
            raw_input=raw_input,
            response_summary=f"HTTP {response.status_code}",
            latency_ms=round(latency, 2),
            profile="ubuntu_web_server",
            metadata={"status_code": response.status_code, "user_agent": request.headers.get("user-agent", "")}
        )
        return response

    @app.get("/", response_class=HTMLResponse)
    @app.get("/login", response_class=HTMLResponse)
    async def get_login(request: Request):
        return HTMLResponse(LOGIN_HTML)

    @app.post("/login", response_class=HTMLResponse)
    async def post_login(request: Request, username: str = Form(""), password: str = Form("")):
        # Check for SQL injection in login
        if "' or " in username.lower() or "' or " in password.lower() or "1=1" in username or "1=1" in password:
            # Believable honeypot bypass reward: let attacker into admin dashboard!
            return HTMLResponse(ADMIN_HTML)
        # Any other credential grants enticement access
        return HTMLResponse(ADMIN_HTML)

    @app.get("/admin", response_class=HTMLResponse)
    async def get_admin(request: Request):
        return HTMLResponse(ADMIN_HTML)

    @app.get("/api/users")
    async def api_users(request: Request):
        from core.pipeline import pipeline
        session_id = request.cookies.get("chameleon_session", "web-anon")
        client_ip = request.client.host if request.client else "127.0.0.1"
        raw_res, _, _, _ = await pipeline.execute_cycle(
            session_id=session_id,
            service=ServiceType.WEB,
            source_ip=client_ip,
            raw_input="GET /api/users",
        )
        return Response(content=raw_res, media_type="application/json")

    @app.get("/api/config")
    async def api_config(request: Request):
        from core.pipeline import pipeline
        session_id = request.cookies.get("chameleon_session", "web-anon")
        client_ip = request.client.host if request.client else "127.0.0.1"
        raw_res, _, _, _ = await pipeline.execute_cycle(
            session_id=session_id,
            service=ServiceType.WEB,
            source_ip=client_ip,
            raw_input="GET /api/config",
        )
        return Response(content=raw_res, media_type="application/json")

    @app.get("/api/status")
    async def api_status(request: Request):
        return JSONResponse({
            "status": "healthy",
            "uptime_seconds": 384910,
            "version": "4.2.1",
            "cluster_nodes": 3,
        })

    return app

app = create_web_app()
