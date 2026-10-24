from __future__ import annotations

from bs4 import BeautifulSoup

from ..core.constants import IMAGE_PLACEHOLDERS
from ..core.utils import classify_message, strip_bot_mark, strip_invisible_suffix
from ..schemas import ChatShortcut, MessageSnapshot, MessageTypes

_SUPPORT = frozenset({"поддержка", "підтримка", "support"})
_MODERATION = frozenset({"модерация", "модерація", "moderation"})
_ARBITRATION = frozenset({"арбитраж", "арбітраж", "arbitration"})
_AUTO = frozenset({"автоответ", "автовідповідь", "auto-reply"})


def parse_bookmarks(html: str, *, self_id: int) -> list[ChatShortcut]:
    del self_id
    soup = BeautifulSoup(html, "lxml")
    chats: list[ChatShortcut] = []
    for anchor in soup.select("a.contact-item"):
        if anchor.select_one("div.contact-item-message") is None:
            continue
        preview_node = anchor.select_one("div.contact-item-message")
        preview = preview_node.get_text(" ", strip=True) if preview_node is not None else ""
        if preview in IMAGE_PLACEHOLDERS:
            text = preview
            last_by_bot = False
        else:
            text, last_by_bot = strip_bot_mark(preview, author_is_self=False)
        name_node = anchor.select_one("div.media-user-name")
        classes = anchor.get("class") or []
        chats.append(
            ChatShortcut(
                id=int(anchor.get("data-id") or 0),
                name=name_node.get_text(" ", strip=True) if name_node is not None else "",
                last_message_text=text,
                node_message_id=int(anchor.get("data-node-msg") or 0),
                user_message_id=int(anchor.get("data-user-msg") or 0),
                unread="unread" in classes,
                last_by_bot=last_by_bot,
                html=str(anchor),
            )
        )
    return chats


def _author_name(
    author: int,
    soup: BeautifulSoup,
    *,
    self_id: int,
    self_username: str | None,
    interlocutor_id: int | None,
    interlocutor_name: str | None,
) -> str | None:
    if author == 0:
        return "FunPay"
    block = soup.select_one("div.media-user-name a")
    if block is not None and block.get_text(strip=True):
        return block.get_text(strip=True)
    if author == self_id:
        return self_username
    if interlocutor_id is not None and author == interlocutor_id:
        return interlocutor_name
    return interlocutor_name


def parse_history(
    messages_json,
    chat_id: int | str,
    *,
    self_id: int,
    self_username: str | None,
    interlocutor_id: int | None,
    interlocutor_name: str | None,
) -> list[MessageSnapshot]:
    items = messages_json
    if isinstance(messages_json, dict):
        chat = messages_json.get("chat") or {}
        items = chat.get("messages") or messages_json.get("messages") or []
    result: list[MessageSnapshot] = []
    for item in items or []:
        author = int(item.get("author") or 0)
        html = item.get("html") or ""
        soup = BeautifulSoup(html.replace("<br>", "\n"), "lxml")
        image_link = None
        image_name = None
        image = soup.select_one("a.chat-img-link")
        if image is not None:
            image_link = image.get("href")
            img = image.select_one("img") or soup.select_one("img")
            image_name = img.get("alt") if img is not None else None
            text = None
            by_bot = False
        else:
            if author == 0:
                alert = soup.select_one("div[role=alert]")
                source = alert if alert is not None else soup
                text = source.get_text("\n", strip=True) or None
            else:
                body = soup.select_one("div.chat-msg-text")
                text = body.get_text("\n", strip=True) if body is not None else None
            if text:
                text = strip_invisible_suffix(text)
                if author == self_id:
                    text, by_bot = strip_bot_mark(text, author_is_self=True)
                else:
                    by_bot = False
            else:
                by_bot = False
        if image_name and (
            "funpay_cardinal" in image_name.lower() or image_name == "funpay_vertex_image.png"
        ):
            by_bot = True
        label = soup.select_one("span.chat-msg-author-label.label-success")
        badge = label.get_text(strip=True) if label is not None else None
        badge_key = badge.lower() if badge else ""
        auto = soup.select_one("span.chat-msg-author-label.label-default")
        auto_text = auto.get_text(strip=True).lower() if auto is not None else ""
        result.append(
            MessageSnapshot(
                id=int(item.get("id") or 0),
                text=text,
                chat_id=chat_id,
                chat_name=interlocutor_name,
                author=_author_name(
                    author,
                    soup,
                    self_id=self_id,
                    self_username=self_username,
                    interlocutor_id=interlocutor_id,
                    interlocutor_name=interlocutor_name,
                ),
                author_id=author,
                interlocutor_id=interlocutor_id,
                image_link=image_link,
                image_name=image_name,
                type=MessageTypes.NON_SYSTEM if author != 0 else classify_message(text),
                by_bot=by_bot,
                badge=badge,
                is_support=badge_key in _SUPPORT,
                is_moderation=badge_key in _MODERATION,
                is_arbitration=badge_key in _ARBITRATION,
                is_auto_reply=auto_text in _AUTO,
                html=html,
            )
        )
    return result
