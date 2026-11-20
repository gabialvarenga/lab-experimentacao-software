import shutil

import pytest

from conftest import PILOTO
from lab05 import analise, config, executor

RAPIDO = {"grade_n": [5, 10], "candidatos_n": [5, 10], "diferencas": [0.05, 0.5], "simulacoes": 100, "bootstrap": 200}
ARQUIVOS = ["descritiva", "teste-principal", "comparacoes", "repeticoes", "curva-poder", "diferenca-detectavel"]


@pytest.fixture
def cfg(tmp_path):
    (tmp_path / "coleta").mkdir()
    shutil.copy(PILOTO, tmp_path / "coleta" / "piloto.csv")
    c = {**config.carregar(), "pasta": str(tmp_path)}
    c["analise"] = {**c["analise"], **RAPIDO}
    return executor.aplicar_ajustes(c, saida="coleta", nome="piloto")


def test_parametros_completam_o_config_com_os_padroes():
    p = analise.parametros({"analise": {"poder": 0.9}})
    assert p["poder"] == 0.9 and p["diferenca_relevante"] == 0.05 and p["cenario_holm"] == "conservador"
    assert analise.parametros({})["simulacoes"] == analise.PADROES["simulacoes"]


def test_config_versionado_tem_o_bloco_de_analise():
    p = analise.parametros(config.carregar())
    assert (p["diferenca_relevante"], p["alfa"], p["poder"], p["bootstrap"]) == (0.05, 0.05, 0.80, 10000)


def test_analisar_o_piloto_gera_todas_as_tabelas(cfg):
    r = analise.analisar(cfg)
    assert list(r) == ARQUIVOS
    assert len(r["descritiva"]) == 48 and len(r["teste-principal"]) == 4 and len(r["comparacoes"]) == 24
    assert len(r["repeticoes"]) == 3 * 4 and set(r["repeticoes"]["variabilidade"]) == {"bruta", "sem efeito de bloco"}
    assert set(r["repeticoes"]["cenario"]) == {"conservador", "todas"}
    assert len(r["curva-poder"]) == 4 * 2 * 6 and len(r["diferenca-detectavel"]) == 4 * 2


def test_gravar_escreve_os_csvs_e_um_registro_deterministico(cfg):
    r = analise.analisar(cfg)
    pasta = analise.gravar(cfg, r, "python -m lab05 analisar")
    assert pasta == analise.pasta_saida(cfg)
    assert all((pasta / f"{nome}.csv").exists() for nome in ARQUIVOS)
    texto = (pasta / "registro-analise.md").read_text(encoding="utf-8")
    assert texto == analise.registro(cfg, analise.analisar(cfg), "python -m lab05 analisar")
    for trecho in ("# Registro da análise — piloto.csv", "`python -m lab05 analisar`", "| Execuções | 60 |",
                   "## Teste principal por métrica (regra 5.1)", "**não é conclusão**", "| n = 5 | n = 10 |"):  # fmt: skip
        assert trecho in texto
    assert analise.sha256(executor.caminhos(cfg)["csv"]) in texto


def test_sha256_ignora_a_diferenca_entre_lf_e_crlf(tmp_path):
    (tmp_path / "lf.txt").write_bytes(b"a\nb\n")
    (tmp_path / "crlf.txt").write_bytes(b"a\r\nb\r\n")
    assert analise.sha256(tmp_path / "lf.txt") == analise.sha256(tmp_path / "crlf.txt")


def test_sem_csv_levanta_erro(cfg):
    executor.caminhos(cfg)["csv"].unlink()
    with pytest.raises(FileNotFoundError, match="rode o executor"):
        analise.analisar(cfg)
