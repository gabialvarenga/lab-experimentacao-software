"""Análise pareada por bloco: Valkey × Redis dentro de cada repetição (S02-01, adendo de 23/11/2026).

**Análise de sensibilidade** das Q1, Q2 e Q4 (decisão do grupo no adendo de 23/11/2026, seção 9
de `docs/plano-analise.md`): o teste principal continua o Mann-Whitney de `testes.comparar`
(adendo de 19/11/2026). Cada repetição é um bloco com as 12 combinações em ordem sorteada; a
deriva da máquina entre blocos atinge os dois servidores do mesmo bloco, e a razão dentro do bloco
a cancela.

Por métrica e por (`io_threads`, carga):

- **Pares:** a execução do Valkey e a do Redis da mesma repetição. A razão do par é valkey ÷ redis.
- **Bloco incompleto:** o par **sai** se uma das duas execuções aparece em `falhas.csv` (a
  execução falhou e foi refeita depois, fora do horário do bloco, sem a deriva dele) ou se falta
  uma das duas. A execução continua na análise independente. `n_excluidos` conta os pares que
  saíram.
- **Teste:** Wilcoxon pareado (postos sinalizados) bicaudal no log das razões, pelo
  `scipy.stats.wilcoxon` (exato até 50 pares sem empates; senão, aproximação normal), com os
  zeros descartados (`zero_method="wilcox"`, o padrão do SciPy).
- **Efeito:** estimador de Hodges-Lehmann (mediana das médias de Walsh do log das razões), com o
  IC exato pela distribuição do Wilcoxon, voltado à escala de razão por exp. Com poucos pares, a
  cobertura de 95% não é atingível (com 5 pares, o máximo é 93,75%): o IC usa então o intervalo
  mais largo possível e `cobertura_ic` diz a cobertura real.
- **Holm** sobre as 6 comparações de cada métrica, como em `testes.comparar`; a situação da
  seção 6 do plano usa o p de Holm e o IC de Hodges-Lehmann.

Com o log das razões constante (por exemplo, a memória sem variação), a linha é `deterministica`:
a situação vem da razão observada, sem teste, como em `testes.comparar`.
"""

from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from lab05 import testes

COLUNAS = [
    "metrica", "io_threads", "carga", "n_pares", "n_excluidos", "razao_hl", "ic_inf", "ic_sup",
    "cobertura_ic", "desvio_log_razao", "wilcoxon_w", "p_wilcoxon", "p_holm", "deterministica",
    "situacao", "situacao_principal", "concorda",
]  # fmt: skip


def ler_refeitas(caminho) -> set:
    """Os `execucao_id` de `falhas.csv` (execuções que falharam e foram refeitas); vazio sem o arquivo."""
    caminho = Path(caminho)
    if not caminho.exists():
        return set()
    return set(pd.read_csv(caminho, usecols=["execucao_id"])["execucao_id"].astype(str))


def formar_pares(df: pd.DataFrame, metrica: str, refeitas=frozenset()) -> pd.DataFrame:
    """Um par por (`io_threads`, carga, repetição): colunas `valkey`, `redis` e `excluido`.

    `excluido` é verdadeiro se falta uma das execuções ou se uma delas está em `refeitas`.
    Levanta `ValueError` se faltam colunas (`execucao_id` só é exigida com `refeitas`) ou se um
    servidor tem mais de uma execução na mesma repetição.
    """
    faltam = {"servidor", "io_threads", "carga", "repeticao", metrica} - set(df.columns)
    if refeitas and "execucao_id" not in df.columns:
        faltam.add("execucao_id")
    if faltam:
        raise ValueError(f"faltam as colunas {sorted(faltam)}")
    chaves = ["io_threads", "carga", "repeticao"]
    if df.duplicated([*chaves, "servidor"]).any():
        raise ValueError("um servidor tem mais de uma execução na mesma repetição")
    dados = df.assign(_valor=pd.to_numeric(df[metrica], errors="coerce"))
    dados["_refeita"] = dados["execucao_id"].astype(str).isin(refeitas) if refeitas else False
    valores = dados.pivot(index=chaves, columns="servidor", values="_valor")
    refeita = dados.pivot(index=chaves, columns="servidor", values="_refeita").fillna(False).astype(bool)
    for servidor in (testes.GRUPO_A, testes.GRUPO_B):
        if servidor not in valores:
            valores[servidor] = np.nan
            refeita[servidor] = False
    pares = pd.DataFrame({
        "valkey": valores[testes.GRUPO_A], "redis": valores[testes.GRUPO_B],
        "excluido": valores[[testes.GRUPO_A, testes.GRUPO_B]].isna().any(axis=1) | refeita.any(axis=1),
    })  # fmt: skip
    return pares.reset_index()


def _distribuicao_postos_sinalizados(n: int) -> np.ndarray:
    """P(T⁺ = t), t = 0 … n(n+1)/2, sob H0, para n pares sem empates (programação dinâmica)."""
    probs = np.zeros(n * (n + 1) // 2 + 1)
    probs[0] = 1.0
    for k in range(1, n + 1):
        deslocado = np.zeros_like(probs)
        deslocado[k:] = probs[:-k]
        probs = (probs + deslocado) / 2
    return probs


def hodges_lehmann(d, confianca: float = testes.CONFIANCA) -> dict:
    """Estimador de Hodges-Lehmann de uma amostra e o IC exato pelo Wilcoxon.

    Médias de Walsh W (todas as (dᵢ + dⱼ)/2 com i ≤ j, M = n(n+1)/2 delas, ordenadas); a
    estimativa é a mediana delas. O IC é [W₍c+1₎; W₍M−c₎], com c o maior inteiro tal que
    2·P(T⁺ ≤ c) ≤ 1 − `confianca`; a cobertura é 1 − 2·P(T⁺ ≤ c). Se nem c = 0 basta, usa c = 0
    (o intervalo mais largo) e a cobertura fica abaixo de `confianca`. Devolve `estimativa`,
    `ic_inf`, `ic_sup` e `cobertura`.
    """
    d = testes._como_array(d, "d", 1)
    n = len(d)
    i, j = np.triu_indices(n)
    walsh = np.sort((d[i] + d[j]) / 2)
    acumulada = np.cumsum(_distribuicao_postos_sinalizados(n))
    cabem = np.flatnonzero(2 * acumulada <= 1 - confianca + 1e-12)
    c = int(cabem[-1]) if len(cabem) else 0
    return {
        "estimativa": float(np.median(walsh)),
        "ic_inf": float(walsh[c]),
        "ic_sup": float(walsh[len(walsh) - 1 - c]),
        "cobertura": float(1 - 2 * acumulada[c]),
    }


def comparar(
    df: pd.DataFrame,
    metrica: str,
    refeitas=frozenset(),
    principal: pd.DataFrame | None = None,
    diferenca: float = testes.DIFERENCA_RELEVANTE,
    alfa: float = testes.ALFA,
    confianca: float = testes.CONFIANCA,
) -> pd.DataFrame:
    """As comparações pareadas de uma métrica: uma linha por (`io_threads`, carga), colunas de `COLUNAS`.

    `principal` é a tabela de `testes.comparar` (colunas `metrica`, `io_threads`, `carga` e
    `situacao`): dela vêm `situacao_principal` e `concorda` (as duas situações iguais). Sem ela,
    as duas colunas ficam vazias. Levanta `ValueError` se uma combinação tem menos de 2 pares.
    """
    pares = formar_pares(df, metrica, refeitas)
    if ((pares["valkey"] <= 0) | (pares["redis"] <= 0)).any():
        raise ValueError(f"{metrica}: o log exige valores positivos")
    linhas = []
    for (threads, carga), grupo in pares.groupby(["io_threads", "carga"], sort=True):
        validos = grupo[~grupo["excluido"]]
        if len(validos) < 2:
            raise ValueError(f"io_threads {threads}, carga {carga}: a análise pareada precisa de ao menos 2 pares")
        d = np.log(validos["valkey"].to_numpy(dtype=float) / validos["redis"].to_numpy(dtype=float))
        hl = hodges_lehmann(d, confianca)
        deterministica = bool(np.ptp(d) == 0)
        if deterministica or not d.any():
            w, p = float("nan"), float("nan")
        else:
            teste = stats.wilcoxon(d, alternative="two-sided")
            w, p = float(teste.statistic), float(teste.pvalue)
        linhas.append({
            "metrica": metrica, "io_threads": threads, "carga": carga, "n_pares": len(validos),
            "n_excluidos": int(grupo["excluido"].sum()), "razao_hl": float(np.exp(hl["estimativa"])),
            "ic_inf": float(np.exp(hl["ic_inf"])), "ic_sup": float(np.exp(hl["ic_sup"])), "cobertura_ic": hl["cobertura"],
            "desvio_log_razao": float(np.std(d, ddof=1)), "wilcoxon_w": w, "p_wilcoxon": p, "deterministica": deterministica,
        })  # fmt: skip
    tabela = pd.DataFrame(linhas)
    tabela["p_holm"] = testes.holm(tabela["p_wilcoxon"].to_numpy())
    tabela["situacao"] = [
        testes._situacao_deterministica(l.razao_hl, diferenca) if l.deterministica
        else testes.situacao(l.p_holm, l.ic_inf, l.ic_sup, diferenca, alfa)
        for l in tabela.itertuples()
    ]  # fmt: skip
    if principal is None:
        tabela["situacao_principal"], tabela["concorda"] = None, None
    else:
        referencia = principal[["metrica", "io_threads", "carga", "situacao"]].rename(columns={"situacao": "situacao_principal"})
        tabela = tabela.merge(referencia, on=["metrica", "io_threads", "carga"], how="left")
        tabela["concorda"] = tabela["situacao"] == tabela["situacao_principal"]
    return tabela[COLUNAS]
