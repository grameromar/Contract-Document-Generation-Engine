"""End-to-end tests of the full pipeline through :class:`TemplateService`.

These compile real PDFs with Tectonic, so the whole module is skipped when the
engine is not installed. The first run is slow because Tectonic downloads its
package bundle; later runs use the cache.
"""

import shutil

import pytest

from latexgen.core.exceptions import CompileError
from latexgen.core.service import TemplateService

pytestmark = pytest.mark.skipif(
    shutil.which("tectonic") is None,
    reason="Tectonic is not installed in this environment.",
)


@pytest.fixture
def service():
    return TemplateService()


def _is_pdf(data: bytes) -> bool:
    """A produced PDF starts with the %PDF- signature and is non-trivial."""
    return data[:5] == b"%PDF-" and len(data) > 1000


class TestRealCompilation:
    """Realistic documents exercising every field type and feature."""

    def test_lease_contract_all_types(self, service):
        template = (
            "\\documentclass{article}\n"
            "\\begin{document}\n"
            "\\section*{Lease Agreement}\n"
            "Between {{lessor}} and {{lessee}}, effective "
            "{{start:date(%d/%m/%Y)}}, for \\${{amount:number}}.\n\n"
            "Active: {{active:boolean}}. "
            "Type: {{kind:enum(Residential,Commercial)}}.\n"
            "\\end{document}\n"
        )
        values = {
            "lessor": "Ana & Co.",
            "lessee": "Luis",
            "start": "2026-01-05",
            "amount": "1500000",
            "active": "true",
            "kind": "Commercial",
        }
        assert _is_pdf(service.generate(template, values))

    def test_special_characters_compile_cleanly(self, service):
        template = (
            "\\documentclass{article}\n\\begin{document}\n"
            "{{payload}}\n\\end{document}\n"
        )
        payload = r"100% of A&B costs $5, item #1, a~b, x^y, z_w, {grp}"
        assert _is_pdf(service.generate(template, {"payload": payload}))

    def test_optional_field_omitted(self, service):
        template = (
            "\\documentclass{article}\n\\begin{document}\n"
            "Name: {{name}}.{{note?}}\n\\end{document}\n"
        )
        assert _is_pdf(service.generate(template, {"name": "Ada"}))

    def test_compiles_with_on_demand_package(self, service):
        template = (
            "\\documentclass{article}\n"
            "\\usepackage[margin=3cm]{geometry}\n"
            "\\begin{document}\n"
            "{{title}}\n"
            "\\end{document}\n"
        )
        assert _is_pdf(service.generate(template, {"title": "Quarterly Report"}))

    def test_numbers_and_dates_render_in_pdf(self, service):
        template = (
            "\\documentclass{article}\n\\begin{document}\n"
            "Total: \\${{total:number}} on {{day:date(%B %d, %Y)}}.\n"
            "\\end{document}\n"
        )
        values = {"total": "1234567.89", "day": "2026-03-09"}
        assert _is_pdf(service.generate(template, values))


class TestRealCompilationErrors:
    """A broken document surfaces as a CompileError end to end."""

    def test_broken_latex_raises_compile_error(self, service):
        template = (
            "\\documentclass{article}\n\\begin{document}\n"
            "{{name}} \\undefinedcommand\n\\end{document}\n"
        )
        with pytest.raises(CompileError) as exc:
            service.generate(template, {"name": "Ada"})
        assert exc.value.errors