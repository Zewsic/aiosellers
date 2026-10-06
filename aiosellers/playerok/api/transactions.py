from __future__ import annotations

from datetime import datetime
from typing import TYPE_CHECKING, AsyncIterator

from ..entities.transaction import Transaction
from ..schemas import (
    SBPBankMember,
    SortDirections,
    TransactionOperations,
    TransactionPaymentMethodIds,
    TransactionProvider,
    TransactionProviderDirections,
    TransactionProviderIds,
    TransactionStatuses,
    UserBankCard,
)

if TYPE_CHECKING:
    from ..playerok import Playerok


class TransactionAPI:
    def __init__(self, client: Playerok) -> None:
        self._client = client

    def _create(self, schema) -> Transaction:
        transaction = Transaction(
            id=schema.id,
            status=schema.status,
            operation=schema.operation,
            direction=schema.direction,
            value=schema.value,
            provider_id=schema.provider_id,
            created_at=schema.created_at,
        )
        transaction._client = self._client
        return transaction

    async def list(
        self,
        *,
        limit: int = 24,
        cursor: str | None = None,
        operation: list[TransactionOperations] | None = None,
        status: list[TransactionStatuses] | None = None,
        provider_id: list[TransactionProviderIds] | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> list[Transaction]:
        result: list[Transaction] = []
        remain = limit
        current_cursor = cursor

        while remain > 0:
            response = await self._client._raw.transactions.get_transactions(
                user_id=self._client._me_id,
                count=min(24, remain),
                operation=operation,
                min_value=min_value,
                max_value=max_value,
                provider_id=provider_id,
                status=status,
                after_cursor=current_cursor,
                from_date=from_date,
                to_date=to_date,
            )
            if response is None or not response.transactions:
                break
            for schema in response.transactions:
                result.append(self._create(schema))
                if len(result) >= limit:
                    break
            if len(result) >= limit:
                break
            remain -= len(response.transactions)
            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor
        return result[:limit]

    async def iter(
        self,
        *,
        cursor: str | None = None,
        operation: list[TransactionOperations] | None = None,
        status: list[TransactionStatuses] | None = None,
        provider_id: list[TransactionProviderIds] | None = None,
        min_value: int | None = None,
        max_value: int | None = None,
        from_date: datetime | None = None,
        to_date: datetime | None = None,
    ) -> AsyncIterator[Transaction]:
        current_cursor = cursor
        while True:
            response = await self._client._raw.transactions.get_transactions(
                user_id=self._client._me_id,
                operation=operation,
                min_value=min_value,
                max_value=max_value,
                provider_id=provider_id,
                status=status,
                after_cursor=current_cursor,
                from_date=from_date,
                to_date=to_date,
            )
            if response is None or not response.transactions:
                return
            for schema in response.transactions:
                yield self._create(schema)
            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor

    async def providers(
        self, direction: TransactionProviderDirections = TransactionProviderDirections.IN
    ) -> list[TransactionProvider]:
        return await self._client._raw.transactions.get_transaction_providers(direction)

    async def sbp_banks(self) -> list[SBPBankMember]:
        return await self._client._raw.transactions.get_sbp_bank_members()

    async def cards(
        self,
        *,
        limit: int = 24,
        cursor: str | None = None,
        direction: SortDirections = SortDirections.ASC,
    ) -> list[UserBankCard]:
        result: list[UserBankCard] = []
        remain = limit
        current_cursor = cursor
        while remain > 0:
            response = await self._client._raw.transactions.get_verified_cards(
                count=min(24, remain),
                after_cursor=current_cursor,
                direction=direction,
            )
            if response is None or not response.bank_cards:
                break
            result.extend(response.bank_cards)
            if len(result) >= limit:
                break
            remain -= len(response.bank_cards)
            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor
        return result[:limit]

    async def delete_card(self, card_id: str) -> bool:
        return await self._client._raw.transactions.delete_card(card_id)

    async def withdraw(
        self,
        *,
        provider: TransactionProviderIds,
        account: str,
        value: int,
        payment_method_id: TransactionPaymentMethodIds | None = None,
        sbp_bank_member_id: str | None = None,
    ) -> Transaction:
        schema = await self._client._raw.transactions.request_withdrawal(
            provider=provider,
            account=account,
            value=value,
            payment_method_id=payment_method_id,
            sbp_bank_member_id=sbp_bank_member_id,
        )
        return self._create(schema)

    async def cancel(self, transaction_id: str) -> Transaction:
        schema = await self._client._raw.transactions.remove_transaction(transaction_id)
        return self._create(schema)
