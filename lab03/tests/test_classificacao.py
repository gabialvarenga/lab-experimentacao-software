import pytest

from metricas.classificacao import (
    classificar,
    nota_cfr,
    nota_frequencia,
    nota_lead_time,
    nota_recuperacao,
)

SEMANAS = 365 / 7
UMA_POR_MES = 12 / SEMANAS

# Um valor de cada métrica para cada nota, usado para montar combinações de notas
FREQUENCIA = {4: 7, 3: 1, 2: 0.5, 1: 0.1}
LEAD_TIME = {4: 12, 3: 48, 2: 240, 1: 1000}
CFR = {4: 0.10, 3: 0.20, 2: 0.40, 1: 0.60}
RECUPERACAO = {4: 0.5, 3: 5, 2: 48, 1: 500}


def com_notas(frequencia, lead_time, cfr, recuperacao):
    return classificar(
        FREQUENCIA.get(frequencia),
        LEAD_TIME.get(lead_time),
        CFR.get(cfr),
        RECUPERACAO.get(recuperacao),
    )


@pytest.mark.parametrize(
    "freq_semana, nota",
    [
        (30, 4),
        (7, 4),
        (6.99, 3),
        (1, 3),
        (0.99, 2),
        (UMA_POR_MES, 2),
        (UMA_POR_MES - 0.001, 1),
        (0, 1),
        (None, None),
    ],
)
def test_cortes_da_frequencia(freq_semana, nota):
    assert nota_frequencia(freq_semana) == nota


def test_uma_por_mes_e_cerca_de_0_23_por_semana():
    assert round(UMA_POR_MES, 2) == 0.23
    assert nota_frequencia(0.23) == 1  # logo abaixo de 12 ÷ 52,14
    assert nota_frequencia(0.24) == 2


def test_corte_mensal_acompanha_as_semanas_da_janela():
    # Em uma janela de 24 semanas, "1 por mês" vale 0,5 por semana
    assert nota_frequencia(0.5, semanas_janela=24) == 2
    assert nota_frequencia(0.49, semanas_janela=24) == 1
    assert nota_frequencia(0.49) == 2


@pytest.mark.parametrize(
    "horas, nota",
    [
        (0, 4),
        (23.99, 4),
        (24, 3),
        (167.99, 3),
        (168, 2),
        (719.99, 2),
        (720, 1),
        (5000, 1),
        (None, None),
    ],
)
def test_cortes_do_lead_time(horas, nota):
    assert nota_lead_time(horas) == nota


@pytest.mark.parametrize(
    "cfr, nota",
    [
        (0, 4),
        (0.15, 4),
        (0.1501, 3),
        (0.30, 3),
        (0.3001, 2),
        (0.45, 2),
        (0.4501, 1),
        (1, 1),
        (None, None),
    ],
)
def test_cortes_do_cfr(cfr, nota):
    assert nota_cfr(cfr) == nota


@pytest.mark.parametrize(
    "horas, nota",
    [
        (0, 4),
        (0.99, 4),
        (1, 3),
        (23.99, 3),
        (24, 2),
        (167.99, 2),
        (168, 1),
        (2000, 1),
        (None, None),
    ],
)
def test_cortes_da_recuperacao(horas, nota):
    assert nota_recuperacao(horas) == nota


def test_notas_4_3_3_1_resultam_em_high():
    assert com_notas(4, 3, 3, 1) == ("High", 4)


def test_notas_4_3_2_1_resultam_em_medium():
    assert com_notas(4, 3, 2, 1) == ("Medium", 4)  # mediana 2,5 arredondada para baixo


@pytest.mark.parametrize(
    "notas, categoria",
    [
        ((4, 4, 4, 4), "Elite"),
        ((4, 4, 3, 3), "High"),  # mediana 3,5
        ((3, 3, 3, 3), "High"),
        ((2, 2, 1, 1), "Low"),  # mediana 1,5
        ((1, 1, 1, 1), "Low"),
    ],
)
def test_categoria_geral_com_as_quatro_metricas(notas, categoria):
    assert com_notas(*notas) == (categoria, 4)


def test_ordem_das_metricas_nao_muda_a_categoria():
    assert com_notas(1, 3, 3, 4) == com_notas(4, 3, 3, 1) == com_notas(3, 4, 1, 3)


@pytest.mark.parametrize(
    "notas, esperado",
    [
        ((4, 3, None, 1), ("High", 3)),  # mediana de 4, 3 e 1
        ((4, None, None, 1), ("Medium", 2)),  # mediana 2,5
        ((4, None, None, 3), ("High", 2)),  # mediana 3,5
        ((None, None, 2, None), ("Medium", 1)),
        ((None, None, None, None), (None, 0)),
    ],
)
def test_metrica_indefinida_nao_recebe_nota(notas, esperado):
    assert com_notas(*notas) == esperado


def test_classificar_repassa_as_semanas_da_janela():
    assert classificar(0.49, None, None, None) == ("Medium", 1)
    assert classificar(0.49, None, None, None, semanas_janela=24) == ("Low", 1)
