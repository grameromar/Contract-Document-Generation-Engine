"""Integration tests for the end-to-end template generation pipeline.

This module orchestrates integration tests verifying that the template parser 
and LaTeX renderer stages collaborate correctly. It guarantees that fields 
extracted by the parser correctly guide the formatting, escaping, and 
validation constraints implemented during the rendering pipeline.

Tested behaviors include:
    - Happy-path type coercion and automated escaping (string, number, date, boolean, enum).
    - Validation integrity (missing required inputs, invalid values).
    - Edge cases like optional field evaluation (`?`), repeated markers, and code injection.
"""

import pytest

from latexgen.core.exceptions import InvalidFieldValueError, MissingFieldsError
from latexgen.core.parser import parse_template
from latexgen.core.renderer import Renderer


@pytest.fixture
def renderer():
    return Renderer()


class TestParseThenRender:
    """Happy-path templates parsed and rendered end to end."""

    def test_contract_template(self, renderer):
        template = (
            r"Contrato entre {{arrendador}} y {{arrendatario}} "
            r"el {{fecha:date}} por {{monto:number}} pesos."
        )
        fields = parse_template(template)
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

    def test_all_field_types_together(self, renderer):
        template = (
            r"{{name}} | {{age:number}} | {{start?:date(%d/%m/%Y)}} | "
            r"{{active:boolean}} | {{role:enum(Admin,User)}}"
        )
        fields = parse_template(template)
        values = {
            "name": "R&D Team",
            "age": "1500",
            "start": "2026-01-05",
            "active": "true",
            "role": "Admin",
        }
        out = renderer.render(template, fields, values)
        assert out == r"R\&D Team | 1,500 | 05/01/2026 | Sí | Admin"

    def test_repeated_field_substituted_everywhere(self, renderer):
        template = "{{name}} ... {{name}} ... {{name}}"
        fields = parse_template(template)
        assert len(fields) == 1  # the parser collapses repeats into one field
        out = renderer.render(template, fields, {"name": "Ada"})
        assert out == "Ada ... Ada ... Ada"

    def test_preserves_surrounding_latex(self, renderer):
        template = (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Pago de \\${{monto:number}} por {{concepto}}.\n"
            "\\end{document}"
        )
        fields = parse_template(template)
        values = {"monto": "15000", "concepto": "renta & servicios"}
        out = renderer.render(template, fields, values)
        assert out == (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "Pago de \\$15,000 por renta \\& servicios.\n"
            "\\end{document}"
        )

    def test_optional_field_filled(self, renderer):
        template = "Nota: {{nota?}}"
        fields = parse_template(template)
        out = renderer.render(template, fields, {"nota": "urgente & breve"})
        assert out == r"Nota: urgente \& breve"

    def test_optional_field_omitted(self, renderer):
        template = "Nombre: {{nombre}}{{nota?}}"
        fields = parse_template(template)
        out = renderer.render(template, fields, {"nombre": "Ana"})
        assert out == "Nombre: Ana"

    def test_command_injection_is_neutralised(self, renderer):
        template = "Field: {{payload}}"
        fields = parse_template(template)
        out = renderer.render(
            template, fields, {"payload": r"\input{/etc/passwd}"}
        )
        assert out == r"Field: \textbackslash{}input\{/etc/passwd\}"


class TestValidationAcrossStages:
    """Errors raised by the renderer over fields produced by the parser."""

    def test_missing_required_field(self, renderer):
        template = "{{a}} {{b}} {{c}}"
        fields = parse_template(template)
        with pytest.raises(MissingFieldsError) as exc:
            renderer.render(template, fields, {"a": "x", "c": "z"})
        assert exc.value.missing_fields == ["b"]

    def test_invalid_number_value(self, renderer):
        template = "Total: {{amount:number}}"
        fields = parse_template(template)
        with pytest.raises(InvalidFieldValueError) as exc:
            renderer.render(template, fields, {"amount": "abc"})
        assert exc.value.field_name == "amount"

    def test_invalid_enum_value(self, renderer):
        # Options flow from the parser (parsed out of the marker) into the
        # renderer, which validates against them.
        template = "Role: {{role:enum(Admin,User)}}"
        fields = parse_template(template)
        with pytest.raises(InvalidFieldValueError) as exc:
            renderer.render(template, fields, {"role": "Root"})
        assert exc.value.field_name == "role"