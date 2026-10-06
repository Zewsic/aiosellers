from __future__ import annotations

from typing import TYPE_CHECKING

from ..entities.user import User
from ..schemas import Account, AccountProfile, Review, ReviewStatuses, SortDirections

if TYPE_CHECKING:
    from ..playerok import Playerok


class AccountAPI:
    def __init__(self, client: Playerok) -> None:
        self._client = client

    async def me(self) -> Account:
        return await self._client._raw.account.get_me()

    async def profile(self) -> AccountProfile:
        me = await self.me()
        return await self._client._raw.account.get_account(me.username)

    async def get_user(
        self,
        user_id: str | None = None,
        *,
        username: str | None = None,
        force_refresh: bool = False,
    ) -> User:
        if user_id is None and username is None:
            raise ValueError("Either user_id or username must be provided")

        if user_id and not force_refresh and self._client._use_identity_map:
            cached = self._client._identity_maps.users.get(user_id)
            if cached:
                return cached

        profile = await self._client._raw.account.get_user(id=user_id, username=username)
        if profile is None:
            if user_id:
                # Create stub user with just ID
                user = User(id=user_id)
            else:
                raise ValueError(f"User with username '{username}' not found")
        else:
            user = User(
                id=profile.id,
                username=profile.username,
                avatar_url=profile.avatar_url,
                role=profile.role,
                is_online=profile.is_online,
                is_blocked=profile.is_blocked,
                rating=profile.rating,
                reviews_count=profile.reviews_count,
            )

        user._client = self._client

        if self._client._use_identity_map:
            self._client._identity_maps.users.set(user.id, user)

        return user

    async def reviews(
        self,
        *,
        limit: int = 24,
        cursor: str | None = None,
        status: ReviewStatuses | None = ReviewStatuses.APPROVED,
        comment_required: bool = False,
        rating: int | None = None,
        game_id: str | None = None,
        category_id: str | None = None,
        min_item_price: int | None = None,
        max_item_price: int | None = None,
        sort_direction: SortDirections = SortDirections.DESC,
        sort_field: str = "createdAt",
    ) -> list[Review]:
        result: list[Review] = []
        remain = limit
        current_cursor = cursor
        while remain > 0:
            response = await self._client._raw.account.get_reviews(
                self._client._me_id,
                count=min(24, remain),
                after_cursor=current_cursor,
                status=status,
                comment_required=comment_required,
                rating=rating,
                game_id=game_id,
                category_id=category_id,
                min_item_price=min_item_price,
                max_item_price=max_item_price,
                sort_direction=sort_direction,
                sort_field=sort_field,
            )
            if response is None or not response.reviews:
                break
            result.extend(response.reviews)
            if len(result) >= limit:
                break
            remain -= len(response.reviews)
            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor
        return result[:limit]
