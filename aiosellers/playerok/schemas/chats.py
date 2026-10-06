from __future__ import annotations

import typing
from datetime import datetime

from pydantic import Field, model_validator

from . import (
    ApiModel,
    ChatMessageButtonTypes,
    ChatStatuses,
    ChatTypes,
    Game,
    Item,
    MessageTemplateTypes,
    PageInfo,
)
from .account import UserProfile
from .basic import File, UnimplementedApiModel

if typing.TYPE_CHECKING:
    from .deals import ItemDeal
    from .transactions import Transaction


class Event(UnimplementedApiModel):
    """# TODO: Implement Event model fields."""

    pass


class Moderator(UnimplementedApiModel):
    """# TODO: Implement Moderator model fields."""

    pass


class ChatMessageButton(ApiModel):
    type: ChatMessageButtonTypes = Field(..., alias="type")
    url: str | None = Field(None, alias="url")
    text: str | None = Field(None, alias="text")


class ChatMessage(ApiModel):
    id: str = Field(..., alias="id")
    text: str | None = Field(None, alias="text")
    created_at: datetime = Field(..., alias="createdAt")
    deleted_at: datetime | None = Field(None, alias="deletedAt")
    is_read: bool = Field(..., alias="isRead")
    is_suspicious: bool | None = Field(None, alias="isSuspicious")
    is_bulk_messaging: bool | None = Field(None, alias="isBulkMessaging")
    file: File | None = Field(None, alias="file")
    game: Game | None = Field(None, alias="game")
    user: UserProfile | None = Field(None, alias="user")
    deal: ItemDeal | None = Field(None, alias="deal")
    item: Item | None = Field(None, alias="item")
    transaction: Transaction | None = Field(None, alias="transaction")
    moderator: Moderator | None = Field(None, alias="moderator")
    event_by_user: UserProfile | None = Field(None, alias="eventByUser")
    event_to_user: UserProfile | None = Field(None, alias="eventToUser")
    is_auto_response: bool | None = Field(None, alias="isAutoResponse")
    event: Event | str | None = Field(None, alias="event")
    buttons: list[ChatMessageButton] | None = Field(None, alias="buttons")


class ChatMessageList(ApiModel):
    messages: list[ChatMessage] = Field(..., alias="messages")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "messages" not in data:
            edges = data.get("edges") or []
            data["messages"] = [
                (edge or {}).get("node") for edge in edges if (edge or {}).get("node")
            ]
        return data


class Chat(ApiModel):
    id: str = Field(..., alias="id")
    type: ChatTypes = Field(ChatTypes.PM, alias="type")
    status: ChatStatuses | None = Field(None, alias="status")
    unread_messages_counter: int | None = Field(None, alias="unreadMessagesCounter")
    bookmarked: bool | None = Field(None, alias="bookmarked")
    is_texting_allowed: bool | None = Field(None, alias="isTextingAllowed")
    owner: UserProfile | None = Field(None, alias="owner")
    deals: list[ItemDeal] | None = Field(None, alias="deals")
    last_message: ChatMessage | None = Field(None, alias="lastMessage")
    users: list[UserProfile] | None = Field(None, alias="participants")
    started_at: datetime | None = Field(None, alias="startedAt")
    finished_at: datetime | None = Field(None, alias="finishedAt")


class ChatList(ApiModel):
    chats: list[Chat] = Field(..., alias="chats")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "chats" not in data:
            edges = data.get("edges") or []
            data["chats"] = [(edge or {}).get("node") for edge in edges if (edge or {}).get("node")]
        return data


class MessageTemplate(ApiModel):
    id: str = Field(..., alias="id")
    type: MessageTemplateTypes = Field(..., alias="type")
    title: str = Field(..., alias="title")
    text: str = Field(..., alias="text")
    sequence: int = Field(..., alias="sequence")
    created_at: datetime = Field(..., alias="createdAt")
    group: typing.Any | None = Field(None, alias="group")


class MessageTemplateList(ApiModel):
    templates: list[MessageTemplate] = Field(..., alias="templates")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data
        if "templates" not in data:
            edges = data.get("edges") or []
            data["templates"] = [
                (edge or {}).get("node") for edge in edges if (edge or {}).get("node")
            ]
        return data


class TemporaryAttachment(ApiModel):
    id: str = Field(..., alias="id")
    url: str = Field(..., alias="url")
    chat_id: str = Field(..., alias="chatId")
    client_attachment_id: str = Field(..., alias="clientAttachmentId")
    expires_at: datetime = Field(..., alias="expiresAt")


# Resolve forward references after all models are defined
from .deals import ItemDeal  # noqa: E402
from .transactions import Transaction  # noqa: E402

ChatMessage.model_rebuild()
Chat.model_rebuild()
ChatList.model_rebuild()
ChatMessageList.model_rebuild()
