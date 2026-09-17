import math


def _converter_minutos(horario: str) -> int:
    partes = horario.split(":")
    if len(partes) != 2 or not (partes[0].isdigit() and partes[1].isdigit()) or len(partes[0]) != 2 or len(partes[1]) != 2:
        raise ValueError(f"horário inválido: {horario}")

    h, m = int(partes[0]), int(partes[1])
    if not (0 <= h <= 23 and 0 <= m <= 59):
        raise ValueError(f"horário inválido: {horario}")

    return h * 60 + m


def calcular_tarifa(entrada: str, saida: str) -> float:
    m_entrada = _converter_minutos(entrada)
    m_saida = _converter_minutos(saida)

    if m_saida <= m_entrada:
        raise ValueError("saída anterior à entrada")

    duracao = m_saida - m_entrada

    if duracao <= 15:
        return 0.0

    horas_iniciadas = math.ceil(duracao / 60)
    valor = 5.0 + (horas_iniciadas - 1) * 3.0

    return min(valor, 25.0)
