"""Explicit 4-stage feedback loop pipeline:
Interaction Captured -> Telemetry Analyzed -> LLM Generates Response -> Honeypot Adapts.
"""
import time
from typing import Dict, Any, Tuple, Optional
from core.models import ServiceType, FidelityMode, Event, Session, AdaptationAction
from telemetry.engine import telemetry_engine
from policy.rules import policy_engine
from orchestrator.engine import orchestrator_engine

class DeceptionPipeline:
    """
    Coordinates the closed-loop deception cycle and records stage transitions
    for visualization in the live dashboard.
    """
    def __init__(self):
        self.last_pipeline_state: Dict[str, Any] = {
            "stage": "IDLE",
            "session_id": "",
            "service": "",
            "input": "",
            "timestamp": time.time(),
            "telemetry": {},
            "adaptation": {},
            "response_preview": ""
        }

    async def execute_cycle(
        self,
        session_id: str,
        service: ServiceType,
        source_ip: str,
        raw_input: str,
        profile: str = "ubuntu_web_server"
    ) -> Tuple[str, Event, Session, AdaptationAction]:
        t0 = time.time()

        # -------------------------------------------------------------
        # STAGE 1: Interaction Captured
        # -------------------------------------------------------------
        self.last_pipeline_state["stage"] = "INTERACTION_CAPTURED"
        self.last_pipeline_state["session_id"] = session_id
        self.last_pipeline_state["service"] = service.value
        self.last_pipeline_state["input"] = raw_input
        self.last_pipeline_state["timestamp"] = t0

        # Retrieve or initialize session
        session = telemetry_engine.get_or_create_session(
            session_id=session_id,
            service=service,
            source_ip=source_ip,
            profile=profile
        )

        # -------------------------------------------------------------
        # STAGE 2: Telemetry Analyzed
        # -------------------------------------------------------------
        self.last_pipeline_state["stage"] = "TELEMETRY_ANALYZED"
        # Classify techniques and preview skill updates
        from telemetry.mitre_tags import classify_techniques
        techniques = classify_techniques(raw_input)
        for t in techniques:
            session.technique_counts[t] = session.technique_counts.get(t, 0) + 1
        session.command_count += 1
        session.dwell_seconds = round(time.time() - session.start_time, 2)
        session.skill_score = telemetry_engine.calculate_skill_score(session, raw_input)

        self.last_pipeline_state["telemetry"] = {
            "dwell_seconds": session.dwell_seconds,
            "command_count": session.command_count,
            "skill_score": session.skill_score,
            "techniques": techniques
        }

        # -------------------------------------------------------------
        # STAGE 3: Honeypot Adapts (Policy Layer)
        # -------------------------------------------------------------
        self.last_pipeline_state["stage"] = "HONEYPOT_ADAPTS"
        adaptation = policy_engine.evaluate_adaptation(session, raw_input)

        if adaptation.upgrade_fidelity:
            session.current_fidelity = adaptation.upgrade_fidelity

        if adaptation.rotate_profile:
            session.current_profile = adaptation.rotate_profile

        self.last_pipeline_state["adaptation"] = {
            "current_fidelity": session.current_fidelity.value,
            "decoys_injected": [d.path for d in adaptation.inject_decoys],
            "reasons": adaptation.reasons,
            "profile": session.current_profile
        }

        # -------------------------------------------------------------
        # STAGE 4: LLM Generates Response
        # -------------------------------------------------------------
        self.last_pipeline_state["stage"] = "LLM_GENERATES_RESPONSE"
        response_text = await orchestrator_engine.handle_input(
            service=service,
            session_id=session_id,
            command_or_input=raw_input,
            profile=session.current_profile,
            fidelity=session.current_fidelity,
            decoys=[d.model_dump() for d in adaptation.inject_decoys]
        )

        # Apply any artificial throttle delay if requested by rate limiting policy
        if adaptation.apply_delay_ms > 0:
            import asyncio
            await asyncio.sleep(adaptation.apply_delay_ms / 1000.0)

        latency = (time.time() - t0) * 1000.0

        # Commit final event and session state to SQLite
        telemetry_engine.db.upsert_session(session)
        event = Event(
            session_id=session_id,
            timestamp=time.time(),
            source_ip=source_ip,
            service=service,
            raw_input=raw_input,
            response_summary=response_text[:200] if response_text else "",
            latency_ms=round(latency, 2),
            technique_tags=techniques,
            fidelity_mode=session.current_fidelity,
            metadata={"adaptation_reasons": adaptation.reasons}
        )
        event.id = telemetry_engine.db.insert_event(event)

        # Broadcast live updates
        telemetry_engine.notify_subscribers(event, session)

        self.last_pipeline_state["stage"] = "CYCLE_COMPLETE"
        self.last_pipeline_state["response_preview"] = response_text[:120]

        return response_text, event, session, adaptation

pipeline = DeceptionPipeline()
