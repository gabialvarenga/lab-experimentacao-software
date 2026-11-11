"""Piloto da S02-01: roda a grade do config com poucas repetições e grava o CSV de exemplo.

O piloto serviu para calibrar a grade de efeitos antes de congelar o `config.yaml` e dá aos
gráficos G3 e G4 um CSV real no formato congelado. Desde a S02-02 ele só chama o motor
(`simulacao.rodar_grade`) com `simulacao.repeticoes_piloto` repetições e grava em `simulacao.piloto`.

Uso, a partir da pasta `lab04/`: `python -m lab04.piloto` (regrava `dados/simulacao/piloto.csv`).
"""

import sys
from pathlib import Path

from lab04 import config, simulacao


def executar(cfg: dict) -> Path:
    """Roda o piloto e grava `simulacao.piloto` (caminho relativo à pasta do config)."""
    sim = config.simulacao(cfg)
    simulacao.rodar_grade(cfg, n_rep=sim["repeticoes_piloto"], saida=sim["piloto"])
    return Path(cfg["pasta"]) / sim["piloto"]


def main(argv=None) -> int:
    cfg = config.carregar(argv[0]) if argv else config.carregar()
    print(f"piloto gravado em {executar(cfg)}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv[1:]))
