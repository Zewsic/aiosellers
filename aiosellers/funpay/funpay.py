from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass, fields
from typing import Any

from .api import AccountAPI, CategoryAPI, ChatAPI, FinanceAPI, LotAPI, OrderAPI
from .client_config import FunPayClientConfig
from .core.identity_map import IdentityMap
from .entities.category import Category
from .entities.chat import Chat
from .entities.lot import Lot, MyLot
from .entities.order import Order
from .entities.user import User
from .events import FunPayEvent
from .listener import EventListener
from .raw import RawAPI
from .schemas import EventTypes
from .transport import FunPayTransport

logger = logging.getLogger("aiosellers.funpay")

Handler = Callable[[FunPayEvent], Awaitable[None]]
Predicate = Callable[[FunPayEvent], bool]
TextFilter = str | Callable[[str | None], bool]

_SKIP = {
    EventTypes.INITIAL_CHAT,
    EventTypes.INITIAL_ORDER,
    EventTypes.INITIAL_PURCHASE,
}


@dataclass(slots=True)
class _Handler:
    event_type: EventTypes
    fn: Handler
    text: TextFilter | None = None
    predicate: Predicate | None = None
    stars: int | None = None


@dataclass(slots=True)
class _IdentityMaps:
    users: IdentityMap[int, User]
    chats: IdentityMap[int, Chat]
    orders: IdentityMap[str, Order]
    lots: IdentityMap[str, Lot | MyLot]
    categories: IdentityMap[int, Category]


class FunPay:
    """High-level FunPay client."""

    def __init__(self, config: FunPayClientConfig | str | None = None) -> None:
        if isinstance(config, str):
            config = FunPayClientConfig(golden_key=config)
        elif config is None:
            config = FunPayClientConfig()
        self._config = config
        self._transport: FunPayTransport | None = None
        self._raw: RawAPI | None = None
        self._listener: EventListener | None = None
        self._use_identity_map = config.use_identity_map
        self._account_id: int | None = None
        if self._use_identity_map:
            self._identity_maps = _IdentityMaps(
                users=IdentityMap(),
                chats=IdentityMap(),
                orders=IdentityMap(),
                lots=IdentityMap(),
                categories=IdentityMap(),
            )
        self.account = AccountAPI(self)
        self.chats = ChatAPI(self)
        self.orders = OrderAPI(self)
        self.lots = LotAPI(self)
        self.categories = CategoryAPI(self)
        self.finance = FinanceAPI(self)
        self.users = self.account
        self._handlers: list[_Handler] = []

    @property
    def account_id(self) -> int | None:
        return self._account_id

    def remember(self, bucket: str, key, entity):
        entity._client = self
        if not self._use_identity_map:
            return entity
        cache = getattr(self._identity_maps, bucket)
        current = cache.get(key)
        if current is None or type(current) is not type(entity):
            return cache.set(key, entity)
        for item in fields(entity):
            if item.name.startswith("_"):
                continue
            setattr(current, item.name, getattr(entity, item.name))
        return current

    def cached(self, bucket: str, key):
        if not self._use_identity_map:
            return None
        return getattr(self._identity_maps, bucket).get(key)

    async def __aenter__(self) -> FunPay:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.close()

    async def start(self) -> None:
        if self._transport is not None:
            return
        self._transport = FunPayTransport(self._config)
        self._raw = RawAPI(self._transport)
        try:
            await self._transport.refresh_profile()
        except Exception:
            await self.close()
            raise
        self._account_id = self._transport.account_id

    async def close(self) -> None:
        transport = self._transport
        self._transport = None
        self._raw = None
        self._account_id = None
        self._listener = None
        if self._use_identity_map:
            self._identity_maps.users.clear()
            self._identity_maps.chats.clear()
            self._identity_maps.orders.clear()
            self._identity_maps.lots.clear()
            self._identity_maps.categories.clear()
        if transport is not None:
            await transport.close()

    def listen(
        self,
        *,
        messages: bool = True,
        orders: bool = True,
        purchases: bool = True,
        reviews: bool = True,
        interval: float | None = None,
    ):
        if self._transport is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        return EventListener(self).listen(
            messages=messages,
            orders=orders,
            purchases=purchases,
            reviews=reviews,
            interval=interval,
        )

    async def start_polling(
        self,
        *,
        messages: bool = True,
        orders: bool = True,
        purchases: bool = True,
        reviews: bool = True,
    ) -> None:
        await self.start()
        try:
            async for event in self.listen(
                messages=messages, orders=orders, purchases=purchases, reviews=reviews
            ):
                await self._dispatch(event)
        finally:
            await self.close()

    def on(
        self,
        event_type: EventTypes,
        fn: Handler | Predicate | None = None,
        *,
        text: TextFilter | None = None,
    ):
        return self._on(event_type, fn, text=text)

    def on_message(self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None):
        return self._on(EventTypes.NEW_MESSAGE, fn, text=text)

    def on_new_order(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.NEW_ORDER, fn, text=text)

    def on_order_status_changed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.ORDER_STATUS_CHANGED, fn, text=text)

    def on_order_closed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.ORDER_CLOSED, fn, text=text)

    def on_order_refunded(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.ORDER_REFUNDED, fn, text=text)

    def on_order_partially_refunded(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.ORDER_PARTIALLY_REFUNDED, fn, text=text)

    def on_new_purchase(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.NEW_PURCHASE, fn, text=text)

    def on_purchase_status_changed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.PURCHASE_STATUS_CHANGED, fn, text=text)

    def on_purchase_closed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.PURCHASE_CLOSED, fn, text=text)

    def on_purchase_refunded(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.PURCHASE_REFUNDED, fn, text=text)

    def on_new_review(
        self,
        fn: Handler | Predicate | None = None,
        *,
        text: TextFilter | None = None,
        stars: int | None = None,
    ):
        return self._on(EventTypes.NEW_REVIEW, fn, text=text, stars=stars)

    def on_review_changed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.REVIEW_CHANGED, fn, text=text)

    def on_review_deleted(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.REVIEW_DELETED, fn, text=text)

    def on_last_chat_message_changed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.LAST_CHAT_MESSAGE_CHANGED, fn, text=text)

    def on_chats_list_changed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.CHATS_LIST_CHANGED, fn, text=text)

    def on_orders_list_changed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.ORDERS_LIST_CHANGED, fn, text=text)

    def on_purchases_list_changed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.PURCHASES_LIST_CHANGED, fn, text=text)

    def _on(
        self,
        event_type: EventTypes,
        fn: Handler | Predicate | None = None,
        *,
        text: TextFilter | None = None,
        stars: int | None = None,
    ):
        def register(func: Handler, predicate: Predicate | None = None) -> Handler:
            self._handlers.append(
                _Handler(
                    event_type=event_type,
                    fn=func,
                    text=text,
                    predicate=predicate,
                    stars=stars,
                )
            )
            return func

        if fn is None:
            return register
        if inspect.iscoroutinefunction(fn):
            return register(fn)
        return lambda func: register(func, predicate=fn)

    async def _dispatch(self, event: FunPayEvent) -> None:
        if event.type in _SKIP:
            return
        stars = None
        star_failed = False
        if event.type is EventTypes.NEW_REVIEW and any(
            handler.stars is not None and handler.event_type is EventTypes.NEW_REVIEW
            for handler in self._handlers
        ):
            try:
                order = await self.orders.get(getattr(event, "order_id", None))
                stars = order.review.stars if order.review is not None else None
            except Exception:
                logger.exception("Review star lookup failed")
                star_failed = True
        for handler in list(self._handlers):
            if handler.event_type != event.type:
                continue
            if handler.stars is not None and (star_failed or stars != handler.stars):
                continue
            if handler.text is not None:
                text = _event_text(event)
                try:
                    matched = handler.text(text) if callable(handler.text) else text == handler.text
                except Exception:
                    logger.exception("Event text filter failed")
                    continue
                if not matched:
                    continue
            if handler.predicate is not None:
                try:
                    if not handler.predicate(event):
                        continue
                except Exception:
                    logger.exception("Event filter failed")
                    continue
            try:
                await handler.fn(event)
            except Exception:
                logger.exception("Event handler failed")


def _event_text(event: Any) -> str | None:
    order = getattr(event, "order", None)
    message = getattr(event, "message", None)
    if order is not None and message is None:
        return order.description
    if message is not None:
        return message.text
    return None
