"""Critério de inclusão e tabela do funil de seleção (seções 3 e 7 do enunciado).

`aprovado` decide se um repositório entra na amostra; `Funil` acumula quantos
repositórios restaram em cada etapa e por que os demais foram descartados.
"""

import csv
import os
from datetime import date

from metricas.conclusao import runs_validos
from metricas.frequencia import deploys_na_janela

MIN_RELEASES = 5
MIN_RUNS = 50

# Motivos de descarte. `aprovado` devolve os dois de contagem; os outros dois são
# decididos fora dela (busca de workflows e tratamento de erros da coleta) e entram no
# funil por `Funil.registrar`.
SEM_ACTIONS = "sem Actions"
ERRO_DA_API = "erro da API"


def motivo_poucas_releases(minimo: int = MIN_RELEASES) -> str:
    return f"menos de {minimo} releases"


def motivo_poucos_runs(minimo: int = MIN_RUNS) -> str:
    return f"menos de {minimo} runs"


def aprovado(
    releases: list[dict],
    runs: list[dict] | None,
    inicio: date,
    fim: date,
    min_releases: int = MIN_RELEASES,
    min_runs: int = MIN_RUNS,
) -> tuple[bool, str | None]:
    """`(True, None)` se o repositório atende ao critério; senão `(False, motivo)`.

    Conta deploys (release publicada, sem `draft` nem `prerelease`, dentro da janela) e
    runs válidos (`conclusion` de sucesso ou falha). Os `runs` já vêm filtrados pela
    janela da coleta. Com `runs = None`, só o critério de releases é avaliado, para
    descartar o repositório antes de coletar os runs. As releases são avaliadas primeiro:
    4 deploys e 500 runs são descartados por releases.
    """
    if len(deploys_na_janela(releases, inicio, fim)) < min_releases:
        return False, motivo_poucas_releases(min_releases)
    if runs is not None and len(runs_validos(runs)) < min_runs:
        return False, motivo_poucos_runs(min_runs)
    return True, None


class Funil:
    """Tabela com uma linha por etapa: quantos repositórios entraram, quantos saíram e o motivo."""

    COLUNAS = ("etapa", "entrada", "saida", "motivo")

    def __init__(self):
        self._linhas: list[tuple[str, int, int, str]] = []

    def registrar(self, etapa: str, entrada: int, saida: int, motivo: str) -> None:
        """Acrescenta uma etapa. `motivo` descreve por que `entrada - saida` repositórios saíram."""
        if entrada < 0 or saida < 0:
            raise ValueError("entrada e saída não podem ser negativas")
        if saida > entrada:
            raise ValueError(f"etapa {etapa!r}: saída ({saida}) maior que a entrada ({entrada})")
        self._linhas.append((etapa, entrada, saida, motivo))

    @property
    def linhas(self) -> list[tuple[str, int, int, str]]:
        return list(self._linhas)

    def salvar_csv(self, caminho: str) -> None:
        """Grava a tabela em CSV (UTF-8, quebra de linha `\\n`), criando a pasta se preciso."""
        pasta = os.path.dirname(caminho)
        if pasta:
            os.makedirs(pasta, exist_ok=True)
        with open(caminho, "w", encoding="utf-8", newline="") as arquivo:
            escritor = csv.writer(arquivo, lineterminator="\n")
            escritor.writerow(self.COLUNAS)
            escritor.writerows(self._linhas)
