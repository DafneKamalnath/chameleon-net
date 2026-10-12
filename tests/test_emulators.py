"""Unit tests for Web Emulator endpoints and SSH Server integration."""
import pytest
import httpx
from emulators.web.app import app

@pytest.mark.asyncio
async def test_web_emulator_login_page():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        resp = await client.get("/")
        assert resp.status_code == 200
        assert "ApexCloud" in resp.text
        assert "login" in resp.text.lower()

@pytest.mark.asyncio
async def test_web_emulator_sqli_honeypot_bypass():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # SQL injection bypass attempt in login
        resp = await client.post(
            "/login",
            data={"username": "admin' OR 1=1--", "password": "any"}
        )
        assert resp.status_code == 200
        assert "Operations Control" in resp.text
        assert "Available Internal Endpoints" in resp.text

@pytest.mark.asyncio
async def test_web_emulator_dynamic_endpoints():
    transport = httpx.ASGITransport(app=app)
    async with httpx.AsyncClient(transport=transport, base_url="http://testserver") as client:
        # Users endpoint
        res_users = await client.get("/api/users")
        assert res_users.status_code == 200
        data_users = res_users.json()
        assert data_users["status"] == "success"
        assert len(data_users["data"]) >= 1

        # Config endpoint
        res_cfg = await client.get("/api/config")
        assert res_cfg.status_code == 200
        data_cfg = res_cfg.json()
        assert "database" in data_cfg
        assert "staging" in data_cfg["environment"]
