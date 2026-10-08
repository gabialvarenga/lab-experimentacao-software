import pytest

from metricas.cfr import cfr_ci


def runs(*conclusoes):
    return [{"id": i, "workflow_id": 1, "conclusion": c} for i, c in enumerate(conclusoes)]


def test_cfr_e_falhas_sobre_falhas_mais_sucessos():
    assert cfr_ci(runs("success", "success", "success", "failure")) == pytest.approx(0.25)


@pytest.mark.parametrize("falha", ["failure", "timed_out", "startup_failure"])
def test_os_tres_tipos_de_falha_contam(falha):
    assert cfr_ci(runs("success", falha)) == 0.5


def test_runs_ignorados_nao_entram_na_conta():
    ignorados = ["cancelled", "skipped", "neutral", "action_required", "stale", None, ""]

    assert cfr_ci(runs("success", "failure", *ignorados)) == 0.5


def test_repositorio_sem_falhas_tem_cfr_zero():
    assert cfr_ci(runs("success", "success")) == 0.0


def test_so_falhas_da_cfr_um():
    assert cfr_ci(runs("failure", "timed_out")) == 1.0


def test_sem_runs_ou_so_ignorados_o_cfr_e_indefinido():
    assert cfr_ci([]) is None
    assert cfr_ci(runs("cancelled", "skipped", None)) is None


def test_todos_os_workflows_entram_juntos():
    mistos = [
        {"workflow_id": 1, "conclusion": "success"},
        {"workflow_id": 1, "conclusion": "success"},
        {"workflow_id": 2, "conclusion": "failure"},
        {"workflow_id": 3, "conclusion": "success"},
    ]

    assert cfr_ci(mistos) == pytest.approx(0.25)


def test_run_sem_a_chave_conclusion_e_ignorado():
    assert cfr_ci([{"id": 1}, {"id": 2, "conclusion": "success"}]) == 0.0
