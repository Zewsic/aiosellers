import json
import unittest
from types import SimpleNamespace
from unittest.mock import patch

from aiosellers.funpay import FunPay
from aiosellers.funpay.entities.lot import LotFields
from aiosellers.funpay.raw import RawAPI
from aiosellers.funpay.raw.chats import RawChats
from aiosellers.funpay.transport.tls import FunPayTransport

HOME_HTML = """
<html><body data-app-data='{"userId":5,"csrf-token":"t","locale":"ru"}'>
<div class="user-link-name">seller</div>
<span class="badge badge-trade">2</span>
<span class="badge badge-orders">3</span>
<div class="promo-game-list"></div>
<div class="promo-game-list">
  <div class="promo-game-item">
    <div class="game-title" data-id="10"><a href="/games/10/">Game</a></div>
    <ul class="list-inline" data-id="10">
      <li><a href="/chips/81/">Gold</a></li>
      <li><a href="/lots/82/">Accounts</a></li>
    </ul>
  </div>
</div>
</body></html>
"""


class _Transport:
    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.csrf_token = "t"
        self.account_id = 5
        self.username = "me"
        self.locale = "ru"
        self.rate_limited_until = 0

    async def refresh_profile(self, force: bool = False) -> None:
        del force

    async def request(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        return SimpleNamespace(status_code=200, text="{}", json=lambda: {})


def _sent(chat_id: int) -> dict:
    return {
        "response": {},
        "objects": [
            {
                "type": "chat_node",
                "data": {
                    "node": {"id": chat_id, "name": "users-5-9"},
                    "messages": [
                        {
                            "id": 15,
                            "author": 5,
                            "html": '<div class="chat-msg-text">hi</div>',
                        }
                    ],
                },
            }
        ],
    }


class FunPayClientTests(unittest.IsolatedAsyncioTestCase):
    def test_lot_fields_renew_writes_form(self) -> None:
        fields = LotFields(1, {"fields[summary][ru]": "Hi", "price": "10"})
        self.assertEqual(fields.title_ru, "Hi")
        self.assertFalse(fields.active)
        fields.title_ru = "Yo"
        fields.renew()
        self.assertEqual(fields.fields["fields[summary][ru]"], "Yo")
        self.assertEqual(fields.fields["active"], "")

    async def test_delete_posts_deleted_without_editor_get(self) -> None:
        transport = _Transport()
        client = FunPay("key")
        client._account_id = 5
        client._transport = transport  # type: ignore[assignment]
        client._raw = RawAPI(transport)  # type: ignore[arg-type]
        await client.lots.delete(7)
        paths = [path for _method, path, _kwargs in transport.calls]
        self.assertFalse(any("offerEdit" in path for path in paths))
        data = transport.calls[-1][2]["data"]
        self.assertEqual(data["offer_id"], "7")
        self.assertEqual(data["deleted"], "1")

    async def test_send_payload_marks_text_and_image(self) -> None:
        transport = _Transport()

        async def request(method, path, **kwargs):
            transport.calls.append((method, path, kwargs))
            return SimpleNamespace(status_code=200, text="{}", json=lambda: _sent(3))

        transport.request = request  # type: ignore[method-assign]
        raw = RawChats(transport)  # type: ignore[arg-type]
        await raw.send(3, "hi", None, False)
        sent = json.loads(transport.calls[-1][2]["data"]["request"])
        self.assertEqual(sent["data"]["content"], "\u2061hi")

        await raw.send(3, None, 9, False)
        image = json.loads(transport.calls[-1][2]["data"]["request"])
        self.assertEqual(image["data"]["content"], "")
        self.assertEqual(image["data"]["image_id"], 9)

    async def test_context_manager_sets_and_clears_account_id(self) -> None:
        class _Response:
            status_code = 200
            text = HOME_HTML
            headers: dict = {}
            url = "https://funpay.com/"

            def json(self):
                return {}

        async def request(self, method, path, **kwargs):
            del self, method, path, kwargs
            return _Response()

        with patch.object(FunPayTransport, "request", request):
            async with FunPay("key") as client:
                self.assertEqual(client.account_id, 5)
            self.assertIsNone(client.account_id)
