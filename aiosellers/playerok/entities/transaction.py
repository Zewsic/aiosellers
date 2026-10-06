from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import TYPE_CHECKING

from ..schemas.enums import (
    TransactionDirections,
    TransactionOperations,
    TransactionProviderIds,
    TransactionStatuses,
)

if TYPE_CHECKING:  # pragma: no cover
    from ..playerok import Playerok


@dataclass(slots=True)
class Transaction:
    id: str
    status: TransactionStatuses | None = None
    operation: TransactionOperations | None = None
    direction: TransactionDirections | None = None
    value: float | None = None
    provider_id: TransactionProviderIds | None = None
    created_at: datetime | None = None

    _client: Playerok | None = field(default=None, repr=False, init=False, compare=False)

    def _require_client(self) -> Playerok:
        if self._client is None:
            raise RuntimeError(
                f"{self.__class__.__name__} is not attached to a client. "
                f"Use client.transactions.list() to fetch an active instance."
            )
        return self._client

    async def cancel(self) -> Transaction:
        return await self._require_client().transactions.cancel(self.id)
