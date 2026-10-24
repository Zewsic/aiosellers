from __future__ import annotations

import json
from typing import Literal

from bs4 import BeautifulSoup

from ..core.constants import BOT_MARK
from ..exceptions import ImageUploadError, MessageNotDeliveredError, RequestFailedError
from ..parsers.chats import parse_history
from ..transport.tls import response_json, response_text
from .base import RawBase


def _error_message(response) -> str | None:
    try:
        body = response_json(response)
    except Exception:
        return None
    if isinstance(body, dict):
        msg = body.get("msg") or body.get("error")
        return str(msg) if msg else None
    return None


class RawChats(RawBase):
    async def history(self, chat_id: int | str, last_message_id: int, *, retry: bool = True):
        async def run():
            response = await self.transport.request(
                "GET",
                f"chat/history?node={chat_id}&last_message={last_message_id}",
                headers={"x-requested-with": "XMLHttpRequest"},
            )
            data = response_json(response)
            chat = data.get("chat") or {}
            messages = chat.get("messages") or []
            if not messages:
                return []
            node = chat.get("node") or {}
            name = str(node.get("name") or "")
            interlocutor = None
            if name.startswith("users-"):
                ids = [int(part) for part in name.split("-")[1:] if part.isdigit()]
                me = self.transport.account_id
                others = [item for item in ids if item != me]
                interlocutor = others[0] if others else None
            return parse_history(
                messages,
                chat_id,
                self_id=self.transport.account_id or 0,
                self_username=self.transport.username,
                interlocutor_id=interlocutor,
                interlocutor_name=None,
            )

        return await self._call(run, retry=retry)

    async def page(self, chat_id: int | str, *, retry: bool = True) -> str:
        async def run():
            response = await self.transport.request("GET", f"chat/?node={chat_id}")
            html = response_text(response)
            soup = BeautifulSoup(html, "lxml")
            header = soup.find("h1")
            header_text = header.get_text(strip=True) if header is not None else ""
            if header_text in {"Чат", "Chat"} and soup.select_one("a.contact-item") is None:
                raise RequestFailedError("chat not found", body=html)
            return html

        return await self._call(run, retry=retry)

    async def send(
        self,
        chat_id: int | str,
        text: str | None,
        image_id: int | None,
        leave_as_unread: bool,
    ):
        del leave_as_unread
        request = {
            "action": "chat_message",
            "data": {"node": chat_id, "last_message": -1, "content": text or ""},
        }
        if image_id is not None:
            request["data"]["content"] = ""
            request["data"]["image_id"] = image_id
        elif text:
            request["data"]["content"] = f"{BOT_MARK}{text}"

        async def run():
            before = await self._node_message_id(chat_id)
            payload = await self.transport.request(
                "POST",
                "runner/",
                data={
                    "objects": json.dumps([]),
                    "request": json.dumps(request),
                },
                headers={"content-type": "application/x-www-form-urlencoded; charset=UTF-8"},
            )
            data = response_json(payload)
            try:
                return self._sent_message(data, chat_id)
            except MessageNotDeliveredError:
                resp = data.get("response") if isinstance(data, dict) else None
                if not isinstance(resp, dict) or resp.get("error"):
                    raise
                found = await self._message_after(chat_id, before)
                if found is None:
                    raise
                return found

        return await self._call(run)

    async def _node_message_id(self, chat_id: int | str) -> int | None:
        account_id = self.transport.account_id
        if not account_id:
            return None
        from ..core.utils import random_tag
        from ..parsers.chats import parse_bookmarks
        from .account import RawAccount

        payload = await RawAccount(self.transport).runner_poll(
            [{"type": "chat_bookmarks", "id": account_id, "tag": random_tag(), "data": False}]
        )
        html = ""
        for obj in payload.get("objects") or []:
            if obj.get("type") != "chat_bookmarks":
                continue
            data = obj.get("data")
            html = data.get("html") if isinstance(data, dict) else (data or "")
            break
        if not isinstance(html, str):
            return None
        wanted = int(chat_id)
        for shortcut in parse_bookmarks(html, self_id=account_id):
            if shortcut.id == wanted:
                return shortcut.node_message_id
        return None

    async def _message_after(self, chat_id: int | str, before: int | None):
        if before is None:
            return None
        node = await self._node_message_id(chat_id)
        if node is None or node <= before:
            return None
        history = await self.history(chat_id, node + 1, retry=False)
        self_id = self.transport.account_id or 0
        own = [item for item in history if item.id > before and item.author_id == self_id]
        if not own:
            return None
        return max(own, key=lambda item: item.id)

    def _sent_message(self, payload: dict, chat_id: int | str):
        resp = payload.get("response") if isinstance(payload, dict) else None
        body = json.dumps(payload) if isinstance(payload, dict) else ""
        if not isinstance(resp, dict):
            raise MessageNotDeliveredError(None, chat_id, body=body)
        if resp.get("error"):
            raise MessageNotDeliveredError(str(resp.get("error")), chat_id, body=body)
        for obj in payload.get("objects") or []:
            if obj.get("type") != "chat_node":
                continue
            data = obj.get("data") or {}
            node = data.get("node") or {}
            idents = {node.get("id"), node.get("name"), obj.get("id")}
            if chat_id not in idents and str(chat_id) not in {str(item) for item in idents}:
                continue
            parsed = parse_history(
                data.get("messages") or [],
                chat_id,
                self_id=self.transport.account_id or 0,
                self_username=self.transport.username,
                interlocutor_id=None,
                interlocutor_name=None,
            )
            if parsed:
                return max(parsed, key=lambda item: item.id)
        raise MessageNotDeliveredError(None, chat_id, body=body)

    async def upload(
        self,
        kind: Literal["chat", "offer"],
        content: bytes,
        filename: str,
        content_type: str,
    ) -> int:
        path = "file/addChatImage" if kind == "chat" else "file/addOfferImage"

        async def run():
            response = await self.transport.upload(path, filename, content, content_type)
            status = getattr(response, "status_code", None)
            text = response_text(response)
            if status == 400:
                raise ImageUploadError(_error_message(response), status_code=400, body=text)
            try:
                data = response_json(response)
            except Exception as exc:
                raise ImageUploadError(
                    _error_message(response), status_code=status, body=text
                ) from exc
            if not isinstance(data, dict) or "fileId" not in data:
                raise ImageUploadError(_error_message(response), status_code=status, body=text)
            return int(data["fileId"])

        return await self._call(run)

    async def mute(self, node_id: int | str, mute: bool) -> None:
        async def run():
            response = await self.transport.request(
                "POST",
                "chat/mute",
                data={"node_id": node_id, "mute": "1" if mute else "0"},
            )
            body = response_json(response)
            if isinstance(body, dict) and body.get("error"):
                raise RequestFailedError(
                    str(body.get("msg") or body.get("error")),
                    status_code=getattr(response, "status_code", None),
                    body=response_text(response),
                )

        await self._call(run)
