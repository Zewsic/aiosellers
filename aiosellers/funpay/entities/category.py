from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..schemas import SubCategoryTypes
from .user import _detached

if TYPE_CHECKING:
    from ..funpay import FunPay
    from .lot import Lot, MyLot


@dataclass(slots=True)
class SubCategory:
    id: int
    name: str
    type: SubCategoryTypes
    category_id: int
    position: int = 0
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.categories.subcategory()")
        return self._client

    async def list_public(self) -> list[Lot]:
        return await self._require_client().lots.list_public(self.id, kind=self.type)

    async def list_self(self) -> list[MyLot]:
        return await self._require_client().lots.list_self(self.id)


@dataclass(slots=True)
class Category:
    id: int
    name: str
    position: int = 0
    subcategories: list[SubCategory] = field(default_factory=list)
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.categories.get()")
        return self._client

    async def raise_lots(self) -> int:
        return await self._require_client().lots.raise_category(self.id)
