"""Integration tests across pipeline stages.

Unlike the unit tests, which cover each core module in isolation, these exercise
more than one module working together.
"""

import pytest

from latexgen.core.parser import parse_template
from latexgen.core.renderer import Renderer


@pytest.fixture
def renderer():
    return Renderer()


class TestParseThenRender:
    """A template is parsed and then rendered end to end."""

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

    def test_optional_field_omitted(self, renderer):
        template = "Nombre: {{nombre}}{{nota?}}"
        fields = parse_template(template)
        out = renderer.render(template, fields, {"nombre": "Ana"})
        assert out == "Nombre: Ana"