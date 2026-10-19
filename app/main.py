"""Ponto de entrada da aplicação web (FastAPI).

Execute com ``uvicorn app.main:app --reload``.
"""

from collections.abc import Awaitable, Callable

from fastapi import FastAPI, Request, Response

from app.api.routes import router as passwords_router

# Respostas podem conter senhas: proibir cache evita que fiquem gravadas no
# disco do navegador ou em proxies intermediários.
NO_CACHE_HEADERS = {
    "Cache-Control": "no-store, no-cache, must-revalidate, max-age=0",
    "Pragma": "no-cache",
    "Expires": "0",
}
HARDENING_HEADERS = {
    "X-Content-Type-Options": "nosniff",
    "Referrer-Policy": "no-referrer",
}


def create_app() -> FastAPI:
    """Cria e configura a aplicação FastAPI.

    Returns:
        Aplicação com rotas e cabeçalhos de segurança configurados.
    """
    application = FastAPI(
        title="SecurePass",
        description="API para geração de senhas criptograficamente seguras.",
        version="1.0.0",
        redoc_url=None,
    )
    application.middleware("http")(add_security_headers)
    application.include_router(passwords_router)
    return application


async def add_security_headers(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Acrescenta cabeçalhos de segurança e de não cache a todas as respostas.

    Args:
        request: Requisição recebida.
        call_next: Próximo manipulador da cadeia de middlewares.

    Returns:
        Resposta original com os cabeçalhos de segurança aplicados.
    """
    response = await call_next(request)
    response.headers.update(NO_CACHE_HEADERS)
    response.headers.update(HARDENING_HEADERS)
    return response


app = create_app()
