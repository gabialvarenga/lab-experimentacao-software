"""Q3: interação servidor × `io_threads`, por carga (S02-01, adendo de 23/11/2026).

Regras em `docs/plano-analise.md`, seção 5.2, e no adendo de 23/11/2026 da seção 9:

- **Modelo.** Em cada carga, um modelo de dois fatores (servidor × `io_threads`, com o termo de
  interação) sobre o **logaritmo natural** da métrica. A pergunta se responde pelo termo de
  interação; os efeitos principais são reportados.
- **Método principal** (`escolher_metodo`, a regra 5.1 aplicada aos resíduos do modelo): ANOVA
  se os resíduos juntados das três cargas não rejeitam a normalidade (Shapiro-Wilk p ≥ α), a
  assimetria está entre −1 e 1 e o Levene não rejeita variâncias iguais nas 4 células de nenhuma
  carga; senão, **ART-ANOVA** (*Aligned Rank Transform*). O critério visual (gráfico
  quantil-quantil) fica no documento da análise do piloto.
- **Sensibilidade:** a ANOVA no log **com o bloco** (`repeticao`) como fator aditivo. A deriva
  da máquina entre blocos atinge as 4 células do bloco, e o termo de bloco a retira dos resíduos.
- **Efeito:** a razão das razões R = (mediana valkey 4 ÷ mediana valkey 1) ÷ (mediana redis 4 ÷
  mediana redis 1), com IC de 95% por *bootstrap* percentil (as 4 células reamostradas
  independentemente), e o η² parcial da interação do método principal.
- **Holm** sobre as 3 cargas de cada métrica (a família da Q3), no p da interação do principal.
  A situação da seção 6 do plano usa o p de Holm e o IC de R.

A ART segue Wobbrock et al. (2011), o método do pacote ARTool do R: para cada efeito, a resposta
alinhada é o resíduo do modelo completo somado à estimativa daquele efeito (pelas médias
marginais); os alinhados são ranqueados (postos médios nos empates) e a ANOVA completa é
ajustada nos postos, lendo-se só o termo do efeito alinhado. Aqui o alinhamento é feito no log da
métrica, como a ANOVA: em log, a interação é a razão das razões.
"""

import warnings

import numpy as np
import pandas as pd
import statsmodels.formula.api as smf
from scipy import stats
from statsmodels.stats.anova import anova_lm

from lab05 import testes

METRICAS = ["ops_s", "lat_p99_ms"]  # plano de análise, seção 5.2
METODOS = ("anova", "art")
TERMOS = {
    "servidor": "C(servidor, Sum)",
    "io_threads": "C(io_threads, Sum)",
    "interacao": "C(servidor, Sum):C(io_threads, Sum)",
}
SENSIBILIDADE = "anova_bloco"
COLUNAS = [
    "metrica", "carga", "teste", "n_por_celula",
    "mediana_valkey_1", "mediana_valkey_4", "mediana_redis_1", "mediana_redis_4",
    "razao_valkey", "razao_redis", "razao_das_razoes", "ic_inf", "ic_sup",
    "f_interacao", "p_interacao", "p_holm", "eta2_parcial", "p_servidor", "p_io_threads",
    "teste_sensibilidade", "p_sensibilidade", "eta2_parcial_sensibilidade", "testes_discordam", "situacao",
    "regra_metodo", "regra_shapiro_p", "regra_assimetria", "regra_levene_p_min", "regra_motivo",
]  # fmt: skip


def _preparar(df: pd.DataFrame, metrica: str, com_bloco: bool = False) -> pd.DataFrame:
    """Colunas do modelo (`y` = log da métrica), conferidas: 2 servidores, 2 níveis, 2+ por célula."""
    colunas = {"servidor", "io_threads", "carga", metrica} | ({"repeticao"} if com_bloco else set())
    faltam = colunas - set(df.columns)
    if faltam:
        raise ValueError(f"faltam as colunas {sorted(faltam)}")
    valores = pd.to_numeric(df[metrica], errors="coerce")
    if (valores.dropna() <= 0).any():
        raise ValueError(f"{metrica}: o log exige valores positivos")
    dados = df.assign(y=np.log(valores)).dropna(subset=["y"])
    if set(dados["servidor"]) != {testes.GRUPO_A, testes.GRUPO_B}:
        raise ValueError(f"a Q3 precisa dos dois servidores ({testes.GRUPO_A} e {testes.GRUPO_B})")
    if dados["io_threads"].nunique() != 2:
        raise ValueError("a Q3 precisa de exatamente 2 níveis de io_threads")
    contagem = dados.groupby(["carga", "servidor", "io_threads"]).size().unstack(["servidor", "io_threads"], fill_value=0)
    if contagem.shape[1] != 4 or (contagem < 2).any().any():
        raise ValueError("cada célula (servidor × io_threads) de cada carga precisa de ao menos 2 execuções")
    return dados


def residuos_modelo(df: pd.DataFrame, metrica: str) -> np.ndarray:
    """Resíduos do modelo completo de dois fatores no log, por carga: log(y) − média da sua célula."""
    dados = _preparar(df, metrica)
    medias = dados.groupby(["carga", "servidor", "io_threads"])["y"].transform("mean")
    return (dados["y"] - medias).to_numpy(dtype=float)


def escolher_metodo(df: pd.DataFrame, metrica: str, alfa: float = testes.ALFA) -> dict:
    """A regra 5.1 aplicada aos resíduos do modelo da Q3: `anova` ou `art`, uma vez por métrica.

    Devolve `metodo`, `shapiro_p`, `assimetria`, `levene_p_min` (o menor p do Levene, centro na
    mediana, entre as cargas), `n_residuos` e `motivo`. Resíduos sem variação dão `art`.
    """
    dados = _preparar(df, metrica)
    r = residuos_modelo(df, metrica)
    if np.ptp(r) == 0:
        return {"metodo": "art", "shapiro_p": float("nan"), "assimetria": float("nan"), "levene_p_min": float("nan"),
                "n_residuos": len(r), "motivo": "resíduos sem variação"}  # fmt: skip
    shapiro_p = float(stats.shapiro(r).pvalue)
    assimetria = float(stats.skew(r, bias=False))
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        levene_p_min = float(min(
            stats.levene(*[c["y"] for _, c in grupo.groupby(["servidor", "io_threads"])], center="median").pvalue
            for _, grupo in dados.groupby("carga")
        ))  # fmt: skip
    falhas = []
    if not shapiro_p >= alfa:
        falhas.append(f"Shapiro-Wilk rejeita a normalidade (p < {alfa:g})".replace(".", ","))
    if abs(assimetria) > testes.LIMITE_ASSIMETRIA:
        falhas.append("|assimetria| > 1")
    if not levene_p_min >= alfa:
        falhas.append(f"Levene rejeita variâncias iguais (p < {alfa:g})".replace(".", ","))
    metodo = "art" if falhas else "anova"
    motivo = "; ".join(falhas) if falhas else "Shapiro-Wilk e Levene não rejeitam e |assimetria| ≤ 1"
    return {"metodo": metodo, "shapiro_p": shapiro_p, "assimetria": assimetria, "levene_p_min": levene_p_min,
            "n_residuos": len(r), "motivo": motivo}  # fmt: skip


def _ajustar(dados: pd.DataFrame, resposta: str, com_bloco: bool = False) -> pd.DataFrame:
    """Tabela da ANOVA (tipo III, contrastes de soma) do modelo completo sobre `resposta`."""
    formula = f"{resposta} ~ C(servidor, Sum) * C(io_threads, Sum)" + (" + C(repeticao, Sum)" if com_bloco else "")
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return anova_lm(smf.ols(formula, data=dados).fit(), typ=3)


def _termo(tabela: pd.DataFrame, termo: str) -> dict:
    ss, ss_res = tabela.loc[termo, "sum_sq"], tabela.loc["Residual", "sum_sq"]
    total = ss + ss_res
    return {
        "f": float(tabela.loc[termo, "F"]),
        "p": float(tabela.loc[termo, "PR(>F)"]),
        "eta2_parcial": float(ss / total) if total > 0 else float("nan"),
    }


def anova(dados: pd.DataFrame, com_bloco: bool = False) -> dict:
    """ANOVA no log (`y`) de uma carga: `{"servidor": {...}, "io_threads": {...}, "interacao": {...}}`.

    Cada termo tem `f`, `p` e `eta2_parcial` (SS do termo ÷ (SS do termo + SS residual)).
    """
    tabela = _ajustar(dados, "y", com_bloco)
    return {nome: _termo(tabela, termo) for nome, termo in TERMOS.items()}


def alinhar(dados: pd.DataFrame, efeito: str) -> np.ndarray:
    """Resposta alinhada da ART para `efeito` (`servidor`, `io_threads` ou `interacao`).

    Resíduo do modelo completo (`y` − média da célula) + a estimativa do efeito pelas médias
    marginais: servidor = média do servidor − média geral; idem para `io_threads`; interação =
    média da célula − média do servidor − média do nível + média geral.
    """
    y = dados["y"]
    geral = y.mean()
    celula = y.groupby([dados["servidor"], dados["io_threads"]]).transform("mean")
    servidor = y.groupby(dados["servidor"]).transform("mean")
    threads = y.groupby(dados["io_threads"]).transform("mean")
    estimativa = {
        "servidor": servidor - geral,
        "io_threads": threads - geral,
        "interacao": celula - servidor - threads + geral,
    }
    if efeito not in estimativa:
        raise ValueError(f"efeito '{efeito}' desconhecido; use {', '.join(estimativa)}")
    return ((y - celula) + estimativa[efeito]).to_numpy(dtype=float)


def art(dados: pd.DataFrame) -> dict:
    """ART-ANOVA de uma carga: cada efeito com o seu alinhamento e a ANOVA completa nos postos."""
    saida = {}
    for nome, termo in TERMOS.items():
        postos = dados.assign(postos=stats.rankdata(alinhar(dados, nome)))
        saida[nome] = _termo(_ajustar(postos, "postos"), termo)
    return saida


def _medianas(dados: pd.DataFrame, metrica: str) -> dict:
    baixo, alto = sorted(dados["io_threads"].unique())
    valores = {(s, t): g[metrica].to_numpy(dtype=float) for (s, t), g in dados.groupby(["servidor", "io_threads"])}
    return {"baixo": baixo, "alto": alto, "valores": valores}


def razao_das_razoes(v_baixo, v_alto, r_baixo, r_alto) -> float:
    """R = (mediana v_alto ÷ mediana v_baixo) ÷ (mediana r_alto ÷ mediana r_baixo)."""
    m = [float(np.median(x)) for x in (v_baixo, v_alto, r_baixo, r_alto)]
    return (m[1] / m[0]) / (m[3] / m[2])


def ic_razao_das_razoes(v_baixo, v_alto, r_baixo, r_alto, rng=None, n_boot: int = testes.N_BOOTSTRAP,
                        confianca: float = testes.CONFIANCA) -> tuple:  # fmt: skip
    """IC de R por *bootstrap* percentil: as 4 células reamostradas independentemente, nesta ordem."""
    rng = np.random.default_rng(testes.SEMENTE_PADRAO) if rng is None else rng
    medianas = []
    for x in (v_baixo, v_alto, r_baixo, r_alto):
        x = np.asarray(x, dtype=float)
        medianas.append(np.median(x[rng.integers(0, len(x), (n_boot, len(x)))], axis=1))
    razoes = (medianas[1] / medianas[0]) / (medianas[3] / medianas[2])
    inf, sup = np.percentile(razoes, [100 * (1 - confianca) / 2, 100 * (1 + confianca) / 2])
    return float(inf), float(sup)


def analisar(
    df: pd.DataFrame,
    metrica: str,
    metodo: str | None = None,
    rng=None,
    n_boot: int = testes.N_BOOTSTRAP,
    diferenca: float = testes.DIFERENCA_RELEVANTE,
    alfa: float = testes.ALFA,
) -> pd.DataFrame:
    """A Q3 de uma métrica: uma linha por carga, com as colunas de `COLUNAS`.

    `metodo` (`anova` ou `art`; sem ele, o de `escolher_metodo` sobre o próprio `df`) é o
    principal, corrigido por Holm entre as cargas. As colunas `regra_*` registram o que a regra
    daria no `df`, mesmo quando `metodo` vem fixado (no `analisar`, pelo `config.yaml`). A sensibilidade é sempre a ANOVA no log com o
    bloco (`repeticao`); sem essa coluna, `p_sensibilidade` sai NaN. `testes_discordam` compara
    as decisões dos dois, sem correção, em `alfa`. `rng` é usado no *bootstrap*, na ordem das
    cargas.
    """
    regra = escolher_metodo(df, metrica, alfa)
    metodo = regra["metodo"] if metodo is None else metodo
    if metodo not in METODOS:
        raise ValueError(f"método '{metodo}' desconhecido; use {' ou '.join(METODOS)}")
    com_bloco = "repeticao" in df.columns
    dados = _preparar(df, metrica)
    rng = np.random.default_rng(testes.SEMENTE_PADRAO) if rng is None else rng
    linhas = []
    for carga, grupo in dados.groupby("carga", sort=True):
        principal = (anova if metodo == "anova" else art)(grupo)
        sensibilidade = anova(grupo, com_bloco=True)["interacao"] if com_bloco else {"p": float("nan"), "eta2_parcial": float("nan")}
        m = _medianas(grupo, metrica)
        v = m["valores"]
        celulas = (v[testes.GRUPO_A, m["baixo"]], v[testes.GRUPO_A, m["alto"]], v[testes.GRUPO_B, m["baixo"]], v[testes.GRUPO_B, m["alto"]])
        med = [float(np.median(c)) for c in celulas]
        ic_inf, ic_sup = ic_razao_das_razoes(*celulas, rng, n_boot)
        linhas.append({
            "metrica": metrica, "carga": carga, "teste": metodo, "n_por_celula": min(len(c) for c in celulas),
            "mediana_valkey_1": med[0], "mediana_valkey_4": med[1], "mediana_redis_1": med[2], "mediana_redis_4": med[3],
            "razao_valkey": med[1] / med[0], "razao_redis": med[3] / med[2], "razao_das_razoes": razao_das_razoes(*celulas),
            "ic_inf": ic_inf, "ic_sup": ic_sup,
            "f_interacao": principal["interacao"]["f"], "p_interacao": principal["interacao"]["p"],
            "eta2_parcial": principal["interacao"]["eta2_parcial"],
            "p_servidor": principal["servidor"]["p"], "p_io_threads": principal["io_threads"]["p"],
            "teste_sensibilidade": SENSIBILIDADE, "p_sensibilidade": sensibilidade["p"],
            "eta2_parcial_sensibilidade": sensibilidade["eta2_parcial"],
            "regra_metodo": regra["metodo"], "regra_shapiro_p": regra["shapiro_p"], "regra_assimetria": regra["assimetria"],
            "regra_levene_p_min": regra["levene_p_min"], "regra_motivo": regra["motivo"],
        })  # fmt: skip
    tabela = pd.DataFrame(linhas)
    tabela["p_holm"] = testes.holm(tabela["p_interacao"].to_numpy())
    tabela["testes_discordam"] = tabela["p_sensibilidade"].notna() & (
        (tabela["p_interacao"] < alfa) != (tabela["p_sensibilidade"] < alfa)
    )
    tabela["situacao"] = [testes.situacao(l.p_holm, l.ic_inf, l.ic_sup, diferenca, alfa) for l in tabela.itertuples()]
    return tabela[COLUNAS]
