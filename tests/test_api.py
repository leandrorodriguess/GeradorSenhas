"""Testes da API REST e das páginas servidas pelo FastAPI."""

import pytest
from fastapi.testclient import TestClient

from app.core.constants import (
    DEFAULT_PASSWORD_COUNT,
    DEFAULT_PASSWORD_LENGTH,
    LOWERCASE_CHARACTERS,
    MAX_PASSWORD_COUNT,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    NUMBER_CHARACTERS,
    SYMBOL_CHARACTERS,
    UPPERCASE_CHARACTERS,
)
from app.main import app

GENERATE_URL = "/api/v1/passwords/generate"

VALID_PAYLOAD = {
    "length": 16,
    "uppercase": True,
    "lowercase": True,
    "numbers": True,
    "symbols": True,
    "count": 1,
}


@pytest.fixture
def client() -> TestClient:
    return TestClient(app)


def payload_with(**overrides: object) -> dict[str, object]:
    return {**VALID_PAYLOAD, **overrides}


# --- Contrato de sucesso ---------------------------------------------------


def test_generate_returns_contract_fields(client):
    response = client.post(GENERATE_URL, json=VALID_PAYLOAD)

    assert response.status_code == 200
    body = response.json()
    assert set(body) == {"passwords", "length", "count"}
    assert body["length"] == 16
    assert body["count"] == 1
    assert len(body["passwords"]) == 1
    assert len(body["passwords"][0]) == 16


def test_generate_uses_defaults_for_omitted_fields(client):
    response = client.post(GENERATE_URL, json={})

    assert response.status_code == 200
    body = response.json()
    assert body["length"] == DEFAULT_PASSWORD_LENGTH
    assert body["count"] == DEFAULT_PASSWORD_COUNT
    assert len(body["passwords"]) == DEFAULT_PASSWORD_COUNT


def test_generate_multiple_passwords(client):
    response = client.post(
        GENERATE_URL,
        json=payload_with(count=MAX_PASSWORD_COUNT, length=MAX_PASSWORD_LENGTH),
    )

    assert response.status_code == 200
    passwords = response.json()["passwords"]
    assert len(passwords) == MAX_PASSWORD_COUNT
    assert all(len(password) == MAX_PASSWORD_LENGTH for password in passwords)


def test_generate_respects_selected_categories(client):
    response = client.post(
        GENERATE_URL,
        json=payload_with(uppercase=False, symbols=False, length=MIN_PASSWORD_LENGTH),
    )

    password = response.json()["passwords"][0]
    allowed = set(LOWERCASE_CHARACTERS + NUMBER_CHARACTERS)
    assert set(password) <= allowed
    assert not set(password) & set(UPPERCASE_CHARACTERS + SYMBOL_CHARACTERS)


# --- Validação de entrada --------------------------------------------------


@pytest.mark.parametrize(
    "overrides",
    [
        {"length": MIN_PASSWORD_LENGTH - 1},
        {"length": MAX_PASSWORD_LENGTH + 1},
        {"length": 16.5},
        {"length": "16"},
        {"length": None},
        {"count": 0},
        {"count": MAX_PASSWORD_COUNT + 1},
        {"count": "2"},
        {"uppercase": "yes"},
        {"unexpected_field": True},
    ],
    ids=[
        "comprimento-curto",
        "comprimento-longo",
        "comprimento-decimal",
        "comprimento-texto",
        "comprimento-nulo",
        "quantidade-zero",
        "quantidade-excessiva",
        "quantidade-texto",
        "booleano-invalido",
        "campo-desconhecido",
    ],
)
def test_generate_rejects_invalid_payload(client, overrides):
    response = client.post(GENERATE_URL, json=payload_with(**overrides))

    assert response.status_code == 422


def test_generate_rejects_when_no_category_selected(client):
    response = client.post(
        GENERATE_URL,
        json=payload_with(
            uppercase=False, lowercase=False, numbers=False, symbols=False
        ),
    )

    assert response.status_code == 422
    assert "categoria" in response.json()["detail"]


def test_generate_rejects_get_method(client):
    response = client.get(GENERATE_URL)

    assert response.status_code == 405


# --- Segurança ----------------------------------------------------------------


def test_api_response_disables_cache(client):
    response = client.post(GENERATE_URL, json=VALID_PAYLOAD)

    assert "no-store" in response.headers["cache-control"]
    assert response.headers["pragma"] == "no-cache"


def test_api_response_has_hardening_headers(client):
    response = client.post(GENERATE_URL, json=VALID_PAYLOAD)

    assert response.headers["x-content-type-options"] == "nosniff"
    assert response.headers["referrer-policy"] == "no-referrer"


def test_error_response_also_disables_cache(client):
    response = client.post(GENERATE_URL, json=payload_with(length=1))

    assert response.status_code == 422
    assert "no-store" in response.headers["cache-control"]


def test_openapi_documents_endpoint_without_real_passwords(client):
    schema = client.get("/openapi.json").json()

    assert GENERATE_URL in schema["paths"]
    response_schema = schema["components"]["schemas"]["PasswordGenerationResponse"]
    example_passwords = response_schema["examples"][0]["passwords"]
    assert all(set(password) == {"*"} for password in example_passwords)
