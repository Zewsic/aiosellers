from __future__ import annotations

from typing import TYPE_CHECKING, AsyncIterator

from ..entities.deal import Deal
from ..schemas.enums import ItemDealDirections, ItemDealStatuses

if TYPE_CHECKING:
    from ..entities.item import Item
    from ..playerok import Playerok


class DealAPI:
    def __init__(self, client: Playerok) -> None:
        self._client = client

    def _create_deal(self, schema) -> Deal:
        deal = Deal(
            id=schema.id,
            status=schema.status,
            user_id=schema.user.id if schema.user else None,
            chat_id=schema.chat.id if schema.chat else None,
            item_id=schema.item.id if schema.item else None,
        )
        deal._client = self._client

        if self._client._use_identity_map:
            self._client._identity_maps.deals.set(schema.id, deal)

        return deal

    async def get(self, deal_id: str, *, force_refresh: bool = False) -> Deal | None:
        if not force_refresh and self._client._use_identity_map:
            cached = self._client._identity_maps.deals.get(deal_id)
            if cached:
                return cached

        schema = await self._client._raw.deals.get_deal(deal_id)
        if schema is None:
            return None

        return self._create_deal(schema)

    async def list(
        self,
        *,
        limit: int = 24,
        cursor: str | None = None,
        statuses: list[ItemDealStatuses] | None = None,
        direction: ItemDealDirections | None = None,
        user_id: str | None = None,
        item_id: str | None = None,
    ) -> list[Deal]:
        result = []
        remain = limit
        current_cursor = cursor

        while remain > 0:
            response = await self._client._raw.deals.get_deals(
                user_id=self._client._me_id,
                count=min(24, remain),
                after_cursor=current_cursor,
                statuses=statuses,
                direction=direction,
            )
            if response is None or not response.deals:
                break

            for schema in response.deals:
                deal_user_id = schema.user.id if schema.user else None
                deal_item_id = schema.item.id if schema.item else None

                # Filter by user_id if specified
                if user_id is not None and deal_user_id != user_id:
                    continue

                # Filter by item_id if specified
                if item_id is not None and deal_item_id != item_id:
                    continue

                result.append(self._create_deal(schema))
                if len(result) >= limit:
                    break

            if len(result) >= limit:
                break

            remain -= len(response.deals)

            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor

        return result[:limit]

    async def iter(
        self,
        *,
        cursor: str | None = None,
        statuses: list[ItemDealStatuses] | None = None,
        direction: ItemDealDirections | None = None,
        user_id: str | None = None,
        item_id: str | None = None,
    ) -> AsyncIterator[Deal]:
        current_cursor = cursor

        while True:
            response = await self._client._raw.deals.get_deals(
                user_id=self._client._me_id,
                after_cursor=current_cursor,
                statuses=statuses,
                direction=direction,
            )
            if response is None or not response.deals:
                return

            for schema in response.deals:
                deal_user_id = schema.user.id if schema.user else None
                deal_item_id = schema.item.id if schema.item else None

                # Filter by user_id if specified
                if user_id is not None and deal_user_id != user_id:
                    continue

                # Filter by item_id if specified
                if item_id is not None and deal_item_id != item_id:
                    continue

                yield self._create_deal(schema)

            if not response.page_info.has_next_page:
                break
            current_cursor = response.page_info.end_cursor

    async def confirm(self, deal_id: str) -> Deal:
        """Confirm DONE work (for buyer)"""
        updated = await self._client._raw.deals.update_deal(deal_id, ItemDealStatuses.CONFIRMED)
        if updated is None:
            return await self.get(deal_id, force_refresh=True)
        return self._create_deal(updated)

    async def complete(self, deal_id: str) -> Deal:
        """Mark PAID work as COMPLETED (sent), ask for confirmation (for seller)"""
        updated = await self._client._raw.deals.update_deal(deal_id, ItemDealStatuses.SENT)
        if updated is None:
            return await self.get(deal_id, force_refresh=True)
        return self._create_deal(updated)

    async def report_problem(self, deal_id: str, description: str, problem_type_id: str) -> Deal:
        updated = await self._client._raw.deals.report_problem(
            deal_id, description, problem_type_id
        )
        if updated is None:
            refreshed = await self.get(deal_id, force_refresh=True)
            if refreshed is None:
                raise RuntimeError(f"Deal {deal_id} was not found after reporting a problem")
            return refreshed
        return self._create_deal(updated)

    async def cancel(self, deal_id: str) -> Deal:
        """Reject PAID work and refund money (for seller)"""
        updated = await self._client._raw.deals.update_deal(deal_id, ItemDealStatuses.ROLLED_BACK)
        if updated is None:
            return await self.get(deal_id, force_refresh=True)
        return self._create_deal(updated)

    def _extract_obtaining_fields(
        self, fields: dict[str, str] | list | None
    ) -> dict[str, str] | None:
        """Extract obtaining fields from dict or list of GameCategoryDataField."""
        if fields is None:
            return None
        if isinstance(fields, dict):
            return fields
        result = {}
        for field in fields:
            if hasattr(field, "_input_value") and field._input_value is not None:
                result[field.id] = field._input_value
        return result if result else None

    async def create(
        self,
        item: str | Item,
        *,
        obtaining_fields: dict[str, str] | list | None = None,
        comment: str | None = None,
    ) -> Deal | None:
        """Create a deal to buy an item.

        Args:
            item: Item entity or item_id string
            obtaining_fields: Data fields for obtaining the item. Can be dict or list of GameCategoryDataField.
            comment: Optional comment from buyer

        Returns:
            Created Deal entity or None if creation failed
        """
        from ..schemas.enums import TransactionProviderIds

        # Extract item_id
        item_id = item.id if isinstance(item, Item) else item

        # Extract obtaining fields
        fields_dict = self._extract_obtaining_fields(obtaining_fields)

        # Create deal via raw API
        transaction = await self._client._raw.deals.create_deal(
            item_id=item_id,
            transaction_provider_id=TransactionProviderIds.LOCAL,
            obtaining_fields=fields_dict,
            comment_from_buyer=comment,
        )

        if transaction is None:
            return None

        # Extract deal_id from transaction.props.dealId
        deal_id = None
        if transaction.props and isinstance(transaction.props, dict):
            deal_id = transaction.props.get("dealId")

        if deal_id:
            return await self.get(deal_id)

        return None
