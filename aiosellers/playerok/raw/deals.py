from __future__ import annotations

from ..core.exceptions import UnsupportedPaymentProvider
from ..core.utils import _dig, _raise_on_gql_errors
from ..graphql import GraphQLQuery as GQL
from ..schemas import (
    ItemDeal,
    ItemDealDirections,
    ItemDealList,
    ItemDealStatuses,
    Transaction,
    TransactionPaymentMethodIds,
    TransactionProviderIds,
)
from ..transport import PlayerokTransport


class RawDealsService:
    def __init__(self, transport: PlayerokTransport):
        self._transport = transport

    async def get_deals(
        self,
        user_id: str,
        count: int = 24,
        statuses: list[ItemDealStatuses] | None = None,
        direction: ItemDealDirections | None = None,
        after_cursor: str | None = None,
    ) -> ItemDealList | None:
        response = await self._transport.request(
            "post",
            "graphql",
            GQL.get_deals(
                count=count,
                user_id=user_id,
                statuses=statuses,
                direction=direction,
                after_cursor=after_cursor,
            ),
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "deals"))
        if data is None:
            return None
        return ItemDealList(**data)

    async def get_deal(self, deal_id: str) -> ItemDeal | None:
        response = await self._transport.request("post", "graphql", GQL.get_deal(deal_id=deal_id))
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "deal"))
        if data is None:
            return None
        return ItemDeal(**data)

    async def update_deal(self, deal_id: str, new_status: ItemDealStatuses) -> ItemDeal | None:
        response = await self._transport.request(
            "post", "graphql", GQL.update_deal(deal_id=deal_id, new_status=new_status)
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "updateDeal"))
        if data is None:
            return None
        return ItemDeal(**data)

    async def report_problem(
        self, deal_id: str, description: str, problem_type_id: str
    ) -> ItemDeal | None:
        response = await self._transport.request(
            "post",
            "graphql",
            GQL.report_deal_problem(deal_id, description, problem_type_id),
        )
        raw = response.json()
        _raise_on_gql_errors(raw)
        data = _dig(raw, ("data", "reportDealProblem"))
        if data is None:
            return None
        return ItemDeal(**data)

    async def create_deal(
        self,
        item_id: str,
        transaction_provider_id: TransactionProviderIds,
        obtaining_fields: dict[str, str] | None = None,
        comment_from_buyer: str | None = None,
        payment_method_id: TransactionPaymentMethodIds | None = None,
    ) -> Transaction | None:
        if transaction_provider_id != TransactionProviderIds.LOCAL:
            raise UnsupportedPaymentProvider(
                f"Only LOCAL payment provider is supported, got {transaction_provider_id}"
            )
        payload_obtaining_fields = (
            [{"fieldId": k, "value": v} for k, v in obtaining_fields.items()]
            if obtaining_fields
            else None
        )

        response = await self._transport.request(
            "post",
            "graphql",
            GQL.create_deal(
                item_id=item_id,
                transaction_provider_id=transaction_provider_id.name,
                obtaining_fields=payload_obtaining_fields,
                comment_from_buyer=comment_from_buyer,
                payment_method_id=payment_method_id.name if payment_method_id else None,
            ),
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "createDeal"))
        if data is None:
            return None
        return Transaction(**data)
