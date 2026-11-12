"""Lógica do dashboard interativo (`app.py`, em Streamlit), separada da interface para ser testada.

O dashboard estático (`dashboard.py`) mostra os resultados congelados; o interativo deixa mudar os
parâmetros na hora da apresentação e ver o efeito: sortear outros dados simulados (G1), mudar o
efeito, o n e o α de um exemplo e ver onde cada estatística cai (G2), filtrar cenários e trocar o α
do G3 e do G4, trocar o α dos testes nos dados reais e rodar uma simulação nova com um cenário
montado na tela (laboratório ao vivo).

Nada aqui grava arquivo: os CSVs versionados continuam sendo a fonte das seções 4 e 5, e a
simulação ao vivo usa o mesmo motor (`simulacao.simular`) e o mesmo esquema de sementes
(`simulacao.gerador_da_celula`). Por isso, com os parâmetros de um cenário do config, a semente 42 e
10.000 repetições, o laboratório reproduz exatamente as linhas do `resultados.csv` (há um teste para isso).
"""

import math
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
from plotly import graph_objects as go

from lab04 import calibracao, config, gerador, graficos, resultados, simulacao, testes
from lab04.descritiva import GRUPOS, horas_do_grupo

ID_PERSONALIZADO = "Personalizado"
ALFAS_INTERATIVOS = (0.01, 0.05, 0.10)
REPETICOES_INTERATIVAS = (500, 1_000, 2_000, 5_000, 10_000)
N_MINIMO, N_MAXIMO = 5, 200


def carregar(cfg: dict | None = None) -> dict:
    """Config, dados reais, calibração, resultados da simulação e cenários do config.

    Devolve `cfg`, `reais` (o `prs.csv`), `calibracao`, `resultados` (o `resultados.csv`, ou None se
    ele falta) e `cenarios` (`{id: cenário}` na ordem do config).
    """
    cfg = cfg or config.carregar()
    base = Path(cfg["pasta"])
    caminho_resultados = base / cfg["simulacao"]["saida"]
    return {
        "cfg": cfg,
        "reais": pd.read_csv(base / cfg["coleta"]["saida"]),
        "calibracao": calibracao.ler(base / cfg["calibracao"]["saida"]),
        "resultados": pd.read_csv(caminho_resultados) if caminho_resultados.exists() else None,
        "cenarios": cenarios_do_config(cfg),
    }


def cenarios_do_config(cfg: dict) -> dict:
    """`{id: cenário}` dos cenários do config, na ordem em que aparecem (C0 a C4)."""
    return {c["id"]: dict(c) for c in config.simulacao(cfg)["cenarios"]}


def indice_do_cenario(cfg: dict, cenario_id: str) -> int:
    """Posição do cenário no config: é o `i` da semente das células (`gerador_da_celula`)."""
    return list(cenarios_do_config(cfg)).index(cenario_id)


def rotulo_cenario(cenario: dict) -> str:
    """`C1: referência`, ou só o id se o cenário não tem nome."""
    nome = cenario.get("nome")
    return f"{cenario['id']}: {nome}" if nome else str(cenario["id"])


def cenario_personalizado(familia: str, sigma: float, n: int, p_contaminacao: float = 0.0,
                          fator: float = 1.0, mu: float = 0.0) -> dict:
    """Cenário montado na tela, no formato do config (o que `simulacao.simular` lê).

    Na normal o efeito δ está em desvios-padrão; na lognormal, na escala log (razão de medianas e^δ).
    Com `p_contaminacao` > 0, cada observação é multiplicada por `fator` com essa probabilidade.
    Os dois testes não dependem da escala dos dados, então `mu` não muda as taxas de rejeição.
    """
    if familia not in gerador.FAMILIAS:
        raise ValueError(f"família '{familia}' desconhecida; use {' ou '.join(gerador.FAMILIAS)}")
    if not N_MINIMO <= int(n) <= N_MAXIMO:
        raise ValueError(f"n deve estar entre {N_MINIMO} e {N_MAXIMO}")
    cenario = {
        "id": ID_PERSONALIZADO,
        "nome": "personalizado",
        "familia": familia,
        "mu": float(mu),
        "sigma": float(sigma),
        "n": int(n),
        "unidade_efeito": "dp" if familia == "normal" else "log",
    }
    if p_contaminacao > 0:
        cenario["contaminacao"] = {"p": float(p_contaminacao), "fator": float(fator)}
    return cenario


def grade_de_efeitos(maximo: float, pontos: int) -> list:
    """`pontos` efeitos igualmente espaçados de 0 a `maximo` (o primeiro é a hipótese nula)."""
    if pontos < 2 or maximo <= 0:
        raise ValueError("a grade precisa de ao menos 2 pontos e de um efeito máximo positivo")
    return [round(float(d), 4) for d in np.linspace(0, maximo, pontos)]


def simular_cenario(cenario: dict, efeitos, n_rep: int, semente: int, indice: int = 0,
                    alfas=simulacao.ALFAS) -> pd.DataFrame:
    """Roda a grade de `efeitos` de um cenário e devolve a tabela no formato do `resultados.csv`.

    A célula do efeito na posição `j` usa `gerador_da_celula(semente, indice, j)`, o mesmo esquema
    das simulações finais: com o `indice` do cenário no config, a semente do config e as mesmas
    repetições, o resultado é igual ao do CSV versionado. Os p-valores NaN não contam como rejeição
    (como no motor); o aviso do motor é silenciado aqui, porque a interface não o mostraria.
    """
    linhas = []
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        for j, delta in enumerate(efeitos):
            rng = simulacao.gerador_da_celula(semente, indice, j)
            linhas += simulacao.simular(cenario, float(delta), int(n_rep), rng, alfas=tuple(alfas))
    return pd.DataFrame(linhas, columns=simulacao.COLUNAS)


def iguais_ao_csv(simulado: pd.DataFrame, referencia: pd.DataFrame) -> bool:
    """True se as rejeições do `simulado` são as mesmas das linhas correspondentes da `referencia`."""
    chave = ["delta", "n", "n_rep", "alfa", "teste"]
    a = simulado.set_index(chave)["rejeicoes"].sort_index()
    b = referencia.set_index(chave)["rejeicoes"].sort_index()
    return a.index.equals(b.index) and bool((a.values == b.values).all())


def delta_exato(valor: float, calibrado: float, tolerancia: float = 0.005) -> float:
    """O δ calibrado quando o controle (de 0,05 em 0,05) está no ponto mais perto dele; senão o próprio valor.

    O slider não para em 0,3517; com isso, "0,35" na tela dá exatamente o exemplo do relatório.
    """
    return float(calibrado) if abs(float(valor) - float(calibrado)) < tolerancia else float(valor)


def amostras_simuladas(calib: dict, delta: float, n: int, semente: int) -> tuple:
    """Par `(A, B)` da lognormal calibrada com efeito `delta`, `n` por grupo e a `semente` dada (G1)."""
    cenario, _ = gerador.cenario_calibrado(calib)
    return gerador.gerar_amostra(cenario, float(delta), int(n), np.random.default_rng(int(semente)))


def _pct(valor: float, casas: int = 2) -> str:
    return f"{graficos._num(valor * 100, casas)}%"


def resumo_exemplo(exemplo: dict, alfa: float) -> pd.DataFrame:
    """Uma linha por teste com a estatística, o p-valor, o tamanho de efeito e a decisão em `alfa` (seção 3)."""
    r = exemplo["resultado"]
    linhas = []
    for teste, compara, estatistica, p, efeito in (
        ("welch", "médias", f"t = {graficos._num(r['welch_t'], 3)} (gl = {graficos._num(r['welch_gl'], 1)})",
         r["welch_p"], f"g de Hedges = {graficos._num(r['hedges_g'], 2)} ({testes.magnitude_hedges(r['hedges_g'])})"),
        ("mann_whitney", "postos", f"U = {graficos._num(r['mw_u'], 0)} ({r['mw_metodo']})",
         r["mw_p"], f"δ de Cliff = {graficos._num(r['cliff_delta'], 2)} ({testes.magnitude_cliff(r['cliff_delta'])})"),
    ):
        rejeita = math.isfinite(p) and p < alfa
        linhas.append({
            "Teste": graficos.NOMES_TESTE[teste],
            "Compara": compara,
            "Estatística": estatistica,
            "p-valor": graficos._p_rotulo(p),
            "Tamanho de efeito": efeito,
            f"Decisão (α = {graficos._num(alfa, 2)})": "rejeita H₀" if rejeita else "não rejeita H₀",
        })
    return pd.DataFrame(linhas)


def leitura_exemplo(exemplo: dict, alfa: float) -> str:
    """Uma frase sobre o exemplo: se as decisões estão certas, e qual erro cada teste cometeu."""
    r = exemplo["resultado"]
    h0_verdadeira = exemplo["delta"] == 0
    frases = []
    for teste, p in (("welch", r["welch_p"]), ("mann_whitney", r["mw_p"])):
        rejeita = math.isfinite(p) and p < alfa
        if h0_verdadeira:
            avaliacao = "erro tipo I (falso positivo)" if rejeita else "decisão certa"
        else:
            avaliacao = "decisão certa (detectou o efeito)" if rejeita else "erro tipo II (não detectou o efeito)"
        frases.append(f"{graficos.NOMES_TESTE[teste]}: {'rejeita' if rejeita else 'não rejeita'} H₀, {avaliacao}")
    verdade = "H₀ é verdadeira (δ = 0)" if h0_verdadeira else f"H₀ é falsa (δ = {graficos._num(exemplo['delta'], 2)})"
    return f"Neste conjunto {verdade}. " + "; ".join(frases) + "."


def tabela_classificacao(res: pd.DataFrame, alfa: float) -> pd.DataFrame:
    """Erro tipo I por cenário e teste em `alfa`, com o IC de Wilson, o desvio e a classificação (seção 4)."""
    clas = resultados.classificar(res[np.isclose(res["alfa"], alfa)])
    return pd.DataFrame({
        "Cenário": [graficos.NOMES_CENARIO.get(c, c) for c in clas["cenario"]],
        "Teste": [graficos.NOMES_TESTE[t] for t in clas["teste"]],
        "n": clas["n"],
        "Taxa de rejeição": [_pct(t) for t in clas["taxa"]],
        "IC de Wilson (95%)": [f"[{_pct(i)}; {_pct(s)}]" for i, s in zip(clas["ic_inf"], clas["ic_sup"])],
        "Desvio (p.p.)": [graficos._num(d, 2) for d in clas["desvio_pp"]],
        "Classificação": clas["classificacao"],
    })


def tabela_poder(res: pd.DataFrame, alfa: float, unidades: dict | None = None) -> pd.DataFrame:
    """Poder dos dois testes por cenário e efeito em `alfa`, com a vantagem e o líder (seção 5)."""
    poder = resultados.vantagem_de_poder(res[np.isclose(res["alfa"], alfa)])
    unidade_de = {**graficos.UNIDADE_EFEITO, **(unidades or {})}

    def efeito(cenario, delta):
        if unidade_de.get(cenario, "log") == "dp":
            return f"δ = {graficos._num(delta, 2)} dp"
        return f"δ = {graficos._num(delta, 2)} (×{graficos._num(math.exp(delta), 2)})"

    lider = {"welch": "Welch", "mann_whitney": "Mann-Whitney", "empate": "empate"}
    return pd.DataFrame({
        "Cenário": [graficos.NOMES_CENARIO.get(c, c) for c in poder["cenario"]],
        "Efeito": [efeito(c, d) for c, d in zip(poder["cenario"], poder["delta"])],
        "Poder do Welch": [_pct(p, 1) for p in poder["poder_welch"]],
        "Poder do Mann-Whitney": [_pct(p, 1) for p in poder["poder_mann_whitney"]],
        "Vantagem do MW (p.p.)": [graficos._num(v, 1) for v in poder["vantagem_pp"]],
        "Melhor": [lider[m] for m in poder["melhor"]],
    })


def resumo_simulacao(res: pd.DataFrame, alfa: float) -> dict:
    """Erro tipo I, classificação e poder máximo de cada teste numa simulação de um só cenário."""
    nivel = res[np.isclose(res["alfa"], alfa)]
    clas = resultados.classificar(nivel).set_index("teste")
    saida = {}
    for teste in graficos.NOMES_TESTE:
        linhas = nivel[nivel["teste"] == teste]
        saida[teste] = {
            "erro_tipo_1": float(clas.loc[teste, "taxa"]),
            "classificacao": str(clas.loc[teste, "classificacao"]),
            "poder_maximo": float(linhas.loc[linhas["delta"] > 0, "taxa"].max()),
        }
    return saida


def figura_dados_reais(reais: pd.DataFrame) -> go.Figure:
    """Horas até o merge de cada PR real, por grupo, num eixo log: caixa com todos os pontos (seção 6).

    O hover mostra o número do PR e as horas, para apontar na apresentação os PRs extremos.
    """
    figura = go.Figure()
    for grupo in GRUPOS:
        linhas = reais[reais["grupo"] == grupo]
        horas = horas_do_grupo(reais, grupo)
        figura.add_trace(go.Box(
            y=horas,
            name=graficos.NOMES_GRUPO[grupo],
            marker={"color": graficos.CORES_GRUPO[grupo]},
            boxpoints="all", jitter=0.4, pointpos=0,
            customdata=linhas[["numero_pr"]].to_numpy() if "numero_pr" in linhas else None,
            hovertemplate=(("PR #%{customdata[0]}<br>" if "numero_pr" in linhas else "")
                           + "%{y:.1f} h até o merge<extra></extra>"),
        ))
    figura.update_layout(
        title="Horas até o merge de cada PR real, por grupo",
        yaxis={"title": {"text": "Horas até o merge (h, escala log)"}, "type": "log"},
        showlegend=False,
        template="plotly_white",
        height=420,
    )
    return figura


def medianas(a, b) -> dict:
    """Medianas de A e B e a razão B/A (para os indicadores do G1)."""
    med_a, med_b = float(np.median(a)), float(np.median(b))
    return {"a": med_a, "b": med_b, "razao": med_b / med_a if med_a else float("nan")}

