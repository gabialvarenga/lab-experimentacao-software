"""Fixtures compartilhadas: carregamento de respostas e listas escritas à mão."""

import json
from pathlib import Path

import pytest

PASTA_FIXTURES = Path(__file__).parent / "fixtures"


def carregar_fixture(nome: str):
    """Lê `tests/fixtures/<nome>.json` e devolve o conteúdo já decodificado."""
    with open(PASTA_FIXTURES / f"{nome}.json", encoding="utf-8") as arquivo:
        return json.load(arquivo)


@pytest.fixture
def fixture_json():
    return carregar_fixture
