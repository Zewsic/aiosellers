from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from ..entities.transaction import Transaction
from ..exceptions import AccountNotInitiatedError
from ..schemas import Balance, Currency, TransactionSnapshot, Wallet

if TYPE_CHECKING:
    from ..funpay import FunPay


class FinanceAPI:
    def __init__(self, client: FunPay) -> None:
        self._client = client

    def _require(self):
        if self._client._raw is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        return self._client._raw

    def _tx(self, snap: TransactionSnapshot) -> Transaction:
        row = Transaction(
            id=snap.id,
            type=snap.type,
            amount=snap.amount,
            currency=snap.currency,
            date=snap.date,
            description=snap.description,
            status=snap.status,
            withdrawal_number=snap.withdrawal_number,
        )
        row._client = self._client
        return row

    async def balance(self) -> Balance:
        balance, _page = await self._require().finance.balance_page()
        return balance

    async def balance_on_offer(self, lot_id: int) -> Balance:
        return await self._require().finance.offer_balance(lot_id)

    async def transactions(
        self,
        *,
        limit: int = 24,
        filter: str = "",
        cursor: str | None = None,
    ) -> tuple[str | None, list[Transaction]]:
        user_id = self._client.account_id
        if user_id is None:
            raise AccountNotInitiatedError("account is not initiated")
        next_cursor, rows = await self._require().finance.transactions(cursor, filter, user_id)
        if limit:
            rows = rows[:limit]
        return next_cursor, [self._tx(row) for row in rows]

    async def iter_transactions(
        self,
        *,
        limit: int = 24,
        filter: str = "",
        cursor: str | None = None,
    ) -> AsyncIterator[Transaction]:
        yielded = 0
        while True:
            remaining = None if limit == 0 else limit - yielded
            if remaining is not None and remaining <= 0:
                return
            cursor, rows = await self.transactions(
                limit=0 if remaining is None else remaining,
                filter=filter,
                cursor=cursor,
            )
            if not rows:
                return
            for row in rows:
                yield row
                yielded += 1
                if limit and yielded >= limit:
                    return
            if not cursor:
                return

    async def exchange_rate(self, currency: Currency) -> tuple[float, Currency]:
        return await self._require().finance.exchange(currency)

    async def withdraw(
        self, currency: Currency, wallet: Wallet, amount: float, address: str
    ) -> float:
        return await self._require().finance.withdraw(currency, wallet, amount, address)

    async def wallets(self) -> list[dict]:
        return await self._require().finance.wallets()

    async def save_wallets(self, rows: list[dict]) -> None:
        await self._require().finance.save_wallets(rows)
