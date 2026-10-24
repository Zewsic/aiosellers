from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

from ..entities.lot import ChipFields, Lot, LotFields, MyLot
from ..exceptions import AccountNotInitiatedError
from ..schemas import CalcResult, LotShortcut, MyLotShortcut, SubCategoryTypes

if TYPE_CHECKING:
    from ..funpay import FunPay


class LotAPI:
    def __init__(self, client: FunPay) -> None:
        self._client = client

    def _require(self):
        if self._client._raw is None or self._client._transport is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        return self._client._raw

    def _public(self, snap: LotShortcut) -> Lot:
        lot = Lot(
            id=snap.id,
            server=snap.server,
            description=snap.description,
            price=snap.price,
            subcategory_id=snap.subcategory_id,
            seller_id=snap.seller_id,
            seller_username=snap.seller_username,
            auto_delivery=snap.auto_delivery,
            html=snap.html,
        )
        return self._client.remember("lots", snap.id, lot)

    def _mine(self, snap: MyLotShortcut) -> MyLot:
        lot = MyLot(
            id=snap.id,
            description=snap.description,
            price=snap.price,
            active=snap.active,
            auto_delivery=snap.auto_delivery,
            amount=snap.amount,
            server=snap.server,
            subcategory_id=snap.subcategory_id,
            html=snap.html,
        )
        return self._client.remember("lots", snap.id, lot)

    async def list_public(
        self, subcategory_id: int, *, kind: SubCategoryTypes = SubCategoryTypes.COMMON
    ) -> list[Lot]:
        rows = await self._require().lots.public(subcategory_id, kind)
        return [self._public(row) for row in rows]

    async def list_self(self, subcategory_id: int) -> list[MyLot]:
        rows = await self._require().lots.mine(subcategory_id)
        return [self._mine(row) for row in rows]

    async def fields(self, lot_id: int = 0, *, node_id: int | None = None) -> LotFields:
        data, currency = await self._require().lots.edit_form(lot_id, node_id)
        fields = LotFields(lot_id, data, subcategory_id=node_id, currency=currency)
        fields._client = self._client
        return fields

    async def chip_fields(self, subcategory_id: int) -> ChipFields:
        data = await self._require().lots.chip_form(subcategory_id)
        fields = ChipFields(subcategory_id, data)
        fields._client = self._client
        return fields

    async def save(self, fields: LotFields | ChipFields) -> None:
        if isinstance(fields, LotFields):
            fields.renew()
            await self._require().lots.save_offer(fields.fields)
            return
        await self._require().lots.save_chips(fields.fields)

    async def delete(self, lot_id: int) -> None:
        await self._require().lots.save_offer({"offer_id": str(lot_id), "deleted": "1"})

    async def raise_category(
        self,
        category_id: int,
        *,
        subcategory_ids: list[int] | None = None,
        exclude: list[int] | None = None,
    ) -> int:
        self._require()
        transport = self._client._transport
        if transport is None:
            raise RuntimeError("Client is not started. Call start() or start_polling() first.")
        category = next((item for item in transport.categories if item.id == category_id), None)
        if category is None:
            raise ValueError(f"Unknown category: {category_id}")
        excluded = set(exclude or [])
        subs = [
            sub
            for sub in category.subcategories
            if sub.type is SubCategoryTypes.COMMON and sub.id not in excluded
        ]
        if subcategory_ids is not None:
            wanted = set(subcategory_ids)
            subs = [sub for sub in subs if sub.id in wanted]
        if not subs:
            raise ValueError("No common subcategories to raise")
        return await self._require().lots.raise_lots(
            category_id, subs[0].id, [sub.id for sub in subs]
        )

    async def calc(
        self,
        subcategory_id: int,
        *,
        kind: SubCategoryTypes = SubCategoryTypes.COMMON,
        price: float = 1000,
        game_id: int | None = None,
    ) -> CalcResult:
        return await self._require().lots.calc(kind, subcategory_id, game_id, price)

    async def hide_all(self, hidden: bool = True) -> None:
        account_id = self._client.account_id
        if account_id is None:
            raise AccountNotInitiatedError("account is not initiated")
        await self._require().lots.hide_all(account_id, hidden)

    async def upload_offer_image(self, image: bytes | str | Path) -> int:
        return await self._client.chats.upload_image(image, kind="offer")
