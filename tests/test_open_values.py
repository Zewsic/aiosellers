import unittest

from aiosellers.playerok.graphql import GraphQLQuery
from aiosellers.playerok.listener import parse_chat_message
from aiosellers.playerok.schemas import (
    ChatList,
    ChatMessage,
    Item,
    ItemLog,
    ItemsSortOptions,
    UserType,
)


class OpenEnumTests(unittest.TestCase):
    def test_unknown_role_is_a_member(self) -> None:
        role = UserType("POSTMODERATOR")
        self.assertIs(UserType("POSTMODERATOR"), role)
        self.assertEqual(role.value, "POSTMODERATOR")
        self.assertIs(UserType.GAMES_AND_APPS.value, "GAMES_AND_APPS")

    def test_blank_role_is_rejected(self) -> None:
        with self.assertRaises(ValueError):
            UserType("")

    def test_chat_list_accepts_active_and_unknown_role(self) -> None:
        page = ChatList.model_validate(
            {
                "edges": [
                    {
                        "node": {
                            "id": "c1",
                            "type": "PM",
                            "status": "ACTIVE",
                            "lastMessage": {
                                "id": "m1",
                                "createdAt": "2026-10-11T00:00:00Z",
                                "isRead": True,
                                "user": {"id": "u1", "username": "mod", "role": "POSTMODERATOR"},
                            },
                        }
                    }
                ],
                "pageInfo": {},
                "totalCount": 1,
            }
        )
        chat = page.chats[0]
        self.assertEqual(chat.status.value, "ACTIVE")
        self.assertEqual(chat.last_message.user.role.value, "POSTMODERATOR")

    def test_message_keeps_item_when_game_is_only_a_profile(self) -> None:
        message = ChatMessage.model_validate(
            {
                "id": "m1",
                "createdAt": "2026-10-11T00:00:00Z",
                "isRead": False,
                "text": "{{ITEM_PAID}}",
                "game": {
                    "id": "g1",
                    "name": "Brawl Stars",
                    "slug": "brawl-stars",
                    "type": "MOBILE_GAME",
                    "logo": {"id": "f1", "url": "https://cdn.example/logo.png"},
                },
                "user": {"id": "u1", "username": "buyer", "role": "SECURITY"},
                "deal": {
                    "id": "d1",
                    "status": "PAID",
                    "direction": "OUT",
                    "item": {
                        "id": "item-1",
                        "name": "Аккаунт",
                        "price": 500,
                        "slug": "akkaunt",
                        "sellerType": "GAMES_AND_APPS",
                        "category": {"id": "cat-1"},
                        "dataFields": [
                            {
                                "id": "df1",
                                "label": "Почта",
                                "type": "ITEM_DATA",
                                "inputType": "INPUT",
                                "copyable": True,
                                "hidden": False,
                                "required": True,
                                "value": "a@b.c",
                            }
                        ],
                    },
                    "testimonial": {"id": "rev-1", "__typename": "TestimonialProfile"},
                },
            }
        )
        self.assertEqual(message.game.name, "Brawl Stars")
        self.assertIsNone(message.game.logo.filename)
        item = message.deal.item
        self.assertEqual(item.name, "Аккаунт")
        self.assertEqual(item.seller_type.value, "GAMES_AND_APPS")
        self.assertEqual(item.category_id, "cat-1")
        self.assertEqual(item.data_fields[0].value, "a@b.c")
        self.assertIsNone(message.deal.review.created_at)

    def test_fallback_keeps_the_item_name(self) -> None:
        message = parse_chat_message(
            {
                "id": "m1",
                "text": "{{ITEM_PAID}}",
                "createdAt": "2026-10-11T00:00:00Z",
                "isRead": False,
                "event": 1,
                "deal": {
                    "id": "d1",
                    "status": "PAID",
                    "direction": "OUT",
                    "item": {
                        "id": "item-1",
                        "name": "Аккаунт",
                        "price": 500,
                        "sellerType": "POSTMODERATOR",
                    },
                    "testimonial": {"id": "rev-1", "text": "норм", "rating": 5},
                },
            }
        )
        self.assertEqual(message.deal.item.name, "Аккаунт")
        self.assertEqual(message.deal.item.seller_type.value, "POSTMODERATOR")
        self.assertEqual(message.deal.review.text, "норм")

    def test_unknown_item_log_event(self) -> None:
        log = ItemLog.model_validate(
            {"id": "l1", "event": "PRIORITY_CHANGED", "createdAt": "2026-10-11T00:00:00Z"}
        )
        self.assertEqual(log.event.value, "PRIORITY_CHANGED")

    def test_item_accepts_unknown_status(self) -> None:
        item = Item.model_validate({"id": "i1", "status": "ARCHIVED"})
        self.assertEqual(item.status.value, "ARCHIVED")


class ItemQueryTests(unittest.TestCase):
    def test_created_sort_and_zero_minimum(self) -> None:
        body = GraphQLQuery.get_items(
            game_id="g1",
            minimal_price=0,
            maximal_price=1000,
            sort=ItemsSortOptions.CREATED_DESC,
        )
        self.assertEqual(body["variables"]["filter"]["price"], {"min": 0, "max": 1000})
        self.assertEqual(body["variables"]["sort"], {"field": "createdAt", "direction": "DESC"})

    def test_default_sort_is_not_rewritten_to_rating(self) -> None:
        body = GraphQLQuery.get_items(game_id="g1", sort=ItemsSortOptions.DEFAULT)
        self.assertIsNone(body["variables"]["sort"])

    def test_price_sort_stays_price(self) -> None:
        body = GraphQLQuery.get_items(game_id="g1", sort=ItemsSortOptions.PRICE_ASC)
        self.assertEqual(body["variables"]["sort"], {"field": "price", "direction": "ASC"})


if __name__ == "__main__":
    unittest.main()
