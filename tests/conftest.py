"""Fixtures compartilhadas entre os módulos de teste."""

import pytest

from app.core.constants import CHARACTER_SETS


@pytest.fixture
def all_character_sets() -> list[str]:
    """Retorna todos os conjuntos de caracteres configurados."""
    return list(CHARACTER_SETS.values())
