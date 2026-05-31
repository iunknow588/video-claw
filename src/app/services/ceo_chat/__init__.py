from __future__ import annotations

from sqlalchemy.ext.asyncio import AsyncSession

from app.services.cmo import CMOService, PromotionEventCallback


class CEOChatService:
    """Compatibility facade: the legacy CEO chat entry now proxies to the CMO service."""

    def __init__(self, session: AsyncSession):
        self.cmo_service = CMOService(session)

    async def handle_message(
        self,
        message: str,
        *,
        event_callback: PromotionEventCallback | None = None,
    ) -> None:
        await self.cmo_service.handle_user_message(message, event_callback=event_callback)
