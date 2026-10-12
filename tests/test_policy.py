"""Unit tests for the Adaptive Policy Engine, fidelity escalation, and decoy injection."""
import pytest
from core.models import ServiceType, FidelityMode, Session
from policy.rules import policy_engine
from policy.manager import policy_manager
from orchestrator.memory import memory_manager

def test_fidelity_escalation():
    # Novice session with low metrics
    low_sess = Session(
        session_id="test-policy-low",
        service=ServiceType.SSH,
        source_ip="10.0.0.1",
        dwell_seconds=5.0,
        command_count=2,
        skill_score=1.5,
        current_profile="ubuntu_web_server",
        current_fidelity=FidelityMode.LOW,
    )
    act_low = policy_engine.evaluate_adaptation(low_sess, "ls")
    # No escalation yet
    assert act_low.upgrade_fidelity is None

    # Intermediate session exceeding command count
    med_sess = Session(
        session_id="test-policy-med",
        service=ServiceType.SSH,
        source_ip="10.0.0.1",
        dwell_seconds=20.0,
        command_count=6,
        skill_score=3.5,
        current_profile="ubuntu_web_server",
        current_fidelity=FidelityMode.LOW,
    )
    act_med = policy_engine.evaluate_adaptation(med_sess, "uname -a")
    assert act_med.upgrade_fidelity == FidelityMode.MEDIUM

    # High skill session exceeding skill threshold
    high_sess = Session(
        session_id="test-policy-high",
        service=ServiceType.SSH,
        source_ip="10.0.0.1",
        dwell_seconds=75.0,
        command_count=12,
        skill_score=6.8,
        current_profile="ubuntu_web_server",
        current_fidelity=FidelityMode.MEDIUM,
    )
    act_high = policy_engine.evaluate_adaptation(high_sess, "sudo -l")
    assert act_high.upgrade_fidelity == FidelityMode.HIGH

def test_dynamic_decoy_injection():
    sess_id = "test-decoy-injection"
    sess = Session(
        session_id=sess_id,
        service=ServiceType.SSH,
        source_ip="10.0.0.2",
        dwell_seconds=40.0,
        command_count=5,
        skill_score=4.0,
        current_profile="ubuntu_web_server",
        current_fidelity=FidelityMode.MEDIUM,
        technique_counts={"T1548: Abuse Elevation Control Mechanism": 1},
    )

    action = policy_engine.evaluate_adaptation(sess, "sudo -l")
    assert len(action.inject_decoys) > 0
    decoy_paths = [d.path for d in action.inject_decoys]
    assert any(".aws/credentials" in p for p in decoy_paths)

    # Verify planted in session memory
    mem = memory_manager.get_session(sess_id, "ubuntu_web_server")
    assert any(".aws/credentials" in d["path"] for d in mem.decoys)

def test_hot_reload_policy_config():
    policy = policy_manager.get_policy()
    assert "containment" in policy
    assert "fidelity_escalation" in policy
    assert "decoy_rules" in policy
    assert policy["containment"]["egress_prohibited"] is True
