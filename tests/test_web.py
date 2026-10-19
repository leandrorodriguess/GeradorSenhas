"""Testes da página web e dos arquivos estáticos."""

import pytest
from fastapi.testclient import TestClient

from app.core.constants import (
    AMBIGUOUS_CHARACTERS,
    CHARACTER_SETS,
    DEFAULT_PASSWORD_LENGTH,
    MAX_PASSWORD_COUNT,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_COUNT,
    MIN_PASSWORD_LENGTH,
)
from app.main import PRESETS, app


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


def test_index_page_shows_akcit_logo_from_own_origin(client):
    # A CSP só permite imagens de 'self'; o logo precisa ser servido localmente.
    html = client.get("/").text

    assert 'src="http://testserver/static/img/logo-akcit-branca.png"' in html
    assert 'alt="AKCIT' in html


def test_index_page_has_skip_link_to_main_content(client):
    html = client.get("/").text

    assert 'class="skip-link" href="#main"' in html
    assert 'id="main"' in html


def test_index_page_has_inline_error_slots_linked_to_fields(client):
    # Erros junto ao campo e associados via aria-describedby são lidos por
    # leitores de tela quando o campo recebe o foco.
    html = client.get("/").text

    assert 'aria-describedby="length-hint length-error"' in html
    assert 'aria-describedby="count-hint count-error"' in html
    assert 'aria-describedby="categories-error"' in html
    for error_id in ("length-error", "count-error", "categories-error"):
        assert f'id="{error_id}"' in html


def test_index_page_has_status_region_and_helper_actions(client):
    html = client.get("/").text

    assert 'role="status"' in html
    assert 'id="reset-button"' in html
    assert 'id="copy-all-button"' in html


def test_index_page_credits_the_author(client):
    html = client.get("/").text

    assert "Desenvolvido por: <strong>Leandro Rodrigues da Silva Souza</strong>" in html
    assert '<meta name="author" content="Leandro Rodrigues da Silva Souza">' in html


def test_index_page_declares_akcit_favicon(client):
    html = client.get("/").text

    assert 'rel="icon" href="http://testserver/static/img/favicon.ico"' in html


@pytest.mark.parametrize(
    "path, content_type",
    [
        ("/static/css/style.css", "text/css"),
        ("/static/js/script.js", "javascript"),
        ("/static/img/logo-akcit-branca.png", "image/png"),
        ("/static/img/logo-akcit.png", "image/png"),
        ("/static/img/favicon.ico", "image/"),
    ],
)
def test_static_assets_are_served(client, path, content_type):
    response = client.get(path)

    assert response.status_code == 200
    assert content_type in response.headers["content-type"]


def test_unknown_route_returns_404(client):
    assert client.get("/inexistente").status_code == 404


def test_index_page_offers_ambiguous_exclusion_with_pool_sizes(client):
    # O indicador de entropia precisa do tamanho dos conjuntos com e sem os
    # caracteres ambíguos, sem que o JavaScript redefina os caracteres.
    html = client.get("/").text

    assert 'name="exclude_ambiguous"' in html
    for characters in CHARACTER_SETS.values():
        without_ambiguous = [c for c in characters if c not in AMBIGUOUS_CHARACTERS]
        assert f'data-pool-size-unambiguous="{len(without_ambiguous)}"' in html


def test_index_page_has_quick_profiles(client):
    html = client.get("/").text

    assert html.count('class="preset') >= 3
    assert "data-preset-length=" in html


@pytest.mark.parametrize(
    "element_id",
    ["visibility-button", "clear-button", "theme-button", "entropy-tip"],
)
def test_index_page_has_presentation_controls(client, element_id):
    assert f'id="{element_id}"' in client.get("/").text


@pytest.mark.parametrize("preset", PRESETS, ids=lambda preset: preset["label"])
def test_presets_respect_domain_limits(preset):
    assert MIN_PASSWORD_LENGTH <= preset["length"] <= MAX_PASSWORD_LENGTH
    assert preset["categories"]
    assert preset["length"] >= len(preset["categories"])
