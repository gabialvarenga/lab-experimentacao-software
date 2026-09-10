# Lab02 — Assistentes de IA vs. codificação manual

Experimento controlado (crossover *within-subject*, *time-boxed*) para avaliar o
efeito do uso de um assistente de IA generativa na resolução de tarefas de
programação, quanto a tempo, defeitos e estrutura do código.

## Integrantes

- Brenda Evers (1523565)
- Carlos José Gomes Batista Figueiredo (1507022)
- Gabriela Alvarenga Cardoso (1026227)

## GitHub Projects (Kanban)

Board do grupo: [Kanban](https://github.com/users/gabialvarenga/projects/9)

## Documentação

| Documento | Descrição |
|---|---|
| [docs/00-decisoes.md](docs/00-decisoes.md) | Decisões de setup (linguagem, ferramentas, assistente de IA, framework de testes, esquema de dados) — issue #59 |
| [docs/katas.md](docs/katas.md) | Katas do experimento: critério de equivalência de dificuldade, candidatos e distribuição contrabalanceada — issue #61 |
| [scripts/README.md](scripts/README.md) | Uso dos scripts de cronometragem e de validação das katas |

## Estrutura

```
lab02/
    docs/            # decisões e desenho do experimento
    katas/           # k1..k6: enunciado, suíte de aceitação e esqueleto
    scripts/         # cronometro.py e validar_katas.py
    tests/           # testes dos scripts
    dados/           # trials.csv e metricas-estaticas.csv (coleta da S02)
    trials/          # código produzido em cada trial
```
