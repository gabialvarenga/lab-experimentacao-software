# Relatório de qualidade de dados

Gerado a partir de `data/repositories.csv` — base para as hipóteses informais das Issues #9, #10 e #11.

## RQ01 — Idade (anos)

Coluna: `idade_anos`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0.04 | 18.38 | 7.72 | 3.46 | 11.34 | 0 | 0/1000 |

## RQ02 — PRs aceitas

Coluna: `prs_aceitas`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 103690 | 773.50 | 175.00 | 3425.50 | 124 | 0/1000 |

## RQ03 — Total de releases

Coluna: `total_releases`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 1000 | 41.00 | 0.00 | 149.25 | 94 | 0/1000 |

## RQ04 — Dias desde a última atualização

Coluna: `dias_desde_atualizacao`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 2458 | 1.00 | 0.00 | 42.00 | 198 | 0/1000 |

## RQ05 — Linguagem primária

Coluna: `linguagem`

| Categoria | Contagem |
|---|---|
| Python | 228 |
| TypeScript | 173 |
| JavaScript | 109 |
| Go | 77 |
| Rust | 58 |
| *(demais 38 categorias)* | — |
| **Não informado** | 87 |

## RQ06 — Razão de issues fechadas

Coluna: `razao_issues_fechadas`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 1 | 0.87 | 0.67 | 0.97 | 61 | 0/1000 |

## RQ08 (bônus) — Total de forks

Coluna: `total_forks`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 38 | 108902 | 6403.00 | 3624.50 | 10915.50 | 95 | 0/1000 |

## RQ08 (bônus) — Total de estrelas

Coluna: `total_estrelas`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 33040 | 543177 | 48868.50 | 38662.75 | 72965.50 | 82 | 0/1000 |

## RQ08 (bônus) — Razão fork/estrela

Coluna: `razao_fork_estrela`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0.0009096785004668088 | 1.9473825985453892 | 0.11 | 0.08 | 0.18 | 54 | 0/1000 |

## RQ09 (extra) — Licença

Coluna: `licenca`

| Categoria | Contagem |
|---|---|
| MIT License | 395 |
| Apache License 2.0 | 181 |
| Other | 148 |
| GNU General Public License v3.0 | 50 |
| GNU Affero General Public License v3.0 | 49 |
| *(demais 15 categorias)* | — |
| **Não informado** | 82 |

## RQ10 (extra) — Possui CI/CD

Coluna: `possui_ci_cd`

| Valor | Contagem |
|---|---|
| true | 800 |
| false | 200 |

## RQ11 (extra) — Total de linguagens

Coluna: `total_linguagens`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 56 | 5.00 | 3.00 | 9.00 | 48 | 0/1000 |

