from __future__ import annotations

from datetime import datetime

from ..core.exceptions import UnsupportedPaymentProvider
from ..core.utils import _dig, _raise_on_gql_errors
from ..graphql import GraphQLQuery as GQL
from ..schemas import (
    SBPBankMember,
    SortDirections,
    Transaction,
    TransactionList,
    TransactionOperations,
    TransactionPaymentMethodIds,
    TransactionProvider,
    TransactionProviderDirections,
    TransactionProviderIds,
    TransactionStatuses,
    UserBankCardList,
)
from ..transport import PlayerokTransport


class RawTransactionService:
    def __init__(self, transport: PlayerokTransport):
        self._transport = transport

    async def get_transaction_providers(
        self, direction: TransactionProviderDirections = TransactionProviderDirections.IN
    ) -> list[TransactionProvider]:
        response = await self._transport.request(
            "post", "graphql", GQL.get_transaction_providers(direction)
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "transactionProviders")) or []
        return [TransactionProvider(**provider) for provider in data]

    async def get_transactions(
        self,
        user_id: str,
        count: int = 24,
        operation: list[TransactionOperations] | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        provider_id: list[TransactionProviderIds] | None = None,
        status: list[TransactionStatuses] | None = None,
        after_cursor: str | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> TransactionList:
        response = await self._transport.request(
            "post",
            "graphql",
            GQL.get_transactions(
                user_id=user_id,
                count=count,
                operation=operation,
                min_value=min_value,
                max_value=max_value,
                provider_id=provider_id,
                status=status,
                after_cursor=after_cursor,
                from_date=from_date,
                to_date=to_date,
            ),
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "transactions"))
        return TransactionList(**data)

    async def get_sbp_bank_members(self) -> list[SBPBankMember]:
        response = await self._transport.request("post", "graphql", GQL.get_sbp_bank_members())
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "sbpBankMembers")) or []
        return [SBPBankMember(**member) for member in data]

    async def get_verified_cards(
        self,
        count: int = 24,
        after_cursor: str | None = None,
        direction: SortDirections = SortDirections.ASC,
    ) -> UserBankCardList:
        response = await self._transport.request(
            "post", "graphql", GQL.get_verified_cards(count, after_cursor, direction)
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "verifiedCards"))
        return UserBankCardList(**data)

    async def delete_card(self, card_id: str) -> bool:
        response = await self._transport.request("post", "graphql", GQL.delete_card(card_id))
        raw = response.json()
        _raise_on_gql_errors(raw)

        return _dig(raw, ("data", "deleteCard"))

    async def request_withdrawal(
        self,
        provider: TransactionProviderIds,
        account: str,
        value: int,
        payment_method_id: TransactionPaymentMethodIds | None = None,
        sbp_bank_member_id: str | None = None,
    ) -> Transaction:
        if provider != TransactionProviderIds.LOCAL:
            raise UnsupportedPaymentProvider(
                f"Only LOCAL payment provider is supported, got {provider}"
            )
        response = await self._transport.request(
            "post",
            "graphql",
            GQL.request_withdrawal(provider, account, value, payment_method_id, sbp_bank_member_id),
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "requestWithdrawal"))
        return Transaction(**data)

    async def remove_transaction(self, transaction_id: str) -> Transaction:
        response = await self._transport.request(
            "post", "graphql", GQL.remove_transaction(transaction_id)
        )
        raw = response.json()
        _raise_on_gql_errors(raw)

        data = _dig(raw, ("data", "removeTransaction"))
        return Transaction(**data)
