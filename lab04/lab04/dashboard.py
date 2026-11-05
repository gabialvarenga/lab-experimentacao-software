"""Montagem do dashboard em HTML com as 7 seções (S01-11, S02-11).

`montar(saida)` grava uma página HTML estática única, com o Plotly.js embutido uma vez (a página
abre sem internet). O topo tem os links do Kanban, do repositório e do próprio dashboard; depois
vêm as 7 seções do enunciado, em ordem fixa:

1. Cenário (pergunta, hipóteses e origem dos dados reais);
2. Os dados (G1);
3. Como os testes funcionam (G2, um por exemplo da S01-08);
4. a 7. Erro tipo I, Poder, Dados reais e Conclusão: "em construção" até a S02.

Os gráficos vêm de `graficos` pelo nome; se um ainda não existir ou falhar, a seção mostra um
marcador com o motivo e o resto da página é gerado (`_figura_ou_marcador`).
"""

import html
from pathlib import Path

import pandas as pd

from lab04 import calibracao, config, gerador, graficos
from lab04.descritiva import GRUPOS

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
EM_CONSTRUCAO = {
    "erro-tipo-1": "G3, erro tipo I por situação, com IC de Wilson e linha em 5% (S02-08, S02-11)",
    "poder": "G4, curvas de poder por cenário (S02-09, S02-11)",
    "dados-reais": "os dois testes aplicados aos dados reais, com estatística, p-valor e tamanho de efeito (S02-10)",
    "conclusao": "expectativa × resultado e a recomendação do grupo (S02-12)",
}

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
p.texto { line-height: 1.55; max-width: 70rem; }
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


def _pagina(cfg: dict) -> str:
    base = Path(cfg["pasta"])
    reais = pd.read_csv(base / cfg["coleta"]["saida"])
    exemplos = gerador.exemplos_calibrados(calibracao.ler(base / cfg["calibracao"]["saida"]))
    figuras = _Figuras()
    conteudo = {
        "cenario": _secao_cenario(cfg, reais),
        "dados": _secao_dados(figuras, reais, exemplos),
        "testes": _secao_testes(figuras, exemplos),
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
