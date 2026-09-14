import pytest

from solucao import consumo_bateria


def test_lista_vazia_devolve_a_carga_inicial():
    assert consumo_bateria([], 73.5) == 73.5


def test_leitura_gasta_002_por_segundo():
    assert consumo_bateria([{"tipo": "leitura", "duracao_s": 100}], 100.0) == 98.0


def test_transmissao_gasta_015_por_segundo():
    assert consumo_bateria([{"tipo": "transmissao", "duracao_s": 100}], 50.0) == 35.0


def test_espera_gasta_0001_por_segundo():
    assert consumo_bateria([{"tipo": "espera", "duracao_s": 1000}], 80.0) == 79.0


def test_recarga_repoe_005_por_segundo():
    assert consumo_bateria([{"tipo": "recarga", "duracao_s": 100}], 50.0) == 55.0


def test_carga_nao_passa_de_100():
    assert consumo_bateria([{"tipo": "recarga", "duracao_s": 1000}], 98.0) == 100.0


def test_carga_nao_fica_negativa():
    assert consumo_bateria([{"tipo": "transmissao", "duracao_s": 1000}], 5.0) == 0.0


def test_sequencia_de_eventos_na_ordem():
    eventos = [
        {"tipo": "leitura", "duracao_s": 60},
        {"tipo": "transmissao", "duracao_s": 20},
        {"tipo": "espera", "duracao_s": 3600},
        {"tipo": "recarga", "duracao_s": 40},
    ]
    assert consumo_bateria(eventos, 100.0) == 94.2


def test_tipo_desconhecido_levanta_erro():
    with pytest.raises(ValueError, match="tipo desconhecido: reboot"):
        consumo_bateria([{"tipo": "reboot", "duracao_s": 10}], 100.0)


def test_duracao_negativa_levanta_erro():
    with pytest.raises(ValueError, match="duração negativa"):
        consumo_bateria([{"tipo": "leitura", "duracao_s": -5}], 100.0)
