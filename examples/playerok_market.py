"""Search a game and print the average listed price.

uv run python examples/playerok_market.py
"""

import asyncio
from statistics import mean

from aiosellers.playerok import Playerok


async def main() -> None:
    async with Playerok() as client:
        games = await client.games.list(search="dota", limit=1)
        if not games:
            print("game not found")
            return
        game = games[0]
        items = await client.items.list(game_id=game.id, search="mmr", limit=100)
        prices = [item.price for item in items if item.price]
        if not prices:
            print(f"{game.name}: no priced items")
            return
        print(f"{game.name}: {len(prices)} items, avg {mean(prices):.2f}")


if __name__ == "__main__":
    asyncio.run(main())
