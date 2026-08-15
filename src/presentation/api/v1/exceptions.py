"""HTTP exception handlers."""

from __future__ import annotations

import logging

from fastapi import FastAPI, Request, status
from fastapi.responses import JSONResponse

from domain.exceptions import (
    AuthenticationError,
    AuthorizationError,
    DomainError,
    DuplicateEntityError,
    EmailNotVerifiedError,
    EntityNotFoundError,
    PaymentVerificationError,
    ValidationError,
)
from presentation.api.v1.schemas.responses import ErrorResponse

logger = logging.getLogger(__name__)


def register_exception_handlers(app: FastAPI) -> None:
    """Register domain → HTTP exception mapping."""

    @app.exception_handler(EntityNotFoundError)
    async def not_found_handler(_: Request, exc: EntityNotFoundError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_404_NOT_FOUND,
            content=ErrorResponse(detail=exc.message, code="not_found").model_dump(),
        )

    @app.exception_handler(DuplicateEntityError)
    async def duplicate_handler(_: Request, exc: DuplicateEntityError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_409_CONFLICT,
            content=ErrorResponse(detail=exc.message, code="duplicate").model_dump(),
        )

    @app.exception_handler(AuthenticationError)
    async def auth_handler(_: Request, exc: AuthenticationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_401_UNAUTHORIZED,
            content=ErrorResponse(detail=exc.message, code="authentication_error").model_dump(),
            headers={"WWW-Authenticate": "Bearer"},
        )

    @app.exception_handler(AuthorizationError)
    async def forbidden_handler(_: Request, exc: AuthorizationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(detail=exc.message, code="authorization_error").model_dump(),
        )

    @app.exception_handler(EmailNotVerifiedError)
    async def email_not_verified_handler(_: Request, exc: EmailNotVerifiedError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_403_FORBIDDEN,
            content=ErrorResponse(detail=exc.message, code="email_not_verified").model_dump(),
        )

    @app.exception_handler(ValidationError)
    async def validation_handler(_: Request, exc: ValidationError) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=ErrorResponse(detail=exc.message, code="validation_error").model_dump(),
        )

    @app.exception_handler(PaymentVerificationError)
    async def payment_verification_handler(
        _: Request, exc: PaymentVerificationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(
                detail=exc.message, code="payment_verification_error"
            ).model_dump(),
        )

    @app.exception_handler(DomainError)
    async def domain_handler(_: Request, exc: DomainError) -> JSONResponse:
        logger.warning("Domain error: %s", exc.message)
        return JSONResponse(
            status_code=status.HTTP_400_BAD_REQUEST,
            content=ErrorResponse(detail=exc.message, code="domain_error").model_dump(),
        )

    @app.exception_handler(Exception)
    async def unhandled_handler(_: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception")
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=ErrorResponse(
                detail="Internal server error", code="internal_error"
            ).model_dump(),
        )
