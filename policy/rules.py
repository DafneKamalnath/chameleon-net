"""Rule-based adaptive policy engine for dynamic honeypot behavior adjustment."""
from typing import List, Optional, Dict, Any
from core.models import Session, FidelityMode, AdaptationAction, DecoyItem
from policy.manager import policy_manager, PolicyManager
from orchestrator.memory import memory_manager

class PolicyEngine:
    def __init__(self, manager: Optional[PolicyManager] = None):
        self.manager = manager or policy_manager

    def evaluate_adaptation(self, session: Session, recent_input: str) -> AdaptationAction:
        """
        Evaluates session metrics against active policies and produces an AdaptationAction.
        """
        policy = self.manager.get_policy()
        action = AdaptationAction()

        # 1. Containment: Rate Limit Evaluation
        containment = policy.get("containment", {})
        rate_limit = containment.get("rate_limit_commands_per_minute", 60)
        # If commands occur faster than 1 command/sec on average over 10 commands
        if session.command_count > 10 and session.dwell_seconds > 0:
            rate_cpm = (session.command_count / session.dwell_seconds) * 60.0
            if rate_cpm > rate_limit:
                action.rate_limited = True
                action.apply_delay_ms = 1500  # introduce throttling delay
                action.reasons.append(f"Rate limit exceeded ({rate_cpm:.1f} cpm > {rate_limit} cpm)")

        # 2. Fidelity Escalation Evaluation
        escalations = policy.get("fidelity_escalation", [])
        for rule in escalations:
            target = rule.get("target_fidelity", "medium")
            target_mode = FidelityMode(target)

            # Evaluate condition
            cond_str = rule.get("condition", "")
            matched = False
            if "skill_score >= 5.5" in cond_str and session.skill_score >= 5.5:
                matched = True
            elif "dwell_seconds >= 60" in cond_str and session.dwell_seconds >= 60:
                matched = True
            elif "command_count >= 5" in cond_str and session.command_count >= 5:
                matched = True
            elif "skill_score >= 3.0" in cond_str and session.skill_score >= 3.0:
                matched = True

            if matched:
                # Only upgrade fidelity, never downgrade
                priority = {"low": 1, "medium": 2, "high": 3}
                if priority.get(target_mode.value, 1) > priority.get(session.current_fidelity.value, 1):
                    action.upgrade_fidelity = target_mode
                    action.reasons.append(rule.get("reason", f"Upgraded to {target_mode.value} fidelity"))
                    break

        # 3. Decoy Triggers Evaluation
        decoy_rules = policy.get("decoy_rules", [])
        memory = memory_manager.get_session(session.session_id, session.current_profile)
        username = memory.username

        for drule in decoy_rules:
            decoy_id = drule.get("id")
            if decoy_id in session.decoys_revealed:
                continue  # Already injected

            tech_triggers = drule.get("trigger_techniques", [])
            min_skill = drule.get("min_skill_score", 0.0)
            min_dwell = drule.get("min_dwell_seconds", 0)
            min_cmd = drule.get("min_command_count", 0)

            tech_matched = any(t in session.technique_counts for t in tech_triggers)
            qualifies = False
            if tech_matched and session.skill_score >= min_skill:
                qualifies = True
            elif min_dwell > 0 and session.dwell_seconds >= min_dwell:
                qualifies = True
            elif min_cmd > 0 and session.command_count >= min_cmd:
                qualifies = True

            if qualifies:
                dinfo = drule.get("decoy", {})
                raw_path = dinfo.get("path", f"/home/{username}/decoy.txt")
                path = raw_path.replace("{username}", username)
                content = dinfo.get("content", "").replace("{username}", username)

                decoy_item = DecoyItem(
                    path=path,
                    content=content,
                    category=dinfo.get("category", "decoy"),
                    description=dinfo.get("description", "Synthetic decoy file"),
                )
                action.inject_decoys.append(decoy_item)
                action.reasons.append(f"Planted decoy: {path} ({decoy_item.description})")

                # Plant into session memory
                memory.plant_decoy(path, content, decoy_item.category)
                session.decoys_revealed.append(decoy_id)

        # 4. Profile Rotation Evaluation
        rotations = policy.get("profile_rotation", [])
        for rrule in rotations:
            trigger_tech = rrule.get("trigger_technique")
            if trigger_tech in session.technique_counts:
                rot_target = rrule.get("target_profile")
                if rot_target != session.current_profile:
                    action.rotate_profile = rot_target
                    action.reasons.append(f"Rotated honeypot profile to: {rot_target}")
                    break

        return action

policy_engine = PolicyEngine()
