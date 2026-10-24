from __future__ import annotations

import json
import re

from bs4 import BeautifulSoup

from ..schemas import (
    AccountSnapshot,
    BuyerViewing,
    CategorySnapshot,
    SubCategorySnapshot,
    SubCategoryTypes,
    UserSnapshot,
)


def _text(node) -> str:
    if node is None:
        return ""
    return node.get_text(" ", strip=True)


def _subcategory(anchor, category_id: int, position: int) -> SubCategorySnapshot | None:
    href = anchor.get("href") or ""
    parts = [part for part in href.split("/") if part]
    if len(parts) < 2:
        return None
    raw_id = parts[-1] if parts[-1].isdigit() else parts[-2]
    if not str(raw_id).isdigit():
        return None
    kind = SubCategoryTypes.CURRENCY if "chips" in href else SubCategoryTypes.COMMON
    return SubCategorySnapshot(
        id=int(raw_id),
        name=_text(anchor),
        type=kind,
        category_id=category_id,
        position=position,
    )


def parse_categories(html: str) -> list[CategorySnapshot]:
    soup = BeautifulSoup(html, "lxml")
    lists = soup.select("div.promo-game-list")
    if not lists:
        return []
    container = lists[1] if len(lists) >= 2 else lists[0]
    categories: list[CategorySnapshot] = []
    position = 0
    for item in container.select("div.promo-game-item"):
        title = item.select_one("div.game-title")
        game_raw = title.get("data-id") if title is not None else None
        game_id = int(game_raw) if game_raw and str(game_raw).isdigit() else 0
        game_name = _text(item.select_one("a"))
        grouped: dict[str, list[SubCategorySnapshot]] = {}
        for ul in item.select("ul.list-inline"):
            owner = ul.get("data-id") or str(game_id)
            owner_id = int(owner) if str(owner).isdigit() else game_id
            bucket = grouped.setdefault(str(owner_id), [])
            for anchor in ul.select("li a"):
                sub = _subcategory(anchor, owner_id, len(bucket))
                if sub is not None:
                    bucket.append(sub)
        categories.append(
            CategorySnapshot(
                id=game_id,
                name=game_name,
                position=position,
                subcategories=grouped.get(str(game_id), []),
            )
        )
        position += 1
        group = item.select_one("div[role=group]")
        if group is None:
            continue
        for button in group.select("button[data-id]"):
            raw = button.get("data-id")
            if not raw or not str(raw).isdigit():
                continue
            button_id = int(raw)
            categories.append(
                CategorySnapshot(
                    id=button_id,
                    name=f"{game_name} ({_text(button)})",
                    position=position,
                    subcategories=grouped.get(str(button_id), []),
                )
            )
            position += 1
    return categories


def parse_home(html: str) -> AccountSnapshot:
    soup = BeautifulSoup(html, "lxml")
    username = _text(soup.select_one("div.user-link-name"))
    body = soup.find("body")
    app: dict = {}
    if body is not None and body.get("data-app-data"):
        try:
            loaded = json.loads(body["data-app-data"])
        except json.JSONDecodeError:
            loaded = {}
        if isinstance(loaded, dict):
            app = loaded
    user_raw = app.get("userId") or 0
    sales = soup.select_one("span.badge.badge-trade")
    purchases = soup.select_one("span.badge.badge-orders")
    return AccountSnapshot(
        id=int(user_raw or 0),
        username=username,
        csrf_token=str(app.get("csrf-token") or ""),
        locale=app.get("locale"),
        active_sales=int(sales.get_text(strip=True)) if sales and sales.get_text(strip=True) else 0,
        active_purchases=(
            int(purchases.get_text(strip=True))
            if purchases and purchases.get_text(strip=True)
            else 0
        ),
        categories=parse_categories(html),
    )


def parse_user(html: str, user_id: int) -> UserSnapshot:
    soup = BeautifulSoup(html, "lxml")
    username = _text(soup.select_one("div.user-link-name")) or _text(soup.find("h1"))
    avatar = None
    photo = soup.select_one("div.avatar-photo")
    if photo is not None:
        match = re.search(r"url\(([^)]+)\)", photo.get("style") or "")
        if match:
            avatar = match.group(1).strip("\"'")
            if avatar.startswith("//"):
                avatar = "https:" + avatar
            elif avatar.startswith("/"):
                avatar = "https://funpay.com" + avatar
    status = soup.select_one(".media-user-status, .user-status, .online-status")
    status_text = _text(status)
    online = "Онлайн" in status_text or "Online" in status_text
    banned = soup.select_one("span.label.label-danger") is not None
    return UserSnapshot(
        id=user_id,
        username=username,
        avatar_url=avatar,
        online=online,
        banned=banned,
    )


def parse_buyer_viewing(obj: dict, buyer_id: int) -> BuyerViewing:
    data = obj.get("data")
    if not isinstance(data, dict) or not data:
        return BuyerViewing(buyer_id=buyer_id)
    lot_id = None
    if "node" in data and data["node"] not in (None, "", False):
        try:
            lot_id = int(data["node"])
        except (TypeError, ValueError):
            lot_id = None
    elif "tag" in data and data["tag"] not in (None, "", False):
        try:
            lot_id = int(data["tag"])
        except (TypeError, ValueError):
            lot_id = None
    lot_text = None
    if "html" in data and data["html"]:
        lot_text = BeautifulSoup(str(data["html"]), "lxml").get_text(" ", strip=True) or None
    return BuyerViewing(buyer_id=buyer_id, lot_id=lot_id, lot_text=lot_text)
