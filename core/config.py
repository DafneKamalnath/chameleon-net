"""Configuration management for ChameleonNet."""
import os
from pathlib import Path
from typing import Optional

BASE_DIR = Path(__file__).resolve().parent.parent

def _is_port_in_use(port: int, host: str = "127.0.0.1") -> bool:
    import socket
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex((host, port)) == 0

class Settings:
    # Environment & paths
    ENV: str = os.getenv("CHAMELEON_ENV", "development")
    BASE_DIR: Path = BASE_DIR
    DATA_DIR: Path = BASE_DIR / "data"
    DB_PATH: Path = DATA_DIR / "telemetry.db"
    POLICIES_PATH: Path = BASE_DIR / "policies.yaml"

    # Services ports
    SSH_HOST: str = os.getenv("SSH_HOST", "0.0.0.0")
    SSH_PORT: int = int(os.getenv("SSH_PORT", "2222"))
    WEB_HOST: str = os.getenv("WEB_HOST", "0.0.0.0")
    WEB_PORT: int = int(os.getenv("WEB_PORT", "8088" if _is_port_in_use(8080) else "8080"))
    DASHBOARD_HOST: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    DASHBOARD_PORT: int = int(os.getenv("DASHBOARD_PORT", "8500"))

    # LLM Settings
    LLM_PROVIDER: str = os.getenv("LLM_PROVIDER", "mock")  # mock | gemini | claude
    GEMINI_API_KEY: Optional[str] = os.getenv("GEMINI_API_KEY", None)
    CLAUDE_API_KEY: Optional[str] = os.getenv("CLAUDE_API_KEY", None)
    LLM_MODEL: str = os.getenv("LLM_MODEL", "gemini-2.5-flash")
    LLM_TIMEOUT_SECONDS: float = float(os.getenv("LLM_TIMEOUT_SECONDS", "5.0"))

    # Deception & Profiles
    DEFAULT_PROFILE: str = os.getenv("DEFAULT_PROFILE", "ubuntu_web_server")
    STATIC_FALLBACK_ENABLED: bool = True

    # Security & Containment
    EGRESS_PROHIBITED: bool = True
    MAX_SESSION_DURATION_SECONDS: int = int(os.getenv("MAX_SESSION_DURATION_SECONDS", "3600"))
    RATE_LIMIT_COMMANDS_PER_MINUTE: int = int(os.getenv("RATE_LIMIT_COMMANDS_PER_MINUTE", "60"))

settings = Settings()
settings.DATA_DIR.mkdir(parents=True, exist_ok=True)
