"""Unit tests for :mod:`latexgen.core.parser`."""

import pytest

from latexgen.core.exceptions import ParseError
from latexgen.core.models import TemplateField
from latexgen.core.parser import parse_template


class TestBasicParsing:
    """Field discovery, typing, and order preservation."""

    def test_detects_a_plain_field_as_string(self):
        assert parse_template("Hello {{name}}") == [TemplateField("name")]

    def test_reads_declared_types(self):
        fields = parse_template("{{age:number}} {{when:date}} {{ok:boolean}}")
        assert [(f.name, f.type) for f in fields] == [
            ("age", "number"),
            ("when", "date"),
            ("ok", "boolean"),
        ]

    def test_ignores_surrounding_whitespace_in_marker(self):
        assert parse_template("{{  name : number  }}") == [
            TemplateField("name", "number")
        ]

    def test_preserves_order_of_first_appearance(self):
        fields = parse_template("{{b}} {{a}} {{c}}")
        assert [f.name for f in fields] == ["b", "a", "c"]


class TestEnum:
    """Enum option parsing and the no-options degradation."""

    def test_parses_options(self):
        (field,) = parse_template("{{c:enum(A,B,C)}}")
        assert field.type == "enum"
        assert field.options == ["A", "B", "C"]

    def test_trims_whitespace_in_options(self):
        (field,) = parse_template("{{c:enum(Admin, User , Guest)}}")
        assert field.options == ["Admin", "User", "Guest"]

    def test_enum_without_options_degrades_to_string(self):
        assert parse_template("{{c:enum()}}") == [TemplateField("c", "string")]
        assert parse_template("{{c:enum}}") == [TemplateField("c", "string")]


class TestDate:
    """Date format capture."""

    def test_captures_format(self):
        (field,) = parse_template("{{d:date(%d/%m/%Y)}}")
        assert field.type == "date"
        assert field.date_format == "%d/%m/%Y"

    def test_date_without_format_uses_none(self):
        (field,) = parse_template("{{d:date}}")
        assert field.date_format is None


class TestDeduplication:
    """Repeated markers collapse, conflicting ones raise."""

    def test_consistent_repetition_is_collapsed(self):
        assert parse_template("{{x}} and {{x}}") == [TemplateField("x")]

    def test_conflicting_repetition_raises(self):
        with pytest.raises(ParseError):
            parse_template("{{x:number}} and {{x:string}}")


class TestErrors:
    """Type validation."""

    def test_unsupported_type_raises(self):
        with pytest.raises(ParseError):
            parse_template("{{x:color}}")

class TestOptionalFields:
    """A trailing ``?`` on the name marks a field optional."""

    def test_plain_optional_field(self):
        (field,) = parse_template("{{note?}}")
        assert field == TemplateField("note", required=False)

    def test_typed_optional_field(self):
        (field,) = parse_template("{{age?:number}}")
        assert field == TemplateField("age", "number", required=False)

    def test_optional_enum(self):
        (field,) = parse_template("{{country?:enum(MX,US)}}")
        assert field == TemplateField(
            "country", "enum", required=False, options=["MX", "US"]
        )

    def test_required_by_default(self):
        (field,) = parse_template("{{name}}")
        assert field.required is True

    def test_whitespace_around_optional_marker(self):
        (field,) = parse_template("{{ note ? : string }}")
        assert field.required is False

    def test_conflicting_required_and_optional_raises(self):
        with pytest.raises(ParseError):
            parse_template("{{x}} and {{x?}}")
