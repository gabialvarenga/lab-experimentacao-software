"""Gráficos G1 a G4 em Plotly (S02-05) e a página de apresentação das figuras.

Só lê CSVs, nunca roda o benchmark. As funções recebem tabelas já lidas e devolvem
`plotly.graph_objects.Figure`; o dashboard (S02-09) usa as mesmas funções.

- G1 (`g1`): mediana de cada métrica por combinação, em barras com o valor escrito, Redis e Valkey
  lado a lado, a barra de erro do 1º ao 3º quartil e a razão Valkey ÷ Redis acima de cada par. Um
  painel por métrica, cada um com o seu eixo (a memória não some ao lado da vazão). Com o CV de cerca
  de 1% da coleta completa, um box plot vira um traço e não mostra a comparação, que é o que importa.
- G2 (`g2`): deriva ao longo da coleta. Cada valor é dividido pela mediana da sua combinação; o
  gráfico mostra os valores relativos por bloco (repetição) e a mediana de cada bloco, com a faixa
  de ±5%.
- G3 (`g3`): quem ganha em cada combinação. Razão de medianas Valkey/Redis com o IC de 95% por
  bootstrap, uma linha por combinação, com a faixa de empate [0,95; 1,05], o fundo de cada lado na cor
  do servidor que ganha ali (depende do sentido da métrica) e o ponto na cor do veredito (`veredito`,
  a partir da `situacao` do `analisar`). Lê `comparacoes.csv`. O eixo é log e nunca corta o IC.
- G4 (`g4`): interação servidor × `io_threads` (Q3): mediana de cada servidor com 1 e 4 threads, por
  carga, em escala log, com o IQR como barra.

`exportar` grava as quatro figuras em HTML (`g1.html` a `g4.html`, com o Plotly.js pela CDN) e
`apresentacao.html`, uma página única com as figuras e o texto de leitura de cada uma, pensada para
mostrar em sala: ela embute o Plotly.js (cerca de 4,7 MB) e abre sem internet.
"""

from datetime import datetime
from html import escape
from pathlib import Path

import numpy as np
import pandas as pd
from plotly import graph_objects as go
from plotly.subplots import make_subplots

from lab05.descritiva import CHAVES, METRICAS

SERVIDORES = ("redis", "valkey")
CORES_SERVIDOR = {"redis": "#e4572e", "valkey": "#2e86ab"}
NOMES_SERVIDOR = {"redis": "Redis 8.10.3", "valkey": "Valkey 9.1.3"}
CARGAS = ("set", "get", "misto")
NOMES_CARGA = {"set": "SET (1:0)", "get": "GET (0:1)", "misto": "Misto (1:4)"}
THREADS = (1, 4)
ROTULOS = {
    "ops_s": "Vazão (ops/s)",
    "lat_p50_ms": "Latência p50 (ms)",
    "lat_p99_ms": "Latência p99 (ms)",
    "memoria_bytes": "Memória usada (MiB)",
}
SENTIDO = {"ops_s": "maior é melhor", "lat_p50_ms": "menor é melhor", "lat_p99_ms": "menor é melhor",
           "memoria_bytes": "menor é melhor"}
NOMES_METRICA = {"ops_s": "Vazão", "lat_p50_ms": "Latência p50", "lat_p99_ms": "Latência p99", "memoria_bytes": "Memória"}
ESCALA = {"memoria_bytes": 1 / 2**20}   # bytes -> MiB só no desenho; os CSVs continuam em bytes
FAIXA = (0.95, 1.05)                    # diferença relevante do plano de análise (seção 6)
COR_FAIXA = "rgba(120, 120, 120, 0.15)"
COR_NEUTRA = "#444444"
METRICAS_DERIVA = ("ops_s", "lat_p99_ms")
METRICAS_Q3 = ("ops_s", "lat_p99_ms")
COLUNAS_COMPARACOES = ("metrica", "io_threads", "carga", "razao_medianas", "ic_inf", "ic_sup", "p_holm", "situacao")
FONTE = {"family": "system-ui, -apple-system, Segoe UI, sans-serif", "size": 13}

TEXTO_G1 = (
    "Cada painel é uma métrica, e o título diz se valor maior ou menor é melhor. Cada barra é o valor típico "
    "(mediana) das repetições de uma combinação, com o número escrito em cima (na vazão, \"k\" é mil ops/s): laranja é o Redis e azul é o Valkey, "
    "na mesma carga e com o mesmo número de threads de E/S. O texto \"V÷R\" acima de cada par é quantas vezes o "
    "valor do Valkey é o do Redis (1,00× é empate). O tracinho preto mostra a faixa entre o 1º e o 3º quartil; "
    "quando quase não aparece, é porque as repetições deram praticamente o mesmo valor."
)
TEXTO_G2 = (
    "Cada ponto é uma execução dividida pela mediana da sua combinação, então 1,0 é o valor típico. O eixo x é o "
    "bloco (repetição), na ordem em que a coleta rodou, e a linha preta é a mediana de cada bloco. Se a máquina "
    "tivesse ficado mais lenta ou mais rápida durante a noite, a linha sairia da faixa cinza de ±5%; uma linha "
    "plana mostra que não houve deriva."
)
TEXTO_G3 = (
    "Cada ponto compara os dois servidores numa combinação: é o valor do Valkey dividido pelo do Redis, e o número "
    "ao lado diz quantas vezes um é o outro (1,00× é empate). O fundo mostra quem ganha de cada lado; o lado muda "
    "com a métrica, porque na vazão maior é melhor e na latência e na memória menor é melhor. A faixa cinza do "
    "meio (±5%) é o empate na prática: diferenças ali dentro são pequenas demais para importar. A cor do ponto é o "
    "veredito do teste (Mann-Whitney com Holm), e a barra horizontal é o IC de 95%, tão estreito aqui que quase "
    "some atrás do ponto."
)
TEXTO_G4 = (
    "Cada painel é uma carga e cada linha liga a mediana de um servidor com 1 e com 4 threads de E/S (a barra é "
    "o IQR). O eixo y é log, então inclinações iguais significam o mesmo ganho relativo. Linhas paralelas indicam "
    "que mais threads ajudam os dois servidores igualmente; linhas que se abrem indicam interação, ou seja, um "
    "servidor aproveita melhor as threads que o outro (Q3)."
)
TEXTOS = {"g1": TEXTO_G1, "g2": TEXTO_G2, "g3": TEXTO_G3, "g4": TEXTO_G4}
TITULOS = {
    "g1": "G1 — Resultado de cada métrica: Redis × Valkey",
    "g2": "G2 — Deriva ao longo da coleta",
    "g3": "G3 — Quem ganha em cada combinação (Valkey ÷ Redis, com IC de 95%)",
    "g4": "G4 — Interação servidor × io_threads (Q3)",
}


def _conferir(df: pd.DataFrame, colunas, nome: str) -> None:
    faltando = [c for c in colunas if c not in df.columns]
    if faltando:
        raise ValueError(f"{nome} sem as colunas: {', '.join(faltando)}")
    if df.empty:
        raise ValueError(f"{nome} vazio")


def _valores(df: pd.DataFrame, metrica: str) -> pd.Series:
    return df[metrica].astype(float) * ESCALA.get(metrica, 1.0)


def _combinacao(carga: str, threads, quebra: bool = False) -> str:
    """Rótulo da combinação; `quebra` põe as threads numa segunda linha (eixos com muitas categorias)."""
    sep = "<br>" if quebra else " · "
    return f"{NOMES_CARGA.get(carga, carga)}{sep}{threads} thread{'s' if int(threads) > 1 else ''}"


def _layout(figura: go.Figure, titulo: str, altura: int) -> go.Figure:
    figura.update_layout(
        title={"text": titulo, "x": 0.01, "xanchor": "left"},
        height=altura,
        template="plotly_white",
        font=FONTE,
        separators=",.",   # vírgula decimal e ponto de milhar, como no texto
        legend={"orientation": "h", "yref": "container", "y": 0.995, "yanchor": "top", "x": 1, "xanchor": "right"},
        margin={"l": 70, "r": 20, "t": 100, "b": 60},
    )
    return figura


# --------------------------------------------------------------------------- G1


def _formatar(valor: float, metrica: str) -> str:
    """Valor curto para o rótulo da barra: vazão em milhares (k), latência em ms, memória em MiB."""
    if metrica == "ops_s":
        return f"{valor / 1000:.0f}k"
    casas = 1 if metrica == "memoria_bytes" else 2
    return f"{valor:.{casas}f}".replace(".", ",")


def g1(df: pd.DataFrame, metricas=METRICAS) -> go.Figure:
    """Mediana de cada métrica por combinação, em barras, Redis e Valkey lado a lado.

    Um painel por métrica, cada um com o seu eixo começando em zero. A barra é a mediana das
    repetições, com o valor escrito em cima, e a barra de erro vai do 1º ao 3º quartil. Acima de cada
    par aparece a razão Valkey ÷ Redis. O eixo x agrupa as cargas por número de threads de E/S.
    """
    _conferir(df, [*CHAVES, *metricas], "coleta")
    metricas = list(metricas)
    colunas = 2 if len(metricas) > 1 else 1
    linhas = -(-len(metricas) // colunas)
    figura = make_subplots(rows=linhas, cols=colunas, vertical_spacing=0.2, horizontal_spacing=0.08,
                           subplot_titles=[f"{ROTULOS[m]} · {SENTIDO[m]}" for m in metricas])
    grupos = [f"{t} thread{'s' if t > 1 else ''} de E/S" for t in THREADS for _ in CARGAS]
    cargas = [NOMES_CARGA[c] for _ in THREADS for c in CARGAS]
    for i, metrica in enumerate(metricas):
        linha, coluna = i // colunas + 1, i % colunas + 1
        valores = _valores(df, metrica).groupby([df["servidor"], df["io_threads"], df["carga"]])
        resumo = pd.DataFrame({"mediana": valores.median(), "q1": valores.quantile(0.25), "q3": valores.quantile(0.75)})
        topo = 0.0
        for servidor in SERVIDORES:
            chaves = [(servidor, t, c) for t in THREADS for c in CARGAS]
            r = resumo.reindex(chaves)
            if r["mediana"].isna().all():
                continue
            topo = max(topo, float(r["q3"].max()))
            figura.add_trace(go.Bar(
                x=[grupos, cargas], y=r["mediana"], name=NOMES_SERVIDOR[servidor], legendgroup=servidor,
                showlegend=i == 0, marker={"color": CORES_SERVIDOR[servidor]},
                error_y={"type": "data", "symmetric": False, "array": r["q3"] - r["mediana"],
                         "arrayminus": r["mediana"] - r["q1"], "thickness": 1.2, "width": 3, "color": "#333333"},
                text=[_formatar(v, metrica) if pd.notna(v) else "" for v in r["mediana"]],
                textposition="outside", cliponaxis=False, textfont={"size": 11},
                hovertemplate=f"{NOMES_SERVIDOR[servidor]}<br>%{{x}}<br>mediana: %{{y:,.4g}}<extra></extra>",
            ), row=linha, col=coluna)
        for (grupo, carga), (t, c) in zip(zip(grupos, cargas), [(t, c) for t in THREADS for c in CARGAS]):
            if ("valkey", t, c) in resumo.index and ("redis", t, c) in resumo.index:
                razao = resumo.loc[("valkey", t, c), "mediana"] / resumo.loc[("redis", t, c), "mediana"]
                figura.add_annotation(x=[grupo, carga], y=topo * 1.22, text=f"V÷R {_num(razao, 2)}×", showarrow=False,
                                      font={"size": 11, "color": "#555555"}, row=linha, col=coluna)
        figura.update_yaxes(range=[0, topo * 1.32], title_text=ROTULOS[metrica], row=linha, col=coluna)
        figura.update_xaxes(tickfont={"size": 11}, row=linha, col=coluna)
    figura.update_layout(barmode="group", bargap=0.25, bargroupgap=0.05, uniformtext={"minsize": 9, "mode": "show"})
    return _layout(figura, TITULOS["g1"], 400 * linhas + 140)


# --------------------------------------------------------------------------- G2


def relativos(df: pd.DataFrame, metrica: str) -> pd.Series:
    """Valor ÷ mediana da combinação (servidor, io_threads, carga)."""
    return df[metrica].astype(float) / df.groupby(CHAVES)[metrica].transform("median")


def g2(df: pd.DataFrame, metricas=METRICAS_DERIVA) -> go.Figure:
    """Métrica relativa por bloco (repetição), com a mediana de cada bloco e a faixa de ±5%."""
    _conferir(df, [*CHAVES, "repeticao", *metricas], "coleta")
    metricas = list(metricas)
    figura = make_subplots(rows=len(metricas), cols=1, shared_xaxes=True, vertical_spacing=0.1,
                           subplot_titles=[f"{ROTULOS[m]} relativa à mediana da combinação" for m in metricas])
    blocos = sorted(df["repeticao"].unique())
    for i, metrica in enumerate(metricas, start=1):
        rel = relativos(df, metrica)
        figura.add_hrect(y0=FAIXA[0], y1=FAIXA[1], fillcolor=COR_FAIXA, line_width=0, row=i, col=1)
        figura.add_hline(y=1, line={"color": COR_NEUTRA, "width": 1, "dash": "dot"}, row=i, col=1)
        for servidor in SERVIDORES:
            filtro = df["servidor"] == servidor
            if not filtro.any():
                continue
            parte = df[filtro]
            figura.add_trace(go.Scatter(
                x=parte["repeticao"] + (-0.15 if servidor == "redis" else 0.15), y=rel[filtro], mode="markers",
                name=NOMES_SERVIDOR[servidor], legendgroup=servidor, showlegend=i == 1,
                marker={"color": CORES_SERVIDOR[servidor], "size": 5, "opacity": 0.55},
                customdata=np.stack([parte["carga"], parte["io_threads"]], axis=-1),
                hovertemplate=f"{NOMES_SERVIDOR[servidor]}, bloco %{{x:.0f}}<br>carga %{{customdata[0]}}, "
                              f"%{{customdata[1]}} thread(s)<br>relativo: %{{y:.3f}}<extra></extra>",
            ), row=i, col=1)
        mediana = rel.groupby(df["repeticao"]).median().reindex(blocos)
        figura.add_trace(go.Scatter(
            x=blocos, y=mediana.values, mode="lines+markers", name="Mediana do bloco", legendgroup="bloco",
            showlegend=i == 1, line={"color": "#111111", "width": 2}, marker={"size": 5},
            hovertemplate="bloco %{x}<br>mediana relativa: %{y:.3f}<extra></extra>",
        ), row=i, col=1)
        figura.update_yaxes(title_text="valor ÷ mediana", row=i, col=1)
    figura.update_xaxes(title_text="Bloco (repetição, na ordem da coleta)", dtick=5 if len(blocos) > 10 else 1,
                        row=len(metricas), col=1)
    return _layout(figura, TITULOS["g2"], 300 * len(metricas) + 150)


# --------------------------------------------------------------------------- G3


VEREDITOS = {   # nome na legenda -> (cor, símbolo)
    "Valkey melhor": (CORES_SERVIDOR["valkey"], "circle"),
    "Redis melhor": (CORES_SERVIDOR["redis"], "circle"),
    "Empate na prática (diferença < 5%)": ("#8a8f98", "diamond"),
    "Inconclusivo": ("#8a8f98", "circle-open"),
}
COR_LADO = {"valkey": "rgba(46, 134, 171, 0.10)", "redis": "rgba(228, 87, 46, 0.10)"}


def veredito(metrica: str, razao: float, situacao: str) -> str:
    """Quem ganha numa comparação, pela situação da seção 6 do plano e pelo sentido da métrica.

    Só a vazão é "maior é melhor"; nas latências e na memória, razão abaixo de 1 favorece o Valkey.
    """
    if situacao == "diferença relevante":
        valkey_maior = razao > 1
        return "Valkey melhor" if valkey_maior == (metrica == "ops_s") else "Redis melhor"
    if situacao in ("diferença pequena demais", "equivalência prática"):
        return "Empate na prática (diferença < 5%)"
    return "Inconclusivo"


def g3(comparacoes: pd.DataFrame, metricas=METRICAS, alfa: float = 0.05) -> go.Figure:
    """Quem ganha em cada combinação: razão de medianas Valkey ÷ Redis com o IC de 95%.

    Um painel por métrica. O fundo de cada lado da faixa de empate tem a cor do servidor que ganha
    naquele lado (o lado muda com o sentido da métrica), e o ponto tem a cor do veredito, com o valor
    escrito ao lado. O eixo é log e nunca corta o IC. `alfa` fica para o dashboard; o veredito usa a
    `situacao` do `analisar`, que já aplica Holm.
    """
    _conferir(comparacoes, COLUNAS_COMPARACOES, "comparacoes")
    metricas = [m for m in metricas if (comparacoes["metrica"] == m).any()]
    figura = make_subplots(rows=1, cols=len(metricas), shared_yaxes=True, horizontal_spacing=0.025,
                           subplot_titles=[f"{NOMES_METRICA[m]} · {SENTIDO[m]}" for m in metricas])
    ordem = [_combinacao(c, t) for t in THREADS for c in CARGAS]
    minimo = float(np.nanmin(comparacoes[["ic_inf", "razao_medianas"]].to_numpy()))
    maximo = float(np.nanmax(comparacoes[["ic_sup", "razao_medianas"]].to_numpy()))
    lim = (min(minimo, FAIXA[0]) / 1.25, max(maximo, FAIXA[1]) * 1.25)
    faixa_x = [np.log10(lim[0]), np.log10(lim[1])]
    na_legenda = set()
    for j, metrica in enumerate(metricas, start=1):
        parte = comparacoes[comparacoes["metrica"] == metrica].copy()
        parte["rotulo"] = [_combinacao(c, t) for c, t in zip(parte["carga"], parte["io_threads"])]
        parte["veredito"] = [veredito(metrica, r, s) for r, s in zip(parte["razao_medianas"], parte["situacao"])]
        acima, abaixo = ("valkey", "redis") if metrica == "ops_s" else ("redis", "valkey")
        figura.add_vrect(x0=FAIXA[1], x1=lim[1], fillcolor=COR_LADO[acima], line_width=0, row=1, col=j)
        figura.add_vrect(x0=lim[0], x1=FAIXA[0], fillcolor=COR_LADO[abaixo], line_width=0, row=1, col=j)
        figura.add_vrect(x0=FAIXA[0], x1=FAIXA[1], fillcolor=COR_FAIXA, line_width=0, row=1, col=j)
        figura.add_vline(x=1, line={"color": COR_NEUTRA, "width": 1, "dash": "dot"}, row=1, col=j)
        eixo = "x" if j == 1 else f"x{j}"
        for x, texto, ancora in ((lim[0], f"← {NOMES_SERVIDOR[abaixo].split()[0]} melhor", "left"),
                                 (lim[1], f"{NOMES_SERVIDOR[acima].split()[0]} melhor →", "right")):
            lado = abaixo if ancora == "left" else acima
            figura.add_annotation(x=np.log10(x), y=1.0, xref=eixo, yref="paper", yanchor="bottom", xanchor=ancora,
                                  text=f"<b>{texto}</b>", showarrow=False,
                                  font={"size": 11, "color": CORES_SERVIDOR[lado]})
        for nome, (cor, simbolo) in VEREDITOS.items():
            sel = parte[parte["veredito"] == nome]
            if sel.empty:
                continue
            figura.add_trace(go.Scatter(
                x=sel["razao_medianas"], y=sel["rotulo"], mode="markers+text", name=nome, legendgroup=nome,
                showlegend=nome not in na_legenda,
                marker={"symbol": simbolo, "size": 12, "color": cor, "line": {"width": 2, "color": cor}},
                text=[f"{_num(r, 2)}×" for r in sel["razao_medianas"]], textposition="top center",
                textfont={"size": 11, "color": "#333333"},
                error_x={"type": "data", "symmetric": False, "array": sel["ic_sup"] - sel["razao_medianas"],
                         "arrayminus": sel["razao_medianas"] - sel["ic_inf"], "thickness": 2, "width": 5, "color": cor},
                customdata=np.stack([sel["ic_inf"], sel["ic_sup"], sel["p_holm"], sel["situacao"]], axis=-1),
                hovertemplate="%{y}<br>Valkey ÷ Redis: %{x:.3f}<br>IC 95%: [%{customdata[0]:.3f}; %{customdata[1]:.3f}]"
                              "<br>p (Holm): %{customdata[2]:.3g}<br>%{customdata[3]}<extra></extra>",
            ), row=1, col=j)
            na_legenda.add(nome)
        figura.update_xaxes(type="log", range=faixa_x, title_text="Valkey ÷ Redis (1 = empate)",
                            tickvals=[0.5, 0.6, 0.8, 1, 1.25, 1.6, 2], row=1, col=j)
    figura.update_yaxes(categoryorder="array", categoryarray=list(reversed(ordem)), row=1, col=1)
    titulos = {f"{NOMES_METRICA[m]} · {SENTIDO[m]}" for m in metricas}
    figura.for_each_annotation(lambda a: a.update(y=1.07, font={"size": 14}) if a.text in titulos else None)
    figura = _layout(figura, TITULOS["g3"], 540)
    figura.update_layout(margin={"t": 150})
    return figura


# --------------------------------------------------------------------------- G4


def g4(df: pd.DataFrame, metricas=METRICAS_Q3) -> go.Figure:
    """Mediana de cada servidor com 1 e 4 threads, por carga, em escala log (interação da Q3)."""
    _conferir(df, [*CHAVES, *metricas], "coleta")
    metricas = list(metricas)
    figura = make_subplots(rows=len(metricas), cols=len(CARGAS), shared_yaxes="rows", horizontal_spacing=0.04,
                           vertical_spacing=0.14, subplot_titles=[NOMES_CARGA[c] for _ in metricas for c in CARGAS])
    for i, metrica in enumerate(metricas, start=1):
        for j, carga in enumerate(CARGAS, start=1):
            for servidor in SERVIDORES:
                parte = df[(df["servidor"] == servidor) & (df["carga"] == carga)]
                if parte.empty:
                    continue
                v = _valores(parte, metrica).groupby(parte["io_threads"])
                resumo = pd.DataFrame({"mediana": v.median(), "q1": v.quantile(0.25), "q3": v.quantile(0.75)}).reindex(THREADS)
                figura.add_trace(go.Scatter(
                    x=[f"{t} thread{'s' if t > 1 else ''}" for t in THREADS], y=resumo["mediana"],
                    mode="lines+markers", name=NOMES_SERVIDOR[servidor], legendgroup=servidor,
                    showlegend=i == 1 and j == 1, line={"color": CORES_SERVIDOR[servidor], "width": 3},
                    marker={"size": 9},
                    error_y={"type": "data", "symmetric": False, "array": resumo["q3"] - resumo["mediana"],
                             "arrayminus": resumo["mediana"] - resumo["q1"], "thickness": 1.5, "width": 4},
                    hovertemplate=f"{NOMES_SERVIDOR[servidor]}, {NOMES_CARGA[carga]}<br>%{{x}}<br>"
                                  f"mediana: %{{y:,.4g}}<extra></extra>",
                ), row=i, col=j)
            figura.update_yaxes(type="log", row=i, col=j)
        figura.update_yaxes(title_text=f"{ROTULOS[metrica]} (log)", row=i, col=1)
    return _layout(figura, TITULOS["g4"], 330 * len(metricas) + 140)


# --------------------------------------------------------------------------- exportação


FIGURAS = ("g1", "g2", "g3", "g4")


def figuras(df: pd.DataFrame, comparacoes: pd.DataFrame) -> dict:
    """As quatro figuras, pelo nome."""
    return {"g1": g1(df), "g2": g2(df), "g3": g3(comparacoes), "g4": g4(df)}


def destaques(df: pd.DataFrame, comparacoes: pd.DataFrame) -> list:
    """Números de destaque da página: (rótulo, valor, detalhe)."""
    cv = df.groupby(CHAVES)["ops_s"].agg(lambda s: s.std() / s.mean())
    rel = relativos(df, "ops_s").groupby(df["repeticao"]).median()
    vazao = comparacoes[comparacoes["metrica"] == "ops_s"]
    maior = vazao.loc[vazao["razao_medianas"].idxmax()] if not vazao.empty else None
    memoria = comparacoes[comparacoes["metrica"] == "memoria_bytes"]
    itens = [
        ("Execuções", f"{len(df)}", f"{df['repeticao'].nunique()} blocos × {df.groupby(CHAVES).ngroups} combinações"),
        ("CV mediano da vazão", _pct(cv.median()), f"máximo {_pct(cv.max())}"),
        ("Deriva entre blocos", f"{_num(rel.min())}–{_num(rel.max())}", "mediana relativa da vazão por bloco"),
    ]
    if maior is not None:
        itens.append(("Maior razão de vazão", f"{_num(maior['razao_medianas'], 2)}×",
                      f"Valkey ÷ Redis, {_combinacao(maior['carga'], maior['io_threads'])}"))
    if not memoria.empty:
        itens.append(("Memória Valkey ÷ Redis", f"{_num(memoria['razao_medianas'].min(), 2)}–{_num(memoria['razao_medianas'].max(), 2)}×",
                      "nas 6 combinações"))
    return itens


def _num(valor, casas: int = 3) -> str:
    return f"{valor:.{casas}f}".replace(".", ",")


def _pct(valor, casas: int = 1) -> str:
    return _num(valor * 100, casas) + "%"


ESTILO = """
:root { --fundo: #f6f7fb; --cartao: #ffffff; --borda: #e3e6ef; --texto: #1f2430; --suave: #5b6378; --destaque: #2e86ab; }
body { margin: 0; background: var(--fundo); color: var(--texto); font-family: system-ui, -apple-system, "Segoe UI", sans-serif; }
header { max-width: 1400px; margin: 0 auto; padding: 24px 28px 4px; }
header h1 { margin: 0 0 4px; font-size: 26px; }
header p { margin: 2px 0; color: var(--suave); font-size: 14px; }
nav { margin-top: 10px; font-size: 14px; }
nav a { margin-right: 14px; color: var(--destaque); font-weight: 600; text-decoration: none; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(190px, 1fr)); gap: 10px; margin-top: 16px; }
.kpi { background: var(--cartao); border: 1px solid var(--borda); border-left: 4px solid var(--destaque); border-radius: 8px; padding: 10px 14px; }
.kpi span { display: block; font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: var(--suave); }
.kpi strong { display: block; font-size: 22px; margin: 2px 0; }
.kpi small { color: var(--suave); font-size: 12px; }
main { max-width: 1400px; margin: 0 auto; padding: 4px 28px 48px; }
section { background: var(--cartao); border: 1px solid var(--borda); border-radius: 12px; padding: 12px 18px 16px; margin: 18px 0; }
section p.leitura { font-size: 16px; line-height: 1.6; max-width: 70rem; margin: 6px 4px 0; }
section p.leitura b { color: var(--destaque); }
footer { max-width: 1400px; margin: 0 auto; padding: 0 28px 28px; color: var(--suave); font-size: 12px; }
@media (max-width: 700px) { header, main, footer { padding-left: 16px; padding-right: 16px; } }
"""


def pagina(df: pd.DataFrame, comparacoes: pd.DataFrame, titulo: str, origem: str) -> str:
    """HTML de uma página com os destaques, as quatro figuras e o texto de leitura de cada uma."""
    partes, primeira = [], True
    for nome, figura in figuras(df, comparacoes).items():
        grafico = figura.to_html(full_html=False, include_plotlyjs=primeira,  # embutido: abre sem internet
                                 config={"responsive": True, "displaylogo": False})
        primeira = False
        partes.append(f'<section id="{nome}">{grafico}<p class="leitura"><b>Como ler.</b> {escape(TEXTOS[nome])}</p></section>')
    kpis = "".join(f'<div class="kpi"><span>{escape(r)}</span><strong>{escape(v)}</strong><small>{escape(d)}</small></div>'
                   for r, v, d in destaques(df, comparacoes))
    links = "".join(f'<a href="#{n}">{escape(TITULOS[n].split(" — ")[0])}</a>' for n in FIGURAS)
    gerado = datetime.now().astimezone().strftime("%d/%m/%Y %H:%M")
    return (
        '<!DOCTYPE html>\n<html lang="pt-BR">\n<head>\n<meta charset="utf-8">\n'
        '<meta name="viewport" content="width=device-width, initial-scale=1">\n'
        f"<title>{escape(titulo)}</title>\n<style>{ESTILO}</style>\n</head>\n<body>\n"
        f"<header><h1>{escape(titulo)}</h1>"
        "<p>Benchmark local com Docker e memtier_benchmark 2.6.1: 2 servidores × io_threads 1 e 4 × cargas SET, GET e "
        "misto, 4 threads × 12 clientes, valores de 100 bytes, 100.000 chaves, medição de 30 s.</p>"
        f"<p>Dados: <code>{escape(origem)}</code></p><nav>{links}</nav><div class=\"kpis\">{kpis}</div></header>\n"
        f"<main>{''.join(partes)}</main>\n"
        f"<footer>Gerado por <code>python -m lab05 graficos</code> em {gerado}. "
        "Laboratório de Experimentação de Software — PUC Minas.</footer>\n</body>\n</html>\n"
    )


def exportar(df: pd.DataFrame, comparacoes: pd.DataFrame, pasta, titulo: str, origem: str) -> list:
    """Grava `g1.html` a `g4.html` e `apresentacao.html` em `pasta`; devolve os caminhos."""
    pasta = Path(pasta)
    pasta.mkdir(parents=True, exist_ok=True)
    caminhos = []
    for nome, figura in figuras(df, comparacoes).items():
        caminho = pasta / f"{nome}.html"
        figura.write_html(caminho, include_plotlyjs="cdn", config={"responsive": True, "displaylogo": False})
        caminhos.append(caminho)
    caminho = pasta / "apresentacao.html"
    caminho.write_text(pagina(df, comparacoes, titulo, origem), encoding="utf-8")
    caminhos.append(caminho)
    return caminhos
