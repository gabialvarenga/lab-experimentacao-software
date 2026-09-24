import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analise.dashboard import (
    boxplot_por_tratamento,
    gerar_todos,
    graficos_diferenciais,
    graficos_rq1,
    graficos_rq2,
    graficos_rq3,
    matriz_correlacao,
    mediana_por_kata,
    preparar_tempo_vs_estrutura,
    sem_variancia,
)

DIR_DADOS_REAIS = Path(__file__).resolve().parent.parent / "dados"


def _df_trials() -> pd.DataFrame:
    """Dois integrantes x 2 katas x 2 tratamentos, com-ia sempre mais rápido."""
    return pd.DataFrame(
        {
            "integrante": ["ana"] * 4 + ["bia"] * 4,
            "kata": ["k1", "k2", "k1", "k2"] * 2,
            "tratamento": ["com-ia", "com-ia", "sem-ia", "sem-ia"] * 2,
            "ordem": [1, 2, 3, 4] * 2,
            "tempo_segundos": [30, 40, 300, 400, 35, 45, 310, 410],
            "prompts": [1, 2, 0, 0, 1, 3, 0, 0],
            "taxa_sucesso": [100.0] * 8,
            "testes_falhando": [0] * 8,
        }
    )


def _df_metricas() -> pd.DataFrame:
    return pd.DataFrame(
        {
            "integrante": ["ana"] * 4 + ["bia"] * 4,
            "kata": ["k1", "k2", "k1", "k2"] * 2,
            "tratamento": ["com-ia", "com-ia", "sem-ia", "sem-ia"] * 2,
            "loc": [10, 12, 20, 22, 11, 13, 21, 23],
            "cc_media": [2.0, 4.0, 6.0, 8.0, 3.0, 5.0, 7.0, 9.0],
            "mi": [80.0, 75.0, 60.0, 55.0, 78.0, 73.0, 58.0, 53.0],
            "duplicacao_pct": [0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0],
        }
    )


# --------------------------------------------------------------------------
# Helpers puros
# --------------------------------------------------------------------------

def test_sem_variancia_detecta_coluna_constante():
    assert sem_variancia(pd.Series([100.0, 100.0, 100.0]))
    assert not sem_variancia(pd.Series([100.0, 99.0]))


def test_sem_variancia_em_serie_de_um_elemento():
    assert sem_variancia(pd.Series([1.0]))


def test_matriz_correlacao_e_quadrada_e_tem_diagonal_unitaria():
    matriz = matriz_correlacao(_df_metricas())
    assert list(matriz.columns) == list(matriz.index)
    assert matriz.shape == (4, 4)
    for coluna in matriz.columns:
        assert matriz.loc[coluna, coluna] == pytest.approx(1.0)


def test_matriz_correlacao_capta_relacao_monotonica_conhecida():
    # loc e cc_media crescem juntos no fixture; mi decresce contra loc.
    matriz = matriz_correlacao(_df_metricas())
    assert matriz.loc["loc", "cc_media"] > 0.5
    assert matriz.loc["loc", "mi"] < -0.5


def test_mediana_por_kata_devolve_uma_linha_por_kata_e_colunas_por_tratamento():
    tabela = mediana_por_kata(_df_trials(), "tempo_segundos")
    assert list(tabela.columns) == ["kata", "com-ia", "sem-ia"]
    assert list(tabela["kata"]) == ["k1", "k2"]
    assert tabela.loc[tabela["kata"] == "k1", "com-ia"].item() == pytest.approx(32.5)
    assert tabela.loc[tabela["kata"] == "k1", "sem-ia"].item() == pytest.approx(305.0)


def test_preparar_tempo_vs_estrutura_junta_tempo_e_metricas_sem_perder_trials():
    completo = preparar_tempo_vs_estrutura(DIR_DADOS_REAIS)
    trials = pd.read_csv(DIR_DADOS_REAIS / "trials.csv")
    assert len(completo) == len(trials)
    for coluna in ("tempo_segundos", "cc_media", "loc"):
        assert completo[coluna].notna().all()


# --------------------------------------------------------------------------
# Geração dos arquivos
# --------------------------------------------------------------------------

def test_boxplot_por_tratamento_cria_o_arquivo(tmp_path):
    caminho = boxplot_por_tratamento(
        _df_trials(), "tempo_segundos", "titulo", "rotulo", tmp_path / "box.png"
    )
    assert caminho.exists() and caminho.stat().st_size > 0


def test_boxplot_cria_subdiretorio_inexistente(tmp_path):
    caminho = boxplot_por_tratamento(
        _df_trials(), "tempo_segundos", "t", "r", tmp_path / "novo" / "box.png"
    )
    assert caminho.exists()


def test_boxplot_de_coluna_constante_nao_quebra(tmp_path):
    """RQ2 real: taxa_sucesso=100% em todos os trials."""
    caminho = boxplot_por_tratamento(
        _df_trials(), "taxa_sucesso", "t", "r", tmp_path / "plano.png"
    )
    assert caminho.exists()


def test_graficos_rq1_gera_os_tres_esperados(tmp_path):
    caminhos = graficos_rq1(_df_trials(), tmp_path)
    assert [c.name for c in caminhos] == [
        "rq1_tempo_boxplot.png",
        "rq1_prompts_vs_tempo.png",
        "rq1_tempo_vs_ordem.png",
    ]
    assert all(c.exists() for c in caminhos)


def test_graficos_rq2_gera_os_tres_esperados(tmp_path):
    caminhos = graficos_rq2(_df_trials(), tmp_path, DIR_DADOS_REAIS)
    assert [c.name for c in caminhos] == [
        "rq2_taxa_sucesso_boxplot.png",
        "rq2_testes_falhando_boxplot.png",
        "rq2_densidade_defeitos_boxplot.png",
    ]
    assert all(c.exists() for c in caminhos)


def test_graficos_rq3_gera_os_quatro_esperados(tmp_path):
    caminhos = graficos_rq3(_df_metricas(), tmp_path)
    assert [c.name for c in caminhos] == [
        "rq3_cc_media_boxplot.png",
        "rq3_duplicacao_boxplot.png",
        "rq3_loc_histograma_boxplot.png",
        "rq3_mi_boxplot.png",
    ]
    assert all(c.exists() for c in caminhos)


def test_graficos_diferenciais_gera_os_tres_esperados(tmp_path):
    completo = _df_trials().merge(
        _df_metricas(), on=["integrante", "kata", "tratamento"], how="left"
    )
    caminhos = graficos_diferenciais(completo, _df_metricas(), tmp_path)
    assert [c.name for c in caminhos] == [
        "extra_bubble_tempo_vs_cc.png",
        "extra_heatmap_correlacao.png",
        "extra_barras_por_kata.png",
    ]
    assert all(c.exists() for c in caminhos)


def test_gerar_todos_nos_dados_reais_produz_13_graficos(tmp_path):
    caminhos = gerar_todos(tmp_path, DIR_DADOS_REAIS)
    assert len(caminhos) == 13
    assert len({c.name for c in caminhos}) == 13  # sem sobrescrita entre gráficos
    assert all(c.exists() and c.stat().st_size > 0 for c in caminhos)
