"""Rotas da API REST versionada.

As rotas apenas traduzem HTTP para chamadas ao núcleo e vice-versa; nenhuma
regra de geração é implementada aqui.
"""

from fastapi import APIRouter, HTTPException, status

from app.core.password_generator import (
    PasswordGenerationError,
    generate_passwords,
    select_character_sets,
)
from app.schemas.password import (
    ErrorResponse,
    PasswordGenerationRequest,
    PasswordGenerationResponse,
)

router = APIRouter(prefix="/api/v1/passwords", tags=["passwords"])


@router.post(
    "/generate",
    response_model=PasswordGenerationResponse,
    summary="Gera senhas criptograficamente seguras",
    responses={
        status.HTTP_422_UNPROCESSABLE_CONTENT: {
            "description": (
                "Parâmetros inválidos: tipo incorreto, valor fora dos limites, "
                "campo desconhecido ou nenhuma categoria selecionada."
            ),
            "model": ErrorResponse,
        }
    },
)
def generate(request: PasswordGenerationRequest) -> PasswordGenerationResponse:
    """Gera uma ou mais senhas conforme os critérios informados.

    Cada senha contém ao menos um caractere de cada categoria marcada e
    nenhum caractere de categorias desmarcadas. As senhas não são registradas
    em log nem armazenadas.

    Args:
        request: Critérios de geração já validados pelo Pydantic.

    Returns:
        Senhas geradas com o comprimento e a quantidade aplicados.

    Raises:
        HTTPException: 422 quando o núcleo rejeita a combinação de
            parâmetros (por exemplo, nenhuma categoria selecionada).
    """
    character_sets = select_character_sets(
        uppercase=request.uppercase,
        lowercase=request.lowercase,
        numbers=request.numbers,
        symbols=request.symbols,
        exclude_ambiguous=request.exclude_ambiguous,
    )
    try:
        passwords = generate_passwords(request.length, character_sets, request.count)
    except PasswordGenerationError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_CONTENT, detail=str(error)
        ) from error

    return PasswordGenerationResponse(
        passwords=passwords, length=request.length, count=len(passwords)
    )
