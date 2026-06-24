"""FastAPI application factory for the latexgen web API.

``create_app`` wires the pieces together: CORS for the frontend (with origins
read from the YAML config), the domain exception handlers, and the API routes.
Exposing a factory keeps construction explicit and test-friendly.
"""

from __future__ import annotations

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from .config import load_settings
from .errors import register_exception_handlers
from .routes import router


def create_app() -> FastAPI:
    """Build and return the configured FastAPI application."""
    settings = load_settings()
    app = FastAPI(
        title="latexgen",
        version="0.1.0",
        description="Generate PDFs from LaTeX templates with dynamic fields.",
    )
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    register_exception_handlers(app)
    app.include_router(router)
    return app


app = create_app()