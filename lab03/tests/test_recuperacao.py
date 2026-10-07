from datetime import datetime, timedelta, timezone

import pytest

from metricas.recuperacao import tempo_recuperacao

BASE = datetime(2026, 3, 10, 9, 0, tzinfo=timezone.utc)


def run(id, conclusion, inicio_min, fim_min=None, workflow_id=1):
    """Run que começa `inicio_min` minutos após BASE e termina `fim_min` (padrão: 5 min depois)."""
    fim_min = inicio_min + 5 if fim_min is None else fim_min
    return {
        "id": id,
        "workflow_id": workflow_id,
        "conclusion": conclusion,
        "run_started_at": BASE + timedelta(minutes=inicio_min),
        "updated_at": BASE + timedelta(minutes=fim_min),
    }


@pytest.fixture
def carregar(fixture_json):
    def _carregar(nome):
        return [
            {**item, "run_started_at": datetime.fromisoformat(item["run_started_at"]), "updated_at": datetime.fromisoformat(item["updated_at"])}
            for item in fixture_json("recuperacao")[nome]
        ]

    return _carregar


def contagens(resultado):
    return (resultado["n_episodios"], resultado["n_censurados_direita"], resultado["n_censurados_esquerda"])


def test_exemplo_da_rq04_resulta_em_1h20(carregar):
    resultado = tempo_recuperacao(carregar("exemplo_rq04"))

    assert resultado["mediana_horas"] == pytest.approx(80 / 60)
    assert contagens(resultado) == (1, 0, 0)


def test_falhas_consecutivas_sao_um_so_episodio_medido_desde_a_primeira():
    runs = [run(1, "success", 0), run(2, "failure", 60), run(3, "failure", 90), run(4, "failure", 120), run(5, "success", 180)]

    resultado = tempo_recuperacao(runs)

    assert resultado["mediana_horas"] == pytest.approx((185 - 60) / 60)  # sucesso terminou 5 min após o início
    assert contagens(resultado) == (1, 0, 0)


def test_repositorio_sem_nenhuma_falha_tem_mediana_indefinida():
    resultado = tempo_recuperacao([run(1, "success", 0), run(2, "success", 60)])

    assert resultado["mediana_horas"] is None
    assert contagens(resultado) == (0, 0, 0)


def test_sem_runs_o_resultado_e_vazio():
    assert tempo_recuperacao([]) == {
        "mediana_horas": None,
        "n_episodios": 0,
        "n_censurados_direita": 0,
        "n_censurados_esquerda": 0,
    }


def test_falha_nunca_recuperada_e_censurada_a_direita():
    resultado = tempo_recuperacao([run(1, "success", 0), run(2, "failure", 60), run(3, "failure", 120)])

    assert resultado["mediana_horas"] is None
    assert contagens(resultado) == (1, 1, 0)


def test_censurado_a_direita_nao_entra_na_mediana_mas_conta_nos_episodios():
    runs = [
        run(1, "success", 0),
        run(2, "failure", 60),
        run(3, "success", 120, 180),  # episódio completo: 180 − 60 = 2 h
        run(4, "failure", 240),  # sem sucesso depois
    ]

    resultado = tempo_recuperacao(runs)

    assert resultado["mediana_horas"] == pytest.approx(2.0)
    assert contagens(resultado) == (2, 1, 0)


def test_falha_no_inicio_da_janela_e_censurada_a_esquerda_e_fora_da_mediana():
    runs = [run(1, "failure", 0), run(2, "success", 60, 70), run(3, "failure", 120), run(4, "success", 150, 180)]

    resultado = tempo_recuperacao(runs)

    assert resultado["mediana_horas"] == pytest.approx(1.0)  # só o segundo episódio: 180 − 120 min
    assert contagens(resultado) == (2, 0, 1)


def test_censura_a_esquerda_vale_mesmo_sem_recuperacao_e_conta_uma_vez():
    resultado = tempo_recuperacao([run(1, "failure", 0), run(2, "failure", 60)])

    assert resultado["mediana_horas"] is None
    assert contagens(resultado) == (1, 0, 1)


def test_execucoes_ignoradas_nao_abrem_nem_encerram_episodios():
    runs = [
        run(1, "success", 0),
        run(2, "cancelled", 30),
        run(3, "failure", 60),
        run(4, "cancelled", 90),
        run(5, "skipped", 100),
        run(6, "success", 120, 130),
    ]

    resultado = tempo_recuperacao(runs)

    assert resultado["mediana_horas"] == pytest.approx(70 / 60)
    assert contagens(resultado) == (1, 0, 0)


def test_run_ignorado_no_inicio_nao_impede_a_censura_a_esquerda():
    resultado = tempo_recuperacao([run(1, "cancelled", 0), run(2, "failure", 30), run(3, "success", 60)])

    assert contagens(resultado) == (1, 0, 1)


def test_so_runs_ignorados_nao_geram_episodios():
    assert contagens(tempo_recuperacao([run(1, "cancelled", 0), run(2, None, 30)])) == (0, 0, 0)


def test_dois_workflows_intercalados_sao_calculados_separadamente(carregar):
    resultado = tempo_recuperacao(carregar("dois_workflows_intercalados"))

    # workflow 1: falha 09:00 → sucesso termina 13:05 = 4h05; workflow 2: falha 09:30 → sucesso termina 10:30 = 1h
    assert resultado["mediana_horas"] == pytest.approx((4 + 5 / 60 + 1) / 2)
    assert contagens(resultado) == (2, 0, 0)


def test_um_sucesso_de_outro_workflow_nao_encerra_o_episodio():
    runs = [
        run(1, "success", 0, workflow_id=1),
        run(2, "failure", 60, workflow_id=1),
        run(3, "success", 90, workflow_id=2),  # outro workflow
    ]

    resultado = tempo_recuperacao(runs)

    assert resultado["mediana_horas"] is None
    assert contagens(resultado) == (1, 1, 0)


def test_cada_workflow_tem_a_sua_propria_censura_a_esquerda():
    runs = [
        run(1, "failure", 0, workflow_id=1),
        run(2, "success", 10, workflow_id=2),
        run(3, "failure", 20, workflow_id=2),
    ]

    assert contagens(tempo_recuperacao(runs)) == (2, 1, 1)


def test_mediana_de_varios_episodios_completos_usa_a_mediana_e_nao_a_media():
    runs = []
    id = 0
    for duracao in (60, 120, 6000):  # 1 h, 2 h e 100 h
        inicio = id * 10000
        runs += [run(id + 1, "success", inicio), run(id + 2, "failure", inicio + 60), run(id + 3, "success", inicio + 60 + duracao - 5)]
        id += 3

    assert tempo_recuperacao(runs)["mediana_horas"] == pytest.approx(2.0)


def test_runs_fora_de_ordem_sao_ordenados_por_run_started_at():
    runs = [run(3, "success", 120, 130), run(1, "success", 0), run(2, "failure", 60)]

    resultado = tempo_recuperacao(runs)

    assert resultado["mediana_horas"] == pytest.approx(70 / 60)
    assert contagens(resultado) == (1, 0, 0)


def test_a_entrada_nao_e_alterada():
    runs = [run(2, "failure", 60), run(1, "success", 0)]
    copia = list(runs)

    tempo_recuperacao(runs)

    assert runs == copia
