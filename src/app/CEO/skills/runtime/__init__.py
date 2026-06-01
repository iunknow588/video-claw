from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator, Iterator
import inspect
import json
from dataclasses import dataclass, field
from time import perf_counter
from typing import Any

from fastapi.encoders import jsonable_encoder

from app.CEO.skills.base import BaseSkill


def _canonical_skill_name(instance: Any) -> str:
    return (
        getattr(instance, "skill_name", None)
        or getattr(instance, "name", None)
        or f"{instance.__class__.__module__}.{instance.__class__.__name__}"
    )


def _infer_tags(skill_name: str) -> list[str]:
    parts = skill_name.split(".")
    tags = [part for part in parts if part not in {"lead", "workflow"}]
    return list(dict.fromkeys(tags))


def _default_description(skill_name: str) -> str:
    return f"Managed skill for {skill_name}"


def _list_public_methods(instance: Any) -> list[str]:
    excluded = {"setup", "teardown", "validate_input", "on_error", "canonical_name"}
    priority = {
        "execute": 0,
        "async_execute": 1,
        "execute_stream": 2,
        "run": 3,
        "build_plan": 4,
        "record": 5,
    }
    methods = []
    for method_name in dir(instance):
        if method_name.startswith("_") or method_name in excluded:
            continue
        if not callable(getattr(instance, method_name, None)):
            continue
        methods.append(method_name)
    return sorted(set(methods), key=lambda name: (priority.get(name, 99), name))


def _estimate_tokens(payload: Any) -> int:
    normalized = jsonable_encoder(payload)
    raw = json.dumps(normalized, ensure_ascii=False, separators=(",", ":"))
    if not raw:
        return 0
    return max(1, len(raw) // 4)


@dataclass(slots=True)
class SkillTokenUsage:
    input_tokens: int = 0
    output_tokens: int = 0
    total_tokens: int = 0

    def to_dict(self) -> dict[str, int]:
        return {
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "total_tokens": self.total_tokens,
        }


@dataclass(slots=True)
class SkillDescriptor:
    name: str
    description: str
    parameters_schema: dict[str, Any] = field(default_factory=lambda: {"type": "object"})
    tags: list[str] = field(default_factory=list)
    default_config: dict[str, Any] = field(default_factory=dict)
    retry_policy: dict[str, Any] = field(default_factory=lambda: {"max_retries": 1, "backoff": 0.0})
    dependencies: list[str] = field(default_factory=list)
    required_tokens: list[str] = field(default_factory=list)
    methods: list[str] = field(default_factory=list)
    streamable: bool = False


@dataclass(slots=True)
class SkillInvocationResult:
    descriptor: SkillDescriptor
    raw_output: Any
    output_json: Any
    token_usage: SkillTokenUsage
    retry_count: int
    duration_ms: int
    progress: float
    status_message: str
    stream_events: list[Any] = field(default_factory=list)


def build_descriptor(instance: Any, overrides: dict[str, Any] | None = None) -> SkillDescriptor:
    merged = overrides or {}
    name = merged.get("name") or _canonical_skill_name(instance)
    description = merged.get("description") or getattr(instance, "description", "") or _default_description(name)
    parameters_schema = merged.get("parameters_schema") or getattr(instance, "parameters_schema", None) or {"type": "object"}
    tags = list(merged.get("tags") or getattr(instance, "tags", None) or _infer_tags(name))
    default_config = dict(merged.get("default_config") or getattr(instance, "default_config", None) or {})
    retry_policy = dict(merged.get("retry_policy") or getattr(instance, "retry_policy", None) or {"max_retries": 1, "backoff": 0.0})
    dependencies = list(merged.get("dependencies") or getattr(instance, "dependencies", None) or [])
    required_tokens = list(merged.get("required_tokens") or getattr(instance, "required_tokens", None) or [])
    methods = _list_public_methods(instance)
    return SkillDescriptor(
        name=name,
        description=description,
        parameters_schema=parameters_schema,
        tags=tags,
        default_config=default_config,
        retry_policy=retry_policy,
        dependencies=dependencies,
        required_tokens=required_tokens,
        methods=methods,
        streamable="execute_stream" in methods,
    )


class SkillRuntimeManager:
    """Executes skills through a uniform lifecycle and retry contract."""

    async def invoke(
        self,
        instance: Any,
        input_data: dict[str, Any],
        *,
        descriptor_overrides: dict[str, Any] | None = None,
        method_name: str | None = None,
    ) -> SkillInvocationResult:
        descriptor = build_descriptor(instance, descriptor_overrides)
        resolved_method_name = method_name or self._resolve_method_name(instance)
        if not resolved_method_name:
            raise AttributeError(f"{descriptor.name} does not expose an executable method")

        validate_input = getattr(instance, "validate_input", None)
        is_valid = await self._call_maybe_async(validate_input, input_data) if callable(validate_input) else True
        if is_valid is False:
            raise ValueError(f"Skill input rejected by {descriptor.name}")

        retry_policy = descriptor.retry_policy or {"max_retries": 1, "backoff": 0.0}
        max_retries = max(0, int(retry_policy.get("max_retries", 1)))
        backoff = float(retry_policy.get("backoff", 0.0) or 0.0)

        started = perf_counter()
        last_error: Exception | None = None
        for attempt in range(max_retries + 1):
            try:
                await self._call_maybe_async(getattr(instance, "setup", None))
                raw_output = await self._call_maybe_async(getattr(instance, resolved_method_name), input_data)
                stream_events: list[Any] = []
                if resolved_method_name == "execute_stream":
                    raw_output, stream_events = await self._consume_stream_output(raw_output)
                output_json = jsonable_encoder(raw_output)
                token_usage = self._extract_token_usage(input_data, raw_output, output_json, stream_events=stream_events)
                duration_ms = int((perf_counter() - started) * 1000)
                return SkillInvocationResult(
                    descriptor=descriptor,
                    raw_output=raw_output,
                    output_json=output_json,
                    token_usage=token_usage,
                    retry_count=attempt,
                    duration_ms=duration_ms,
                    progress=float(getattr(instance, "progress", 1.0) or 0.0),
                    status_message=str(getattr(instance, "status_message", "") or ""),
                    stream_events=stream_events,
                )
            except Exception as exc:  # noqa: BLE001
                last_error = exc
                handler = getattr(instance, "on_error", None)
                if callable(handler):
                    maybe_handled = await self._call_maybe_async(handler, exc, input_data)
                    if maybe_handled is not None:
                        output_json = jsonable_encoder(maybe_handled)
                        token_usage = self._extract_token_usage(input_data, maybe_handled, output_json)
                        duration_ms = int((perf_counter() - started) * 1000)
                        return SkillInvocationResult(
                            descriptor=descriptor,
                            raw_output=maybe_handled,
                            output_json=output_json,
                            token_usage=token_usage,
                            retry_count=attempt,
                            duration_ms=duration_ms,
                            progress=float(getattr(instance, "progress", 0.0) or 0.0),
                            status_message=str(getattr(instance, "status_message", "") or ""),
                        )
                if attempt >= max_retries:
                    raise
                if backoff > 0:
                    await asyncio.sleep(backoff * (attempt + 1))
            finally:
                await self._call_maybe_async(getattr(instance, "teardown", None))

        raise RuntimeError(f"{descriptor.name} failed without a terminal error") from last_error

    def _resolve_method_name(self, instance: Any) -> str | None:
        for candidate in ("async_execute", "execute", "execute_stream", "run", "build_plan", "record"):
            if callable(getattr(instance, candidate, None)):
                return candidate
        return None

    async def _call_maybe_async(self, func: Any, *args: Any) -> Any:
        if not callable(func):
            return None
        result = func(*args)
        if inspect.isawaitable(result):
            return await result
        return result

    def _extract_token_usage(
        self,
        input_data: dict[str, Any],
        raw_output: Any,
        output_json: Any,
        *,
        stream_events: list[Any] | None = None,
    ) -> SkillTokenUsage:
        explicit_usage = self._resolve_explicit_usage(raw_output)
        if explicit_usage is None and stream_events:
            for event in reversed(stream_events):
                explicit_usage = self._resolve_explicit_usage(event)
                if explicit_usage is not None:
                    break
                if isinstance(event, dict):
                    explicit_usage = self._resolve_explicit_usage(event.get("data"))
                    if explicit_usage is not None:
                        break

        if explicit_usage:
            input_tokens = int(explicit_usage.get("input_tokens", 0) or 0)
            output_tokens = int(explicit_usage.get("output_tokens", 0) or 0)
            total_tokens = int(explicit_usage.get("total_tokens", input_tokens + output_tokens) or 0)
            return SkillTokenUsage(
                input_tokens=input_tokens,
                output_tokens=output_tokens,
                total_tokens=total_tokens,
            )

        input_tokens = _estimate_tokens(input_data)
        output_tokens = _estimate_tokens(output_json)
        return SkillTokenUsage(
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            total_tokens=input_tokens + output_tokens,
        )

    def _resolve_explicit_usage(self, payload: Any) -> dict[str, Any] | None:
        if isinstance(payload, dict):
            return payload.get("token_usage") or payload.get("_token_usage")
        return None

    async def _consume_stream_output(self, raw_output: Any) -> tuple[Any, list[Any]]:
        if inspect.isasyncgen(raw_output) or isinstance(raw_output, AsyncIterator):
            events = [event async for event in raw_output]
            return self._finalize_stream_events(events), events
        if isinstance(raw_output, Iterator):
            events = list(raw_output)
            return self._finalize_stream_events(events), events
        return raw_output, []

    def _finalize_stream_events(self, events: list[Any]) -> Any:
        final_payload = None
        for event in events:
            if not isinstance(event, dict):
                continue
            if event.get("type") in {"result", "final"}:
                if "data" in event:
                    final_payload = event["data"]
                elif "result" in event:
                    final_payload = event["result"]
            elif "token_usage" in event and final_payload is None:
                final_payload = {"token_usage": event["token_usage"]}
        if final_payload is not None:
            return final_payload
        return {"events": events}
