"""Print the FunPay profile, balance, and latest transactions.

uv run python examples/funpay_account.py
"""

import asyncio

from aiosellers.funpay import FunPay


async def main() -> None:
    async with FunPay() as client:
        me = await client.account.profile()
        balance = await client.finance.balance()
        print(f"{me.username} id={me.id}")
        print(f"RUB {balance.rub} | USD {balance.usd} | EUR {balance.eur}")
        _cursor, rows = await client.finance.transactions(limit=10)
        for row in rows:
            print(row.date, row.amount, row.currency, row.description)


if __name__ == "__main__":
    asyncio.run(main())
