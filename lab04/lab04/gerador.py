"""Gerador de dados simulados: gerar_amostra, gerar_lote e os exemplos da S01-08 (S01-07, S01-08).

Um `cenario` é um dicionário com:

- `familia`: `"normal"` ou `"lognormal"`;
- `mu` e `sigma`: parâmetros da normal (na lognormal, de log(x)); `sigma` ≥ 0;
- `contaminacao` (opcional): `{"p": ..., "fator": ...}`.

Os dois grupos (A e B) são amostras independentes. O grupo A vem de `mu` e `sigma`; o grupo B é
o A com o efeito `delta` (δ):

- normal: a média de B é `mu + delta · sigma` (δ em unidades de desvio-padrão);
- lognormal: o μ de B é `mu + delta` (razão de medianas B/A = e^δ).

Com δ = 0 os dois grupos têm a mesma distribuição.

Contaminação: cada observação, nos dois grupos, é multiplicada por `fator` com probabilidade `p`
(sorteio independente por observação, então a fração de valores extremos é p em média, para
qualquer `n`). Com `p = 0` ou sem `contaminacao` não há outliers; com `p = 1` todos os valores são
multiplicados.

A ordem dos sorteios é fixa: primeiro as normais padrão de A e de B, depois, só se `0 < p < 1`, os
sorteios da contaminação. Por isso, com a mesma semente, os dados de um cenário com e sem
contaminação são os mesmos até a multiplicação. O `rng` é um `numpy.random.Generator` e avança a
cada chamada: reutilizá-lo dá amostras novas, e um gerador novo com a mesma semente repete os
dados. `gerar_amostra` é `gerar_lote` com `n_rep = 1`, então os dois usam os mesmos números.
"""

import math

import numpy as np

from lab04 import testes

FAMILIAS = ("normal", "lognormal")


def _numero(cenario: dict, chave: str) -> float:
    try:
        valor = float(cenario[chave])
    except KeyError:
        raise ValueError(f"o cenário precisa da chave '{chave}'") from None
    if not math.isfinite(valor):
        raise ValueError(f"'{chave}' deve ser um número finito")
    return valor


def _contaminacao(cenario: dict):
    """`(p, fator)` validados, ou `(0.0, 1.0)` se o cenário não tem contaminação."""
    contaminacao = cenario.get("contaminacao")
    if not contaminacao:
        return 0.0, 1.0
    p, fator = _numero(contaminacao, "p"), _numero(contaminacao, "fator")
    if not 0 <= p <= 1:
        raise ValueError("a contaminação 'p' deve estar em [0, 1]")
    if fator <= 0:
        raise ValueError("a contaminação 'fator' deve ser positivo")
    return p, fator


def _inteiro_positivo(valor, nome: str) -> int:
    if isinstance(valor, bool) or not isinstance(valor, (int, np.integer)) or valor < 1:
        raise ValueError(f"{nome} deve ser um inteiro positivo")
    return int(valor)


def gerar_lote(cenario: dict, delta: float, n: int, n_rep: int, rng) -> tuple:
    """`n_rep` pares de amostras de tamanho `n`: devolve `(A, B)`, cada um com formato `(n_rep, n)`.

    Levanta `ValueError` para família desconhecida, parâmetro ausente ou inválido (`sigma` < 0,
    `p` fora de [0, 1], `fator` ≤ 0, `delta` não finito, `n` ou `n_rep` não positivos) e
    `TypeError` se `rng` não for um `numpy.random.Generator`.
    """
    if not isinstance(rng, np.random.Generator):
        raise TypeError("rng deve ser um numpy.random.Generator")
    familia = cenario.get("familia")
    if familia not in FAMILIAS:
        raise ValueError(f"família '{familia}' desconhecida; use {' ou '.join(FAMILIAS)}")
    mu, sigma = _numero(cenario, "mu"), _numero(cenario, "sigma")
    if sigma < 0:
        raise ValueError("sigma não pode ser negativo")
    if not math.isfinite(delta):
        raise ValueError("delta deve ser um número finito")
    n, n_rep = _inteiro_positivo(n, "n"), _inteiro_positivo(n_rep, "n_rep")
    p, fator = _contaminacao(cenario)

    deslocamento = delta * sigma if familia == "normal" else delta
    a = mu + sigma * rng.standard_normal((n_rep, n))
    b = mu + deslocamento + sigma * rng.standard_normal((n_rep, n))
    if familia == "lognormal":
        a, b = np.exp(a), np.exp(b)

    if p > 0:
        for grupo in (a, b):
            extremos = np.ones(grupo.shape, dtype=bool) if p == 1 else rng.random(grupo.shape) < p
            grupo[extremos] *= fator
    return a, b


def gerar_amostra(cenario: dict, delta: float, n: int, rng) -> tuple:
    """Um par de amostras `(A, B)`, cada uma com `n` valores (ver `gerar_lote`)."""
    a, b = gerar_lote(cenario, delta, n, 1, rng)
    return a[0], b[0]


# Exemplos da S01-08. As sementes foram fixadas antes de qualquer p-valor ser visto (datas das
# entregas: 04/11 e 05/11) e não mudam; n = 30 por grupo é o tamanho do cenário de referência.
SEMENTE_SEM_EFEITO = 20261104
SEMENTE_COM_EFEITO = 20261105
N_EXEMPLO = 30


def exemplo_simulado(cenario: dict, delta: float, n: int, semente: int) -> dict:
    """Gera um par de amostras com semente fixa e aplica Welch e Mann-Whitney (S01-08).

    Devolve `cenario`, `delta`, `n`, `semente`, as amostras `a` e `b` e o `resultado` de
    `testes.aplicar_testes(a, b)`. O G2 (S01-10) lê desse dicionário. A mesma semente dá sempre
    o mesmo exemplo.
    """
    a, b = gerar_amostra(cenario, delta, n, np.random.default_rng(semente))
    return {
        "cenario": cenario,
        "delta": delta,
        "n": n,
        "semente": semente,
        "a": a,
        "b": b,
        "resultado": testes.aplicar_testes(a, b),
    }


def cenario_calibrado(calibracao: dict) -> tuple:
    """`(cenario, delta)` da lognormal de referência (C1) a partir da calibração (S01-06).

    O grupo A é o `com_bot`: `mu` é o dele. O `sigma` é a raiz da média das variâncias de
    log(horas) dos dois grupos, porque o gerador usa um σ só. O `delta` é a diferença observada
    entre os μ dos grupos (`sem_bot` − `com_bot`), de modo que B reproduz a mediana implícita
    do `sem_bot` (razão de medianas e^δ).
    """
    com, sem = calibracao["com_bot"], calibracao["sem_bot"]
    sigma = math.sqrt((com["sigma"] ** 2 + sem["sigma"] ** 2) / 2)
    cenario = {"familia": "lognormal", "mu": com["mu"], "sigma": sigma}
    return cenario, sem["mu"] - com["mu"]


def exemplos_calibrados(calibracao: dict) -> dict:
    """Os dois exemplos da S01-08, `sem_efeito` (δ = 0) e `com_efeito` (δ da calibração)."""
    cenario, delta = cenario_calibrado(calibracao)
    return {
        "sem_efeito": exemplo_simulado(cenario, 0.0, N_EXEMPLO, SEMENTE_SEM_EFEITO),
        "com_efeito": exemplo_simulado(cenario, delta, N_EXEMPLO, SEMENTE_COM_EFEITO),
    }
