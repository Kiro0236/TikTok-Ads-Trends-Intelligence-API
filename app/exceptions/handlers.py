"""
Registers exception handlers that translate AppError (and unhandled
exceptions) into the consistent JSON error envelope used across the API.
"""
import logging

from fastapi import FastAPI, Request, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

from app.exceptions.errors import AppError

logger = logging.getLogger("tiktok_ads_api")


def _error_body(code: str, message: str, details: dict | None = None) -> dict:
    return {
        "error": {
            "code": code,
            "message": message,
            "details": details or {},
        }
    }


def register_exception_handlers(app: FastAPI) -> None:
    @app.exception_handler(AppError)
    async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
        logger.warning(
            "AppError handled: %s | path=%s | details=%s",
            exc.code,
            request.url.path,
            exc.details,
        )
        return JSONResponse(
            status_code=exc.status_code,
            content=_error_body(exc.code, exc.message, exc.details),
        )

    @app.exception_handler(RequestValidationError)
    async def validation_error_handler(
        request: Request, exc: RequestValidationError
    ) -> JSONResponse:
        return JSONResponse(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            content=_error_body(
                "INVALID_PARAMETERS",
                "One or more request parameters are invalid.",
                {"errors": exc.errors()},
            ),
        )

    @app.exception_handler(NotImplementedError)
    async def not_implemented_handler(request: Request, exc: NotImplementedError) -> JSONResponse:
        # Raised by LiveDataProviderClient stub methods when
        # DATA_PROVIDER_MODE=live but no real provider is wired in yet.
        logger.warning("NotImplementedError on path=%s: %s", request.url.path, exc)
        return JSONResponse(
            status_code=status.HTTP_501_NOT_IMPLEMENTED,
            content=_error_body(
                "PROVIDER_NOT_IMPLEMENTED",
                "The live data provider is not yet configured for this operation.",
            ),
        )

    @app.exception_handler(Exception)
    async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
        logger.exception("Unhandled exception on path=%s", request.url.path)
        return JSONResponse(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            content=_error_body(
                "INTERNAL_ERROR",
                "An unexpected error occurred. Please try again later.",
            ),
        )
