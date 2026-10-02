"""Universal LLM Gateway with multi-provider support: Groq, Ollama, OpenRouter, Gemini, OpenAI, Anthropic, and Local vLLM."""

import json
import re
import time
from typing import List, Dict, Any, Optional, Type, TypeVar
import httpx
from pydantic import BaseModel

from app.core.config import get_settings
from app.core.logging import get_logger
from app.core.exceptions import AppBaseException

logger = get_logger("career_copilot.llm")
T = TypeVar("T", bound=BaseModel)


class LLMResponse(BaseModel):
    """Normalized response envelope returned by any LLM provider."""
    content: str
    provider: str
    model: str
    prompt_tokens: Optional[int] = None
    completion_tokens: Optional[int] = None
    latency_ms: float = 0.0


class LLMGateway:
    """Resilient multi-provider LLM dispatcher supporting Groq, Ollama, OpenRouter, and more."""

    def __init__(self):
        self.settings = get_settings()

    async def complete(
        self,
        prompt: str,
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None,
        model: Optional[str] = None,
        temperature: float = 0.2,
        max_tokens: int = 2048
    ) -> LLMResponse:
        """Dispatches prompt to selected or default LLM provider with fallback handling."""
        active_provider = (provider or self.settings.default_llm_provider).lower()
        start_time = time.perf_counter()

        try:
            if active_provider == "groq":
                return await self._call_groq(prompt, system_prompt, model, temperature, max_tokens, start_time)
            elif active_provider == "ollama":
                return await self._call_ollama(prompt, system_prompt, model, temperature, max_tokens, start_time)
            elif active_provider == "openrouter":
                return await self._call_openrouter(prompt, system_prompt, model, temperature, max_tokens, start_time)
            elif active_provider == "gemini":
                return await self._call_gemini(prompt, system_prompt, model, temperature, max_tokens, start_time)
            elif active_provider == "openai":
                return await self._call_openai(prompt, system_prompt, model, temperature, max_tokens, start_time)
            elif active_provider == "anthropic":
                return await self._call_anthropic(prompt, system_prompt, model, temperature, max_tokens, start_time)
            elif active_provider == "custom":
                return await self._call_custom_openai_compatible(prompt, system_prompt, model, temperature, max_tokens, start_time)
            else:
                # Default to Groq if key exists, otherwise Ollama or mock fallback
                if self.settings.groq_api_key:
                    return await self._call_groq(prompt, system_prompt, model, temperature, max_tokens, start_time)
                return await self._call_ollama(prompt, system_prompt, model, temperature, max_tokens, start_time)
        except Exception as exc:
            logger.warning(f"Primary provider '{active_provider}' call failed: {exc}. Attempting fallback...")
            return self._mock_or_fallback_response(prompt, active_provider, start_time)

    async def _call_groq(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        start_time: float
    ) -> LLMResponse:
        """Executes completion via Groq Cloud API."""
        api_key = self.settings.groq_api_key
        if not api_key or "your_groq_api_key" in api_key:
            raise AppBaseException("GROQ_API_KEY is not configured in .env")

        target_model = model or self.settings.groq_default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post("https://api.groq.com/openai/v1/chat/completions", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice,
            provider="groq",
            model=target_model,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            latency_ms=latency
        )

    async def _call_ollama(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        start_time: float
    ) -> LLMResponse:
        """Executes completion via local Ollama instance."""
        base_url = self.settings.ollama_base_url.rstrip("/")
        target_model = model or self.settings.ollama_default_model

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        payload = {
            "model": target_model,
            "messages": messages,
            "stream": False,
            "options": {"temperature": temperature, "num_predict": max_tokens}
        }

        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(f"{base_url}/api/chat", json=payload)
            res.raise_for_status()
            data = res.json()

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        content = data.get("message", {}).get("content", "")

        return LLMResponse(
            content=content,
            provider="ollama",
            model=target_model,
            prompt_tokens=data.get("prompt_eval_count"),
            completion_tokens=data.get("eval_count"),
            latency_ms=latency
        )

    async def _call_openrouter(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        start_time: float
    ) -> LLMResponse:
        """Executes completion via OpenRouter gateway."""
        api_key = self.settings.openrouter_api_key
        if not api_key:
            raise AppBaseException("OPENROUTER_API_KEY is not configured in .env")

        target_model = model or self.settings.openrouter_default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/career-copilot",
            "X-Title": "Career Copilot",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "messages": messages,
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post("https://openrouter.ai/api/v1/chat/completions", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        choice = data["choices"][0]["message"]["content"]
        usage = data.get("usage", {})

        return LLMResponse(
            content=choice,
            provider="openrouter",
            model=target_model,
            prompt_tokens=usage.get("prompt_tokens"),
            completion_tokens=usage.get("completion_tokens"),
            latency_ms=latency
        )

    async def _call_gemini(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        start_time: float
    ) -> LLMResponse:
        """Executes completion via Google Gemini REST API."""
        api_key = self.settings.gemini_api_key
        if not api_key:
            raise AppBaseException("GEMINI_API_KEY is not configured in .env")

        target_model = model or self.settings.gemini_default_model
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key}"

        contents = []
        if system_prompt:
            contents.append({"role": "user", "parts": [{"text": f"SYSTEM INSTRUCTION: {system_prompt}"}]})
        contents.append({"role": "user", "parts": [{"text": prompt}]})

        payload = {
            "contents": contents,
            "generationConfig": {
                "temperature": temperature,
                "maxOutputTokens": max_tokens
            }
        }

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post(url, json=payload)
            res.raise_for_status()
            data = res.json()

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        candidates = data.get("candidates", [])
        text = candidates[0]["content"]["parts"][0]["text"] if candidates else ""

        return LLMResponse(
            content=text,
            provider="gemini",
            model=target_model,
            latency_ms=latency
        )

    async def _call_openai(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        start_time: float
    ) -> LLMResponse:
        """Executes completion via OpenAI API."""
        api_key = self.settings.openai_api_key
        if not api_key:
            raise AppBaseException("OPENAI_API_KEY is not configured in .env")

        target_model = model or self.settings.openai_default_model
        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": target_model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post("https://api.openai.com/v1/chat/completions", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            provider="openai",
            model=target_model,
            latency_ms=latency
        )

    async def _call_anthropic(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        start_time: float
    ) -> LLMResponse:
        """Executes completion via Anthropic Claude Messages API."""
        api_key = self.settings.anthropic_api_key
        if not api_key:
            raise AppBaseException("ANTHROPIC_API_KEY is not configured in .env")

        target_model = model or self.settings.anthropic_default_model
        headers = {
            "x-api-key": api_key,
            "anthropic-version": "2023-06-01",
            "Content-Type": "application/json"
        }
        payload = {
            "model": target_model,
            "max_tokens": max_tokens,
            "messages": [{"role": "user", "content": prompt}]
        }
        if system_prompt:
            payload["system"] = system_prompt

        async with httpx.AsyncClient(timeout=30.0) as client:
            res = await client.post("https://api.anthropic.com/v1/messages", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        content_parts = data.get("content", [])
        text = content_parts[0]["text"] if content_parts else ""

        return LLMResponse(
            content=text,
            provider="anthropic",
            model=target_model,
            latency_ms=latency
        )

    async def _call_custom_openai_compatible(
        self,
        prompt: str,
        system_prompt: Optional[str],
        model: Optional[str],
        temperature: float,
        max_tokens: int,
        start_time: float
    ) -> LLMResponse:
        """Executes completion via custom local inference servers (vLLM, LM Studio, LocalAI)."""
        base_url = (self.settings.custom_llm_base_url or "http://localhost:1234/v1").rstrip("/")
        api_key = self.settings.custom_llm_api_key or "local"
        target_model = model or self.settings.custom_llm_model or "local-model"

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}
        payload = {"model": target_model, "messages": messages, "temperature": temperature, "max_tokens": max_tokens}

        async with httpx.AsyncClient(timeout=45.0) as client:
            res = await client.post(f"{base_url}/chat/completions", headers=headers, json=payload)
            res.raise_for_status()
            data = res.json()

        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return LLMResponse(
            content=data["choices"][0]["message"]["content"],
            provider="custom_local",
            model=target_model,
            latency_ms=latency
        )

    def _mock_or_fallback_response(self, prompt: str, provider: str, start_time: float) -> LLMResponse:
        """Deterministic local fallback when external LLM APIs are offline or unconfigured."""
        latency = round((time.perf_counter() - start_time) * 1000, 2)
        return LLMResponse(
            content=f"[Deterministic Fallback] Processed query offline. LLM Provider '{provider}' not connected.",
            provider="deterministic_fallback",
            model="offline_rule_engine",
            latency_ms=latency
        )

    async def complete_structured(
        self,
        prompt: str,
        schema: Type[T],
        system_prompt: Optional[str] = None,
        provider: Optional[str] = None
    ) -> T:
        """Prompts LLM with strict JSON schema instructions and validates response into Pydantic model."""
        json_instruction = (
            f"\n\nYou MUST respond STRICTLY with a valid JSON object conforming to this schema:\n"
            f"{json.dumps(schema.model_json_schema(), indent=2)}\n"
            f"Do not include markdown code block backticks (```json) or conversational text. Return ONLY the raw JSON object."
        )
        full_prompt = prompt + json_instruction
        response = await self.complete(prompt=full_prompt, system_prompt=system_prompt, provider=provider, temperature=0.1)

        # Extract JSON substring
        raw_text = response.content.strip()
        json_match = re.search(r"\{[\s\S]*\}", raw_text)
        if json_match:
            clean_json = json_match.group(0)
        else:
            clean_json = raw_text

        parsed_dict = json.loads(clean_json)
        return schema.model_validate(parsed_dict)


llm_gateway = LLMGateway()
