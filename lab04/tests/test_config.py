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
