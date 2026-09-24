import sys
from pathlib import Path

import pandas as pd
import pytest

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from analise.rq3_estatistica import (
    comparar_metrica,
    contagem_trials_com_duplicacao,
    correlacao_spearman,
    tabela_descritiva,
    trials_com_duplicacao,
)


def _df_exemplo() -> pd.DataFrame:
    """Dois integrantes, 2 trials por tratamento; com-ia sempre menor em cc."""
    return pd.DataFrame(
        {
            "integrante": ["ana"] * 4 + ["bia"] * 4,
            "kata": ["k1", "k2", "k3", "k4"] * 2,
            "tratamento": ["com-ia", "com-ia", "sem-ia", "sem-ia"] * 2,
            "loc": [10, 12, 20, 22, 11, 13, 21, 23],
            "cc_media": [2.0, 4.0, 6.0, 8.0, 3.0, 5.0, 7.0, 9.0],
            "duplicacao_pct": [0.0, 0.0, 0.0, 10.0, 0.0, 0.0, 0.0, 0.0],
        }
    )


def test_tabela_descritiva_tem_mediana_e_iqr_por_metrica_e_tratamento():
    t = tabela_descritiva(_df_exemplo(), ("cc_media", "loc"))
    assert set(t["metrica"]) == {"cc_media", "loc"}
    linha = t[(t["metrica"] == "cc_media") & (t["tratamento"] == "com-ia")].iloc[0]
    assert linha["mediana"] == pytest.approx(3.5)
    assert linha["iqr"] == pytest.approx(linha["q3"] - linha["q1"])
    assert len(t) == 4


def test_comparar_metrica_direcao_e_estrutura():
    r = comparar_metrica(_df_exemplo(), "cc_media")
    assert r["wilcoxon"].sem_variancia is False
    assert r["wilcoxon"].n == 2
    assert r["r_biserial"] == pytest.approx(-1.0)
    lo, hi = r["ic_diferenca_mediana"]
    assert lo <= hi < 0  

def test_comparar_metrica_sem_variancia_quando_todas_as_medianas_iguais():
    """Caso real: mediana de duplicacao_pct por integrante é 0 nos dois tratamentos."""

    df = pd.DataFrame(
        {
            "integrante": ["ana"] * 6,
            "tratamento": ["com-ia"] * 3 + ["sem-ia"] * 3,
            "duplicacao_pct": [0.0, 0.0, 0.0, 0.0, 0.0, 35.7],
        }
    )
    r = comparar_metrica(df, "duplicacao_pct")
    assert r["wilcoxon"].sem_variancia is True
    assert r["wilcoxon"].p_valor is None
    assert r["r_biserial"] is None


def test_trials_com_duplicacao_expoe_o_que_a_mediana_esconde():
    t = trials_com_duplicacao(_df_exemplo())
    assert len(t) == 1
    assert t.iloc[0]["integrante"] == "ana"
    assert t.iloc[0]["tratamento"] == "sem-ia"


def test_contagem_trials_com_duplicacao_por_tratamento():
    assert contagem_trials_com_duplicacao(_df_exemplo()) == {"com-ia": 0, "sem-ia": 1}


def test_correlacao_spearman_monotonica_perfeita():
    df = pd.DataFrame({"loc": [1, 2, 3, 4], "cc_media": [10, 20, 30, 40]})
    assert correlacao_spearman(df, "loc", "cc_media") == pytest.approx(1.0)
