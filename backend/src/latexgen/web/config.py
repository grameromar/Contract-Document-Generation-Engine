"""Application settings loaded from a YAML configuration file.

Configuration that is not code -- the allowed CORS origins today, other
deployment knobs later -- lives in ``config/settings.yaml`` rather than being
hard-coded in Python, so it can change per environment without editing source.
PyYAML reads the file into a plain dict; a Pydantic model then validates its
shape, so a malformed config fails fast at startup with a clear error.
"""

from __future__ import annotations

import os
from pathlib import Path

import yaml
from pydantic import BaseModel

# Default location: backend/config/settings.yaml, resolved relative to this
# file. From web/config.py the parents are: [0]=web [1]=latexgen [2]=src
# [3]=backend.
_DEFAULT_CONFIG_PATH = (
    Path(__file__).resolve().parents[3] / "config" / "settings.yaml"
)


class Settings(BaseModel):
    """Validated application configuration."""

    cors_origins: list[str]


def load_settings(path: Path | None = None) -> Settings:
    """Load and validate settings from a YAML file.

    Args:
        path: Explicit config path. When omitted, the ``LATEXGEN_CONFIG``
            environment variable is used, falling back to the default
            ``config/settings.yaml``.

    Returns:
        The validated :class:`Settings`.
    """
    config_path = path or Path(
        os.environ.get("LATEXGEN_CONFIG", _DEFAULT_CONFIG_PATH)
    )
    with config_path.open(encoding="utf-8") as handle:
        data = yaml.safe_load(handle) or {}
    return Settings(**data)