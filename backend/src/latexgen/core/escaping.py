"""Type-aware escaping of user-provided values for safe insertion into LaTeX.

LaTeX assigns syntactic meaning to ten characters. Inserting a raw value that
contains any of them produces either a compilation error or a visually broken
PDF (for example, an unescaped ``%`` turns the rest of the line into a comment
and silently deletes it). Escaping replaces each special character with a
command sequence that renders it as literal text, and it doubles as the first
line of defense against command injection: an escaped ``\\input{...}`` becomes
inert text instead of an executable macro.

Escaping is *type-aware* because different field types require different
handling. A free-text ``string`` must escape all ten special characters, while
a ``number`` is validated and formatted, a ``date`` is parsed and rendered with
a caller-chosen pattern, a ``boolean`` is mapped to safe display text, and an
``enum`` value is validated against a closed set of options. A small factory,
:func:`get_escaper`, returns the appropriate strategy for a given type.
"""

from __future__ import annotations

from datetime import date
from typing import Callable

# Mapping from each LaTeX special character to its safe replacement sequence.
#
# Three of these (``~``, ``^`` and ``\``) cannot be escaped with a leading
# backslash, because ``\~``, ``\^`` and ``\\`` already mean something else in
# LaTeX (the first two are accents, the third is a line break). They require the
# dedicated ``\textasciitilde``, ``\textasciicircum`` and ``\textbackslash``
# commands instead.
_LATEX_SPECIAL_CHARACTERS = {
    "\\": r"\textbackslash{}",
    "&": r"\&",
    "%": r"\%",
    "$": r"\$",
    "#": r"\#",
    "_": r"\_",
    "{": r"\{",
    "}": r"\}",
    "~": r"\textasciitilde{}",
    "^": r"\textasciicircum{}",
}

# A translation table consumed by ``str.translate``. Building it once lets every
# call apply all substitutions in a single pass. The single pass is essential:
# sequential replacement would be order-dependent, and escaping ``\`` after
# ``&`` would corrupt the backslashes just introduced by the ``&`` -> ``\&`` step.
_LATEX_TRANSLATION_TABLE = str.maketrans(_LATEX_SPECIAL_CHARACTERS)

# strftime pattern used when a caller does not request a specific date format.
DEFAULT_DATE_FORMAT = "%Y-%m-%d"

# Textual representations (English and Spanish) accepted as boolean "true".
_TRUTHY_STRINGS = frozenset(
    {"true", "1", "yes", "y", "si", "sí", "on", "verdadero"}
)

# A callable that converts a single raw field value into a LaTeX-safe string.
Escaper = Callable[[object], str]


def escape_latex(text: str) -> str:
    """Escape every LaTeX special character in ``text``.

    Args:
        text: Arbitrary plain text destined to be inserted into a LaTeX
            document.

    Returns:
        The same text with each of the ten LaTeX special characters replaced by
        a sequence that renders it literally.

    Example:
        >>> print(escape_latex("50% off & more"))
        50\% off \& more
    """
    return text.translate(_LATEX_TRANSLATION_TABLE)


def _escape_string(value: object) -> str:
    """Escape an arbitrary value as LaTeX-safe free text.

    The value is coerced to ``str`` first so that non-string inputs (for
    instance a number arriving through a generic form payload) are handled
    gracefully rather than raising.

    Args:
        value: The raw value entered by the user.

    Returns:
        The stringified value with all LaTeX special characters escaped.
    """
    return escape_latex(str(value))


def _escape_number(value: object) -> str:
    """Validate that ``value`` is numeric and format it with grouping.

    Integers, floats and numeric strings are accepted. Grouping separators
    already present in a string input are stripped before parsing, so an input
    of ``"1,250"`` is treated as ``1250``. Integer-valued inputs are rendered
    without a decimal part.

    Args:
        value: The raw value, expected to represent a number.

    Returns:
        The number formatted with commas as thousands separators, e.g.
        ``"1,234,567"`` or ``"1,234,567.89"``.

    Raises:
        ValueError: If ``value`` cannot be interpreted as a number.
    """
    try:
        number = float(str(value).replace(",", "").strip())
    except (TypeError, ValueError):
        raise ValueError(f"Expected a numeric value, received: {value!r}")
    if number.is_integer():
        return f"{int(number):,}"
    return f"{number:,}"


def _make_date_escaper(date_format: str = DEFAULT_DATE_FORMAT) -> Escaper:
    """Build a date escaper bound to a specific output format.

    The format is captured at construction time so the resulting escaper keeps
    the uniform ``Escaper`` signature ``(value) -> str`` that the renderer
    expects for every field type.

    Args:
        date_format: A strftime pattern describing how the date should be
            rendered, e.g. ``"%d/%m/%Y"`` or ``"%d de %B de %Y"``. Defaults to
            ISO 8601 (``"%Y-%m-%d"``). Note that locale-dependent directives
            such as ``%B`` follow the process locale.

    Returns:
        An :data:`Escaper` that parses an ISO date and formats it with
        ``date_format``.
    """

    def _escape_date(value: object) -> str:
        """Parse an ISO date value and format it with the bound pattern.

        Args:
            value: A :class:`datetime.date` instance, or an ISO string
                (``"YYYY-MM-DD"``) as produced by an HTML
                ``<input type="date">``.

        Returns:
            The date rendered according to the bound strftime pattern.

        Raises:
            ValueError: If ``value`` is not a valid ISO date.
        """
        if isinstance(value, date):
            parsed = value
        else:
            try:
                parsed = date.fromisoformat(str(value).strip())
            except (TypeError, ValueError):
                raise ValueError(
                    f"Expected an ISO date (YYYY-MM-DD), received: {value!r}"
                )
        return parsed.strftime(date_format)

    return _escape_date


def _escape_boolean(value: object) -> str:
    """Map a truthy or falsy value to a safe textual representation.

    Recognises native Python booleans as well as common textual forms in
    English and Spanish (``"true"``, ``"1"``, ``"yes"``, ``"sí"``, ...). The
    output text is fixed by this function, so it is safe by construction and
    needs no escaping.

    Args:
        value: The raw value to interpret as a boolean.

    Returns:
        ``"Sí"`` when the value is truthy, ``"No"`` otherwise.
    """
    if isinstance(value, bool):
        is_true = value
    else:
        is_true = str(value).strip().lower() in _TRUTHY_STRINGS
    return "Sí" if is_true else "No"


def _make_enum_escaper(options: list[str]) -> Escaper:
    """Build an enum escaper that only accepts a fixed set of options.

    Args:
        options: The values declared in the template marker, e.g. the
            ``["México", "USA", "Canadá"]`` from
            ``"{{country:enum(México,USA,Canadá)}}"``.

    Returns:
        An :data:`Escaper` that validates its input against ``options`` and then
        escapes it as text (an option may itself contain special characters).
    """
    allowed = set(options)

    def _escape_enum(value: object) -> str:
        """Validate ``value`` against the allowed options and escape it.

        Args:
            value: The selected value, expected to be one of the options.

        Returns:
            The escaped option text.

        Raises:
            ValueError: If ``value`` is not one of the allowed options.
        """
        text = str(value)
        if text not in allowed:
            raise ValueError(
                f"Value '{text}' is not among the allowed options: {options}"
            )
        return escape_latex(text)

    return _escape_enum


# Escapers whose behaviour needs no per-field configuration. Date and enum are
# handled separately in the factory because they are parameterised.
_SIMPLE_ESCAPERS: dict[str, Escaper] = {
    "string": _escape_string,
    "number": _escape_number,
    "boolean": _escape_boolean,
}


def get_escaper(
    field_type: str,
    *,
    options: list[str] | None = None,
    date_format: str = DEFAULT_DATE_FORMAT,
) -> Escaper:
    """Return the escaper appropriate for ``field_type``.

    This is the Factory entry point used by the renderer: given a field's
    declared type, it returns a callable that knows how to validate, format and
    escape values of that type. The configuration arguments are keyword-only and
    each is consumed by exactly one type; the rest are ignored.

    Args:
        field_type: One of ``"string"``, ``"number"``, ``"date"``,
            ``"boolean"`` or ``"enum"``.
        options: Allowed values for an ``enum`` field; ignored otherwise.
        date_format: strftime pattern for a ``date`` field; ignored otherwise.

    Returns:
        An :data:`Escaper` callable for the given type.

    Raises:
        ValueError: If ``field_type`` has no associated escaper.
    """
    if field_type == "enum":
        return _make_enum_escaper(options or [])
    if field_type == "date":
        return _make_date_escaper(date_format)
    try:
        return _SIMPLE_ESCAPERS[field_type]
    except KeyError:
        raise ValueError(f"No escaper available for type: {field_type}")