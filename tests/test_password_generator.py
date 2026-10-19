"""Testes unitários do núcleo de geração de senhas."""

import pytest

from app.core import password_generator
from app.core.constants import (
    AMBIGUOUS_CHARACTERS,
    CHARACTER_SETS,
    LOWERCASE_CHARACTERS,
    MAX_PASSWORD_COUNT,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_COUNT,
    MIN_PASSWORD_LENGTH,
    NUMBER_CHARACTERS,
    SYMBOL_CHARACTERS,
    UPPERCASE_CHARACTERS,
    CharacterCategory,
)
from app.core.password_generator import (
    PasswordGenerationError,
    generate_password,
    generate_passwords,
    secure_shuffle,
    select_character_sets,
)

SINGLE_CATEGORY_CASES = [
    pytest.param(UPPERCASE_CHARACTERS, id="apenas-maiusculas"),
    pytest.param(LOWERCASE_CHARACTERS, id="apenas-minusculas"),
    pytest.param(NUMBER_CHARACTERS, id="apenas-numeros"),
    pytest.param(SYMBOL_CHARACTERS, id="apenas-simbolos"),
]


def contains_any(text: str, characters: str) -> bool:
    return any(char in characters for char in text)


# --- Comprimento -----------------------------------------------------------


@pytest.mark.parametrize("length", [MIN_PASSWORD_LENGTH, MAX_PASSWORD_LENGTH])
def test_generates_password_with_boundary_lengths(length, all_character_sets):
    password = generate_password(length, all_character_sets)

    assert len(password) == length


@pytest.mark.parametrize(
    "length",
    [MIN_PASSWORD_LENGTH - 1, MAX_PASSWORD_LENGTH + 1, 0, -1],
    ids=["abaixo-do-minimo", "acima-do-maximo", "zero", "negativo"],
)
def test_rejects_length_out_of_range(length, all_character_sets):
    with pytest.raises(PasswordGenerationError, match="comprimento"):
        generate_password(length, all_character_sets)


@pytest.mark.parametrize(
    "length",
    [16.0, 16.5, "16", None, True],
    ids=["float", "decimal", "str", "none", "bool"],
)
def test_rejects_non_integer_length(length, all_character_sets):
    with pytest.raises(TypeError, match="inteiro"):
        generate_password(length, all_character_sets)


# --- Categorias ------------------------------------------------------------


def test_rejects_empty_character_sets():
    with pytest.raises(PasswordGenerationError, match="categoria"):
        generate_password(MIN_PASSWORD_LENGTH, [])


def test_rejects_blank_character_set():
    with pytest.raises(PasswordGenerationError, match="vazio"):
        generate_password(MIN_PASSWORD_LENGTH, [UPPERCASE_CHARACTERS, ""])


def test_rejects_length_smaller_than_number_of_categories():
    many_sets = list("ABCDEFGHIJ")  # 10 categorias de 1 caractere cada

    with pytest.raises(PasswordGenerationError, match="categorias"):
        generate_password(MIN_PASSWORD_LENGTH, many_sets)


@pytest.mark.parametrize("allowed", SINGLE_CATEGORY_CASES)
def test_single_category_uses_only_its_characters(allowed):
    password = generate_password(MAX_PASSWORD_LENGTH, [allowed])

    assert set(password) <= set(allowed)


def test_all_categories_are_present_when_all_selected(all_character_sets):
    # Repetir com o comprimento mínimo maximiza a chance de detectar falha na
    # garantia de presença, já que sobram poucas posições aleatórias.
    for _ in range(200):
        password = generate_password(MIN_PASSWORD_LENGTH, all_character_sets)

        for character_set in all_character_sets:
            assert contains_any(password, character_set)


@pytest.mark.parametrize(
    "selected, excluded",
    [
        (
            [UPPERCASE_CHARACTERS, NUMBER_CHARACTERS, SYMBOL_CHARACTERS],
            [LOWERCASE_CHARACTERS],
        ),
        (
            [LOWERCASE_CHARACTERS, NUMBER_CHARACTERS],
            [UPPERCASE_CHARACTERS, SYMBOL_CHARACTERS],
        ),
        (
            [UPPERCASE_CHARACTERS, SYMBOL_CHARACTERS],
            [LOWERCASE_CHARACTERS, NUMBER_CHARACTERS],
        ),
    ],
    ids=["sem-minusculas", "sem-maiusculas-e-simbolos", "sem-minusculas-e-numeros"],
)
def test_respects_selected_and_excluded_categories(selected, excluded):
    for _ in range(100):
        password = generate_password(MIN_PASSWORD_LENGTH, selected)

        for character_set in selected:
            assert contains_any(password, character_set)
        for character_set in excluded:
            assert not contains_any(password, character_set)


# --- Seleção de categorias -------------------------------------------------


def test_select_character_sets_returns_only_flagged_categories():
    selected = select_character_sets(
        uppercase=True, lowercase=False, numbers=True, symbols=False
    )

    assert selected == [UPPERCASE_CHARACTERS, NUMBER_CHARACTERS]


def test_select_character_sets_with_nothing_flagged_returns_empty_list():
    selected = select_character_sets(
        uppercase=False, lowercase=False, numbers=False, symbols=False
    )

    assert selected == []


def test_character_sets_cover_every_category():
    assert set(CHARACTER_SETS) == set(CharacterCategory)


# --- Múltiplas senhas ------------------------------------------------------


@pytest.mark.parametrize("count", [MIN_PASSWORD_COUNT, 5, MAX_PASSWORD_COUNT])
def test_generates_requested_number_of_passwords(count, all_character_sets):
    passwords = generate_passwords(MIN_PASSWORD_LENGTH, all_character_sets, count)

    assert len(passwords) == count
    assert all(len(password) == MIN_PASSWORD_LENGTH for password in passwords)


@pytest.mark.parametrize("count", [MIN_PASSWORD_COUNT - 1, MAX_PASSWORD_COUNT + 1, -3])
def test_rejects_invalid_password_count(count, all_character_sets):
    with pytest.raises(PasswordGenerationError, match="quantidade"):
        generate_passwords(MIN_PASSWORD_LENGTH, all_character_sets, count)


@pytest.mark.parametrize("count", [1.0, "2", None, False])
def test_rejects_non_integer_password_count(count, all_character_sets):
    with pytest.raises(TypeError, match="inteiro"):
        generate_passwords(MIN_PASSWORD_LENGTH, all_character_sets, count)


# --- Aleatoriedade criptograficamente segura -------------------------------


def test_secure_shuffle_implements_fisher_yates_with_randbelow(monkeypatch):
    calls: list[int] = []

    def fake_randbelow(upper_bound: int) -> int:
        calls.append(upper_bound)
        return 0

    monkeypatch.setattr(password_generator.secrets, "randbelow", fake_randbelow)
    items = ["a", "b", "c"]

    secure_shuffle(items)

    # Com randbelow sempre 0: [a,b,c] -> troca(2,0) -> [c,b,a] -> troca(1,0) -> [b,c,a]
    assert items == ["b", "c", "a"]
    assert calls == [3, 2]


def test_secure_shuffle_keeps_the_same_elements():
    items = list("abcdefghij")

    secure_shuffle(items)

    assert sorted(items) == list("abcdefghij")


def test_generation_uses_secrets_choice_and_randbelow(monkeypatch):
    choice_calls: list[str] = []
    randbelow_calls: list[int] = []

    def fake_choice(sequence: str) -> str:
        choice_calls.append(sequence)
        return sequence[0]

    def fake_randbelow(upper_bound: int) -> int:
        randbelow_calls.append(upper_bound)
        return upper_bound - 1  # mantém cada elemento na posição: troca(i, i)

    monkeypatch.setattr(password_generator.secrets, "choice", fake_choice)
    monkeypatch.setattr(password_generator.secrets, "randbelow", fake_randbelow)

    password = generate_password(
        MIN_PASSWORD_LENGTH, [UPPERCASE_CHARACTERS, NUMBER_CHARACTERS]
    )

    # Resultado determinístico: um caractere obrigatório de cada categoria,
    # seguido do preenchimento a partir do conjunto combinado.
    assert password == "A0AAAAAA"
    assert len(choice_calls) == MIN_PASSWORD_LENGTH
    assert choice_calls[:2] == [UPPERCASE_CHARACTERS, NUMBER_CHARACTERS]
    assert randbelow_calls == list(range(MIN_PASSWORD_LENGTH, 1, -1))


def test_module_does_not_use_insecure_random():
    assert not hasattr(password_generator, "random")


# --- Caracteres ambíguos -----------------------------------------------------


def test_ambiguous_characters_are_the_visually_confusable_ones():
    assert set(AMBIGUOUS_CHARACTERS) == set("0O1lI")


def test_select_character_sets_keeps_ambiguous_characters_by_default():
    sets = select_character_sets(
        uppercase=True, lowercase=True, numbers=True, symbols=True
    )

    assert sets == list(CHARACTER_SETS.values())


def test_select_character_sets_can_exclude_ambiguous_characters():
    sets = select_character_sets(
        uppercase=True,
        lowercase=True,
        numbers=True,
        symbols=True,
        exclude_ambiguous=True,
    )

    assert len(sets) == len(CharacterCategory)
    assert not any(contains_any(chars, AMBIGUOUS_CHARACTERS) for chars in sets)
    assert sets[0] == UPPERCASE_CHARACTERS.replace("O", "").replace("I", "")
    assert sets[1] == LOWERCASE_CHARACTERS.replace("l", "")
    assert sets[2] == "23456789"
    assert sets[3] == SYMBOL_CHARACTERS


@pytest.mark.parametrize("_", range(20))
def test_passwords_without_ambiguous_characters_never_contain_them(_):
    sets = select_character_sets(
        uppercase=True,
        lowercase=True,
        numbers=True,
        symbols=False,
        exclude_ambiguous=True,
    )

    password = generate_password(MAX_PASSWORD_LENGTH, sets)

    assert not contains_any(password, AMBIGUOUS_CHARACTERS)
