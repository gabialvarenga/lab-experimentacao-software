"""Consolidação dos resultados da simulação e classificação dos testes (S02-07).

`consolidar` junta os CSVs de cada simulação (`c0_c1.csv`, `c2_c3.csv`, `c4.csv` e, se existir,
`c5.csv`) em uma tabela única, no formato congelado na S02-01. `classificar` diz, para cada cenário,
teste e α, se o erro tipo I ficou perto do nominal. `vantagem_de_poder` e `lideres` comparam o poder
dos dois testes. Os gráficos G3 e G4 e a conclusão leem estas tabelas.

Classificação do erro tipo I (δ = 0), com o intervalo de Wilson de 95% da taxa e a referência α
(5% ou 1%):

    liberal      limite inferior do IC acima de α (o teste rejeita demais);
    conservador  limite superior do IC abaixo de α (rejeita de menos);
    ok           o IC contém α.

Com 10.000 repetições o IC é estreito (cerca de ±0,4 ponto percentual em 5%), então um desvio
pequeno já classifica o teste. A coluna `desvio_pp` dá o tamanho do desvio para o leitor julgar se
ele importa na prática.

Vantagem de poder (δ > 0): `vantagem_pp` = poder do Mann-Whitney − poder do Welch, em pontos
percentuais (positivo: Mann-Whitney à frente). A diferença só conta se passar de 1,96 erros-padrão
de duas proporções; senão o `melhor` é `empate`. Os dois testes rodam nas mesmas amostras, então a
diferença verdadeira é mais estável que esse erro-padrão: o critério é conservador.

Linha de comando (a partir da pasta `lab04/`):

    python -m lab04.resultados

grava `resultados.csv`, `classificacao.csv`, `poder.csv` e `resumo-resultados.md` em
`dados/simulacao/`.
"""

import argparse
import sys
from pathlib import Path

import numpy as np
import pandas as pd

from lab04 import config, simulacao

CHAVE = ["cenario", "delta", "alfa", "teste"]
PADRAO_DOS_ARQUIVOS = "c[0-9]*.csv"   # c0_c1, c2_c3, c4 e c5 (opcional); fora piloto, resultados e derivados
COLUNAS_CLASSIFICACAO = ["cenario", "alfa", "teste", "n", "n_rep", "taxa", "ic_inf", "ic_sup", "desvio_pp", "classificacao"]
COLUNAS_PODER = ["cenario", "delta", "alfa", "n", "n_rep", "poder_welch", "poder_mann_whitney", "vantagem_pp", "melhor"]
COLUNAS_LIDERES = [
    "cenario", "alfa", "lider", "inverte_com_o_efeito", "pontos_welch", "pontos_mann_whitney",
    "pontos_empate", "vantagem_media_pp", "vantagem_maxima_pp", "delta_vantagem_maxima",
]
Z = 1.96
NOMES = {"welch": "Welch", "mann_whitney": "Mann-Whitney"}


def consolidar(pasta, obrigatorios=None) -> pd.DataFrame:
    """Junta os CSVs de simulação de `pasta` em uma tabela, na ordem dos arquivos e das linhas.

    Lê `c0_c1.csv`, `c2_c3.csv`, `c4.csv` e qualquer `c<dígito>*.csv` opcional (como o `c5.csv`).
    `obrigatorios` (ids de cenário, na ordem desejada) exige que todos estejam presentes e põe
    esses cenários primeiro, nessa ordem; os demais (opcionais) vão depois. Levanta `ValueError`
    se não houver CSV, se as colunas não forem as de `simulacao.COLUNAS`, se uma linha (cenário,
    efeito, α, teste) aparecer mais de uma vez ou se faltar um cenário obrigatório.
    """
    arquivos = sorted(Path(pasta).glob(PADRAO_DOS_ARQUIVOS))
    if not arquivos:
        raise ValueError(f"nenhum CSV de simulação ({PADRAO_DOS_ARQUIVOS}) em {pasta}")
    partes = []
    for arquivo in arquivos:
        parte = pd.read_csv(arquivo)
        if list(parte.columns) != simulacao.COLUNAS:
            raise ValueError(f"{arquivo.name}: colunas {list(parte.columns)} em vez de {simulacao.COLUNAS}")
        partes.append(parte)
    tabela = pd.concat(partes, ignore_index=True)
    repetidas = tabela[tabela.duplicated(CHAVE, keep=False)]
    if not repetidas.empty:
        raise ValueError(f"linhas repetidas em {sorted(repetidas['cenario'].unique())}")
    if obrigatorios is not None:
        faltam = [c for c in obrigatorios if c not in set(tabela["cenario"])]
        if faltam:
            raise ValueError(f"faltam os cenários {faltam} em {pasta}")
        posicao = {c: i for i, c in enumerate(obrigatorios)}
        tabela = tabela.sort_values("cenario", key=lambda s: s.map(lambda c: posicao.get(c, len(posicao))), kind="stable")
    return tabela.reset_index(drop=True)


def classificar(df: pd.DataFrame) -> pd.DataFrame:
    """Classificação do erro tipo I (δ = 0): uma linha por (cenário, α, teste).

    Colunas de `COLUNAS_CLASSIFICACAO`. `desvio_pp` = (taxa − α) em pontos percentuais.
    Levanta `ValueError` se algum cenário não tem linha de δ = 0.
    """
    h0 = df[df["delta"] == 0]
    sem_h0 = sorted(set(df["cenario"]) - set(h0["cenario"]))
    if sem_h0:
        raise ValueError(f"cenários sem linha de δ = 0: {sem_h0}")
    classe = np.where(h0["ic_inf"] > h0["alfa"], "liberal", np.where(h0["ic_sup"] < h0["alfa"], "conservador", "ok"))
    saida = h0[["cenario", "alfa", "teste", "n", "n_rep", "taxa", "ic_inf", "ic_sup"]].copy()
    saida["desvio_pp"] = ((h0["taxa"] - h0["alfa"]) * 100).round(4)
    saida["classificacao"] = classe
    return saida[COLUNAS_CLASSIFICACAO].reset_index(drop=True)


def vantagem_de_poder(df: pd.DataFrame, z: float = Z) -> pd.DataFrame:
    """Poder dos dois testes por (cenário, efeito, α), com δ > 0, e a vantagem de um sobre o outro.

    Colunas de `COLUNAS_PODER`. `vantagem_pp` = Mann-Whitney − Welch em pontos percentuais.
    `melhor` é `welch`, `mann_whitney` ou `empate` (diferença dentro de `z` erros-padrão).
    """
    chave = ["cenario", "delta", "alfa"]
    com_efeito = df[df["delta"] > 0]
    w = com_efeito[com_efeito["teste"] == "welch"].set_index(chave)
    m = com_efeito[com_efeito["teste"] == "mann_whitney"].set_index(chave)
    if not w.index.equals(m.index):
        raise ValueError("os dois testes precisam ter as mesmas células (cenário, efeito, α)")
    pw, pm, n_rep = w["taxa"], m["taxa"], w["n_rep"]
    erro = np.sqrt(pw * (1 - pw) / n_rep + pm * (1 - pm) / n_rep)
    diferenca = pm - pw
    melhor = np.where(diferenca.abs() <= z * erro, "empate", np.where(diferenca > 0, "mann_whitney", "welch"))
    saida = pd.DataFrame({
        "n": w["n"], "n_rep": n_rep, "poder_welch": pw, "poder_mann_whitney": pm,
        "vantagem_pp": (diferenca * 100).round(4), "melhor": melhor,
    }, index=w.index)
    return saida.reset_index()[COLUNAS_PODER]


def lideres(poder: pd.DataFrame) -> pd.DataFrame:
    """Resumo da vantagem por (cenário, α): quem lidera e se a liderança muda com o efeito.

    `lider` é o teste que é o `melhor` em algum efeito e nunca perde para o outro; `alternado`
    se cada um lidera em algum efeito (a vantagem inverte de lado ao longo do efeito); `empate` se
    nenhum lidera. As colunas `pontos_*` contam os efeitos em que cada resultado ocorre.
    """
    linhas = []
    for (cenario, alfa), g in poder.groupby(["cenario", "alfa"], sort=False):
        welch, mw = int((g["melhor"] == "welch").sum()), int((g["melhor"] == "mann_whitney").sum())
        lider = "alternado" if welch and mw else "welch" if welch else "mann_whitney" if mw else "empate"
        maior = g.loc[g["vantagem_pp"].abs().idxmax()]
        linhas.append({
            "cenario": cenario, "alfa": alfa, "lider": lider, "inverte_com_o_efeito": bool(welch and mw),
            "pontos_welch": welch, "pontos_mann_whitney": mw, "pontos_empate": int((g["melhor"] == "empate").sum()),
            "vantagem_media_pp": round(float(g["vantagem_pp"].mean()), 4),
            "vantagem_maxima_pp": float(maior["vantagem_pp"]), "delta_vantagem_maxima": float(maior["delta"]),
        })
    return pd.DataFrame(linhas, columns=COLUNAS_LIDERES)


def lideres_diferentes_do_primeiro(lid: pd.DataFrame) -> dict:
    """Por α, os cenários cujo líder difere do líder do primeiro cenário (o controle).

    Devolve `{alfa: [(cenario, lider), ...]}`; lista vazia se a vantagem não muda de lado entre cenários.
    """
    mudancas = {}
    for alfa, g in lid.groupby("alfa", sort=False):
        referencia = g.iloc[0]["lider"]
        mudancas[alfa] = [(r["cenario"], r["lider"]) for _, r in g.iloc[1:].iterrows() if r["lider"] != referencia]
    return mudancas


def _pct(x: float) -> str:
    return f"{x * 100:.2f}%".replace(".", ",")


def _g(x: float) -> str:
    return f"{x:g}".replace(".", ",")


def _pp(x: float) -> str:
    return f"{x:+.2f}".replace(".", ",")


def resumo(clas: pd.DataFrame, poder: pd.DataFrame, lid: pd.DataFrame) -> str:
    """Texto Markdown do `resumo-resultados.md`: classificação, poder e onde a vantagem muda de lado."""
    L = [
        "# Resumo dos resultados da simulação",
        "",
        "Gerado por `lab04/resultados.py`; não edite à mão. Para refazer: `python -m lab04.resultados` (a partir de `lab04/`).",
        "",
        "## Erro tipo I (δ = 0)",
        "",
        "Critério: **liberal** se o limite inferior do IC de Wilson de 95% está acima de α; **conservador** se o "
        "limite superior está abaixo de α; **ok** se o IC contém α. `Desvio` é taxa − α em pontos percentuais.",
        "",
        "| Cenário | α | Teste | Taxa | IC de Wilson de 95% | Desvio (p.p.) | Classificação |",
        "|---|---|---|---|---|---|---|",
    ]
    for _, r in clas.iterrows():
        L.append(
            f"| {r['cenario']} | {_g(r['alfa'])} | {NOMES[r['teste']]} | {_pct(r['taxa'])} | "
            f"[{_pct(r['ic_inf'])}; {_pct(r['ic_sup'])}] | {_pp(r['desvio_pp'])} | {r['classificacao']} |"
        )
    L += ["", "## Poder (α = 0,05)", "",
          "Vantagem = poder do Mann-Whitney − poder do Welch, em pontos percentuais (positivo: Mann-Whitney à frente). "
          "`empate` quando a diferença não passa de 1,96 erros-padrão. Os resultados de α = 0,01 estão em `poder.csv`.",
          "", "| Cenário | Efeito δ | Welch | Mann-Whitney | Vantagem (p.p.) | Melhor |", "|---|---|---|---|---|---|"]
    for _, r in poder[poder["alfa"] == 0.05].iterrows():
        L.append(
            f"| {r['cenario']} | {_g(r['delta'])} | {_pct(r['poder_welch'])} | {_pct(r['poder_mann_whitney'])} | "
            f"{_pp(r['vantagem_pp'])} | {NOMES.get(r['melhor'], r['melhor'])} |"
        )
    L += ["", "## Quem lidera em cada cenário", "",
          "| Cenário | α | Líder | Efeitos Welch / Mann-Whitney / empate | Vantagem média (p.p.) | Maior vantagem (p.p.) | em δ |",
          "|---|---|---|---|---|---|---|"]
    for _, r in lid.iterrows():
        L.append(
            f"| {r['cenario']} | {_g(r['alfa'])} | {NOMES.get(r['lider'], r['lider'])} | "
            f"{r['pontos_welch']} / {r['pontos_mann_whitney']} / {r['pontos_empate']} | {_pp(r['vantagem_media_pp'])} | "
            f"{_pp(r['vantagem_maxima_pp'])} | {_g(r['delta_vantagem_maxima'])} |"
        )
    L += ["", "## Onde a vantagem de poder muda de lado", ""]
    alternados = lid[lid["inverte_com_o_efeito"]]
    L.append("**Ao longo do efeito, dentro de um cenário:** " + (
        "; ".join(f"{r['cenario']} (α = {_g(r['alfa'])})" for _, r in alternados.iterrows()) + "." if len(alternados)
        else "nenhum. Em cada cenário o mesmo teste lidera em todos os efeitos em que há diferença."))
    L.append("")
    primeiro = lid.iloc[0]["cenario"]
    for alfa, mudancas in lideres_diferentes_do_primeiro(lid).items():
        referencia = lid[(lid["cenario"] == primeiro) & (lid["alfa"] == alfa)].iloc[0]["lider"]
        if mudancas:
            texto = ", ".join(f"{c} ({NOMES.get(l, l)})" for c, l in mudancas)
            L.append(f"- **Entre cenários, α = {_g(alfa)}:** em {primeiro} lidera {NOMES.get(referencia, referencia)}; "
                     f"o líder muda em {texto}.")
        else:
            L.append(f"- **Entre cenários, α = {_g(alfa)}:** o líder de {primeiro} ({NOMES.get(referencia, referencia)}) "
                     "é o mesmo em todos os cenários.")
    return "\n".join(L) + "\n"


def _escrever(df: pd.DataFrame, caminho) -> None:
    df.to_csv(caminho, index=False, lineterminator="\n")


def executar(cfg: dict) -> dict:
    """Consolida os CSVs da pasta de `simulacao.saida` e grava as quatro saídas ao lado de `resultados.csv`.

    Exige todos os cenários do config. Devolve as tabelas e os caminhos gravados.
    """
    sim = config.simulacao(cfg)
    destino = Path(cfg["pasta"]) / sim["saida"]
    pasta = destino.parent
    df = consolidar(pasta, obrigatorios=[c["id"] for c in sim["cenarios"]])
    clas, poder = classificar(df), vantagem_de_poder(df)
    lid = lideres(poder)
    caminhos = {
        "resultados": destino, "classificacao": pasta / "classificacao.csv",
        "poder": pasta / "poder.csv", "resumo": pasta / "resumo-resultados.md",
    }
    _escrever(df, caminhos["resultados"])
    _escrever(clas, caminhos["classificacao"])
    _escrever(poder, caminhos["poder"])
    caminhos["resumo"].write_text(resumo(clas, poder, lid), encoding="utf-8", newline="\n")
    return {"resultados": df, "classificacao": clas, "poder": poder, "lideres": lid, "caminhos": caminhos}


def main(argv=None) -> int:
    """`python -m lab04.resultados [--config YAML]`."""
    parser = argparse.ArgumentParser(prog="python -m lab04.resultados", description="Consolida e classifica os resultados.")
    parser.add_argument("--config", default=str(config.CONFIG_PADRAO), help="caminho do config.yaml")
    args = parser.parse_args(argv)
    saida = executar(config.carregar(args.config))
    for nome, caminho in saida["caminhos"].items():
        print(f"{nome}: {caminho}")
    contagem = saida["classificacao"]["classificacao"].value_counts().to_dict()
    print(f"{len(saida['resultados'])} linhas consolidadas; erro tipo I: {contagem}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
