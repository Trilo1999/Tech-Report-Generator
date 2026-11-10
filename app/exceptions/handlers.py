import asyncio

from fastapi import Request
from fastapi.encoders import jsonable_encoder
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.config.log_config import logger
from app.exceptions.domain import AppError


async def request_validation_handler(
    request: Request, exc: RequestValidationError
) -> JSONResponse:
    """Handle Pydantic request validation errors (422 or 400 for security guardrail violations).

    Args:
        request: The FastAPI request.
        exc: The validation error exception.

    Returns:
        JSONResponse with appropriate status and sanitized validation details.
    """
    errors = jsonable_encoder(exc.errors())

    # Detect if validation was blocked by security guardrails
    is_security_error = any(
        "security guardrail" in str(err.get("msg", "")).lower()
        or "prompt injection" in str(err.get("msg", "")).lower()
        for err in errors
    )

    if is_security_error:
        security_msg = next(
            (
                str(err.get("msg", ""))
                for err in errors
                if "security guardrail" in str(err.get("msg", "")).lower()
                or "prompt injection" in str(err.get("msg", "")).lower()
            ),
            "Adversarial or prompt injection pattern detected in input.",
        )
        # Clean up Pydantic prefix if present
        if security_msg.startswith("Value error, "):
            security_msg = security_msg[len("Value error, ") :]

        return JSONResponse(
            status_code=400,
            content={
                "error": {
                    "code": "security_validation_error",
                    "message": security_msg,
                    "details": errors,
                },
                "detail": security_msg,
                "path": request.url.path,
            },
        )

    return JSONResponse(
        status_code=422,
        content={
            "error": {
                "code": "validation_error",
                "message": "Validation error",
                "details": errors,
            },
            "detail": "Validation error",
            "path": request.url.path,
        },
    )


async def http_exception_handler(
    request: Request, exc: StarletteHTTPException
) -> JSONResponse:
    """Handle FastAPI/Starlette HTTPException.

    Args:
        request: The FastAPI request.
        exc: The HTTP exception.

    Returns:
        JSONResponse with exception status and detail.
    """
    status_code = exc.status_code
    detail = exc.detail
    return JSONResponse(
        status_code=status_code,
        content={
            "error": {
                "code": "http_error",
                "message": detail,
            },
            "detail": detail,
            "path": request.url.path,
        },
    )


async def app_error_handler(request: Request, exc: AppError) -> JSONResponse:
    """Handle domain AppError and subclasses (response shape from domain).

    Args:
        request: The FastAPI request.
        exc: The domain AppError instance.

    Returns:
        JSONResponse with status_code and content from exc.to_response_content().
    """
    return JSONResponse(
        status_code=exc.status_code,
        content=exc.to_response_content(request.url.path),
    )


async def global_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Catch-all for unhandled exceptions; log and return safe 500 response.

    Args:
        request: The FastAPI request.
        exc: The unhandled exception.

    Returns:
        JSONResponse with 500 status and generic error message.
    """
    logger.exception(
        "Unhandled exception",
        extra={"path": request.url.path, "method": request.method},
    )
    return JSONResponse(
        status_code=500,
        content={
            "error": {
                "code": "internal_server_error",
                "message": "Internal Server Error",
            },
            "path": request.url.path,
        },
    )


async def cancelled_error_handler(
    request: Request, exc: asyncio.CancelledError
) -> None:
    """Re-raise CancelledError so it is not logged as an unhandled exception.

    Args:
        request: The FastAPI request.
        exc: The CancelledError (re-raised).
    """
    raise exc
