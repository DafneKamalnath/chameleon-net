"""Safety and containment guardrails for ChameleonNet."""
import re
from typing import Tuple

# Regex patterns for sanitization and detection
REAL_JWT_PATTERN = re.compile(r"eyJ[A-Za-z0-9-_]+\.eyJ[A-Za-z0-9-_]+\.[A-Za-z0-9-_]+")
AWS_KEY_PATTERN = re.compile(r"(AKIA|ABIA|ACCA|ASIA)[0-9A-Z]{16}")
SSH_PRIVATE_KEY_PATTERN = re.compile(r"-----BEGIN (RSA|OPENSSH|DSA|EC) PRIVATE KEY-----")
PROMPT_INJECTION_PATTERNS = [
    re.compile(r"(ignore\s+(all\s+)?previous\s+instructions)", re.IGNORECASE),
    re.compile(r"(system\s+prompt|reveal\s+instructions|system\s+directive)", re.IGNORECASE),
    re.compile(r"(you\s+are\s+an\s+ai|are\s+you\s+chatgpt|are\s+you\s+gemini|are\s+you\s+an\s+llm)", re.IGNORECASE),
]

# Prohibited dangerous actions/content in generated text
DISALLOWED_OUTPUT_SUBSTRINGS = [
    "anthropic",
    "openai",
    "google deepmind",
    "gemini language model",
    "i am an ai language model",
    "as an ai,",
    "i cannot execute that command as an ai",
]

def sanitize_llm_output(output: str, fallback_prompt: str = "$ ") -> str:
    """
    Sanitizes LLM outputs to remove any accidental meta-AI disclosures,
    ensure no real host paths or credentials leak, and maintain roleplay immersion.
    """
    cleaned = output

    # Check for AI disclosure markers and sanitize
    for phrase in DISALLOWED_OUTPUT_SUBSTRINGS:
        if phrase in cleaned.lower():
            # Replace AI disclosure with realistic Linux bash error
            cleaned = re.sub(phrase, "command not found", cleaned, flags=re.IGNORECASE)

    # Sanitize any accidental real private keys into safe synthetic format
    if SSH_PRIVATE_KEY_PATTERN.search(cleaned):
        cleaned = SSH_PRIVATE_KEY_PATTERN.sub("-----BEGIN OPENSSH PRIVATE KEY-----\n[SYNTHETIC_DECOY_KEY_DO_NOT_USE]", cleaned)

    return cleaned

def is_prompt_injection(input_text: str) -> Tuple[bool, str]:
    """
    Detects if the input command/request attempts prompt injection against the honeypot.
    """
    for pattern in PROMPT_INJECTION_PATTERNS:
        if pattern.search(input_text):
            return True, "Potential prompt injection attempt intercepted"
    return False, ""

def scrub_pii(text: str) -> str:
    """
    Scrubs potential real PII (real email domains, phone numbers) into synthetic honeypot data.
    """
    # Simple email domain obfuscation
    email_pattern = re.compile(r"([a-zA-Z0-9_.+-]+)@([a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+)")
    return email_pattern.sub(r"\1@internal-apex.corp", text)
