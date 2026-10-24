from __future__ import annotations

import asyncio
import inspect
import json
import re
import time
from typing import Any
from urllib.parse import urlencode

from bs4 import BeautifulSoup

from ..core.config import FunPayConfig
from ..exceptions import RateLimitedError, RequestFailedError, UnauthorizedError
from ..parsers.home import parse_home

_LOGIN = "account/login"


def response_json(response: Any) -> Any:
    if hasattr(response, "json"):
        try:
            data = response.json()
        except Exception:
            data = None
        else:
            if not inspect.isawaitable(data):
                return data
    text = response_text(response)
    return json.loads(text or "null")


def response_text(response: Any) -> str:
    text = getattr(response, "text", "") or ""
    if isinstance(text, bytes):
        return text.decode("utf-8", "replace")
    return str(text)


class FunPayTransport:
    """One tls_requests session for a FunPay golden_key."""

    def __init__(self, config) -> None:
        from tls_requests import AsyncClient  # type: ignore

        self._config = FunPayConfig.from_client(config)
        self.account_id: int | None = None
        self.username: str | None = None
        self.csrf_token: str | None = None
        self.locale: str | None = None
        self.active_sales: int = 0
        self.active_purchases: int = 0
        self.categories: list = []
        self.currency = None
        self.last_refresh: float = 0.0
        self.rate_limited_until: float = 0.0
        self._lock = asyncio.Lock()
        signature = inspect.signature(AsyncClient.__init__)
        kwargs: dict[str, Any] = {
            "cookies": {"golden_key": self._config.golden_key, "cookie_prefs": "1"},
            "timeout": self._config.request_timeout,
            "headers": {"user-agent": self._config.user_agent, "accept": "*/*"},
        }
        if self._config.proxy:
            if "proxy" in signature.parameters:
                kwargs["proxy"] = self._config.proxy
            elif "proxies" in signature.parameters:
                kwargs["proxies"] = self._config.proxy
            else:
                raise TypeError("installed tls_requests cannot proxy")
        self._client = AsyncClient(**kwargs)

    @property
    def config(self) -> FunPayConfig:
        return self._config

    async def refresh_profile(self, *, force: bool = False) -> None:
        now = time.monotonic()
        if (
            not force
            and self.last_refresh
            and now - self.last_refresh <= self._config.session_refresh_seconds
        ):
            return
        response = await self.request("GET", "/")
        snapshot = parse_home(response_text(response))
        if not snapshot.username:
            raise UnauthorizedError(
                "unauthorized",
                status_code=getattr(response, "status_code", None),
                body=response_text(response),
            )
        self.account_id = snapshot.id
        self.username = snapshot.username
        if snapshot.csrf_token:
            self.csrf_token = snapshot.csrf_token
        if snapshot.locale:
            self.locale = snapshot.locale
        self.active_sales = snapshot.active_sales
        self.active_purchases = snapshot.active_purchases
        if not self.categories:
            self.categories = list(snapshot.categories)
        self.last_refresh = time.monotonic()

    async def request(
        self,
        method: str,
        path: str,
        *,
        data: dict | None = None,
        json_body: Any = None,
        headers: dict[str, str] | None = None,
        locale: str | None = None,
        raise_not_200: bool = True,
    ) -> Any:
        async with self._lock:
            return await self._exchange(
                method,
                path,
                data=data,
                json_body=json_body,
                headers=headers,
                locale=locale,
                raise_not_200=raise_not_200,
            )

    async def upload(self, path: str, filename: str, content: bytes, content_type: str) -> Any:
        async with self._lock:
            return await self._exchange(
                "POST",
                path,
                files={"file": (filename, content, content_type)},
                raise_not_200=False,
            )

    async def close(self) -> None:
        close = getattr(self._client, "aclose", None) or getattr(self._client, "close", None)
        if close is None:
            return
        result = close()
        if inspect.isawaitable(result):
            await result

    def _url(self, path: str, locale: str | None) -> str:
        if path.startswith("http://") or path.startswith("https://"):
            return path
        relative = path.lstrip("/")
        base = self._config.base_url.rstrip("/") + "/"
        if relative.startswith("api/"):
            return base + relative
        for prefix in ("en/", "uk/"):
            if relative.startswith(prefix):
                relative = relative[len(prefix) :]
        effective = locale if locale is not None else self._config.locale
        if effective in {"en", "uk"}:
            relative = f"{effective}/{relative}" if relative else f"{effective}/"
        return base + relative

    def _fields(self, data: dict) -> dict[str, str | list[str]]:
        payload = dict(data)
        if "csrf_token" not in payload and self.csrf_token:
            payload["csrf_token"] = self.csrf_token
        fields: dict[str, str | list[str]] = {}
        for key, value in payload.items():
            if isinstance(value, bool):
                if value:
                    fields[str(key)] = "1"
                continue
            if value is None:
                continue
            if isinstance(value, list):
                fields[str(key)] = [str(item) for item in value]
                continue
            fields[str(key)] = str(value)
        return fields

    async def _exchange(
        self,
        method: str,
        path: str,
        *,
        data: dict | None = None,
        json_body: Any = None,
        files: dict | None = None,
        headers: dict[str, str] | None = None,
        locale: str | None = None,
        raise_not_200: bool = True,
    ) -> Any:
        verb = method.upper()
        url = self._url(path, locale)
        effective = locale if locale is not None else self._config.locale
        if verb == "GET" and effective and self.locale and effective != self.locale:
            url += ("&" if "?" in url else "?") + urlencode({"setlocale": effective})
        request_headers = {
            "accept": "*/*",
            "user-agent": self._config.user_agent,
        }
        if verb == "POST":
            request_headers["x-requested-with"] = "XMLHttpRequest"
        if headers:
            request_headers.update(headers)
        post: dict[str, Any] = {}
        if files is not None:
            request_headers.pop("content-type", None)
            request_headers.pop("Content-Type", None)
            post["files"] = files
        elif json_body is not None:
            post["json"] = json_body
        elif data is not None:
            post["data"] = self._fields(data)
        if verb == "GET":
            response = await self._client.get(url, headers=request_headers)
        else:
            response = await self._client.post(url, headers=request_headers, **post)
        self._absorb(response)
        self._raise_for_status(response, raise_not_200=raise_not_200)
        return response

    def _absorb(self, response: Any) -> None:
        text = response_text(response)
        if "data-app-data" in text and getattr(response, "status_code", 200) == 200:
            soup = BeautifulSoup(text, "lxml")
            body = soup.find("body")
            raw = body.get("data-app-data") if body is not None else None
            if raw:
                try:
                    app = json.loads(raw)
                except json.JSONDecodeError:
                    app = None
                if isinstance(app, dict):
                    if app.get("csrf-token"):
                        self.csrf_token = app["csrf-token"]
                    if app.get("locale"):
                        self.locale = app["locale"]
        php = _phpsessid(response)
        if not php:
            return
        jar = self._client.cookies
        if hasattr(jar, "set"):
            try:
                jar.set("PHPSESSID", php)
                return
            except Exception:
                try:
                    jar.set("PHPSESSID", php, domain="funpay.com")
                    return
                except Exception:
                    return
        if hasattr(jar, "update"):
            jar.update({"PHPSESSID": php})

    def _raise_for_status(self, response: Any, *, raise_not_200: bool) -> None:
        code = getattr(response, "status_code", None)
        text = response_text(response)
        if code == 403 or _is_login(response):
            raise UnauthorizedError("unauthorized", status_code=code, body=text)
        if code == 429:
            self.rate_limited_until = time.monotonic() + 60
            raise RateLimitedError("rate limited", status_code=code, body=text)
        if raise_not_200 and code not in (None, 200):
            raise RequestFailedError(f"HTTP {code}", status_code=code, body=text)


def _ends_login(value: str) -> bool:
    return value.split("?", 1)[0].rstrip("/").endswith(_LOGIN)


def _header_text(headers: Any, name: str) -> str:
    if headers is None or not hasattr(headers, "get"):
        return ""
    try:
        value = headers.get(name)
    except Exception:
        return ""
    if value is None:
        return ""
    if isinstance(value, (list, tuple)):
        return " ".join(str(item) for item in value)
    return str(value)


def _is_login(response: Any) -> bool:
    found: list[str] = [str(getattr(response, "url", "") or "")]
    headers = getattr(response, "headers", None)
    found.append(_header_text(headers, "location"))
    for item in getattr(response, "history", []) or []:
        found.append(str(getattr(item, "url", "") or ""))
        found.append(_header_text(getattr(item, "headers", None), "location"))
    return any(value and _ends_login(value) for value in found)


def _phpsessid(response: Any) -> str | None:
    cookies = getattr(response, "cookies", None)
    if cookies is not None and hasattr(cookies, "get"):
        try:
            value = cookies.get("PHPSESSID")
        except Exception:
            value = None
        if value:
            return str(value)
    headers = getattr(response, "headers", None)
    blob = _header_text(headers, "set-cookie")
    match = re.search(r"PHPSESSID=([^;,\s]+)", blob)
    return match.group(1) if match else None
