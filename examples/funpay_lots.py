"""Print your FunPay lots. Does not edit or raise them.

uv run python examples/funpay_lots.py
"""

import asyncio

from aiosellers.funpay import FunPay
from aiosellers.funpay.schemas import SubCategoryTypes


async def main() -> None:
    async with FunPay() as client:
        shown = 0
        for category in await client.categories.list():
            for sub in category.subcategories:
                if sub.type is not SubCategoryTypes.COMMON:
                    continue
                for lot in await sub.list_self():
                    print(category.name, sub.name, lot.id, lot.price, "on" if lot.active else "off")
                    shown += 1
                    if shown >= 30:
                        return


if __name__ == "__main__":
    asyncio.run(main())
