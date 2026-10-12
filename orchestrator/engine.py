"""LLM Orchestrator coordinator with safety filtering and memory synchronization."""
import time
from typing import Dict, Any, List, Optional
from core.config import settings
from core.models import ServiceType, FidelityMode
from core.safety import sanitize_llm_output, is_prompt_injection
from orchestrator.client import LLMClient
from orchestrator.mock_provider import MockLLMClient
from orchestrator.gemini_provider import GeminiLLMClient
from orchestrator.memory import memory_manager, SessionMemory

class OrchestratorEngine:
    def __init__(self):
        self.mock_client = MockLLMClient()
        self.gemini_client = GeminiLLMClient()

    def get_client(self) -> LLMClient:
        if settings.LLM_PROVIDER == "gemini" and settings.GEMINI_API_KEY:
            return self.gemini_client
        return self.mock_client

    async def handle_input(
        self,
        service: ServiceType,
        session_id: str,
        command_or_input: str,
        profile: str = "ubuntu_web_server",
        fidelity: FidelityMode = FidelityMode.MEDIUM,
        decoys: Optional[List[Dict[str, str]]] = None
    ) -> str:
        memory = memory_manager.get_session(session_id, profile)

        # 1. Prompt injection check
        is_inj, inj_msg = is_prompt_injection(command_or_input)
        if is_inj:
            # Emulate realistic terminal syntax error or permission denial without breaking immersion
            return f"bash: syntax error near unexpected token `{command_or_input.split()[0]}`"

        # 2. Intercept shell built-ins like `cd` directly in memory
        cmd_stripped = command_or_input.strip()
        if service == ServiceType.SSH and cmd_stripped.startswith("cd "):
            target_dir = cmd_stripped[3:].strip()
            memory.set_cwd(target_dir)
            return ""

        # 3. Intercept `touch` or `echo >` in virtual files
        if service == ServiceType.SSH and cmd_stripped.startswith("touch "):
            filename = cmd_stripped[6:].strip()
            full_path = filename if filename.startswith("/") else f"{memory.cwd.rstrip('/')}/{filename}"
            memory.virtual_files[full_path] = ""
            return ""

        # Combine decoys from memory and policy layer
        active_decoys = memory.decoys + (decoys or [])

        context: Dict[str, Any] = {
            "cwd": memory.cwd,
            "env_vars": memory.env_vars,
            "virtual_files": memory.virtual_files,
            "history": memory.history[-5:],
        }

        # 4. Dispatch to selected LLM provider
        client = self.get_client()
        raw_output = await client.generate_response(
            service=service,
            command_or_input=command_or_input,
            session_id=session_id,
            profile=profile,
            fidelity=fidelity,
            context=context,
            decoys=active_decoys,
        )

        # 5. Sanitize output through safety filters
        safe_output = sanitize_llm_output(raw_output)

        # 6. Record interaction into session memory
        memory.add_interaction(command_or_input, safe_output)

        return safe_output

orchestrator_engine = OrchestratorEngine()
