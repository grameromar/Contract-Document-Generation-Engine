"""Unit tests for :mod:`latexgen.core.renderer`."""

import pytest

from latexgen.core.exceptions import InvalidFieldValueError, MissingFieldsError
from latexgen.core.models import TemplateField
from latexgen.core.renderer import Renderer


@pytest.fixture
def renderer():
    return Renderer()


class TestBasicSubstitution:
    """Marker substitution and escaping for plain fields."""

    def test_replaces_a_single_marker(self, renderer):
        fields = [TemplateField("name")]
        out = renderer.render("Hello {{name}}!", fields, {"name": "Ada"})
        assert out == "Hello Ada!"

    def test_replaces_repeated_markers(self, renderer):
        fields = [TemplateField("who")]
        out = renderer.render("{{who}} and {{who}}", fields, {"who": "X"})
        assert out == "X and X"

    def test_replaces_typed_marker(self, renderer):
        fields = [TemplateField("amount", "number")]
        out = renderer.render(
            "Total: {{amount:number}}", fields, {"amount": "1500"}
        )
        assert out == "Total: 1,500"

    def test_escapes_special_characters(self, renderer):
        fields = [TemplateField("company")]
        out = renderer.render("{{company}}", fields, {"company": "Juan & Co."})
        assert out == r"Juan \& Co."


class TestTypedFields:
    """Each field type is escaped through its own strategy."""

    def test_date_uses_field_format(self, renderer):
        fields = [TemplateField("d", "date", date_format="%d/%m/%Y")]
        out = renderer.render("{{d:date}}", fields, {"d": "2026-06-20"})
        assert out == "20/06/2026"

    def test_enum_is_validated(self, renderer):
        fields = [TemplateField("c", "enum", options=["A", "B"])]
        out = renderer.render("{{c:enum(A,B)}}", fields, {"c": "A"})
        assert out == "A"

    def test_boolean_is_mapped(self, renderer):
        fields = [TemplateField("ok", "boolean")]
        out = renderer.render("{{ok:boolean}}", fields, {"ok": "true"})
        assert out == "Sí"


class TestValidation:
    """Required-field validation and value-level errors."""

    def test_missing_required_field_raises(self, renderer):
        fields = [TemplateField("a"), TemplateField("b")]
        with pytest.raises(MissingFieldsError) as exc:
            renderer.render("{{a}} {{b}}", fields, {"a": "x"})
        assert exc.value.missing_fields == ["b"]

    def test_whitespace_only_counts_as_missing(self, renderer):
        fields = [TemplateField("a")]
        with pytest.raises(MissingFieldsError):
            renderer.render("{{a}}", fields, {"a": "   "})

    def test_optional_unfilled_renders_empty(self, renderer):
        fields = [TemplateField("note", required=False)]
        out = renderer.render("[{{note}}]", fields, {})
        assert out == "[]"

    def test_invalid_value_raises_with_field_name(self, renderer):
        fields = [TemplateField("n", "number")]
        with pytest.raises(InvalidFieldValueError) as exc:
            renderer.render("{{n:number}}", fields, {"n": "abc"})
        assert exc.value.field_name == "n"


class TestContractExample:
    """The lease-contract example from the project brief, end to end."""

    def test_full_contract_template(self, renderer):
        template = (
            r"Contrato entre {{arrendador}} y {{arrendatario}} "
            r"el {{fecha:date}} por {{monto:number}} pesos."
        )
        fields = [
            TemplateField("arrendador"),
            TemplateField("arrendatario"),
            TemplateField("fecha", "date"),
            TemplateField("monto", "number"),
        ]
        values = {
            "arrendador": "Ana & Co.",
            "arrendatario": "Luis",
            "fecha": "2026-06-20",
            "monto": "15000",
        }
        out = renderer.render(template, fields, values)
        assert out == (
            r"Contrato entre Ana \& Co. y Luis "
            r"el 2026-06-20 por 15,000 pesos."
        )