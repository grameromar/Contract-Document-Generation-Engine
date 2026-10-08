"""End-to-end test of ``POST /generate`` with the real Tectonic engine.

The app is used exactly as configured (service built from the settings), so
this checks the whole path: HTTP, parsing, rendering, compiling and the PDF
response. Skipped automatically when Tectonic is not on the PATH.
"""

import shutil

import pytest
from fastapi.testclient import TestClient

from latexgen.web.main import create_app

pytestmark = pytest.mark.skipif(
    shutil.which("tectonic") is None,
    reason="Tectonic is not installed in this environment.",
)


def test_generate_returns_a_real_pdf():
    template = (
        "\\documentclass{article}\n"
        "\\begin{document}\n"
        "Contract with {{client}} for \\${{amount:number}}"
        " starting {{start:date(%d/%m/%Y)}}.\n"
        "\\end{document}\n"
    )
    values = {"client": "Smith & Sons", "amount": "1500000", "start": "2026-10-07"}

    resp = TestClient(create_app()).post(
        "/generate", json={"template": template, "values": values}
    )

    assert resp.status_code == 200
    assert resp.headers["content-type"] == "application/pdf"
    assert resp.content.startswith(b"%PDF")


def test_broken_latex_returns_422_with_errors():
    template = "\\documentclass{article}\n\\begin{document}\n\\undefinedcommand\n\\end{document}\n"

    resp = TestClient(create_app()).post("/generate", json={"template": template})

    assert resp.status_code == 422
    body = resp.json()
    assert body["detail"] == "LaTeX compilation failed."
    assert body["errors"]
