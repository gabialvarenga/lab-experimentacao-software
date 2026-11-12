"""Montagem do dashboard em HTML (S01-11, S02-11).

`montar(saida)` grava uma página HTML estática única, com o Plotly.js embutido uma vez (a página
abre sem internet). Tema escuro; no topo, o título, os links e os sete indicadores (KPIs); depois, as
seções de 1 a 6 uma abaixo da outra, em tela cheia, para rolar a página durante a apresentação:

1. Cenário (pergunta, hipóteses e origem dos dados reais);
2. Os dados (G1);
3. Como os testes funcionam (G2, um por exemplo da S01-08);
4. Erro tipo I (G3) e 5. Poder (G4), lidos de `resultados.csv` (S02-11);
6. Dados reais: a tabela dos dois testes nos PRs coletados, com a conclusão (S02-10).

A seção 7 (Conclusão, S02-12) não aparece: `MOSTRAR_CONCLUSAO = True` a traz de volta, no fim da
página, e também na folha de interpretação. Cada seção tem uma legenda de uma linha. Os textos de
interpretação ficam fora da tela, numa folha que abre com a tecla `i` (ou o botão "Interpretação") e
fecha com `Esc`; `MOSTRAR_INTERPRETACAO = False` tira a folha e o botão. O nível de significância
(α = 5% ou 1%) troca o G3 e o G4, e o G2 alterna entre o exemplo sem efeito e o com efeito. Os gráficos
vêm de `graficos` pelo nome; se um ainda não existir ou falhar, a seção mostra um marcador com o motivo
e o resto da página é gerado (`_figura_ou_marcador`). O mesmo vale para o `resultados.csv` das seções 4 e 5.
"""

import html
from datetime import datetime
from pathlib import Path

import numpy as np
import pandas as pd

from lab04 import calibracao, config, gerador, graficos, testes
from lab04.descritiva import GRUPOS, horas_do_grupo
from lab04.resultados import classificar, lideres, vantagem_de_poder

TITULO = "Lab04: testes de hipótese por dentro (t de Welch × Mann-Whitney)"
INTEGRANTES = ("Brenda Evers", "Carlos José Gomes Batista Figueiredo", "Gabriela Alvarenga Cardoso")
LINK_KANBAN = "https://github.com/users/gabialvarenga/projects/9"
LINK_REPOSITORIO = "https://github.com/gabialvarenga/lab-experimentacao-software/tree/main/lab04"
LINK_DASHBOARD = "https://gabialvarenga.github.io/lab-experimentacao-software/"
LINK_CENARIO = LINK_REPOSITORIO + "/docs/cenario.md"
LINK_PROTOCOLO = LINK_REPOSITORIO + "/docs/protocolo-coleta.md"

SECOES = (
    ("cenario", "1. Cenário"),
    ("dados", "2. Os dados"),
    ("testes", "3. Como os testes funcionam"),
    ("erro-tipo-1", "4. Erro tipo I"),
    ("poder", "5. Poder"),
    ("dados-reais", "6. Dados reais"),
)
SECAO_CONCLUSAO = ("conclusao", "7. Conclusão")
MOSTRAR_CONCLUSAO = False   # True: acrescenta a seção 7 (esperado × encontrado, recomendação e limitação)
EM_CONSTRUCAO: dict = {}   # seções ainda sem conteúdo: {âncora: o que falta}; todas prontas desde a S02-12
MOSTRAR_INTERPRETACAO = True   # False: sem a folha "Interpretação" (tecla i) e sem o botão que a abre

ESTILO = """
html { background: #0b1020; }
body { margin: 0; font-family: system-ui, -apple-system, "Segoe UI", sans-serif; color: #e5e7eb; background: #0b1020; font-size: 16px; }
a { color: #9db4ff; }
header.topo { padding: 18px 28px 6px; max-width: 1560px; margin: 0 auto; box-sizing: border-box; }
.marca h1 { margin: 0 0 4px; font-size: 22px; line-height: 1.25; color: #fff; }
.marca p { margin: 0; font-size: 13px; color: #9ca3af; }
nav.links { margin-top: 8px; font-size: 13px; }
nav.links a { margin-right: 14px; font-weight: 600; text-decoration: none; border-bottom: 1px solid #4b5b8f; }
nav.links span.marcador { color: #6b7280; }
.acoes { margin-top: 8px; font-size: 12px; color: #6b7280; display: flex; align-items: center; gap: 12px; }
.acoes button, #interpretacao button { cursor: pointer; background: #1f2a4a; color: #dbe4ff; border: 1px solid #34426b; border-radius: 6px;
                                       padding: 5px 12px; font-size: 13px; }
.kpis { display: grid; grid-template-columns: repeat(auto-fit, minmax(170px, 1fr)); gap: 10px; margin-top: 14px; }
.kpi { background: #141a2e; border: 1px solid #232b45; border-left: 4px solid #3b82f6; border-radius: 8px; padding: 8px 12px;
       display: flex; flex-direction: column; gap: 2px; min-width: 0; }
.kpi.verde { border-left-color: #22c55e; } .kpi.ambar { border-left-color: #f59e0b; } .kpi.vermelho { border-left-color: #ef4444; }
.kpi span { font-size: 11px; text-transform: uppercase; letter-spacing: .05em; color: #9ca3af; }
.kpi strong { font-size: 21px; line-height: 1.25; color: #fff; }
.kpi small { font-size: 12px; color: #9ca3af; line-height: 1.3; }
.controle { display: inline-flex; align-items: center; gap: 6px; font-size: 13px; color: #9ca3af; }
.controle label { cursor: pointer; padding: 3px 12px; border: 1px solid #34426b; border-radius: 999px; color: #cbd5e1; background: #141a2e; }
.controle label:has(input:checked) { background: #3b82f6; color: #fff; border-color: #3b82f6; }
.controle input { position: absolute; opacity: 0; pointer-events: none; }
.controle label:has(input:focus-visible) { outline: 2px solid #93c5fd; outline-offset: 2px; }
[hidden] { display: none !important; }
main.coluna { max-width: 1560px; margin: 0 auto; padding: 8px 28px 64px; box-sizing: border-box; }
section { background: #141a2e; border: 1px solid #232b45; border-radius: 12px; padding: 14px 22px 16px; margin: 18px 0; }
section .cab { display: flex; justify-content: space-between; align-items: center; gap: 12px; min-height: 30px; }
section h2 { margin: 0; font-size: 21px; color: #9db4ff; letter-spacing: .01em; }
section h3 { margin: 0 0 6px; font-size: 15px; color: #9db4ff; }
section .corpo { position: relative; margin-top: 8px; }
#dados .corpo { height: 460px; } #testes .corpo { height: 500px; } #erro-tipo-1 .corpo { height: 480px; } #poder .corpo { height: 680px; }
section .corpo > div[data-painel] { height: 100%; }
section .corpo .plotly-graph-div, section .corpo div[data-painel] > div { height: 100% !important; }
p.legenda { margin: 8px 0 0; font-size: 13.5px; color: #8b95b0; line-height: 1.4; }
.pergunta { margin: 10px 0; font-size: 18px; line-height: 1.5; padding: 12px 16px; background: #1b2540; border-radius: 10px; }
.duas { display: grid; grid-template-columns: repeat(auto-fit, minmax(380px, 1fr)); gap: 16px; margin: 8px 0; }
.caixa { border: 1px solid #232b45; border-radius: 10px; padding: 10px 14px; background: #10162a; }
.caixa p { margin: 4px 0; font-size: 14px; line-height: 1.5; color: #cbd5e1; }
.fichas { display: flex; flex-wrap: wrap; gap: 8px; }
.fichas span { background: #1b2540; border-radius: 999px; padding: 4px 13px; font-size: 14px; color: #cbd5e1; }
table { border-collapse: collapse; width: 100%; font-size: 15px; margin: 6px 0; }
th, td { border: 1px solid #232b45; padding: 8px 12px; text-align: left; vertical-align: top; }
th { background: #1b2540; color: #cbd5e1; font-weight: 600; }
#dados-reais table { font-size: 16px; }
.faixa-conclusao { display: grid; grid-template-columns: 1.4fr 1fr 1fr; gap: 16px; align-items: start; margin-top: 8px; }
.selos { display: grid; grid-template-columns: repeat(2, 1fr); gap: 6px; }
.selo { display: flex; justify-content: space-between; align-items: center; gap: 8px; padding: 6px 10px; border: 1px solid #232b45;
        border-radius: 8px; font-size: 14px; background: #10162a; min-width: 0; }
.selo b { font-size: 11px; padding: 2px 9px; border-radius: 999px; color: #fff; white-space: nowrap; }
.selo.sim b { background: #15803d; } .selo.parte b { background: #b45309; } .selo.nao b { background: #b91c1c; }
div.marcador { border: 2px dashed #34426b; color: #8b95b0; padding: 1.2rem; text-align: center; border-radius: 8px; font-size: 14px; }
#interpretacao { position: fixed; inset: 0; z-index: 50; overflow: auto; background: rgba(5, 8, 18, .97); padding: 28px 10vw 60px; color: #e5e7eb; }
#interpretacao h2 { font-size: 22px; color: #fff; } #interpretacao h3 { font-size: 17px; color: #9db4ff; margin-top: 26px; }
#interpretacao p.texto, #interpretacao ul.texto { line-height: 1.6; max-width: 70rem; font-size: 15px; }
#interpretacao .cabecalho { display: flex; justify-content: space-between; align-items: center; }
#interpretacao table { font-size: 14px; } #interpretacao p.legenda { font-size: 13px; }
@media (max-width: 900px) { .faixa-conclusao { grid-template-columns: 1fr; } }
"""

SCRIPT = """
function mostrar(grupo, valor) {
  document.querySelectorAll('[data-painel="' + grupo + '"]').forEach(function (p) { p.hidden = p.dataset.valor !== valor; });
  document.querySelectorAll('[data-painel="' + grupo + '"]:not([hidden]) .plotly-graph-div').forEach(function (g) {
    if (window.Plotly) { Plotly.Plots.resize(g); }
  });
}
document.querySelectorAll('input[data-grupo]').forEach(function (r) {
  r.addEventListener('change', function () {
    document.querySelectorAll('input[data-grupo="' + r.dataset.grupo + '"]').forEach(function (o) { o.checked = o.value === r.value; });
    mostrar(r.dataset.grupo, r.value);
  });
});
function redimensionar() {   // os gráficos são desenhados antes de o resto da página existir: ajusta ao tamanho final
  document.querySelectorAll('.plotly-graph-div').forEach(function (g) {
    if (window.Plotly && g.offsetParent !== null) { Plotly.Plots.resize(g); }
  });
}
window.addEventListener('load', function () { redimensionar(); setTimeout(redimensionar, 300); });
var folha = document.getElementById('interpretacao');
function interpretacao(abrir) { if (folha) { folha.hidden = !abrir; } }
var abrir = document.getElementById('abrir-interpretacao');
if (abrir) { abrir.addEventListener('click', function () { interpretacao(true); }); }
var fechar = document.getElementById('fechar-interpretacao');
if (fechar) { fechar.addEventListener('click', function () { interpretacao(false); }); }
document.addEventListener('keydown', function (e) {
  if (e.key === 'Escape') { interpretacao(false); }
  else if ((e.key === 'i' || e.key === 'I') && folha && !e.ctrlKey && !e.metaKey && !e.altKey) { interpretacao(folha.hidden); }
});
"""


def _e(texto) -> str:
    return html.escape(str(texto))


def _data(valor) -> str:
    """Data do config (`date` ou texto ISO) no formato dd/mm/aaaa."""
    return pd.Timestamp(valor).strftime("%d/%m/%Y")


def _marcador(texto: str) -> str:
    return f'<div class="marcador">{_e(texto)}</div>'


def _compacto(figura, nome: str) -> None:
    """Ajusta a figura ao painel de parede: fundo escuro e transparente, sem título, margens curtas e fonte pequena."""
    figura.update_layout(
        template="plotly_dark", paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)", title=None,
        height=None, width=None, autosize=True, font={"size": 13, "color": "#e5e7eb"},
        margin={"l": 50, "r": 16, "t": 40, "b": 30},
    )
    figura.update_annotations(font_size=13)
    figura.update_xaxes(title_font={"size": 12}, title_standoff=6, automargin=True)   # a margem cresce até caber rótulo e título
    figura.update_yaxes(title_font={"size": 12}, title_standoff=6, automargin=True)
    if nome == "g1":   # títulos curtos: a contagem de PRs já está no painel 1
        figura.for_each_annotation(lambda a: a.update(text=a.text.split(" (")[0]))
    elif nome == "g2":   # a legenda do painel já diz o que cada elemento é
        figura.update_layout(showlegend=False)
        figura.update_annotations(selector={"bgcolor": "rgba(255,255,255,0.8)"}, bgcolor="rgba(20,26,46,0.9)")
    elif nome == "g3":
        figura.update_layout(legend={"orientation": "h", "x": 0.5, "xanchor": "center", "y": 1.0, "yanchor": "bottom"})
    elif nome == "g4":   # a unidade do efeito vai no título da faceta, um só título no eixo y e a legenda na faceta vazia
        figura.update_xaxes(title_text="")
        figura.update_yaxes(title_text="")
        figura.for_each_annotation(lambda a: a.update(text=a.text + (" · δ em dp" if a.text.startswith("C0") else " · razão de medianas (×)")))
        figura.add_annotation(text="Rejeições de H₀ (%)", textangle=-90, xref="paper", yref="paper", x=-0.05, y=0.5,
                              showarrow=False, font_size=12)
        figura.update_layout(legend={"orientation": "v", "x": 0.72, "xanchor": "left", "y": 0.2, "yanchor": "top"})


class _Figuras:
    """Converte figuras em HTML, embutindo o Plotly.js só na primeira."""

    def __init__(self):
        self.plotly_embutido = False

    def html(self, figura, nome: str | None = None) -> str:
        if nome:
            _compacto(figura, nome)
        trecho = figura.to_html(
            full_html=False, include_plotlyjs=not self.plotly_embutido, config={"responsive": True, "displayModeBar": False}
        )
        self.plotly_embutido = True
        return trecho


def _figura_ou_marcador(figuras: _Figuras, nome: str, *args) -> str:
    """HTML do gráfico `graficos.<nome>(*args)`, ou um marcador se ele não existe ou falha."""
    funcao = getattr(graficos, nome, None)
    if funcao is None:
        return _marcador(f"Gráfico indisponível: {nome} ainda não foi implementado.")
    try:
        return figuras.html(funcao(*args), nome)
    except Exception as erro:  # o dashboard sai mesmo com um gráfico quebrado
        return _marcador(f"Gráfico indisponível: {nome} falhou ({type(erro).__name__}: {erro}).")


def _texto(nome: str) -> str:
    texto = getattr(graficos, nome, None)
    return f'<p class="texto">{_e(texto)}</p>' if texto else ""


def _legenda(texto: str) -> str:
    return f'<p class="legenda">{_e(texto)}</p>'



def _controle(grupo: str, opcoes, marcado: str, rotulo: str, sufixo: str = "") -> str:
    """Seletor de botões de rádio; troca os painéis `_paineis(grupo, ...)` pelo JavaScript da página.

    `sufixo` dá um `name` próprio a cada seletor do mesmo `grupo`, que o JavaScript mantém sincronizados.
    """
    nome = f"{grupo}-{sufixo}" if sufixo else grupo
    botoes = "".join(
        f'<label><input type="radio" name="{nome}" data-grupo="{grupo}" value="{valor}"'
        f'{" checked" if valor == marcado else ""}>{_e(texto)}</label>'
        for valor, texto in opcoes
    )
    return f'<div class="controle"><span>{_e(rotulo)}</span>{botoes}</div>'


def _paineis(grupo: str, itens, marcado: str) -> str:
    """Um painel por opção do seletor `grupo`; só o `marcado` começa visível."""
    return "".join(
        f'<div data-painel="{grupo}" data-valor="{valor}"{"" if valor == marcado else " hidden"}>{corpo}</div>'
        for valor, corpo in itens
    )


ALFAS = (("5", "α = 5%", 0.05), ("1", "α = 1%", 0.01))


def _topo(indicadores: str) -> str:
    gerado = datetime.now().strftime("%d/%m/%Y %H:%M")
    botao = '<button type="button" id="abrir-interpretacao">Interpretação (i)</button>' if MOSTRAR_INTERPRETACAO else ""
    return f"""<header class="topo">
<div class="marca"><h1>{_e(TITULO)}</h1>
<p>{_e(" · ".join(INTEGRANTES))}</p>
<nav class="links">
<a href="{LINK_KANBAN}">Kanban (GitHub Projects)</a>
<a href="{LINK_REPOSITORIO}">Repositório</a>
<a href="{LINK_DASHBOARD}">Dashboard publicado</a> <span class="marcador">(publicação na S02-13)</span>
</nav>
<div class="acoes">{botao}<span>Gerado em {gerado}</span></div></div>
{indicadores or "<div></div>"}
</header>""" 


def _kpi(rotulo: str, valor: str, sub: str, tom: str = "") -> str:
    return f'<div class="kpi {tom}"><span>{_e(rotulo)}</span><strong>{_e(valor)}</strong><small>{_e(sub)}</small></div>'


def _faixa(valores) -> str:
    """`4,35%–4,96%` a partir de taxas (proporções)."""
    return f"{graficos._num(min(valores) * 100, 2)}%–{graficos._num(max(valores) * 100, 2)}%"


def _indicadores(reais: pd.DataFrame, resultados) -> str:
    """Faixa de KPIs: dados coletados, testes nos dados reais e resumo da simulação (α = 5%)."""
    if reais.empty:
        return ""
    cartoes = []
    try:
        n = reais["grupo"].value_counts()
        com, sem = horas_do_grupo(reais, "com_bot"), horas_do_grupo(reais, "sem_bot")
        if not len(com) or not len(sem):
            raise ValueError("falta um dos grupos")
        cartoes.append(_kpi("PRs coletados", str(len(reais)), f"{n.get('com_bot', 0)} com bot · {n.get('sem_bot', 0)} sem bot"))
        cartoes.append(_kpi("Mediana até o merge", f"{graficos._num(np.median(com), 1)} h · {graficos._num(np.median(sem), 1)} h",
                            "com bot · sem bot"))
        t = testes.tabela_dados_reais(reais).set_index("teste")
        nenhum = not t["rejeita_h0"].any()
        cartoes.append(_kpi("p-valor nos dados reais",
                            f"{graficos._p_rotulo(t.loc['welch', 'p_valor'])} · {graficos._p_rotulo(t.loc['mann_whitney', 'p_valor'])}",
                            "Welch · Mann-Whitney: " + ("nenhum rejeita H₀" if nenhum else "há rejeição de H₀ (α = 0,05)"),
                            "verde" if nenhum else "ambar"))
        cartoes.append(_kpi("Tamanho de efeito",
                            f"g {graficos._num(t.loc['welch', 'tamanho_efeito'], 2)} · δ {graficos._num(t.loc['mann_whitney', 'tamanho_efeito'], 2)}",
                            f"{t.loc['welch', 'magnitude']} · {t.loc['mann_whitney', 'magnitude']}"))
    except Exception:  # sem os dados reais, a faixa mostra só o que conseguir
        pass
    if resultados is not None:
        try:
            c = classificar(resultados)
            c5 = c[np.isclose(c["alfa"], 0.05)]
            mw, welch = c5[c5["teste"] == "mann_whitney"]["taxa"], c5[c5["teste"] == "welch"]["taxa"]
            cartoes.append(_kpi("Erro tipo I · Mann-Whitney", _faixa(mw), "α = 5%: perto do nominal em todos os cenários", "verde"))
            cartoes.append(_kpi("Erro tipo I · Welch", _faixa(welch), "α = 5%: bem abaixo do nominal fora de C0", "ambar"))
            l5 = lideres(vantagem_de_poder(resultados))
            l5 = l5[np.isclose(l5["alfa"], 0.05)]
            do_welch = ", ".join(l5[l5["lider"] == "welch"]["cenario"])
            cartoes.append(_kpi("Maior poder", f"Mann-Whitney {int((l5['lider'] == 'mann_whitney').sum())}/{len(l5)}",
                                f"cenários em que lidera · Welch: {do_welch}" if do_welch else "cenários em que lidera · Welch: nenhum"))
        except Exception:
            pass
    return f'<div class="kpis">{"".join(cartoes)}</div>' if cartoes else ""


def _cenario_detalhado(cfg: dict, reais: pd.DataFrame) -> str:
    c = cfg["coleta"]
    repositorio, revisor, limite = c["repositorio"], c["revisor"], c["limite_revisao_horas"]
    contagem = reais["grupo"].value_counts()
    n = {g: int(contagem.get(g, 0)) for g in GRUPOS}
    return f"""<p class="texto"><strong>Pergunta.</strong> O tempo até o merge de um PR do
<code>{_e(repositorio)}</code> muda quando ele recebe, em até {_e(limite)} h após a abertura, a revisão automática
do Copilot?</p>
<p class="texto">Em palavras simples: H₀ diz que a revisão do Copilot não faz diferença no tempo até o merge;
H₁ diz que faz diferença, para mais ou para menos. Os dois testes comparam coisas diferentes, e por isso cada um
tem a sua formulação (X é o tempo até o merge, em horas):</p>
<table>
<tr><th></th><th>t de Welch</th><th>Mann-Whitney</th></tr>
<tr><th>O que compara</th><td>As médias dos dois grupos</td>
<td>Os postos: com que frequência um PR com bot demora mais que um PR sem bot</td></tr>
<tr><th>H₀</th><td>μ<sub>com</sub> = μ<sub>sem</sub></td>
<td>P(X<sub>com</sub> &gt; X<sub>sem</sub>) + ½·P(X<sub>com</sub> = X<sub>sem</sub>) = ½</td></tr>
<tr><th>H₁</th><td>μ<sub>com</sub> ≠ μ<sub>sem</sub></td>
<td>P(X<sub>com</sub> &gt; X<sub>sem</sub>) + ½·P(X<sub>com</sub> = X<sub>sem</sub>) ≠ ½</td></tr>
</table>
<p class="texto">Os testes são bicaudais, com α = 0,05: não há direção prevista, porque a revisão automática
pode acelerar o merge (feedback imediato) ou atrasá-lo (comentários a resolver).</p>
<p class="texto"><strong>Dados reais.</strong> PRs mesclados no <code>{_e(repositorio)}</code> entre
{_data(c["janela"]["inicio"])} e {_data(c["janela"]["fim"])} (UTC), de autores humanos e com mais de
{_e(c["min_horas_ate_merge"])} h até o merge. O grupo <strong>com bot</strong> ({n["com_bot"]} PRs) recebeu a
primeira revisão do <code>{_e(revisor)}</code> em até {_e(limite)} h após a abertura; o grupo
<strong>sem bot</strong> ({n["sem_bot"]} PRs) não recebeu revisão dele. Foram sorteados {_e(c["por_mes"])} PRs
por mês e por grupo, com semente fixa ({_e(cfg["semente"])}). Os dados calibram a simulação e são testados na
seção 6.</p>
<p class="legenda">Detalhes: <a href="{LINK_CENARIO}">cenário e expectativa</a> ·
<a href="{LINK_PROTOCOLO}">protocolo de coleta</a>.</p>"""


def _secao_cenario(cfg: dict, reais: pd.DataFrame) -> str:
    c = cfg["coleta"]
    contagem = reais["grupo"].value_counts()
    n = {g: int(contagem.get(g, 0)) for g in GRUPOS}
    return f"""<div class="cab"><h2>1. Cenário</h2></div>
<p class="pergunta"><strong>Pergunta.</strong> O tempo até o merge de um PR do <code>{_e(c["repositorio"])}</code>
muda quando ele recebe, em até {_e(c["limite_revisao_horas"])} h após a abertura, a revisão automática do Copilot?</p>
<div class="caixa"><h3>Hipóteses (bicaudal, α = 0,05)</h3>
<table>
<tr><th></th><th>t de Welch</th><th>Mann-Whitney</th></tr>
<tr><th>H₀</th><td>μ<sub>com</sub> = μ<sub>sem</sub></td><td>P(X<sub>com</sub> &gt; X<sub>sem</sub>) = ½</td></tr>
<tr><th>H₁</th><td>μ<sub>com</sub> ≠ μ<sub>sem</sub></td><td>P(X<sub>com</sub> &gt; X<sub>sem</sub>) ≠ ½</td></tr>
</table></div>
<div class="caixa" style="margin-top:8px"><h3>Dados reais</h3>
<div class="fichas"><span>{_e(c["repositorio"])}</span>
<span>{_data(c["janela"]["inicio"])} a {_data(c["janela"]["fim"])}</span>
<span>com bot: {n["com_bot"]} PRs</span><span>sem bot: {n["sem_bot"]} PRs</span>
<span>{_e(c["por_mes"])} por mês e por grupo</span><span>semente {_e(cfg["semente"])}</span></div></div>
<p class="legenda">X é o tempo até o merge, em horas. Detalhes: <a href="{LINK_CENARIO}">cenário</a> ·
<a href="{LINK_PROTOCOLO}">protocolo de coleta</a>.</p>"""


def _secao_dados(figuras: _Figuras, reais: pd.DataFrame, exemplos: dict) -> str:
    exemplo = exemplos["com_efeito"]
    return (
        '<div class="cab"><h2>2. Os dados</h2></div><div class="corpo">'
        + _figura_ou_marcador(figuras, "g1", reais, (exemplo["a"], exemplo["b"]))
        + "</div>"
        + _legenda("G1: horas até o merge em escala log; dados reais à esquerda, simulados (lognormal calibrada, "
                   f"δ = {graficos._num(exemplo['delta'], 2)}, n = {exemplo['n']} por grupo) à direita.")
    )


def _secao_testes(figuras: _Figuras, exemplos: dict) -> str:
    itens, legendas = [], []
    for valor, caso, descricao in (("sem", "sem_efeito", "H₀ verdadeira"), ("com", "com_efeito", "H₀ falsa")):
        exemplo = exemplos[caso]
        itens.append((valor, _figura_ou_marcador(figuras, "g2", exemplo)))
        legendas.append((valor, _legenda(
            f"G2, exemplo {caso.replace('_', ' ')} ({descricao}): δ = {graficos._num(exemplo['delta'], 2)}, "
            f"n = {exemplo['n']} por grupo, semente {exemplo['semente']}. Cinza: simulação sob H₀; vermelho: região de "
            "rejeição; hachurado: p-valor; linha: estatística do exemplo.")))
    seletor = _controle("g2", (("sem", "Sem efeito (H₀ verdadeira)"), ("com", "Com efeito (H₀ falsa)")), "sem", "Exemplo")
    return (
        f'<div class="cab"><h2>3. Como os testes funcionam</h2>{seletor}</div><div class="corpo">'
        + _paineis("g2", itens, "sem") + "</div>" + _paineis("g2", legendas, "sem")
    )


LEGENDA_G3 = "G3: taxa de rejeição com H₀ verdadeira; linha vermelha = α; barras de erro = intervalo de Wilson de 95%."
LEGENDA_G4 = "G4: proporção de rejeições por tamanho de efeito; em δ = 0 é o erro tipo I; linha vermelha = α."
NOMES_CURTOS_CENARIOS = {"C0": "C0 normal", "C1": "C1 lognormal", "C2": "C2 assimetria", "C3": "C3 outliers", "C4": "C4 n = 10"}
TITULOS_SIMULACAO = {"g3": ("erro-tipo-1", "4. Erro tipo I"), "g4": ("poder", "5. Poder")}


def _ler_resultados(cfg: dict):
    """(`resultados.csv`, None), ou (None, marcador) se o CSV falta ou não abre."""
    caminho = cfg["simulacao"]["saida"]
    try:
        return pd.read_csv(Path(cfg["pasta"]) / caminho), None
    except Exception as erro:  # o dashboard sai mesmo sem os resultados da simulação
        return None, _marcador(f"Gráfico indisponível: não foi possível ler {caminho} ({type(erro).__name__}: {erro}).")


def _tamanhos(resultados: pd.DataFrame) -> str:
    """`n = 30 por grupo (10 em C4)`: o n mais comum entre os cenários e as exceções; vazio sem as colunas."""
    if not {"cenario", "n"} <= set(resultados.columns):
        return ""
    cenarios_por_n = resultados.drop_duplicates("cenario").groupby("n", sort=False)["cenario"].apply(list)
    comum, *outros = sorted(cenarios_por_n.items(), key=lambda par: -len(par[1]))
    excecoes = "; ".join(f"{n} em {', '.join(cenarios)}" for n, cenarios in outros)
    return f"n = {comum[0]} por grupo" + (f" ({excecoes})" if excecoes else "")


def _secao_simulacao(figuras: _Figuras, resultados, marcador, grafico: str, legenda: str) -> str:
    """Seções 4 e 5: o gráfico `grafico` em α = 5% e em α = 1% (o seletor da seção troca) e a legenda."""
    titulo = TITULOS_SIMULACAO[grafico][1]
    if resultados is None:
        return f'<div class="cab"><h2>{titulo}</h2></div><div class="corpo">{marcador}</div>'
    tamanhos = _tamanhos(resultados)
    itens = [(valor, _figura_ou_marcador(figuras, grafico, resultados, alfa, NOMES_CURTOS_CENARIOS)) for valor, _, alfa in ALFAS]
    seletor = _controle("alfa", [(v, t) for v, t, _ in ALFAS], "5", "Nível de significância", sufixo=grafico)
    return (
        f'<div class="cab"><h2>{titulo}</h2>{seletor}</div><div class="corpo">' + _paineis("alfa", itens, "5") + "</div>"
        + _legenda((tamanhos + ". " if tamanhos else "") + legenda)
    )


NOMES_TESTE_TABELA = {"welch": "t de Welch", "mann_whitney": "Mann-Whitney"}
O_QUE_COMPARA = {"welch": "as médias", "mann_whitney": "os postos"}
NOMES_MEDIDA = {"hedges_g": "g de Hedges", "cliff_delta": "δ de Cliff"}
LIMITACOES = (
    "Limitações: só PRs mesclados entram na amostra (viés de seleção), o tamanho do PR e a atribuição da "
    "revisão do Copilot não são controlados, e os dados vêm de um único repositório e de uma janela curta."
)


def _estatistica(linha) -> str:
    """`t = −1,115 (gl = 29,35)` no Welch e `U = 414` no Mann-Whitney."""
    valor = float(linha["estatistica"])
    if linha["teste"] == "welch":
        return f"{linha['estatistica_nome']} = {graficos._num(valor)} (gl = {graficos._num(linha['graus_de_liberdade'], 2)})"
    return f"{linha['estatistica_nome']} = {graficos._num(valor, 0 if valor.is_integer() else 1)}"


def tabela_dados_reais_html(tabela: pd.DataFrame, alfa: float = testes.ALFA) -> str:
    """Tabela HTML da seção 6: uma coluna por teste e uma linha por medida, com os números de `testes.tabela_dados_reais`."""
    linhas = [r for _, r in tabela.iterrows()]
    medidas = (
        ("Compara", lambda r: _e(O_QUE_COMPARA[r["teste"]])),
        ("Estatística", lambda r: _e(_estatistica(r))),
        ("p-valor", lambda r: _e(graficos._p_rotulo(r["p_valor"]))),
        ("Tamanho de efeito", lambda r: f"{_e(NOMES_MEDIDA[r['medida_efeito']])} = {_e(graficos._num(r['tamanho_efeito'], 2))} ({_e(r['magnitude'])})"),
        ("Razão de medianas (com bot ÷ sem bot)", lambda r: _e(graficos._num(r["razao_medianas"], 2))),
        (f"Conclusão (α = {graficos._num(alfa, 2)})", lambda r: f"<strong>{_e(r['conclusao'])}</strong>"),
    )
    cabecalho = "".join(f"<th>{_e(NOMES_TESTE_TABELA[r['teste']])}</th>" for r in linhas)
    corpo = "\n".join(
        f"<tr><th>{_e(nome)}</th>" + "".join(f"<td>{formato(r)}</td>" for r in linhas) + "</tr>" for nome, formato in medidas
    )
    return f"<table>\n<tr><th>Medida</th>{cabecalho}</tr>\n{corpo}\n</table>"


def _sentido(tabela: pd.DataFrame) -> str:
    """Para os testes que rejeitam H₀, de que lado está o efeito (vazio se nenhum rejeita)."""
    por_teste = tabela.set_index("teste")
    frases = []
    if por_teste.loc["welch", "rejeita_h0"]:
        menor = por_teste.loc["welch", "tamanho_efeito"] < 0
        frases.append(f"o Welch aponta média {'menor' if menor else 'maior'} no grupo com bot")
    if por_teste.loc["mann_whitney", "rejeita_h0"]:
        menor = por_teste.loc["mann_whitney", "tamanho_efeito"] < 0
        frases.append(f"o Mann-Whitney aponta que os PRs com bot tendem a demorar {'menos' if menor else 'mais'}")
    return (" Nos testes que rejeitam, " + " e ".join(frases) + ".") if frases else ""


def texto_dados_reais(tabela: pd.DataFrame, reais: pd.DataFrame, alfa: float = testes.ALFA) -> list:
    """Os parágrafos da seção 6: concordância dos testes, efeito e importância prática, cautela e limitações.

    O texto sai dos números da `tabela` e das horas de `reais`; se os dois testes discordam, o texto
    diz e explica a divergência. Devolve uma lista de parágrafos (texto puro).
    """
    por_teste = tabela.set_index("teste")
    w, m = por_teste.loc["welch"], por_teste.loc["mann_whitney"]
    com, sem = horas_do_grupo(reais, "com_bot"), horas_do_grupo(reais, "sem_bot")
    nivel = graficos._num(alfa, 2)
    p_w, p_m = graficos._p_rotulo(w["p_valor"]), graficos._p_rotulo(m["p_valor"])
    if "indefinida" in (w["conclusao"], m["conclusao"]):
        decisao = (
            f"Um dos testes não pôde ser calculado (p-valor do Welch: {p_w}; do Mann-Whitney: {p_m}), "
            "por falta de variação nos dados."
        )
    elif w["rejeita_h0"] == m["rejeita_h0"]:
        quais = "os dois testes rejeitam H₀" if w["rejeita_h0"] else "nenhum dos dois testes rejeita H₀"
        decisao = (
            f"Com α = {nivel}, {quais} (Welch: p = {p_w}; Mann-Whitney: p = {p_m}): os dois chegam à mesma "
            "conclusão." + _sentido(tabela)
        )
    else:
        decisao = (
            f"Os dois testes discordam com α = {nivel}: o Welch {w['conclusao']} (p = {p_w}) e o Mann-Whitney "
            f"{m['conclusao']} (p = {p_m}). Eles respondem a perguntas diferentes: o Welch compara médias, que os "
            "PRs mais longos puxam, e o Mann-Whitney compara postos, que não dependem do tamanho dos valores "
            "extremos; a divergência faz parte do resultado." + _sentido(tabela)
        )

    med_com, med_sem = float(np.median(com)), float(np.median(sem))
    razao = float(w["razao_medianas"])
    diferenca = med_com - med_sem
    pct = abs(razao - 1) * 100
    lado = "maior" if diferenca >= 0 else "menor"
    limite = graficos._num(testes.DIFERENCA_RELEVANTE * 100, 0)
    efeito = (
        f"Tamanho de efeito: {NOMES_MEDIDA['hedges_g']} = {graficos._num(w['tamanho_efeito'], 2)} ({w['magnitude']}) e "
        f"{NOMES_MEDIDA['cliff_delta']} = {graficos._num(m['tamanho_efeito'], 2)} ({m['magnitude']}). A mediana do grupo "
        f"com bot ({graficos._num(med_com, 1)} h) é {graficos._num(abs(diferenca), 1)} h {lado} que a do grupo sem bot "
        f"({graficos._num(med_sem, 1)} h), uma diferença de {graficos._num(pct, 0)}% (razão {graficos._num(razao, 2)})."
    )
    relevante = pct >= testes.DIFERENCA_RELEVANTE * 100 or bool({w["magnitude"], m["magnitude"]} & {"médio", "grande"})
    if relevante:
        efeito += f" Isso pode ter importância prática: a diferença chega a {limite}% ou o tamanho de efeito é médio ou grande."
    else:
        efeito += f" Isso não tem importância prática evidente: a diferença das medianas fica abaixo dos {limite}% que o grupo trata como relevantes."
    sinais = {s for s in np.sign([w["tamanho_efeito"], m["tamanho_efeito"], razao - 1]) if s != 0}
    if len(sinais) > 1:
        efeito += (
            " Os sinais das medidas não coincidem (a média, os postos e a razão de medianas apontam lados "
            "diferentes), o que é esperado quando o efeito está perto de zero."
        )

    tamanhos = str(len(com)) if len(com) == len(sem) else f"{len(com)} e {len(sem)}"
    if w["rejeita_h0"] or m["rejeita_h0"]:
        cautela = (
            "Rejeitar H₀ diz que a diferença seria improvável se H₀ fosse verdadeira, não que ela seja grande: "
            "o que importa na prática é o tamanho de efeito."
        )
    else:
        cautela = (
            f"Não rejeitar H₀ não prova que não há efeito: com {tamanhos} PRs por grupo os testes têm pouco "
            "poder para efeitos pequenos (G4), e o resultado mostra só que esta amostra não basta para "
            "distinguir uma diferença."
        )
    return [decisao, efeito, cautela, LIMITACOES]


def _secao_dados_reais(tabela, erro, reais: pd.DataFrame) -> str:
    titulo = '<div class="cab"><h2>6. Dados reais</h2></div>'
    if tabela is None:
        return titulo + _marcador(f"Tabela indisponível: os testes nos dados reais falharam ({type(erro).__name__}: {erro}).")
    n = reais["grupo"].value_counts()
    return (
        titulo + '<div class="corpo">' + tabela_dados_reais_html(tabela) + "</div>"
        + _legenda(f"{n.get('com_bot', 0)} PRs com bot e {n.get('sem_bot', 0)} sem bot; testes bicaudais; "
                   "g de Hedges (médias) e δ de Cliff (postos) como tamanhos de efeito.")
    )


# --- seção 7: expectativa × resultado, recomendação e limitação principal (S02-12) ---

LINK_COMMIT = "https://github.com/gabialvarenga/lab-experimentacao-software/commit/"
COMMITS = {   # chave: (hash completo, data, o que o commit fixa)
    "expectativa": ("f998a188efa50b48efcd33fbf56449be585092f2", "03/11/2026",
                    "a expectativa escrita em docs/cenario.md (#227, PR #252)"),
    "primeira_simulacao": ("101eb5485e8301e6c849b9531a6d39a06317a72f", "04/11/2026",
                           "o primeiro commit que roda os dois testes em dados simulados (#232)"),
    "config_congelado": ("dc4f47857519a3fd1e64f0122f7abcc55d58d6d0", "11/11/2026",
                         "o config.yaml congelado, antes das simulações finais (#236, PR #261)"),
}

# Cada linha: (situação, citações literais da seção 5 do cenario.md, o que a simulação ou os dados mostraram,
# se confirmou). As citações não são reescritas; um teste confere que estão no cenario.md, e outro confere
# os números do resultado contra classificacao.csv, poder.csv e a tabela da seção 6.
EXPECTATIVA_X_RESULTADO = (
    ("C0: controle (normal)",
     ("Os dois perto de 5%", "Empate técnico, com leve vantagem do Welch"),
     "Welch com 4,63% (ok) e Mann-Whitney com 4,43% (conservador, −0,57 p.p.); o Welch fica à frente em poder "
     "por no máximo 3,0 p.p.",
     "Sim"),
    ("C1: referência (lognormal calibrada)",
     ("Os dois perto de 5%; o Welch possivelmente um pouco abaixo", "Mann-Whitney maior que Welch"),
     "Welch com 2,47% (conservador, −2,53 p.p.) e Mann-Whitney com 4,67% (ok); o Mann-Whitney fica à frente "
     "em todos os efeitos, por até 41,0 p.p.",
     "Em parte: o Welch ficou bem abaixo de 5%, não só um pouco"),
    ("C2: assimetria forte",
     ("Mann-Whitney perto de 5%; Welch se afasta de 5%, provavelmente para baixo", "Mann-Whitney bem maior que Welch"),
     "Welch com 1,98% (conservador) e Mann-Whitney com 4,86% (ok); vantagem do Mann-Whitney de até 53,1 p.p.",
     "Sim"),
    ("C3: outliers",
     ("Mann-Whitney perto de 5%; Welch abaixo de 5%", "Mann-Whitney maior; o poder do Welch cai muito"),
     "Welch com 1,61% (conservador) e Mann-Whitney com 4,96% (ok); o poder do Welch não passa de 41,5%, e a "
     "vantagem do Mann-Whitney chega a 59,9 p.p.",
     "Sim"),
    ("C4: amostra pequena (n = 10)",
     ("Mann-Whitney em torno de 5%, talvez um pouco abaixo; Welch pode se afastar de 5%",
      "Poder baixo nos dois, com Mann-Whitney igual ou melhor"),
     "Welch com 1,54% e Mann-Whitney com 4,35% (os dois conservadores); no maior efeito, o Mann-Whitney "
     "rejeita em 67,7% dos conjuntos e o Welch em 22,1%",
     "Sim; o Mann-Whitney ficou bem acima do Welch, não só igual"),
    ("Onde a vantagem muda de lado",
     ("o Welch só seja melhor ou igual em C0 (dados normais)",
      "com a diferença crescendo com a assimetria e com os outliers"),
     "O Welch lidera só em C0, e o Mann-Whitney em C1 a C4; a vantagem máxima cresce de 41,0 p.p. (C1) para "
     "53,1 p.p. (C2) e 59,9 p.p. (C3)",
     "Sim"),
    ("α = 0,01",
     ("o poder dos dois testes caia, sem inverter a ordem entre eles",),
     "O poder cai em todos os pontos, o líder de cada cenário é o mesmo e a classificação do erro tipo I não "
     "muda; em C1 a C4 o Welch rejeita de 0,04% a 0,17% com H₀ verdadeira",
     "Sim"),
    ("Dados reais",
     ("os dois testes rejeitem H₀ com folga nos dados reais", "que o tamanho de efeito seja relevante na prática"),
     "Nenhum dos dois rejeita H₀ (Welch: p = 0,274; Mann-Whitney: p = 0,600); as medianas são de 17,8 h com bot "
     "e 17,2 h sem bot (diferença de 4%), com g de Hedges = −0,28 e δ de Cliff = −0,08",
     "Não"),
)

TEXTO_DIFERENCA_DADOS_REAIS = (
    "A expectativa sobre os dados reais não se confirmou. Ela partia da sondagem do protocolo de coleta "
    "(03/11/2026), em que a mediana até o merge era de 21,3 h nos PRs com revisão do Copilot em até 1 h e de "
    "4,5 h nos 100 PRs mais recentes sem revisão. A amostra final é outra: só PRs com mais de 1 h até o merge, "
    "30 por grupo, sorteados por mês entre agosto e outubro. A explicação provável é que o filtro de 1 h tirou "
    "os PRs mais rápidos, que puxavam para baixo a mediana do grupo sem bot; quantos PRs o filtro tirou de "
    "cada grupo não foi medido. Com 30 PRs por grupo e um efeito pequeno, os testes têm pouco poder (seção 5), "
    "então o resultado não mostra que a revisão do Copilot não faz diferença, só que esta amostra não a distingue."
)

TEXTO_RECOMENDACAO = (
    "No cenário real (tempo até o merge com cauda longa e 30 PRs por grupo, o que o C1 reproduz), o grupo "
    "recomenda o Mann-Whitney: o erro tipo I dele ficou em 4,67%, perto dos 5% nominais, enquanto o Welch "
    "rejeitou só 2,47%, e o poder dele foi maior em todos os efeitos, por até 41 pontos percentuais. A escolha "
    "muda nestas condições:"
)
CONDICOES_RECOMENDACAO = (
    "Dados aproximadamente normais (C0): os dois testes servem; o Welch tem uma vantagem pequena de poder "
    "(até 3,0 p.p.) e responde diretamente sobre a diferença de médias.",
    "Pergunta sobre médias, por exemplo o total de horas que a equipe espera: o Welch, porque o Mann-Whitney "
    "compara postos e responde a outra pergunta; com cauda longa, é preciso aceitar o poder menor do Welch.",
    "Assimetria mais forte, outliers ou amostra pequena (C2 a C4): o Mann-Whitney, com vantagem ainda maior.",
    "Grupos com variâncias ou formas diferentes: o estudo não cobre esse caso (ver a limitação abaixo).",
)
TEXTO_LIMITACAO = (
    "Todos os cenários simulam grupos com a mesma forma e a mesma variância, que diferem "
    "só pela posição; o cenário C5, com variâncias e tamanhos desiguais, não foi feito. Quando as formas diferem, "
    "o Mann-Whitney deixa de comparar só a posição e pode rejeitar H₀ mesmo com medianas iguais, e é para "
    "variâncias desiguais que o Welch foi feito. Nos dados reais os dois grupos têm forma parecida na escala log "
    "(seção 2), mas isso não foi testado, e a recomendação depende disso."
)


RECOMENDACAO_CURTA = (
    "Mann-Whitney para o tempo até o merge de PRs (cauda longa, cerca de 30 PRs por grupo): erro tipo I de 4,67% "
    "contra 2,47% do Welch e poder até 41 p.p. maior (C1). Welch só com dados aproximadamente normais ou se a pergunta "
    "for sobre médias."
)
LIMITACAO_CURTA = (
    "Os cenários simulam grupos com a mesma forma e variância (C5 não foi feito); os dados reais vêm de um repositório, "
    "de uma janela curta e de 30 PRs por grupo."
)
CLASSE_DO_SELO = (("Sim", "sim", "Confirmado"), ("Em parte", "parte", "Em parte"), ("Não", "nao", "Não confirmado"))
NOMES_CURTOS_SITUACOES = (   # (início do rótulo da seção 7, rótulo curto do selo)
    ("C0", "C0 normal"), ("C1", "C1 lognormal"), ("C2", "C2 assimetria"), ("C3", "C3 outliers"), ("C4", "C4 n = 10"),
    ("Onde a vantagem", "Muda de lado"), ("α = 0,01", "α = 1%"), ("Dados reais", "Dados reais"),
)


def _selo(situacao: str, confirmou: str) -> str:
    nome = next((curto for prefixo, curto in NOMES_CURTOS_SITUACOES if situacao.startswith(prefixo)), situacao)
    for inicio, classe, rotulo in CLASSE_DO_SELO:
        if confirmou.startswith(inicio):
            return f'<div class="selo {classe}" title="{_e(situacao)}"><span>{_e(nome)}</span><b>{_e(rotulo)}</b></div>'
    return f'<div class="selo" title="{_e(situacao)}"><span>{_e(nome)}</span><b>{_e(confirmou)}</b></div>'


def _link_commit(chave: str) -> str:
    sha, data, _ = COMMITS[chave]
    return f'<a href="{LINK_COMMIT}{sha}"><code>{sha[:7]}</code></a> ({data})'


def _conclusao_detalhada() -> str:
    linhas = "\n".join(
        f"<tr><th>{_e(situacao)}</th><td>{'<br>'.join(f'“{_e(c)}”' for c in citacoes)}</td>"
        f"<td>{_e(resultado)}</td><td>{_e(confirmou)}</td></tr>"
        for situacao, citacoes, resultado, confirmou in EXPECTATIVA_X_RESULTADO
    )
    condicoes = "".join(f"<li>{_e(c)}</li>" for c in CONDICOES_RECOMENDACAO)
    return f"""<p class="texto">A expectativa do grupo foi escrita em <a href="{LINK_CENARIO}">docs/cenario.md</a>
(seção 5) no commit {_link_commit("expectativa")}, antes do primeiro commit que roda os testes em dados simulados,
{_link_commit("primeira_simulacao")}, e não foi reescrita depois. Os parâmetros das simulações estão congelados no
<code>config.yaml</code> desde o commit {_link_commit("config_congelado")}, e o hash desse arquivo está no registro de
cada simulação.</p>
<table>
<tr><th>Situação</th><th>O que o grupo esperava (citação do cenario.md)</th><th>O que encontrou</th><th>Confirmou?</th></tr>
{linhas}
</table>
<p class="legenda">Erro tipo I com α = 0,05 e classificação da S02-07 (seção 4); poder e vantagem em pontos
percentuais (p.p.) da seção 5; dados reais da seção 6.</p>
<p class="texto">{_e(TEXTO_DIFERENCA_DADOS_REAIS)}</p>
<p class="texto"><strong>Recomendação.</strong> {_e(TEXTO_RECOMENDACAO)}</p>
<ul class="texto">{condicoes}</ul>
<p class="texto"><strong>Limitação principal.</strong> {_e(TEXTO_LIMITACAO)}</p>"""


def _secao_conclusao() -> str:
    selos = "".join(_selo(situacao, confirmou) for situacao, _, _, confirmou in EXPECTATIVA_X_RESULTADO)
    return (
        '<div class="cab"><h2>7. Conclusão</h2></div><div class="faixa-conclusao">'
        f'<div><h3>Esperado × encontrado</h3><div class="selos">{selos}</div></div>'
        f'<div class="caixa"><h3>Recomendação</h3><p>{_e(RECOMENDACAO_CURTA)}</p></div>'
        f'<div class="caixa"><h3>Limitação principal</h3><p>{_e(LIMITACAO_CURTA)}</p></div></div>'
    )


def _interpretacao(cfg: dict, reais: pd.DataFrame, paragrafos_dados_reais) -> str:
    """A folha com os textos longos (abre com a tecla i); vazia se `MOSTRAR_INTERPRETACAO` é falso."""
    if not MOSTRAR_INTERPRETACAO:
        return ""
    reais_html = "".join(f'<p class="texto">{_e(p)}</p>' for p in paragrafos_dados_reais)
    partes = [
        ("1. Cenário", _cenario_detalhado(cfg, reais)),
        ("2. Os dados", _texto("TEXTO_G1")),
        ("3. Como os testes funcionam", _texto("TEXTO_G2")),
        ("4. Erro tipo I", _texto("TEXTO_G3")),
        ("5. Poder", _texto("TEXTO_G4")),
        ("6. Dados reais", reais_html),
    ]
    if MOSTRAR_CONCLUSAO:
        partes.append((SECAO_CONCLUSAO[1], _conclusao_detalhada()))
    corpo = "".join(f"<h3>{_e(titulo)}</h3>{texto}" for titulo, texto in partes if texto)
    return (
        '<aside id="interpretacao" hidden><div class="cabecalho"><h2>Interpretação</h2>'
        f'<button type="button" id="fechar-interpretacao">Fechar (Esc)</button></div>{corpo}</aside>'
    )


def _pagina(cfg: dict) -> str:
    base = Path(cfg["pasta"])
    reais = pd.read_csv(base / cfg["coleta"]["saida"])
    exemplos = gerador.exemplos_calibrados(calibracao.ler(base / cfg["calibracao"]["saida"]))
    resultados, sem_resultados = _ler_resultados(cfg)
    try:
        tabela = testes.tabela_dados_reais(reais)
        paragrafos, erro = texto_dados_reais(tabela, reais), None
    except Exception as falha:  # o dashboard sai mesmo se a tabela falhar
        tabela, paragrafos, erro = None, [], falha
    figuras = _Figuras()
    conteudo = {
        "cenario": _secao_cenario(cfg, reais),
        "dados": _secao_dados(figuras, reais, exemplos),
        "testes": _secao_testes(figuras, exemplos),
        "erro-tipo-1": _secao_simulacao(figuras, resultados, sem_resultados, "g3", LEGENDA_G3),
        "poder": _secao_simulacao(figuras, resultados, sem_resultados, "g4", LEGENDA_G4),
        "dados-reais": _secao_dados_reais(tabela, erro, reais),
    }
    secoes_da_pagina = SECOES
    if MOSTRAR_CONCLUSAO:
        conteudo["conclusao"] = _secao_conclusao()
        secoes_da_pagina = (*SECOES, SECAO_CONCLUSAO)
    for ancora, previsto in EM_CONSTRUCAO.items():
        conteudo[ancora] = _marcador(f"Em construção: {previsto}.")
    secoes = "\n".join(f'<section id="{ancora}">\n{conteudo[ancora]}\n</section>' for ancora, _ in secoes_da_pagina)
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(TITULO)}</title>
<style>{ESTILO}</style>
</head>
<body>
{_topo(_indicadores(reais, resultados))}
<main class="coluna">
{secoes}
</main>
{_interpretacao(cfg, reais, paragrafos)}
<script>{SCRIPT}</script>
</body>
</html>
"""


def montar(saida: Path, cfg: dict | None = None) -> None:
    """Gera o dashboard em `saida` (HTML único, UTF-8). Sem `cfg`, lê o `config.yaml` padrão."""
    if cfg is None:
        cfg = config.carregar()
    saida = Path(saida)
    saida.parent.mkdir(parents=True, exist_ok=True)
    saida.write_text(_pagina(cfg), encoding="utf-8", newline="\n")
