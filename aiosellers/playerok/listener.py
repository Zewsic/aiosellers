from __future__ import annotations

import asyncio
import contextlib
import json
import logging
import uuid
from collections import deque
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any, AsyncIterator

from pydantic import ValidationError

from .documents import CHAT_MESSAGE_CREATED, CHAT_UPDATED, USER_UPDATED
from .events import (
    _DEAL_EVENT,
    ChatInitializedEvent,
    NewMessageEvent,
    NewReviewEvent,
    PlayerokEvent,
)
from .schemas import Chat as ChatSchema
from .schemas import ChatMessage as ChatMessageSchema
from .schemas import EventTypes

if TYPE_CHECKING:
    from .playerok import Playerok

logger = logging.getLogger("aiosellers.playerok.listener")

_WS_URL = "wss://ws.playerok.com/graphql"
_STOP = object()


def _as_utc(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc)


def classify_message(text: str | None) -> list[EventTypes]:
    if not text:
        return []
    if text == "{{ITEM_PAID}}":
        return [EventTypes.NEW_DEAL, EventTypes.ITEM_PAID]
    if text == "{{ITEM_SENT}}":
        return [EventTypes.ITEM_SENT, EventTypes.DEAL_STATUS_CHANGED]
    if text.startswith("{{DEAL_CONFIRMED") and text.endswith("}}"):
        kind = (
            EventTypes.DEAL_CONFIRMED_AUTOMATICALLY
            if "AUTOMATICALLY" in text
            else EventTypes.DEAL_CONFIRMED
        )
        return [kind, EventTypes.DEAL_STATUS_CHANGED]
    if text == "{{DEAL_ROLLED_BACK}}":
        return [EventTypes.DEAL_ROLLED_BACK, EventTypes.DEAL_STATUS_CHANGED]
    if text == "{{DEAL_HAS_PROBLEM}}":
        return [EventTypes.DEAL_HAS_PROBLEM, EventTypes.DEAL_STATUS_CHANGED]
    if text == "{{DEAL_PROBLEM_RESOLVED}}":
        return [EventTypes.DEAL_PROBLEM_RESOLVED, EventTypes.DEAL_STATUS_CHANGED]
    return [EventTypes.NEW_MESSAGE]


def parse_chat_message(data: dict[str, Any]) -> ChatMessageSchema:
    try:
        return ChatMessageSchema.model_validate(data)
    except ValidationError:
        logger.debug("Chat message payload did not match the schema", exc_info=True)
    slim: dict[str, Any] = {
        "id": data.get("id"),
        "text": data.get("text"),
        "createdAt": data.get("createdAt"),
        "isRead": bool(data.get("isRead", False)),
    }
    user = data.get("user")
    if isinstance(user, dict) and user.get("id") and user.get("username"):
        slim["user"] = {
            "id": user["id"],
            "username": user["username"],
            "role": user.get("role") or "USER",
        }
    deal = data.get("deal")
    if isinstance(deal, dict) and deal.get("id") and deal.get("status") and deal.get("direction"):
        slim_deal: dict[str, Any] = {
            "id": deal["id"],
            "status": deal["status"],
            "direction": deal["direction"],
            "hasProblem": deal.get("hasProblem", False),
        }
        chat = deal.get("chat")
        if isinstance(chat, dict) and chat.get("id"):
            slim_deal["chat"] = {"id": chat["id"]}
        slim["deal"] = slim_deal
    return ChatMessageSchema.model_validate(slim)


def parse_chat(data: dict[str, Any]) -> ChatSchema:
    try:
        return ChatSchema.model_validate(data)
    except ValidationError:
        logger.debug("Chat payload did not match the schema", exc_info=True)
    slim = {"id": data.get("id"), "type": data.get("type") or "PM"}
    last = data.get("lastMessage")
    if isinstance(last, dict):
        slim["lastMessage"] = parse_chat_message(last).model_dump(by_alias=True)
    return ChatSchema.model_validate(slim)


class EventListener:
    """Realtime Playerok feed: GraphQL subscriptions plus system-message parsing."""

    def __init__(
        self,
        client: Playerok,
        *,
        refetch_message_delay: float = 6.0,
        refetch_deal_delay: float = 3.0,
        refetch_attempts: int = 3,
        history_grace_seconds: float = 90.0,
        new_chat_pause: float = 8.0,
        review_delay: float = 30.0,
        review_tries: int = 30,
    ) -> None:
        self.client = client
        self.refetch_message_delay = refetch_message_delay
        self.refetch_deal_delay = refetch_deal_delay
        self.refetch_attempts = refetch_attempts
        self.history_grace_seconds = history_grace_seconds
        self.new_chat_pause = new_chat_pause
        self.review_delay = review_delay
        self.review_tries = review_tries

        self.sent: list[str] = []
        self.processed_message_ids: set[str] = set()
        self._processed_order: deque[str] = deque()
        self.processed_deal_ids: set[str] = set()
        self.review_deal_ids: list[str] = []
        self.review_checks: dict[str, dict[str, float | int]] = {}
        self.known_chat_ids: set[str] = set()
        self.chat_subscriptions: dict[str, str] = {}
        self._possible_new_chat = asyncio.Event()
        self._stop = asyncio.Event()
        self._ws: Any = None
        self._tasks: list[asyncio.Task[Any]] = []

    def remember_history(self, chats: list[ChatSchema], *, now: datetime | None = None) -> None:
        moment = now or datetime.now(timezone.utc)
        for chat in chats:
            message = chat.last_message
            if message is None:
                continue
            age = (moment - _as_utc(message.created_at)).total_seconds()
            if age > self.history_grace_seconds:
                self._mark_message(message.id)

    def subscription_frames(self) -> list[dict[str, Any]]:
        user_id = self.client.me_id
        frames = [
            self._subscribe(
                "chatUpdated",
                CHAT_UPDATED,
                {"filter": {"userId": user_id}, "showForbiddenImage": True},
            ),
            self._subscribe("userUpdated", USER_UPDATED, {"userId": user_id}),
        ]
        for chat_id in list(self.known_chat_ids):
            frames.append(self._chat_message_frame(chat_id))
        return frames

    async def handle_frame(self, data: dict[str, Any]) -> list[PlayerokEvent]:
        if data.get("type") == "connection_ack":
            for frame in self.subscription_frames():
                await self._send(frame)
            return []

        payload = (data.get("payload") or {}).get("data") or {}
        events: list[PlayerokEvent] = []

        updated_user = payload.get("userUpdated")
        if isinstance(updated_user, dict) and updated_user.get("unreadChatsCounter", 0) > 0:
            self._possible_new_chat.set()

        updated_chat = payload.get("chatUpdated")
        if isinstance(updated_chat, dict):
            events.extend(await self._on_chat_updated(updated_chat))

        created = payload.get("chatMessageCreated")
        if isinstance(created, dict):
            chat_id = self.chat_subscriptions.get(str(data.get("id")))
            if chat_id is None:
                logger.debug("chatMessageCreated for an unknown subscription")
            else:
                message = parse_chat_message(created)
                chat = self.client.chats._create_chat(
                    ChatSchema.model_validate({"id": chat_id, "type": "PM"})
                )
                events.extend(await self.events_for_message(chat, message))
        return events

    async def poll_new_chats_once(self) -> list[PlayerokEvent]:
        if not self._possible_new_chat.is_set():
            return []
        self._possible_new_chat.clear()
        if self.new_chat_pause:
            await asyncio.sleep(self.new_chat_pause)

        page = await self.client._raw.chats.get_chats(
            user_id=self.client.me_id, count=15, type=self._pm_type()
        )
        if page is None:
            return []

        now = datetime.now(timezone.utc)
        events: list[PlayerokEvent] = []
        for chat_schema in page.chats:
            message = chat_schema.last_message
            if message is None:
                continue
            fresh = (
                now - _as_utc(message.created_at)
            ).total_seconds() <= self.history_grace_seconds
            unseen = message.id not in self.processed_message_ids
            if message.text == "{{ITEM_PAID}}" and fresh:
                chat = self.client.chats._create_chat(chat_schema)
                events.extend(await self.events_for_message(chat, message))
                continue
            if chat_schema.id not in self.known_chat_ids or unseen or fresh:
                events.extend(await self._scan_recent_paid(chat_schema, now))
        return events

    async def poll_reviews_once(self) -> list[PlayerokEvent]:
        events: list[PlayerokEvent] = []
        for deal_id in list(self.review_deal_ids):
            if not self._should_check_review(deal_id):
                continue
            schema = await self.client._raw.deals.get_deal(deal_id)
            if schema is None or schema.review is None:
                continue
            self.review_deal_ids.remove(deal_id)
            deal = self.client.deals._create_deal(schema)
            chat = None
            if deal.chat_id:
                chat = await self.client.chats.get(deal.chat_id)
            if chat is None and schema.chat is not None:
                chat = self.client.chats._create_chat(schema.chat)
            if chat is None:
                continue
            events.append(NewReviewEvent(client=self.client, chat=chat, deal=deal))
        return events

    async def events_for_message(self, chat, message: ChatMessageSchema) -> list[PlayerokEvent]:
        if not message.text:
            return []
        if message.id in self.processed_message_ids:
            return []
        self._mark_message(message.id)

        kinds = classify_message(message.text)
        if kinds == [EventTypes.NEW_MESSAGE]:
            return [
                NewMessageEvent(
                    client=self.client,
                    chat=chat,
                    message=self.client.chats.messages._create_message(message, chat.id),
                )
            ]

        actual = await self._refetch_message(chat.id, message.id) or message
        deal_schema = actual.deal
        if deal_schema is None or not deal_schema.id:
            return []
        if EventTypes.NEW_DEAL in kinds:
            if deal_schema.id in self.processed_deal_ids:
                return []
            self.processed_deal_ids.add(deal_schema.id)
            if deal_schema.id not in self.review_deal_ids:
                self.review_deal_ids.append(deal_schema.id)

        fetched = await self._refetch_deal(deal_schema.id)
        if fetched is not None:
            deal_schema = fetched
        deal = self.client.deals._create_deal(deal_schema)
        entity_message = self.client.chats.messages._create_message(actual, chat.id)
        events: list[PlayerokEvent] = []
        for kind in kinds:
            event_cls = _DEAL_EVENT[kind]
            events.append(
                event_cls(
                    client=self.client,
                    chat=chat,
                    deal=deal,
                    message=entity_message,
                )
            )
        return events

    async def listen(
        self, *, messages: bool = True, reviews: bool = True
    ) -> AsyncIterator[PlayerokEvent]:
        if not messages and not reviews:
            return

        queue: asyncio.Queue[Any] = asyncio.Queue()

        async def produce(iterator: AsyncIterator[PlayerokEvent]) -> None:
            try:
                async for event in iterator:
                    await queue.put(event)
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.exception("Event feed task failed")

        tasks: list[asyncio.Task[Any]] = []
        if messages:
            page = await self.client._raw.chats.get_chats(user_id=self.client.me_id, count=24)
            chats = list(page.chats) if page is not None else []
            self.remember_history(chats)
            for chat_schema in chats:
                self.known_chat_ids.add(chat_schema.id)
                chat = self.client.chats._create_chat(chat_schema)
                await queue.put(ChatInitializedEvent(client=self.client, chat=chat))
            tasks.append(asyncio.create_task(produce(self._socket_events())))
            tasks.append(asyncio.create_task(produce(self._new_chat_events())))
        if reviews:
            tasks.append(asyncio.create_task(produce(self._review_events())))
        self._tasks = tasks

        try:
            while not self._stop.is_set():
                item = await queue.get()
                if item is _STOP:
                    break
                yield item
        finally:
            await self.aclose()

    async def aclose(self) -> None:
        self._stop.set()
        for task in self._tasks:
            task.cancel()
        for task in self._tasks:
            with contextlib.suppress(asyncio.CancelledError):
                await task
        self._tasks.clear()
        ws = self._ws
        self._ws = None
        if ws is not None:
            with contextlib.suppress(Exception):
                await ws.close()

    async def _socket_events(self) -> AsyncIterator[PlayerokEvent]:
        import websockets

        while not self._stop.is_set():
            try:
                connect = websockets.connect(
                    _WS_URL,
                    subprotocols=["graphql-transport-ws"],
                    additional_headers=self._headers(),
                    origin="https://playerok.com",
                )
                async with connect as ws:
                    self._ws = ws
                    await self._send(
                        {
                            "type": "connection_init",
                            "payload": {
                                "x-gql-op": "ws-subscription",
                                "x-gql-path": "/chats/[id]",
                                "x-timezone-offset": -180,
                            },
                        }
                    )
                    async for raw in ws:
                        if self._stop.is_set():
                            break
                        try:
                            data = json.loads(raw)
                        except json.JSONDecodeError:
                            continue
                        for event in await self.handle_frame(data):
                            yield event
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("WebSocket connection dropped", exc_info=True)
                self._ws = None
                if self._stop.is_set():
                    break
                await asyncio.sleep(3)

    async def _new_chat_events(self) -> AsyncIterator[PlayerokEvent]:
        while not self._stop.is_set():
            try:
                await asyncio.wait_for(self._possible_new_chat.wait(), timeout=15)
            except TimeoutError:
                pass
            except asyncio.CancelledError:
                raise
            if self._stop.is_set():
                break
            try:
                for event in await self.poll_new_chats_once():
                    yield event
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("New chat poll failed", exc_info=True)

    async def _review_events(self) -> AsyncIterator[PlayerokEvent]:
        while not self._stop.is_set():
            try:
                for event in await self.poll_reviews_once():
                    yield event
            except asyncio.CancelledError:
                raise
            except Exception:
                logger.debug("Review poll failed", exc_info=True)
            try:
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                raise

    async def _on_chat_updated(self, data: dict[str, Any]) -> list[PlayerokEvent]:
        chat_schema = parse_chat(data)
        events: list[PlayerokEvent] = []
        if chat_schema.id not in self.chat_subscriptions.values():
            await self._send(self._chat_message_frame(chat_schema.id))
            chat = self.client.chats._create_chat(chat_schema)
            self.known_chat_ids.add(chat_schema.id)
            events.append(ChatInitializedEvent(client=self.client, chat=chat))
            if chat_schema.last_message is not None:
                events.extend(await self.events_for_message(chat, chat_schema.last_message))
        return events

    async def _scan_recent_paid(
        self, chat_schema: ChatSchema, now: datetime
    ) -> list[PlayerokEvent]:
        page = await self.client._raw.chats.get_chat_messages(chat_schema.id, count=12)
        if page is None:
            return []
        for message in page.messages:
            if message.text != "{{ITEM_PAID}}":
                continue
            age = (now - _as_utc(message.created_at)).total_seconds()
            if age > self.history_grace_seconds:
                continue
            chat = self.client.chats._create_chat(chat_schema)
            self.known_chat_ids.add(chat_schema.id)
            return await self.events_for_message(chat, message)
        return []

    async def _refetch_message(self, chat_id: str, message_id: str) -> ChatMessageSchema | None:
        for _ in range(self.refetch_attempts):
            if self.refetch_message_delay:
                await asyncio.sleep(self.refetch_message_delay)
            page = await self.client._raw.chats.get_chat_messages(chat_id, count=12)
            if page is None:
                continue
            for message in page.messages:
                if message.id == message_id:
                    return message
        return None

    async def _refetch_deal(self, deal_id: str):
        for _ in range(self.refetch_attempts):
            try:
                deal = await self.client._raw.deals.get_deal(deal_id)
            except Exception:
                deal = None
            if deal is not None:
                return deal
            if self.refetch_deal_delay:
                await asyncio.sleep(self.refetch_deal_delay)
        return None

    def _should_check_review(self, deal_id: str) -> bool:
        now = asyncio.get_running_loop().time()
        info = self.review_checks.get(deal_id, {"last": 0.0, "tries": 0})
        last = float(info["last"])
        tries = int(info["tries"])
        if now - last > self.review_delay:
            self.review_checks[deal_id] = {"last": now, "tries": tries + 1}
            return True
        if tries >= self.review_tries:
            if deal_id in self.review_deal_ids:
                self.review_deal_ids.remove(deal_id)
            self.review_checks.pop(deal_id, None)
        return False

    def _mark_message(self, message_id: str) -> None:
        if message_id in self.processed_message_ids:
            return
        self.processed_message_ids.add(message_id)
        self._processed_order.append(message_id)
        while len(self._processed_order) > 300:
            oldest = self._processed_order.popleft()
            self.processed_message_ids.discard(oldest)

    def _subscribe(
        self, operation: str, query: str, variables: dict[str, Any], *, sub_id: str | None = None
    ) -> dict[str, Any]:
        return {
            "id": sub_id or str(uuid.uuid4()),
            "type": "subscribe",
            "payload": {
                "extensions": {},
                "operationName": operation,
                "query": query,
                "variables": variables,
            },
        }

    def _chat_message_frame(self, chat_id: str) -> dict[str, Any]:
        for sub_id, known in self.chat_subscriptions.items():
            if known == chat_id:
                return self._subscribe(
                    "chatMessageCreated",
                    CHAT_MESSAGE_CREATED,
                    {"filter": {"chatId": chat_id}, "showForbiddenImage": True},
                    sub_id=sub_id,
                )
        sub_id = str(uuid.uuid4())
        self.chat_subscriptions[sub_id] = chat_id
        self.known_chat_ids.add(chat_id)
        return self._subscribe(
            "chatMessageCreated",
            CHAT_MESSAGE_CREATED,
            {"filter": {"chatId": chat_id}, "showForbiddenImage": True},
            sub_id=sub_id,
        )

    async def _send(self, frame: dict[str, Any]) -> None:
        raw = json.dumps(frame)
        self.sent.append(raw)
        if self._ws is not None:
            await self._ws.send(raw)

    def _headers(self) -> dict[str, str]:
        transport = self.client._transport
        token = transport._access_token if transport is not None else ""
        user_agent = transport.config.user_agent if transport is not None else "aiosellers"
        return {
            "Origin": "https://playerok.com",
            "Cookie": f"token={token}",
            "User-Agent": user_agent,
        }

    @staticmethod
    def _pm_type():
        from .schemas import ChatTypes

        return ChatTypes.PM
