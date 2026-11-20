"""Testes de `lab05/testes.py`.

Os testes das funções copiadas do Lab04 foram copiados de `lab04/tests/test_testes.py` (até
`test_vetorizado_sem_efeito_rejeita_perto_de_5_por_cento` e os de magnitude); os demais são novos.
"""

import warnings

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from conftest import coleta_sintetica
from lab05 import testes

A = [1.0, 2.0, 3.0]
B = [2.0, 3.0, 5.0]


# --- copiados do Lab04 ---


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


@pytest.mark.parametrize("g, esperado", [(0.0, "negligível"), (-0.19, "negligível"), (0.2, "pequeno"), (-0.49, "pequeno"),
                                         (0.5, "médio"), (0.79, "médio"), (-0.8, "grande"), (3.0, "grande"), (float("nan"), "indefinido")])
def test_magnitude_do_g_de_hedges(g, esperado):
    assert testes.magnitude_hedges(g) == esperado


@pytest.mark.parametrize("d, esperado", [(0.0, "negligível"), (-0.146, "negligível"), (0.147, "pequeno"), (0.32, "pequeno"),
                                         (-0.33, "médio"), (0.473, "médio"), (0.474, "grande"), (-1.0, "grande"), (float("nan"), "indefinido")])
def test_magnitude_do_delta_de_cliff(d, esperado):
    assert testes.magnitude_cliff(d) == esperado


# --- novos no Lab05 ---


def holm_ingenuo(p):
    """Holm escrito do jeito mais direto, para comparar."""
    p = list(p)
    m = len(p)
    ordem = sorted(range(m), key=lambda i: p[i])
    saida, maior = [0.0] * m, 0.0
    for posicao, i in enumerate(ordem):
        maior = max(maior, min(1.0, (m - posicao) * p[i]))
        saida[i] = maior
    return saida


def test_holm_confere_com_a_conta_feita_a_mao():
    # ordenados: 0,005·4 = 0,02; 0,01·3 = 0,03; 0,03·2 = 0,06; 0,04·1 = 0,04 → 0,06 (não diminui)
    assert testes.holm([0.01, 0.04, 0.03, 0.005]) == pytest.approx([0.03, 0.06, 0.06, 0.02])


def test_holm_limita_a_um_e_confere_com_a_versao_direta():
    rng = np.random.default_rng(3)
    for _ in range(50):
        p = rng.random(6)
        assert testes.holm(p) == pytest.approx(holm_ingenuo(p))
    assert testes.holm([0.5, 0.9]).max() == 1.0


def test_holm_em_matriz_e_igual_linha_a_linha():
    P = np.random.default_rng(4).random((20, 6))
    ajustados = testes.holm(P)
    for linha, original in zip(ajustados, P):
        assert linha == pytest.approx(testes.holm(original))


def test_holm_ignora_nan_na_contagem():
    r = testes.holm([0.01, np.nan, 0.04])
    assert r[0] == pytest.approx(0.02) and np.isnan(r[1]) and r[2] == pytest.approx(0.04)


def test_holm_recusa_tres_dimensoes():
    with pytest.raises(ValueError):
        testes.holm(np.ones((2, 2, 2)))


def test_bootstrap_e_reprodutivel_e_contem_a_razao_observada():
    rng = np.random.default_rng(0)
    a, b = rng.lognormal(np.log(1.2), 0.1, 30), rng.lognormal(0, 0.1, 30)
    ic = testes.ic_razao_bootstrap(a, b, np.random.default_rng(1), 2000)
    assert ic == testes.ic_razao_bootstrap(a, b, np.random.default_rng(1), 2000)
    assert ic[0] < testes.razao_medianas(a, b) < ic[1] and 1.0 < ic[0] < ic[1] < 1.4
    assert testes.ic_razao_bootstrap(a, b, n_boot=500) == testes.ic_razao_bootstrap(a, b, n_boot=500)


def test_bootstrap_de_grupos_constantes_e_de_mediana_zero():
    assert testes.ic_razao_bootstrap([2.0, 2.0], [1.0, 1.0], n_boot=100) == (2.0, 2.0)
    assert all(np.isnan(testes.ic_razao_bootstrap([1.0, 2.0], [0.0, 0.0], n_boot=100)))


def test_residuos_sao_relativos_a_mediana_da_combinacao():
    df = coleta_sintetica(n=3)
    r = testes.residuos(df, "ops_s")
    assert len(r) == len(df) and (r == 0).sum() == 12  # n = 3: a mediana é um dos valores, um zero por combinação


def test_regra_5_1_escolhe_welch_com_residuos_normais():
    e = testes.escolher_teste(coleta_sintetica(n=10, sigma=0.01, semente=1), "ops_s")
    assert e["teste"] == "welch" and e["shapiro_p"] >= 0.05 and abs(e["assimetria"]) <= 1 and e["n_residuos"] == 120


def test_regra_5_1_escolhe_mann_whitney_com_cauda_pesada():
    e = testes.escolher_teste(coleta_sintetica(n=10, sigma=1.0, semente=1), "ops_s")
    assert e["teste"] == "mann_whitney" and "Shapiro-Wilk rejeita" in e["motivo"] and "0,05" in e["motivo"]


def test_regra_5_1_sem_variacao_e_com_poucos_residuos():
    df = coleta_sintetica(n=2, sigma=0.0)
    assert testes.escolher_teste(df, "ops_s")["motivo"] == "resíduos sem variação"
    with pytest.raises(ValueError, match="3 resíduos"):
        testes.escolher_teste(df.head(2), "ops_s")
    with pytest.raises(ValueError, match="faltam"):
        testes.escolher_teste(df.drop(columns="carga"), "ops_s")


@pytest.mark.parametrize("p, ic, esperado", [
    (0.01, (1.10, 1.20), "diferença relevante"),
    (0.01, (0.80, 0.94), "diferença relevante"),
    (0.01, (0.97, 1.03), "diferença pequena demais"),
    (0.30, (0.97, 1.03), "equivalência prática"),
    (np.nan, (0.96, 1.04), "equivalência prática"),
    (0.01, (1.02, 1.10), "inconclusivo"),
    (0.30, (0.90, 1.10), "inconclusivo"),
    (0.30, (1.10, 1.20), "inconclusivo"),
    (0.01, (np.nan, np.nan), "inconclusivo"),
])
def test_quatro_situacoes_da_secao_6(p, ic, esperado):
    assert testes.situacao(p, *ic) == esperado


def test_comparar_tem_seis_linhas_valkey_sobre_redis_e_holm():
    df = coleta_sintetica(n=10, razao=1.0, razao_threads4=1.5, sigma=0.05, semente=2)
    t = testes.comparar(df, "ops_s", "welch", np.random.default_rng(0), n_boot=500)
    assert list(t.columns) == testes.COLUNAS_COMPARACAO and len(t) == 6
    assert list(zip(t["io_threads"], t["carga"]))[:3] == [(1, "get"), (1, "misto"), (1, "set")]
    assert (t["p_holm"] >= t["p_principal"]).all() and (t["p_principal"] == t["welch_p"]).all()
    assert (t["teste_sensibilidade"] == "mann_whitney").all() and (t["p_sensibilidade"] == t["mw_p"]).all()
    quatro = t[t["io_threads"] == 4]
    assert quatro["rejeita_h0"].all() and (quatro["situacao"] == "diferença relevante").all()
    assert (quatro["razao_medianas"] > 1.3).all() and (quatro["cliff_delta"] == 1).all()  # Valkey em relação ao Redis


def test_comparar_reproduz_e_usa_a_regra_5_1_sem_teste():
    df = coleta_sintetica(n=6, sigma=1.0, semente=5)
    t1, t2 = testes.comparar(df, "ops_s", n_boot=300), testes.comparar(df, "ops_s", n_boot=300)
    pd.testing.assert_frame_equal(t1, t2)
    assert (t1["teste_principal"] == testes.escolher_teste(df, "ops_s")["teste"]).all()


def test_comparar_marca_quando_os_testes_discordam():
    df = coleta_sintetica(n=10, sigma=0.05, semente=2)
    t = testes.comparar(df, "ops_s", "welch", n_boot=200)
    esperado = (t["welch_p"] < 0.05) != (t["mw_p"] < 0.05)
    assert (t["testes_discordam"] == esperado).all()


def test_comparar_memoria_constante_e_deterministica():
    df = coleta_sintetica(n=4, razao=0.9, sigma=0.0)
    t = testes.comparar(df, "memoria_bytes", "welch", n_boot=100)
    assert t["deterministica"].all() and t["p_principal"].isna().all() and t["p_holm"].isna().all()
    assert (t["situacao"] == "diferença relevante").all() and not t["testes_discordam"].any()
    iguais = testes.comparar(coleta_sintetica(n=4, razao=1.02, sigma=0.0), "memoria_bytes", "welch", n_boot=100)
    assert (iguais["situacao"] == "equivalência prática").all()


def test_comparar_recusa_teste_desconhecido_e_poucas_execucoes():
    df = coleta_sintetica(n=3)
    with pytest.raises(ValueError, match="desconhecido"):
        testes.comparar(df, "ops_s", "anova")
    with pytest.raises(ValueError, match="ao menos 2 execuções"):
        testes.comparar(df[df["repeticao"] == 1], "ops_s", "welch")


@pytest.mark.parametrize("metrica", ["ops_s", "lat_p50_ms", "lat_p99_ms", "memoria_bytes"])
def test_comparar_roda_no_piloto(piloto, metrica):
    t = testes.comparar(piloto, metrica, n_boot=500)
    assert len(t) == 6 and (t["n_valkey"] == 5).all() and (t["n_redis"] == 5).all()
    assert t["situacao"].isin(testes.SITUACOES).all() and t["razao_medianas"].between(t["ic_inf"], t["ic_sup"]).all()
