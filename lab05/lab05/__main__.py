"""Ponto de entrada: `python -m lab05` (a partir da pasta `lab05/`).

Subcomandos:
    executar   roda o plano de execuções do benchmark e grava o CSV bruto   (S01-07)
    validar    confere os dados coletados                                   (S01-08)
    analisar   descritiva, testes, tamanhos de efeito e poder               (S01-09)
               Q3 e análise pareada por bloco                               (S02-01)
    graficos   figuras G1 a G4 e a página de apresentação em HTML           (S02-05)
    app        dashboard interativo (Streamlit), só lê os CSVs gravados      (S02-09)
"""

import argparse
import importlib.util
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

import pandas as pd

from lab05 import analise, config, executor, graficos, validacao

APP = Path(__file__).resolve().parent / "app.py"   # o Streamlit roda um script, e não um módulo do pacote
ESPERA_NAVEGADOR_S = 4.0   # segundos até abrir o navegador, enquanto o servidor sobe
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
        help="descritiva, testes, Q3, análise pareada e número de repetições (não precisa do Docker)",
        description="Analisa o CSV de uma coleta (as mesmas opções usadas no executar) e grava "
        "os CSVs e o registro em <pasta da coleta>/analise/. Parâmetros no bloco `analise` do config.",
    )
    _opcoes_da_coleta(ana)
    ana.add_argument("--simulacoes", type=int, help="simulações por ponto da curva de poder (padrão: config)")
    gra = sub.add_parser(
        "graficos",
        help="figuras G1 a G4 e a página de apresentação (não precisa do Docker)",
        description="Lê o CSV de uma coleta e o comparacoes.csv do `analisar` e grava as figuras em HTML "
        "em <pasta da coleta>/analise/figuras/, com a página apresentacao.html.",
    )
    _opcoes_da_coleta(gra)
    app = sub.add_parser(
        "app",
        help="dashboard interativo (Streamlit); só lê os CSVs, não precisa do Docker",
        description="Sobe o dashboard em http://localhost:<porta> e o abre no navegador. Lê a coleta completa "
        "(execucoes.csv) e as tabelas do `analisar`; abrir a página nunca roda o benchmark. Ctrl+C encerra.",
    )
    app.add_argument("--porta", type=int, default=8501, help="porta do servidor local (padrão: 8501)")
    app.add_argument("--sem-abrir", action="store_true", help="sobe o servidor sem abrir o navegador")
    return parser


def _comando(argv) -> str:
    """O comando como foi digitado, para o registro da análise."""
    return " ".join(["python -m lab05", *argv])


def _app(abrir: bool, porta: int) -> int:
    """Sobe o servidor do Streamlit com o `app.py` e fica rodando até Ctrl+C.

    Sempre em modo *headless*: sem ele, a primeira execução do Streamlit para num pedido de e-mail
    no terminal. As estatísticas de uso do Streamlit ficam desligadas. O navegador é aberto daqui, depois de `ESPERA_NAVEGADOR_S`, para dar tempo de o
    servidor subir.
    """
    if importlib.util.find_spec("streamlit") is None:
        print("o Streamlit não está instalado: rode `python -m pip install -r requirements.txt`", file=sys.stderr)
        return 1
    url = f"http://localhost:{porta}"
    comando = [sys.executable, "-m", "streamlit", "run", str(APP), "--server.port", str(porta), "--server.headless", "true",
               "--browser.gatherUsageStats", "false"]
    print(f"Dashboard em {url} (deixe este terminal aberto; Ctrl+C para encerrar)")
    if abrir:
        threading.Timer(ESPERA_NAVEGADOR_S, webbrowser.open, args=(url,)).start()
    return subprocess.call(comando, cwd=APP.parent.parent)


def main(argv=None) -> int:
    parser = _parser()
    args = parser.parse_args(argv)
    if args.etapa == "app":
        return _app(abrir=not args.sem_abrir, porta=args.porta)
    cfg = config.carregar(args.config)
    if args.etapa in ("executar", "validar", "analisar", "graficos"):
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
    if args.etapa == "graficos":
        df = analise.ler_coleta(cfg)
        comparacoes_csv = analise.pasta_saida(cfg) / "comparacoes.csv"
        if not comparacoes_csv.exists():
            raise SystemExit(f"{comparacoes_csv} não existe: rode o analisar antes (o G3 usa as comparações)")
        comparacoes = pd.read_csv(comparacoes_csv)
        csv = executor.caminhos(cfg)["csv"]
        origem = f"{csv.parent.name}/{csv.name} ({len(df)} execuções)"
        titulo = "Lab05: Redis × Valkey" + (" (piloto)" if args.piloto else "")
        caminhos = graficos.exportar(df, comparacoes, analise.pasta_saida(cfg) / "figuras", titulo, origem)
        print(f"{len(caminhos)} arquivo(s) gravado(s) em {caminhos[0].parent}")
        return 0
    parser.print_help()
    return 0


if __name__ == "__main__":
    sys.exit(main())
