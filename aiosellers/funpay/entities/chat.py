from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from ..schemas import MessageTypes
from .user import _detached

if TYPE_CHECKING:
    from ..funpay import FunPay
    from .user import User


@dataclass(slots=True)
class Message:
    id: int
    text: str | None
    chat_id: int | str
    chat_name: str | None = None
    author: str | None = None
    author_id: int = 0
    interlocutor_id: int | None = None
    image_link: str | None = None
    image_name: str | None = None
    type: MessageTypes = MessageTypes.NON_SYSTEM
    by_bot: bool = False
    badge: str | None = None
    is_support: bool = False
    is_moderation: bool = False
    is_arbitration: bool = False
    is_auto_reply: bool = False
    html: str = ""
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.chats.get()")
        return self._client

    async def answer(self, text: str) -> Message:
        return await self._require_client().chats.send_message(self.chat_id, text=text)


@dataclass(slots=True)
class Chat:
    id: int
    name: str = ""
    last_message_text: str = ""
    node_message_id: int = 0
    user_message_id: int = 0
    unread: bool = False
    last_by_bot: bool = False
    html: str = ""
    interlocutor_id: int | None = None
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.chats.get()")
        return self._client

    async def send_text(self, text: str) -> Message:
        return await self._require_client().chats.send_message(self.id, text=text)

    async def send_photo(self, image: str | Path | bytes) -> Message:
        return await self._require_client().chats.send_message(self.id, image=image)

    async def get_messages(self, limit: int = 50) -> list[Message]:
        return await self._require_client().chats.messages.list(self.id, limit=limit)

    async def mute(self) -> None:
        await self._require_client().chats.mute(self.id, muted=True)

    async def unmute(self) -> None:
        await self._require_client().chats.mute(self.id, muted=False)

    async def refresh(self) -> Chat:
        return await self._require_client().chats.get(self.id, force_refresh=True)

    async def get_user(self) -> User | None:
        if not self.interlocutor_id:
            return None
        return await self._require_client().account.get_user(self.interlocutor_id)
