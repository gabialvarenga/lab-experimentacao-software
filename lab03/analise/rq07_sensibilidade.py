"""Análise de sensibilidade da classificação DORA às definições operacionais (RQ 07).

`python -m analise.rq07_sensibilidade`

Lê `categoria_c1`, `categoria_c2` e `categoria_c3` de `dados/saida/repositorios.csv` e compara
as combinações par a par (C1×C2, C1×C3, C2×C3): percentual de repositórios que mudaram de
categoria e kappa de Cohen ponderado linear sobre as categorias ordenadas
(Low < Medium < High < Elite). Repositório com categoria indefinida em um dos lados fica fora
do par e é contado em `n_excluidos`.

Grava em `--saida` (padrão `analise/saida`):

- `rq07.csv`: uma linha por par, com n, percentuais de mudança, direção e kappa;
- `rq07_matrizes.csv`: matriz de transição de cada par, em formato longo (`de`, `para`, `n`);
- `rq07_categorias.csv`: quantos repositórios há em cada categoria de cada combinação;
- `rq07_metricas.csv`: o mesmo percentual de mudança para cada métrica sozinha (frequência, lead time e
  CFR, que são as que variam entre as combinações), a partir da nota de cada uma. Só é gerado quando o
  CSV traz as colunas das métricas de C2 e C3;
- `rq07_matrizes.png`: as três matrizes de transição.

As colunas de C2 e C3 só são preenchidas depois da coleta das variantes (S03-07).
"""

import argparse
import csv
import itertools
import os
import sys
import warnings

import numpy as np
from sklearn.metrics import cohen_kappa_score

from analise.concordancia import interpretar
from metricas.classificacao import nota_cfr, nota_frequencia, nota_lead_time
from metricas.sensibilidade import percentual_mudanca

CATEGORIAS = ("Low", "Medium", "High", "Elite")  # da pior para a melhor
COMBINACOES = ("c1", "c2", "c3")
PARES = tuple(itertools.combinations(COMBINACOES, 2))
COLUNAS_RQ07 = (
    "combinacao_x", "combinacao_y", "n", "n_excluidos", "n_mudaram", "pct_mudanca",
    "n_melhor", "n_pior", "n_vizinha", "kappa_linear", "interpretacao",
)  # fmt: skip

# Coluna de cada métrica em cada combinação. O tempo de recuperação é o de C1 nas três, e fica de fora.
METRICAS = {
    "frequencia": {"c1": "frequencia_semana", "c2": "frequencia_semana_c2", "c3": "frequencia_semana_c3"},
    "lead_time": {"c1": "lead_time_a_h", "c2": "lead_time_b_h_c2", "c3": "lead_time_b_h_c3"},
    "cfr": {"c1": "cfr_a", "c2": "cfr_b_c2", "c3": "cfr_a"},
}
NOTAS = {"frequencia": nota_frequencia, "lead_time": nota_lead_time, "cfr": nota_cfr}
COLUNAS_METRICAS = (
    "metrica", "combinacao_x", "combinacao_y", "n", "n_mudaram", "pct_mudanca",
    "n_melhor", "n_pior", "mediana_x", "mediana_y",
)  # fmt: skip


class ErroDeAnalise(Exception):
    """Entrada ausente ou inválida; a mensagem diz o que corrigir."""


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        categorias = ler_categorias(args.csv)
        resultados = [comparar_par(x, y, categorias[x], categorias[y]) for x, y in PARES]
        if all(r["n"] == 0 for r in resultados):
            raise ErroDeAnalise(
                "nenhum repositório tem C2 ou C3 definidas em "
                f"{args.csv}: rode a coleta das variantes com coleta.variantes_rq07: true (S03-07)"
            )
    except ErroDeAnalise as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    os.makedirs(args.saida, exist_ok=True)
    matrizes = {(x, y): matriz_de_transicao(categorias[x], categorias[y]) for x, y in PARES}
    _gravar(os.path.join(args.saida, "rq07.csv"), COLUNAS_RQ07, resultados)
    _gravar(
        os.path.join(args.saida, "rq07_matrizes.csv"),
        ("combinacao_x", "combinacao_y", "de", "para", "n"),
        [
            {"combinacao_x": x, "combinacao_y": y, "de": de, "para": para, "n": matriz[de][para]}
            for (x, y), matriz in matrizes.items()
            for de in CATEGORIAS
            for para in CATEGORIAS
        ],
    )
    _gravar(
        os.path.join(args.saida, "rq07_categorias.csv"),
        ("combinacao", "categoria", "n"),
        [
            {"combinacao": c, "categoria": categoria, "n": n}
            for c in COMBINACOES
            for categoria, n in distribuicao(categorias[c]).items()
        ],
    )
    valores = ler_valores(args.csv)
    if valores is not None:
        _gravar(
            os.path.join(args.saida, "rq07_metricas.csv"),
            COLUNAS_METRICAS,
            [comparar_metrica(m, x, y, valores) for m in METRICAS for x, y in PARES],
        )
    figura(matrizes, os.path.join(args.saida, "rq07_matrizes.png"))
    for r in resultados:
        print(
            f"{r['combinacao_x']} x {r['combinacao_y']}: n={r['n']} (excluídos {r['n_excluidos']}) "
            f"mudaram={_fmt(r['pct_mudanca'], '%')} kappa={_fmt(r['kappa_linear'])} ({r['interpretacao']})"
        )
    print(f"saídas em {args.saida}")
    return 0


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    analisador = argparse.ArgumentParser(
        prog="python -m analise.rq07_sensibilidade",
        description="Compara a classificação DORA entre as combinações C1, C2 e C3 (RQ 07).",
    )
    analisador.add_argument(
        "--csv", default=os.path.join("dados", "saida", "repositorios.csv"), help="dataset de repositórios"
    )
    analisador.add_argument("--saida", default=os.path.join("analise", "saida"), help="pasta das saídas")
    return analisador.parse_args(argv)


def ler_categorias(caminho: str) -> dict[str, list[str | None]]:
    """`{"c1": [...], "c2": [...], "c3": [...]}`, na ordem das linhas; célula vazia vira `None`."""
    try:
        with open(caminho, encoding="utf-8", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            colunas = {c: f"categoria_{c}" for c in COMBINACOES}
            ausentes = [coluna for coluna in colunas.values() if coluna not in (leitor.fieldnames or [])]
            if ausentes:
                raise ErroDeAnalise(
                    f"{caminho} não tem as colunas {', '.join(ausentes)}: o pipeline precisa rodar com "
                    "coleta.variantes_rq07: true (S03-07)"
                )
            categorias = {c: [] for c in COMBINACOES}
            for numero, linha in enumerate(leitor, start=2):
                for c, coluna in colunas.items():
                    valor = (linha[coluna] or "").strip()
                    if valor and valor not in CATEGORIAS:
                        raise ErroDeAnalise(
                            f"{caminho}, linha {numero}: {coluna} = {valor!r} "
                            f"(esperado {', '.join(reversed(CATEGORIAS))} ou vazio)"
                        )
                    categorias[c].append(valor or None)
    except OSError as erro:
        raise ErroDeAnalise(f"não foi possível ler {caminho}: {erro.strerror}") from erro
    return categorias


def ler_valores(caminho: str) -> dict[str, list[float | None]] | None:
    """Valores das colunas de `METRICAS`, na ordem das linhas; célula vazia vira `None`.

    Devolve `None` quando o CSV não traz alguma dessas colunas (o `rq07_metricas.csv` não é gerado).
    """
    colunas = {coluna for por_combinacao in METRICAS.values() for coluna in por_combinacao.values()}
    with open(caminho, encoding="utf-8", newline="") as arquivo:
        leitor = csv.DictReader(arquivo)
        if not colunas <= set(leitor.fieldnames or []):
            return None
        valores = {coluna: [] for coluna in colunas}
        for linha in leitor:
            for coluna in colunas:
                texto = (linha[coluna] or "").strip()
                valores[coluna].append(float(texto) if texto else None)
    return valores


def comparar_metrica(metrica: str, x: str, y: str, valores: dict) -> dict:
    """Percentual de repositórios cuja nota da `metrica` muda entre as combinações `x` e `y`.

    Compara as notas de 1 (Low) a 4 (Elite), só nos repositórios com a métrica definida nas duas
    combinações. `n_melhor` e `n_pior` contam quem sobe ou desce de `x` para `y`. As medianas são
    as dos valores definidos de cada combinação, e não só dos pares.
    """
    valores_x = valores[METRICAS[metrica][x]]
    valores_y = valores[METRICAS[metrica][y]]
    nota = NOTAS[metrica]
    pares = [
        (nota(a), nota(b)) for a, b in zip(valores_x, valores_y) if a is not None and b is not None
    ]
    definidos_x = [v for v in valores_x if v is not None]
    definidos_y = [v for v in valores_y if v is not None]
    return {
        "metrica": metrica,
        "combinacao_x": x,
        "combinacao_y": y,
        "n": len(pares),
        "n_mudaram": sum(a != b for a, b in pares),
        "pct_mudanca": 100 * sum(a != b for a, b in pares) / len(pares) if pares else None,
        "n_melhor": sum(b > a for a, b in pares),
        "n_pior": sum(b < a for a, b in pares),
        "mediana_x": float(np.median(definidos_x)) if definidos_x else None,
        "mediana_y": float(np.median(definidos_y)) if definidos_y else None,
    }


def comparar_par(x: str, y: str, cat_x: list, cat_y: list) -> dict:
    """Métricas de concordância entre as classificações das combinações `x` e `y`.

    As listas são pareadas pela posição (mesmo repositório). `n` conta os pares com as duas
    categorias definidas, e `n_excluidos`, os demais. `n_melhor` e `n_pior` contam os
    repositórios que sobem ou descem de `x` para `y`, e `n_vizinha`, as mudanças de uma única
    categoria. `kappa_linear` é `None` quando o kappa é indefinido (uma só categoria nos dois
    lados) e `pct_mudanca` e o kappa são `None` sem nenhum par.
    """
    pares = [(a, b) for a, b in zip(cat_x, cat_y) if a is not None and b is not None]
    linha = {
        "combinacao_x": x,
        "combinacao_y": y,
        "n": len(pares),
        "n_excluidos": len(cat_x) - len(pares),
        "n_mudaram": sum(a != b for a, b in pares),
        "pct_mudanca": None,
        "n_melhor": sum(CATEGORIAS.index(b) > CATEGORIAS.index(a) for a, b in pares),
        "n_pior": sum(CATEGORIAS.index(b) < CATEGORIAS.index(a) for a, b in pares),
        "n_vizinha": sum(abs(CATEGORIAS.index(b) - CATEGORIAS.index(a)) == 1 for a, b in pares),
        "kappa_linear": None,
        "interpretacao": "indefinido",
    }
    if not pares:
        return linha
    linha["pct_mudanca"] = percentual_mudanca(cat_x, cat_y)
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        kappa = cohen_kappa_score(
            [a for a, _ in pares], [b for _, b in pares], labels=list(CATEGORIAS), weights="linear"
        )
    if not np.isnan(kappa):
        linha["kappa_linear"] = float(kappa)
        linha["interpretacao"] = interpretar(float(kappa))
    return linha


def matriz_de_transicao(cat_x: list, cat_y: list) -> dict[str, dict[str, int]]:
    """`matriz[de][para]`: repositórios que vão da categoria `de` em `x` para `para` em `y`."""
    matriz = {de: {para: 0 for para in CATEGORIAS} for de in CATEGORIAS}
    for de, para in zip(cat_x, cat_y):
        if de is not None and para is not None:
            matriz[de][para] += 1
    return matriz


def distribuicao(categorias: list) -> dict[str, int]:
    """Quantos repositórios há em cada categoria (as indefinidas não entram)."""
    return {categoria: categorias.count(categoria) for categoria in reversed(CATEGORIAS)}


def figura(matrizes: dict, caminho: str) -> None:
    """Uma matriz de transição por par, com a contagem em cada célula."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    ordem = list(reversed(CATEGORIAS))  # Elite no topo e à esquerda
    grafico, eixos = plt.subplots(1, len(matrizes), figsize=(4.2 * len(matrizes), 4.2), squeeze=False)
    for eixo, ((x, y), matriz) in zip(eixos[0], matrizes.items()):
        valores = np.array([[matriz[de][para] for para in ordem] for de in ordem])
        eixo.imshow(valores, cmap="Blues")
        eixo.set_xticks(range(len(ordem)), ordem, rotation=45)
        eixo.set_yticks(range(len(ordem)), ordem)
        eixo.set_xlabel(f"categoria em {y.upper()}")
        eixo.set_ylabel(f"categoria em {x.upper()}")
        eixo.set_title(f"{x.upper()} × {y.upper()}")
        corte = valores.max() / 2 if valores.max() else 0
        for i, j in itertools.product(range(len(ordem)), repeat=2):
            eixo.text(j, i, valores[i, j], ha="center", va="center", color="white" if valores[i, j] > corte else "black")
    grafico.tight_layout()
    grafico.savefig(caminho, dpi=150)
    plt.close(grafico)


def _gravar(caminho: str, colunas, linhas: list[dict]) -> None:
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows({c: "" if linha[c] is None else linha[c] for c in colunas} for linha in linhas)


def _fmt(valor, sufixo: str = "") -> str:
    return "indefinido" if valor is None else f"{valor:.3f}{sufixo}"


if __name__ == "__main__":
    sys.exit(main())
