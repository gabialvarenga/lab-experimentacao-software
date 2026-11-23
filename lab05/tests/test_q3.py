"""Testes de `lab05/q3.py` (S02-01)."""

import numpy as np
import pandas as pd
import pytest

from conftest import coleta_sintetica
from lab05 import q3, testes


def _carga(df, carga="get", metrica="ops_s"):
    dados = q3._preparar(df, metrica)
    return dados[dados["carga"] == carga]


def test_residuos_do_modelo_somam_zero_em_cada_celula():
    df = coleta_sintetica(n=6, sigma=0.1)
    r = q3.residuos_modelo(df, "ops_s")
    assert len(r) == len(df)
    soma = pd.Series(r).groupby([df["carga"], df["servidor"], df["io_threads"]]).sum()
    assert np.allclose(soma, 0)


def test_regra_escolhe_anova_com_residuos_normais_e_art_com_cauda_pesada():
    normal = coleta_sintetica(n=30, sigma=0.1, semente=5)
    assert q3.escolher_metodo(normal, "ops_s")["metodo"] == "anova"
    pesada = normal.copy()
    pesada["ops_s"] *= np.exp(np.random.default_rng(1).standard_t(1.5, len(pesada)) * 0.1)
    escolha = q3.escolher_metodo(pesada, "ops_s")
    assert escolha["metodo"] == "art" and "Shapiro-Wilk" in escolha["motivo"] and escolha["n_residuos"] == len(pesada)


def test_regra_recusa_variancias_diferentes_entre_as_celulas():
    df = coleta_sintetica(n=40, sigma=0.05, semente=2)
    ruidosa = (df["servidor"] == "valkey") & (df["io_threads"] == 4)
    df.loc[ruidosa, "ops_s"] *= np.exp(np.random.default_rng(3).normal(0, 0.4, ruidosa.sum()))
    escolha = q3.escolher_metodo(df, "ops_s")
    assert escolha["metodo"] == "art" and "Levene" in escolha["motivo"]


def test_regra_sem_variacao_cai_na_art():
    df = coleta_sintetica(n=3, sigma=0.0)
    assert q3.escolher_metodo(df, "ops_s")["motivo"] == "resíduos sem variação"


def test_no_piloto_a_regra_escolhe_a_art_nas_duas_metricas(piloto):
    for metrica in q3.METRICAS:
        escolha = q3.escolher_metodo(piloto, metrica)
        assert escolha["metodo"] == "art" and escolha["shapiro_p"] < 0.05 and abs(escolha["assimetria"]) <= 1


def test_soma_de_quadrados_da_interacao_confere_com_a_conta_feita_a_mao():
    # 2 × 2 balanceado: SS da interação = n · c² / 4, com c = m11 − m12 − m21 + m22 (médias das células)
    dados = _carga(coleta_sintetica(n=8, sigma=0.1, semente=7, razao_threads4=1.3))
    m = dados.groupby(["servidor", "io_threads"])["y"].mean()
    c = m["redis", 1] - m["redis", 4] - m["valkey", 1] + m["valkey", 4]
    tabela = q3._ajustar(dados, "y")
    assert tabela.loc[q3.TERMOS["interacao"], "sum_sq"] == pytest.approx(8 * c**2 / 4)
    r = q3.anova(dados)
    ss, ss_res = tabela.loc[q3.TERMOS["interacao"], "sum_sq"], tabela.loc["Residual", "sum_sq"]
    assert r["interacao"]["eta2_parcial"] == pytest.approx(ss / (ss + ss_res))


def test_alinhamento_da_interacao_nao_tem_efeitos_principais():
    dados = _carga(coleta_sintetica(n=6, sigma=0.1, razao=1.3, razao_threads4=2.0))
    alinhado = pd.Series(q3.alinhar(dados, "interacao"), index=dados.index)
    assert np.allclose(alinhado.groupby(dados["servidor"]).mean(), 0)
    assert np.allclose(alinhado.groupby(dados["io_threads"]).mean(), 0)
    with pytest.raises(ValueError, match="efeito"):
        q3.alinhar(dados, "carga")


def test_art_acha_a_interacao_quando_ela_existe_e_nao_inventa_quando_nao_existe():
    com = q3.art(_carga(coleta_sintetica(n=15, sigma=0.05, semente=1, razao=1.0, razao_threads4=1.3)))
    sem = q3.art(_carga(coleta_sintetica(n=15, sigma=0.05, semente=1, razao=1.3, razao_threads4=1.3)))
    assert com["interacao"]["p"] < 0.001
    assert sem["servidor"]["p"] < 0.001 and sem["interacao"]["p"] > 0.05


def test_razao_das_razoes_confere_com_a_conta_feita_a_mao():
    assert q3.razao_das_razoes([1.0], [2.0], [1.0], [4.0]) == pytest.approx(0.5)
    inf, sup = q3.ic_razao_das_razoes([1.0, 1.0], [2.0, 2.0], [1.0, 1.0], [4.0, 4.0], np.random.default_rng(0), 100)
    assert inf == pytest.approx(0.5) and sup == pytest.approx(0.5)


def test_analisar_recupera_a_interacao_simulada():
    df = coleta_sintetica(n=20, sigma=0.05, semente=3, razao=1.0, razao_threads4=1.5)
    t = q3.analisar(df, "ops_s", "anova", np.random.default_rng(0), 500)
    assert list(t.columns) == q3.COLUNAS and len(t) == 3 and list(t["carga"]) == ["get", "misto", "set"]
    assert t["razao_das_razoes"].to_numpy() == pytest.approx(1.5, rel=0.08)
    assert (t["ic_inf"] < t["razao_das_razoes"]).all() and (t["razao_das_razoes"] < t["ic_sup"]).all()
    assert (t["p_holm"] >= t["p_interacao"]).all() and (t["situacao"] == "diferença relevante").all()
    assert (t["teste"] == "anova").all() and (t["teste_sensibilidade"] == q3.SENSIBILIDADE).all()
    assert t["p_sensibilidade"].notna().all() and not t["testes_discordam"].any()


def test_o_bloco_tira_a_deriva_dos_residuos_da_sensibilidade():
    df = coleta_sintetica(n=10, sigma=0.03, semente=4, razao=1.0, razao_threads4=1.06)
    for repeticao, fator in zip(range(1, 11), [1.0, 0.7, 1.2, 0.9, 1.1, 0.8, 1.0, 1.3, 0.75, 1.05]):
        df.loc[df["repeticao"] == repeticao, "ops_s"] *= fator
    t = q3.analisar(df, "ops_s", "anova", np.random.default_rng(0), 200)
    assert (t["p_sensibilidade"] < t["p_interacao"]).all()


def test_analisar_sem_repeticao_nao_tem_sensibilidade_e_usa_a_regra_sem_metodo():
    df = coleta_sintetica(n=5, sigma=0.1).drop(columns="repeticao")
    t = q3.analisar(df, "lat_p99_ms", rng=np.random.default_rng(0), n_boot=100)
    assert t["p_sensibilidade"].isna().all() and not t["testes_discordam"].any()
    assert (t["teste"] == q3.escolher_metodo(df, "lat_p99_ms")["metodo"]).all()


def test_analisar_recusa_entradas_invalidas():
    df = coleta_sintetica(n=3)
    with pytest.raises(ValueError, match="método"):
        q3.analisar(df, "ops_s", "kruskal")
    with pytest.raises(ValueError, match="faltam"):
        q3.analisar(df.drop(columns="carga"), "ops_s")
    with pytest.raises(ValueError, match="positivos"):
        q3.analisar(df.assign(ops_s=0.0), "ops_s")
    with pytest.raises(ValueError, match="2 níveis"):
        q3.analisar(df[df["io_threads"] == 1], "ops_s")
    with pytest.raises(ValueError, match="dois servidores"):
        q3.analisar(df[df["servidor"] == "redis"], "ops_s")
    with pytest.raises(ValueError, match="ao menos 2"):
        q3.analisar(df[df["repeticao"] == 1], "ops_s")


def test_q3_roda_no_piloto(piloto):
    t = q3.analisar(piloto, "ops_s", rng=np.random.default_rng(0), n_boot=200)
    assert (t["teste"] == "art").all() and (t["n_por_celula"] == 5).all()
    assert t["situacao"].isin(testes.SITUACOES).all() and t["eta2_parcial"].between(0, 1).all()
