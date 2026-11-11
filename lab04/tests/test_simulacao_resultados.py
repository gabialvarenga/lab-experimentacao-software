"""Verificação da simulação (S02-06): o motor dá o resultado esperado no caso fácil e os CSVs
versionados são íntegros, reprodutíveis e coerentes.

Complementa `test_simulacao.py`, que testa o motor e o formato de cada CSV: aqui estão o controle
com n grande, a reprodução byte a byte, a integridade dos resultados e a monotonia do poder.

Banda de Monte Carlo: com `n_rep` repetições, uma taxa verdadeira `p` é estimada com erro-padrão
sqrt(p (1 − p) / n_rep); a banda de 95% é 1,96 vezes isso (±0,43 ponto percentual em torno de 5%
com 10.000 repetições).
"""

import copy
from pathlib import Path

import numpy as np
import pandas as pd
import pytest
from scipy import stats

from lab04 import config, gerador, simulacao

CFG = config.carregar()
SIM = config.simulacao(CFG)
CENARIOS = {c["id"]: c for c in SIM["cenarios"]}
PASTA = Path(CFG["pasta"]) / "dados" / "simulacao"
CSVS = {"c0_c1": ["C0", "C1"], "c2_c3": ["C2", "C3"], "c4": ["C4"]}
CHAVE = ["cenario", "delta", "alfa", "teste"]
N_REP = SIM["repeticoes"]


def banda(p: float, n_rep: int, z: float = 1.96) -> float:
    """Meia-largura da banda de Monte Carlo de uma taxa `p` estimada com `n_rep` repetições."""
    return z * np.sqrt(p * (1 - p) / n_rep)


def lido(nome: str) -> pd.DataFrame:
    return pd.read_csv(PASTA / f"{nome}.csv")


def todos() -> pd.DataFrame:
    return pd.concat([lido(nome) for nome in CSVS], ignore_index=True)


def bytes_lf(caminho) -> bytes:
    """Conteúdo do arquivo com fins de linha LF (o checkout no Windows pode converter para CRLF)."""
    return Path(caminho).read_bytes().replace(b"\r\n", b"\n")


# --- a banda de Monte Carlo ---


def test_banda_de_5_por_cento_com_10_mil_repeticoes_e_043_ponto_percentual():
    assert banda(0.05, 10_000) == pytest.approx(0.0043, abs=0.00005)
    assert banda(0.01, 10_000) == pytest.approx(0.00195, abs=0.00005)


# --- 1. controle: dados normais, n grande ---


@pytest.mark.parametrize("n", [200, 500])
def test_controle_com_n_grande_dados_normais_mantem_o_erro_tipo_i_dentro_da_banda(n):
    """Caso fácil: com H₀ verdadeira, dados normais e n grande, os dois testes rejeitam em torno de α.

    Se este teste falhar, o código tem um problema (geração, teste ou contagem): investigar antes de
    olhar qualquer resultado das simulações finais.
    """
    cenario = {**CENARIOS["C0"], "n": n}
    rng = np.random.default_rng(np.random.SeedSequence(42, spawn_key=(99, n)))  # célula própria, fora da grade
    linhas = pd.DataFrame(simulacao.simular(cenario, 0.0, N_REP, rng))
    assert len(linhas) == 4
    for _, linha in linhas.iterrows():
        assert abs(linha["taxa"] - linha["alfa"]) <= banda(linha["alfa"], N_REP), (
            f"{linha['teste']} em α = {linha['alfa']}: taxa {linha['taxa']:.4f} fora da banda"
        )


def test_o_controle_pega_um_teste_defeituoso():
    """Sensibilidade do controle: um teste que rejeita demais (p-valor pela metade) sai da banda."""
    cenario = {**CENARIOS["C0"], "n": 200}
    rng = np.random.default_rng(np.random.SeedSequence(42, spawn_key=(99, 0)))
    A, B = gerador.gerar_lote(cenario, 0.0, 200, N_REP, rng)
    p = stats.ttest_ind(A, B, axis=1, equal_var=False).pvalue
    taxa_defeituosa = float((p / 2 < 0.05).mean())
    assert abs(taxa_defeituosa - 0.05) > banda(0.05, N_REP)


@pytest.mark.parametrize("id_", ["C0", "C1", "C4"])
def test_o_motor_conta_as_mesmas_rejeicoes_que_o_scipy_chamado_repeticao_a_repeticao(id_):
    """Confere a contagem do motor (vetorizada) contra o SciPy direto, um par de amostras por vez."""
    cenario, delta, n_rep = CENARIOS[id_], CENARIOS[id_]["efeitos"][2], 400
    semente = np.random.SeedSequence(42, spawn_key=(98, 0))
    linhas = pd.DataFrame(simulacao.simular(cenario, delta, n_rep, np.random.default_rng(semente)))
    A, B = gerador.gerar_lote(cenario, delta, cenario["n"], n_rep, np.random.default_rng(semente))
    p_welch = np.array([stats.ttest_ind(a, b, equal_var=False).pvalue for a, b in zip(A, B)])
    p_mw = np.array([stats.mannwhitneyu(a, b, alternative="two-sided").pvalue for a, b in zip(A, B)])
    for alfa in SIM["alfas"]:
        esperado = {"welch": int((p_welch < alfa).sum()), "mann_whitney": int((p_mw < alfa).sum())}
        obtido = linhas[linhas["alfa"] == alfa].set_index("teste")["rejeicoes"].to_dict()
        assert obtido == esperado


# --- 2. reprodutibilidade ---


def cfg_em(pasta, **mudancas):
    cfg = copy.deepcopy(CFG)
    cfg["pasta"] = str(pasta)
    cfg.update(mudancas)
    return cfg


def test_mesma_semente_gera_o_mesmo_csv_byte_a_byte(tmp_path):
    cfg = cfg_em(tmp_path)
    simulacao.rodar_grade(cfg, n_rep=500, saida="a.csv", cenarios=["C0", "C4"])
    simulacao.rodar_grade(cfg, n_rep=500, saida="b.csv", cenarios=["C0", "C4"])
    assert bytes_lf(tmp_path / "a.csv") == bytes_lf(tmp_path / "b.csv")


def test_semente_diferente_gera_outro_csv(tmp_path):
    simulacao.rodar_grade(cfg_em(tmp_path), n_rep=500, saida="a.csv", cenarios=["C0"])
    simulacao.rodar_grade(cfg_em(tmp_path, semente=43), n_rep=500, saida="b.csv", cenarios=["C0"])
    assert bytes_lf(tmp_path / "a.csv") != bytes_lf(tmp_path / "b.csv")


@pytest.mark.parametrize("nome", list(CSVS))
def test_csv_versionado_e_reproduzido_byte_a_byte_pela_semente_do_config(tmp_path, nome):
    """Refazer a simulação com o config congelado dá, byte a byte, o CSV que está no repositório."""
    simulacao.rodar_grade(cfg_em(tmp_path), saida=f"{nome}.csv", cenarios=CSVS[nome])
    assert bytes_lf(tmp_path / f"{nome}.csv") == bytes_lf(PASTA / f"{nome}.csv")


# --- 3. integridade dos CSVs ---


@pytest.mark.parametrize("nome", list(CSVS))
def test_csv_tem_as_colunas_e_as_linhas_esperadas_do_config(nome):
    tabela = lido(nome)
    assert list(tabela.columns) == simulacao.COLUNAS
    esperado = [
        (c["id"], delta, alfa, teste)
        for c in SIM["cenarios"] if c["id"] in CSVS[nome]
        for delta in c["efeitos"] for alfa in SIM["alfas"] for teste in simulacao.TESTES
    ]
    obtido = list(tabela[CHAVE].itertuples(index=False, name=None))
    assert obtido == esperado   # as linhas certas, sem repetição, na ordem do config


def test_juntos_os_csvs_cobrem_toda_a_grade_do_config_uma_vez():
    tabela = todos()
    assert set(tabela["cenario"]) == set(CENARIOS) and not tabela.duplicated(CHAVE).any()
    assert len(tabela) == sum(len(c["efeitos"]) for c in SIM["cenarios"]) * len(SIM["alfas"]) * len(simulacao.TESTES)


def test_nenhuma_celula_tem_valor_ausente():
    tabela = todos()
    assert not tabela.isna().any().any()


def test_colunas_de_parametros_batem_com_o_config():
    tabela = todos()
    assert (tabela["n_rep"] == N_REP).all()
    for c in SIM["cenarios"]:
        assert (tabela[tabela["cenario"] == c["id"]]["n"] == c["n"]).all()
    assert set(tabela["alfa"]) == set(SIM["alfas"]) and set(tabela["teste"]) == set(simulacao.TESTES)


def test_rejeicoes_sao_inteiros_entre_0_e_n_rep_e_a_taxa_e_rejeicoes_sobre_n_rep():
    tabela = todos()
    assert pd.api.types.is_integer_dtype(tabela["rejeicoes"])
    assert tabela["rejeicoes"].between(0, tabela["n_rep"]).all()
    assert tabela["taxa"].between(0, 1).all()
    assert (tabela["taxa"] - tabela["rejeicoes"] / tabela["n_rep"]).abs().max() < 1e-6   # CSV com 6 casas


def test_o_intervalo_de_wilson_contem_a_taxa_e_e_o_do_motor():
    tabela = todos()
    assert (tabela["ic_inf"] <= tabela["taxa"] + 1e-6).all() and (tabela["taxa"] <= tabela["ic_sup"] + 1e-6).all()
    assert tabela["ic_inf"].between(0, 1).all() and tabela["ic_sup"].between(0, 1).all()
    refeito = np.array([simulacao.intervalo_wilson(int(r), int(n)) for r, n in zip(tabela["rejeicoes"], tabela["n_rep"])])
    assert np.abs(refeito[:, 0] - tabela["ic_inf"]).max() < 1e-6 and np.abs(refeito[:, 1] - tabela["ic_sup"]).max() < 1e-6


def test_a_mesma_repeticao_que_rejeita_em_alfa_menor_rejeita_em_alfa_maior():
    """Os eventos {p < 0,01} ⊂ {p < 0,05} estão aninhados: as rejeições em 1% não passam das de 5%."""
    t = todos().pivot_table(index=["cenario", "delta", "teste"], columns="alfa", values="rejeicoes")
    assert (t[0.01] <= t[0.05]).all()


def test_o_poder_nao_fica_abaixo_do_erro_tipo_i_alem_do_erro_de_monte_carlo():
    """Com efeito, a taxa de rejeição não pode ser menor que com H₀ (mesmo cenário, teste e α)."""
    tabela = todos().set_index(CHAVE)
    for (cenario, delta, alfa, teste), linha in tabela.iterrows():
        if delta == 0:
            continue
        nulo = tabela.loc[(cenario, 0.0, alfa, teste)]
        folga = banda(max(linha["taxa"], nulo["taxa"], alfa), N_REP, z=3) * np.sqrt(2)
        assert linha["taxa"] >= nulo["taxa"] - folga, f"{cenario} δ = {delta}, α = {alfa}, {teste}"


# --- 4. monotonia do poder ---


@pytest.mark.parametrize("id_", ["C0", "C1"])
def test_o_poder_cresce_com_o_efeito_em_c0_e_c1_dentro_do_erro_de_monte_carlo(id_):
    tabela = todos()
    tabela = tabela[tabela["cenario"] == id_]
    for (alfa, teste), grupo in tabela.groupby(["alfa", "teste"]):
        taxas = grupo.sort_values("delta")["taxa"].to_numpy()
        for antes, depois in zip(taxas, taxas[1:]):
            folga = np.hypot(banda(antes, N_REP, z=3), banda(depois, N_REP, z=3))
            assert depois >= antes - folga, f"{id_}, α = {alfa}, {teste}: {antes:.4f} → {depois:.4f}"


@pytest.mark.parametrize("id_", ["C0", "C1"])
def test_o_poder_do_maior_efeito_e_bem_maior_que_o_erro_tipo_i_em_c0_e_c1(id_):
    """Além de não cair, a curva sobe: o maior efeito rejeita pelo menos 3 vezes mais que H₀."""
    tabela = todos()
    tabela = tabela[tabela["cenario"] == id_]
    for (alfa, teste), grupo in tabela.groupby(["alfa", "teste"]):
        taxas = grupo.sort_values("delta")["taxa"].to_numpy()
        assert taxas[-1] >= 3 * max(taxas[0], alfa), f"{id_}, α = {alfa}, {teste}"


def test_em_c0_o_poder_chega_a_mais_de_90_por_cento_no_maior_efeito_nos_dois_testes():
    """No caso fácil (δ = 1 desvio-padrão, n = 30 por grupo) os dois testes acham o efeito quase sempre."""
    c0 = todos()
    c0 = c0[(c0["cenario"] == "C0") & (c0["alfa"] == 0.05) & (c0["delta"] == max(CENARIOS["C0"]["efeitos"]))]
    assert (c0["taxa"] > 0.9).all() and len(c0) == 2


@pytest.mark.parametrize("id_", ["C2", "C3", "C4"])
def test_a_monotonia_tambem_vale_nos_cenarios_com_violacao_dentro_do_erro_de_monte_carlo(id_):
    tabela = todos()
    tabela = tabela[tabela["cenario"] == id_]
    for (alfa, teste), grupo in tabela.groupby(["alfa", "teste"]):
        taxas = grupo.sort_values("delta")["taxa"].to_numpy()
        for antes, depois in zip(taxas, taxas[1:]):
            folga = np.hypot(banda(antes, N_REP, z=3), banda(depois, N_REP, z=3))
            assert depois >= antes - folga, f"{id_}, α = {alfa}, {teste}: {antes:.4f} → {depois:.4f}"
