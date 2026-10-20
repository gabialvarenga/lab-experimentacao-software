"""Comparação das métricas DORA entre grupos de repositórios (RQ 06).

`python -m analise.rq06_fatores`

Para cada fator e cada métrica, testa se a distribuição da métrica difere entre os grupos do
fator: Kruskal-Wallis com 3 ou mais grupos e Mann-Whitney com 2. Os p-valores de todos os
testes executados são corrigidos juntos pelo método de Holm. O tamanho de efeito é
ε² = H / (n − 1) no Kruskal-Wallis e o δ de Cliff = 2·U₁ / (n₁·n₂) − 1 no Mann-Whitney
(U₁ é a estatística de `scipy.stats.mannwhitneyu(x, y)`, com `x` o primeiro grupo).

Fatores:

- `linguagem`: as linguagens com ao menos `--min-linguagem` repositórios; as demais e a
  linguagem vazia formam o grupo `outras`;
- `estrelas`, `contribuidores` e `idade` (`idade_dias`): quartis do valor (Q1 a Q4; valores
  repetidos podem gerar menos de 4 grupos);
- `tipo_projeto`: rótulo de consenso da amostra-ouro (`dados/rotulagem/consenso.csv`), que só
  existe para os 60 repositórios sorteados.

Métricas: `frequencia_semana`, `lead_time_a_h`, `cfr_a` e `recuperacao_mediana_h`; com
`--variantes-b`, também `lead_time_b_h` e `cfr_b`. Grupos com menos de `--min-grupo` valores
definidos ficam fora do teste, e um teste sem ao menos 2 grupos restantes não é executado.

Grava em `--saida` (padrão `analise/saida`): `rq06.csv`, uma linha por fator e métrica, e
`rq06_grupos.csv`, com n, mediana, Q1 e Q3 de cada grupo.
"""

import argparse
import csv
import os
import sys

import numpy as np
import pandas as pd
from scipy import stats
from statsmodels.stats.multitest import multipletests

FATORES = ("linguagem", "estrelas", "contribuidores", "idade", "tipo_projeto")
METRICAS = ("frequencia_semana", "lead_time_a_h", "cfr_a", "recuperacao_mediana_h")
METRICAS_B = ("lead_time_b_h", "cfr_b")
COLUNAS_FATOR = {"estrelas": "estrelas", "contribuidores": "contribuidores", "idade": "idade_dias"}
MIN_GRUPO = 5
MIN_LINGUAGEM = 15
ALFA = 0.05
OUTRAS = "outras"
SEM_GRUPOS = "sem grupos suficientes"

COLUNAS_RQ06 = (
    "fator", "metrica", "status", "teste", "n", "n_grupos", "grupos", "n_excluidos",
    "estatistica", "p_bruto", "p_holm", "significativo_holm",
    "tipo_efeito", "tamanho_efeito", "interpretacao_efeito",
)  # fmt: skip
COLUNAS_GRUPOS = ("fator", "metrica", "grupo", "n", "mediana", "q1", "q3", "faixa")


class ErroDeAnalise(Exception):
    """Entrada ausente ou inválida; a mensagem diz o que corrigir."""


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    metricas = METRICAS + (METRICAS_B if args.variantes_b else ())
    try:
        linhas = ler_repositorios(args.csv, metricas)
        tipos = tipos_de_projeto(linhas, args.consenso)
        resultados, grupos = executar(linhas, tipos, metricas, args.min_grupo, args.min_linguagem)
    except ErroDeAnalise as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    os.makedirs(args.saida, exist_ok=True)
    _gravar(os.path.join(args.saida, "rq06.csv"), COLUNAS_RQ06, resultados)
    _gravar(os.path.join(args.saida, "rq06_grupos.csv"), COLUNAS_GRUPOS, grupos)
    executados = [r for r in resultados if r["status"] == "ok"]
    significativos = [r for r in executados if r["significativo_holm"]]
    print(
        f"{len(resultados)} combinações de fator e métrica; {len(executados)} testes executados; "
        f"{len(significativos)} significativos após Holm (alfa = {ALFA})"
    )
    for r in sorted(significativos, key=lambda r: -abs(r["tamanho_efeito"]))[:10]:
        print(
            f"  {r['fator']} x {r['metrica']}: p_holm={r['p_holm']:.3g} "
            f"{r['tipo_efeito']}={r['tamanho_efeito']:.3f} ({r['interpretacao_efeito']})"
        )
    print(f"saídas em {args.saida}")
    return 0


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    analisador = argparse.ArgumentParser(
        prog="python -m analise.rq06_fatores",
        description="Compara as métricas DORA entre grupos de repositórios (RQ 06).",
    )
    analisador.add_argument(
        "--csv", default=os.path.join("dados", "saida", "repositorios.csv"), help="dataset de repositórios"
    )
    analisador.add_argument(
        "--consenso",
        default=os.path.join("dados", "rotulagem", "consenso.csv"),
        help="consenso da amostra-ouro, de onde vem o tipo de projeto",
    )
    analisador.add_argument("--saida", default=os.path.join("analise", "saida"), help="pasta das saídas")
    analisador.add_argument("--min-grupo", type=int, default=MIN_GRUPO, help="mínimo de valores por grupo no teste")
    analisador.add_argument(
        "--min-linguagem", type=int, default=MIN_LINGUAGEM, help="mínimo de repositórios para uma linguagem ter grupo próprio"
    )
    analisador.add_argument("--variantes-b", action="store_true", help="inclui lead_time_b_h e cfr_b")
    return analisador.parse_args(argv)


# ---------------------------------------------------------------- leitura


def ler_repositorios(caminho: str, metricas: tuple[str, ...] = METRICAS) -> list[dict]:
    """Uma linha por repositório, com números como `float` e vazio como `None`."""
    numericas = ("estrelas", "contribuidores", "idade_dias") + tuple(metricas)
    obrigatorias = ("full_name", "linguagem") + numericas
    try:
        with open(caminho, encoding="utf-8", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            ausentes = [c for c in obrigatorias if c not in (leitor.fieldnames or [])]
            if ausentes:
                raise ErroDeAnalise(f"{caminho} não tem as colunas {', '.join(ausentes)}")
            linhas = []
            for numero, bruta in enumerate(leitor, start=2):
                linha = {"full_name": bruta["full_name"], "linguagem": (bruta["linguagem"] or "").strip()}
                for coluna in numericas:
                    texto = (bruta[coluna] or "").strip()
                    try:
                        linha[coluna] = float(texto) if texto else None
                    except ValueError as erro:
                        raise ErroDeAnalise(f"{caminho}, linha {numero}: {coluna} = {texto!r} não é número") from erro
                linhas.append(linha)
    except OSError as erro:
        raise ErroDeAnalise(f"não foi possível ler {caminho}: {erro.strerror}") from erro
    return linhas


def tipos_de_projeto(linhas: list[dict], caminho_consenso: str) -> list[str | None]:
    """Tipo de projeto de cada linha, pelo consenso; `None` fora da amostra-ouro."""
    try:
        with open(caminho_consenso, encoding="utf-8", newline="") as arquivo:
            consenso = {
                l["full_name"]: l["consenso"] for l in csv.DictReader(arquivo) if l["dimensao"] == "tipo_projeto"
            }
    except OSError as erro:
        raise ErroDeAnalise(f"não foi possível ler {caminho_consenso}: {erro.strerror}") from erro
    return [consenso.get(linha["full_name"]) or None for linha in linhas]


# ---------------------------------------------------------------- fatores


def quartis(valores: list[float | None]) -> list[str | None]:
    """`Q1` a `Q4` pelo quartil do valor; `None` para valor ausente.

    Com valores repetidos, `pandas.qcut(..., duplicates="drop")` junta quartis iguais e sai
    com menos de 4 grupos.
    """
    codigos = pd.qcut(pd.Series(valores, dtype="float"), 4, labels=False, duplicates="drop")
    return [None if pd.isna(c) else f"Q{int(c) + 1}" for c in codigos]


def agrupar_linguagens(linguagens: list[str], minimo: int = MIN_LINGUAGEM) -> list[str]:
    """A própria linguagem se tem ao menos `minimo` repositórios; senão, `outras`."""
    contagem = {}
    for linguagem in linguagens:
        contagem[linguagem] = contagem.get(linguagem, 0) + 1
    return [l if l and contagem[l] >= minimo else OUTRAS for l in linguagens]


def montar_fatores(linhas: list[dict], tipos: list[str | None], min_linguagem: int = MIN_LINGUAGEM) -> dict:
    fatores = {"linguagem": agrupar_linguagens([l["linguagem"] for l in linhas], min_linguagem)}
    for fator in ("estrelas", "contribuidores", "idade"):
        fatores[fator] = quartis([l[COLUNAS_FATOR[fator]] for l in linhas])
    fatores["tipo_projeto"] = list(tipos)
    return fatores


def agrupar(valores: list, rotulos: list, minimo: int = MIN_GRUPO) -> tuple[dict, dict]:
    """`(grupos, excluidos)`: valores definidos por grupo e os grupos abaixo de `minimo`.

    `outras` vem por último; os demais grupos, em ordem alfabética.
    """
    por_grupo = {}
    for valor, rotulo in zip(valores, rotulos):
        if rotulo is not None and valor is not None:
            por_grupo.setdefault(rotulo, []).append(valor)
    ordem = sorted(por_grupo, key=lambda g: (g == OUTRAS, g))
    grupos = {g: por_grupo[g] for g in ordem if len(por_grupo[g]) >= minimo}
    excluidos = {g: len(por_grupo[g]) for g in ordem if len(por_grupo[g]) < minimo}
    return grupos, excluidos


# ---------------------------------------------------------------- estatística


def holm(p_valores: list[float]) -> list[float]:
    """P-valores corrigidos pelo método de Holm (`statsmodels`, `method="holm"`)."""
    if not p_valores:
        return []
    return [float(p) for p in multipletests(p_valores, method="holm")[1]]


def delta_de_cliff(x: list, y: list) -> tuple[float, float]:
    """`(delta, U1)`: δ = 2·U₁ / (n₁·n₂) − 1, com U₁ de `mannwhitneyu(x, y)`."""
    u1 = float(stats.mannwhitneyu(x, y, alternative="two-sided").statistic)
    return 2 * u1 / (len(x) * len(y)) - 1, u1


def interpretar_delta(delta: float) -> str:
    """Romano et al. (2006): |δ| < 0,147 desprezível; < 0,33 pequeno; < 0,474 médio; senão grande."""
    magnitude = abs(delta)
    if magnitude < 0.147:
        return "desprezível"
    if magnitude < 0.33:
        return "pequeno"
    if magnitude < 0.474:
        return "médio"
    return "grande"


def interpretar_epsilon(epsilon: float) -> str:
    """Tomczak e Tomczak (2014): ε² < 0,01 desprezível; < 0,08 pequeno; < 0,26 médio; senão grande."""
    if epsilon < 0.01:
        return "desprezível"
    if epsilon < 0.08:
        return "pequeno"
    if epsilon < 0.26:
        return "médio"
    return "grande"


def testar(grupos: list[list]) -> dict | None:
    """Teste e tamanho de efeito para 2 ou mais grupos; `None` com menos de 2."""
    if len(grupos) < 2:
        return None
    n = sum(len(g) for g in grupos)
    if len(grupos) == 2:
        delta, u1 = delta_de_cliff(grupos[0], grupos[1])
        p = float(stats.mannwhitneyu(grupos[0], grupos[1], alternative="two-sided").pvalue)
        return {
            "teste": "mannwhitney", "n": n, "n_grupos": 2, "estatistica": u1, "p_bruto": p,
            "tipo_efeito": "cliff_delta", "tamanho_efeito": delta, "interpretacao_efeito": interpretar_delta(delta),
        }  # fmt: skip
    h, p = stats.kruskal(*grupos)
    epsilon = float(h) / (n - 1)
    return {
        "teste": "kruskal", "n": n, "n_grupos": len(grupos), "estatistica": float(h), "p_bruto": float(p),
        "tipo_efeito": "epsilon2", "tamanho_efeito": epsilon, "interpretacao_efeito": interpretar_epsilon(epsilon),
    }  # fmt: skip


# ---------------------------------------------------------------- execução


def executar(
    linhas: list[dict],
    tipos: list[str | None],
    metricas: tuple[str, ...] = METRICAS,
    min_grupo: int = MIN_GRUPO,
    min_linguagem: int = MIN_LINGUAGEM,
) -> tuple[list[dict], list[dict]]:
    """`(resultados, grupos)`: uma linha por fator e métrica, e uma por grupo testado."""
    fatores = montar_fatores(linhas, tipos, min_linguagem)
    resultados, tabela_grupos = [], []
    for fator in FATORES:
        rotulos = fatores[fator]
        faixas = _faixas(fator, linhas, rotulos)
        for metrica in metricas:
            valores = [l[metrica] for l in linhas]
            grupos, excluidos = agrupar(valores, rotulos, min_grupo)
            teste = testar(list(grupos.values()))
            resultado = {c: None for c in COLUNAS_RQ06}
            resultado.update(
                fator=fator, metrica=metrica, status="ok" if teste else SEM_GRUPOS,
                grupos="|".join(f"{g}:{len(v)}" for g, v in grupos.items()),
                n_excluidos=sum(excluidos.values()),
            )  # fmt: skip
            if teste:
                resultado.update(teste)
            resultados.append(resultado)
            for grupo, v in grupos.items():
                q1, mediana, q3 = np.percentile(v, [25, 50, 75])
                tabela_grupos.append(
                    {
                        "fator": fator, "metrica": metrica, "grupo": grupo, "n": len(v),
                        "mediana": float(mediana), "q1": float(q1), "q3": float(q3), "faixa": faixas.get(grupo),
                    }  # fmt: skip
                )
    executados = [r for r in resultados if r["status"] == "ok"]
    for r, p_holm in zip(executados, holm([r["p_bruto"] for r in executados])):
        r["p_holm"] = p_holm
        r["significativo_holm"] = p_holm < ALFA
    return resultados, tabela_grupos


def _faixas(fator: str, linhas: list[dict], rotulos: list) -> dict[str, str]:
    """Intervalo de valores do fator em cada quartil (vazio nos fatores categóricos)."""
    if fator not in COLUNAS_FATOR:
        return {}
    por_grupo = {}
    for linha, rotulo in zip(linhas, rotulos):
        valor = linha[COLUNAS_FATOR[fator]]
        if rotulo is not None and valor is not None:
            por_grupo.setdefault(rotulo, []).append(valor)
    return {g: f"{min(v):.0f}-{max(v):.0f}" for g, v in por_grupo.items()}


def _gravar(caminho: str, colunas, linhas: list[dict]) -> None:
    with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=colunas, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows({c: "" if linha.get(c) is None else linha[c] for c in colunas} for linha in linhas)


if __name__ == "__main__":
    sys.exit(main())
