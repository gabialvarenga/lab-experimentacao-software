from solucao import ranking_trilhas


def trilha(nome, distancia_km=1.0, desnivel_m=0, nota=3.0):
    return {
        "nome": nome,
        "distancia_km": distancia_km,
        "desnivel_m": desnivel_m,
        "nota": nota,
    }


def test_lista_vazia():
    assert ranking_trilhas([], {"distancia": 1}) == []


def test_ordena_da_maior_para_a_menor_pontuacao():
    dados = [trilha("Curta", distancia_km=5.0), trilha("Longa", distancia_km=10.0)]
    assert ranking_trilhas(dados, {"distancia": 1}) == ["Longa", "Curta"]


def test_empate_resolve_por_ordem_alfabetica():
    dados = [trilha("Zeta", distancia_km=5.0), trilha("Alfa", distancia_km=5.0)]
    assert ranking_trilhas(dados, {"distancia": 1}) == ["Alfa", "Zeta"]


def test_descarta_nota_acima_de_cinco():
    dados = [trilha("Boa", nota=5.0), trilha("Invalida", nota=5.1)]
    assert ranking_trilhas(dados, {"nota": 1}) == ["Boa"]


def test_descarta_nota_negativa():
    dados = [trilha("Boa", nota=0.0), trilha("Invalida", nota=-0.1)]
    assert ranking_trilhas(dados, {"nota": 1}) == ["Boa"]


def test_descarta_distancia_zero_ou_negativa():
    dados = [trilha("Ok", distancia_km=1.0), trilha("Zero", distancia_km=0.0)]
    assert ranking_trilhas(dados, {"distancia": 1}) == ["Ok"]


def test_peso_ausente_vale_zero():
    dados = [trilha("Beta", distancia_km=9.0), trilha("Alfa", distancia_km=1.0)]
    assert ranking_trilhas(dados, {}) == ["Alfa", "Beta"]


def test_combina_os_tres_pesos():
    dados = [
        trilha("T1", distancia_km=5.0, desnivel_m=200, nota=4.0),
        trilha("T2", distancia_km=8.0, desnivel_m=100, nota=3.0),
        trilha("T3", distancia_km=3.0, desnivel_m=500, nota=5.0),
    ]
    pesos = {"distancia": 2, "desnivel": 0.01, "nota": 10}
    assert ranking_trilhas(dados, pesos) == ["T3", "T1", "T2"]


def test_limite_corta_o_resultado():
    dados = [
        trilha("A", distancia_km=3.0),
        trilha("B", distancia_km=2.0),
        trilha("C", distancia_km=1.0),
    ]
    assert ranking_trilhas(dados, {"distancia": 1}, limite=2) == ["A", "B"]


def test_limite_maior_que_a_lista_devolve_tudo():
    dados = [trilha("A", distancia_km=3.0)]
    assert ranking_trilhas(dados, {"distancia": 1}, limite=10) == ["A"]
