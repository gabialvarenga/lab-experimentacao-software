"""Coletas sintéticas no formato do CSV da S01-07, para os testes da análise (S01-09)."""

from pathlib import Path

import numpy as np
import pandas as pd
import pytest

PILOTO = Path(__file__).resolve().parent.parent / "dados" / "piloto" / "piloto.csv"
BASES = {"ops_s": 80_000.0, "lat_p50_ms": 0.6, "lat_p99_ms": 1.1, "memoria_bytes": 17_000_000.0}


def coleta_sintetica(n=10, razao=1.0, sigma=0.1, semente=0, razao_threads4=None) -> pd.DataFrame:
    """2 servidores × 2 `io_threads` × 3 cargas × `n` repetições, com métricas lognormais.

    O Valkey tem mediana `razao` vezes a do Redis (com 4 threads, `razao_threads4`, se dado).
    """
    rng = np.random.default_rng(semente)
    linhas = []
    for repeticao in range(1, n + 1):
        for servidor in ("redis", "valkey"):
            for threads in (1, 4):
                for carga in ("get", "misto", "set"):
                    r = razao if threads == 1 or razao_threads4 is None else razao_threads4
                    fator = r if servidor == "valkey" else 1.0
                    linha = {"servidor": servidor, "io_threads": threads, "carga": carga, "repeticao": repeticao}
                    for metrica, base in BASES.items():
                        linha[metrica] = base * fator * float(np.exp(sigma * rng.standard_normal()))
                    linhas.append(linha)
    return pd.DataFrame(linhas)


@pytest.fixture
def piloto() -> pd.DataFrame:
    return pd.read_csv(PILOTO)
