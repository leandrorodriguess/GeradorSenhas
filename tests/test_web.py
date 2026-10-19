"""Testes da página web e dos arquivos estáticos."""

import pytest
from fastapi.testclient import TestClient

from app.core.constants import (
    CHARACTER_SETS,
    DEFAULT_PASSWORD_LENGTH,
    MAX_PASSWORD_COUNT,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_COUNT,
    MIN_PASSWORD_LENGTH,
)
from app.main import app


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def test_index_page_is_served(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]
    assert "Gerar senhas" in response.text


def test_index_page_has_security_headers(client):
    headers = client.get("/").headers

    assert "no-store" in headers["cache-control"]
    assert headers["x-content-type-options"] == "nosniff"
    assert headers["x-frame-options"] == "DENY"
    assert headers["referrer-policy"] == "no-referrer"
    assert "default-src 'self'" in headers["content-security-policy"]
    assert "frame-ancestors 'none'" in headers["content-security-policy"]


def test_swagger_docs_are_not_blocked_by_page_csp(client):
    # A Swagger UI carrega recursos de CDN e scripts inline; a CSP estrita da
    # página a quebraria, por isso é aplicada somente fora da documentação.
    response = client.get("/docs")

    assert response.status_code == 200
    assert "content-security-policy" not in response.headers


def test_index_page_renders_limits_from_constants(client):
    html = client.get("/").text

    assert f'min="{MIN_PASSWORD_LENGTH}"' in html
    assert f'max="{MAX_PASSWORD_LENGTH}"' in html
    assert f'value="{DEFAULT_PASSWORD_LENGTH}"' in html
    assert f'min="{MIN_PASSWORD_COUNT}"' in html
    assert f'max="{MAX_PASSWORD_COUNT}"' in html


def test_index_page_exposes_pool_sizes_for_entropy_indicator(client):
    html = client.get("/").text

    for category, characters in CHARACTER_SETS.items():
        assert f'name="{category}"' in html
        assert f'data-pool-size="{len(characters)}"' in html


def test_index_page_escapes_symbol_characters(client):
    # "&" faz parte dos símbolos; deve chegar ao HTML escapado pelo Jinja2.
    html = client.get("/").text

    assert "&amp;" in html


@pytest.mark.parametrize(
    "path, content_type",
    [("/static/css/style.css", "text/css"), ("/static/js/script.js", "javascript")],
)
def test_static_assets_are_served(client, path, content_type):
    response = client.get(path)

    assert response.status_code == 200
    assert content_type in response.headers["content-type"]


def test_unknown_route_returns_404(client):
    assert client.get("/inexistente").status_code == 404
