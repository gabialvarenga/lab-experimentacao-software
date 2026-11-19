"""Ponto de entrada: `python -m lab05` (a partir da pasta `lab05/`).

Subcomandos:
    executar   roda o plano de execuções do benchmark e grava o CSV bruto   (S01-07)
    validar    confere os dados coletados                                   (S01-08)
    analisar   descritiva, testes e tamanhos de efeito                      (S01-09)
"""

import argparse
import sys

from lab05 import config, executor, validacao

PENDENTES = {
    "analisar": "S01-09",
}
AJUSTES = ("repeticoes", "aquecimento_s", "medicao_s", "pausa_s", "saida", "nome", "piloto")


def _opcoes_da_coleta(sub) -> None:
    """Opções comuns a `executar` e `validar`: as duas precisam descrever a mesma coleta."""
    sub.add_argument("--piloto", action="store_true", help="usa o bloco `piloto` do config (S01-08)")
    sub.add_argument("--repeticoes", type=int, help="repetições por combinação")
    sub.add_argument("--saida", help="pasta das saídas, relativa à pasta do config")
    sub.add_argument("--nome", help="nome da coleta: <nome>.csv e registro-<nome>.md")


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
    _opcoes_da_coleta(exe)
    exe.add_argument("--aquecimento", type=int, dest="aquecimento_s", help="segundos de aquecimento")
    exe.add_argument("--medicao", type=int, dest="medicao_s", help="segundos de medição")
    exe.add_argument("--pausa", type=int, dest="pausa_s", help="segundos de pausa entre execuções")
    val = sub.add_parser(
        "validar",
        help="confere os dados de uma coleta e grava o relatório de qualidade",
        description="Valida o CSV de uma coleta (as mesmas opções usadas no executar) e grava qualidade-<nome>.md.",
    )
    _opcoes_da_coleta(val)
    for nome in PENDENTES:
        sub.add_parser(nome)
    return parser


def _pendente(etapa: str) -> None:
    print(f"etapa '{etapa}' ainda não implementada (Issue {PENDENTES[etapa]})", file=sys.stderr)


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    cfg = config.carregar(args.config)
    if args.etapa in ("executar", "validar"):
        cfg = executor.aplicar_ajustes(cfg, **{k: getattr(args, k, None) for k in AJUSTES})
    if args.etapa == "executar":
        resumo = executor.executar(cfg)
        return 1 if resumo["falhas"] or resumo["interrompida"] else 0
    if args.etapa == "validar":
        resultado = validacao.validar(cfg)
        validacao.escrever_relatorio(cfg, resultado)
        print(f"{len(resultado.erros)} erro(s), {len(resultado.avisos)} aviso(s); relatório: {executor.caminhos(cfg)['qualidade']}")
        return 0 if resultado.ok else 1
    if args.etapa in PENDENTES:
        _pendente(args.etapa)
        return 1
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
