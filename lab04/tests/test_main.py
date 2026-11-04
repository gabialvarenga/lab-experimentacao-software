import importlib

import pytest

from lab04 import __main__ as principal
from lab04 import coleta

MODULOS = ["coleta", "descritiva", "calibracao", "gerador", "testes", "simulacao", "graficos", "dashboard"]


@pytest.mark.parametrize("modulo", MODULOS)
def test_modulos_previstos_sao_importaveis(modulo):
    assert importlib.import_module(f"lab04.{modulo}").__doc__


def test_help_sai_com_zero(capsys):
    with pytest.raises(SystemExit) as saida:
        principal.main(["--help"])
    assert saida.value.code == 0
    assert "usage" in capsys.readouterr().out


@pytest.mark.parametrize("etapa", [[], ["simular"], ["dashboard"]])
def test_etapas_pendentes_avisam_e_saem_com_um(etapa, capsys):
    assert principal.main(etapa) == 1
    assert "ainda não implementada" in capsys.readouterr().err


def test_coletar_chama_a_coleta_com_o_token(monkeypatch):
    chamadas = []
    monkeypatch.setenv("GITHUB_TOKEN", "abc")
    monkeypatch.setattr(coleta, "executar", lambda cfg, token: chamadas.append((cfg["semente"], token)))
    assert principal.main(["coletar"]) == 0
    assert chamadas == [(42, "abc")]


def test_coletar_sem_token_falha_com_mensagem(monkeypatch):
    monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        principal.main(["coletar"])
