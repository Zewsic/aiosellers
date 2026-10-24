"""FunPay bot: greet a buyer and answer a chat phrase.

uv run python examples/funpay_bot.py
"""

import asyncio

from aiosellers.funpay import FunPay
from aiosellers.funpay.events import NewMessageEvent, NewOrderEvent

client = FunPay()


@client.on_message(text="привет")
async def hi(event: NewMessageEvent) -> None:
    if event.message.author_id == event.client.account_id:
        return
    await event.message.answer("Ну привет...")


@client.on_new_order()
async def paid(event: NewOrderEvent) -> None:
    if "аккаунт" not in (event.order.description or "").lower():
        return
    chat = await event.client.chats.get_by_name(event.order.buyer_username, fetch=True)
    if chat is not None:
        await chat.send_text(f"Привет, {event.order.buyer_username}!")


asyncio.run(client.start_polling())
