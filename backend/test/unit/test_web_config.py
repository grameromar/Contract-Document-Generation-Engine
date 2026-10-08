"""Tests for the web settings and the service dependency built from them."""

from pathlib import Path

import pytest
from pydantic import ValidationError

from latexgen.web.config import load_settings
from latexgen.web.dependencies import get_service


def _write_config(tmp_path: Path, content: str) -> Path:
    path = tmp_path / "settings.yaml"
    path.write_text(content, encoding="utf-8")
    return path


class TestLoadSettings:
    """YAML is read and validated, with defaults for the engine settings."""

    def test_engine_settings_default_when_absent(self, tmp_path):
        path = _write_config(tmp_path, "cors_origins: []\n")
        settings = load_settings(path)
        assert settings.tectonic_path == "tectonic"
        assert settings.compile_timeout == 30.0

    def test_engine_settings_are_read(self, tmp_path):
        path = _write_config(
            tmp_path,
            "cors_origins: []\n"
            "tectonic_path: 'C:/Tools/tectonic.exe'\n"
            "compile_timeout: 5\n",
        )
        settings = load_settings(path)
        assert settings.tectonic_path == "C:/Tools/tectonic.exe"
        assert settings.compile_timeout == 5.0

    def test_non_positive_timeout_is_rejected(self, tmp_path):
        path = _write_config(tmp_path, "cors_origins: []\ncompile_timeout: 0\n")
        with pytest.raises(ValidationError):
            load_settings(path)

    def test_environment_variable_selects_the_file(self, tmp_path, monkeypatch):
        path = _write_config(
            tmp_path, "cors_origins: []\ntectonic_path: from-env\n"
        )
        monkeypatch.setenv("LATEXGEN_CONFIG", str(path))
        assert load_settings().tectonic_path == "from-env"


class TestGetService:
    """The shared service's compiler is configured from the settings."""

    @pytest.fixture(autouse=True)
    def _fresh_cache(self):
        get_service.cache_clear()
        yield
        get_service.cache_clear()

    def test_compiler_uses_configured_path_and_timeout(self, tmp_path, monkeypatch):
        path = _write_config(
            tmp_path,
            "cors_origins: []\ntectonic_path: my-tectonic\ncompile_timeout: 12.5\n",
        )
        monkeypatch.setenv("LATEXGEN_CONFIG", str(path))
        service = get_service()
        assert service.compiler.tectonic_path == "my-tectonic"
        assert service.compiler.timeout == 12.5

    def test_service_is_shared_between_calls(self):
        assert get_service() is get_service()
