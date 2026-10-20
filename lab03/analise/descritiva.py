"""Estatística descritiva e classificação DORA de referência (RQ 01 a 04).

`python -m analise.descritiva`

Lê só `--csv` (padrão `dados/saida/repositorios.csv`) e grava em `--saida` (padrão
`analise/saida`):

- `descritiva.csv`: por métrica, n com valor, n indefinido, mediana, Q1, Q3, mínimo e máximo.
  Inclui `proporcao_censurada`, a fração de episódios de falha censurados por repositório.
- `faixas_por_metrica.csv`: repositórios em cada faixa (Elite, High, Medium, Low) de cada métrica,
  pelas notas de `metricas/classificacao.py`, mais os indefinidos.
- `categorias_c1.csv`: repositórios em cada `categoria_c1`.
- `hist_<metrica>.png`, `faixas_por_metrica.png` e `categorias_c1.png`.

Mediana e quartis usam a interpolação linear do pandas. Métrica indefinida (célula vazia) é
contada à parte e nunca entra como zero. `cfr_b` é opcional: só aparece se a coluna existir no CSV.
"""

import argparse
import os
import sys

import matplotlib

matplotlib.use("Agg")

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd

from metricas.classificacao import CATEGORIAS, nota_cfr, nota_frequencia, nota_lead_time, nota_recuperacao

# métrica -> (função de nota, rótulo do eixo)
METRICAS = {
    "frequencia_semana": (nota_frequencia, "deploys por semana"),
    "lead_time_a_h": (nota_lead_time, "lead time (a), horas"),
    "lead_time_b_h": (nota_lead_time, "lead time (b), horas"),
    "cfr_a": (nota_cfr, "change failure rate (a), fração"),
    "cfr_b": (nota_cfr, "change failure rate (b), fração"),
    "recuperacao_mediana_h": (nota_recuperacao, "tempo de recuperação, horas"),
}
OBRIGATORIAS = ["frequencia_semana", "lead_time_a_h", "lead_time_b_h", "cfr_a", "recuperacao_mediana_h"]
COLUNAS_CENSURA = ["n_episodios", "n_censurados_direita", "n_censurados_esquerda"]
COLUNAS_OBRIGATORIAS = OBRIGATORIAS + COLUNAS_CENSURA + ["categoria_c1"]

FAIXAS = ["Elite", "High", "Medium", "Low"]
CORES = {"Elite": "#2a9d8f", "High": "#8ab17d", "Medium": "#e9c46a", "Low": "#e76f51"}
VARIACAO_PARA_ESCALA_LOG = 100  # máximo ÷ mínimo a partir do qual o eixo vira logarítmico


class ErroDeDescritiva(Exception):
    """CSV ausente ou sem as colunas esperadas; a mensagem diz o que corrigir."""


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        df = ler_repositorios(args.csv)
    except ErroDeDescritiva as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1
    metricas = metricas_presentes(df)
    os.makedirs(args.saida, exist_ok=True)

    tabela = descrever(df, metricas)
    censura = descrever_serie(proporcao_censurada(df), "proporcao_censurada")
    tabela = pd.concat([tabela, censura], ignore_index=True)
    faixas = faixas_por_metrica(df, metricas)
    categorias = categorias_c1(df)

    tabela.to_csv(os.path.join(args.saida, "descritiva.csv"), index=False)
    faixas.to_csv(os.path.join(args.saida, "faixas_por_metrica.csv"), index=False)
    categorias.to_csv(os.path.join(args.saida, "categorias_c1.csv"), index=False)
    for metrica in metricas:
        histograma(df[metrica], metrica, os.path.join(args.saida, f"hist_{metrica}.png"))
    grafico_faixas(faixas, os.path.join(args.saida, "faixas_por_metrica.png"))
    grafico_categorias(categorias, os.path.join(args.saida, "categorias_c1.png"))

    print(tabela.to_string(index=False))
    print(f"\n{len(df)} repositórios; saídas em {args.saida}")
    return 0


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        prog="python -m analise.descritiva",
        description="Mediana, IQR e faixas DORA das métricas das RQ 01 a 04.",
    )
    parser.add_argument("--csv", default=os.path.join("dados", "saida", "repositorios.csv"), help="CSV dos repositórios")
    parser.add_argument("--saida", default=os.path.join("analise", "saida"), help="pasta das tabelas e figuras")
    return parser.parse_args(argv)


def ler_repositorios(caminho: str) -> pd.DataFrame:
    if not os.path.isfile(caminho):
        raise ErroDeDescritiva(f"CSV não encontrado: {caminho}")
    df = pd.read_csv(caminho)
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in df.columns]
    if faltando:
        raise ErroDeDescritiva(f"{caminho} não tem as colunas {', '.join(faltando)}")
    return df


def metricas_presentes(df: pd.DataFrame) -> list[str]:
    """Métricas de `METRICAS` que existem no CSV, na ordem da tabela (`cfr_b` é opcional)."""
    return [m for m in METRICAS if m in df.columns]


def descrever(df: pd.DataFrame, metricas: list[str]) -> pd.DataFrame:
    """Uma linha por métrica: n, n_indefinido, mediana, q1, q3, minimo, maximo."""
    return pd.concat([descrever_serie(df[m], m) for m in metricas], ignore_index=True)


def descrever_serie(serie: pd.Series, nome: str) -> pd.DataFrame:
    valores = pd.to_numeric(serie, errors="coerce").dropna()
    n = len(valores)
    vazio = n == 0
    return pd.DataFrame(
        [
            {
                "metrica": nome,
                "n": n,
                "n_indefinido": len(serie) - n,
                "mediana": np.nan if vazio else valores.median(),
                "q1": np.nan if vazio else valores.quantile(0.25),
                "q3": np.nan if vazio else valores.quantile(0.75),
                "minimo": np.nan if vazio else valores.min(),
                "maximo": np.nan if vazio else valores.max(),
            }
        ]
    )


def proporcao_censurada(df: pd.DataFrame) -> pd.Series:
    """`(n_censurados_direita + n_censurados_esquerda) ÷ n_episodios` por repositório.

    Repositório sem episódios fica indefinido (NaN), em vez de 0.
    """
    censurados = df["n_censurados_direita"] + df["n_censurados_esquerda"]
    episodios = df["n_episodios"].where(df["n_episodios"] > 0)
    return censurados / episodios


def faixas_por_metrica(df: pd.DataFrame, metricas: list[str]) -> pd.DataFrame:
    """Contagem de repositórios em cada faixa de cada métrica, mais os indefinidos."""
    linhas = []
    for metrica in metricas:
        nota = METRICAS[metrica][0]
        contagem = {faixa: 0 for faixa in FAIXAS}
        indefinido = 0
        for valor in df[metrica]:
            pontos = None if pd.isna(valor) else nota(float(valor))
            if pontos is None:
                indefinido += 1
            else:
                contagem[CATEGORIAS[pontos]] += 1
        linhas.append({"metrica": metrica, **contagem, "indefinido": indefinido})
    return pd.DataFrame(linhas)


def categorias_c1(df: pd.DataFrame) -> pd.DataFrame:
    """Repositórios em cada `categoria_c1`; categorias sem repositório aparecem com 0."""
    contagem = df["categoria_c1"].value_counts()
    linhas = [{"categoria": faixa, "n_repositorios": int(contagem.get(faixa, 0))} for faixa in FAIXAS]
    sem_categoria = int(df["categoria_c1"].isna().sum())
    if sem_categoria:
        linhas.append({"categoria": "indefinida", "n_repositorios": sem_categoria})
    return pd.DataFrame(linhas)


def usar_escala_log(valores: pd.Series) -> bool:
    """Escala logarítmica quando todos os valores são positivos e a variação passa de 100 vezes."""
    if valores.empty or valores.min() <= 0:
        return False
    return valores.max() / valores.min() >= VARIACAO_PARA_ESCALA_LOG


def histograma(serie: pd.Series, metrica: str, caminho: str) -> None:
    valores = pd.to_numeric(serie, errors="coerce").dropna()
    figura, eixo = plt.subplots(figsize=(7, 4))
    if valores.empty:
        eixo.text(0.5, 0.5, "sem valores definidos", ha="center", va="center", transform=eixo.transAxes)
    else:
        if usar_escala_log(valores):
            bins = np.geomspace(valores.min(), valores.max(), 31)
            eixo.set_xscale("log")
        else:
            bins = 30
        eixo.hist(valores, bins=bins, color="#2a6f97", edgecolor="white")
        eixo.axvline(valores.median(), color="#c1121f", linestyle="--", label=f"mediana = {valores.median():.3g}")
        eixo.legend(frameon=False)
    eixo.set_xlabel(METRICAS[metrica][1])
    eixo.set_ylabel("repositórios")
    eixo.set_title(f"{metrica} (n = {len(valores)}, indefinidos = {len(serie) - len(valores)})")
    eixo.spines[["top", "right"]].set_visible(False)
    figura.tight_layout()
    figura.savefig(caminho, dpi=150)
    plt.close(figura)


def grafico_faixas(faixas: pd.DataFrame, caminho: str) -> None:
    figura, eixo = plt.subplots(figsize=(8, 0.6 * len(faixas) + 1.5))
    esquerda = np.zeros(len(faixas))
    for faixa in FAIXAS:
        eixo.barh(faixas["metrica"], faixas[faixa], left=esquerda, color=CORES[faixa], label=faixa)
        esquerda += faixas[faixa].to_numpy()
    eixo.barh(faixas["metrica"], faixas["indefinido"], left=esquerda, color="#cccccc", label="indefinido")
    eixo.invert_yaxis()
    eixo.set_xlabel("repositórios")
    eixo.set_title("Repositórios por faixa DORA de cada métrica")
    eixo.legend(ncol=5, frameon=False, loc="upper center", bbox_to_anchor=(0.5, -0.18))
    eixo.spines[["top", "right"]].set_visible(False)
    figura.tight_layout()
    figura.savefig(caminho, dpi=150)
    plt.close(figura)


def grafico_categorias(categorias: pd.DataFrame, caminho: str) -> None:
    figura, eixo = plt.subplots(figsize=(6, 4))
    cores = [CORES.get(c, "#cccccc") for c in categorias["categoria"]]
    barras = eixo.bar(categorias["categoria"], categorias["n_repositorios"], color=cores)
    eixo.bar_label(barras)
    eixo.set_ylabel("repositórios")
    eixo.set_title(f"Categoria DORA geral (C1), n = {int(categorias['n_repositorios'].sum())}")
    eixo.spines[["top", "right"]].set_visible(False)
    figura.tight_layout()
    figura.savefig(caminho, dpi=150)
    plt.close(figura)


if __name__ == "__main__":
    sys.exit(main())
