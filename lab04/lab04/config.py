"""Leitura do `config.yaml` e criação do gerador de números aleatórios."""

from pathlib import Path

import numpy as np
import yaml

CONFIG_PADRAO = Path(__file__).resolve().parent.parent / "config.yaml"


def carregar(caminho=CONFIG_PADRAO) -> dict:
    """Lê o YAML e exige a chave `semente`."""
    with open(caminho, encoding="utf-8") as arquivo:
        cfg = yaml.safe_load(arquivo) or {}
    if "semente" not in cfg:
        raise ValueError(f"{caminho}: falta a chave 'semente'")
    return cfg


def criar_rng(cfg: dict) -> np.random.Generator:
    """Gerador com a semente fixa do config (`default_rng(42)` no padrão)."""
    return np.random.default_rng(cfg["semente"])
