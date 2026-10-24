from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal

from .constants import DEFAULT_USER_AGENT


@dataclass
class FunPayConfig:
    golden_key: str
    user_agent: str
    request_timeout: float
    base_url: str
    locale: Literal["ru", "en", "uk"] | None
    proxy: str | None
    session_refresh_seconds: float

    @classmethod
    def from_client(cls, config) -> FunPayConfig:
        key = config.golden_key or os.getenv("FUNPAY_GOLDEN_KEY")
        if not key:
            raise RuntimeError(
                "Please provide funpay golden_key or fill FUNPAY_GOLDEN_KEY environment variable."
            )
        user_agent = (config.user_agent or "").strip() or DEFAULT_USER_AGENT
        return cls(
            golden_key=key,
            user_agent=user_agent,
            request_timeout=config.request_timeout,
            base_url=config.base_url or "https://funpay.com/",
            locale=config.locale,
            proxy=config.proxy,
            session_refresh_seconds=config.session_refresh_seconds,
        )
