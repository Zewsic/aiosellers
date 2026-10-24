"""Replay saved FunPay chat history through the same handlers. Sends nothing.

uv run python examples/funpay_backtest.py
"""

import asyncio

from aiosellers.funpay import FunPay
from aiosellers.funpay.events import NewMessageEvent, NewReviewEvent

client = FunPay()


@client.on_message()
async def message(event: NewMessageEvent) -> None:
    print("message", event.chat.name, event.message.id, event.message.text)


@client.on_new_review()
async def review(event: NewReviewEvent) -> None:
    print("review", event.order_id, event.message.text)


async def main() -> None:
    # await client.backtest_messages(chat_id=123456, limit=20)
    await client.backtest_messages(limit=20)


if __name__ == "__main__":
    asyncio.run(main())
