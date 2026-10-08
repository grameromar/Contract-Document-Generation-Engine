"""Tests for the ``POST /generate`` endpoint.

The real FastAPI app is driven through ``TestClient``, with the service
dependency overridden so it uses a fake compiler: these tests need no LaTeX
engine. The parser and renderer still run for real.
"""

import pytest
from fastapi.testclient import TestClient

from latexgen.core.compiler import Compiler
from latexgen.core.exceptions import CompilerNotFoundError
from latexgen.core.models import CompileResult
from latexgen.core.service import TemplateService
from latexgen.web.dependencies import get_service
from latexgen.web.main import create_app

FAKE_PDF = b"%PDF-fake"


class _FakeCompiler(Compiler):
    """Records the LaTeX it receives and returns a result or raises."""

    def __init__(self, result=None, exc=None):
        self.result = result or CompileResult(ok=True, pdf=FAKE_PDF)
        self.exc = exc
        self.received_source = None

    def compile(self, tex_source):
        self.received_source = tex_source
        if self.exc is not None:
            raise self.exc
        return self.result


@pytest.fixture
def make_client():
    """Build a client whose service uses the given fake compiler."""

    def _make(compiler):
        app = create_app()
        app.dependency_overrides[get_service] = lambda: TemplateService(
            compiler=compiler
        )
        return TestClient(app)

    return _make


class TestGenerateSuccess:
    """A valid request returns the PDF as a download."""

    def test_returns_pdf_bytes_as_attachment(self, make_client):
        client = make_client(_FakeCompiler())
        resp = client.post(
            "/generate", json={"template": "Hi {{name}}", "values": {"name": "Ana"}}
        )
        assert resp.status_code == 200
        assert resp.content == FAKE_PDF
        assert resp.headers["content-type"] == "application/pdf"
        assert (
            resp.headers["content-disposition"]
            == 'attachment; filename="document.pdf"'
        )

    def test_compiler_receives_escaped_source(self, make_client):
        compiler = _FakeCompiler()
        make_client(compiler).post(
            "/generate",
            json={"template": "Hi {{name}}", "values": {"name": "A & B 50%"}},
        )
        assert compiler.received_source == r"Hi A \& B 50\%"

    def test_json_numbers_booleans_and_null_are_accepted(self, make_client):
        compiler = _FakeCompiler()
        resp = make_client(compiler).post(
            "/generate",
            json={
                "template": "{{n:number}} {{b:boolean}} [{{note?}}]",
                "values": {"n": 1500, "b": True, "note": None},
            },
        )
        assert resp.status_code == 200
        assert compiler.received_source == "1,500 Sí []"

    def test_values_default_to_empty(self, make_client):
        resp = make_client(_FakeCompiler()).post(
            "/generate", json={"template": "No markers here."}
        )
        assert resp.status_code == 200


class TestGenerateErrors:
    """Domain and validation errors map to the right status and body."""

    def test_missing_fields_return_422_with_names(self, make_client):
        resp = make_client(_FakeCompiler()).post(
            "/generate", json={"template": "{{a}} {{b}} {{c?}}", "values": {}}
        )
        assert resp.status_code == 422
        assert resp.json()["missing_fields"] == ["a", "b"]

    def test_invalid_value_returns_422_with_field(self, make_client):
        resp = make_client(_FakeCompiler()).post(
            "/generate",
            json={"template": "{{n:number}}", "values": {"n": "abc"}},
        )
        assert resp.status_code == 422
        assert resp.json()["field"] == "n"

    def test_parse_error_returns_422(self, make_client):
        resp = make_client(_FakeCompiler()).post(
            "/generate", json={"template": "{{x:color}}", "values": {}}
        )
        assert resp.status_code == 422
        assert "color" in resp.json()["detail"]

    def test_compile_failure_returns_422_without_log(self, make_client):
        failed = CompileResult(
            ok=False,
            log="INTERNAL LOG LINE",
            errors=["! Undefined control sequence."],
        )
        resp = make_client(_FakeCompiler(result=failed)).post(
            "/generate", json={"template": r"\broken", "values": {}}
        )
        assert resp.status_code == 422
        assert resp.json() == {
            "detail": "LaTeX compilation failed.",
            "errors": ["! Undefined control sequence."],
        }
        assert "INTERNAL LOG LINE" not in resp.text

    def test_missing_compiler_returns_503(self, make_client):
        compiler = _FakeCompiler(exc=CompilerNotFoundError("Tectonic not found"))
        resp = make_client(compiler).post(
            "/generate", json={"template": "x", "values": {}}
        )
        assert resp.status_code == 503
        assert resp.json() == {"detail": "Tectonic not found"}

    def test_missing_template_returns_422(self, make_client):
        resp = make_client(_FakeCompiler()).post("/generate", json={"values": {}})
        assert resp.status_code == 422

    def test_unsupported_value_type_returns_422(self, make_client):
        resp = make_client(_FakeCompiler()).post(
            "/generate", json={"template": "{{a}}", "values": {"a": [1, 2]}}
        )
        assert resp.status_code == 422
