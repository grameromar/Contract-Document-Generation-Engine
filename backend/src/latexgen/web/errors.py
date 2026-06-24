"""Map core domain exceptions to HTTP responses.

User-facing document problems (bad template, missing or invalid values, failed
compilation) become ``422 Unprocessable Entity``; an environment problem (the
compiler executable missing) becomes ``503 Service Unavailable``. Registering
these here keeps the route handlers free of try/except boilerplate.
"""

from __future__ import annotations

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from latexgen.core.exceptions import (
    CompileError,
    CompilerNotFoundError,
    InvalidFieldValueError,
    MissingFieldsError,
    ParseError,
)

_UNPROCESSABLE = 422
_SERVICE_UNAVAILABLE = 503


def register_exception_handlers(app: FastAPI) -> None:
    """Attach handlers translating domain exceptions to JSON responses."""

    @app.exception_handler(ParseError)
    async def _on_parse_error(request: Request, exc: ParseError) -> JSONResponse:
        return JSONResponse(
            status_code=_UNPROCESSABLE, 
            content={"detail": str(exc)}
        )

    @app.exception_handler(MissingFieldsError)
    async def _on_missing_fields( request: Request, exc: MissingFieldsError ) -> JSONResponse:
        return JSONResponse(
            status_code=_UNPROCESSABLE,
            content={"detail": str(exc), "missing_fields": exc.missing_fields},
        )

    @app.exception_handler(InvalidFieldValueError)
    async def _on_invalid_value( request: Request, exc: InvalidFieldValueError ) -> JSONResponse:
        return JSONResponse(
            status_code=_UNPROCESSABLE,
            content={"detail": str(exc), "field": exc.field_name},
        )

    @app.exception_handler(CompileError)
    async def _on_compile_error( request: Request, exc: CompileError ) -> JSONResponse:
        return JSONResponse(
            status_code=_UNPROCESSABLE,
            content={"detail": "LaTeX compilation failed.", "errors": exc.errors},
        )

    @app.exception_handler(CompilerNotFoundError)
    async def _on_compiler_missing( request: Request, exc: CompilerNotFoundError ) -> JSONResponse:
        return JSONResponse(
            status_code=_SERVICE_UNAVAILABLE, 
            content={"detail": str(exc)}
        )