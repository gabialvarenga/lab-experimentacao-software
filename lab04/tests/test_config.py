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
