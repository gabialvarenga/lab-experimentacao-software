import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from lab04 import calibracao, config, gerador, piloto

CFG = config.carregar()
SIM = config.simulacao(CFG)
CENARIOS = {c["id"]: c for c in SIM["cenarios"]}
NORMAL = {"id": "N", "familia": "normal", "mu": 0.0, "sigma": 1.0, "n": 30}
N_LINHAS = sum(len(c["efeitos"]) for c in SIM["cenarios"]) * len(SIM["alfas"]) * len(piloto.TESTES)


def csv_do_piloto() -> pd.DataFrame:
    return pd.read_csv(Path(CFG["pasta"]) / SIM["piloto"])


# --- o config congelado (S02-01) ---


def test_config_tem_os_cinco_cenarios_na_ordem_c0_a_c4():
    assert list(CENARIOS) == ["C0", "C1", "C2", "C3", "C4"]


def test_cada_cenario_tem_ao_menos_cinco_efeitos_comecando_em_zero():
    for cenario in CENARIOS.values():
        assert len(cenario["efeitos"]) >= 5 and cenario["efeitos"][0] == 0


def test_parametros_congelados_da_simulacao():
    assert CFG["semente"] == 42
    assert SIM["repeticoes"] == 10_000 and SIM["repeticoes_piloto"] == 1_000
    assert SIM["alfas"] == [0.05, 0.01]


def test_c0_e_normal_em_desvios_padrao_e_c1_a_c4_sao_lognormais_em_log():
    c0 = CENARIOS["C0"]
    assert (c0["familia"], c0["unidade_efeito"], c0["n"]) == ("normal", "dp", 30)
    for id_ in ("C1", "C2", "C3", "C4"):
        assert (CENARIOS[id_]["familia"], CENARIOS[id_]["unidade_efeito"]) == ("lognormal", "log")


def test_c1_vem_da_calibracao_versionada():
    versionada = calibracao.ler(Path(CFG["pasta"]) / "dados" / "reais" / "calibracao.json")
    esperado, _ = gerador.cenario_calibrado(versionada)
    c1 = CENARIOS["C1"]
    assert c1["mu"] == pytest.approx(esperado["mu"], abs=5e-5)
    assert c1["sigma"] == pytest.approx(esperado["sigma"], abs=5e-5)
    assert c1["n"] == 30 and "contaminacao" not in c1


def test_c2_c3_e_c4_mudam_so_o_que_o_enunciado_pede():
    c1 = CENARIOS["C1"]
    assert 1.5 <= CENARIOS["C2"]["sigma"] <= 2 and CENARIOS["C2"]["sigma"] > c1["sigma"]
    assert CENARIOS["C2"]["mu"] == c1["mu"] and CENARIOS["C2"]["n"] == 30
    assert CENARIOS["C3"]["contaminacao"] == {"p": 0.05, "fator": 20}
    assert (CENARIOS["C3"]["mu"], CENARIOS["C3"]["sigma"], CENARIOS["C3"]["n"]) == (c1["mu"], c1["sigma"], 30)
    assert (CENARIOS["C4"]["mu"], CENARIOS["C4"]["sigma"], CENARIOS["C4"]["n"]) == (c1["mu"], c1["sigma"], 10)


def test_cenarios_do_config_funcionam_no_gerador():
    for cenario in CENARIOS.values():
        a, b = gerador.gerar_lote(cenario, cenario["efeitos"][-1], cenario["n"], 3, np.random.default_rng(1))
        assert a.shape == b.shape == (3, cenario["n"])


# --- Wilson e semente ---


@pytest.mark.parametrize("k, n", [(0, 10), (10, 10), (5, 100), (43, 1000), (500, 10_000)])
def test_intervalo_de_wilson_confere_com_o_scipy(k, n):
    esperado = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    inf, sup = piloto.intervalo_wilson(k, n, 0.95)
    assert inf == pytest.approx(esperado.low, abs=1e-9) and sup == pytest.approx(esperado.high, abs=1e-9)


def test_wilson_respeita_o_nivel_e_os_limites():
    estreito, largo = piloto.intervalo_wilson(50, 1000, 0.90), piloto.intervalo_wilson(50, 1000, 0.99)
    assert largo[0] < estreito[0] < 0.05 < estreito[1] < largo[1]
    assert piloto.intervalo_wilson(0, 10)[0] == 0 and piloto.intervalo_wilson(10, 10)[1] == 1


@pytest.mark.parametrize("k, n", [(0, 0), (-1, 10), (11, 10)])
def test_wilson_recusa_contagens_invalidas(k, n):
    with pytest.raises(ValueError):
        piloto.intervalo_wilson(k, n)


def test_geradores_de_celulas_diferentes_sao_independentes_e_o_da_mesma_celula_se_repete():
    a = piloto.gerador_da_celula(42, 0, 1).random(5)
    assert np.array_equal(a, piloto.gerador_da_celula(42, 0, 1).random(5))
    assert not np.array_equal(a, piloto.gerador_da_celula(42, 1, 0).random(5))
    assert not np.array_equal(a, piloto.gerador_da_celula(43, 0, 1).random(5))


# --- a célula e a grade ---


def test_celula_devolve_uma_linha_por_alfa_e_teste_nas_colunas_congeladas():
    linhas = piloto.simular_celula(NORMAL, 0.5, 200, np.random.default_rng(1), [0.05, 0.01])
    assert [(x["alfa"], x["teste"]) for x in linhas] == [
        (0.05, "welch"),
        (0.05, "mann_whitney"),
        (0.01, "welch"),
        (0.01, "mann_whitney"),
    ]
    for linha in linhas:
        assert list(linha) == piloto.COLUNAS
        assert (linha["cenario"], linha["delta"], linha["n"], linha["n_rep"]) == ("N", 0.5, 30, 200)
        assert linha["taxa"] == linha["rejeicoes"] / 200
        assert linha["ic_inf"] <= linha["taxa"] <= linha["ic_sup"]


def test_alfa_menor_rejeita_menos():
    linhas = piloto.simular_celula(NORMAL, 0.5, 500, np.random.default_rng(1), [0.05, 0.01])
    for teste in ("welch", "mann_whitney"):
        por_alfa = {x["alfa"]: x["rejeicoes"] for x in linhas if x["teste"] == teste}
        assert por_alfa[0.01] <= por_alfa[0.05]


def test_erro_tipo_i_do_controle_fica_perto_de_5_por_cento():
    linhas = piloto.simular_celula(NORMAL, 0.0, 5000, np.random.default_rng(3), [0.05])
    for linha in linhas:
        assert linha["ic_inf"] <= 0.05 <= linha["ic_sup"]


def test_efeito_grande_no_controle_rejeita_quase_sempre():
    linhas = piloto.simular_celula(NORMAL, 2.0, 300, np.random.default_rng(1), [0.05])
    assert all(x["taxa"] > 0.99 for x in linhas)


def test_p_valor_nan_nao_conta_como_rejeicao_e_avisa():
    constante = {"id": "K", "familia": "normal", "mu": 1.0, "sigma": 0.0, "n": 10}
    with pytest.warns(UserWarning, match="NaN"):
        linhas = piloto.simular_celula(constante, 0.0, 20, np.random.default_rng(1), [0.05])
    assert [x["rejeicoes"] for x in linhas if x["teste"] == "welch"] == [0]


def test_celula_sem_nan_nao_avisa():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        piloto.simular_celula(NORMAL, 0.5, 50, np.random.default_rng(1), [0.05])


def test_grade_pequena_tem_uma_linha_por_cenario_efeito_alfa_e_teste():
    tabela = piloto.rodar_piloto(CFG, n_rep=20)
    assert list(tabela.columns) == piloto.COLUNAS and len(tabela) == N_LINHAS
    assert set(tabela["n_rep"]) == {20}
    assert set(tabela["cenario"]) == set(CENARIOS)


def test_mesma_semente_gera_a_mesma_tabela():
    pd.testing.assert_frame_equal(piloto.rodar_piloto(CFG, n_rep=30), piloto.rodar_piloto(CFG, n_rep=30))


def test_resultado_da_celula_nao_depende_da_ordem_das_celulas():
    cenario = CENARIOS["C3"]
    isolada = piloto.simular_celula(cenario, 0.8, 100, piloto.gerador_da_celula(42, 3, 2), SIM["alfas"])
    # a mesma célula depois de rodar todas as outras, em ordem inversa
    reproduzida = None
    for i, c in reversed(list(enumerate(SIM["cenarios"]))):
        for j, delta in reversed(list(enumerate(c["efeitos"]))):
            linhas = piloto.simular_celula(c, delta, 100, piloto.gerador_da_celula(42, i, j), SIM["alfas"])
            if (i, j) == (3, 2):
                reproduzida = linhas
    assert reproduzida == isolada


def test_n_rep_padrao_e_o_do_piloto(monkeypatch):
    vistos = []
    monkeypatch.setattr(piloto, "simular_celula", lambda c, d, n_rep, *a, **k: vistos.append(n_rep) or [])
    piloto.rodar_piloto(CFG)
    assert set(vistos) == {SIM["repeticoes_piloto"]}


# --- o CSV do piloto versionado ---


def test_csv_do_piloto_tem_o_formato_congelado():
    tabela = csv_do_piloto()
    assert list(tabela.columns) == piloto.COLUNAS
    chaves = tabela[["cenario", "delta", "alfa", "teste"]].drop_duplicates()
    assert len(chaves) == len(tabela) == N_LINHAS  # uma linha por (cenário, efeito, α, teste)
    assert set(tabela["n_rep"]) == {SIM["repeticoes_piloto"]}
    assert set(tabela["teste"]) == set(piloto.TESTES) and set(tabela["alfa"]) == set(SIM["alfas"])
    assert (tabela["taxa"] - tabela["rejeicoes"] / tabela["n_rep"]).abs().max() < 1e-6
    assert (tabela["ic_inf"] <= tabela["taxa"]).all() and (tabela["taxa"] <= tabela["ic_sup"]).all()
    for id_, cenario in CENARIOS.items():
        do_cenario = tabela[tabela["cenario"] == id_]
        assert sorted(do_cenario["delta"].unique()) == cenario["efeitos"]
        assert set(do_cenario["n"]) == {cenario["n"]}


def test_csv_do_piloto_e_reproduzido_pelo_codigo():
    """Uma célula regerada com a semente do config dá as mesmas linhas do CSV versionado."""
    i, cenario = 4, CENARIOS["C4"]
    j = len(cenario["efeitos"]) - 1
    delta = cenario["efeitos"][j]
    linhas = piloto.simular_celula(
        cenario, delta, SIM["repeticoes_piloto"], piloto.gerador_da_celula(42, i, j), SIM["alfas"], SIM["confianca_ic"]
    )
    novo = pd.DataFrame(linhas, columns=piloto.COLUNAS).round({"taxa": 6, "ic_inf": 6, "ic_sup": 6})
    tabela = csv_do_piloto()
    antigo = tabela[(tabela["cenario"] == "C4") & (tabela["delta"] == delta)].reset_index(drop=True)
    pd.testing.assert_frame_equal(novo, antigo)


def test_a_curva_de_poder_de_c1_vai_de_perto_de_5_a_perto_de_100_por_cento():
    tabela = csv_do_piloto()
    mw = tabela[(tabela["cenario"] == "C1") & (tabela["alfa"] == 0.05) & (tabela["teste"] == "mann_whitney")]
    mw = mw.sort_values("delta")
    assert mw["taxa"].iloc[0] < 0.07 and mw["taxa"].iloc[-1] > 0.95
    assert mw["taxa"].is_monotonic_increasing


# --- execução ---


def test_executar_grava_o_csv_na_pasta_do_config(tmp_path, monkeypatch):
    monkeypatch.setitem(SIM, "repeticoes_piloto", 10)
    destino = piloto.executar({**CFG, "pasta": str(tmp_path)})
    assert destino == tmp_path / SIM["piloto"] and destino.exists()
    assert list(pd.read_csv(destino).columns) == piloto.COLUNAS


def test_main_grava_o_piloto(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(SIM, "repeticoes_piloto", 5)
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text((Path(CFG["pasta"]) / "config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    assert piloto.main([str(arquivo)]) == 0
    assert (tmp_path / SIM["piloto"]).exists() and "piloto gravado" in capsys.readouterr().out
