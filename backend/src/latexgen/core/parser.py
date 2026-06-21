"""Discover the dynamic fields declared in a LaTeX template.

The parser is the first stage of the pipeline (parser -> renderer -> compiler).
It scans the template for ``{{...}}`` markers using the shared grammar in
:mod:`latexgen.core.markers`, and returns one :class:`TemplateField` per
distinct field, in order of first appearance. The renderer later substitutes
these same markers, so both stages agree on what a marker is by construction.
"""

from __future__ import annotations

from .exceptions import ParseError
from .markers import MARKER_PATTERN
from .models import TemplateField

# The field types the parser recognises. An unknown type is a ParseError.
VALID_TYPES = frozenset({"string", "number", "date", "boolean", "enum"})


def parse_template(content: str) -> list[TemplateField]:
    """Extract the dynamic fields declared in ``content``.

    Fields are de-duplicated by name and returned in order of first appearance.
    A field repeated with a consistent declaration is collapsed into one entry;
    repeated with a conflicting declaration, it is an error.

    Args:
        content: The raw ``.tex`` template text.

    Returns:
        One :class:`TemplateField` per distinct field, in source order.

    Raises:
        ParseError: If a field declares an unsupported type, or if the same
            name appears with conflicting declarations.
    """
    seen: dict[str, TemplateField] = {}
    for match in MARKER_PATTERN.finditer(content):
        name = match.group(1)
        declared_type = (match.group(2) or "string").lower()
        raw_argument = match.group(3)

        if declared_type not in VALID_TYPES:
            raise ParseError(
                f"Unsupported type '{declared_type}' for field '{name}'. "
                f"Valid types: {', '.join(sorted(VALID_TYPES))}."
            )

        field = _build_field(name, declared_type, raw_argument)

        if name in seen:
            if seen[name] != field:
                raise ParseError(
                    f"Field '{name}' is declared inconsistently across markers."
                )
            continue
        seen[name] = field

    return list(seen.values())


def _build_field(
    name: str,
    declared_type: str,
    raw_argument: str | None,
) -> TemplateField:
    """Construct a :class:`TemplateField` from a marker's parts.

    An ``enum`` with no options carries no constraint, so it degrades to a plain
    string field. A ``date`` keeps its parenthesised argument as the strftime
    format; every other type ignores the argument.

    Args:
        name: The field identifier.
        declared_type: The validated type name.
        raw_argument: The text inside the marker's parentheses, or ``None``.

    Returns:
        The constructed field.
    """
    if declared_type == "enum":
        options = _split_options(raw_argument)
        if not options:
            return TemplateField(name=name, type="string")
        return TemplateField(name=name, type="enum", options=options)
    if declared_type == "date":
        date_format = raw_argument.strip() if raw_argument else None
        return TemplateField(
            name=name, type="date", date_format=date_format or None
        )
    return TemplateField(name=name, type=declared_type)


def _split_options(raw_argument: str | None) -> list[str]:
    """Split an enum's parenthesised argument into trimmed options.

    Each option is stripped of surrounding whitespace so an accidental space in
    ``enum(Admin, User )`` does not become part of the option text. Empty
    entries are dropped.

    Args:
        raw_argument: The comma-separated text inside the parentheses, or
            ``None``.

    Returns:
        The list of cleaned option values.
    """
    if not raw_argument:
        return []
    return [option.strip() for option in raw_argument.split(",") if option.strip()]