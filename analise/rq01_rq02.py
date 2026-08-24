from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from estilo import AZUL, LARANJA, TINTA_PRIMARIA, TINTA_SECUNDARIA, aplicar_estilo

RAIZ = Path(__file__).resolve().parent.parent
CSV_PATH = RAIZ / "data" / "repositories.csv"
GRAFICOS_DIR = RAIZ / "relatorio" / "graficos"


def estatisticas_descritivas(serie: pd.Series) -> dict:
    return {
        "n": int(serie.count()),
        "min": serie.min(),
        "q1": serie.quantile(0.25),
        "mediana": serie.median(),
        "q3": serie.quantile(0.75),
        "max": serie.max(),
        "media": serie.mean(),
    }


def grafico_rq01_idade(df: pd.DataFrame) -> dict:
    idade = df["idade_anos"]
    stats = estatisticas_descritivas(idade)

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(10, 4))

    ax_hist.hist(idade, bins=30, color=AZUL, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax_hist.axvline(stats["mediana"], color=TINTA_PRIMARIA, linestyle="--", linewidth=1.2)
    ax_hist.text(
        stats["mediana"], ax_hist.get_ylim()[1] * 0.95,
        f"  mediana={stats['mediana']:.1f} anos",
        color=TINTA_SECUNDARIA, fontsize=9, va="top",
    )
    ax_hist.set_title("RQ01 — Distribuição da idade dos repositórios")
    ax_hist.set_xlabel("Idade (anos)")
    ax_hist.set_ylabel("Nº de repositórios")
    aplicar_estilo(ax_hist)

    box = ax_box.boxplot(
        idade, patch_artist=True, orientation="vertical", widths=0.5,
        medianprops={"color": TINTA_PRIMARIA, "linewidth": 1.5},
        flierprops={"markeredgecolor": AZUL, "markersize": 4, "alpha": 0.6},
    )
    box["boxes"][0].set_facecolor(AZUL)
    box["boxes"][0].set_alpha(0.55)
    box["boxes"][0].set_edgecolor(TINTA_PRIMARIA)
    ax_box.set_title("RQ01 — Boxplot da idade")
    ax_box.set_ylabel("Idade (anos)")
    ax_box.set_xticks([])
    aplicar_estilo(ax_box)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq01_idade.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return stats


def grafico_rq02_prs(df: pd.DataFrame) -> dict:
    prs = df["prs_aceitas"]
    stats = estatisticas_descritivas(prs)

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(10, 4))

    prs_positivos = prs[prs > 0]
    bins_log = np.logspace(
        np.log10(prs_positivos.min()), np.log10(prs_positivos.max()), 25
    )
    ax_hist.hist(prs_positivos, bins=bins_log, color=LARANJA, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax_hist.set_xscale("log")
    ax_hist.axvline(stats["mediana"], color=TINTA_PRIMARIA, linestyle="--", linewidth=1.2)
    ax_hist.text(
        stats["mediana"], ax_hist.get_ylim()[1] * 0.95,
        f"  mediana={stats['mediana']:.0f}",
        color=TINTA_SECUNDARIA, fontsize=9, va="top",
    )
    ax_hist.set_title("RQ02 — Distribuição de PRs aceitas (escala log)")
    ax_hist.set_xlabel("PRs aceitas (log)")
    ax_hist.set_ylabel("Nº de repositórios")
    aplicar_estilo(ax_hist)

    box = ax_box.boxplot(
        prs, patch_artist=True, orientation="vertical", widths=0.5,
        medianprops={"color": TINTA_PRIMARIA, "linewidth": 1.5},
        flierprops={"markeredgecolor": LARANJA, "markersize": 4, "alpha": 0.5},
    )
    box["boxes"][0].set_facecolor(LARANJA)
    box["boxes"][0].set_alpha(0.55)
    box["boxes"][0].set_edgecolor(TINTA_PRIMARIA)
    ax_box.set_yscale("symlog")
    ax_box.set_title("RQ02 — Boxplot de PRs aceitas (escala log)")
    ax_box.set_ylabel("PRs aceitas")
    ax_box.set_xticks([])
    aplicar_estilo(ax_box)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq02_prs.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return stats


def main() -> None:
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CSV_PATH)

    print(f"Analisando {len(df)} repositórios de {CSV_PATH}...\n")

    stats_rq01 = grafico_rq01_idade(df)
    print("RQ01 (idade_anos):")
    for chave, valor in stats_rq01.items():
        print(f"  {chave}: {valor:.2f}" if isinstance(valor, float) else f"  {chave}: {valor}")

    stats_rq02 = grafico_rq02_prs(df)
    print("\nRQ02 (prs_aceitas):")
    for chave, valor in stats_rq02.items():
        print(f"  {chave}: {valor:.2f}" if isinstance(valor, float) else f"  {chave}: {valor}")

    print(f"\nGráficos salvos em {GRAFICOS_DIR}")


if __name__ == "__main__":
    main()
