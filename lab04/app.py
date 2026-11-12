"""Dashboard interativo do Lab04 (Streamlit), numa página única.

Rode a partir da pasta `lab04/`:

    python -m lab04 app            # ou: python -m streamlit run app.py

Segue a seção 4 do enunciado: os links do repositório, do GitHub Projects e do dashboard no topo, e
as 7 seções na ordem pedida (cenário, os dados, como os testes funcionam, erro tipo I, poder, dados
reais e conclusão), cada gráfico com o texto curto do grupo logo abaixo, sempre visível. A diferença
para o dashboard estático (`dashboard.py`) são os controles dentro de cada seção: sortear outros dados
simulados, mudar o efeito, o n e o α de um exemplo, filtrar cenários e trocar o α. Depois da seção 7,
um apêndice ("Laboratório ao vivo") roda uma simulação nova com um cenário montado na tela.

Cada seção é um `st.fragment`: mexer num controle refaz só aquela seção, sem recarregar a página.
A lógica fica em `lab04/interativo.py`; este arquivo só monta a interface.
"""

import random

import numpy as np
import pandas as pd
import streamlit as st

from lab04 import dashboard, gerador, graficos, interativo, testes

ANCORA_LAB = "laboratorio"
TITULO_LAB = "Apêndice: laboratório ao vivo"
TITULOS = dict(dashboard.SECOES)   # âncora → "1. Cenário", ...

st.set_page_config(page_title="Lab04: Welch × Mann-Whitney", page_icon="📊", layout="wide")

CSS = """
<style>
div.lab04 table { border-collapse: collapse; margin: .6rem 0; font-size: .95rem; }
div.lab04 th, div.lab04 td { border: 1px solid rgba(128,128,128,.4); padding: .4rem .7rem; text-align: left; vertical-align: top; }
div.lab04 th { background: rgba(128,128,128,.12); }
div.lab04 p.legenda { opacity: .75; font-size: .9rem; }
div.lab04 p.texto, div.lab04 ul.texto { line-height: 1.55; }
div.leitura { border-left: 4px solid #2b2d42; background: rgba(43,45,66,.06); padding: .6rem 1rem;
              border-radius: 4px; line-height: 1.55; margin: .4rem 0 1rem; }
div.topo { background: #2b2d42; color: #fff; padding: 1rem 1.4rem; border-radius: 8px; margin-bottom: .6rem; }
div.topo h1 { color: #fff; font-size: 1.6rem; margin: 0 0 .3rem; padding: 0; }
div.topo p { margin: .15rem 0; opacity: .9; }
div.topo a { color: #fff; font-weight: 600; margin-right: 1.2rem; }
div.indice a { margin-right: 1rem; }
</style>
"""


# --- dados e cálculos em cache: cada combinação de controles é calculada uma vez por sessão do servidor ---

@st.cache_data(show_spinner=False)
def _dados():
    return interativo.carregar()


@st.cache_data(show_spinner="Gerando o exemplo e 10.000 conjuntos sob H₀...")
def _figura_g2(cenario: dict, delta: float, n: int, semente: int, alfa: float):
    exemplo = gerador.exemplo_simulado(cenario, delta, n, semente)
    return exemplo, graficos.g2(exemplo, alfa)


@st.cache_data(show_spinner="Rodando a simulação...")
def _simular(cenario: dict, efeitos: tuple, n_rep: int, semente: int, indice: int):
    return interativo.simular_cenario(cenario, list(efeitos), n_rep, semente, indice)


# --- peças de interface ---

def _html(trecho: str) -> None:
    st.markdown(f'<div class="lab04">{trecho}</div>', unsafe_allow_html=True)


def _grafico(figura) -> None:
    st.plotly_chart(figura, theme=None, width="stretch")


def _leitura(texto: str, rotulo: str = "Leitura do grupo") -> None:
    """O texto curto que acompanha cada gráfico (enunciado, seção 4), sempre visível."""
    st.markdown(f'<div class="leitura"><strong>{rotulo}.</strong> {dashboard._e(texto)}</div>', unsafe_allow_html=True)


def _alfa(rotulo: str, chave: str, opcoes=interativo.ALFAS_INTERATIVOS, padrao: float = testes.ALFA) -> float:
    return st.segmented_control(
        rotulo, opcoes, default=padrao, key=chave, format_func=lambda a: f"α = {graficos._num(a * 100, 0)}%",
    ) or padrao


def _secao(ancora: str) -> None:
    st.divider()
    st.header(TITULOS.get(ancora, TITULO_LAB), anchor=ancora)


def topo(d: dict) -> None:
    """Título, integrantes e os links pedidos no topo (repositório, GitHub Projects e dashboard), e o índice."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f"""<div class="topo"><h1>{dashboard._e(dashboard.TITULO)}</h1>
<p>{dashboard._e(" · ".join(dashboard.INTEGRANTES))}</p>
<p><a href="{dashboard.LINK_KANBAN}">Kanban (GitHub Projects)</a>
<a href="{dashboard.LINK_REPOSITORIO}">Repositório</a>
<a href="{dashboard.LINK_DASHBOARD}">Dashboard publicado</a></p></div>""",
        unsafe_allow_html=True,
    )
    indice = [f'<a href="#{ancora}">{dashboard._e(titulo)}</a>' for ancora, titulo in dashboard.SECOES]
    indice.append(f'<a href="#{ANCORA_LAB}">{TITULO_LAB}</a>')
    st.markdown(f'<div class="indice">{"".join(indice)}</div>', unsafe_allow_html=True)
    st.caption(
        "Dashboard interativo: os controles de cada seção refazem só aquela seção. As seções 4 e 5 leem as "
        f"simulações gravadas em resultados.csv (10.000 repetições por ponto, semente {d['cfg']['semente']})."
    )


# --- as 7 seções do enunciado, nesta ordem ---

@st.fragment
def secao_cenario(d: dict) -> None:
    _html(dashboard._secao_cenario(d["cfg"], d["reais"]))


@st.fragment
def secao_dados(d: dict) -> None:
    _, delta_calibrado = gerador.cenario_calibrado(d["calibracao"])
    padrao = {"g1_delta": round(float(delta_calibrado), 2), "g1_n": gerador.N_EXEMPLO,
              "g1_semente": gerador.SEMENTE_COM_EFEITO}
    for chave, valor in padrao.items():
        st.session_state.setdefault(chave, valor)

    def sortear():
        st.session_state["g1_semente"] = random.randint(1, 99_999_999)

    def restaurar():
        st.session_state.update(padrao)

    c1, c2, c3, c4 = st.columns([3, 3, 2, 2])
    delta = c1.slider("Efeito δ dos simulados (escala log; razão de medianas B/A = e^δ)", -1.0, 2.0, step=0.05,
                      key="g1_delta")
    n = c2.slider("PRs simulados por grupo (n)", 5, 200, step=5, key="g1_n")
    semente = c3.number_input("Semente", min_value=1, step=1, key="g1_semente")
    c4.button("🎲 Sortear outro conjunto", on_click=sortear, width="stretch", key="g1_sortear")
    c4.button("↺ Voltar ao exemplo do relatório", on_click=restaurar, width="stretch", key="g1_restaurar")

    delta = interativo.delta_exato(delta, delta_calibrado)
    a, b = interativo.amostras_simuladas(d["calibracao"], delta, n, semente)
    _grafico(graficos.g1(d["reais"], (a, b)))

    reais = d["reais"]
    reais_med = interativo.medianas(*(reais.loc[reais["grupo"] == g, "horas_ate_merge"] for g in ("com_bot", "sem_bot")))
    sim_med = interativo.medianas(a, b)
    m1, m2, m3, m4 = st.columns(4)
    m1.metric("Mediana real, com bot", f"{graficos._num(reais_med['a'], 1)} h")
    m2.metric("Mediana real, sem bot", f"{graficos._num(reais_med['b'], 1)} h")
    m3.metric("Mediana simulada A / B", f"{graficos._num(sim_med['a'], 1)} / {graficos._num(sim_med['b'], 1)} h")
    m4.metric("Razão B/A simulada", f"{graficos._num(sim_med['razao'], 2)}×",
              f"modelo: {graficos._num(np.exp(delta), 2)}×", delta_color="off")
    st.caption(
        f"Lognormal calibrada nos dados reais (μ e σ de calibracao.json). δ = {graficos._num(delta_calibrado, 2)} no "
        f"controle usa o δ calibrado exato ({graficos._num(delta_calibrado, 4)}); com ele, n = 30 e a semente "
        f"{gerador.SEMENTE_COM_EFEITO}, a figura é a do texto abaixo. Sorteie outros conjuntos: com n = 30 a razão das "
        "medianas simuladas varia muito em torno da do modelo."
    )
    _leitura(graficos.TEXTO_G1, "Leitura do grupo (exemplo do relatório)")


@st.fragment
def secao_testes(d: dict) -> None:
    cenario_calibrado, delta_calibrado = gerador.cenario_calibrado(d["calibracao"])
    opcoes = {"Lognormal calibrada nos dados reais": cenario_calibrado}
    opcoes.update({interativo.rotulo_cenario(c): c for c in d["cenarios"].values()})
    exemplos = {
        "sem": {"g2_delta": 0.0, "g2_semente": gerador.SEMENTE_SEM_EFEITO},
        "com": {"g2_delta": round(float(delta_calibrado), 2), "g2_semente": gerador.SEMENTE_COM_EFEITO},
    }
    st.session_state.setdefault("g2_cenario", next(iter(opcoes)))
    st.session_state.setdefault("g2_n", gerador.N_EXEMPLO)
    for chave, valor in exemplos["com"].items():
        st.session_state.setdefault(chave, valor)

    def carregar(qual):
        st.session_state.update(exemplos[qual], g2_cenario=next(iter(opcoes)), g2_n=gerador.N_EXEMPLO)

    b1, b2, b3, _ = st.columns([2, 2, 2, 4])
    b1.button("Exemplo sem efeito (H₀ verdadeira)", on_click=carregar, args=("sem",), width="stretch", key="g2_sem")
    b2.button("Exemplo com efeito (H₀ falsa)", on_click=carregar, args=("com",), width="stretch", key="g2_com")
    b3.button("🎲 Sortear outro conjunto", width="stretch", key="g2_sortear",
              on_click=lambda: st.session_state.update(g2_semente=random.randint(1, 99_999_999)))

    c1, c2, c3, c4, c5 = st.columns([3, 2, 2, 2, 2])
    nome = c1.selectbox("Distribuição dos dados", list(opcoes), key="g2_cenario")
    cenario = opcoes[nome]
    unidade = "desvios-padrão" if cenario["familia"] == "normal" else "escala log"
    delta = c2.slider(f"Efeito δ ({unidade})", 0.0, 2.0, step=0.05, key="g2_delta")
    n = c3.slider("n por grupo", interativo.N_MINIMO, interativo.N_MAXIMO, key="g2_n")
    semente = c4.number_input("Semente", min_value=1, step=1, key="g2_semente")
    with c5:
        alfa = _alfa("Nível de significância", "g2_alfa")

    if cenario is cenario_calibrado:
        delta = interativo.delta_exato(delta, delta_calibrado)
    exemplo, figura = _figura_g2(cenario, float(delta), int(n), int(semente), float(alfa))
    _grafico(figura)
    st.dataframe(interativo.resumo_exemplo(exemplo, alfa), hide_index=True, width="stretch")
    leitura = interativo.leitura_exemplo(exemplo, alfa)
    (st.warning if "erro" in leitura else st.success)(leitura)
    _leitura(graficos.TEXTO_G2, "Leitura do grupo (exemplos do relatório, α = 5%)")


def _filtro_de_cenarios(d: dict, chave: str) -> list:
    ids = list(dict.fromkeys(d["resultados"]["cenario"]))
    return st.multiselect("Cenários", ids, default=ids, key=chave,
                          format_func=lambda c: graficos.NOMES_CENARIO.get(c, c)) or ids


def _sem_resultados() -> None:
    st.error("dados/simulacao/resultados.csv não encontrado: rode `python -m lab04.resultados`.")


@st.fragment
def secao_erro_tipo_1(d: dict) -> None:
    if d["resultados"] is None:
        return _sem_resultados()
    c1, c2 = st.columns([3, 1])
    with c1:
        cenarios = _filtro_de_cenarios(d, "g3_cenarios")
    with c2:
        alfa = _alfa("Nível de significância", "g3_alfa", opcoes=(0.05, 0.01))
    res = d["resultados"][d["resultados"]["cenario"].isin(cenarios)]
    _grafico(graficos.g3(res, alfa))
    _leitura(graficos.TEXTO_G3)
    with st.expander("Tabela da classificação (liberal, conservador ou ok)"):
        st.dataframe(interativo.tabela_classificacao(res, alfa), hide_index=True, width="stretch")
        st.caption(dashboard.LEGENDA_G3)


@st.fragment
def secao_poder(d: dict) -> None:
    if d["resultados"] is None:
        return _sem_resultados()
    c1, c2 = st.columns([3, 1])
    with c1:
        cenarios = _filtro_de_cenarios(d, "g4_cenarios")
    with c2:
        alfa = _alfa("Nível de significância", "g4_alfa", opcoes=(0.05, 0.01))
    res = d["resultados"][d["resultados"]["cenario"].isin(cenarios)]
    _grafico(graficos.g4(res, alfa))
    _leitura(graficos.TEXTO_G4)
    with st.expander("Tabela do poder e da vantagem em cada efeito"):
        st.dataframe(interativo.tabela_poder(res, alfa), hide_index=True, width="stretch")
        st.caption(dashboard.LEGENDA_G4)


@st.fragment
def secao_dados_reais(d: dict) -> None:
    reais = d["reais"]
    alfa = _alfa("Nível de significância dos testes", "reais_alfa")
    tabela = testes.tabela_dados_reais(reais, alfa)
    _html(dashboard.tabela_dados_reais_html(tabela, alfa))
    _leitura(" ".join(dashboard.texto_dados_reais(tabela, reais, alfa)))
    with st.expander("Cada PR coletado, por grupo"):
        _grafico(interativo.figura_dados_reais(reais))
        st.caption(
            "Cada ponto é um PR; passe o mouse para ver o número e as horas. O eixo está em escala log: as caixas dos "
            "dois grupos ficam quase na mesma altura, o que combina com a razão de medianas perto de 1 da tabela."
        )


@st.fragment
def secao_conclusao(d: dict) -> None:
    _html(dashboard._secao_conclusao())


# --- apêndice: fora das 7 seções do enunciado ---

@st.fragment
def secao_laboratorio(d: dict) -> None:
    st.markdown(
        "Monte um cenário, rode uma simulação nova e compare com o cenário gravado em `resultados.csv`. Usa o "
        "mesmo motor e o mesmo esquema de sementes das simulações finais: com os parâmetros de um cenário, a "
        "semente 42 e 10.000 repetições, o resultado é idêntico ao do CSV."
    )
    cenarios = d["cenarios"]
    base_id = st.selectbox("Partir do cenário", list(cenarios), index=1 if len(cenarios) > 1 else 0, key="lab_base",
                           format_func=lambda c: interativo.rotulo_cenario(cenarios[c]))
    base = cenarios[base_id]
    contaminacao = base.get("contaminacao") or {"p": 0.0, "fator": 20.0}

    with st.form(f"lab_{base_id}"):
        c1, c2, c3 = st.columns(3)
        familia = c1.radio("Distribuição", ["normal", "lognormal"], horizontal=True,
                           index=0 if base["familia"] == "normal" else 1)
        # number_input, e não slider: guarda o σ do config sem arredondar (1,6493), o que mantém a reprodução do CSV
        sigma = c1.number_input("σ (na lognormal, de log x: mede a assimetria)", 0.1, 3.0, float(base["sigma"]), 0.1,
                                format="%.4f")
        n = c2.slider("n por grupo", interativo.N_MINIMO, interativo.N_MAXIMO, int(base["n"]))
        p = c2.slider("Outliers: fração das observações multiplicadas", 0.0, 0.2, float(contaminacao["p"]), 0.01)
        fator = c2.slider("Outliers: fator de multiplicação", 1.0, 100.0, float(contaminacao["fator"]), 1.0)
        efeitos_base = base["efeitos"]
        maximo = c3.slider("Maior efeito δ da grade", 0.2, 3.0, float(efeitos_base[-1]), 0.1)
        pontos = c3.slider("Pontos na grade (o primeiro é δ = 0)", 3, 11, len(efeitos_base))
        n_rep = c3.select_slider("Repetições por ponto", interativo.REPETICOES_INTERATIVAS, value=10_000)
        semente = c3.number_input("Semente", min_value=0, value=int(d["cfg"]["semente"]), step=1)
        rodar = st.form_submit_button("▶ Rodar simulação", type="primary")

    if rodar:
        cenario = interativo.cenario_personalizado(familia, sigma, n, p, fator, mu=float(base["mu"]))
        efeitos = interativo.grade_de_efeitos(maximo, pontos)
        if len(efeitos) == len(efeitos_base) and np.allclose(efeitos, efeitos_base):
            efeitos = [float(e) for e in efeitos_base]
        indice = interativo.indice_do_cenario(d["cfg"], base_id)
        simulado = _simular(cenario, tuple(efeitos), int(n_rep), int(semente), indice)
        st.session_state["lab_resultado"] = (base_id, cenario["unidade_efeito"], simulado)
    if "lab_resultado" not in st.session_state:
        st.info("Ajuste os parâmetros e clique em **Rodar simulação**.")
        return
    base_id, unidade, simulado = st.session_state["lab_resultado"]

    alfa = _alfa("Nível de significância", "lab_alfa", opcoes=(0.05, 0.01))
    resumo = interativo.resumo_simulacao(simulado, alfa)
    colunas = st.columns(4)
    for i, teste in enumerate(graficos.NOMES_TESTE):
        r = resumo[teste]
        colunas[2 * i].metric(f"Erro tipo I, {graficos.NOMES_TESTE[teste]}", f"{graficos._num(r['erro_tipo_1'] * 100, 2)}%",
                              r["classificacao"], delta_color="off")
        colunas[2 * i + 1].metric(f"Maior poder, {graficos.NOMES_TESTE[teste]}", f"{graficos._num(r['poder_maximo'] * 100, 1)}%")

    referencia = None
    if d["resultados"] is not None:
        referencia = d["resultados"][d["resultados"]["cenario"] == base_id]
        if interativo.iguais_ao_csv(simulado, referencia):
            st.success(f"Reproduziu exatamente as linhas de {base_id} do resultados.csv (mesmas rejeições em todos os pontos).")
    juntos = pd.concat([referencia, simulado]) if referencia is not None else simulado
    nomes = {base_id: f"{graficos.NOMES_CENARIO.get(base_id, base_id)} (resultados.csv)",
             interativo.ID_PERSONALIZADO: "Simulação nova"}
    unidades = {interativo.ID_PERSONALIZADO: unidade}
    g1, g2 = st.columns([2, 3])
    with g1:
        _grafico(graficos.g3(juntos, alfa, nomes=nomes))
    with g2:
        _grafico(graficos.g4(juntos, alfa, nomes=nomes, unidades=unidades))
    st.caption(
        "À esquerda, o erro tipo I (δ = 0) e, à direita, o poder ao longo da grade, da simulação nova ao lado do "
        "cenário de partida gravado em resultados.csv. A simulação nova não muda os CSVs nem as seções 4 e 5."
    )
    with st.expander("Tabela da simulação nova"):
        st.dataframe(interativo.tabela_poder(simulado, alfa, unidades), hide_index=True, width="stretch")
        st.download_button("Baixar CSV da simulação", simulado.to_csv(index=False).encode("utf-8"),
                           "simulacao-interativa.csv", "text/csv")


SECOES = (
    ("cenario", secao_cenario), ("dados", secao_dados), ("testes", secao_testes),
    ("erro-tipo-1", secao_erro_tipo_1), ("poder", secao_poder), ("dados-reais", secao_dados_reais),
    ("conclusao", secao_conclusao), (ANCORA_LAB, secao_laboratorio),
)


def main() -> None:
    d = _dados()
    topo(d)
    for ancora, renderizar in SECOES:
        _secao(ancora)
        renderizar(d)


main()
