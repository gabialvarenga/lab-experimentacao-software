from solucao import validar_lote


def test_codigo_valido_nao_tem_erros():
    assert validar_lote("ABC-1234-K") == []


def test_prefixo_minusculo():
    assert validar_lote("abc-1234-K") == ["PREFIXO"]


def test_prefixo_parcialmente_maiusculo():
    assert validar_lote("AbC-1234-K") == ["PREFIXO"]


def test_digitos_todos_iguais():
    assert validar_lote("ABC-1111-E") == ["SEQUENCIA"]


def test_verificador_errado():
    assert validar_lote("ABC-1234-Z") == ["DIGITO"]


def test_soma_maior_que_26_da_a_volta_no_alfabeto():
    assert validar_lote("ABC-9999-K") == ["SEQUENCIA"]


def test_erros_saem_na_ordem_definida():
    assert validar_lote("abc-9999-J") == ["PREFIXO", "SEQUENCIA", "DIGITO"]


def test_formato_curto_demais():
    assert validar_lote("AB-1234-K") == ["FORMATO"]


def test_formato_com_numero_errado_de_digitos():
    assert validar_lote("ABC-123-K") == ["FORMATO"]


def test_texto_vazio():
    assert validar_lote("") == ["FORMATO"]


def test_formato_sem_hifens():
    assert validar_lote("ABC1234K") == ["FORMATO"]
