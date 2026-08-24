from pathlib import Path

import matplotlib.pyplot as plt
import pandas as pd

from estilo import AZUL, LARANJA, TINTA_MUTED, TINTA_PRIMARIA, TINTA_SECUNDARIA, aplicar_estilo

RAIZ = Path(__file__).resolve().parent.parent
CSV_PATH = RAIZ / "data" / "repositories.csv"
GRAFICOS_DIR = RAIZ / "relatorio" / "graficos"

AUSENTE_LICENCA = "Não informado"
TOP_N_LICENCAS = 5


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


def grafico_rq09_licenca(df: pd.DataFrame) -> dict:
    stats = top_categorias(df["licenca"], AUSENTE_LICENCA, TOP_N_LICENCAS)

    rotulos = [nome for nome, _ in stats["top"]] + [AUSENTE_LICENCA]
    valores = [contagem for _, contagem in stats["top"]] + [stats["ausentes"]]
    # Mesma convenção de RQ05: "Não informado" fica fora da ordenação por
    # valor e com cor neutra, pra não ser lida como parte do ranking.
    cores = [AZUL] * len(stats["top"]) + [TINTA_MUTED]

    fig, ax = plt.subplots(figsize=(8, 4.5))
    posicoes = range(len(rotulos))
    ax.barh(posicoes, valores, color=cores, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax.set_yticks(list(posicoes))
    ax.set_yticklabels(rotulos)
    ax.invert_yaxis()
    for pos, valor in zip(posicoes, valores):
        ax.text(valor, pos, f"  {valor}", color=TINTA_SECUNDARIA, va="center", fontsize=9)
    ax.set_title(f"Extra — Top {TOP_N_LICENCAS} licenças")
    ax.set_xlabel("Nº de repositórios")
    aplicar_estilo(ax)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq09_licenca.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return stats


def grafico_rq10_cicd(df: pd.DataFrame) -> dict:
    contagens = df["possui_ci_cd"].value_counts()
    com_cicd = int(contagens.get(True, 0))
    sem_cicd = int(contagens.get(False, 0))

    rotulos = ["Com CI/CD", "Sem CI/CD"]
    valores = [com_cicd, sem_cicd]
    cores = [AZUL, TINTA_MUTED]

    fig, ax = plt.subplots(figsize=(8, 3))
    posicoes = range(len(rotulos))
    ax.barh(posicoes, valores, color=cores, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax.set_yticks(list(posicoes))
    ax.set_yticklabels(rotulos)
    ax.invert_yaxis()
    for pos, valor in zip(posicoes, valores):
        ax.text(valor, pos, f"  {valor}", color=TINTA_SECUNDARIA, va="center", fontsize=9)
    ax.set_title("Extra — Presença de CI/CD (GitHub Actions)")
    ax.set_xlabel("Nº de repositórios")
    aplicar_estilo(ax)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq10_cicd.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return {"com_cicd": com_cicd, "sem_cicd": sem_cicd, "total": com_cicd + sem_cicd}


def grafico_rq11_linguagens(df: pd.DataFrame) -> dict:
    linguagens = df["total_linguagens"]
    stats = estatisticas_descritivas(linguagens)

    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(10, 4))

    ax_hist.hist(linguagens, bins=30, color=LARANJA, edgecolor=TINTA_PRIMARIA, linewidth=0.3)
    ax_hist.axvline(stats["mediana"], color=TINTA_PRIMARIA, linestyle="--", linewidth=1.2)
    ax_hist.text(
        stats["mediana"], ax_hist.get_ylim()[1] * 0.95,
        f"  mediana={stats['mediana']:.0f}",
        color=TINTA_SECUNDARIA, fontsize=9, va="top",
    )
    ax_hist.set_title("Extra — Distribuição do nº de linguagens")
    ax_hist.set_xlabel("Nº de linguagens detectadas")
    ax_hist.set_ylabel("Nº de repositórios")
    aplicar_estilo(ax_hist)

    box = ax_box.boxplot(
        linguagens, patch_artist=True, widths=0.5,
        medianprops={"color": TINTA_PRIMARIA, "linewidth": 1.5},
        flierprops={"markeredgecolor": LARANJA, "markersize": 4, "alpha": 0.5},
    )
    box["boxes"][0].set_facecolor(LARANJA)
    box["boxes"][0].set_alpha(0.55)
    box["boxes"][0].set_edgecolor(TINTA_PRIMARIA)
    ax_box.set_title("Extra — Boxplot do nº de linguagens")
    ax_box.set_ylabel("Nº de linguagens detectadas")
    ax_box.set_xticks([])
    aplicar_estilo(ax_box)

    fig.tight_layout()
    caminho = GRAFICOS_DIR / "rq11_linguagens.png"
    fig.savefig(caminho, dpi=150)
    plt.close(fig)

    return stats


def main() -> None:
    GRAFICOS_DIR.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(CSV_PATH)
    df["possui_ci_cd"] = df["possui_ci_cd"].astype(bool)

    print(f"Analisando {len(df)} repositórios de {CSV_PATH}...\n")

    stats_rq09 = grafico_rq09_licenca(df)
    print("RQ09 extra (licenca):")
    print(f"  top: {stats_rq09['top']}")
    print(f"  categorias_unicas={stats_rq09['categorias_unicas']} restantes={stats_rq09['restantes']} "
          f"ausentes={stats_rq09['ausentes']}/{stats_rq09['total']}")

    stats_rq10 = grafico_rq10_cicd(df)
    print("\nRQ10 extra (possui_ci_cd):")
    for chave, valor in stats_rq10.items():
        print(f"  {chave}: {valor}")

    stats_rq11 = grafico_rq11_linguagens(df)
    print("\nRQ11 extra (total_linguagens):")
    for chave, valor in stats_rq11.items():
        print(f"  {chave}: {valor:.2f}" if isinstance(valor, float) else f"  {chave}: {valor}")

    print(f"\nGráficos salvos em {GRAFICOS_DIR}")


if __name__ == "__main__":
    main()
