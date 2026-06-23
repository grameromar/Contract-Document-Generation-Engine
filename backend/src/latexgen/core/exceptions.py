"""Domain-specific exceptions raised by the latexgen core.

A small hierarchy lets the delivery layers (web, desktop) translate failures
into user-facing messages: catching :class:`RenderError` covers anything that
went wrong while turning user input into a rendered document.
"""

from __future__ import annotations


class LatexGenError(Exception):
    """Base class for every domain error raised by the latexgen core."""


class RenderError(LatexGenError):
    """Base class for errors raised while rendering a template."""


class MissingFieldsError(RenderError):
    """Raised when one or more required fields have no value.

    Attributes:
        missing_fields: The names of the required fields left unfilled.
    """

    def __init__(self, missing_fields: list[str]) -> None:
        self.missing_fields = list(missing_fields)
        joined = ", ".join(self.missing_fields)
        super().__init__(f"Missing required fields: {joined}")


class InvalidFieldValueError(RenderError):
    """Raised when a field value fails its type's validation.

    Attributes:
        field_name: The field whose value was rejected.
        reason: A human-readable explanation from the underlying escaper.
    """

    def __init__(self, field_name: str, reason: str) -> None:
        self.field_name = field_name
        self.reason = reason
        super().__init__(f"Invalid value for field '{field_name}': {reason}")

class ParseError(LatexGenError):
    """Raised when a template's markers cannot be parsed.

    Covers unsupported field types and fields declared inconsistently across
    repeated markers.
    """

class CompilerNotFoundError(LatexGenError):
    """Raised when the LaTeX compiler executable cannot be found.

    This is an environment/configuration problem rather than a fault in the
    user's document, so it is raised instead of being reported as a failed
    compilation result.
    """

class CompileError(LatexGenError):
    """Raised when rendered LaTeX source fails to compile to a PDF.

    The service raises this from a failed :class:`~latexgen.core.models.
    CompileResult`, turning the compiler's data result into a domain exception
    that the delivery layer can map to a user-facing error.

    Attributes:
        errors: Human-readable error lines extracted from the compiler output.
        log: The full compiler output, for debugging.
    """

    def __init__(self, errors: list[str], log: str = "") -> None:
        self.errors = list(errors)
        self.log = log
        super().__init__("; ".join(self.errors) or "LaTeX compilation failed.")