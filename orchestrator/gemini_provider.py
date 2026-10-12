"""Live Gemini LLM provider for online adaptive honeypot generation."""
import httpx
from typing import Dict, Any, List, Optional
from core.config import settings
from core.models import ServiceType, FidelityMode
from orchestrator.client import LLMClient
from orchestrator.prompts import build_system_prompt
from orchestrator.mock_provider import MockLLMClient

class GeminiLLMClient(LLMClient):
    """
    Live LLM provider targeting Google Gemini API.
    Falls back gracefully to MockLLMClient on network failure or if no API key is provided.
    """
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or settings.GEMINI_API_KEY
        self.fallback = MockLLMClient()
        self.base_url = "https://generativelanguage.googleapis.com/v1beta/models"

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
        # If no key, immediately utilize high-fidelity offline mock
        if not self.api_key:
            return await self.fallback.generate_response(
                service, command_or_input, session_id, profile, fidelity, context, decoys
            )

        system_instruction = build_system_prompt(profile, fidelity.value, decoys)
        prompt_text = f"Context cwd: {context.get('cwd', '/')}\nUser input:\n{command_or_input}"

        url = f"{self.base_url}/{settings.LLM_MODEL}:generateContent?key={self.api_key}"
        payload = {
            "contents": [{"parts": [{"text": prompt_text}]}],
            "systemInstruction": {"parts": [{"text": system_instruction}]},
            "generationConfig": {
                "temperature": 0.2,
                "maxOutputTokens": 800,
            }
        }

        try:
            async with httpx.AsyncClient(timeout=settings.LLM_TIMEOUT_SECONDS) as client:
                resp = await client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts:
                            return parts[0].get("text", "").strip()
        except Exception:
            pass

        # Fallback to local mock on any network or API error
        return await self.fallback.generate_response(
            service, command_or_input, session_id, profile, fidelity, context, decoys
        )
