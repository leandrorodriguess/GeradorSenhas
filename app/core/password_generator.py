"""Geração de senhas criptograficamente seguras.

Este módulo concentra toda a regra de negócio da aplicação. API REST, CLI e
interface web delegam para as funções daqui, de modo que a lógica seja única,
reutilizável e testável sem depender de nenhuma interface.

Toda a aleatoriedade vem do módulo ``secrets``, que usa a fonte segura do
sistema operacional. O módulo ``random`` não deve ser usado: seu gerador
(Mersenne Twister) é previsível e inadequado para senhas.
"""

import secrets
from collections.abc import Sequence

from app.core.constants import (
    AMBIGUOUS_CHARACTERS,
    CHARACTER_SETS,
    MAX_PASSWORD_COUNT,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_COUNT,
    MIN_PASSWORD_LENGTH,
    CharacterCategory,
)


class PasswordGenerationError(ValueError):
    """Indica parâmetros de geração com valor inválido.

    Herda de ``ValueError`` para que chamadores possam tratá-la como um erro
    de valor comum, enquanto as interfaces distinguem erros de negócio de
    falhas inesperadas.
    """


def select_character_sets(
    *,
    uppercase: bool,
    lowercase: bool,
    numbers: bool,
    symbols: bool,
    exclude_ambiguous: bool = False,
) -> list[str]:
    """Converte as opções escolhidas pelo usuário em conjuntos de caracteres.

    Args:
        uppercase: Incluir letras maiúsculas (A-Z).
        lowercase: Incluir letras minúsculas (a-z).
        numbers: Incluir dígitos (0-9).
        symbols: Incluir caracteres especiais.
        exclude_ambiguous: Remover caracteres confundíveis
            (``AMBIGUOUS_CHARACTERS``) de todos os conjuntos.

    Returns:
        Conjuntos de caracteres das categorias marcadas, na ordem de
        ``CharacterCategory``. Lista vazia se nenhuma categoria foi marcada.
    """
    flags = {
        CharacterCategory.UPPERCASE: uppercase,
        CharacterCategory.LOWERCASE: lowercase,
        CharacterCategory.NUMBERS: numbers,
        CharacterCategory.SYMBOLS: symbols,
    }
    selected = [
        CHARACTER_SETS[category] for category in CharacterCategory if flags[category]
    ]
    if exclude_ambiguous:
        selected = [remove_ambiguous_characters(chars) for chars in selected]
    return selected


def remove_ambiguous_characters(characters: str) -> str:
    """Remove de um conjunto os caracteres visualmente confundíveis.

    Args:
        characters: Conjunto de caracteres original.

    Returns:
        O mesmo conjunto, na mesma ordem, sem ``AMBIGUOUS_CHARACTERS``.
    """
    return "".join(char for char in characters if char not in AMBIGUOUS_CHARACTERS)


def secure_shuffle(items: list[str]) -> None:
    """Embaralha a lista no próprio lugar usando Fisher-Yates.

    ``random.shuffle`` não é usado porque depende de um gerador
    pseudoaleatório previsível. Aqui cada índice é sorteado com
    ``secrets.randbelow``, que produz distribuição uniforme sem viés de módulo.

    Args:
        items: Lista a ser embaralhada; é modificada diretamente.
    """
    for index in range(len(items) - 1, 0, -1):
        swap_index = secrets.randbelow(index + 1)
        items[index], items[swap_index] = items[swap_index], items[index]


def generate_password(length: int, character_sets: Sequence[str]) -> str:
    """Gera uma senha criptograficamente segura.

    Garante a presença de pelo menos um caractere de cada conjunto informado,
    utilizando aleatoriedade segura. Os demais caracteres são sorteados do
    conjunto combinado e o resultado é embaralhado, para que os caracteres
    obrigatórios não fiquem em posições previsíveis.

    Args:
        length: Quantidade total de caracteres da senha.
        character_sets: Conjuntos de caracteres permitidos; cada um representa
            uma categoria que deve aparecer na senha.

    Returns:
        Senha gerada de acordo com os critérios informados.

    Raises:
        TypeError: Se o comprimento não for um número inteiro.
        PasswordGenerationError: Se o comprimento estiver fora dos limites, se
            nenhum conjunto for informado, se algum conjunto estiver vazio ou
            se o comprimento for menor que a quantidade de categorias.
    """
    _validate_length(length)
    _validate_character_sets(character_sets, length)

    required_characters = [secrets.choice(chars) for chars in character_sets]
    combined_pool = _combine_character_sets(character_sets)
    remaining_count = length - len(required_characters)
    random_characters = [secrets.choice(combined_pool) for _ in range(remaining_count)]

    password_characters = required_characters + random_characters
    secure_shuffle(password_characters)
    return "".join(password_characters)


def generate_passwords(
    length: int, character_sets: Sequence[str], count: int
) -> list[str]:
    """Gera várias senhas independentes com os mesmos critérios.

    Args:
        length: Quantidade de caracteres de cada senha.
        character_sets: Conjuntos de caracteres permitidos.
        count: Quantidade de senhas a gerar.

    Returns:
        Lista com ``count`` senhas.

    Raises:
        TypeError: Se o comprimento ou a quantidade não forem inteiros.
        PasswordGenerationError: Se algum parâmetro estiver fora das regras
            descritas em ``generate_password`` ou se a quantidade estiver fora
            dos limites permitidos.
    """
    _validate_count(count)
    return [generate_password(length, character_sets) for _ in range(count)]


def _require_integer(value: object, field_name: str) -> None:
    # bool é subclasse de int em Python; aceitar True como "1" mascararia erros
    # de chamada, por isso é rejeitado explicitamente.
    if isinstance(value, bool) or not isinstance(value, int):
        raise TypeError(f"O campo {field_name} deve ser um número inteiro.")


def _validate_length(length: int) -> None:
    _require_integer(length, "comprimento")
    if not MIN_PASSWORD_LENGTH <= length <= MAX_PASSWORD_LENGTH:
        raise PasswordGenerationError(
            f"O comprimento deve estar entre {MIN_PASSWORD_LENGTH} "
            f"e {MAX_PASSWORD_LENGTH} caracteres."
        )


def _validate_count(count: int) -> None:
    _require_integer(count, "quantidade")
    if not MIN_PASSWORD_COUNT <= count <= MAX_PASSWORD_COUNT:
        raise PasswordGenerationError(
            f"A quantidade de senhas deve estar entre {MIN_PASSWORD_COUNT} "
            f"e {MAX_PASSWORD_COUNT}."
        )


def _validate_character_sets(character_sets: Sequence[str], length: int) -> None:
    if not character_sets:
        raise PasswordGenerationError(
            "Selecione pelo menos uma categoria de caracteres."
        )
    if any(not chars for chars in character_sets):
        raise PasswordGenerationError("Nenhum conjunto de caracteres pode ser vazio.")
    if length < len(character_sets):
        raise PasswordGenerationError(
            "O comprimento deve ser maior ou igual à quantidade de categorias "
            "selecionadas."
        )


def _combine_character_sets(character_sets: Sequence[str]) -> str:
    # dict.fromkeys remove repetições preservando a ordem; um caractere
    # presente em dois conjuntos teria, caso contrário, probabilidade dobrada.
    return "".join(dict.fromkeys("".join(character_sets)))
