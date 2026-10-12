"""Unit tests for Telemetry Engine, MITRE tagging, dwell time, and skill scoring."""
import pytest
import time
from core.models import ServiceType, FidelityMode
from telemetry.engine import telemetry_engine
from telemetry.mitre_tags import classify_techniques

def test_mitre_technique_classification():
    # Recon techniques
    tags_sys = classify_techniques("uname -a && cat /etc/os-release")
    assert any("T1082" in t for t in tags_sys)

    tags_user = classify_techniques("whoami && id")
    assert any("T1033" in t for t in tags_user)

    tags_passwd = classify_techniques("cat /etc/passwd")
    assert any("T1087" in t for t in tags_passwd)

    # Credential access
    tags_cred = classify_techniques("cat /etc/shadow && cat ~/.aws/credentials")
    assert any("T1552" in t for t in tags_cred)

    # Privilege escalation
    tags_priv = classify_techniques("sudo -l && find / -perm -4000")
    assert any("T1548" in t for t in tags_priv)

    # Web attack probe
    tags_web = classify_techniques("/login?user=admin' OR 1=1--")
    assert any("T1190" in t for t in tags_web)

def test_skill_score_scaling():
    sess = telemetry_engine.get_or_create_session(
        session_id="test-skill-sess",
        service=ServiceType.SSH,
        source_ip="10.0.1.12",
        profile="ubuntu_web_server"
    )

    # Basic discovery commands
    score_basic = telemetry_engine.calculate_skill_score(sess, "ls -la")
    assert 1.0 <= score_basic <= 3.0

    # Advanced targeted credential and setuid harvesting
    sess.technique_counts["T1552: Unsecured Credentials"] = 2
    sess.technique_counts["T1548: Abuse Elevation Control Mechanism"] = 2
    sess.command_count = 8
    score_advanced = telemetry_engine.calculate_skill_score(sess, "find / -perm -4000 -exec ls -l {} + | grep root")
    assert score_advanced >= 6.0
    assert score_advanced <= 10.0

def test_telemetry_event_recording():
    sess_id = f"test-event-sess-{int(time.time())}"
    evt = telemetry_engine.record_interaction(
        session_id=sess_id,
        service=ServiceType.SSH,
        source_ip="192.168.1.55",
        raw_input="cat /etc/passwd",
        response_summary="root:x:0:0...",
        latency_ms=14.2,
        fidelity_mode=FidelityMode.MEDIUM,
    )
    assert evt.id is not None
    assert any("T1087" in t for t in evt.technique_tags)

    saved_sess = telemetry_engine.db.get_session(sess_id)
    assert saved_sess is not None
    assert saved_sess.command_count >= 1
    assert saved_sess.skill_score >= 1.0
