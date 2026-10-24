from __future__ import annotations

import json

from ..core.utils import parse_currency
from ..exceptions import LotSavingError, RaiseError, RequestFailedError
from ..parsers.home import parse_categories
from ..parsers.lots import parse_chip_form, parse_my_lots, parse_offer_form, parse_public_lots
from ..schemas import CalcResult, CategorySnapshot, SubCategoryTypes
from ..transport.tls import response_json, response_text
from .base import RawBase


def _saving_error(body: dict, fields: dict, text: str) -> LotSavingError | None:
    errors = body.get("errors")
    error = body.get("error")
    if not errors and not error:
        return None
    parsed: dict[str, str] = {}
    if isinstance(errors, dict):
        parsed = {str(key): str(value) for key, value in errors.items()}
    elif errors:
        parsed["errors"] = str(errors)
    if error:
        parsed.setdefault("error", str(error))
    offer = fields.get("offer_id")
    lot_id = int(offer) if isinstance(offer, str) and offer.isdigit() else None
    return LotSavingError(str(error) if error else None, lot_id=lot_id, errors=parsed, body=text)


class RawLots(RawBase):
    async def public(self, subcategory_id: int, kind: SubCategoryTypes):
        path = (
            f"chips/{subcategory_id}/"
            if kind is SubCategoryTypes.CURRENCY
            else f"lots/{subcategory_id}/"
        )

        async def run():
            response = await self.transport.request("GET", path)
            return parse_public_lots(
                response_text(response), subcategory_id=subcategory_id, kind=kind
            )

        return await self._call(run)

    async def mine(self, subcategory_id: int):
        async def run():
            response = await self.transport.request("GET", f"lots/{subcategory_id}/trade")
            return parse_my_lots(response_text(response), subcategory_id=subcategory_id)

        return await self._call(run)

    async def offer_page(self, lot_id: int) -> str:
        async def run():
            response = await self.transport.request("GET", f"lots/offer?id={lot_id}")
            return response_text(response)

        return await self._call(run)

    async def edit_form(self, lot_id: int, node_id: int | None):
        path = f"lots/offerEdit?offer={lot_id}"
        if node_id is not None:
            path += f"&node={node_id}"

        async def run():
            response = await self.transport.request("GET", path)
            return parse_offer_form(response_text(response), lot_id)

        return await self._call(run)

    async def chip_form(self, subcategory_id: int):
        async def run():
            response = await self.transport.request("GET", f"chips/{subcategory_id}/trade")
            return parse_chip_form(response_text(response), subcategory_id)

        return await self._call(run)

    async def save_offer(self, fields: dict) -> None:
        async def run():
            response = await self.transport.request("POST", "lots/offerSave", data=fields)
            text = response_text(response)
            body = response_json(response)
            if isinstance(body, dict):
                error = _saving_error(body, fields, text)
                if error is not None:
                    raise error

        await self._call(run)

    async def save_chips(self, fields: dict) -> None:
        async def run():
            response = await self.transport.request("POST", "chips/saveOffers", data=fields)
            text = response_text(response)
            body = response_json(response)
            if isinstance(body, dict):
                error = _saving_error(body, fields, text)
                if error is not None:
                    raise error

        await self._call(run)

    async def raise_lots(self, category_id: int, node_id: int, node_ids: list[int]) -> int:
        async def run():
            response = await self.transport.request(
                "POST",
                "lots/raise",
                data={"game_id": category_id, "node_id": node_id, "node_ids[]": node_ids},
            )
            text = response_text(response)
            body = response_json(response)
            if isinstance(body, dict) and not body.get("error") and not body.get("url"):
                wait = body.get("wait")
                return int(wait) if wait not in (None, "") else 0
            message = body.get("msg") if isinstance(body, dict) else None
            wait = body.get("wait") if isinstance(body, dict) else None
            raise RaiseError(
                category_id,
                str(message) if message else None,
                int(wait or 7200),
                status_code=getattr(response, "status_code", None),
                body=text,
            )

        return await self._call(run)

    async def calc(
        self,
        kind: SubCategoryTypes,
        subcategory_id: int,
        game_id: int | None,
        price: float,
    ) -> CalcResult:
        if kind is SubCategoryTypes.CURRENCY and game_id is None:
            raise ValueError("game_id is required for currency calc")
        if kind is SubCategoryTypes.COMMON:
            path = "lots/calc"
            data = {"nodeId": subcategory_id, "price": price}
        else:
            path = "chips/calc"
            data = {"game": game_id, "price": price}

        async def run():
            response = await self.transport.request("POST", path, data=data)
            body = response_json(response)
            if isinstance(body, dict) and body.get("error"):
                raise RequestFailedError(
                    str(body.get("error")),
                    status_code=getattr(response, "status_code", None),
                    body=response_text(response),
                )
            methods = []
            for method in (body or {}).get("methods") or []:
                raw_price = str(method.get("price") or "0").replace(" ", "")
                methods.append(
                    (
                        str(method.get("name") or ""),
                        float(raw_price),
                        parse_currency(str(method.get("unit") or "")),
                    )
                )
            return CalcResult(methods=methods)

        return await self._call(run)

    async def hide_all(self, user_id: int, hidden: bool) -> None:
        async def run():
            response = await self.transport.request(
                "POST",
                "trade/tradeLockSettings",
                data={"userId": user_id, "mode": "1" if hidden else "0"},
            )
            body = response_json(response)
            if isinstance(body, dict) and body.get("error"):
                raise RequestFailedError(
                    str(body.get("msg") or body.get("error")),
                    status_code=getattr(response, "status_code", None),
                    body=response_text(response),
                )

        await self._call(run)

    async def search(self, query: str) -> list[CategorySnapshot]:
        async def run():
            response = await self.transport.request(
                "POST", "games/promoFilter", data={"query": query}
            )
            text = response_text(response)
            payload = None
            stripped = text.lstrip()
            if stripped.startswith("{") or stripped.startswith("["):
                try:
                    payload = json.loads(text)
                except json.JSONDecodeError:
                    payload = None
            if isinstance(payload, dict) and "html" in payload:
                return parse_categories(payload.get("html") or "")
            if isinstance(payload, list):
                categories = []
                for index, item in enumerate(payload):
                    if not isinstance(item, dict) or "id" not in item or "name" not in item:
                        raise RequestFailedError("search failed", body=text)
                    categories.append(
                        CategorySnapshot(
                            id=int(item["id"]),
                            name=str(item["name"]),
                            position=index,
                            subcategories=[],
                        )
                    )
                return categories
            if payload is None:
                return parse_categories(text)
            raise RequestFailedError("search failed", body=text)

        return await self._call(run)
