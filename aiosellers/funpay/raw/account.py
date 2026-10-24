from __future__ import annotations

import json

from ..parsers.home import parse_buyer_viewing, parse_home, parse_user
from ..schemas import BuyerViewing
from ..transport.tls import response_json
from .base import RawBase


class RawAccount(RawBase):
    async def _post_runner(self, objects: list[dict], request: dict | None):
        response = await self.transport.request(
            "POST",
            "runner/",
            data={
                "objects": json.dumps(objects),
                "request": "false" if request is None else json.dumps(request),
            },
            headers={"content-type": "application/x-www-form-urlencoded; charset=UTF-8"},
        )
        return response_json(response)

    async def runner_poll(self, objects: list[dict], request: dict | None = None):
        return await self._post_runner(objects, request)

    async def runner(self, objects: list[dict], request: dict | None = None):
        return await self._call(lambda: self._post_runner(objects, request))

    async def home(self):
        async def run():
            response = await self.transport.request("GET", "/")
            return parse_home(response.text)

        return await self._call(run)

    async def user(self, user_id: int):
        async def run():
            response = await self.transport.request("GET", f"users/{user_id}/")
            return parse_user(response.text, user_id)

        return await self._call(run)

    async def buyer_viewing(self, buyer_id: int) -> BuyerViewing:
        payload = await self.runner(
            [{"type": "c-p-u", "id": str(buyer_id), "tag": "00000000", "data": False}]
        )
        for item in payload.get("objects") or []:
            if item.get("type") == "c-p-u" and str(item.get("id")) == str(buyer_id):
                return parse_buyer_viewing(item, buyer_id)
        return BuyerViewing(buyer_id=buyer_id)
