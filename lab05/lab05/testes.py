"""Testes de hipótese, tamanho de efeito, Holm e a comparação Valkey × Redis (S01-09).

Origem: `metodo_mw`, `hedges_g`, `cliff_delta`, `razao_medianas`, `aplicar_testes`,
`aplicar_testes_vetorizado` e as magnitudes foram copiados de `lab04/lab04/testes.py` (copiados, e
não importados: cada laboratório roda sozinho), sem mudança de cálculo. Saiu `tabela_dados_reais`,
própria do Lab04. Por convenção, `a` = `valkey` e `b` = `redis`: as razões e os tamanhos de efeito
são do **Valkey em relação ao Redis** (plano de análise, seção 5).

Novo no Lab05, pelas regras do plano de análise (`docs/plano-analise.md`):

- `holm`: correção de Holm-Bonferroni dentro de uma família (seção 6);
- `ic_razao_bootstrap`: IC de 95% da razão de medianas por *bootstrap* percentil (seção 5.2);
- `escolher_teste`: a regra 5.1, que decide o teste principal de cada métrica no piloto;
- `situacao`: as quatro situações da seção 6 (relevante, pequena demais, equivalência, inconclusivo);
- `comparar(df, metrica)`: as 6 comparações de uma pergunta (3 cargas × 2 níveis de `io_threads`).

A ANOVA da Q3 (interação servidor × `io_threads`) é da S02-06 e não está aqui.
"""

import warnings

import numpy as np
import pandas as pd
from scipy import stats

# ---------------------------------------------------------------------------------------------
# Copiado de lab04/lab04/testes.py
# ---------------------------------------------------------------------------------------------


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

    Só tem sentido para variáveis positivas (as quatro métricas do Lab05 são de razão).
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


ALFA = 0.05
# Magnitudes: Cohen (1988) para o g de Hedges e Romano et al. (2006) para o delta de Cliff.
LIMITES_HEDGES = ((0.2, "negligível"), (0.5, "pequeno"), (0.8, "médio"))
LIMITES_CLIFF = ((0.147, "negligível"), (0.33, "pequeno"), (0.474, "médio"))


def _magnitude(valor: float, limites) -> str:
    if np.isnan(valor):
        return "indefinido"
    for limite, nome in limites:
        if abs(valor) < limite:
            return nome
    return "grande"


def magnitude_hedges(g: float) -> str:
    """`negligível` (|g| < 0,2), `pequeno` (< 0,5), `médio` (< 0,8) ou `grande`; `indefinido` se NaN."""
    return _magnitude(g, LIMITES_HEDGES)


def magnitude_cliff(delta: float) -> str:
    """`negligível` (|δ| < 0,147), `pequeno` (< 0,33), `médio` (< 0,474) ou `grande`; `indefinido` se NaN."""
    return _magnitude(delta, LIMITES_CLIFF)


# ---------------------------------------------------------------------------------------------
# Novo no Lab05 (plano de análise, seções 5 e 6)
# ---------------------------------------------------------------------------------------------

GRUPO_A, GRUPO_B = "valkey", "redis"
TESTES = {"welch": "welch_p", "mann_whitney": "mw_p"}  # nome do teste -> chave de `aplicar_testes`
DIFERENCA_RELEVANTE = 0.05  # razão de medianas fora de [0,95; 1,05] (plano, seção 6)
N_BOOTSTRAP = 10_000
CONFIANCA = 0.95
SEMENTE_PADRAO = 42  # a mesma de `config.yaml`; a linha de comando passa o gerador do config
LIMITE_ASSIMETRIA = 1.0  # regra 5.1: Welch só com assimetria entre −1 e 1
SITUACOES = ("diferença relevante", "diferença pequena demais", "equivalência prática", "inconclusivo")
COLUNAS_COMPARACAO = [
    "metrica", "io_threads", "carga", "n_valkey", "n_redis", "mediana_valkey", "mediana_redis",
    "razao_medianas", "ic_inf", "ic_sup", "teste_principal", "p_principal", "p_holm", "rejeita_h0",
    "teste_sensibilidade", "p_sensibilidade", "testes_discordam", "situacao", "deterministica",
    "welch_t", "welch_gl", "welch_p", "mw_u", "mw_p", "mw_metodo", "hedges_g", "magnitude_hedges",
    "cliff_delta", "magnitude_cliff", "razao_desvios", "levene_p",
]


def holm(p) -> np.ndarray:
    """p-valores ajustados por Holm-Bonferroni, ao longo do último eixo.

    Aceita um vetor (uma família) ou uma matriz `(n_rep, m)` (uma família por linha, como na
    simulação de poder). Ordena os m p-valores, multiplica o i-ésimo menor (i = 0, 1, ...) por
    m − i, impõe que os ajustados não diminuam nessa ordem e limita a 1. Um p-valor NaN (por
    exemplo, o Welch com variância zero) continua NaN e não conta em m.
    """
    p = np.asarray(p, dtype=float)
    if p.ndim not in (1, 2):
        raise ValueError("p deve ser um vetor ou uma matriz")
    linhas = np.atleast_2d(p)
    ordem = np.argsort(linhas, axis=1)  # os NaN ficam no fim
    ordenados = np.take_along_axis(linhas, ordem, axis=1)
    m = (~np.isnan(linhas)).sum(axis=1, keepdims=True)
    fatores = m - np.arange(linhas.shape[1])[None, :]
    ajustados = np.minimum(np.fmax.accumulate(ordenados * fatores, axis=1), 1.0)
    ajustados[np.isnan(ordenados)] = np.nan
    saida = np.empty_like(ajustados)
    np.put_along_axis(saida, ordem, ajustados, axis=1)
    return saida[0] if p.ndim == 1 else saida


def ic_razao_bootstrap(a, b, rng=None, n_boot: int = N_BOOTSTRAP, confianca: float = CONFIANCA) -> tuple:
    """IC da razão de medianas `a ÷ b` por *bootstrap* percentil.

    Reamostra com reposição **dentro de cada grupo** (as amostras são independentes), `n_boot`
    vezes, e devolve os percentis (1 − confianca)/2 e (1 + confianca)/2 das razões. Sem `rng`, usa
    `default_rng(SEMENTE_PADRAO)`. Reamostras com mediana de `b` igual a zero dão NaN e são
    ignoradas; se todas derem, o IC é `(NaN, NaN)`.
    """
    a, b = _como_array(a, "a", 1), _como_array(b, "b", 1)
    rng = np.random.default_rng(SEMENTE_PADRAO) if rng is None else rng
    medianas_a = np.median(a[rng.integers(0, len(a), (n_boot, len(a)))], axis=1)
    medianas_b = np.median(b[rng.integers(0, len(b), (n_boot, len(b)))], axis=1)
    with np.errstate(divide="ignore", invalid="ignore"):
        razoes = np.where(medianas_b != 0, medianas_a / medianas_b, np.nan)
    razoes = razoes[~np.isnan(razoes)]
    if len(razoes) == 0:
        return float("nan"), float("nan")
    inf, sup = np.percentile(razoes, [100 * (1 - confianca) / 2, 100 * (1 + confianca) / 2])
    return float(inf), float(sup)


def _conferir_colunas(df: pd.DataFrame, metrica: str) -> None:
    faltam = {"servidor", "io_threads", "carga", metrica} - set(df.columns)
    if faltam:
        raise ValueError(f"faltam as colunas {sorted(faltam)}")


def residuos(df: pd.DataFrame, metrica: str) -> np.ndarray:
    """Cada observação menos a mediana da sua combinação (servidor × `io_threads` × carga)."""
    _conferir_colunas(df, metrica)
    valores = pd.to_numeric(df[metrica], errors="coerce")
    medianas = valores.groupby([df["servidor"], df["io_threads"], df["carga"]]).transform("median")
    return (valores - medianas).dropna().to_numpy(dtype=float)


def escolher_teste(df: pd.DataFrame, metrica: str, alfa: float = ALFA) -> dict:
    """Regra 5.1 do plano: o teste principal de uma métrica, decidido uma vez no piloto.

    Junta os resíduos de todas as combinações (`residuos`). O principal é o Welch se o
    Shapiro-Wilk não rejeita a normalidade (p ≥ `alfa`) **e** a assimetria está entre −1 e 1;
    senão, o Mann-Whitney. O terceiro critério da regra (histograma e gráfico quantil-quantil sem
    bimodalidade) é visual e fica no documento da análise do piloto: se ele mostrar bimodalidade,
    o grupo troca para o Mann-Whitney ao registrar a decisão.

    Devolve `teste` (`welch` ou `mann_whitney`), `shapiro_p`, `assimetria`, `n_residuos` e
    `motivo`. Resíduos todos iguais (métrica sem variação) dão `mann_whitney` com
    `shapiro_p` NaN. Levanta `ValueError` com menos de 3 resíduos.
    """
    r = residuos(df, metrica)
    if len(r) < 3:
        raise ValueError("a regra 5.1 precisa de ao menos 3 resíduos")
    if np.ptp(r) == 0:
        return {"teste": "mann_whitney", "shapiro_p": float("nan"), "assimetria": float("nan"),
                "n_residuos": len(r), "motivo": "resíduos sem variação"}  # fmt: skip
    shapiro_p = float(stats.shapiro(r).pvalue)
    assimetria = float(stats.skew(r, bias=False))
    normal = shapiro_p >= alfa
    simetrica = abs(assimetria) <= LIMITE_ASSIMETRIA
    if normal and simetrica:
        teste, motivo = "welch", "Shapiro-Wilk não rejeita a normalidade e |assimetria| ≤ 1"
    else:
        partes = ([] if normal else [f"Shapiro-Wilk rejeita a normalidade (p < {alfa:g})".replace(".", ",")]) + (
            [] if simetrica else ["|assimetria| > 1"]
        )
        teste, motivo = "mann_whitney", "; ".join(partes)
    return {"teste": teste, "shapiro_p": shapiro_p, "assimetria": assimetria, "n_residuos": len(r), "motivo": motivo}


def situacao(p_ajustado: float, ic_inf: float, ic_sup: float, diferenca: float = DIFERENCA_RELEVANTE, alfa: float = ALFA) -> str:
    """Uma das quatro situações da seção 6 do plano, pelo p de Holm e pelo IC da razão de medianas.

    Faixa de equivalência: [1 − `diferenca`; 1 + `diferenca`]. Na ordem da tabela do plano:
    relevante (p < α e IC inteiro fora da faixa), pequena demais (p < α e IC inteiro dentro),
    equivalência prática (IC inteiro dentro, sem significância) e inconclusivo (o resto). p NaN
    conta como não significativo; IC com NaN é inconclusivo.
    """
    if np.isnan(ic_inf) or np.isnan(ic_sup):
        return "inconclusivo"
    baixo, alto = 1 - diferenca, 1 + diferenca
    significativo = not np.isnan(p_ajustado) and p_ajustado < alfa
    fora = ic_inf > alto or ic_sup < baixo
    dentro = baixo <= ic_inf and ic_sup <= alto
    if significativo and fora:
        return "diferença relevante"
    if dentro:
        return "diferença pequena demais" if significativo else "equivalência prática"
    return "inconclusivo"


def _situacao_deterministica(razao: float, diferenca: float) -> str:
    """Variância zero nos dois grupos: a decisão usa a razão observada (plano, seção 5.2)."""
    if np.isnan(razao):
        return "inconclusivo"
    return "diferença relevante" if abs(razao - 1) >= diferenca else "equivalência prática"


def _valores(df: pd.DataFrame, metrica: str, servidor: str) -> np.ndarray:
    return pd.to_numeric(df.loc[df["servidor"] == servidor, metrica], errors="coerce").dropna().to_numpy(dtype=float)


def comparar(
    df: pd.DataFrame,
    metrica: str,
    teste_principal: str | None = None,
    rng=None,
    n_boot: int = N_BOOTSTRAP,
    diferenca: float = DIFERENCA_RELEVANTE,
    alfa: float = ALFA,
) -> pd.DataFrame:
    """As comparações Valkey × Redis de uma métrica: uma linha por (`io_threads`, carga).

    Em cada combinação aplica os dois testes (`aplicar_testes`, `a` = valkey, `b` = redis), o
    IC da razão de medianas por *bootstrap* e o teste de Levene (centro na mediana), com a razão
    entre os desvios-padrão. O `teste_principal` (`welch` ou `mann_whitney`; sem ele, o de
    `escolher_teste` sobre o próprio `df`) é o único corrigido por Holm, dentro da família formada
    pelas linhas da tabela; o outro é a análise de sensibilidade, sem correção. `testes_discordam`
    marca as linhas em que os dois testes, ambos sem correção, tomam decisões diferentes em `alfa`.

    Com variância zero nos dois grupos a linha é `deterministica`: a situação vem da razão
    observada, sem teste (o p do Welch é NaN e não entra em Holm).

    `rng` é usado no *bootstrap*, na ordem das linhas (sem ele, `default_rng(SEMENTE_PADRAO)`).
    Colunas de `COLUNAS_COMPARACAO`. Levanta `ValueError` se faltam colunas, se o teste é
    desconhecido ou se um servidor tem menos de 2 execuções numa combinação.
    """
    _conferir_colunas(df, metrica)
    if teste_principal is None:
        teste_principal = escolher_teste(df, metrica, alfa)["teste"]
    if teste_principal not in TESTES:
        raise ValueError(f"teste '{teste_principal}' desconhecido; use {' ou '.join(TESTES)}")
    sensibilidade = next(t for t in TESTES if t != teste_principal)
    rng = np.random.default_rng(SEMENTE_PADRAO) if rng is None else rng
    linhas = []
    for (threads, carga), grupo in df.groupby(["io_threads", "carga"], sort=True):
        a, b = _valores(grupo, metrica, GRUPO_A), _valores(grupo, metrica, GRUPO_B)
        if len(a) < 2 or len(b) < 2:
            raise ValueError(f"io_threads {threads}, carga {carga}: cada servidor precisa de ao menos 2 execuções")
        r = aplicar_testes(a, b)
        deterministica = bool(a.var() == 0 and b.var() == 0)
        ic_inf, ic_sup = ic_razao_bootstrap(a, b, rng, n_boot)
        desvio_b = b.std(ddof=1)
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            levene_p = float(stats.levene(a, b, center="median").pvalue)
        linhas.append({
            "metrica": metrica, "io_threads": threads, "carga": carga, "n_valkey": len(a), "n_redis": len(b),
            "mediana_valkey": float(np.median(a)), "mediana_redis": float(np.median(b)),
            "razao_medianas": r["razao_medianas"], "ic_inf": ic_inf, "ic_sup": ic_sup,
            "teste_principal": teste_principal, "p_principal": float("nan") if deterministica else r[TESTES[teste_principal]],
            "teste_sensibilidade": sensibilidade, "p_sensibilidade": r[TESTES[sensibilidade]],
            "deterministica": deterministica, **r,
            "magnitude_hedges": magnitude_hedges(r["hedges_g"]), "magnitude_cliff": magnitude_cliff(r["cliff_delta"]),
            "razao_desvios": float(a.std(ddof=1) / desvio_b) if desvio_b > 0 else float("nan"), "levene_p": levene_p,
        })  # fmt: skip
    tabela = pd.DataFrame(linhas)
    tabela["p_holm"] = holm(tabela["p_principal"].to_numpy())
    tabela["rejeita_h0"] = tabela["p_holm"] < alfa
    decide = tabela["p_principal"] < alfa
    tabela["testes_discordam"] = ~tabela["deterministica"] & (decide != (tabela["p_sensibilidade"] < alfa))
    tabela["situacao"] = [
        _situacao_deterministica(l.razao_medianas, diferenca) if l.deterministica else situacao(l.p_holm, l.ic_inf, l.ic_sup, diferenca, alfa)
        for l in tabela.itertuples()
    ]
    return tabela[COLUNAS_COMPARACAO]
