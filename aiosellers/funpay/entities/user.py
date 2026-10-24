from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..funpay import FunPay
    from .chat import Chat


def _detached(owner: str, hint: str) -> RuntimeError:
    return RuntimeError(
        f"{owner} is not attached to a client. Use {hint} to fetch an active instance."
    )


@dataclass(slots=True)
class User:
    id: int
    username: str | None = None
    avatar_url: str | None = None
    online: bool = False
    banned: bool = False
    active_sales: int | None = None
    active_purchases: int | None = None
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.account.get_user()")
        return self._client

    async def refresh(self) -> User:
        return await self._require_client().account.get_user(self.id, force_refresh=True)

    async def get_chat(self) -> Chat | None:
        if not self.username:
            return None
        return await self._require_client().chats.get_by_name(self.username, fetch=True)
