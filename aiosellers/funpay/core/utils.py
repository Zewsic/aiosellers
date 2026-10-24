from __future__ import annotations

import re
import secrets

from ..schemas.enums import Currency, MessageTypes
from .constants import BOT_MARK, IMAGE_PLACEHOLDERS, OLD_BOT_MARK

_INVISIBLE = frozenset("\u200b\u200c\u200d\u2060\ufeff")

_USER = r"[A-Za-z0-9]+"
_ORDER = r"#[A-Z0-9]{8}\s*"
_ORDER_ID = re.compile(r"#([A-Z0-9]{8})")

_PURCHASED_1 = re.compile(
    rf"(?:Покупатель {_USER} оплатил заказ {_ORDER}\."
    rf"|The buyer {_USER} has paid for order {_ORDER}\.)"
)
_PURCHASED_2 = re.compile(
    rf"(?:{_USER}, не забудьте потом нажать кнопку "
    rf"«Подтвердить (?:выполнение заказа|получение валюты)»\."
    rf"|{_USER}, do not forget to press the "
    rf"«Confirm (?:order fulfilment|currency receipt)» button once you finish\.)"
)
_CONFIRMED = re.compile(
    rf"(?:Покупатель {_USER} подтвердил успешное выполнение заказа {_ORDER} "
    rf"и отправил деньги продавцу {_USER}\."
    rf"|The buyer {_USER} has confirmed that order {_ORDER} has been fulfilled "
    rf"successfully and that the seller {_USER} has been paid\.)"
)
_NEW_FEEDBACK = re.compile(
    rf"(?:Покупатель {_USER} написал отзыв к заказу {_ORDER}\."
    rf"|The buyer {_USER} has given feedback to the order {_ORDER}\.)"
)
_NEW_ANSWER = re.compile(
    rf"(?:Продавец {_USER} ответил на отзыв к заказу {_ORDER}\."
    rf"|The seller {_USER} has replied to their feedback to the order {_ORDER}\.)"
)
_REOPENED = re.compile(rf"(?:Заказ {_ORDER} открыт повторно\.|Order {_ORDER} has been reopened\.)")
_REFUND = re.compile(
    rf"(?:Продавец {_USER} вернул деньги покупателю {_USER} по заказу {_ORDER}\."
    rf"|The seller {_USER} has refunded the buyer {_USER} on order {_ORDER}\.)"
)
_ADMIN_REFUND = re.compile(
    rf"(?:Администратор {_USER} вернул деньги покупателю {_USER} по заказу {_ORDER}\."
    rf"|The administrator {_USER} has refunded the buyer {_USER} on order {_ORDER}\.)"
)
_PARTIAL = re.compile(
    rf"(?:Часть средств по заказу {_ORDER} возвращена покупателю\."
    rf"|A part of the funds pertaining to the order {_ORDER} has been refunded\.)"
)
_ADMIN_CONFIRM = re.compile(
    rf"(?:Администратор {_USER} подтвердил успешное выполнение заказа {_ORDER} "
    rf"и отправил деньги продавцу {_USER}\."
    rf"|The administrator {_USER} has confirmed that order {_ORDER} has been fulfilled "
    rf"successfully and that the seller {_USER} has been paid\.)"
)
_DISCORD = (
    "Вы можете перейти в Discord. Внимание: общение за пределами сервера FunPay "
    "считается нарушением правил.",
    "You can switch to Discord. However, note that friending someone is considered a violation rules.",
)
_VENDORS = (
    "Уважаемые продавцы, не доверяйте сообщениям в чате! Перед выполнением заказа "
    "всегда проверяйте наличие оплаты в разделе «Мои продажи».",
    "Dear vendors, do not rely on chat messages! Before you process an order, you should "
    "always check whether you've been paid in «My sales» section.",
)

_EXCHANGE = re.compile(
    r"(?:You will receive payment in|Вы начнёте получать оплату в|Ви почнете одержувати оплату в)"
    r"\s*(USD|RUB|EUR)\..*?"
    r"([\d][\d\s\u00a0.,]*)\s*([₽€$])\s*(?:за|for)\s*([\d][\d\s\u00a0.,]*)\s*([₽€$])",
    re.IGNORECASE | re.DOTALL,
)


def strip_invisible_suffix(text: str) -> str:
    if not text:
        return text
    end = len(text)
    while end > 0 and text[end - 1] in _INVISIBLE:
        end -= 1
    if end < len(text) and end > 0 and text[end - 1] == " ":
        end -= 1
    return text[:end]


def strip_bot_mark(text: str, author_is_self: bool) -> tuple[str, bool]:
    if text.startswith(BOT_MARK):
        return text[len(BOT_MARK) :], True
    if text.startswith(OLD_BOT_MARK) and author_is_self:
        return text[len(OLD_BOT_MARK) :], True
    return text, False


def random_tag() -> str:
    return secrets.token_hex(4)


def parse_currency(token: str) -> Currency:
    cleaned = (token or "").strip().lower()
    if cleaned in {"$", "usd"}:
        return Currency.USD
    if cleaned in {"₽", "rub"}:
        return Currency.RUB
    if cleaned in {"€", "eur"}:
        return Currency.EUR
    return Currency.UNKNOWN


def order_id_from(text: str | None) -> str | None:
    if not text:
        return None
    match = _ORDER_ID.search(text)
    return match.group(1) if match else None


def classify_message(text: str | None) -> MessageTypes:
    if not text:
        return MessageTypes.NON_SYSTEM
    text = " ".join(text.split())
    if not text or text in IMAGE_PLACEHOLDERS:
        return MessageTypes.NON_SYSTEM
    if any(phrase in text for phrase in _DISCORD):
        return MessageTypes.DISCORD
    if any(phrase in text for phrase in _VENDORS):
        return MessageTypes.DEAR_VENDORS
    if _ORDER_ID.search(text) is None:
        return MessageTypes.NON_SYSTEM
    if _PURCHASED_1.search(text) and _PURCHASED_2.search(text):
        return MessageTypes.ORDER_PURCHASED
    ordered: tuple[tuple[re.Pattern[str] | tuple[str, ...], MessageTypes], ...] = (
        (_CONFIRMED, MessageTypes.ORDER_CONFIRMED),
        (_NEW_FEEDBACK, MessageTypes.NEW_FEEDBACK),
        (_NEW_ANSWER, MessageTypes.NEW_FEEDBACK_ANSWER),
        (
            ("изменил отзыв к заказу", "has edited their feedback to the order"),
            MessageTypes.FEEDBACK_CHANGED,
        ),
        (
            ("удалил отзыв к заказу", "has deleted their feedback to the order"),
            MessageTypes.FEEDBACK_DELETED,
        ),
        (_REFUND, MessageTypes.REFUND),
        (
            (
                "изменил ответ на отзыв к заказу",
                "has edited a reply to their feedback to the order",
            ),
            MessageTypes.FEEDBACK_ANSWER_CHANGED,
        ),
        (
            (
                "удалил ответ на отзыв к заказу",
                "has deleted a reply to their feedback to the order",
            ),
            MessageTypes.FEEDBACK_ANSWER_DELETED,
        ),
        (_ADMIN_CONFIRM, MessageTypes.ORDER_CONFIRMED_BY_ADMIN),
        (_PARTIAL, MessageTypes.PARTIAL_REFUND),
        (_REOPENED, MessageTypes.ORDER_REOPENED),
        (_ADMIN_REFUND, MessageTypes.REFUND_BY_ADMIN),
    )
    for probe, kind in ordered:
        if isinstance(probe, tuple):
            if any(phrase in text for phrase in probe):
                return kind
        elif probe.search(text):
            return kind
    return MessageTypes.NON_SYSTEM


def parse_price(text: str) -> tuple[float, Currency]:
    cleaned = (text or "").replace("\xa0", " ").strip()
    cleaned = re.sub(r"\s+", " ", cleaned)
    if " " in cleaned:
        amount_text, token = cleaned.rsplit(" ", 1)
    else:
        match = re.match(r"^(.*?)([₽$€¤])$", cleaned)
        if match:
            amount_text, token = match.group(1), match.group(2)
        else:
            amount_text, token = cleaned, ""
    amount_text = amount_text.replace(" ", "").replace(",", ".")
    try:
        amount = float(amount_text) if amount_text else 0.0
    except ValueError:
        amount = 0.0
    return amount, parse_currency(token)


def parse_number(text: str) -> float:
    cleaned = (text or "").replace("\xa0", "").replace(" ", "")
    if cleaned.count(",") == 1 and "." not in cleaned:
        cleaned = cleaned.replace(",", ".")
    elif "," in cleaned and "." in cleaned:
        cleaned = cleaned.replace(",", "")
    return float(cleaned)


def sniff_image(content: bytes) -> str:
    if content.startswith(b"\x89PNG"):
        return "image/png"
    if content.startswith(b"\xff\xd8\xff"):
        return "image/jpeg"
    if content.startswith(b"GIF8"):
        return "image/gif"
    if content.startswith(b"RIFF") and b"WEBP" in content[:16]:
        return "image/webp"
    return "image/png"


def exchange_rate_pattern() -> re.Pattern[str]:
    return _EXCHANGE


def format_form_number(value: float) -> str:
    number = float(value)
    if number.is_integer():
        return str(int(number))
    return str(number)
