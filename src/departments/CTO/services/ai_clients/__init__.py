"""
AI provider client skeletons.
"""

from __future__ import annotations

import asyncio
import base64
from datetime import datetime, timezone
import hashlib
import hmac
import json
from email.utils import format_datetime
from dataclasses import dataclass
from typing import Any, Dict, Literal, Optional
from urllib.parse import urlencode, urlparse

import httpx

from departments.CEO.core.config import settings
from departments.CEO.core.logging import get_logger
from departments.CIO.config.schema import (
    AIProviderProfile,
    AIProvidersConfig,
    AIRuntimeConfig,
    HiDreamProviderConfig,
)

logger = get_logger(__name__)


class AIProviderError(RuntimeError):
    """Raised when an upstream AI provider call fails."""


ProviderName = Literal["deepseek", "glm", "xfyun_maas", "seedance"]


@dataclass(slots=True)
class HiDreamConfig:
    app_id: str
    api_key: str
    api_secret: str
    create_url: str
    query_url: str
    default_resolution: str
    default_aspect_ratio: str

    @property
    def is_configured(self) -> bool:
        return bool(
            self.app_id
            and self.api_key
            and self.api_secret
            and self.create_url
            and self.query_url
        )


@dataclass(slots=True)
class AIProviderConfig:
    provider: ProviderName
    api_key: str
    base_url: str
    model: str
    resource_id: str = ""

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url)

@dataclass(slots=True)
class AIRuntimePolicy:
    http_timeout: float
    max_retries: int
    use_placeholder_when_unconfigured: bool


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

    def add(self, other: "TokenUsage") -> "TokenUsage":
        return TokenUsage(
            input_tokens=int(self.input_tokens or 0) + int(other.input_tokens or 0),
            output_tokens=int(self.output_tokens or 0) + int(other.output_tokens or 0),
            total_tokens=int(self.total_tokens or 0) + int(other.total_tokens or 0),
        )


@dataclass(slots=True)
class AIProviderResult:
    data: Dict[str, Any]
    usage: TokenUsage
    raw_response: Dict[str, Any]


def get_ai_runtime_policy() -> AIRuntimePolicy:
    runtime: AIRuntimeConfig = settings.ai_providers.runtime
    return AIRuntimePolicy(
        http_timeout=float(runtime.http_timeout),
        max_retries=int(runtime.max_retries),
        use_placeholder_when_unconfigured=bool(runtime.use_placeholder_when_unconfigured),
    )


def get_ai_provider_config(provider: ProviderName) -> AIProviderConfig:
    ai_providers: AIProvidersConfig = settings.ai_providers
    provider_profiles: dict[ProviderName, AIProviderProfile] = {
        "deepseek": ai_providers.deepseek,
        "glm": ai_providers.glm,
        "xfyun_maas": ai_providers.xfyun_maas,
        "seedance": ai_providers.seedance,
    }
    profile = provider_profiles[provider]
    return AIProviderConfig(
        provider=provider,
        api_key=str(profile.api_key or ""),
        base_url=str(profile.base_url or ""),
        model=str(profile.model or ""),
        resource_id=str(profile.resource_id or ""),
    )


def get_hidream_config() -> HiDreamConfig:
    ai_providers: AIProvidersConfig = settings.ai_providers
    profile: HiDreamProviderConfig = ai_providers.hidream
    return HiDreamConfig(
        app_id=str(profile.app_id or ""),
        api_key=str(profile.api_key or ""),
        api_secret=str(profile.api_secret or ""),
        create_url=str(profile.create_url or ""),
        query_url=str(profile.query_url or ""),
        default_resolution=str(profile.default_resolution or "2k"),
        default_aspect_ratio=str(profile.default_aspect_ratio or "9:16"),
    )


def should_use_placeholder(config: AIProviderConfig) -> bool:
    return bool(get_ai_runtime_policy().use_placeholder_when_unconfigured and not config.is_configured)


def should_use_hidream_placeholder(config: HiDreamConfig) -> bool:
    return bool(get_ai_runtime_policy().use_placeholder_when_unconfigured and not config.is_configured)


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
        policy = get_ai_runtime_policy()
        self.timeout = timeout if timeout is not None else policy.http_timeout
        self.max_retries = max_retries if max_retries is not None else policy.max_retries

    @property
    def is_configured(self) -> bool:
        return bool(self.api_key and self.base_url)

    @staticmethod
    def _format_http_error(exc: Exception | None) -> str:
        if exc is None:
            return "unknown error"
        if isinstance(exc, httpx.HTTPStatusError):
            response = exc.response
            body = (response.text or "").strip()
            if len(body) > 500:
                body = f"{body[:500]}..."
            if body:
                return f"{exc} | body={body}"
        return str(exc)

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
                    error=self._format_http_error(exc),
                )

        raise AIProviderError(
            f"{self.provider_name} request failed after {self.max_retries + 1} attempt(s): {self._format_http_error(last_error)}"
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


class XFYunMaaSClient(BaseAIClient):
    provider_name = "xfyun_maas"

    def __init__(
        self,
        *,
        api_key: str,
        base_url: str,
        resource_id: str = "",
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        super().__init__(
            api_key=api_key,
            base_url=base_url,
            timeout=timeout,
            max_retries=max_retries,
        )
        self.resource_id = str(resource_id or "").strip()

    async def chat_json(
        self,
        *,
        model: str,
        prompt: str,
        system_prompt: str,
        temperature: float = 0.3,
    ) -> AIProviderResult:
        payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": system_prompt,
                },
                {
                    "role": "user",
                    "content": prompt,
                },
            ],
            "temperature": temperature,
            "search_disable": True,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.resource_id and self.resource_id != "0":
            headers["lora_id"] = self.resource_id
        data = await self._post_json(
            path="/chat/completions",
            payload=payload,
            headers=headers,
        )
        content = data["choices"][0]["message"]["content"]
        primary_usage = self.normalize_usage(data.get("usage"), prompt=prompt, completion_text=content)
        try:
            parsed = self.extract_json_object(content)
            usage = primary_usage
            raw_response: Dict[str, Any] = data
        except json.JSONDecodeError:
            repaired = await self._repair_json_content(model=model, malformed_content=content)
            repaired_content = repaired["choices"][0]["message"]["content"]
            repaired_usage = self.normalize_usage(
                repaired.get("usage"),
                prompt=content,
                completion_text=repaired_content,
            )
            parsed = self.extract_json_object(repaired_content)
            usage = primary_usage.add(repaired_usage)
            raw_response = {"primary": data, "repair": repaired}
        return AIProviderResult(
            data=parsed,
            usage=usage,
            raw_response=raw_response,
        )

    async def _repair_json_content(self, *, model: str, malformed_content: str) -> Dict[str, Any]:
        repair_payload = {
            "model": model,
            "messages": [
                {
                    "role": "system",
                    "content": (
                        "You repair malformed JSON. Return one valid JSON object only. "
                        "Do not add explanations. Preserve the original meaning."
                    ),
                },
                {
                    "role": "user",
                    "content": malformed_content,
                },
            ],
            "temperature": 0.0,
            "search_disable": True,
        }
        repair_headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        if self.resource_id and self.resource_id != "0":
            repair_headers["lora_id"] = self.resource_id
        return await self._post_json(
            path="/chat/completions",
            payload=repair_payload,
            headers=repair_headers,
        )


class HiDreamClient:
    provider_name = "hidream"

    def __init__(
        self,
        *,
        app_id: str,
        api_key: str,
        api_secret: str,
        create_url: str,
        query_url: str,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ) -> None:
        self.app_id = app_id
        self.api_key = api_key
        self.api_secret = api_secret
        self.create_url = create_url
        self.query_url = query_url
        policy = get_ai_runtime_policy()
        self.timeout = timeout if timeout is not None else policy.http_timeout
        self.max_retries = max_retries if max_retries is not None else policy.max_retries

    @property
    def is_configured(self) -> bool:
        return bool(self.app_id and self.api_key and self.api_secret and self.create_url and self.query_url)

    async def create_image_task(self, *, payload: Dict[str, Any]) -> Dict[str, Any]:
        return await self._post_signed_json(url=self.create_url, payload=payload)

    async def query_image_task(self, *, task_id: str) -> Dict[str, Any]:
        return await self._post_signed_json(
            url=self.query_url,
            payload={"header": {"app_id": self.app_id, "task_id": task_id}},
        )

    async def _post_signed_json(self, *, url: str, payload: Dict[str, Any]) -> Dict[str, Any]:
        signed_url = self._build_signed_url(url)
        last_error: Optional[Exception] = None
        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.post(signed_url, json=payload)
                    response.raise_for_status()
                    return response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "AI provider request failed",
                    provider=self.provider_name,
                    url=url,
                    attempt=attempt + 1,
                    error=self._format_http_error(exc),
                )
        raise AIProviderError(
            f"{self.provider_name} request failed after {self.max_retries + 1} attempt(s): {self._format_http_error(last_error)}"
        )

    async def _get_json(
        self,
        *,
        path: str,
        headers: Optional[Dict[str, str]] = None,
    ) -> Dict[str, Any]:
        url = f"{self.base_url}/{path.lstrip('/')}"
        last_error: Optional[Exception] = None

        for attempt in range(self.max_retries + 1):
            try:
                async with httpx.AsyncClient(timeout=self.timeout) as client:
                    response = await client.get(url, headers=headers)
                    response.raise_for_status()
                    return response.json()
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                logger.warning(
                    "AI provider request failed",
                    provider=self.provider_name,
                    url=url,
                    attempt=attempt + 1,
                    error=self._format_http_error(exc),
                )

        raise AIProviderError(
            f"{self.provider_name} request failed after {self.max_retries + 1} attempt(s): {self._format_http_error(last_error)}"
        )

    def _build_signed_url(self, raw_url: str) -> str:
        parsed = urlparse(raw_url)
        host = parsed.netloc
        path = parsed.path or "/"
        date = format_datetime(datetime.now(timezone.utc), usegmt=True)
        signature_origin = "\n".join(
            [
                f"host: {host}",
                f"date: {date}",
                f"POST {path} HTTP/1.1",
            ]
        )
        digest = hmac.new(
            self.api_secret.encode("utf-8"),
            signature_origin.encode("utf-8"),
            hashlib.sha256,
        ).digest()
        signature = base64.b64encode(digest).decode("utf-8")
        authorization_origin = (
            f'api_key="{self.api_key}", algorithm="hmac-sha256", '
            f'headers="host date request-line", signature="{signature}"'
        )
        authorization = base64.b64encode(authorization_origin.encode("utf-8")).decode("utf-8")
        query = urlencode(
            {
                "host": host,
                "date": date,
                "authorization": authorization,
            }
        )
        return f"{parsed.scheme}://{host}{path}?{query}"


class SeedanceClient(BaseAIClient):
    provider_name = "seedance"

    async def create_video(
        self,
        *,
        model: str,
        prompt: str,
        duration: int,
        ratio: str = "9:16",
    ) -> AIProviderResult:
        payload = {
            "model": model,
            "content": [
                {
                    "type": "text",
                    "text": prompt,
                }
            ],
            "duration": duration,
            "ratio": ratio,
            "watermark": False,
            "generate_audio": False,
        }
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }
        create_result = await self._post_json(
            path="/contents/generations/tasks",
            payload=payload,
            headers=headers,
        )
        task_id = self._extract_task_id(create_result)
        final_result = await self._poll_video_task(task_id=task_id, headers=headers)
        completion_text = json.dumps(final_result, ensure_ascii=False)
        return AIProviderResult(
            data=final_result,
            usage=self.normalize_usage(final_result.get("usage"), prompt=prompt, completion_text=completion_text),
            raw_response={"create": create_result, "final": final_result},
        )

    async def _poll_video_task(self, *, task_id: str, headers: Dict[str, str]) -> Dict[str, Any]:
        last_result: Dict[str, Any] | None = None
        for _ in range(30):
            result = await self._get_json(
                path=f"/contents/generations/tasks/{task_id}",
                headers=headers,
            )
            last_result = result
            status = str(
                result.get("status")
                or ((result.get("data") or {}).get("status"))
                or ((result.get("task") or {}).get("status"))
                or ""
            ).lower()
            if status in {"succeeded", "success", "completed", "done"}:
                return result
            if status in {"failed", "error", "canceled", "cancelled"}:
                raise AIProviderError(f"Seedance task failed: {result}")
            await asyncio.sleep(3)
        raise AIProviderError(f"Seedance task polling timed out: {last_result}")

    @staticmethod
    def _extract_task_id(payload: Dict[str, Any]) -> str:
        task_id = (
            payload.get("id")
            or payload.get("task_id")
            or ((payload.get("data") or {}).get("id"))
            or ((payload.get("data") or {}).get("task_id"))
        )
        if not task_id:
            raise AIProviderError(f"Seedance task creation response missing task id: {payload}")
        return str(task_id)


def build_deepseek_client(config: AIProviderConfig | None = None) -> DeepSeekClient:
    provider = config or get_ai_provider_config("deepseek")
    policy = get_ai_runtime_policy()
    return DeepSeekClient(
        api_key=provider.api_key,
        base_url=provider.base_url,
        timeout=policy.http_timeout,
        max_retries=policy.max_retries,
    )


def build_glm_client(config: AIProviderConfig | None = None) -> GLMClient:
    provider = config or get_ai_provider_config("glm")
    policy = get_ai_runtime_policy()
    return GLMClient(
        api_key=provider.api_key,
        base_url=provider.base_url,
        timeout=policy.http_timeout,
        max_retries=policy.max_retries,
    )


def build_xfyun_maas_client(config: AIProviderConfig | None = None) -> XFYunMaaSClient:
    provider = config or get_ai_provider_config("xfyun_maas")
    policy = get_ai_runtime_policy()
    return XFYunMaaSClient(
        api_key=provider.api_key,
        base_url=provider.base_url,
        resource_id=provider.resource_id,
        timeout=policy.http_timeout,
        max_retries=policy.max_retries,
    )


def build_hidream_client(config: HiDreamConfig | None = None) -> HiDreamClient:
    provider = config or get_hidream_config()
    policy = get_ai_runtime_policy()
    return HiDreamClient(
        app_id=provider.app_id,
        api_key=provider.api_key,
        api_secret=provider.api_secret,
        create_url=provider.create_url,
        query_url=provider.query_url,
        timeout=policy.http_timeout,
        max_retries=policy.max_retries,
    )


def build_seedance_client(config: AIProviderConfig | None = None) -> SeedanceClient:
    provider = config or get_ai_provider_config("seedance")
    policy = get_ai_runtime_policy()
    return SeedanceClient(
        api_key=provider.api_key,
        base_url=provider.base_url,
        timeout=policy.http_timeout,
        max_retries=policy.max_retries,
    )
