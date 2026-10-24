import unittest

from aiosellers.funpay import FunPay
from aiosellers.funpay.client_config import FunPayClientConfig
from aiosellers.funpay.entities.chat import Chat, Message
from aiosellers.funpay.events import NewMessageEvent, NewReviewEvent
from aiosellers.funpay.listener import EventListener
from aiosellers.funpay.parsers.orders import parse_order_list
from aiosellers.funpay.schemas import EventTypes, MessageSnapshot, MessageTypes, OrderSide

BOOKMARK = """
<a class="contact-item" data-id="3" data-node-msg="{node}" data-user-msg="9">
  <div class="media-user-name">Ann</div>
  <div class="contact-item-message">{text}</div>
</a>
"""


def _order_row(order_id: str, marker: str) -> str:
    return f"""
    <a class="tc-item {marker}" href="/orders/{order_id}/">
      <div class="tc-order">#{order_id}</div>
      <div class="order-desc"><div>аккаунт</div></div>
      <div class="tc-price">10 ₽</div>
      <div class="media-user-name"><span data-href="/users/9/">Bob</span></div>
    </a>
    """


class _Raw:
    def __init__(self) -> None:
        self.account = self
        self.chats = self
        self.orders = self
        self.payloads: list[dict] = []
        self.history_calls: list[tuple] = []
        self.history_result: list[MessageSnapshot] = []
        self.sales_pages: list[tuple] = []

    async def runner_poll(self, objects, request=None):
        del request
        return self.payloads.pop(0)

    async def history(self, chat_id, last_message_id, retry=True):
        del retry
        self.history_calls.append((chat_id, last_message_id))
        return list(self.history_result)

    async def sales(self, cursor=None, query=None, retry=True):
        del cursor, query, retry
        return self.sales_pages.pop(0)

    async def purchases(self, cursor=None, retry=True):
        del cursor, retry
        return None, []


class _Transport:
    account_id = 5
    username = "me"
    locale = "ru"
    rate_limited_until = 0
    categories: list = []

    async def refresh_profile(self, force: bool = False) -> None:
        del force


def _listener() -> tuple[FunPay, EventListener, _Raw]:
    client = FunPay(FunPayClientConfig(golden_key="key"))
    raw = _Raw()
    client._account_id = 5
    client._raw = raw  # type: ignore[assignment]
    client._transport = _Transport()  # type: ignore[assignment]
    return client, EventListener(client), raw


def _runner(html: str) -> dict:
    return {
        "objects": [
            {"type": "chat_bookmarks", "tag": "chat-tag", "data": html},
            {"type": "orders_counters", "tag": "order-tag", "data": {"buyer": 1, "seller": 2}},
        ]
    }


class FunPayEventTests(unittest.IsolatedAsyncioTestCase):
    async def test_bookmark_ticks_and_image_preview(self) -> None:
        _client, listener, raw = _listener()
        raw.payloads.append(_runner(BOOKMARK.format(node=10, text="hi")))
        first = await listener.tick(orders=False, purchases=False)
        self.assertEqual([event.type for event in first], [EventTypes.INITIAL_CHAT])
        self.assertEqual(raw.history_calls, [])

        raw.history_result = [
            MessageSnapshot(
                id=11,
                text="hey",
                chat_id=3,
                chat_name="Ann",
                author="Ann",
                author_id=9,
                interlocutor_id=9,
                image_link=None,
                image_name=None,
                type=MessageTypes.NON_SYSTEM,
                by_bot=False,
                badge=None,
                is_support=False,
                is_moderation=False,
                is_arbitration=False,
                is_auto_reply=False,
                html="",
            )
        ]
        raw.payloads.append(_runner(BOOKMARK.format(node=11, text="hey")))
        second = await listener.tick(orders=False, purchases=False)
        self.assertEqual(
            [event.type for event in second],
            [
                EventTypes.CHATS_LIST_CHANGED,
                EventTypes.LAST_CHAT_MESSAGE_CHANGED,
                EventTypes.NEW_MESSAGE,
            ],
        )
        self.assertEqual(raw.history_calls, [(3, 12)])

        raw.history_calls.clear()
        raw.payloads.append(_runner(BOOKMARK.format(node=12, text="Изображение")))
        await listener.tick(orders=False, purchases=False)
        self.assertEqual(raw.history_calls, [(3, 13)])

    async def test_order_diff_and_oversized_page(self) -> None:
        _client, listener, raw = _listener()
        raw.payloads.append(_runner(""))
        raw.sales_pages.append(
            parse_order_list(_order_row("ABCD1234", "info"), side=OrderSide.SALE)
        )
        first = await listener.tick(messages=False, purchases=False)
        self.assertEqual([event.type for event in first], [EventTypes.INITIAL_ORDER])

        raw.payloads.append(_runner(""))
        raw.sales_pages.append(
            parse_order_list(_order_row("ABCD1235", "info"), side=OrderSide.SALE)
        )
        second = await listener.tick(messages=False, purchases=False)
        self.assertIn(EventTypes.NEW_ORDER, [event.type for event in second])

        _client2, listener2, raw2 = _listener()
        raw2.payloads.append(_runner(""))
        raw2.sales_pages.append(
            parse_order_list(_order_row("ABCD1234", "info"), side=OrderSide.SALE)
        )
        await listener2.tick(messages=False, purchases=False)
        raw2.payloads.append(_runner(""))
        raw2.sales_pages.append(parse_order_list(_order_row("ABCD1234", ""), side=OrderSide.SALE))
        changed = await listener2.tick(messages=False, purchases=False)
        kinds = [event.type for event in changed]
        self.assertIn(EventTypes.ORDER_STATUS_CHANGED, kinds)
        self.assertIn(EventTypes.ORDER_CLOSED, kinds)

        _client3, listener3, raw3 = _listener()
        raw3.payloads.append(_runner(""))
        raw3.sales_pages.append(
            parse_order_list(_order_row("ABCD1234", "info"), side=OrderSide.SALE)
        )
        await listener3.tick(messages=False, purchases=False)
        wide = "".join(_order_row(f"A{index:07d}", "info") for index in range(101))
        raw3.payloads.append(_runner(""))
        raw3.sales_pages.append(parse_order_list(wide, side=OrderSide.SALE))
        skipped = await listener3.tick(messages=False, purchases=False)
        diff = {
            EventTypes.NEW_ORDER,
            EventTypes.ORDER_STATUS_CHANGED,
            EventTypes.ORDER_CLOSED,
            EventTypes.ORDER_REFUNDED,
        }
        self.assertFalse(diff.intersection(event.type for event in skipped))

    async def test_handlers_text_and_review_stars(self) -> None:
        client = FunPay(FunPayClientConfig(golden_key="key"))
        seen: list[str] = []

        @client.on_message()
        async def boom(_event: NewMessageEvent) -> None:
            raise RuntimeError("boom")

        @client.on_message()
        async def later(_event: NewMessageEvent) -> None:
            seen.append("later")

        message = Message(id=1, text="x", chat_id=1)
        await client._dispatch(NewMessageEvent(client=client, chat=None, message=message))  # type: ignore[arg-type]
        self.assertEqual(seen, ["later"])

        filtered = FunPay(FunPayClientConfig(golden_key="key"))
        ran: list[str] = []

        @filtered.on_message(text="привет")
        async def hi(_event: NewMessageEvent) -> None:
            ran.append("hi")

        await filtered._dispatch(
            NewMessageEvent(
                client=filtered, chat=None, message=Message(id=2, text="Привет", chat_id=1)
            )  # type: ignore[arg-type]
        )
        self.assertEqual(ran, [])

        reviews = FunPay(FunPayClientConfig(golden_key="key"))
        stars: list[str] = []

        @reviews.on_new_review(stars=5)
        async def five(_event: NewReviewEvent) -> None:
            stars.append("five")

        @reviews.on_new_review()
        async def any_stars(_event: NewReviewEvent) -> None:
            stars.append("any")

        class _Review:
            stars = 4

        class _Order:
            review = _Review()

        async def get(order_id: str, force_refresh: bool = False):
            del order_id, force_refresh
            return _Order()

        reviews.orders.get = get  # type: ignore[method-assign]
        await reviews._dispatch(
            NewReviewEvent(
                client=reviews,
                message=Message(id=3, text="ok", chat_id=1),
                order_id="AB12CD34",
            )
        )
        self.assertEqual(stars, ["any"])

    async def test_backtest_replays_messages_in_id_order(self) -> None:
        client, _listener_obj, _raw = _listener()
        chat_a = Chat(id=1, name="Ann")
        chat_b = Chat(id=2, name="Bob")
        feedback = "Покупатель Bob написал отзыв к заказу #AB12CD34."

        async def list_chats(*, fetch: bool = True):
            del fetch
            return [chat_b, chat_a]

        async def list_messages(chat_id, *, last_message_id=None, limit=100):
            del last_message_id, limit
            if chat_id == 1:
                return [
                    Message(id=5, text=feedback, chat_id=1, type=MessageTypes.NEW_FEEDBACK),
                    Message(id=2, text="first", chat_id=1),
                ]
            return [Message(id=3, text="second", chat_id=2)]

        client.chats.list = list_chats  # type: ignore[method-assign]

        async def get_chat(chat_id: int, *, force_refresh: bool = False) -> Chat:
            del force_refresh
            return chat_a if chat_id == 1 else chat_b

        client.chats.get = get_chat  # type: ignore[method-assign]
        client.chats.messages.list = list_messages  # type: ignore[method-assign]
        seen: list[tuple[EventTypes, int]] = []
        async for event in client.replay_messages(limit=2):
            seen.append((event.type, event.message.id))
        self.assertEqual(
            seen,
            [
                (EventTypes.NEW_MESSAGE, 3),
                (EventTypes.NEW_MESSAGE, 5),
                (EventTypes.NEW_REVIEW, 5),
            ],
        )

        dispatched: list[int] = []

        @client.on_message()
        async def handle(event: NewMessageEvent) -> None:
            dispatched.append(event.message.id)

        await client.backtest_messages(chat_id=1, reviews=False)
        self.assertEqual(dispatched, [2, 5])
