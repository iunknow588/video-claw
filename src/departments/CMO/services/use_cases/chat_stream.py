from __future__ import annotations

import asyncio
import json
from collections.abc import AsyncIterator
from typing import Any

from fastapi.encoders import jsonable_encoder
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CMO.services.chat import CMOService


class ChatStreamUseCase:
    """API-facing chat streaming use case owned by CMO."""

    def __init__(self, session: AsyncSession):
        self.session = session
        self.service = CMOService(session)

    async def stream_user_message(self, message: str) -> AsyncIterator[str]:
        event_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        async def publish(event: dict[str, Any]) -> None:
            await event_queue.put(event)

        async def produce() -> None:
            try:
                await self.service.handle_user_message(message, event_callback=publish)
            except Exception as exc:
                await self.session.rollback()
                await event_queue.put(
                    {
                        "type": "error",
                        "message": f"CMO channel error: {exc}",
                    }
                )
            finally:
                await event_queue.put(None)

        producer = asyncio.create_task(produce())
        try:
            while True:
                event = await event_queue.get()
                if event is None:
                    break
                yield json.dumps(jsonable_encoder(event), ensure_ascii=False) + "\n"
        finally:
            await producer
            await self.session.commit()
