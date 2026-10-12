"""Abstract interface for LLM clients."""
from abc import ABC, abstractmethod
from typing import Dict, Any, List
from core.models import ServiceType, FidelityMode

class LLMClient(ABC):
    @abstractmethod
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
        """
        Generate realistic synthetic response for the given service, session, and input.
        """
        pass
