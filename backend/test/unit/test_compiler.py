"""Unit tests for :mod:`latexgen.core.compiler`.

These never invoke Tectonic for real: ``subprocess.run`` is replaced with a fake
that mimics each outcome (success, LaTeX failure, timeout, missing executable),
so the compiler's logic is verified without the engine or the network.
"""

import subprocess
from pathlib import Path

import pytest

from latexgen.core.compiler import TectonicCompiler
from latexgen.core.exceptions import CompilerNotFoundError


def _outdir_of(cmd: list[str]) -> Path:
    """Return the --outdir path from a faked tectonic command line."""
    return Path(cmd[cmd.index("--outdir") + 1])


class TestSuccessfulCompilation:
    """A zero exit code with a produced PDF yields ok=True."""

    def test_returns_pdf_bytes(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            (_outdir_of(cmd) / "document.pdf").write_bytes(b"%PDF-data")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = TectonicCompiler().compile(r"\documentclass{article}...")
        assert result.ok is True
        assert result.pdf == b"%PDF-data"
        assert result.errors == []

    def test_writes_source_and_invokes_tectonic(self, monkeypatch):
        captured = {}

        def fake_run(cmd, **kwargs):
            outdir = _outdir_of(cmd)
            captured["cmd"] = cmd
            captured["source"] = (outdir / "document.tex").read_text(
                encoding="utf-8"
            )
            (outdir / "document.pdf").write_bytes(b"%PDF")
            return subprocess.CompletedProcess(cmd, 0, stdout="", stderr="")

        monkeypatch.setattr(subprocess, "run", fake_run)
        TectonicCompiler(tectonic_path="tectonic").compile("HELLO BODY")
        assert captured["cmd"][0] == "tectonic"
        assert captured["source"] == "HELLO BODY"


class TestFailedCompilation:
    """LaTeX errors and timeouts are reported as ok=False, not raised."""

    def test_nonzero_exit_returns_extracted_errors(self, monkeypatch):
        stderr = (
            "error: undefined control sequence\n"
            "some unrelated noise\n"
            "! LaTeX Error: Something went wrong"
        )

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(cmd, 1, stdout="", stderr=stderr)

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = TectonicCompiler().compile("broken")
        assert result.ok is False
        assert result.pdf is None
        assert any("undefined control sequence" in e for e in result.errors)
        assert any("LaTeX Error" in e for e in result.errors)
        assert "some unrelated noise" not in " ".join(result.errors)

    def test_timeout_returns_failure(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            raise subprocess.TimeoutExpired(cmd, timeout=kwargs.get("timeout"))

        monkeypatch.setattr(subprocess, "run", fake_run)
        result = TectonicCompiler(timeout=5).compile("loop")
        assert result.ok is False
        assert any("timed out" in e.lower() for e in result.errors)


class TestEnvironment:
    """A missing executable is an environment error and raises."""

    def test_missing_executable_raises(self, monkeypatch):
        def fake_run(cmd, **kwargs):
            raise FileNotFoundError(cmd[0])

        monkeypatch.setattr(subprocess, "run", fake_run)
        with pytest.raises(CompilerNotFoundError):
            TectonicCompiler(tectonic_path="nonexistent").compile("x")