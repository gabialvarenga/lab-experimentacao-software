import numpy as np
import pandas as pd
import pytest

from conftest import coleta_sintetica
from lab05 import descritiva


def test_resumir_confere_com_a_conta_feita_a_mao():
    r = descritiva.resumir([1.0, 2.0, 3.0, 4.0, 100.0])
    assert (r["n"], r["q1"], r["mediana"], r["q3"], r["iqr"]) == (5, 2.0, 3.0, 4.0, 2.0)
    assert (r["minimo"], r["maximo"], r["media"]) == (1.0, 100.0, 22.0)
    assert r["n_outliers"] == 1  # 100 > Q3 + 1,5 × IQR = 7
    assert r["cv"] == pytest.approx(np.std([1, 2, 3, 4, 100], ddof=1) / 22)


def test_resumir_conta_outliers_dos_dois_lados():
    assert descritiva.resumir([-100.0, 10.0, 11.0, 12.0, 13.0, 200.0])["n_outliers"] == 2


def test_resumir_vazio_e_com_um_valor():
    vazio = descritiva.resumir([])
    assert vazio["n"] == 0 and vazio["n_outliers"] == 0 and np.isnan(vazio["mediana"])
    um = descritiva.resumir([5.0])
    assert um["mediana"] == 5.0 and np.isnan(um["desvio_padrao"]) and np.isnan(um["cv"])


def test_cv_com_media_zero_e_nan():
    assert np.isnan(descritiva.resumir([-1.0, 1.0])["cv"])


def test_descrever_tem_uma_linha_por_combinacao_e_metrica():
    tabela = descritiva.descrever(coleta_sintetica(n=4))
    assert list(tabela.columns) == descritiva.COLUNAS
    assert len(tabela) == 12 * 4 and (tabela["n"] == 4).all()
    primeira = tabela.iloc[0]
    assert (primeira["servidor"], primeira["io_threads"], primeira["carga"], primeira["metrica"]) == ("redis", 1, "get", "ops_s")


def test_descrever_ignora_ausentes_e_aceita_metricas_escolhidas():
    df = coleta_sintetica(n=3)
    df.loc[0, "ops_s"] = np.nan
    tabela = descritiva.descrever(df, ["ops_s"])
    assert set(tabela["metrica"]) == {"ops_s"}
    assert sorted(tabela["n"].unique()) == [2, 3]


def test_descrever_sem_colunas_levanta_erro():
    with pytest.raises(ValueError, match="faltam"):
        descritiva.descrever(pd.DataFrame({"servidor": ["redis"]}))


def test_descrever_no_piloto_confere_com_o_relatorio_de_qualidade(piloto):
    tabela = descritiva.descrever(piloto)
    assert len(tabela) == 48 and (tabela["n"] == 5).all()
    linha = tabela[(tabela["servidor"] == "redis") & (tabela["io_threads"] == 1) & (tabela["carga"] == "get") & (tabela["metrica"] == "ops_s")].iloc[0]
    assert round(linha["mediana"]) == 80214 and round(linha["iqr"]) == 10135
    assert linha["cv"] == pytest.approx(0.118, abs=5e-4)
