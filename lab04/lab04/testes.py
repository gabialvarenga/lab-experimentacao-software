"""Welch, Mann-Whitney e tamanhos de efeito (Issue S01-05).

Os dois testes são bicaudais. Por convenção, `a` é o primeiro grupo e `b` o segundo; os
tamanhos de efeito são `a` em relação a `b` (no Lab04, `a` = com_bot e `b` = sem_bot).

`aplicar_testes` serve a um par de amostras (dados reais, exemplo simulado e G2).
`aplicar_testes_vetorizado` aplica os testes a milhares de pares de uma vez (simulação) e
devolve só os p-valores; para cada linha dá o mesmo p-valor que `aplicar_testes`.
"""

import warnings

import numpy as np
from scipy import stats


def _como_array(x, nome: str, minimo: int = 2) -> np.ndarray:
    x = np.asarray(x, dtype=float)
    if x.ndim != 1:
        raise ValueError(f"{nome} deve ser um vetor")
    if np.isnan(x).any():
        raise ValueError(f"{nome} tem NaN")
    if len(x) < minimo:
        raise ValueError(f"{nome} precisa de ao menos {minimo} observações")
    return x


def metodo_mw(n1: int, n2: int, empates: bool) -> str:
    """Método do p-valor do Mann-Whitney, pela mesma regra do `method="auto"` do SciPy.

    Assintótico se os dois grupos têm mais de 8 observações ou se há empates; exato nos demais
    casos. É explícito aqui para o registro (`mw_metodo`) e para a versão vetorizada.
    """
    if n1 > 8 and n2 > 8:
        return "asymptotic"
    return "asymptotic" if empates else "exact"


def hedges_g(a, b) -> float:
    """Diferença padronizada de médias (a − b) com a correção de viés de Hedges.

    Vale 0 se os dois grupos são constantes e iguais, e NaN se o desvio-padrão combinado é
    zero e as médias diferem (o efeito é indefinido).
    """
    a, b = _como_array(a, "a"), _como_array(b, "b")
    n1, n2 = len(a), len(b)
    graus = n1 + n2 - 2
    variancia = ((n1 - 1) * a.var(ddof=1) + (n2 - 1) * b.var(ddof=1)) / graus
    diferenca = a.mean() - b.mean()
    if variancia == 0:
        return 0.0 if diferenca == 0 else float("nan")
    return float(diferenca / np.sqrt(variancia) * (1 - 3 / (4 * graus - 1)))


def cliff_delta(a, b) -> float:
    """Delta de Cliff: (pares com a > b − pares com a < b) / (n1 · n2), em [−1, 1]."""
    a, b = _como_array(a, "a", 1), _como_array(b, "b", 1)
    maiores = (a[:, None] > b[None, :]).sum()
    menores = (a[:, None] < b[None, :]).sum()
    return float((maiores - menores) / (len(a) * len(b)))


def razao_medianas(a, b) -> float:
    """Mediana de `a` dividida pela de `b`; NaN se a mediana de `b` for zero.

    Só tem sentido para variáveis positivas, como o tempo até o merge.
    """
    a, b = _como_array(a, "a", 1), _como_array(b, "b", 1)
    mediana_b = np.median(b)
    return float(np.median(a) / mediana_b) if mediana_b != 0 else float("nan")


def aplicar_testes(a, b) -> dict:
    """Welch e Mann-Whitney bicaudais em um par de amostras, com os tamanhos de efeito.

    Chaves: `welch_t`, `welch_gl`, `welch_p`, `mw_u` (estatística U de `a`), `mw_p`,
    `mw_metodo` (`exact` ou `asymptotic`), `hedges_g`, `cliff_delta` e `razao_medianas`.
    Levanta `ValueError` com NaN, amostra com menos de 2 observações ou dimensão diferente de 1.
    Com variância zero nos dois grupos, `welch_t` e `welch_p` saem NaN, sem aviso.
    """
    a, b = _como_array(a, "a"), _como_array(b, "b")
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        welch = stats.ttest_ind(a, b, equal_var=False)
    empates = len(np.unique(np.concatenate([a, b]))) < len(a) + len(b)
    metodo = metodo_mw(len(a), len(b), empates)
    mw = stats.mannwhitneyu(a, b, alternative="two-sided", method=metodo)
    return {
        "welch_t": float(welch.statistic),
        "welch_gl": float(welch.df),
        "welch_p": float(welch.pvalue),
        "mw_u": float(mw.statistic),
        "mw_p": float(mw.pvalue),
        "mw_metodo": metodo,
        "hedges_g": hedges_g(a, b),
        "cliff_delta": cliff_delta(a, b),
        "razao_medianas": razao_medianas(a, b),
    }


def aplicar_testes_vetorizado(A, B) -> dict:
    """p-valores de Welch e Mann-Whitney para cada linha de `A` e `B` (matrizes `(n_rep, n)`).

    Devolve `{"welch_p": ndarray, "mw_p": ndarray}`, cada um com `n_rep` valores. O método do
    Mann-Whitney segue a regra de `metodo_mw` linha a linha, então o resultado de uma linha é
    igual ao de `aplicar_testes` sobre ela. Linhas sem variância dão NaN no Welch.
    """
    A, B = np.asarray(A, dtype=float), np.asarray(B, dtype=float)
    if A.ndim != 2 or B.ndim != 2 or A.shape[0] != B.shape[0]:
        raise ValueError("A e B devem ser matrizes com o mesmo número de linhas")
    if A.shape[1] < 2 or B.shape[1] < 2:
        raise ValueError("cada linha precisa de ao menos 2 observações por grupo")
    if np.isnan(A).any() or np.isnan(B).any():
        raise ValueError("A ou B tem NaN")
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        welch_p = stats.ttest_ind(A, B, axis=1, equal_var=False).pvalue
    n1, n2 = A.shape[1], B.shape[1]
    if n1 > 8 and n2 > 8:
        mw_p = stats.mannwhitneyu(A, B, axis=1, alternative="two-sided", method="asymptotic").pvalue
    else:
        juntos = np.sort(np.concatenate([A, B], axis=1), axis=1)
        com_empate = (np.diff(juntos, axis=1) == 0).any(axis=1)
        mw_p = np.empty(A.shape[0])
        for empate in (False, True):
            linhas = com_empate == empate
            if linhas.any():
                metodo = metodo_mw(n1, n2, empate)
                mw_p[linhas] = stats.mannwhitneyu(A[linhas], B[linhas], axis=1, alternative="two-sided", method=metodo).pvalue
    return {"welch_p": np.asarray(welch_p, dtype=float), "mw_p": mw_p}
