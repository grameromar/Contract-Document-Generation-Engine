"""FastAPI dependency that provides the core :class:`TemplateService`.

The service is created once and reused across requests. It is exposed as a
dependency (rather than a module global) so tests can override it via
``app.dependency_overrides`` and so configuration (e.g. the Tectonic path) can
be wired in here later.
"""

from __future__ import annotations

from functools import lru_cache

from latexgen.core.service import TemplateService

@lru_cache
def get_service() -> TemplateService:
    """Return the shared :class:`TemplateService` instance."""
    return TemplateService()