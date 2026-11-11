"""Motor de simulação: rejeições, IC de Wilson e SeedSequence (S02-02).

Uma célula é um par (cenário, efeito). `simular` gera `n_rep` pares de amostras com
`gerador.gerar_lote`, aplica Welch e Mann-Whitney com `testes.aplicar_testes_vetorizado` e conta os
p-valores abaixo de cada α. `rodar_grade` percorre todas as células do `config.yaml` e grava o CSV.

Semente: cada célula tem o seu gerador, `SeedSequence(semente, spawn_key=(i, j))`, com `i` a
posição do cenário e `j` a do efeito no config. É o mesmo que um `spawn` por célula, mas a chave
só depende da posição da célula, então o resultado não muda com a ordem de execução nem com
paralelismo. Mudar a ordem dos cenários ou dos efeitos no config muda as sementes; o config está
congelado (S02-01), e acrescentar um cenário no fim não altera as células existentes.

Formato do CSV (congelado na S02-01, descrito no README): uma linha por (cenário, efeito, α, teste),
nas colunas de `COLUNAS`. O Mann-Whitney usa o p-valor assintótico quando os dois grupos têm mais de
8 observações, e o exato nos demais casos sem empates (`testes.metodo_mw`); como o formato não tem
coluna para isso, o método de cada cenário fica em `tabela.attrs["mw_metodo"]`
(ver `metodo_mw_do_cenario`). Os p-valores NaN (variância zero no Welch) não contam como rejeição:
geram um aviso por célula e o total por teste fica em `tabela.attrs["p_nan"]`.

Linha de comando (a partir da pasta `lab04/`), usada nas simulações das S02-03 a S02-05:

    python -m lab04.simulacao --cenarios C0 C1 --saida dados/simulacao/c0_c1.csv

roda só os cenários pedidos (com as sementes que eles têm na grade inteira), grava o CSV e o
registro `registro-<nome do CSV>.md` ao lado dele (ver `registro`).
"""

import argparse
import hashlib
import platform
import sys
import time
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
from scipy import stats

from lab04 import config, gerador, testes

COLUNAS = ["cenario", "delta", "n", "n_rep", "alfa", "teste", "rejeicoes", "taxa", "ic_inf", "ic_sup"]
TESTES = {"welch": "welch_p", "mann_whitney": "mw_p"}  # `teste` no CSV (como em graficos.CORES_TESTE) → chave de testes
ALFAS = (0.05, 0.01)
CONFIANCA = 0.95
CASAS = 6  # casas decimais de taxa e IC no CSV


def intervalo_wilson(rejeicoes: int, n: int, confianca: float = CONFIANCA) -> tuple:
    """Intervalo de Wilson para a proporção `rejeicoes / n`, no nível `confianca`."""
    if n < 1 or not 0 <= rejeicoes <= n:
        raise ValueError("precisa de n ≥ 1 e 0 ≤ rejeicoes ≤ n")
    z = stats.norm.ppf(1 - (1 - confianca) / 2)
    p = rejeicoes / n
    centro = (p + z**2 / (2 * n)) / (1 + z**2 / n)
    meia = z * np.sqrt(p * (1 - p) / n + z**2 / (4 * n**2)) / (1 + z**2 / n)
    # com 0 ou n rejeições um dos limites é exatamente 0 ou 1; a conta em ponto flutuante erra por ~1e-16
    inf = 0.0 if rejeicoes == 0 else max(centro - meia, 0.0)
    sup = 1.0 if rejeicoes == n else min(centro + meia, 1.0)
    return float(inf), float(sup)


def gerador_da_celula(semente: int, i: int, j: int) -> np.random.Generator:
    """Gerador da célula do cenário na posição `i` e do efeito na posição `j`."""
    return np.random.default_rng(np.random.SeedSequence(semente, spawn_key=(i, j)))


def metodo_mw_do_cenario(n: int) -> str:
    """Método do p-valor do Mann-Whitney para grupos de tamanho `n`.

    `asymptotic` com mais de 8 observações por grupo; senão `exact`, que vira `asymptotic` nas
    repetições com empates (regra de `testes.metodo_mw`). Nos cenários do config (n = 30 e 10) é
    sempre `asymptotic`.
    """
    if testes.metodo_mw(n, n, empates=False) == "asymptotic":
        return "asymptotic"
    return "exact (asymptotic nas repetições com empates)"


def _simular(cenario: dict, delta: float, n_rep: int, rng, alfas, confianca: float) -> tuple:
    """`(linhas, p_nan)`: as linhas de `simular` e os p-valores NaN de cada teste na célula."""
    n = cenario["n"]
    A, B = gerador.gerar_lote(cenario, delta, n, n_rep, rng)
    p = testes.aplicar_testes_vetorizado(A, B)
    p_nan = {teste: int(np.isnan(p[chave]).sum()) for teste, chave in TESTES.items()}
    if any(p_nan.values()):
        warnings.warn(
            f"{cenario['id']}, δ = {delta}: p-valores NaN (não contam como rejeição): {p_nan}", stacklevel=3
        )
    linhas = []
    for alfa in alfas:
        for teste, chave in TESTES.items():
            rejeicoes = int((p[chave] < alfa).sum())
            inf, sup = intervalo_wilson(rejeicoes, n_rep, confianca)
            linhas.append(
                {
                    "cenario": cenario["id"],
                    "delta": delta,
                    "n": n,
                    "n_rep": n_rep,
                    "alfa": alfa,
                    "teste": teste,
                    "rejeicoes": rejeicoes,
                    "taxa": rejeicoes / n_rep,
                    "ic_inf": inf,
                    "ic_sup": sup,
                }
            )
    return linhas, p_nan


def simular(cenario: dict, delta: float, n_rep: int, rng, *, alfas=ALFAS, confianca: float = CONFIANCA) -> list:
    """Roda uma célula: uma linha por (α, teste), com as colunas de `COLUNAS`.

    `cenario` é um dicionário do config (`id`, `n` e o que `gerador.gerar_lote` lê: `familia`,
    `mu`, `sigma`, `contaminacao`). Gera `n_rep` pares de amostras de tamanho `cenario["n"]` com o
    efeito `delta`, aplica os dois testes e conta os p-valores abaixo de cada α. A taxa é
    `rejeicoes / n_rep` e o intervalo é o de Wilson no nível `confianca` (95%). `alfas` e
    `confianca` são opcionais; o padrão é α = 0,05 e 0,01, a 95%.

    Os p-valores NaN não contam como rejeição e geram um `UserWarning`. Levanta `ValueError` para
    cenário, `delta` ou `n_rep` inválidos (as validações são as de `gerador.gerar_lote`).
    """
    return _simular(cenario, delta, n_rep, rng, alfas, confianca)[0]


def celulas(sim: dict, semente: int) -> list:
    """Células da grade na ordem do config: `(i, j, cenario, delta, gerador)`.

    `sim` é a seção `simulacao` do config; cada célula traz o seu gerador, derivado da `semente`.
    """
    return [
        (i, j, cenario, delta, gerador_da_celula(semente, i, j))
        for i, cenario in enumerate(sim["cenarios"])
        for j, delta in enumerate(cenario["efeitos"])
    ]


def rodar_grade(cfg: dict, n_rep: int | None = None, saida: str | None = None, cenarios=None) -> pd.DataFrame:
    """Percorre cenários e efeitos do config, grava o CSV e devolve a tabela.

    `cfg` é o dicionário de `config.carregar()`. `n_rep` padrão é `simulacao.repeticoes` (10.000) e
    `saida` padrão é `simulacao.saida`; os dois existem para o piloto e para os testes. O caminho de
    `saida` é relativo à pasta do config e a pasta é criada se não existir. As linhas saem na
    ordem do config (cenário, efeito, α, teste), seja qual for a ordem em que as células rodam.

    `cenarios` (ids, como `["C0", "C1"]`) restringe a grade a esses cenários, que mantêm as
    sementes que têm na grade inteira: rodar C0 e C1 à parte dá as mesmas linhas que rodar tudo.
    Um id que não está no config levanta `ValueError`.

    `tabela.attrs` registra `mw_metodo` (método do Mann-Whitney por cenário), `p_nan` (p-valores NaN
    por teste, na grade toda) e `segundos` (tempo gasto).
    """
    sim = config.simulacao(cfg)
    n_rep = sim["repeticoes"] if n_rep is None else n_rep
    ids = [c["id"] for c in sim["cenarios"]]
    escolhidos = ids if cenarios is None else list(cenarios)
    desconhecidos = sorted(set(escolhidos) - set(ids))
    if not escolhidos or desconhecidos:
        raise ValueError(f"cenários {desconhecidos or escolhidos} não estão no config; use {ids}")
    inicio = time.perf_counter()
    por_celula, p_nan = {}, dict.fromkeys(TESTES, 0)
    for i, j, cenario, delta, rng in celulas(sim, cfg["semente"]):
        if cenario["id"] not in escolhidos:
            continue
        linhas, nan_da_celula = _simular(cenario, delta, n_rep, rng, sim["alfas"], sim["confianca_ic"])
        por_celula[(i, j)] = linhas
        for teste, quantos in nan_da_celula.items():
            p_nan[teste] += quantos
    linhas = [linha for chave in sorted(por_celula) for linha in por_celula[chave]]
    tabela = pd.DataFrame(linhas, columns=COLUNAS).round({"taxa": CASAS, "ic_inf": CASAS, "ic_sup": CASAS})
    tabela.attrs["mw_metodo"] = {c["id"]: metodo_mw_do_cenario(c["n"]) for c in sim["cenarios"] if c["id"] in escolhidos}
    tabela.attrs["p_nan"] = p_nan
    tabela.attrs["segundos"] = time.perf_counter() - inicio

    destino = Path(cfg["pasta"]) / (sim["saida"] if saida is None else saida)
    destino.parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(destino, index=False, lineterminator="\n")
    return tabela


def sha256(caminho) -> str:
    """SHA-256 do arquivo com os fins de linha normalizados para LF.

    A normalização faz o hash valer em Windows (que pode converter para CRLF no checkout) e em Linux.
    """
    return hashlib.sha256(Path(caminho).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def registro(cfg: dict, tabela: pd.DataFrame, comando: str, caminho_config) -> str:
    """Texto Markdown do registro de uma simulação: comando, parâmetros, hash do config e erro tipo I.

    É determinístico (sem data nem tempo de execução): rodar o comando de novo, no mesmo ambiente,
    regrava o mesmo texto. O hash do `config.yaml` (com fins de linha em LF) permite conferir que o
    CSV veio do config congelado.
    """
    sim = config.simulacao(cfg)
    ids = list(tabela["cenario"].unique())
    efeitos = "; ".join(f"{c['id']}: {c['efeitos']}" for c in sim["cenarios"] if c["id"] in ids)
    metodos = "; ".join(f"{k}: {v}" for k, v in tabela.attrs["mw_metodo"].items())
    p_nan = ", ".join(f"{k}: {v}" for k, v in tabela.attrs["p_nan"].items())
    ambiente = f"Python {platform.python_version()}, numpy {np.__version__}, scipy {scipy.__version__}, pandas {pd.__version__}"
    linhas = [
        f"# Registro da simulação {', '.join(ids)}",
        "",
        "Gerado por `lab04/simulacao.py`; não edite à mão. Para refazer, rode o comando abaixo.",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Comando (a partir de `lab04/`) | `{comando}` |",
        f"| Cenários | {', '.join(ids)} |",
        f"| Efeitos | {efeitos} |",
        f"| Repetições por célula | {int(tabela['n_rep'].iloc[0])} |",
        f"| α | {', '.join(str(a) for a in sim['alfas'])} |",
        f"| Semente | {cfg['semente']} |",
        f"| SHA-256 do `config.yaml` (fins de linha LF) | `{sha256(caminho_config)}` |",
        f"| Linhas do CSV | {len(tabela)} |",
        f"| Mann-Whitney | {metodos} |",
        f"| p-valores NaN | {p_nan} |",
        f"| Ambiente | {ambiente} |",
        "",
        "## Erro tipo I (δ = 0)",
        "",
        "| Cenário | α | Teste | Taxa | IC de Wilson de 95% | α dentro do IC |",
        "|---|---|---|---|---|---|",
    ]
    for _, linha in tabela[tabela["delta"] == 0].iterrows():
        dentro = "sim" if linha["ic_inf"] <= linha["alfa"] <= linha["ic_sup"] else "não"
        linhas.append(
            f"| {linha['cenario']} | {linha['alfa']} | {linha['teste']} | {linha['taxa']:.4f} | "
            f"[{linha['ic_inf']:.4f}; {linha['ic_sup']:.4f}] | {dentro} |"
        )
    return "\n".join(linhas) + "\n"


def main(argv=None) -> int:
    """`python -m lab04.simulacao [--cenarios C0 C1 ...] [--saida CSV] [--config YAML]`."""
    parser = argparse.ArgumentParser(prog="python -m lab04.simulacao", description="Roda a grade de simulação.")
    parser.add_argument("--config", default=str(config.CONFIG_PADRAO), help="caminho do config.yaml")
    parser.add_argument("--cenarios", nargs="+", metavar="ID", help="ids dos cenários (padrão: todos)")
    parser.add_argument("--saida", help="CSV de saída, relativo à pasta do config (padrão: simulacao.saida)")
    args = parser.parse_args(argv)

    cfg = config.carregar(args.config)
    saida = args.saida or config.simulacao(cfg)["saida"]
    tabela = rodar_grade(cfg, saida=saida, cenarios=args.cenarios)

    comando = "python -m lab04.simulacao"
    if args.config != str(config.CONFIG_PADRAO):
        comando += f" --config {args.config}"
    if args.cenarios:
        comando += f" --cenarios {' '.join(args.cenarios)}"
    comando += f" --saida {saida}"
    destino = Path(cfg["pasta"]) / saida
    caminho_registro = destino.with_name(f"registro-{destino.stem}.md")
    caminho_registro.write_text(registro(cfg, tabela, comando, args.config), encoding="utf-8", newline="\n")
    print(f"{len(tabela)} linhas em {destino} ({tabela.attrs['segundos']:.1f} s); registro em {caminho_registro}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
