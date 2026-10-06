from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from ..core.types import ImageInput
from ..entities.chat import Chat, ChatMessage
from ..entities.file import File
from ..entities.user import User
from ..schemas import (
    ChatMessageDirection,
    ChatStatuses,
    ChatTypes,
    MessageTemplate,
    MessageTemplateTypes,
    TemporaryAttachment,
)

if TYPE_CHECKING:
    from ..playerok import Playerok


class ChatMessagesAPI:
    def __init__(self, client: Playerok) -> None:
        self._client = client

    def _create_message(self, msg_schema, chat_id: str) -> ChatMessage:
        user = None
        direction = ChatMessageDirection.SYSTEM
        if msg_schema.user:
            # Some fields can be empty. Use *.get_user() to fetch all fields.
            user = User.from_schema(msg_schema.user, self._client)
            if self._client._me_id and msg_schema.user.id == self._client._me_id:
                direction = ChatMessageDirection.OUT
            else:
                direction = ChatMessageDirection.IN

        return ChatMessage(
            id=msg_schema.id,
            sent_at=msg_schema.created_at,
            is_read=msg_schema.is_read,
            text=msg_schema.text,
            file=File.from_schema(msg_schema.file) if msg_schema.file else None,
            user_id=msg_schema.user.id if msg_schema.user else None,
            user=user,
            chat_id=chat_id,
            direction=direction,
        )

    async def list(
        self, chat_id: str, *, limit: int = 50, cursor: str | None = None
    ) -> list[ChatMessage]:
        result = []
        remain = limit
        current_cursor = cursor

        while remain > 0:
            response = await self._client._raw.chats.get_chat_messages(
                chat_id=chat_id, count=min(50, remain), after_cursor=current_cursor
            )
            if response is None or not response.messages:
                break

            for msg in response.messages:
                result.append(self._create_message(msg, chat_id))

            remain -= len(response.messages)

            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor

        return result[:limit]

    async def iter(self, chat_id: str, *, cursor: str | None = None) -> AsyncIterator[ChatMessage]:
        current_cursor = cursor

        while True:
            response = await self._client._raw.chats.get_chat_messages(
                chat_id=chat_id, after_cursor=current_cursor
            )
            if response is None or not response.messages:
                return

            for msg in response.messages:
                yield self._create_message(msg, chat_id)

            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor


class ChatAPI:
    def __init__(self, client: Playerok) -> None:
        self._client = client
        self.messages = ChatMessagesAPI(client)

    def _create_chat(self, schema) -> Chat:
        user_id = None
        user = None
        name = None

        if schema.users:
            me_id = self._client._me_id
            for u in schema.users:
                if me_id and u.id != me_id:
                    user_id = u.id
                    user = User.from_schema(u, self._client)
                    name = u.username
                    break
            if user_id is None:
                u = schema.users[0]
                user_id = u.id
                user = User.from_schema(u, self._client)
                name = u.username

        chat = Chat(
            id=schema.id,
            type=schema.type,
            unread_messages_counter=schema.unread_messages_counter,
            user_id=user_id,
            user=user,
            name=name,
        )

        chat._client = self._client
        return chat

    async def get(self, chat_id: str, *, force_refresh: bool = False) -> Chat | None:
        if not force_refresh and self._client._use_identity_map:
            cached = self._client._identity_maps.chats.get(chat_id)
            if cached:
                return cached

        schema = await self._client._raw.chats.get_chat(chat_id)
        if schema is None:
            return None

        chat = self._create_chat(schema)

        if self._client._use_identity_map:
            self._client._identity_maps.chats.set(chat_id, chat)

        return chat

    async def list(
        self,
        *,
        limit: int = 24,
        cursor: str | None = None,
        type: ChatTypes | None = None,
        status: ChatStatuses | None = None,
        user_id: str | None = None,
        unread_only: bool = False,
    ) -> list[Chat]:
        result = []
        remain = limit
        current_cursor = cursor

        while remain > 0:
            response = await self._client._raw.chats.get_chats(
                user_id=self._client._me_id,
                count=min(24, remain),
                cursor=current_cursor,
                type=type,
                status=status,
            )
            if response is None or not response.chats:
                break

            for schema in response.chats:
                chat = self._create_chat(schema)

                # Filter by user_id if specified
                if user_id is not None and chat.user_id != user_id:
                    continue
                if unread_only and (chat.unread_messages_counter or 0) == 0:
                    continue

                if self._client._use_identity_map:
                    self._client._identity_maps.chats.set(chat.id, chat)

                result.append(chat)
                if len(result) >= limit:
                    break

            if len(result) >= limit:
                break

            remain -= len(response.chats)

            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor

        return result[:limit]

    async def iter(
        self,
        *,
        cursor: str | None = None,
        type: ChatTypes | None = None,
        status: ChatStatuses | None = None,
        user_id: str | None = None,
        unread_only: bool = False,
    ) -> AsyncIterator[Chat]:
        current_cursor = cursor

        while True:
            response = await self._client._raw.chats.get_chats(
                user_id=self._client._me_id,
                cursor=current_cursor,
                type=type,
                status=status,
            )
            if response is None or not response.chats:
                return

            for schema in response.chats:
                chat = self._create_chat(schema)

                # Filter by user_id if specified
                if user_id is not None and chat.user_id != user_id:
                    continue
                if unread_only and (chat.unread_messages_counter or 0) == 0:
                    continue

                if self._client._use_identity_map:
                    self._client._identity_maps.chats.set(chat.id, chat)

                yield chat

            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor

    async def send_message(
        self,
        chat_id: str,
        *,
        text: str | None = None,
        photo: ImageInput | None = None,
        mark_as_read: bool = False,
    ) -> ChatMessage:
        if text is None and photo is None:
            raise ValueError("Either text or photo must be provided")

        msg = await self._client._raw.chats.send_message(
            chat_id=chat_id,
            text=text,
            photo=photo,
            mark_as_read=mark_as_read,
        )

        return self.messages._create_message(msg, chat_id)

    async def mark_as_read(self, chat_id: str) -> None:
        await self._client._raw.chats.mark_chat_as_read(chat_id)

    async def message_templates(
        self,
        template_type: MessageTemplateTypes = MessageTemplateTypes.ACTIVE_DEAL_PROBLEM,
        *,
        limit: int = 24,
        cursor: str | None = None,
    ) -> list[MessageTemplate]:
        result: list[MessageTemplate] = []
        remain = limit
        current_cursor = cursor
        while remain > 0:
            response = await self._client._raw.chats.get_message_templates(
                template_type, count=min(24, remain), after_cursor=current_cursor
            )
            if response is None or not response.templates:
                break
            result.extend(response.templates)
            if len(result) >= limit:
                break
            remain -= len(response.templates)
            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor
        return result[:limit]

    async def upload_image(self, chat_id: str, image: ImageInput) -> TemporaryAttachment | None:
        return await self._client._raw.chats.upload_image(chat_id, image)
