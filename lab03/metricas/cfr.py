"""CFR (RQ 03), variante (a): proporção de workflow runs com falha."""

from metricas.conclusao import FALHA, SUCESSO, classificar_conclusao


def cfr_ci(runs: list[dict]) -> float | None:
    """`falhas ÷ (falhas + sucessos)`, com todos os workflows juntos.

    Runs ignorados (`cancelled`, `skipped`, em andamento etc.) não entram. Devolve `None`
    quando não há nenhum run de sucesso ou falha.
    """
    classes = [classificar_conclusao(run.get("conclusion")) for run in runs]
    falhas = classes.count(FALHA)
    total = falhas + classes.count(SUCESSO)
    return falhas / total if total else None
