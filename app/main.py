"""Ponto de entrada da aplicação web (FastAPI).

Execute com ``uvicorn app.main:app --reload``.
"""

from collections.abc import Awaitable, Callable
from pathlib import Path

from fastapi import FastAPI, Request, Response
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api.routes import router as passwords_router
from app.core.constants import (
    CHARACTER_SETS,
    DEFAULT_PASSWORD_COUNT,
    DEFAULT_PASSWORD_LENGTH,
    MAX_PASSWORD_COUNT,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_COUNT,
    MIN_PASSWORD_LENGTH,
    CharacterCategory,
)

APP_DIRECTORY = Path(__file__).resolve().parent
DOCS_URL = "/docs"

# Respostas podem conter senhas: proibir cache evita que fiquem gravadas no
# disco do navegador ou em proxies intermediários.
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}
HARDENING_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "X-Frame-Options": "DENY",
    "Referrer-Policy": "no-referrer",
}
# Sem scripts/estilos inline nem origens externas: reduz o impacto de uma
# eventual injeção de HTML e impede que a página seja embutida em outro site.
CONTENT_SECURITY_POLICY = (
    "default-src 'self'; script-src 'self'; style-src 'self'; img-src 'self'; "
    "connect-src 'self'; form-action 'self'; base-uri 'none'; "
    "object-src 'none'; frame-ancestors 'none'"
)

CATEGORY_LABELS = {
    CharacterCategory.UPPERCASE: "Letras maiúsculas",
    CharacterCategory.LOWERCASE: "Letras minúsculas",
    CharacterCategory.NUMBERS: "Números",
    CharacterCategory.SYMBOLS: "Caracteres especiais",
}

templates = Jinja2Templates(directory=APP_DIRECTORY / "templates")


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI.

    Returns:
        Aplicação com rotas, arquivos estáticos e cabeçalhos de segurança.
    """
    application = FastAPI(
        title="SecurePass",
        description="API para geração de senhas criptograficamente seguras.",
        version="1.0.0",
        docs_url=DOCS_URL,
        redoc_url=None,
    )
    application.middleware("http")(add_security_headers)
    application.mount(
        "/static", StaticFiles(directory=APP_DIRECTORY / "static"), name="static"
    )
    application.include_router(passwords_router)
    application.get("/", response_class=HTMLResponse, include_in_schema=False)(
        render_index
    )
    return application


def render_index(request: Request) -> HTMLResponse:
    """Renderiza a página do gerador de senhas.

    Limites e tamanhos dos conjuntos vêm das constantes do domínio, para que o
    HTML nunca divirja das regras aplicadas pelo backend.

    Args:
        request: Requisição recebida, exigida pelo Jinja2Templates.

    Returns:
        Página HTML do gerador.
    """
    categories = [
        {
            "name": category.value,
            "label": CATEGORY_LABELS[category],
            "characters": CHARACTER_SETS[category],
        }
        for category in CharacterCategory
    ]
    context = {
        "categories": categories,
        "min_length": MIN_PASSWORD_LENGTH,
        "max_length": MAX_PASSWORD_LENGTH,
        "default_length": DEFAULT_PASSWORD_LENGTH,
        "min_count": MIN_PASSWORD_COUNT,
        "max_count": MAX_PASSWORD_COUNT,
        "default_count": DEFAULT_PASSWORD_COUNT,
    }
    return templates.TemplateResponse(request, "index.html", context)


async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Acrescenta cabeçalhos de segurança e de não cache a todas as respostas.

    A CSP não é aplicada à Swagger UI, que depende de scripts inline e de CDN.

    Args:
        request: Requisição recebida.
        call_next: Próximo manipulador da cadeia de middlewares.

    Returns:
        Resposta original com os cabeçalhos de segurança aplicados.
    """
    response = await call_next(request)
    response.headers.update(NO_CACHE_HEADERS)
    response.headers.update(HARDENING_HEADERS)
    if not request.url.path.startswith(DOCS_URL):
        response.headers["Content-Security-Policy"] = CONTENT_SECURITY_POLICY
    return response


app = create_app()
