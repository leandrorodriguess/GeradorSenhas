"""Contrato de entrada e saída do endpoint de geração de senhas.

Os limites declarados aqui vêm de ``app.core.constants``; a validação
estrutural (tipos e faixas) fica com o Pydantic, enquanto regras que envolvem
mais de um campo permanecem no núcleo de domínio.
"""

from pydantic import BaseModel, ConfigDict, Field

from app.core.constants import (
    DEFAULT_PASSWORD_COUNT,
    DEFAULT_PASSWORD_LENGTH,
    MAX_PASSWORD_COUNT,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_COUNT,
    MIN_PASSWORD_LENGTH,
)

# Exemplos com asteriscos: a documentação interativa nunca deve exibir algo que
# pareça uma senha real que alguém possa copiar e reutilizar.
MASKED_PASSWORD_EXAMPLE = "*" * DEFAULT_PASSWORD_LENGTH


class PasswordGenerationRequest(BaseModel):
    """Parâmetros enviados pelo cliente para gerar senhas.

    Todos os campos são opcionais e possuem valores padrão. O modo estrito
    impede conversões implícitas (por exemplo, ``"16"`` ou ``16.0`` para
    ``16``) e campos desconhecidos são rejeitados.

    Attributes:
        length: Comprimento de cada senha.
        uppercase: Incluir letras maiúsculas (A-Z).
        lowercase: Incluir letras minúsculas (a-z).
        numbers: Incluir dígitos (0-9).
        symbols: Incluir caracteres especiais.
        count: Quantidade de senhas a gerar.
    """

    model_config = ConfigDict(
        strict=True,
        extra="forbid",
        json_schema_extra={
            "examples": [
                {
                    "length": DEFAULT_PASSWORD_LENGTH,
                    "uppercase": True,
                    "lowercase": True,
                    "numbers": True,
                    "symbols": True,
                    "count": DEFAULT_PASSWORD_COUNT,
                }
            ]
        },
    )

    length: int = Field(
        default=DEFAULT_PASSWORD_LENGTH,
        ge=MIN_PASSWORD_LENGTH,
        le=MAX_PASSWORD_LENGTH,
        description="Comprimento de cada senha.",
    )
    uppercase: bool = Field(default=True, description="Incluir letras A-Z.")
    lowercase: bool = Field(default=True, description="Incluir letras a-z.")
    numbers: bool = Field(default=True, description="Incluir dígitos 0-9.")
    symbols: bool = Field(default=True, description="Incluir caracteres especiais.")
    count: int = Field(
        default=DEFAULT_PASSWORD_COUNT,
        ge=MIN_PASSWORD_COUNT,
        le=MAX_PASSWORD_COUNT,
        description="Quantidade de senhas a gerar.",
    )


class PasswordGenerationResponse(BaseModel):
    """Senhas geradas e os parâmetros efetivamente aplicados.

    Attributes:
        passwords: Senhas geradas, na ordem de criação.
        length: Comprimento de cada senha.
        count: Quantidade de senhas retornadas.
    """

    model_config = ConfigDict(
        json_schema_extra={
            "examples": [
                {
                    "passwords": [MASKED_PASSWORD_EXAMPLE],
                    "length": DEFAULT_PASSWORD_LENGTH,
                    "count": DEFAULT_PASSWORD_COUNT,
                }
            ]
        }
    )

    passwords: list[str] = Field(description="Senhas geradas.")
    length: int = Field(description="Comprimento de cada senha.")
    count: int = Field(description="Quantidade de senhas retornadas.")


class ErrorResponse(BaseModel):
    """Corpo de erro para violações das regras de negócio.

    Attributes:
        detail: Mensagem legível descrevendo o problema.
    """

    detail: str
