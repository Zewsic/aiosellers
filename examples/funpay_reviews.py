"""Reply once when a buyer leaves a new FunPay review.

uv run python examples/funpay_reviews.py
"""

import asyncio

from aiosellers.funpay import FunPay
from aiosellers.funpay.events import NewReviewEvent

client = FunPay()


@client.on_new_review()
async def thanks(event: NewReviewEvent) -> None:
    if not event.order_id:
        return
    await event.client.orders.reply_review(event.order_id, "Спасибо за отзыв!")


async def main() -> None:
    await client.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
