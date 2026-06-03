from __future__ import annotations

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from sqlalchemy.ext.asyncio import AsyncSession

from departments.CIO.db.session import get_db
from departments.CIO.schemas.video import ChatMessageRequest
from departments.CMO.services.use_cases.chat_stream import ChatStreamUseCase

router = APIRouter()


@router.post("/chat")
async def chat_with_cmo(
    data: ChatMessageRequest,
    db: AsyncSession = Depends(get_db),
):
    return StreamingResponse(
        ChatStreamUseCase(db).stream_user_message(
            data.message,
            workflow_params=data.workflow_params.model_dump(exclude_none=True) if data.workflow_params else None,
        ),
        media_type="application/x-ndjson",
    )
