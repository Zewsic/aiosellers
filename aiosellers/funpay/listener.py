from __future__ import annotations

import logging
import time
from typing import TYPE_CHECKING

from .core.utils import order_id_from, random_tag
from .events import (
    ChatsListChangedEvent,
    InitialChatEvent,
    InitialOrderEvent,
    InitialPurchaseEvent,
    LastChatMessageChangedEvent,
    NewMessageEvent,
    NewOrderEvent,
    NewPurchaseEvent,
    NewReviewEvent,
    OrderClosedEvent,
    OrderPartiallyRefundedEvent,
    OrderRefundedEvent,
    OrdersListChangedEvent,
    OrderStatusChangedEvent,
    PurchaseClosedEvent,
    PurchaseRefundedEvent,
    PurchasesListChangedEvent,
    PurchaseStatusChangedEvent,
    ReviewChangedEvent,
    ReviewDeletedEvent,
)
from .exceptions import (
    AccountNotInitiatedError,
    RateLimitedError,
    RequestFailedError,
    UnauthorizedError,
)
from .parsers.chats import parse_bookmarks
from .schemas import MessageTypes, OrderSide, OrderStatuses

if TYPE_CHECKING:
    from .funpay import FunPay

logger = logging.getLogger("aiosellers.funpay.listener")

_REVIEW_EVENTS = {
    MessageTypes.NEW_FEEDBACK: NewReviewEvent,
    MessageTypes.FEEDBACK_CHANGED: ReviewChangedEvent,
    MessageTypes.FEEDBACK_DELETED: ReviewDeletedEvent,
}


class EventListener:
    """Poll FunPay runner objects. There is no websocket."""

    def __init__(self, client: FunPay) -> None:
        self.client = client
        self.sent_ids: dict[int | str, set[int]] = {}
        self._chat_tag: str | None = None
        self._order_tag: str | None = None
        self._chats: dict[int, tuple[int, int, str]] = {}
        self._orders: dict[str, OrderStatuses] = {}
        self._purchases: dict[str, OrderStatuses] = {}
        self._chat_ready = False
        self._orders_ready = False
        self._purchases_ready = False
        self._refresh_failures = 0
        client._listener = self

    def remember_sent(self, chat_id: int | str, message_id: int) -> None:
        self.sent_ids.setdefault(chat_id, set()).add(message_id)
        if isinstance(chat_id, int):
            self.sent_ids.setdefault(str(chat_id), set()).add(message_id)
        elif chat_id.isdigit():
            self.sent_ids.setdefault(int(chat_id), set()).add(message_id)

    def was_sent(self, chat_id: int | str, message_id: int) -> bool:
        if message_id in self.sent_ids.get(chat_id, ()):
            return True
        if isinstance(chat_id, int):
            return message_id in self.sent_ids.get(str(chat_id), ())
        if isinstance(chat_id, str) and chat_id.isdigit():
            return message_id in self.sent_ids.get(int(chat_id), ())
        return False

    async def listen(
        self,
        *,
        messages: bool = True,
        orders: bool = True,
        purchases: bool = True,
        reviews: bool = True,
        interval: float | None = None,
    ):
        pause = self.client._config.poll_interval if interval is None else interval
        while True:
            started = time.monotonic()
            transport = self.client._transport
            if transport is not None and time.monotonic() < transport.rate_limited_until:
                await _sleep(pause)
                continue
            events = await self.tick(
                messages=messages, orders=orders, purchases=purchases, reviews=reviews
            )
            for event in events:
                yield event
            remain = pause - (time.monotonic() - started)
            if remain > 0:
                await _sleep(remain)

    async def tick(
        self,
        *,
        messages: bool = True,
        orders: bool = True,
        purchases: bool = True,
        reviews: bool = True,
    ):
        transport = self.client._transport
        if transport is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        try:
            await transport.refresh_profile()
        except RequestFailedError as exc:
            self._refresh_failures += 1
            logger.exception("FunPay session refresh failed")
            if self._refresh_failures >= 3:
                if isinstance(exc, UnauthorizedError):
                    raise
                raise RequestFailedError(
                    str(exc), status_code=exc.status_code, body=exc.body
                ) from exc
            return []
        self._refresh_failures = 0
        try:
            return await self._collect(
                messages=messages, orders=orders, purchases=purchases, reviews=reviews
            )
        except RateLimitedError:
            logger.warning("FunPay rate limited")
            return []

    async def _collect(self, *, messages: bool, orders: bool, purchases: bool, reviews: bool):
        account_id = self.client.account_id
        if account_id is None:
            raise AccountNotInitiatedError("account is not initiated")
        raw = self.client._raw
        assert raw is not None
        payload = await raw.account.runner_poll(
            [
                {
                    "type": "chat_bookmarks",
                    "id": account_id,
                    "tag": self._chat_tag or random_tag(),
                    "data": False,
                },
                {
                    "type": "orders_counters",
                    "id": account_id,
                    "tag": self._order_tag or random_tag(),
                    "data": False,
                },
            ]
        )
        bookmarks = None
        counters = None
        for obj in payload.get("objects") or []:
            kind = obj.get("type")
            if obj.get("tag"):
                if kind == "chat_bookmarks":
                    self._chat_tag = obj["tag"]
                elif kind == "orders_counters":
                    self._order_tag = obj["tag"]
            if kind == "chat_bookmarks":
                bookmarks = obj
            elif kind == "orders_counters":
                counters = obj
        events = []
        if messages and bookmarks is not None:
            events.extend(await self._chat_events(bookmarks, reviews=reviews))
        buyer, seller = _counts(counters)
        if orders and counters is not None:
            _cursor, rows = await raw.orders.sales(None, {}, retry=False)
            events.extend(self._order_diff(rows, buyer, seller))
        if purchases:
            _cursor, rows = await raw.orders.purchases(None, retry=False)
            events.extend(
                self._purchase_diff(
                    rows,
                    buyer if counters is not None else 0,
                    seller if counters is not None else 0,
                )
            )
        return events

    async def _chat_events(self, obj: dict, *, reviews: bool):
        data = obj.get("data")
        html = data.get("html") if isinstance(data, dict) else data
        shortcuts = parse_bookmarks(
            html if isinstance(html, str) else "",
            self_id=self.client.account_id or 0,
        )
        if not self._chat_ready:
            events = []
            for shortcut in shortcuts:
                events.append(
                    InitialChatEvent(
                        client=self.client, chat=self.client.chats._from_shortcut(shortcut)
                    )
                )
                self._chats[shortcut.id] = (
                    shortcut.node_message_id,
                    shortcut.user_message_id,
                    shortcut.last_message_text,
                )
            self._chat_ready = True
            return events
        changed = []
        for shortcut in shortcuts:
            previous = self._chats.get(shortcut.id)
            stored = previous[0] if previous else 0
            if shortcut.node_message_id > stored:
                changed.append((shortcut, stored))
        if not changed:
            return []
        events = [
            ChatsListChangedEvent(
                client=self.client,
                chat=self.client.chats._from_shortcut(changed[0][0]),
            )
        ]
        raw = self.client._raw
        assert raw is not None
        for shortcut, stored in changed:
            chat = self.client.chats._from_shortcut(shortcut)
            events.append(LastChatMessageChangedEvent(client=self.client, chat=chat))
            try:
                history = await raw.chats.history(
                    shortcut.id, shortcut.node_message_id, retry=False
                )
            except Exception:
                logger.exception("FunPay history failed for chat %s", shortcut.id)
                history = []
                newest = shortcut.node_message_id
            else:
                newest = max((item.id for item in history), default=shortcut.node_message_id)
                for snap in sorted(history, key=lambda item: item.id):
                    if snap.id <= stored:
                        continue
                    message = self.client.chats._message(snap)
                    events.append(NewMessageEvent(client=self.client, chat=chat, message=message))
                    if reviews:
                        review_type = _REVIEW_EVENTS.get(message.type)
                        if review_type is not None:
                            events.append(
                                review_type(
                                    client=self.client,
                                    message=message,
                                    order_id=order_id_from(message.text),
                                )
                            )
            self._chats[shortcut.id] = (
                max(newest, shortcut.node_message_id),
                shortcut.user_message_id,
                shortcut.last_message_text,
            )
        return events

    def _order_diff(self, rows, buyer: int, seller: int):
        return self._diff(
            rows,
            self._orders,
            ready_name="_orders_ready",
            initial=InitialOrderEvent,
            changed=OrdersListChangedEvent,
            new=NewOrderEvent,
            status=OrderStatusChangedEvent,
            closed=OrderClosedEvent,
            refunded=OrderRefundedEvent,
            partial=OrderPartiallyRefundedEvent,
            buyer=buyer,
            seller=seller,
        )

    def _purchase_diff(self, rows, buyer: int, seller: int):
        return self._diff(
            rows,
            self._purchases,
            ready_name="_purchases_ready",
            initial=InitialPurchaseEvent,
            changed=PurchasesListChangedEvent,
            new=NewPurchaseEvent,
            status=PurchaseStatusChangedEvent,
            closed=PurchaseClosedEvent,
            refunded=PurchaseRefundedEvent,
            partial=None,
            buyer=buyer,
            seller=seller,
        )

    def _diff(
        self,
        rows,
        saved: dict[str, OrderStatuses],
        *,
        ready_name: str,
        initial,
        changed,
        new,
        status,
        closed,
        refunded,
        partial,
        buyer: int,
        seller: int,
    ):
        if not getattr(self, ready_name):
            events = []
            for row in rows:
                saved[row.id] = row.status
                order = self.client.orders._from_shortcut(row)
                if row.side is OrderSide.PURCHASE:
                    order.side = OrderSide.PURCHASE
                events.append(initial(client=self.client, order=order))
            setattr(self, ready_name, True)
            return events
        events = [changed(client=self.client, buyer_count=buyer, seller_count=seller)]
        if len(rows) > 100 or len(rows) < len(saved):
            logger.warning("skip order diff: page has %s rows, saved %s", len(rows), len(saved))
            return events
        seen: set[str] = set()
        for row in rows:
            seen.add(row.id)
            order = self.client.orders._from_shortcut(row)
            previous = saved.get(row.id)
            if previous is None:
                events.append(new(client=self.client, order=order))
                if row.status is OrderStatuses.CLOSED:
                    events.append(closed(client=self.client, order=order))
            elif previous != row.status:
                events.append(status(client=self.client, order=order))
                extra = {
                    OrderStatuses.CLOSED: closed,
                    OrderStatuses.REFUNDED: refunded,
                    OrderStatuses.PARTIALLY_REFUNDED: partial,
                }.get(row.status)
                if extra is not None:
                    events.append(extra(client=self.client, order=order))
            saved[row.id] = row.status
        for gone in [key for key in saved if key not in seen]:
            del saved[gone]
        return events


def _counts(counters: dict | None) -> tuple[int, int]:
    if not isinstance(counters, dict):
        return 0, 0
    data = counters.get("data") or {}
    if not isinstance(data, dict):
        return 0, 0
    return int(data.get("buyer") or 0), int(data.get("seller") or 0)


async def _sleep(seconds: float) -> None:
    import asyncio

    await asyncio.sleep(seconds)
