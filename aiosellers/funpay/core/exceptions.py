from __future__ import annotations


class FunPayError(Exception):
    pass


class AccountNotInitiatedError(FunPayError):
    pass


class RequestFailedError(FunPayError):
    def __init__(
        self,
        message: str = "",
        *,
        status_code: int | None = None,
        body: str = "",
    ) -> None:
        self.status_code = status_code
        self.body = (body or "")[:500]
        super().__init__(message or self.body or "request failed")


class UnauthorizedError(RequestFailedError):
    pass


class RateLimitedError(RequestFailedError):
    pass


class WithdrawError(RequestFailedError):
    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        body: str = "",
    ) -> None:
        self.message = message
        super().__init__(message or "", status_code=status_code, body=body)


class RaiseError(RequestFailedError):
    def __init__(
        self,
        category_id: int,
        message: str | None,
        wait_seconds: int,
        *,
        status_code: int | None = None,
        body: str = "",
    ) -> None:
        self.category_id = category_id
        self.message = message
        self.wait_seconds = wait_seconds
        super().__init__(message or "", status_code=status_code, body=body)


class ImageUploadError(RequestFailedError):
    def __init__(
        self,
        message: str | None = None,
        *,
        status_code: int | None = None,
        body: str = "",
    ) -> None:
        self.message = message
        super().__init__(message or "", status_code=status_code, body=body)


class MessageNotDeliveredError(RequestFailedError):
    def __init__(
        self,
        message: str | None,
        chat_id: int | str,
        *,
        status_code: int | None = None,
        body: str = "",
    ) -> None:
        self.message = message
        self.chat_id = chat_id
        super().__init__(message or "", status_code=status_code, body=body)


class FeedbackEditingError(RequestFailedError):
    def __init__(
        self,
        message: str | None,
        order_id: str,
        *,
        status_code: int | None = None,
        body: str = "",
    ) -> None:
        self.message = message
        self.order_id = order_id
        super().__init__(message or "", status_code=status_code, body=body)


class LotParsingError(RequestFailedError):
    def __init__(
        self,
        message: str | None,
        lot_id: int,
        *,
        status_code: int | None = None,
        body: str = "",
    ) -> None:
        self.message = message
        self.lot_id = lot_id
        super().__init__(message or "", status_code=status_code, body=body)


class LotSavingError(RequestFailedError):
    def __init__(
        self,
        message: str | None,
        *,
        lot_id: int | None,
        errors: dict[str, str],
        status_code: int | None = None,
        body: str = "",
    ) -> None:
        self.message = message
        self.lot_id = lot_id
        self.errors = errors
        super().__init__(message or "", status_code=status_code, body=body)


class RefundError(RequestFailedError):
    def __init__(
        self,
        message: str | None,
        order_id: str,
        *,
        status_code: int | None = None,
        body: str = "",
    ) -> None:
        self.message = message
        self.order_id = order_id
        super().__init__(message or "", status_code=status_code, body=body)
