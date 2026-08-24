from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from estilo import AZUL, TINTA_MUTED, TINTA_PRIMARIA, TINTA_SECUNDARIA, VERMELHO, aplicar_estilo

RAIZ = Path(__file__).resolve().parent.parent
CSV_PATH = RAIZ / "data" / "repositories.csv"
GRAFICOS_DIR = RAIZ / "relatorio" / "graficos"

TETO_API_RELEASES = 1000


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


def grafico_rq03_releases(df: pd.DataFrame) -> dict:
    releases = df["total_releases"]
    stats = estatisticas_descritivas(releases)

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(10, 4))

    bins = np.linspace(0, releases.max(), 40)
    ax_hist.hist(releases, bins=bins, color=AZUL, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax_hist.axvline(stats["mediana"], color=TINTA_PRIMARIA, linestyle="--", linewidth=1.2)
    ax_hist.text(
        stats["mediana"], ax_hist.get_ylim()[1] * 0.95,
        f"  mediana={stats['mediana']:.1f}",
        color=TINTA_SECUNDARIA, fontsize=9, va="top",
    )
    if releases.max() >= TETO_API_RELEASES:
        ax_hist.axvline(TETO_API_RELEASES, color=TINTA_MUTED, linestyle=":", linewidth=1.2)
        ax_hist.text(
            TETO_API_RELEASES, ax_hist.get_ylim()[1] * 0.72,
            "  teto da API\n  (truncado)",
            color=TINTA_MUTED, fontsize=8, va="top",
        )
    ax_hist.set_title("RQ03 — Distribuição do total de releases")
    ax_hist.set_xlabel("Total de releases")
    ax_hist.set_ylabel("Nº de repositórios")
    aplicar_estilo(ax_hist)

    box = ax_box.boxplot(
        releases, patch_artist=True, widths=0.5,
        medianprops={"color": TINTA_PRIMARIA, "linewidth": 1.5},
        flierprops={"markeredgecolor": AZUL, "markersize": 4, "alpha": 0.6},
    )
    box["boxes"][0].set_facecolor(AZUL)
    box["boxes"][0].set_alpha(0.55)
    box["boxes"][0].set_edgecolor(TINTA_PRIMARIA)
    ax_box.set_title("RQ03 — Boxplot do total de releases")
    ax_box.set_ylabel("Total de releases")
    ax_box.set_xticks([])
    aplicar_estilo(ax_box)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq03_releases.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return stats


def grafico_rq04_atualizacao(df: pd.DataFrame) -> dict:
    dias = df["dias_desde_atualizacao"]
    stats = estatisticas_descritivas(dias)

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(10, 4))

    bins = np.concatenate(([0], np.logspace(0, np.log10(dias.max()), 39)))
    ax_hist.hist(dias, bins=bins, color=VERMELHO, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax_hist.set_xscale("symlog", linthresh=1)
    ax_hist.axvline(stats["mediana"], color=TINTA_PRIMARIA, linestyle="--", linewidth=1.2)
    ax_hist.text(
        stats["mediana"], ax_hist.get_ylim()[1] * 0.95,
        f"  mediana={stats['mediana']:.0f} dias",
        color=TINTA_SECUNDARIA, fontsize=9, va="top",
    )
    ax_hist.set_title("RQ04 — Distribuição de dias sem atualização")
    ax_hist.set_xlabel("Dias desde a última atualização (symlog)")
    ax_hist.set_ylabel("Nº de repositórios")
    aplicar_estilo(ax_hist)

    box = ax_box.boxplot(
        dias, patch_artist=True, widths=0.5,
        medianprops={"color": TINTA_PRIMARIA, "linewidth": 1.5},
        flierprops={"markeredgecolor": VERMELHO, "markersize": 4, "alpha": 0.5},
    )
    box["boxes"][0].set_facecolor(VERMELHO)
    box["boxes"][0].set_alpha(0.55)
    box["boxes"][0].set_edgecolor(TINTA_PRIMARIA)
    ax_box.set_yscale("symlog", linthresh=1)
    ax_box.set_title("RQ04 — Boxplot de dias sem atualização")
    ax_box.set_ylabel("Dias desde última atualização")
    ax_box.set_xticks([])
    aplicar_estilo(ax_box)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq04_atualizacao.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return stats


def main() -> None:
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CSV_PATH)

    print(f"Analisando {len(df)} repositórios de {CSV_PATH}...\n")

    stats_rq03 = grafico_rq03_releases(df)
    print("RQ03 (total_releases):")
    for chave, valor in stats_rq03.items():
        print(f"  {chave}: {valor:.2f}" if isinstance(valor, float) else f"  {chave}: {valor}")

    stats_rq04 = grafico_rq04_atualizacao(df)
    print("\nRQ04 (dias_desde_atualizacao):")
    for chave, valor in stats_rq04.items():
        print(f"  {chave}: {valor:.2f}" if isinstance(valor, float) else f"  {chave}: {valor}")

    print(f"\nGráficos salvos em {GRAFICOS_DIR}")


if __name__ == "__main__":
    main()
