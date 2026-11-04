"""Mediana, IQR, assimetria e outliers dos dados reais (S01-06).

`descrever(df)` resume as horas até o merge de cada grupo (`com_bot` e `sem_bot`) numa tabela com
uma linha por grupo. Convenções:

- quartis pelo método linear do NumPy (o padrão de `numpy.percentile`);
- assimetria de Fisher-Pearson ajustada para amostra (`scipy.stats.skew(bias=False)`), definida
  só com 3 ou mais observações que não sejam todas iguais (senão fica NaN);
- outlier: observação acima de Q3 + 1,5 × IQR. Como o tempo até o merge é positivo e de cauda
  longa, só o limite superior importa (o inferior, Q1 − 1,5 × IQR, fica abaixo de zero).
"""

import numpy as np
import pandas as pd
from scipy import stats

GRUPOS = ("com_bot", "sem_bot")
COLUNA_HORAS = "horas_ate_merge"
FATOR_OUTLIER = 1.5
COLUNAS = [
    "n",
    "media",
    "desvio_padrao",
    "minimo",
    "q1",
    "mediana",
    "q3",
    "maximo",
    "iqr",
    "assimetria",
    "limite_outlier",
    "n_outliers",
    "pct_outliers",
]


def horas_do_grupo(df: pd.DataFrame, grupo: str) -> np.ndarray:
    """Horas até o merge dos PRs do grupo, como vetor de floats (vazio se o grupo não aparece).

    Levanta `ValueError` se faltam as colunas `grupo` e `horas_ate_merge` ou se há horas ausentes.
    """
    faltam = {"grupo", COLUNA_HORAS} - set(df.columns)
    if faltam:
        raise ValueError(f"faltam as colunas {sorted(faltam)}")
    horas = pd.to_numeric(df.loc[df["grupo"] == grupo, COLUNA_HORAS], errors="coerce").to_numpy(dtype=float)
    if np.isnan(horas).any():
        raise ValueError(f"o grupo {grupo} tem {COLUNA_HORAS} ausente ou não numérico")
    return horas


def resumir(horas) -> dict:
    """As medidas da tabela para um vetor de horas; grupo vazio dá n = 0 e o resto NaN."""
    x = np.asarray(horas, dtype=float)
    n = len(x)
    if n == 0:
        return {"n": 0, **{coluna: float("nan") for coluna in COLUNAS[1:]}, "n_outliers": 0}
    q1, mediana, q3 = (float(v) for v in np.percentile(x, [25, 50, 75]))
    iqr = q3 - q1
    limite = q3 + FATOR_OUTLIER * iqr
    n_outliers = int((x > limite).sum())
    variavel = n >= 3 and np.ptp(x) > 0
    return {
        "n": n,
        "media": float(x.mean()),
        "desvio_padrao": float(x.std(ddof=1)) if n >= 2 else float("nan"),
        "minimo": float(x.min()),
        "q1": q1,
        "mediana": mediana,
        "q3": q3,
        "maximo": float(x.max()),
        "iqr": iqr,
        "assimetria": float(stats.skew(x, bias=False)) if variavel else float("nan"),
        "limite_outlier": limite,
        "n_outliers": n_outliers,
        "pct_outliers": 100 * n_outliers / n,
    }


def descrever(df: pd.DataFrame) -> pd.DataFrame:
    """Tabela descritiva das horas até o merge, uma linha por grupo (índice `grupo`).

    Traz sempre `com_bot` e `sem_bot`, nessa ordem (n = 0 se um deles faltar), seguidos de
    qualquer outro grupo que apareça no `df`, em ordem alfabética.
    """
    if "grupo" not in df.columns:
        raise ValueError("falta a coluna 'grupo'")
    extras = sorted(set(df["grupo"].dropna().unique()) - set(GRUPOS))
    grupos = [*GRUPOS, *extras]
    linhas = [resumir(horas_do_grupo(df, grupo)) for grupo in grupos]
    tabela = pd.DataFrame(linhas, index=pd.Index(grupos, name="grupo"), columns=COLUNAS)
    return tabela.astype({"n": int, "n_outliers": int})
