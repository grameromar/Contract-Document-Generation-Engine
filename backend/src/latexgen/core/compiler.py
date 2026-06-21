"""Compile a rendered LaTeX source into a PDF.

The compiler is the third stage of the pipeline (parser -> renderer ->
compiler). The :class:`Compiler` interface lets the engine be swapped (Strategy
pattern); :class:`TectonicCompiler` drives the Tectonic engine, which bundles
its own TeX distribution, fetches packages on demand, and disables shell-escape
by default -- a safer choice for compiling untrusted templates.

Compilation runs in an isolated temporary directory and is bounded by a timeout.
A LaTeX error is reported as a :class:`CompileResult` with ``ok=False`` rather
than raised, because a broken document is an expected outcome; only an
environment problem (the engine missing) raises.
"""

from __future__ import annotations

import subprocess
import tempfile
from abc import ABC, abstractmethod
from pathlib import Path

from .exceptions import CompilerNotFoundError
from .models import CompileResult

# Stem of the source and output files written inside the build directory.
_DOCUMENT_STEM = "document"


class Compiler(ABC):
    """Interface for engines that turn LaTeX source into a PDF."""

    @abstractmethod
    def compile(self, tex_source: str) -> CompileResult:
        """Compile ``tex_source`` and return the outcome.

        Args:
            tex_source: A complete LaTeX document.

        Returns:
            A :class:`CompileResult` carrying the PDF on success, or the error
            details on failure.
        """
        raise NotImplementedError


class TectonicCompiler(Compiler):
    """Compile LaTeX with the Tectonic engine via its command-line interface."""

    def __init__(
        self,
        tectonic_path: str = "tectonic",
        timeout: float = 30.0,
    ) -> None:
        """Initialise the compiler.

        Args:
            tectonic_path: The Tectonic executable name or path.
            timeout: Maximum seconds to allow a single compilation to run.
        """
        self.tectonic_path = tectonic_path
        self.timeout = timeout

    def compile(self, tex_source: str) -> CompileResult:
        """Compile ``tex_source`` to a PDF in an isolated temporary directory.

        Args:
            tex_source: A complete LaTeX document.

        Returns:
            A :class:`CompileResult` with ``ok=True`` and the PDF bytes on
            success, or ``ok=False`` with extracted error lines on a LaTeX
            failure or a timeout.

        Raises:
            CompilerNotFoundError: If the Tectonic executable cannot be found.
        """
        with tempfile.TemporaryDirectory() as build_dir:
            directory = Path(build_dir)
            tex_path = directory / f"{_DOCUMENT_STEM}.tex"
            tex_path.write_text(tex_source, encoding="utf-8")

            try:
                completed = subprocess.run(
                    [
                        self.tectonic_path,
                        "--outdir", str(directory),
                        str(tex_path),
                    ],
                    capture_output=True,
                    text=True,
                    timeout=self.timeout,
                )
            except FileNotFoundError as exc:
                raise CompilerNotFoundError(
                    f"Tectonic executable not found: '{self.tectonic_path}'. "
                    "Install Tectonic or pass its path to TectonicCompiler."
                ) from exc
            except subprocess.TimeoutExpired:
                return CompileResult(
                    ok=False,
                    errors=[f"Compilation timed out after {self.timeout:g}s."],
                )

            if completed.returncode != 0:
                return CompileResult(
                    ok=False,
                    log=completed.stderr,
                    errors=self._extract_errors(completed.stderr),
                )

            pdf_path = directory / f"{_DOCUMENT_STEM}.pdf"
            return CompileResult(
                ok=True,
                pdf=pdf_path.read_bytes(),
                log=completed.stderr,
            )

    @staticmethod
    def _extract_errors(output: str) -> list[str]:
        """Pull human-readable error lines out of the compiler output.

        Tectonic prefixes its own messages with ``error:`` and surfaces LaTeX
        errors with a leading ``!``. Lines matching either are collected; if
        none match, a single generic message is returned so the result is never
        empty.

        Args:
            output: The compiler's combined log output.

        Returns:
            A non-empty list of error lines.
        """
        errors = [
            line.strip()
            for line in output.splitlines()
            if line.strip().startswith("error:") or line.strip().startswith("!")
        ]
        return errors or ["LaTeX compilation failed."]