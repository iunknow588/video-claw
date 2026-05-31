from __future__ import annotations

import asyncio
import json
from typing import Any

from fastapi import APIRouter, Depends
from fastapi.encoders import jsonable_encoder
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.session import get_db
from app.schemas.video import CEOChatRequest
from app.services.cmo import CMOService

router = APIRouter()


@router.post("/chat")
async def chat_with_cmo(
    data: CEOChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Stream CMO events for the external communication channel."""

    async def event_stream():
        service = CMOService(db)
        event_queue: asyncio.Queue[dict[str, Any] | None] = asyncio.Queue()

        async def publish(event: dict[str, Any]) -> None:
            await event_queue.put(event)

        async def produce() -> None:
            try:
                await service.handle_user_message(data.message, event_callback=publish)
            except Exception as exc:
                await db.rollback()
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
            await db.commit()

    return StreamingResponse(event_stream(), media_type="application/x-ndjson")
