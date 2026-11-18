import importlib

import pytest

from lab05 import __main__ as principal

MODULOS = ["ambiente", "executor", "leitura", "validacao", "descritiva", "testes", "poder", "graficos", "app"]


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


@pytest.mark.parametrize("falhas, interrompida, codigo", [([], False, 0), ([("x", "subida", "erro")], False, 1), ([], True, 1)])
def test_executar_repassa_as_opcoes_e_sai_conforme_o_resumo(monkeypatch, falhas, interrompida, codigo):
    recebido = {}

    def executar_falso(cfg):
        recebido.update(cfg)
        return {"falhas": falhas, "interrompida": interrompida}

    monkeypatch.setattr(principal.executor, "executar", executar_falso)
    argv = ["executar", "--repeticoes", "1", "--aquecimento", "2", "--medicao", "5", "--pausa", "1", "--saida", "dados/brutos/exemplo"]
    assert principal.main(argv) == codigo
    assert recebido["plano"]["repeticoes"] == 1 and recebido["saida"] == "dados/brutos/exemplo"
    assert (recebido["cliente"]["aquecimento_s"], recebido["cliente"]["medicao_s"], recebido["cliente"]["pausa_s"]) == (2, 5, 1)
