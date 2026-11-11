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


# --- G3: erro tipo I por situação simulada (S02-08) ---

PASTA_SIMULACAO = PASTA / "dados" / "simulacao"
RESULTADOS = pd.read_csv(PASTA_SIMULACAO / "resultados.csv")
PILOTO = pd.read_csv(PASTA_SIMULACAO / "piloto.csv")


def linha_h0(cenario, teste, taxa, n_rep=10_000, alfa=0.05, delta=0.0, largura=0.004):
    return {"cenario": cenario, "delta": delta, "n": 30, "n_rep": n_rep, "alfa": alfa, "teste": teste,
            "rejeicoes": round(taxa * n_rep), "taxa": taxa, "ic_inf": max(taxa - largura, 0), "ic_sup": min(taxa + largura, 1)}


def sintetico(taxas, **kwargs):
    """`taxas`: {cenario: (taxa_welch, taxa_mann_whitney)} com δ = 0."""
    return pd.DataFrame([linha_h0(c, t, x, **kwargs) for c, par in taxas.items() for t, x in zip(("welch", "mann_whitney"), par)])


@pytest.mark.parametrize("tabela_", [RESULTADOS, PILOTO], ids=["resultados", "piloto"])
def test_fumaca_g3_devolve_figura_com_titulo_eixos_e_legenda(tabela_):
    fig = graficos.g3(tabela_)
    assert isinstance(fig, go.Figure)
    assert [t.name for t in fig.data if t.showlegend is not False] == ["Welch", "Mann-Whitney", "Nível nominal (α = 5%)"]
    assert fig.layout.title.text.startswith("G3") and "Wilson de 95%" in fig.layout.title.text
    assert "Situação simulada" in fig.layout.xaxis.title.text
    assert "Taxa de rejeição" in fig.layout.yaxis.title.text and "(%)" in fig.layout.yaxis.title.text
    assert fig.layout.barmode == "group"


def test_g3_usa_a_mesma_cor_de_cada_teste_do_g2():
    fig = graficos.g3(RESULTADOS)
    g2 = graficos.g2(exemplos()["sem_efeito"])
    for traco in fig.data[:2]:
        teste = {"Welch": "welch", "Mann-Whitney": "mann_whitney"}[traco.name]
        assert traco.marker.color == graficos.CORES_TESTE[teste]
    cores_g2 = {t.line.color for t in g2.data if getattr(t, "mode", None) == "lines" and t.line.color in graficos.CORES_TESTE.values()}
    assert {t.marker.color for t in fig.data[:2]} == cores_g2


def test_g3_desenha_a_taxa_em_percentual_e_o_ic_de_wilson_assimetrico_como_barra_de_erro():
    fig = graficos.g3(RESULTADOS)
    h0 = RESULTADOS[(RESULTADOS["delta"] == 0) & (RESULTADOS["alfa"] == 0.05)]
    for traco, teste in zip(fig.data[:2], ("welch", "mann_whitney")):
        linhas = h0[h0["teste"] == teste]
        assert np.allclose(traco.y, linhas["taxa"] * 100)
        assert np.allclose(traco.error_y.array, (linhas["ic_sup"] - linhas["taxa"]) * 100)
        assert np.allclose(traco.error_y.arrayminus, (linhas["taxa"] - linhas["ic_inf"]) * 100)
        assert traco.error_y.symmetric is False


def test_g3_tem_a_linha_em_5_por_cento_e_um_grupo_por_cenario_na_ordem_da_tabela():
    fig = graficos.g3(RESULTADOS)
    assert [(s.y0, s.y1) for s in fig.layout.shapes] == [(5.0, 5.0)]
    assert list(fig.data[0].x) == [graficos.NOMES_CENARIO[c] for c in ("C0", "C1", "C2", "C3", "C4")]
    assert list(fig.data[0].x) == list(fig.data[1].x)


def test_g3_no_nivel_de_1_por_cento_move_a_linha_e_usa_as_taxas_de_1_por_cento():
    fig = graficos.g3(RESULTADOS, alfa=0.01)
    assert [(s.y0, s.y1) for s in fig.layout.shapes] == [(1.0, 1.0)]
    assert fig.data[0].y[0] == pytest.approx(0.89) and "α = 1%" in fig.data[2].name
    assert fig.layout.yaxis.range[1] < 2.5   # a escala acompanha o nível, não os 5%


def test_g3_desenha_so_os_cenarios_presentes_e_aceita_um_opcional_a_mais():
    sem_c4 = RESULTADOS[RESULTADOS["cenario"] != "C4"]
    assert len(graficos.g3(sem_c4).data[0].x) == 4
    c5 = RESULTADOS[RESULTADOS["cenario"] == "C4"].assign(cenario="C5")
    fig = graficos.g3(pd.concat([RESULTADOS, c5], ignore_index=True))
    assert list(fig.data[0].x)[-1] == "C5"   # id sem nome cadastrado aparece como ele mesmo


def test_g3_aceita_nomes_proprios_para_os_cenarios():
    fig = graficos.g3(RESULTADOS, nomes={"C0": "controle"})
    assert fig.data[0].x[0] == "controle" and fig.data[0].x[1] == graficos.NOMES_CENARIO["C1"]


def test_g3_escala_comporta_a_barra_de_erro_maior_que_a_taxa():
    tabela_ = sintetico({"A": (0.5, 0.3)}, largura=0.2)
    fig = graficos.g3(tabela_)
    assert fig.layout.yaxis.range[0] == 0 and fig.layout.yaxis.range[1] >= 70   # ic_sup de 70% cabe
    assert np.allclose(fig.data[0].error_y.array, 20)
    pequena = graficos.g3(sintetico({"A": (0.0, 0.001)}, largura=0.001))
    assert pequena.layout.yaxis.range[1] >= 5   # a linha de 5% sempre cabe, mesmo com taxas minúsculas


def test_g3_hover_traz_a_taxa_o_intervalo_as_rejeicoes_e_a_classificacao():
    fig = graficos.g3(RESULTADOS)
    welch_c1 = fig.data[0].customdata[1]
    assert welch_c1[0] == "2,47%" and welch_c1[3:6] == [247, 10_000, 30] and welch_c1[6] == "conservador"
    mw_c2 = fig.data[1].customdata[2]
    assert mw_c2[0] == "4,86%" and mw_c2[6] == "ok"
    assert "Classificação" in fig.data[0].hovertemplate and "IC de Wilson" in fig.data[0].hovertemplate


def test_g3_marca_um_teste_liberal_na_classificacao_do_hover():
    fig = graficos.g3(sintetico({"A": (0.07, 0.05)}, largura=0.003))
    assert fig.data[0].customdata[0][6] == "liberal" and fig.data[1].customdata[0][6] == "ok"


def test_g3_ignora_as_linhas_com_efeito():
    com_efeito = pd.concat([RESULTADOS, RESULTADOS.assign(delta=0.4, taxa=0.9, ic_inf=0.89, ic_sup=0.91)])
    assert np.allclose(graficos.g3(com_efeito).data[0].y, graficos.g3(RESULTADOS).data[0].y)


@pytest.mark.parametrize("quebrar, mensagem", [
    (lambda d: d.drop(columns="ic_sup"), "faltam as colunas.*ic_sup"),
    (lambda d: d.assign(teste="t_de_student"), "testes desconhecidos"),
    (lambda d: d[d["delta"] > 0], "não tem linhas de δ = 0"),
])
def test_g3_recusa_tabelas_invalidas(quebrar, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        graficos.g3(quebrar(RESULTADOS))


def test_g3_recusa_alfa_ausente():
    with pytest.raises(ValueError, match="α = 0.1"):
        graficos.g3(RESULTADOS, alfa=0.1)


def test_texto_do_g3_tem_de_2_a_4_frases():
    frases = [f for f in re.split(r"(?<=[.!?])\s+", graficos.TEXTO_G3.strip()) if f]
    assert 2 <= len(frases) <= 4


def _pct(x):
    return f"{x * 100:.2f}%".replace(".", ",")


def test_numeros_do_texto_do_g3_batem_com_a_classificacao_dos_resultados():
    """Se os resultados mudarem, o texto precisa ser revisto: os números dele saem daqui."""
    from lab04 import resultados

    c = resultados.classificar(RESULTADOS)
    c5 = c[c["alfa"] == 0.05].set_index(["cenario", "teste"])
    mw = c5.xs("mann_whitney", level="teste")
    welch = c5.xs("welch", level="teste")
    texto = graficos.TEXTO_G3
    assert f"entre {_pct(mw['taxa'].min())} e {_pct(mw['taxa'].max())}" in texto
    for cenario in ("C0", "C4"):   # o Mann-Whitney conservador do texto
        assert mw.loc[cenario, "classificacao"] == "conservador"
        assert f"{mw.loc[cenario, 'desvio_pp']:.2f}".replace("-", "−").replace(".", ",") in texto
    assert (mw.drop(["C0", "C4"])["classificacao"] == "ok").all()
    assert welch.loc["C0", "classificacao"] == "ok" and f"({_pct(welch.loc['C0', 'taxa'])})" in texto
    assert (welch.drop("C0")["classificacao"] == "conservador").all()
    assert f"de {_pct(welch.drop('C0')['taxa'].min())} a {_pct(welch.drop('C0')['taxa'].max())}" in texto
    assert "liberal" not in set(c["classificacao"])                    # "Nenhum teste foi liberal"
    por_alfa = c.pivot_table(index=["cenario", "teste"], columns="alfa", values="classificacao", aggfunc="first")
    assert (por_alfa[0.05] == por_alfa[0.01]).all()                    # "Com α = 1% a classificação é a mesma"


# --- G4: curvas de poder (S02-09) ---


def curvas(fig):
    """Os traços das curvas de poder (os com dados), sem a entrada de legenda da linha de referência."""
    return [t for t in fig.data if t.x is not None and len(t.x) and t.x[0] is not None]


def linhas_do_csv(tabela_, cenario, teste, alfa=0.05):
    d = tabela_[(tabela_["cenario"] == cenario) & (tabela_["teste"] == teste) & np.isclose(tabela_["alfa"], alfa)]
    return d.sort_values("delta")


@pytest.mark.parametrize("tabela_", [RESULTADOS, PILOTO], ids=["resultados", "piloto"])
def test_fumaca_g4_devolve_figura_com_titulo_eixos_e_legenda(tabela_):
    fig = graficos.g4(tabela_)
    assert isinstance(fig, go.Figure)
    assert [t.name for t in fig.data if t.showlegend is not False] == ["Welch", "Mann-Whitney", "Nível nominal (α = 5%)"]
    assert fig.layout.title.text.startswith("G4") and "α = 5%" in fig.layout.title.text
    titulos_x = [fig.layout[f"xaxis{'' if i == 1 else i}"].title.text for i in range(1, 6)]
    assert titulos_x == ["Efeito δ (desvios-padrão)"] + ["Razão de medianas B/A (×)"] * 4
    assert all("Proporção de rejeições" in fig.layout[a].title.text and "(%)" in fig.layout[a].title.text
               for a in ("yaxis", "yaxis4"))   # o título do eixo y vai na primeira coluna de cada linha
    assert fig.layout.yaxis.ticksuffix == "%" and tuple(fig.layout.yaxis.range) == (0, 103)


def test_g4_tem_uma_faceta_por_cenario_com_duas_curvas_em_cada():
    fig = graficos.g4(RESULTADOS)
    assert [a.text for a in fig.layout.annotations] == [graficos.NOMES_CENARIO[c] for c in ("C0", "C1", "C2", "C3", "C4")]
    assert len(curvas(fig)) == 10
    por_faceta = {}
    for t in curvas(fig):
        por_faceta.setdefault(t.xaxis, []).append(t.name)
    assert len(por_faceta) == 5 and all(sorted(n) == ["Mann-Whitney", "Welch"] for n in por_faceta.values())


def test_g4_desenha_o_poder_em_percentual_na_grade_de_efeitos_de_cada_cenario():
    fig = graficos.g4(RESULTADOS)
    esperado = [(c, t) for c in ("C0", "C1", "C2", "C3", "C4") for t in ("welch", "mann_whitney")]
    for traco, (cenario, teste) in zip(curvas(fig), esperado):
        d = linhas_do_csv(RESULTADOS, cenario, teste)
        assert list(traco.x) == list(d["delta"]) and len(traco.x) == 6 and traco.x[0] == 0
        assert np.allclose(traco.y, d["taxa"] * 100)


def test_g4_usa_as_cores_do_teste_e_simbolos_e_tracos_diferentes_para_as_curvas_coincidentes():
    fig = graficos.g4(RESULTADOS)
    for traco in curvas(fig):
        teste = {"Welch": "welch", "Mann-Whitney": "mann_whitney"}[traco.name]
        assert traco.line.color == graficos.CORES_TESTE[teste] == traco.marker.color
    welch, mw = curvas(fig)[0], curvas(fig)[1]   # C0, onde as curvas quase coincidem
    assert (welch.marker.symbol, welch.line.dash) != (mw.marker.symbol, mw.line.dash)
    assert fig.data[0].line.color == graficos.g3(RESULTADOS).data[0].marker.color   # mesma cor do G3


def test_g4_tem_a_linha_de_referencia_em_5_por_cento_em_todas_as_facetas():
    fig = graficos.g4(RESULTADOS)
    assert [(s.y0, s.y1) for s in fig.layout.shapes] == [(5.0, 5.0)] * 5
    assert fig.data[-1].name == "Nível nominal (α = 5%)" and fig.data[-1].showlegend is not False


def test_g4_rotula_o_eixo_com_desvios_padrao_em_c0_e_razao_de_medianas_nos_demais():
    fig = graficos.g4(RESULTADOS)
    assert list(fig.layout.xaxis.ticktext) == ["0,0", "0,2", "0,4", "0,6", "0,8", "1,0"]
    assert list(fig.layout.xaxis2.ticktext) == ["1,0×", "1,5×", "2,2×", "3,3×", "5,0×", "7,4×"]
    assert list(fig.layout.xaxis2.tickvals) == [0.0, 0.4, 0.8, 1.2, 1.6, 2.0]


def test_g4_aceita_trocar_a_unidade_do_efeito_e_os_nomes_dos_cenarios():
    fig = graficos.g4(RESULTADOS, unidades={"C0": "log", "C1": "dp"}, nomes={"C0": "controle"})
    assert fig.layout.xaxis.title.text == "Razão de medianas B/A (×)"
    assert fig.layout.xaxis2.title.text == "Efeito δ (desvios-padrão)"
    assert fig.layout.annotations[0].text == "controle" and fig.layout.annotations[1].text == graficos.NOMES_CENARIO["C1"]


def test_g4_no_nivel_de_1_por_cento_move_a_linha_e_usa_as_taxas_de_1_por_cento():
    fig = graficos.g4(RESULTADOS, alfa=0.01)
    assert [(s.y0, s.y1) for s in fig.layout.shapes] == [(1.0, 1.0)] * 5
    assert np.allclose(curvas(fig)[0].y, linhas_do_csv(RESULTADOS, "C0", "welch", 0.01)["taxa"] * 100)
    assert "α = 1%" in fig.data[-1].name


@pytest.mark.parametrize("n_cenarios, linhas", [(1, 1), (2, 1), (3, 1), (4, 2), (5, 2), (6, 2)])
def test_g4_distribui_as_facetas_em_ate_tres_colunas(n_cenarios, linhas):
    base = RESULTADOS[RESULTADOS["cenario"] == "C1"]
    tabela_ = pd.concat([base.assign(cenario=f"X{i}") for i in range(n_cenarios)], ignore_index=True)
    fig = graficos.g4(tabela_)
    assert len(curvas(fig)) == 2 * n_cenarios and len(fig.layout.annotations) == n_cenarios
    assert fig.layout.height == 430 * linhas + 160
    assert len({t.xaxis for t in curvas(fig)}) == n_cenarios


def test_g4_desenha_so_os_cenarios_presentes():
    sem_c4 = RESULTADOS[RESULTADOS["cenario"] != "C4"]
    assert len(curvas(graficos.g4(sem_c4))) == 8


def test_g4_a_primeira_ponta_da_curva_e_o_erro_tipo_i_do_g3():
    g4 = graficos.g4(RESULTADOS)
    g3 = graficos.g3(RESULTADOS)
    for i, traco in enumerate(curvas(g4)):
        barra = g3.data[i % 2]   # Welch e Mann-Whitney, na ordem dos cenários
        assert traco.y[0] == pytest.approx(barra.y[i // 2])


def test_g4_curvas_coincidentes_em_c0_continuam_com_duas_series_distintas():
    welch, mw = curvas(graficos.g4(RESULTADOS))[:2]
    assert np.abs(np.array(welch.y) - np.array(mw.y)).max() < 4   # quase se sobrepõem em C0 (até 3 p.p.)
    assert not np.allclose(welch.y, mw.y)


def test_g4_hover_traz_o_efeito_a_razao_de_medianas_o_poder_e_o_ic():
    fig = graficos.g4(RESULTADOS)
    mw_c1 = curvas(fig)[3]   # Mann-Whitney em C1
    ponto = mw_c1.customdata[3]   # δ = 1,2
    assert ponto[0] == "1,2" and ponto[1] == "3,32×" and ponto[2] == "76,86%" and list(ponto[5:8]) == [7686, 10_000, 30]
    assert ponto[8] == "poder" and mw_c1.customdata[0][8] == "erro tipo I" and mw_c1.customdata[0][9] == "ok"
    assert curvas(fig)[0].customdata[2][1] == "—"   # C0 não tem razão de medianas
    assert "razão de medianas" in mw_c1.hovertemplate and "desvio-padrão" in curvas(fig)[0].hovertemplate


@pytest.mark.parametrize("quebrar, mensagem", [
    (lambda d: d.drop(columns="ic_inf"), "faltam as colunas.*ic_inf"),
    (lambda d: d.assign(teste="t_de_student"), "testes desconhecidos"),
    (lambda d: d[d["delta"] == 0], "não tem linhas com efeito"),
])
def test_g4_recusa_tabelas_invalidas(quebrar, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        graficos.g4(quebrar(RESULTADOS))


def test_g4_recusa_alfa_ausente():
    with pytest.raises(ValueError, match="α = 0.1"):
        graficos.g4(RESULTADOS, alfa=0.1)


def test_texto_do_g4_tem_de_2_a_4_frases():
    frases = [f for f in re.split(r"(?<=[.!?])\s+", graficos.TEXTO_G4.strip()) if f]
    assert 2 <= len(frases) <= 4


def test_numeros_do_texto_do_g4_batem_com_a_vantagem_de_poder_dos_resultados():
    """Se os resultados mudarem, o texto precisa ser revisto: os números dele saem daqui."""
    from lab04 import resultados

    poder = resultados.vantagem_de_poder(RESULTADOS)
    lid = resultados.lideres(poder)
    texto = graficos.TEXTO_G4
    c1 = poder[(poder["cenario"] == "C1") & (poder["alfa"] == 0.05) & (poder["delta"] == 1.2)].iloc[0]
    assert f"{np.exp(1.2):.1f}".replace(".", ",") + " vezes" in texto
    assert f"{c1['poder_mann_whitney'] * 100:.1f}%".replace(".", ",") in texto
    assert f"{c1['poder_welch'] * 100:.1f}%".replace(".", ",") in texto
    maximos = poder[poder["alfa"] == 0.05].groupby("cenario")["vantagem_pp"].apply(lambda s: s.abs().max())
    demais = maximos[["C1", "C2", "C3", "C4"]]
    assert f"entre {round(demais.min())} e {round(demais.max())} pontos" in texto
    assert f"{maximos['C0']:.1f}".replace(".", ",") + " pontos percentuais" in texto
    for alfa in (0.05, 0.01):   # Welch lidera o controle, Mann-Whitney os demais, e nada alterna: vale nos dois α
        lider = lid[lid["alfa"] == alfa].set_index("cenario")["lider"]
        assert lider["C0"] == "welch" and (lider.drop("C0") == "mann_whitney").all()
    assert not lid["inverte_com_o_efeito"].any()
