from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from ..funpay import FunPay


@dataclass(slots=True)
class Review:
    stars: int | None = None
    text: str | None = None
    reply: str | None = None
    order_id: str | None = None
    author: str | None = None
    author_id: int | None = None
    by_bot: bool = False
    reply_by_bot: bool = False
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)
