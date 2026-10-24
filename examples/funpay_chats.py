"""Print FunPay chats and the latest messages of the first one.

uv run python examples/funpay_chats.py
"""

import asyncio

from aiosellers.funpay import FunPay


async def main() -> None:
    async with FunPay() as client:
        chats = await client.chats.list()
        for chat in chats[:10]:
            mark = "unread" if chat.unread else "read"
            print(f"{chat.id} {chat.name} {mark}: {chat.last_message_text}")
        if not chats:
            return
        messages = await chats[0].get_messages(limit=5)
        for message in messages:
            print(message.id, message.author, message.text)


if __name__ == "__main__":
    asyncio.run(main())
