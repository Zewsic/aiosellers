"""Playerok bot: register handlers, then poll.

uv run python examples/playerok_bot.py
"""

import asyncio

from aiosellers.playerok import Playerok
from aiosellers.playerok.events import (
    DealConfirmedEvent,
    ItemPaidEvent,
    ItemSentEvent,
    NewMessageEvent,
)

client = Playerok()


@client.on_message(text="!команды")
async def commands(event: NewMessageEvent) -> None:
    await event.client.chats.send_message(event.chat.id, text="!привет, !дата")


@client.on_message(text=lambda text: bool(text) and text.startswith("!"))
async def any_command(event: NewMessageEvent) -> None:
    await event.client.chats.send_message(event.chat.id, text=f"Команда: {event.message.text}")


@client.on_message(lambda event: event.message.user_id != event.client.me_id)
async def incoming(event: NewMessageEvent) -> None:
    print(event.chat.id, event.message.text)


@client.on_item_paid
async def paid(event: ItemPaidEvent) -> None:
    await event.client.deals.complete(event.deal.id)


@client.on_item_sent
async def sent(event: ItemSentEvent) -> None:
    print("sent", event.deal.id)


@client.on_deal_confirmed
async def confirmed(event: DealConfirmedEvent) -> None:
    print("confirmed", event.deal.id)


async def main() -> None:
    await client.start_polling()


if __name__ == "__main__":
    asyncio.run(main())
