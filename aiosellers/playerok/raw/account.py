from __future__ import annotations

from ..core.exceptions import Unauthorized
from ..core.utils import _dig, _raise_on_gql_errors
from ..graphql import GraphQLQuery as GQL
from ..schemas import (
    Account,
    AccountProfile,
    ReviewList,
    ReviewStatuses,
    SortDirections,
    UserProfile,
)
from ..transport import PlayerokTransport


class RawAccountService:
    def __init__(self, transport: PlayerokTransport):
        self._transport = transport

    async def get_me(self) -> Account:
        response = await self._transport.request("post", "graphql", GQL.get_me())
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "viewer"))
        if data is None:
            raise Unauthorized()
        return Account(**data)

    async def get_account(self, username: str | None = None) -> AccountProfile | None:
        if username is None:
            raise ValueError("Can't get account with no username")
        response = await self._transport.request("post", "graphql", GQL.get_user(username=username))
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "user"))
        if data.get("__typename") == "User":
            profile = data
        else:
            return None
        return AccountProfile(**profile)

    async def get_user(
        self, username: str | None = None, id: str | None = None
    ) -> UserProfile | None:
        if username is None and id is None:
            raise ValueError("Can't get user with no username or id")
        response = await self._transport.request(
            "post", "graphql", GQL.get_user(username=username, id=id)
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "user"))
        if data.get("__typename") == "UserFragment":
            profile = data
        elif data.get("__typename") == "User":
            profile = data.get("profile")
        else:
            return None
        return UserProfile(**profile)

    async def get_reviews(
        self,
        user_id: str,
        *,
        count: int = 24,
        after_cursor: str | None = None,
        status: ReviewStatuses | None = ReviewStatuses.APPROVED,
        comment_required: bool = False,
        rating: int | None = None,
        game_id: str | None = None,
        category_id: str | None = None,
        min_item_price: int | None = None,
        max_item_price: int | None = None,
        sort_direction: SortDirections = SortDirections.DESC,
        sort_field: str = "createdAt",
    ) -> ReviewList | None:
        response = await self._transport.request(
            "post",
            "graphql",
            GQL.get_testimonials(
                user_id,
                count=count,
                after_cursor=after_cursor,
                status=status,
                comment_required=comment_required,
                rating=rating,
                game_id=game_id,
                category_id=category_id,
                min_item_price=min_item_price,
                max_item_price=max_item_price,
                sort_direction=sort_direction,
                sort_field=sort_field,
            ),
        )
        raw = response.json()
        _raise_on_gql_errors(raw)
        data = _dig(raw, ("data", "testimonials"))
        if data is None:
            return None
        return ReviewList(**data)
