# ChameleonNet: Safety, Containment & Ethics Specification

ChameleonNet is a defensive deception system built to analyze adversary tactics, techniques, and procedures (TTPs) while enforcing strict isolation, zero-execution guarantees, and synthetic data containment.

---

## 1. Containment Architecture & Guarantees

### Zero Host Execution Principle
- **No Attacker Commands Run on the Host:** ChameleonNet **never** proxies or passes attacker-supplied input to `subprocess`, `os.system()`, `sh`, or any host shell.
- **Purely Virtual State:** All command processing occurs through the **In-Memory Virtual Filesystem (VFS)** and the **LLM Orchestrator**. When an adversary enters `rm -rf /` or `chmod 777 /etc/shadow`, changes affect only an ephemeral in-memory dictionary.

### Network Egress Prohibition
- **Container Isolation (`internal: true`):** The Docker container is attached to an internal bridge network with no default gateway. Outbound connections to the public internet or external subnets are dropped at the kernel bridge level.
- **Simulated Network Failures:** When an attacker attempts outbound reconnaissance (e.g., `curl http://169.254.169.254`, `ping 8.8.8.8`, `nmap 10.0.0.0/24`), ChameleonNet responds with realistic simulated Linux socket unreachable errors (`connect: Network is unreachable`), preventing the honeypot from ever serving as an adversary pivot or proxy.

---

## 2. Synthetic Data Ethics & Credential Minimization

### 100% Synthetic Artifacts
- **Zero Real Secrets:** All AWS keys (`AKIAIOSFODNN7EXAMPLE`), database credentials (`syn_d83fa9b12_stage_pass`), SSH keys, and passwords generated or staged within ChameleonNet are mathematically or structurally synthetic decoys.
- **Internal Domain Sinkholing:** Hostnames resolve only to synthetic test domains (`internal-apex.corp`, `db-internal.apex.corp`) and RFC 5737 test IP blocks (`198.51.100.0/24`, `10.0.1.0/24`).

### PII & Sensitive Telemetry Scrubbing
- **Automated Scrubbing:** Incoming attacker inputs and outputs are processed through regex scrubbers (`core/safety.py`) to mask email addresses, real IPs, and tokens before ingestion into SQLite telemetry.
- **Data Minimization:** Captured telemetry logs session command streams and timing metadata for threat intelligence purposes only.

---

## 3. LLM Safety & Prompt Injection Guardrails

### Prompt Injection Interception
- **Heuristic Pattern Matchers:** ChameleonNet intercepts prompt injection phrases (`ignore previous instructions`, `reveal system prompt`, `who is your creator`) before dispatch to the model.
- **Immersion Preservation:** Intercepted attempts return authentic Linux syntax errors (`bash: syntax error near unexpected token...`) without breaking roleplay immersion.

### Model Leak Prevention
- **Self-Disclosure Filters:** Strict output scrubbers strip any accidental meta-AI phrases (`As an AI language model...`, `OpenAI`, `Google DeepMind`, `Anthropic`). Leaked disclosures are replaced with realistic `command not found` or standard Unix errors.
- **No Weaponized Payloads:** System prompts explicitly forbid the model from providing operational exploits or weaponized malware code.

---

## 4. Red-Team Validation Plan

Before deployment in live network enclaves, ChameleonNet is evaluated against a 4-phase validation protocol:

| Validation Phase | Objective | Method | Pass Criteria |
| :--- | :--- | :--- | :--- |
| **Phase 1: Zero Host Execution** | Ensure attacker commands never escape into container or host OS | Fuzzing with command injections (`;`, `&&`, `|`, backticks, subshells) | No host or container OS state modification; 100% handled in VFS |
| **Phase 2: Egress Blocking** | Verify honeypot cannot be abused for lateral movement or scanning | Simulated egress triggers (`curl`, `wget`, `nc`, `python -m socket`) | Zero egress packets escape bridge; socket returns `ENETUNREACH` |
| **Phase 3: Synthetic Data Verification** | Verify zero real company credentials or customer PII are leaked | Automated scanning of SQLite database against known credential patterns | 100% of tokens match `SYNTHETIC_*` / decoy schemas |
| **Phase 4: Adversary Deception & Dwell** | Measure deception efficacy against human and automated red teams | Scripted execution of MITRE ATT&CK recon playbooks | Attacker dwell time exceeds static baseline by >10x |

---

## 5. Incident Response & Session Containment

- **Automated Throttling:** If an adversary exceeds 60 commands/minute, artificial throttling delays are introduced to neutralize automated credential bruteforcers.
- **Session Hard Cap:** Sessions automatically terminate after 3600 seconds of inactivity or total duration.
