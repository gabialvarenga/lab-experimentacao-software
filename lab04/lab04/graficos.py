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
"""

import math

import numpy as np
import pandas as pd
from plotly import graph_objects as go
from plotly.subplots import make_subplots

from lab04 import calibracao
from lab04.descritiva import GRUPOS, horas_do_grupo

CORES_GRUPO = {"com_bot": "#1f77b4", "sem_bot": "#ff7f0e"}
NOMES_GRUPO = {"com_bot": "Com bot (A)", "sem_bot": "Sem bot (B)"}

LARGURA_CLASSE = 0.25  # em décadas de log10(horas)
MAX_CLASSES = 40
OPACIDADE = 0.6

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
