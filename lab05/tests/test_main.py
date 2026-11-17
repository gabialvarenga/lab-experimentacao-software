import importlib

import pytest

from lab05 import __main__ as principal

MODULOS = ["ambiente", "executor", "validacao", "descritiva", "testes", "poder", "graficos", "app"]


def test_pacote_e_importavel():
    assert importlib.import_module("lab05").__doc__


@pytest.mark.parametrize("modulo", MODULOS)
def test_modulos_previstos_sao_importaveis(modulo):
    assert importlib.import_module(f"lab05.{modulo}").__doc__


def test_help_sai_com_zero(capsys):
    with pytest.raises(SystemExit) as saida:
        principal.main(["--help"])
    assert saida.value.code == 0
    assert "usage" in capsys.readouterr().out


def test_sem_subcomando_mostra_a_ajuda(capsys):
    assert principal.main([]) == 0
    assert "usage" in capsys.readouterr().out


@pytest.mark.parametrize("etapa", list(principal.PENDENTES))
def test_etapa_pendente_avisa_e_sai_com_um(etapa, capsys):
    assert principal.main([etapa]) == 1
    assert "ainda não implementada" in capsys.readouterr().err
