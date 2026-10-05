"""Janela de observação: duração em semanas e pertinência de datas."""

from datetime import date, datetime, time, timezone


def semanas(inicio: date, fim: date) -> float:
    """Duração da janela em semanas, com intervalo fechado [inicio, fim]."""
    if fim < inicio:
        raise ValueError("fim não pode ser anterior ao início")
    return ((fim - inicio).days + 1) / 7


def dentro_da_janela(data: datetime, inicio: date, fim: date) -> bool:
    """True se `data` está em [inicio 00:00:00 UTC, fim 23:59:59.999999 UTC]."""
    if data.tzinfo is None:
        raise ValueError("data sem fuso horário; normalize para UTC na coleta")
    if fim < inicio:
        raise ValueError("fim não pode ser anterior ao início")
    limite_inicial = datetime.combine(inicio, time.min, tzinfo=timezone.utc)
    limite_final = datetime.combine(fim, time.max, tzinfo=timezone.utc)
    return limite_inicial <= data.astimezone(timezone.utc) <= limite_final
