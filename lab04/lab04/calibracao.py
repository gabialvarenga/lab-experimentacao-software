"""Parâmetros da lognormal estimados dos dados reais (S01-06).

O tempo até o merge de cada grupo é modelado como lognormal: log(horas) ~ Normal(μ, σ). Os
estimadores são a média (μ) e o desvio-padrão amostral, com n − 1 (σ), de log(horas); a
mediana implícita é e^μ. `calibrar(df)` devolve, por grupo:

    {"com_bot": {"mu": ..., "sigma": ..., ...}, "sem_bot": {...}}

`mu` e `sigma` são o valor central que entra na simulação de referência (cenário C1). Os demais
campos registram a incerteza e o ajuste:

- `mu_ic` e `sigma_ic`: IC de `confianca` (95% por padrão); de μ pela t de Student e de σ pela
  qui-quadrado, `sigma · sqrt((n − 1) / χ²)`. Ambos supõem log(horas) normal, que é justamente
  a hipótese da lognormal;
- `sigma_ic_bootstrap`: o mesmo IC de σ por percentis do bootstrap, para conferir a versão
  paramétrica sem depender da normalidade;
- `ajuste`: Shapiro-Wilk, correlação do QQ-plot e assimetria de log(horas). Um ajuste ruim
  (`bom = False`, Shapiro com p < 0,05) é registrado, e a calibração segue mesmo assim.

Horas iguais a zero: o log é indefinido, então, se o grupo tem alguma hora ≤ 0, soma-se o piso
`PISO_HORAS` (0,01 h, cerca de 36 s) a todas as horas do grupo antes de tomar o log, o que
preserva a ordem e as razões entre os valores. O piso usado fica em `piso_somado` (0 se
nenhum). Horas negativas são erro nos dados e levantam `ValueError`. No protocolo de coleta só
entram PRs com mais de 1 h até o merge, então o piso não chega a ser usado nos dados reais.
"""

import json
import math
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats

from lab04 import config, descritiva
from lab04.descritiva import GRUPOS, horas_do_grupo

PISO_HORAS = 0.01
CONFIANCA = 0.95
REPS_BOOTSTRAP = 10_000
SEMENTE_PADRAO = 42
MIN_PRS = 3  # abaixo disso não há σ com IC útil nem teste de normalidade
AVISO_PRS = 10  # abaixo disso a estimativa é calculada, mas muito imprecisa
ALFA_AJUSTE = 0.05


def logaritmos(horas, piso: float = PISO_HORAS) -> tuple:
    """`(log(horas), piso_somado)`; o piso é somado a todas as horas só se alguma for ≤ 0."""
    x = np.asarray(horas, dtype=float)
    if np.isnan(x).any() or (x < 0).any():
        raise ValueError("as horas devem ser números não negativos")
    somado = 0.0
    if (x <= 0).any():
        if not piso > 0:
            raise ValueError("há horas iguais a zero e o piso não é positivo")
        somado = float(piso)
    return np.log(x + somado), somado


def _ic(inferior: float, superior: float) -> list:
    return [float(inferior), float(superior)]


def ajuste_normal(logs: np.ndarray) -> dict:
    """Shapiro-Wilk, correlação do QQ-plot e assimetria de log(horas).

    Sem variação (todos iguais) o ajuste não se avalia: os campos ficam `None`.
    """
    if np.ptp(logs) == 0:
        return {"shapiro_p": None, "qq_r": None, "assimetria_log": None, "bom": None}
    p = float(stats.shapiro(logs).pvalue)
    r = float(stats.probplot(logs, dist="norm")[1][2])
    return {
        "shapiro_p": p,
        "qq_r": r,
        "assimetria_log": float(stats.skew(logs, bias=False)),
        "bom": bool(p >= ALFA_AJUSTE),
    }


def estimar_grupo(horas, piso=PISO_HORAS, confianca=CONFIANCA, reps=REPS_BOOTSTRAP, rng=None) -> dict:
    """Parâmetros da lognormal de um grupo, com ICs e o ajuste (ver o docstring do módulo)."""
    logs, somado = logaritmos(horas, piso)
    n = len(logs)
    if n < MIN_PRS:
        raise ValueError(f"são necessários ao menos {MIN_PRS} PRs por grupo, há {n}")
    if rng is None:
        rng = np.random.default_rng(SEMENTE_PADRAO)
    alfa = 1 - confianca
    gl = n - 1
    mu = float(logs.mean())
    sigma = float(logs.std(ddof=1))

    qui_inf, qui_sup = stats.chi2.ppf([alfa / 2, 1 - alfa / 2], gl)
    erro_mu = stats.t.ppf(1 - alfa / 2, gl) * sigma / math.sqrt(n)
    sorteio = rng.integers(0, n, size=(reps, n))
    sigmas_boot = logs[sorteio].std(axis=1, ddof=1)
    boot_inf, boot_sup = np.percentile(sigmas_boot, [100 * alfa / 2, 100 * (1 - alfa / 2)])

    resultado = {
        "n": n,
        "mu": mu,
        "sigma": sigma,
        "mediana_implicita": math.exp(mu),
        "confianca": confianca,
        "mu_ic": _ic(mu - erro_mu, mu + erro_mu),
        "sigma_ic": _ic(sigma * math.sqrt(gl / qui_sup), sigma * math.sqrt(gl / qui_inf)),
        "sigma_ic_bootstrap": _ic(boot_inf, boot_sup),
        "piso_somado": somado,
        "ajuste": ajuste_normal(logs),
    }
    if n < AVISO_PRS:
        resultado["aviso"] = f"apenas {n} PRs: estimativas muito imprecisas"
    return resultado


def calibrar(df: pd.DataFrame, *, piso=PISO_HORAS, confianca=CONFIANCA, reps=REPS_BOOTSTRAP, rng=None) -> dict:
    """`{"com_bot": {"mu", "sigma", ...}, "sem_bot": {...}}` a partir das horas até o merge.

    O `rng` do bootstrap é compartilhado pelos dois grupos, em ordem; sem `rng`, usa-se
    `default_rng(42)`. Levanta `ValueError` se um grupo tem menos de `MIN_PRS` PRs.
    """
    if rng is None:
        rng = np.random.default_rng(SEMENTE_PADRAO)
    calibracao = {}
    for grupo in GRUPOS:
        horas = horas_do_grupo(df, grupo)
        try:
            calibracao[grupo] = estimar_grupo(horas, piso, confianca, reps, rng)
        except ValueError as erro:
            raise ValueError(f"grupo {grupo}: {erro}") from erro
    return calibracao


def gravar(calibracao: dict, caminho) -> None:
    """Grava a calibração em JSON (UTF-8, indentado, com quebra de linha final)."""
    caminho = Path(caminho)
    caminho.parent.mkdir(parents=True, exist_ok=True)
    texto = json.dumps(calibracao, indent=2, ensure_ascii=False)
    caminho.write_text(texto + "\n", encoding="utf-8", newline="\n")


def ler(caminho) -> dict:
    """Lê o JSON gravado por `gravar`."""
    return json.loads(Path(caminho).read_text(encoding="utf-8"))


def qq_pontos(horas, piso: float = PISO_HORAS) -> dict:
    """Pontos do QQ-plot de log(horas) contra a normal, e a reta ajustada.

    Devolve `teoricos` (quantis da normal padrão), `observados` (as horas ordenadas, na escala
    original), `reta` (as horas previstas pela lognormal ajustada em cada quantil teórico,
    `exp(μ + σ · z)`) e `r`, a correlação do QQ-plot.
    """
    logs, somado = logaritmos(horas, piso)
    (teoricos, _), (inclinacao, intercepto, r) = stats.probplot(logs, dist="norm")
    return {
        "teoricos": teoricos,
        "observados": np.sort(np.asarray(horas, dtype=float)),
        "reta": np.exp(intercepto + inclinacao * teoricos) - somado,
        "r": float(r),
    }


def qq_figura(df: pd.DataFrame, piso: float = PISO_HORAS):
    """QQ-plot de log(horas) de cada grupo contra a normal, com o eixo das horas em escala log.

    Pontos sobre a reta indicam que a lognormal descreve bem o grupo.
    """
    from plotly import graph_objects as go
    from plotly.subplots import make_subplots

    figura = make_subplots(rows=1, cols=len(GRUPOS), subplot_titles=[f"{g} (r = …)" for g in GRUPOS])
    cores = {"com_bot": "#1f77b4", "sem_bot": "#ff7f0e"}
    for coluna, grupo in enumerate(GRUPOS, start=1):
        pontos = qq_pontos(horas_do_grupo(df, grupo), piso)
        figura.layout.annotations[coluna - 1].text = f"{grupo} (r = {pontos['r']:.3f})"
        figura.add_trace(
            go.Scatter(x=pontos["teoricos"], y=pontos["observados"], mode="markers", name=grupo,
                       marker={"color": cores[grupo]}),
            row=1, col=coluna,
        )
        figura.add_trace(
            go.Scatter(x=pontos["teoricos"], y=pontos["reta"], mode="lines", name="lognormal ajustada",
                       line={"color": "gray", "dash": "dash"}, showlegend=coluna == 1),
            row=1, col=coluna,
        )
        figura.update_xaxes(title_text="Quantil teórico da normal padrão", row=1, col=coluna)
        figura.update_yaxes(title_text="Horas até o merge (escala log)", type="log", row=1, col=coluna)
    figura.update_layout(title="QQ-plot de log(horas até o merge) contra a normal", template="plotly_white")
    return figura


def executar(cfg: dict) -> dict:
    """Lê `prs.csv`, grava a tabela descritiva, `calibracao.json` e o QQ-plot, e resume no terminal.

    Os caminhos e os parâmetros vêm do bloco `calibracao` do config; a entrada é a saída da coleta.
    """
    c = cfg["calibracao"]
    base = Path(cfg["pasta"])
    df = pd.read_csv(base / cfg["coleta"]["saida"])
    tabela = descritiva.descrever(df)
    calibracao = calibrar(
        df, piso=c["piso_horas"], confianca=c["confianca"], reps=c["repeticoes_bootstrap"], rng=config.criar_rng(cfg)
    )

    (base / c["descritiva"]).parent.mkdir(parents=True, exist_ok=True)
    tabela.to_csv(base / c["descritiva"], float_format="%.4f", lineterminator="\n")
    gravar(calibracao, base / c["saida"])
    caminho_qq = base / c["qqplot"]
    caminho_qq.parent.mkdir(parents=True, exist_ok=True)
    qq_figura(df, c["piso_horas"]).write_html(caminho_qq, include_plotlyjs="cdn")

    for grupo, p in calibracao.items():
        ajuste = {True: "bom", False: "ruim", None: "não avaliado"}[p["ajuste"]["bom"]]
        print(
            f"{grupo}: n = {p['n']}, μ = {p['mu']:.4f}, σ = {p['sigma']:.4f} "
            f"(IC {p['sigma_ic'][0]:.4f} a {p['sigma_ic'][1]:.4f}), mediana = {p['mediana_implicita']:.2f} h, "
            f"ajuste {ajuste}"
        )
    print(f"Gravados: {base / c['descritiva']}, {base / c['saida']} e {caminho_qq}")
    return calibracao
