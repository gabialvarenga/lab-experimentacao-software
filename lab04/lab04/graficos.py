"""Gráficos G1 a G4 em Plotly (S01-09, S01-10, S02-08, S02-09).

Cores e rótulos dos grupos ficam aqui para valerem em todo o dashboard: o `com_bot` é sempre o
grupo A e o `sem_bot` o grupo B, como no gerador e em `testes.py`.

G1 (`g1`): histogramas das horas até o merge, dados reais à esquerda e simulados à direita, com os
dois grupos sobrepostos em cada painel. As horas são desenhadas em log10 num eixo linear, com as
marcas nas potências de 10 rotuladas em horas: o Plotly calcula as classes de `go.Histogram` na
escala linear, e elas ficariam distorcidas num eixo `type="log"`. As classes são as mesmas nas
quatro séries (largura de ¼ de década, alargada para no máximo `MAX_CLASSES`), calculadas sobre a
união dos dados; assim nenhum valor fica fora do eixo, mesmo com valores muito pequenos ou com
simulados numa escala muito diferente da real. Zeros recebem o piso da calibração
(`calibracao.logaritmos`); horas negativas ou ausentes levantam `ValueError`.

G2 (`g2`): como cada teste decide num exemplo da S01-08, Welch à esquerda e Mann-Whitney à
direita. Cada painel tem a curva da estatística sob H₀, a região de rejeição bicaudal em
α = 0,05, a estatística observada, o p-valor como área nas duas caudas e o histograma da
estatística em `N_H0` conjuntos simulados sob H₀ (ver `estatisticas_sob_h0`). O z do Mann-Whitney
segue a aproximação normal do SciPy, com correção de empates e de continuidade, então a área
desenhada é o `mw_p` do exemplo quando o método é o assintótico. O eixo x vai de −4 a 4 e se
estende até ±8 para incluir a estatística; além disso ela fica na borda, com uma anotação.
"""

import math

import numpy as np
import pandas as pd
from plotly import graph_objects as go
from plotly.subplots import make_subplots
from scipy import stats

from lab04 import calibracao, gerador
from lab04.descritiva import GRUPOS, horas_do_grupo

CORES_GRUPO = {"com_bot": "#1f77b4", "sem_bot": "#ff7f0e"}
NOMES_GRUPO = {"com_bot": "Com bot (A)", "sem_bot": "Sem bot (B)"}
CORES_TESTE = {"welch": "#2ca02c", "mann_whitney": "#9467bd"}
NOMES_TESTE = {"welch": "Welch", "mann_whitney": "Mann-Whitney"}
COR_REJEICAO = "#d62728"
COR_REJEICAO_AREA = "rgba(214, 39, 40, 0.35)"  # o mesmo vermelho, transparente, no sombreado
COR_SIMULACAO = "#7f7f7f"

LARGURA_CLASSE = 0.25  # em décadas de log10(horas)
MAX_CLASSES = 40
OPACIDADE = 0.6

ALFA = 0.05
N_H0 = 10_000  # conjuntos simulados sob H₀ no histograma do G2
LIMITE_PADRAO = 4.0  # o eixo x do G2 vai de −4 a 4 ...
LIMITE_MAXIMO = 8.0  # ... e se estende até ±8 para incluir a estatística observada
LARGURA_CLASSE_H0 = 0.2
P_QUASE_INVISIVEL = 1e-3

TEXTO_G1 = (
    "Os histogramas mostram as horas até o merge dos 30 PRs de cada grupo no supabase/supabase "
    "(esquerda) e de 30 PRs por grupo simulados pela lognormal calibrada (direita), num eixo em escala log. "
    "Na escala log os quatro histogramas têm forma de sino parecida, centrada entre 10 e 20 h, o que "
    "sustenta a escolha da lognormal; em horas, a distribuição é fortemente assimétrica à direita, com "
    "cauda até cerca de 4.000 h no sem_bot real. "
    "O modelo põe alguns PRs abaixo de 1 h, faixa que o protocolo de coleta exclui, e não reproduz o PR "
    "mais extremo do sem_bot, cuja cauda é mais pesada que a do modelo de σ único; por isso o cenário de "
    "outliers (C3) também entra na simulação. "
    "Com n = 30 o sorteio pesa: no conjunto simulado a mediana de B (10 h) ficou abaixo da de A (20 h), "
    "embora o modelo dê a B uma mediana 42% maior (e^δ = 1,42)."
)


def _log10(horas, origem: str) -> np.ndarray:
    x = np.asarray(horas, dtype=float)
    if x.ndim != 1:
        raise ValueError(f"{origem}: as horas devem ser um vetor (1 dimensão)")
    try:
        logs, _ = calibracao.logaritmos(x)
    except ValueError as erro:
        raise ValueError(f"{origem}: {erro}") from erro
    return logs / math.log(10)


def _bordas(series) -> np.ndarray:
    """Bordas das classes em log10, comuns a todas as séries, em múltiplos de ¼ de década."""
    todos = np.concatenate(series)
    if todos.size == 0:
        raise ValueError("não há horas para desenhar")
    passos = 1 / LARGURA_CLASSE
    inicio = math.floor(todos.min() * passos) / passos
    fim = math.ceil(todos.max() * passos) / passos
    largura = LARGURA_CLASSE
    if (fim - inicio) / largura > MAX_CLASSES:
        largura = math.ceil((fim - inicio) / MAX_CLASSES * passos) / passos
    n_classes = max(1, math.ceil((fim - inicio) / largura - 1e-9))
    return inicio + largura * np.arange(n_classes + 1)


def _rotulo_horas(expoente: int) -> str:
    """10^expoente em horas, no formato brasileiro (0,01 · 1 · 1.000)."""
    if expoente >= 0:
        return f"{10 ** expoente:,}".replace(",", ".")
    return f"{10.0 ** expoente:.{-expoente}f}".replace(".", ",")


def g1(reais: pd.DataFrame, simulados: tuple) -> go.Figure:
    """Histogramas das horas até o merge: dados reais ao lado dos simulados (S01-09).

    `reais` tem as colunas `grupo` e `horas_ate_merge` (o `prs.csv` da coleta); `simulados` é o par
    `(A, B)` do gerador, com A no papel do `com_bot` e B no do `sem_bot`.
    """
    a, b = simulados
    paineis = {
        "reais": {g: _log10(horas_do_grupo(reais, g), f"reais/{g}") for g in GRUPOS},
        "simulados": {g: _log10(x, f"simulados/{g}") for g, x in zip(GRUPOS, (a, b))},
    }
    bordas = _bordas([x for painel in paineis.values() for x in painel.values()])
    largura = float(bordas[1] - bordas[0])
    centros = (bordas[:-1] + bordas[1:]) / 2
    faixas = np.column_stack([10 ** bordas[:-1], 10 ** bordas[1:]])

    def contagem(painel):
        return ", ".join(f"{NOMES_GRUPO[g].split(' (')[0].lower()}: {len(x)}" for g, x in painel.items())

    titulos = [
        f"Dados reais ({contagem(paineis['reais'])} PRs)",
        f"Simulados: lognormal calibrada ({contagem(paineis['simulados'])} PRs)",
    ]
    figura = make_subplots(rows=1, cols=2, shared_xaxes=True, shared_yaxes=True, subplot_titles=titulos)
    for coluna, painel in enumerate(paineis.values(), start=1):
        for grupo, logs in painel.items():
            frequencias, _ = np.histogram(logs, bins=bordas)
            figura.add_trace(
                go.Bar(
                    x=centros,
                    y=frequencias,
                    width=largura,
                    name=NOMES_GRUPO[grupo],
                    legendgroup=grupo,
                    showlegend=coluna == 1,
                    marker={"color": CORES_GRUPO[grupo], "line": {"width": 0}},
                    opacity=OPACIDADE,
                    customdata=faixas,
                    hovertemplate="%{customdata[0]:.3g} a %{customdata[1]:.3g} h<br>%{y} PRs",
                ),
                row=1,
                col=coluna,
            )

    expoentes = range(math.floor(bordas[0]), math.ceil(bordas[-1]) + 1)
    figura.update_xaxes(
        title_text="Horas até o merge (h, escala log)",
        tickvals=list(expoentes),
        ticktext=[_rotulo_horas(e) for e in expoentes],
        range=[float(bordas[0]), float(bordas[-1])],
    )
    figura.update_yaxes(title_text="Frequência (nº de PRs)", row=1, col=1)
    figura.update_layout(
        title="G1: horas até o merge, dados reais × simulados",
        barmode="overlay",
        bargap=0,
        legend_title_text="Grupo",
        template="plotly_white",
    )
    return figura


TEXTO_G2 = (
    "Cada painel mostra a distribuição da estatística quando H₀ é verdadeira: a t de Student do Welch, que "
    "compara as médias dos grupos, e o z do Mann-Whitney, que compara os postos dos valores de um grupo em "
    "relação aos do outro; em cinza, a mesma estatística em 10.000 conjuntos simulados sob H₀. "
    "A região de rejeição (vermelho) são as duas caudas que somam α = 5%, e o p-valor (hachurado) é a área "
    "além da estatística observada nas duas caudas: a probabilidade de uma estatística pelo menos tão "
    "extrema se H₀ fosse verdadeira. "
    "Nos dois exemplos nenhuma estatística cai na região de rejeição, o que é a decisão certa sem efeito e "
    "um erro tipo II com efeito, em que os testes chegam a apontar para lados opostos (a média de A é "
    "menor, mas seus postos são maiores). "
    "Com a lognormal calibrada, o histograma do t fica achatado, com dois ombros, e só cerca de 2,5% dos "
    "conjuntos sob H₀ caem na região de rejeição, contra 5% do Mann-Whitney: com essa assimetria e n = 30, "
    "o Welch rejeita menos que o α nominal."
)


def _num(valor: float, casas: int = 3) -> str:
    """Número no formato brasileiro, com o sinal de menos tipográfico."""
    return f"{valor:.{casas}f}".replace("-", "−").replace(".", ",")


def _p_rotulo(p: float) -> str:
    if not math.isfinite(p):
        return "indefinido"
    if p < P_QUASE_INVISIVEL:
        return f"{p:.1e}".replace("-", "−").replace(".", ",")
    return _num(p)


def _termo_empates(valores) -> float:
    """Σ(t³ − t) sobre os grupos de valores empatados."""
    _, contagens = np.unique(valores, return_counts=True)
    return float((contagens.astype(float) ** 3 - contagens).sum())


def z_mann_whitney(u, n1: int, n2: int, termo_empates=0.0):
    """z do Mann-Whitney pela aproximação normal do SciPy (empates e continuidade).

    `u` é a estatística U do primeiro grupo (escalar ou vetor). O sinal acompanha `u − n1·n2/2`,
    e a correção de continuidade aproxima o z de zero em 0,5 sem trocar o sinal; assim
    `2 · (1 − Φ(|z|))` é o p-valor bicaudal assintótico do SciPy.
    """
    n = n1 + n2
    desvio = np.sqrt(n1 * n2 / 12 * ((n + 1) - np.asarray(termo_empates, dtype=float) / (n * (n - 1))))
    distancia = np.asarray(u, dtype=float) - n1 * n2 / 2
    with np.errstate(divide="ignore", invalid="ignore"):
        return np.sign(distancia) * np.maximum(np.abs(distancia) - 0.5, 0) / desvio


def estatisticas_sob_h0(exemplo: dict, n_rep: int = N_H0) -> dict:
    """t de Welch e z do Mann-Whitney em `n_rep` conjuntos simulados sob H₀ (δ = 0).

    Usa o cenário e o `n` do exemplo, com a semente `[semente do exemplo, 0]`: reprodutível e
    sem repetir os sorteios do próprio exemplo. Devolve `{"welch_t": ndarray, "mw_z": ndarray}`;
    conjuntos sem variância (t indefinido) ficam de fora do Welch.
    """
    n = exemplo["n"]
    rng = np.random.default_rng([int(exemplo["semente"]), 0])
    A, B = gerador.gerar_lote(exemplo["cenario"], 0.0, n, n_rep, rng)
    with np.errstate(all="ignore"):
        t = stats.ttest_ind(A, B, axis=1, equal_var=False).statistic
    u = stats.mannwhitneyu(A, B, axis=1, alternative="two-sided", method="asymptotic").statistic
    juntos = np.sort(np.concatenate([A, B], axis=1), axis=1)
    termos = np.zeros(n_rep)
    for linha in np.flatnonzero((np.diff(juntos, axis=1) == 0).any(axis=1)):
        termos[linha] = _termo_empates(juntos[linha])
    return {"welch_t": t[np.isfinite(t)], "mw_z": z_mann_whitney(u, n, n, termos)}


def _paineis_g2(exemplo: dict) -> list:
    """Dados de cada painel do G2: estatística observada, distribuição sob H₀ e p-valor."""
    r = exemplo["resultado"]
    a, b = np.asarray(exemplo["a"], dtype=float), np.asarray(exemplo["b"], dtype=float)
    z = float(z_mann_whitney(r["mw_u"], len(a), len(b), _termo_empates(np.concatenate([a, b]))))
    p_area_mw = float(2 * stats.norm.sf(abs(z))) if math.isfinite(z) else float("nan")
    rotulo_mw = f"p-valor = {_p_rotulo(r['mw_p'])}"
    if r["mw_metodo"] == "exact":
        rotulo_mw = f"p-valor (aprox. normal) = {_p_rotulo(p_area_mw)} · p-valor exato = {_p_rotulo(r['mw_p'])}"
    gl = r["welch_gl"]
    return [
        {
            "teste": "welch",
            "simbolo": "t",
            "eixo": "Estatística t de Welch (adimensional)",
            "curva": f"t de Student, gl = {_num(gl, 1)}" if math.isfinite(gl) else "t de Student",
            "distribuicao": stats.t(gl) if math.isfinite(gl) else stats.norm(),
            "observado": r["welch_t"],
            "p": r["welch_p"],
            "rotulo_p": f"p-valor = {_p_rotulo(r['welch_p'])}",
        },
        {
            "teste": "mann_whitney",
            "simbolo": "z",
            "eixo": "Estatística z do Mann-Whitney (adimensional)",
            "curva": "normal padrão",
            "distribuicao": stats.norm(),
            "observado": z,
            "p": p_area_mw,
            "rotulo_p": rotulo_mw,
        },
    ]


def _area(x, dist, nome, grupo, mostrar_legenda, hover, *, cor=None, hachura=None) -> go.Scatter:
    """Área sob a curva `dist` nos pontos `x` (uma cauda): sólida em `cor` ou hachurada em `hachura`.

    A hachura deixa ver o que está por baixo: o p-valor (hachurado) e a região de rejeição
    (sólida) aparecem os dois onde se sobrepõem.
    """
    preenchimento = {"fillcolor": cor}
    if hachura is not None:
        preenchimento = {
            "fillcolor": "rgba(0,0,0,0)",
            "fillpattern": {"shape": "/", "fgcolor": hachura, "bgcolor": "rgba(0,0,0,0)", "size": 7, "solidity": 0.35},
        }
    return go.Scatter(
        x=x, y=dist.pdf(x), mode="lines", line={"width": 0}, fill="tozeroy", **preenchimento,
        name=nome, legendgroup=grupo, showlegend=mostrar_legenda, hoverinfo="text", text=hover,
    )


def g2(exemplo: dict) -> go.Figure:
    """Estatística sob H₀, região de rejeição e p-valor de cada teste num exemplo (S01-10).

    `exemplo` é o retorno de `gerador.exemplo_simulado` (S01-08).
    """
    paineis = _paineis_g2(exemplo)
    sob_h0 = estatisticas_sob_h0(exemplo)
    delta = exemplo["delta"]
    caso = "sem efeito (δ = 0)" if delta == 0 else f"com efeito (δ = {_num(delta, 2)})"
    figura = make_subplots(rows=1, cols=2, subplot_titles=[NOMES_TESTE[p["teste"]] for p in paineis])

    for coluna, painel in enumerate(paineis, start=1):
        teste, simbolo = painel["teste"], painel["simbolo"]
        cor, nome = CORES_TESTE[teste], NOMES_TESTE[teste]
        dist, obs = painel["distribuicao"], painel["observado"]
        finito = math.isfinite(obs)
        limite = LIMITE_PADRAO
        if finito:
            limite = min(max(LIMITE_PADRAO, float(math.ceil(abs(obs) + 0.5))), LIMITE_MAXIMO)
        x = np.linspace(-limite, limite, 801)
        critico = float(dist.ppf(1 - ALFA / 2))
        topo = float(dist.pdf(0))
        celula = {"row": 1, "col": coluna}

        bordas = np.arange(-limite, limite + LARGURA_CLASSE_H0 / 2, LARGURA_CLASSE_H0)
        valores = sob_h0["welch_t" if teste == "welch" else "mw_z"]
        contagens, _ = np.histogram(valores, bins=bordas)
        figura.add_trace(
            go.Bar(
                x=(bordas[:-1] + bordas[1:]) / 2,
                y=contagens / (len(valores) * LARGURA_CLASSE_H0),
                width=LARGURA_CLASSE_H0,
                marker={"color": COR_SIMULACAO, "line": {"width": 0}},
                opacity=0.35,
                name=f"Simulação sob H₀ ({len(valores):,} conjuntos)".replace(",", "."),
                legendgroup="simulacao",
                showlegend=coluna == 1,
                hovertemplate="densidade %{y:.3f}<extra></extra>",
            ),
            **celula,
        )
        for lado in (-1, 1):
            figura.add_trace(
                _area(x[lado * x >= critico], dist, f"Região de rejeição (α = {_num(ALFA, 2)})", "rejeicao",
                      coluna == 1 and lado == 1, f"|{simbolo}| ≥ {_num(critico, 2)}", cor=COR_REJEICAO_AREA),
                **celula,
            )
            figura.add_vline(x=lado * critico, line={"color": COR_REJEICAO, "dash": "dash", "width": 1}, **celula)
        if finito:
            for lado in (-1, 1):
                figura.add_trace(
                    _area(x[lado * x >= abs(obs)], dist, f"{nome}: p-valor (área)", f"p_{teste}", lado == 1,
                          painel["rotulo_p"], hachura=cor),
                    **celula,
                )
        figura.add_trace(
            go.Scatter(x=x, y=dist.pdf(x), mode="lines", line={"color": cor, "width": 2.5},
                       name=f"{nome}: curva sob H₀ ({painel['curva']})", legendgroup=f"curva_{teste}"),
            **celula,
        )
        if finito:
            dentro = abs(obs) <= limite
            posicao = obs if dentro else math.copysign(limite, obs)
            figura.add_trace(
                go.Scatter(x=[posicao, posicao], y=[0, topo * 1.05], mode="lines", line={"color": cor, "width": 3},
                           name=f"{nome}: {simbolo} observado = {_num(obs, 2)}", legendgroup=f"obs_{teste}"),
                **celula,
            )
            if not dentro:
                figura.add_annotation(
                    x=posicao, y=topo * 0.6, showarrow=False, xanchor="right" if obs > 0 else "left",
                    text=f"{simbolo} = {_num(obs, 1)} (fora do eixo) {'→' if obs > 0 else '←'}", **celula,
                )

        rotulo = painel["rotulo_p"]
        if math.isfinite(painel["p"]) and painel["p"] < P_QUASE_INVISIVEL:
            rotulo += " (área quase invisível)"
        figura.add_annotation(
            x=0.02, y=0.98, xref="x domain", yref="y domain", xanchor="left", yanchor="top", showarrow=False,
            text=rotulo, bgcolor="rgba(255,255,255,0.8)", **celula,
        )
        figura.update_xaxes(title_text=painel["eixo"], range=[-limite, limite], **celula)
        figura.update_yaxes(title_text="Densidade de probabilidade", rangemode="tozero", **celula)

    figura.update_layout(
        title=f"G2: como os testes decidem, exemplo {caso}",
        barmode="overlay",
        bargap=0,
        legend={"orientation": "h", "y": -0.25},
        template="plotly_white",
    )
    return figura
