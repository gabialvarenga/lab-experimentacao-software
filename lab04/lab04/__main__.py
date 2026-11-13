"""Ponto de entrada: `python -m lab04` (a partir da pasta `lab04/`).

Subcomandos:
    coletar    coleta os PRs reais pela API (precisa de GITHUB_TOKEN)   (S01-04)
    calibrar   descritiva, parâmetros da lognormal e QQ-plot dos dados reais (S01-06)
    simular    roda as simulações Q1, Q2 e Q3, grava os CSVs e os consolida (S02-03 a S02-07)
    dashboard  gera o HTML do dashboard e o abre no navegador            (S01-11, S02-11)
    app        sobe o dashboard interativo (Streamlit) e o abre no navegador   (S02-13)

Sem subcomando, o comando único (S02-13) encadeia simular e dashboard: as simulações leem os
parâmetros do `config.yaml`, calibrados a partir do CSV da coleta já versionado, e o dashboard lê
o CSV da coleta e os resultados das simulações. A coleta fica fora, porque precisa de token.
`--sem-abrir` gera o dashboard sem abrir o navegador (no `app`, sobe o servidor sem abrir).
"""

import argparse
import subprocess
import sys
import threading
import webbrowser
from pathlib import Path

from lab04 import config

APP = Path(__file__).resolve().parent.parent / "app.py"   # dashboard interativo; o Streamlit roda um script, fora do pacote
ESPERA_NAVEGADOR_S = 4.0   # segundos até abrir o navegador no `app`, enquanto o servidor sobe

# As simulações finais (S02-03, S02-04 e S02-05): cenários e CSV de cada uma, relativo à pasta do
# config. Cada uma roda como o comando gravado no seu `registro-<nome>.md`, e cada cenário mantém as
# sementes que tem na grade inteira, então os CSVs versionados se reproduzem byte a byte.
SIMULACOES_FINAIS = (
    (("C0", "C1"), "dados/simulacao/c0_c1.csv"),
    (("C2", "C3"), "dados/simulacao/c2_c3.csv"),
    (("C4",), "dados/simulacao/c4.csv"),
)


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="python -m lab04", description=__doc__.split("\n")[0])
    parser.add_argument("--config", default=str(config.CONFIG_PADRAO), help="caminho do config.yaml")
    parser.add_argument("--sem-abrir", action="store_true", help="gera o dashboard sem abrir o navegador")
    sub = parser.add_subparsers(dest="etapa")
    for nome in ("coletar", "calibrar", "simular"):
        sub.add_parser(nome)
    painel = sub.add_parser("dashboard")
    # SUPPRESS: sem a opção aqui, vale a do parser principal (aceita antes ou depois de `dashboard`)
    painel.add_argument("--sem-abrir", action="store_true", default=argparse.SUPPRESS,
                        help="só gera o HTML, sem abrir o navegador")
    app = sub.add_parser("app")
    app.add_argument("--sem-abrir", action="store_true", default=argparse.SUPPRESS,
                     help="sobe o servidor sem abrir o navegador")
    app.add_argument("--porta", type=int, default=8501, help="porta do servidor local (padrão: 8501)")
    return parser


def _simular(caminho_config: str) -> int:
    """Roda as `SIMULACOES_FINAIS` e consolida os resultados (`resultados.csv`, classificação e poder).

    Usa as linhas de comando de `simulacao` e `resultados`, para que os registros gravados sejam
    os mesmos de rodar cada comando à mão. Uma falha interrompe a sequência com a exceção.
    """
    from lab04 import resultados, simulacao

    for cenarios, saida in SIMULACOES_FINAIS:
        simulacao.main(["--config", caminho_config, "--cenarios", *cenarios, "--saida", saida])
    resultados.main(["--config", caminho_config])
    return 0


def _dashboard(cfg: dict, abrir: bool) -> int:
    from lab04 import dashboard

    saida = Path(cfg["pasta"]) / cfg["dashboard"]["saida"]
    dashboard.montar(saida, cfg)
    print(f"Dashboard gravado em {saida}")
    if abrir:
        webbrowser.open(saida.resolve().as_uri())
    return 0


def _app(abrir: bool, porta: int) -> int:
    """Sobe o servidor do Streamlit com o `app.py`; fica rodando até Ctrl+C.

    Sempre em modo headless: sem ele, a primeira execução do Streamlit para num prompt de e-mail no
    terminal e o servidor não sobe até alguém apertar Enter. O navegador é aberto por aqui, depois
    de `ESPERA_NAVEGADOR_S` segundos, para dar tempo de o servidor subir.
    """
    url = f"http://localhost:{porta}"
    comando = [sys.executable, "-m", "streamlit", "run", str(APP), "--server.port", str(porta),
               "--server.headless", "true"]
    print(f"Dashboard interativo em {url} (deixe este terminal aberto; Ctrl+C para encerrar)")
    if abrir:
        threading.Timer(ESPERA_NAVEGADOR_S, webbrowser.open, args=(url,)).start()
    return subprocess.call(comando, cwd=APP.parent)


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
    if args.etapa == "app":
        return _app(abrir=not args.sem_abrir, porta=args.porta)
    if args.etapa == "simular":
        return _simular(args.config)
    _simular(args.config)
    return _dashboard(cfg, abrir=not args.sem_abrir)


if __name__ == "__main__":
    sys.exit(main())
