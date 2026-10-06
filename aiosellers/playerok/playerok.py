from __future__ import annotations

import inspect
import logging
from collections.abc import Awaitable, Callable
from dataclasses import dataclass
from typing import Any

from .api import AccountAPI, ChatAPI, DealAPI, GameAPI, ItemAPI, TransactionAPI
from .client_config import PlayerokClientConfig
from .core.config import PlayerokConfig
from .core.identity_map import IdentityMap
from .entities.chat import Chat
from .entities.deal import Deal
from .entities.game import Game
from .entities.item import Item, MyItem
from .entities.user import User
from .events import PlayerokEvent
from .listener import EventListener
from .raw import RawAPI
from .schemas import EventTypes
from .transport import PlayerokTransport

logger = logging.getLogger("aiosellers.playerok")

Handler = Callable[[PlayerokEvent], Awaitable[None]]
Predicate = Callable[[PlayerokEvent], bool]
TextFilter = str | Callable[[str | None], bool]


@dataclass(slots=True)
class _Handler:
    event_type: EventTypes
    fn: Handler
    text: TextFilter | None = None
    predicate: Predicate | None = None


@dataclass(slots=True)
class _IdentityMaps:
    users: IdentityMap[str, User]
    chats: IdentityMap[str, Chat]
    deals: IdentityMap[str, Deal]
    games: IdentityMap[str, Game]
    items: IdentityMap[str, Item | MyItem]


class Playerok:
    """High-level Playerok client with modular API."""

    def __init__(self, config: PlayerokClientConfig | str | None = None) -> None:
        """Initialize Playerok client.

        Args:
            config: Client configuration. Can be:
                - PlayerokClientConfig instance
                - str: access token (creates default config)
                - None: creates default config (expects PLAYEROK_ACCESS_TOKEN env var)
        """
        if isinstance(config, str):  # Access Token or Config
            config = PlayerokClientConfig(access_token=config)
        elif config is None:
            config = PlayerokClientConfig()

        self._config = config
        self._transport: PlayerokTransport | None = None
        self._raw: RawAPI | None = None
        self._use_identity_map = config.use_identity_map
        self._me_id: str | None = None

        if self._use_identity_map:
            self._identity_maps = _IdentityMaps(
                users=IdentityMap(),
                chats=IdentityMap(),
                deals=IdentityMap(),
                games=IdentityMap(),
                items=IdentityMap(),
            )

        self.account = AccountAPI(self)
        self.chats = ChatAPI(self)
        self.deals = DealAPI(self)
        self.games = GameAPI(self)
        self.items = ItemAPI(self)
        self.transactions = TransactionAPI(self)
        self._handlers: list[_Handler] = []

        self.users = self.account

    @property
    def me_id(self) -> str | None:
        return self._me_id

    async def __aenter__(self) -> Playerok:
        await self.start()
        return self

    async def __aexit__(self, exc_type, exc, tb) -> None:  # noqa: ANN001
        await self.close()

    async def start(self) -> None:
        """Start the client."""
        if self._transport is not None:
            return

        self._transport = PlayerokTransport(
            access_token=self._config.access_token,
            config=PlayerokConfig(
                user_agent=self._config.user_agent,
                request_timeout=self._config.request_timeout,
                base_url=self._config.base_url,
            ),
        )
        self._raw = RawAPI(self._transport)

        me = await self._raw.account.get_me()
        self._me_id = me.id

    async def close(self) -> None:
        """Close the client."""
        if self._transport is None:
            return

        await self._transport.close()
        self._transport = None
        self._raw = None

        if self._use_identity_map:
            self._identity_maps.users.clear()
            self._identity_maps.chats.clear()
            self._identity_maps.deals.clear()
            self._identity_maps.games.clear()
            self._identity_maps.items.clear()

    async def download(self, url: str) -> bytes:
        if self._transport is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        return await self._transport.download(url)

    def listen(self, *, messages: bool = True, reviews: bool = True, **listener_options: Any):
        """Low-level event stream. The client must already be started."""
        if self._transport is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        return EventListener(self, **listener_options).listen(messages=messages, reviews=reviews)

    async def start_polling(self, *, messages: bool = True, reviews: bool = True) -> None:
        """Start the session, dispatch decorator handlers, and close on exit."""
        await self.start()
        try:
            async for event in self.listen(messages=messages, reviews=reviews):
                await self._dispatch(event)
        finally:
            await self.close()

    def on(
        self,
        event_type: EventTypes,
        fn: Handler | Predicate | None = None,
        *,
        text: TextFilter | None = None,
    ):
        return self._on(event_type, fn, text=text)

    def on_message(self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None):
        return self._on(EventTypes.NEW_MESSAGE, fn, text=text)

    def on_new_deal(self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None):
        return self._on(EventTypes.NEW_DEAL, fn, text=text)

    def on_new_review(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.NEW_REVIEW, fn, text=text)

    def on_item_paid(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.ITEM_PAID, fn, text=text)

    def on_item_sent(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.ITEM_SENT, fn, text=text)

    def on_deal_confirmed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.DEAL_CONFIRMED, fn, text=text)

    def on_deal_confirmed_automatically(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.DEAL_CONFIRMED_AUTOMATICALLY, fn, text=text)

    def on_deal_rolled_back(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.DEAL_ROLLED_BACK, fn, text=text)

    def on_deal_has_problem(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.DEAL_HAS_PROBLEM, fn, text=text)

    def on_deal_problem_resolved(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.DEAL_PROBLEM_RESOLVED, fn, text=text)

    def on_deal_status_changed(
        self, fn: Handler | Predicate | None = None, *, text: TextFilter | None = None
    ):
        return self._on(EventTypes.DEAL_STATUS_CHANGED, fn, text=text)

    def _on(
        self,
        event_type: EventTypes,
        fn: Handler | Predicate | None = None,
        *,
        text: TextFilter | None = None,
    ):
        def register(func: Handler, predicate: Predicate | None = None) -> Handler:
            self._handlers.append(
                _Handler(event_type=event_type, fn=func, text=text, predicate=predicate)
            )
            return func

        if fn is None:
            return register
        if inspect.iscoroutinefunction(fn):
            return register(fn)
        return lambda func: register(func, predicate=fn)

    async def _dispatch(self, event: PlayerokEvent) -> None:
        if event.type is EventTypes.CHAT_INITIALIZED:
            return
        for handler in list(self._handlers):
            if handler.event_type != event.type:
                continue
            if handler.text is not None:
                message = getattr(event, "message", None)
                text = message.text if message is not None else None
                try:
                    matched = handler.text(text) if callable(handler.text) else text == handler.text
                except Exception:
                    logger.exception("Event text filter failed")
                    continue
                if not matched:
                    continue
            if handler.predicate is not None:
                try:
                    if not handler.predicate(event):
                        continue
                except Exception:
                    logger.exception("Event filter failed")
                    continue
            try:
                await handler.fn(event)
            except Exception:
                logger.exception("Event handler failed")
