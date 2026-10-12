"""Session context memory for ChameleonNet to maintain behavioral consistency."""
from typing import Dict, Any, List, Optional
from orchestrator.prompts import PROFILES

class SessionMemory:
    def __init__(self, session_id: str, profile_key: str = "ubuntu_web_server"):
        self.session_id = session_id
        self.profile_key = profile_key
        profile = PROFILES.get(profile_key, PROFILES["ubuntu_web_server"])
        self.hostname: str = profile["hostname"]
        self.username: str = profile["username"]
        self.cwd: str = f"/home/{self.username}"
        self.env_vars: Dict[str, str] = {
            "USER": self.username,
            "LOGNAME": self.username,
            "HOME": f"/home/{self.username}",
            "SHELL": "/bin/bash",
            "HOSTNAME": self.hostname,
            "PATH": "/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin",
            "PWD": self.cwd,
            "TERM": "xterm-256color",
        }
        self.history: List[Dict[str, str]] = []  # [{input, output, timestamp}]
        self.virtual_files: Dict[str, str] = {}  # path -> content
        self.decoys: List[Dict[str, str]] = []

    def set_cwd(self, new_dir: str):
        if new_dir.startswith("/"):
            self.cwd = new_dir
        elif new_dir == "..":
            parts = [p for p in self.cwd.split("/") if p]
            if parts:
                parts.pop()
            self.cwd = "/" + "/".join(parts) if parts else "/"
        elif new_dir == "~" or not new_dir:
            self.cwd = f"/home/{self.username}"
        else:
            self.cwd = f"{self.cwd.rstrip('/')}/{new_dir}"
        self.env_vars["PWD"] = self.cwd

    def add_interaction(self, user_input: str, output: str):
        self.history.append({"input": user_input, "output": output})
        if len(self.history) > 30:
            self.history = self.history[-30:]

    def plant_decoy(self, path: str, content: str, category: str = "general"):
        self.virtual_files[path] = content
        if not any(d["path"] == path for d in self.decoys):
            self.decoys.append({"path": path, "content": content, "category": category})

    def get_prompt_symbol(self) -> str:
        prompt_cwd = "~" if self.cwd == f"/home/{self.username}" else self.cwd
        return f"{self.username}@{self.hostname}:{prompt_cwd}$ "

class MemoryManager:
    def __init__(self):
        self._sessions: Dict[str, SessionMemory] = {}

    def get_session(self, session_id: str, profile_key: str = "ubuntu_web_server") -> SessionMemory:
        if session_id not in self._sessions:
            self._sessions[session_id] = SessionMemory(session_id, profile_key)
        return self._sessions[session_id]

    def reset_session(self, session_id: str):
        if session_id in self._sessions:
            del self._sessions[session_id]

memory_manager = MemoryManager()
