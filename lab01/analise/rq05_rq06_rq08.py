from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from estilo import AZUL, LARANJA, VERMELHO, TINTA_MUTED, TINTA_PRIMARIA, TINTA_SECUNDARIA, aplicar_estilo

RAIZ = Path(__file__).resolve().parent.parent
CSV_PATH = RAIZ / "data" / "repositories.csv"
GRAFICOS_DIR = RAIZ / "relatorio" / "graficos"

AUSENTE_LINGUAGEM = "Não informado"
TOP_N_LINGUAGENS = 5


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


def top_categorias(serie: pd.Series, valor_ausente: str, top_n: int) -> dict:
    presentes = serie[serie != valor_ausente]
    ausentes = int((serie == valor_ausente).sum())
    contagens = presentes.value_counts()
    top = contagens.head(top_n)
    restantes = int(contagens.iloc[top_n:].sum())
    return {
        "top": list(top.items()),
        "categorias_unicas": int(contagens.size),
        "restantes": restantes,
        "ausentes": ausentes,
        "total": int(serie.count()),
    }


def grafico_rq05_linguagem(df: pd.DataFrame) -> dict:
    stats = top_categorias(df["linguagem"], AUSENTE_LINGUAGEM, TOP_N_LINGUAGENS)

    rotulos = [nome for nome, _ in stats["top"]] + [AUSENTE_LINGUAGEM]
    valores = [contagem for _, contagem in stats["top"]] + [stats["ausentes"]]
    # "Não informado" fica sempre por último, fora da ordenação por valor —
    # é uma categoria à parte (ausência de dado), não uma linguagem ranqueada
    # (mesma convenção usada em data-quality-report.md/hipoteses-informais.md)
    # — por isso ganha cor neutra, para não ser lida como parte do ranking.
    cores = [AZUL] * len(stats["top"]) + [TINTA_MUTED]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    posicoes = range(len(rotulos))
    ax.barh(posicoes, valores, color=cores, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax.set_yticks(list(posicoes))
    ax.set_yticklabels(rotulos)
    ax.invert_yaxis()
    for pos, valor in zip(posicoes, valores):
        ax.text(valor, pos, f"  {valor}", color=TINTA_SECUNDARIA, va="center", fontsize=9)
    ax.set_title(f"RQ05 — Top {TOP_N_LINGUAGENS} linguagens primárias")
    ax.set_xlabel("Nº de repositórios")
    aplicar_estilo(ax)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq05_linguagem.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return stats


def grafico_rq06_issues(df: pd.DataFrame) -> dict:
    razao = df["razao_issues_fechadas"]
    stats = estatisticas_descritivas(razao)

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(10, 4))

    ax_hist.hist(razao, bins=30, color=LARANJA, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax_hist.axvline(stats["mediana"], color=TINTA_PRIMARIA, linestyle="--", linewidth=1.2)
    ax_hist.text(
        stats["mediana"], ax_hist.get_ylim()[1] * 0.95,
        f"  mediana={stats['mediana']:.2f}",
        color=TINTA_SECUNDARIA, fontsize=9, va="top",
    )
    ax_hist.set_title("RQ06 — Distribuição da razão de issues fechadas")
    ax_hist.set_xlabel("Razão de issues fechadas")
    ax_hist.set_ylabel("Nº de repositórios")
    aplicar_estilo(ax_hist)

    box = ax_box.boxplot(
        razao, patch_artist=True, widths=0.5,
        medianprops={"color": TINTA_PRIMARIA, "linewidth": 1.5},
        flierprops={"markeredgecolor": LARANJA, "markersize": 4, "alpha": 0.5},
    )
    box["boxes"][0].set_facecolor(LARANJA)
    box["boxes"][0].set_alpha(0.55)
    box["boxes"][0].set_edgecolor(TINTA_PRIMARIA)
    ax_box.set_title("RQ06 — Boxplot da razão de issues fechadas")
    ax_box.set_ylabel("Razão de issues fechadas")
    ax_box.set_xticks([])
    aplicar_estilo(ax_box)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq06_issues.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return stats


def grafico_rq08_forks(df: pd.DataFrame) -> dict:
    forks = df["total_forks"]
    stats = estatisticas_descritivas(forks)

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(10, 4))

    bins_log = np.logspace(np.log10(forks.min()), np.log10(forks.max()), 25)
    ax_hist.hist(forks, bins=bins_log, color=VERMELHO, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax_hist.set_xscale("log")
    ax_hist.axvline(stats["mediana"], color=TINTA_PRIMARIA, linestyle="--", linewidth=1.2)
    ax_hist.text(
        stats["mediana"], ax_hist.get_ylim()[1] * 0.95,
        f"  mediana={stats['mediana']:.0f}",
        color=TINTA_SECUNDARIA, fontsize=9, va="top",
    )
    ax_hist.set_title("RQ08 (bônus) — Distribuição de forks (escala log)")
    ax_hist.set_xlabel("Total de forks (log)")
    ax_hist.set_ylabel("Nº de repositórios")
    aplicar_estilo(ax_hist)

    box = ax_box.boxplot(
        forks, patch_artist=True, widths=0.5,
        medianprops={"color": TINTA_PRIMARIA, "linewidth": 1.5},
        flierprops={"markeredgecolor": VERMELHO, "markersize": 4, "alpha": 0.5},
    )
    box["boxes"][0].set_facecolor(VERMELHO)
    box["boxes"][0].set_alpha(0.55)
    box["boxes"][0].set_edgecolor(TINTA_PRIMARIA)
    ax_box.set_yscale("log")
    ax_box.set_title("RQ08 (bônus) — Boxplot de forks (escala log)")
    ax_box.set_ylabel("Total de forks")
    ax_box.set_xticks([])
    aplicar_estilo(ax_box)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq08_forks.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return stats


def main() -> None:
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CSV_PATH)

    print(f"Analisando {len(df)} repositórios de {CSV_PATH}...\n")

    stats_rq05 = grafico_rq05_linguagem(df)
    print("RQ05 (linguagem):")
    print(f"  top: {stats_rq05['top']}")
    print(f"  categorias_unicas={stats_rq05['categorias_unicas']} restantes={stats_rq05['restantes']} "
          f"ausentes={stats_rq05['ausentes']}/{stats_rq05['total']}")

    stats_rq06 = grafico_rq06_issues(df)
    print("\nRQ06 (razao_issues_fechadas):")
    for chave, valor in stats_rq06.items():
        print(f"  {chave}: {valor:.4f}" if isinstance(valor, float) else f"  {chave}: {valor}")

    stats_rq08 = grafico_rq08_forks(df)
    print("\nRQ08 (total_forks):")
    for chave, valor in stats_rq08.items():
        print(f"  {chave}: {valor:.2f}" if isinstance(valor, float) else f"  {chave}: {valor}")

    print(f"\nGráficos salvos em {GRAFICOS_DIR}")


if __name__ == "__main__":
    main()
