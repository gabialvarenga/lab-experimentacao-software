import re


def _minutos(horario: str) -> int:
    m = re.fullmatch(r"(\d{2}):(\d{2})", horario)
    if not m:
        raise ValueError(f"horário inválido: {horario}")
    hora, minuto = int(m.group(1)), int(m.group(2))
    if not (0 <= hora <= 23) or not (0 <= minuto <= 59):
        raise ValueError(f"horário inválido: {horario}")
    return hora * 60 + minuto


def calcular_tarifa(entrada: str, saida: str) -> float:
    minutos_entrada = _minutos(entrada)
    minutos_saida = _minutos(saida)
    if minutos_saida <= minutos_entrada:
        raise ValueError("saída anterior à entrada")

    permanencia = minutos_saida - minutos_entrada
    if permanencia <= 15:
        return 0.0

    horas_iniciadas = -(-permanencia // 60)
    tarifa = 5.0 + max(0, horas_iniciadas - 1) * 3.0
    return min(tarifa, 25.0)
