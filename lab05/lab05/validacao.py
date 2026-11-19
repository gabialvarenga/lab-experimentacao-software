"""Validação dos dados coletados e relatório de qualidade (S01-08).

Roda sem Docker, sobre o CSV do executor (`executor.caminhos`). Regras:

Erros (a coleta não está pronta para a análise):
- colunas diferentes das congeladas, `execucao_id` repetido, valor faltante ou não numérico;
- métrica negativa ou zero, `lat_p99_ms` < `lat_p50_ms`, `fim` antes de `inicio`;
- execução fora do plano ou com ordem, servidor, threads, carga ou repetição diferentes do plano;
- contagem diferente do plano: cada execução que falta é listada, com a falha registrada em
  `falhas.csv` ou como **falha não registrada**;
- versão do servidor diferente de `versao_esperada` no config;
- saída do cliente ausente ou com erros de conexão.

Avisos (não impedem, mas precisam de explicação no relatório):
- coeficiente de variação acima de 10% numa combinação (ruído da máquina, ver o plano de análise);
- execução que falhou e depois foi repetida com sucesso.
"""

import json
from dataclasses import dataclass, field
from datetime import datetime

import pandas as pd

from lab05 import executor

METRICAS = ["ops_s", "lat_p50_ms", "lat_p99_ms", "memoria_bytes"]
LIMITE_CV = 0.10
CHAVES = ["servidor", "io_threads", "carga"]


@dataclass
class Resultado:
    erros: list = field(default_factory=list)
    avisos: list = field(default_factory=list)
    dados: pd.DataFrame | None = None
    plano: int = 0
    falhas: pd.DataFrame | None = None

    @property
    def ok(self) -> bool:
        return not self.erros


def _ler_csv(caminho):
    return pd.read_csv(caminho, dtype=str, keep_default_na=False) if caminho.exists() else None


def _conferir_valores(df: pd.DataFrame, r: Resultado) -> pd.DataFrame:
    vazios = [(linha.execucao_id, coluna) for linha in df.itertuples() for coluna in executor.COLUNAS if getattr(linha, coluna) == ""]
    r.erros += [f"`{eid}`: valor faltante em `{coluna}`" for eid, coluna in vazios]
    numeros = df.copy()
    for coluna in METRICAS + ["ordem", "io_threads", "repeticao"]:
        numeros[coluna] = pd.to_numeric(df[coluna], errors="coerce")
        ruins = df.loc[numeros[coluna].isna() & (df[coluna] != ""), "execucao_id"]
        r.erros += [f"`{eid}`: `{coluna}` não numérico" for eid in ruins]
    for coluna in METRICAS:
        r.erros += [f"`{eid}`: `{coluna}` ≤ 0" for eid in numeros.loc[numeros[coluna] <= 0, "execucao_id"]]
    invertidas = numeros["lat_p99_ms"] < numeros["lat_p50_ms"]
    r.erros += [f"`{eid}`: `lat_p99_ms` menor que `lat_p50_ms`" for eid in numeros.loc[invertidas, "execucao_id"]]
    for linha in df.itertuples():
        try:
            if datetime.fromisoformat(linha.fim) < datetime.fromisoformat(linha.inicio):
                r.erros.append(f"`{linha.execucao_id}`: `fim` antes de `inicio`")
        except ValueError:
            if linha.inicio and linha.fim:
                r.erros.append(f"`{linha.execucao_id}`: data inválida em `inicio` ou `fim`")
    return numeros


def _conferir_plano(cfg: dict, df: pd.DataFrame, falhas, r: Resultado) -> None:
    plano = {ex.execucao_id: ex for ex in executor.gerar_plano(cfg)}
    r.plano = len(plano)
    repetidos = df.loc[df["execucao_id"].duplicated(), "execucao_id"].unique()
    r.erros += [f"`{eid}`: execução gravada mais de uma vez" for eid in repetidos]
    for linha in df.drop_duplicates("execucao_id").itertuples():
        ex = plano.get(linha.execucao_id)
        if ex is None:
            r.erros.append(f"`{linha.execucao_id}`: execução fora do plano")
            continue
        esperado = (str(ex.ordem), ex.servidor, str(ex.io_threads), ex.carga, str(ex.repeticao))
        if (linha.ordem, linha.servidor, linha.io_threads, linha.carga, linha.repeticao) != esperado:
            r.erros.append(f"`{linha.execucao_id}`: ordem, servidor, threads, carga ou repetição diferente do plano")
    gravadas = set(df["execucao_id"])
    falharam = {} if falhas is None else falhas.groupby("execucao_id")["etapa"].apply(list).to_dict()
    for eid in sorted(set(plano) - gravadas, key=lambda e: plano[e].ordem):
        if eid in falharam:
            r.erros.append(f"`{eid}`: falta no CSV (falhou na etapa {', '.join(falharam[eid])}; rodar de novo o executor)")
        else:
            r.erros.append(f"`{eid}`: falta no CSV e não há falha registrada")
    for eid in sorted(set(falharam) & gravadas):
        r.avisos.append(f"`{eid}`: falhou ({', '.join(falharam[eid])}) e foi repetida com sucesso")


def _conferir_versoes(cfg: dict, df: pd.DataFrame, r: Resultado) -> None:
    for servidor, s in cfg["plano"]["servidores"].items():
        esperada = str(s.get("versao_esperada", ""))
        if not esperada:
            continue
        erradas = df[(df["servidor"] == servidor) & (df["versao"] != esperada)]
        r.erros += [f"`{l.execucao_id}`: versão {l.versao}, esperada {esperada}" for l in erradas.itertuples()]


def _conferir_saidas(pasta_saidas, df: pd.DataFrame, r: Resultado) -> None:
    for eid in df["execucao_id"]:
        arquivo = pasta_saidas / f"{eid}.json"
        if not arquivo.exists():
            r.erros.append(f"`{eid}`: saída do cliente ausente ({arquivo.name})")
            continue
        try:
            totais = json.loads(arquivo.read_text(encoding="utf-8"))["ALL STATS"]["Totals"]
            erros = float(totais.get("Connection Errors", 0))
        except (ValueError, KeyError, TypeError):
            r.erros.append(f"`{eid}`: saída do cliente ilegível")
            continue
        if erros > 0:
            r.erros.append(f"`{eid}`: {erros:g} erros de conexão do cliente")


def resumo_por_combinacao(numeros: pd.DataFrame) -> pd.DataFrame:
    """n, mediana, IQR e CV (desvio-padrão amostral ÷ média) por combinação e métrica."""
    linhas = []
    for chave, grupo in numeros.groupby(CHAVES, sort=True):
        for metrica in METRICAS:
            valores = grupo[metrica].dropna()
            media = valores.mean()
            linhas.append({
                **dict(zip(CHAVES, chave)), "metrica": metrica, "n": len(valores),
                "mediana": valores.median(), "iqr": valores.quantile(0.75) - valores.quantile(0.25),
                "cv": valores.std(ddof=1) / media if len(valores) > 1 and media else float("nan"),
            })  # fmt: skip
    return pd.DataFrame(linhas)


def tempo(df: pd.DataFrame) -> dict:
    """Do primeiro `inicio` ao último `fim` e a duração média de uma execução, em minutos."""
    inicio = pd.to_datetime(df["inicio"], errors="coerce", utc=True)
    fim = pd.to_datetime(df["fim"], errors="coerce", utc=True)
    if inicio.isna().all() or fim.isna().all():
        return {"total_min": float("nan"), "por_execucao_min": float("nan")}
    return {
        "total_min": (fim.max() - inicio.min()).total_seconds() / 60,
        "por_execucao_min": (fim - inicio).dt.total_seconds().mean() / 60,
    }


def validar(cfg: dict) -> Resultado:
    """Aplica todas as regras ao CSV da coleta descrita pelo config."""
    arquivos = executor.caminhos(cfg)
    r = Resultado()
    df = _ler_csv(arquivos["csv"])
    if df is None:
        r.erros.append(f"{arquivos['csv'].name} não existe: rode o executor antes")
        return r
    if list(df.columns) != executor.COLUNAS:
        r.erros.append(f"colunas diferentes das congeladas: {list(df.columns)}")
        return r
    r.falhas = _ler_csv(arquivos["falhas"])
    numeros = _conferir_valores(df, r)
    _conferir_plano(cfg, df, r.falhas, r)
    _conferir_versoes(cfg, df, r)
    _conferir_saidas(arquivos["saidas"], df, r)
    r.dados = numeros
    resumo = resumo_por_combinacao(numeros)
    altos = resumo[resumo["cv"] > LIMITE_CV]
    r.avisos += [
        f"CV de `{l.metrica}` em {l.servidor}, io_threads {l.io_threads}, carga {l.carga}: {l.cv:.1%} (acima de {LIMITE_CV:.0%})".replace(".", ",")
        for l in altos.itertuples()
    ]
    return r


def _formatar(valor, metrica: str) -> str:
    if pd.isna(valor):
        return "—"
    if metrica == "memoria_bytes":
        return f"{valor:,.0f}".replace(",", ".")
    if metrica == "ops_s":
        return f"{valor:,.0f}".replace(",", ".")
    return f"{valor:.3f}".replace(".", ",")


def escrever_relatorio(cfg: dict, r: Resultado, caminho=None) -> str:
    """Relatório de qualidade em Markdown; devolve o texto e grava em `qualidade-<nome>.md`."""
    arquivos = executor.caminhos(cfg)
    caminho = caminho or arquivos["qualidade"]
    gravadas = 0 if r.dados is None else len(r.dados)
    falhas = 0 if r.falhas is None else len(r.falhas)
    linhas = [
        f"# Relatório de qualidade — {arquivos['csv'].name}",
        "",
        "Gerado por `python -m lab05 validar` (regras em `lab05/validacao.py`).",
        "",
        "## Resultado",
        "",
        f"- **{'Sem erros' if r.ok else f'{len(r.erros)} erro(s)'}**; {len(r.avisos)} aviso(s).",
        f"- Execuções no plano: {r.plano}; gravadas: {gravadas}; tentativas com falha em `falhas.csv`: {falhas}.",
    ]
    if r.dados is not None and gravadas:
        t = tempo(r.dados)
        linhas.append(
            f"- Tempo total (primeiro início ao último fim): {t['total_min']:.1f} min; ".replace(".", ",")
            + f"duração média de uma execução: {t['por_execucao_min']:.2f} min.".replace(".", ",", 1)
        )
    for titulo, itens in (("Erros", r.erros), ("Avisos", r.avisos)):
        linhas += ["", f"## {titulo}", ""] + ([f"- {item}" for item in itens] or ["Nenhum."])
    if r.dados is not None and gravadas:
        resumo = resumo_por_combinacao(r.dados)
        linhas += [
            "",
            "## Variabilidade por combinação",
            "",
            f"Mediana, IQR e coeficiente de variação (CV). CV acima de {LIMITE_CV:.0%} marcado com ⚠.",
            "",
            "| servidor | io_threads | carga | métrica | n | mediana | IQR | CV |",
            "|---|---|---|---|---|---|---|---|",
        ]
        for l in resumo.itertuples():
            alerta = " ⚠" if l.cv > LIMITE_CV else ""
            cv = "—" if pd.isna(l.cv) else f"{l.cv:.1%}".replace(".", ",")
            linhas.append(
                f"| {l.servidor} | {int(l.io_threads)} | {l.carga} | `{l.metrica}` | {l.n} | "
                f"{_formatar(l.mediana, l.metrica)} | {_formatar(l.iqr, l.metrica)} | {cv}{alerta} |"
            )
    texto = "\n".join(linhas) + "\n"
    caminho.parent.mkdir(parents=True, exist_ok=True)
    caminho.write_text(texto, encoding="utf-8", newline="\n")
    return texto
