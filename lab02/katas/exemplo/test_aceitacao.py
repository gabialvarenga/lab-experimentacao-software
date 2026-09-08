from solucao import soma_pares


def test_lista_vazia():
    assert soma_pares([]) == 0


def test_apenas_impares():
    assert soma_pares([1, 3, 5, 7]) == 0


def test_mistura_de_pares_e_impares():
    assert soma_pares([1, 2, 3, 4, 5, 6]) == 12


def test_inclui_negativos_pares():
    assert soma_pares([-2, -3, -4, 5]) == -6
