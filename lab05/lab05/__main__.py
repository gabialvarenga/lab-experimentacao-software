"""Ponto de entrada: `python -m lab05` (a partir da pasta `lab05/`).

Subcomandos:
    executar   roda o plano de execuções do benchmark e grava o CSV bruto   (S01-07)
    validar    confere os dados coletados                                   (S01-08)
    analisar   descritiva, testes e tamanhos de efeito                      (S01-09)
"""

import argparse
import sys

from lab05 import config

PENDENTES = {
    "executar": "S01-07",
    "validar": "S01-08",
    "analisar": "S01-09",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m lab05", description=__doc__.split("\n")[0])
    parser.add_argument("--config", default=str(config.CONFIG_PADRAO), help="caminho do config.yaml")
    sub = parser.add_subparsers(dest="etapa")
    for nome in PENDENTES:
        sub.add_parser(nome)
    return parser


def _pendente(etapa: str) -> None:
    print(f"etapa '{etapa}' ainda não implementada (Issue {PENDENTES[etapa]})", file=sys.stderr)


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    config.carregar(args.config)
    if args.etapa in PENDENTES:
        _pendente(args.etapa)
        return 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
