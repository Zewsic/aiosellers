from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..schemas.enums import ItemDealStatuses

if TYPE_CHECKING:  # pragma: no cover
    from ..playerok import Playerok
    from .chat import Chat
    from .item import Item
    from .user import User


@dataclass(slots=True)
class Deal:
    id: str
    status: ItemDealStatuses | None = None
    user_id: str | None = None
    chat_id: str | None = None
    item_id: str | None = None

    _client: Playerok | None = field(default=None, repr=False, init=False, compare=False)

    def _require_client(self) -> Playerok:
        if self._client is None:
            raise RuntimeError(
                f"{self.__class__.__name__} is not attached to a client. "
                f"Use client.deals.get() to fetch an active instance."
            )
        return self._client

    async def confirm(self) -> Deal:
        """Confirm DONE work (for buyer)"""
        return await self._require_client().deals.confirm(self.id)

    async def cancel(self) -> Deal:
        """Reject PAID work and refund money (for seller)"""
        return await self._require_client().deals.cancel(self.id)

    async def complete(self) -> Deal:
        """Mark SENT work as COMPLETED, ask for confirmation (for seller)"""
        return await self._require_client().deals.complete(self.id)

    async def get_chat(self) -> Chat | None:
        if not self.chat_id:
            return None
        return await self._require_client().chats.get(self.chat_id)

    async def get_user(self) -> User | None:
        if not self.user_id:
            return None
        return await self._require_client().account.get_user(self.user_id)

    async def get_item(self) -> Item | None:
        if not self.item_id:
            return None
        return await self._require_client().items.get(id=self.item_id)

    async def refresh(self) -> Deal:
        return await self._require_client().deals.get(self.id, force_refresh=True)

    async def report_problem(self, description: str, problem_type_id: str) -> Deal:
        return await self._require_client().deals.report_problem(
            self.id, description, problem_type_id
        )
