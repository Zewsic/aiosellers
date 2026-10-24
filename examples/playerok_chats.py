"""Print unread PlayerOK chats and their latest messages.

uv run python examples/playerok_chats.py
"""

import asyncio

from aiosellers.playerok import Playerok


async def main() -> None:
    async with Playerok() as client:
        chats = await client.chats.list(limit=10, unread_only=True)
        for chat in chats:
            who = chat.name or (chat.user.username if chat.user else "system")
            print(f"{who} unread={chat.unread_messages_counter}")
            for message in await chat.get_messages(limit=3):
                author = message.user.username if message.user else "system"
                print(f"  {author}: {message.text}")


if __name__ == "__main__":
    asyncio.run(main())
