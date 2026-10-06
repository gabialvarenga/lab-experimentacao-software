import logging
from datetime import date, datetime, timezone

import pytest

from pipeline import runs

INICIO = date(2025, 10, 1)
FIM = date(2026, 9, 30)


class ApiFalsa:
    """Substitui `get_paginado`: devolve a lista registrada para cada intervalo `created`."""

    def __init__(self, respostas=None):
        self.respostas = respostas or {}
        self.chamadas = []

    def get_paginado(self, caminho, params=None, chave=None):
        self.chamadas.append((caminho, dict(params), chave))
        return self.respostas.get(params["created"], [])


@pytest.fixture
def api(monkeypatch):
    falsa = ApiFalsa()
    monkeypatch.setattr(runs.cliente_http, "get_paginado", falsa.get_paginado)
    return falsa


def bruto(id, criado, conclusion="success", workflow_id=1):
    return {
        "id": id,
        "workflow_id": workflow_id,
        "name": "CI",
        "event": "push",
        "conclusion": conclusion,
        "created_at": criado,
        "run_started_at": criado,
        "updated_at": criado,
    }


def em_massa(quantidade, criado="2025-11-10T12:00:00Z", base=100_000):
    return [bruto(base + i, criado) for i in range(quantidade)]


def test_dividir_em_meses_da_janela_completa():
    fatias = runs.dividir_em_meses(INICIO, FIM)

    assert len(fatias) == 12
    assert fatias[0] == (date(2025, 10, 1), date(2025, 10, 31))
    assert fatias[-1] == (date(2026, 9, 1), date(2026, 9, 30))


def test_dividir_em_meses_com_janela_no_meio_do_mes():
    assert runs.dividir_em_meses(date(2025, 10, 15), date(2025, 12, 10)) == [
        (date(2025, 10, 15), date(2025, 10, 31)),
        (date(2025, 11, 1), date(2025, 11, 30)),
        (date(2025, 12, 1), date(2025, 12, 10)),
    ]


def test_dividir_em_meses_dentro_de_um_unico_mes():
    assert runs.dividir_em_meses(date(2025, 10, 5), date(2025, 10, 9)) == [(date(2025, 10, 5), date(2025, 10, 9))]


def test_dividir_em_meses_fevereiro_bissexto():
    assert runs.dividir_em_meses(date(2028, 2, 1), date(2028, 2, 29)) == [(date(2028, 2, 1), date(2028, 2, 29))]


def test_dividir_em_meses_janela_invertida():
    with pytest.raises(ValueError):
        runs.dividir_em_meses(FIM, INICIO)


def test_uma_consulta_por_mes_com_os_filtros_da_issue(api):
    runs.coletar_runs("o", "r", "main", INICIO, FIM)

    assert len(api.chamadas) == 12
    caminho, params, chave = api.chamadas[0]
    assert caminho == "/repos/o/r/actions/runs"
    assert params == {"branch": "main", "event": "push", "created": "2025-10-01..2025-10-31"}
    assert chave == "workflow_runs"
    assert api.chamadas[-1][1]["created"] == "2026-09-01..2026-09-30"


def test_janela_comecando_no_meio_do_mes(api):
    runs.coletar_runs("o", "r", "main", date(2025, 10, 15), date(2025, 11, 10))

    assert [c[1]["created"] for c in api.chamadas] == ["2025-10-15..2025-10-31", "2025-11-01..2025-11-10"]


def test_mes_com_exatamente_1000_resultados_e_subdividido_em_dias(api):
    api.respostas["2025-11-01..2025-11-30"] = em_massa(1000)
    api.respostas["2025-11-10..2025-11-10"] = [bruto(1, "2025-11-10T08:00:00Z")]
    api.respostas["2025-11-20..2025-11-20"] = [bruto(2, "2025-11-20T08:00:00Z")]

    resultado = runs.coletar_runs("o", "r", "main", INICIO, FIM)

    consultas = [c[1]["created"] for c in api.chamadas]
    assert len(consultas) == 12 + 30  # 12 meses + 30 dias de novembro
    assert "2025-11-01..2025-11-01" in consultas and "2025-11-30..2025-11-30" in consultas
    assert [r["id"] for r in resultado] == [1, 2]  # só o que veio das consultas diárias


def test_mes_com_999_resultados_nao_e_subdividido(api):
    api.respostas["2025-11-01..2025-11-30"] = em_massa(999)

    resultado = runs.coletar_runs("o", "r", "main", INICIO, FIM)

    assert len(api.chamadas) == 12
    assert len(resultado) == 999


def test_dia_com_1000_resultados_gera_aviso(api, caplog):
    api.respostas["2025-11-01..2025-11-30"] = em_massa(1000)
    api.respostas["2025-11-10..2025-11-10"] = em_massa(1000, base=200_000)

    with caplog.at_level(logging.WARNING, logger="pipeline.runs"):
        resultado = runs.coletar_runs("o", "r", "main", INICIO, FIM)

    assert any("2025-11-10" in mensagem for mensagem in caplog.messages)
    assert len(resultado) == 1000  # mantém o que veio, truncado


def test_campos_normalizados_a_partir_da_fixture(api, fixture_json):
    api.respostas["2025-10-01..2025-10-31"] = fixture_json("runs_mensal")["workflow_runs"]

    resultado = runs.coletar_runs("o", "r", "main", INICIO, FIM)

    assert [r["id"] for r in resultado] == [1001, 1002, 1003, 1004, 1005]
    primeiro = resultado[0]
    assert set(primeiro) == {"id", "workflow_id", "conclusion", "created_at", "run_started_at", "updated_at"}
    assert primeiro["workflow_id"] == 11
    assert primeiro["created_at"] == datetime(2025, 10, 2, 9, 0, tzinfo=timezone.utc)
    assert primeiro["run_started_at"] == datetime(2025, 10, 2, 9, 0, 5, tzinfo=timezone.utc)
    assert primeiro["updated_at"] == datetime(2025, 10, 2, 9, 10, tzinfo=timezone.utc)
    assert [r["conclusion"] for r in resultado] == ["success", "failure", "cancelled", None, "success"]


def test_run_started_at_ausente_usa_created_at(api):
    item = bruto(1, "2025-10-02T09:00:00Z")
    item["run_started_at"] = None
    api.respostas["2025-10-01..2025-10-31"] = [item]

    (run,) = runs.coletar_runs("o", "r", "main", INICIO, FIM)

    assert run["run_started_at"] == run["created_at"]


def test_duplicados_ordem_e_runs_fora_da_janela(api):
    api.respostas["2025-10-01..2025-10-31"] = [
        bruto(3, "2025-10-20T10:00:00Z"),
        bruto(1, "2025-10-02T10:00:00Z"),
        bruto(1, "2025-10-02T10:00:00Z"),
        bruto(9, "2025-09-30T23:59:59Z"),
        bruto(2, "2025-10-10T10:00:00Z"),
    ]

    resultado = runs.coletar_runs("o", "r", "main", INICIO, FIM)

    assert [r["id"] for r in resultado] == [1, 2, 3]


def test_repositorio_sem_runs_devolve_lista_vazia(api):
    assert runs.coletar_runs("o", "sem-actions", "main", INICIO, FIM) == []
