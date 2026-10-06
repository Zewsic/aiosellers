from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import TYPE_CHECKING, Any

from .entities.chat import Chat, ChatMessage
from .entities.deal import Deal
from .schemas import EventTypes

if TYPE_CHECKING:
    from .playerok import Playerok
else:
    Playerok = Any


def _now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass(slots=True)
class ChatInitializedEvent:
    """Snapshot of a chat already known when polling starts."""

    client: Playerok
    chat: Chat
    occurred_at: datetime = field(default_factory=_now)
    type: EventTypes = EventTypes.CHAT_INITIALIZED


@dataclass(slots=True)
class NewMessageEvent:
    client: Playerok
    chat: Chat
    message: ChatMessage
    occurred_at: datetime = field(default_factory=_now)
    type: EventTypes = EventTypes.NEW_MESSAGE


@dataclass(slots=True)
class _DealMessageEvent:
    client: Playerok
    chat: Chat
    deal: Deal
    message: ChatMessage
    occurred_at: datetime = field(default_factory=_now)


@dataclass(slots=True)
class NewDealEvent(_DealMessageEvent):
    type: EventTypes = EventTypes.NEW_DEAL


@dataclass(slots=True)
class ItemPaidEvent(_DealMessageEvent):
    type: EventTypes = EventTypes.ITEM_PAID


@dataclass(slots=True)
class ItemSentEvent(_DealMessageEvent):
    type: EventTypes = EventTypes.ITEM_SENT


@dataclass(slots=True)
class DealConfirmedEvent(_DealMessageEvent):
    type: EventTypes = EventTypes.DEAL_CONFIRMED


@dataclass(slots=True)
class DealConfirmedAutomaticallyEvent(_DealMessageEvent):
    type: EventTypes = EventTypes.DEAL_CONFIRMED_AUTOMATICALLY


@dataclass(slots=True)
class DealRolledBackEvent(_DealMessageEvent):
    type: EventTypes = EventTypes.DEAL_ROLLED_BACK


@dataclass(slots=True)
class DealHasProblemEvent(_DealMessageEvent):
    type: EventTypes = EventTypes.DEAL_HAS_PROBLEM


@dataclass(slots=True)
class DealProblemResolvedEvent(_DealMessageEvent):
    type: EventTypes = EventTypes.DEAL_PROBLEM_RESOLVED


@dataclass(slots=True)
class DealStatusChangedEvent(_DealMessageEvent):
    type: EventTypes = EventTypes.DEAL_STATUS_CHANGED


@dataclass(slots=True)
class NewReviewEvent:
    client: Playerok
    chat: Chat
    deal: Deal
    occurred_at: datetime = field(default_factory=_now)
    type: EventTypes = EventTypes.NEW_REVIEW


PlayerokEvent = (
    ChatInitializedEvent
    | NewMessageEvent
    | NewDealEvent
    | ItemPaidEvent
    | ItemSentEvent
    | DealConfirmedEvent
    | DealConfirmedAutomaticallyEvent
    | DealRolledBackEvent
    | DealHasProblemEvent
    | DealProblemResolvedEvent
    | DealStatusChangedEvent
    | NewReviewEvent
)

_DEAL_EVENT = {
    EventTypes.NEW_DEAL: NewDealEvent,
    EventTypes.ITEM_PAID: ItemPaidEvent,
    EventTypes.ITEM_SENT: ItemSentEvent,
    EventTypes.DEAL_CONFIRMED: DealConfirmedEvent,
    EventTypes.DEAL_CONFIRMED_AUTOMATICALLY: DealConfirmedAutomaticallyEvent,
    EventTypes.DEAL_ROLLED_BACK: DealRolledBackEvent,
    EventTypes.DEAL_HAS_PROBLEM: DealHasProblemEvent,
    EventTypes.DEAL_PROBLEM_RESOLVED: DealProblemResolvedEvent,
    EventTypes.DEAL_STATUS_CHANGED: DealStatusChangedEvent,
}
