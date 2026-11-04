# Lab04 — Dicionário de dados

Descreve cada coluna e cada campo dos arquivos de `dados/reais/`. A fonte, os grupos e os critérios da coleta estão em [protocolo-coleta.md](protocolo-coleta.md); a calibração, em [calibracao-lognormal.md](calibracao-lognormal.md).

Siglas: PR (*Pull Request*); API (*Application Programming Interface*); CSV (*Comma-Separated Values*); IC (intervalo de confiança); IQR (amplitude interquartil); UTC (*Coordinated Universal Time*).

## 1. `dados/reais/prs.csv`

Uma linha por PR da amostra (60 linhas: 30 por grupo, 10 por mês de merge). Gerado por `python -m lab04 coletar`, ordenado por grupo e número do PR.

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `numero_pr` | inteiro | — | Número do PR em `supabase/supabase` (`number` da API de busca) |
| `grupo` | texto: `com_bot` ou `sem_bot` | — | Definido pela coleta: `com_bot` se a primeira revisão do Copilot saiu até 1 h após a abertura; `sem_bot` se o PR não teve revisão do Copilot |
| `autor` | texto | — | Login do autor (`user.login`); sempre de tipo `User`, nunca `Bot` |
| `criado_em` | data e hora ISO 8601 | UTC | `created_at` do PR |
| `mesclado_em` | data e hora ISO 8601 | UTC | `merged_at` do PR; é o que define o mês de merge usado na amostragem |
| `horas_ate_merge` | decimal (4 casas) | horas | `mesclado_em` − `criado_em`. Variável de resposta dos testes; sempre > 1 pelo protocolo |
| `horas_ate_revisao_bot` | decimal (4 casas) ou vazio | horas | `submitted_at` da primeira revisão de `copilot-pull-request-reviewer[bot]` − `criado_em`. Vazio no grupo `sem_bot`; ≤ 1 no `com_bot` |

## 2. `dados/reais/descritiva.csv`

Uma linha por grupo, sobre `horas_ate_merge`. Gerado por `python -m lab04 calibrar` (função `descritiva.descrever`), com 4 casas decimais.

| Coluna | Tipo | Unidade | Origem |
|---|---|---|---|
| `grupo` | texto | — | Valor de `grupo` em `prs.csv` |
| `n` | inteiro | PRs | Quantidade de PRs do grupo |
| `media` | decimal | horas | Média aritmética |
| `desvio_padrao` | decimal | horas | Desvio-padrão amostral (n − 1) |
| `minimo`, `maximo` | decimal | horas | Menor e maior valor |
| `q1`, `mediana`, `q3` | decimal | horas | Percentis 25, 50 e 75 (interpolação linear do NumPy) |
| `iqr` | decimal | horas | `q3` − `q1` |
| `assimetria` | decimal | adimensional | Coeficiente de Fisher-Pearson ajustado para amostra (`scipy.stats.skew(bias=False)`); positivo indica cauda longa à direita |
| `limite_outlier` | decimal | horas | `q3` + 1,5 × `iqr`; acima dele o PR é outlier |
| `n_outliers` | inteiro | PRs | Quantidade de PRs acima de `limite_outlier` |
| `pct_outliers` | decimal | % | `n_outliers` / `n` × 100 |

## 3. `dados/reais/calibracao.json`

Um objeto por grupo (`com_bot`, `sem_bot`) com os parâmetros da lognormal de `horas_ate_merge` e a incerteza deles. Gerado por `python -m lab04 calibrar` (função `calibracao.calibrar`). `mu` e `sigma` são os campos que a simulação lê (cenário C1).

| Campo | Tipo | Unidade | Origem |
|---|---|---|---|
| `n` | inteiro | PRs | Quantidade de PRs do grupo |
| `mu` | decimal | log(horas) | Média de log(`horas_ate_merge`) |
| `sigma` | decimal | log(horas) | Desvio-padrão amostral (n − 1) de log(`horas_ate_merge`) |
| `mediana_implicita` | decimal | horas | e^`mu`, a mediana da lognormal ajustada |
| `confianca` | decimal | — | Nível dos IC (0,95) |
| `mu_ic` | lista de 2 decimais | log(horas) | IC de `mu` pela t de Student (limites inferior e superior) |
| `sigma_ic` | lista de 2 decimais | log(horas) | IC de `sigma` pela qui-quadrado: `sigma · sqrt((n − 1) / χ²)` |
| `sigma_ic_bootstrap` | lista de 2 decimais | log(horas) | IC de `sigma` pelos percentis de 10.000 reamostragens (semente 42); conferência do IC acima |
| `piso_somado` | decimal | horas | Piso somado às horas do grupo antes do log; 0 se nenhuma hora é zero (nos dados reais é 0) |
| `ajuste.shapiro_p` | decimal | — | p-valor do Shapiro-Wilk sobre log(horas); `null` se todos os valores são iguais |
| `ajuste.qq_r` | decimal | — | Correlação do QQ-plot de log(horas) contra a normal; `null` se todos iguais |
| `ajuste.assimetria_log` | decimal | adimensional | Assimetria de log(horas); `null` se todos iguais |
| `ajuste.bom` | booleano | — | `true` se `shapiro_p` ≥ 0,05; `null` se não avaliado |
| `aviso` | texto (opcional) | — | Só aparece com menos de 10 PRs no grupo |

## 4. `docs/qqplot-lognormal.html`

QQ-plot interativo (Plotly) de log(horas) contra a normal, um painel por grupo, com o eixo das horas em escala log. Gerado junto com os arquivos acima. Mostra o que sustenta a escolha da lognormal; a leitura está em [calibracao-lognormal.md](calibracao-lognormal.md).
