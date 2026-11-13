from pathlib import Path

import numpy as np
import pandas as pd
import pytest

from lab04 import config, gerador, graficos, interativo

PASTA = Path(__file__).resolve().parent.parent


@pytest.fixture(scope="module")
def dados():
    return interativo.carregar()


def test_carregar_le_os_arquivos_versionados(dados):
    assert set(dados) == {"cfg", "reais", "calibracao", "resultados", "cenarios"}
    assert list(dados["cenarios"]) == ["C0", "C1", "C2", "C3", "C4"]
    assert len(dados["resultados"]) == 120
    assert set(dados["reais"]["grupo"]) == {"com_bot", "sem_bot"}


def test_carregar_sem_resultados_devolve_none(tmp_path, dados):
    cfg = {**dados["cfg"], "simulacao": {**dados["cfg"]["simulacao"], "saida": str(tmp_path / "nao-existe.csv")}}
    assert interativo.carregar(cfg)["resultados"] is None


def test_indice_e_rotulo_do_cenario(dados):
    assert interativo.indice_do_cenario(dados["cfg"], "C3") == 3
    assert interativo.rotulo_cenario(dados["cenarios"]["C1"]) == "C1: referência"
    assert interativo.rotulo_cenario({"id": "X"}) == "X"


@pytest.mark.parametrize("familia, unidade", [("normal", "dp"), ("lognormal", "log")])
def test_cenario_personalizado(familia, unidade):
    cenario = interativo.cenario_personalizado(familia, 1.2, 25)
    assert cenario["id"] == interativo.ID_PERSONALIZADO
    assert cenario["unidade_efeito"] == unidade
    assert cenario["n"] == 25 and cenario["sigma"] == 1.2
    assert "contaminacao" not in cenario


def test_cenario_personalizado_com_outliers():
    cenario = interativo.cenario_personalizado("lognormal", 1.6, 30, p_contaminacao=0.05, fator=20)
    assert cenario["contaminacao"] == {"p": 0.05, "fator": 20.0}


@pytest.mark.parametrize("argumentos", [("weibull", 1.0, 30), ("normal", 1.0, 2), ("normal", 1.0, 500)])
def test_cenario_personalizado_invalido(argumentos):
    with pytest.raises(ValueError):
        interativo.cenario_personalizado(*argumentos)


def test_grade_de_efeitos():
    assert interativo.grade_de_efeitos(2.0, 6) == [0.0, 0.4, 0.8, 1.2, 1.6, 2.0]
    with pytest.raises(ValueError):
        interativo.grade_de_efeitos(2.0, 1)
    with pytest.raises(ValueError):
        interativo.grade_de_efeitos(0, 5)


def test_simulacao_ao_vivo_reproduz_o_csv_versionado(dados):
    """Mesmo cenário, semente, repetições e índice: as rejeições são as do resultados.csv (C4, o mais rápido)."""
    c4 = dados["cenarios"]["C4"]
    simulado = interativo.simular_cenario(c4, c4["efeitos"], 10_000, dados["cfg"]["semente"],
                                          interativo.indice_do_cenario(dados["cfg"], "C4"))
    referencia = dados["resultados"][dados["resultados"]["cenario"] == "C4"]
    assert list(simulado.columns) == list(referencia.columns)
    assert interativo.iguais_ao_csv(simulado, referencia)


def test_simulacao_com_outra_semente_difere_do_csv(dados):
    c4 = dados["cenarios"]["C4"]
    simulado = interativo.simular_cenario(c4, c4["efeitos"], 10_000, 7, 4)
    assert not interativo.iguais_ao_csv(simulado, dados["resultados"][dados["resultados"]["cenario"] == "C4"])


def test_simulacao_personalizada_tem_uma_linha_por_efeito_alfa_e_teste():
    cenario = interativo.cenario_personalizado("normal", 1.0, 20)
    tabela = interativo.simular_cenario(cenario, [0.0, 0.5, 1.0], 500, 1)
    assert len(tabela) == 3 * 2 * 2
    assert set(tabela["cenario"]) == {interativo.ID_PERSONALIZADO}
    assert tabela["taxa"].between(0, 1).all()
    poder = tabela[(tabela["alfa"] == 0.05) & (tabela["delta"] == 1.0)]["taxa"]
    assert (poder > 0.5).all()   # n = 20 e δ = 1 dp: os dois testes detectam o efeito na maioria das vezes


def test_simulacao_com_n_pequeno_usa_o_metodo_exato():
    """n ≤ 8 cai no caminho do Mann-Whitney exato do motor e ainda assim roda."""
    tabela = interativo.simular_cenario(interativo.cenario_personalizado("lognormal", 1.0, 5), [0.0, 1.0], 200, 3)
    assert len(tabela) == 8


def test_resumo_simulacao(dados):
    res = dados["resultados"][dados["resultados"]["cenario"] == "C1"]
    resumo = interativo.resumo_simulacao(res, 0.05)
    assert resumo["welch"]["classificacao"] == "conservador"
    assert resumo["mann_whitney"]["classificacao"] == "ok"
    assert resumo["mann_whitney"]["poder_maximo"] > resumo["welch"]["poder_maximo"]


def test_amostras_simuladas_reproduzem_o_exemplo_do_relatorio(dados):
    cenario, delta = gerador.cenario_calibrado(dados["calibracao"])
    exemplo = gerador.exemplo_simulado(cenario, delta, gerador.N_EXEMPLO, gerador.SEMENTE_COM_EFEITO)
    a, b = interativo.amostras_simuladas(dados["calibracao"], delta, gerador.N_EXEMPLO, gerador.SEMENTE_COM_EFEITO)
    np.testing.assert_array_equal(a, exemplo["a"])
    np.testing.assert_array_equal(b, exemplo["b"])


def test_delta_exato():
    assert interativo.delta_exato(0.35, 0.3517) == 0.3517
    assert interativo.delta_exato(0.40, 0.3517) == 0.40


@pytest.mark.parametrize("delta, palavra", [(0.0, "H₀ é verdadeira"), (5.0, "detectou o efeito")])
def test_resumo_e_leitura_do_exemplo(delta, palavra):
    cenario = interativo.cenario_personalizado("normal", 1.0, 30)
    exemplo = gerador.exemplo_simulado(cenario, delta, 30, 11)
    tabela = interativo.resumo_exemplo(exemplo, 0.05)
    assert list(tabela["Teste"]) == ["Welch", "Mann-Whitney"]
    decisao = tabela.columns[-1]
    for p, d in zip((exemplo["resultado"]["welch_p"], exemplo["resultado"]["mw_p"]), tabela[decisao]):
        assert d == ("rejeita H₀" if p < 0.05 else "não rejeita H₀")
    assert palavra in interativo.leitura_exemplo(exemplo, 0.05)


def test_leitura_aponta_erro_tipo_ii():
    exemplo = {"delta": 0.3, "resultado": {"welch_p": 0.4, "mw_p": 0.01}}
    leitura = interativo.leitura_exemplo(exemplo, 0.05)
    assert "Welch: não rejeita H₀, erro tipo II" in leitura
    assert "Mann-Whitney: rejeita H₀, decisão certa" in leitura


def test_leitura_aponta_erro_tipo_i():
    leitura = interativo.leitura_exemplo({"delta": 0.0, "resultado": {"welch_p": 0.01, "mw_p": float("nan")}}, 0.05)
    assert "Welch: rejeita H₀, erro tipo I" in leitura
    assert "Mann-Whitney: não rejeita H₀, decisão certa" in leitura


@pytest.mark.parametrize("alfa", [0.05, 0.01])
def test_tabelas_de_classificacao_e_poder(dados, alfa):
    clas = interativo.tabela_classificacao(dados["resultados"], alfa)
    assert len(clas) == 10
    assert set(clas["Classificação"]) <= {"ok", "conservador", "liberal"}
    poder = interativo.tabela_poder(dados["resultados"], alfa)
    assert len(poder) == 5 * 5
    assert poder["Efeito"].iloc[0].endswith("dp")        # C0 em desvios-padrão
    assert "×" in poder["Efeito"].iloc[-1]                # demais na razão de medianas


def test_classificacao_bate_com_o_csv_versionado(dados):
    clas = interativo.tabela_classificacao(dados["resultados"], 0.05)
    versionado = pd.read_csv(PASTA / "dados/simulacao/classificacao.csv")
    versionado = versionado[versionado["alfa"] == 0.05]
    assert list(clas["Classificação"]) == list(versionado["classificacao"])


def test_figura_dados_reais(dados):
    figura = interativo.figura_dados_reais(dados["reais"])
    assert len(figura.data) == 2
    assert figura.layout.yaxis.type == "log"
    assert sum(len(t.y) for t in figura.data) == len(dados["reais"])


def test_medianas():
    assert interativo.medianas([1, 2, 3], [2, 4, 6]) == {"a": 2.0, "b": 4.0, "razao": 2.0}
    assert np.isnan(interativo.medianas([0, 0, 0], [1, 2, 3])["razao"])


@pytest.mark.parametrize("alfa, critico", [(0.05, "1,96"), (0.01, "2,58")])
def test_g2_aceita_outro_alfa(alfa, critico):
    cenario = interativo.cenario_personalizado("normal", 1.0, 30)
    figura = graficos.g2(gerador.exemplo_simulado(cenario, 0.0, 30, 5), alfa)
    regioes = [t for t in figura.data if t.name and t.name.startswith("Região de rejeição")]
    assert regioes and all(graficos._num(alfa, 2) in t.name for t in regioes)
    assert any(t.text == f"|z| ≥ {critico}" for t in regioes)


def test_cenarios_do_config_sao_copias(dados):
    cenarios = interativo.cenarios_do_config(config.carregar())
    cenarios["C0"]["n"] = 999
    assert interativo.cenarios_do_config(config.carregar())["C0"]["n"] == 30
