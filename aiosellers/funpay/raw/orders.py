from __future__ import annotations

from urllib.parse import urlencode

from ..core.constants import BOT_MARK
from ..exceptions import FeedbackEditingError, RefundError, RequestFailedError
from ..parsers.orders import parse_order_api, parse_order_list
from ..schemas import OrderSide
from ..transport.tls import response_json, response_text
from .base import RawBase

_QUERY_KEYS = ("id", "buyer", "state", "game")


class RawOrders(RawBase):
    async def sales(
        self,
        cursor: str | None = None,
        query: dict | None = None,
        *,
        retry: bool = True,
    ):
        filters = {
            key: value
            for key, value in (query or {}).items()
            if key in _QUERY_KEYS and value is not None
        }

        async def run():
            if cursor is None:
                path = "orders/trade"
                if filters:
                    path += "?" + urlencode(filters)
                response = await self.transport.request("GET", path)
            else:
                response = await self.transport.request(
                    "POST",
                    "orders/trade",
                    data={"continue": cursor, **filters},
                )
            return parse_order_list(response_text(response), side=OrderSide.SALE)

        return await self._call(run, retry=retry)

    async def purchases(self, cursor: str | None = None, *, retry: bool = True):
        async def run():
            if cursor is None:
                response = await self.transport.request("GET", "orders/")
            else:
                response = await self.transport.request(
                    "POST", "orders/", data={"continue": cursor}
                )
            return parse_order_list(response_text(response), side=OrderSide.PURCHASE)

        return await self._call(run, retry=retry)

    async def get_many(self, ids: list[str], locale: str | None = None):
        if not 1 <= len(ids) <= 10:
            raise ValueError("order_ids must contain 1–10 items")

        async def run():
            language = locale or self.transport.locale or "ru"
            response = await self.transport.request(
                "POST",
                "https://funpay.com/api/orders/get",
                json_body={"order_uids": list(ids), "include": ["details", "users", "review"]},
                headers={"Accept-Language": language},
            )
            data = response_json(response)
            if not isinstance(data, dict) or data.get("status") != "SUCCESS" or "data" not in data:
                raise RequestFailedError(
                    "orders lookup failed",
                    status_code=getattr(response, "status_code", None),
                    body=response_text(response),
                )
            return {key: parse_order_api(value) for key, value in data["data"].items()}

        return await self._call(run)

    async def refund(self, order_id: str) -> None:
        async def run():
            response = await self.transport.request("POST", "orders/refund", data={"id": order_id})
            body = response_json(response)
            if isinstance(body, dict) and body.get("error"):
                raise RefundError(
                    body.get("msg"),
                    order_id,
                    status_code=getattr(response, "status_code", None),
                    body=response_text(response),
                )

        await self._call(run)

    async def review(self, order_id: str, text: str | None, rating: int | None) -> None:
        async def run():
            response = await self.transport.request(
                "POST",
                "orders/review",
                data={
                    "authorId": self.transport.account_id,
                    "text": f"{text}{BOT_MARK}" if text else "",
                    "rating": rating if rating is not None else "",
                    "orderId": order_id,
                },
                raise_not_200=False,
            )
            self._raise_feedback(response, order_id)

        await self._call(run)

    async def delete_review(self, order_id: str) -> None:
        async def run():
            response = await self.transport.request(
                "POST",
                "orders/reviewDelete",
                data={"authorId": self.transport.account_id, "orderId": order_id},
                raise_not_200=False,
            )
            self._raise_feedback(response, order_id)

        await self._call(run)

    @staticmethod
    def _raise_feedback(response, order_id: str) -> None:
        status = getattr(response, "status_code", None)
        if status == 400:
            message = None
            try:
                body = response_json(response)
                if isinstance(body, dict):
                    message = body.get("msg")
            except Exception:
                message = None
            raise FeedbackEditingError(
                str(message) if message else None,
                order_id,
                status_code=400,
                body=response_text(response),
            )
        if status not in (None, 200):
            raise RequestFailedError(
                f"HTTP {status}",
                status_code=status,
                body=response_text(response),
            )
