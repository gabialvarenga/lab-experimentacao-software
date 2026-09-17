import math
import re

FORMATO = re.compile(r"^(\d{2}):(\d{2})$")

TARIFA_PRIMEIRA_HORA = 5.0
TARIFA_HORA_ADICIONAL = 3.0
TETO_DIARIO = 25.0
MINUTOS_GRATIS = 15


def _minutos_desde_meia_noite(horario: str) -> int:
    match = FORMATO.match(horario)
    if not match:
        raise ValueError(f"horário inválido: {horario}")

    hora, minuto = int(match.group(1)), int(match.group(2))
    if not (0 <= hora <= 23) or not (0 <= minuto <= 59):
        raise ValueError(f"horário inválido: {horario}")

    return hora * 60 + minuto


def calcular_tarifa(entrada: str, saida: str) -> float:
    entrada_min = _minutos_desde_meia_noite(entrada)
    saida_min = _minutos_desde_meia_noite(saida)

    if saida_min <= entrada_min:
        raise ValueError("saída anterior à entrada")

    duracao_min = saida_min - entrada_min
    if duracao_min <= MINUTOS_GRATIS:
        return 0.0

    horas_iniciadas = math.ceil(duracao_min / 60)
    tarifa = TARIFA_PRIMEIRA_HORA + TARIFA_HORA_ADICIONAL * (horas_iniciadas - 1)
    return min(tarifa, TETO_DIARIO)
