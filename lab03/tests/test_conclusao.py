import pytest

from metricas.conclusao import classificar_conclusao, runs_validos


@pytest.mark.parametrize(
    "conclusion, esperado",
    [
        ("success", "sucesso"),
        ("failure", "falha"),
        ("timed_out", "falha"),
        ("startup_failure", "falha"),
        ("cancelled", None),
        ("skipped", None),
        ("neutral", None),
        ("action_required", None),
        ("stale", None),
        (None, None),
        ("", None),
        ("valor_desconhecido", None),
    ],
)
def test_classificar_conclusao(conclusion, esperado):
    assert classificar_conclusao(conclusion) == esperado


def test_runs_validos_filtra_e_preserva_a_ordem():
    runs = [
        {"id": 1, "conclusion": "success"},
        {"id": 2, "conclusion": "cancelled"},
        {"id": 3, "conclusion": None},
        {"id": 4, "conclusion": "timed_out"},
        {"id": 5},
        {"id": 6, "conclusion": "failure"},
    ]

    assert [r["id"] for r in runs_validos(runs)] == [1, 4, 6]


def test_runs_validos_nao_altera_a_entrada():
    runs = [{"id": 1, "conclusion": "success"}, {"id": 2, "conclusion": "skipped"}]
    copia = [dict(r) for r in runs]

    runs_validos(runs)

    assert runs == copia


def test_runs_validos_lista_vazia():
    assert runs_validos([]) == []
