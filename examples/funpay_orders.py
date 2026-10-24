"""List recent FunPay sales and open the first order card.

uv run python examples/funpay_orders.py
"""

import asyncio

from aiosellers.funpay import FunPay
from aiosellers.funpay.schemas import OrderSide


async def main() -> None:
    async with FunPay() as client:
        _cursor, sales = await client.orders.list(side=OrderSide.SALE, limit=10)
        for order in sales:
            print(order.id, order.status, order.price, order.currency, order.buyer_username)
        if not sales:
            return
        card = await client.orders.get(sales[0].id)
        print("card", card.id, card.description, card.review)


if __name__ == "__main__":
    asyncio.run(main())
