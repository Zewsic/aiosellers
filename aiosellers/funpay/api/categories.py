from __future__ import annotations

from typing import TYPE_CHECKING

from ..entities.category import Category, SubCategory
from ..schemas import CategorySnapshot, SubCategoryTypes

if TYPE_CHECKING:
    from ..funpay import FunPay


class CategoryAPI:
    def __init__(self, client: FunPay) -> None:
        self._client = client

    def _require(self):
        if self._client._transport is None or self._client._raw is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        return self._client._transport

    def _sub(self, snap, category_id: int) -> SubCategory:
        sub = SubCategory(
            id=snap.id,
            name=snap.name,
            type=snap.type,
            category_id=category_id,
            position=snap.position,
        )
        sub._client = self._client
        return sub

    def _category(self, snap: CategorySnapshot) -> Category:
        category = Category(
            id=snap.id,
            name=snap.name,
            position=snap.position,
            subcategories=[self._sub(sub, snap.id) for sub in snap.subcategories],
        )
        return self._client.remember("categories", snap.id, category)

    async def list(self) -> list[Category]:
        transport = self._require()
        return [self._category(item) for item in transport.categories]

    async def get(self, category_id: int, *, force_refresh: bool = False) -> Category:
        if force_refresh and self._client._transport is not None:
            self._client._transport.categories = []
            await self._client._transport.refresh_profile(force=True)
        elif not force_refresh:
            cached = self._client.cached("categories", category_id)
            if cached is not None:
                return cached
        for item in await self.list():
            if item.id == category_id:
                return item
        raise ValueError(f"Unknown category: {category_id}")

    async def subcategory(self, kind: SubCategoryTypes, subcategory_id: int) -> SubCategory:
        for category in await self.list():
            for sub in category.subcategories:
                if sub.id == subcategory_id and sub.type is kind:
                    return sub
        raise ValueError(f"Unknown subcategory: {subcategory_id}")

    async def search(self, query: str) -> list[Category]:
        self._require()
        rows = await self._client._raw.lots.search(query)  # type: ignore[union-attr]
        return [self._category(item) for item in rows]
