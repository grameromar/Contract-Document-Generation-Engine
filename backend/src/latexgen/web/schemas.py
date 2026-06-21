"""Pydantic schemas for the web API.

These translate the core's plain dataclasses (which stay framework-free) to and
from JSON. Keeping the translation here lets the core remain usable from a
non-web context, such as a desktop app, without importing Pydantic.
"""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict, Field


class FieldSchema(BaseModel):
    """JSON representation of a :class:`~latexgen.core.models.TemplateField`.

    ``from_attributes`` lets it be built directly from the core dataclass with
    ``FieldSchema.model_validate(template_field)``.
    """

    model_config = ConfigDict(from_attributes=True)

    name: str
    type: str
    required: bool
    options: list[str]
    date_format: str | None


class ParseRequest(BaseModel):
    """Request body for ``POST /parse``."""

    template: str = Field(..., description="Raw .tex template text.")


class ParseResponse(BaseModel):
    """Response body for ``POST /parse``: the discovered fields."""

    fields: list[FieldSchema]