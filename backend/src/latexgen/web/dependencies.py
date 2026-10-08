"""FastAPI dependency that provides the core :class:`TemplateService`.

The service is created once and reused across requests. Its compiler is built
from the application settings (Tectonic path and timeout), so the engine can be
configured per environment without editing code. It is exposed as a dependency
(rather than a module global) so tests can override it via
``app.dependency_overrides``.
"""

from __future__ import annotations

from functools import lru_cache

from latexgen.core.compiler import TectonicCompiler
from latexgen.core.service import TemplateService

from .config import load_settings


@lru_cache
def get_service() -> TemplateService:
    """Return the shared :class:`TemplateService` instance.

    The first call reads the settings and builds a
    :class:`~latexgen.core.compiler.TectonicCompiler` from ``tectonic_path``
    and ``compile_timeout``; later calls return the same cached service.

    Returns:
        The service used by every request.
    """
    settings = load_settings()
    compiler = TectonicCompiler(
        tectonic_path=settings.tectonic_path,
        timeout=settings.compile_timeout,
    )
    return TemplateService(compiler=compiler)
