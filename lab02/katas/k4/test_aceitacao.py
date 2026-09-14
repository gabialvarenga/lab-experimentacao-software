import pytest

from solucao import calcular_tarifa


def test_ate_15_minutos_e_gratuito():
    assert calcular_tarifa("08:00", "08:15") == 0.0


def test_16_minutos_cobra_a_primeira_hora():
    assert calcular_tarifa("08:00", "08:16") == 5.0


def test_uma_hora_exata_cobra_so_a_primeira():
    assert calcular_tarifa("08:00", "09:00") == 5.0


def test_hora_iniciada_conta_como_hora_cheia():
    assert calcular_tarifa("08:00", "09:01") == 8.0


def test_tres_horas_somam_as_adicionais():
    assert calcular_tarifa("08:00", "11:00") == 11.0


def test_valor_e_limitado_ao_teto_diario():
    assert calcular_tarifa("08:00", "20:00") == 25.0


def test_atravessa_a_virada_de_hora():
    assert calcular_tarifa("23:00", "23:50") == 5.0


def test_saida_anterior_a_entrada_levanta_erro():
    with pytest.raises(ValueError, match="saída anterior à entrada"):
        calcular_tarifa("10:00", "09:00")


def test_saida_igual_a_entrada_levanta_erro():
    with pytest.raises(ValueError, match="saída anterior à entrada"):
        calcular_tarifa("10:00", "10:00")


def test_formato_invalido_levanta_erro():
    with pytest.raises(ValueError, match="horário inválido: 8h00"):
        calcular_tarifa("8h00", "09:00")


def test_hora_fora_da_faixa_levanta_erro():
    with pytest.raises(ValueError, match="horário inválido: 25:00"):
        calcular_tarifa("07:00", "25:00")
