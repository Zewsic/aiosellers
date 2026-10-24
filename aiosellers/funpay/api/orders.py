from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator, Literal

from ..entities.order import Order
from ..entities.review import Review
from ..exceptions import RequestFailedError
from ..schemas import OrderShortcut, OrderSide, OrderSnapshot, OrderStatuses

if TYPE_CHECKING:
    from ..funpay import FunPay


class OrderAPI:
    def __init__(self, client: FunPay) -> None:
        self._client = client

    def _require(self):
        if self._client._raw is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        return self._client._raw

    def _review(self, snap) -> Review | None:
        if snap is None:
            return None
        review = Review(
            stars=snap.stars,
            text=snap.text,
            reply=snap.reply,
            order_id=snap.order_id,
            author=snap.author,
            author_id=snap.author_id,
            by_bot=snap.by_bot,
            reply_by_bot=snap.reply_by_bot,
        )
        review._client = self._client
        return review

    def _side(self, snap: OrderSnapshot) -> OrderSide:
        me = self._client.account_id
        if me and snap.buyer_id == me:
            return OrderSide.PURCHASE
        if me and snap.seller_id == me:
            return OrderSide.SALE
        return snap.side

    def _from_shortcut(self, snap: OrderShortcut) -> Order:
        order = Order(
            id=snap.id,
            status=snap.status,
            side=snap.side,
            description=snap.description,
            price=snap.price,
            currency=snap.currency,
            buyer_username=snap.buyer_username,
            buyer_id=snap.buyer_id,
            subcategory_name=snap.subcategory_name,
            html=snap.html,
        )
        return self._client.remember("orders", snap.id, order)

    def _from_snapshot(self, snap: OrderSnapshot) -> Order:
        order = Order(
            id=snap.id,
            status=snap.status,
            side=self._side(snap),
            description=snap.description,
            price=snap.price,
            currency=snap.currency,
            buyer_username=snap.buyer_username,
            buyer_id=snap.buyer_id,
            subcategory_name=snap.subcategory_name,
            chat_id=snap.chat_id,
            amount=snap.amount,
            review=self._review(snap.review),
            seller_username=snap.seller_username,
            seller_id=snap.seller_id,
            html=snap.html,
        )
        return self._client.remember("orders", snap.id, order)

    async def list(
        self,
        *,
        side: OrderSide = OrderSide.SALE,
        limit: int | None = None,
        cursor: str | None = None,
        buyer: str | None = None,
        state: Literal["closed", "paid", "refunded"] | None = None,
        game: int | None = None,
        include_paid: bool = True,
        include_closed: bool = True,
        include_refunded: bool = True,
    ) -> tuple[str | None, list[Order]]:
        if side is OrderSide.PURCHASE:
            cursor, rows = await self._require().orders.purchases(cursor)
        else:
            query = {}
            if buyer is not None:
                query["buyer"] = buyer
            if state is not None:
                query["state"] = state
            if game is not None:
                query["game"] = game
            cursor, rows = await self._require().orders.sales(cursor, query)
        allowed: set[OrderStatuses] = set()
        if include_paid:
            allowed.add(OrderStatuses.PAID)
            allowed.add(OrderStatuses.UNPAID)
        if include_closed:
            allowed.add(OrderStatuses.CLOSED)
        if include_refunded:
            allowed.add(OrderStatuses.REFUNDED)
            allowed.add(OrderStatuses.PARTIALLY_REFUNDED)
        rows = [row for row in rows if row.status in allowed]
        if limit is not None:
            rows = rows[:limit]
        return cursor, [self._from_shortcut(row) for row in rows]

    async def iter(self, *, side: OrderSide = OrderSide.SALE, **filters) -> AsyncIterator[Order]:
        cursor = filters.pop("cursor", None)
        while True:
            cursor, rows = await self.list(side=side, cursor=cursor, **filters)
            for row in rows:
                yield row
            if not cursor:
                return

    async def get(self, order_id: str, *, force_refresh: bool = False) -> Order:
        if not force_refresh:
            cached = self._client.cached("orders", order_id)
            if cached is not None:
                return cached
        found = await self._require().orders.get_many([order_id])
        snap = found.get(order_id)
        if snap is None:
            raise RequestFailedError(f"order {order_id} missing")
        return self._from_snapshot(snap)

    async def refund(self, order_id: str) -> None:
        await self._require().orders.refund(order_id)

    async def reply_review(self, order_id: str, text: str) -> None:
        await self._require().orders.review(order_id, text, None)

    async def send_review(
        self, order_id: str, text: str, rating: Literal[1, 2, 3, 4, 5] = 5
    ) -> None:
        await self._require().orders.review(order_id, text, rating)

    async def delete_review(self, order_id: str) -> None:
        await self._require().orders.delete_review(order_id)
