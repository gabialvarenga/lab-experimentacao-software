"""Lead time (RQ 02): tempo entre o commit e a release que o publicou, em horas.

Release com `commits = None` (primeira release ou `compare` com 404) ou com lista vazia
(sem commits novos) fica fora do cálculo nas duas variantes.
"""

from datetime import datetime
from statistics import median


def lead_time_por_release(releases: list[dict]) -> float | None:
    """Variante (a): mediana, entre releases, de `published_at − commit mais antigo`."""
    return _mediana(
        [_horas(release["published_at"], min(release["commits"])) for release in releases if release["commits"]]
    )


def lead_time_por_commit(releases: list[dict]) -> float | None:
    """Variante (b): mediana, entre todos os commits, de `published_at − data do commit`."""
    return _mediana(
        [
            _horas(release["published_at"], commit)
            for release in releases
            for commit in release["commits"] or []
        ]
    )


def _horas(publicacao: datetime, commit: datetime) -> float:
    return (publicacao - commit).total_seconds() / 3600


def _mediana(valores: list[float]) -> float | None:
    return median(valores) if valores else None
