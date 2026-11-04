"""Ponto de entrada: `python -m lab04` (a partir da pasta `lab04/`).

Subcomandos:
    coletar    coleta os PRs reais pela API (precisa de GITHUB_TOKEN)   (S01-04)
    simular    roda as simulações Q1, Q2 e Q3 e grava os CSVs            (S02-02 a S02-05)
    dashboard  gera o HTML do dashboard a partir dos CSVs                (S01-11, S02-11)

Sem subcomando, o comando único encadeia simular e dashboard, lendo o CSV da coleta
já versionado (S02-13). Enquanto as etapas não existem, cada uma avisa e sai com 1.
"""

import argparse
import sys

from lab04 import config

ETAPAS = {
    "coletar": "S01-04",
    "simular": "S02-02",
    "dashboard": "S01-11",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m lab04", description=__doc__.split("\n")[0])
    parser.add_argument("--config", default=str(config.CONFIG_PADRAO), help="caminho do config.yaml")
    sub = parser.add_subparsers(dest="etapa")
    for nome in ETAPAS:
        sub.add_parser(nome)
    return parser


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    config.carregar(args.config)
    etapas = [args.etapa] if args.etapa else ["simular", "dashboard"]
    for etapa in etapas:
        print(f"etapa '{etapa}' ainda não implementada (Issue {ETAPAS[etapa]})", file=sys.stderr)
    return 1


if __name__ == "__main__":
    sys.exit(main())
