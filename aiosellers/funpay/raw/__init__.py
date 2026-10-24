from ..transport import FunPayTransport
from .account import RawAccount
from .chats import RawChats
from .finance import RawFinance
from .lots import RawLots
from .orders import RawOrders


class RawAPI:
    """Low-level FunPay HTTP access."""

    def __init__(self, transport: FunPayTransport) -> None:
        self.account = RawAccount(transport)
        self.chats = RawChats(transport)
        self.orders = RawOrders(transport)
        self.lots = RawLots(transport)
        self.finance = RawFinance(transport)


__all__ = ["RawAPI", "RawAccount", "RawChats", "RawOrders", "RawLots", "RawFinance"]
