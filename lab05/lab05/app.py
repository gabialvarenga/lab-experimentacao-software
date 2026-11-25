"""Dashboard interativo do Lab05 (Streamlit), numa página única (S02-09).

Rode a partir da pasta `lab05/`:

    python -m lab05 app            # ou: python -m streamlit run lab05/app.py

Cinco seções, de método e de resultados: (1) o software e a pergunta, (2) como medimos, (3) dados e
deriva (G1 e G2), (4) resultados das Q1, Q2 e Q4 (G3 e tabela) e (5) a Q3 (G4 e tabela). Impacto e
conclusões entram na S03.

O app **só lê CSVs** já gravados pelo `executar` e pelo `analisar`: abrir a página nunca roda o
*benchmark*. Se um CSV falta, a seção que depende dele mostra um aviso com o comando que o gera, e as
outras seguem funcionando. As figuras são as de `lab05/graficos.py` (as mesmas do `python -m lab05
graficos`), e os textos que citam números os leem das tabelas, então não ficam defasados se a análise
for refeita.

As funções que não dependem do Streamlit (carregar os CSVs, montar as tabelas e as frases) ficam no
topo e são testadas sem interface; a página só é montada em `main`, chamada quando o Streamlit roda o
arquivo.
"""

import sys
from html import escape
from pathlib import Path

# `streamlit run lab05/app.py` põe a pasta do script no caminho, e não a pasta `lab05/` (o pacote):
# sem isto, `from lab05 import ...` falharia fora do `python -m`.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import numpy as np  # noqa: E402
import pandas as pd  # noqa: E402
import streamlit as st  # noqa: E402

from lab05 import analise, config, executor, graficos  # noqa: E402

TITULO = "Lab05: Redis × Valkey"
INTEGRANTES = ("Brenda Evers", "Carlos José Gomes Batista Figueiredo", "Gabriela Alvarenga Cardoso")
LINK_KANBAN = "https://github.com/users/gabialvarenga/projects/9"
LINK_REPOSITORIO = "https://github.com/gabialvarenga/lab-experimentacao-software/tree/main/lab05"
LINK_CENARIO = LINK_REPOSITORIO + "/docs/cenario.md"
LINK_PROTOCOLO = LINK_REPOSITORIO + "/docs/protocolo-execucao.md"
LINK_PLANO = LINK_REPOSITORIO + "/docs/plano-analise.md"
LINK_RESULTADOS = LINK_REPOSITORIO + "/docs/resultados.md"
LINK_AMEACAS = LINK_REPOSITORIO + "/docs/ameacas-validade.md"

SECOES = (
    ("software", "1. O software e a pergunta"),
    ("medicao", "2. Como medimos"),
    ("dados", "3. Dados e deriva"),
    ("q1-q2-q4", "4. Resultados das Q1, Q2 e Q4"),
    ("q3", "5. A diferença depende das threads? (Q3)"),
)
TITULOS = dict(SECOES)

# Tabelas lidas de `<pasta da coleta>/analise/`; ausente = None
TABELAS = {
    "comparacoes": "comparacoes.csv",
    "q3": "q3.csv",
    "q3_detectavel": "q3-diferenca-detectavel.csv",
}
COMANDO_COLETA = "python -m lab05 executar"
COMANDO_ANALISE = "python -m lab05 analisar"

# As perguntas da seção 4: rótulo -> métrica
PERGUNTAS = {
    "Q1: vazão": "ops_s",
    "Q2: latência p99": "lat_p99_ms",
    "Q2 (descritiva): latência p50": "lat_p50_ms",
    "Q4: memória": "memoria_bytes",
}
SITUACAO_CURTA = {"diferença relevante": "relevante", "diferença pequena demais": "pequena demais",
                  "equivalência prática": "equivalência prática", "inconclusivo": "inconclusivo"}


# --- carregar e formatar (sem Streamlit) ---


def carregar(caminho_config=config.CONFIG_PADRAO) -> dict:
    """Os CSVs da coleta descrita pelo config: `{"cfg", "df", **TABELAS}`; `None` no que não existe.

    `df` é o CSV bruto (`execucoes.csv`); as demais chaves são as tabelas do `analisar`. Nenhum
    arquivo ausente levanta erro: a seção que precisa dele mostra o aviso (`aviso`).
    """
    cfg = config.carregar(caminho_config)
    pasta_analise = analise.pasta_saida(cfg)
    dados = {"cfg": cfg, "df": None}
    csv = executor.caminhos(cfg)["csv"]
    if csv.exists():
        dados["df"] = pd.read_csv(csv)
    for chave, arquivo in TABELAS.items():
        caminho = pasta_analise / arquivo
        dados[chave] = pd.read_csv(caminho) if caminho.exists() else None
    return dados


def aviso(dados: dict, *necessarios) -> str | None:
    """Texto do aviso se falta alguma das tabelas `necessarios` (chaves de `dados`); senão `None`."""
    faltam = [n for n in necessarios if dados.get(n) is None]
    if not faltam:
        return None
    arquivos = ["execucoes.csv" if n == "df" else TABELAS[n] for n in faltam]
    comando = COMANDO_COLETA if "df" in faltam else COMANDO_ANALISE
    return f"Faltam arquivos desta seção: {', '.join(arquivos)}. Gere-os com `{comando}` (a partir de `lab05/`)."


def _num(valor, casas: int = 3) -> str:
    return "—" if pd.isna(valor) else f"{valor:.{casas}f}".replace(".", ",")


def _pct(valor, casas: int = 1) -> str:
    return "—" if pd.isna(valor) else _num(100 * valor, casas) + "%"


def _p(valor) -> str:
    """p-valor curto: `< 0,0001` abaixo de 1e-4, senão com 4 casas."""
    if pd.isna(valor):
        return "—"
    return "< 0,0001" if valor < 1e-4 else _num(valor, 4)


def _valor(valor, metrica: str) -> str:
    """Mediana de uma métrica para a tabela: vazão em ops/s com milhar, latência em ms, memória em MiB."""
    if metrica == "ops_s":
        return f"{valor:,.0f}".replace(",", ".")
    if metrica == "memoria_bytes":
        return _num(valor * graficos.ESCALA["memoria_bytes"], 2) + " MiB"
    return _num(valor, 3) + " ms"


def _ordenar(tabela: pd.DataFrame) -> pd.DataFrame:
    """Threads crescentes e cargas na ordem set, get, misto."""
    ordem = tabela["carga"].map({c: i for i, c in enumerate(graficos.CARGAS)})
    return tabela.assign(_o=ordem).sort_values(["io_threads", "_o"] if "io_threads" in tabela else ["_o"]).drop(columns="_o")


def tabela_comparacoes(comparacoes: pd.DataFrame, metrica: str) -> pd.DataFrame:
    """As 6 comparações Valkey × Redis de uma métrica, prontas para mostrar (texto já formatado)."""
    t = _ordenar(comparacoes[comparacoes["metrica"] == metrica])
    return pd.DataFrame({
        "Threads de E/S": t["io_threads"].astype(int).to_numpy(),
        "Carga": t["carga"].map(graficos.NOMES_CARGA).to_numpy(),
        "Mediana Redis": [_valor(v, metrica) for v in t["mediana_redis"]],
        "Mediana Valkey": [_valor(v, metrica) for v in t["mediana_valkey"]],
        "Valkey ÷ Redis": [_num(v) for v in t["razao_medianas"]],
        "IC de 95%": [f"[{_num(a)}; {_num(b)}]" for a, b in zip(t["ic_inf"], t["ic_sup"])],
        "p Holm": [_p(v) for v in t["p_holm"]],
        "Situação": t["situacao"].to_numpy(),
    })


def tabela_q3(q3: pd.DataFrame, detectavel: pd.DataFrame | None = None) -> pd.DataFrame:
    """A Q3 por métrica e carga: o ganho de cada servidor com 4 threads, R com IC, p Holm e situação.

    Com `detectavel` (`q3-diferenca-detectavel.csv`), acrescenta a menor interação detectável.
    """
    t = q3.copy()
    t["_m"] = t["metrica"].map({m: i for i, m in enumerate(graficos.METRICAS_Q3)})
    t["_c"] = t["carga"].map({c: i for i, c in enumerate(graficos.CARGAS)})
    t = t.sort_values(["_m", "_c"])
    saida = pd.DataFrame({
        "Métrica": t["metrica"].map(graficos.NOMES_METRICA).to_numpy(),
        "Carga": t["carga"].map(graficos.NOMES_CARGA).to_numpy(),
        "Valkey 4 ÷ 1 thread": [_num(v, 2) for v in t["razao_valkey"]],
        "Redis 4 ÷ 1 thread": [_num(v, 2) for v in t["razao_redis"]],
        "R (razão das razões)": [_num(v) for v in t["razao_das_razoes"]],
        "IC de 95%": [f"[{_num(a)}; {_num(b)}]" for a, b in zip(t["ic_inf"], t["ic_sup"])],
        "p Holm": [_p(v) for v in t["p_holm"]],
        "Situação": t["situacao"].to_numpy(),
    })
    if detectavel is not None:
        chaves = detectavel.set_index(["metrica", "carga"])["diferenca_detectavel"]
        saida["Interação detectável (R − 1)"] = [_pct(chaves.get((m, c), np.nan)) for m, c in zip(t["metrica"], t["carga"])]
    return saida


def frase_comparacoes(comparacoes: pd.DataFrame, metrica: str) -> str:
    """Uma frase com a faixa da razão Valkey ÷ Redis e a situação, para cada nível de threads."""
    t = comparacoes[comparacoes["metrica"] == metrica]
    partes = []
    for threads, g in t.groupby("io_threads", sort=True):
        situacoes = sorted({SITUACAO_CURTA.get(s, s) for s in g["situacao"]})
        faixa = (f"{_num(g['razao_medianas'].min())}×" if np.isclose(g["razao_medianas"].min(), g["razao_medianas"].max(), atol=5e-4)
                 else f"{_num(g['razao_medianas'].min())}× a {_num(g['razao_medianas'].max())}×")
        partes.append(f"com {int(threads)} thread{'s' if threads > 1 else ''} de E/S, Valkey ÷ Redis fica em {faixa} ({', '.join(situacoes)})")
    texto = "; ".join(partes)
    return texto[:1].upper() + texto[1:] + "." if texto else ""


def frase_q3(q3: pd.DataFrame, detectavel: pd.DataFrame | None) -> str:
    """Uma frase com a faixa de R em cada métrica da Q3, a situação e a interação detectável."""
    partes = []
    for metrica in graficos.METRICAS_Q3:
        g = q3[q3["metrica"] == metrica]
        if g.empty:
            continue
        partes.append(f"{graficos.NOMES_METRICA[metrica].lower()}: R de {_num(g['razao_das_razoes'].min(), 2)} a "
                      f"{_num(g['razao_das_razoes'].max(), 2)}")
    situacoes = sorted({SITUACAO_CURTA.get(s, s) for s in q3["situacao"]})
    texto = "; ".join(partes)
    texto = texto[:1].upper() + texto[1:] + f" ({', '.join(situacoes)} nas {len(q3)} linhas)."
    if detectavel is not None and detectavel["diferenca_detectavel"].notna().any():
        texto += (f" Com {int(detectavel['n_por_celula'].min())} repetições por célula, a interação detectável (80% de poder) "
                  f"fica entre {_pct(detectavel['diferenca_detectavel'].min())} e {_pct(detectavel['diferenca_detectavel'].max())}.")
    return texto


def frase_dados(df: pd.DataFrame) -> str:
    """Uma frase com o CV mediano e a deriva entre blocos da vazão."""
    cv = df.groupby(graficos.CHAVES)["ops_s"].agg(lambda s: s.std() / s.mean())
    rel = graficos.relativos(df, "ops_s").groupby(df["repeticao"]).median()
    return (f"O CV mediano da vazão é de {_pct(cv.median())} (máximo {_pct(cv.max())}), e a mediana relativa por bloco "
            f"fica entre {_num(rel.min())} e {_num(rel.max())}: não há deriva da máquina na coleta.")


# --- peças de interface ---

CSS = """
<style>
div.lab05 table { border-collapse: collapse; margin: .6rem 0; font-size: .95rem; }
div.lab05 th, div.lab05 td { border: 1px solid rgba(128,128,128,.4); padding: .4rem .7rem; text-align: left; vertical-align: top; }
div.lab05 th { background: rgba(128,128,128,.12); }
div.leitura { border-left: 4px solid #2e86ab; background: rgba(46,134,171,.07); padding: .6rem 1rem;
              border-radius: 4px; line-height: 1.55; margin: .4rem 0 1rem; }
div.topo { background: #1f2430; color: #fff; padding: 1rem 1.4rem; border-radius: 8px; margin-bottom: .6rem; }
div.topo h1 { color: #fff; font-size: 1.6rem; margin: 0 0 .3rem; padding: 0; }
div.topo p { margin: .15rem 0; opacity: .9; }
div.topo a { color: #fff; font-weight: 600; margin-right: 1.2rem; }
div.indice a { margin-right: 1rem; }
</style>
"""


def _grafico(figura) -> None:
    st.plotly_chart(figura, theme=None, width="stretch")


def _leitura(texto: str, rotulo: str = "Leitura do grupo") -> None:
    """O texto curto do grupo junto de cada seção, sempre visível."""
    st.markdown(f'<div class="leitura"><strong>{escape(rotulo)}.</strong> {escape(texto)}</div>', unsafe_allow_html=True)


def _como_ler(texto: str) -> None:
    with st.expander("Como ler este gráfico"):
        st.write(texto)


def _secao(ancora: str) -> None:
    st.divider()
    st.header(TITULOS[ancora], anchor=ancora)


def _aviso(dados: dict, *necessarios) -> bool:
    """Mostra o aviso e devolve `True` se falta algum dos arquivos (a seção para por aí, sem erro)."""
    texto = aviso(dados, *necessarios)
    if texto:
        st.warning(texto)
    return texto is not None


def topo(dados: dict) -> None:
    """Título, integrantes, links e índice."""
    st.markdown(CSS, unsafe_allow_html=True)
    st.markdown(
        f"""<div class="topo"><h1>{escape(TITULO)}</h1>
<p>{escape(" · ".join(INTEGRANTES))}</p>
<p><a href="{LINK_KANBAN}">Kanban (GitHub Projects)</a><a href="{LINK_REPOSITORIO}">Repositório</a></p></div>""",
        unsafe_allow_html=True,
    )
    indice = "".join(f'<a href="#{ancora}">{escape(titulo)}</a>' for ancora, titulo in SECOES)
    st.markdown(f'<div class="indice">{indice}</div>', unsafe_allow_html=True)
    st.caption(
        "Este painel só lê os CSVs já gravados: abrir a página nunca roda o benchmark. "
        "Impacto e conclusões ficam para a próxima etapa."
    )


def secao_software() -> None:
    _secao("software")
    st.markdown(
        "O Lab05 compara o **Redis 8.10.3** e o **Valkey 9.1.3**, duas imagens oficiais do Docker Hub. O Valkey nasceu em "
        "março de 2024 como um *fork* do Redis 7.2, criado pela Linux Foundation depois que o Redis mudou de licença, e os "
        "dois evoluem de forma independente desde então."
    )
    st.markdown("**Pergunta principal:** migrar do Redis para o Valkey muda o desempenho de um cache?")
    st.markdown(
        '<div class="lab05"><table><tr><th>Pergunta</th><th>Texto</th><th>Métrica</th></tr>'
        "<tr><td>Q1</td><td>A vazão difere entre os dois servidores?</td><td>ops/s</td></tr>"
        "<tr><td>Q2</td><td>A latência de cauda difere?</td><td>p99 (o p50 é descritivo)</td></tr>"
        "<tr><td>Q3</td><td>A diferença depende do uso de <em>threads</em> de E/S?</td><td>interação servidor × threads, em ops/s e p99</td></tr>"
        "<tr><td>Q4</td><td>O uso de memória para o mesmo conjunto de chaves difere?</td><td>memória usada</td></tr></table></div>",
        unsafe_allow_html=True,
    )
    st.caption(f"Hipóteses e expectativa do grupo, escritas antes da coleta: [cenário]({LINK_CENARIO}).")


def secao_medicao(dados: dict) -> None:
    _secao("medicao")
    df = dados["df"]
    plano = (f"{len(df)} execuções ({df['repeticao'].nunique()} repetições de cada uma das "
             f"{df.groupby(graficos.CHAVES).ngroups} combinações)") if df is not None else "480 execuções (40 repetições de cada uma das 12 combinações)"
    st.markdown(
        "Um benchmark local: o servidor roda num contêiner Docker (sobre WSL2, num notebook) e o `memtier_benchmark` 2.6.1, "
        "o mesmo cliente para os dois, gera a carga. Cada execução sobe um contêiner novo, aquece 10 s, mede 30 s e lê a "
        "memória; o cliente usa 4 threads × 12 clientes, valores de 100 bytes e 100.000 chaves."
    )
    st.markdown(
        f"A coleta tem {plano}: 2 servidores × 1 ou 4 threads de E/S × 3 cargas (só SET, só GET e 80% GET com 20% SET). "
        "Cada repetição é um bloco com as 12 combinações em ordem sorteada (semente 42), para que qualquer mudança lenta "
        "da máquina atinja todas por igual."
    )
    st.caption(f"Detalhes: [protocolo de execução]({LINK_PROTOCOLO}), [plano de análise]({LINK_PLANO}) e "
               f"[ameaças à validade]({LINK_AMEACAS}).")


@st.fragment
def secao_dados(dados: dict) -> None:
    _secao("dados")
    if _aviso(dados, "df", "comparacoes"):
        return
    df, comparacoes = dados["df"], dados["comparacoes"]
    colunas = st.columns(3)
    for coluna, (rotulo, valor, detalhe) in zip(colunas * 2, graficos.destaques(df, comparacoes)):
        coluna.metric(rotulo, valor, detalhe, delta_color="off", border=True)
    _leitura(frase_dados(df))
    metricas = st.multiselect("Métricas do G1", graficos.METRICAS, default=graficos.METRICAS,
                              format_func=lambda m: graficos.NOMES_METRICA[m], key="g1_metricas")
    if metricas:
        _grafico(graficos.g1(df, metricas))
    else:
        st.info("Escolha ao menos uma métrica.")
    _como_ler(graficos.TEXTOS["g1"])
    _grafico(graficos.g2(df))
    _como_ler(graficos.TEXTOS["g2"])


@st.fragment
def secao_q1_q2_q4(dados: dict) -> None:
    _secao("q1-q2-q4")
    if _aviso(dados, "comparacoes"):
        return
    comparacoes = dados["comparacoes"]
    rotulo = st.segmented_control("Pergunta", list(PERGUNTAS), default=next(iter(PERGUNTAS)), key="pergunta") or next(iter(PERGUNTAS))
    metrica = PERGUNTAS[rotulo]
    _leitura(frase_comparacoes(comparacoes, metrica))
    _grafico(graficos.g3(comparacoes, (metrica,)))
    _como_ler(graficos.TEXTOS["g3"])
    st.dataframe(tabela_comparacoes(comparacoes, metrica), hide_index=True, width="stretch")
    st.caption(
        "Razão e IC de 95% sobre as medianas das 40 execuções de cada lado (*bootstrap*); teste principal Mann-Whitney, com "
        "Holm entre as 6 comparações de cada pergunta. Diferença relevante: IC inteiro fora de [0,95; 1,05]. "
        f"Tabelas completas e interpretação: [resultados]({LINK_RESULTADOS})."
    )


@st.fragment
def secao_q3(dados: dict) -> None:
    _secao("q3")
    if _aviso(dados, "df", "q3"):
        return
    df, q3 = dados["df"], dados["q3"]
    _leitura(frase_q3(q3, dados["q3_detectavel"]))
    _grafico(graficos.g4(df))
    _como_ler(graficos.TEXTOS["g4"])
    st.dataframe(tabela_q3(q3, dados["q3_detectavel"]), hide_index=True, width="stretch")
    st.caption(
        "R = (Valkey 4 ÷ Valkey 1) ÷ (Redis 4 ÷ Redis 1), nas medianas; R = 1 é sem interação, e a interação é relevante se "
        "R sai de [0,95; 1,05]. Teste: ART-ANOVA no log, por carga, com Holm entre as 3 cargas."
    )


@st.cache_data(show_spinner=False, ttl=60)
def _dados(caminho_config: str) -> dict:
    return carregar(caminho_config)


def main() -> None:
    st.set_page_config(page_title=TITULO, page_icon="📊", layout="wide")
    dados = _dados(str(config.CONFIG_PADRAO))
    topo(dados)
    secao_software()
    secao_medicao(dados)
    secao_dados(dados)
    secao_q1_q2_q4(dados)
    secao_q3(dados)


if __name__ == "__main__":
    main()
