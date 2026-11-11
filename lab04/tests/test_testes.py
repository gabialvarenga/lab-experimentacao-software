import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from lab04 import testes

A = [1.0, 2.0, 3.0]
B = [2.0, 3.0, 5.0]


def test_welch_confere_com_a_conta_feita_a_mao():
    # médias 2 e 10/3; variâncias 1 e 7/3; erro-padrão = sqrt(1/3 + 7/9) = sqrt(10/9)
    r = testes.aplicar_testes(A, B)
    assert r["welch_t"] == pytest.approx((2 - 10 / 3) / np.sqrt(10 / 9))
    assert r["welch_gl"] == pytest.approx((10 / 9) ** 2 / ((1 / 3) ** 2 / 2 + (7 / 9) ** 2 / 2))


def test_tamanhos_de_efeito_conferem_com_a_conta_feita_a_mao():
    # pares com a > b: 1; com a < b: 6; empates: 2; de 9 pares
    assert testes.cliff_delta(A, B) == pytest.approx(-5 / 9)
    # d = (2 - 10/3) / sqrt((2*1 + 2*7/3) / 4); J = 1 - 3 / (4*4 - 1) = 0.8
    d = (2 - 10 / 3) / np.sqrt((2 * 1 + 2 * 7 / 3) / 4)
    assert testes.hedges_g(A, B) == pytest.approx(0.8 * d)
    assert testes.razao_medianas(A, B) == pytest.approx(2 / 3)


def test_amostras_identicas_nao_mostram_efeito():
    x = [3.0, 1.0, 4.0, 1.5, 9.0, 2.6, 5.3, 5.8]
    r = testes.aplicar_testes(x, x)
    assert r["hedges_g"] == 0 and r["cliff_delta"] == 0 and r["razao_medianas"] == 1
    assert r["welch_p"] == pytest.approx(1) and r["mw_p"] == pytest.approx(1)


def test_amostras_separadas_dao_p_pequeno_e_efeito_maximo():
    a, b = np.arange(1.0, 11), np.arange(101.0, 111)
    r = testes.aplicar_testes(a, b)
    assert r["welch_p"] < 1e-10 and r["mw_p"] < 1e-3
    assert r["cliff_delta"] == -1 and r["hedges_g"] < -5
    assert testes.cliff_delta(b, a) == 1


def test_confere_com_o_scipy_chamado_direto():
    rng = np.random.default_rng(0)
    a, b = rng.lognormal(0, 1, 25), rng.lognormal(0.3, 1, 40)
    r = testes.aplicar_testes(a, b)
    w = stats.ttest_ind(a, b, equal_var=False)
    m = stats.mannwhitneyu(a, b, alternative="two-sided")
    assert (r["welch_t"], r["welch_p"], r["welch_gl"]) == (w.statistic, w.pvalue, w.df)
    assert (r["mw_u"], r["mw_p"]) == (m.statistic, m.pvalue)
    assert r["cliff_delta"] == pytest.approx(2 * m.statistic / (25 * 40) - 1)


def test_aceita_tamanhos_diferentes_e_listas():
    r = testes.aplicar_testes([1, 2, 3, 4, 5], [2, 4, 6, 8, 10, 12, 14])
    assert r["welch_gl"] > 0 and -1 <= r["cliff_delta"] <= 1


@pytest.mark.parametrize("n1, n2, empates, esperado", [
    (30, 30, False, "asymptotic"), (30, 30, True, "asymptotic"), (9, 9, False, "asymptotic"),
    (8, 30, False, "exact"), (10, 5, False, "exact"), (5, 5, False, "exact"), (5, 5, True, "asymptotic"),
])
def test_metodo_do_mann_whitney(n1, n2, empates, esperado):
    assert testes.metodo_mw(n1, n2, empates) == esperado


def test_metodo_registrado_no_resultado():
    assert testes.aplicar_testes(np.arange(30.0), np.arange(30.0) + 0.5)["mw_metodo"] == "asymptotic"
    assert testes.aplicar_testes([1, 2, 3, 4, 5], [6.5, 7, 8, 9, 10])["mw_metodo"] == "exact"
    assert testes.aplicar_testes([1, 2, 3, 4, 5], [5, 7, 8, 9, 10])["mw_metodo"] == "asymptotic"


def test_variancia_zero_nao_gera_aviso_nem_erro():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        iguais = testes.aplicar_testes([2.0, 2.0, 2.0], [2.0, 2.0, 2.0])
        diferentes = testes.aplicar_testes([2.0, 2.0, 2.0], [5.0, 5.0, 5.0])
    assert np.isnan(iguais["welch_t"]) and np.isnan(iguais["welch_p"]) and iguais["hedges_g"] == 0
    assert np.isnan(diferentes["hedges_g"]) and diferentes["mw_p"] < 0.2


def test_razao_de_medianas_com_mediana_zero_e_nan():
    assert np.isnan(testes.razao_medianas([1.0, 2.0], [0.0, 0.0]))


@pytest.mark.parametrize("a, b, msg", [
    ([1.0, np.nan, 3.0], [1.0, 2.0], "NaN"),
    ([1.0], [1.0, 2.0], "ao menos 2"),
    ([[1.0, 2.0]], [1.0, 2.0], "vetor"),
])
def test_entradas_invalidas_levantam_erro(a, b, msg):
    with pytest.raises(ValueError, match=msg):
        testes.aplicar_testes(a, b)


@pytest.mark.parametrize("n", [30, 10, 6])
def test_vetorizado_e_igual_ao_escalar_linha_a_linha(n):
    rng = np.random.default_rng(1)
    A, B = rng.lognormal(0, 1, (40, n)), rng.lognormal(0.4, 1, (40, n))
    v = testes.aplicar_testes_vetorizado(A, B)
    assert v["welch_p"].shape == v["mw_p"].shape == (40,)
    for i in range(40):
        r = testes.aplicar_testes(A[i], B[i])
        assert v["welch_p"][i] == pytest.approx(r["welch_p"], rel=1e-12)
        assert v["mw_p"][i] == pytest.approx(r["mw_p"], rel=1e-12)


def test_vetorizado_com_empates_so_em_algumas_linhas():
    rng = np.random.default_rng(2)
    A, B = rng.random((20, 6)), rng.random((20, 6))
    A[::3] = np.round(A[::3], 1)   # linhas com empates usam o método assintótico
    B[::3] = np.round(B[::3], 1)
    v = testes.aplicar_testes_vetorizado(A, B)
    for i in range(20):
        assert v["mw_p"][i] == pytest.approx(testes.aplicar_testes(A[i], B[i])["mw_p"], rel=1e-12)


def test_vetorizado_com_linha_sem_variancia_da_nan_no_welch():
    A = np.array([[1.0, 2, 3, 4], [2.0, 2, 2, 2]])
    B = np.array([[2.0, 3, 4, 6], [2.0, 2, 2, 2]])
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        v = testes.aplicar_testes_vetorizado(A, B)
    assert not np.isnan(v["welch_p"][0]) and np.isnan(v["welch_p"][1])


@pytest.mark.parametrize("A, B", [
    (np.ones((3, 5)), np.ones((4, 5))),
    (np.ones(5), np.ones(5)),
    (np.ones((3, 1)), np.ones((3, 5))),
    (np.array([[1.0, np.nan, 2.0]]), np.ones((1, 3))),
])
def test_vetorizado_rejeita_entradas_invalidas(A, B):
    with pytest.raises(ValueError):
        testes.aplicar_testes_vetorizado(A, B)


def test_vetorizado_sem_efeito_rejeita_perto_de_5_por_cento():
    rng = np.random.default_rng(42)
    A, B = rng.normal(size=(10_000, 30)), rng.normal(size=(10_000, 30))
    v = testes.aplicar_testes_vetorizado(A, B)
    for p in v.values():
        assert abs((p < 0.05).mean() - 0.05) < 0.01


# --- tabela dos dados reais (S02-10) ---


def prs(a, b):
    """CSV da coleta fictício: `a` é o grupo com_bot e `b` o sem_bot."""
    return pd.DataFrame({"grupo": ["com_bot"] * len(a) + ["sem_bot"] * len(b), "horas_ate_merge": [*a, *b]})


REAIS = pd.read_csv(Path(__file__).resolve().parent.parent / "dados" / "reais" / "prs.csv")


def test_tabela_dados_reais_tem_uma_linha_por_teste_com_todas_as_colunas():
    t = testes.tabela_dados_reais(prs(A, B))
    assert list(t.columns) == testes.COLUNAS_TABELA and list(t["teste"]) == ["welch", "mann_whitney"]
    assert list(t["estatistica_nome"]) == ["t", "U"] and list(t["medida_efeito"]) == ["hedges_g", "cliff_delta"]
    assert np.isnan(t.loc[1, "graus_de_liberdade"]) and t.loc[0, "graus_de_liberdade"] == pytest.approx(3.448, abs=1e-3)


def test_tabela_dados_reais_repete_os_numeros_de_aplicar_testes():
    a, b = np.random.default_rng(0).lognormal(2.5, 1.5, 30), np.random.default_rng(1).lognormal(2.5, 1.5, 30)
    r, t = testes.aplicar_testes(a, b), testes.tabela_dados_reais(prs(a, b)).set_index("teste")
    assert t.loc["welch", "estatistica"] == r["welch_t"] and t.loc["welch", "p_valor"] == r["welch_p"]
    assert t.loc["mann_whitney", "estatistica"] == r["mw_u"] and t.loc["mann_whitney", "p_valor"] == r["mw_p"]
    assert t.loc["welch", "tamanho_efeito"] == r["hedges_g"] and t.loc["mann_whitney", "tamanho_efeito"] == r["cliff_delta"]
    assert (t["razao_medianas"] == r["razao_medianas"]).all()   # a mesma nas duas linhas


def test_tabela_dados_reais_do_csv_coletado():
    t = testes.tabela_dados_reais(REAIS).set_index("teste")
    assert t.loc["welch", "estatistica"] == pytest.approx(-1.1149, abs=1e-4) and t.loc["welch", "p_valor"] == pytest.approx(0.2739, abs=1e-4)
    assert t.loc["welch", "graus_de_liberdade"] == pytest.approx(29.35, abs=1e-2)
    assert t.loc["mann_whitney", "estatistica"] == 414 and t.loc["mann_whitney", "p_valor"] == pytest.approx(0.5997, abs=1e-4)
    assert t.loc["welch", "tamanho_efeito"] == pytest.approx(-0.2841, abs=1e-4) and t.loc["welch", "magnitude"] == "pequeno"
    assert t.loc["mann_whitney", "tamanho_efeito"] == pytest.approx(-0.08) and t.loc["mann_whitney", "magnitude"] == "negligível"
    assert t["razao_medianas"].iloc[0] == pytest.approx(17.8381 / 17.1696, abs=1e-4)
    assert not t["rejeita_h0"].any() and set(t["conclusao"]) == {"não rejeita H₀"}


@pytest.mark.parametrize("g, esperado", [(0.0, "negligível"), (-0.19, "negligível"), (0.2, "pequeno"), (-0.49, "pequeno"),
                                         (0.5, "médio"), (0.79, "médio"), (-0.8, "grande"), (3.0, "grande"), (float("nan"), "indefinido")])
def test_magnitude_do_g_de_hedges(g, esperado):
    assert testes.magnitude_hedges(g) == esperado


@pytest.mark.parametrize("d, esperado", [(0.0, "negligível"), (-0.146, "negligível"), (0.147, "pequeno"), (0.32, "pequeno"),
                                         (-0.33, "médio"), (0.473, "médio"), (0.474, "grande"), (-1.0, "grande"), (float("nan"), "indefinido")])
def test_magnitude_do_delta_de_cliff(d, esperado):
    assert testes.magnitude_cliff(d) == esperado


def test_conclusao_muda_com_o_alfa():
    a, b = np.random.default_rng(5).normal(0, 1, 30), np.random.default_rng(1005).normal(0.5, 1, 30)
    p = testes.aplicar_testes(a, b)["welch_p"]
    assert 0.01 < p < 0.05   # amostra escolhida: significativa a 5%, não a 1%
    assert testes.tabela_dados_reais(prs(a, b), alfa=0.05).loc[0, "conclusao"] == "rejeita H₀"
    assert testes.tabela_dados_reais(prs(a, b), alfa=0.01).loc[0, "conclusao"] == "não rejeita H₀"


def test_dois_testes_que_rejeitam_e_efeito_grande():
    t = testes.tabela_dados_reais(prs(np.arange(1.0, 31), np.arange(101.0, 131)))
    assert t["rejeita_h0"].all() and set(t["conclusao"]) == {"rejeita H₀"}
    assert t.loc[1, "tamanho_efeito"] == -1 and t.loc[1, "magnitude"] == "grande" and t.loc[0, "magnitude"] == "grande"


def test_os_dois_testes_podem_discordar_nos_dois_sentidos():
    r = np.random.default_rng(1)   # cauda pesada: os postos separam os grupos, as médias não
    t = testes.tabela_dados_reais(prs(r.lognormal(0, 2, 30), r.lognormal(1.2, 2, 30))).set_index("teste")
    assert not t.loc["welch", "rejeita_h0"] and t.loc["mann_whitney", "rejeita_h0"]
    r = np.random.default_rng(0)   # seis PRs muito longos num grupo: a média separa, os postos não
    a = np.concatenate([r.uniform(9, 11, 24), r.uniform(60, 90, 6)])
    b = np.concatenate([r.uniform(9, 11, 24), r.uniform(10, 12, 6)])
    t = testes.tabela_dados_reais(prs(a, b)).set_index("teste")
    assert t.loc["welch", "rejeita_h0"] and not t.loc["mann_whitney", "rejeita_h0"]


def test_dados_sem_variacao_deixam_os_dois_testes_indefinidos_sem_aviso():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        t = testes.tabela_dados_reais(prs([5.0, 5.0, 5.0], [5.0, 5.0, 5.0]))
    assert set(t["conclusao"]) == {"indefinida"} and not t["rejeita_h0"].any()   # tudo empatado: p-valores NaN


@pytest.mark.parametrize("df, mensagem", [
    (prs([1.0], [1.0, 2.0]), "ao menos 2"),
    (prs([1.0, 2.0], []), "ao menos 2"),
    (REAIS.drop(columns="horas_ate_merge"), "faltam as colunas"),
])
def test_tabela_dados_reais_recusa_dados_invalidos(df, mensagem):
    with pytest.raises(ValueError, match=mensagem):
        testes.tabela_dados_reais(df)
