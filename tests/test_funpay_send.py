import unittest


from aiosellers.funpay.exceptions import MessageNotDeliveredError
from aiosellers.funpay.raw.chats import RawChats

BOOKMARK = """
<a class="contact-item" data-id="3" data-node-msg="{node}" data-user-msg="9">
  <div class="media-user-name">Ann</div>
  <div class="contact-item-message">hi</div>
</a>
"""


class _Response:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def json(self):
        return self._payload


class _Transport:
    account_id = 5
    username = "me"

    def __init__(self, pages: list[dict]) -> None:
        self.pages = pages
        self.gets = 0

    async def refresh_profile(self) -> None:
        return None

    async def request(self, method, url, **kwargs):
        del url
        if method == "GET":
            self.gets += 1
            return _Response(
                {
                    "chat": {
                        "node": {"name": "users-5-9"},
                        "messages": [
                            {
                                "id": 11,
                                "author": 5,
                                "html": '<div class="chat-msg-text">old</div>',
                            },
                            {
                                "id": 12,
                                "author": 5,
                                "html": '<div class="chat-msg-text">new</div>',
                            },
                        ],
                    }
                }
            )
        data = kwargs.get("data") or {}
        request = data.get("request") or ""
        if "chat_message" in request:
            return _Response({"objects": [], "response": {"error": None}})
        node = self.pages.pop(0)
        return _Response(
            {
                "objects": [
                    {
                        "type": "chat_bookmarks",
                        "data": {"html": BOOKMARK.format(node=node)},
                    }
                ],
                "response": False,
            }
        )


class FunPaySendTests(unittest.IsolatedAsyncioTestCase):
    async def test_empty_runner_uses_the_new_own_message(self) -> None:
        transport = _Transport([11, 12])
        sent = await RawChats(transport).send(3, "new", None, False)
        self.assertEqual(sent.id, 12)
        self.assertEqual(transport.gets, 1)

    async def test_runner_error_is_not_treated_as_sent(self) -> None:
        transport = _Transport([11, 12])

        async def request(method, url, **kwargs):
            del method, url
            data = kwargs.get("data") or {}
            if "chat_message" in (data.get("request") or ""):
                return _Response({"objects": [], "response": {"error": "denied"}})
            return await _Transport.request(transport, "POST", "runner/", **kwargs)

        transport.request = request
        with self.assertRaises(MessageNotDeliveredError):
            await RawChats(transport).send(3, "new", None, False)
        self.assertEqual(transport.gets, 0)


if __name__ == "__main__":
    unittest.main()
