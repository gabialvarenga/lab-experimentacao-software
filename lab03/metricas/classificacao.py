"""Classificação DORA (tabela da RQ 07): nota por métrica e categoria geral do repositório.

Notas: Elite 4, High 3, Medium 2, Low 1. A categoria geral é a mediana das notas
existentes, arredondada para baixo; métrica indefinida (`None`) não recebe nota.
"""

from math import floor
from statistics import median

CATEGORIAS = {4: "Elite", 3: "High", 2: "Medium", 1: "Low"}

SEMANAS_DA_JANELA = 365 / 7
HORAS_DIA = 24
HORAS_SEMANA = 7 * HORAS_DIA
HORAS_30_DIAS = 30 * HORAS_DIA


def classificar(
    freq_semana: float | None,
    lead_time_h: float | None,
    cfr: float | None,
    recuperacao_h: float | None,
    semanas_janela: float = SEMANAS_DA_JANELA,
) -> tuple[str | None, int]:
    """Categoria geral e número de métricas classificadas; `(None, 0)` sem nenhuma métrica.

    `cfr` é uma fração entre 0 e 1. `semanas_janela` define o corte de "1 por mês"
    (12 ÷ semanas da janela).
    """
    notas = [
        nota
        for nota in (
            nota_frequencia(freq_semana, semanas_janela),
            nota_lead_time(lead_time_h),
            nota_cfr(cfr),
            nota_recuperacao(recuperacao_h),
        )
        if nota is not None
    ]
    if not notas:
        return None, 0
    return CATEGORIAS[floor(median(notas))], len(notas)


def nota_frequencia(freq_semana: float | None, semanas_janela: float = SEMANAS_DA_JANELA) -> int | None:
    """Deploys por semana: Elite ≥ 7; High ≥ 1; Medium ≥ 1 por mês; Low abaixo disso."""
    if freq_semana is None:
        return None
    if freq_semana >= 7:
        return 4
    if freq_semana >= 1:
        return 3
    if freq_semana >= 12 / semanas_janela:
        return 2
    return 1


def nota_lead_time(lead_time_h: float | None) -> int | None:
    """Horas: Elite < 1 dia; High < 1 semana; Medium < 30 dias; Low ≥ 30 dias."""
    if lead_time_h is None:
        return None
    if lead_time_h < HORAS_DIA:
        return 4
    if lead_time_h < HORAS_SEMANA:
        return 3
    if lead_time_h < HORAS_30_DIAS:
        return 2
    return 1


def nota_cfr(cfr: float | None) -> int | None:
    """Fração de 0 a 1: Elite ≤ 15%; High ≤ 30%; Medium ≤ 45%; Low > 45%."""
    if cfr is None:
        return None
    if cfr <= 0.15:
        return 4
    if cfr <= 0.30:
        return 3
    if cfr <= 0.45:
        return 2
    return 1


def nota_recuperacao(recuperacao_h: float | None) -> int | None:
    """Horas: Elite < 1 hora; High < 1 dia; Medium < 1 semana; Low ≥ 1 semana."""
    if recuperacao_h is None:
        return None
    if recuperacao_h < 1:
        return 4
    if recuperacao_h < HORAS_DIA:
        return 3
    if recuperacao_h < HORAS_SEMANA:
        return 2
    return 1
