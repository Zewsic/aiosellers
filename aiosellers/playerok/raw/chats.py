from __future__ import annotations

import uuid

from ..core.types import ImageInput
from ..core.utils import _dig, _raise_on_gql_errors, prepare_image_file
from ..graphql import GraphQLQuery as GQL
from ..schemas import (
    Chat,
    ChatList,
    ChatMessage,
    ChatMessageList,
    ChatStatuses,
    ChatTypes,
    MessageTemplateList,
    MessageTemplateTypes,
    TemporaryAttachment,
)
from ..transport import PlayerokTransport


class RawChatService:
    def __init__(self, transport: PlayerokTransport):
        self._transport = transport

    async def get_chats(
        self,
        user_id: str | None = None,
        count: int = 24,
        type: ChatTypes | None = None,
        status: ChatStatuses | None = None,
        cursor: str | None = None,
    ) -> ChatList | None:
        response = await self._transport.request(
            "post",
            "graphql",
            GQL.get_chats(user_id=user_id, count=count, type=type, status=status, cursor=cursor),
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "chats"))
        if data is None:
            return None
        return ChatList(**data)

    async def get_chat(self, chat_id: str) -> Chat | None:
        response = await self._transport.request("post", "graphql", GQL.get_chat(chat_id=chat_id))
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "chat"))
        if data is None:
            return None
        return Chat(**data)

    async def mark_chat_as_read(self, chat_id: str) -> Chat | None:
        response = await self._transport.request(
            "post", "graphql", GQL.mark_chat_as_read(chat_id=chat_id)
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "markChatAsRead"))
        if data is None:
            return None
        return Chat(**data)

    async def get_chat_messages(
        self, chat_id: str, count: int = 24, after_cursor: str | None = None
    ) -> ChatMessageList | None:
        response = await self._transport.request(
            "post",
            "graphql",
            GQL.get_chat_messages(chat_id=chat_id, count=count, after_cursor=after_cursor),
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "chatMessages"))
        if data is None:
            return None
        return ChatMessageList(**data)

    async def send_message(
        self,
        chat_id: str,
        text: str | None = None,
        photo: ImageInput | None = None,
        mark_as_read: bool = False,
    ) -> ChatMessage | None:
        if not text and not photo:
            raise ValueError("Either 'text' or 'photo' must be provided.")

        if mark_as_read:
            await self.mark_chat_as_read(chat_id=chat_id)
        if text and photo:
            await self.send_message(chat_id=chat_id, photo=photo)
            return await self.send_message(chat_id=chat_id, text=text)  # can't send both at once

        if photo:
            payload = GQL.create_chat_message_with_photo(chat_id=chat_id, text=text)
            file_obj, should_close = await prepare_image_file(photo)
            try:
                files = {"1": file_obj}
                response = await self._transport.request("post", "graphql", payload, files=files)
            finally:
                if should_close:
                    file_obj.close()
        else:
            payload = GQL.create_chat_message(chat_id=chat_id, text=text)
            response = await self._transport.request("post", "graphql", payload)

        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "createChatMessage"))
        if data is None:
            return None
        return ChatMessage(**data)

    async def get_message_templates(
        self,
        template_type: MessageTemplateTypes = MessageTemplateTypes.ACTIVE_DEAL_PROBLEM,
        *,
        count: int = 24,
        after_cursor: str | None = None,
    ) -> MessageTemplateList | None:
        response = await self._transport.request(
            "post",
            "graphql",
            GQL.get_message_templates(template_type, count=count, after_cursor=after_cursor),
        )
        raw = response.json()
        _raise_on_gql_errors(raw)
        data = _dig(raw, ("data", "messageTemplates"))
        if data is None:
            return None
        return MessageTemplateList(**data)

    async def upload_image(self, chat_id: str, image: ImageInput) -> TemporaryAttachment | None:
        payload = GQL.upload_chat_image(chat_id, str(uuid.uuid4()))
        file_obj, should_close = await prepare_image_file(image)
        try:
            response = await self._transport.request(
                "post", "graphql", payload, files={"1": file_obj}
            )
        finally:
            if should_close:
                file_obj.close()
        raw = response.json()
        _raise_on_gql_errors(raw)
        data = _dig(raw, ("data", "uploadChatImageIntoTemporaryStore"))
        if data is None:
            return None
        return TemporaryAttachment(**data)
