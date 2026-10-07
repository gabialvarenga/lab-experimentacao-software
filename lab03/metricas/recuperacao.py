"""Tempo de recuperação (RQ 04): duração dos episódios de falha de cada workflow, em horas.

Um episódio começa na primeira falha depois de um sucesso e termina no próximo sucesso do
mesmo workflow. A duração é `updated_at` do sucesso − `run_started_at` da primeira falha.
Runs ignorados (`cancelled`, `skipped`, em andamento etc.) não abrem nem encerram episódios.

Censura (seção 3 do enunciado): episódios que não terminam na janela são contados, não
descartados.
- À direita: falha sem sucesso posterior.
- À esquerda: o workflow já começa a janela falhando, então o início real da falha é
  desconhecido. Vale mesmo que o episódio também não se recupere, e cada episódio é
  contado uma única vez, como censurado à esquerda.
A mediana usa só os episódios completos.
"""

from collections import defaultdict
from statistics import median

from metricas.conclusao import FALHA, classificar_conclusao


def tempo_recuperacao(runs: list[dict]) -> dict:
    """Mediana e contagens dos episódios de todos os workflows do repositório.

    Devolve `mediana_horas` (`None` se não há episódio completo), `n_episodios` (inclui os
    censurados), `n_censurados_direita` e `n_censurados_esquerda`. A proporção censurada é
    `(direita + esquerda) ÷ n_episodios`.
    """
    por_workflow = defaultdict(list)
    for run in runs:
        if classificar_conclusao(run.get("conclusion")) is not None:
            por_workflow[run.get("workflow_id")].append(run)

    duracoes = []
    n_episodios = n_direita = n_esquerda = 0
    for do_workflow in por_workflow.values():
        do_workflow.sort(key=lambda run: (run["run_started_at"], run.get("id", 0)))
        primeira_falha = None
        censurado_esquerda = False
        anterior = None
        for run in do_workflow:
            falhou = classificar_conclusao(run["conclusion"]) == FALHA
            if falhou and primeira_falha is None:
                primeira_falha = run
                censurado_esquerda = anterior is None
                n_episodios += 1
            elif not falhou and primeira_falha is not None:
                if censurado_esquerda:
                    n_esquerda += 1
                else:
                    duracoes.append(_horas(primeira_falha["run_started_at"], run["updated_at"]))
                primeira_falha = None
            anterior = run
        if primeira_falha is not None:  # falha sem sucesso posterior
            if censurado_esquerda:
                n_esquerda += 1
            else:
                n_direita += 1

    return {
        "mediana_horas": median(duracoes) if duracoes else None,
        "n_episodios": n_episodios,
        "n_censurados_direita": n_direita,
        "n_censurados_esquerda": n_esquerda,
    }


def _horas(inicio, fim) -> float:
    return (fim - inicio).total_seconds() / 3600
