import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from plotly import graph_objects as go

from lab04 import calibracao, gerador, graficos

PASTA = Path(__file__).resolve().parent.parent


def rng(semente=42):
    return np.random.default_rng(semente)


def tabela(com_bot, sem_bot):
    grupos = ["com_bot"] * len(com_bot) + ["sem_bot"] * len(sem_bot)
    return pd.DataFrame({"grupo": grupos, "horas_ate_merge": [*com_bot, *sem_bot]})


def ficticios(escala_sim=1.0, n=30):
    """Dados fictícios: reais e simulados lognormais, os simulados multiplicados por `escala_sim`."""
    reais = tabela(np.exp(rng(1).normal(2.7, 1.5, n)), np.exp(rng(2).normal(3.0, 1.8, n)))
    a, b = gerador.gerar_amostra({"familia": "lognormal", "mu": 2.7, "sigma": 1.6}, 0.35, n, rng(3))
    return reais, (a * escala_sim, b * escala_sim)


def test_fumaca_g1_devolve_figura_com_titulo_eixos_e_legenda():
    fig = graficos.g1(*ficticios())
    assert isinstance(fig, go.Figure)
    assert len(fig.data) == 4 and all(isinstance(t, go.Bar) for t in fig.data)
    assert fig.layout.title.text
    assert "Horas até o merge" in fig.layout.xaxis.title.text and "(h" in fig.layout.xaxis.title.text
    assert "Frequência" in fig.layout.yaxis.title.text and "PRs" in fig.layout.yaxis.title.text
    assert [t.name for t in fig.data if t.showlegend] == ["Com bot (A)", "Sem bot (B)"]
    assert [a.text.split(" (")[0] for a in fig.layout.annotations] == ["Dados reais", "Simulados: lognormal calibrada"]


def test_cores_do_mesmo_grupo_coincidem_nos_dois_paineis():
    fig = graficos.g1(*ficticios())
    for traco in fig.data:
        assert traco.marker.color == graficos.CORES_GRUPO[traco.legendgroup]
    assert {t.xaxis for t in fig.data} == {"x", "x2"}
    assert calibracao.qq_figura(ficticios()[0]).data[0].marker.color == graficos.CORES_GRUPO["com_bot"]


def test_contagens_somam_n_e_classes_sao_as_mesmas_nos_quatro_tracos():
    fig = graficos.g1(*ficticios(n=25))
    assert [sum(t.y) for t in fig.data] == [25] * 4
    for traco in fig.data[1:]:
        assert np.array_equal(traco.x, fig.data[0].x) and traco.width == fig.data[0].width


@pytest.mark.parametrize("escala_sim", [1e-5, 1e3])
def test_valores_pequenos_ou_escala_muito_diferente_cabem_no_eixo(escala_sim):
    fig = graficos.g1(*ficticios(escala_sim))
    assert [sum(t.y) for t in fig.data] == [30] * 4
    assert len(fig.data[0].x) <= graficos.MAX_CLASSES
    inicio, fim = fig.layout.xaxis.range
    simulados = np.log10(np.concatenate(ficticios(escala_sim)[1]))
    assert inicio <= simulados.min() and simulados.max() <= fim


def test_amplitude_enorme_alarga_as_classes():
    reais = tabela([1e-6, 1.0], [1.0, 1e6])
    fig = graficos.g1(reais, (np.array([1e-8]), np.array([1e8])))
    assert len(fig.data[0].x) <= graficos.MAX_CLASSES and fig.data[0].width > graficos.LARGURA_CLASSE
    assert [sum(t.y) for t in fig.data] == [2, 2, 1, 1]


def test_rotulos_do_eixo_sao_horas_no_formato_brasileiro():
    assert [graficos._rotulo_horas(e) for e in (-2, 0, 3)] == ["0,01", "1", "1.000"]


def test_zero_recebe_o_piso_e_negativo_ou_nan_levantam_erro():
    reais, (a, b) = ficticios()
    a = a.copy()
    a[0] = 0.0
    assert sum(graficos.g1(reais, (a, b)).data[2].y) == 30
    with pytest.raises(ValueError, match="simulados/sem_bot"):
        graficos.g1(reais, (a, np.array([1.0, -1.0])))
    with pytest.raises(ValueError, match="simulados/com_bot"):
        graficos.g1(reais, (np.array([np.nan]), b))
    with pytest.raises(ValueError, match="vetor"):
        graficos.g1(reais, (a.reshape(5, 6), b))


def test_sem_nenhuma_hora_levanta_erro():
    with pytest.raises(ValueError, match="não há horas"):
        graficos.g1(tabela([], []), (np.array([]), np.array([])))


def test_g1_com_os_dados_reais_e_a_calibracao_versionada():
    reais = pd.read_csv(PASTA / "dados" / "reais" / "prs.csv")
    exemplo = gerador.exemplos_calibrados(calibracao.ler(PASTA / "dados" / "reais" / "calibracao.json"))["com_efeito"]
    fig = graficos.g1(reais, (exemplo["a"], exemplo["b"]))
    assert [sum(t.y) for t in fig.data] == [30] * 4


def test_texto_do_g1_tem_de_2_a_4_frases():
    frases = [f for f in re.split(r"(?<=[.!?])\s+", graficos.TEXTO_G1.strip()) if f]
    assert 2 <= len(frases) <= 4
