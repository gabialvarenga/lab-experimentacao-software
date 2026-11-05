import re
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from plotly import graph_objects as go
from scipy import stats

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


# G2 (S01-10)

NORMAL = {"familia": "normal", "mu": 10.0, "sigma": 2.0}


def exemplos():
    return gerador.exemplos_calibrados(calibracao.ler(PASTA / "dados" / "reais" / "calibracao.json"))


def tracos(fig, prefixo):
    return [t for t in fig.data if (t.name or "").startswith(prefixo)]


@pytest.mark.parametrize("caso, titulo", [("sem_efeito", "sem efeito (δ = 0)"), ("com_efeito", "com efeito (δ = 0,35)")])
def test_fumaca_g2_tem_dois_paineis_titulo_eixos_e_legenda(caso, titulo):
    fig = graficos.g2(exemplos()[caso])
    assert isinstance(fig, go.Figure)
    assert titulo in fig.layout.title.text
    assert [a.text for a in fig.layout.annotations[:2]] == ["Welch", "Mann-Whitney"]
    assert "t de Welch" in fig.layout.xaxis.title.text and "z do Mann-Whitney" in fig.layout.xaxis2.title.text
    assert all("(adimensional)" in e.title.text for e in (fig.layout.xaxis, fig.layout.xaxis2))
    assert fig.layout.yaxis.title.text == fig.layout.yaxis2.title.text == "Densidade de probabilidade"
    legenda = [t.name for t in fig.data if t.showlegend is not False]
    for nome in ("Simulação sob H₀", "Região de rejeição", "Welch: curva", "Welch: p-valor", "Welch: t observado",
                 "Mann-Whitney: curva", "Mann-Whitney: p-valor", "Mann-Whitney: z observado"):
        assert sum(n.startswith(nome) for n in legenda) == 1, nome


def test_cores_dos_testes_vem_de_cores_teste():
    fig = graficos.g2(exemplos()["sem_efeito"])
    for teste, nome in graficos.NOMES_TESTE.items():
        cor = graficos.CORES_TESTE[teste]
        for traco in tracos(fig, f"{nome}:"):
            assert cor in (traco.line.color, traco.fillpattern.fgcolor)
    assert set(graficos.CORES_TESTE.values()).isdisjoint(graficos.CORES_GRUPO.values())


def test_p_valor_hachurado_deixa_ver_a_regiao_de_rejeicao_solida_por_baixo():
    fig = graficos.g2(exemplos()["sem_efeito"])
    rejeicao = tracos(fig, "Região de rejeição")
    p_valor = tracos(fig, "Welch: p-valor") + tracos(fig, "Mann-Whitney: p-valor")
    assert len(rejeicao) == len(p_valor) == 4
    assert all(t.fillcolor == graficos.COR_REJEICAO_AREA and not t.fillpattern.shape for t in rejeicao)
    assert all(t.fillpattern.shape == "/" and t.fillcolor == "rgba(0,0,0,0)" for t in p_valor)
    # em cada painel a região de rejeição vem antes, então fica por baixo da hachura
    for eixo in ("x", "x2"):
        ordem = [i for i, t in enumerate(fig.data) if t in rejeicao and t.xaxis == eixo]
        hachura = [i for i, t in enumerate(fig.data) if t in p_valor and t.xaxis == eixo]
        assert max(ordem) < min(hachura)


@pytest.mark.parametrize("arredondar, n1, n2", [(None, 30, 30), (0, 30, 30), (None, 12, 20), (0, 9, 15)])
def test_z_do_mann_whitney_reproduz_o_p_valor_do_scipy(arredondar, n1, n2):
    a, b = rng(5).lognormal(2, 1, n1), rng(6).lognormal(2.5, 1, n2)
    if arredondar is not None:
        a, b = np.round(a, arredondar), np.round(b, arredondar)  # cria empates
    mw = stats.mannwhitneyu(a, b, alternative="two-sided", method="asymptotic")
    z = graficos.z_mann_whitney(mw.statistic, n1, n2, graficos._termo_empates(np.concatenate([a, b])))
    assert 2 * stats.norm.sf(abs(z)) == pytest.approx(mw.pvalue, rel=1e-9)
    assert np.sign(z) == np.sign(mw.statistic - n1 * n2 / 2)


def test_z_do_mann_whitney_sem_diferenca_e_zero():
    assert graficos.z_mann_whitney(450.2, 30, 30) == 0


def test_areas_do_p_valor_e_da_regiao_de_rejeicao_conferem_com_o_exemplo():
    exemplo = exemplos()["com_efeito"]
    welch, mw = graficos._paineis_g2(exemplo)
    r = exemplo["resultado"]
    assert 2 * welch["distribuicao"].sf(abs(welch["observado"])) == pytest.approx(r["welch_p"], rel=1e-9)
    assert mw["p"] == pytest.approx(r["mw_p"], rel=1e-9)
    for painel in (welch, mw):
        critico = painel["distribuicao"].ppf(1 - graficos.ALFA / 2)
        assert 2 * painel["distribuicao"].sf(critico) == pytest.approx(0.05)


def test_simulacao_sob_h0_e_reprodutivel_e_o_histograma_e_uma_densidade():
    exemplo = exemplos()["sem_efeito"]
    s1, s2 = graficos.estatisticas_sob_h0(exemplo, 500), graficos.estatisticas_sob_h0(exemplo, 500)
    assert np.array_equal(s1["welch_t"], s2["welch_t"]) and np.array_equal(s1["mw_z"], s2["mw_z"])
    outra = graficos.estatisticas_sob_h0({**exemplo, "semente": exemplo["semente"] + 1}, 500)
    assert not np.array_equal(s1["mw_z"], outra["mw_z"])
    fig = graficos.g2(exemplo)
    for barras in (t for t in fig.data if isinstance(t, go.Bar)):
        assert 0.98 <= sum(barras.y) * barras.width <= 1 + 1e-9


def test_no_cenario_normal_cerca_de_5_por_cento_dos_conjuntos_sob_h0_caem_na_regiao_de_rejeicao():
    exemplo = gerador.exemplo_simulado(NORMAL, 0.0, 30, 11)
    sob_h0 = graficos.estatisticas_sob_h0(exemplo)
    critico_t = stats.t.ppf(0.975, exemplo["resultado"]["welch_gl"])
    assert np.mean(np.abs(sob_h0["welch_t"]) >= critico_t) == pytest.approx(0.05, abs=0.01)
    assert np.mean(np.abs(sob_h0["mw_z"]) >= stats.norm.ppf(0.975)) == pytest.approx(0.05, abs=0.01)


def test_estatistica_fora_do_eixo_fica_na_borda_com_anotacao_e_p_minusculo_tem_rotulo():
    exemplo = gerador.exemplo_simulado(NORMAL, 6.0, 30, 11)
    assert abs(exemplo["resultado"]["welch_t"]) > graficos.LIMITE_MAXIMO
    fig = graficos.g2(exemplo)
    assert list(fig.layout.xaxis.range) == [-graficos.LIMITE_MAXIMO, graficos.LIMITE_MAXIMO]
    linha = tracos(fig, "Welch: t observado")[0]
    assert abs(linha.x[0]) == graficos.LIMITE_MAXIMO
    textos = [a.text for a in fig.layout.annotations]
    assert any("fora do eixo" in t for t in textos)
    assert sum("área quase invisível" in t for t in textos) == 2


def test_estatistica_moderada_estende_o_eixo_ate_inclui_la():
    exemplo = gerador.exemplo_simulado(NORMAL, 1.2, 30, 11)
    t = exemplo["resultado"]["welch_t"]
    assert graficos.LIMITE_PADRAO < abs(t) < graficos.LIMITE_MAXIMO - 0.5
    fig = graficos.g2(exemplo)
    assert fig.layout.xaxis.range[1] >= abs(t) and not any("fora do eixo" in a.text for a in fig.layout.annotations)


def test_mann_whitney_exato_mostra_os_dois_p_valores():
    exemplo = gerador.exemplo_simulado(NORMAL, 0.5, 5, 11)
    assert exemplo["resultado"]["mw_metodo"] == "exact"
    fig = graficos.g2(exemplo)
    assert any("p-valor (aprox. normal)" in a.text and "p-valor exato" in a.text for a in fig.layout.annotations)


def test_rotulo_de_p_e_numeros_no_formato_brasileiro():
    assert graficos._p_rotulo(0.19) == "0,190"
    assert graficos._p_rotulo(1.2e-8) == "1,2e−08"
    assert graficos._p_rotulo(float("nan")) == "indefinido"
    assert graficos._num(-1.5, 2) == "−1,50"


def test_texto_do_g2_tem_de_2_a_4_frases():
    frases = [f for f in re.split(r"(?<=[.!?])\s+", graficos.TEXTO_G2.strip()) if f]
    assert 2 <= len(frases) <= 4


def test_simulacao_sob_h0_trata_empates_como_o_scipy(monkeypatch):
    original = gerador.gerar_lote

    def com_empates(*args):
        A, B = original(*args)
        return np.round(A), np.round(B)

    monkeypatch.setattr(graficos.gerador, "gerar_lote", com_empates)
    exemplo = exemplos()["sem_efeito"]
    sob_h0 = graficos.estatisticas_sob_h0(exemplo, 50)
    A, B = com_empates(exemplo["cenario"], 0.0, 30, 50, np.random.default_rng([exemplo["semente"], 0]))
    p = stats.mannwhitneyu(A, B, axis=1, alternative="two-sided", method="asymptotic").pvalue
    assert 2 * stats.norm.sf(np.abs(sob_h0["mw_z"])) == pytest.approx(p, rel=1e-9)
