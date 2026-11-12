"""Montagem do dashboard em HTML com as 7 seções (S01-11, S02-11).

`montar(saida)` grava uma página HTML estática única, com o Plotly.js embutido uma vez (a página
abre sem internet). O topo tem os links do Kanban, do repositório e do próprio dashboard; depois
vêm as 7 seções do enunciado, em ordem fixa:

1. Cenário (pergunta, hipóteses e origem dos dados reais);
2. Os dados (G1);
3. Como os testes funcionam (G2, um por exemplo da S01-08);
4. Erro tipo I (G3, α = 0,05) e 5. Poder (G4, α = 0,05), lidos de `resultados.csv` (S02-11);
6. Dados reais: a tabela dos dois testes nos PRs coletados, com a conclusão (S02-10);
7. Conclusão: expectativa × resultado, recomendação e limitação principal, com os commits da
   expectativa e do `config.yaml` congelado (S02-12).

Os gráficos vêm de `graficos` pelo nome; se um ainda não existir ou falhar, a seção mostra um
marcador com o motivo e o resto da página é gerado (`_figura_ou_marcador`). O mesmo vale para o
`resultados.csv` das seções 4 e 5: se ele faltar ou não abrir, as duas mostram o marcador.
"""

import html
from pathlib import Path

import numpy as np
import pandas as pd

from lab04 import calibracao, config, gerador, graficos, testes
from lab04.descritiva import GRUPOS, horas_do_grupo

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
    ("conclusao", "7. Conclusão"),
)
EM_CONSTRUCAO: dict = {}   # seções ainda sem conteúdo: {âncora: o que falta}; todas prontas desde a S02-12

ESTILO = """
body { font-family: system-ui, -apple-system, "Segoe UI", sans-serif; margin: 0; color: #222; background: #fafafa; }
header { background: #2b2d42; color: #fff; padding: 1.2rem 2rem; }
header h1 { margin: 0 0 .4rem; font-size: 1.5rem; }
header p { margin: .2rem 0; font-size: .9rem; opacity: .9; }
nav.links a { color: #fff; margin-right: 1.2rem; font-weight: 600; }
nav.links span.marcador { font-weight: 400; opacity: .75; }
nav.indice { padding: .6rem 2rem; background: #edf2f4; font-size: .9rem; }
nav.indice a { margin-right: 1rem; color: #2b2d42; }
main { max-width: 1200px; margin: 0 auto; padding: 0 2rem 3rem; }
section { background: #fff; margin: 1.5rem 0; padding: 1rem 1.5rem; border-radius: 8px;
          box-shadow: 0 1px 3px rgba(0, 0, 0, .08); }
section h2 { margin-top: .3rem; color: #2b2d42; }
p.texto, ul.texto { line-height: 1.55; max-width: 70rem; }
p.legenda { color: #555; font-size: .9rem; margin-bottom: 0; }
table { border-collapse: collapse; margin: .8rem 0; font-size: .95rem; }
th, td { border: 1px solid #ccc; padding: .4rem .7rem; text-align: left; vertical-align: top; }
th { background: #edf2f4; }
div.marcador { border: 2px dashed #bbb; color: #666; padding: 1.5rem; text-align: center; border-radius: 6px; }
"""


def _e(texto) -> str:
    return html.escape(str(texto))


def _data(valor) -> str:
    """Data do config (`date` ou texto ISO) no formato dd/mm/aaaa."""
    return pd.Timestamp(valor).strftime("%d/%m/%Y")


def _marcador(texto: str) -> str:
    return f'<div class="marcador">{_e(texto)}</div>'


class _Figuras:
    """Converte figuras em HTML, embutindo o Plotly.js só na primeira."""

    def __init__(self):
        self.plotly_embutido = False

    def html(self, figura) -> str:
        trecho = figura.to_html(full_html=False, include_plotlyjs=not self.plotly_embutido, config={"responsive": True})
        self.plotly_embutido = True
        return trecho


def _figura_ou_marcador(figuras: _Figuras, nome: str, *args) -> str:
    """HTML do gráfico `graficos.<nome>(*args)`, ou um marcador se ele não existe ou falha."""
    funcao = getattr(graficos, nome, None)
    if funcao is None:
        return _marcador(f"Gráfico indisponível: {nome} ainda não foi implementado.")
    try:
        return figuras.html(funcao(*args))
    except Exception as erro:  # o dashboard sai mesmo com um gráfico quebrado
        return _marcador(f"Gráfico indisponível: {nome} falhou ({type(erro).__name__}: {erro}).")


def _texto(nome: str) -> str:
    texto = getattr(graficos, nome, None)
    return f'<p class="texto">{_e(texto)}</p>' if texto else ""


def _topo() -> str:
    return f"""<header>
<h1>{_e(TITULO)}</h1>
<p>{_e(" · ".join(INTEGRANTES))}</p>
<nav class="links">
<a href="{LINK_KANBAN}">Kanban (GitHub Projects)</a>
<a href="{LINK_REPOSITORIO}">Repositório</a>
<a href="{LINK_DASHBOARD}">Dashboard publicado</a> <span class="marcador">(publicação na S02-13)</span>
</nav>
</header>
<nav class="indice">{"".join(f'<a href="#{ancora}">{_e(titulo)}</a>' for ancora, titulo in SECOES)}</nav>"""


def _secao_cenario(cfg: dict, reais: pd.DataFrame) -> str:
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


def _secao_dados(figuras: _Figuras, reais: pd.DataFrame, exemplos: dict) -> str:
    exemplo = exemplos["com_efeito"]
    return (
        _figura_ou_marcador(figuras, "g1", reais, (exemplo["a"], exemplo["b"]))
        + f'<p class="legenda">Simulados: lognormal calibrada nos dados reais, δ = {graficos._num(exemplo["delta"], 2)}, '
        f'n = {exemplo["n"]} por grupo, semente {exemplo["semente"]}.</p>'
        + _texto("TEXTO_G1")
    )


def _secao_testes(figuras: _Figuras, exemplos: dict) -> str:
    partes = []
    for caso, descricao in (("sem_efeito", "H₀ verdadeira"), ("com_efeito", "H₀ falsa")):
        exemplo = exemplos[caso]
        partes.append(_figura_ou_marcador(figuras, "g2", exemplo))
        partes.append(
            f'<p class="legenda">Exemplo {caso.replace("_", " ")} ({descricao}): '
            f'δ = {graficos._num(exemplo["delta"], 2)}, n = {exemplo["n"]} por grupo, semente {exemplo["semente"]}.</p>'
        )
    return "".join(partes) + _texto("TEXTO_G2")


LEGENDA_G3 = (
    "Classificação (S02-07): liberal se o limite inferior do intervalo de Wilson de 95% fica acima de α, "
    "conservador se o limite superior fica abaixo de α e ok se o intervalo contém α; a de cada barra aparece "
    "ao passar o mouse, e a tabela completa, com α = 0,01, está em dados/simulacao/classificacao.csv."
)
LEGENDA_G4 = (
    "Em δ = 0 a curva é o erro tipo I do G3; a vantagem de um teste sobre o outro em cada efeito, com α = 0,05 "
    "e α = 0,01, está em dados/simulacao/poder.csv."
)


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


def _secao_simulacao(figuras: _Figuras, resultados, marcador, grafico: str, legenda: str, texto: str) -> str:
    """Seções 4 e 5: o gráfico `grafico` com α = 0,05, a legenda e o texto de `graficos.<texto>`."""
    if resultados is None:
        return marcador + _texto(texto)
    tamanhos = _tamanhos(resultados)
    return (
        _figura_ou_marcador(figuras, grafico, resultados)
        + f'<p class="legenda">{_e((tamanhos + ". " if tamanhos else "") + legenda)}</p>'
        + _texto(texto)
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
    """Tabela HTML da seção 6: uma linha por teste, com os números de `testes.tabela_dados_reais`."""
    linhas = []
    for _, r in tabela.iterrows():
        linhas.append(
            f"<tr><th>{_e(NOMES_TESTE_TABELA[r['teste']])}</th><td>{_e(O_QUE_COMPARA[r['teste']])}</td>"
            f"<td>{_e(_estatistica(r))}</td><td>{_e(graficos._p_rotulo(r['p_valor']))}</td>"
            f"<td>{_e(NOMES_MEDIDA[r['medida_efeito']])} = {_e(graficos._num(r['tamanho_efeito'], 2))} ({_e(r['magnitude'])})</td>"
            f"<td>{_e(graficos._num(r['razao_medianas'], 2))}</td><td><strong>{_e(r['conclusao'])}</strong></td></tr>"
        )
    return (
        "<table>\n<tr><th>Teste</th><th>Compara</th><th>Estatística</th><th>p-valor</th><th>Tamanho de efeito</th>"
        f"<th>Razão de medianas (com bot ÷ sem bot)</th><th>Conclusão (α = {_e(graficos._num(alfa, 2))})</th></tr>\n"
        + "\n".join(linhas)
        + "\n</table>"
    )


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


def _secao_dados_reais(reais: pd.DataFrame, cfg: dict) -> str:
    try:
        tabela = testes.tabela_dados_reais(reais)
        paragrafos = texto_dados_reais(tabela, reais)
    except Exception as erro:  # o dashboard sai mesmo se a tabela falhar
        return _marcador(f"Tabela indisponível: os testes nos dados reais falharam ({type(erro).__name__}: {erro}).")
    n = reais["grupo"].value_counts()
    legenda = (
        f"{n.get('com_bot', 0)} PRs com bot e {n.get('sem_bot', 0)} sem bot; testes bicaudais; o Welch compara médias e o "
        "Mann-Whitney compara postos. Magnitude: |g| < 0,2 negligível, < 0,5 pequeno, < 0,8 médio; |δ de Cliff| < 0,147 "
        "negligível, < 0,33 pequeno, < 0,474 médio."
    )
    return (
        tabela_dados_reais_html(tabela)
        + f'<p class="legenda">{_e(legenda)}</p>'
        + "".join(f'<p class="texto">{_e(p)}</p>' for p in paragrafos)
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


def _link_commit(chave: str) -> str:
    sha, data, _ = COMMITS[chave]
    return f'<a href="{LINK_COMMIT}{sha}"><code>{sha[:7]}</code></a> ({data})'


def _secao_conclusao() -> str:
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


def _pagina(cfg: dict) -> str:
    base = Path(cfg["pasta"])
    reais = pd.read_csv(base / cfg["coleta"]["saida"])
    exemplos = gerador.exemplos_calibrados(calibracao.ler(base / cfg["calibracao"]["saida"]))
    resultados, sem_resultados = _ler_resultados(cfg)
    figuras = _Figuras()
    conteudo = {
        "cenario": _secao_cenario(cfg, reais),
        "dados": _secao_dados(figuras, reais, exemplos),
        "testes": _secao_testes(figuras, exemplos),
        "erro-tipo-1": _secao_simulacao(figuras, resultados, sem_resultados, "g3", LEGENDA_G3, "TEXTO_G3"),
        "poder": _secao_simulacao(figuras, resultados, sem_resultados, "g4", LEGENDA_G4, "TEXTO_G4"),
        "dados-reais": _secao_dados_reais(reais, cfg),
        "conclusao": _secao_conclusao(),
    }
    for ancora, previsto in EM_CONSTRUCAO.items():
        conteudo[ancora] = _marcador(f"Em construção: {previsto}.")
    secoes = "\n".join(
        f'<section id="{ancora}">\n<h2>{_e(titulo)}</h2>\n{conteudo[ancora]}\n</section>' for ancora, titulo in SECOES
    )
    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{_e(TITULO)}</title>
<style>{ESTILO}</style>
</head>
<body>
{_topo()}
<main>
{secoes}
</main>
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
