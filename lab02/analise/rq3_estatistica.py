from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd

RAIZ_LAB02 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_LAB02))

from analise.rq1_rq2_estatistica import (  
    DIR_DADOS,
    TRATAMENTOS,
    agregar_mediana_por_integrante,
    bootstrap_ic_diferenca_mediana,
    correlacao_rank_biserial,
    identificar_outliers,
    resumo_descritivo,
    rodar_wilcoxon,
)

METRICAS_TESTADAS = ("cc_media", "duplicacao_pct")
METRICA_CONTROLE = "loc"
METRICA_MI = "mi"


# --------------------------------------------------------------------------
# Funções puras (cobertas por tests/test_rq3_estatistica.py)
# --------------------------------------------------------------------------

def carregar_metricas(dir_dados: Path = DIR_DADOS) -> pd.DataFrame:
    return pd.read_csv(dir_dados / "metricas-estaticas.csv")


def tabela_descritiva(df: pd.DataFrame, colunas: tuple[str, ...]) -> pd.DataFrame:
    """Mediana/Q1/Q3/IQR por métrica e tratamento (não média/desvio, N pequeno)."""
    linhas = []
    for coluna in colunas:
        for tratamento in TRATAMENTOS:
            r = resumo_descritivo(df[df["tratamento"] == tratamento][coluna])
            linhas.append({"metrica": coluna, "tratamento": tratamento, **r})
    return pd.DataFrame(linhas)


def comparar_metrica(df: pd.DataFrame, coluna: str) -> dict:
    """Wilcoxon pareado bicaudal + rank-biserial + bootstrap para uma métrica.

    Bicaudal porque RQ3 não fixa direção a priori (docs/02-hipoteses.md).
    O par formal é a mediana por integrante por tratamento (mesmo esquema
    de RQ1/RQ2); o bootstrap reamostra no nível de trial.
    """
    pares = agregar_mediana_por_integrante(df, coluna)
    wilcoxon = rodar_wilcoxon(pares["com-ia"], pares["sem-ia"], alternative="two-sided")
    ic = bootstrap_ic_diferenca_mediana(
        df[df["tratamento"] == "com-ia"][coluna],
        df[df["tratamento"] == "sem-ia"][coluna],
    )
    return {
        "pares": pares,
        "wilcoxon": wilcoxon,
        "r_biserial": correlacao_rank_biserial(pares["com-ia"], pares["sem-ia"]),
        "ic_diferenca_mediana": ic,
    }


def trials_com_duplicacao(df: pd.DataFrame) -> pd.DataFrame:
    """Trials com duplicacao_pct > 0 — a mediana por integrante esconde esses casos."""
    return df[df["duplicacao_pct"] > 0][
        ["integrante", "kata", "tratamento", "duplicacao_pct"]
    ].reset_index(drop=True)


def contagem_trials_com_duplicacao(df: pd.DataFrame) -> dict[str, int]:
    contagem = (df["duplicacao_pct"] > 0).groupby(df["tratamento"]).sum()
    return {t: int(contagem.get(t, 0)) for t in TRATAMENTOS}


def correlacao_spearman(df: pd.DataFrame, coluna_a: str, coluna_b: str) -> float:
    """Spearman entre duas métricas, sobre os 18 trials (exploratório)."""
    return float(df[coluna_a].corr(df[coluna_b], method="spearman"))


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def _fmt_wilcoxon(resultado) -> str:
    if resultado.sem_variancia:
        return "sem variância nos pares (diferença zero em todos) — não computável"
    return f"W={resultado.estatistica:.2f}  p={resultado.p_valor:.4f}"


def _imprimir_metrica(df: pd.DataFrame, coluna: str) -> None:
    r = comparar_metrica(df, coluna)
    print(f"  Pares (mediana por integrante):")
    print("    " + r["pares"].to_string(index=False).replace("\n", "\n    "))
    print(f"  Wilcoxon pareado (N={r['wilcoxon'].n}, bicaudal): {_fmt_wilcoxon(r['wilcoxon'])}")
    if r["r_biserial"] is not None:
        print(f"  Rank-biserial: r={r['r_biserial']:.3f}")
    ic_lo, ic_hi = r["ic_diferenca_mediana"]
    print(f"  Bootstrap IC95% (diferença de mediana, com-ia - sem-ia): [{ic_lo:.2f}, {ic_hi:.2f}]")


def main() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except Exception:
            pass

    df = carregar_metricas()

    print("=" * 70)
    print("RQ3 — Estatística descritiva (mediana e IQR por tratamento)")
    print("=" * 70)
    colunas = (*METRICAS_TESTADAS, METRICA_CONTROLE, METRICA_MI, "cc_max")
    print(tabela_descritiva(df, colunas).round(2).to_string(index=False))
    for coluna in colunas:
        print(f"  outliers de {coluna} (IQR global): {identificar_outliers(df[coluna])}")

    for titulo, coluna in (
        ("RQ3 — cc_media (H: mediana difere)", "cc_media"),
        ("RQ3 — duplicacao_pct (H: mediana difere)", "duplicacao_pct"),
        ("Controle — loc", METRICA_CONTROLE),
        ("Aprofundamento — Índice de Manutenibilidade (mi)", METRICA_MI),
    ):
        print()
        print("=" * 70)
        print(titulo)
        print("=" * 70)
        _imprimir_metrica(df, coluna)

    print()
    print("=" * 70)
    print("Duplicação — trials com duplicacao_pct > 0")
    print("=" * 70)
    print(f"  contagem por tratamento: {contagem_trials_com_duplicacao(df)}")
    print(trials_com_duplicacao(df).to_string(index=False))

    print()
    print("=" * 70)
    print("loc lado a lado com cc/duplicação — Spearman entre os 18 trials")
    print("=" * 70)
    for coluna in ("cc_media", "cc_max", "duplicacao_pct", METRICA_MI):
        print(f"  loc x {coluna}: rho={correlacao_spearman(df, 'loc', coluna):.2f}")


if __name__ == "__main__":
    main()
