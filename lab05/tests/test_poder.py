"""Testes de `lab05/poder.py`.

Os testes do intervalo de Wilson e do gerador por célula foram copiados de
`lab04/tests/test_simulacao.py`; os demais são novos.
"""

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from conftest import coleta_sintetica
from lab05 import poder

# --- copiados do Lab04 ---


@pytest.mark.parametrize("k, n", [(0, 10), (10, 10), (5, 100), (43, 1000), (500, 10_000)])
def test_intervalo_de_wilson_confere_com_o_scipy(k, n):
    esperado = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    inf, sup = poder.intervalo_wilson(k, n, 0.95)
    assert inf == pytest.approx(esperado.low, abs=1e-9) and sup == pytest.approx(esperado.high, abs=1e-9)


def test_wilson_respeita_o_nivel_e_os_limites():
    estreito, largo = poder.intervalo_wilson(50, 1000, 0.90), poder.intervalo_wilson(50, 1000, 0.99)
    assert largo[0] < estreito[0] < 0.05 < estreito[1] < largo[1]
    assert poder.intervalo_wilson(0, 10)[0] == 0 and poder.intervalo_wilson(10, 10)[1] == 1


@pytest.mark.parametrize("k, n", [(0, 0), (-1, 10), (11, 10)])
def test_wilson_recusa_contagens_invalidas(k, n):
    with pytest.raises(ValueError):
        poder.intervalo_wilson(k, n)


def test_geradores_de_celulas_diferentes_sao_independentes_e_o_da_mesma_celula_se_repete():
    a = poder.gerador_da_celula(42, 0, 1).random(5)
    assert np.array_equal(a, poder.gerador_da_celula(42, 0, 1).random(5))
    assert not np.array_equal(a, poder.gerador_da_celula(42, 1, 0).random(5))
    assert not np.array_equal(a, poder.gerador_da_celula(43, 0, 1).random(5))


# --- novos no Lab05 ---


def test_gerar_lote_tem_a_forma_e_a_razao_de_medianas_pedidas():
    A, B = poder.gerar_lote(0.1, 0.05, 2000, 3, np.random.default_rng(0))
    assert A.shape == B.shape == (3, 2000)
    assert np.median(A) / np.median(B) == pytest.approx(1.05, abs=0.01)
    assert np.std(np.log(B)) == pytest.approx(0.1, abs=0.005)


def test_gerar_lote_sem_sigma_e_constante():
    A, B = poder.gerar_lote(0.0, 0.2, 4, 2, np.random.default_rng(0))
    assert np.allclose(A, 1.2) and np.allclose(B, 1.0)


@pytest.mark.parametrize("sigma, diferenca, n, n_rep", [(-0.1, 0.05, 5, 5), (np.nan, 0.05, 5, 5), (0.1, -1.0, 5, 5),
                                                        (0.1, np.inf, 5, 5), (0.1, 0.05, 0, 5), (0.1, 0.05, 5, True)])
def test_gerar_lote_recusa_parametros_invalidos(sigma, diferenca, n, n_rep):
    with pytest.raises(ValueError):
        poder.gerar_lote(sigma, diferenca, n, n_rep, np.random.default_rng(0))


def test_gerar_lote_exige_um_generator():
    with pytest.raises(TypeError):
        poder.gerar_lote(0.1, 0.05, 5, 5, 42)


def test_estimar_sigmas_junta_os_dois_servidores_pela_regra_do_lab04():
    df = coleta_sintetica(n=2)
    df["ops_s"] = np.where(df["servidor"] == "redis", np.where(df["repeticao"] == 1, 1.0, np.e), np.e**2)
    s = poder.estimar_sigmas(df, "ops_s")
    # log do Redis: 0 e 1 (variância 0,5); log do Valkey: 2 e 2 (variância 0) → σ = √0,25
    assert len(s) == 6 and s["sigma_log"].to_numpy() == pytest.approx([0.5] * 6) and (s["n_redis"] == 2).all()


def test_estimar_sigmas_recupera_o_sigma_da_coleta():
    s = poder.estimar_sigmas(coleta_sintetica(n=400, sigma=0.15, semente=3), "lat_p99_ms")
    assert s["sigma_log"].to_numpy() == pytest.approx(0.15, abs=0.01)


def test_estimar_sigmas_recusa_dados_invalidos():
    df = coleta_sintetica(n=2)
    with pytest.raises(ValueError, match="positivos"):
        poder.estimar_sigmas(df.assign(ops_s=0.0), "ops_s")
    with pytest.raises(ValueError, match="ao menos 2"):
        poder.estimar_sigmas(df[df["repeticao"] == 1], "ops_s")
    with pytest.raises(ValueError, match="faltam"):
        poder.estimar_sigmas(df.drop(columns="carga"), "ops_s")


def test_remover_efeito_bloco_desfaz_uma_deriva_comum():
    df = coleta_sintetica(n=5, sigma=0.0)
    derivado = df.copy()
    derivado.loc[derivado["repeticao"] == 2, "ops_s"] *= 0.8  # bloco 2 mais lento em todas as combinações
    ajustado = poder.remover_efeito_bloco(derivado, ["ops_s"])
    assert ajustado["ops_s"].to_numpy() == pytest.approx(df["ops_s"].to_numpy())
    assert poder.estimar_sigmas(derivado, "ops_s")["sigma_log"].gt(0).all()
    with pytest.raises(ValueError, match="repeticao"):
        poder.remover_efeito_bloco(df.drop(columns="repeticao"))


def test_sem_diferenca_a_familia_controla_o_erro_tipo_i():
    sigmas = [0.1] * 6
    rejeicoes = poder.poder_familia(sigmas, 20, 0.0, "welch", 4000, np.random.default_rng(0), cenario="todas")
    # cada comparação, sob H0 e com Holm, rejeita no máximo ~α/6 das vezes
    assert (rejeicoes / 4000 < 0.05 / 6 + 0.006).all()


def test_poder_conservador_confere_com_a_aproximacao_normal():
    sigma, diferenca, n = 0.1, 0.05, 60
    rejeicoes = poder.poder_familia([sigma] * 6, n, diferenca, "welch", 4000, np.random.default_rng(1))
    z = np.log1p(diferenca) / (sigma * np.sqrt(2 / n)) - stats.norm.ppf(1 - 0.05 / 12)
    assert rejeicoes / 4000 == pytest.approx([stats.norm.cdf(z)] * 6, abs=0.04)


def test_poder_cresce_com_n_e_e_maior_quando_todas_tem_efeito():
    rng = lambda: np.random.default_rng(2)  # noqa: E731
    pequeno = poder.poder_familia([0.1] * 6, 10, 0.05, "mann_whitney", 2000, rng())
    grande = poder.poder_familia([0.1] * 6, 60, 0.05, "mann_whitney", 2000, rng())
    todas = poder.poder_familia([0.1] * 6, 60, 0.05, "mann_whitney", 2000, rng(), cenario="todas")
    assert (grande > pequeno).all() and todas.sum() > grande.sum()


def test_comparacao_sem_variacao_conta_como_detectada():
    rejeicoes = poder.poder_familia([0.0, 0.1], 10, 0.05, "welch", 200, np.random.default_rng(0))
    assert rejeicoes[0] == 200
    assert poder.poder_familia([0.0, 0.1], 10, 0.0, "welch", 200, np.random.default_rng(0))[0] == 0


def test_poder_familia_recusa_cenario_e_teste_desconhecidos():
    with pytest.raises(ValueError, match="cenário"):
        poder.poder_familia([0.1], 10, 0.05, "welch", 10, np.random.default_rng(0), cenario="otimista")
    with pytest.raises(ValueError, match="teste"):
        poder.poder_familia([0.1], 10, 0.05, "anova", 10, np.random.default_rng(0))


def test_curva_tem_uma_linha_por_ponto_e_comparacao():
    df = coleta_sintetica(n=5, sigma=0.1)
    curva = poder.curva_poder(df, "ops_s", (10, 20), (0.05, 0.2), "welch", 200)
    assert list(curva.columns) == poder.COLUNAS_CURVA and len(curva) == 2 * 2 * 6
    assert curva["poder"].between(curva["ic_inf"], curva["ic_sup"]).all()


def test_curva_nao_depende_da_grade_nem_da_ordem():
    df = coleta_sintetica(n=5, sigma=0.1)
    inteira = poder.curva_poder(df, "ops_s", (10, 20, 30), (0.05, 0.1), "welch", 300)
    parte = poder.curva_poder(df, "ops_s", (30, 10), (0.1,), "welch", 300)
    esperado = inteira[(inteira["diferenca"] == 0.1) & inteira["n"].isin([10, 30])].sort_values(["n", "io_threads", "carga"])
    pd.testing.assert_frame_equal(parte.sort_values(["n", "io_threads", "carga"]).reset_index(drop=True), esperado.reset_index(drop=True))


def test_curva_usa_a_regra_5_1_sem_teste():
    df = coleta_sintetica(n=5, sigma=1.0, semente=1)
    assert (poder.curva_poder(df, "ops_s", (5,), (0.05,), n_rep=50)["teste"] == "mann_whitney").all()


def test_repeticoes_necessarias_acha_o_menor_n_e_marca_quando_a_grade_nao_basta():
    df = coleta_sintetica(n=5, sigma=0.05, semente=4)
    t = poder.repeticoes_necessarias(df, 0.10, 0.80, ["ops_s"], {"ops_s": "welch"}, (2, 5, 10, 20, 40), 500)
    assert list(t.columns) == poder.COLUNAS_REPETICOES and len(t) == 1
    linha = t.iloc[0]
    assert not linha["acima_da_grade"] and linha["n_necessario"] in (5, 10, 20, 40) and linha["poder_no_n"] >= 0.8
    curva = t.attrs["curva"]
    pior = curva.groupby("n")["poder"].min()
    assert pior[linha["n_necessario"]] >= 0.8 and (pior[pior.index < linha["n_necessario"]] < 0.8).all()
    assert linha["limitante"].startswith("io_threads ")
    curta = poder.repeticoes_necessarias(df, 0.01, 0.80, ["ops_s"], {"ops_s": "welch"}, (3, 4), 200)
    assert curta.iloc[0]["acima_da_grade"] and np.isnan(curta.iloc[0]["n_necessario"])


def test_diferenca_detectavel_escolhe_a_menor_que_basta_na_pior_comparacao():
    curva = pd.DataFrame({
        "metrica": "ops_s", "n": [30] * 6 + [60] * 2,
        "diferenca": [0.05, 0.05, 0.10, 0.10, 0.20, 0.20, 0.05, 0.05],
        "io_threads": [1, 4] * 4, "carga": "get",
        "poder": [0.9, 0.5, 0.95, 0.85, 1.0, 1.0, 0.5, 0.6],
    })  # fmt: skip
    d = poder.diferenca_detectavel(curva, 0.80).set_index("n")
    assert d.loc[30, "diferenca_detectavel"] == 0.10 and d.loc[30, "poder_no_ponto"] == 0.85
    assert np.isnan(d.loc[60, "diferenca_detectavel"])


def test_gerar_pares_tem_a_media_e_o_desvio_pedidos():
    D = poder.gerar_pares(0.1, 0.05, 4000, 2, np.random.default_rng(0))
    assert D.shape == (2, 4000)
    assert D.mean() == pytest.approx(np.log(1.05), abs=0.005) and D.std() == pytest.approx(0.1, abs=0.005)
    with pytest.raises(ValueError):
        poder.gerar_pares(-0.1, 0.05, 5, 5, np.random.default_rng(0))


def test_wilcoxon_pareado_controla_o_erro_tipo_i_e_ganha_poder_com_n():
    h0 = poder.poder_familia([0.1] * 6, 20, 0.0, poder.TESTE_PAREADO, 4000, np.random.default_rng(0), cenario="todas")
    assert (h0 / 4000 < 0.05 / 6 + 0.006).all()
    rng = lambda: np.random.default_rng(1)  # noqa: E731
    pequeno = poder.poder_familia([0.1] * 6, 10, 0.05, poder.TESTE_PAREADO, 2000, rng())
    grande = poder.poder_familia([0.1] * 6, 60, 0.05, poder.TESTE_PAREADO, 2000, rng())
    assert (grande > pequeno).all()


def test_poder_do_wilcoxon_pareado_perto_do_t_pareado():
    # poder exato do t pareado (t não central) com o n efetivo do Wilcoxon: eficiência de 3/π com dados normais
    sigma, diferenca, n = 0.1, 0.05, 40
    rejeicoes = poder.poder_familia([sigma] * 6, n, diferenca, poder.TESTE_PAREADO, 4000, np.random.default_rng(2), cenario="todas")
    alfa, n_efetivo = 0.05 / 6, n * 3 / np.pi
    critico = stats.t.ppf(1 - alfa / 2, n_efetivo - 1)
    esperado = 1 - stats.nct.cdf(critico, n_efetivo - 1, np.log1p(diferenca) / sigma * np.sqrt(n_efetivo))
    # no cenário "todas", Holm só pode ajudar: o poder fica entre o de α/6 e o de α
    assert (rejeicoes / 4000 > esperado - 0.03).all()
    sozinho = poder.poder_familia([sigma] * 6, n, diferenca, poder.TESTE_PAREADO, 4000, np.random.default_rng(2))
    assert sozinho / 4000 == pytest.approx([esperado] * 6, abs=0.03)


def test_curva_pareada_usa_raiz_de_2_vezes_o_sigma_sem_bloco():
    df = coleta_sintetica(n=5, sigma=0.1, semente=6)
    sem_bloco = poder.remover_efeito_bloco(df, ["ops_s"])
    curva = poder.curva_poder_pareada(sem_bloco, "ops_s", (10,), (0.05,), 100)
    esperado = poder.estimar_sigmas(sem_bloco, "ops_s")["sigma_log"].to_numpy() * np.sqrt(2)
    assert list(curva.columns) == poder.COLUNAS_CURVA and (curva["teste"] == poder.TESTE_PAREADO).all()
    assert curva["sigma_log"].to_numpy() == pytest.approx(esperado)


def test_repeticoes_necessarias_roda_no_piloto(piloto):
    t = poder.repeticoes_necessarias(piloto, metricas=["memoria_bytes"], grade=(5, 10), n_rep=200)
    assert t.iloc[0]["n_necessario"] == 5  # memória quase constante: 5 repetições bastam
