from __future__ import annotations

import argparse
import csv
import subprocess
import sys
import threading
import time
import xml.etree.ElementTree as ET
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path

INTEGRANTES = ("brenda", "carlos", "gabriela")
TRATAMENTOS = ("com-ia", "sem-ia")
TIMEBOX_MIN_PADRAO = 35
POLL_SEG_PADRAO = 15

COLUNAS = [
    "integrante",
    "kata",
    "tratamento",
    "ordem",
    "data_inicio",
    "tempo_segundos",
    "censurado",
    "testes_total",
    "testes_passando",
    "prompts",
    "observacoes",
]

RAIZ_LAB02 = Path(__file__).resolve().parent.parent
DIR_KATAS = RAIZ_LAB02 / "katas"
DIR_TRIALS = RAIZ_LAB02 / "trials"
CSV_TRIALS = RAIZ_LAB02 / "dados" / "trials.csv"


# --------------------------------------------------------------------------
# Funções puras (cobertas por tests/test_cronometro.py)
# --------------------------------------------------------------------------

@dataclass
class Contagem:
    total: int
    passando: int
    falhando: int
    erros: int
    ignorados: int


def parse_junit(xml_text: str) -> Contagem:
    """Lê um relatório JUnit do pytest (``--junitxml``) e conta os testes.

    Aceita tanto ``<testsuites>`` com filhos quanto um ``<testsuite>`` na raiz.
    """
    root = ET.fromstring(xml_text)
    suites = root.findall("testsuite") if root.tag == "testsuites" else [root]

    total = sum(int(s.get("tests", 0)) for s in suites)
    falhando = sum(int(s.get("failures", 0)) for s in suites)
    erros = sum(int(s.get("errors", 0)) for s in suites)
    ignorados = sum(int(s.get("skipped", 0)) for s in suites)
    passando = total - falhando - erros - ignorados
    return Contagem(total, passando, falhando, erros, ignorados)


def esta_verde(c: Contagem) -> bool:
    """Verde = existe pelo menos um teste e todos passaram."""
    return c.total > 0 and c.falhando == 0 and c.erros == 0 and c.ignorados == 0


def validar_entrada(integrante: str, kata: str, tratamento: str, ordem: int) -> list[str]:
    """Devolve a lista de mensagens de erro dos parâmetros (vazia se tudo ok)."""
    erros: list[str] = []
    if integrante not in INTEGRANTES:
        erros.append(f"integrante inválido: {integrante!r} (use um de {', '.join(INTEGRANTES)})")
    if tratamento not in TRATAMENTOS:
        erros.append(f"tratamento inválido: {tratamento!r} (use {' ou '.join(TRATAMENTOS)})")
    if not isinstance(ordem, int) or isinstance(ordem, bool) or ordem < 1:
        erros.append("ordem deve ser um inteiro >= 1")
    if not kata or any(c not in "abcdefghijklmnopqrstuvwxyz0123456789-_" for c in kata):
        erros.append(f"kata inválido: {kata!r} (apenas letras minúsculas, dígitos, '-' e '_')")
    return erros


def tempo_registrado(decorrido_s: float, censurado: bool, timebox_s: int) -> int:
    """Tempo gravado no CSV: o time-box cheio quando censurado, senão o decorrido."""
    return timebox_s if censurado else round(decorrido_s)


def montar_linha(
    *,
    integrante: str,
    kata: str,
    tratamento: str,
    ordem: int,
    data_inicio: str,
    decorrido_s: float,
    censurado: bool,
    contagem: Contagem,
    prompts: int,
    observacoes: str,
    timebox_s: int,
) -> dict:
    """Monta o dicionário de uma linha do ``trials.csv`` na ordem de ``COLUNAS``."""
    return {
        "integrante": integrante,
        "kata": kata,
        "tratamento": tratamento,
        "ordem": ordem,
        "data_inicio": data_inicio,
        "tempo_segundos": tempo_registrado(decorrido_s, censurado, timebox_s),
        "censurado": "true" if censurado else "false",
        "testes_total": contagem.total,
        "testes_passando": contagem.passando,
        "prompts": prompts,
        "observacoes": observacoes,
    }


def anexar_linha(csv_path: Path, linha: dict) -> None:
    """Anexa ``linha`` ao CSV, criando o arquivo e o cabeçalho se necessário."""
    csv_path.parent.mkdir(parents=True, exist_ok=True)
    novo = not csv_path.exists()
    with csv_path.open("a", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=COLUNAS)
        if novo:
            writer.writeheader()
        writer.writerow({col: linha.get(col, "") for col in COLUNAS})


def linha_existe(csv_path: Path, integrante: str, kata: str, tratamento: str) -> bool:
    """True se já há uma linha para essa combinação integrante+kata+tratamento."""
    if not csv_path.exists():
        return False
    with csv_path.open(newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if (row["integrante"], row["kata"], row["tratamento"]) == (
                integrante,
                kata,
                tratamento,
            ):
                return True
    return False


# --------------------------------------------------------------------------
# Execução do trial (parte interativa, validada de ponta a ponta pelo kata
# de exemplo em katas/exemplo/)
# --------------------------------------------------------------------------

def _preparar_dir_trial(kata: str, integrante: str, tratamento: str) -> Path:
    origem = DIR_KATAS / kata
    if not (origem / "test_aceitacao.py").exists():
        raise SystemExit(
            f"kata não encontrado: {origem / 'test_aceitacao.py'} não existe"
        )
    destino = DIR_TRIALS / integrante / f"{kata}-{tratamento}"
    destino.mkdir(parents=True, exist_ok=True)

    (destino / "test_aceitacao.py").write_text(
        (origem / "test_aceitacao.py").read_text(encoding="utf-8"), encoding="utf-8"
    )
    solucao = destino / "solucao.py"
    if not solucao.exists():
        starter = origem / "solucao_starter.py"
        solucao.write_text(
            starter.read_text(encoding="utf-8") if starter.exists() else "",
            encoding="utf-8",
        )
    return destino


def _rodar_testes(dir_trial: Path) -> Contagem:
    report = dir_trial / "report.xml"
    subprocess.run(
        [sys.executable, "-m", "pytest", "test_aceitacao.py",
         f"--junitxml={report.name}", "-q"],
        cwd=dir_trial,
        env={**_env_com_pythonpath(dir_trial)},
        capture_output=True,
    )
    if not report.exists():
        return Contagem(0, 0, 0, 0, 0)
    return parse_junit(report.read_text(encoding="utf-8"))


def _env_com_pythonpath(dir_trial: Path) -> dict:
    import os

    env = dict(os.environ)
    anterior = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = str(dir_trial) + (os.pathsep + anterior if anterior else "")
    return env


def _formatar_mmss(segundos: float) -> str:
    m, s = divmod(int(segundos), 60)
    return f"{m:02d}:{s:02d}"


def executar_trial(args: argparse.Namespace) -> int:
    for fluxo in (sys.stdout, sys.stderr):
        try:
            fluxo.reconfigure(encoding="utf-8")  # acentos no console do Windows
        except Exception:
            pass

    erros = validar_entrada(args.integrante, args.kata, args.tratamento, args.ordem)
    if erros:
        for e in erros:
            print(f"  erro: {e}", file=sys.stderr)
        return 2

    csv_path = Path(args.csv) if args.csv else CSV_TRIALS
    if linha_existe(csv_path, args.integrante, args.kata, args.tratamento):
        resp = input(
            f"Já existe trial para {args.integrante}/{args.kata}/{args.tratamento}. "
            "Gravar outra linha mesmo assim? [s/N] "
        ).strip().lower()
        if resp != "s":
            print("cancelado.")
            return 1

    dir_trial = _preparar_dir_trial(args.kata, args.integrante, args.tratamento)
    timebox_s = int(round(args.timebox * 60))

    print("=" * 64)
    print(f"  trial: {args.integrante} · {args.kata} · {args.tratamento} · ordem {args.ordem}")
    print(f"  edite: {dir_trial / 'solucao.py'}")
    print(f"  time-box: {args.timebox:g} min   ·   checagem a cada {args.poll}s")
    print("  Ctrl+C encerra o trial manualmente (registra como censurado).")
    print("=" * 64)

    data_inicio = datetime.now().isoformat(timespec="seconds")
    inicio = time.monotonic()
    fim = threading.Event()
    estado: dict = {"censurado": False, "contagem": Contagem(0, 0, 0, 0, 0)}

    def _monitor() -> None:
        avisou = False
        while not fim.wait(args.poll):
            decorrido = time.monotonic() - inicio
            if decorrido >= timebox_s:
                estado["censurado"] = True
                estado["contagem"] = _rodar_testes(dir_trial)
                print(f"\n>>> TEMPO ESGOTADO ({args.timebox:g} min). "
                      "Trial encerrado como censurado.")
                fim.set()
                return
            if timebox_s > 300 and not avisou and decorrido >= timebox_s - 300:
                avisou = True
                print("\n>>> Faltam ~5 min para o fim do time-box.")
            contagem = _rodar_testes(dir_trial)
            estado["contagem"] = contagem
            print(
                f"  [{_formatar_mmss(decorrido)}] "
                f"{contagem.passando}/{contagem.total} testes passando"
            )
            if esta_verde(contagem):
                print("\n>>> VERDE! Todos os testes de aceitação passaram.")
                fim.set()
                return

    monitor = threading.Thread(target=_monitor, daemon=True)
    monitor.start()
    try:
        fim.wait(timeout=timebox_s + 30)
    except KeyboardInterrupt:
        estado["censurado"] = True
        fim.set()
        print("\n>>> Encerrado manualmente. Registrando como censurado.")
    monitor.join(timeout=args.poll + 5)

    decorrido_s = time.monotonic() - inicio
    contagem = _rodar_testes(dir_trial)  # medição final autoritativa
    censurado = estado["censurado"] or not esta_verde(contagem)

    prompts = 0
    if args.tratamento == "com-ia":
        prompts = _perguntar_int("Nº de prompts/interações com a IA neste trial: ")
    observacoes = input("Observações (opcional): ").strip()

    linha = montar_linha(
        integrante=args.integrante,
        kata=args.kata,
        tratamento=args.tratamento,
        ordem=args.ordem,
        data_inicio=data_inicio,
        decorrido_s=decorrido_s,
        censurado=censurado,
        contagem=contagem,
        prompts=prompts,
        observacoes=observacoes,
        timebox_s=timebox_s,
    )
    anexar_linha(csv_path, linha)

    print("-" * 64)
    print(f"  tempo real:      {_formatar_mmss(decorrido_s)}")
    print(f"  gravado (s):     {linha['tempo_segundos']}")
    print(f"  censurado:       {linha['censurado']}")
    print(f"  testes:          {contagem.passando}/{contagem.total} passando")
    print(f"  linha anexada a: {csv_path}")
    print("-" * 64)
    return 0


def _perguntar_int(prompt: str) -> int:
    while True:
        bruto = input(prompt).strip()
        try:
            valor = int(bruto)
            if valor < 0:
                raise ValueError
            return valor
        except ValueError:
            print("  informe um inteiro >= 0.")


def _construir_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        prog="cronometro",
        description="Cronometra e registra um trial do experimento do Lab02.",
    )
    p.add_argument("--integrante", required=True, choices=INTEGRANTES)
    p.add_argument("--kata", required=True, help="id do kata (ex.: k1, exemplo)")
    p.add_argument("--tratamento", required=True, choices=TRATAMENTOS)
    p.add_argument("--ordem", required=True, type=int,
                   help="posição do trial na sequência do integrante (1..6)")
    p.add_argument("--timebox", type=float, default=TIMEBOX_MIN_PADRAO,
                   help="minutos do time-box (padrão 35; só reduzir, com "
                        "justificativa no relatório)")
    p.add_argument("--poll", type=int, default=POLL_SEG_PADRAO,
                   help="intervalo em segundos entre checagens dos testes")
    p.add_argument("--csv", default=None,
                   help="caminho alternativo do CSV (padrão: lab02/dados/trials.csv)")
    return p


def main(argv: list[str] | None = None) -> int:
    args = _construir_parser().parse_args(argv)
    return executar_trial(args)


if __name__ == "__main__":
    raise SystemExit(main())
