"""Integration test that compiles a real PDF with Tectonic.

Skipped automatically when Tectonic is not installed (for example in CI without
the engine), so the unit suite stays self-contained while this still exercises
the real toolchain on a developer machine.
"""

import shutil

import pytest

from latexgen.core.compiler import TectonicCompiler

pytestmark = pytest.mark.skipif(
    shutil.which("tectonic") is None,
    reason="Tectonic is not installed in this environment.",
)


def test_compiles_minimal_document_to_pdf():
    source = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Hello, world.\n"
        "\\end{document}\n"
    )
    result = TectonicCompiler(timeout=120).compile(source)
    assert result.ok is True
    assert result.pdf is not None
    assert result.pdf[:5] == b"%PDF-"


def test_reports_failure_on_broken_document():
    source = "\\documentclass{article}\\begin{document}\\undefinedcmd"
    result = TectonicCompiler(timeout=120).compile(source)
    assert result.ok is False
    assert result.errors