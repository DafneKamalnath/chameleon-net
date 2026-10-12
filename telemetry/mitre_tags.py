"""MITRE ATT&CK technique tagging for ChameleonNet."""
from typing import List, Dict
import re

# MITRE technique definitions with detection rules
TECHNIQUE_RULES: Dict[str, Dict[str, any]] = {
    "T1082: System Information Discovery": {
        "category": "Discovery",
        "patterns": [
            r"\buname\b", r"\bhostname\b", r"\bos-release\b", r"\b/proc/version\b",
            r"\blsb_release\b", r"\barch\b", r"\bsysteminfo\b", r"\bsw_vers\b"
        ],
        "weight": 1.0,
    },
    "T1033: System Owner/User Discovery": {
        "category": "Discovery",
        "patterns": [
            r"\bwhoami\b", r"\bid\b", r"\bwho\b", r"\bw\b", r"\busers\b", r"\blast\b", r"\blastlog\b"
        ],
        "weight": 1.0,
    },
    "T1087: Account Discovery": {
        "category": "Discovery",
        "patterns": [
            r"/etc/passwd", r"/etc/group", r"\bgetent passwd\b", r"\bcut -d: -f1 /etc/passwd\b"
        ],
        "weight": 1.5,
    },
    "T1057: Process Discovery": {
        "category": "Discovery",
        "patterns": [
            r"\bps\b", r"\btop\b", r"\bhtop\b", r"\bpstree\b", r"\bpgrep\b", r"\btasklist\b"
        ],
        "weight": 1.2,
    },
    "T1016: Network Configuration Discovery": {
        "category": "Discovery",
        "patterns": [
            r"\bifconfig\b", r"\bip\s+(addr|a|route)\b", r"\bnetstat\b", r"\bss\b",
            r"\broute\b", r"\barp\b", r"/etc/resolv\.conf", r"/etc/hosts"
        ],
        "weight": 1.5,
    },
    "T1083: File and Directory Discovery": {
        "category": "Discovery",
        "patterns": [
            r"\bls\b", r"\bfind\b", r"\btree\b", r"\bdir\b", r"\blocate\b", r"\bstat\b"
        ],
        "weight": 0.8,
    },
    "T1552: Unsecured Credentials": {
        "category": "Credential Access",
        "patterns": [
            r"/etc/shadow", r"\.ssh/id_rsa", r"\.ssh/authorized_keys", r"\.aws/credentials",
            r"\.env\b", r"\bpassword\b", r"\btoken\b", r"\.bash_history", r"db_config", r"wp-config"
        ],
        "weight": 3.0,
    },
    "T1548: Abuse Elevation Control Mechanism": {
        "category": "Privilege Escalation",
        "patterns": [
            r"\bsudo\s+-l\b", r"\bsudo\b", r"\bsu\b", r"\bpkexec\b", r"/etc/sudoers",
            r"find\s+/\s+-perm\s+-[0-9]*4000", r"\bdoas\b"
        ],
        "weight": 3.5,
    },
    "T1046: Network Service Discovery": {
        "category": "Discovery",
        "patterns": [
            r"\bnmap\b", r"\bnc\b", r"\bcurl\b", r"\bwget\b", r"\bping\b", r"\btelnet\b"
        ],
        "weight": 2.0,
    },
    "T1190: Exploit Public-Facing Application": {
        "category": "Initial Access / Exploitation",
        "patterns": [
            r"('|\")\s*OR\s*('|\"|1=1)", r"\.\./\.\./", r"<script", r"\{\{.*\}\}", r"union\s+select",
            r"/admin", r"/phpmyadmin", r"/actuator", r"/wp-admin", r"\.git/config"
        ],
        "weight": 3.0,
    },
    "T1213: Data from Information Repositories": {
        "category": "Collection",
        "patterns": [
            r"/api/users", r"/api/config", r"\benv\b", r"\bprintenv\b", r"\bhistory\b"
        ],
        "weight": 2.0,
    },
}

COMPILED_RULES = {
    tech: {
        "category": data["category"],
        "weight": data["weight"],
        "patterns": [re.compile(p, re.IGNORECASE) for p in data["patterns"]]
    }
    for tech, data in TECHNIQUE_RULES.items()
}

def classify_techniques(input_text: str) -> List[str]:
    """
    Scans input command or HTTP path/query to detect MITRE ATT&CK technique tags.
    """
    matched = []
    for tech, data in COMPILED_RULES.items():
        for pattern in data["patterns"]:
            if pattern.search(input_text):
                matched.append(tech)
                break
    return matched
