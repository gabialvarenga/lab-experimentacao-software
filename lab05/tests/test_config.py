import pytest

from lab05 import config


def test_config_padrao_tem_a_semente_42():
    cfg = config.carregar()
    assert cfg["semente"] == 42


def test_carregar_acrescenta_a_pasta_do_arquivo(tmp_path):
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text("semente: 7\n", encoding="utf-8")
    cfg = config.carregar(arquivo)
    assert cfg["semente"] == 7
    assert cfg["pasta"] == str(tmp_path.resolve())


@pytest.mark.parametrize("texto", ["", "outra: 1\n"])
def test_carregar_sem_semente_levanta_erro(tmp_path, texto):
    arquivo = tmp_path / "config.yaml"
    arquivo.write_text(texto, encoding="utf-8")
    with pytest.raises(ValueError, match="semente"):
        config.carregar(arquivo)


def test_criar_rng_e_reprodutivel():
    cfg = {"semente": 42}
    assert config.criar_rng(cfg).random(5).tolist() == config.criar_rng(cfg).random(5).tolist()
