import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analise.rq1_rq2_estatistica import (
    agregar_mediana_por_integrante,
    bootstrap_ic_diferenca_mediana,
    correlacao_rank_biserial,
    identificar_outliers,
    proporcao_censura,
    resumo_descritivo,
    rodar_wilcoxon,
)


def test_resumo_descritivo_mediana_e_iqr():
    valores = pd.Series([10, 20, 30, 40, 50])
    r = resumo_descritivo(valores)
    assert r["mediana"] == 30
    assert r["q1"] == 20
    assert r["q3"] == 40
    assert r["iqr"] == 20


def test_identificar_outliers_encontra_valor_fora_da_faixa():
    valores = pd.Series([10, 11, 12, 13, 14, 1000])
    assert identificar_outliers(valores) == [1000]


def test_identificar_outliers_vazio_quando_nao_ha_outlier():
    valores = pd.Series([10, 11, 12, 13, 14])
    assert identificar_outliers(valores) == []


def test_agregar_mediana_por_integrante_pivota_por_tratamento():
    df = pd.DataFrame(
        {
            "integrante": ["ana", "ana", "ana", "ana", "bia", "bia"],
            "tratamento": ["com-ia", "com-ia", "sem-ia", "sem-ia", "com-ia", "sem-ia"],
            "tempo_segundos": [10, 20, 100, 200, 5, 50],
        }
    )
    r = agregar_mediana_por_integrante(df, "tempo_segundos")
    ana = r[r["integrante"] == "ana"].iloc[0]
    assert ana["com-ia"] == 15
    assert ana["sem-ia"] == 150


def test_rodar_wilcoxon_caso_normal():
    com_ia = pd.Series([10, 20, 30])
    sem_ia = pd.Series([100, 200, 300])
    resultado = rodar_wilcoxon(com_ia, sem_ia, alternative="less")
    assert resultado.sem_variancia is False
    assert resultado.n == 3
    assert resultado.p_valor is not None


def test_rodar_wilcoxon_diferencas_todas_zero_nao_lanca_excecao():
    """Caso real de RQ2 nesta amostra: taxa_sucesso=100% pros 3 integrantes."""
    com_ia = pd.Series([100.0, 100.0, 100.0])
    sem_ia = pd.Series([100.0, 100.0, 100.0])
    resultado = rodar_wilcoxon(com_ia, sem_ia, alternative="greater")
    assert resultado.sem_variancia is True
    assert resultado.p_valor is None
    assert resultado.estatistica is None


def test_correlacao_rank_biserial_favoravel_a_com_ia():
    com_ia = pd.Series([10, 20, 30])
    sem_ia = pd.Series([100, 200, 300])
    r = correlacao_rank_biserial(com_ia, sem_ia)
    assert r == pytest.approx(-1.0)


def test_correlacao_rank_biserial_sem_variancia_devolve_none():
    com_ia = pd.Series([100.0, 100.0, 100.0])
    sem_ia = pd.Series([100.0, 100.0, 100.0])
    assert correlacao_rank_biserial(com_ia, sem_ia) is None


def test_bootstrap_ic_diferenca_mediana_e_reprodutivel_com_mesma_seed():
    com_ia = pd.Series([10, 20, 30, 15, 25])
    sem_ia = pd.Series([100, 110, 120, 105, 115])
    ic1 = bootstrap_ic_diferenca_mediana(com_ia, sem_ia, n_resamples=500, seed=1)
    ic2 = bootstrap_ic_diferenca_mediana(com_ia, sem_ia, n_resamples=500, seed=1)
    assert ic1 == ic2
    assert ic1[0] < ic1[1]
    assert ic1[1] < 0  # com_ia sempre menor que sem_ia nesse fixture


def test_proporcao_censura_por_tratamento():
    df = pd.DataFrame(
        {
            "tratamento": ["com-ia", "com-ia", "sem-ia", "sem-ia"],
            "censurado": [False, True, False, False],
        }
    )
    r = proporcao_censura(df)
    assert r["com-ia"] == 50.0
    assert r["sem-ia"] == 0.0
