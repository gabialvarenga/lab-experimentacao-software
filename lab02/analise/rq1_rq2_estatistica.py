from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

RAIZ_LAB02 = Path(__file__).resolve().parent.parent
DIR_DADOS = RAIZ_LAB02 / "dados"
DIR_GRAFICOS = Path(__file__).resolve().parent / "graficos"

TRATAMENTOS = ("com-ia", "sem-ia")
SEED_BOOTSTRAP = 42
N_RESAMPLES_BOOTSTRAP = 10_000


# --------------------------------------------------------------------------
# Funções puras (cobertas por tests/test_rq1_rq2_estatistica.py)
# --------------------------------------------------------------------------

def carregar_dados(dir_dados: Path = DIR_DADOS) -> pd.DataFrame:
    """Junta trials.csv + contagem-testes.csv por integrante/kata/tratamento."""
    trials = pd.read_csv(dir_dados / "trials.csv")
    contagem = pd.read_csv(dir_dados / "contagem-testes.csv")
    return trials.merge(
        contagem, on=["integrante", "kata", "tratamento"], how="left"
    )


def resumo_descritivo(valores: pd.Series) -> dict:
    """Mediana, Q1, Q3 e IQR — não média/desvio, N pequeno (convenção do Lab02)."""
    q1, mediana, q3 = valores.quantile([0.25, 0.5, 0.75])
    return {"mediana": mediana, "q1": q1, "q3": q3, "iqr": q3 - q1}


def identificar_outliers(valores: pd.Series) -> list[float]:
    """Regra do IQR (1.5x), mesma convenção do lab01/analise/*.py."""
    q1, q3 = valores.quantile([0.25, 0.75])
    iqr = q3 - q1
    limite_inf, limite_sup = q1 - 1.5 * iqr, q3 + 1.5 * iqr
    return sorted(v for v in valores if v < limite_inf or v > limite_sup)


def agregar_mediana_por_integrante(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Uma linha por integrante, com a mediana de `coluna` em cada tratamento.

    É o par formal do Wilcoxon: 'mesmo integrante sob os dois tratamentos'
    (docs/02-hipoteses.md) — como cada um tem 3 trials por tratamento, o par
    é a mediana dessas 3, não um trial isolado.
    """
    return (
        df.groupby(["integrante", "tratamento"])[coluna]
        .median()
        .unstack("tratamento")[list(TRATAMENTOS)]
        .reset_index()
    )


@dataclass
class ResultadoWilcoxon:
    estatistica: float | None
    p_valor: float | None
    n: int
    sem_variancia: bool


def rodar_wilcoxon(
    com_ia: pd.Series, sem_ia: pd.Series, alternative: str
) -> ResultadoWilcoxon:
    """Wilcoxon pareado, tratando o caso de diferenças todas zero.

    Checa a condição diretamente nos dados (em vez de confiar que o scipy
    lança ValueError — em algumas versões/tamanhos de amostra ele não lança,
    só devolve p=1.0 com um RuntimeWarning de divisão inválida por baixo dos
    panos, o que mascararia o achado em vez de reportá-lo). Caso real de
    RQ2 nesta amostra: taxa_sucesso=100% para todo mundo, diferença zero.
    """
    n = len(com_ia)
    diferencas = np.asarray(com_ia) - np.asarray(sem_ia)
    if np.all(diferencas == 0):
        return ResultadoWilcoxon(None, None, n, True)
    try:
        estatistica, p_valor = stats.wilcoxon(
            com_ia, sem_ia, alternative=alternative
        )
        return ResultadoWilcoxon(float(estatistica), float(p_valor), n, False)
    except ValueError:
        return ResultadoWilcoxon(None, None, n, True)


def correlacao_rank_biserial(com_ia: pd.Series, sem_ia: pd.Series) -> float | None:
    """Effect size pareado, companion natural do Wilcoxon signed-rank.

    Calculado direto dos postos assinados das diferenças (com_ia - sem_ia):
    r = (W+ - W-) / (W+ + W-). Não depende da convenção interna de qual
    estatística o scipy.stats.wilcoxon devolve — evita ambiguidade entre
    versões/argumentos do scipy.
    """
    diferencas = np.asarray(com_ia) - np.asarray(sem_ia)
    diferencas = diferencas[diferencas != 0]
    if len(diferencas) == 0:
        return None
    postos = stats.rankdata(np.abs(diferencas))
    w_mais = postos[diferencas > 0].sum()
    w_menos = postos[diferencas < 0].sum()
    return (w_mais - w_menos) / (w_mais + w_menos)


def bootstrap_ic_diferenca_mediana(
    com_ia: pd.Series,
    sem_ia: pd.Series,
    n_resamples: int = N_RESAMPLES_BOOTSTRAP,
    seed: int = SEED_BOOTSTRAP,
) -> tuple[float, float]:
    """IC 95% da diferença de mediana (com-ia - sem-ia) via bootstrap.

    Reamostra no nível de trial, independente por grupo (não nos N=3 pares
    agregados) — mais resolução de reamostragem que os 3 pares permitiriam
    sozinhos. Troca "estritamente pareado" por "mais dados", registrado como
    escolha deliberada no relatório, não escondida.
    """
    rng = np.random.default_rng(seed)
    com_ia_arr, sem_ia_arr = np.asarray(com_ia), np.asarray(sem_ia)
    diferencas = np.empty(n_resamples)
    for i in range(n_resamples):
        amostra_com = rng.choice(com_ia_arr, size=len(com_ia_arr), replace=True)
        amostra_sem = rng.choice(sem_ia_arr, size=len(sem_ia_arr), replace=True)
        diferencas[i] = np.median(amostra_com) - np.median(amostra_sem)
    return tuple(np.percentile(diferencas, [2.5, 97.5]))


def proporcao_censura(df: pd.DataFrame) -> dict[str, float]:
    """% de trials censurados por tratamento (ameaça #5, docs/03-ameacas-validade.md)."""
    return (
        df.groupby("tratamento")["censurado"].mean().mul(100).round(1).to_dict()
    )


def densidade_defeitos(dir_dados: Path = DIR_DADOS) -> pd.DataFrame:
    """testes_falhando / KLOC — complementar/opcional, precisa de LOC (RQ3)."""
    df = carregar_dados(dir_dados)
    metricas = pd.read_csv(dir_dados / "metricas-estaticas.csv")
    completo = df.merge(
        metricas[["integrante", "kata", "tratamento", "loc"]],
        on=["integrante", "kata", "tratamento"],
        how="left",
    )
    completo["densidade_defeitos"] = completo["testes_falhando"] / (
        completo["loc"] / 1000
    )
    return completo[["integrante", "kata", "tratamento", "densidade_defeitos"]]


# --------------------------------------------------------------------------
# Gráficos exploratórios (2, pedidos nesta issue — os "oficiais" ficam na #123)
# --------------------------------------------------------------------------

def grafico_prompts_vs_tempo(df: pd.DataFrame, caminho: Path) -> None:
    import matplotlib.pyplot as plt

    com_ia = df[df["tratamento"] == "com-ia"]
    fig, ax = plt.subplots(figsize=(6, 4))
    ax.scatter(com_ia["prompts"], com_ia["tempo_segundos"])
    ax.set_xlabel("nº de prompts")
    ax.set_ylabel("tempo até verde (s)")
    ax.set_title("Prompts x tempo — trials com-ia (exploratório)")
    fig.tight_layout()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho, dpi=150)
    plt.close(fig)


def grafico_tempo_vs_ordem(df: pd.DataFrame, caminho: Path) -> None:
    import matplotlib.pyplot as plt

    fig, ax = plt.subplots(figsize=(6, 4))
    for tratamento, marcador in zip(TRATAMENTOS, ("o", "x")):
        subset = df[df["tratamento"] == tratamento]
        ax.scatter(
            subset["ordem"], subset["tempo_segundos"], marker=marcador, label=tratamento
        )
    coef = np.polyfit(df["ordem"], df["tempo_segundos"], 1)
    xs = np.array([df["ordem"].min(), df["ordem"].max()])
    ax.plot(xs, np.polyval(coef, xs), linestyle="--", color="gray")
    ax.set_xlabel("ordem na sequência do integrante")
    ax.set_ylabel("tempo até verde (s)")
    ax.set_title("Tempo x ordem — efeito de aprendizado (exploratório)")
    ax.legend()
    fig.tight_layout()
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.savefig(caminho, dpi=150)
    plt.close(fig)


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def main() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")  # acentos no console do Windows
        except Exception:
            pass

    df = carregar_dados()

    print("=" * 70)
    print("RQ1 — Tempo (tempo_segundos)")
    print("=" * 70)
    for tratamento in TRATAMENTOS:
        r = resumo_descritivo(df[df["tratamento"] == tratamento]["tempo_segundos"])
        print(f"  {tratamento}: mediana={r['mediana']:.1f}s  IQR=[{r['q1']:.1f}, {r['q3']:.1f}]")
    outliers = identificar_outliers(df["tempo_segundos"])
    print(f"  outliers (IQR global): {outliers}")

    pares_tempo = agregar_mediana_por_integrante(df, "tempo_segundos")
    resultado = rodar_wilcoxon(
        pares_tempo["com-ia"], pares_tempo["sem-ia"], alternative="less"
    )
    if resultado.sem_variancia:
        print("  Wilcoxon: sem variância nos pares — não computável.")
    else:
        r_biserial = correlacao_rank_biserial(pares_tempo["com-ia"], pares_tempo["sem-ia"])
        print(
            f"  Wilcoxon pareado (N={resultado.n}, unicaudal com-ia<sem-ia): "
            f"W={resultado.estatistica:.2f}  p={resultado.p_valor:.4f}  r={r_biserial:.3f}"
        )
    ic_lo, ic_hi = bootstrap_ic_diferenca_mediana(
        df[df["tratamento"] == "com-ia"]["tempo_segundos"],
        df[df["tratamento"] == "sem-ia"]["tempo_segundos"],
    )
    print(f"  Bootstrap IC95% (diferença de mediana, com-ia - sem-ia): [{ic_lo:.1f}, {ic_hi:.1f}]")

    print()
    print("=" * 70)
    print("RQ2 — Defeitos (taxa_sucesso)")
    print("=" * 70)
    for tratamento in TRATAMENTOS:
        r = resumo_descritivo(df[df["tratamento"] == tratamento]["taxa_sucesso"])
        print(f"  {tratamento}: mediana={r['mediana']:.1f}%  IQR=[{r['q1']:.1f}, {r['q3']:.1f}]")

    pares_taxa = agregar_mediana_por_integrante(df, "taxa_sucesso")
    resultado_rq2 = rodar_wilcoxon(
        pares_taxa["com-ia"], pares_taxa["sem-ia"], alternative="greater"
    )
    if resultado_rq2.sem_variancia:
        print(
            "  Wilcoxon: SEM VARIÂNCIA — os 18 trials tiveram taxa_sucesso=100%. "
            "H0 não pode ser rejeitada nem confirmada por falta de variação."
        )
    else:
        r_biserial = correlacao_rank_biserial(pares_taxa["com-ia"], pares_taxa["sem-ia"])
        print(
            f"  Wilcoxon pareado (N={resultado_rq2.n}, unicaudal com-ia>sem-ia): "
            f"W={resultado_rq2.estatistica:.2f}  p={resultado_rq2.p_valor:.4f}  r={r_biserial:.3f}"
        )

    dens = densidade_defeitos()
    print(f"  Densidade de defeitos (testes_falhando/KLOC) — máx observado: {dens['densidade_defeitos'].max():.3f}")

    print()
    print("Proporção de censura por tratamento:", proporcao_censura(df))

    grafico_prompts_vs_tempo(df, DIR_GRAFICOS / "rq1_prompts_vs_tempo_exploratorio.png")
    grafico_tempo_vs_ordem(df, DIR_GRAFICOS / "rq1_tempo_vs_ordem_exploratorio.png")
    print(f"\nGráficos salvos em {DIR_GRAFICOS}")


if __name__ == "__main__":
    main()
