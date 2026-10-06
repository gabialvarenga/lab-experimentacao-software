"""Classificação do `conclusion` de um workflow run (seção 3 do enunciado)."""

SUCESSO = "sucesso"
FALHA = "falha"

_SUCESSOS = {"success"}
_FALHAS = {"failure", "timed_out", "startup_failure"}


def classificar_conclusao(conclusion: str | None) -> str | None:
    """`"sucesso"`, `"falha"` ou `None` para o que deve ser ignorado.

    Ignorados: `cancelled`, `skipped`, `neutral`, `action_required`, `stale`, vazio
    (execução em andamento) e qualquer valor desconhecido.
    """
    if conclusion in _SUCESSOS:
        return SUCESSO
    if conclusion in _FALHAS:
        return FALHA
    return None


def runs_validos(runs: list[dict]) -> list[dict]:
    """Runs cuja `conclusion` conta como sucesso ou falha, na ordem original."""
    return [run for run in runs if classificar_conclusao(run.get("conclusion")) is not None]
