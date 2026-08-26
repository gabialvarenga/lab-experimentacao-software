# Relatório de qualidade de dados

Gerado a partir de `data/repositories.csv` — base para as hipóteses informais das Issues #9, #10 e #11.

## RQ01 — Idade (anos)

Coluna: `idade_anos`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0.01 | 18.35 | 7.72 | 3.51 | 11.34 | 0 | 0/1000 |

## RQ02 — PRs aceitas

Coluna: `prs_aceitas`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 103142 | 765.50 | 175.00 | 3390.00 | 123 | 0/1000 |

## RQ03 — Total de releases

Coluna: `total_releases`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 1000 | 39.50 | 0.00 | 148.25 | 94 | 0/1000 |

## RQ04 — Dias desde a última atualização

Coluna: `dias_desde_atualizacao`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 2448 | 3.00 | 0.00 | 49.00 | 191 | 0/1000 |

## RQ05 — Linguagem primária

Coluna: `linguagem`

| Categoria | Contagem |
|---|---|
| Python | 229 |
| TypeScript | 174 |
| JavaScript | 110 |
| Go | 76 |
| Rust | 57 |
| *(demais 38 categorias)* | — |
| **Não informado** | 87 |

## RQ06 — Razão de issues fechadas

Coluna: `razao_issues_fechadas`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 1 | 0.86 | 0.67 | 0.97 | 60 | 0/1000 |

## RQ08 (bônus) — Total de forks

Coluna: `total_forks`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 36 | 109092 | 6339.00 | 3575.50 | 10857.50 | 93 | 0/1000 |

## RQ09 (extra) — Licença

Coluna: `licenca`

| Categoria | Contagem |
|---|---|
| MIT License | 394 |
| Apache License 2.0 | 181 |
| Other | 148 |
| GNU General Public License v3.0 | 50 |
| GNU Affero General Public License v3.0 | 48 |
| *(demais 14 categorias)* | — |
| **Não informado** | 84 |

## RQ10 (extra) — Possui CI/CD

Coluna: `possui_ci_cd`

| Valor | Contagem |
|---|---|
| true | 798 |
| false | 202 |

## RQ11 (extra) — Total de linguagens

Coluna: `total_linguagens`

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 56 | 5.00 | 3.00 | 9.00 | 48 | 0/1000 |

