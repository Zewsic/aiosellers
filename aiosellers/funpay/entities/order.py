from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..schemas import Currency, OrderSide, OrderStatuses
from .chat import Message
from .review import Review
from .user import _detached

if TYPE_CHECKING:
    from ..funpay import FunPay
    from .chat import Chat


@dataclass(slots=True)
class Order:
    id: str
    status: OrderStatuses
    side: OrderSide
    description: str
    price: float
    currency: Currency
    buyer_username: str
    buyer_id: int
    subcategory_name: str | None = None
    chat_id: int | None = None
    amount: int | None = None
    review: Review | None = None
    seller_username: str | None = None
    seller_id: int | None = None
    html: str = ""
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.orders.get()")
        return self._client

    def counterparty(self) -> str:
        if self.side is OrderSide.PURCHASE and self.seller_username:
            return self.seller_username
        return self.buyer_username

    async def refund(self) -> None:
        await self._require_client().orders.refund(self.id)

    async def reply_review(self, text: str) -> None:
        await self._require_client().orders.reply_review(self.id, text)

    async def delete_review(self) -> None:
        await self._require_client().orders.delete_review(self.id)

    async def get_chat(self) -> Chat | None:
        name = self.counterparty()
        if not name:
            return None
        return await self._require_client().chats.get_by_name(name, fetch=True)

    async def refresh(self) -> Order:
        return await self._require_client().orders.get(self.id, force_refresh=True)

    async def send_text(self, text: str) -> Message:
        chat = await self.get_chat()
        if chat is None:
            raise RuntimeError(f"Chat for order {self.id} was not found.")
        return await chat.send_text(text)
