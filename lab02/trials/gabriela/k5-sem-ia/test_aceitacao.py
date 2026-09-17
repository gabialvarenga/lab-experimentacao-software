from solucao import mesclar_leituras


def leitura(ts, valor, precisao):
    return {"ts": ts, "valor": valor, "precisao": precisao}


def test_duas_listas_vazias():
    assert mesclar_leituras([], []) == []


def test_apenas_uma_lista_sai_ordenada():
    a = [leitura(3, 1.0, 1), leitura(1, 2.0, 1)]
    assert [r["ts"] for r in mesclar_leituras(a, [])] == [1, 3]


def test_intercala_as_duas_listas_por_ts():
    a = [leitura(1, 1.0, 1), leitura(3, 3.0, 1)]
    b = [leitura(2, 2.0, 1), leitura(4, 4.0, 1)]
    assert [r["ts"] for r in mesclar_leituras(a, b)] == [1, 2, 3, 4]


def test_maior_precisao_vence_quando_esta_em_b():
    a = [leitura(1, 1.0, 2)]
    b = [leitura(1, 9.0, 5)]
    assert mesclar_leituras(a, b) == [leitura(1, 9.0, 5)]


def test_maior_precisao_vence_quando_esta_em_a():
    a = [leitura(1, 1.0, 8)]
    b = [leitura(1, 9.0, 5)]
    assert mesclar_leituras(a, b) == [leitura(1, 1.0, 8)]


def test_empate_de_precisao_prevalece_a_lista_a():
    a = [leitura(1, 1.0, 4)]
    b = [leitura(1, 9.0, 4)]
    assert mesclar_leituras(a, b) == [leitura(1, 1.0, 4)]


def test_duplicata_dentro_da_propria_lista():
    a = [leitura(1, 1.0, 2), leitura(1, 7.0, 6)]
    assert mesclar_leituras(a, []) == [leitura(1, 7.0, 6)]


def test_empate_dentro_da_propria_lista_mantem_a_primeira():
    a = [leitura(1, 1.0, 3), leitura(1, 7.0, 3)]
    assert mesclar_leituras(a, []) == [leitura(1, 1.0, 3)]


def test_descarta_leituras_com_valor_none():
    a = [leitura(1, None, 9), leitura(2, 2.0, 1)]
    assert mesclar_leituras(a, []) == [leitura(2, 2.0, 1)]


def test_nao_modifica_as_listas_de_entrada():
    a = [leitura(2, 1.0, 1)]
    b = [leitura(1, 2.0, 1)]
    copia_a = [dict(r) for r in a]
    copia_b = [dict(r) for r in b]
    resultado = mesclar_leituras(a, b)
    assert a == copia_a and b == copia_b
    assert all(r is not orig for r in resultado for orig in a + b)
