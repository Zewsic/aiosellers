"""List paid and sent PlayerOK deals. Does not change them.

uv run python examples/playerok_deals.py
"""

import asyncio

from aiosellers.playerok import Playerok
from aiosellers.playerok.schemas import ItemDealStatuses


async def main() -> None:
    async with Playerok() as client:
        paid = await client.deals.list(statuses=[ItemDealStatuses.PAID], limit=20)
        sent = await client.deals.list(statuses=[ItemDealStatuses.SENT], limit=20)
        print("paid")
        for deal in paid:
            print(deal.id, deal.item_id)
        print("sent")
        for deal in sent:
            print(deal.id, deal.item_id)
        # await deal.complete()  # seller: mark a paid deal as sent
        # await deal.confirm()   # buyer: confirm a sent deal


if __name__ == "__main__":
    asyncio.run(main())
