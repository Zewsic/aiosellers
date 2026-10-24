import unittest

from aiosellers.funpay.core.utils import classify_message
from aiosellers.funpay.parsers.home import parse_home
from aiosellers.funpay.parsers.orders import parse_order_list
from aiosellers.funpay.schemas import MessageTypes, OrderSide, OrderStatuses, SubCategoryTypes

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

PURCHASED = (
    "Покупатель Bob оплатил заказ #AB12CD34. "
    "Bob, не забудьте потом нажать кнопку «Подтвердить выполнение заказа»."
)
CONFIRMED = (
    "The buyer Bob has confirmed that order #AB12CD34 has been fulfilled "
    "successfully and that the seller Ann has been paid."
)


def _order(order_id: str, marker: str) -> str:
    return f"""
    <a class="tc-item {marker}" href="/orders/{order_id}/">
      <div class="tc-order">#{order_id}</div>
      <div class="order-desc"><div>аккаунт</div></div>
      <div class="tc-price">100 ₽</div>
      <div class="media-user-name"><span data-href="/users/9/">Bob</span></div>
      <div class="text-muted">Steam</div>
    </a>
    """


class FunPayParserTests(unittest.IsolatedAsyncioTestCase):
    def test_classify_message(self) -> None:
        self.assertIs(classify_message(PURCHASED), MessageTypes.ORDER_PURCHASED)
        self.assertIs(classify_message(CONFIRMED), MessageTypes.ORDER_CONFIRMED)
        self.assertIs(classify_message("hello"), MessageTypes.NON_SYSTEM)
        self.assertIs(classify_message(""), MessageTypes.NON_SYSTEM)
        self.assertIs(classify_message(None), MessageTypes.NON_SYSTEM)
        self.assertIs(classify_message("Изображение"), MessageTypes.NON_SYSTEM)

    def test_home_ignores_the_first_promo_list(self) -> None:
        account = parse_home(HOME_HTML)
        self.assertEqual(account.username, "seller")
        self.assertEqual(account.id, 5)
        self.assertEqual(account.csrf_token, "t")
        self.assertEqual(len(account.categories), 1)
        kinds = {sub.type for sub in account.categories[0].subcategories}
        self.assertEqual(kinds, {SubCategoryTypes.CURRENCY, SubCategoryTypes.COMMON})
        ids = {sub.id for sub in account.categories[0].subcategories}
        self.assertEqual(ids, {81, 82})

    def test_sales_row_classes(self) -> None:
        html = _order("ABCD1234", "info") + _order("ABCD1235", "warning") + _order("ABCD1236", "")
        _cursor, orders = parse_order_list(html, side=OrderSide.SALE)
        self.assertEqual(
            [order.status for order in orders],
            [OrderStatuses.PAID, OrderStatuses.REFUNDED, OrderStatuses.CLOSED],
        )
        self.assertEqual(orders[0].buyer_username, "Bob")
        self.assertEqual(orders[0].buyer_id, 9)
        self.assertEqual(orders[0].price, 100)
