"""Análise de uma coleta: descritiva, testes, poder e o registro em Markdown (S01-09).

`python -m lab05 analisar [--piloto]` chama `analisar` e `gravar`. As regras estão em
`docs/plano-analise.md`, e os parâmetros no bloco `analise` do `config.yaml`. O resultado do piloto
**não é conclusão**: serve para conferir que o código roda, decidir o teste principal de cada
métrica (regra 5.1) e estimar o número de repetições da coleta completa.

Saídas, em `<pasta da coleta>/analise/`:

| Arquivo | Conteúdo |
|---|---|
| `descritiva.csv` | `descritiva.descrever`: uma linha por combinação e métrica |
| `teste-principal.csv` | Regra 5.1 por métrica (`testes.escolher_teste`) |
| `comparacoes.csv` | `testes.comparar` das quatro métricas (6 comparações cada) |
| `repeticoes.csv` | `poder.repeticoes_necessarias` na variabilidade bruta e nas sensibilidades |
| `curva-poder.csv` | Poder de cada comparação na grade de n (variabilidade bruta, cenário do config) |
| `diferenca-detectavel.csv` | Menor diferença com o poder do config em cada n candidato |
| `registro-analise.md` | Comando, parâmetros, hash do CSV de entrada, ambiente e as tabelas principais |

O registro é determinístico (sem data nem tempo de execução): rodar o comando de novo, no mesmo
ambiente, regrava o mesmo texto.
"""

import hashlib
import platform
from pathlib import Path

import numpy as np
import pandas as pd
import scipy

from lab05 import config, descritiva, executor, poder, testes

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
}
VARIANTES = (  # (variabilidade, cenário de Holm): a primeira é a principal
    ("bruta", None),
    ("bruta", "todas"),
    ("sem efeito de bloco", None),
)


def parametros(cfg: dict) -> dict:
    """O bloco `analise` do config, completado com os padrões."""
    return {**PADROES, **(cfg.get("analise") or {})}


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
    principal = {m: e["teste"] for m, e in escolhas.items()}
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
    return {
        "descritiva": descritiva.descrever(df, metricas),
        "teste-principal": pd.DataFrame([{"metrica": m, **e} for m, e in escolhas.items()]),
        "comparacoes": comparacoes,
        "repeticoes": pd.concat(repeticoes, ignore_index=True)[["variabilidade", *poder.COLUNAS_REPETICOES]],
        "curva-poder": curva,
        "diferenca-detectavel": poder.diferenca_detectavel(candidatos, p["poder"]),
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
    ambiente = f"Python {platform.python_version()}, numpy {np.__version__}, scipy {scipy.__version__}, pandas {pd.__version__}"
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
        "| Métrica | Shapiro-Wilk p | Assimetria | Resíduos | Teste principal | Motivo |",
        "|---|---|---|---|---|---|",
    ]
    for l in resultado["teste-principal"].itertuples():
        linhas.append(f"| `{l.metrica}` | {_num(l.shapiro_p, 4)} | {_num(l.assimetria, 2)} | {l.n_residuos} | {l.teste} | {l.motivo} |")
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
        "Variabilidade bruta, cenário de Holm do config. Diferenças simuladas: "
        + ", ".join(_pct(d) for d in p["diferencas"]) + ". \"—\": nenhuma delas basta.",
        "",
        "| Métrica | " + " | ".join(f"n = {n}" for n in p["candidatos_n"]) + " |",
        "|---|" + "---|" * len(p["candidatos_n"]),
    ]
    detectavel = resultado["diferenca-detectavel"]
    for metrica in descritiva.METRICAS:
        grupo = detectavel[detectavel["metrica"] == metrica]
        valores = dict(zip(grupo["n"], grupo["diferenca_detectavel"]))
        linhas.append(f"| `{metrica}` | " + " | ".join(_pct(valores.get(n)) for n in p["candidatos_n"]) + " |")
    return "\n".join(linhas) + "\n"


def gravar(cfg: dict, resultado: dict, comando: str) -> Path:
    """Grava os CSVs e o registro em `pasta_saida(cfg)`; devolve a pasta."""
    pasta = pasta_saida(cfg)
    pasta.mkdir(parents=True, exist_ok=True)
    for nome, tabela in resultado.items():
        tabela.to_csv(pasta / f"{nome}.csv", index=False, lineterminator="\n")
    (pasta / "registro-analise.md").write_text(registro(cfg, resultado, comando), encoding="utf-8", newline="\n")
    return pasta
