from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from app.CIO.db.session import get_db
from app.CIO.schemas.video import CEOChatRequest
from app.CMO.services.use_cases.chat_stream import ChatStreamUseCase

router = APIRouter()


@router.post("/chat")
async def chat_with_cmo(
    data: CEOChatRequest,
    db: AsyncSession = Depends(get_db),
):
    """Stream CMO events for the external communication channel."""
    return StreamingResponse(
        ChatStreamUseCase(db).stream_user_message(data.message),
        media_type="application/x-ndjson",
    )
