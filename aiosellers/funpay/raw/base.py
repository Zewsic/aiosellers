from __future__ import annotations

import asyncio
import time

from ..exceptions import RateLimitedError
from ..transport.tls import FunPayTransport


class RawBase:
    def __init__(self, transport: FunPayTransport) -> None:
        self.transport = transport

    async def _retry(self, factory):
        try:
            return await factory()
        except RateLimitedError:
            delay = min(60.0, max(0.0, self.transport.rate_limited_until - time.monotonic()))
            await asyncio.sleep(delay)
            return await factory()

    async def _call(self, fn, *, retry: bool = True):
        async def run():
            await self.transport.refresh_profile()
            return await fn()

        if retry:
            return await self._retry(run)
        return await run()
