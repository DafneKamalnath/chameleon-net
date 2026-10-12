"""Automated benign attacker simulator for interactive demo presentations."""
import asyncio
import time
from typing import List, Dict
from core.models import ServiceType
from core.pipeline import pipeline

SSH_RECON_SEQUENCE = [
    ("whoami", 0.6),
    ("uname -a", 0.8),
    ("id", 0.5),
    ("cat /etc/os-release", 0.7),
    ("cat /etc/passwd", 0.9),
    ("ps aux", 1.0),
    ("sudo -l", 1.2),
    ("find / -perm -4000", 1.1),
    ("cat ~/.aws/credentials", 1.4),
    ("cat /etc/hosts", 0.8),
    ("cat ~/.db_staging.env", 1.2),
]

WEB_INTRUSION_SEQUENCE = [
    ("GET /", 0.5),
    ("POST /login (SQLi payload: admin' OR '1'='1)", 0.8),
    ("GET /admin", 0.6),
    ("GET /api/users", 0.9),
    ("GET /api/config", 1.1),
]

async def run_simulated_attack(scenario: str = "ssh_recon"):
    """
    Executes a realistic benign reconnaissance sequence to demonstrate live adaptation.
    """
    session_id = f"sim-{scenario[:4]}-{int(time.time())}"
    source_ip = "192.0.2.145"

    if scenario == "ssh_recon":
        for cmd, delay in SSH_RECON_SEQUENCE:
            await pipeline.execute_cycle(
                session_id=session_id,
                service=ServiceType.SSH,
                source_ip=source_ip,
                raw_input=cmd,
                profile="ubuntu_web_server"
            )
            await asyncio.sleep(delay)

    elif scenario == "web_intrusion":
        for req, delay in WEB_INTRUSION_SEQUENCE:
            await pipeline.execute_cycle(
                session_id=session_id,
                service=ServiceType.WEB,
                source_ip=source_ip,
                raw_input=req,
                profile="ubuntu_web_server"
            )
            await asyncio.sleep(delay)
