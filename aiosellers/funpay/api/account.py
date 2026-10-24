from __future__ import annotations

from typing import TYPE_CHECKING

from ..entities.user import User
from ..exceptions import AccountNotInitiatedError

if TYPE_CHECKING:
    from ..funpay import FunPay


class AccountAPI:
    def __init__(self, client: FunPay) -> None:
        self._client = client

    def _require(self):
        if self._client._raw is None or self._client._transport is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        return self._client._raw

    async def me(self) -> User:
        transport = self._client._transport
        if transport is None or transport.account_id is None:
            raise AccountNotInitiatedError("account is not initiated")
        user = User(
            id=transport.account_id,
            username=transport.username,
            active_sales=transport.active_sales,
            active_purchases=transport.active_purchases,
        )
        return self._client.remember("users", user.id, user)

    async def profile(self) -> User:
        if self._client._transport is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        await self._client._transport.refresh_profile(force=True)
        return await self.me()

    async def get_user(self, user_id: int, *, force_refresh: bool = False) -> User:
        if not force_refresh:
            cached = self._client.cached("users", user_id)
            if cached is not None:
                return cached
        snap = await self._require().account.user(user_id)
        user = User(
            id=snap.id,
            username=snap.username,
            avatar_url=snap.avatar_url,
            online=snap.online,
            banned=snap.banned,
        )
        return self._client.remember("users", user.id, user)

    async def buyer_viewing(self, buyer_id: int):
        return await self._require().account.buyer_viewing(buyer_id)
