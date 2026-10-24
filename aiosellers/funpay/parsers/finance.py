from __future__ import annotations

import re
from urllib.parse import parse_qs, urlsplit

from bs4 import BeautifulSoup

from ..core.utils import exchange_rate_pattern, parse_currency, parse_number
from ..exceptions import RequestFailedError
from ..schemas import Balance, Currency, TransactionSnapshot


def _money(text: str) -> tuple[float, Currency]:
    cleaned = (text or "").replace("\xa0", " ")
    currency = Currency.UNKNOWN
    for symbol, kind in (("₽", Currency.RUB), ("$", Currency.USD), ("€", Currency.EUR)):
        if symbol in cleaned:
            currency = kind
            break
    match = re.search(r"-?\d[\d\s]*(?:[.,]\d+)?", cleaned)
    if match is None:
        return 0.0, currency
    return parse_number(match.group(0)), currency


def parse_finance_balance(html: str) -> Balance:
    soup = BeautifulSoup(html, "lxml")
    container = soup.select_one("span.balances-list")
    values = container.select("span.balances-value") if container is not None else []
    if container is None or not values:
        raise RequestFailedError("empty balance", body=html)
    balance = {"rub": 0.0, "usd": 0.0, "eur": 0.0}
    for node in values:
        amount, currency = _money(node.get_text(" ", strip=True))
        if currency is Currency.RUB:
            balance["rub"] = amount
        elif currency is Currency.USD:
            balance["usd"] = amount
        elif currency is Currency.EUR:
            balance["eur"] = amount
    return Balance(**balance)


def parse_offer_balance(html: str) -> Balance:
    soup = BeautifulSoup(html, "lxml")
    select = soup.select_one("select[name=method]")
    if select is None:
        raise RequestFailedError("offer balance missing", body=html)

    def read(name: str) -> float:
        raw = select.get(name)
        if raw in (None, ""):
            return 0.0
        return float(raw)

    return Balance(
        rub=read("data-balance-rub"),
        usd=read("data-balance-usd"),
        eur=read("data-balance-eur"),
        total_rub=read("data-balance-total-rub"),
        total_usd=read("data-balance-total-usd"),
        total_eur=read("data-balance-total-eur"),
    )


def _cursor(soup: BeautifulSoup) -> str | None:
    node = soup.select_one("input[name=continue]")
    if node is None:
        return None
    value = node.get("value") or None
    return value or None


def _tx_status(item) -> str:
    classes = list(item.get("class") or [])
    for child in item.find_all(True):
        classes.extend(child.get("class") or [])
    blob = " ".join(classes)
    if "transaction-status-complete" in blob:
        return "completed"
    if "transaction-status-cancel" in blob:
        return "cancelled"
    if "transaction-status-waiting" in blob:
        return "pending"
    status = item.select_one(".tc-status, .transaction-status")
    text = status.get_text(" ", strip=True) if status is not None else ""
    return text or "unknown"


def _tx_type(description: str) -> str:
    lowered = description.lower()
    if "заказ" in lowered or "order" in lowered:
        return "order"
    if "вывод" in lowered or "withdraw" in lowered:
        return "withdraw"
    if "оплат" in lowered or "пополн" in lowered or "payment" in lowered:
        return "payment"
    return "other"


def _tx_id(item) -> str | None:
    if item.get("data-transaction"):
        return str(item["data-transaction"])
    href = item.get("href") or ""
    if not href:
        anchor = item.find("a")
        href = anchor.get("href") if anchor is not None else ""
    values = parse_qs(urlsplit(href).query).get("id")
    return values[0] if values else None


def parse_transactions(html: str) -> tuple[str | None, list[TransactionSnapshot]]:
    soup = BeautifulSoup(html, "lxml")
    items = soup.select("div.tc-item")
    if not items:
        items = soup.find_all(attrs={"data-transaction": True})
    rows: list[TransactionSnapshot] = []
    for item in items:
        tx_id = _tx_id(item)
        if not tx_id:
            continue
        date_node = item.select_one("span.tc-date-time") or item.select_one("div.tc-date-time")
        title = item.select_one("span.tc-title") or item.select_one("div.tc-title")
        price = item.select_one("div.tc-price") or item.select_one("span.tc-price")
        number = item.select_one("span.tc-payment-number") or item.select_one(
            "div.tc-payment-number"
        )
        description = title.get_text(" ", strip=True) if title is not None else ""
        amount, currency = _money(price.get_text(" ", strip=True) if price is not None else "")
        rows.append(
            TransactionSnapshot(
                id=tx_id,
                type=_tx_type(description),
                amount=amount,
                currency=currency,
                date=date_node.get_text(" ", strip=True) if date_node is not None else "",
                description=description,
                status=_tx_status(item),
                withdrawal_number=number.get_text(" ", strip=True) if number is not None else None,
            )
        )
    return _cursor(soup), rows


def parse_exchange(payload: dict, requested: Currency) -> tuple[float, Currency, bool]:
    """Return rate, account currency, and whether the session currency switched."""
    if "url" in payload and not payload["url"]:
        return 1.0, requested, True
    modal = payload.get("modal") or ""
    text = BeautifulSoup(str(modal), "lxml").select_one("p.lead")
    sentence = text.get_text(" ", strip=True).replace("\xa0", " ") if text is not None else ""
    match = exchange_rate_pattern().search(sentence)
    if match is None:
        raise RequestFailedError("exchange rate missing", body=sentence)
    target = match.group(1).lower()
    if target != requested.code:
        raise RequestFailedError("exchange currency mismatch", body=sentence)
    price1 = parse_number(match.group(2))
    currency1 = parse_currency(match.group(3))
    price2 = parse_number(match.group(4))
    currency2 = parse_currency(match.group(5))
    others = {currency1, currency2} - {requested}
    if len(others) != 1:
        raise RequestFailedError("exchange currencies missing", body=sentence)
    current = others.pop()
    if current is currency1:
        rate = price2 / price1
    else:
        rate = price1 / price2
    return rate, current, False
