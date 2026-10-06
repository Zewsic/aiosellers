import json
import unittest
from datetime import datetime, timedelta, timezone
from types import SimpleNamespace

from aiosellers.playerok import Playerok
from aiosellers.playerok.client_config import PlayerokClientConfig
from aiosellers.playerok.entities.chat import Chat, ChatMessage
from aiosellers.playerok.events import ItemPaidEvent, NewMessageEvent
from aiosellers.playerok.graphql import GraphQLQuery
from aiosellers.playerok.listener import EventListener, classify_message
from aiosellers.playerok.schemas import Chat as ChatSchema
from aiosellers.playerok.schemas import ChatMessage as ChatMessageSchema
from aiosellers.playerok.schemas import ChatTypes, EventTypes, QueryID


def _message(
    message_id: str, text: str, deal_id: str | None = None, *, age: timedelta = timedelta()
) -> ChatMessageSchema:
    payload = {
        "id": message_id,
        "text": text,
        "createdAt": datetime.now(timezone.utc) - age,
        "isRead": False,
    }
    if deal_id:
        payload["deal"] = {
            "id": deal_id,
            "status": "PAID",
            "direction": "OUT",
            "hasProblem": False,
        }
    return ChatMessageSchema.model_validate(payload)


class _Raw:
    def __init__(self, message: ChatMessageSchema) -> None:
        self.message = message
        self.chat_calls = 0
        self.chats = self
        self.deals = self

    async def get_chat_messages(
        self, chat_id: str, count: int = 24, after_cursor: str | None = None
    ):
        return SimpleNamespace(messages=[self.message])

    async def get_deal(self, deal_id: str):
        return self.message.deal

    async def get_chats(self, **kwargs):
        self.chat_calls += 1
        return SimpleNamespace(chats=[])


def _listener(message: ChatMessageSchema | None = None) -> tuple[Playerok, EventListener]:
    client = Playerok(PlayerokClientConfig(access_token="token"))
    client._me_id = "me"
    raw = _Raw(message or _message("m", "hi"))
    client._raw = raw
    listener = EventListener(
        client,
        refetch_message_delay=0,
        refetch_deal_delay=0,
        refetch_attempts=1,
        new_chat_pause=0,
        review_delay=0,
    )
    return client, listener


class EventFeedTests(unittest.IsolatedAsyncioTestCase):
    def test_classify_confirmed_variants(self) -> None:
        self.assertEqual(
            classify_message("{{DEAL_CONFIRMED}}"),
            [EventTypes.DEAL_CONFIRMED, EventTypes.DEAL_STATUS_CHANGED],
        )
        self.assertEqual(
            classify_message("{{DEAL_CONFIRMED_AUTOMATICALLY}}"),
            [EventTypes.DEAL_CONFIRMED_AUTOMATICALLY, EventTypes.DEAL_STATUS_CHANGED],
        )
        self.assertEqual(classify_message(None), [])
        self.assertEqual(classify_message(""), [])

    def test_chat_messages_query_exposes_forbidden_images(self) -> None:
        payload = GraphQLQuery.get_chat_messages("chat")
        self.assertTrue(payload["variables"]["showForbiddenImage"])
        self.assertEqual(
            payload["extensions"]["persistedQuery"]["sha256Hash"],
            QueryID.chat_messages.value,
        )
        self.assertEqual(
            QueryID.chat_messages.value,
            "9b4e264ff1b20e0fd3929afe023dee8f50affc02b85f80cb4b3dc1516ecfbaa0",
        )

    async def test_item_paid_is_deduplicated(self) -> None:
        message = _message("m1", "{{ITEM_PAID}}", "deal-1")
        client, listener = _listener(message)
        chat = client.chats._create_chat(ChatSchema(id="c1", type=ChatTypes.PM))
        first = await listener.events_for_message(chat, message)
        self.assertEqual(
            [event.type for event in first], [EventTypes.NEW_DEAL, EventTypes.ITEM_PAID]
        )

        again = _message("m2", "{{ITEM_PAID}}", "deal-1")
        listener.client._raw.message = again
        second = await listener.events_for_message(chat, again)
        self.assertEqual(second, [])

    async def test_old_startup_message_is_not_new(self) -> None:
        message = _message("old", "hello", age=timedelta(minutes=10))
        _client, listener = _listener(message)
        chat = ChatSchema(id="c1", type=ChatTypes.PM, last_message=message)
        listener.remember_history([chat])
        entity = _client.chats._create_chat(chat)
        self.assertEqual(await listener.events_for_message(entity, message), [])

    async def test_connection_ack_subscribes_chat_and_user(self) -> None:
        _client, listener = _listener()
        await listener.handle_frame({"type": "connection_ack"})
        names = [json.loads(raw)["payload"]["operationName"] for raw in listener.sent]
        self.assertEqual(names, ["chatUpdated", "userUpdated"])

    async def test_unread_counter_polls_chats(self) -> None:
        _client, listener = _listener()
        await listener.handle_frame(
            {"type": "next", "payload": {"data": {"userUpdated": {"unreadChatsCounter": 2}}}}
        )
        self.assertTrue(listener._possible_new_chat.is_set())
        await listener.poll_new_chats_once()
        self.assertEqual(listener.client._raw.chat_calls, 1)

    async def test_decorators_filter_without_checking_type_in_the_handler(self) -> None:
        client, _listener_unused = _listener()
        seen: list[str] = []

        @client.on_message(text="!команды")
        async def commands(event: NewMessageEvent) -> None:
            seen.append(event.message.text or "")

        @client.on_message(text=lambda text: bool(text) and text.startswith("!"))
        async def prefixed(event: NewMessageEvent) -> None:
            seen.append("prefix")

        @client.on_item_paid
        async def paid(event: ItemPaidEvent) -> None:
            seen.append("paid")

        chat = Chat(id="c1")
        sent_at = datetime.now(timezone.utc)

        async def emit(text: str) -> None:
            event = NewMessageEvent(
                client=client,
                chat=chat,
                message=ChatMessage(id="m", sent_at=sent_at, is_read=False, text=text),
            )
            await client._dispatch(event)

        await emit("!команды")
        await emit("!другое")
        await emit("привет")
        self.assertEqual(seen, ["!команды", "prefix", "prefix"])


if __name__ == "__main__":
    unittest.main()
