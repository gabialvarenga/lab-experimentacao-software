from __future__ import annotations

import argparse
import json
import subprocess
import sys
import tempfile
from pathlib import Path
from typing import Literal

TRATAMENTOS_SUFIXO = ("com-ia", "sem-ia")

COLUNAS = [
    "integrante",
    "kata",
    "tratamento",
    "loc",
    "cc_media",
    "cc_max",
    "mi",
    "duplicacao_pct",
]

RAIZ_LAB02 = Path(__file__).resolve().parent.parent
DIR_TRIALS = RAIZ_LAB02 / "trials"
CSV_METRICAS = RAIZ_LAB02 / "dados" / "metricas-estaticas.csv"

MIN_LINES_PADRAO = 3
MIN_TOKENS_PADRAO = 20


# --------------------------------------------------------------------------
# Funções puras (cobertas por tests/test_metricas_estaticas.py)
# --------------------------------------------------------------------------

def extrair_loc(raw: dict) -> int:
    """LOC = linhas de código-fonte, campo ``sloc`` de ``radon raw -j``."""
    return raw["sloc"]


def calcular_complexidade(blocos: list[dict]) -> tuple[float, int]:
    """Média e máximo de complexidade ciclomática entre funções/métodos.

    Blocos do tipo ``class`` são excluídos: o Radon já reporta a
    complexidade de cada método da classe separadamente, então incluir a
    classe também contaria a mesma complexidade duas vezes.
    """
    valores = [b["complexity"] for b in blocos if b.get("type") != "class"]
    if not valores:
        return 0.0, 0
    return sum(valores) / len(valores), max(valores)


def extrair_mi(saida_mi: dict) -> float:
    """Índice de manutenibilidade, campo ``mi`` de ``radon mi -j``."""
    return saida_mi["mi"]


def extrair_duplicacao_pct(saida_jscpd: dict) -> float:
    """Percentual de linhas duplicadas, do relatório JSON do jscpd."""
    return saida_jscpd["statistics"]["total"]["percentage"]


def extrair_kata_e_tratamento(nome_pasta: str) -> tuple[str, str]:
    """Separa ``<kata>-<tratamento>`` pelo sufixo de tratamento.

    Não corta no primeiro/último hífen: o id do kata também pode conter
    hífen (ex.: ``kata-dois-sem-ia`` -> kata ``kata-dois``, tratamento
    ``sem-ia``).
    """
    for tratamento in TRATAMENTOS_SUFIXO:
        sufixo = f"-{tratamento}"
        if nome_pasta.endswith(sufixo):
            return nome_pasta[: -len(sufixo)], tratamento
    raise ValueError(
        f"pasta de trial sem sufixo de tratamento reconhecido: {nome_pasta!r}"
    )


def montar_linha_metricas(
    *,
    integrante: str,
    kata: str,
    tratamento: str,
    loc: int,
    cc_media: float,
    cc_max: int,
    mi: float,
    duplicacao_pct: float,
) -> dict:
    """Monta o dicionário de uma linha de ``metricas-estaticas.csv``."""
    return {
        "integrante": integrante,
        "kata": kata,
        "tratamento": tratamento,
        "loc": loc,
        "cc_media": round(cc_media, 2),
        "cc_max": cc_max,
        "mi": round(mi, 2),
        "duplicacao_pct": round(duplicacao_pct, 2),
    }


# --------------------------------------------------------------------------
# Integração (subprocess) — validadas manualmente contra arquivos reais,
# não cobertas por teste automatizado (mesma linha do cronometro.py)
# --------------------------------------------------------------------------

def rodar_radon(subcomando: Literal["cc", "raw", "mi"], caminho: Path):
    resultado = subprocess.run(
        [sys.executable, "-m", "radon", subcomando, str(caminho), "-j"],
        capture_output=True,
        text=True,
        check=True,
    )
    saida = json.loads(resultado.stdout)
    valor = saida[str(caminho)]
    # Arquivo com erro de sintaxe: o radon sai com exit code 0 mesmo assim,
    # só troca o valor esperado por {"error": "..."} — não é um
    # CalledProcessError, precisa ser detectado à parte.
    if isinstance(valor, dict) and "error" in valor:
        raise RuntimeError(f"radon {subcomando} falhou em {caminho}: {valor['error']}")
    return valor


def rodar_jscpd(
    caminho: Path,
    min_lines: int = MIN_LINES_PADRAO,
    min_tokens: int = MIN_TOKENS_PADRAO,
) -> dict:
    with tempfile.TemporaryDirectory() as tmp:
        subprocess.run(
            [
                "npx", "jscpd", str(caminho),
                "--reporters", "json",
                "--output", tmp,
                "--silent",
                "--min-lines", str(min_lines),
                "--min-tokens", str(min_tokens),
            ],
            capture_output=True,
            text=True,
            check=True,
            shell=(sys.platform == "win32"),
        )
        relatorio = Path(tmp) / "jscpd-report.json"
        return json.loads(relatorio.read_text(encoding="utf-8"))


def coletar_metricas_trial(caminho_solucao: Path) -> dict | None:
    """Roda radon + jscpd sobre um ``solucao.py`` e monta a linha de métricas.

    Devolve ``None`` (em vez de propagar a exceção) quando o arquivo não é
    Python válido ou uma das ferramentas falha — caso esperado para trials
    censurados com código incompleto/quebrado, que não podem derrubar o
    lote inteiro.
    """
    pasta_trial = caminho_solucao.parent
    integrante = pasta_trial.parent.name
    kata, tratamento = extrair_kata_e_tratamento(pasta_trial.name)

    try:
        blocos_cc = rodar_radon("cc", caminho_solucao)
        saida_raw = rodar_radon("raw", caminho_solucao)
        saida_mi = rodar_radon("mi", caminho_solucao)
        saida_jscpd = rodar_jscpd(caminho_solucao)
    except (
        subprocess.CalledProcessError,
        json.JSONDecodeError,
        KeyError,
        RuntimeError,
    ) as erro:
        print(f"  aviso: falha ao medir {pasta_trial}: {erro}", file=sys.stderr)
        return None

    cc_media, cc_max = calcular_complexidade(blocos_cc)
    return montar_linha_metricas(
        integrante=integrante,
        kata=kata,
        tratamento=tratamento,
        loc=extrair_loc(saida_raw),
        cc_media=cc_media,
        cc_max=cc_max,
        mi=extrair_mi(saida_mi),
        duplicacao_pct=extrair_duplicacao_pct(saida_jscpd),
    )


def coletar_todos_os_trials(dir_trials: Path = DIR_TRIALS) -> list[dict]:
    linhas: list[dict] = []
    for solucao in sorted(dir_trials.glob("*/*/solucao.py")):
        if solucao.parent.name.startswith("exemplo-"):
            continue  # kata de exemplo não entra no experimento
        linha = coletar_metricas_trial(solucao)
        if linha is not None:
            linhas.append(linha)
    return linhas


def escrever_csv(csv_path: Path, linhas: list[dict]) -> None:
    import csv

    csv_path.parent.mkdir(parents=True, exist_ok=True)
    with csv_path.open("w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUNAS)
        writer.writeheader()
        for linha in linhas:
            writer.writerow(linha)


# --------------------------------------------------------------------------
# CLI
# --------------------------------------------------------------------------

def _construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="metricas_estaticas",
        description="Extrai métricas estáticas (RQ3) do código final de um "
        "trial, via Radon (complexidade, LOC, MI) e jscpd (duplicação).",
    )
    modo = p.add_mutually_exclusive_group(required=True)
    modo.add_argument("--integrante", help="roda um único trial")
    modo.add_argument(
        "--lote", action="store_true",
        help="roda sobre todos os trials em lab02/trials/ e consolida o CSV",
    )
    p.add_argument("--kata")
    p.add_argument("--tratamento", choices=TRATAMENTOS_SUFIXO)
    p.add_argument(
        "--csv", default=None,
        help="caminho alternativo do CSV (padrão: lab02/dados/metricas-estaticas.csv)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = _construir_parser().parse_args(argv)
    csv_path = Path(args.csv) if args.csv else CSV_METRICAS

    if args.lote:
        linhas = coletar_todos_os_trials()
        escrever_csv(csv_path, linhas)
        print(f"{len(linhas)} trials medidos. CSV escrito em {csv_path}.")
        return 0

    if not args.kata or not args.tratamento:
        print("erro: --kata e --tratamento são obrigatórios sem --lote", file=sys.stderr)
        return 2

    caminho_solucao = (
        DIR_TRIALS / args.integrante / f"{args.kata}-{args.tratamento}" / "solucao.py"
    )
    if not caminho_solucao.exists():
        print(f"erro: {caminho_solucao} não existe", file=sys.stderr)
        return 2

    linha = coletar_metricas_trial(caminho_solucao)
    if linha is None:
        print("erro: falha ao medir o trial (veja avisos acima)", file=sys.stderr)
        return 1

    for chave, valor in linha.items():
        print(f"  {chave}: {valor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
