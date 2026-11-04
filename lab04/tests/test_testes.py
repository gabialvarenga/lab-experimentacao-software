import warnings

import numpy as np
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
