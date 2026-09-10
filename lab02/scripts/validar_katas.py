"""Validação das katas do Lab02 (issue #61).

O enunciado pede katas com testes de aceitação automatizados e de dificuldade
comparável. Este script confere, para cada kata:

- que a pasta tem `enunciado.md`, `test_aceitacao.py` e `solucao_starter.py`;
- que a suíte de aceitação roda pelo pytest sem erro de importação/coleta;
- que, com o esqueleto vazio (`solucao_starter.py`), **todos** os casos falham
  — garante que cada teste depende de uma implementação de verdade e nenhum
  passa "de graça";
- reporta o nº de casos de teste, um dos critérios de dificuldade comparável
  documentados em `docs/katas.md`.

Uso:
    python lab02/scripts/validar_katas.py
    python lab02/scripts/validar_katas.py --kata k3
    python lab02/scripts/validar_katas.py --incluir-exemplo

Sai com código 1 se alguma kata estiver mal-formada.
"""

from __future__ import annotations

import argparse
import shutil
import subprocess
import sys
import tempfile
from dataclasses import dataclass
from pathlib import Path

from cronometro import parse_junit

RAIZ_LAB02 = Path(__file__).resolve().parent.parent
DIR_KATAS = RAIZ_LAB02 / "katas"
IGNORADAS = {"exemplo"}
ARQUIVOS_KATA = ("enunciado.md", "test_aceitacao.py", "solucao_starter.py")


# --------------------------------------------------------------------------
# Funções puras (cobertas por tests/test_validar_katas.py)
# --------------------------------------------------------------------------

def listar_katas(dir_katas: Path, ignorar: set[str] = frozenset()) -> list[str]:
    """Ids das katas: subpastas que tenham `test_aceitacao.py`, em ordem."""
    return sorted(
        p.name
        for p in dir_katas.iterdir()
        if p.is_dir() and p.name not in ignorar and (p / "test_aceitacao.py").exists()
    )


def arquivos_faltando(dir_kata: Path) -> list[str]:
    """Quais dos arquivos esperados de uma kata não existem na pasta."""
    return [nome for nome in ARQUIVOS_KATA if not (dir_kata / nome).exists()]


def contar_testes(fonte: str) -> int:
    """Nº de casos de aceitação: funções cujo nome começa com `test_`."""
    return sum(1 for linha in fonte.splitlines() if linha.lstrip().startswith("def test_"))


# --------------------------------------------------------------------------
# Execução
# --------------------------------------------------------------------------

@dataclass
class Resultado:
    kata: str
    ok: bool
    testes: int
    detalhe: str


def validar_kata(kata: str, dir_katas: Path) -> Resultado:
    dir_kata = dir_katas / kata
    faltando = arquivos_faltando(dir_kata)
    if faltando:
        return Resultado(kata, False, 0, f"faltando: {', '.join(faltando)}")

    suite = dir_kata / "test_aceitacao.py"
    declarados = contar_testes(suite.read_text(encoding="utf-8"))

    with tempfile.TemporaryDirectory() as tmp:
        area = Path(tmp)
        shutil.copy(suite, area / "test_aceitacao.py")
        shutil.copy(dir_kata / "solucao_starter.py", area / "solucao.py")
        proc = subprocess.run(
            [sys.executable, "-m", "pytest", "test_aceitacao.py",
             "--junitxml=report.xml", "-q"],
            cwd=area,
            capture_output=True,
            text=True,
        )
        relatorio = area / "report.xml"
        if not relatorio.exists():
            linhas = (proc.stdout or proc.stderr or "").strip().splitlines()
            return Resultado(kata, False, declarados,
                             linhas[-1] if linhas else "pytest não coletou a suíte")
        c = parse_junit(relatorio.read_text(encoding="utf-8"))

    if c.total == 0:
        return Resultado(kata, False, declarados, "nenhum caso coletado")
    if c.total != declarados:
        return Resultado(kata, False, c.total,
                         f"{c.total} casos coletados, {declarados} declarados no arquivo")
    if c.passando > 0:
        return Resultado(kata, False, c.total,
                         f"{c.passando} caso(s) passam com o esqueleto vazio")
    return Resultado(kata, True, c.total, f"{c.total} casos, todos falham sem implementação")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="validar_katas",
        description="Confere que cada kata está completa e que a suíte de aceitação é automatizada.",
    )
    parser.add_argument("--kata", help="valida apenas esta kata (padrão: todas)")
    parser.add_argument("--incluir-exemplo", action="store_true",
                        help="inclui a kata de brinquedo katas/exemplo/")
    args = parser.parse_args(argv)

    try:
        sys.stdout.reconfigure(encoding="utf-8")  # acentos no console do Windows
    except Exception:
        pass

    ignorar = set() if args.incluir_exemplo else IGNORADAS
    katas = [args.kata] if args.kata else listar_katas(DIR_KATAS, ignorar)
    if not katas:
        print("nenhuma kata encontrada em", DIR_KATAS)
        return 1

    resultados = [validar_kata(k, DIR_KATAS) for k in katas]

    print(f"{'kata':<10}{'testes':>8}  {'':<4}{'detalhe'}")
    print("-" * 58)
    for r in resultados:
        marca = "ok" if r.ok else "FALHOU"
        print(f"{r.kata:<10}{r.testes:>8}  {marca:<8}{r.detalhe}")
    print("-" * 58)

    falhas = [r for r in resultados if not r.ok]
    if falhas:
        print(f"{len(falhas)} de {len(resultados)} katas com problema.")
        return 1

    testes = [r.testes for r in resultados]
    print(f"{len(resultados)} katas ok.  casos de teste: {min(testes)}-{max(testes)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
