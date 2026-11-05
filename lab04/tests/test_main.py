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


def test_simular_pendente_avisa_e_sai_com_um(capsys):
    assert principal.main(["simular"]) == 1
    assert "ainda não implementada" in capsys.readouterr().err


@pytest.fixture
def painel(monkeypatch):
    """Substitui `montar` e o navegador; devolve as chamadas registradas."""
    from lab04 import dashboard

    chamadas = {"montar": [], "abrir": []}
    monkeypatch.setattr(dashboard, "montar", lambda saida, cfg: chamadas["montar"].append((saida, cfg["semente"])))
    monkeypatch.setattr(principal.webbrowser, "open", lambda uri: chamadas["abrir"].append(uri))
    return chamadas


def test_dashboard_gera_no_caminho_do_config_e_abre_no_navegador(painel, capsys):
    assert principal.main(["dashboard"]) == 0
    [(saida, semente)] = painel["montar"]
    assert saida.as_posix().endswith("lab04/dashboard/index.html") and semente == 42
    assert painel["abrir"] == [saida.resolve().as_uri()]
    assert "Dashboard gravado em" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["dashboard", "--sem-abrir"], ["--sem-abrir", "dashboard"]])
def test_dashboard_sem_abrir_nao_abre_o_navegador(argv, painel):
    assert principal.main(argv) == 0
    assert len(painel["montar"]) == 1 and painel["abrir"] == []


def test_comando_unico_avisa_simular_e_gera_o_dashboard(painel, capsys):
    assert principal.main(["--sem-abrir"]) == 0
    assert "'simular' ainda não implementada" in capsys.readouterr().err
    assert len(painel["montar"]) == 1 and painel["abrir"] == []


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


def test_calibrar_chama_a_calibracao_com_o_config(monkeypatch):
    from lab04 import calibracao

    chamadas = []
    monkeypatch.setattr(calibracao, "executar", lambda cfg: chamadas.append(cfg["calibracao"]["confianca"]))
    assert principal.main(["calibrar"]) == 0
    assert chamadas == [0.95]
