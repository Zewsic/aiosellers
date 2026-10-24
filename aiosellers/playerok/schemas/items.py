from datetime import datetime
from typing import Any

from pydantic import Field, model_validator

from . import ApiModel, ItemLogEvents, ItemStatuses, PageInfo, PriorityTypes, UserType
from .account import UserProfile
from .basic import File
from .games import GameCategoryDataField


class ItemPriorityStatusPriceRange(ApiModel):
    min: int | None = Field(None, alias="min")
    max: int | None = Field(None, alias="max")


class ItemPriorityStatus(ApiModel):
    id: str = Field(..., alias="id")
    price: int = Field(..., alias="price")
    name: str = Field(..., alias="name")
    type: PriorityTypes = Field(..., alias="type")
    period: int = Field(..., alias="period")
    price_range: ItemPriorityStatusPriceRange = Field(..., alias="priceRange")


class ItemLog(ApiModel):
    id: str = Field(..., alias="id")
    event: ItemLogEvents = Field(..., alias="event")
    created_at: datetime = Field(..., alias="createdAt")
    user: UserProfile | None = Field(None, alias="user")


class Item(ApiModel):
    id: str = Field(..., alias="id")
    slug: str | None = Field(None, alias="slug")
    name: str | None = Field(None, alias="name")
    description: str | None = Field(None, alias="description")
    price: int | None = Field(None, alias="price")
    raw_price: int | None = Field(None, alias="rawPrice")

    priority: PriorityTypes | None = Field(None, alias="priority")
    status: ItemStatuses | None = Field(None, alias="status")
    seller_type: UserType | None = Field(None, alias="sellerType")

    attachment: File | None = Field(None, alias="attachment")
    attachments: list[File] | None = Field(None, alias="attachments")
    user: UserProfile | None = Field(None, alias="user")

    attributes: dict[str, Any] | None = Field(None, alias="attributes")
    data_fields: list[GameCategoryDataField] | None = Field(None, alias="dataFields")
    comment: str | None = Field(None, alias="comment")

    approval_date: datetime | None = Field(None, alias="approvalDate")
    priority_position: int | None = Field(None, alias="priorityPosition")
    views_counter: int | None = Field(None, alias="viewsCounter")
    fee_multiplier: float | None = Field(None, alias="feeMultiplier")
    created_at: datetime | None = Field(None, alias="createdAt")
    updated_at: datetime | None = Field(None, alias="updatedAt")
    deleted_at: datetime | None = Field(None, alias="deletedAt")

    # Extracted from nested objects
    category_id: str | None = Field(None, alias="category")
    obtaining_type_id: str | None = Field(None, alias="obtainingType")

    @model_validator(mode="before")
    @classmethod
    def _extract_nested_ids(cls, data):
        if not isinstance(data, dict):
            return data

        # Extract category.id
        if "category" in data:
            category = data.get("category")
            if isinstance(category, dict) and "id" in category:
                data["category"] = category.get("id")

        # Extract obtainingType.id
        if "obtainingType" in data:
            obtaining_type = data.get("obtainingType")
            if isinstance(obtaining_type, dict) and "id" in obtaining_type:
                data["obtainingType"] = obtaining_type.get("id")

        return data


class MyItem(Item):
    prev_price: int | None = Field(None, alias="prevPrice")
    prev_fee_multiplier: float | None = Field(None, alias="prevFeeMultiplier")
    seller_notified_about_fee_change: bool | None = Field(
        None, alias="sellerNotifiedAboutFeeChange"
    )
    priority_price: int | None = Field(None, alias="priorityPrice")
    sequence: int | None = Field(None, alias="sequence")
    status_expiration_date: datetime | None = Field(None, alias="statusExpirationDate")
    status_description: str | None = Field(None, alias="statusDescription")
    status_payment: Any | None = Field(None, alias="statusPayment")  # Transaction
    is_editable: bool | None = Field(None, alias="isEditable")
    buyer: UserProfile | None = Field(None, alias="buyer")


class ItemList(ApiModel):
    items: list[Item] = Field(..., alias="items")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "items" not in data:
            edges = data.get("edges") or []
            data["items"] = [(edge or {}).get("node") for edge in edges if (edge or {}).get("node")]

        return data
