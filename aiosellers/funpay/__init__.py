"""FunPay API client library."""

from . import exceptions, schemas
from .client_config import FunPayClientConfig
from .funpay import FunPay

__all__ = ["FunPay", "FunPayClientConfig", "exceptions", "schemas"]
