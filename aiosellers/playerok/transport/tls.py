import os
from typing import Any, Literal

from ..core.config import PlayerokConfig
from ..core.constants import CLOUDFLARE_SIGNATURES
from ..core.exceptions import CloudflareDetected


class PlayerokTransport:
    """
    Shared network transport for a single Playerok session.

    Owns one underlying TLS/HTTP client (tls_requests.AsyncClient) that is reused by all raw services.
    """

    def __init__(self, access_token: str | None = None, config: PlayerokConfig | None = None):
        # Lazy import so `aiosellers.playerok` can be imported without optional deps installed
        # (useful for tooling/tests in environments without network access).
        from tls_requests import AsyncClient  # type: ignore

        self._access_token = access_token or os.getenv("PLAYEROK_ACCESS_TOKEN")
        self._config = config or PlayerokConfig()

        if not self._access_token:
            raise RuntimeError(
                "Please provide playerok access token or fill PLAYEROK_ACCESS_TOKEN environment variable."
            )

        self._client = AsyncClient(
            cookies={"token": self._access_token},
            headers=self._config.headers,
            timeout=self._config.request_timeout,
        )

    @property
    def config(self) -> PlayerokConfig:
        return self._config

    @staticmethod
    def _raise_if_cloudflare(response: Any) -> None:
        # tls_requests.Response has .text property
        if any(sig in response.text for sig in CLOUDFLARE_SIGNATURES):
            raise CloudflareDetected("The cloudflare protection is detected.")

    async def request(
        self,
        method: Literal["get", "post"],
        url: str,
        payload: dict[str, Any] | None = None,
        *,
        headers: dict[str, str] | None = None,
        files: dict[str, Any] | None = None,
    ) -> Any:
        request_headers = self._config.headers.copy()
        if headers is not None:
            request_headers.update(headers)

        if not url.startswith("http"):
            url = self._config.base_url + url

        payload = payload or {}

        if method == "get":
            response = await self._client.get(url=url, headers=request_headers, params=payload)
        elif method == "post":
            if files:
                # Let the client set proper multipart boundary.
                request_headers.pop("content-type", None)
                response = await self._client.post(
                    url=url, headers=request_headers, data=payload, files=files
                )
            else:
                response = await self._client.post(url=url, headers=request_headers, json=payload)
        else:
            raise RuntimeError(f"Unsupported HTTP method: {method}")

        self._raise_if_cloudflare(response)
        return response

    async def download(self, url: str) -> bytes:
        """Download a file by URL. Retries three times, same as PlayerokAPI."""
        last_error: Exception | str | None = None
        for _ in range(3):
            try:
                response = await self._client.get(
                    url, headers={"user-agent": self._config.user_agent}
                )
            except Exception as exc:
                last_error = exc
                continue
            status = getattr(response, "status_code", None)
            if status == 200:
                content = getattr(response, "content", None)
                if content is None:
                    text = getattr(response, "text", "")
                    return text.encode()
                return content
            last_error = f"HTTP {status}"
        raise RuntimeError(f"Failed to download {url}: {last_error}")

    async def close(self) -> None:
        await self._client.aclose()
