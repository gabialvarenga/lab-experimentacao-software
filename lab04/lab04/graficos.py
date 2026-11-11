"""Gráficos G1 a G4 em Plotly (S01-09, S01-10, S02-08, S02-09).

G4 (`g4`): curvas de poder, a proporção de rejeições de cada teste em função do tamanho do efeito,
uma faceta por cenário com as duas curvas no mesmo gráfico (Q2 e Q3). Cada faceta tem o seu eixo x:
em C0 o efeito é δ em desvios-padrão; nos demais cenários δ está na escala log e os rótulos do eixo
mostram a razão de medianas e^δ. Em δ = 0 a curva é o erro tipo I (o G3), e a linha em α serve de
referência. As curvas usam símbolos e traços diferentes para continuarem legíveis onde se sobrepõem
(C0). Como o G3, lê o formato de CSV congelado na S02-01.

G3 (`g3`): erro tipo I de cada teste em cada situação simulada (Q1 e Q3), isto é, a taxa de rejeição
com H₀ verdadeira (δ = 0). Barras agrupadas por cenário, uma por teste, com a linha no nível
nominal (α = 5%) e o intervalo de Wilson de 95% como barra de erro. Lê o formato de CSV congelado
na S02-01 (`resultados.csv`, ou o `piloto.csv`) e desenha os cenários que estão na tabela; o hover
traz a taxa, o intervalo, as rejeições e a classificação (liberal, conservador ou ok) de
`resultados.classificar`.

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
from lab04.resultados import classificar

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
NOMES_CENARIO = {   # os nomes do config.yaml, para os rótulos do G3 e do G4
    "C0": "C0: controle (normal)",
    "C1": "C1: referência (lognormal)",
    "C2": "C2: assimetria forte",
    "C3": "C3: outliers",
    "C4": "C4: amostra pequena (n = 10)",
}
UNIDADE_EFEITO = {"C0": "dp"}   # δ em desvios-padrão no controle normal; nos demais cenários, "log" (razão de medianas = e^δ)
MAXIMO_DE_COLUNAS_G4 = 3
COLUNAS_RESULTADOS = ("cenario", "delta", "n", "n_rep", "alfa", "teste", "rejeicoes", "taxa", "ic_inf", "ic_sup")
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

TEXTO_G3 = (
    "Com H₀ verdadeira, o Mann-Whitney ficou perto de 5% em todas as situações, entre 4,35% e 4,96%; em C0 e "
    "em C4 o desvio é pequeno (−0,57 e −0,65 pontos percentuais), mas o intervalo de 95% não alcança 5%, e por "
    "isso o teste é classificado como conservador. "
    "O Welch só ficou perto de 5% no controle normal (4,63%): em C1 a C4, em que os dados violam a normalidade, "
    "ele rejeitou apenas de 1,54% a 2,47%, ou seja, ficou conservador e se desviou muito do nominal. "
    "Nenhum teste foi liberal, então nenhum produz falsos positivos além do nível escolhido, mas um teste "
    "conservador detecta menos efeitos reais (G4). "
    "Com α = 1% a classificação é a mesma."
)

TEXTO_G4 = (
    "O Mann-Whitney detecta o efeito melhor em C1 a C4, as situações em que os dados violam a normalidade: em C1, "
    "com a mediana de B 3,3 vezes a de A (δ = 1,2), ele rejeita H₀ em 76,9% dos conjuntos e o Welch em 36,7%, e a "
    "vantagem máxima de cada cenário fica entre 41 e 60 pontos percentuais. "
    "No controle normal (C0) o Welch lidera, mas por no máximo 3,0 pontos percentuais, e as duas curvas quase se "
    "sobrepõem. "
    "A vantagem muda de lado entre os cenários, do Welch no caso normal para o Mann-Whitney em todos os outros, e "
    "não muda ao longo do efeito dentro de nenhum deles. "
    "Com α = 1% o quadro é o mesmo."
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


def _validar_resultados(resultados: pd.DataFrame) -> None:
    """`ValueError` se faltam colunas do CSV de resultados ou se há um teste que os gráficos não conhecem."""
    faltam = [c for c in COLUNAS_RESULTADOS if c not in resultados.columns]
    if faltam:
        raise ValueError(f"faltam as colunas {faltam} em resultados")
    desconhecidos = sorted(set(resultados["teste"]) - set(NOMES_TESTE))
    if desconhecidos:
        raise ValueError(f"testes desconhecidos em resultados: {desconhecidos}")


def g3(resultados: pd.DataFrame, alfa: float = ALFA, nomes: dict | None = None) -> go.Figure:
    """Erro tipo I de cada teste por situação simulada (Q1 e Q3), com a linha no nível nominal (S02-08).

    `resultados` está no formato de CSV congelado na S02-01. Usa as linhas de δ = 0 no nível `alfa`
    (5% por padrão) e desenha um grupo de barras por cenário, na ordem em que aparecem na tabela,
    uma barra por teste, com o intervalo de Wilson de 95% como barra de erro. `nomes` troca os
    rótulos dos cenários (padrão: `NOMES_CENARIO`; um id desconhecido aparece como ele mesmo).
    Levanta `ValueError` se faltam colunas, se há um teste desconhecido ou se não há linha de δ = 0
    no nível pedido.
    """
    _validar_resultados(resultados)
    h0 = resultados[(resultados["delta"] == 0) & np.isclose(resultados["alfa"], alfa)]
    if h0.empty:
        raise ValueError(f"resultados não tem linhas de δ = 0 com α = {alfa}")
    classes = classificar(h0).set_index(["cenario", "teste"])["classificacao"]
    rotulos = {**NOMES_CENARIO, **(nomes or {})}
    cenarios = list(dict.fromkeys(h0["cenario"]))
    x = [rotulos.get(c, c) for c in cenarios]
    pct = lambda valor: f"{_num(valor * 100, 2)}%"   # noqa: E731
    nivel = f"{_num(alfa * 100, 0 if alfa * 100 == int(alfa * 100) else 1)}%"

    figura = go.Figure()
    for teste in NOMES_TESTE:
        linhas = h0[h0["teste"] == teste].set_index("cenario").reindex(cenarios)
        figura.add_trace(
            go.Bar(
                x=x,
                y=linhas["taxa"] * 100,
                name=NOMES_TESTE[teste],
                marker={"color": CORES_TESTE[teste]},
                error_y={
                    "type": "data", "symmetric": False,
                    "array": (linhas["ic_sup"] - linhas["taxa"]) * 100,
                    "arrayminus": (linhas["taxa"] - linhas["ic_inf"]) * 100,
                    "color": "#333333", "thickness": 1.5, "width": 4,
                },
                customdata=[
                    [pct(r.taxa), pct(r.ic_inf), pct(r.ic_sup), int(r.rejeicoes), int(r.n_rep), int(r.n),
                     classes.get((c, teste), "—")]
                    for c, r in zip(cenarios, linhas.itertuples())
                ],
                hovertemplate=(
                    f"<b>{NOMES_TESTE[teste]}</b><br>%{{x}}<br>Taxa de rejeição: %{{customdata[0]}}<br>"
                    "IC de Wilson de 95%: [%{customdata[1]}; %{customdata[2]}]<br>"
                    "Rejeições: %{customdata[3]} de %{customdata[4]}<br>n = %{customdata[5]} por grupo<br>"
                    "Classificação: %{customdata[6]}<extra></extra>"
                ),
            )
        )
    figura.add_trace(   # entrada de legenda para a linha, que o Plotly não lista sozinho
        go.Scatter(x=[None], y=[None], mode="lines", line={"color": COR_REJEICAO, "dash": "dash", "width": 2},
                   name=f"Nível nominal (α = {nivel})")
    )
    figura.add_hline(y=alfa * 100, line={"color": COR_REJEICAO, "dash": "dash", "width": 2})

    topo = max(float((h0["ic_sup"] * 100).max()), alfa * 100) * 1.15
    repeticoes = " e ".join(f"{n:,}".replace(",", ".") for n in sorted(set(h0["n_rep"])))
    figura.update_layout(
        title=(
            "G3: erro tipo I de cada teste por situação simulada"
            f"<br><sup>H₀ verdadeira (δ = 0), α = {nivel}; barras de erro: intervalo de Wilson de 95% "
            f"({repeticoes} repetições por barra)</sup>"
        ),
        xaxis={"title": {"text": "Situação simulada (cenário)"}},
        yaxis={"title": {"text": "Taxa de rejeição com H₀ verdadeira (%)"}, "range": [0, topo], "ticksuffix": "%"},
        barmode="group",
        legend={"orientation": "h", "y": -0.25},
        template="plotly_white",
    )
    return figura

def _rotulos_do_efeito(deltas, unidade: str) -> list:
    """Rótulos do eixo x de uma faceta: δ em desvios-padrão (`dp`) ou a razão de medianas e^δ (`log`)."""
    if unidade == "dp":
        return [_num(d, 1) for d in deltas]
    return [f"{_num(math.exp(d), 1)}×" for d in deltas]


def g4(resultados: pd.DataFrame, alfa: float = ALFA, nomes: dict | None = None, unidades: dict | None = None) -> go.Figure:
    """Curvas de poder dos dois testes por situação simulada (Q2 e Q3), uma faceta por cenário (S02-09).

    `resultados` está no formato de CSV congelado na S02-01. Usa as linhas do nível `alfa` (5% por
    padrão) e desenha, em cada faceta, a proporção de rejeições em função do efeito δ, com a curva
    do Welch e a do Mann-Whitney no mesmo gráfico e a linha em `alfa` como referência (em δ = 0 a
    curva é o erro tipo I). Cada faceta tem o seu eixo x: `unidades` diz, por cenário, se δ está em
    desvios-padrão (`dp`, padrão em C0) ou na escala log (`log`, padrão nos demais), cujos rótulos
    mostram a razão de medianas e^δ. `nomes` troca os rótulos dos cenários (padrão: `NOMES_CENARIO`).
    Levanta `ValueError` se faltam colunas, se há um teste desconhecido ou se não há linhas de efeito
    (δ > 0) no nível pedido.
    """
    _validar_resultados(resultados)
    nivel_alfa = resultados[np.isclose(resultados["alfa"], alfa)]
    if not (nivel_alfa["delta"] > 0).any():
        raise ValueError(f"resultados não tem linhas com efeito (δ > 0) e α = {alfa}")
    rotulos = {**NOMES_CENARIO, **(nomes or {})}
    unidade_de = {**UNIDADE_EFEITO, **(unidades or {})}
    cenarios = list(dict.fromkeys(nivel_alfa["cenario"]))
    colunas = min(len(cenarios), MAXIMO_DE_COLUNAS_G4)
    linhas = math.ceil(len(cenarios) / colunas)
    classes = classificar(nivel_alfa[nivel_alfa["delta"] == 0]).set_index(["cenario", "teste"])["classificacao"]
    pct = lambda valor: f"{_num(valor * 100, 2)}%"   # noqa: E731
    nivel = f"{_num(alfa * 100, 0 if alfa * 100 == int(alfa * 100) else 1)}%"

    figura = make_subplots(
        rows=linhas, cols=colunas, shared_yaxes=True, horizontal_spacing=0.05, vertical_spacing=0.24 / linhas,
        subplot_titles=[rotulos.get(c, c) for c in cenarios],
    )
    estilo = {"welch": {"symbol": "circle", "dash": "solid"}, "mann_whitney": {"symbol": "diamond", "dash": "dash"}}
    for posicao, cenario in enumerate(cenarios):
        linha, coluna = posicao // colunas + 1, posicao % colunas + 1
        unidade = unidade_de.get(cenario, "log")
        dados = nivel_alfa[nivel_alfa["cenario"] == cenario]
        deltas = sorted(set(dados["delta"]))
        for teste in NOMES_TESTE:
            curva = dados[dados["teste"] == teste].sort_values("delta")
            if curva.empty:
                continue
            figura.add_trace(
                go.Scatter(
                    x=curva["delta"], y=curva["taxa"] * 100, mode="lines+markers", name=NOMES_TESTE[teste],
                    legendgroup=teste, showlegend=posicao == 0,
                    line={"color": CORES_TESTE[teste], "width": 2.5, "dash": estilo[teste]["dash"]},
                    marker={"color": CORES_TESTE[teste], "size": 8, "symbol": estilo[teste]["symbol"]},
                    customdata=[
                        [_num(r.delta, 1), f"{_num(math.exp(r.delta), 2)}×" if unidade == "log" else "—",
                         pct(r.taxa), pct(r.ic_inf), pct(r.ic_sup), int(r.rejeicoes), int(r.n_rep), int(r.n),
                         "erro tipo I" if r.delta == 0 else "poder", classes.get((cenario, teste), "—") if r.delta == 0 else ""]
                        for r in curva.itertuples()
                    ],
                    hovertemplate=(
                        f"<b>{NOMES_TESTE[teste]}</b>, {rotulos.get(cenario, cenario)}<br>δ = %{{customdata[0]}}"
                        + ("  (razão de medianas %{customdata[1]})" if unidade == "log" else " desvio-padrão")
                        + "<br>Taxa de rejeição (%{customdata[8]}): %{customdata[2]}<br>"
                        "IC de Wilson de 95%: [%{customdata[3]}; %{customdata[4]}]<br>"
                        "Rejeições: %{customdata[5]} de %{customdata[6]}<br>n = %{customdata[7]} por grupo"
                        "<extra></extra>"
                    ),
                ),
                row=linha, col=coluna,
            )
        titulo_x = "Efeito δ (desvios-padrão)" if unidade == "dp" else "Razão de medianas B/A (×)"
        figura.update_xaxes(title_text=titulo_x, tickmode="array", tickvals=deltas,
                            ticktext=_rotulos_do_efeito(deltas, unidade), row=linha, col=coluna)
        if coluna == 1:
            figura.update_yaxes(title_text="Proporção de rejeições de H₀ (%)", row=linha, col=coluna)
    figura.add_trace(   # entrada de legenda para a linha de referência
        go.Scatter(x=[None], y=[None], mode="lines", line={"color": COR_REJEICAO, "dash": "dot", "width": 2},
                   name=f"Nível nominal (α = {nivel})")
    )
    figura.add_hline(y=alfa * 100, line={"color": COR_REJEICAO, "dash": "dot", "width": 2}, row="all", col="all")
    figura.update_yaxes(range=[0, 103], ticksuffix="%")
    figura.update_xaxes(zeroline=False)   # sem a linha vertical em δ = 0
    repeticoes = " e ".join(f"{n:,}".replace(",", ".") for n in sorted(set(nivel_alfa["n_rep"])))
    figura.update_layout(
        title=(
            "G4: poder dos testes por tamanho de efeito e situação simulada"
            "<br><sup>Proporção de rejeições de H₀ com o efeito verdadeiro; em δ = 0 é o erro tipo I.</sup>"
            f"<br><sup>α = {nivel}, {repeticoes} repetições por ponto"
            + ("; fora de C0, o eixo x está na escala log de δ." if any(unidade_de.get(c, "log") == "log" for c in cenarios) else ".")
            + "</sup>"
        ),
        legend={"orientation": "h", "y": -0.14 / linhas},
        height=430 * linhas + 160,
        margin={"t": 140},
        template="plotly_white",
    )
    return figura
