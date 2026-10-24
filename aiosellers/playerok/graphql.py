import json
from datetime import datetime, timezone
from typing import Any

from .documents import REPORT_DEAL_PROBLEM, UPLOAD_CHAT_IMAGE
from .schemas import (
    ChatStatuses,
    ChatTypes,
    GameCategoryDataFieldTypes,
    GameCategoryInstructionTypes,
    GameType,
    ItemDealDirections,
    ItemDealStatuses,
    ItemsSortOptions,
    MessageTemplateTypes,
    QueryID,
    ReviewStatuses,
    SortDirections,
    TransactionOperations,
    TransactionPaymentMethodIds,
    TransactionProviderDirections,
    TransactionProviderIds,
    TransactionStatuses,
)


def _utc_stamp(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return value.astimezone(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.000Z")


def _items_sort(sort: ItemsSortOptions | None) -> dict[str, str] | None:
    if sort is None or sort == ItemsSortOptions.DEFAULT:
        return None
    name = sort.value
    if name.endswith("_ASC"):
        direction = "ASC"
        stem = name[: -len("_ASC")]
    elif name.endswith("_DESC"):
        direction = "DESC"
        stem = name[: -len("_DESC")]
    else:
        raise ValueError(f"unknown item sort {name}")
    field = {"PRICE": "price", "RATING": "userRating", "CREATED": "createdAt"}.get(stem)
    if field is None:
        raise ValueError(f"unknown item sort {name}")
    return {"field": field, "direction": direction}


def _persisted(
    operation_name: str,
    variables: dict[str, Any],
    *,
    sha256_hash: Any | None = None,
    query: str | None = None,
) -> dict[str, Any]:
    r = {
        "operationName": operation_name,
        "variables": variables,
    }
    if query:
        r["query"] = query
    if sha256_hash:
        r["extensions"] = {
            "persistedQuery": {
                "version": 1,
                "sha256Hash": sha256_hash,
            }
        }
    return r


class GraphQLQuery:
    # ------------ Accounts ------------
    @staticmethod
    def get_me():
        return _persisted(
            operation_name="viewer",
            variables={},
            query="query viewer {\n  viewer {\n    ...Viewer\n    __typename\n  }\n}\n\nfragment Viewer on User {\n  id\n  username\n  email\n  role\n  hasFrozenBalance\n  supportChatId\n  systemChatId\n  unreadChatsCounter\n  isBlocked\n  isBlockedFor\n  isFundsProtectionActive\n  createdAt\n  lastItemCreatedAt\n  hasConfirmedPhoneNumber\n  canPublishItems\n  chosenVerifiedCard {\n    ...MinimalUserBankCard\n    __typename\n  }\n  profile {\n    id\n    avatarURL\n    testimonialCounter\n    __typename\n  }\n  __typename\n}\n\nfragment MinimalUserBankCard on UserBankCard {\n  id\n  cardFirstSix\n  cardLastFour\n  cardType\n  isChosen\n  __typename\n}",
        )

    @staticmethod
    def get_user(username: str | None = None, id: str | None = None) -> dict[str, Any]:
        return _persisted(
            operation_name="user",
            variables={"id": id, "username": username, "hasSupportAccess": False},
            sha256_hash=QueryID.user.value,
        )

    # ------------ Games ------------

    @staticmethod
    def get_games(
        count: int = 24,
        type: GameType | None = None,
        name: str | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="games",
            variables={
                "pagination": {"first": count, "after": cursor},
                "filter": {"type": type.name if type else None, "name": name},
            },
            sha256_hash=QueryID.games.value,
        )

    @staticmethod
    def get_game(id: str | None = None, slug: str | None = None) -> dict[str, Any]:
        return _persisted(
            operation_name="GamePage",
            variables={"id": id, "slug": slug},
            sha256_hash=QueryID.game.value,
        )

    @staticmethod
    def get_game_category(
        game_id: str | None = None,
        slug: str | None = None,
        id: str | None = None,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="GamePageCategory",
            variables={"id": id, "gameId": game_id, "slug": slug},
            sha256_hash=QueryID.game_category.value,
        )

    @staticmethod
    def get_game_category_agreements(
        game_category_id: str,
        user_id: str,
        obtaining_type_id: str | None = None,
        count: int = 24,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="gameCategoryAgreements",
            variables={
                "pagination": {"first": count, "after": cursor},
                "filter": {
                    "gameCategoryId": game_category_id,
                    "userId": user_id,
                    "gameCategoryObtainingTypeId": obtaining_type_id,
                },
            },
            sha256_hash=QueryID.game_category_agreements.value,
        )

    @staticmethod
    def accept_game_category_agreement(
        agreement_id: str,
        user_id: str,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="acceptGameCategoryAgreement",
            variables={
                "input": {"agreementId": agreement_id, "userId": user_id},
            },
            query="mutation acceptGameCategoryAgreement($input: AcceptGameCategoryAgreementInput!) {\n  acceptGameCategoryAgreement(input: $input) {\n    ...RegularGameCategoryAgreement\n    __typename\n  }\n}\n\nfragment RegularGameCategoryAgreement on GameCategoryAgreement {\n  description\n  gameCategoryId\n  gameCategoryObtainingTypeId\n  iconType\n  id\n  sequence\n  __typename\n}",
        )

    @staticmethod
    def get_game_category_obtaining_types(
        game_category_id: str,
        count: int = 24,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="gameCategoryObtainingTypes",
            variables={
                "pagination": {"first": count, "after": cursor},
                "filter": {"gameCategoryId": game_category_id},
            },
            sha256_hash=QueryID.game_category_obtaining_types.value,
        )

    @staticmethod
    def get_game_category_instructions(
        game_category_id: str,
        obtaining_type_id: str,
        count: int = 24,
        type: GameCategoryInstructionTypes | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="gameCategoryInstructions",
            variables={
                "pagination": {"first": count, "after": cursor},
                "filter": {
                    "gameCategoryId": game_category_id,
                    "obtainingTypeId": obtaining_type_id,
                    "type": type.name if type else None,
                },
            },
            sha256_hash=QueryID.game_category_instructions.value,
        )

    @staticmethod
    def get_game_category_data_fields(
        game_category_id: str,
        obtaining_type_id: str,
        count: int = 24,
        type: GameCategoryDataFieldTypes | None = None,
        cursor: str | None = None,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="gameCategoryDataFields",
            variables={
                "pagination": {"first": count, "after": cursor},
                "filter": {
                    "gameCategoryId": game_category_id,
                    "obtainingTypeId": obtaining_type_id,
                    "type": type.name if type else None,
                },
            },
            sha256_hash=QueryID.game_category_data_fields.value,
        )

    @staticmethod
    def get_game_category_options(
        game_category_id: str,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="gameCategoryOptions",
            variables={"id": game_category_id},
            sha256_hash=QueryID.game_category_options.value,
        )

    # ------------ Items ------------

    @staticmethod
    def get_items(
        count: int = 24,
        cursor: str | None = None,
        game_id: str | None = None,
        user_id: str | None = None,
        category_id: str | None = None,
        minimal_price: int | None = None,
        maximal_price: int | None = None,
        has_discount: bool | None = None,
        has_reviews: bool | None = None,
        attributes: list[dict[str, str]] | None = None,
        search: str | None = None,
        sort: ItemsSortOptions | None = None,
    ) -> dict[str, Any]:
        if user_id is None:
            filters = {
                "gameId": game_id,
                "gameCategoryId": category_id,
                "status": ["APPROVED", "PENDING_MODERATION", "PENDING_APPROVAL"],
                "withOfficial": False,
            }
        else:
            filters = {
                "userId": user_id,
                "status": ["APPROVED"],
                "withOfficial": False,
            }

        if minimal_price is not None or maximal_price is not None:
            filters["price"] = {"min": minimal_price, "max": maximal_price}
        if has_discount:
            filters["hasDiscount"] = has_discount
        if has_reviews:
            filters["hasTestimonials"] = has_reviews
        if attributes:
            filters["attributes"] = attributes
        if search:
            filters["searchQuery"] = search

        return _persisted(
            operation_name="items",
            variables={
                "pagination": {"first": count, "after": cursor},
                "filter": filters,
                "sort": _items_sort(sort),
            },
            sha256_hash=QueryID.items.value,
        )

    @staticmethod
    def get_item(id: str | None = None, slug: str | None = None) -> dict[str, Any]:
        return _persisted(
            operation_name="item",
            variables={
                "id": id,
                "slug": slug,
                "hasSupportAccess": False,
                "showForbiddenImage": True,
            },
            sha256_hash=QueryID.item.value,
        )

    @staticmethod
    def create_item(
        game_category_id: str,
        obtaining_type_id: str,
        name: str,
        price: int,
        description: str,
        attributes: dict[str, Any],
        data_fields: list[dict[str, Any]],
        attachments_count: int,
    ) -> tuple[dict[str, Any], dict[str, Any]]:
        operations = {
            "operationName": "createItem",
            "query": "mutation createItem($input: CreateItemInput!, $attachments: [Upload!]!) {\n  createItem(input: $input, attachments: $attachments) {\n    ...RegularItem\n    __typename\n  }\n}\n\nfragment RegularItem on Item {\n  ...RegularMyItem\n  ...RegularForeignItem\n  __typename\n}\n\nfragment RegularMyItem on MyItem {\n  ...ItemFields\n  prevPrice\n  priority\n  sequence\n  priorityPrice\n  statusExpirationDate\n  comment\n  viewsCounter\n  statusDescription\n  editable\n  statusPayment {\n    ...StatusPaymentTransaction\n    __typename\n  }\n  moderator {\n    id\n    username\n    __typename\n  }\n  approvalDate\n  deletedAt\n  createdAt\n  updatedAt\n  mayBePublished\n  prevFeeMultiplier\n  sellerNotifiedAboutFeeChange\n  __typename\n}\n\nfragment ItemFields on Item {\n  id\n  slug\n  name\n  description\n  rawPrice\n  price\n  attributes\n  status\n  priorityPosition\n  sellerType\n  feeMultiplier\n  user {\n    ...ItemUser\n    __typename\n  }\n  buyer {\n    ...ItemUser\n    __typename\n  }\n  attachments {\n    ...PartialFile\n    __typename\n  }\n  category {\n    ...RegularGameCategory\n    __typename\n  }\n  game {\n    ...RegularGameProfile\n    __typename\n  }\n  comment\n  dataFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  obtainingType {\n    ...GameCategoryObtainingType\n    __typename\n  }\n  __typename\n}\n\nfragment ItemUser on UserFragment {\n  ...UserEdgeNode\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment PartialFile on File {\n  id\n  url\n  __typename\n}\n\nfragment RegularGameCategory on GameCategory {\n  id\n  slug\n  name\n  categoryId\n  gameId\n  obtaining\n  options {\n    ...RegularGameCategoryOption\n    __typename\n  }\n  props {\n    ...GameCategoryProps\n    __typename\n  }\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  useCustomObtaining\n  autoConfirmPeriod\n  autoModerationMode\n  agreements {\n    ...RegularGameCategoryAgreement\n    __typename\n  }\n  feeMultiplier\n  __typename\n}\n\nfragment RegularGameCategoryOption on GameCategoryOption {\n  id\n  group\n  label\n  type\n  field\n  value\n  valueRangeLimit {\n    min\n    max\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryProps on GameCategoryPropsObjectType {\n  minTestimonials\n  minTestimonialsForSeller\n  __typename\n}\n\nfragment RegularGameCategoryAgreement on GameCategoryAgreement {\n  description\n  gameCategoryId\n  gameCategoryObtainingTypeId\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment RegularGameProfile on GameProfile {\n  id\n  name\n  type\n  slug\n  logo {\n    ...PartialFile\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {\n  id\n  label\n  type\n  inputType\n  copyable\n  hidden\n  required\n  value\n  __typename\n}\n\nfragment GameCategoryObtainingType on GameCategoryObtainingType {\n  id\n  name\n  description\n  gameCategoryId\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  sequence\n  feeMultiplier\n  agreements {\n    ...MinimalGameCategoryAgreement\n    __typename\n  }\n  props {\n    minTestimonialsForSeller\n    __typename\n  }\n  __typename\n}\n\nfragment MinimalGameCategoryAgreement on GameCategoryAgreement {\n  description\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment StatusPaymentTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  props {\n    paymentURL\n    __typename\n  }\n  __typename\n}\n\nfragment RegularForeignItem on ForeignItem {\n  ...ItemFields\n  __typename\n}",
            "variables": {
                "input": {
                    "gameCategoryId": game_category_id,
                    "obtainingTypeId": obtaining_type_id,
                    "name": name,
                    "price": price,
                    "description": description,
                    "attributes": attributes,
                    "dataFields": data_fields,
                },
                "attachments": [None] * attachments_count,
            },
        }
        map_data = {str(i + 1): [f"variables.attachments.{i}"] for i in range(attachments_count)}
        return {
            "operations": json.dumps(operations),
            "map": json.dumps(map_data),
        }

    @staticmethod
    def get_item_priority_statuses(item_id: str, price: int) -> dict[str, Any]:
        return _persisted(
            operation_name="itemPriorityStatuses",
            variables={"itemId": item_id, "price": price},
            sha256_hash=QueryID.item_priority_statuses.value,
        )

    @staticmethod
    def increase_item_priority_status(
        item_id: str,
        priority_status_id: str,
        payment_method_id: str | None = None,
        transaction_provider_id: str = "LOCAL",
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="increaseItemPriorityStatus",
            variables={
                "input": {
                    "itemId": item_id,
                    "priorityStatuses": [priority_status_id],
                    "transactionProviderData": {
                        "paymentMethodId": payment_method_id,
                    },
                    "transactionProviderId": transaction_provider_id,
                }
            },
            query="mutation increaseItemPriorityStatus($input: PublishItemInput!) {\n  increaseItemPriorityStatus(input: $input) {\n    ...RegularItem\n    __typename\n  }\n}\n\nfragment RegularItem on Item {\n  ...RegularMyItem\n  ...RegularForeignItem\n  __typename\n}\n\nfragment RegularMyItem on MyItem {\n  ...ItemFields\n  prevPrice\n  priority\n  sequence\n  priorityPrice\n  statusExpirationDate\n  comment\n  viewsCounter\n  statusDescription\n  editable\n  statusPayment {\n    ...StatusPaymentTransaction\n    __typename\n  }\n  moderator {\n    id\n    username\n    __typename\n  }\n  approvalDate\n  deletedAt\n  createdAt\n  updatedAt\n  mayBePublished\n  prevFeeMultiplier\n  sellerNotifiedAboutFeeChange\n  __typename\n}\n\nfragment ItemFields on Item {\n  id\n  slug\n  name\n  description\n  rawPrice\n  price\n  attributes\n  status\n  priorityPosition\n  sellerType\n  feeMultiplier\n  user {\n    ...ItemUser\n    __typename\n  }\n  buyer {\n    ...ItemUser\n    __typename\n  }\n  attachments {\n    ...PartialFile\n    __typename\n  }\n  category {\n    ...RegularGameCategory\n    __typename\n  }\n  game {\n    ...RegularGameProfile\n    __typename\n  }\n  comment\n  dataFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  obtainingType {\n    ...GameCategoryObtainingType\n    __typename\n  }\n  __typename\n}\n\nfragment ItemUser on UserFragment {\n  ...UserEdgeNode\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment PartialFile on File {\n  id\n  url\n  __typename\n}\n\nfragment RegularGameCategory on GameCategory {\n  id\n  slug\n  name\n  categoryId\n  gameId\n  obtaining\n  options {\n    ...RegularGameCategoryOption\n    __typename\n  }\n  props {\n    ...GameCategoryProps\n    __typename\n  }\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  useCustomObtaining\n  autoConfirmPeriod\n  autoModerationMode\n  agreements {\n    ...RegularGameCategoryAgreement\n    __typename\n  }\n  feeMultiplier\n  __typename\n}\n\nfragment RegularGameCategoryOption on GameCategoryOption {\n  id\n  group\n  label\n  type\n  field\n  value\n  valueRangeLimit {\n    min\n    max\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryProps on GameCategoryPropsObjectType {\n  minTestimonials\n  minTestimonialsForSeller\n  __typename\n}\n\nfragment RegularGameCategoryAgreement on GameCategoryAgreement {\n  description\n  gameCategoryId\n  gameCategoryObtainingTypeId\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment RegularGameProfile on GameProfile {\n  id\n  name\n  type\n  slug\n  logo {\n    ...PartialFile\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {\n  id\n  label\n  type\n  inputType\n  copyable\n  hidden\n  required\n  value\n  __typename\n}\n\nfragment GameCategoryObtainingType on GameCategoryObtainingType {\n  id\n  name\n  description\n  gameCategoryId\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  sequence\n  feeMultiplier\n  agreements {\n    ...MinimalGameCategoryAgreement\n    __typename\n  }\n  props {\n    minTestimonialsForSeller\n    __typename\n  }\n  __typename\n}\n\nfragment MinimalGameCategoryAgreement on GameCategoryAgreement {\n  description\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment StatusPaymentTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  props {\n    paymentURL\n    __typename\n  }\n  __typename\n}\n\nfragment RegularForeignItem on ForeignItem {\n  ...ItemFields\n  __typename\n}",
        )

    @staticmethod
    def update_item(
        id: str,
        name: str | None = None,
        price: int | None = None,
        description: str | None = None,
        attributes: dict[str, Any] | None = None,
        data_fields: list[dict[str, Any]] | None = None,
        removed_attachments: list[str] | None = None,
        attachments_count: int = 0,
    ) -> dict[str, Any]:
        variables_input: dict[str, Any] = {"id": id}
        if name:
            variables_input["name"] = name
        if price is not None:
            variables_input["price"] = price
        if description:
            variables_input["description"] = description
        if attributes:
            variables_input["attributes"] = attributes
        if data_fields:
            variables_input["dataFields"] = data_fields
        if removed_attachments:
            variables_input["removedAttachments"] = removed_attachments

        operations = {
            "operationName": "updateItem",
            "query": "mutation updateItem($input: UpdateItemInput!, $addedAttachments: [Upload!]) {\n  updateItem(input: $input, addedAttachments: $addedAttachments) {\n    ...RegularItem\n    __typename\n  }\n}\n\nfragment RegularItem on Item {\n  ...RegularMyItem\n  ...RegularForeignItem\n  __typename\n}\n\nfragment RegularMyItem on MyItem {\n  ...ItemFields\n  prevPrice\n  priority\n  sequence\n  priorityPrice\n  statusExpirationDate\n  comment\n  viewsCounter\n  statusDescription\n  editable\n  statusPayment {\n    ...StatusPaymentTransaction\n    __typename\n  }\n  moderator {\n    id\n    username\n    __typename\n  }\n  approvalDate\n  deletedAt\n  createdAt\n  updatedAt\n  mayBePublished\n  prevFeeMultiplier\n  sellerNotifiedAboutFeeChange\n  __typename\n}\n\nfragment ItemFields on Item {\n  id\n  slug\n  name\n  description\n  rawPrice\n  price\n  attributes\n  status\n  priorityPosition\n  sellerType\n  feeMultiplier\n  user {\n    ...ItemUser\n    __typename\n  }\n  buyer {\n    ...ItemUser\n    __typename\n  }\n  attachments {\n    ...PartialFile\n    __typename\n  }\n  category {\n    ...RegularGameCategory\n    __typename\n  }\n  game {\n    ...RegularGameProfile\n    __typename\n  }\n  comment\n  dataFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  obtainingType {\n    ...GameCategoryObtainingType\n    __typename\n  }\n  __typename\n}\n\nfragment ItemUser on UserFragment {\n  ...UserEdgeNode\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment PartialFile on File {\n  id\n  url\n  __typename\n}\n\nfragment RegularGameCategory on GameCategory {\n  id\n  slug\n  name\n  categoryId\n  gameId\n  obtaining\n  options {\n    ...RegularGameCategoryOption\n    __typename\n  }\n  props {\n    ...GameCategoryProps\n    __typename\n  }\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  useCustomObtaining\n  autoConfirmPeriod\n  autoModerationMode\n  agreements {\n    ...RegularGameCategoryAgreement\n    __typename\n  }\n  feeMultiplier\n  __typename\n}\n\nfragment RegularGameCategoryOption on GameCategoryOption {\n  id\n  group\n  label\n  type\n  field\n  value\n  valueRangeLimit {\n    min\n    max\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryProps on GameCategoryPropsObjectType {\n  minTestimonials\n  minTestimonialsForSeller\n  __typename\n}\n\nfragment RegularGameCategoryAgreement on GameCategoryAgreement {\n  description\n  gameCategoryId\n  gameCategoryObtainingTypeId\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment RegularGameProfile on GameProfile {\n  id\n  name\n  type\n  slug\n  logo {\n    ...PartialFile\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {\n  id\n  label\n  type\n  inputType\n  copyable\n  hidden\n  required\n  value\n  __typename\n}\n\nfragment GameCategoryObtainingType on GameCategoryObtainingType {\n  id\n  name\n  description\n  gameCategoryId\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  sequence\n  feeMultiplier\n  agreements {\n    ...MinimalGameCategoryAgreement\n    __typename\n  }\n  props {\n    minTestimonialsForSeller\n    __typename\n  }\n  __typename\n}\n\nfragment MinimalGameCategoryAgreement on GameCategoryAgreement {\n  description\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment StatusPaymentTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  props {\n    paymentURL\n    __typename\n  }\n  __typename\n}\n\nfragment RegularForeignItem on ForeignItem {\n  ...ItemFields\n  __typename\n}",
            "variables": {
                "input": variables_input,
                "addedAttachments": [None] * attachments_count if attachments_count > 0 else None,
            },
        }
        map_data = (
            {str(i + 1): [f"variables.addedAttachments.{i}"] for i in range(attachments_count)}
            if attachments_count > 0
            else {}
        )

        if attachments_count > 0:
            return {
                "operations": json.dumps(operations),
                "map": json.dumps(map_data),
            }

        return operations

    @staticmethod
    def remove_item(id: str) -> dict[str, Any]:
        return {
            "operationName": "removeItem",
            "query": "mutation removeItem($id: UUID!) {\n  removeItem(id: $id) {\n    ...RegularItem\n    __typename\n  }\n}\n\nfragment RegularItem on Item {\n  ...RegularMyItem\n  ...RegularForeignItem\n  __typename\n}\n\nfragment RegularMyItem on MyItem {\n  ...ItemFields\n  prevPrice\n  priority\n  sequence\n  priorityPrice\n  statusExpirationDate\n  comment\n  viewsCounter\n  statusDescription\n  editable\n  statusPayment {\n    ...StatusPaymentTransaction\n    __typename\n  }\n  moderator {\n    id\n    username\n    __typename\n  }\n  approvalDate\n  deletedAt\n  createdAt\n  updatedAt\n  mayBePublished\n  prevFeeMultiplier\n  sellerNotifiedAboutFeeChange\n  __typename\n}\n\nfragment ItemFields on Item {\n  id\n  slug\n  name\n  description\n  rawPrice\n  price\n  attributes\n  status\n  priorityPosition\n  sellerType\n  feeMultiplier\n  user {\n    ...ItemUser\n    __typename\n  }\n  buyer {\n    ...ItemUser\n    __typename\n  }\n  attachments {\n    ...PartialFile\n    __typename\n  }\n  category {\n    ...RegularGameCategory\n    __typename\n  }\n  game {\n    ...RegularGameProfile\n    __typename\n  }\n  comment\n  dataFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  obtainingType {\n    ...GameCategoryObtainingType\n    __typename\n  }\n  __typename\n}\n\nfragment ItemUser on UserFragment {\n  ...UserEdgeNode\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment PartialFile on File {\n  id\n  url\n  __typename\n}\n\nfragment RegularGameCategory on GameCategory {\n  id\n  slug\n  name\n  categoryId\n  gameId\n  obtaining\n  options {\n    ...RegularGameCategoryOption\n    __typename\n  }\n  props {\n    ...GameCategoryProps\n    __typename\n  }\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  useCustomObtaining\n  autoConfirmPeriod\n  autoModerationMode\n  agreements {\n    ...RegularGameCategoryAgreement\n    __typename\n  }\n  feeMultiplier\n  __typename\n}\n\nfragment RegularGameCategoryOption on GameCategoryOption {\n  id\n  group\n  label\n  type\n  field\n  value\n  valueRangeLimit {\n    min\n    max\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryProps on GameCategoryPropsObjectType {\n  minTestimonials\n  minTestimonialsForSeller\n  __typename\n}\n\nfragment RegularGameCategoryAgreement on GameCategoryAgreement {\n  description\n  gameCategoryId\n  gameCategoryObtainingTypeId\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment RegularGameProfile on GameProfile {\n  id\n  name\n  type\n  slug\n  logo {\n    ...PartialFile\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {\n  id\n  label\n  type\n  inputType\n  copyable\n  hidden\n  required\n  value\n  __typename\n}\n\nfragment GameCategoryObtainingType on GameCategoryObtainingType {\n  id\n  name\n  description\n  gameCategoryId\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  sequence\n  feeMultiplier\n  agreements {\n    ...MinimalGameCategoryAgreement\n    __typename\n  }\n  props {\n    minTestimonialsForSeller\n    __typename\n  }\n  __typename\n}\n\nfragment MinimalGameCategoryAgreement on GameCategoryAgreement {\n  description\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment StatusPaymentTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  props {\n    paymentURL\n    __typename\n  }\n  __typename\n}\n\nfragment RegularForeignItem on ForeignItem {\n  ...ItemFields\n  __typename\n}",
            "variables": {"id": id},
        }

    @staticmethod
    def publish_item(
        item_id: str,
        priority_status_id: str,
        transaction_provider_id: str,
    ) -> dict[str, Any]:
        return {
            "operationName": "publishItem",
            "query": "mutation publishItem($input: PublishItemInput!) {\n  publishItem(input: $input) {\n    ...RegularItem\n    __typename\n  }\n}\n\nfragment RegularItem on Item {\n  ...RegularMyItem\n  ...RegularForeignItem\n  __typename\n}\n\nfragment RegularMyItem on MyItem {\n  ...ItemFields\n  prevPrice\n  priority\n  sequence\n  priorityPrice\n  statusExpirationDate\n  comment\n  viewsCounter\n  statusDescription\n  editable\n  statusPayment {\n    ...StatusPaymentTransaction\n    __typename\n  }\n  moderator {\n    id\n    username\n    __typename\n  }\n  approvalDate\n  deletedAt\n  createdAt\n  updatedAt\n  mayBePublished\n  prevFeeMultiplier\n  sellerNotifiedAboutFeeChange\n  __typename\n}\n\nfragment ItemFields on Item {\n  id\n  slug\n  name\n  description\n  rawPrice\n  price\n  attributes\n  status\n  priorityPosition\n  sellerType\n  feeMultiplier\n  user {\n    ...ItemUser\n    __typename\n  }\n  buyer {\n    ...ItemUser\n    __typename\n  }\n  attachments {\n    ...PartialFile\n    __typename\n  }\n  category {\n    ...RegularGameCategory\n    __typename\n  }\n  game {\n    ...RegularGameProfile\n    __typename\n  }\n  comment\n  dataFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  obtainingType {\n    ...GameCategoryObtainingType\n    __typename\n  }\n  __typename\n}\n\nfragment ItemUser on UserFragment {\n  ...UserEdgeNode\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment PartialFile on File {\n  id\n  url\n  __typename\n}\n\nfragment RegularGameCategory on GameCategory {\n  id\n  slug\n  name\n  categoryId\n  gameId\n  obtaining\n  options {\n    ...RegularGameCategoryOption\n    __typename\n  }\n  props {\n    ...GameCategoryProps\n    __typename\n  }\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  useCustomObtaining\n  autoConfirmPeriod\n  autoModerationMode\n  agreements {\n    ...RegularGameCategoryAgreement\n    __typename\n  }\n  feeMultiplier\n  __typename\n}\n\nfragment RegularGameCategoryOption on GameCategoryOption {\n  id\n  group\n  label\n  type\n  field\n  value\n  valueRangeLimit {\n    min\n    max\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryProps on GameCategoryPropsObjectType {\n  minTestimonials\n  minTestimonialsForSeller\n  __typename\n}\n\nfragment RegularGameCategoryAgreement on GameCategoryAgreement {\n  description\n  gameCategoryId\n  gameCategoryObtainingTypeId\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment RegularGameProfile on GameProfile {\n  id\n  name\n  type\n  slug\n  logo {\n    ...PartialFile\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {\n  id\n  label\n  type\n  inputType\n  copyable\n  hidden\n  required\n  value\n  __typename\n}\n\nfragment GameCategoryObtainingType on GameCategoryObtainingType {\n  id\n  name\n  description\n  gameCategoryId\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  sequence\n  feeMultiplier\n  agreements {\n    ...MinimalGameCategoryAgreement\n    __typename\n  }\n  props {\n    minTestimonialsForSeller\n    __typename\n  }\n  __typename\n}\n\nfragment MinimalGameCategoryAgreement on GameCategoryAgreement {\n  description\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment StatusPaymentTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  props {\n    paymentURL\n    __typename\n  }\n  __typename\n}\n\nfragment RegularForeignItem on ForeignItem {\n  ...ItemFields\n  __typename\n}",
            "variables": {
                "input": {
                    "itemId": item_id,
                    "priorityStatuses": [priority_status_id],
                    "transactionProviderId": transaction_provider_id,
                }
            },
        }

    # ------------ Chats ------------

    @staticmethod
    def get_chats(
        count: int = 24,
        user_id: str | None = None,
        type: ChatTypes | None = None,
        status: ChatStatuses | None = None,
        cursor: str | None = None,
    ):
        return _persisted(
            operation_name="userChats",
            variables={
                "pagination": {"first": count, "after": cursor},
                "filter": {
                    "userId": user_id,
                    "type": type.name if type else None,
                    "status": status.name if status else None,
                },
                "hasSupportAccess": False,
            },
            sha256_hash=QueryID.chats.value,
        )

    @staticmethod
    def get_chat(chat_id: str):
        return _persisted(
            operation_name="chat",
            variables={"id": chat_id, "hasSupportAccess": False},
            sha256_hash=QueryID.chat.value,
        )

    @staticmethod
    def mark_chat_as_read(chat_id: str):
        return _persisted(
            operation_name="markChatAsRead",
            variables={"input": {"chatId": chat_id}},
            query="mutation markChatAsRead($input: MarkChatAsReadInput!) {\n	markChatAsRead(input: $input) {\n		...RegularChat\n		__typename\n	}\n}\n\nfragment RegularChat on Chat {\n	id\n	type\n	unreadMessagesCounter\n	bookmarked\n	isTextingAllowed\n	owner {\n		...ChatParticipant\n		__typename\n	}\n	agent {\n		...ChatParticipant\n		__typename\n	}\n	participants {\n		...ChatParticipant\n		__typename\n	}\n	deals {\n		...ChatActiveItemDeal\n		__typename\n	}\n	status\n	startedAt\n	finishedAt\n	__typename\n}\n\nfragment ChatParticipant on UserFragment {\n	...RegularUserFragment\n	__typename\n}\n\nfragment RegularUserFragment on UserFragment {\n	id\n	username\n	role\n	avatarURL\n	isOnline\n	isBlocked\n	rating\n	testimonialCounter\n	createdAt\n	supportChatId\n	systemChatId\n	__typename\n}\n\nfragment ChatActiveItemDeal on ItemDealProfile {\n	id\n	direction\n	status\n	hasProblem\n	testimonial {\n		id\n		rating\n		__typename\n	}\n	item {\n		...ChatDealItemEdgeNode\n		__typename\n	}\n	user {\n		...RegularUserFragment\n		__typename\n	}\n	__typename\n}\n\nfragment ChatDealItemEdgeNode on ItemProfile {\n	...ChatDealMyItemEdgeNode\n	...ChatDealForeignItemEdgeNode\n	__typename\n}\n\nfragment ChatDealMyItemEdgeNode on MyItemProfile {\n	id\n	slug\n	priority\n	status\n	name\n	price\n	rawPrice\n	statusExpirationDate\n	sellerType\n	attachment {\n		...PartialFile\n		__typename\n	}\n	user {\n		...UserItemEdgeNode\n		__typename\n	}\n	approvalDate\n	createdAt\n	priorityPosition\n	feeMultiplier\n	__typename\n}\n\nfragment PartialFile on File {\n	id\n	url\n	__typename\n}\n\nfragment UserItemEdgeNode on UserFragment {\n	...UserEdgeNode\n	__typename\n}\n\nfragment UserEdgeNode on UserFragment {\n	...RegularUserFragment\n	__typename\n}\n\nfragment ChatDealForeignItemEdgeNode on ForeignItemProfile {\n	id\n	slug\n	priority\n	status\n	name\n	price\n	rawPrice\n	sellerType\n	attachment {\n		...PartialFile\n		__typename\n	}\n	user {\n		...UserItemEdgeNode\n		__typename\n	}\n	approvalDate\n	priorityPosition\n	createdAt\n	feeMultiplier\n	__typename\n}",
        )

    @staticmethod
    def get_chat_messages(chat_id: str, count: int = 24, after_cursor: str | None = None):
        return _persisted(
            operation_name="chatMessages",
            variables={
                "pagination": {"first": count, "after": after_cursor},
                "filter": {
                    "chatId": chat_id,
                },
                "hasSupportAccess": False,
                "showForbiddenImage": True,
            },
            sha256_hash=QueryID.chat_messages.value,
        )

    # ------------ Transactions ------------

    @staticmethod
    def get_transaction_providers(
        direction: TransactionProviderDirections = TransactionProviderDirections.IN,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="transactionProviders",
            variables={"filter": {"direction": direction.name if direction else None}},
            sha256_hash=QueryID.transaction_providers.value,
        )

    @staticmethod
    def get_transactions(
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
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {"userId": user_id}
        if operation:
            filters["operation"] = [op.name for op in operation]
        if min_value or max_value:
            filters["value"] = {}
            if min_value:
                filters["value"]["min"] = str(min_value)
            if max_value:
                filters["value"]["max"] = str(max_value)
        if provider_id:
            filters["providerId"] = [pid.name for pid in provider_id]
        if status:
            filters["status"] = [s.name for s in status]
        if from_date or to_date:
            date_range: dict[str, str] = {}
            if from_date:
                date_range["from"] = _utc_stamp(from_date)
            if to_date:
                date_range["to"] = _utc_stamp(to_date)
            filters["dateRange"] = date_range

        return _persisted(
            operation_name="transactions",
            variables={
                "pagination": {"first": count, "after": after_cursor},
                "filter": filters,
                "hasSupportAccess": False,
            },
            sha256_hash=QueryID.transactions.value,
        )

    @staticmethod
    def get_sbp_bank_members() -> dict[str, Any]:
        return _persisted(
            operation_name="SbpBankMembers",
            variables={},
            sha256_hash=QueryID.sbp_bank_members.value,
        )

    @staticmethod
    def get_verified_cards(
        count: int = 24,
        after_cursor: str | None = None,
        direction: SortDirections = SortDirections.ASC,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="verifiedCards",
            variables={
                "pagination": {"first": count, "after": after_cursor},
                "sort": {"direction": direction.name},
                "field": "createdAt",
            },
            sha256_hash=QueryID.verified_cards.value,
        )

    @staticmethod
    def delete_card(card_id: str) -> dict[str, Any]:
        return {
            "operationName": "deleteCard",
            "query": "mutation deleteCard($input: DeleteCardInput!) {\n  deleteCard(input: $input)\n}",
            "variables": {"input": {"cardId": card_id}},
        }

    @staticmethod
    def request_withdrawal(
        provider: TransactionProviderIds,
        account: str,
        value: int,
        payment_method_id: TransactionPaymentMethodIds | None = None,
        sbp_bank_member_id: str | None = None,
    ) -> dict[str, Any]:
        return {
            "operationName": "requestWithdrawal",
            "query": "mutation requestWithdrawal($input: CreateWithdrawalTransactionInput!) {\n  requestWithdrawal(input: $input) {\n    ...RegularTransaction\n    __typename\n  }\n}\n\nfragment RegularTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  provider {\n    ...RegularTransactionProvider\n    __typename\n  }\n  user {\n    ...RegularUserFragment\n    __typename\n  }\n  creator {\n    ...RegularUserFragment\n    __typename\n  }\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  fee\n  createdAt\n  props {\n    ...RegularTransactionProps\n    __typename\n  }\n  verifiedAt\n  verifiedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  completedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  paymentMethodId\n  completedAt\n  isSuspicious\n  spbBankName\n  __typename\n}\n\nfragment RegularTransactionProvider on TransactionProvider {\n  id\n  name\n  fee\n  minFeeAmount\n  description\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  paymentMethods {\n    ...TransactionPaymentMethod\n    __typename\n  }\n  __typename\n}\n\nfragment RegularTransactionProviderAccount on TransactionProviderAccount {\n  id\n  value\n  userId\n  providerId\n  paymentMethodId\n  __typename\n}\n\nfragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {\n  requiredUserData {\n    ...TransactionProviderRequiredUserData\n    __typename\n  }\n  tooltip\n  __typename\n}\n\nfragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {\n  email\n  phoneNumber\n  eripAccountNumber\n  __typename\n}\n\nfragment ProviderLimits on ProviderLimits {\n  incoming {\n    ...ProviderLimitRange\n    __typename\n  }\n  outgoing {\n    ...ProviderLimitRange\n    __typename\n  }\n  __typename\n}\n\nfragment ProviderLimitRange on ProviderLimitRange {\n  min\n  max\n  __typename\n}\n\nfragment TransactionPaymentMethod on TransactionPaymentMethod {\n  id\n  name\n  fee\n  providerId\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment RegularTransactionProps on TransactionPropsFragment {\n  creatorId\n  dealId\n  paidFromPendingIncome\n  paymentURL\n  successURL\n  fee\n  paymentAccount {\n    id\n    value\n    __typename\n  }\n  paymentGateway\n  alreadySpent\n  exchangeRate\n  amountAfterConversionRub\n  amountAfterConversionUsdt\n  userData {\n    account\n    email\n    ipAddress\n    phoneNumber\n    __typename\n  }\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}",
            "variables": {
                "input": {
                    "provider": provider.name,
                    "account": account,
                    "value": value,
                    "providerData": {
                        "paymentMethodId": payment_method_id.name if payment_method_id else None,
                        "sbpBankMemberId": sbp_bank_member_id if sbp_bank_member_id else None,
                    },
                }
            },
        }

    @staticmethod
    def remove_transaction(transaction_id: str) -> dict[str, Any]:
        return {
            "operationName": "removeTransaction",
            "query": "mutation removeTransaction($id: UUID!) {\n  removeTransaction(id: $id) {\n    ...RegularTransaction\n    __typename\n  }\n}\n\nfragment RegularTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  provider {\n    ...RegularTransactionProvider\n    __typename\n  }\n  user {\n    ...RegularUserFragment\n    __typename\n  }\n  creator {\n    ...RegularUserFragment\n    __typename\n  }\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  fee\n  createdAt\n  props {\n    ...RegularTransactionProps\n    __typename\n  }\n  verifiedAt\n  verifiedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  completedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  paymentMethodId\n  completedAt\n  isSuspicious\n  spbBankName\n  __typename\n}\n\nfragment RegularTransactionProvider on TransactionProvider {\n  id\n  name\n  fee\n  minFeeAmount\n  description\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  paymentMethods {\n    ...TransactionPaymentMethod\n    __typename\n  }\n  __typename\n}\n\nfragment RegularTransactionProviderAccount on TransactionProviderAccount {\n  id\n  value\n  userId\n  providerId\n  paymentMethodId\n  __typename\n}\n\nfragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {\n  requiredUserData {\n    ...TransactionProviderRequiredUserData\n    __typename\n  }\n  tooltip\n  __typename\n}\n\nfragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {\n  email\n  phoneNumber\n  eripAccountNumber\n  __typename\n}\n\nfragment ProviderLimits on ProviderLimits {\n  incoming {\n    ...ProviderLimitRange\n    __typename\n  }\n  outgoing {\n    ...ProviderLimitRange\n    __typename\n  }\n  __typename\n}\n\nfragment ProviderLimitRange on ProviderLimitRange {\n  min\n  max\n  __typename\n}\n\nfragment TransactionPaymentMethod on TransactionPaymentMethod {\n  id\n  name\n  fee\n  providerId\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment RegularTransactionProps on TransactionPropsFragment {\n  creatorId\n  dealId\n  paidFromPendingIncome\n  paymentURL\n  successURL\n  fee\n  paymentAccount {\n    id\n    value\n    __typename\n  }\n  paymentGateway\n  alreadySpent\n  exchangeRate\n  amountAfterConversionRub\n  amountAfterConversionUsdt\n  userData {\n    account\n    email\n    ipAddress\n    phoneNumber\n    __typename\n  }\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}",
            "variables": {"id": transaction_id},
        }

    @staticmethod
    def create_chat_message(chat_id: str, text: str) -> dict[str, Any]:
        return _persisted(
            operation_name="createChatMessage",
            variables={
                "input": {
                    "chatId": chat_id,
                    "text": text,
                }
            },
            query="mutation createChatMessage($input: CreateChatMessageInput!, $file: Upload) {\n  createChatMessage(input: $input, file: $file) {\n    ...RegularChatMessage\n    __typename\n  }\n}\n\nfragment RegularChatMessage on ChatMessage {\n  id\n  text\n  createdAt\n  deletedAt\n  isRead\n  isSuspicious\n  isBulkMessaging\n  game {\n    ...RegularGameProfile\n    __typename\n  }\n  file {\n    ...PartialFile\n    __typename\n  }\n  user {\n    ...ChatMessageUserFields\n    __typename\n  }\n  deal {\n    ...ChatMessageItemDeal\n    __typename\n  }\n  item {\n    ...ItemEdgeNode\n    __typename\n  }\n  transaction {\n    ...RegularTransaction\n    __typename\n  }\n  moderator {\n    ...UserEdgeNode\n    __typename\n  }\n  eventByUser {\n    ...ChatMessageUserFields\n    __typename\n  }\n  eventToUser {\n    ...ChatMessageUserFields\n    __typename\n  }\n  isAutoResponse\n  event\n  buttons {\n    ...ChatMessageButton\n    __typename\n  }\n  __typename\n}\n\nfragment RegularGameProfile on GameProfile {\n  id\n  name\n  type\n  slug\n  logo {\n    ...PartialFile\n    __typename\n  }\n  __typename\n}\n\nfragment PartialFile on File {\n  id\n  url\n  __typename\n}\n\nfragment ChatMessageUserFields on UserFragment {\n  ...UserEdgeNode\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment ChatMessageItemDeal on ItemDeal {\n  id\n  direction\n  status\n  statusDescription\n  hasProblem\n  user {\n    ...ChatParticipant\n    __typename\n  }\n  testimonial {\n    ...ChatMessageDealTestimonial\n    __typename\n  }\n  item {\n    id\n    name\n    price\n    slug\n    rawPrice\n    sellerType\n    user {\n      ...ChatParticipant\n      __typename\n    }\n    category {\n      id\n      __typename\n    }\n    attachments {\n      ...PartialFile\n      __typename\n    }\n    comment\n    dataFields {\n      ...GameCategoryDataFieldWithValue\n      __typename\n    }\n    obtainingType {\n      ...GameCategoryObtainingType\n      __typename\n    }\n    __typename\n  }\n  obtainingFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  chat {\n    id\n    type\n    __typename\n  }\n  transaction {\n    id\n    statusExpirationDate\n    __typename\n  }\n  statusExpirationDate\n  commentFromBuyer\n  __typename\n}\n\nfragment ChatParticipant on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment ChatMessageDealTestimonial on Testimonial {\n  id\n  status\n  text\n  rating\n  createdAt\n  updatedAt\n  creator {\n    ...RegularUserFragment\n    __typename\n  }\n  moderator {\n    ...RegularUserFragment\n    __typename\n  }\n  user {\n    ...RegularUserFragment\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {\n  id\n  label\n  type\n  inputType\n  copyable\n  hidden\n  required\n  value\n  __typename\n}\n\nfragment GameCategoryObtainingType on GameCategoryObtainingType {\n  id\n  name\n  description\n  gameCategoryId\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  sequence\n  feeMultiplier\n  agreements {\n    ...MinimalGameCategoryAgreement\n    __typename\n  }\n  props {\n    minTestimonialsForSeller\n    __typename\n  }\n  __typename\n}\n\nfragment MinimalGameCategoryAgreement on GameCategoryAgreement {\n  description\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment ItemEdgeNode on ItemProfile {\n  ...MyItemEdgeNode\n  ...ForeignItemEdgeNode\n  __typename\n}\n\nfragment MyItemEdgeNode on MyItemProfile {\n  id\n  slug\n  priority\n  status\n  name\n  price\n  rawPrice\n  statusExpirationDate\n  sellerType\n  attachment {\n    ...PartialFile\n    __typename\n  }\n  user {\n    ...UserItemEdgeNode\n    __typename\n  }\n  approvalDate\n  createdAt\n  priorityPosition\n  viewsCounter\n  feeMultiplier\n  __typename\n}\n\nfragment UserItemEdgeNode on UserFragment {\n  ...UserEdgeNode\n  __typename\n}\n\nfragment ForeignItemEdgeNode on ForeignItemProfile {\n  id\n  slug\n  priority\n  status\n  name\n  price\n  rawPrice\n  sellerType\n  attachment {\n    ...PartialFile\n    __typename\n  }\n  user {\n    ...UserItemEdgeNode\n    __typename\n  }\n  approvalDate\n  priorityPosition\n  createdAt\n  viewsCounter\n  feeMultiplier\n  __typename\n}\n\nfragment RegularTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  provider {\n    ...RegularTransactionProvider\n    __typename\n  }\n  user {\n    ...RegularUserFragment\n    __typename\n  }\n  creator {\n    ...RegularUserFragment\n    __typename\n  }\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  fee\n  createdAt\n  props {\n    ...RegularTransactionProps\n    __typename\n  }\n  verifiedAt\n  verifiedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  completedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  paymentMethodId\n  completedAt\n  isSuspicious\n  __typename\n}\n\nfragment RegularTransactionProvider on TransactionProvider {\n  id\n  name\n  fee\n  minFeeAmount\n  description\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  paymentMethods {\n    ...TransactionPaymentMethod\n    __typename\n  }\n  __typename\n}\n\nfragment RegularTransactionProviderAccount on TransactionProviderAccount {\n  id\n  value\n  userId\n  __typename\n}\n\nfragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {\n  requiredUserData {\n    ...TransactionProviderRequiredUserData\n    __typename\n  }\n  tooltip\n  __typename\n}\n\nfragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {\n  email\n  phoneNumber\n  __typename\n}\n\nfragment ProviderLimits on ProviderLimits {\n  incoming {\n    ...ProviderLimitRange\n    __typename\n  }\n  outgoing {\n    ...ProviderLimitRange\n    __typename\n  }\n  __typename\n}\n\nfragment ProviderLimitRange on ProviderLimitRange {\n  min\n  max\n  __typename\n}\n\nfragment TransactionPaymentMethod on TransactionPaymentMethod {\n  id\n  name\n  fee\n  providerId\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  __typename\n}\n\nfragment RegularTransactionProps on TransactionPropsFragment {\n  creatorId\n  dealId\n  paidFromPendingIncome\n  paymentURL\n  successURL\n  fee\n  paymentAccount {\n    id\n    value\n    __typename\n  }\n  paymentGateway\n  alreadySpent\n  exchangeRate\n  amountAfterConversionRub\n  amountAfterConversionUsdt\n  __typename\n}\n\nfragment ChatMessageButton on ChatMessageButton {\n  type\n  url\n  text\n  __typename\n}",
        )

    @staticmethod
    def create_chat_message_with_photo(chat_id: str, text: str | None = None) -> dict[str, Any]:
        operations = {
            "operationName": "createChatMessage",
            "variables": {
                "input": {
                    "chatId": chat_id,
                },
                "file": None,
                "showForbiddenImage": True,
            },
            "query": "mutation createChatMessage($input: CreateChatMessageInput!, $file: Upload, $showForbiddenImage: Boolean) {\n  createChatMessage(input: $input, file: $file) {\n    ...RegularChatMessage\n    __typename\n  }\n}\n\nfragment RegularChatMessage on ChatMessage {\n  id\n  text\n  createdAt\n  deletedAt\n  isRead\n  isSuspicious\n  isBulkMessaging\n  game {\n    ...RegularGameProfile\n    __typename\n  }\n  file {\n    ...PartialFile\n    __typename\n  }\n  user {\n    ...ChatMessageUserFields\n    __typename\n  }\n  deal {\n    ...ChatMessageItemDeal\n    __typename\n  }\n  item {\n    ...ItemEdgeNode\n    __typename\n  }\n  transaction {\n    ...RegularTransaction\n    __typename\n  }\n  moderator {\n    ...UserEdgeNode\n    __typename\n  }\n  eventByUser {\n    ...ChatMessageUserFields\n    __typename\n  }\n  eventToUser {\n    ...ChatMessageUserFields\n    __typename\n  }\n  isAutoResponse\n  event\n  buttons {\n    ...ChatMessageButton\n    __typename\n  }\n  images {\n    ...RegularFile\n    __typename\n  }\n  __typename\n}\n\nfragment RegularGameProfile on GameProfile {\n  id\n  name\n  type\n  slug\n  logo {\n    ...PartialFile\n    __typename\n  }\n  __typename\n}\n\nfragment PartialFile on File {\n  id\n  url\n  __typename\n}\n\nfragment ChatMessageUserFields on UserFragment {\n  ...UserEdgeNode\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment ChatMessageItemDeal on ItemDeal {\n  id\n  direction\n  status\n  statusDescription\n  hasProblem\n  user {\n    ...ChatParticipant\n    __typename\n  }\n  testimonial {\n    ...ChatMessageDealTestimonial\n    __typename\n  }\n  item {\n    id\n    name\n    price\n    slug\n    rawPrice\n    sellerType\n    user {\n      ...ChatParticipant\n      __typename\n    }\n    category {\n      id\n      __typename\n    }\n    attachments(showForbiddenImage: $showForbiddenImage) {\n      ...PartialFile\n      __typename\n    }\n    isAttachmentsForbidden\n    comment\n    dataFields {\n      ...GameCategoryDataFieldWithValue\n      __typename\n    }\n    obtainingType {\n      ...GameCategoryObtainingType\n      __typename\n    }\n    __typename\n  }\n  obtainingFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  chat {\n    id\n    type\n    __typename\n  }\n  transaction {\n    id\n    statusExpirationDate\n    __typename\n  }\n  statusExpirationDate\n  commentFromBuyer\n  __typename\n}\n\nfragment ChatParticipant on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment ChatMessageDealTestimonial on Testimonial {\n  id\n  status\n  text\n  rating\n  createdAt\n  updatedAt\n  creator {\n    ...RegularUserFragment\n    __typename\n  }\n  moderator {\n    ...RegularUserFragment\n    __typename\n  }\n  user {\n    ...RegularUserFragment\n    __typename\n  }\n  __typename\n}\n\nfragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {\n  id\n  label\n  type\n  inputType\n  copyable\n  hidden\n  required\n  value\n  __typename\n}\n\nfragment GameCategoryObtainingType on GameCategoryObtainingType {\n  id\n  name\n  description\n  gameCategoryId\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  sequence\n  feeMultiplier\n  agreements {\n    ...MinimalGameCategoryAgreement\n    __typename\n  }\n  props {\n    minTestimonialsForSeller\n    __typename\n  }\n  __typename\n}\n\nfragment MinimalGameCategoryAgreement on GameCategoryAgreement {\n  description\n  iconType\n  id\n  sequence\n  __typename\n}\n\nfragment ItemEdgeNode on ItemProfile {\n  ...MyItemEdgeNode\n  ...ForeignItemEdgeNode\n  __typename\n}\n\nfragment MyItemEdgeNode on MyItemProfile {\n  id\n  slug\n  priority\n  status\n  name\n  price\n  rawPrice\n  statusExpirationDate\n  sellerType\n  attachment(showForbiddenImage: $showForbiddenImage) {\n    ...PartialFile\n    __typename\n  }\n  isAttachmentsForbidden\n  user {\n    ...UserItemEdgeNode\n    __typename\n  }\n  approvalDate\n  createdAt\n  priorityPosition\n  viewsCounter\n  feeMultiplier\n  __typename\n}\n\nfragment UserItemEdgeNode on UserFragment {\n  ...UserEdgeNode\n  __typename\n}\n\nfragment ForeignItemEdgeNode on ForeignItemProfile {\n  id\n  slug\n  priority\n  status\n  name\n  price\n  rawPrice\n  sellerType\n  attachment(showForbiddenImage: $showForbiddenImage) {\n    ...PartialFile\n    __typename\n  }\n  isAttachmentsForbidden\n  user {\n    ...UserItemEdgeNode\n    __typename\n  }\n  approvalDate\n  priorityPosition\n  createdAt\n  viewsCounter\n  feeMultiplier\n  __typename\n}\n\nfragment RegularTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  provider {\n    ...RegularTransactionProvider\n    __typename\n  }\n  user {\n    ...RegularUserFragment\n    __typename\n  }\n  creator {\n    ...RegularUserFragment\n    __typename\n  }\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  fee\n  createdAt\n  props {\n    ...RegularTransactionProps\n    __typename\n  }\n  verifiedAt\n  verifiedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  completedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  paymentMethodId\n  completedAt\n  isSuspicious\n  spbBankName\n  __typename\n}\n\nfragment RegularTransactionProvider on TransactionProvider {\n  id\n  name\n  fee\n  minFeeAmount\n  description\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  paymentMethods {\n    ...TransactionPaymentMethod\n    __typename\n  }\n  __typename\n}\n\nfragment RegularTransactionProviderAccount on TransactionProviderAccount {\n  id\n  value\n  userId\n  __typename\n}\n\nfragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {\n  requiredUserData {\n    ...TransactionProviderRequiredUserData\n    __typename\n  }\n  tooltip\n  __typename\n}\n\nfragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {\n  email\n  phoneNumber\n  eripAccountNumber\n  __typename\n}\n\nfragment ProviderLimits on ProviderLimits {\n  incoming {\n    ...ProviderLimitRange\n    __typename\n  }\n  outgoing {\n    ...ProviderLimitRange\n    __typename\n  }\n  __typename\n}\n\nfragment ProviderLimitRange on ProviderLimitRange {\n  min\n  max\n  __typename\n}\n\nfragment TransactionPaymentMethod on TransactionPaymentMethod {\n  id\n  name\n  fee\n  providerId\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  __typename\n}\n\nfragment RegularTransactionProps on TransactionPropsFragment {\n  creatorId\n  dealId\n  paidFromPendingIncome\n  paymentURL\n  successURL\n  fee\n  paymentAccount {\n    id\n    value\n    __typename\n  }\n  paymentGateway\n  alreadySpent\n  exchangeRate\n  amountAfterConversionRub\n  amountAfterConversionUsdt\n  userData {\n    account\n    email\n    ipAddress\n    phoneNumber\n    __typename\n  }\n  __typename\n}\n\nfragment ChatMessageButton on ChatMessageButton {\n  type\n  url\n  text\n  __typename\n}\n\nfragment RegularFile on File {\n  id\n  url\n  filename\n  mime\n  __typename\n}",
        }
        if text:
            operations["variables"]["input"]["text"] = text

        map_data = {"1": ["variables.file"]}
        return {
            "operations": json.dumps(operations),
            "map": json.dumps(map_data),
        }

    # ------------ Deals ------------

    @staticmethod
    def get_deals(
        user_id: str,
        count: int = 24,
        statuses: list[ItemDealStatuses] | None = None,
        direction: ItemDealDirections | None = None,
        after_cursor: str | None = None,
    ) -> dict[str, Any]:
        str_statuses = [status.name for status in statuses] if statuses else None
        str_direction = direction.name if direction else None
        return _persisted(
            operation_name="deals",
            variables={
                "pagination": {"first": count, "after": after_cursor},
                "filter": {
                    "userId": user_id,
                    "direction": str_direction,
                    "status": str_statuses,
                },
                "showForbiddenImage": True,
            },
            sha256_hash=QueryID.deals.value,
        )

    @staticmethod
    def get_deal(deal_id: str) -> dict[str, Any]:
        return _persisted(
            operation_name="deal",
            variables={
                "id": deal_id,
                "hasSupportAccess": False,
                "showForbiddenImage": True,
            },
            sha256_hash=QueryID.deal.value,
        )

    @staticmethod
    def update_deal(deal_id: str, new_status: ItemDealStatuses) -> dict[str, Any]:
        return _persisted(
            operation_name="updateDeal",
            variables={
                "input": {
                    "id": deal_id,
                    "status": new_status.name,
                }
            },
            query="mutation updateDeal($input: UpdateItemDealInput!) {\n  updateDeal(input: $input) {\n    ...RegularItemDeal\n    __typename\n  }\n}\n\nfragment RegularItemDeal on ItemDeal {\n  id\n  status\n  direction\n  statusExpirationDate\n  statusDescription\n  obtaining\n  hasProblem\n  reportProblemEnabled\n  completedBy {\n    ...MinimalUserFragment\n    __typename\n  }\n  props {\n    ...ItemDealProps\n    __typename\n  }\n  prevStatus\n  completedAt\n  createdAt\n  logs {\n    ...ItemLog\n    __typename\n  }\n  transaction {\n    ...ItemDealTransaction\n    __typename\n  }\n  user {\n    ...UserEdgeNode\n    __typename\n  }\n  chat {\n    ...RegularChatId\n    __typename\n  }\n  item {\n    ...PartialDealItem\n    __typename\n  }\n  testimonial {\n    ...RegularItemDealTestimonial\n    __typename\n  }\n  obtainingFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  commentFromBuyer\n  __typename\n}\n\nfragment MinimalUserFragment on UserFragment {\n  id\n  username\n  role\n  __typename\n}\n\nfragment ItemDealProps on ItemDealProps {\n  autoConfirmPeriod\n  __typename\n}\n\nfragment ItemLog on ItemLog {\n  id\n  event\n  createdAt\n  user {\n    ...UserEdgeNode\n    __typename\n  }\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment ItemDealTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  status\n  value\n  createdAt\n  paymentMethodId\n  statusExpirationDate\n  __typename\n}\n\nfragment RegularChatId on Chat {\n  id\n  __typename\n}\n\nfragment PartialDealItem on Item {\n  ...PartialDealMyItem\n  ...PartialDealForeignItem\n  __typename\n}\n\nfragment PartialDealMyItem on MyItem {\n  id\n  slug\n  priority\n  status\n  name\n  price\n  priorityPrice\n  rawPrice\n  statusExpirationDate\n  sellerType\n  approvalDate\n  createdAt\n  priorityPosition\n  viewsCounter\n  feeMultiplier\n  comment\n  attachments {\n    ...RegularFile\n    __typename\n  }\n  user {\n    ...UserEdgeNode\n    __typename\n  }\n  game {\n    ...RegularGameProfile\n    __typename\n  }\n  category {\n    ...MinimalGameCategory\n    __typename\n  }\n  dataFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  obtainingType {\n    ...MinimalGameCategoryObtainingType\n    __typename\n  }\n  __typename\n}\n\nfragment RegularFile on File {\n  id\n  url\n  filename\n  mime\n  __typename\n}\n\nfragment RegularGameProfile on GameProfile {\n  id\n  name\n  type\n  slug\n  logo {\n    ...PartialFile\n    __typename\n  }\n  __typename\n}\n\nfragment PartialFile on File {\n  id\n  url\n  __typename\n}\n\nfragment MinimalGameCategory on GameCategory {\n  id\n  slug\n  name\n  __typename\n}\n\nfragment GameCategoryDataFieldWithValue on GameCategoryDataFieldWithValue {\n  id\n  label\n  type\n  inputType\n  copyable\n  hidden\n  required\n  value\n  __typename\n}\n\nfragment MinimalGameCategoryObtainingType on GameCategoryObtainingType {\n  id\n  name\n  description\n  gameCategoryId\n  noCommentFromBuyer\n  instructionForBuyer\n  instructionForSeller\n  sequence\n  feeMultiplier\n  props {\n    minTestimonialsForSeller\n    __typename\n  }\n  __typename\n}\n\nfragment PartialDealForeignItem on ForeignItem {\n  id\n  slug\n  priority\n  status\n  name\n  price\n  rawPrice\n  sellerType\n  approvalDate\n  priorityPosition\n  createdAt\n  viewsCounter\n  feeMultiplier\n  comment\n  attachments {\n    ...RegularFile\n    __typename\n  }\n  user {\n    ...UserEdgeNode\n    __typename\n  }\n  game {\n    ...RegularGameProfile\n    __typename\n  }\n  category {\n    ...MinimalGameCategory\n    __typename\n  }\n  dataFields {\n    ...GameCategoryDataFieldWithValue\n    __typename\n  }\n  obtainingType {\n    ...MinimalGameCategoryObtainingType\n    __typename\n  }\n  __typename\n}\n\nfragment RegularItemDealTestimonial on Testimonial {\n  id\n  status\n  text\n  rating\n  createdAt\n  updatedAt\n  creator {\n    ...RegularUserFragment\n    __typename\n  }\n  moderator {\n    ...RegularUserFragment\n    __typename\n  }\n  user {\n    ...RegularUserFragment\n    __typename\n  }\n  __typename\n}",
        )

    @staticmethod
    def create_deal(
        item_id: str,
        transaction_provider_id: str,
        obtaining_fields: list[dict[str, str]] | None = None,
        comment_from_buyer: str | None = None,
        payment_method_id: str | None = None,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="createDeal",
            variables={
                "input": {
                    "itemId": item_id,
                    "transactionProviderId": transaction_provider_id,
                    "obtainingFields": obtaining_fields or [],
                    "commentFromBuyer": comment_from_buyer,
                    "transactionProviderData": {"paymentMethodId": payment_method_id},
                }
            },
            query="mutation createDeal($input: CreateItemDealInput!) {\n  createDeal(input: $input) {\n    ...RegularTransaction\n    __typename\n  }\n}\n\nfragment RegularTransaction on Transaction {\n  id\n  operation\n  direction\n  providerId\n  provider {\n    ...RegularTransactionProvider\n    __typename\n  }\n  user {\n    ...RegularUserFragment\n    __typename\n  }\n  creator {\n    ...RegularUserFragment\n    __typename\n  }\n  status\n  statusDescription\n  statusExpirationDate\n  value\n  fee\n  createdAt\n  props {\n    ...RegularTransactionProps\n    __typename\n  }\n  verifiedAt\n  verifiedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  completedBy {\n    ...UserEdgeNode\n    __typename\n  }\n  paymentMethodId\n  completedAt\n  isSuspicious\n  spbBankName\n  __typename\n}\n\nfragment RegularTransactionProvider on TransactionProvider {\n  id\n  name\n  fee\n  minFeeAmount\n  description\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  paymentMethods {\n    ...TransactionPaymentMethod\n    __typename\n  }\n  __typename\n}\n\nfragment RegularTransactionProviderAccount on TransactionProviderAccount {\n  id\n  value\n  userId\n  providerId\n  paymentMethodId\n  __typename\n}\n\nfragment TransactionProviderPropsFragment on TransactionProviderPropsFragment {\n  requiredUserData {\n    ...TransactionProviderRequiredUserData\n    __typename\n  }\n  tooltip\n  __typename\n}\n\nfragment TransactionProviderRequiredUserData on TransactionProviderRequiredUserData {\n  email\n  phoneNumber\n  eripAccountNumber\n  __typename\n}\n\nfragment ProviderLimits on ProviderLimits {\n  incoming {\n    ...ProviderLimitRange\n    __typename\n  }\n  outgoing {\n    ...ProviderLimitRange\n    __typename\n  }\n  __typename\n}\n\nfragment ProviderLimitRange on ProviderLimitRange {\n  min\n  max\n  __typename\n}\n\nfragment TransactionPaymentMethod on TransactionPaymentMethod {\n  id\n  name\n  fee\n  providerId\n  account {\n    ...RegularTransactionProviderAccount\n    __typename\n  }\n  props {\n    ...TransactionProviderPropsFragment\n    __typename\n  }\n  limits {\n    ...ProviderLimits\n    __typename\n  }\n  __typename\n}\n\nfragment RegularUserFragment on UserFragment {\n  id\n  username\n  role\n  avatarURL\n  isOnline\n  isBlocked\n  rating\n  testimonialCounter\n  createdAt\n  supportChatId\n  systemChatId\n  __typename\n}\n\nfragment RegularTransactionProps on TransactionPropsFragment {\n  creatorId\n  dealId\n  paidFromPendingIncome\n  paymentURL\n  successURL\n  fee\n  paymentAccount {\n    id\n    value\n    __typename\n  }\n  paymentGateway\n  alreadySpent\n  exchangeRate\n  amountAfterConversionRub\n  amountAfterConversionUsdt\n  userData {\n    account\n    email\n    ipAddress\n    phoneNumber\n    __typename\n  }\n  __typename\n}\n\nfragment UserEdgeNode on UserFragment {\n  ...RegularUserFragment\n  __typename\n}",
        )

    @staticmethod
    def get_testimonials(
        user_id: str,
        *,
        count: int = 24,
        after_cursor: str | None = None,
        status: ReviewStatuses | None = ReviewStatuses.APPROVED,
        comment_required: bool = False,
        rating: int | None = None,
        game_id: str | None = None,
        category_id: str | None = None,
        min_item_price: int | None = None,
        max_item_price: int | None = None,
        sort_direction: SortDirections = SortDirections.DESC,
        sort_field: str = "createdAt",
    ) -> dict[str, Any]:
        filters: dict[str, Any] = {
            "userId": user_id,
            "hasComment": comment_required,
            "status": [status.name] if status else None,
        }
        if game_id is not None:
            filters["gameId"] = game_id
        if category_id is not None:
            filters["categoryId"] = category_id
        if rating is not None:
            filters["rating"] = rating
        if min_item_price is not None or max_item_price is not None:
            item_price: dict[str, int] = {}
            if min_item_price is not None:
                item_price["min"] = min_item_price
            if max_item_price is not None:
                item_price["max"] = max_item_price
            filters["itemPrice"] = item_price
        return _persisted(
            operation_name="testimonials",
            variables={
                "pagination": {"first": count, "after": after_cursor},
                "filter": filters,
                "sort": {
                    "direction": sort_direction.name if sort_direction else None,
                    "field": sort_field,
                },
                "hasSupportAccess": False,
            },
            sha256_hash=QueryID.testimonials.value,
        )

    @staticmethod
    def get_message_templates(
        template_type: MessageTemplateTypes,
        *,
        count: int = 24,
        after_cursor: str | None = None,
    ) -> dict[str, Any]:
        return _persisted(
            operation_name="messageTemplates",
            variables={
                "pagination": {"first": count, "after": after_cursor},
                "filter": {"type": template_type.name},
            },
            sha256_hash=QueryID.message_templates.value,
        )

    @staticmethod
    def report_deal_problem(deal_id: str, description: str, problem_type_id: str) -> dict[str, Any]:
        return {
            "operationName": "reportDealProblem",
            "query": REPORT_DEAL_PROBLEM,
            "variables": {
                "input": {
                    "dealId": deal_id,
                    "description": description,
                    "problemTypeId": problem_type_id,
                },
                "showForbiddenImage": True,
            },
        }

    @staticmethod
    def upload_chat_image(chat_id: str, client_attachment_id: str) -> dict[str, str]:
        operations = {
            "operationName": "uploadChatImageIntoTemporaryStore",
            "query": UPLOAD_CHAT_IMAGE,
            "variables": {
                "file": None,
                "input": {
                    "chatId": chat_id,
                    "clientAttachmentId": client_attachment_id,
                },
            },
        }
        return {
            "operations": json.dumps(operations),
            "map": json.dumps({"1": ["variables.file"]}),
        }
