from __future__ import annotations

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from ..core.utils import format_form_number
from ..schemas import Currency
from .user import _detached

if TYPE_CHECKING:
    from ..funpay import FunPay


@dataclass(slots=True)
class LotFields:
    """Mutable offer form.

    Creating a lot::

        fields = await client.lots.fields(0, node_id=node)
        fields.title_ru = "Title"
        fields.price = 100
        fields.amount = 1
        fields.active = True
        await client.lots.save(fields)
    """

    lot_id: int
    fields: dict[str, str]
    subcategory_id: int | None = None
    currency: Currency = Currency.UNKNOWN
    title_ru: str | None = None
    title_en: str | None = None
    description_ru: str | None = None
    description_en: str | None = None
    payment_msg_ru: str | None = None
    payment_msg_en: str | None = None
    images: list[int] = field(default_factory=list)
    auto_delivery: bool | None = None
    secrets: list[str] = field(default_factory=list)
    amount: int | None = None
    price: float | None = None
    active: bool = False
    deactivate_after_sale: bool | None = None
    _client: FunPay | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.fields = dict(self.fields)
        self._load()

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.lots.fields()")
        return self._client

    def _load(self) -> None:
        form = self.fields
        self.title_ru = form.get("fields[summary][ru]")
        self.title_en = form.get("fields[summary][en]")
        self.description_ru = form.get("fields[desc][ru]")
        self.description_en = form.get("fields[desc][en]")
        self.payment_msg_ru = form.get("fields[payment_msg][ru]")
        self.payment_msg_en = form.get("fields[payment_msg][en]")
        images = form.get("fields[images]") or ""
        self.images = [int(part) for part in images.split(",") if part.strip().isdigit()]
        secrets = form.get("secrets") or ""
        self.secrets = secrets.split("\n") if secrets else []
        self.price = float(form["price"]) if form.get("price") not in (None, "") else None
        self.amount = int(float(form["amount"])) if form.get("amount") not in (None, "") else None
        self.active = form.get("active") == "on"
        if "auto_delivery" in form:
            self.auto_delivery = form.get("auto_delivery") == "on"
        else:
            self.auto_delivery = None
        if "deactivate_after_sale" in form:
            self.deactivate_after_sale = form.get("deactivate_after_sale") == "on"
        else:
            self.deactivate_after_sale = None
        if self.subcategory_id is None and str(form.get("node_id") or "").isdigit():
            self.subcategory_id = int(form["node_id"])

    def renew(self) -> dict[str, str]:
        form = self.fields
        form["fields[summary][ru]"] = self.title_ru or ""
        form["fields[summary][en]"] = self.title_en or ""
        form["fields[desc][ru]"] = self.description_ru or ""
        form["fields[desc][en]"] = self.description_en or ""
        form["fields[payment_msg][ru]"] = self.payment_msg_ru or ""
        form["fields[payment_msg][en]"] = self.payment_msg_en or ""
        form["fields[images]"] = ",".join(str(image) for image in self.images)
        form["secrets"] = "\n".join(self.secrets)
        if self.price is None:
            form.pop("price", None)
        else:
            form["price"] = format_form_number(self.price)
        if self.amount is None:
            form.pop("amount", None)
        else:
            form["amount"] = str(self.amount)
        form["active"] = "on" if self.active else ""
        if self.auto_delivery is None:
            form.pop("auto_delivery", None)
        else:
            form["auto_delivery"] = "on" if self.auto_delivery else ""
        if self.deactivate_after_sale is None:
            form.pop("deactivate_after_sale", None)
        else:
            form["deactivate_after_sale"] = "on" if self.deactivate_after_sale else ""
        form["offer_id"] = str(self.lot_id)
        client = self._client
        token = None
        if client is not None and client._transport is not None:
            token = client._transport.csrf_token
        if token:
            form["csrf_token"] = token
        return form

    def set_field(self, key: str, value) -> None:
        self.fields[str(key)] = "" if value is None else str(value)

    async def save(self) -> None:
        await self._require_client().lots.save(self)


@dataclass(slots=True)
class ChipFields:
    """Chips are a table of offers. Edit ``fields`` and call ``save``."""

    subcategory_id: int
    fields: dict[str, str]
    _client: FunPay | None = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        self.fields = dict(self.fields)

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.lots.chip_fields()")
        return self._client

    def set_field(self, key: str, value) -> None:
        self.fields[str(key)] = "" if value is None else str(value)

    async def save(self) -> None:
        await self._require_client().lots.save(self)


@dataclass(slots=True)
class Lot:
    id: str
    server: str | None = None
    description: str | None = None
    price: float = 0
    subcategory_id: int = 0
    seller_id: int | None = None
    seller_username: str | None = None
    auto_delivery: bool = False
    html: str = ""
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.lots.list_public()")
        return self._client


@dataclass(slots=True)
class MyLot:
    id: str
    description: str | None = None
    price: float | None = None
    active: bool = False
    auto_delivery: bool = False
    amount: int | None = None
    server: str | None = None
    subcategory_id: int = 0
    html: str = ""
    _client: FunPay | None = field(default=None, repr=False, compare=False, init=False)

    def _require_client(self) -> FunPay:
        if self._client is None:
            raise _detached(self.__class__.__name__, "client.lots.list_self()")
        return self._client

    async def edit(self) -> LotFields:
        return await self._require_client().lots.fields(int(self.id))

    async def delete(self) -> None:
        await self._require_client().lots.delete(int(self.id))

    async def set_active(self, active: bool) -> None:
        fields = await self.edit()
        fields.active = active
        await fields.save()

    async def set_price(self, price: float) -> None:
        fields = await self.edit()
        fields.price = price
        await fields.save()
