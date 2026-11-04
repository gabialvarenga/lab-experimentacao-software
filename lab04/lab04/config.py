"""Leitura do `config.yaml`, do token do GitHub e criação do gerador de números aleatórios."""

import os
from pathlib import Path

import numpy as np
import yaml

CONFIG_PADRAO = Path(__file__).resolve().parent.parent / "config.yaml"
VARIAVEL_DO_TOKEN = "GITHUB_TOKEN"


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


def token() -> str:
    """Token do GitHub, lido de `GITHUB_TOKEN`. Nunca é escrito em arquivo nem em log."""
    valor = os.environ.get(VARIAVEL_DO_TOKEN, "").strip()
    if not valor:
        raise ValueError(
            f"a variável de ambiente {VARIAVEL_DO_TOKEN} não está definida. Defina-a com um token do GitHub: "
            f'$env:{VARIAVEL_DO_TOKEN} = "<token>" (PowerShell) ou export {VARIAVEL_DO_TOKEN}=<token> (bash)'
        )
    return valor
