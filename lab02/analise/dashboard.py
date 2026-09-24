"""Dashboard de gráficos do Lab02 — consolida RQ1, RQ2 e RQ3 (issue #123).

Lê os três CSVs de `lab02/dados/` e gera os gráficos comparativos
com-ia vs. sem-ia, reaproveitando as funções de carga e de derivação já
cobertas por testes em `rq1_rq2_estatistica.py` e `rq3_estatistica.py`.

Convenções desta amostra (N=18: 3 integrantes x 6 katas, 9 trials por
tratamento):

- Todo boxplot leva os pontos individuais por cima. Com 9 observações por
  caixa, a caixa sozinha esconde mais do que mostra.
- Variáveis sem variância recebem uma anotação no próprio gráfico. RQ2 é
  o caso: taxa_sucesso=100% e testes_falhando=0 nos 18 trials. O gráfico
  plano é o resultado (efeito teto), não uma falha do script — sem a
  anotação, parece bug.
"""

from __future__ import annotations

import sys
from pathlib import Path

import matplotlib

matplotlib.use("Agg")  # headless: roda igual em CI e no terminal

import matplotlib.pyplot as plt  # noqa: E402
import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import seaborn as sns  # noqa: E402

RAIZ_LAB02 = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(RAIZ_LAB02))

from analise.rq1_rq2_estatistica import (  # noqa: E402
    DIR_DADOS,
    TRATAMENTOS,
    carregar_dados,
    densidade_defeitos,
)
from analise.rq3_estatistica import carregar_metricas  # noqa: E402

DIR_GRAFICOS = Path(__file__).resolve().parent / "graficos" / "dashboard"

PALETA = {"com-ia": "#4C72B0", "sem-ia": "#DD8452"}
METRICAS_CORRELACAO = ("cc_media", "loc", "mi", "duplicacao_pct")


# --------------------------------------------------------------------------
# Helpers (cobertos por tests/test_dashboard.py)
# --------------------------------------------------------------------------

def sem_variancia(valores: pd.Series) -> bool:
    """True quando todos os trials têm o mesmo valor — gráfico degenerado."""
    return valores.nunique(dropna=False) <= 1


def matriz_correlacao(
    df: pd.DataFrame, colunas: tuple[str, ...] = METRICAS_CORRELACAO
) -> pd.DataFrame:
    """Spearman entre as métricas de RQ3 — posto, não Pearson (N pequeno)."""
    return df[list(colunas)].corr(method="spearman")


def preparar_tempo_vs_estrutura(dir_dados: Path = DIR_DADOS) -> pd.DataFrame:
    """Um trial por linha com tempo (RQ1) e cc_media/loc (RQ3) lado a lado."""
    trials = carregar_dados(dir_dados)
    metricas = carregar_metricas(dir_dados)
    return trials.merge(
        metricas[["integrante", "kata", "tratamento", "cc_media", "loc"]],
        on=["integrante", "kata", "tratamento"],
        how="left",
    )


def mediana_por_kata(df: pd.DataFrame, coluna: str) -> pd.DataFrame:
    """Mediana de `coluna` por kata e tratamento, em formato largo.

    O contrabalanceamento deixa 1 ou 2 trials por célula kata x tratamento,
    então "mediana" aqui é quase sempre o próprio trial. Serve para ler a
    direção do efeito por kata, não para inferência.
    """
    return (
        df.groupby(["kata", "tratamento"])[coluna]
        .median()
        .unstack("tratamento")
        .reindex(columns=list(TRATAMENTOS))
        .reset_index()
    )


def _salvar(fig: plt.Figure, caminho: Path) -> Path:
    caminho.parent.mkdir(parents=True, exist_ok=True)
    fig.tight_layout()
    fig.savefig(caminho, dpi=150)
    plt.close(fig)
    return caminho


def _anotar_sem_variancia(ax: plt.Axes, valores: pd.Series) -> None:
    if not sem_variancia(valores):
        return
    ax.text(
        0.5,
        0.78,  # acima da linha achatada, para não cobrir os pontos
        f"Sem variância: todos os {len(valores)} trials em {valores.iloc[0]:g}",
        transform=ax.transAxes,
        ha="center",
        va="center",
        fontsize=9,
        color="dimgray",
        bbox={"facecolor": "white", "alpha": 0.8, "edgecolor": "lightgray"},
    )


def boxplot_por_tratamento(
    df: pd.DataFrame, coluna: str, titulo: str, rotulo_y: str, caminho: Path
) -> Path:
    """Boxplot com-ia vs. sem-ia, com os trials individuais por cima."""
    fig, ax = plt.subplots(figsize=(6, 4.5))
    sns.boxplot(
        data=df, x="tratamento", y=coluna, order=list(TRATAMENTOS),
        palette=PALETA, hue="tratamento", legend=False, width=0.5,
        showfliers=False, ax=ax,
    )
    sns.stripplot(
        data=df, x="tratamento", y=coluna, order=list(TRATAMENTOS),
        color="black", size=5, alpha=0.7, jitter=0.15, ax=ax,
    )
    ax.set_xlabel("")
    ax.set_ylabel(rotulo_y)
    ax.set_title(titulo)
    _anotar_sem_variancia(ax, df[coluna])
    return _salvar(fig, caminho)


# --------------------------------------------------------------------------
# RQ1 — tempo
# --------------------------------------------------------------------------

def graficos_rq1(df: pd.DataFrame, dir_saida: Path) -> list[Path]:
    caminhos = [
        boxplot_por_tratamento(
            df, "tempo_segundos",
            "RQ1 — tempo até a suíte verde por tratamento",
            "tempo até verde (s)",
            dir_saida / "rq1_tempo_boxplot.png",
        )
    ]

    com_ia = df[df["tratamento"] == "com-ia"]
    fig, ax = plt.subplots(figsize=(6, 4.5))
    ax.scatter(com_ia["prompts"], com_ia["tempo_segundos"], color=PALETA["com-ia"])
    ax.set_xlabel("nº de prompts")
    ax.set_ylabel("tempo até verde (s)")
    ax.set_title("RQ1 — prompts x tempo (trials com-ia)")
    ax.set_xticks(sorted(com_ia["prompts"].unique()))
    caminhos.append(_salvar(fig, dir_saida / "rq1_prompts_vs_tempo.png"))

    fig, ax = plt.subplots(figsize=(6, 4.5))
    for tratamento in TRATAMENTOS:
        subset = df[df["tratamento"] == tratamento]
        ax.scatter(
            subset["ordem"], subset["tempo_segundos"],
            color=PALETA[tratamento], label=tratamento,
        )
    coef = np.polyfit(df["ordem"], df["tempo_segundos"], 1)
    xs = np.array([df["ordem"].min(), df["ordem"].max()])
    ax.plot(
        xs, np.polyval(coef, xs), linestyle="--", color="gray",
        label=f"tendência ({coef[0]:+.1f} s/trial)",
    )
    ax.set_xlabel("ordem na sequência do integrante")
    ax.set_ylabel("tempo até verde (s)")
    ax.set_title("RQ1 — tempo x ordem (efeito de aprendizado)")
    ax.legend()
    caminhos.append(_salvar(fig, dir_saida / "rq1_tempo_vs_ordem.png"))
    return caminhos


# --------------------------------------------------------------------------
# RQ2 — defeitos
# --------------------------------------------------------------------------

def graficos_rq2(
    df: pd.DataFrame, dir_saida: Path, dir_dados: Path = DIR_DADOS
) -> list[Path]:
    caminhos = [
        boxplot_por_tratamento(
            df, "taxa_sucesso",
            "RQ2 — taxa de sucesso dos testes por tratamento",
            "taxa de sucesso (%)",
            dir_saida / "rq2_taxa_sucesso_boxplot.png",
        ),
        boxplot_por_tratamento(
            df, "testes_falhando",
            "RQ2 — testes falhando por tratamento",
            "testes falhando (nº)",
            dir_saida / "rq2_testes_falhando_boxplot.png",
        ),
    ]
    dens = densidade_defeitos(dir_dados)
    caminhos.append(
        boxplot_por_tratamento(
            dens, "densidade_defeitos",
            "RQ2 — densidade de defeitos por tratamento",
            "testes falhando / KLOC",
            dir_saida / "rq2_densidade_defeitos_boxplot.png",
        )
    )
    return caminhos


# --------------------------------------------------------------------------
# RQ3 — estrutura do código
# --------------------------------------------------------------------------

def graficos_rq3(metricas: pd.DataFrame, dir_saida: Path) -> list[Path]:
    caminhos = [
        boxplot_por_tratamento(
            metricas, "cc_media",
            "RQ3 — complexidade ciclomática média por tratamento",
            "cc_media (McCabe)",
            dir_saida / "rq3_cc_media_boxplot.png",
        ),
        boxplot_por_tratamento(
            metricas, "duplicacao_pct",
            "RQ3 — duplicação de código por tratamento",
            "duplicação (%)",
            dir_saida / "rq3_duplicacao_boxplot.png",
        ),
    ]

    # loc é variável de controle: histograma geral + boxplot por tratamento
    fig, (ax_hist, ax_box) = plt.subplots(1, 2, figsize=(10, 4.5))
    ax_hist.hist(metricas["loc"], bins=8, color="#8C8C8C", edgecolor="white")
    ax_hist.set_xlabel("loc")
    ax_hist.set_ylabel("nº de trials")
    ax_hist.set_title("Distribuição geral de loc")
    sns.boxplot(
        data=metricas, x="tratamento", y="loc", order=list(TRATAMENTOS),
        palette=PALETA, hue="tratamento", legend=False, width=0.5,
        showfliers=False, ax=ax_box,
    )
    sns.stripplot(
        data=metricas, x="tratamento", y="loc", order=list(TRATAMENTOS),
        color="black", size=5, alpha=0.7, jitter=0.15, ax=ax_box,
    )
    ax_box.set_xlabel("")
    ax_box.set_ylabel("loc")
    ax_box.set_title("loc por tratamento (controle)")
    fig.suptitle("RQ3 — loc como variável de controle")
    caminhos.append(_salvar(fig, dir_saida / "rq3_loc_histograma_boxplot.png"))

    caminhos.append(
        boxplot_por_tratamento(
            metricas, "mi",
            "RQ3 — índice de manutenibilidade (MI) por tratamento",
            "mi (0-100, maior = mais manutenível)",
            dir_saida / "rq3_mi_boxplot.png",
        )
    )
    return caminhos


# --------------------------------------------------------------------------
# Diferenciais
# --------------------------------------------------------------------------

def graficos_diferenciais(
    completo: pd.DataFrame, metricas: pd.DataFrame, dir_saida: Path
) -> list[Path]:
    caminhos: list[Path] = []

    # Bubble: velocidade (x) x complexidade (y), bolha = loc, cor = tratamento
    fig, ax = plt.subplots(figsize=(7, 5))
    escala_bolha = 8
    for tratamento in TRATAMENTOS:
        subset = completo[completo["tratamento"] == tratamento]
        ax.scatter(
            subset["tempo_segundos"], subset["cc_media"],
            s=subset["loc"] * escala_bolha, color=PALETA[tratamento],
            alpha=0.6, edgecolor="white", label=tratamento,
        )
    ax.set_xlabel("tempo até verde (s)")
    ax.set_ylabel("cc_media (McCabe)")
    ax.set_title("Trade-off velocidade x complexidade (bolha = loc)")
    legenda_tratamento = ax.legend(title="tratamento", loc="upper right")
    bolhas = [
        ax.scatter(
            [], [], s=valor * escala_bolha, color="lightgray",
            edgecolor="gray", label=str(valor),
        )
        for valor in (int(completo["loc"].min()), int(completo["loc"].max()))
    ]
    ax.legend(handles=bolhas, title="loc", loc="lower right", labelspacing=1.4)
    ax.add_artist(legenda_tratamento)
    caminhos.append(_salvar(fig, dir_saida / "extra_bubble_tempo_vs_cc.png"))

    # Heatmap de correlação entre as métricas estruturais
    correlacao = matriz_correlacao(metricas)
    fig, ax = plt.subplots(figsize=(6, 5))
    sns.heatmap(
        correlacao, annot=True, fmt=".2f", cmap="RdBu_r", center=0,
        vmin=-1, vmax=1, square=True, linewidths=0.5, ax=ax,
    )
    ax.set_title("Correlação de Spearman entre métricas de RQ3")
    if (metricas["duplicacao_pct"] > 0).sum() <= 1:
        # nota como xlabel, e não fig.text: assim o tight_layout reserva espaço
        ax.set_xlabel(
            "duplicacao_pct tem no máximo 1 trial > 0 —\n"
            "sua linha/coluna é dominada por esse ponto.",
            fontsize=8, color="dimgray",
        )
    caminhos.append(_salvar(fig, dir_saida / "extra_heatmap_correlacao.png"))

    # Barras agrupadas por kata: a IA ajuda mais em kata fácil ou difícil?
    katas = sorted(completo["kata"].unique())
    fig, ax = plt.subplots(figsize=(8, 4.5))
    sns.barplot(
        data=completo, x="kata", y="tempo_segundos", hue="tratamento",
        order=katas, hue_order=list(TRATAMENTOS), palette=PALETA,
        estimator="median", errorbar=None, ax=ax,
    )
    sns.stripplot(
        data=completo, x="kata", y="tempo_segundos", hue="tratamento",
        order=katas, hue_order=list(TRATAMENTOS), dodge=True,
        palette={t: "black" for t in TRATAMENTOS},  # color= com hue vira gradiente
        size=4, alpha=0.8, legend=False, ax=ax,
    )
    ax.set_xlabel("kata")
    ax.set_ylabel("tempo até verde (s) — mediana")
    ax.set_title("Tempo por kata e tratamento")
    ax.annotate(
        "1 a 2 trials por célula kata x tratamento (contrabalanceamento) — "
        "leia a direção, não a magnitude.",
        xy=(0.5, -0.18), xycoords="axes fraction",
        ha="center", fontsize=8, color="dimgray", annotation_clip=False,
    )
    caminhos.append(_salvar(fig, dir_saida / "extra_barras_por_kata.png"))
    return caminhos


# --------------------------------------------------------------------------
# main
# --------------------------------------------------------------------------

def gerar_todos(
    dir_saida: Path = DIR_GRAFICOS, dir_dados: Path = DIR_DADOS
) -> list[Path]:
    df = carregar_dados(dir_dados)
    metricas = carregar_metricas(dir_dados)
    completo = preparar_tempo_vs_estrutura(dir_dados)
    return [
        *graficos_rq1(df, dir_saida),
        *graficos_rq2(df, dir_saida, dir_dados),
        *graficos_rq3(metricas, dir_saida),
        *graficos_diferenciais(completo, metricas, dir_saida),
    ]


def main() -> None:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")  # acentos no console do Windows
        except Exception:
            pass

    sns.set_theme(style="whitegrid")
    caminhos = gerar_todos()

    print("=" * 70)
    print(f"Dashboard Lab02 — {len(caminhos)} gráficos gerados")
    print("=" * 70)
    for caminho in caminhos:
        print(f"  {caminho.relative_to(RAIZ_LAB02.parent)}")

    df = carregar_dados()
    if sem_variancia(df["taxa_sucesso"]):
        print(
            "\nAviso: taxa_sucesso e testes_falhando não têm variância nesta "
            "amostra (efeito teto). Os gráficos de RQ2 saem planos por isso, "
            "e trazem a anotação correspondente."
        )


if __name__ == "__main__":
    main()
