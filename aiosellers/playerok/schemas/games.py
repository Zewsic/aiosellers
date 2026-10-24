from datetime import datetime

from pydantic import Field, model_validator

from . import (
    ApiModel,
    GameCategoryAgreementIconTypes,
    GameCategoryAutoConfirmPeriods,
    GameCategoryDataFieldInputTypes,
    GameCategoryDataFieldTypes,
    GameCategoryOptionTypes,
    GameType,
    PageInfo,
)
from .basic import File


class GameCategoryDataField(ApiModel):
    id: str = Field(..., alias="id")
    label: str = Field(..., alias="label")

    type: GameCategoryDataFieldTypes = Field(..., alias="type")
    input_type: GameCategoryDataFieldInputTypes = Field(..., alias="inputType")

    copyable: bool = Field(..., alias="copyable")
    hidden: bool = Field(..., alias="hidden")
    required: bool = Field(..., alias="required")

    value: str | None = Field(None, alias="value")


class GameCategoryDataFieldList(ApiModel):
    data_fields: list[GameCategoryDataField] = Field(..., alias="dataFields")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "dataFields" not in data and "data_fields" not in data:
            edges = data.get("edges") or []
            data["dataFields"] = [
                (edge or {}).get("node") for edge in edges if (edge or {}).get("node")
            ]

        if "data_fields" in data and "dataFields" not in data:
            data["dataFields"] = data["data_fields"]

        return data


class GameCategoryProps(ApiModel):
    min_reviews: int | None = Field(None, alias="minTestimonials")
    min_reviews_for_seller: int = Field(..., alias="minTestimonialsForSeller")


class GameCategoryOptionRangeLimit(ApiModel):
    min: int | None = Field(None, alias="min")
    max: int | None = Field(None, alias="max")


class GameCategoryOption(ApiModel):
    id: str = Field(..., alias="id")
    group: str = Field(..., alias="group")
    label: str = Field(..., alias="label")

    type: GameCategoryOptionTypes = Field(..., alias="type")
    field: str = Field(..., alias="field")
    value: str = Field(..., alias="value")
    value_range_limit: GameCategoryOptionRangeLimit | None = Field(None, alias="valueRangeLimit")


class GameCategoryAgreement(ApiModel):
    id: str = Field(..., alias="id")
    description: str = Field(..., alias="description")
    icon_type: GameCategoryAgreementIconTypes = Field(..., alias="iconType")
    sequence: int = Field(..., alias="sequence")


class GameCategoryAgreementList(ApiModel):
    agreements: list[GameCategoryAgreement] = Field(..., alias="agreements")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "agreements" not in data:
            edges = data.get("edges") or []
            data["agreements"] = [
                (edge or {}).get("node") for edge in edges if (edge or {}).get("node")
            ]
        return data


class GameCategoryObtainingType(ApiModel):
    id: str = Field(..., alias="id")
    name: str = Field(..., alias="name")
    description: str | None = Field(None, alias="description")

    game_category_id: str = Field(..., alias="gameCategoryId")
    no_comment_from_buyer: bool = Field(..., alias="noCommentFromBuyer")
    instruction_for_buyer: str | None = Field(None, alias="instructionForBuyer")
    instruction_for_seller: str | None = Field(None, alias="instructionForSeller")

    sequence: int = Field(..., alias="sequence")
    fee_multiplier: float | None = Field(None, alias="feeMultiplier")

    agreements: list[GameCategoryAgreement] = Field(..., alias="agreements")
    props: GameCategoryProps | None = Field(None, alias="props")


class GameCategoryObtainingTypeList(ApiModel):
    obtaining_types: list[GameCategoryObtainingType] = Field(..., alias="obtainingTypes")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "obtainingTypes" not in data and "obtaining_types" not in data:
            edges = data.get("edges") or []
            data["obtainingTypes"] = [
                (edge or {}).get("node") for edge in edges if (edge or {}).get("node")
            ]

        if "obtaining_types" in data and "obtainingTypes" not in data:
            data["obtainingTypes"] = data["obtaining_types"]

        return data


class GameCategoryInstruction(ApiModel):
    id: str = Field(..., alias="id")
    text: str = Field(..., alias="text")


class GameCategoryInstructionList(ApiModel):
    instructions: list[GameCategoryInstruction] = Field(..., alias="instructions")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "instructions" not in data:
            edges = data.get("edges") or []
            data["instructions"] = [
                (edge or {}).get("node") for edge in edges if (edge or {}).get("node")
            ]
        return data


class GameCategory(ApiModel):
    id: str = Field(..., alias="id")
    slug: str = Field(..., alias="slug")
    name: str = Field(..., alias="name")

    category_id: str | None = Field(None, alias="categoryId")
    game_id: str | None = Field(None, alias="gameId")

    obtaining: str | None = Field(None, alias="obtaining")

    options: list[GameCategoryOption] | None = Field(None, alias="options")
    props: GameCategoryProps | None = Field(None, alias="props")

    no_comment_from_buyer: bool | None = Field(None, alias="noCommentFromBuyer")
    instruction_for_buyer: str | None = Field(None, alias="instructionForBuyer")
    instruction_for_seller: str | None = Field(None, alias="instructionForSeller")

    use_custom_obtaining: bool | None = Field(None, alias="useCustomObtaining")
    auto_confirm_period: GameCategoryAutoConfirmPeriods | None = Field(
        None, alias="autoConfirmPeriod"
    )
    auto_moderation_mode: bool | None = Field(None, alias="autoModerationMode")

    agreements: list[GameCategoryAgreement] | None = Field(None, alias="agreements")
    fee_multiplier: float | None = Field(None, alias="feeMultiplier")


class GameProfile(ApiModel):
    """Профиль игры в сообщении. Это не карточка каталога: категорий и даты там нет."""

    id: str = Field(..., alias="id")
    slug: str | None = Field(None, alias="slug")
    name: str | None = Field(None, alias="name")
    type: GameType | None = Field(None, alias="type")
    logo: File | None = Field(None, alias="logo")


class Game(ApiModel):
    id: str = Field(..., alias="id")
    slug: str = Field(..., alias="slug")
    name: str = Field(..., alias="name")

    type: GameType = Field(..., alias="type")

    logo: File = Field(..., alias="logo")
    banner: File | None = Field(None, alias="banner")

    categories: list[GameCategory] = Field(..., alias="categories")
    created_at: datetime = Field(..., alias="createdAt")


class GameList(ApiModel):
    games: list[Game] = Field(..., alias="games")
    page_info: PageInfo = Field(..., alias="pageInfo")
    total_count: int = Field(..., alias="totalCount")

    @model_validator(mode="before")
    @classmethod
    def _inflate_from_edges(cls, data):
        if not isinstance(data, dict):
            return data

        if "games" not in data:
            edges = data.get("edges") or []
            data["games"] = [(edge or {}).get("node") for edge in edges if (edge or {}).get("node")]
        return data
