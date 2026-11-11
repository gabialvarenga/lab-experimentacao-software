from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lab04 import calibracao, config, gerador, piloto, simulacao

CFG = config.carregar()
SIM = config.simulacao(CFG)
CENARIOS = {c["id"]: c for c in SIM["cenarios"]}
N_LINHAS = sum(len(c["efeitos"]) for c in SIM["cenarios"]) * len(SIM["alfas"]) * len(simulacao.TESTES)


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


# --- o CSV do piloto versionado ---


def test_csv_do_piloto_tem_o_formato_congelado():
    tabela = csv_do_piloto()
    assert list(tabela.columns) == simulacao.COLUNAS
    chaves = tabela[["cenario", "delta", "alfa", "teste"]].drop_duplicates()
    assert len(chaves) == len(tabela) == N_LINHAS  # uma linha por (cenário, efeito, α, teste)
    assert set(tabela["n_rep"]) == {SIM["repeticoes_piloto"]}
    assert set(tabela["teste"]) == set(simulacao.TESTES) and set(tabela["alfa"]) == set(SIM["alfas"])
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
    linhas = simulacao.simular(
        cenario,
        delta,
        SIM["repeticoes_piloto"],
        simulacao.gerador_da_celula(42, i, j),
        alfas=SIM["alfas"],
        confianca=SIM["confianca_ic"],
    )
    novo = pd.DataFrame(linhas, columns=simulacao.COLUNAS).round({"taxa": 6, "ic_inf": 6, "ic_sup": 6})
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
    assert list(pd.read_csv(destino).columns) == simulacao.COLUNAS


def test_main_grava_o_piloto(tmp_path, monkeypatch, capsys):
    monkeypatch.setitem(SIM, "repeticoes_piloto", 5)
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text((Path(CFG["pasta"]) / "config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    assert piloto.main([str(arquivo)]) == 0
    assert (tmp_path / SIM["piloto"]).exists() and "piloto gravado" in capsys.readouterr().out
