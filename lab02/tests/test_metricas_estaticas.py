from metricas_estaticas import (
    COLUNAS,
    calcular_complexidade,
    extrair_duplicacao_pct,
    extrair_kata_e_tratamento,
    extrair_loc,
    extrair_mi,
    montar_linha_metricas,
)


def test_calcular_complexidade_media_e_maximo():
    blocos = [
        {"type": "function", "complexity": 1},
        {"type": "function", "complexity": 5},
        {"type": "method", "complexity": 3},
    ]
    media, maximo = calcular_complexidade(blocos)
    assert media == 3.0
    assert maximo == 5


def test_calcular_complexidade_exclui_bloco_de_classe():
    blocos = [
        {"type": "class", "complexity": 20},
        {"type": "method", "complexity": 2},
        {"type": "method", "complexity": 4},
    ]
    media, maximo = calcular_complexidade(blocos)
    assert media == 3.0
    assert maximo == 4


def test_calcular_complexidade_lista_vazia():
    assert calcular_complexidade([]) == (0.0, 0)


def test_extrair_kata_e_tratamento_kata_simples():
    assert extrair_kata_e_tratamento("k1-com-ia") == ("k1", "com-ia")
    assert extrair_kata_e_tratamento("k1-sem-ia") == ("k1", "sem-ia")


def test_extrair_kata_e_tratamento_kata_com_hifen_no_nome():
    assert extrair_kata_e_tratamento("kata-dois-sem-ia") == ("kata-dois", "sem-ia")


def test_extrair_kata_e_tratamento_sem_sufixo_reconhecido():
    import pytest

    with pytest.raises(ValueError):
        extrair_kata_e_tratamento("k1-desconhecido")


def test_extrair_loc():
    assert extrair_loc({"loc": 10, "sloc": 7, "comments": 1}) == 7


def test_extrair_mi():
    assert extrair_mi({"mi": 84.31, "rank": "A"}) == 84.31


def test_extrair_duplicacao_pct():
    saida = {"statistics": {"total": {"percentage": 12.5, "clones": 1}}}
    assert extrair_duplicacao_pct(saida) == 12.5


def test_montar_linha_metricas_ordem_e_arredondamento():
    linha = montar_linha_metricas(
        integrante="carlos",
        kata="k2",
        tratamento="com-ia",
        loc=42,
        cc_media=3.333333,
        cc_max=7,
        mi=91.6789,
        duplicacao_pct=0.0,
    )
    assert list(linha.keys()) == COLUNAS
    assert linha["cc_media"] == 3.33
    assert linha["mi"] == 91.68
    assert linha["loc"] == 42
    assert linha["cc_max"] == 7
