from datetime import date, datetime

import pytest

from metricas.janela import dentro_da_janela, semanas

INICIO = date(2025, 10, 1)
FIM = date(2026, 9, 30)


def test_semanas_da_janela_completa():
    assert semanas(INICIO, FIM) == pytest.approx(365 / 7)
    assert round(semanas(INICIO, FIM), 1) == 52.1


def test_semanas_de_um_dia():
    assert semanas(INICIO, INICIO) == pytest.approx(1 / 7)


def test_semanas_fim_antes_do_inicio():
    with pytest.raises(ValueError):
        semanas(FIM, INICIO)


def test_dentro_da_janela_com_fixture(fixture_json):
    dados = fixture_json("janela")
    inicio = date.fromisoformat(dados["inicio"])
    fim = date.fromisoformat(dados["fim"])
    for texto in dados["dentro"]:
        assert dentro_da_janela(datetime.fromisoformat(texto), inicio, fim), texto
    for texto in dados["fora"]:
        assert not dentro_da_janela(datetime.fromisoformat(texto), inicio, fim), texto


def test_primeiro_e_ultimo_dia_da_janela():
    assert dentro_da_janela(datetime.fromisoformat("2025-10-01T00:00:00+00:00"), INICIO, FIM)
    assert dentro_da_janela(
        datetime.fromisoformat("2026-09-30T23:59:59.999999+00:00"), INICIO, FIM
    )


def test_data_naive_levanta_erro():
    with pytest.raises(ValueError):
        dentro_da_janela(datetime(2026, 1, 1), INICIO, FIM)


def test_janela_invertida_levanta_erro():
    with pytest.raises(ValueError):
        dentro_da_janela(datetime.fromisoformat("2026-01-01T00:00:00+00:00"), FIM, INICIO)
