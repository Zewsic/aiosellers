from __future__ import annotations

import typing
from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from . import (
    ApiModel,
    ItemDealDirections,
    ItemDealStatuses,
    PageInfo,
    ReviewStatuses,
)
from .account import UserProfile
from .games import GameCategoryDataField
from .items import Item, ItemLog

if typing.TYPE_CHECKING:
    from . import Chat, Moderator, Transaction


class ItemDeal(ApiModel):
    id: str = Field(..., alias="id")
    status: ItemDealStatuses = Field(..., alias="status")
    status_expiration_date: datetime | None = Field(None, alias="statusExpirationDate")
    status_description: str | None = Field(None, alias="statusDescription")
    direction: ItemDealDirections = Field(..., alias="direction")
    obtaining: str | None = Field(None, alias="obtaining")
    has_problem: bool = Field(False, alias="hasProblem")
    report_problem_enabled: bool | None = Field(None, alias="reportProblemEnabled")
    completed_user: UserProfile | None = Field(None, alias="completedBy")
    props: dict[str, Any] | None = Field(None, alias="props")
    previous_status: ItemDealStatuses | None = Field(None, alias="prevStatus")
    completed_at: datetime | None = Field(None, alias="completedAt")
    created_at: datetime | None = Field(None, alias="createdAt")
    logs: list[ItemLog] | None = Field(None, alias="logs")
    transaction: Transaction | None = Field(None, alias="transaction")
    user: UserProfile | None = Field(None, alias="user")
    chat: Chat | None = Field(None, alias="chat")
    item: Item | None = Field(None, alias="item")
    review: Review | None = Field(None, alias="testimonial")
    obtaining_fields: list[GameCategoryDataField] | None = Field(None, alias="obtainingFields")
    comment_from_buyer: str | None = Field(None, alias="commentFromBuyer")


class ItemDealList(ApiModel):
    deals: list[ItemDeal] = Field(..., alias="deals")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "deals" not in data:
            edges = data.get("edges") or []
            data["deals"] = [(edge or {}).get("node") for edge in edges if (edge or {}).get("node")]
        return data


class Review(ApiModel):
    id: str = Field(..., alias="id")
    status: ReviewStatuses | None = Field(None, alias="status")
    text: str | None = Field(None, alias="text")
    rating: int | None = Field(None, alias="rating")
    created_at: datetime | None = Field(None, alias="createdAt")
    updated_at: datetime | None = Field(None, alias="updatedAt")
    deal: ItemDeal | None = Field(None, alias="deal")
    creator: UserProfile | None = Field(None, alias="creator")
    moderator: Moderator | None = Field(None, alias="moderator")
    user: UserProfile | None = Field(None, alias="user")


class ReviewList(ApiModel):
    reviews: list[Review] = Field(..., alias="reviews")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "reviews" not in data:
            edges = data.get("edges") or []
            data["reviews"] = [
                (edge or {}).get("node") for edge in edges if (edge or {}).get("node")
            ]
        return data


# Resolve forward references after all models are defined
from .chats import Chat, Moderator  # noqa: E402
from .transactions import Transaction  # noqa: E402

ItemDeal.model_rebuild()
ItemDealList.model_rebuild()
Review.model_rebuild()
ReviewList.model_rebuild()
