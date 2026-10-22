"""Distribuição do *rework rate* e comparação com o CFR (b) (RQ 08).

`python -m analise.rq08_rework`

Lê `rework_rate` e `cfr_b` de `--csv` (padrão `dados/saida/repositorios.csv`) e a linha da versão
`VERSAO_HEURISTICA` da heurística de release corretiva em `--heuristica` (padrão
`dados/rotulagem/versoes_heuristica.csv`). Grava em `--saida` (padrão `analise/saida`):

- `rq08.csv`: uma linha por métrica (`rework_rate` e `cfr_b`) com n, indefinidos, zeros, mediana,
  Q1, Q3, IQR, mínimo e máximo. As colunas do par (`comparado_com` em diante) só são preenchidas
  na linha do `rework_rate`: ρ de Spearman com o `cfr_b`, contagens de pares em que o *rework
  rate* é maior, menor ou igual, e o teste de Wilcoxon pareado unilateral (H1: *rework rate* >
  CFR (b)) com a correlação rank-biserial pareada como tamanho de efeito. As duas linhas trazem a
  versão, a precisão, o recall e o F1 da heurística, que é a mesma nas duas métricas;
- `rq08_hist.png`: histogramas sobrepostos das duas métricas, com as medianas;
- `rq08_cfr_b.png`: dispersão do *rework rate* contra o CFR (b), com a diagonal y = x.

Em que as duas métricas diferem: o CFR (b) atribui a falha à release que precisou de correção e
só conta correções publicadas em até 7 dias; o *rework rate* conta as próprias releases
corretivas, inclusive as publicadas depois desse prazo e as que corrigem outra correção.

Repositório sem nenhuma release avaliável tem `rework_rate` vazio: fica fora da distribuição
(contado em `n_indefinido`) e do par (contado em `n_excluidos`), e nunca entra como 0. Mediana e
quartis usam a interpolação linear, como `analise/descritiva.py`. No Wilcoxon, os pares
empatados (diferença 0) são descartados (`zero_method="wilcox"`, o padrão do `scipy`) e contados
em `n_empates`.

Limitação: as duas métricas dependem da heurística de release corretiva, cujo F1 contra a
amostra-ouro (versão 3: 0,644) fica abaixo da meta de 0,70 do enunciado. Os valores herdam os
falsos positivos e os falsos negativos dela, e as colunas `*_heuristica` registram isso na tabela.
"""

import argparse
import csv
import math
import os
import sys
import warnings

import numpy as np
from scipy import stats

from analise.rq05_spearman import MIN_PARES, ErroDeAnalise, correlacao, interpretar

METRICAS = ("rework_rate", "cfr_b")
VERSAO_HEURISTICA = 3  # a de `metricas/corretiva.py`, usada no `rework_rate` e no `cfr_b`
COLUNAS_HEURISTICA = ("precisao", "recall", "f1")
COLUNAS_RQ08 = (
    "metrica", "n", "n_indefinido", "n_zero", "mediana", "q1", "q3", "iqr", "minimo", "maximo",
    "comparado_com", "n_pares", "n_excluidos", "rho", "p_valor_spearman", "direcao", "interpretacao_rho",
    "n_maior", "n_menor", "n_empates", "w_mais", "p_valor_wilcoxon", "rank_biserial",
    "interpretacao_rank_biserial",
    "versao_heuristica", "precisao_heuristica", "recall_heuristica", "f1_heuristica",
)  # fmt: skip


def main(argv: list[str] | None = None) -> int:
    args = _argumentos(argv)
    try:
        dados = ler_repositorios(args.csv)
        heuristica = ler_heuristica(args.heuristica, VERSAO_HEURISTICA)
    except ErroDeAnalise as erro:
        print(f"erro: {erro}", file=sys.stderr)
        return 1

    rework, cfr_b = dados["rework_rate"], dados["cfr_b"]
    rho = correlacao(cfr_b, rework)
    pareada = comparacao_pareada(rework, cfr_b)
    par = {
        "comparado_com": "cfr_b",
        "n_pares": rho["n"],
        "n_excluidos": rho["n_excluidos"],
        "rho": rho["rho"],
        "p_valor_spearman": rho["p_valor"],
        "direcao": rho["direcao"],
        "interpretacao_rho": rho["interpretacao"],
        **pareada,
    }
    da_heuristica = {
        "versao_heuristica": VERSAO_HEURISTICA,
        **{f"{c}_heuristica": heuristica[c] for c in COLUNAS_HEURISTICA},
    }
    linhas = [
        {"metrica": "rework_rate", **distribuicao(rework), **par, **da_heuristica},
        {"metrica": "cfr_b", **distribuicao(cfr_b), **da_heuristica},
    ]

    os.makedirs(args.saida, exist_ok=True)
    with open(os.path.join(args.saida, "rq08.csv"), "w", encoding="utf-8", newline="") as arquivo:
        escritor = csv.DictWriter(arquivo, fieldnames=COLUNAS_RQ08, lineterminator="\n")
        escritor.writeheader()
        escritor.writerows({c: "" if linha.get(c) is None else linha[c] for c in COLUNAS_RQ08} for linha in linhas)
    histogramas(rework, cfr_b, os.path.join(args.saida, "rq08_hist.png"))
    dispersao(rework, cfr_b, rho, os.path.join(args.saida, "rq08_cfr_b.png"))

    for linha in linhas:
        print(
            f"{linha['metrica']}: n={linha['n']} (indefinidos {linha['n_indefinido']}) "
            f"mediana={_numero(linha['mediana'])} IQR={_numero(linha['iqr'])} "
            f"[{_numero(linha['q1'])}; {_numero(linha['q3'])}]"
        )
    print(
        f"rework_rate x cfr_b: rho={_numero(par['rho'])} p={_numero(par['p_valor_spearman'], '.3g')} "
        f"n={par['n_pares']} (excluídos {par['n_excluidos']}) {par['direcao']} {par['interpretacao_rho']}"
    )
    print(
        f"rework_rate > cfr_b: {par['n_maior']} maior, {par['n_menor']} menor, {par['n_empates']} empates; "
        f"Wilcoxon p={_numero(par['p_valor_wilcoxon'], '.3g')} "
        f"rank-biserial={_numero(par['rank_biserial'])} {par['interpretacao_rank_biserial']}"
    )
    print(f"heurística v{VERSAO_HEURISTICA}: F1={heuristica['f1']:.3f}; saídas em {args.saida}")
    return 0


def _argumentos(argv: list[str] | None) -> argparse.Namespace:
    analisador = argparse.ArgumentParser(
        prog="python -m analise.rq08_rework",
        description="Distribuição do rework rate e comparação com o CFR (b) (RQ 08).",
    )
    analisador.add_argument(
        "--csv", default=os.path.join("dados", "saida", "repositorios.csv"), help="dataset de repositórios"
    )
    analisador.add_argument(
        "--heuristica",
        default=os.path.join("dados", "rotulagem", "versoes_heuristica.csv"),
        help="precisão, recall e F1 de cada versão da heurística de release corretiva",
    )
    analisador.add_argument("--saida", default=os.path.join("analise", "saida"), help="pasta das saídas")
    return analisador.parse_args(argv)


def _numero(valor, formato: str = ".3f") -> str:
    return "indefinido" if valor is None else format(valor, formato)


def ler_repositorios(caminho: str) -> dict[str, list[float | None]]:
    """`rework_rate` e `cfr_b` de cada repositório; vazio vira `None`."""
    try:
        with open(caminho, encoding="utf-8", newline="") as arquivo:
            leitor = csv.DictReader(arquivo)
            ausentes = [c for c in METRICAS if c not in (leitor.fieldnames or [])]
            if ausentes:
                raise ErroDeAnalise(f"{caminho} não tem as colunas {', '.join(ausentes)}")
            dados = {c: [] for c in METRICAS}
            for numero, linha in enumerate(leitor, start=2):
                for coluna in METRICAS:
                    texto = (linha[coluna] or "").strip()
                    try:
                        dados[coluna].append(float(texto) if texto else None)
                    except ValueError as erro:
                        raise ErroDeAnalise(f"{caminho}, linha {numero}: {coluna} = {texto!r} não é número") from erro
    except OSError as erro:
        raise ErroDeAnalise(f"não foi possível ler {caminho}: {erro.strerror}") from erro
    return dados


def ler_heuristica(caminho: str, versao: int) -> dict[str, float]:
    """Precisão, recall e F1 da linha `versao` de `versoes_heuristica.csv`."""
    try:
        with open(caminho, encoding="utf-8", newline="") as arquivo:
            linhas = list(csv.DictReader(arquivo))
    except OSError as erro:
        raise ErroDeAnalise(f"não foi possível ler {caminho}: {erro.strerror}") from erro
    for linha in linhas:
        if (linha.get("versao") or "").strip() == str(versao):
            try:
                return {c: float(linha[c]) for c in COLUNAS_HEURISTICA}
            except (KeyError, TypeError, ValueError) as erro:
                raise ErroDeAnalise(f"{caminho}: a versão {versao} não tem precisão, recall e F1 numéricos") from erro
    raise ErroDeAnalise(f"{caminho} não tem a versão {versao} da heurística")


def distribuicao(valores: list[float | None]) -> dict:
    """n, indefinidos, zeros, mediana, Q1, Q3, IQR, mínimo e máximo dos valores definidos."""
    definidos = np.array([v for v in valores if v is not None], dtype=float)
    resultado = {"n": len(definidos), "n_indefinido": len(valores) - len(definidos), "n_zero": int((definidos == 0).sum())}
    if not len(definidos):
        return {**resultado, **dict.fromkeys(("mediana", "q1", "q3", "iqr", "minimo", "maximo"))}
    q1, mediana, q3 = (float(q) for q in np.quantile(definidos, [0.25, 0.5, 0.75]))
    return {
        **resultado,
        "mediana": mediana,
        "q1": q1,
        "q3": q3,
        "iqr": q3 - q1,
        "minimo": float(definidos.min()),
        "maximo": float(definidos.max()),
    }


def comparacao_pareada(x: list, y: list) -> dict:
    """Wilcoxon pareado unilateral (H1: `x` > `y`) e rank-biserial pareada, nos pares definidos.

    Os pares com `x == y` são descartados do teste (`zero_method="wilcox"`) e contados em
    `n_empates`. `w_mais` é a soma dos postos de |x − y| nos pares com `x > y`, e a rank-biserial
    é `(W+ − W−) ÷ (W+ + W−)`, de −1 (todo par com `x < y`) a 1 (todo par com `x > y`). Teste e
    efeito ficam `None` com menos de `MIN_PARES` pares não empatados.
    """
    diferencas = np.array([a - b for a, b in zip(x, y) if a is not None and b is not None], dtype=float)
    resultado = {
        "n_maior": int((diferencas > 0).sum()),
        "n_menor": int((diferencas < 0).sum()),
        "n_empates": int((diferencas == 0).sum()),
        "w_mais": None,
        "p_valor_wilcoxon": None,
        "rank_biserial": None,
        "interpretacao_rank_biserial": "indefinido",
    }
    nao_nulas = diferencas[diferencas != 0]
    if len(nao_nulas) < MIN_PARES:
        return resultado
    postos = stats.rankdata(np.abs(nao_nulas))
    w_mais = float(postos[nao_nulas > 0].sum())
    w_menos = float(postos[nao_nulas < 0].sum())
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        teste = stats.wilcoxon(nao_nulas, alternative="greater", zero_method="wilcox")
    if math.isnan(teste.pvalue):
        return resultado
    resultado["w_mais"] = w_mais
    resultado["p_valor_wilcoxon"] = float(teste.pvalue)
    resultado["rank_biserial"] = (w_mais - w_menos) / (w_mais + w_menos)
    resultado["interpretacao_rank_biserial"] = interpretar(resultado["rank_biserial"])
    return resultado


def _pyplot():
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    return plt


def histogramas(rework: list, cfr_b: list, caminho: str) -> None:
    """Histogramas sobrepostos das duas métricas, de 0 a 1, com as medianas tracejadas."""
    plt = _pyplot()
    grafico, eixo = plt.subplots(figsize=(7, 4))
    faixas = np.linspace(0, 1, 21)
    for nome, valores, cor in (("rework_rate", rework, "#2a6f97"), ("cfr_b", cfr_b, "#e76f51")):
        definidos = [v for v in valores if v is not None]
        if not definidos:
            continue
        mediana = float(np.median(definidos))
        eixo.hist(definidos, bins=faixas, color=cor, alpha=0.5, edgecolor="white", label=f"{nome} (n = {len(definidos)})")
        eixo.axvline(mediana, color=cor, linestyle="--", label=f"mediana {nome} = {mediana:.3g}")
    eixo.set_xlim(0, 1)
    eixo.set_xlabel("fração de releases (0 a 1)")
    eixo.set_ylabel("repositórios")
    eixo.set_title("rework rate e CFR (b)")
    eixo.legend(frameon=False)
    eixo.spines[["top", "right"]].set_visible(False)
    grafico.tight_layout()
    grafico.savefig(caminho, dpi=150)
    plt.close(grafico)


def dispersao(rework: list, cfr_b: list, resultado: dict, caminho: str) -> None:
    """CFR (b) no eixo x e *rework rate* no y; acima da diagonal, o *rework rate* é maior."""
    plt = _pyplot()
    pontos = [(b, r) for r, b in zip(rework, cfr_b) if r is not None and b is not None]
    grafico, eixo = plt.subplots(figsize=(5.4, 5.0))
    if pontos:
        eixo.scatter([b for b, _ in pontos], [r for _, r in pontos], s=18, alpha=0.55, edgecolors="none")
    eixo.plot([0, 1], [0, 1], color="#888888", linestyle="--", linewidth=1, label="y = x")
    eixo.set_xlim(-0.02, 1.02)  # margem para os pontos em 0 e em 1 não ficarem cortados
    eixo.set_ylim(-0.02, 1.02)
    eixo.set_aspect("equal")
    eixo.set_xlabel("cfr_b (fração de 0 a 1)")
    eixo.set_ylabel("rework_rate (fração de 0 a 1)")
    rho = "indefinido" if resultado["rho"] is None else f"{resultado['rho']:.2f}"
    p = "indefinido" if resultado["p_valor"] is None else f"{resultado['p_valor']:.2g}"
    eixo.set_title(f"Spearman: rho = {rho}, p = {p}, n = {resultado['n']}")
    eixo.legend(frameon=False, loc="lower right")
    eixo.grid(alpha=0.25)
    grafico.tight_layout()
    grafico.savefig(caminho, dpi=150)
    plt.close(grafico)


if __name__ == "__main__":
    sys.exit(main())
