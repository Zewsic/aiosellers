from __future__ import annotations

from bs4 import BeautifulSoup

from ..core.constants import BOT_MARK, OLD_BOT_MARK
from ..core.utils import parse_currency, parse_price
from ..exceptions import UnauthorizedError
from ..schemas import OrderShortcut, OrderSide, OrderSnapshot, OrderStatuses, ReviewSnapshot

_SALES_HEADERS = frozenset({"мои продажи", "my sales", "мої продажі"})


def _user_id(href: str | None) -> int:
    if not href or "/users/" not in href:
        return 0
    rest = href.split("/users/", 1)[1].strip("/")
    head = rest.split("/", 1)[0]
    return int(head) if head.isdigit() else 0


def _status(classes: list[str]) -> OrderStatuses:
    if "warning" in classes:
        return OrderStatuses.REFUNDED
    if "info" in classes:
        return OrderStatuses.PAID
    return OrderStatuses.CLOSED


def parse_order_list(html: str, *, side: OrderSide) -> tuple[str | None, list[OrderShortcut]]:
    soup = BeautifulSoup(html, "lxml")
    if side is OrderSide.SALE:
        header = soup.select_one("h1.page-header")
        if header is not None:
            first = next(header.stripped_strings, "")
            if first.lower() not in _SALES_HEADERS:
                raise UnauthorizedError("sales page unauthorized", body=html)
    cursor_node = soup.select_one("input[name=continue]")
    cursor = cursor_node.get("value") if cursor_node is not None else None
    if cursor == "":
        cursor = None
    orders: list[OrderShortcut] = []
    for row in soup.select("a.tc-item"):
        order_node = row.select_one("div.tc-order")
        order_id = (order_node.get_text(strip=True) if order_node is not None else "").lstrip("#")
        desc_node = row.select_one("div.order-desc div")
        price_node = row.select_one("div.tc-price")
        price, currency = parse_price(price_node.get_text(" ", strip=True) if price_node else "")
        user = row.select_one("div.media-user-name span")
        sub = row.select_one("div.text-muted")
        orders.append(
            OrderShortcut(
                id=order_id,
                status=_status(row.get("class") or []),
                side=side,
                description=desc_node.get_text(" ", strip=True) if desc_node is not None else "",
                price=price,
                currency=currency,
                buyer_username=user.get_text(" ", strip=True) if user is not None else "",
                buyer_id=_user_id(user.get("data-href") if user is not None else None),
                subcategory_name=sub.get_text(" ", strip=True) if sub is not None else None,
                html=str(row),
            )
        )
    return cursor, orders


def _map_status(status: str) -> OrderStatuses:
    lowered = (status or "").lower()
    if lowered == "paid":
        return OrderStatuses.PAID
    if lowered == "closed":
        return OrderStatuses.CLOSED
    if lowered == "refunded":
        return OrderStatuses.REFUNDED
    if "partial" in lowered:
        return OrderStatuses.PARTIALLY_REFUNDED
    return OrderStatuses.UNPAID


def _marked(text: str | None) -> bool:
    return bool(text and (text.endswith(BOT_MARK) or text.endswith(OLD_BOT_MARK)))


def _chat_id(value) -> int | None:
    if isinstance(value, int):
        return value
    if isinstance(value, str) and value.isdigit():
        return int(value)
    return None


def parse_order_api(data: dict) -> OrderSnapshot:
    order_id = str(data["order_uid"])
    buyer = data.get("buyer") or {}
    seller = data.get("seller") or {}
    chat = data.get("chat") or {}
    review_raw = data.get("review")
    review = None
    if isinstance(review_raw, dict) and (
        review_raw.get("text") or review_raw.get("rating") or review_raw.get("reply")
    ):
        text = review_raw.get("text") or None
        reply = review_raw.get("reply") or None
        review = ReviewSnapshot(
            stars=review_raw.get("rating"),
            text=text,
            reply=reply,
            order_id=order_id,
            author=buyer.get("name"),
            author_id=buyer.get("user_id"),
            by_bot=_marked(text),
            reply_by_bot=_marked(reply),
        )
    type_data = data.get("type_data") or {}
    amount = None
    if type_data.get("amount") not in (None, ""):
        amount_float = float(type_data["amount"])
        if int(amount_float) == amount_float:
            amount = int(amount_float)
    section = data.get("section") or {}
    node = type_data.get("node") or {}
    buyer_id = buyer.get("user_id")
    seller_id = seller.get("user_id")
    return OrderSnapshot(
        id=order_id,
        status=_map_status(str(data.get("status") or "")),
        side=OrderSide.SALE,
        description=_offer_title(type_data.get("fields")),
        price=float(data.get("amount") or 0),
        currency=parse_currency(str(data.get("currency") or "")),
        buyer_username=str(buyer.get("name") or ""),
        buyer_id=int(buyer_id or 0),
        subcategory_name=node.get("name") or section.get("name") or section.get("title"),
        html="",
        chat_id=_chat_id(chat.get("node_name")),
        amount=amount,
        review=review,
        seller_username=seller.get("name"),
        seller_id=int(seller_id) if seller_id is not None else None,
    )


def _offer_title(fields) -> str:
    if not isinstance(fields, dict):
        return ""
    for item in fields.values():
        if not isinstance(item, dict):
            continue
        value = item.get("value")
        if isinstance(value, str) and value.strip():
            return value.strip()
    return ""
