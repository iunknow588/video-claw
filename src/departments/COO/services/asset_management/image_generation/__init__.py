from __future__ import annotations

import asyncio
import base64
from datetime import datetime
import json
from pathlib import Path
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CEO.core.logging import get_logger
from departments.CIO.models.image import ImageTask
from departments.CIO.services.storage import get_storage_runtime
from departments.CQO.services.audit import AuditService
from departments.CTO.services.ai_clients import (
    AIProviderError,
    build_hidream_client,
    get_hidream_config,
    should_use_hidream_placeholder,
)

logger = get_logger(__name__)


class ImageGenerationService:
    """COO-owned image asset generation service with HiDream and placeholder modes."""

    _PLACEHOLDER_PNG = base64.b64decode(
        "iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAusB9Wn4nK0AAAAASUVORK5CYII="
    )

    def __init__(self, session: AsyncSession):
        self.session = session
        self.provider = get_hidream_config()
        self.client = build_hidream_client(self.provider)
        self.storage_runtime = get_storage_runtime()
        self.audit_service = AuditService(session)

    async def create_task(
        self,
        *,
        script_id: str | None,
        prompt: str,
        negative_prompt: str,
        aspect_ratio: str,
        resolution: str,
        image_count: int,
        use_case: str,
    ) -> ImageTask:
        task = ImageTask(
            script_id=script_id,
            status="pending",
            provider_name="hidream",
            prompt=prompt,
            negative_prompt=negative_prompt,
            aspect_ratio=aspect_ratio,
            resolution=resolution,
            image_count=image_count,
            request_payload=self._build_provider_payload(
                prompt=prompt,
                negative_prompt=negative_prompt,
                aspect_ratio=aspect_ratio,
                resolution=resolution,
                image_count=image_count,
                use_case=use_case,
            ),
        )
        self.session.add(task)
        await self.session.flush()
        return task

    async def process_task(self, task_id: str) -> ImageTask:
        task = await self.get_task_status(task_id)
        if not task:
            raise ValueError(f"Image task {task_id} not found")

        task.status = "processing"
        await self.session.flush()

        try:
            if should_use_hidream_placeholder(self.provider):
                image_url = await self._save_placeholder_image(task.uuid)
                task.status = "completed"
                task.primary_image_url = image_url
                task.image_urls = [image_url]
                task.result_payload = {"mode": "placeholder", "image_urls": [image_url]}
                task.completed_at = datetime.now().isoformat()
                return task

            create_result = await self.client.create_image_task(payload=dict(task.request_payload or {}))
            task.provider_task_id = self._extract_provider_task_id(create_result)
            query_result = await self._wait_for_result(task.provider_task_id)
            parsed_result = self._decode_result_payload(query_result)
            image_urls = self._collect_image_urls(parsed_result)
            primary_url = await self._materialize_primary_image(task.uuid, parsed_result, image_urls)

            task.status = "completed"
            task.primary_image_url = primary_url or (image_urls[0] if image_urls else None)
            task.image_urls = image_urls or ([primary_url] if primary_url else [])
            task.result_payload = parsed_result
            task.completed_at = datetime.now().isoformat()
            task.api_cost = float(self._extract_api_cost(query_result) or 0.0)
            await self.audit_service.record_cost(
                source_type="image",
                source_uuid=task.uuid,
                provider="hidream",
                model_name="hidream",
                amount=float(task.api_cost or 0.0),
                request_summary=str(task.prompt or "")[:500],
                metadata_json={
                    "script_id": task.script_id,
                    "provider_task_id": task.provider_task_id,
                    "image_count": task.image_count,
                    "image_urls": task.image_urls or [],
                },
            )
        except Exception as exc:  # noqa: BLE001
            task.status = "failed"
            task.error_message = str(exc)
            logger.error("Image generation failed", uuid=task_id, error=str(exc))
        return task

    async def get_task_status(self, task_id: str) -> ImageTask | None:
        result = await self.session.execute(select(ImageTask).where(ImageTask.uuid == task_id))
        return result.scalar_one_or_none()

    def _build_provider_payload(
        self,
        *,
        prompt: str,
        negative_prompt: str,
        aspect_ratio: str,
        resolution: str,
        image_count: int,
        use_case: str,
    ) -> dict[str, Any]:
        return {
            "header": {"app_id": self.provider.app_id},
            "parameter": {
                "hidream": {
                    "resolution": resolution or self.provider.default_resolution,
                    "aspect_ratio": aspect_ratio or self.provider.default_aspect_ratio,
                    "image_count": image_count,
                    "use_case": use_case,
                }
            },
            "payload": {
                "prompt": {"text": prompt},
                "negative_prompt": {"text": negative_prompt},
            },
        }

    def _extract_provider_task_id(self, create_result: dict[str, Any]) -> str:
        header = create_result.get("header") or {}
        task_id = header.get("task_id") or create_result.get("task_id")
        if not task_id:
            raise ValueError("HiDream create response did not include task_id")
        return str(task_id)

    async def _wait_for_result(self, provider_task_id: str) -> dict[str, Any]:
        last_response: dict[str, Any] | None = None
        for _ in range(12):
            response = await self.client.query_image_task(task_id=provider_task_id)
            last_response = response
            header = response.get("header") or {}
            code = int(header.get("code") or 0)
            if code not in {0, 202, 10214}:
                raise AIProviderError(f"HiDream query failed: {response}")
            status = str(
                header.get("task_status")
                or response.get("task_status")
                or ((response.get("payload") or {}).get("status") or "")
            ).lower()
            if status in {"success", "completed", "done", "4"}:
                return response
            if status in {"failed", "error", "5"}:
                raise AIProviderError(f"HiDream task failed: {response}")
            await asyncio.sleep(2)
        return last_response or {}

    def _decode_result_payload(self, payload: dict[str, Any]) -> dict[str, Any]:
        result = dict(payload)
        result_payload = result.get("payload") or {}
        text_node = None
        if isinstance(result_payload, dict):
            text_node = (
                ((result_payload.get("result") or {}).get("text"))
                or ((result_payload.get("output") or {}).get("text"))
                or result_payload.get("text")
            )
        if isinstance(text_node, str) and text_node.strip():
            try:
                decoded = base64.b64decode(text_node).decode("utf-8")
                try:
                    result["decoded_result"] = json.loads(decoded)
                except json.JSONDecodeError:
                    result["decoded_result_text"] = decoded
            except Exception:  # noqa: BLE001
                pass
        return result

    def _collect_image_urls(self, payload: dict[str, Any]) -> list[str]:
        urls: list[str] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for item in value.values():
                    visit(item)
                return
            if isinstance(value, list):
                for item in value:
                    visit(item)
                return
            if isinstance(value, str):
                text = value.strip()
                if text.startswith(("http://", "https://")) and text not in urls:
                    urls.append(text)

        visit(payload.get("decoded_result") or payload)
        return urls

    async def _materialize_primary_image(
        self,
        task_uuid: str,
        payload: dict[str, Any],
        image_urls: list[str],
    ) -> str | None:
        image_bytes = self._extract_inline_image_bytes(payload)
        if image_bytes is not None:
            return await self._save_image_bytes(task_uuid, image_bytes)
        if image_urls:
            try:
                async with httpx.AsyncClient(timeout=30.0) as client:
                    response = await client.get(image_urls[0])
                    response.raise_for_status()
                    return await self._save_image_bytes(task_uuid, response.content)
            except Exception:  # noqa: BLE001
                return image_urls[0]
        return None

    def _extract_inline_image_bytes(self, payload: dict[str, Any]) -> bytes | None:
        candidates: list[str] = []

        def visit(value: Any) -> None:
            if isinstance(value, dict):
                for item in value.values():
                    visit(item)
                return
            if isinstance(value, list):
                for item in value:
                    visit(item)
                return
            if isinstance(value, str) and len(value) > 128 and not value.startswith(("http://", "https://")):
                candidates.append(value)

        visit(payload.get("decoded_result") or payload)
        for item in candidates:
            try:
                return base64.b64decode(item)
            except Exception:  # noqa: BLE001
                continue
        return None

    def _extract_api_cost(self, payload: dict[str, Any]) -> float | None:
        usage = payload.get("usage") or {}
        cost = usage.get("cost") or payload.get("cost")
        if cost is None:
            return None
        return float(cost)

    async def _save_placeholder_image(self, task_uuid: str) -> str:
        return await self._save_image_bytes(task_uuid, self._PLACEHOLDER_PNG)

    async def _save_image_bytes(self, task_uuid: str, content: bytes) -> str:
        image_dir = self.storage_runtime.resolve_path("images")
        image_dir.mkdir(parents=True, exist_ok=True)
        file_path = image_dir / f"{task_uuid}.png"
        file_path.write_bytes(content)
        relative_path = Path("images") / file_path.name
        return self.storage_runtime.build_public_url(str(relative_path))
