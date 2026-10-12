"""Main entrypoint for ChameleonNet deception platform.
Launches the SSH honeypot daemon, Web emulator, and Live Operations Dashboard concurrently.
"""
import asyncio
import logging
import uvicorn
from core.config import settings
from emulators.ssh.server import start_ssh_server
from emulators.web.app import app as web_app
from dashboard.api import dashboard_app

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("ChameleonNet")

async def run_server(app, host: str, port: int, name: str):
    config = uvicorn.Config(
        app=app,
        host=host,
        port=port,
        log_level="warning",
        access_log=False,
    )
    server = uvicorn.Server(config)
    logger.info(f"[{name}] Listening on http://{host}:{port}")
    await server.serve()

async def main():
    logger.info("=" * 60)
    logger.info("Starting ChameleonNet: LLM-Powered Adaptive Honeypot")
    logger.info(f"Default Profile: {settings.DEFAULT_PROFILE}")
    logger.info(f"LLM Provider: {settings.LLM_PROVIDER}")
    logger.info(f"Egress Prohibited: {settings.EGRESS_PROHIBITED}")
    logger.info("=" * 60)

    # 1. Start SSH Emulator
    ssh_server = await start_ssh_server(host=settings.SSH_HOST, port=settings.SSH_PORT)
    logger.info(f"[SSH Emulator] Listening on {settings.SSH_HOST}:{settings.SSH_PORT}")

    # 2. Start Web Emulator & Dashboard
    try:
        await asyncio.gather(
            run_server(web_app, settings.WEB_HOST, settings.WEB_PORT, "Web Emulator"),
            run_server(dashboard_app, settings.DASHBOARD_HOST, settings.DASHBOARD_PORT, "Live Dashboard"),
        )
    finally:
        ssh_server.close()
        await ssh_server.wait_closed()
        logger.info("ChameleonNet shutdown complete.")

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Terminated by user.")
