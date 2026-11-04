import math

import numpy as np
import pytest

from lab04 import gerador

NORMAL = {"familia": "normal", "mu": 10.0, "sigma": 2.0}
LOGNORMAL = {"familia": "lognormal", "mu": 1.0, "sigma": 1.0}


def rng(semente=42):
    return np.random.default_rng(semente)


def com(cenario, p, fator=20):
    return {**cenario, "contaminacao": {"p": p, "fator": fator}}


@pytest.mark.parametrize("cenario", [NORMAL, LOGNORMAL])
def test_formatos_de_amostra_e_de_lote(cenario):
    a, b = gerador.gerar_amostra(cenario, 0.5, 30, rng())
    assert a.shape == b.shape == (30,)
    A, B = gerador.gerar_lote(cenario, 0.5, 30, 7, rng())
    assert A.shape == B.shape == (7, 30)


def test_lognormal_e_sempre_positiva_e_normal_nao():
    a, b = gerador.gerar_amostra(LOGNORMAL, 0.5, 1000, rng())
    assert (a > 0).all() and (b > 0).all()
    assert (gerador.gerar_amostra({**NORMAL, "mu": 0.0}, 0, 1000, rng())[0] < 0).any()


def test_mesma_semente_gera_os_mesmos_dados_e_semente_diferente_nao():
    a1, b1 = gerador.gerar_amostra(LOGNORMAL, 0.5, 30, rng(7))
    a2, b2 = gerador.gerar_amostra(LOGNORMAL, 0.5, 30, rng(7))
    assert np.array_equal(a1, a2) and np.array_equal(b1, b2)
    a3, _ = gerador.gerar_amostra(LOGNORMAL, 0.5, 30, rng(8))
    assert not np.array_equal(a1, a3)
    A1, B1 = gerador.gerar_lote(LOGNORMAL, 0.5, 30, 5, rng(7))
    A2, B2 = gerador.gerar_lote(LOGNORMAL, 0.5, 30, 5, rng(7))
    assert np.array_equal(A1, A2) and np.array_equal(B1, B2)


def test_rng_reutilizado_entre_chamadas_da_amostras_novas():
    gerador_unico = rng(7)
    primeira = gerador.gerar_amostra(NORMAL, 0, 30, gerador_unico)
    segunda = gerador.gerar_amostra(NORMAL, 0, 30, gerador_unico)
    assert not np.array_equal(primeira[0], segunda[0])
    # e a sequência inteira se reproduz com uma semente nova
    repetido = rng(7)
    assert np.array_equal(gerador.gerar_amostra(NORMAL, 0, 30, repetido)[0], primeira[0])
    assert np.array_equal(gerador.gerar_amostra(NORMAL, 0, 30, repetido)[0], segunda[0])


def test_amostra_e_a_primeira_linha_do_lote_de_uma_repeticao():
    a, b = gerador.gerar_amostra(com(LOGNORMAL, 0.1), 0.3, 25, rng(3))
    A, B = gerador.gerar_lote(com(LOGNORMAL, 0.1), 0.3, 25, 1, rng(3))
    assert np.array_equal(a, A[0]) and np.array_equal(b, B[0])


def test_repeticoes_de_um_lote_sao_independentes():
    A, _ = gerador.gerar_lote(NORMAL, 0, 30, 4, rng())
    assert len({tuple(linha) for linha in A}) == 4


def test_lognormal_delta_zero_aproxima_as_medianas():
    a, b = gerador.gerar_amostra(LOGNORMAL, 0, 100_000, rng())
    assert np.median(a) == pytest.approx(math.exp(1.0), rel=0.03)
    assert np.median(b) / np.median(a) == pytest.approx(1, abs=0.03)


@pytest.mark.parametrize("delta", [0.3, 0.5, 1.0, -0.5])
def test_lognormal_razao_de_medianas_e_perto_de_e_elevado_a_delta(delta):
    a, b = gerador.gerar_amostra(LOGNORMAL, delta, 100_000, rng())
    assert np.median(b) / np.median(a) == pytest.approx(math.exp(delta), rel=0.03)


def test_normal_desloca_a_media_em_delta_desvios_padrao():
    a, b = gerador.gerar_amostra(NORMAL, 0.5, 100_000, rng())
    assert a.mean() == pytest.approx(10.0, abs=0.05) and a.std() == pytest.approx(2.0, rel=0.02)
    assert b.mean() - a.mean() == pytest.approx(0.5 * 2.0, abs=0.05)
    assert b.std() == pytest.approx(2.0, rel=0.02)


@pytest.mark.parametrize("p", [0.05, 0.2])
def test_contaminacao_multiplica_a_fracao_p_nos_dois_grupos(p):
    cenario = com({"familia": "lognormal", "mu": 0.0, "sigma": 0.1}, p)
    a, b = gerador.gerar_amostra(cenario, 0, 200_000, rng())
    # sem contaminação os valores ficam perto de 1; multiplicados por 20, passam de 10
    assert (a > 10).mean() == pytest.approx(p, abs=0.004)
    assert (b > 10).mean() == pytest.approx(p, abs=0.004)


def test_contaminacao_zero_ou_ausente_nao_altera_os_dados():
    base = gerador.gerar_amostra(LOGNORMAL, 0.5, 30, rng(9))
    for cenario in (com(LOGNORMAL, 0), {**LOGNORMAL, "contaminacao": None}, {**LOGNORMAL, "contaminacao": {}}):
        a, b = gerador.gerar_amostra(cenario, 0.5, 30, rng(9))
        assert np.array_equal(a, base[0]) and np.array_equal(b, base[1])


def test_contaminacao_um_multiplica_todos_os_valores():
    base = gerador.gerar_amostra(LOGNORMAL, 0.5, 30, rng(9))
    a, b = gerador.gerar_amostra(com(LOGNORMAL, 1, fator=3), 0.5, 30, rng(9))
    assert a == pytest.approx(3 * base[0]) and b == pytest.approx(3 * base[1])


def test_contaminacao_parcial_so_multiplica_valores_dos_dados_originais():
    base = gerador.gerar_amostra(LOGNORMAL, 0.5, 200, rng(9))
    a, _ = gerador.gerar_amostra(com(LOGNORMAL, 0.3, fator=5), 0.5, 200, rng(9))
    razao = a / base[0]
    assert np.all(np.isclose(razao, 1) | np.isclose(razao, 5)) and np.isclose(razao, 5).any()


def test_amostra_pequena_de_dez_valores():
    a, b = gerador.gerar_amostra(com(LOGNORMAL, 0.05), 0.5, 10, rng())
    assert a.shape == b.shape == (10,) and np.isfinite(a).all() and np.isfinite(b).all()


def test_n_igual_a_um_e_aceito():
    a, b = gerador.gerar_amostra(NORMAL, 0, 1, rng())
    assert a.shape == b.shape == (1,)


def test_sigma_zero_gera_grupos_constantes_com_o_efeito_exato():
    a, b = gerador.gerar_amostra({"familia": "lognormal", "mu": 1.0, "sigma": 0.0}, 0.5, 10, rng())
    assert a == pytest.approx(math.exp(1.0)) and b == pytest.approx(math.exp(1.5))
    assert len(set(a)) == len(set(b)) == 1
    a, b = gerador.gerar_amostra({"familia": "normal", "mu": 5.0, "sigma": 0.0}, 2.0, 10, rng())
    assert np.all(a == 5) and np.all(b == 5)  # δ está em unidades de σ, e σ = 0


@pytest.mark.parametrize(
    "cenario, trecho",
    [
        ({"familia": "poisson", "mu": 0, "sigma": 1}, "desconhecida"),
        ({"mu": 0, "sigma": 1}, "desconhecida"),
        ({"familia": "normal", "sigma": 1}, "'mu'"),
        ({"familia": "normal", "mu": 0}, "'sigma'"),
        ({"familia": "normal", "mu": 0, "sigma": -1}, "negativo"),
        ({"familia": "normal", "mu": float("nan"), "sigma": 1}, "finito"),
        (com(NORMAL, 1.5), "em \\[0, 1\\]"),
        (com(NORMAL, -0.1), "em \\[0, 1\\]"),
        (com(NORMAL, 0.1, fator=0), "positivo"),
        ({**NORMAL, "contaminacao": {"fator": 20}}, "'p'"),
    ],
)
def test_cenario_invalido_levanta_erro(cenario, trecho):
    with pytest.raises(ValueError, match=trecho):
        gerador.gerar_amostra(cenario, 0, 10, rng())


@pytest.mark.parametrize("n, n_rep", [(0, 1), (-5, 1), (10, 0), (2.5, 1), (True, 1), ("10", 1)])
def test_tamanhos_invalidos_levantam_erro(n, n_rep):
    with pytest.raises(ValueError, match="inteiro positivo"):
        gerador.gerar_lote(NORMAL, 0, n, n_rep, rng())


def test_delta_nao_finito_e_rng_invalido_levantam_erro():
    with pytest.raises(ValueError, match="delta"):
        gerador.gerar_amostra(NORMAL, float("inf"), 10, rng())
    with pytest.raises(TypeError, match="Generator"):
        gerador.gerar_amostra(NORMAL, 0, 10, np.random.RandomState(1))


def test_aceita_inteiros_do_numpy_em_n_e_n_rep():
    A, _ = gerador.gerar_lote(NORMAL, 0, np.int64(5), np.int32(3), rng())
    assert A.shape == (3, 5)
