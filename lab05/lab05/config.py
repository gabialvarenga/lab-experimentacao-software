"""Leitura do `config.yaml` e criação do gerador de números aleatórios.

Origem: copiado de `lab04/lab04/config.py`, sem a parte do token do GitHub e da simulação.
O Lab05 não importa de `lab04/`: cada laboratório roda sozinho.
"""

from pathlib import Path

import numpy as np
import yaml

CONFIG_PADRAO = Path(__file__).resolve().parent.parent / "config.yaml"


def carregar(caminho=CONFIG_PADRAO) -> dict:
    """Lê o YAML, exige a chave `semente` e acrescenta `pasta` (onde o arquivo está).

    Os caminhos relativos do config valem a partir de `pasta`.
    """
    with open(caminho, encoding="utf-8") as arquivo:
        cfg = yaml.safe_load(arquivo) or {}
    if "semente" not in cfg:
        raise ValueError(f"{caminho}: falta a chave 'semente'")
    cfg["pasta"] = str(Path(caminho).resolve().parent)
    return cfg


def criar_rng(cfg: dict) -> np.random.Generator:
    """Gerador com a semente fixa do config (`default_rng(42)` no padrão)."""
    return np.random.default_rng(cfg["semente"])
