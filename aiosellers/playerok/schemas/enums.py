import threading
from enum import StrEnum

_ENUM_LOCK = threading.Lock()


class OpenStrEnum(StrEnum):
    """Площадка добавляет значения без предупреждения. Неизвестное становится членом, объект не падает."""

    @classmethod
    def _missing_(cls, value: object):
        if not isinstance(value, str) or not value:
            return None
        with _ENUM_LOCK:
            existing = cls._member_map_.get(value)
            if existing is not None:
                return existing
            member = str.__new__(cls, value)
            member._name_ = value
            member._value_ = value
            cls._member_map_[value] = member
            cls._value2member_map_[value] = member
            cls._member_names_.append(value)
            if value.isidentifier() and value not in cls.__dict__:
                type.__setattr__(cls, value, member)
            return member

    @classmethod
    def _coerce(cls, value: object):
        if isinstance(value, cls):
            return value
        if isinstance(value, str) and value:
            return cls(value)
        raise ValueError(f"{cls.__name__}: {value!r}")

    @classmethod
    def __get_pydantic_core_schema__(cls, source_type: object, handler: object):
        from pydantic_core import core_schema

        return core_schema.no_info_plain_validator_function(
            cls._coerce,
            serialization=core_schema.plain_serializer_function_ser_schema(
                lambda member: member.value,
                when_used="json",
            ),
        )

    @classmethod
    def __get_pydantic_json_schema__(cls, core_schema: object, handler: object):
        return {"type": "string"}


class QueryID(StrEnum):
    user = "48cadfa521497f9445eaa9abda29a4251149636d9393f536165889a61e332384"
    deals = "591b0e6d036c2120c8f95b97dbfdf5635df3747cd901f4895e009935229417ef"
    deal = "d0421fb8dea49652876d69b1a14ce2c715ea9c7127c48c85a78e06de31a845ae"
    games = "5de9b3240c148579c82e2310a30b4aad5462884fd1abf93dd3c43d1f5ef14d85"
    game = "4775f8630a3e234c50537e68649043ac32a40b0370b0f1fb2dc314500ef6202d"
    game_category = "7759f743651176ddad6afefb5f2e889ec9984cae08a015281879cd61e94bdb60"
    game_category_agreements = "3ea4b047196ed9f84aa5eb652299c4bd73f2e99e9fdf4587877658d9ea6330f6"
    game_category_obtaining_types = (
        "15b0991414821528251930b4c8161c299eb39882fd635dd5adb1a81fb0570aea"
    )
    game_category_instructions = "5991cead6a8ca46195bc4f7ae3164e7606105dbb82834c910658edeb0a1d1918"
    game_category_data_fields = "6fdadfb9b05880ce2d307a1412bc4f2e383683061c281e2b65a93f7266ea4a49"
    game_category_options = "ee8fdbe4e6fe6a924d5c19d5eed47bd9856f4dd16ee2e0e76841d0794a1f1b9b"
    chats = "c1ddbcd7c8b87160ac25e0734f9dc32fc945287b056f4b14abf1473bfb1ad11a"
    chat = "bb024dc0652fc7c1302a64a117d56d99fb0d726eb4b896ca803dca55f611d933"
    chat_messages = "9b4e264ff1b20e0fd3929afe023dee8f50affc02b85f80cb4b3dc1516ecfbaa0"
    items = "206ae9d63e58bc41df9023aae39b9136f358282a808c32ee95f5b8b6669a8c8b"
    item = "1cdb4b335f6c119db77883451f41cef83fc449f79f021627f27b76ec49203487"
    testimonials = "773d40b7efec82a4b86021ba8bcaa462f68eb236e255926f2168c5cd4685e881"
    message_templates = "f3d4b4053f7c758d4cd84429bbf974a27b0afed6a473ab47fbe8d13ac6bf87a2"
    item_priority_statuses = "b922220c6f979537e1b99de6af8f5c13727daeff66727f679f07f986ce1c025a"
    transaction_providers = "31960e5dd929834c1f85bc685db80657ff576373076f016b2578c0a34e6e9f42"
    transactions = "63672f5d6b617b27fe213cd5dec566e4ee90df9ea79080b74c5e6b6e9d448568"
    sbp_bank_members = "ef7902598e855fa15fb5e3112156ac226180f0b009a36606fc80a18f00b80c63"
    verified_cards = "eb338d8432981307a2b3d322b3310b2447cab3a6acf21aba4b8773b97e72d1aa"


class GameType(OpenStrEnum):
    MOBILE_GAME = "MOBILE_GAME"
    GAME = "GAME"
    APPLICATION = "APPLICATION"


class UserType(OpenStrEnum):
    USER = "USER"
    MODERATOR = "MODERATOR"
    BOT = "BOT"
    CHECKER = "CHECKER"
    ADMIN = "ADMIN"
    SUPPORT = "SUPPORT"
    SECURITY = "SECURITY"
    GAMES_AND_APPS = "GAMES_AND_APPS"


class GameCategoryDataFieldTypes(OpenStrEnum):
    ITEM_DATA = "ITEM_DATA"
    OBTAINING_DATA = "OBTAINING_DATA"


class EventTypes(OpenStrEnum):
    CHAT_INITIALIZED = "CHAT_INITIALIZED"
    NEW_MESSAGE = "NEW_MESSAGE"
    NEW_DEAL = "NEW_DEAL"
    NEW_REVIEW = "NEW_REVIEW"
    DEAL_CONFIRMED = "DEAL_CONFIRMED"
    DEAL_CONFIRMED_AUTOMATICALLY = "DEAL_CONFIRMED_AUTOMATICALLY"
    DEAL_ROLLED_BACK = "DEAL_ROLLED_BACK"
    DEAL_HAS_PROBLEM = "DEAL_HAS_PROBLEM"
    DEAL_PROBLEM_RESOLVED = "DEAL_PROBLEM_RESOLVED"
    DEAL_STATUS_CHANGED = "DEAL_STATUS_CHANGED"
    ITEM_PAID = "ITEM_PAID"
    ITEM_SENT = "ITEM_SENT"


class ItemLogEvents(OpenStrEnum):
    PAID = "PAID"
    SENT = "SENT"
    DEAL_CONFIRMED = "DEAL_CONFIRMED"
    DEAL_ROLLED_BACK = "DEAL_ROLLED_BACK"
    PROBLEM_REPORTED = "PROBLEM_REPORTED"
    PROBLEM_RESOLVED = "PROBLEM_RESOLVED"


class TransactionOperations(OpenStrEnum):
    DEPOSIT = "DEPOSIT"
    BUY = "BUY"
    SELL = "SELL"
    ITEM_DEFAULT_PRIORITY = "ITEM_DEFAULT_PRIORITY"
    ITEM_PREMIUM_PRIORITY = "ITEM_PREMIUM_PRIORITY"
    WITHDRAW = "WITHDRAW"
    MANUAL_BALANCE_INCREASE = "MANUAL_BALANCE_INCREASE"
    MANUAL_BALANCE_DECREASE = "MANUAL_BALANCE_DECREASE"
    REFERRAL_BONUS = "REFERRAL_BONUS"
    STEAM_DEPOSIT = "STEAM_DEPOSIT"


class TransactionDirections(OpenStrEnum):
    IN = "IN"
    OUT = "OUT"


class TransactionStatuses(OpenStrEnum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    CONFIRMED = "CONFIRMED"
    ROLLED_BACK = "ROLLED_BACK"
    FAILED = "FAILED"


class TransactionPaymentMethodIds(OpenStrEnum):
    MIR = "MIR"
    VISA_MASTERCARD = "VISA_MASTERCARD"
    ERIP = "ERIP"


class TransactionProviderDirections(OpenStrEnum):
    IN = "IN"
    OUT = "OUT"


class TransactionProviderIds(OpenStrEnum):
    LOCAL = "LOCAL"
    SBP = "SBP"
    BANK_CARD_RU = "BANK_CARD_RU"
    BANK_CARD_BY = "BANK_CARD_BY"
    BANK_CARD = "BANK_CARD"
    YMONEY = "YMONEY"
    USDT = "USDT"
    CRYPTO = "CRYPTO"
    PENDING_INCOME = "PENDING_INCOME"


class BankCardTypes(OpenStrEnum):
    MIR = "MIR"
    VISA = "VISA"
    MASTERCARD = "MASTERCARD"


class ItemDealStatuses(OpenStrEnum):
    PAID = "PAID"
    PENDING = "PENDING"
    SENT = "SENT"
    CONFIRMED = "CONFIRMED"
    CONFIRMED_AUTOMATICALLY = "CONFIRMED_AUTOMATICALLY"
    ROLLED_BACK = "ROLLED_BACK"


class ItemDealDirections(OpenStrEnum):
    IN = "IN"
    OUT = "OUT"


class ChatMessageDirection(OpenStrEnum):
    IN = "IN"
    OUT = "OUT"
    SYSTEM = "SYSTEM"


class ChatTypes(OpenStrEnum):
    PM = "PM"
    NOTIFICATIONS = "NOTIFICATIONS"
    SUPPORT = "SUPPORT"


class ChatStatuses(OpenStrEnum):
    NEW = "NEW"
    FINISHED = "FINISHED"
    ACTIVE = "ACTIVE"


class ChatMessageButtonTypes(OpenStrEnum):
    REDIRECT = "REDIRECT"
    LOTTERY = "LOTTERY"
    ASK_FOR_EXTERNAL_REVIEW = "ASK_FOR_EXTERNAL_REVIEW"


class ItemStatuses(OpenStrEnum):
    PENDING_APPROVAL = "PENDING_APPROVAL"
    PENDING_MODERATION = "PENDING_MODERATION"
    APPROVED = "APPROVED"
    DECLINED = "DECLINED"
    BLOCKED = "BLOCKED"
    EXPIRED = "EXPIRED"
    SOLD = "SOLD"
    DRAFT = "DRAFT"


class ReviewStatuses(OpenStrEnum):
    APPROVED = "APPROVED"
    DELETED = "DELETED"


class SortDirections(OpenStrEnum):
    DESC = "DESC"
    ASC = "ASC"


class ItemsSortOptions(OpenStrEnum):
    PRICE_ASC = "PRICE_ASC"
    PRICE_DESC = "PRICE_DESC"
    RATING_ASC = "RATING_ASC"
    RATING_DESC = "RATING_DESC"
    CREATED_ASC = "CREATED_ASC"
    CREATED_DESC = "CREATED_DESC"
    DEFAULT = "DEFAULT"


class PriorityTypes(OpenStrEnum):
    DEFAULT = "DEFAULT"
    PREMIUM = "PREMIUM"


class GameCategoryAgreementIconTypes(OpenStrEnum):
    RESTRICTION = "RESTRICTION"
    CONFIRMATION = "CONFIRMATION"


class GameCategoryOptionTypes(OpenStrEnum):
    SELECTOR = "SELECTOR"
    SWITCH = "SWITCH"
    RANGE = "RANGE"


class GameCategoryDataFieldInputTypes(OpenStrEnum):
    INPUT = "INPUT"
    TEXTAREA = "TEXTAREA"


class GameCategoryAutoConfirmPeriods(OpenStrEnum):
    TWO_DAYS = "TWO_DAYS"
    SEVEN_DAYS = "SEVEN_DAYS"


class MessageTemplateTypes(OpenStrEnum):
    ACTIVE_DEAL_PROBLEM = "ACTIVE_DEAL_PROBLEM"
    FINISHED_DEAL_PROBLEM = "FINISHED_DEAL_PROBLEM"


class ChatMessageEvents(OpenStrEnum):
    CHAT_STARTED = "CHAT_STARTED"
    CHAT_FINISHED = "CHAT_FINISHED"


class GameCategoryInstructionTypes(OpenStrEnum):
    FOR_SELLER = "FOR_SELLER"
    FOR_BUYER = "FOR_BUYER"
