"""Estatística descritiva por combinação e métrica: mediana, IQR e coeficiente de variação (S01-09).

Origem: `resumir` foi adaptado de `lab04/lab04/descritiva.py` (copiado, e não importado: cada
laboratório roda sozinho). Mudanças: o CV entra no resumo (as quatro métricas são de razão, ver o
plano de análise, seção 3), os *outliers* são contados nos dois lados (a vazão pode cair, e não só
subir) e o resumo é feito por combinação (servidor × `io_threads` × carga) em vez de por grupo.

Convenções:

- quartis pelo método linear (o padrão de `numpy.percentile` e de `pandas.Series.quantile`);
- CV = desvio-padrão amostral (ddof = 1) ÷ média; NaN com menos de 2 valores ou média zero;
- *outlier*: abaixo de Q1 − 1,5 × IQR ou acima de Q3 + 1,5 × IQR. Só é **contado**: o plano
  (seção 4) não remove *outliers* por valor.

`descrever(df)` é a tabela usada pela análise e pelo relatório de qualidade (`validacao.py`), para
que a mediana, o IQR e o CV sejam calculados num lugar só.
"""

import numpy as np
import pandas as pd

METRICAS = ["ops_s", "lat_p50_ms", "lat_p99_ms", "memoria_bytes"]
CHAVES = ["servidor", "io_threads", "carga"]
FATOR_OUTLIER = 1.5
LIMITE_CV = 0.10  # alerta de ruído do ambiente (plano de análise, seção 4)
MEDIDAS = ["n", "media", "desvio_padrao", "minimo", "q1", "mediana", "q3", "maximo", "iqr", "cv", "n_outliers"]
COLUNAS = [*CHAVES, "metrica", *MEDIDAS]


def resumir(valores) -> dict:
    """As medidas de `MEDIDAS` para um vetor; vetor vazio dá n = 0 e o resto NaN."""
    x = np.asarray(valores, dtype=float)
    n = len(x)
    if n == 0:
        return {"n": 0, **{medida: float("nan") for medida in MEDIDAS[1:]}, "n_outliers": 0}
    q1, mediana, q3 = (float(v) for v in np.percentile(x, [25, 50, 75]))
    iqr = q3 - q1
    fora = (x < q1 - FATOR_OUTLIER * iqr) | (x > q3 + FATOR_OUTLIER * iqr)
    media = float(x.mean())
    desvio = float(x.std(ddof=1)) if n >= 2 else float("nan")
    return {
        "n": n,
        "media": media,
        "desvio_padrao": desvio,
        "minimo": float(x.min()),
        "q1": q1,
        "mediana": mediana,
        "q3": q3,
        "maximo": float(x.max()),
        "iqr": iqr,
        "cv": desvio / media if n >= 2 and media != 0 else float("nan"),
        "n_outliers": int(fora.sum()),
    }


def descrever(df: pd.DataFrame, metricas=METRICAS) -> pd.DataFrame:
    """Uma linha por combinação e métrica, nas colunas de `COLUNAS`, ordenada por combinação.

    Valores ausentes (NaN) são ignorados, e `n` conta só os presentes: a validação (S01-08) já
    aponta os ausentes como erro. Levanta `ValueError` se faltam colunas.
    """
    faltam = set(CHAVES) | set(metricas)
    faltam -= set(df.columns)
    if faltam:
        raise ValueError(f"faltam as colunas {sorted(faltam)}")
    linhas = []
    for chave, grupo in df.groupby(CHAVES, sort=True):
        for metrica in metricas:
            valores = pd.to_numeric(grupo[metrica], errors="coerce").dropna()
            linhas.append({**dict(zip(CHAVES, chave)), "metrica": metrica, **resumir(valores)})
    tabela = pd.DataFrame(linhas, columns=COLUNAS)
    return tabela.astype({"n": int, "n_outliers": int})
