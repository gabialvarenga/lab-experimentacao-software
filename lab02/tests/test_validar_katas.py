"""Testes das funções puras do validador de katas (issue #61)."""

from validar_katas import (
    ARQUIVOS_KATA,
    arquivos_faltando,
    contar_testes,
    listar_katas,
)


def _criar_kata(raiz, nome, arquivos=ARQUIVOS_KATA):
    pasta = raiz / nome
    pasta.mkdir()
    for arq in arquivos:
        (pasta / arq).write_text("x\n", encoding="utf-8")
    return pasta


# --- listar_katas -------------------------------------------------------

def test_listar_katas_devolve_ids_ordenados(tmp_path):
    _criar_kata(tmp_path, "k2")
    _criar_kata(tmp_path, "k1")
    assert listar_katas(tmp_path) == ["k1", "k2"]


def test_listar_katas_ignora_pasta_sem_suite_de_aceitacao(tmp_path):
    _criar_kata(tmp_path, "k1")
    _criar_kata(tmp_path, "rascunho", arquivos=["enunciado.md"])
    assert listar_katas(tmp_path) == ["k1"]


def test_listar_katas_respeita_a_lista_de_ignorados(tmp_path):
    _criar_kata(tmp_path, "k1")
    _criar_kata(tmp_path, "exemplo")
    assert listar_katas(tmp_path, ignorar={"exemplo"}) == ["k1"]


# --- arquivos_faltando ------------------------------------------------

def test_arquivos_faltando_vazio_quando_kata_completa(tmp_path):
    pasta = _criar_kata(tmp_path, "k1")
    assert arquivos_faltando(pasta) == []


def test_arquivos_faltando_lista_o_que_falta(tmp_path):
    pasta = _criar_kata(tmp_path, "k1", arquivos=["test_aceitacao.py"])
    assert arquivos_faltando(pasta) == ["enunciado.md", "solucao_starter.py"]


# --- contar_testes --------------------------------------------------

def test_contar_testes_conta_apenas_funcoes_de_teste():
    fonte = (
        "def ajuda(x):\n    return x\n\n"
        "def test_um():\n    pass\n\n"
        "def test_dois():\n    pass\n"
    )
    assert contar_testes(fonte) == 2


def test_contar_testes_sem_nenhum_teste():
    assert contar_testes("def ajuda():\n    pass\n") == 0


def test_contar_testes_ignora_a_palavra_test_no_meio_da_linha():
    assert contar_testes("x = 'def test_falso'\ndef test_real():\n    pass\n") == 1
