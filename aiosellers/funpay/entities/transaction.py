from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..schemas import Currency

if TYPE_CHECKING:
    from ..funpay import FunPay


@dataclass(slots=True)
class Transaction:
    id: str
    type: str
    amount: float
    currency: Currency
    date: str
    description: str
    status: str
    withdrawal_number: str | None = None
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)
