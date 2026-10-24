from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

from .entities.chat import Chat, Message
from .entities.order import Order
from .schemas import EventTypes

if TYPE_CHECKING:
    from .funpay import FunPay


@dataclass(slots=True)
class InitialChatEvent:
    client: FunPay
    chat: Chat
    type: EventTypes = EventTypes.INITIAL_CHAT


@dataclass(slots=True)
class ChatsListChangedEvent:
    client: FunPay
    chat: Chat
    type: EventTypes = EventTypes.CHATS_LIST_CHANGED


@dataclass(slots=True)
class LastChatMessageChangedEvent:
    client: FunPay
    chat: Chat
    type: EventTypes = EventTypes.LAST_CHAT_MESSAGE_CHANGED


@dataclass(slots=True)
class NewMessageEvent:
    client: FunPay
    chat: Chat
    message: Message
    type: EventTypes = EventTypes.NEW_MESSAGE


@dataclass(slots=True)
class InitialOrderEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.INITIAL_ORDER


@dataclass(slots=True)
class OrdersListChangedEvent:
    client: FunPay
    buyer_count: int
    seller_count: int
    type: EventTypes = EventTypes.ORDERS_LIST_CHANGED


@dataclass(slots=True)
class NewOrderEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.NEW_ORDER


@dataclass(slots=True)
class OrderStatusChangedEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.ORDER_STATUS_CHANGED


@dataclass(slots=True)
class OrderClosedEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.ORDER_CLOSED


@dataclass(slots=True)
class OrderRefundedEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.ORDER_REFUNDED


@dataclass(slots=True)
class OrderPartiallyRefundedEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.ORDER_PARTIALLY_REFUNDED


@dataclass(slots=True)
class InitialPurchaseEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.INITIAL_PURCHASE


@dataclass(slots=True)
class PurchasesListChangedEvent:
    client: FunPay
    buyer_count: int
    seller_count: int
    type: EventTypes = EventTypes.PURCHASES_LIST_CHANGED


@dataclass(slots=True)
class NewPurchaseEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.NEW_PURCHASE


@dataclass(slots=True)
class PurchaseStatusChangedEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.PURCHASE_STATUS_CHANGED


@dataclass(slots=True)
class PurchaseClosedEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.PURCHASE_CLOSED


@dataclass(slots=True)
class PurchaseRefundedEvent:
    client: FunPay
    order: Order
    type: EventTypes = EventTypes.PURCHASE_REFUNDED


@dataclass(slots=True)
class NewReviewEvent:
    client: FunPay
    message: Message
    order_id: str | None
    type: EventTypes = EventTypes.NEW_REVIEW


@dataclass(slots=True)
class ReviewChangedEvent:
    client: FunPay
    message: Message
    order_id: str | None
    type: EventTypes = EventTypes.REVIEW_CHANGED


@dataclass(slots=True)
class ReviewDeletedEvent:
    client: FunPay
    message: Message
    order_id: str | None
    type: EventTypes = EventTypes.REVIEW_DELETED


FunPayEvent = (
    InitialChatEvent
    | ChatsListChangedEvent
    | LastChatMessageChangedEvent
    | NewMessageEvent
    | InitialOrderEvent
    | OrdersListChangedEvent
    | NewOrderEvent
    | OrderStatusChangedEvent
    | OrderClosedEvent
    | OrderRefundedEvent
    | OrderPartiallyRefundedEvent
    | InitialPurchaseEvent
    | PurchasesListChangedEvent
    | NewPurchaseEvent
    | PurchaseStatusChangedEvent
    | PurchaseClosedEvent
    | PurchaseRefundedEvent
    | NewReviewEvent
    | ReviewChangedEvent
    | ReviewDeletedEvent
)
