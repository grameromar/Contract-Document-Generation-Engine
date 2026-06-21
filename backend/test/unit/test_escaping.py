"""Unit tests for :mod:`latexgen.core.escaping`.

This module is the home for escaping-related test cases.
"""

from datetime import date
import pytest

from latexgen.core.escaping import escape_latex, get_escaper


class TestEscapeLatex:
    """Tests for the low-level :func:`escape_latex` helper."""

    def test_escapes_every_special_character(self):
        """All ten special characters map to their safe sequences."""
        source = r"\ & % $ # _ { } ~ ^"
        expected = (
            r"\textbackslash{} \& \% \$ \# \_ \{ \} \textasciitilde{} \textasciicircum{}"
        )
        assert escape_latex(source) == expected

    @pytest.mark.parametrize("simple_input", [
        "",                  # Edge case: empty string
        "Hello world",       # Standard plain text
        "1234567890-+=/:",   # Non-special LaTeX characters
        "café façade",       # Accented/Unicode text passes through untouched
    ])
    def test_plain_or_empty_text_is_unchanged(self, simple_input):
        """Text without special characters (or empty) passes through untouched."""
        assert escape_latex(simple_input) == simple_input

    def test_backslash_does_not_corrupt_later_escapes(self):
        """A single pass keeps the order-sensitive backslash escape intact."""
        assert escape_latex(r"\&") == r"\textbackslash{}\&"

    def test_prevents_command_injection(self):
        """A LaTeX command in user input becomes inert literal text."""
        assert (
            escape_latex(r"\input{/etc/passwd}")
            == r"\textbackslash{}input\{/etc/passwd\}"
        )

    def test_complex_nested_and_repeated_special_characters(self):
        """Complex case: multiple consecutive and repeated special characters."""
        source = r"%$#__{}&&"
        expected = r"\%\$\#\_\_\{\}\&\&"
        assert escape_latex(source) == expected


class TestStringEscaper:
    """Tests for the ``string`` escaper."""

    def test_escapes_user_text(self):
        esc = get_escaper("string")
        assert esc("Juan & Co.") == r"Juan \& Co."

    @pytest.mark.parametrize("input_val,expected", [
        (42, "42"),
        (3.1416, "3.1416"),
        (None, ""),  # Edge case: None becomes an empty string
    ])
    def test_coerces_non_string_values(self, input_val, expected):
        """Coerces integers, floats, and None into safe string formats."""
        esc = get_escaper("string")
        assert esc(input_val) == expected

    def test_complex_string_with_mixed_types_and_latex(self):
        """Complex case: text, numbers, and potential LaTeX injections mixed."""
        esc = get_escaper("string")
        assert esc(r"Item #1: 100% & more") == r"Item \#1: 100\% \& more"


class TestNumberEscaper:
    """Tests for the ``number`` escaper."""

    @pytest.mark.parametrize("input_val,expected", [
        ("1234567", "1,234,567"),
        (1000000, "1,000,000"),
        ("1234.56", "1,234.56"),
        (1234.5, "1,234.5"),        # Native float keeps its decimal part
        (1500.0, "1,500.0"),        # Decimal notation preserved from a float
        (0, "0"),                   # Integer zero
        ("0.0", "0.0"),             # Floating-point zero
        ("-4500", "-4,500"),        # Negative integer
        ("-123456.78", "-123,456.78"),
        ("1,23,45", "12,345"),      # Malformed grouping: commas are cosmetic
        (" 1000 ", "1,000"),        # Surrounding whitespace is ignored
    ])
    def test_valid_numbers_formatting(self, input_val, expected):
        """Thousands/decimal separators across positive, negative and zero values."""
        assert get_escaper("number")(input_val) == expected

    def test_strips_grouping_from_input(self):
        assert get_escaper("number")("1,250") == "1,250"

    @pytest.mark.parametrize("invalid_input", [
        "abc",
        "12.34.56",   # Complex case: malformed numeric format
        "",           # Edge case: empty string
        None,         # Edge case: wrong type (str(None) -> "None")
    ])
    def test_rejects_non_numeric(self, invalid_input):
        """Invalid formats and bad data types raise an exception."""
        with pytest.raises((ValueError, TypeError)):
            get_escaper("number")(invalid_input)


class TestDateEscaper:
    """Tests for the ``date`` escaper and its configurable format."""

    def test_default_format_is_iso(self):
        assert get_escaper("date")("2026-06-20") == "2026-06-20"

    def test_custom_format(self):
        esc = get_escaper("date", date_format="%d/%m/%Y")
        assert esc("2026-06-20") == "20/06/2026"

    def test_accepts_date_object(self):
        assert get_escaper("date")(date(2026, 6, 20)) == "2026-06-20"

    @pytest.mark.parametrize("invalid_date", [
        "20/06/2026",   # Wrong format order
        "2026-13-40",   # Valid ISO structure but impossible calendar date
        "not-a-date",   # Plain invalid text
        "",             # Empty string
    ])
    def test_rejects_invalid_date_inputs(self, invalid_date):
        """Bad formats and invalid calendar dates are caught."""
        with pytest.raises(ValueError):
            get_escaper("date")(invalid_date)


class TestBooleanEscaper:
    """Tests for the ``boolean`` escaper."""

    @pytest.mark.parametrize("value", [
        "true", "1", "yes", "si", "sí", True,
        "TRUE", "Yes", "SÍ",   # Casing variations
        " yes ",               # Surrounding whitespace is ignored
    ])
    def test_truthy_values(self, value):
        assert get_escaper("boolean")(value) == "Sí"

    @pytest.mark.parametrize("value", [
        "false", "0", "no", "", False,
        "FALSE", "No",   # Casing variations
    ])
    def test_falsy_values(self, value):
        assert get_escaper("boolean")(value) == "No"

    def test_complex_unknown_boolean_strings(self):
        """Complex case: ambiguous/non-binary strings must not convert blindly."""
        esc = get_escaper("boolean")
        with pytest.raises(ValueError):
            esc("maybe")


class TestEnumEscaper:
    """Tests for the ``enum`` escaper."""

    def test_accepts_allowed_option(self):
        esc = get_escaper("enum", options=["México", "USA", "Canadá"])
        assert esc("México") == "México"

    def test_rejects_disallowed_option(self):
        esc = get_escaper("enum", options=["México", "USA"])
        with pytest.raises(ValueError):
            esc("Brasil")

    def test_escapes_special_characters_in_option(self):
        esc = get_escaper("enum", options=["R&D"])
        assert esc("R&D") == r"R\&D"

    def test_complex_case_sensitive_and_whitespace_options(self):
        """Complex case: matching is strict on capitalization and whitespace."""
        esc = get_escaper("enum", options=["Admin", "User "])
        with pytest.raises(ValueError):
            esc("admin")   # Fails: case-sensitive
        with pytest.raises(ValueError):
            esc("User")    # Fails: trailing whitespace is significant

    def test_enum_without_options_behaves_like_string(self):
        """An enum with no options carries no constraint and escapes as text."""
        esc = get_escaper("enum")
        assert esc("a & b") == r"a \& b"


class TestFactory:
    """Tests for the :func:`get_escaper` factory itself."""

    def test_unknown_type_raises(self):
        with pytest.raises(ValueError):
            get_escaper("color")