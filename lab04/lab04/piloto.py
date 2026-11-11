"""Piloto da S02-01: roda a grade do config com poucas repetições e grava o CSV de exemplo.

O piloto serve a duas coisas: calibrar a grade de efeitos antes de congelar o `config.yaml` e dar
aos gráficos G3 e G4 um CSV real no formato congelado (`COLUNAS`) enquanto o motor de simulação
(S02-02) não existe. Ele é só o necessário para isso: usa `gerador.gerar_lote` e
`testes.aplicar_testes_vetorizado`, como o motor fará, e a mesma regra de semente.

Semente: cada célula (cenário × efeito) tem o seu gerador, `SeedSequence(semente, spawn_key=(i, j))`
com `i` a posição do cenário e `j` a do efeito no config. A célula só depende da semente e dessas
duas posições, então o resultado não muda com a ordem de execução nem com paralelismo.

Uso, a partir da pasta `lab04/`: `python -m lab04.piloto` (regrava `dados/simulacao/piloto.csv`).
"""

import sys
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from lab04 import config, gerador, testes

COLUNAS = ["cenario", "delta", "n", "n_rep", "alfa", "teste", "rejeicoes", "taxa", "ic_inf", "ic_sup"]
TESTES = {"welch": "welch_p", "mann_whitney": "mw_p"}  # `teste` no CSV (como em graficos.CORES_TESTE) → chave de testes
CASAS = 6                            # casas decimais de taxa e IC no CSV


def intervalo_wilson(rejeicoes: int, n: int, confianca: float = 0.95) -> tuple:
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


def simular_celula(cenario: dict, delta: float, n_rep: int, rng, alfas, confianca: float = 0.95) -> list:
    """Linhas do CSV de uma célula: uma por (α, teste), com as colunas de `COLUNAS`.

    Gera `n_rep` pares de amostras de tamanho `cenario["n"]` e conta os p-valores abaixo de cada α.
    P-valores NaN (variância zero no Welch) não contam como rejeição e geram um aviso.
    """
    n = cenario["n"]
    A, B = gerador.gerar_lote(cenario, delta, n, n_rep, rng)
    p = testes.aplicar_testes_vetorizado(A, B)
    nao_numericos = {teste: int(np.isnan(p[chave]).sum()) for teste, chave in TESTES.items()}
    if any(nao_numericos.values()):
        warnings.warn(f"{cenario['id']}, δ = {delta}: p-valores NaN (não contam como rejeição): {nao_numericos}")
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
    return linhas


def rodar_piloto(cfg: dict, n_rep: int | None = None) -> pd.DataFrame:
    """Percorre todas as células do config e devolve o CSV de resultados como DataFrame.

    `n_rep` padrão é `simulacao.repeticoes_piloto`. As linhas saem na ordem do config
    (cenário, efeito, α, teste).
    """
    sim = config.simulacao(cfg)
    n_rep = sim["repeticoes_piloto"] if n_rep is None else n_rep
    linhas = []
    for i, cenario in enumerate(sim["cenarios"]):
        for j, delta in enumerate(cenario["efeitos"]):
            rng = gerador_da_celula(cfg["semente"], i, j)
            linhas += simular_celula(cenario, delta, n_rep, rng, sim["alfas"], sim["confianca_ic"])
    tabela = pd.DataFrame(linhas, columns=COLUNAS)
    return tabela.round({"taxa": CASAS, "ic_inf": CASAS, "ic_sup": CASAS})


def executar(cfg: dict) -> Path:
    """Roda o piloto e grava `simulacao.piloto` (caminho relativo à pasta do config)."""
    sim = config.simulacao(cfg)
    destino = Path(cfg["pasta"]) / sim["piloto"]
    destino.parent.mkdir(parents=True, exist_ok=True)
    rodar_piloto(cfg).to_csv(destino, index=False, lineterminator="\n")
    return destino


def main(argv=None) -> int:
    cfg = config.carregar(argv[0]) if argv else config.carregar()
    print(f"piloto gravado em {executar(cfg)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
