"""Ponto de entrada: `python -m lab05` (a partir da pasta `lab05/`).

Subcomandos:
    executar   roda o plano de execuções do benchmark e grava o CSV bruto   (S01-07)
    validar    confere os dados coletados                                   (S01-08)
    analisar   descritiva, testes e tamanhos de efeito                      (S01-09)
"""

import argparse
import sys

from lab05 import config, executor

PENDENTES = {
    "validar": "S01-08",
    "analisar": "S01-09",
}


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m lab05", description=__doc__.split("\n")[0])
    parser.add_argument("--config", default=str(config.CONFIG_PADRAO), help="caminho do config.yaml")
    sub = parser.add_subparsers(dest="etapa")
    exe = sub.add_parser(
        "executar",
        help="roda o plano de execuções (precisa do Docker)",
        description="Roda o plano de execuções do config.yaml e retoma de onde parou. "
        "As opções trocam valores do config só nesta chamada (exemplo e piloto).",
    )
    exe.add_argument("--repeticoes", type=int, help="repetições por combinação")
    exe.add_argument("--aquecimento", type=int, dest="aquecimento_s", help="segundos de aquecimento")
    exe.add_argument("--medicao", type=int, dest="medicao_s", help="segundos de medição")
    exe.add_argument("--pausa", type=int, dest="pausa_s", help="segundos de pausa entre execuções")
    exe.add_argument("--saida", help="pasta das saídas, relativa à pasta do config")
    for nome in PENDENTES:
        sub.add_parser(nome)
    return parser


def _pendente(etapa: str) -> None:
    print(f"etapa '{etapa}' ainda não implementada (Issue {PENDENTES[etapa]})", file=sys.stderr)


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    cfg = config.carregar(args.config)
    if args.etapa == "executar":
        ajustes = {k: getattr(args, k) for k in ("repeticoes", "aquecimento_s", "medicao_s", "pausa_s", "saida")}
        resumo = executor.executar(executor.aplicar_ajustes(cfg, **ajustes))
        return 1 if resumo["falhas"] or resumo["interrompida"] else 0
    if args.etapa in PENDENTES:
        _pendente(args.etapa)
        return 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
