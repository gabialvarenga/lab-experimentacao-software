"""Poder e número de repetições por simulação, com a variabilidade observada no piloto (S01-09).

Origem: o motor de simulação do Lab04, copiado (e não importado: cada laboratório roda sozinho):

- `intervalo_wilson` e `gerador_da_celula` vêm de `lab04/lab04/simulacao.py`. O gerador aceita
  aqui qualquer chave inteira, e não só a posição (cenário, efeito) da grade do Lab04;
- `gerar_lote` é o ramo lognormal de `lab04/lab04/gerador.py`, com o efeito expresso como
  diferença relativa entre as medianas (`diferenca` = 0,05 é Valkey 5% acima do Redis), sem a
  contaminação (o piloto não pediu esse cenário);
- `estimar_sigmas` usa a mesma regra de `cenario_calibrado` do Lab04 para juntar os dois grupos
  num σ só: a raiz da média das variâncias de log(métrica) de cada servidor.

O que é novo: a simulação é de uma **família** inteira de comparações (as 6 combinações de
`io_threads` e carga de uma pergunta), com a correção de Holm aplicada a cada repetição simulada,
como na análise (plano de análise, seção 6). Cada comparação tem o σ da sua combinação.

Cenários de Holm (`cenario`):

- `conservador` (padrão, escolhido no planejamento da S01-09): só a comparação avaliada tem a
  diferença, e as outras 5 não têm efeito. É o pior caso de Holm: a comparação precisa vencer o
  limiar α/6 sozinha;
- `todas`: as 6 comparações têm a diferença. Holm fica mais brando (cada rejeição libera a
  seguinte); serve como sensibilidade.

O poder de uma métrica num `n` é o **menor** entre os das 6 comparações: o número de repetições
precisa bastar para a combinação mais ruidosa.

Uma combinação com σ = 0 (os dois servidores sem variação, como pode acontecer com a memória) é
determinística: não entra em Holm e conta como detectada sempre que `diferenca` > 0 (plano,
seção 5.2, "Variância zero").
"""

import numpy as np
import pandas as pd
from scipy import stats

from lab05 import descritiva, testes

GRADE_N = (5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 100, 120, 150, 200, 250, 300)
N_SIMULACOES = 2000  # repetições simuladas por ponto; margem de Wilson de ±1,8 p.p. em torno de 80%
PODER_ALVO = 0.80
CONFIANCA = 0.95
CENARIOS = ("conservador", "todas")
SEMENTE_PADRAO = testes.SEMENTE_PADRAO
COLUNAS_CURVA = [
    "metrica", "teste", "cenario", "n", "diferenca", "io_threads", "carga", "sigma_log",
    "n_rep", "rejeicoes", "poder", "ic_inf", "ic_sup",
]
COLUNAS_REPETICOES = [
    "metrica", "teste", "cenario", "diferenca", "poder_alvo", "sigma_log_max", "n_necessario",
    "poder_no_n", "acima_da_grade", "limitante",
]

# ---------------------------------------------------------------------------------------------
# Adaptado de lab04/lab04/simulacao.py e lab04/lab04/gerador.py
# ---------------------------------------------------------------------------------------------


def intervalo_wilson(rejeicoes: int, n: int, confianca: float = CONFIANCA) -> tuple:
    """Intervalo de Wilson para a proporção `rejeicoes / n`, no nível `confianca`."""
    if n < 1 or not 0 <= rejeicoes <= n:
        raise ValueError("precisa de n ≥ 1 e 0 ≤ rejeicoes ≤ n")
    z = stats.norm.ppf(1 - (1 - confianca) / 2)
    p = rejeicoes / n
    centro = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    meia = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    # com 0 ou n rejeições um dos limites é exatamente 0 ou 1; a conta em ponto flutuante erra por ~1e-16
    inf = 0.0 if rejeicoes == 0 else max(centro - meia, 0.0)
    sup = 1.0 if rejeicoes == n else min(centro + meia, 1.0)
    return float(inf), float(sup)


def gerador_da_celula(semente: int, *chave: int) -> np.random.Generator:
    """Gerador próprio de um ponto da simulação: `SeedSequence(semente, spawn_key=chave)`.

    A chave só depende do ponto (métrica, n, diferença), e não da ordem em que os pontos rodam:
    rodar uma grade menor dá os mesmos números nos pontos que ela tem em comum com a maior.
    """
    return np.random.default_rng(np.random.SeedSequence(semente, spawn_key=tuple(int(c) for c in chave)))


def gerar_lote(sigma: float, diferenca: float, n: int, n_rep: int, rng) -> tuple:
    """`n_rep` pares de amostras lognormais de tamanho `n`: `(A, B)`, cada um `(n_rep, n)`.

    B (Redis) tem mediana 1 e A (Valkey) tem mediana `1 + diferenca`; os dois com o mesmo σ de
    log. A escala não importa: os testes e a razão de medianas não mudam se tudo for multiplicado
    por uma constante. Ordem dos sorteios fixa: primeiro A, depois B.
    """
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng deve ser um numpy.random.Generator")
    if not np.isfinite(sigma) or sigma < 0:
        raise ValueError("sigma deve ser um número finito e não negativo")
    if not np.isfinite(diferenca) or diferenca <= -1:
        raise ValueError("diferenca deve ser finita e maior que −1")
    for valor, nome in ((n, "n"), (n_rep, "n_rep")):
        if isinstance(valor, bool) or not isinstance(valor, (int, np.integer)) or valor < 1:
            raise ValueError(f"{nome} deve ser um inteiro positivo")
    a = np.exp(np.log1p(diferenca) + sigma * rng.standard_normal((n_rep, n)))
    b = np.exp(sigma * rng.standard_normal((n_rep, n)))
    return a, b


def estimar_sigmas(df: pd.DataFrame, metrica: str) -> pd.DataFrame:
    """σ de log(métrica) por (`io_threads`, carga), juntando os dois servidores.

    σ = raiz da média das variâncias amostrais (ddof = 1) de log(métrica) de cada servidor (a
    regra de `cenario_calibrado` do Lab04). Colunas: `io_threads`, `carga`, `sigma_log`,
    `n_valkey`, `n_redis`. Levanta `ValueError` se a métrica tem valor não positivo ou se um
    servidor tem menos de 2 execuções numa combinação.
    """
    faltam = {"servidor", "io_threads", "carga", metrica} - set(df.columns)
    if faltam:
        raise ValueError(f"faltam as colunas {sorted(faltam)}")
    valores = pd.to_numeric(df[metrica], errors="coerce")
    if (valores.dropna() <= 0).any():
        raise ValueError(f"{metrica}: o log exige valores positivos")
    linhas = []
    for (threads, carga), grupo in df.assign(_log=np.log(valores)).dropna(subset=["_log"]).groupby(["io_threads", "carga"], sort=True):
        por_servidor = {s: grupo.loc[grupo["servidor"] == s, "_log"] for s in (testes.GRUPO_A, testes.GRUPO_B)}
        if min(len(v) for v in por_servidor.values()) < 2:
            raise ValueError(f"io_threads {threads}, carga {carga}: cada servidor precisa de ao menos 2 execuções")
        variancia = np.mean([v.var(ddof=1) for v in por_servidor.values()])
        linhas.append({
            "io_threads": threads, "carga": carga, "sigma_log": float(np.sqrt(variancia)),
            "n_valkey": len(por_servidor[testes.GRUPO_A]), "n_redis": len(por_servidor[testes.GRUPO_B]),
        })  # fmt: skip
    return pd.DataFrame(linhas, columns=["io_threads", "carga", "sigma_log", "n_valkey", "n_redis"])


def remover_efeito_bloco(df: pd.DataFrame, metricas=descritiva.METRICAS) -> pd.DataFrame:
    """Cópia do `df` com a deriva entre blocos (repetições) retirada de cada métrica.

    É a conta da investigação dos avisos de CV do piloto (`dados/piloto/LEIA-ME.md`): cada valor
    dividido pela mediana da sua combinação dá o valor relativo; o fator do bloco é a mediana dos
    relativos da repetição; o valor ajustado é o original dividido pelo fator do bloco. Serve só
    como **sensibilidade** do número de repetições: o plano de análise compara amostras
    independentes, sem bloco. Levanta `ValueError` sem a coluna `repeticao`.
    """
    if "repeticao" not in df.columns:
        raise ValueError("falta a coluna 'repeticao'")
    novo = df.copy()
    for metrica in metricas:
        valores = pd.to_numeric(df[metrica], errors="coerce")
        relativos = valores / valores.groupby([df[c] for c in descritiva.CHAVES]).transform("median")
        fator = relativos.groupby(df["repeticao"]).transform("median")
        novo[metrica] = valores / fator
    return novo


# ---------------------------------------------------------------------------------------------
# Novo no Lab05: família com Holm
# ---------------------------------------------------------------------------------------------


def _p_valores(sigmas, diferenca: float, n: int, teste: str, n_rep: int, rng) -> np.ndarray:
    """p-valores `(n_rep, m)` do teste em cada comparação; NaN nas comparações com σ = 0."""
    chave = testes.TESTES[teste]
    p = np.full((n_rep, len(sigmas)), np.nan)
    for j, sigma in enumerate(sigmas):
        A, B = gerar_lote(sigma, diferenca, n, n_rep, rng)
        if sigma > 0:
            p[:, j] = testes.aplicar_testes_vetorizado(A, B)[chave]
    return p


def poder_familia(
    sigmas, n: int, diferenca: float, teste: str, n_rep: int, rng, alfa: float = testes.ALFA, cenario: str = "conservador"
) -> np.ndarray:
    """Rejeições (de `n_rep`) de cada comparação da família, com Holm em cada repetição simulada.

    `sigmas` é o σ de log de cada comparação; `n` é o número de execuções por servidor. Ver os
    cenários no topo do módulo. No `conservador`, os p-valores sem efeito são sorteados uma vez e
    reaproveitados como as "outras" comparações de cada alvo, o que não muda a taxa esperada.
    Devolve um vetor de inteiros, um por comparação.
    """
    if cenario not in CENARIOS:
        raise ValueError(f"cenário '{cenario}' desconhecido; use {' ou '.join(CENARIOS)}")
    if teste not in testes.TESTES:
        raise ValueError(f"teste '{teste}' desconhecido; use {' ou '.join(testes.TESTES)}")
    sigmas = np.asarray(sigmas, dtype=float)
    deterministicas = sigmas == 0
    com_efeito = _p_valores(sigmas, diferenca, n, teste, n_rep, rng)
    if cenario == "todas":
        rejeita = testes.holm(com_efeito) < alfa
    else:
        sem_efeito = _p_valores(sigmas, 0.0, n, teste, n_rep, rng)
        rejeita = np.zeros_like(com_efeito, dtype=bool)
        for k in range(len(sigmas)):
            familia = sem_efeito.copy()
            familia[:, k] = com_efeito[:, k]
            rejeita[:, k] = testes.holm(familia)[:, k] < alfa
    rejeita[:, deterministicas] = diferenca != 0
    return rejeita.sum(axis=0).astype(int)


def _chave_diferenca(diferenca: float) -> int:
    return int(round(abs(diferenca) * 10_000)) * 2 + (diferenca < 0)


def curva_poder(
    df: pd.DataFrame,
    metrica: str,
    ns=GRADE_N,
    diferencas=(testes.DIFERENCA_RELEVANTE,),
    teste: str | None = None,
    n_rep: int = N_SIMULACOES,
    alfa: float = testes.ALFA,
    cenario: str = "conservador",
    semente: int = SEMENTE_PADRAO,
) -> pd.DataFrame:
    """Poder de cada comparação da família, para cada `n` e cada `diferenca`: tabela longa.

    `teste` padrão: o principal da métrica pela regra 5.1 (`testes.escolher_teste` sobre o `df`).
    Cada ponto (n, diferença) tem o seu gerador (`gerador_da_celula`), com a chave (posição da
    métrica em `descritiva.METRICAS`, n, diferença). Colunas de `COLUNAS_CURVA`; `ic_inf` e
    `ic_sup` são o intervalo de Wilson de 95% do poder.
    """
    sigmas = estimar_sigmas(df, metrica)
    teste = testes.escolher_teste(df, metrica, alfa)["teste"] if teste is None else teste
    indice = descritiva.METRICAS.index(metrica) if metrica in descritiva.METRICAS else len(descritiva.METRICAS)
    linhas = []
    for n in ns:
        for diferenca in diferencas:
            rng = gerador_da_celula(semente, indice, n, _chave_diferenca(diferenca))
            rejeicoes = poder_familia(sigmas["sigma_log"], n, diferenca, teste, n_rep, rng, alfa, cenario)
            for comparacao, quantas in zip(sigmas.itertuples(), rejeicoes):
                inf, sup = intervalo_wilson(int(quantas), n_rep)
                linhas.append({
                    "metrica": metrica, "teste": teste, "cenario": cenario, "n": n, "diferenca": diferenca,
                    "io_threads": comparacao.io_threads, "carga": comparacao.carga, "sigma_log": comparacao.sigma_log,
                    "n_rep": n_rep, "rejeicoes": int(quantas), "poder": quantas / n_rep, "ic_inf": inf, "ic_sup": sup,
                })  # fmt: skip
    return pd.DataFrame(linhas, columns=COLUNAS_CURVA)


def _pior_por_ponto(curva: pd.DataFrame) -> pd.DataFrame:
    """A comparação de menor poder em cada (métrica, n, diferença)."""
    indices = curva.groupby(["metrica", "n", "diferenca"], sort=True)["poder"].idxmin()
    return curva.loc[indices].reset_index(drop=True)


def repeticoes_necessarias(
    df: pd.DataFrame,
    diferenca: float = testes.DIFERENCA_RELEVANTE,
    poder: float = PODER_ALVO,
    metricas=None,
    testes_principais: dict | None = None,
    grade=GRADE_N,
    n_rep: int = N_SIMULACOES,
    alfa: float = testes.ALFA,
    cenario: str = "conservador",
    semente: int = SEMENTE_PADRAO,
) -> pd.DataFrame:
    """Menor n da `grade` com poder ≥ `poder` nas 6 comparações de cada métrica, para `diferenca`.

    `metricas` padrão: as de `descritiva.METRICAS`. `testes_principais` (métrica -> teste) troca
    a regra 5.1. Colunas de `COLUNAS_REPETICOES`: o maior σ de log da métrica, `n_necessario`
    (NaN se nem o maior n da grade basta, com `acima_da_grade` verdadeiro), o poder da comparação
    limitante nesse n (ou no maior da grade) e qual comparação é a limitante. A curva completa
    fica em `tabela.attrs["curva"]` (colunas de `COLUNAS_CURVA`).
    """
    metricas = list(descritiva.METRICAS if metricas is None else metricas)
    testes_principais = testes_principais or {}
    curvas, linhas = [], []
    for metrica in metricas:
        curva = curva_poder(df, metrica, grade, (diferenca,), testes_principais.get(metrica), n_rep, alfa, cenario, semente)
        curvas.append(curva)
        pior = _pior_por_ponto(curva).sort_values("n")
        bastam = pior[pior["poder"] >= poder]
        linha = bastam.iloc[0] if len(bastam) else pior.iloc[-1]
        linhas.append({
            "metrica": metrica, "teste": curva["teste"].iloc[0], "cenario": cenario, "diferenca": diferenca,
            "poder_alvo": poder, "sigma_log_max": float(curva["sigma_log"].max()),
            "n_necessario": int(linha["n"]) if len(bastam) else np.nan, "poder_no_n": float(linha["poder"]),
            "acima_da_grade": not len(bastam), "limitante": f"io_threads {linha['io_threads']}, {linha['carga']}",
        })  # fmt: skip
    tabela = pd.DataFrame(linhas, columns=COLUNAS_REPETICOES)
    tabela.attrs["curva"] = pd.concat(curvas, ignore_index=True)
    return tabela


def diferenca_detectavel(curva: pd.DataFrame, poder: float = PODER_ALVO) -> pd.DataFrame:
    """Menor diferença da curva com poder ≥ `poder` nas 6 comparações, por (métrica, n).

    `curva` é a saída de `curva_poder` com várias diferenças. Colunas: `metrica`, `n`,
    `diferenca_detectavel` (NaN se nenhuma diferença da curva basta) e `poder_no_ponto`.
    """
    pior = _pior_por_ponto(curva)
    linhas = []
    for (metrica, n), grupo in pior.groupby(["metrica", "n"], sort=True):
        bastam = grupo[grupo["poder"] >= poder].sort_values("diferenca")
        linhas.append({
            "metrica": metrica, "n": n,
            "diferenca_detectavel": float(bastam["diferenca"].iloc[0]) if len(bastam) else np.nan,
            "poder_no_ponto": float(bastam["poder"].iloc[0]) if len(bastam) else np.nan,
        })  # fmt: skip
    return pd.DataFrame(linhas, columns=["metrica", "n", "diferenca_detectavel", "poder_no_ponto"])
