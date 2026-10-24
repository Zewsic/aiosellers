"""Print the PlayerOK profile and balance.

uv run python examples/playerok_account.py
"""

import asyncio

from aiosellers.playerok import Playerok


async def main() -> None:
    async with Playerok() as client:
        me = await client.account.me()
        profile = await client.account.profile()
        print(f"{me.username} | {me.email}")
        print(f"Rating: {profile.rating} ({profile.reviews_count} reviews)")
        print(f"Available: {profile.balance.available}")
        print(f"Pending: {profile.balance.pending_income}")
        print(f"Unread chats: {me.unread_chats_counter}")


if __name__ == "__main__":
    asyncio.run(main())
