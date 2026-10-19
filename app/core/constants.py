"""Constantes de configuração do gerador de senhas.

Este módulo é a única fonte de verdade para limites e conjuntos de caracteres.
API, CLI e interface web leem estes valores, evitando números mágicos e
definições duplicadas.
"""

import string
from enum import StrEnum
from types import MappingProxyType
from typing import Final


class CharacterCategory(StrEnum):
    """Categorias de caracteres que o usuário pode incluir na senha."""

    UPPERCASE = "uppercase"
    LOWERCASE = "lowercase"
    NUMBERS = "numbers"
    SYMBOLS = "symbols"


MIN_PASSWORD_LENGTH: Final = 8
MAX_PASSWORD_LENGTH: Final = 128
DEFAULT_PASSWORD_LENGTH: Final = 16

MIN_PASSWORD_COUNT: Final = 1
MAX_PASSWORD_COUNT: Final = 10
DEFAULT_PASSWORD_COUNT: Final = 1

UPPERCASE_CHARACTERS: Final = string.ascii_uppercase
LOWERCASE_CHARACTERS: Final = string.ascii_lowercase
NUMBER_CHARACTERS: Final = string.digits
SYMBOL_CHARACTERS: Final = "!@#$%&*()-_=+"

# Caracteres facilmente confundidos ao ler ou digitar a senha (0/O, 1/l/I).
# Removê-los reduz um pouco a entropia, mas evita erros de transcrição.
AMBIGUOUS_CHARACTERS: Final = "0O1lI"

# MappingProxyType torna o mapeamento somente leitura, evitando estado global
# mutável que poderia alterar silenciosamente os conjuntos de caracteres.
CHARACTER_SETS: Final = MappingProxyType(
    {
        CharacterCategory.UPPERCASE: UPPERCASE_CHARACTERS,
        CharacterCategory.LOWERCASE: LOWERCASE_CHARACTERS,
        CharacterCategory.NUMBERS: NUMBER_CHARACTERS,
        CharacterCategory.SYMBOLS: SYMBOL_CHARACTERS,
    }
)
