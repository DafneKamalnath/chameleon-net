"""Virtual in-memory filesystem for SSH honeypot."""
from typing import Dict, List, Optional
from core.models import DecoyItem

class VirtualFileSystem:
    """
    Virtual in-memory filesystem tree that maintains synthetic files and planted decoys.
    Guarantees that no host file is ever accessed, read, or modified.
    """
    def __init__(self, base_username: str = "ubuntu"):
        self.username = base_username
        self.files: Dict[str, str] = {
            f"/home/{self.username}/.bashrc": "# ~/.bashrc: executed by bash(1) for non-login shells.\nexport PATH=$PATH:/usr/local/bin\n",
            f"/home/{self.username}/.profile": "# ~/.profile: executed by Bourne-compatible login shells.\n",
            f"/home/{self.username}/src/notes.txt": "TODO: rotate staging database credentials before Friday release.\n",
            "/etc/motd": "Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-89-generic x86_64)\n",
        }
        self.decoys: Dict[str, DecoyItem] = {}

    def read_file(self, path: str) -> Optional[str]:
        if path in self.decoys:
            return self.decoys[path].content
        return self.files.get(path)

    def write_file(self, path: str, content: str):
        self.files[path] = content

    def inject_decoy(self, decoy: DecoyItem):
        self.decoys[decoy.path] = decoy

    def list_dir(self, directory: str) -> List[str]:
        prefix = directory.rstrip("/") + "/"
        entries = set()
        for path in list(self.files.keys()) + list(self.decoys.keys()):
            if path.startswith(prefix):
                remainder = path[len(prefix):]
                top_level = remainder.split("/")[0]
                if top_level:
                    entries.add(top_level)
        return sorted(list(entries))
