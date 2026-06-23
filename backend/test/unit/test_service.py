"""Unit tests for :mod:`latexgen.core.service`.

The service is exercised with stub compilers so no LaTeX engine is needed; the
parser and renderer run for real, which is what makes these tests verify the
orchestration (parse -> render -> compile) rather than mocks talking to mocks.
"""

import pytest

from latexgen.core.compiler import Compiler, TectonicCompiler
from latexgen.core.exceptions import (
    CompileError,
    CompilerNotFoundError,
    InvalidFieldValueError,
    MissingFieldsError,
    ParseError,
)
from latexgen.core.models import CompileResult
from latexgen.core.service import TemplateService


class _RecordingCompiler(Compiler):
    """A compiler stub that records its input and returns a fixed result."""

    def __init__(self, result: CompileResult) -> None:
        self.result = result
        self.received_source: str | None = None

    def compile(self, tex_source: str) -> CompileResult:
        self.received_source = tex_source
        return self.result


class _RaisingCompiler(Compiler):
    """A compiler stub that raises, to test exception propagation."""

    def __init__(self, exc: Exception) -> None:
        self.exc = exc

    def compile(self, tex_source: str) -> CompileResult:
        raise self.exc


@pytest.fixture
def pdf_compiler():
    return _RecordingCompiler(CompileResult(ok=True, pdf=b"%PDF-ok"))


class TestParse:
    """parse() exposes the parser and propagates its errors."""

    def test_returns_fields(self):
        fields = TemplateService().parse("{{name}} {{age:number}}")
        assert [f.name for f in fields] == ["name", "age"]

    def test_template_without_markers_returns_no_fields(self):
        assert TemplateService().parse("plain text, no markers") == []

    def test_propagates_parse_error(self):
        with pytest.raises(ParseError):
            TemplateService().parse("{{x:color}}")


class TestGenerateHappyPath:
    """generate() runs the full pipeline on valid input."""

    def test_returns_compiled_pdf(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        assert service.generate("Hello {{name}}", {"name": "Ada"}) == b"%PDF-ok"

    def test_compiler_receives_rendered_source(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        service.generate("Hi {{name}}", {"name": "A & B"})
        assert pdf_compiler.received_source == r"Hi A \& B"

    def test_template_without_fields_compiles_unchanged(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        service.generate("No markers here.", {})
        assert pdf_compiler.received_source == "No markers here."

    def test_extra_values_are_ignored(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        service.generate("{{name}}", {"name": "Ada", "unused": "X"})
        assert pdf_compiler.received_source == "Ada"

    def test_repeated_field_substituted_everywhere(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        service.generate("{{x}}-{{x}}-{{x}}", {"x": "ok"})
        assert pdf_compiler.received_source == "ok-ok-ok"

    def test_optional_field_omitted(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        service.generate("A{{note?}}B", {})
        assert pdf_compiler.received_source == "AB"

    def test_optional_field_present(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        service.generate("A{{note?}}B", {"note": "X & Y"})
        assert pdf_compiler.received_source == r"AX \& YB"

    def test_does_not_mutate_inputs(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        template = "{{name}}"
        values = {"name": "Ada"}
        service.generate(template, values)
        assert template == "{{name}}"
        assert values == {"name": "Ada"}


class TestGenerateValidation:
    """Validation failures stop the pipeline before compilation."""

    def test_reports_all_missing_fields_in_order(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        with pytest.raises(MissingFieldsError) as exc:
            service.generate("{{a}} {{b}} {{c}}", {"b": "x"})
        assert exc.value.missing_fields == ["a", "c"]
        assert pdf_compiler.received_source is None

    def test_invalid_number_raises(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        with pytest.raises(InvalidFieldValueError) as exc:
            service.generate("{{n:number}}", {"n": "abc"})
        assert exc.value.field_name == "n"
        assert pdf_compiler.received_source is None

    def test_invalid_enum_raises(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        with pytest.raises(InvalidFieldValueError) as exc:
            service.generate("{{role:enum(Admin,User)}}", {"role": "Root"})
        assert exc.value.field_name == "role"

    def test_impossible_date_raises(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        with pytest.raises(InvalidFieldValueError) as exc:
            service.generate("{{d:date}}", {"d": "2026-02-31"})
        assert exc.value.field_name == "d"

    def test_parse_error_stops_before_compiling(self, pdf_compiler):
        service = TemplateService(compiler=pdf_compiler)
        with pytest.raises(ParseError):
            service.generate("{{x:color}}", {"x": "1"})
        assert pdf_compiler.received_source is None


class TestGenerateCompilation:
    """Outcomes returned by the compiler are surfaced correctly."""

    def test_compilation_failure_raises_compile_error(self):
        compiler = _RecordingCompiler(
            CompileResult(ok=False, errors=["! LaTeX Error: x"], log="full log")
        )
        service = TemplateService(compiler=compiler)
        with pytest.raises(CompileError) as exc:
            service.generate("{{name}}", {"name": "Ada"})
        assert exc.value.errors == ["! LaTeX Error: x"]
        assert exc.value.log == "full log"

    def test_timeout_failure_becomes_compile_error(self):
        compiler = _RecordingCompiler(
            CompileResult(ok=False, errors=["Compilation timed out after 30s."])
        )
        service = TemplateService(compiler=compiler)
        with pytest.raises(CompileError) as exc:
            service.generate("{{name}}", {"name": "Ada"})
        assert "timed out" in exc.value.errors[0].lower()

    def test_compiler_not_found_propagates(self):
        # An environment error from the compiler is not wrapped as CompileError.
        compiler = _RaisingCompiler(CompilerNotFoundError("missing"))
        service = TemplateService(compiler=compiler)
        with pytest.raises(CompilerNotFoundError):
            service.generate("{{name}}", {"name": "Ada"})


class TestConstruction:
    """Default wiring of the service."""

    def test_default_compiler_is_tectonic(self):
        assert isinstance(TemplateService().compiler, TectonicCompiler)