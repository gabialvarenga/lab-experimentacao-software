import math

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from lab04 import descritiva


def tabela(com_bot, sem_bot=(1.0, 2.0, 3.0)):
    grupos = ["com_bot"] * len(com_bot) + ["sem_bot"] * len(sem_bot)
    return pd.DataFrame({"grupo": grupos, "horas_ate_merge": [*com_bot, *sem_bot]})


def test_quartis_iqr_e_outlier_conferem_com_a_conta_feita_a_mao():
    # 1, 2, 3, 4, 100: Q1 = 2, mediana = 3, Q3 = 4, IQR = 2; limite = 4 + 1,5 · 2 = 7, só o 100 passa
    r = descritiva.descrever(tabela([1, 2, 3, 4, 100])).loc["com_bot"]
    assert (r["n"], r["q1"], r["mediana"], r["q3"], r["iqr"]) == (5, 2, 3, 4, 2)
    assert r["limite_outlier"] == 7
    assert (r["n_outliers"], r["pct_outliers"]) == (1, 20)
    assert (r["minimo"], r["maximo"], r["media"]) == (1, 100, 22)
    assert r["desvio_padrao"] == pytest.approx(np.std([1, 2, 3, 4, 100], ddof=1))


def test_valor_exatamente_no_limite_nao_e_outlier():
    # 0, 1, 2, 3, 7: Q1 = 1, Q3 = 3, limite = 3 + 1,5 · 2 = 6; o 7 passa, e 6 não passaria
    assert descritiva.descrever(tabela([0, 1, 2, 3, 7])).loc["com_bot", "n_outliers"] == 1
    assert descritiva.descrever(tabela([0, 1, 2, 3, 6])).loc["com_bot", "n_outliers"] == 0


def test_assimetria_positiva_na_cauda_longa_e_nula_na_simetrica():
    cauda = [1, 2, 3, 4, 100]
    r = descritiva.descrever(tabela(cauda, sem_bot=[1, 2, 3, 4, 5]))
    assert r.loc["com_bot", "assimetria"] == pytest.approx(stats.skew(cauda, bias=False))
    assert r.loc["com_bot", "assimetria"] > 1
    assert r.loc["sem_bot", "assimetria"] == pytest.approx(0)


def test_tabela_tem_um_grupo_por_linha_na_ordem_do_protocolo():
    r = descritiva.descrever(tabela([1, 2, 3, 4]))
    assert list(r.index) == ["com_bot", "sem_bot"] and r.index.name == "grupo"
    assert list(r.columns) == descritiva.COLUNAS
    assert r["n"].tolist() == [4, 3]


def test_grupo_ausente_tem_n_zero_e_o_resto_nan():
    df = pd.DataFrame({"grupo": ["com_bot"] * 3, "horas_ate_merge": [1.0, 2.0, 3.0]})
    r = descritiva.descrever(df).loc["sem_bot"]
    assert r["n"] == 0 and r["n_outliers"] == 0
    assert math.isnan(r["mediana"]) and math.isnan(r["assimetria"])


def test_grupo_inesperado_aparece_depois_dos_dois_previstos():
    df = pd.DataFrame({"grupo": ["z", "sem_bot", "com_bot", "a"], "horas_ate_merge": [1.0, 2.0, 3.0, 4.0]})
    assert list(descritiva.descrever(df).index) == ["com_bot", "sem_bot", "a", "z"]


def test_poucos_prs_nao_inventam_medidas():
    um = descritiva.resumir([5.0])
    assert um["mediana"] == 5 and um["iqr"] == 0 and math.isnan(um["desvio_padrao"]) and math.isnan(um["assimetria"])
    dois = descritiva.resumir([1.0, 3.0])
    assert dois["desvio_padrao"] == pytest.approx(math.sqrt(2)) and math.isnan(dois["assimetria"])


def test_valores_todos_iguais_nao_tem_assimetria_nem_outlier():
    r = descritiva.resumir([4.0, 4.0, 4.0, 4.0])
    assert math.isnan(r["assimetria"]) and r["n_outliers"] == 0 and r["iqr"] == 0


def test_colunas_ou_horas_invalidas_levantam_erro():
    with pytest.raises(ValueError, match="grupo"):
        descritiva.descrever(pd.DataFrame({"horas_ate_merge": [1.0]}))
    with pytest.raises(ValueError, match="horas_ate_merge"):
        descritiva.descrever(pd.DataFrame({"grupo": ["com_bot"]}))
    with pytest.raises(ValueError, match="sem_bot"):
        descritiva.descrever(pd.DataFrame({"grupo": ["com_bot", "sem_bot"], "horas_ate_merge": [1.0, np.nan]}))
