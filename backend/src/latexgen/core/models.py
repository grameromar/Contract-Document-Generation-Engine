"""Core domain models shared across the latexgen package.

These are plain dataclasses with no dependency on any web or desktop framework,
so the same objects flow through the parser, the renderer and either delivery
layer unchanged.
"""

from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class TemplateField:
    """A dynamic field discovered in a LaTeX template.

    Attributes:
        name: The identifier used in the marker, e.g. ``"start_date"``.
        type: The declared type: ``"string"``, ``"number"``, ``"date"``,
            ``"boolean"`` or ``"enum"``. Defaults to ``"string"``.
        required: Whether a value must be supplied. Defaults to ``True``.
        options: Allowed values for an ``enum`` field; empty for other types.
        date_format: strftime pattern for a ``date`` field; ``None`` means the
            default ISO format is used.
    """

    name: str
    type: str = "string"
    required: bool = True
    options: list[str] = field(default_factory=list)
    date_format: str | None = None