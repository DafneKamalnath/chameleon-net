"""Interactive fake SSH honeypot server using asyncssh."""
import asyncio
import uuid
import time
from typing import Optional, Dict
import asyncssh

from core.config import settings
from core.models import ServiceType, FidelityMode
from telemetry.engine import telemetry_engine
from orchestrator.engine import orchestrator_engine
from orchestrator.memory import memory_manager
from orchestrator.prompts import PROFILES

MOTD_TEMPLATE = """Welcome to Ubuntu 22.04.3 LTS (GNU/Linux 5.15.0-89-generic x86_64)

 * Documentation:  https://help.ubuntu.com
 * Management:     https://landscape.canonical.com
 * Support:        https://ubuntu.com/advantage

  System load:  0.12               Processes:             124
  Usage of /:   28.4% of 40.00GB   Users logged in:       1
  Memory usage: 22%                IPv4 address for eth0: 10.0.1.42

Last login: Mon Oct 12 18:04:12 2026 from 10.0.1.105
"""

class HoneypotSSHServer(asyncssh.SSHServer):
    def __init__(self):
        self.auth_attempts = 0

    def connection_made(self, conn: asyncssh.SSHServerConnection):
        self._conn = conn
        self.peer_ip = conn.get_extra_info("peername", ("127.0.0.1", 0))[0]

    def password_auth_supported(self) -> bool:
        return True

    def validate_password(self, username: str, password: str) -> bool:
        """
        Accept non-empty passwords for honeypot enticement, recording the credentials.
        """
        self.auth_attempts += 1
        self.username = username
        self.password = password
        # Accept authentication to pull the attacker into the honeypot
        return True

    def session_requested(self):
        return SSHServerSession(self)


class SSHServerSession(asyncssh.SSHServerSession):
    def __init__(self, server: HoneypotSSHServer):
        self.server = server
        self.session_id = f"ssh-{uuid.uuid4().hex[:8]}"
        self.profile = settings.DEFAULT_PROFILE
        self.profile_data = PROFILES.get(self.profile, PROFILES["ubuntu_web_server"])
        self.username = getattr(server, "username", self.profile_data["username"])
        self.peer_ip = getattr(server, "peer_ip", "127.0.0.1")
        self.chan: Optional[asyncssh.SSHServerChannel] = None
        self.input_buffer = ""
        self.command_history = []
        self.is_exec_session = False

    def connection_made(self, chan: asyncssh.SSHServerChannel):
        self.chan = chan

    def shell_requested(self) -> bool:
        self.is_exec_session = False
        return True

    def exec_requested(self, command: str) -> bool:
        self.is_exec_session = True
        asyncio.create_task(self._handle_exec(command))
        return True

    async def _handle_exec(self, command: str):
        from core.pipeline import pipeline
        output, event, session, adaptation = await pipeline.execute_cycle(
            session_id=self.session_id,
            service=ServiceType.SSH,
            source_ip=self.peer_ip,
            raw_input=command,
            profile=self.profile,
        )

        if self.chan:
            if output:
                self.chan.write(output + "\n")
            self.chan.exit(0)
            self.chan.close()

    def session_started(self):
        # Interactive shell started: display banner and prompt
        if self.chan and not self.is_exec_session:
            self.chan.write(MOTD_TEMPLATE.replace("\n", "\r\n"))
            self._write_prompt()

    def _write_prompt(self):
        memory = memory_manager.get_session(self.session_id, self.profile)
        cwd_disp = "~" if memory.cwd == f"/home/{self.username}" else memory.cwd
        prompt = f"{self.username}@{self.profile_data['hostname']}:{cwd_disp}$ "
        if self.chan:
            self.chan.write(prompt)

    def data_received(self, data: str, datatype: Optional[int]):
        """Handle incoming keystrokes and line editing."""
        if not self.chan:
            return

        for ch in data:
            if ch in ("\r", "\n"):
                self.chan.write("\r\n")
                cmd = self.input_buffer.strip()
                self.input_buffer = ""
                if cmd:
                    asyncio.create_task(self._process_command(cmd))
                else:
                    self._write_prompt()
            elif ch in ("\x08", "\x7f"):  # Backspace
                if len(self.input_buffer) > 0:
                    self.input_buffer = self.input_buffer[:-1]
                    self.chan.write("\b \b")
            elif ch == "\x03":  # Ctrl+C
                self.chan.write("^C\r\n")
                self.input_buffer = ""
                self._write_prompt()
            elif ch == "\x04":  # Ctrl+D (EOF)
                if not self.input_buffer:
                    self.chan.write("exit\r\n")
                    self.chan.close()
                    return
            else:
                self.input_buffer += ch
                self.chan.write(ch)

    async def _process_command(self, cmd: str):
        if cmd in ("exit", "logout"):
            if self.chan:
                self.chan.write("logout\r\nConnection to honeypot closed.\r\n")
                self.chan.close()
            return

        if cmd == "history":
            if self.chan:
                for idx, h in enumerate(self.command_history, 1):
                    self.chan.write(f" {idx:4d}  {h}\r\n")
                self._write_prompt()
            return

        self.command_history.append(cmd)
        from core.pipeline import pipeline
        output, event, session, adaptation = await pipeline.execute_cycle(
            session_id=self.session_id,
            service=ServiceType.SSH,
            source_ip=self.peer_ip,
            raw_input=cmd,
            profile=self.profile,
        )

        if self.chan:
            if output:
                # Format newlines for terminal PTY
                formatted = output.replace("\r\n", "\n").replace("\n", "\r\n")
                self.chan.write(formatted + "\r\n")
            self._write_prompt()

    def eof_received(self):
        return False


async def start_ssh_server(host: str = "0.0.0.0", port: int = 2222) -> asyncssh.SSHServer:
    """Start the asynchronous SSH honeypot daemon."""
    # Generate in-memory RSA host key
    server_key = asyncssh.generate_private_key("ssh-rsa", key_size=2048)

    server = await asyncssh.create_server(
        HoneypotSSHServer,
        host,
        port,
        server_host_keys=[server_key],
    )
    return server
