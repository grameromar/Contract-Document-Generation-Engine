"""Orchestrate the full template-to-PDF pipeline.

:class:`TemplateService` ties the three core stages together (parser ->
renderer -> compiler) behind a small surface that both delivery layers (web API,
desktop) call. The compiler is injected so the service can be unit-tested
without the real LaTeX engine, and so the engine can be swapped or configured
(for example, its path) by the composition layer.
"""

from __future__ import annotations

from .compiler import Compiler, TectonicCompiler
from .exceptions import CompileError
from .models import TemplateField
from .parser import parse_template
from .renderer import Renderer


class TemplateService:
    """Parse, render and compile templates behind a single entry point."""

    def __init__(self, compiler: Compiler | None = None) -> None:
        """Initialise the service.

        Args:
            compiler: The compiler to use. Defaults to a
                :class:`~latexgen.core.compiler.TectonicCompiler`; inject a
                different one to swap engines or for testing.
        """
        self.renderer = Renderer()
        self.compiler = compiler or TectonicCompiler()

    def parse(self, template: str) -> list[TemplateField]:
        """Discover the dynamic fields declared in ``template``.

        Used by the UI to build the input form before any values exist.

        Args:
            template: The raw ``.tex`` template text.

        Returns:
            The fields declared in the template, in source order.

        Raises:
            ParseError: If the template declares fields inconsistently or with
                an unsupported type.
        """
        return parse_template(template)

    def generate(self, template: str, values: dict[str, object]) -> bytes:
        """Render ``template`` with ``values`` and compile it to a PDF.

        The template is re-parsed here rather than trusting caller-supplied
        field metadata: the template is the single source of truth.

        Args:
            template: The raw ``.tex`` template text.
            values: A mapping from field name to the raw user-supplied value.

        Returns:
            The compiled PDF as bytes.

        Raises:
            ParseError: If the template cannot be parsed.
            MissingFieldsError: If a required field has no value.
            InvalidFieldValueError: If a value fails its type's validation.
            CompileError: If the rendered LaTeX fails to compile.
            CompilerNotFoundError: If the compiler executable is unavailable.
        """
        fields = self.parse(template)
        tex_source = self.renderer.render(template, fields, values)
        result = self.compiler.compile(tex_source)
        if not result.ok:
            raise CompileError(result.errors, result.log)
        return result.pdf