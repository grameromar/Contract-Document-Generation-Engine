"""Render a LaTeX template by substituting type-escaped field values.

The renderer is the second stage of the pipeline (parser -> renderer ->
compiler). It receives the template together with the fields already discovered
by the parser, validates that every required field has a value, escapes each
value according to its type, and replaces every ``{{marker}}`` with the result.
The marker syntax mirrors the parser's, so ``{{name}}``, ``{{name:type}}`` and
``{{name:enum(a,b,c)}}`` are all substituted by the value of ``name``.
"""

from __future__ import annotations

import re


from .escaping import DEFAULT_DATE_FORMAT, get_escaper
from .exceptions import InvalidFieldValueError, MissingFieldsError
from .markers import MARKER_PATTERN
from .models import TemplateField

class Renderer:
    """Substitute ``{{field}}`` markers in a template with escaped values."""

    def render(
        self,
        template: str,
        fields: list[TemplateField],
        values: dict[str, object],
    ) -> str:
        """Render ``template`` by substituting escaped values for its markers.

        Args:
            template: The raw ``.tex`` content containing ``{{...}}`` markers.
            fields: The fields discovered in the template by the parser.
            values: A mapping from field name to the raw value supplied by the
                user.

        Returns:
            The template with every marker replaced by its escaped value.

        Raises:
            MissingFieldsError: If any required field has no value.
            InvalidFieldValueError: If a value fails its type's validation.
        """
        missing = [
            field.name
            for field in fields
            if field.required and self._is_empty(values.get(field.name))
        ]
        if missing:
            raise MissingFieldsError(missing)

        escaped = self._escape_fields(fields, values)

        def _substitute(match: re.Match) -> str:
            name = match.group(1)
            # A marker whose field is unknown is left untouched rather than
            # silently deleted, which surfaces template/field mismatches.
            return escaped.get(name, match.group(0))

        return MARKER_PATTERN.sub(_substitute, template)

    def _escape_fields(
        self,
        fields: list[TemplateField],
        values: dict[str, object],
    ) -> dict[str, str]:
        """Escape each field's value into a name -> escaped-text mapping.

        Required fields are already validated, so any empty value reaching this
        method belongs to an optional field and renders as an empty string.

        Args:
            fields: The fields to escape.
            values: The raw values supplied by the user.

        Returns:
            A mapping from field name to its escaped, LaTeX-safe text.

        Raises:
            InvalidFieldValueError: If a value fails its type's validation.
        """
        escaped: dict[str, str] = {}
        for field in fields:
            raw = values.get(field.name)
            if self._is_empty(raw):
                escaped[field.name] = ""
                continue
            escaper = get_escaper(
                field.type,
                options=field.options,
                date_format=field.date_format or DEFAULT_DATE_FORMAT,
            )
            try:
                escaped[field.name] = escaper(raw)
            except ValueError as exc:
                raise InvalidFieldValueError(field.name, str(exc)) from exc
        return escaped

    @staticmethod
    def _is_empty(value: object) -> bool:
        """Return whether a value counts as "not supplied".

        ``None`` and strings that are empty or whitespace-only are treated as
        empty; every other value (including ``0`` and ``False``) is not.

        Args:
            value: The raw value to test.

        Returns:
            ``True`` if the value is considered absent, ``False`` otherwise.
        """
        return value is None or (isinstance(value, str) and not value.strip())