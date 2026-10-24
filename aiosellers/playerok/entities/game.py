from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, AsyncIterator

from ..schemas import (
    GameCategoryAgreementIconTypes,
    GameCategoryDataFieldInputTypes,
    GameCategoryDataFieldTypes,
    GameCategoryOptionTypes,
    GameType,
    ItemsSortOptions,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..playerok import Playerok
    from .file import File
    from .item import Item


@dataclass(slots=True)
class OptionValue:
    name: str
    value: str

    _option: "GameCategoryOption" | None = field(default=None, repr=False, compare=False)

    def select(self) -> "GameCategoryOption":
        if self._option:
            return self._option.set_value(self)
        raise RuntimeError("OptionValue is not attached to an option")


@dataclass(slots=True)
class GameCategoryOption:
    id: str
    type: GameCategoryOptionTypes
    group_name: str
    slug: str
    possible_values: list[OptionValue]
    category_id: str | None = None

    _input_value: int | str | bool | None = None
    _client: Playerok | None = field(default=None, repr=False, init=False, compare=False)

    def set_value(self, value: int | str | bool | OptionValue | None) -> "GameCategoryOption":
        if hasattr(value, "value"):  # Handle OptionValue
            val = value.value
        else:
            val = str(value).lower() if value is not None else None

        self._input_value = val
        return self


@dataclass(slots=True)
class GameCategoryDataField:
    id: str
    type: GameCategoryDataFieldTypes
    input_type: GameCategoryDataFieldInputTypes
    name: str
    required: bool

    _input_value: str | None = None

    def set_value(self, value: str) -> "GameCategoryDataField":
        self._input_value = value
        return self


@dataclass(slots=True)
class GameCategoryAgreement:
    id: str
    description: str
    type: GameCategoryAgreementIconTypes

    category_id: str | None = None
    obtaining_type_id: str | None = None

    _client: Playerok | None = field(default=None, repr=False, init=False, compare=False)

    def _require_client(self) -> Playerok:
        if self._client is None:
            raise RuntimeError("Entity not attached to client")
        return self._client

    async def accept(self, *, skip_waiting: bool = False) -> bool:
        result = await self._require_client().games.accept_agreement(self.id)
        if result and not skip_waiting:
            await asyncio.sleep(0.2)
        return result


@dataclass(slots=True)
class GameCategoryInstruction:
    id: str
    text: str

    category_id: str | None = None
    obtaining_type_id: str | None = None

    _client: Playerok | None = field(default=None, repr=False, init=False, compare=False)


@dataclass(slots=True)
class GameCategoryObtainingType:
    id: str
    name: str
    description: str

    category_id: str | None = None

    _client: Playerok | None = field(default=None, repr=False, init=False, compare=False)

    def _require_client(self) -> Playerok:
        if self._client is None:
            raise RuntimeError("Entity not attached to client")
        return self._client

    async def get_instructions(self, limit: int = 24) -> list[GameCategoryInstruction]:
        if not self.category_id:
            raise ValueError("Category ID missing")
        return await self._require_client().games.get_instructions(
            self.category_id, self.id, limit=limit
        )

    async def get_data_fields(self) -> list[GameCategoryDataField]:
        if not self.category_id:
            raise ValueError("Category ID missing")
        return await self._require_client().games.get_data_fields(self.category_id, self.id)

    async def get_agreements(self, limit: int = 24) -> list[GameCategoryAgreement]:
        if not self.category_id:
            raise ValueError("Category ID missing")
        return await self._require_client().games.get_agreements(
            self.category_id, obtaining_type_id=self.id, limit=limit
        )


@dataclass(slots=True)
class GameCategory:
    id: str
    name: str
    slug: str

    game: "Game" | None = field(repr=False, default=None)
    game_id: str | None = None

    _client: Playerok | None = field(default=None, repr=False, init=False, compare=False)

    def _require_client(self) -> Playerok:
        if self._client is None:
            raise RuntimeError("Entity not attached to client")
        return self._client

    async def get_agreements(self, limit: int = 24) -> list[GameCategoryAgreement]:
        return await self._require_client().games.get_agreements(self.id, limit=limit)

    async def get_obtaining_types(self, limit: int = 24) -> list[GameCategoryObtainingType]:
        return await self._require_client().games.get_obtaining_types(self.id, limit=limit)

    async def get_options(self) -> list[GameCategoryOption]:
        return await self._require_client().games.get_category_options(self.id)

    async def get_items(
        self,
        *,
        limit: int = 24,
        cursor: str | None = None,
        user_id: str | None = None,
        minimal_price: int | None = None,
        maximal_price: int | None = None,
        has_discount: bool | None = None,
        has_reviews: bool | None = None,
        attributes: list[dict[str, str]] | None = None,
        search: str | None = None,
        sort: ItemsSortOptions | None = None,
    ) -> list["Item"]:
        return await self._require_client().items.list(
            limit=limit,
            cursor=cursor,
            game_id=self.game_id,
            category_id=self.id,
            user_id=user_id,
            minimal_price=minimal_price,
            maximal_price=maximal_price,
            has_discount=has_discount,
            has_reviews=has_reviews,
            attributes=attributes,
            search=search,
            sort=sort,
        )

    async def iter_items(
        self,
        *,
        cursor: str | None = None,
        user_id: str | None = None,
        minimal_price: int | None = None,
        maximal_price: int | None = None,
        has_discount: bool | None = None,
        has_reviews: bool | None = None,
        attributes: list[dict[str, str]] | None = None,
        search: str | None = None,
        sort: ItemsSortOptions | None = None,
    ) -> AsyncIterator["Item"]:
        async for item in self._require_client().items.iter(
            cursor=cursor,
            game_id=self.game_id,
            category_id=self.id,
            user_id=user_id,
            minimal_price=minimal_price,
            maximal_price=maximal_price,
            has_discount=has_discount,
            has_reviews=has_reviews,
            attributes=attributes,
            search=search,
            sort=sort,
        ):
            yield item


@dataclass(slots=True)
class Game:
    id: str
    name: str
    slug: str
    categories: list[GameCategory]
    type: GameType = GameType.GAME
    logo: File | None = None

    _client: Playerok | None = field(default=None, repr=False, init=False, compare=False)

    def _require_client(self) -> Playerok:
        if self._client is None:
            raise RuntimeError(
                f"{self.__class__.__name__} is not attached to a client. "
                f"Use client.games.get() to fetch an active instance."
            )
        return self._client

    async def refresh(self) -> "Game":
        return await self._require_client().games.get(id=self.id, force_refresh=True)

    async def get_category(
        self, *, id: str | None = None, slug: str | None = None
    ) -> GameCategory | None:
        if id:
            for category in self.categories:
                if category.id == id:
                    return category
        elif slug:
            for category in self.categories:
                if category.slug == slug:
                    return category

        return await self._require_client().games.get_category(id=id, slug=slug, game_id=self.id)

    async def get_items(
        self,
        *,
        limit: int = 24,
        cursor: str | None = None,
        category_id: str | None = None,
        user_id: str | None = None,
        minimal_price: int | None = None,
        maximal_price: int | None = None,
        has_discount: bool | None = None,
        has_reviews: bool | None = None,
        attributes: list[dict[str, str]] | None = None,
        search: str | None = None,
        sort: ItemsSortOptions | None = None,
    ) -> list["Item"]:
        return await self._require_client().items.list(
            limit=limit,
            cursor=cursor,
            game_id=self.id,
            category_id=category_id,
            user_id=user_id,
            minimal_price=minimal_price,
            maximal_price=maximal_price,
            has_discount=has_discount,
            has_reviews=has_reviews,
            attributes=attributes,
            search=search,
            sort=sort,
        )

    async def iter_items(
        self,
        *,
        cursor: str | None = None,
        category_id: str | None = None,
        user_id: str | None = None,
        minimal_price: int | None = None,
        maximal_price: int | None = None,
        has_discount: bool | None = None,
        has_reviews: bool | None = None,
        attributes: list[dict[str, str]] | None = None,
        search: str | None = None,
        sort: ItemsSortOptions | None = None,
    ) -> AsyncIterator["Item"]:
        async for item in self._require_client().items.iter(
            cursor=cursor,
            game_id=self.id,
            category_id=category_id,
            user_id=user_id,
            minimal_price=minimal_price,
            maximal_price=maximal_price,
            has_discount=has_discount,
            has_reviews=has_reviews,
            attributes=attributes,
            search=search,
            sort=sort,
        ):
            yield item
