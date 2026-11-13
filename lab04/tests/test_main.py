import importlib
import shutil
from pathlib import Path

import pytest

from lab04 import __main__ as principal
from lab04 import coleta, config

MODULOS = ["coleta", "descritiva", "calibracao", "gerador", "testes", "simulacao", "graficos", "dashboard", "interativo"]


@pytest.mark.parametrize("modulo", MODULOS)
def test_modulos_previstos_sao_importaveis(modulo):
    assert importlib.import_module(f"lab04.{modulo}").__doc__


def test_help_sai_com_zero(capsys):
    with pytest.raises(SystemExit) as saida:
        principal.main(["--help"])
    assert saida.value.code == 0
    assert "usage" in capsys.readouterr().out


@pytest.fixture
def etapas(monkeypatch):
    """Substitui as linhas de comando da simulação e da consolidação; devolve a ordem das chamadas."""
    from lab04 import resultados, simulacao

    chamadas = []
    monkeypatch.setattr(simulacao, "main", lambda argv: chamadas.append(("simulacao", argv)) or 0)
    monkeypatch.setattr(resultados, "main", lambda argv: chamadas.append(("resultados", argv)) or 0)
    return chamadas


def test_simular_roda_as_tres_simulacoes_finais_e_depois_consolida(etapas):
    assert principal.main(["simular"]) == 0
    padrao = str(config.CONFIG_PADRAO)
    assert etapas == [
        ("simulacao", ["--config", padrao, "--cenarios", "C0", "C1", "--saida", "dados/simulacao/c0_c1.csv"]),
        ("simulacao", ["--config", padrao, "--cenarios", "C2", "C3", "--saida", "dados/simulacao/c2_c3.csv"]),
        ("simulacao", ["--config", padrao, "--cenarios", "C4", "--saida", "dados/simulacao/c4.csv"]),
        ("resultados", ["--config", padrao]),
    ]


def test_simulacoes_finais_cobrem_todos_os_cenarios_do_config_uma_vez():
    ids = [c["id"] for c in config.simulacao(config.carregar())["cenarios"]]
    assert [i for cenarios, _ in principal.SIMULACOES_FINAIS for i in cenarios] == ids


@pytest.mark.parametrize("cenarios, saida", principal.SIMULACOES_FINAIS)
def test_cada_simulacao_final_e_o_comando_gravado_no_seu_registro(cenarios, saida):
    csv = config.CONFIG_PADRAO.parent / saida
    registro = (csv.parent / f"registro-{csv.stem}.md").read_text(encoding="utf-8")
    assert f"`python -m lab04.simulacao --cenarios {' '.join(cenarios)} --saida {saida}`" in registro


def _bytes_lf(caminho) -> bytes:
    return Path(caminho).read_bytes().replace(b"\r\n", b"\n")


def test_simular_reproduz_os_csvs_versionados_byte_a_byte(tmp_path):
    """De ponta a ponta, numa cópia do config: as 3 simulações (10.000 repetições) e a consolidação."""
    copia = tmp_path / "config.yaml"
    shutil.copyfile(config.CONFIG_PADRAO, copia)
    assert principal.main(["--config", str(copia), "simular"]) == 0
    versionados = config.CONFIG_PADRAO.parent / "dados" / "simulacao"
    gerados = tmp_path / "dados" / "simulacao"
    nomes = [Path(saida).name for _, saida in principal.SIMULACOES_FINAIS]
    for nome in [*nomes, "resultados.csv", "classificacao.csv", "poder.csv", "resumo-resultados.md"]:
        assert _bytes_lf(gerados / nome) == _bytes_lf(versionados / nome), nome


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


def test_comando_unico_simula_consolida_e_depois_gera_o_dashboard(etapas, painel, monkeypatch):
    from lab04 import dashboard

    # registra o dashboard na mesma lista, para conferir a ordem: simulações, consolidação, página
    monkeypatch.setattr(dashboard, "montar", lambda saida, cfg: etapas.append(("dashboard", saida.name)))
    assert principal.main(["--sem-abrir"]) == 0
    assert [nome for nome, _ in etapas] == ["simulacao"] * 3 + ["resultados", "dashboard"]
    assert painel["abrir"] == []


def test_comando_unico_nao_gera_o_dashboard_se_a_simulacao_falha(etapas, painel, monkeypatch):
    from lab04 import simulacao

    def falha(argv):
        raise ValueError("cenários ['C9'] não estão no config")

    monkeypatch.setattr(simulacao, "main", falha)
    with pytest.raises(ValueError, match="C9"):
        principal.main(["--sem-abrir"])
    assert painel["montar"] == []


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


class _TimerFalso:
    """Registra o navegador que seria aberto, sem esperar nem abrir nada."""

    def __init__(self, registro, espera, funcao, args):
        self.registro, self.espera, self.funcao, self.args = registro, espera, funcao, args

    def start(self):
        self.registro.append((self.espera, self.funcao, self.args))


@pytest.fixture
def servidor(monkeypatch):
    """Substitui o `subprocess.call` que sobe o Streamlit e o timer do navegador; devolve as chamadas."""
    chamadas = {"servidor": [], "navegador": []}
    monkeypatch.setattr(principal.subprocess, "call",
                        lambda comando, cwd: chamadas["servidor"].append((comando, cwd)) or 0)
    monkeypatch.setattr(principal.threading, "Timer",
                        lambda espera, funcao, args: _TimerFalso(chamadas["navegador"], espera, funcao, args))
    return chamadas


def test_app_sobe_o_streamlit_headless_e_abre_o_navegador(servidor, capsys):
    assert principal.main(["app"]) == 0
    [(comando, cwd)] = servidor["servidor"]
    assert comando[1:4] == ["-m", "streamlit", "run"]
    assert comando[4] == str(principal.APP) and principal.APP.is_file()
    assert comando[5:] == ["--server.port", "8501", "--server.headless", "true"]   # headless: sem o prompt de e-mail
    assert cwd == principal.APP.parent
    assert servidor["navegador"] == [(principal.ESPERA_NAVEGADOR_S, principal.webbrowser.open, ("http://localhost:8501",))]
    assert "localhost:8501" in capsys.readouterr().out


@pytest.mark.parametrize("argv", [["app", "--sem-abrir", "--porta", "9000"], ["--sem-abrir", "app", "--porta", "9000"]])
def test_app_sem_abrir_roda_sem_navegador_na_porta_pedida(servidor, argv):
    assert principal.main(argv) == 0
    [(comando, _)] = servidor["servidor"]
    assert comando[5:] == ["--server.port", "9000", "--server.headless", "true"]
    assert servidor["navegador"] == []
