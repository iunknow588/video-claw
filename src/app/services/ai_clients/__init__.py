"""
AI provider client skeletons.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Dict, Optional

import httpx

from app.core.config import settings
from app.core.logging import get_logger

logger = get_logger(__name__)


class AIProviderError(RuntimeError):
    """Raised when an upstream AI provider call fails."""


@dataclass(slots=True)
class TokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> Dict[str, int]:
        return {
            "input_tokens": int(self.input_tokens or 0),
            "output_tokens": int(self.output_tokens or 0),
            "total_tokens": int(self.total_tokens or 0),
        }


@dataclass(slots=True)
class AIProviderResult:
    data: Dict[str, Any]
    usage: TokenUsage
    raw_response: Dict[str, Any]


class BaseAIClient:
    """Shared HTTP helper for AI provider clients."""

    provider_name = "unknown"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout if timeout is not None else settings.AI_HTTP_TIMEOUT
        self.max_retries = max_retries if max_retries is not None else settings.AI_MAX_RETRIES

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url)

    async def _post_json(
        self,
        *,
        path: str,
        payload: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    return response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "AI provider request failed",
                    provider=self.provider_name,
                    url=url,
                    attempt=attempt + 1,
                    error=str(exc),
                )

        raise AIProviderError(
            f"{self.provider_name} request failed after {self.max_retries + 1} attempt(s): {last_error}"
        )

    @staticmethod
    def extract_json_object(text: str) -> Dict[str, Any]:
        """Try to parse a JSON object from plain text or markdown code fences."""
        content = text.strip()
        if content.startswith("```"):
            lines = content.splitlines()
            if len(lines) >= 3:
                content = "\n".join(lines[1:-1]).strip()
        return json.loads(content)

    @staticmethod
    def estimate_text_tokens(text: str) -> int:
        if not text:
            return 0
        return max(1, len(text) // 4)

    @classmethod
    def normalize_usage(
        cls,
        usage: Optional[Dict[str, Any]],
        *,
        prompt: str = "",
        completion_text: str = "",
    ) -> TokenUsage:
        payload = usage or {}
        input_tokens = int(
            payload.get("prompt_tokens")
            or payload.get("input_tokens")
            or payload.get("promptTokenCount")
            or payload.get("inputTokenCount")
            or 0
        )
        output_tokens = int(
            payload.get("completion_tokens")
            or payload.get("output_tokens")
            or payload.get("candidates_tokens")
            or payload.get("completionTokenCount")
            or payload.get("outputTokenCount")
            or 0
        )
        total_tokens = int(
            payload.get("total_tokens")
            or payload.get("totalTokenCount")
            or payload.get("total")
            or 0
        )
        if input_tokens <= 0:
            input_tokens = cls.estimate_text_tokens(prompt)
        if output_tokens <= 0:
            output_tokens = cls.estimate_text_tokens(completion_text)
        if total_tokens <= 0:
            total_tokens = input_tokens + output_tokens
        return TokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=total_tokens,
        )


class DeepSeekClient(BaseAIClient):
    provider_name = "deepseek"

    async def chat_json(self, *, model: str, prompt: str) -> AIProviderResult:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a structured analysis assistant. Return valid JSON only.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.3,
            "response_format": {"type": "json_object"},
        }
        data = await self._post_json(
            path="/chat/completions",
            payload=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        content = data["choices"][0]["message"]["content"]
        return AIProviderResult(
            data=self.extract_json_object(content),
            usage=self.normalize_usage(data.get("usage"), prompt=prompt, completion_text=content),
            raw_response=data,
        )


class GLMClient(BaseAIClient):
    provider_name = "glm"

    async def chat_json(self, *, model: str, prompt: str) -> AIProviderResult:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": "You generate original short-video scripts. Return valid JSON only.",
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": 0.7,
        }
        data = await self._post_json(
            path="/chat/completions",
            payload=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        content = data["choices"][0]["message"]["content"]
        return AIProviderResult(
            data=self.extract_json_object(content),
            usage=self.normalize_usage(data.get("usage"), prompt=prompt, completion_text=content),
            raw_response=data,
        )


class SeedanceClient(BaseAIClient):
    provider_name = "seedance"

    async def create_video(self, *, model: str, prompt: str, duration: int) -> AIProviderResult:
        payload = {
            "model": model,
            "prompt": prompt,
            "duration": duration,
        }
        data = await self._post_json(
            path="/videos/generations",
            payload=payload,
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        completion_text = json.dumps(data, ensure_ascii=False)
        return AIProviderResult(
            data=data,
            usage=self.normalize_usage(data.get("usage"), prompt=prompt, completion_text=completion_text),
            raw_response=data,
        )
