from __future__ import annotations

import re
from pathlib import Path
from typing import TYPE_CHECKING, Literal

from ..core.utils import random_tag, sniff_image
from ..entities.chat import Chat, Message
from ..exceptions import AccountNotInitiatedError
from ..parsers.chats import parse_bookmarks
from ..schemas import ChatShortcut, MessageSnapshot

if TYPE_CHECKING:
    from ..funpay import FunPay

_NODE = re.compile(r"users-(\d+)-(\d+)")


def _load_image(image: bytes | str | Path) -> tuple[bytes, str, str]:
    if isinstance(image, bytes):
        return image, "image.png", sniff_image(image)
    path = Path(image)
    content = path.read_bytes()
    return content, path.name, sniff_image(content)


def _interlocutor(html: str, account_id: int | None) -> int | None:
    match = _NODE.search(html)
    if match is None:
        return None
    first, second = int(match.group(1)), int(match.group(2))
    if account_id == first:
        return second
    if account_id == second:
        return first
    return second


class ChatMessagesAPI:
    def __init__(self, client: FunPay) -> None:
        self._client = client

    async def list(
        self,
        chat_id: int | str,
        *,
        last_message_id: int | None = None,
        limit: int = 100,
    ) -> list[Message]:
        last = 9999999999999999999 if last_message_id is None else last_message_id
        snaps = await self._client.chats._require().chats.history(chat_id, last)
        messages = [self._client.chats._message(snap) for snap in snaps if snap.id > 0]
        messages.sort(key=lambda item: item.id)
        if limit:
            return messages[-limit:]
        return messages


class ChatAPI:
    def __init__(self, client: FunPay) -> None:
        self._client = client
        self.messages = ChatMessagesAPI(client)

    def _require(self):
        if self._client._raw is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        return self._client._raw

    def _message(self, snap: MessageSnapshot) -> Message:
        by_bot = snap.by_bot
        listener = self._client._listener
        if listener is not None and listener.was_sent(snap.chat_id, snap.id):
            by_bot = True
        message = Message(
            id=snap.id,
            text=snap.text,
            chat_id=snap.chat_id,
            chat_name=snap.chat_name,
            author=snap.author,
            author_id=snap.author_id,
            interlocutor_id=snap.interlocutor_id,
            image_link=snap.image_link,
            image_name=snap.image_name,
            type=snap.type,
            by_bot=by_bot,
            badge=snap.badge,
            is_support=snap.is_support,
            is_moderation=snap.is_moderation,
            is_arbitration=snap.is_arbitration,
            is_auto_reply=snap.is_auto_reply,
            html=snap.html,
        )
        message._client = self._client
        return message

    def _from_shortcut(self, shortcut: ChatShortcut) -> Chat:
        chat = Chat(
            id=shortcut.id,
            name=shortcut.name,
            last_message_text=shortcut.last_message_text,
            node_message_id=shortcut.node_message_id,
            user_message_id=shortcut.user_message_id,
            unread=shortcut.unread,
            last_by_bot=shortcut.last_by_bot,
            html=shortcut.html,
        )
        return self._client.remember("chats", shortcut.id, chat)

    async def list(self, *, fetch: bool = True) -> list[Chat]:
        if not fetch:
            if not self._client._use_identity_map:
                return []
            return list(self._client._identity_maps.chats._items.values())
        account_id = self._client.account_id
        if account_id is None:
            raise AccountNotInitiatedError("account is not initiated")
        payload = await self._require().account.runner(
            [{"type": "chat_bookmarks", "id": account_id, "tag": random_tag(), "data": False}]
        )
        html = ""
        for obj in payload.get("objects") or []:
            if obj.get("type") != "chat_bookmarks":
                continue
            data = obj.get("data")
            html = data.get("html") if isinstance(data, dict) else (data or "")
            break
        shortcuts = parse_bookmarks(html if isinstance(html, str) else "", self_id=account_id)
        if self._client._use_identity_map:
            self._client._identity_maps.chats.clear()
        return [self._from_shortcut(shortcut) for shortcut in shortcuts]

    async def get(self, chat_id: int, *, force_refresh: bool = False) -> Chat:
        if not force_refresh:
            cached = self._client.cached("chats", chat_id)
            if cached is not None:
                return cached
        html = await self._require().chats.page(chat_id)
        shortcuts = parse_bookmarks(html, self_id=self._client.account_id or 0)
        match = next((item for item in shortcuts if item.id == chat_id), None)
        if match is None:
            match = ChatShortcut(
                id=chat_id,
                name="",
                last_message_text="",
                node_message_id=0,
                user_message_id=0,
                unread=False,
                last_by_bot=False,
                html=html,
            )
        chat = self._from_shortcut(match)
        interlocutor = _interlocutor(html, self._client.account_id)
        if interlocutor is not None:
            chat.interlocutor_id = interlocutor
        return chat

    async def get_by_name(self, name: str, *, fetch: bool = False) -> Chat | None:
        for chat in await self.list(fetch=fetch):
            if chat.name == name:
                return chat
        return None

    async def send_message(
        self,
        chat_id: int | str,
        *,
        text: str | None = None,
        image: bytes | str | Path | int | None = None,
        leave_as_unread: bool = False,
    ) -> Message:
        if text is None and image is None:
            raise ValueError("text or image is required")
        image_id = None
        if isinstance(image, int):
            image_id = image
        elif image is not None:
            image_id = await self.upload_image(image, kind="chat")
        if image_id is not None:
            snap = await self._require().chats.send(chat_id, "", image_id, leave_as_unread)
        else:
            snap = await self._require().chats.send(chat_id, text, None, leave_as_unread)
        message = self._message(snap)
        message.by_bot = True
        listener = self._client._listener
        if listener is not None:
            listener.remember_sent(chat_id, message.id)
        return message

    async def upload_image(
        self,
        image: bytes | str | Path,
        *,
        kind: Literal["chat", "offer"] = "chat",
    ) -> int:
        content, filename, content_type = _load_image(image)
        return await self._require().chats.upload(kind, content, filename, content_type)

    async def mute(self, chat_id: int, *, muted: bool = True) -> None:
        await self._require().chats.mute(chat_id, muted)
