from __future__ import annotations

import argparse
import re
import sys
from pathlib import Path

from cronometro import Contagem, parse_junit

TRATAMENTOS_SUFIXO = ("com-ia", "sem-ia")

COLUNAS = [
    "integrante",
    "kata",
    "tratamento",
    "testes_total",
    "testes_passando",
    "testes_falhando",
    "taxa_sucesso",
]

RAIZ_LAB02 = Path(__file__).resolve().parent.parent
DIR_TRIALS = RAIZ_LAB02 / "trials"
DIR_KATAS = RAIZ_LAB02 / "katas"
CSV_CONTAGEM = RAIZ_LAB02 / "dados" / "contagem-testes.csv"

_PADRAO_DEF_TESTE = re.compile(r"^\s*def (test_\w+)\s*\(", re.MULTILINE)


# --------------------------------------------------------------------------
# Funções puras (cobertas por tests/test_contagem_testes.py)
# --------------------------------------------------------------------------

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


def contar_testes_da_kata(caminho_test_aceitacao: Path) -> int:
    """Número fixo de casos de um kata, pelo `test_aceitacao.py` original.

    Não usa o `report.xml` de um trial específico: numa falha de coleta
    (ex.: erro de sintaxe em `solucao.py`), o pytest grava ``tests="1"`` —
    a própria falha contada como um teste — o que subestimaria o total
    real e tornaria trials do mesmo kata incomparáveis entre si.
    """
    conteudo = caminho_test_aceitacao.read_text(encoding="utf-8")
    return len(_PADRAO_DEF_TESTE.findall(conteudo))


def calcular_falhas_e_taxa(testes_total_kata: int, passando: int) -> tuple[int, float]:
    """``testes_falhando`` e ``taxa_sucesso`` a partir do total real do kata."""
    if testes_total_kata == 0:
        return 0, 0.0
    falhando = testes_total_kata - passando
    taxa = passando / testes_total_kata * 100
    return falhando, taxa


def montar_linha_contagem(
    *,
    integrante: str,
    kata: str,
    tratamento: str,
    testes_total: int,
    testes_passando: int,
    testes_falhando: int,
    taxa_sucesso: float,
) -> dict:
    """Monta o dicionário de uma linha de ``contagem-testes.csv``."""
    return {
        "integrante": integrante,
        "kata": kata,
        "tratamento": tratamento,
        "testes_total": testes_total,
        "testes_passando": testes_passando,
        "testes_falhando": testes_falhando,
        "taxa_sucesso": round(taxa_sucesso, 2),
    }


# --------------------------------------------------------------------------
# Integração — validadas manualmente contra trials reais
# --------------------------------------------------------------------------

def ler_contagem_do_trial(caminho_report: Path) -> Contagem:
    """Lê o `report.xml` já gravado ao vivo pelo `cronometro.py`.

    Não roda o pytest de novo. Se o arquivo não existir (trial que nem
    chegou a rodar), devolve contagem zerada em vez de falhar.
    """
    if not caminho_report.exists():
        return Contagem(0, 0, 0, 0, 0)
    return parse_junit(caminho_report.read_text(encoding="utf-8"))


def processar_trial(dir_trial: Path, dir_katas: Path = DIR_KATAS) -> dict:
    integrante = dir_trial.parent.name
    kata, tratamento = extrair_kata_e_tratamento(dir_trial.name)

    caminho_teste_kata = dir_katas / kata / "test_aceitacao.py"
    testes_total = contar_testes_da_kata(caminho_teste_kata)

    contagem = ler_contagem_do_trial(dir_trial / "report.xml")
    testes_falhando, taxa_sucesso = calcular_falhas_e_taxa(testes_total, contagem.passando)

    return montar_linha_contagem(
        integrante=integrante,
        kata=kata,
        tratamento=tratamento,
        testes_total=testes_total,
        testes_passando=contagem.passando,
        testes_falhando=testes_falhando,
        taxa_sucesso=taxa_sucesso,
    )


def processar_todos_os_trials(
    dir_trials: Path = DIR_TRIALS, dir_katas: Path = DIR_KATAS
) -> list[dict]:
    linhas: list[dict] = []
    for dir_trial in sorted(dir_trials.glob("*/*")):
        if not dir_trial.is_dir() or dir_trial.name.startswith("exemplo-"):
            continue  # kata de exemplo não entra no experimento
        linhas.append(processar_trial(dir_trial, dir_katas))
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
        prog="contagem_testes",
        description="Calcula testes_total/passando/falhando e taxa de "
        "sucesso (RQ2) a partir do report.xml já gravado por cada trial.",
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
        help="caminho alternativo do CSV (padrão: lab02/dados/contagem-testes.csv)",
    )
    return p


def main(argv: list[str] | None = None) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")
        except Exception:
            pass

    args = _construir_parser().parse_args(argv)
    csv_path = Path(args.csv) if args.csv else CSV_CONTAGEM

    if args.lote:
        linhas = processar_todos_os_trials()
        escrever_csv(csv_path, linhas)
        print(f"{len(linhas)} trials processados. CSV escrito em {csv_path}.")
        return 0

    if not args.kata or not args.tratamento:
        print("erro: --kata e --tratamento são obrigatórios sem --lote", file=sys.stderr)
        return 2

    dir_trial = DIR_TRIALS / args.integrante / f"{args.kata}-{args.tratamento}"
    if not dir_trial.exists():
        print(f"erro: {dir_trial} não existe", file=sys.stderr)
        return 2

    linha = processar_trial(dir_trial)
    for chave, valor in linha.items():
        print(f"  {chave}: {valor}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
