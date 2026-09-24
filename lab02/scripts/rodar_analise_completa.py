from __future__ import annotations

import argparse
import importlib.metadata as metadata
import os
import re
import shutil
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Callable

RAIZ_LAB02 = Path(__file__).resolve().parent.parent
RAIZ_REPO = RAIZ_LAB02.parent
DIR_DADOS = RAIZ_LAB02 / "dados"
DIR_TRIALS = RAIZ_LAB02 / "trials"
CSV_TRIALS = DIR_DADOS / "trials.csv"
CSV_METRICAS = DIR_DADOS / "metricas-estaticas.csv"
ARQ_RESULTADOS = RAIZ_LAB02 / "relatorio" / "resultados-estatisticos.txt"

# Versões fixadas em docs/00-decisoes.md.
VERSOES_TRAVADAS = {"radon": "6.0.1", "jscpd": "5.2.0"}
PACOTES_PYTHON = ("radon", "pandas", "numpy", "scipy", "matplotlib", "seaborn")


@dataclass(frozen=True)
class Passo:
    id: str
    nome: str
    script: str  # relativo a lab02/
    args: tuple[str, ...] = ()
    salvar_saida: bool = False
    requer_node: bool = False
    dica: str = ""


@dataclass(frozen=True)
class ResultadoPasso:
    codigo: int
    saida: str
    segundos: float


# A ordem é a das dependências de dados: os dois CSVs derivados vêm antes das
# estatísticas (que os leem), e o dashboard por último.
PASSOS: tuple[Passo, ...] = (
    Passo(
        "contagem",
        "Contagem de testes por trial (RQ2)",
        "scripts/contagem_testes.py",
        ("--lote",),
    ),
    Passo(
        "metricas",
        "Métricas estáticas por trial (RQ3)",
        "scripts/metricas_estaticas.py",
        ("--lote",),
        requer_node=True,
        dica="chama o jscpd via npx em cada trial, pode levar 1-2 min",
    ),
    Passo(
        "rq1_rq2",
        "Estatística de RQ1 e RQ2",
        "analise/rq1_rq2_estatistica.py",
        salvar_saida=True,
    ),
    Passo(
        "rq3",
        "Estatística de RQ3",
        "analise/rq3_estatistica.py",
        salvar_saida=True,
    ),
    Passo("dashboard", "Dashboard de gráficos", "analise/dashboard.py"),
)


# --------------------------------------------------------------------------
# Funções puras (cobertas por tests/test_rodar_analise_completa.py)
# --------------------------------------------------------------------------

def selecionar_passos(pular_metricas: bool) -> tuple[Passo, ...]:
    if not pular_metricas:
        return PASSOS
    return tuple(p for p in PASSOS if p.id != "metricas")


def montar_comando(passo: Passo, python: str = sys.executable) -> list[str]:
    return [python, str(RAIZ_LAB02 / passo.script), *passo.args]


def normalizar_saida(texto: str, raiz_repo: Path = RAIZ_REPO) -> str:
    """Tira do texto o que muda de máquina para máquina (caminho absoluto, CRLF)."""
    texto = texto.replace("\r\n", "\n")
    for variante in (str(raiz_repo), raiz_repo.as_posix()):
        texto = texto.replace(variante, "<repo>")
    return texto.replace("\\", "/")


def avisos_de_versao(versoes: dict[str, str]) -> list[str]:
    avisos = []
    for ferramenta, esperada in VERSOES_TRAVADAS.items():
        obtida = versoes.get(ferramenta)
        if obtida is not None and obtida != esperada:
            avisos.append(
                f"{ferramenta} {obtida} instalado, mas docs/00-decisoes.md fixa "
                f"{esperada} — o resultado pode divergir do versionado."
            )
    return avisos


def formatar_arquivo_resultados(saidas: list[tuple[Passo, str]]) -> str:
    partes = [
        "# Resultados estatisticos do Lab02",
        "# Gerado por scripts/rodar_analise_completa.py — nao editar a mao.",
        "# Entrada: dados/trials.csv (bruto), dados/contagem-testes.csv e "
        "dados/metricas-estaticas.csv.",
        "",
    ]
    for passo, saida in saidas:
        partes += [f"## {passo.script}", "", saida.strip("\n"), ""]
    return "\n".join(partes)


def executar_pipeline(
    passos: tuple[Passo, ...],
    executar: Callable[[Passo], ResultadoPasso],
    imprimir: Callable[[str], None] = print,
) -> tuple[int, list[tuple[Passo, str]]]:
    """Roda os passos na ordem; para no primeiro que falhar (código 1)."""
    coletadas: list[tuple[Passo, str]] = []
    total = len(passos)
    for i, passo in enumerate(passos, start=1):
        dica = f" ({passo.dica})" if passo.dica else ""
        imprimir(f"[{i}/{total}] {passo.nome}{dica}")
        resultado = executar(passo)
        for linha in resultado.saida.splitlines():
            imprimir(f"    {linha}")
        if resultado.codigo != 0:
            imprimir(
                f"\nFALHOU no passo {i}/{total} ({passo.script}), "
                f"código de saída {resultado.codigo}. Pipeline interrompido."
            )
            return 1, coletadas
        imprimir(f"    ok ({resultado.segundos:.1f}s)\n")
        if passo.salvar_saida:
            coletadas.append((passo, resultado.saida))
    return 0, coletadas


# --------------------------------------------------------------------------
# Integração (subprocess, sistema de arquivos) — validada rodando o pipeline
# de verdade, não coberta por teste automatizado (mesma linha do cronometro.py)
# --------------------------------------------------------------------------

def executar_passo(passo: Passo, python: str = sys.executable) -> ResultadoPasso:
    env = {**os.environ, "PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"}
    inicio = time.monotonic()
    processo = subprocess.run(
        montar_comando(passo, python),
        cwd=RAIZ_REPO,
        env=env,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    saida = processo.stdout + processo.stderr
    return ResultadoPasso(processo.returncode, saida, time.monotonic() - inicio)


def versao_jscpd() -> str | None:
    try:
        resultado = subprocess.run(
            ["npx", "jscpd", "--version"],
            capture_output=True,
            text=True,
            timeout=120,
            shell=(sys.platform == "win32"),
        )
    except (OSError, subprocess.TimeoutExpired):
        return None
    achado = re.search(r"\d+\.\d+\.\d+", resultado.stdout)
    return achado.group(0) if achado else None


def versoes_ambiente(incluir_jscpd: bool) -> dict[str, str]:
    versoes = {"python": sys.version.split()[0]}
    for pacote in PACOTES_PYTHON:
        try:
            versoes[pacote] = metadata.version(pacote)
        except metadata.PackageNotFoundError:
            versoes[pacote] = "nao instalado"
    if incluir_jscpd:
        jscpd = versao_jscpd()
        if jscpd:
            versoes["jscpd"] = jscpd
    return versoes


def verificar_precondicoes(pular_metricas: bool) -> list[str]:
    erros = []
    if not CSV_TRIALS.exists():
        erros.append(f"{CSV_TRIALS} nao existe (dado bruto gravado pelo cronometro.py)")
    if not any(DIR_TRIALS.glob("*/*/solucao.py")):
        erros.append(f"nenhum solucao.py encontrado em {DIR_TRIALS}")
    if pular_metricas:
        if not CSV_METRICAS.exists():
            erros.append(f"--pular-metricas exige {CSV_METRICAS} ja existente")
    elif shutil.which("npx") is None:
        erros.append(
            "npx (Node.js) nao encontrado, necessario para o jscpd — "
            "instale o Node ou use --pular-metricas"
        )
    return erros


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="rodar_analise_completa",
        description="Reproduz a analise do Lab02 de ponta a ponta: CSVs derivados "
        "de lab02/trials/, estatisticas de RQ1-RQ3 e dashboard de graficos.",
    )
    p.add_argument(
        "--pular-metricas",
        action="store_true",
        help="nao roda metricas_estaticas.py (que exige Node/jscpd) e reaproveita "
        "o metricas-estaticas.csv existente",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = _construir_parser().parse_args(argv)

    erros = verificar_precondicoes(args.pular_metricas)
    if erros:
        for erro in erros:
            print(f"erro: {erro}", file=sys.stderr)
        return 2

    print("=" * 64)
    print("  Lab02 — pipeline de analise de ponta a ponta")
    print("=" * 64)
    versoes = versoes_ambiente(incluir_jscpd=not args.pular_metricas)
    print("  ambiente: " + ", ".join(f"{k} {v}" for k, v in versoes.items()))
    for aviso in avisos_de_versao(versoes):
        print(f"  aviso: {aviso}")
    print()

    passos = selecionar_passos(args.pular_metricas)
    codigo, saidas = executar_pipeline(passos, executar_passo)
    if codigo != 0:
        return codigo

    ARQ_RESULTADOS.parent.mkdir(parents=True, exist_ok=True)
    conteudo = normalizar_saida(formatar_arquivo_resultados(saidas))
    ARQ_RESULTADOS.write_text(conteudo, encoding="utf-8", newline="\n")

    print("=" * 64)
    print("  Pipeline concluido. Artefatos regenerados:")
    print("    lab02/dados/contagem-testes.csv")
    if not args.pular_metricas:
        print("    lab02/dados/metricas-estaticas.csv")
    print("    lab02/relatorio/resultados-estatisticos.txt")
    print("    lab02/analise/graficos/ (PNGs)")
    print()
    print("  Para conferir a reproducao (CSVs e estatisticas identicos ao versionado):")
    print("    git status --porcelain lab02/dados lab02/relatorio")
    print("=" * 64)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
