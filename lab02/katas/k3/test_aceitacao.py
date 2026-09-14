import pytest

from solucao import montar_escala


def pessoa(nome, indisponivel=None):
    if indisponivel is None:
        return {"nome": nome}
    return {"nome": nome, "indisponivel": indisponivel}


def test_sem_dias_todos_ficam_com_lista_vazia():
    assert montar_escala([pessoa("Ana"), pessoa("Bia")], []) == {"Ana": [], "Bia": []}


def test_um_dia_uma_pessoa():
    assert montar_escala([pessoa("Ana")], ["seg"]) == {"Ana": ["seg"]}


def test_alterna_entre_duas_pessoas_equilibrando_a_carga():
    equipe = [pessoa("Ana"), pessoa("Bia")]
    assert montar_escala(equipe, ["seg", "ter", "qua", "qui"]) == {
        "Ana": ["seg", "qua"],
        "Bia": ["ter", "qui"],
    }


def test_respeita_a_indisponibilidade():
    equipe = [pessoa("Ana", ["seg"]), pessoa("Bia")]
    assert montar_escala(equipe, ["seg"]) == {"Ana": [], "Bia": ["seg"]}


def test_empate_de_carga_resolve_por_ordem_alfabetica():
    equipe = [pessoa("Zeca"), pessoa("Ana")]
    assert montar_escala(equipe, ["seg"]) == {"Ana": ["seg"], "Zeca": []}


def test_quem_esta_sempre_indisponivel_fica_sem_plantao():
    equipe = [pessoa("Ana", ["seg", "ter"]), pessoa("Bia")]
    assert montar_escala(equipe, ["seg", "ter"]) == {"Ana": [], "Bia": ["seg", "ter"]}


def test_menor_carga_tem_prioridade_sobre_o_alfabeto():
    equipe = [pessoa("Ana"), pessoa("Bia", ["seg"])]
    assert montar_escala(equipe, ["seg", "ter"]) == {"Ana": ["seg"], "Bia": ["ter"]}


def test_sem_ninguem_disponivel_levanta_erro():
    equipe = [pessoa("Ana", ["seg"]), pessoa("Bia", ["seg"])]
    with pytest.raises(ValueError, match="sem cobertura para seg"):
        montar_escala(equipe, ["seg"])


def test_todas_as_pessoas_aparecem_no_resultado():
    equipe = [pessoa("Ana"), pessoa("Bia"), pessoa("Caio")]
    assert set(montar_escala(equipe, ["seg"])) == {"Ana", "Bia", "Caio"}


def test_dias_ficam_na_ordem_em_que_foram_atribuidos():
    equipe = [pessoa("Ana")]
    assert montar_escala(equipe, ["qui", "seg", "ter"]) == {"Ana": ["qui", "seg", "ter"]}
