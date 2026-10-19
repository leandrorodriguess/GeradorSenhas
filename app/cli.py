"""Interface de linha de comando do SecurePass.

Exemplo:
    python -m app.cli --length 20 --uppercase --lowercase --numbers --symbols --count 3

Cada senha é impressa em uma linha da saída padrão, o que facilita redirecionar
para outros programas. Mensagens de erro vão para a saída de erro.

Códigos de saída:
    0: Senhas geradas com sucesso.
    2: Argumentos inválidos (mesma convenção do ``argparse``).
"""

import argparse
import sys
from collections.abc import Sequence

from app.core.constants import (
    AMBIGUOUS_CHARACTERS,
    DEFAULT_PASSWORD_COUNT,
    DEFAULT_PASSWORD_LENGTH,
    MAX_PASSWORD_COUNT,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_COUNT,
    MIN_PASSWORD_LENGTH,
    SYMBOL_CHARACTERS,
)
from app.core.password_generator import (
    PasswordGenerationError,
    generate_passwords,
    select_character_sets,
)

EXIT_SUCCESS = 0
EXIT_USAGE_ERROR = 2


def build_parser() -> argparse.ArgumentParser:
    """Cria o parser de argumentos da CLI.

    Returns:
        Parser configurado com todas as opções de geração.
    """
    parser = argparse.ArgumentParser(
        prog="python -m app.cli",
        description="Gera senhas aleatórias e criptograficamente seguras.",
        epilog="Selecione ao menos uma categoria de caracteres.",
    )
    parser.add_argument(
        "-l",
        "--length",
        type=int,
        default=DEFAULT_PASSWORD_LENGTH,
        help=(
            f"comprimento de cada senha ({MIN_PASSWORD_LENGTH}-"
            f"{MAX_PASSWORD_LENGTH}; padrão: {DEFAULT_PASSWORD_LENGTH})"
        ),
    )
    parser.add_argument(
        "-c",
        "--count",
        type=int,
        default=DEFAULT_PASSWORD_COUNT,
        help=(
            f"quantidade de senhas ({MIN_PASSWORD_COUNT}-{MAX_PASSWORD_COUNT}; "
            f"padrão: {DEFAULT_PASSWORD_COUNT})"
        ),
    )
    parser.add_argument(
        "-U", "--uppercase", action="store_true", help="incluir letras A-Z"
    )
    parser.add_argument(
        "-L", "--lowercase", action="store_true", help="incluir letras a-z"
    )
    parser.add_argument("-D", "--numbers", action="store_true", help="incluir 0-9")
    parser.add_argument(
        "-S",
        "--symbols",
        action="store_true",
        # O argparse aplica formatação "%" aos textos de ajuda; o "%" presente
        # nos símbolos precisa ser escapado para não quebrar o --help.
        help=f"incluir símbolos ({SYMBOL_CHARACTERS.replace('%', '%%')})",
    )
    parser.add_argument(
        "-A",
        "--exclude-ambiguous",
        action="store_true",
        help=f"remover caracteres confundíveis ({AMBIGUOUS_CHARACTERS})",
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    """Executa a CLI.

    Args:
        argv: Argumentos da linha de comando, sem o nome do programa. Quando
            ``None``, usa ``sys.argv``.

    Returns:
        Código de saída do processo.

    Raises:
        SystemExit: Lançada pelo ``argparse`` quando os argumentos estão
            malformados (por exemplo, comprimento não inteiro) ou quando
            ``--help`` é solicitado.
    """
    arguments = build_parser().parse_args(argv)
    character_sets = select_character_sets(
        uppercase=arguments.uppercase,
        lowercase=arguments.lowercase,
        numbers=arguments.numbers,
        symbols=arguments.symbols,
        exclude_ambiguous=arguments.exclude_ambiguous,
    )
    try:
        passwords = generate_passwords(
            arguments.length, character_sets, arguments.count
        )
    except PasswordGenerationError as error:
        print(f"Erro: {error}", file=sys.stderr)
        return EXIT_USAGE_ERROR

    for password in passwords:
        print(password)
    return EXIT_SUCCESS


if __name__ == "__main__":
    sys.exit(main())
