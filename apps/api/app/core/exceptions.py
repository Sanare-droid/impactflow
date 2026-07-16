from __future__ import annotations

from typing import Any, Optional

from fastapi import HTTPException, status


class AppError(Exception):
    def __init__(
        self,
        message: str,
        *,
        code: str = "app_error",
        status_code: int = status.HTTP_400_BAD_REQUEST,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.message = message
        self.code = code
        self.status_code = status_code
        self.details = details or {}
        super().__init__(message)


class NotFoundError(AppError):
    def __init__(self, message: str = "Resource not found", **kwargs: Any) -> None:
        super().__init__(
            message, code="not_found", status_code=status.HTTP_404_NOT_FOUND, **kwargs
        )


class UnauthorizedError(AppError):
    def __init__(self, message: str = "Unauthorized", **kwargs: Any) -> None:
        super().__init__(
            message,
            code="unauthorized",
            status_code=status.HTTP_401_UNAUTHORIZED,
            **kwargs,
        )


class ForbiddenError(AppError):
    def __init__(self, message: str = "Forbidden", **kwargs: Any) -> None:
        super().__init__(
            message, code="forbidden", status_code=status.HTTP_403_FORBIDDEN, **kwargs
        )


class ConflictError(AppError):
    def __init__(self, message: str = "Conflict", **kwargs: Any) -> None:
        super().__init__(
            message, code="conflict", status_code=status.HTTP_409_CONFLICT, **kwargs
        )


def to_http_exception(exc: AppError) -> HTTPException:
    return HTTPException(
        status_code=exc.status_code,
        detail={
            "message": exc.message,
            "code": exc.code,
            "details": exc.details,
        },
    )
