import csv

import pytest

from cronometro import (
    COLUNAS,
    TIMEBOX_MIN_PADRAO,
    Contagem,
    anexar_linha,
    esta_verde,
    linha_existe,
    montar_linha,
    parse_junit,
    tempo_registrado,
    validar_entrada,
)


def test_parse_junit_soma_testsuites_aninhadas():
    xml = """<testsuites>
      <testsuite name="a" tests="3" failures="1" errors="0" skipped="0"/>
      <testsuite name="b" tests="2" failures="0" errors="1" skipped="0"/>
    </testsuites>"""
    c = parse_junit(xml)
    assert (c.total, c.falhando, c.erros, c.ignorados) == (5, 1, 1, 0)
    assert c.passando == 3


def test_parse_junit_aceita_testsuite_na_raiz():
    xml = '<testsuite name="a" tests="4" failures="0" errors="0" skipped="0"/>'
    c = parse_junit(xml)
    assert c.total == 4 and c.passando == 4



def test_esta_verde_quando_todos_passam():
    assert esta_verde(Contagem(total=5, passando=5, falhando=0, erros=0, ignorados=0))


def test_nao_esta_verde_com_falha():
    assert not esta_verde(Contagem(total=5, passando=4, falhando=1, erros=0, ignorados=0))


def test_nao_esta_verde_sem_nenhum_teste():
    assert not esta_verde(Contagem(total=0, passando=0, falhando=0, erros=0, ignorados=0))


def test_nao_esta_verde_com_teste_ignorado():
    assert not esta_verde(Contagem(total=5, passando=4, falhando=0, erros=0, ignorados=1))



def test_validar_entrada_sem_erros():
    assert validar_entrada("gabriela", "k1", "sem-ia", 1) == []


def test_validar_entrada_acumula_todos_os_erros():
    erros = validar_entrada("fulano", "k1", "com_ia", 0)
    assert len(erros) == 3
    assert any("integrante" in e for e in erros)
    assert any("tratamento" in e for e in erros)
    assert any("ordem" in e for e in erros)


def test_tempo_registrado_censurado_usa_o_timebox():
    assert tempo_registrado(1834.2, censurado=True, timebox_s=2100) == 2100


def test_tempo_registrado_verde_arredonda_o_decorrido():
    assert tempo_registrado(842.6, censurado=False, timebox_s=2100) == 843


def test_montar_linha_formata_censura_e_preenche_colunas():
    linha = montar_linha(
        integrante="carlos",
        kata="k3",
        tratamento="com-ia",
        ordem=4,
        data_inicio="2026-09-07T20:00:00",
        decorrido_s=999.0,
        censurado=True,
        contagem=Contagem(total=6, passando=2, falhando=4, erros=0, ignorados=0),
        prompts=7,
        observacoes="travou no parsing",
        timebox_s=2100,
    )
    assert list(linha.keys()) == COLUNAS
    assert linha["censurado"] == "true"
    assert linha["tempo_segundos"] == 2100
    assert linha["testes_total"] == 6
    assert linha["testes_passando"] == 2
    assert linha["prompts"] == 7


def _linha_exemplo(**over):
    base = dict(
        integrante="gabriela", kata="k1", tratamento="sem-ia", ordem=1,
        data_inicio="2026-09-07T20:00:00", decorrido_s=120.0, censurado=False,
        contagem=Contagem(total=3, passando=3, falhando=0, erros=0, ignorados=0),
        prompts=0, observacoes="", timebox_s=2100,
    )
    base.update(over)
    return montar_linha(**base)


def test_anexar_linha_escreve_cabecalho_uma_unica_vez(tmp_path):
    csv_path = tmp_path / "dados" / "trials.csv"
    anexar_linha(csv_path, _linha_exemplo())
    anexar_linha(csv_path, _linha_exemplo(kata="k2", ordem=2))

    linhas = list(csv.DictReader(csv_path.open(encoding="utf-8")))
    assert len(linhas) == 2
    assert csv_path.read_text(encoding="utf-8").count("integrante,kata") == 1


def test_linha_existe_detecta_trial_ja_gravado(tmp_path):
    csv_path = tmp_path / "trials.csv"
    assert linha_existe(csv_path, "gabriela", "k1", "sem-ia") is False
    anexar_linha(csv_path, _linha_exemplo())
    assert linha_existe(csv_path, "gabriela", "k1", "sem-ia") is True
    assert linha_existe(csv_path, "gabriela", "k1", "com-ia") is False


def test_timebox_padrao_e_35_min():
    assert TIMEBOX_MIN_PADRAO == 35
