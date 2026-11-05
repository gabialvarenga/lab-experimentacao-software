"""Ponto de entrada: `python -m lab04` (a partir da pasta `lab04/`).

Subcomandos:
    coletar    coleta os PRs reais pela API (precisa de GITHUB_TOKEN)   (S01-04)
    calibrar   descritiva, parâmetros da lognormal e QQ-plot dos dados reais (S01-06)
    simular    roda as simulações Q1, Q2 e Q3 e grava os CSVs            (S02-02 a S02-05)
    dashboard  gera o HTML do dashboard e o abre no navegador            (S01-11, S02-11)

Sem subcomando, o comando único encadeia simular e dashboard, lendo o CSV da coleta
já versionado (S02-13). Enquanto `simular` não existe, ele avisa e gera só o dashboard.
`--sem-abrir` gera o dashboard sem abrir o navegador.
"""

import argparse
import sys
import webbrowser
from pathlib import Path

from lab04 import config

PENDENTES = {
    "simular": "S02-02",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m lab04", description=__doc__.split("\n")[0])
    parser.add_argument("--config", default=str(config.CONFIG_PADRAO), help="caminho do config.yaml")
    parser.add_argument("--sem-abrir", action="store_true", help="gera o dashboard sem abrir o navegador")
    sub = parser.add_subparsers(dest="etapa")
    for nome in ("coletar", "calibrar", *PENDENTES):
        sub.add_parser(nome)
    painel = sub.add_parser("dashboard")
    # SUPPRESS: sem a opção aqui, vale a do parser principal (aceita antes ou depois de `dashboard`)
    painel.add_argument("--sem-abrir", action="store_true", default=argparse.SUPPRESS,
                        help="só gera o HTML, sem abrir o navegador")
    return parser


def _pendente(etapa: str) -> None:
    print(f"etapa '{etapa}' ainda não implementada (Issue {PENDENTES[etapa]})", file=sys.stderr)


def _dashboard(cfg: dict, abrir: bool) -> int:
    from lab04 import dashboard

    saida = Path(cfg["pasta"]) / cfg["dashboard"]["saida"]
    dashboard.montar(saida, cfg)
    print(f"Dashboard gravado em {saida}")
    if abrir:
        webbrowser.open(saida.resolve().as_uri())
    return 0


def main(argv=None) -> int:
    args = _parser().parse_args(argv)
    cfg = config.carregar(args.config)
    if args.etapa == "coletar":
        from lab04 import coleta

        coleta.executar(cfg, config.token())
        return 0
    if args.etapa == "calibrar":
        from lab04 import calibracao

        calibracao.executar(cfg)
        return 0
    if args.etapa == "dashboard":
        return _dashboard(cfg, abrir=not args.sem_abrir)
    if args.etapa in PENDENTES:
        _pendente(args.etapa)
        return 1
    for etapa in PENDENTES:
        _pendente(etapa)
    return _dashboard(cfg, abrir=not args.sem_abrir)


if __name__ == "__main__":
    sys.exit(main())
