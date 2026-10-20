"""Correlação de Spearman entre frequência de deploy e CFR (RQ 05).

`python -m analise.rq05_spearman`

Calcula `scipy.stats.spearmanr(frequencia_semana, cfr)` para as duas variantes do CFR: `cfr_a`
(proporção de workflow runs com falha) e `cfr_b` (proporção de releases seguidas por uma release
corretiva). Reporta ρ, p-valor e n. Repositórios com valor indefinido em um dos lados ficam fora
do par e são contados em `n_excluidos`. Empates (por exemplo, vários repositórios com CFR igual a
0) recebem o posto médio, que é o tratamento padrão do `scipy`.

Grava em `--saida` (padrão `analise/saida`): `rq05.csv`, uma linha por variante, e os gráficos de
dispersão `rq05_cfr_a.png` e `rq05_cfr_b.png`, com a frequência em escala logarítmica.

Correlação não implica causalidade: um ρ positivo entre frequência e CFR (b) é em parte efeito da
própria definição da métrica (quem publica muitas releases tem mais chance de ter uma release
corretiva em até 7 dias).
"""

import argparse
import csv
import math
import os
import sys
import warnings

import numpy as np
from scipy import stats

VARIANTES = ("cfr_a", "cfr_b")
COLUNAS_RQ05 = ("variante", "n", "n_excluidos", "n_y_zero", "rho", "p_valor", "direcao", "interpretacao")
MIN_PARES = 3


class ErroDeAnalise(Exception):
    """Entrada ausente ou inválida; a mensagem diz o que corrigir."""


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        dados = ler_repositorios(args.csv)
    except ErroDeAnalise as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    os.makedirs(args.saida, exist_ok=True)
    resultados = []
    for variante in VARIANTES:
        resultado = correlacao(dados["frequencia_semana"], dados[variante])
        resultados.append({"variante": variante, **resultado})
        figura(
            dados["frequencia_semana"], dados[variante], variante, resultado,
            os.path.join(args.saida, f"rq05_{variante}.png"),
        )  # fmt: skip
    with open(os.path.join(args.saida, "rq05.csv"), "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_RQ05, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows({c: "" if r[c] is None else r[c] for c in COLUNAS_RQ05} for r in resultados)
    for r in resultados:
        rho = "indefinido" if r["rho"] is None else f"{r['rho']:.3f}"
        p = "indefinido" if r["p_valor"] is None else f"{r['p_valor']:.3g}"
        print(
            f"frequencia_semana x {r['variante']}: rho={rho} p={p} n={r['n']} "
            f"(excluídos {r['n_excluidos']}) {r['direcao']} {r['interpretacao']}"
        )
    print(f"saídas em {args.saida}")
    return 0


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    analisador = argparse.ArgumentParser(
        prog="python -m analise.rq05_spearman",
        description="Correlação de Spearman entre frequência de deploy e CFR (RQ 05).",
    )
    analisador.add_argument(
        "--csv", default=os.path.join("dados", "saida", "repositorios.csv"), help="dataset de repositórios"
    )
    analisador.add_argument("--saida", default=os.path.join("analise", "saida"), help="pasta das saídas")
    return analisador.parse_args(argv)


def ler_repositorios(caminho: str) -> dict[str, list[float | None]]:
    """`frequencia_semana`, `cfr_a` e `cfr_b` de cada repositório; vazio vira `None`."""
    colunas = ("frequencia_semana",) + VARIANTES
    try:
        with open(caminho, encoding="utf-8", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            ausentes = [c for c in colunas if c not in (leitor.fieldnames or [])]
            if ausentes:
                raise ErroDeAnalise(f"{caminho} não tem as colunas {', '.join(ausentes)}")
            dados = {c: [] for c in colunas}
            for numero, linha in enumerate(leitor, start=2):
                for coluna in colunas:
                    texto = (linha[coluna] or "").strip()
                    try:
                        dados[coluna].append(float(texto) if texto else None)
                    except ValueError as erro:
                        raise ErroDeAnalise(f"{caminho}, linha {numero}: {coluna} = {texto!r} não é número") from erro
    except OSError as erro:
        raise ErroDeAnalise(f"não foi possível ler {caminho}: {erro.strerror}") from erro
    return dados


def correlacao(x: list, y: list) -> dict:
    """ρ de Spearman, p-valor e contagens para os pares com `x` e `y` definidos.

    `rho` e `p_valor` são `None` com menos de 3 pares ou com uma das séries constante, casos em
    que o coeficiente não é definido. `n_y_zero` conta os pares com `y == 0`, que geram empates.
    """
    pares = [(a, b) for a, b in zip(x, y) if a is not None and b is not None]
    resultado = {
        "n": len(pares),
        "n_excluidos": len(x) - len(pares),
        "n_y_zero": sum(b == 0 for _, b in pares),
        "rho": None,
        "p_valor": None,
        "direcao": "",
        "interpretacao": "indefinido",
    }
    if len(pares) < MIN_PARES:
        return resultado
    with warnings.catch_warnings(), np.errstate(all="ignore"):
        warnings.simplefilter("ignore")
        calculo = stats.spearmanr([a for a, _ in pares], [b for _, b in pares])
    if math.isnan(calculo.statistic):
        return resultado
    resultado["rho"] = float(calculo.statistic)
    resultado["p_valor"] = float(calculo.pvalue)
    resultado["direcao"] = "positiva" if resultado["rho"] > 0 else ("negativa" if resultado["rho"] < 0 else "nula")
    resultado["interpretacao"] = interpretar(resultado["rho"])
    return resultado


def interpretar(rho: float) -> str:
    """Magnitude de Cohen (1988): |ρ| < 0,1 desprezível; < 0,3 fraca; < 0,5 moderada; senão forte."""
    magnitude = abs(rho)
    if magnitude < 0.1:
        return "desprezível"
    if magnitude < 0.3:
        return "fraca"
    if magnitude < 0.5:
        return "moderada"
    return "forte"


def figura(x: list, y: list, variante: str, resultado: dict, caminho: str) -> None:
    """Dispersão de frequência (escala logarítmica) contra o CFR, com ρ, p e n no título."""
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    pontos = [(a, b) for a, b in zip(x, y) if a is not None and b is not None and a > 0]  # log exige x > 0
    grafico, eixo = plt.subplots(figsize=(6.2, 4.4))
    if pontos:
        eixo.scatter([a for a, _ in pontos], [b for _, b in pontos], s=18, alpha=0.55, edgecolors="none")
    eixo.set_xscale("log")
    eixo.set_xlabel("frequência de deploy (releases por semana, escala logarítmica)")
    eixo.set_ylabel(f"{variante} (fração de 0 a 1)")
    rho = "indefinido" if resultado["rho"] is None else f"{resultado['rho']:.2f}"
    p = "indefinido" if resultado["p_valor"] is None else f"{resultado['p_valor']:.2g}"
    eixo.set_title(f"Spearman: rho = {rho}, p = {p}, n = {resultado['n']}")
    eixo.grid(alpha=0.25)
    grafico.tight_layout()
    grafico.savefig(caminho, dpi=150)
    plt.close(grafico)


if __name__ == "__main__":
    sys.exit(main())
