from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from scipy.stats import kruskal

from estilo import AZUL, LARANJA, VERMELHO, TINTA_MUTED, TINTA_PRIMARIA, TINTA_SECUNDARIA, aplicar_estilo

RAIZ = Path(__file__).resolve().parent.parent
CSV_PATH = RAIZ / "data" / "repositories.csv"
GRAFICOS_DIR = RAIZ / "relatorio" / "graficos"

AUSENTE_LINGUAGEM = "Não informado"
TETO_API_RELEASES = 1000

# Top 5 linguagens por contribuidores, GitHub Octoverse 2025 (mesma fonte
# documentada na Issue #3/RQ05) — confirmado em:
# https://github.blog/news-insights/octoverse/octoverse-a-new-developer-joins-github-every-second-as-ai-leads-typescript-to-1/
# Não é derivado do nosso próprio dataset (seria circular).
POPULARES = {"TypeScript", "Python", "JavaScript", "Java", "C#"}


def classificar_grupo(df: pd.DataFrame) -> pd.DataFrame:
    classificados = df[df["linguagem"] != AUSENTE_LINGUAGEM].copy()
    classificados["grupo"] = np.where(
        classificados["linguagem"].isin(POPULARES), "Populares", "Não populares"
    )
    return classificados


def comparar_grupos(df: pd.DataFrame, coluna: str) -> dict:
    populares = df.loc[df["grupo"] == "Populares", coluna]
    nao_populares = df.loc[df["grupo"] == "Não populares", coluna]
    estatistica, p_valor = kruskal(populares, nao_populares)
    return {
        "n_populares": int(populares.count()),
        "n_nao_populares": int(nao_populares.count()),
        "mediana_populares": populares.median(),
        "mediana_nao_populares": nao_populares.median(),
        "kruskal_estatistica": estatistica,
        "kruskal_p_valor": p_valor,
    }


def _boxplot_grupos(ax, df: pd.DataFrame, coluna: str, titulo: str, ylabel: str) -> None:
    populares = df.loc[df["grupo"] == "Populares", coluna]
    nao_populares = df.loc[df["grupo"] == "Não populares", coluna]

    box = ax.boxplot(
        [populares, nao_populares],
        tick_labels=["Populares", "Não populares"],
        patch_artist=True, widths=0.5,
        medianprops={"color": TINTA_PRIMARIA, "linewidth": 1.5},
        flierprops={"markersize": 4, "alpha": 0.5},
    )
    cores = [AZUL, TINTA_MUTED]
    for patch, cor in zip(box["boxes"], cores):
        patch.set_facecolor(cor)
        patch.set_alpha(0.55)
        patch.set_edgecolor(TINTA_PRIMARIA)
    for flier, cor in zip(box["fliers"], cores):
        flier.set_markeredgecolor(cor)

    ax.set_title(titulo)
    ax.set_ylabel(ylabel)
    aplicar_estilo(ax)


def grafico_rq07(df: pd.DataFrame) -> dict:
    resultado_prs = comparar_grupos(df, "prs_aceitas")
    resultado_releases = comparar_grupos(df, "total_releases")
    resultado_dias = comparar_grupos(df, "dias_desde_atualizacao")

    fig, (ax_prs, ax_releases, ax_dias) = plt.subplots(1, 3, figsize=(14, 4.5))

    _boxplot_grupos(ax_prs, df, "prs_aceitas", "RQ07 — PRs aceitas", "PRs aceitas (log)")
    ax_prs.set_yscale("symlog")

    _boxplot_grupos(ax_releases, df, "total_releases", "RQ07 — Total de releases", "Total de releases")
    if df["total_releases"].max() >= TETO_API_RELEASES:
        ax_releases.axhline(TETO_API_RELEASES, color=TINTA_MUTED, linestyle=":", linewidth=1.2)
        ax_releases.text(
            1.4, TETO_API_RELEASES, "teto da API (truncado)",
            color=TINTA_MUTED, fontsize=8, va="bottom",
        )

    _boxplot_grupos(ax_dias, df, "dias_desde_atualizacao", "RQ07 — Dias sem atualização", "Dias (log)")
    ax_dias.set_yscale("symlog", linthresh=1)

    fig.suptitle("RQ07 — Linguagens populares (Octoverse) vs. não populares", color=TINTA_PRIMARIA)
    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq07_linguagens.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return {
        "prs_aceitas": resultado_prs,
        "total_releases": resultado_releases,
        "dias_desde_atualizacao": resultado_dias,
    }


def _imprimir_resultado(nome: str, resultado: dict) -> None:
    print(f"\n{nome}:")
    print(f"  n populares={resultado['n_populares']} n não populares={resultado['n_nao_populares']}")
    print(f"  mediana populares={resultado['mediana_populares']:.2f} "
          f"mediana não populares={resultado['mediana_nao_populares']:.2f}")
    print(f"  Kruskal-Wallis: H={resultado['kruskal_estatistica']:.2f} "
          f"p={resultado['kruskal_p_valor']:.6f}")


def main() -> None:
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
    df_bruto = pd.read_csv(CSV_PATH)
    df = classificar_grupo(df_bruto)

    print(f"Analisando {len(df_bruto)} repositórios de {CSV_PATH}...")
    print(f"Classificados: {len(df)} (excluídos {len(df_bruto) - len(df)} 'Não informado')")

    resultados = grafico_rq07(df)
    _imprimir_resultado("RQ02 — PRs aceitas", resultados["prs_aceitas"])
    _imprimir_resultado("RQ03 — Total de releases", resultados["total_releases"])
    _imprimir_resultado("RQ04 — Dias sem atualização", resultados["dias_desde_atualizacao"])

    print(f"\nGráfico salvo em {GRAFICOS_DIR}")


if __name__ == "__main__":
    main()
