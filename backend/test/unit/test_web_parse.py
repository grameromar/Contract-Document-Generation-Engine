"""Tests for the ``POST /parse`` endpoint.

These drive the real FastAPI app through ``TestClient``; ``/parse`` does not
compile anything, so no LaTeX engine is needed.
"""

import pytest
from fastapi.testclient import TestClient

from latexgen.web.main import create_app


@pytest.fixture
def client():
    return TestClient(create_app())


class TestParseEndpoint:
    """Happy-path field discovery over HTTP."""

    def test_returns_fields_in_order(self, client):
        resp = client.post(
            "/parse", json={"template": "{{name}} {{age:number}}"}
        )
        assert resp.status_code == 200
        names = [f["name"] for f in resp.json()["fields"]]
        assert names == ["name", "age"]

    def test_includes_field_metadata(self, client):
        resp = client.post(
            "/parse",
            json={"template": "{{role:enum(Admin,User)}} {{note?:string}}"},
        )
        fields = resp.json()["fields"]
        role, note = fields[0], fields[1]
        assert role["type"] == "enum"
        assert role["options"] == ["Admin", "User"]
        assert role["required"] is True
        assert note["required"] is False

    def test_date_format_is_exposed(self, client):
        resp = client.post(
            "/parse", json={"template": "{{d:date(%d/%m/%Y)}}"}
        )
        assert resp.json()["fields"][0]["date_format"] == "%d/%m/%Y"

    def test_template_without_markers_returns_empty(self, client):
        resp = client.post("/parse", json={"template": "no markers here"})
        assert resp.json() == {"fields": []}


class TestParseEndpointErrors:
    """Validation and domain errors map to the right status codes."""

    def test_unsupported_type_returns_422(self, client):
        resp = client.post("/parse", json={"template": "{{x:color}}"})
        assert resp.status_code == 422
        assert "color" in resp.json()["detail"]

    def test_inconsistent_declaration_returns_422(self, client):
        resp = client.post(
            "/parse", json={"template": "{{x:number}} {{x:string}}"}
        )
        assert resp.status_code == 422

    def test_missing_template_field_returns_422(self, client):
        # Pydantic request validation: 'template' is required.
        resp = client.post("/parse", json={})
        assert resp.status_code == 422