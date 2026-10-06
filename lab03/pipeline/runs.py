"""Coleta dos workflow runs do default branch (`event=push`) na janela.

A API limita cada consulta a 1.000 resultados. Por isso a janela é dividida em meses;
um mês que atinge o teto é refeito dia a dia, e um dia que também atinge o teto gera um
aviso (a coleta daquele dia fica truncada).
"""

import calendar
import logging
from datetime import date, datetime, timedelta

from metricas.janela import dentro_da_janela
from pipeline import cliente_http

LIMITE_DA_API = 1000

log = logging.getLogger(__name__)


def dividir_em_meses(inicio: date, fim: date) -> list[tuple[date, date]]:
    """Fatias por mês-calendário, recortadas pelos limites da janela."""
    if fim < inicio:
        raise ValueError("fim não pode ser anterior ao início")
    fatias = []
    atual = inicio
    while atual <= fim:
        ultimo_dia = date(atual.year, atual.month, calendar.monthrange(atual.year, atual.month)[1])
        fatias.append((atual, min(ultimo_dia, fim)))
        atual = ultimo_dia + timedelta(days=1)
    return fatias


def coletar_runs(owner: str, repo: str, branch: str, inicio: date, fim: date) -> list[dict]:
    """Runs criados em [inicio, fim] no `branch`, ordenados por `created_at`.

    Cada item traz `id`, `workflow_id`, `conclusion` (texto ou `None`) e
    `created_at`, `run_started_at`, `updated_at` como `datetime` em UTC.
    """
    brutos = []
    for ini_fatia, fim_fatia in dividir_em_meses(inicio, fim):
        itens = _consultar(owner, repo, branch, ini_fatia, fim_fatia)
        if len(itens) >= LIMITE_DA_API:
            itens = []
            dia = ini_fatia
            while dia <= fim_fatia:
                do_dia = _consultar(owner, repo, branch, dia, dia)
                if len(do_dia) >= LIMITE_DA_API:
                    log.warning("%s/%s: %s atingiu %d runs; coleta do dia truncada", owner, repo, dia, LIMITE_DA_API)
                itens.extend(do_dia)
                dia += timedelta(days=1)
        brutos.extend(itens)

    runs = {}
    for bruto in brutos:
        run = _normalizar(bruto)
        if dentro_da_janela(run["created_at"], inicio, fim):
            runs[run["id"]] = run
    return sorted(runs.values(), key=lambda run: (run["created_at"], run["id"]))


def _consultar(owner: str, repo: str, branch: str, inicio: date, fim: date) -> list[dict]:
    params = {
        "branch": branch,
        "event": "push",
        "created": f"{inicio.isoformat()}..{fim.isoformat()}",
    }
    return cliente_http.get_paginado(f"/repos/{owner}/{repo}/actions/runs", params, chave="workflow_runs")


def _normalizar(bruto: dict) -> dict:
    criado = _data(bruto["created_at"])
    return {
        "id": bruto["id"],
        "workflow_id": bruto["workflow_id"],
        "conclusion": bruto.get("conclusion") or None,
        "created_at": criado,
        "run_started_at": _data(bruto["run_started_at"]) if bruto.get("run_started_at") else criado,
        "updated_at": _data(bruto["updated_at"]),
    }


def _data(texto: str) -> datetime:
    return datetime.fromisoformat(texto)
