from __future__ import annotations

import json
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from ..core.utils import parse_currency, parse_price
from ..exceptions import LotParsingError
from ..schemas import Currency, LotShortcut, MyLotShortcut, SubCategoryTypes


def _query_id(href: str) -> str | None:
    query = urlsplit(href).query
    if not query and "?" in href:
        query = href.split("?", 1)[1]
    values = parse_qs(query).get("id")
    return values[0] if values else None


def _server(row) -> str | None:
    node = row.select_one("div.tc-server.hidden-xxs") or row.select_one("div.tc-server.hidden-xs")
    if node is None:
        return None
    text = node.get_text(" ", strip=True)
    return text or None


def _auto(row) -> bool:
    classes = row.get("class") or []
    return row.select_one("span.auto-delivery") is not None or "has-auto-delivery" in classes


def _seller(row) -> tuple[int | None, str | None]:
    span = row.select_one("span.pseudo-a[data-href]")
    if span is None:
        return None, None
    parts = (span.get("data-href") or "").split("/")
    seller_id = int(parts[-2]) if len(parts) >= 2 and parts[-2].isdigit() else None
    name_node = row.select_one("div.media-user-name")
    username = name_node.get_text(" ", strip=True) if name_node is not None else None
    return seller_id, username or None


def _price(row, kind: SubCategoryTypes) -> float:
    node = row.select_one("div.tc-price")
    if node is None:
        return 0.0
    if kind is SubCategoryTypes.COMMON and node.get("data-s") not in (None, ""):
        return float(node["data-s"])
    inner = node.select_one("div")
    if kind is SubCategoryTypes.CURRENCY and inner is not None:
        token = inner.get_text(" ", strip=True).split()
        return float(token[0].replace(",", ".")) if token else 0.0
    amount, _currency = parse_price(node.get_text(" ", strip=True))
    return amount


def parse_public_lots(
    html: str, *, subcategory_id: int, kind: SubCategoryTypes
) -> list[LotShortcut]:
    soup = BeautifulSoup(html, "lxml")
    lots: list[LotShortcut] = []
    for row in soup.select("a.tc-item"):
        desc = row.select_one("div.tc-desc-text")
        seller_id, seller_name = _seller(row)
        lots.append(
            LotShortcut(
                id=_query_id(row.get("href") or "") or "",
                server=_server(row),
                description=desc.get_text(" ", strip=True) if desc is not None else None,
                price=_price(row, kind),
                subcategory_id=subcategory_id,
                seller_id=seller_id,
                seller_username=seller_name,
                auto_delivery=_auto(row),
                html=str(row),
            )
        )
    return lots


def _amount(row) -> int | None:
    node = row.select_one("div.tc-amount")
    if node is None:
        return None
    digits = "".join(ch for ch in node.get_text() if ch.isdigit())
    return int(digits) if digits else None


def parse_my_lots(html: str, *, subcategory_id: int) -> list[MyLotShortcut]:
    soup = BeautifulSoup(html, "lxml")
    lots: list[MyLotShortcut] = []
    for row in soup.select("a.tc-item"):
        classes = row.get("class") or []
        desc = row.select_one("div.tc-desc-text")
        price_node = row.select_one("div.tc-price")
        price = None
        if price_node is not None and price_node.get("data-s") not in (None, ""):
            price = float(price_node["data-s"])
        elif price_node is not None:
            price = parse_price(price_node.get_text(" ", strip=True))[0]
        lots.append(
            MyLotShortcut(
                id=_query_id(row.get("href") or "") or "",
                description=desc.get_text(" ", strip=True) if desc is not None else None,
                price=price,
                active="warning" not in classes and "deleted" not in classes,
                auto_delivery=_auto(row),
                amount=_amount(row),
                server=_server(row),
                subcategory_id=subcategory_id,
                html=str(row),
            )
        )
    return lots


def _collect_fields(form) -> dict[str, str]:
    fields: dict[str, str] = {}
    for node in form.select("input"):
        name = node.get("name")
        if not name:
            continue
        if (node.get("type") or "").lower() == "checkbox":
            if node.has_attr("checked"):
                fields[name] = node.get("value") or "on"
            continue
        fields[name] = node.get("value") or ""
    for node in form.select("textarea"):
        name = node.get("name")
        if name:
            fields[name] = node.get_text() or ""
    for node in form.select("select"):
        name = node.get("name")
        if not name:
            continue
        selected = node.find("option", selected=True)
        fields[name] = (selected.get("value") if selected is not None else "") or ""
    return fields


def _apply_data_offer(form, fields: dict[str, str]) -> None:
    raw = form.get("data-offer")
    if not raw:
        return
    try:
        payload = json.loads(raw)
    except json.JSONDecodeError:
        return
    if not isinstance(payload, dict) or payload.get("amount") in (None, ""):
        return
    keys = [key for key in fields if key == "amount" or key.endswith("[amount]")]
    target = keys[0] if keys else "amount"
    if not fields.get(target):
        fields[target] = str(payload["amount"])


def parse_offer_form(html: str, lot_id: int) -> tuple[dict[str, str], Currency]:
    soup = BeautifulSoup(html, "lxml")
    alert = soup.select_one("div.alert-danger")
    form = soup.select_one("form.form-offer-editor")
    if form is None or alert is not None:
        message = alert.get_text(" ", strip=True) if alert is not None else "offer form missing"
        raise LotParsingError(message, lot_id=lot_id, body=html)
    fields = _collect_fields(form)
    _apply_data_offer(form, fields)
    feedback = form.select_one("span.form-control-feedback")
    currency = parse_currency(feedback.get_text(strip=True) if feedback is not None else "")
    return fields, currency


def parse_chip_form(html: str, subcategory_id: int) -> dict[str, str]:
    soup = BeautifulSoup(html, "lxml")
    form = soup.find("form")
    if form is None:
        raise LotParsingError("chip form missing", lot_id=subcategory_id, body=html)
    return _collect_fields(form)
