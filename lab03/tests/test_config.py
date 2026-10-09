import os
from datetime import date

import pytest

from pipeline import config
from pipeline.config import ErroDeConfiguracao

VALIDO = """
janela:
  inicio: 2025-10-01
  fim: 2026-09-30
criterios:
  min_releases: 5
  min_workflow_runs: 50
selecao:
  alvo_aprovados: 100
  faixas_estrelas:
    - ">10000"
    - "5000..10000"
caminhos:
  cache: dados/cache
  saida: dados/saida
"""


@pytest.fixture
def com_token(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "token-de-teste")


def gravar(tmp_path, texto=VALIDO):
    caminho = tmp_path / "config.yaml"
    caminho.write_text(texto, encoding="utf-8")
    return str(caminho)


def test_janela_vem_como_date(tmp_path, com_token):
    cfg = config.carregar(gravar(tmp_path))

    assert cfg["janela"] == {"inicio": date(2025, 10, 1), "fim": date(2026, 9, 30)}


def test_janela_entre_aspas_tambem_vira_date(tmp_path, com_token):
    texto = VALIDO.replace("2025-10-01", '"2025-10-01"').replace("2026-09-30", '"2026-09-30"')

    cfg = config.carregar(gravar(tmp_path, texto))

    assert cfg["janela"] == {"inicio": date(2025, 10, 1), "fim": date(2026, 9, 30)}


def test_token_vem_da_variavel_de_ambiente(tmp_path, com_token):
    assert config.carregar(gravar(tmp_path))["token"] == "token-de-teste"


@pytest.mark.parametrize("valor", [None, "", "   "])
def test_sem_token_levanta_erro_que_cita_a_variavel(tmp_path, monkeypatch, valor):
    if valor is None:
        monkeypatch.delenv("GITHUB_TOKEN", raising=False)
    else:
        monkeypatch.setenv("GITHUB_TOKEN", valor)

    with pytest.raises(ErroDeConfiguracao, match="GITHUB_TOKEN"):
        config.carregar(gravar(tmp_path))


def test_demais_valores_sao_mantidos(tmp_path, com_token):
    cfg = config.carregar(gravar(tmp_path))

    assert cfg["criterios"] == {"min_releases": 5, "min_workflow_runs": 50}
    assert cfg["selecao"]["alvo_aprovados"] == 100
    assert cfg["selecao"]["faixas_estrelas"] == [">10000", "5000..10000"]


def test_caminhos_relativos_partem_da_pasta_do_config(tmp_path, com_token):
    cfg = config.carregar(gravar(tmp_path))

    assert cfg["caminhos"] == {
        "cache": os.path.join(str(tmp_path), "dados", "cache"),
        "saida": os.path.join(str(tmp_path), "dados", "saida"),
    }


def test_caminho_absoluto_e_mantido(tmp_path, com_token):
    absoluto = str(tmp_path / "outro" / "cache")
    texto = VALIDO.replace("cache: dados/cache", f"cache: '{absoluto}'")

    assert config.carregar(gravar(tmp_path, texto))["caminhos"]["cache"] == absoluto


@pytest.mark.parametrize(
    "trecho, chave",
    [
        ("  alvo_aprovados: 100\n", "selecao.alvo_aprovados"),
        ("  min_releases: 5\n", "criterios.min_releases"),
        ("  fim: 2026-09-30\n", "janela.fim"),
        ("  saida: dados/saida\n", "caminhos.saida"),
    ],
)
def test_chave_obrigatoria_ausente_e_citada_no_erro(tmp_path, com_token, trecho, chave):
    with pytest.raises(ErroDeConfiguracao, match=chave):
        config.carregar(gravar(tmp_path, VALIDO.replace(trecho, "")))


def test_alvo_que_nao_e_inteiro_positivo_e_rejeitado(tmp_path, com_token):
    with pytest.raises(ErroDeConfiguracao, match="alvo_aprovados"):
        config.carregar(gravar(tmp_path, VALIDO.replace("alvo_aprovados: 100", "alvo_aprovados: 0")))


def test_janela_invertida_e_rejeitada(tmp_path, com_token):
    texto = VALIDO.replace("fim: 2026-09-30", "fim: 2025-01-01")

    with pytest.raises(ErroDeConfiguracao, match="janela.fim"):
        config.carregar(gravar(tmp_path, texto))


def test_arquivo_inexistente_levanta_erro_de_configuracao(tmp_path, com_token):
    with pytest.raises(ErroDeConfiguracao, match="nao-existe.yaml"):
        config.carregar(str(tmp_path / "nao-existe.yaml"))


def test_config_do_projeto_e_valido(com_token):
    raiz = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

    cfg = config.carregar(os.path.join(raiz, "config.yaml"))

    assert cfg["selecao"]["alvo_aprovados"] == 100
    assert cfg["caminhos"]["saida"] == os.path.join(raiz, "dados", "saida")
