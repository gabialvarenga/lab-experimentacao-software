"""Ponto de entrada: `python -m lab05` (a partir da pasta `lab05/`).

Subcomandos:
    executar   roda o plano de execuções do benchmark e grava o CSV bruto   (S01-07)
    validar    confere os dados coletados                                   (S01-08)
    analisar   descritiva, testes, tamanhos de efeito e poder               (S01-09)
"""

import argparse
import sys

from lab05 import analise, config, executor, validacao

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
    ana = sub.add_parser(
        "analisar",
        help="descritiva, testes e número de repetições (não precisa do Docker)",
        description="Analisa o CSV de uma coleta (as mesmas opções usadas no executar) e grava "
        "os CSVs e o registro em <pasta da coleta>/analise/. Parâmetros no bloco `analise` do config.",
    )
    _opcoes_da_coleta(ana)
    ana.add_argument("--simulacoes", type=int, help="simulações por ponto da curva de poder (padrão: config)")
    return parser


def _comando(argv) -> str:
    """O comando como foi digitado, para o registro da análise."""
    return " ".join(["python -m lab05", *argv])


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    cfg = config.carregar(args.config)
    if args.etapa in ("executar", "validar", "analisar"):
        cfg = executor.aplicar_ajustes(cfg, **{k: getattr(args, k, None) for k in AJUSTES})
    if args.etapa == "executar":
        resumo = executor.executar(cfg)
        return 1 if resumo["falhas"] or resumo["interrompida"] else 0
    if args.etapa == "validar":
        resultado = validacao.validar(cfg)
        validacao.escrever_relatorio(cfg, resultado)
        print(f"{len(resultado.erros)} erro(s), {len(resultado.avisos)} aviso(s); relatório: {executor.caminhos(cfg)['qualidade']}")
        return 0 if resultado.ok else 1
    if args.etapa == "analisar":
        if args.simulacoes is not None:
            cfg["analise"] = {**(cfg.get("analise") or {}), "simulacoes": args.simulacoes}
        resultado = analise.analisar(cfg)
        pasta = analise.gravar(cfg, resultado, _comando(sys.argv[1:] if argv is None else argv))
        print(f"análise gravada em {pasta}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
