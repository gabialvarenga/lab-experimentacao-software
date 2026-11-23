"""Análise de uma coleta: descritiva, testes, poder e o registro em Markdown (S01-09).

`python -m lab05 analisar [--piloto]` chama `analisar` e `gravar`. As regras estão em
`docs/plano-analise.md`, e os parâmetros no bloco `analise` do `config.yaml`. O resultado do piloto
**não é conclusão**: serve para conferir que o código roda, decidir o teste principal de cada
métrica (regra 5.1) e estimar o número de repetições da coleta completa.

Saídas, em `<pasta da coleta>/analise/`:

| Arquivo | Conteúdo |
|---|---|
| `descritiva.csv` | `descritiva.descrever`: uma linha por combinação e métrica |
| `teste-principal.csv` | Regra 5.1 por métrica (`testes.escolher_teste`) e o teste usado (`teste_usado`, `origem`) |
| `comparacoes.csv` | `testes.comparar` das quatro métricas (6 comparações cada) |
| `repeticoes.csv` | `poder.repeticoes_necessarias` na variabilidade bruta e nas sensibilidades |
| `curva-poder.csv` | Poder de cada comparação na grade de n (variabilidade bruta, cenário do config) |
| `diferenca-detectavel.csv` | Menor diferença com o poder do config em cada n candidato, por `analise`: `independente` (Mann-Whitney, variabilidade bruta) e `pareada` (Wilcoxon pareado, sem a deriva entre blocos) |
| `q3.csv` | `q3.analisar` de `ops_s` e `lat_p99_ms`: interação servidor × `io_threads`, uma linha por carga (S02-01) |
| `pareada.csv` | `pareada.comparar` das quatro métricas: Valkey × Redis dentro de cada bloco, sensibilidade (S02-01) |
| `registro-analise.md` | Comando, parâmetros, hash do CSV de entrada, ambiente e as tabelas principais |

**Decisões fixas.** O teste principal das Q1, Q2 e Q4 e o método da Q3 são decididos uma vez, no
piloto, e ficam em `analise.teste_principal` e `analise.metodo_q3` do `config.yaml`: o `analisar`
usa esses valores (`origem` = `config`) e só registra o que a regra daria nos dados analisados. Sem
essas chaves, a regra decide sobre os próprios dados (`origem` = `regra`).

A Q3 e a análise pareada seguem o adendo de 23/11/2026 do plano de análise (seção 9). O
*bootstrap* da Q3 usa um gerador próprio (`gerador(cfg, CHAVE_Q3)`), para não mudar os sorteios
das comparações, que vêm antes.

O registro é determinístico (sem data nem tempo de execução): rodar o comando de novo, no mesmo
ambiente, regrava o mesmo texto.
"""

import hashlib
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import scipy
import statsmodels

from lab05 import config, descritiva, executor, pareada, poder, q3, testes

PADROES = {
    "diferenca_relevante": testes.DIFERENCA_RELEVANTE,
    "alfa": testes.ALFA,
    "bootstrap": testes.N_BOOTSTRAP,
    "poder": poder.PODER_ALVO,
    "simulacoes": poder.N_SIMULACOES,
    "cenario_holm": "conservador",
    "grade_n": list(poder.GRADE_N),
    "candidatos_n": [30, 40, 50, 60],
    "diferencas": [0.05, 0.10, 0.15, 0.20],
    "teste_principal": None,  # sem decisão fixa: a regra 5.1 decide sobre os próprios dados
    "metodo_q3": None,
}
CHAVE_Q3 = 3  # chave do gerador do bootstrap da Q3 (Q3 = pergunta 3)
VARIANTES = (  # (variabilidade, cenário de Holm): a primeira é a principal
    ("bruta", None),
    ("bruta", "todas"),
    ("sem efeito de bloco", None),
)


def parametros(cfg: dict) -> dict:
    """O bloco `analise` do config, completado com os padrões."""
    return {**PADROES, **(cfg.get("analise") or {})}


def fixadas(p: dict, chave: str, metricas, permitidos) -> dict:
    """As decisões fixas do config (`teste_principal` ou `metodo_q3`): métrica -> teste.

    Vazio se a chave não está no config. Levanta `ValueError` se falta uma métrica ou se um valor
    não está em `permitidos`.
    """
    valores = p.get(chave)
    if valores is None:
        return {}
    faltam = [m for m in metricas if m not in valores]
    if faltam:
        raise ValueError(f"analise.{chave}: faltam as métricas {faltam}")
    invalidos = {m: t for m, t in valores.items() if t not in permitidos}
    if invalidos:
        raise ValueError(f"analise.{chave}: valores desconhecidos {invalidos}; use {' ou '.join(permitidos)}")
    return dict(valores)


def gerador(cfg: dict, chave: int) -> np.random.Generator:
    """Gerador derivado da semente do config, independente do de `config.criar_rng`."""
    return np.random.default_rng(np.random.SeedSequence(cfg["semente"], spawn_key=(chave,)))


def ler_coleta(cfg: dict) -> pd.DataFrame:
    """O CSV da coleta descrita pelo config (`executor.caminhos`), com as métricas numéricas."""
    caminho = executor.caminhos(cfg)["csv"]
    if not caminho.exists():
        raise FileNotFoundError(f"{caminho} não existe: rode o executor e o validar antes")
    df = pd.read_csv(caminho)
    descritiva.descrever(df)  # confere as colunas
    return df


def analisar(cfg: dict, df: pd.DataFrame | None = None) -> dict:
    """Roda a análise inteira e devolve as tabelas (chaves = nomes dos CSVs, sem extensão)."""
    p = parametros(cfg)
    df = ler_coleta(cfg) if df is None else df
    metricas = descritiva.METRICAS
    escolhas = {m: testes.escolher_teste(df, m, p["alfa"]) for m in metricas}
    fixos = fixadas(p, "teste_principal", metricas, tuple(testes.TESTES))
    principal = {m: fixos.get(m, e["teste"]) for m, e in escolhas.items()}
    metodos_q3 = fixadas(p, "metodo_q3", q3.METRICAS, q3.METODOS)
    rng = config.criar_rng(cfg)
    comparacoes = pd.concat(
        [testes.comparar(df, m, principal[m], rng, p["bootstrap"], p["diferenca_relevante"], p["alfa"]) for m in metricas],
        ignore_index=True,
    )
    sem_bloco = poder.remover_efeito_bloco(df, metricas)
    repeticoes, curva = [], None
    for variabilidade, cenario in VARIANTES:
        dados = df if variabilidade == "bruta" else sem_bloco
        tabela = poder.repeticoes_necessarias(
            dados, p["diferenca_relevante"], p["poder"], metricas, principal, p["grade_n"], p["simulacoes"],
            p["alfa"], cenario or p["cenario_holm"], cfg["semente"],
        )  # fmt: skip
        curva_variante = tabela.attrs.pop("curva")  # o concat do pandas compara os attrs
        curva = curva_variante if curva is None else curva
        repeticoes.append(tabela.assign(variabilidade=variabilidade))
    candidatos = pd.concat(
        [
            poder.curva_poder(df, m, p["candidatos_n"], p["diferencas"], principal[m], p["simulacoes"], p["alfa"],
                              p["cenario_holm"], cfg["semente"])  # fmt: skip
            for m in metricas
        ],
        ignore_index=True,
    )
    candidatos_pareada = pd.concat(
        [
            poder.curva_poder_pareada(sem_bloco, m, p["candidatos_n"], p["diferencas"], p["simulacoes"], p["alfa"],
                                      p["cenario_holm"], cfg["semente"])  # fmt: skip
            for m in metricas
        ],
        ignore_index=True,
    )
    detectavel = pd.concat(
        [
            poder.diferenca_detectavel(candidatos, p["poder"]).assign(analise="independente"),
            poder.diferenca_detectavel(candidatos_pareada, p["poder"]).assign(analise="pareada"),
        ],
        ignore_index=True,
    )
    rng_q3 = gerador(cfg, CHAVE_Q3)
    tabela_q3 = pd.concat(
        [q3.analisar(df, m, metodos_q3.get(m), rng_q3, p["bootstrap"], p["diferenca_relevante"], p["alfa"]) for m in q3.METRICAS],
        ignore_index=True,
    )
    refeitas = pareada.ler_refeitas(executor.caminhos(cfg)["falhas"])
    tabela_pareada = pd.concat(
        [pareada.comparar(df, m, refeitas, comparacoes, p["diferenca_relevante"], p["alfa"]) for m in metricas],
        ignore_index=True,
    )
    return {
        "descritiva": descritiva.descrever(df, metricas),
        "teste-principal": pd.DataFrame([
            {"metrica": m, **e, "teste_usado": principal[m], "origem": "config" if m in fixos else "regra"}
            for m, e in escolhas.items()
        ]),  # fmt: skip
        "comparacoes": comparacoes,
        "repeticoes": pd.concat(repeticoes, ignore_index=True)[["variabilidade", *poder.COLUNAS_REPETICOES]],
        "curva-poder": curva,
        "diferenca-detectavel": detectavel[["analise", "metrica", "n", "diferenca_detectavel", "poder_no_ponto"]],
        "q3": tabela_q3,
        "pareada": tabela_pareada,
    }


def pasta_saida(cfg: dict) -> Path:
    return executor.caminhos(cfg)["pasta"] / "analise"


def sha256(caminho) -> str:
    """SHA-256 do arquivo com os fins de linha normalizados para LF (copiado de `lab04/simulacao.py`)."""
    return hashlib.sha256(Path(caminho).read_bytes().replace(b"\r\n", b"\n")).hexdigest()


def _num(valor, casas: int = 3) -> str:
    if pd.isna(valor):
        return "—"
    return f"{valor:.{casas}f}".replace(".", ",")


def _pct(valor, casas: int = 1) -> str:
    return "—" if pd.isna(valor) else f"{100 * valor:.{casas}f}%".replace(".", ",")


def registro(cfg: dict, resultado: dict, comando: str) -> str:
    """Texto Markdown do registro da análise (determinístico)."""
    p = parametros(cfg)
    entrada = executor.caminhos(cfg)["csv"]
    desc = resultado["descritiva"]
    execucoes = int(desc.loc[desc["metrica"] == descritiva.METRICAS[0], "n"].sum())
    ambiente = f"Python {platform.python_version()}, numpy {np.__version__}, scipy {scipy.__version__}, pandas {pd.__version__}, statsmodels {statsmodels.__version__}"
    linhas = [
        f"# Registro da análise — {entrada.name}",
        "",
        "Gerado por `lab05/analise.py`; não edite à mão. Para refazer, rode o comando abaixo.",
        "",
        "| Item | Valor |",
        "|---|---|",
        f"| Comando (a partir de `lab05/`) | `{comando}` |",
        f"| SHA-256 de `{entrada.name}` (fins de linha LF) | `{sha256(entrada)}` |",
        f"| Execuções | {execucoes} |",
        f"| Semente | {cfg['semente']} |",
        f"| Diferença relevante | {_pct(p['diferenca_relevante'], 0)} (razão de medianas fora de [{_num(1 - p['diferenca_relevante'], 2)}; {_num(1 + p['diferenca_relevante'], 2)}]) |",
        f"| α | {_num(p['alfa'], 2)}, bicaudal, Holm dentro de cada métrica |",
        f"| *Bootstrap* | {p['bootstrap']} reamostragens |",
        f"| Poder | {_pct(p['poder'], 0)}, {p['simulacoes']} simulações por ponto, cenário de Holm `{p['cenario_holm']}` |",
        f"| Ambiente | {ambiente} |",
        "",
        "## Teste principal por métrica (regra 5.1)",
        "",
        "\"Regra\": o que a regra dá nestes dados. \"Usado\": o teste das comparações (`config`: decisão fixa do piloto).",
        "",
        "| Métrica | Shapiro-Wilk p | Assimetria | Resíduos | Regra | Motivo | Usado |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in resultado["teste-principal"].itertuples():
        linhas.append(f"| `{l.metrica}` | {_num(l.shapiro_p, 4)} | {_num(l.assimetria, 2)} | {l.n_residuos} | {l.teste} | "
                      f"{l.motivo} | {l.teste_usado} ({l.origem}) |")  # fmt: skip
    linhas += [
        "",
        "## Comparações Valkey × Redis",
        "",
        "Só para conferir que o código roda: com 5 repetições, o resultado **não é conclusão**.",
        "",
        "| Métrica | io_threads | Carga | Razão de medianas | IC de 95% | p principal | p Holm | p sensibilidade | Discordam | Situação |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]
    for l in resultado["comparacoes"].itertuples():
        linhas.append(
            f"| `{l.metrica}` | {l.io_threads} | {l.carga} | {_num(l.razao_medianas)} | [{_num(l.ic_inf)}; {_num(l.ic_sup)}] | "
            f"{_num(l.p_principal, 4)} | {_num(l.p_holm, 4)} | {_num(l.p_sensibilidade, 4)} | {'sim' if l.testes_discordam else 'não'} | {l.situacao} |"
        )
    linhas += [
        "",
        f"## Repetições necessárias para {_pct(p['diferenca_relevante'], 0)} com {_pct(p['poder'], 0)} de poder",
        "",
        "Poder da comparação limitante (a de menor poder entre as 6). Grade de n: "
        + ", ".join(str(n) for n in p["grade_n"]) + ".",
        "",
        "| Variabilidade | Cenário de Holm | Métrica | Teste | σ de log máximo | n necessário | Poder no n | Limitante |",
        "|---|---|---|---|---|---|---|---|",
    ]
    for l in resultado["repeticoes"].itertuples():
        n = f"> {max(p['grade_n'])}" if l.acima_da_grade else str(int(l.n_necessario))
        linhas.append(
            f"| {l.variabilidade} | {l.cenario} | `{l.metrica}` | {l.teste} | {_num(l.sigma_log_max)} | {n} | {_pct(l.poder_no_n)} | {l.limitante} |"
        )
    linhas += [
        "",
        f"## Diferença detectável com {_pct(p['poder'], 0)} de poder nos n candidatos",
        "",
        "Cenário de Holm do config. Independente: Mann-Whitney com a variabilidade bruta. Pareada: Wilcoxon "
        "pareado com a variabilidade sem a deriva entre blocos (n = pares). Diferenças simuladas: "
        + ", ".join(_pct(d) for d in p["diferencas"]) + ". \"—\": nenhuma delas basta.",
        "",
        "| Métrica | Análise | " + " | ".join(f"n = {n}" for n in p["candidatos_n"]) + " |",
        "|---|---|" + "---|" * len(p["candidatos_n"]),
    ]
    detectavel = resultado["diferenca-detectavel"]
    for metrica in descritiva.METRICAS:
        for tipo in ("independente", "pareada"):
            grupo = detectavel[(detectavel["metrica"] == metrica) & (detectavel["analise"] == tipo)]
            valores = dict(zip(grupo["n"], grupo["diferenca_detectavel"]))
            linhas.append(f"| `{metrica}` | {tipo} | " + " | ".join(_pct(valores.get(n)) for n in p["candidatos_n"]) + " |")
    linhas += _registro_q3(resultado["q3"]) + _registro_pareada(resultado["pareada"])
    return "\n".join(linhas) + "\n"


def _registro_q3(tabela: pd.DataFrame) -> list:
    linhas = [
        "",
        "## Q3: interação servidor × io_threads",
        "",
        "Método principal pela regra 5.1 aplicada aos resíduos do modelo de dois fatores no log, juntados por métrica; "
        "sensibilidade: ANOVA no log com o bloco (repetição). Holm entre as 3 cargas de cada métrica. "
        "R = razão das razões, (valkey 4 ÷ valkey 1) ÷ (redis 4 ÷ redis 1). Só para conferir que o código roda.",
        "",
        "| Métrica | Shapiro-Wilk p | Assimetria | Levene p (menor) | Regra | Motivo | Usado |",
        "|---|---|---|---|---|---|---|",
    ]
    for l in tabela.drop_duplicates("metrica").itertuples():
        linhas.append(f"| `{l.metrica}` | {_num(l.regra_shapiro_p, 4)} | {_num(l.regra_assimetria, 2)} | "
                      f"{_num(l.regra_levene_p_min, 4)} | {l.regra_metodo} | {l.regra_motivo} | {l.teste} |")  # fmt: skip
    linhas += [
        "",
        "| Métrica | Carga | Método | R | IC de 95% | p interação | p Holm | η² parcial | p com bloco | Discordam | Situação |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for l in tabela.itertuples():
        linhas.append(
            f"| `{l.metrica}` | {l.carga} | {l.teste} | {_num(l.razao_das_razoes)} | [{_num(l.ic_inf)}; {_num(l.ic_sup)}] | "
            f"{_num(l.p_interacao, 4)} | {_num(l.p_holm, 4)} | {_num(l.eta2_parcial)} | {_num(l.p_sensibilidade, 4)} | "
            f"{'sim' if l.testes_discordam else 'não'} | {l.situacao} |"
        )
    return linhas


def _registro_pareada(tabela: pd.DataFrame) -> list:
    linhas = [
        "",
        "## Análise pareada por bloco (sensibilidade)",
        "",
        "Valkey ÷ Redis dentro de cada repetição; Wilcoxon pareado no log das razões, Hodges-Lehmann com IC exato, "
        "Holm entre as 6 comparações de cada métrica. Pares com execução refeita (em `falhas.csv`) saem. "
        "\"Principal\" é a situação do Mann-Whitney (comparações acima).",
        "",
        "| Métrica | io_threads | Carga | Pares | Excluídos | Razão HL | IC | Cobertura | p Wilcoxon | p Holm | Situação | Principal |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]
    for l in tabela.itertuples():
        linhas.append(
            f"| `{l.metrica}` | {l.io_threads} | {l.carga} | {l.n_pares} | {l.n_excluidos} | {_num(l.razao_hl)} | "
            f"[{_num(l.ic_inf)}; {_num(l.ic_sup)}] | {_pct(l.cobertura_ic, 2)} | {_num(l.p_wilcoxon, 4)} | {_num(l.p_holm, 4)} | "
            f"{l.situacao} | {l.situacao_principal} |"
        )
    return linhas


def gravar(cfg: dict, resultado: dict, comando: str) -> Path:
    """Grava os CSVs e o registro em `pasta_saida(cfg)`; devolve a pasta."""
    pasta = pasta_saida(cfg)
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, tabela in resultado.items():
        tabela.to_csv(pasta / f"{nome}.csv", index=False, lineterminator="\n")
    (pasta / "registro-analise.md").write_text(registro(cfg, resultado, comando), encoding="utf-8", newline="\n")
    return pasta
