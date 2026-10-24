"""Client configuration for FunPay."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass
class FunPayClientConfig:
    """Configuration for the FunPay client.

    Attributes:
        golden_key: FunPay golden_key cookie (or set FUNPAY_GOLDEN_KEY).
        user_agent: Desktop user agent. None selects the built-in Chrome UA.
        request_timeout: Request timeout in seconds.
        base_url: FunPay origin, with or without a trailing slash.
        locale: Optional locale prefix. ru and None stay unprefixed.
        proxy: Proxy URL passed through to tls_requests when supported.
        use_identity_map: Reuse entity instances for the same id.
        poll_interval: Seconds between listener ticks.
        session_refresh_seconds: How long a parsed home page stays fresh.
    """

    golden_key: str | None = None
    user_agent: str | None = None
    request_timeout: float = 10.0
    base_url: str = "https://funpay.com/"
    locale: Literal["ru", "en", "uk"] | None = None
    proxy: str | None = None
    use_identity_map: bool = True
    poll_interval: float = 6.0
    session_refresh_seconds: float = 2400.0
