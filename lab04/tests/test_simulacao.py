import copy
import warnings
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from lab04 import config, simulacao

CFG = config.carregar()
SIM = config.simulacao(CFG)
NORMAL = {"id": "N", "familia": "normal", "mu": 0.0, "sigma": 1.0, "n": 30}
CONSTANTE = {"id": "K", "familia": "normal", "mu": 1.0, "sigma": 0.0, "n": 10}
EFEITOS = [0.0, 0.5, 1.0, 1.5, 2.0]


def cfg_pequeno(pasta, **sim):
    """Config com dois cenários e 5 efeitos cada, para testar a grade sem custo."""
    cenarios = [
        {**NORMAL, "id": "A", "unidade_efeito": "dp", "efeitos": EFEITOS},
        {**NORMAL, "id": "B", "familia": "lognormal", "unidade_efeito": "log", "efeitos": EFEITOS, "n": 12},
    ]
    sim = {
        "repeticoes": 25,
        "repeticoes_piloto": 10,
        "alfas": [0.05, 0.01],
        "confianca_ic": 0.95,
        "piloto": "p.csv",
        "saida": "saida/resultados.csv",
        "cenarios": cenarios,
        **sim,
    }
    return {"semente": 42, "pasta": str(pasta), "simulacao": sim}


def csv(caminho) -> pd.DataFrame:
    return pd.read_csv(caminho)


# --- Wilson e semente ---


@pytest.mark.parametrize("k, n", [(0, 10), (10, 10), (5, 100), (43, 1000), (500, 10_000)])
def test_intervalo_de_wilson_confere_com_o_scipy(k, n):
    esperado = stats.binomtest(k, n).proportion_ci(confidence_level=0.95, method="wilson")
    inf, sup = simulacao.intervalo_wilson(k, n, 0.95)
    assert inf == pytest.approx(esperado.low, abs=1e-9) and sup == pytest.approx(esperado.high, abs=1e-9)


def test_wilson_respeita_o_nivel_e_os_limites():
    estreito, largo = simulacao.intervalo_wilson(50, 1000, 0.90), simulacao.intervalo_wilson(50, 1000, 0.99)
    assert largo[0] < estreito[0] < 0.05 < estreito[1] < largo[1]
    assert simulacao.intervalo_wilson(0, 10)[0] == 0 and simulacao.intervalo_wilson(10, 10)[1] == 1


@pytest.mark.parametrize("k, n", [(0, 0), (-1, 10), (11, 10)])
def test_wilson_recusa_contagens_invalidas(k, n):
    with pytest.raises(ValueError):
        simulacao.intervalo_wilson(k, n)


def test_geradores_de_celulas_diferentes_sao_independentes_e_o_da_mesma_celula_se_repete():
    a = simulacao.gerador_da_celula(42, 0, 1).random(5)
    assert np.array_equal(a, simulacao.gerador_da_celula(42, 0, 1).random(5))
    assert not np.array_equal(a, simulacao.gerador_da_celula(42, 1, 0).random(5))
    assert not np.array_equal(a, simulacao.gerador_da_celula(43, 0, 1).random(5))


# --- uma célula ---


def test_celula_devolve_uma_linha_por_alfa_e_teste_nas_colunas_congeladas():
    linhas = simulacao.simular(NORMAL, 0.5, 200, np.random.default_rng(1))
    assert [(x["alfa"], x["teste"]) for x in linhas] == [
        (0.05, "welch"),
        (0.05, "mann_whitney"),
        (0.01, "welch"),
        (0.01, "mann_whitney"),
    ]
    for linha in linhas:
        assert list(linha) == simulacao.COLUNAS
        assert (linha["cenario"], linha["delta"], linha["n"], linha["n_rep"]) == ("N", 0.5, 30, 200)
        assert linha["taxa"] == linha["rejeicoes"] / 200
        assert linha["ic_inf"] <= linha["taxa"] <= linha["ic_sup"]


def test_alfas_e_confianca_sao_opcionais():
    linhas = simulacao.simular(NORMAL, 0.5, 200, np.random.default_rng(1), alfas=[0.10], confianca=0.80)
    assert {x["alfa"] for x in linhas} == {0.10} and len(linhas) == 2
    padrao = simulacao.simular(NORMAL, 0.5, 200, np.random.default_rng(1), alfas=[0.10])
    assert all(a["ic_sup"] - a["ic_inf"] < p["ic_sup"] - p["ic_inf"] for a, p in zip(linhas, padrao))


def test_alfa_menor_rejeita_menos():
    linhas = simulacao.simular(NORMAL, 0.5, 500, np.random.default_rng(1))
    for teste in ("welch", "mann_whitney"):
        por_alfa = {x["alfa"]: x["rejeicoes"] for x in linhas if x["teste"] == teste}
        assert por_alfa[0.01] <= por_alfa[0.05]


def test_erro_tipo_i_em_dados_normais_fica_perto_de_5_e_de_1_por_cento():
    linhas = simulacao.simular(NORMAL, 0.0, 10_000, np.random.default_rng(3))
    for linha in linhas:
        assert linha["ic_inf"] <= linha["alfa"] <= linha["ic_sup"], linha


def test_efeito_grande_em_dados_normais_rejeita_quase_sempre():
    linhas = simulacao.simular(NORMAL, 2.0, 300, np.random.default_rng(1), alfas=[0.05])
    assert all(x["taxa"] > 0.99 for x in linhas)


def test_mesmo_gerador_repete_a_celula_e_gerador_novo_nao():
    a = simulacao.simular(NORMAL, 0.5, 100, simulacao.gerador_da_celula(42, 0, 0))
    assert a == simulacao.simular(NORMAL, 0.5, 100, simulacao.gerador_da_celula(42, 0, 0))
    assert a != simulacao.simular(NORMAL, 0.5, 100, simulacao.gerador_da_celula(42, 0, 1))


def test_p_valor_nan_nao_conta_como_rejeicao_e_avisa():
    with pytest.warns(UserWarning, match="NaN"):
        linhas = simulacao.simular(CONSTANTE, 0.0, 20, np.random.default_rng(1), alfas=[0.05])
    assert [x["rejeicoes"] for x in linhas if x["teste"] == "welch"] == [0]


def test_celula_sem_nan_nao_avisa():
    with warnings.catch_warnings():
        warnings.simplefilter("error")
        simulacao.simular(NORMAL, 0.5, 50, np.random.default_rng(1))


def test_amostra_pequena_usa_o_mann_whitney_exato_e_o_resultado_e_valido():
    pequeno = {**NORMAL, "n": 5}
    linhas = simulacao.simular(pequeno, 0.0, 400, np.random.default_rng(2), alfas=[0.05])
    mw = next(x for x in linhas if x["teste"] == "mann_whitney")
    assert mw["n"] == 5 and mw["taxa"] <= 0.05  # o exato é conservador por discretização


@pytest.mark.parametrize(
    "cenario, delta, n_rep",
    [
        ({**NORMAL, "familia": "x"}, 0.0, 10),
        ({**NORMAL, "sigma": -1.0}, 0.0, 10),
        (NORMAL, float("nan"), 10),
        (NORMAL, 0.0, 0),
    ],
)
def test_entradas_invalidas_levantam_value_error(cenario, delta, n_rep):
    with pytest.raises(ValueError):
        simulacao.simular(cenario, delta, n_rep, np.random.default_rng(1))


@pytest.mark.parametrize("n, esperado", [(30, "asymptotic"), (10, "asymptotic"), (9, "asymptotic")])
def test_metodo_do_mann_whitney_acima_de_8_e_assintotico(n, esperado):
    assert simulacao.metodo_mw_do_cenario(n) == esperado


def test_metodo_do_mann_whitney_com_n_pequeno_e_exato_sem_empates():
    assert simulacao.metodo_mw_do_cenario(8).startswith("exact")


# --- a grade ---


def test_celulas_seguem_a_ordem_do_config_e_cada_uma_tem_o_seu_gerador():
    cel = simulacao.celulas(SIM, 42)
    assert [(i, j) for i, j, *_ in cel][:3] == [(0, 0), (0, 1), (0, 2)]
    assert len(cel) == sum(len(c["efeitos"]) for c in SIM["cenarios"])
    for i, j, cenario, delta, rng in cel:
        assert delta == SIM["cenarios"][i]["efeitos"][j] and cenario is SIM["cenarios"][i]
        assert rng.random() == simulacao.gerador_da_celula(42, i, j).random()


def test_grade_tem_uma_linha_por_cenario_efeito_alfa_e_teste(tmp_path):
    tabela = simulacao.rodar_grade(cfg_pequeno(tmp_path))
    assert list(tabela.columns) == simulacao.COLUNAS and len(tabela) == 2 * 5 * 2 * 2
    assert set(tabela["n_rep"]) == {25}  # simulacao.repeticoes por padrão
    assert tabela.groupby("cenario")["delta"].unique().map(list).to_dict() == {"A": EFEITOS, "B": EFEITOS}
    assert set(tabela[tabela["cenario"] == "B"]["n"]) == {12}


def test_grade_grava_o_csv_em_saida_criando_a_pasta(tmp_path):
    tabela = simulacao.rodar_grade(cfg_pequeno(tmp_path))
    destino = tmp_path / "saida" / "resultados.csv"
    assert destino.exists()
    pd.testing.assert_frame_equal(csv(destino), tabela, check_dtype=False)
    assert b"\r" not in destino.read_bytes()


def test_grade_aceita_n_rep_e_saida_proprios(tmp_path):
    tabela = simulacao.rodar_grade(cfg_pequeno(tmp_path), n_rep=7, saida="outra/pasta/t.csv")
    assert set(tabela["n_rep"]) == {7} and (tmp_path / "outra" / "pasta" / "t.csv").exists()
    assert not (tmp_path / "saida").exists()


def test_mesma_semente_gera_o_mesmo_csv(tmp_path):
    simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="1.csv")
    simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="2.csv")
    assert (tmp_path / "1.csv").read_bytes() == (tmp_path / "2.csv").read_bytes()


def test_semente_diferente_gera_outro_csv(tmp_path):
    simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="1.csv")
    simulacao.rodar_grade({**cfg_pequeno(tmp_path), "semente": 43}, saida="2.csv")
    assert (tmp_path / "1.csv").read_bytes() != (tmp_path / "2.csv").read_bytes()


def test_ordem_de_execucao_das_celulas_nao_muda_o_resultado(tmp_path, monkeypatch):
    normal = simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="normal.csv")
    original = simulacao.celulas
    monkeypatch.setattr(simulacao, "celulas", lambda sim, semente: original(sim, semente)[::-1])
    invertida = simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="invertida.csv")
    pd.testing.assert_frame_equal(normal, invertida)
    assert (tmp_path / "normal.csv").read_bytes() == (tmp_path / "invertida.csv").read_bytes()


def test_acrescentar_um_cenario_no_fim_nao_muda_as_celulas_existentes(tmp_path):
    base = simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="base.csv")
    cfg = cfg_pequeno(tmp_path)
    cfg["simulacao"]["cenarios"].append({**NORMAL, "id": "C", "unidade_efeito": "dp", "efeitos": EFEITOS})
    maior = simulacao.rodar_grade(cfg, saida="maior.csv")
    pd.testing.assert_frame_equal(maior[maior["cenario"] != "C"].reset_index(drop=True), base)


def test_grade_registra_o_metodo_do_mann_whitney_o_tempo_e_os_p_valores_nan(tmp_path):
    tabela = simulacao.rodar_grade(cfg_pequeno(tmp_path))
    assert tabela.attrs["mw_metodo"] == {"A": "asymptotic", "B": "asymptotic"}
    assert tabela.attrs["p_nan"] == {"welch": 0, "mann_whitney": 0}
    assert tabela.attrs["segundos"] > 0


def test_grade_conta_e_avisa_os_p_valores_nan(tmp_path):
    cfg = cfg_pequeno(tmp_path)
    cfg["simulacao"]["cenarios"] = [{**CONSTANTE, "unidade_efeito": "dp", "efeitos": [0.0, 0.0001, 0.0002, 0.0003, 0.0004]}]
    with pytest.warns(UserWarning, match="NaN"):
        tabela = simulacao.rodar_grade(cfg, n_rep=5)
    assert tabela.attrs["p_nan"]["welch"] == 5 * 5  # 5 efeitos × 5 repetições, todas sem variância
    assert tabela[tabela["teste"] == "welch"]["rejeicoes"].sum() == 0


def test_grade_valida_o_config(tmp_path):
    cfg = cfg_pequeno(tmp_path)
    cfg["simulacao"]["cenarios"][0]["efeitos"] = [0.1, 0.2, 0.3, 0.4, 0.5]
    with pytest.raises(ValueError, match="começar em 0"):
        simulacao.rodar_grade(cfg)


def test_grade_do_config_congelado_com_1000_repeticoes_reproduz_o_piloto_versionado(tmp_path):
    """O piloto versionado é a grade do config com 1.000 repetições e a semente 42."""
    cfg = copy.deepcopy(CFG)
    cfg["pasta"] = str(tmp_path)
    tabela = simulacao.rodar_grade(cfg, n_rep=SIM["repeticoes_piloto"], saida="piloto.csv")
    versionado = csv(Path(CFG["pasta"]) / SIM["piloto"])
    pd.testing.assert_frame_equal(csv(tmp_path / "piloto.csv"), versionado)
    assert tabela.attrs["mw_metodo"] == {c["id"]: "asymptotic" for c in SIM["cenarios"]}


# --- cenários à parte, registro e linha de comando (S02-03) ---


def test_grade_so_dos_cenarios_pedidos_tem_as_mesmas_linhas_da_grade_inteira(tmp_path):
    inteira = simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="todos.csv")
    so_b = simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="b.csv", cenarios=["B"])
    assert set(so_b["cenario"]) == {"B"} and so_b.attrs["mw_metodo"] == {"B": "asymptotic"}
    pd.testing.assert_frame_equal(so_b, inteira[inteira["cenario"] == "B"].reset_index(drop=True))


def test_a_ordem_dos_ids_em_cenarios_nao_importa(tmp_path):
    a = simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="a.csv", cenarios=["A", "B"])
    b = simulacao.rodar_grade(cfg_pequeno(tmp_path), saida="b.csv", cenarios=["B", "A"])
    pd.testing.assert_frame_equal(a, b)


@pytest.mark.parametrize("cenarios", [["Z"], ["A", "Z"], []])
def test_cenario_desconhecido_ou_lista_vazia_levanta_erro(tmp_path, cenarios):
    with pytest.raises(ValueError, match="não estão no config"):
        simulacao.rodar_grade(cfg_pequeno(tmp_path), cenarios=cenarios)


def test_sha256_ignora_a_diferenca_entre_lf_e_crlf(tmp_path):
    lf, crlf = tmp_path / "lf.txt", tmp_path / "crlf.txt"
    lf.write_bytes(b"a: 1\nb: 2\n")
    crlf.write_bytes(b"a: 1\r\nb: 2\r\n")
    assert simulacao.sha256(lf) == simulacao.sha256(crlf)
    lf.write_bytes(b"a: 1\nb: 3\n")
    assert simulacao.sha256(lf) != simulacao.sha256(crlf)


def test_registro_traz_comando_parametros_hash_e_erro_tipo_i(tmp_path):
    cfg = cfg_pequeno(tmp_path)
    caminho = Path(CFG["pasta"]) / "config.yaml"
    tabela = simulacao.rodar_grade(cfg, cenarios=["A"])
    texto = simulacao.registro(cfg, tabela, "python -m lab04.simulacao --cenarios A", caminho)
    for trecho in [
        "# Registro da simulação A",
        "`python -m lab04.simulacao --cenarios A`",
        "| Repetições por célula | 25 |",
        "| α | 0.05, 0.01 |",
        "| Semente | 42 |",
        simulacao.sha256(caminho),
        "| Linhas do CSV | 20 |",
        "| Mann-Whitney | A: asymptotic |",
        "## Erro tipo I (δ = 0)",
    ]:
        assert trecho in texto
    assert texto.count("| A | 0.0") == 4  # δ = 0: 2 alfas × 2 testes
    assert texto == simulacao.registro(cfg, tabela, "python -m lab04.simulacao --cenarios A", caminho)


def test_main_grava_o_csv_e_o_registro_ao_lado(tmp_path, capsys):
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text((Path(CFG["pasta"]) / "config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    saida = "sim/c4.csv"
    assert simulacao.main(["--config", str(arquivo), "--cenarios", "C4", "--saida", saida]) == 0
    tabela = csv(tmp_path / saida)
    assert set(tabela["cenario"]) == {"C4"} and set(tabela["n_rep"]) == {SIM["repeticoes"]}
    registro = (tmp_path / "sim" / "registro-c4.md").read_text(encoding="utf-8")
    assert f"--cenarios C4 --saida {saida}" in registro and simulacao.sha256(arquivo) in registro
    assert "linhas em" in capsys.readouterr().out


def test_main_sem_cenarios_roda_todos_e_usa_a_saida_do_config(tmp_path):
    texto = (Path(CFG["pasta"]) / "config.yaml").read_text(encoding="utf-8")
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text(texto.replace("repeticoes: 10000", "repeticoes: 20"), encoding="utf-8")
    assert simulacao.main(["--config", str(arquivo)]) == 0
    tabela = csv(tmp_path / SIM["saida"])
    assert set(tabela["cenario"]) == set(c["id"] for c in SIM["cenarios"]) and set(tabela["n_rep"]) == {20}
    assert (tmp_path / "dados" / "simulacao" / "registro-resultados.md").exists()


# --- o CSV de C0 e C1 versionado (S02-03) ---

C0_C1 = Path(CFG["pasta"]) / "dados" / "simulacao" / "c0_c1.csv"
COMANDO_C0_C1 = ["--cenarios", "C0", "C1", "--saida", "dados/simulacao/c0_c1.csv"]


def test_csv_de_c0_e_c1_tem_o_formato_e_o_numero_de_linhas_esperados():
    tabela = csv(C0_C1)
    esperado = sum(len(c["efeitos"]) for c in SIM["cenarios"] if c["id"] in ("C0", "C1")) * len(SIM["alfas"]) * 2
    assert list(tabela.columns) == simulacao.COLUNAS and len(tabela) == esperado == 48
    assert set(tabela["cenario"]) == {"C0", "C1"} and set(tabela["n_rep"]) == {10_000}
    assert len(tabela[["cenario", "delta", "alfa", "teste"]].drop_duplicates()) == len(tabela)
    assert (tabela[tabela["cenario"] == "C0"]["delta"].unique() == SIM["cenarios"][0]["efeitos"]).all()
    assert (tabela[tabela["cenario"] == "C1"]["delta"].unique() == SIM["cenarios"][1]["efeitos"]).all()


def test_csv_de_c0_e_c1_e_reproduzido_pelo_comando_do_readme(tmp_path):
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text((Path(CFG["pasta"]) / "config.yaml").read_text(encoding="utf-8"), encoding="utf-8")
    assert simulacao.main(["--config", str(arquivo), *COMANDO_C0_C1]) == 0
    pd.testing.assert_frame_equal(csv(tmp_path / "dados" / "simulacao" / "c0_c1.csv"), csv(C0_C1))


def test_c0_e_c1_na_grade_inteira_dao_as_mesmas_linhas_que_rodar_so_os_dois(tmp_path):
    cfg = copy.deepcopy(CFG)
    cfg["pasta"] = str(tmp_path)
    inteira = simulacao.rodar_grade(cfg, saida="inteira.csv")
    so = inteira[inteira["cenario"].isin(["C0", "C1"])].reset_index(drop=True)
    pd.testing.assert_frame_equal(so, csv(C0_C1), check_dtype=False)


def test_registro_versionado_cita_o_hash_do_config_congelado():
    """Se o config.yaml mudar depois da simulação, este teste falha: a simulação precisa ser refeita."""
    registro = (C0_C1.parent / "registro-c0_c1.md").read_text(encoding="utf-8")
    assert simulacao.sha256(Path(CFG["pasta"]) / "config.yaml") in registro
    assert "python -m lab04.simulacao --cenarios C0 C1 --saida dados/simulacao/c0_c1.csv" in registro


def test_erro_tipo_i_de_c0_fica_perto_do_nominal():
    """Q1: com δ = 0 e dados normais, as taxas ficam em torno de α (investigação da S02-03 no README)."""
    tabela = csv(C0_C1)
    c0 = tabela[(tabela["cenario"] == "C0") & (tabela["delta"] == 0)]
    assert c0[c0["alfa"] == 0.05]["taxa"].between(0.04, 0.06).all()
    assert c0[c0["alfa"] == 0.01]["taxa"].between(0.005, 0.015).all()
