# All-In-One Sellers API

[![Python](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/release/python-3120/)
[![License: Apache 2.0](https://img.shields.io/badge/license-Apache%202.0-blue.svg)](https://www.apache.org/licenses/LICENSE-2.0)

Asynchronous Python wrapper for working with digital trading platforms. Implemented modules: **PlayerOK** and **FunPay**.

![Python](logo.png)


---

## Installation

```bash
pip install aiosellers
```

or via uv:

```bash
uv add aiosellers
```

**Requirements:** Python 3.12+

---

## Configuration

Token can be passed to the constructor or via environment variable:

```bash
export PLAYEROK_ACCESS_TOKEN="your_token_here"
export FUNPAY_GOLDEN_KEY="your_golden_key"
```

---

## Quick Start

```python
import asyncio
from aiosellers.playerok import Playerok

async def main():
    async with Playerok() as client:
        me = await client.account.me()
        profile = await client.account.profile()

        print(f"User: {me.username} ({me.email})")
        print(f"Rating: {profile.rating} | Reviews: {profile.reviews_count}")
        print(f"Balance: {profile.balance.available} (pending: {profile.balance.pending_income})")
        print(f"Unread chats: {me.unread_chats_counter}")

asyncio.run(main())
```

---

## Examples

### 1. Account Information

```python
async with Playerok() as client:
    me = await client.account.me()
    profile = await client.account.profile()

    print(f"{me.username} | {me.email}")
    print(f"Rating: {profile.rating} ({profile.reviews_count} reviews)")
    print(f"Available: {profile.balance.available}")
    print(f"Pending: {profile.balance.pending_income}")
```

### 2. Market Analysis: Average Item Price

```python
from statistics import mean

async with Playerok() as client:
    games = await client.games.list(search="dota", limit=1)
    game = games[0]

    items = await client.items.list(game_id=game.id, search="mmr", limit=100)
    prices = [i.price for i in items if i.price]

    print(f"{game.name}: avg price = {mean(prices):.2f}")
```

### 3. Working with Chats

```python
async with Playerok() as client:
    user = await client.account.get_user(username="some_user")
    chat = await user.get_chat()

    if not chat:
        print("No chat found")
        return

    messages = await chat.get_messages(limit=20)
    for msg in messages:
        print(f"{msg.sent_at} | {msg.user.username if msg.user else 'system'}: {msg.text}")
        await msg.mark_as_read()

    await chat.send_text("Hello!")
```

### 4. Automatic Item Position Upgrade

```python
async with Playerok() as client:

    async for item in client.items.iter_self():
        pos = item.priority_position or 999
        if pos < 15:
            await item.set_premium_priority()
            print(f"Upgraded: {item.name}")
```

### 5. Batch Deal Processing

```python
from aiosellers.playerok.schemas import ItemDealStatuses

async with Playerok() as client:
    # Send all paid orders
    paid = await client.deals.list(statuses=[ItemDealStatuses.PAID])
    for deal in paid:
        await deal.complete()
        print(f"Sent: {deal.id}")

    # Confirm all sent orders
    sent = await client.deals.list(statuses=[ItemDealStatuses.SENT])
    for deal in sent:
        await deal.confirm()
        print(f"Confirmed: {deal.id}")
```

### 6. Creating an Item with Image

```python
async with Playerok() as client:
    category = await client.games.get_category(slug="skins", game_id="...")
    obtaining_types = await category.get_obtaining_types()
    obtaining_type = obtaining_types[0]

    # Get options (server, region, etc.)
    options = await category.get_options()
    for opt in options:
        opt.set_value(opt.possible_values[0].value)  # select first value

    # Get data fields (fields for seller)
    data_fields = await obtaining_type.get_data_fields()
    for field in data_fields:
        if field.required:
            field.set_value("item data")

    item = await client.items.create(
        category=category.id,
        obtaining_type=obtaining_type.id,
        name="Rare Skin",
        price=1500,
        description="Instant delivery",
        options=options,
        data_fields=data_fields,
        attachments=["https://example.com/preview.jpg"]
    )

    await item.publish(premium=False)
    print(f"Created: {item.id}")
```

### 7. Sniper: Buying the Cheapest Item

```python
import asyncio

async with Playerok() as client:
    games = await client.games.list(search="dota", limit=1)
    items = await client.items.list(game_id=games[0].id, search="arcana", limit=50)

    cheapest = min([i for i in items if i.price], key=lambda x: x.price)

    # Fill in item obtaining fields
    fields = await cheapest.get_obtaining_fields()
    for f in fields:
        if f.required:
            f.set_value("your_data_here")

    deal = await cheapest.create_deal(obtaining_fields=fields)
    await asyncio.sleep(1) # Wait for chat creation on server
    chat = await deal.get_chat()
    await chat.send_text("Hello!")

    print(f"Bought {cheapest.name} for {cheapest.price}")
```

Runnable samples live in [`examples/`](examples/): a PlayerOK bot in `examples/playerok_bot.py`, a FunPay bot in `examples/funpay_bot.py`, and a transaction list in `examples/transactions.py`.

```python
import asyncio

from aiosellers.playerok import Playerok
from aiosellers.playerok.events import NewMessageEvent

client = Playerok()

@client.on_message(text="!команды")
async def commands(event: NewMessageEvent) -> None:
    await event.client.chats.send_message(event.chat.id, text="!привет")

asyncio.run(client.start_polling())
```

---

## Development Status: PlayerOK

| Module                 | Raw API | High-level |
|:-----------------------|:-------:|:----------:|
| **Account**            |    ✅    |     ✅      |
| **Games / Categories** |    ✅    |     ✅      |
| **Items**              |    ✅    |     ✅      |
| **Deals**              |    ✅    |     ✅      |
| **Chats**              |    ✅    |     ✅      |
| **Transactions**       |    ✅    |     ✅      |
| **Event Feed**         |    ✅    |     ✅      |

## Development Status: FunPay

FunPay has no public API. `aiosellers.funpay` speaks the site's HTML and runner endpoints: profile, lots, sales and purchases, chat, balance, and a polling listener.

| Module | Raw API | High-level |
|:-------|:-------:|:----------:|
| **Account** | ✅ | ✅ |
| **Categories** | ✅ | ✅ |
| **Lots** | ✅ | ✅ |
| **Orders** | ✅ | ✅ |
| **Chats** | ✅ | ✅ |
| **Finance** | ✅ | ✅ |
| **Event listener** | ✅ | ✅ |

---

## Acknowledgments

Based on ideas from [PlayerokAPI](https://github.com/alleexxeeyy/PlayerokAPI/)

---

<p align="center">
  <i>Built by developers for developers.</i>
</p>
