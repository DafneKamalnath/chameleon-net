"""High-fidelity local Mock LLM provider for offline honeypot emulation."""
from typing import Dict, Any, List
import re
from core.models import ServiceType, FidelityMode
from orchestrator.client import LLMClient
from orchestrator.prompts import PROFILES

class MockLLMClient(LLMClient):
    """
    Offline realistic mock provider. Emulates standard Unix utilities,
    staged web services, and realistic error responses without external API calls.
    """

    async def generate_response(
        self,
        service: ServiceType,
        command_or_input: str,
        session_id: str,
        profile: str,
        fidelity: FidelityMode,
        context: Dict[str, Any],
        decoys: List[Dict[str, str]]
    ) -> str:
        cmd = command_or_input.strip()
        profile_data = PROFILES.get(profile, PROFILES["ubuntu_web_server"])
        hostname = profile_data["hostname"]
        username = profile_data["username"]
        os_version = profile_data["os_version"]

        if service == ServiceType.WEB:
            return self._handle_web(cmd, profile_data, fidelity)

        # SSH / Shell handler
        return self._handle_ssh(cmd, profile_data, fidelity, context, decoys)

    def _handle_ssh(
        self,
        cmd: str,
        profile: Dict[str, Any],
        fidelity: FidelityMode,
        context: Dict[str, Any],
        decoys: List[Dict[str, str]]
    ) -> str:
        hostname = profile["hostname"]
        username = profile["username"]
        cwd = context.get("cwd", f"/home/{username}")
        virtual_files = context.get("virtual_files", {})

        # Empty command
        if not cmd:
            return ""

        # Check virtual files or decoys first for cat / head / tail / more / less
        cat_match = re.match(r"^(cat|head|tail|more|less)\s+([^\s]+)", cmd)
        if cat_match:
            filepath = cat_match.group(2)
            if filepath.startswith("~/"):
                filepath = f"/home/{username}/{filepath[2:]}"
            elif filepath == "~":
                filepath = f"/home/{username}"
            elif not filepath.startswith("/"):
                filepath = f"{cwd.rstrip('/')}/{filepath}"

            # Check decoys
            for d in decoys:
                if d.get("path") == filepath or filepath.endswith(d.get("path", "")):
                    return d.get("content", "")

            # Check virtual files
            if filepath in virtual_files:
                return virtual_files[filepath]

            # Common system files
            if filepath in ["/etc/passwd", "passwd"]:
                return (
                    f"root:x:0:0:root:/root:/bin/bash\n"
                    f"daemon:x:1:1:daemon:/usr/sbin:/usr/sbin/nologin\n"
                    f"bin:x:2:2:bin:/bin:/usr/sbin/nologin\n"
                    f"sys:x:3:3:sys:/dev:/usr/sbin/nologin\n"
                    f"sync:x:4:65534:sync:/bin:/bin/sync\n"
                    f"www-data:x:33:33:www-data:/var/www:/usr/sbin/nologin\n"
                    f"{username}:x:1000:1000:{username.capitalize()} User,,,:/home/{username}:/bin/bash\n"
                    f"deploy:x:1001:1001:CI/CD Deployment Service:/home/deploy:/bin/bash\n"
                    f"sshd:x:110:65534::/run/sshd:/usr/sbin/nologin\n"
                )

            if filepath in ["/etc/os-release", "/etc/issue"]:
                return (
                    'PRETTY_NAME="Ubuntu 22.04.3 LTS"\n'
                    'NAME="Ubuntu"\n'
                    'VERSION_ID="22.04"\n'
                    'VERSION="22.04.3 LTS (Jammy Jellyfish)"\n'
                    'ID=ubuntu\n'
                    'ID_LIKE=debian\n'
                    'HOME_URL="https://www.ubuntu.com/"\n'
                    'SUPPORT_URL="https://help.ubuntu.com/"\n'
                    'UBUNTU_CODENAME=jammy\n'
                )

            if filepath in ["/etc/hosts"]:
                return (
                    "127.0.0.1 localhost\n"
                    f"127.0.1.1 {hostname}\n"
                    "10.0.1.5 db-internal.apex.corp\n"
                    "10.0.1.12 cache-redis.apex.corp\n"
                    "10.0.2.20 backup-vault.apex.corp\n"
                )

            if filepath in ["/etc/shadow"]:
                return "cat: /etc/shadow: Permission denied"

            if filepath.endswith(".bash_history") or filepath == "~/.bash_history":
                return (
                    "git pull origin main\n"
                    "sudo systemctl restart nginx\n"
                    "docker ps -a\n"
                    "cat /opt/scripts/deploy.sh\n"
                    "curl -s http://169.254.169.254/latest/meta-data/\n"
                    "ssh deploy@10.0.1.5\n"
                )

            return f"cat: {filepath}: No such file or directory"

        # Standard commands
        if cmd == "whoami":
            return username

        if cmd == "id":
            return f"uid=1000({username}) gid=1000({username}) groups=1000({username}),4(adm),24(cdrom),27(sudo),30(dip),46(plugdev),110(lxd)"

        if cmd in ["uname -a", "uname -srm", "uname"]:
            if cmd == "uname":
                return "Linux"
            return f"Linux {hostname} 5.15.0-89-generic #99-Ubuntu SMP Mon Oct 30 20:42:41 UTC 2023 x86_64 x86_64 x86_64 GNU/Linux"

        if cmd == "hostname":
            return hostname

        if cmd in ["pwd", "echo $PWD"]:
            return cwd

        if cmd.startswith("ls"):
            # Check if listing decoys
            decoy_names = [d["path"].split("/")[-1] for d in decoys]
            if cwd == f"/home/{username}":
                base_files = ["Desktop", "Documents", "Downloads", "src", ".bashrc", ".profile", ".ssh"]
                all_files = base_files + decoy_names
                if "-la" in cmd or "-l" in cmd:
                    return "\n".join([f"-rw-r--r-- 1 {username} {username} 4096 Oct 10 14:20 {f}" for f in all_files])
                return "  ".join(all_files)
            elif cwd == "/var/www/html":
                return "index.html  assets  api  config.php"
            else:
                return "bin  boot  dev  etc  home  lib  media  mnt  opt  proc  root  run  sbin  srv  sys  tmp  usr  var"

        if cmd == "ps aux" or cmd == "ps -ef":
            return (
                "USER         PID %CPU %MEM    VSZ   RSS TTY      STAT START   TIME COMMAND\n"
                "root           1  0.0  0.2 168344 11420 ?        Ss   09:00   0:02 /sbin/init\n"
                "root         412  0.0  0.1  45120  6800 ?        Ss   09:00   0:00 /lib/systemd/systemd-udevd\n"
                "systemd+     615  0.0  0.2  89400 12000 ?        Ss   09:00   0:01 /lib/systemd/systemd-resolved\n"
                "root         780  0.0  0.1  15890  4500 ?        Ss   09:00   0:00 /usr/sbin/cron -f\n"
                "root         890  0.0  0.2  18900  8900 ?        Ss   09:00   0:00 /usr/sbin/sshd -D\n"
                "www-data    1024  0.1  1.2 245000 48000 ?        S    09:01   0:05 nginx: worker process\n"
                "www-data    1025  0.1  1.2 245000 48000 ?        S    09:01   0:05 nginx: worker process\n"
                f"{username}    1420  0.0  0.3  22400 14000 pts/0    Ss   09:30   0:00 -bash\n"
                f"{username}    1890  0.0  0.1  18900  3400 pts/0    R+   09:35   0:00 ps aux\n"
            )

        if cmd in ["ifconfig", "ip a", "ip addr"]:
            return (
                "1: lo: <LOOPBACK,UP,LOWER_UP> mtu 65536 qdisc noqueue state UNKNOWN\n"
                "    link/loopback 00:00:00:00:00:00 brd 00:00:00:00:00:00\n"
                "    inet 127.0.0.1/8 scope host lo\n"
                "2: eth0: <BROADCAST,MULTICAST,UP,LOWER_UP> mtu 1500 qdisc mq state UP\n"
                "    link/ether 02:42:0a:00:01:2a brd ff:ff:ff:ff:ff:ff\n"
                "    inet 10.0.1.42/24 brd 10.0.1.255 scope global dynamic eth0\n"
            )

        if cmd in ["netstat -tuln", "ss -tuln"]:
            return (
                "Active Internet connections (only servers)\n"
                "Proto Recv-Q Send-Q Local Address           Foreign Address         State\n"
                "tcp        0      0 0.0.0.0:22              0.0.0.0:*               LISTEN\n"
                "tcp        0      0 0.0.0.0:80              0.0.0.0:*               LISTEN\n"
                "tcp        0      0 0.0.0.0:443             0.0.0.0:*               LISTEN\n"
                "tcp        0      0 127.0.0.1:6379          0.0.0.0:*               LISTEN\n"
                "tcp        0      0 127.0.0.1:3306          0.0.0.0:*               LISTEN\n"
            )

        if "sudo -l" in cmd:
            return (
                f"Matching Defaults entries for {username} on {hostname}:\n"
                "    env_reset, mail_badpass, secure_path=/usr/local/sbin\\:/usr/local/bin\\:/usr/sbin\\:/usr/bin\\:/sbin\\:/bin\n\n"
                f"User {username} may run the following commands on {hostname}:\n"
                "    (ALL : ALL) ALL\n"
                "    (root) NOPASSWD: /usr/bin/systemctl restart nginx\n"
            )

        if cmd.startswith("sudo"):
            return f"[sudo] password for {username}: \nsudo: 3 incorrect password attempts"

        if "find" in cmd and "4000" in cmd:
            return (
                "/usr/bin/sudo\n"
                "/usr/bin/passwd\n"
                "/usr/bin/chsh\n"
                "/usr/bin/gpasswd\n"
                "/usr/bin/newgrp\n"
                "/usr/lib/openssh/ssh-keysign\n"
            )

        if cmd.startswith("env") or cmd.startswith("printenv"):
            return "\n".join([f"{k}={v}" for k, v in context.get("env_vars", {}).items()])

        if cmd.startswith("echo"):
            return cmd[5:].strip().strip('"').strip("'")

        if cmd.startswith("ping") or cmd.startswith("curl") or cmd.startswith("wget"):
            # Enforce simulated timeout / egress blocked realism
            return f"{cmd.split()[0]}: connect: Network is unreachable (egress containment policy active)"

        # Default realistic linux fallback
        first_token = cmd.split()[0] if cmd.split() else cmd
        return f"bash: {first_token}: command not found"

    def _handle_web(self, path_or_query: str, profile: Dict[str, Any], fidelity: FidelityMode) -> str:
        """Dynamic fake web portal handler."""
        if "/api/users" in path_or_query:
            return (
                '{"status":"success","data":['
                '{"id":1,"name":"DevOps Lead","email":"devops@internal-apex.corp","role":"admin"},'
                '{"id":2,"name":"App Server","email":"svc_app@internal-apex.corp","role":"service_account"},'
                '{"id":3,"name":"Security Auditor","email":"secops@internal-apex.corp","role":"viewer"}'
                ']}'
            )

        if "/api/config" in path_or_query:
            return (
                '{"environment":"staging","cluster":"apex-eu-west-1",'
                '"database":{"host":"db-internal.apex.corp","port":5432,"user":"apex_admin","ssl":true},'
                '"auth":{"issuer":"auth.apex.corp","token_ttl_seconds":3600},'
                '"synthetic_vault_key":"vlt-sec-syn-98240-live-demo"}'
            )

        if "/admin" in path_or_query:
            return (
                '<div class="admin-panel">'
                '<h2>ApexCloud Internal Administration Gateway v4.2</h2>'
                '<p class="warning">Authorized Access Only. All audit telemetry is strictly monitored.</p>'
                '<div class="cluster-status">Cluster Status: HEALTHY | Active Pods: 14 | Ingress: Traefik</div>'
                '</div>'
            )

        return '{"status":"ok","system":"ApexCloud Platform Gateway","version":"4.2.1"}'
