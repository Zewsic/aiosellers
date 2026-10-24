from __future__ import annotations

from enum import Enum


class EventTypes(Enum):
    INITIAL_CHAT = 0
    CHATS_LIST_CHANGED = 1
    LAST_CHAT_MESSAGE_CHANGED = 2
    NEW_MESSAGE = 3
    INITIAL_ORDER = 4
    ORDERS_LIST_CHANGED = 5
    NEW_ORDER = 6
    ORDER_STATUS_CHANGED = 7
    ORDER_CLOSED = 8
    ORDER_REFUNDED = 9
    ORDER_PARTIALLY_REFUNDED = 10
    INITIAL_PURCHASE = 11
    PURCHASES_LIST_CHANGED = 12
    NEW_PURCHASE = 13
    PURCHASE_STATUS_CHANGED = 14
    PURCHASE_CLOSED = 15
    PURCHASE_REFUNDED = 16
    NEW_REVIEW = 17
    REVIEW_CHANGED = 18
    REVIEW_DELETED = 19


class MessageTypes(Enum):
    NON_SYSTEM = 0
    ORDER_PURCHASED = 1
    ORDER_CONFIRMED = 2
    NEW_FEEDBACK = 3
    FEEDBACK_CHANGED = 4
    FEEDBACK_DELETED = 5
    NEW_FEEDBACK_ANSWER = 6
    FEEDBACK_ANSWER_CHANGED = 7
    FEEDBACK_ANSWER_DELETED = 8
    ORDER_REOPENED = 9
    REFUND = 10
    PARTIAL_REFUND = 11
    ORDER_CONFIRMED_BY_ADMIN = 12
    DISCORD = 13
    DEAR_VENDORS = 14
    REFUND_BY_ADMIN = 15


class OrderStatuses(Enum):
    PAID = 0
    CLOSED = 1
    REFUNDED = 2
    PARTIALLY_REFUNDED = 3
    UNPAID = 5


class SubCategoryTypes(Enum):
    COMMON = 0
    CURRENCY = 1


class Currency(Enum):
    USD = 0
    RUB = 1
    EUR = 2
    UNKNOWN = 3

    @property
    def code(self) -> str:
        if self is Currency.UNKNOWN:
            raise ValueError("UNKNOWN currency has no code")
        return self.name.lower()

    def __str__(self) -> str:
        return {Currency.USD: "$", Currency.RUB: "₽", Currency.EUR: "€", Currency.UNKNOWN: "¤"}[
            self
        ]


class Wallet(Enum):
    QIWI = 0
    BINANCE = 1
    TRC = 2
    CARD_RUB = 3
    CARD_USD = 4
    CARD_EUR = 5
    WEBMONEY = 6
    YOUMONEY = 7

    @property
    def wire(self) -> str:
        return {
            Wallet.QIWI: "qiwi",
            Wallet.BINANCE: "binance",
            Wallet.TRC: "usdt_trc",
            Wallet.CARD_RUB: "card_rub",
            Wallet.CARD_USD: "card_usd",
            Wallet.CARD_EUR: "card_eur",
            Wallet.WEBMONEY: "wmz",
            Wallet.YOUMONEY: "fps",
        }[self]


class OrderSide(Enum):
    SALE = 0
    PURCHASE = 1
