"""Testes da interface de linha de comando."""

import subprocess
import sys

import pytest

from app import cli
from app.core.constants import (
    DEFAULT_PASSWORD_LENGTH,
    MAX_PASSWORD_LENGTH,
    MIN_PASSWORD_LENGTH,
    NUMBER_CHARACTERS,
)

ALL_CATEGORIES = ["--uppercase", "--lowercase", "--numbers", "--symbols"]


def test_cli_generates_requested_passwords(capsys):
    exit_code = cli.main(["--length", "20", *ALL_CATEGORIES, "--count", "3"])

    output_lines = capsys.readouterr().out.splitlines()
    assert exit_code == cli.EXIT_SUCCESS
    assert len(output_lines) == 3
    assert all(len(line) == 20 for line in output_lines)


def test_cli_uses_default_length_and_count(capsys):
    exit_code = cli.main(["--numbers"])

    output_lines = capsys.readouterr().out.splitlines()
    assert exit_code == cli.EXIT_SUCCESS
    assert len(output_lines) == 1
    assert len(output_lines[0]) == DEFAULT_PASSWORD_LENGTH
    assert set(output_lines[0]) <= set(NUMBER_CHARACTERS)


def test_cli_accepts_short_flags(capsys):
    exit_code = cli.main(["-l", str(MIN_PASSWORD_LENGTH), "-U", "-D", "-c", "2"])

    assert exit_code == cli.EXIT_SUCCESS
    assert len(capsys.readouterr().out.splitlines()) == 2


@pytest.mark.parametrize(
    "arguments, expected_message",
    [
        ([*ALL_CATEGORIES, "--length", str(MIN_PASSWORD_LENGTH - 1)], "comprimento"),
        ([*ALL_CATEGORIES, "--length", str(MAX_PASSWORD_LENGTH + 1)], "comprimento"),
        ([*ALL_CATEGORIES, "--count", "0"], "quantidade"),
        ([*ALL_CATEGORIES, "--count", "11"], "quantidade"),
        (["--length", "16"], "categoria"),
    ],
    ids=["curto", "longo", "quantidade-zero", "quantidade-excessiva", "sem-categoria"],
)
def test_cli_reports_business_errors(capsys, arguments, expected_message):
    exit_code = cli.main(arguments)

    captured = capsys.readouterr()
    assert exit_code == cli.EXIT_USAGE_ERROR
    assert captured.out == ""
    assert expected_message in captured.err


@pytest.mark.parametrize(
    "arguments",
    [["--length", "abc", "--numbers"], ["--length", "16.5"], ["--unknown"]],
    ids=["comprimento-texto", "comprimento-decimal", "opcao-desconhecida"],
)
def test_cli_rejects_malformed_arguments(capsys, arguments):
    with pytest.raises(SystemExit) as exit_info:
        cli.main(arguments)

    assert exit_info.value.code == cli.EXIT_USAGE_ERROR
    assert "error" in capsys.readouterr().err.lower()


def test_cli_runs_as_module():
    completed = subprocess.run(
        [sys.executable, "-m", "app.cli", "--length", "12", "--lowercase"],
        capture_output=True,
        text=True,
        check=False,
    )

    assert completed.returncode == cli.EXIT_SUCCESS
    assert len(completed.stdout.strip()) == 12
