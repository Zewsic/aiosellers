from __future__ import annotations

from ..exceptions import RequestFailedError, WithdrawError
from ..parsers.finance import (
    parse_exchange,
    parse_finance_balance,
    parse_offer_balance,
    parse_transactions,
)
from ..schemas import Currency, Wallet
from ..transport.tls import response_json, response_text
from .base import RawBase


class RawFinance(RawBase):
    async def balance_page(self):
        async def run():
            response = await self.transport.request("GET", "account/balance")
            html = response_text(response)
            return parse_finance_balance(html), parse_transactions(html)

        return await self._call(run)

    async def transactions(self, cursor: str | None, filter: str, user_id: int):
        async def run():
            response = await self.transport.request(
                "POST",
                "users/transactions",
                data={"continue": cursor or "", "filter": filter, "user_id": user_id},
            )
            return parse_transactions(response_text(response))

        return await self._call(run)

    async def offer_balance(self, lot_id: int):
        async def run():
            response = await self.transport.request("GET", f"lots/offer?id={lot_id}")
            return parse_offer_balance(response_text(response))

        return await self._call(run)

    async def exchange(self, currency: Currency):
        before = self.transport.currency

        async def run():
            response = await self.transport.request(
                "POST",
                "account/switchCurrency",
                data={"cy": currency.code, "confirmed": "false"},
            )
            payload = response_json(response)
            if not isinstance(payload, dict):
                raise RequestFailedError("exchange failed", body=response_text(response))
            rate, current, switched = parse_exchange(payload, currency)
            if switched:
                self.transport.currency = currency
                return rate, before or currency
            self.transport.currency = current
            return rate, before or current

        return await self._call(run)

    async def withdraw(
        self, currency: Currency, wallet: Wallet, amount: float, address: str
    ) -> float:
        async def run():
            response = await self.transport.request(
                "POST",
                "withdraw/withdraw",
                data={
                    "currency_id": currency.code,
                    "ext_currency_id": wallet.wire,
                    "wallet": address,
                    "amount_int": str(amount),
                },
            )
            body = response_json(response)
            text = response_text(response)
            if isinstance(body, dict) and body.get("error"):
                raise WithdrawError(
                    body.get("msg"),
                    status_code=getattr(response, "status_code", None),
                    body=text,
                )
            return float(body.get("amount_ext"))

        return await self._call(run)

    async def wallets(self) -> list[dict]:
        async def run():
            response = await self.transport.request("GET", "account/wallets")
            from bs4 import BeautifulSoup

            soup = BeautifulSoup(response_text(response), "lxml")
            form = soup.select_one("form.details-editor")
            if form is None:
                return []
            rows = []
            for node in form.select("input"):
                name = node.get("name")
                if name:
                    rows.append({"name": name, "value": node.get("value") or ""})
            return rows

        return await self._call(run)

    async def save_wallets(self, rows: list[dict]) -> None:
        async def run():
            data = {"cat_id": "wallets"}
            for row in rows:
                data[row["name"]] = row["value"]
            if self.transport.csrf_token:
                data["csrf_token"] = self.transport.csrf_token
            response = await self.transport.request("POST", "account/details", data=data)
            body = response_json(response)
            if isinstance(body, dict) and body.get("error"):
                raise RequestFailedError(
                    str(body.get("msg") or body.get("error")),
                    status_code=getattr(response, "status_code", None),
                    body=response_text(response),
                )

        await self._call(run)
