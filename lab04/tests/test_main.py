import importlib

import pytest

from lab04 import __main__ as principal

MODULOS = ["coleta", "descritiva", "calibracao", "gerador", "testes", "simulacao", "graficos", "dashboard"]


@pytest.mark.parametrize("modulo", MODULOS)
def test_modulos_previstos_sao_importaveis(modulo):
    assert importlib.import_module(f"lab04.{modulo}").__doc__


def test_help_sai_com_zero(capsys):
    with pytest.raises(SystemExit) as saida:
        principal.main(["--help"])
    assert saida.value.code == 0
    assert "usage" in capsys.readouterr().out


@pytest.mark.parametrize("etapa", [[], ["coletar"], ["simular"], ["dashboard"]])
def test_etapas_pendentes_avisam_e_saem_com_um(etapa, capsys):
    assert principal.main(etapa) == 1
    assert "ainda não implementada" in capsys.readouterr().err
