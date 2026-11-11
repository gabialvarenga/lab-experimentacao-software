import numpy as np
import pytest

from lab04 import config


def test_carrega_semente_do_config_padrao():
    assert config.carregar()["semente"] == 42


def test_config_sem_semente_levanta_erro(tmp_path):
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text("outra_chave: 1\n", encoding="utf-8")
    with pytest.raises(ValueError, match="semente"):
        config.carregar(arquivo)


def test_criar_rng_e_reprodutivel():
    a = config.criar_rng({"semente": 42}).random(5)
    b = config.criar_rng({"semente": 42}).random(5)
    assert np.array_equal(a, b)
    assert not np.array_equal(a, config.criar_rng({"semente": 43}).random(5))


def test_carregar_informa_a_pasta_do_config():
    assert config.carregar()["pasta"] == str(config.CONFIG_PADRAO.parent)


def test_config_padrao_tem_a_secao_de_coleta():
    c = config.carregar()["coleta"]
    assert c["repositorio"] == "supabase/supabase" and c["por_mes"] == 10 and c["pausa_busca_s"] >= 20


def test_token_vem_da_variavel_de_ambiente(monkeypatch):
    monkeypatch.setenv("GITHUB_TOKEN", "  abc ")
    assert config.token() == "abc"
    monkeypatch.setenv("GITHUB_TOKEN", " ")
    with pytest.raises(ValueError, match="GITHUB_TOKEN"):
        config.token()


# --- seção `simulacao` (S02-01) ---


def _simulacao_minima():
    cenario = {"id": "X", "familia": "normal", "mu": 0.0, "sigma": 1.0, "n": 30, "unidade_efeito": "dp"}
    return {
        "semente": 42,
        "simulacao": {
            "repeticoes": 10,
            "repeticoes_piloto": 5,
            "alfas": [0.05, 0.01],
            "confianca_ic": 0.95,
            "piloto": "p.csv",
            "saida": "s.csv",
            "cenarios": [{**cenario, "efeitos": [0.0, 0.1, 0.2, 0.3, 0.4]}],
        },
    }


def test_simulacao_aceita_a_configuracao_minima():
    assert config.simulacao(_simulacao_minima())["cenarios"][0]["id"] == "X"


def test_simulacao_sem_a_secao_levanta_erro():
    with pytest.raises(ValueError, match="simulacao"):
        config.simulacao({"semente": 42})


@pytest.mark.parametrize("chave", config.CHAVES_DA_SIMULACAO)
def test_simulacao_exige_cada_chave(chave):
    cfg = _simulacao_minima()
    del cfg["simulacao"][chave]
    with pytest.raises(ValueError, match=chave):
        config.simulacao(cfg)


@pytest.mark.parametrize("chave", config.CHAVES_DO_CENARIO)
def test_simulacao_exige_cada_chave_do_cenario(chave):
    cfg = _simulacao_minima()
    del cfg["simulacao"]["cenarios"][0][chave]
    with pytest.raises(ValueError, match=chave):
        config.simulacao(cfg)


@pytest.mark.parametrize(
    "efeitos, trecho",
    [
        ([0.0, 0.1, 0.2, 0.3], "ao menos 5"),
        ([0.1, 0.2, 0.3, 0.4, 0.5], "começar em 0"),
        ([0.0, 0.2, 0.2, 0.3, 0.4], "crescente"),
        ([0.0, 0.3, 0.2, 0.4, 0.5], "crescente"),
    ],
)
def test_simulacao_valida_a_grade_de_efeitos(efeitos, trecho):
    cfg = _simulacao_minima()
    cfg["simulacao"]["cenarios"][0]["efeitos"] = efeitos
    with pytest.raises(ValueError, match=trecho):
        config.simulacao(cfg)


@pytest.mark.parametrize(
    "chave, valor",
    [("repeticoes", 0), ("repeticoes_piloto", True), ("alfas", [0.05, 1.5]), ("alfas", []), ("confianca_ic", 1.0)],
)
def test_simulacao_valida_repeticoes_alfas_e_confianca(chave, valor):
    cfg = _simulacao_minima()
    cfg["simulacao"][chave] = valor
    with pytest.raises(ValueError, match=chave):
        config.simulacao(cfg)


def test_simulacao_exige_ids_unicos():
    cfg = _simulacao_minima()
    cfg["simulacao"]["cenarios"].append(dict(cfg["simulacao"]["cenarios"][0]))
    with pytest.raises(ValueError, match="únicos"):
        config.simulacao(cfg)
