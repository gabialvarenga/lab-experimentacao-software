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


CHAVES_DA_SIMULACAO = ("repeticoes", "repeticoes_piloto", "alfas", "confianca_ic", "piloto", "saida", "cenarios")
CHAVES_DO_CENARIO = ("id", "familia", "mu", "sigma", "n", "efeitos", "unidade_efeito")
MIN_EFEITOS = 5


def simulacao(cfg: dict) -> dict:
    """Seção `simulacao` do config, validada (S02-01).

    Exige as chaves de `CHAVES_DA_SIMULACAO`, alfas em (0, 1), nível do IC em (0, 1), ids de
    cenário únicos e, em cada cenário, as chaves de `CHAVES_DO_CENARIO` e uma grade de efeitos com
    pelo menos `MIN_EFEITOS` valores, estritamente crescentes e começando em 0 (a hipótese nula).
    Levanta `ValueError` com a mensagem do primeiro problema.
    """
    sim = cfg.get("simulacao")
    if not sim:
        raise ValueError("falta a seção 'simulacao' no config")
    for chave in CHAVES_DA_SIMULACAO:
        if chave not in sim:
            raise ValueError(f"simulacao: falta a chave '{chave}'")
    for chave in ("repeticoes", "repeticoes_piloto"):
        if isinstance(sim[chave], bool) or not isinstance(sim[chave], int) or sim[chave] < 1:
            raise ValueError(f"simulacao.{chave} deve ser um inteiro positivo")
    if not sim["alfas"] or not all(0 < a < 1 for a in sim["alfas"]):
        raise ValueError("simulacao.alfas deve ser uma lista de valores em (0, 1)")
    if not 0 < sim["confianca_ic"] < 1:
        raise ValueError("simulacao.confianca_ic deve estar em (0, 1)")
    ids = [c.get("id") for c in sim["cenarios"]]
    if not ids or len(set(ids)) != len(ids):
        raise ValueError("simulacao.cenarios precisa de ids únicos")
    for cenario in sim["cenarios"]:
        for chave in CHAVES_DO_CENARIO:
            if chave not in cenario:
                raise ValueError(f"cenário {cenario.get('id')}: falta a chave '{chave}'")
        efeitos = cenario["efeitos"]
        if len(efeitos) < MIN_EFEITOS:
            raise ValueError(f"cenário {cenario['id']}: a grade precisa de ao menos {MIN_EFEITOS} efeitos")
        if efeitos[0] != 0:
            raise ValueError(f"cenário {cenario['id']}: a grade de efeitos deve começar em 0")
        if any(b <= a for a, b in zip(efeitos, efeitos[1:])):
            raise ValueError(f"cenário {cenario['id']}: a grade de efeitos deve ser estritamente crescente")
    return sim
