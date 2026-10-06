"""List transactions, cancel a pending one, and read cards.

uv run python examples/transactions.py
"""

import asyncio

from aiosellers.playerok import Playerok
from aiosellers.playerok.schemas import TransactionStatuses


async def main() -> None:
    async with Playerok() as client:
        transactions = await client.transactions.list(
            limit=20, status=[TransactionStatuses.PENDING]
        )
        for transaction in transactions:
            print(transaction.operation, transaction.value, transaction.status)
            if transaction.status is TransactionStatuses.PENDING:
                await transaction.cancel()

        for bank in await client.transactions.sbp_banks():
            print(bank.name)
        for card in await client.transactions.cards():
            print(card.card_last_four)


if __name__ == "__main__":
    asyncio.run(main())
