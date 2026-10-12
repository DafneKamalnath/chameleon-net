"""Policy manager with hot-reloading for policies.yaml."""
import os
import yaml
from pathlib import Path
from typing import Dict, Any, Optional
from core.config import settings

DEFAULT_POLICIES = {
    "version": "1.0",
    "containment": {
        "egress_prohibited": True,
        "rate_limit_commands_per_minute": 60,
        "session_timeout_seconds": 3600,
        "pii_scrubbing": True,
    },
    "fidelity_escalation": [
        {"trigger_id": "high_skill", "condition": "skill_score >= 5.5 or dwell_seconds >= 60", "target_fidelity": "high", "reason": "High skill / dwell"},
        {"trigger_id": "velocity", "condition": "command_count >= 5 or skill_score >= 3.0", "target_fidelity": "medium", "reason": "Recon velocity"},
    ],
    "decoy_rules": [],
    "profile_rotation": []
}

class PolicyManager:
    def __init__(self, policy_path: Optional[Path] = None):
        self.policy_path = policy_path or settings.POLICIES_PATH
        self._last_mtime: float = 0.0
        self._cached_policy: Dict[str, Any] = DEFAULT_POLICIES
        self.load_policy()

    def load_policy(self) -> Dict[str, Any]:
        """Loads or reloads policies from YAML if modified."""
        if not self.policy_path.exists():
            self._cached_policy = DEFAULT_POLICIES
            return self._cached_policy

        try:
            mtime = os.path.getmtime(self.policy_path)
            if mtime > self._last_mtime:
                with open(self.policy_path, "r", encoding="utf-8") as f:
                    data = yaml.safe_load(f)
                    if isinstance(data, dict):
                        self._cached_policy = data
                        self._last_mtime = mtime
        except Exception:
            pass
        return self._cached_policy

    def get_policy(self) -> Dict[str, Any]:
        # Fast mtime check for hot-reload
        return self.load_policy()

policy_manager = PolicyManager()
