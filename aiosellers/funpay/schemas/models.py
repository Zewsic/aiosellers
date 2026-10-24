from __future__ import annotations

from pydantic import BaseModel, ConfigDict

from .enums import Currency, MessageTypes, OrderSide, OrderStatuses, SubCategoryTypes


class _Frozen(BaseModel):
    model_config = ConfigDict(frozen=True)


class SubCategorySnapshot(_Frozen):
    id: int
    name: str
    type: SubCategoryTypes
    category_id: int
    position: int


class CategorySnapshot(_Frozen):
    id: int
    name: str
    position: int
    subcategories: list[SubCategorySnapshot]


class AccountSnapshot(_Frozen):
    id: int
    username: str
    csrf_token: str
    locale: str | None
    active_sales: int
    active_purchases: int
    categories: list[CategorySnapshot]


class ChatShortcut(_Frozen):
    id: int
    name: str
    last_message_text: str
    node_message_id: int
    user_message_id: int
    unread: bool
    last_by_bot: bool
    html: str


class MessageSnapshot(_Frozen):
    id: int
    text: str | None
    chat_id: int | str
    chat_name: str | None
    author: str | None
    author_id: int
    interlocutor_id: int | None
    image_link: str | None
    image_name: str | None
    type: MessageTypes
    by_bot: bool
    badge: str | None
    is_support: bool
    is_moderation: bool
    is_arbitration: bool
    is_auto_reply: bool
    html: str


class OrderShortcut(_Frozen):
    id: str
    status: OrderStatuses
    side: OrderSide
    description: str
    price: float
    currency: Currency
    buyer_username: str
    buyer_id: int
    subcategory_name: str | None
    html: str


class ReviewSnapshot(_Frozen):
    stars: int | None = None
    text: str | None = None
    reply: str | None = None
    order_id: str | None = None
    author: str | None = None
    author_id: int | None = None
    by_bot: bool = False
    reply_by_bot: bool = False


class OrderSnapshot(OrderShortcut):
    chat_id: int | None = None
    amount: int | None = None
    review: ReviewSnapshot | None = None
    seller_username: str | None = None
    seller_id: int | None = None


class LotShortcut(_Frozen):
    id: str
    server: str | None
    description: str | None
    price: float
    subcategory_id: int
    seller_id: int | None
    seller_username: str | None
    auto_delivery: bool
    html: str


class MyLotShortcut(_Frozen):
    id: str
    description: str | None
    price: float | None
    active: bool
    auto_delivery: bool
    amount: int | None
    server: str | None
    subcategory_id: int
    html: str


class Balance(_Frozen):
    rub: float = 0
    usd: float = 0
    eur: float = 0
    total_rub: float | None = None
    total_usd: float | None = None
    total_eur: float | None = None


class TransactionSnapshot(_Frozen):
    id: str
    type: str
    amount: float
    currency: Currency
    date: str
    description: str
    status: str
    withdrawal_number: str | None = None


class BuyerViewing(_Frozen):
    buyer_id: int
    lot_id: int | None = None
    lot_text: str | None = None
    subcategory_id: int | None = None
    subcategory_text: str | None = None


class CalcResult(_Frozen):
    methods: list[tuple[str, float, Currency]]


class UserSnapshot(_Frozen):
    id: int
    username: str
    avatar_url: str | None = None
    online: bool = False
    banned: bool = False
