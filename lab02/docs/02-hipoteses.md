# Lab02 — Hipóteses estatísticas por RQ (Passo 1)

Formaliza o item (A) do Passo 1 — hipóteses nula e alternativa — deixado em
aberto em [01-desenho-experimento.md](01-desenho-experimento.md) (#64).
Reaproveita, sem redefinir, o que já foi decidido em
[00-decisoes.md](00-decisoes.md) (#59) e em `01-desenho-experimento.md`: as
colunas de `trials.csv`/`metricas-estaticas.csv`, os dois níveis do
tratamento (`com-ia` / `sem-ia`) e o teste de Wilcoxon pareado.

## Convenções comuns às três RQs

- **Nível de significância:** α = 0,05 para os três testes.
- **Teste estatístico:** Wilcoxon signed-rank pareado (não paramétrico),
  adequado ao N pequeno e à ausência de garantia de normalidade — já
  convenção do enunciado e de `00-decisoes.md`.
- **Natureza pareada (within-subject):** o par comparado em cada teste é
  sempre *o mesmo integrante sob os dois tratamentos*, nunca integrantes
  diferentes entre si — decorrência direta do desenho crossover
  contrabalanceado de `01-desenho-experimento.md` (#64). O esquema exato de
  agregação dos pares (por trial na sequência contrabalanceada ou por
  mediana agregada por integrante) é detalhe de execução do teste e fica
  para o Passo 4 (Análise), fora do escopo desta issue.
- **Estatística descritiva:** mediana e IQR por tratamento, não média/desvio
  padrão — N pequeno (3 trials por tratamento por integrante).

## RQ1 — Tempo

**Variável:** `tempo_segundos` (`trials.csv`) — tempo até passar todos os
testes de aceitação; trials que estouram o time-box entram como censurados
em 2100s (35 min), não descartados (`00-decisoes.md`).

- **H0:** a mediana do tempo até verde é igual com e sem IA.
  `Med(tempo_segundos | com-ia) = Med(tempo_segundos | sem-ia)`
- **H1:** a mediana do tempo até verde é **menor** com IA.
  `Med(tempo_segundos | com-ia) < Med(tempo_segundos | sem-ia)`
- **Direção esperada:** redução de tempo com IA.
- **Teste previsto:** Wilcoxon pareado, **unicaudal** (a favor de `com-ia`
  menor).

## RQ2 — Defeitos

**Variáveis:** `taxa_sucesso` (primária, = `testes_passando / testes_total`)
e nº de testes falhando (complementar, = `testes_total - testes_passando`),
ambas de `trials.csv`.

- **H0:** a mediana da taxa de sucesso é igual com e sem IA.
  `Med(taxa_sucesso | com-ia) = Med(taxa_sucesso | sem-ia)`
- **H1:** a mediana da taxa de sucesso é **maior** com IA (equivalente a
  menos testes falhando ao final do time-box).
  `Med(taxa_sucesso | com-ia) > Med(taxa_sucesso | sem-ia)`
- **Direção esperada:** menos defeitos (mais testes passando) com IA.
- **Teste previsto:** Wilcoxon pareado, **unicaudal** (a favor de `com-ia`
  maior). A mesma hipótese, formulada sobre o nº de testes falhando, é
  unicaudal na direção oposta (`com-ia` menor) — é a mesma pergunta com
  sinal invertido, não uma hipótese adicional.

## RQ3 — Estrutura do código

**Variáveis:** `cc_media` (complexidade ciclomática média por função) e
`duplicacao_pct` (% de linhas duplicadas), ambas de
`metricas-estaticas.csv`, sempre reportadas junto de `loc` como controle
obrigatório — código gerado por IA pode ser mais verboso, e comparar
complexidade/duplicação sem essa referência pode enganar (convenção do
enunciado, já registrada em `01-desenho-experimento.md`). `loc` é controle,
não uma variável testada por hipótese própria.

- **H0 (complexidade):** a mediana de `cc_media` é igual com e sem IA.
  `Med(cc_media | com-ia) = Med(cc_media | sem-ia)`
- **H1 (complexidade):** a mediana de `cc_media` **difere** entre os
  tratamentos.
  `Med(cc_media | com-ia) ≠ Med(cc_media | sem-ia)`
- **H0 (duplicação):** a mediana de `duplicacao_pct` é igual com e sem IA.
  `Med(duplicacao_pct | com-ia) = Med(duplicacao_pct | sem-ia)`
- **H1 (duplicação):** a mediana de `duplicacao_pct` **difere** entre os
  tratamentos.
  `Med(duplicacao_pct | com-ia) ≠ Med(duplicacao_pct | sem-ia)`
- **Direção esperada:** nenhuma fixada a priori. O enunciado só prevê que a
  IA "altera" complexidade/duplicação, sem prever sentido de melhora ou
  piora — diferente de RQ1/RQ2, que têm uma direção de melhoria clara.
- **Teste previsto:** Wilcoxon pareado, **bicaudal**, um teste para
  `cc_media` e outro para `duplicacao_pct`.

## Tabela-resumo

| RQ | Variável(is) | H0 | H1 | Direção esperada | Teste | α | Pareamento |
|---|---|---|---|---|---|---|---|
| RQ1 — Tempo | `tempo_segundos` | mediana igual entre tratamentos | mediana **menor** com IA | redução de tempo com IA | Wilcoxon pareado, unicaudal | 0,05 | within-subject |
| RQ2 — Defeitos | `taxa_sucesso` (nº de testes falhando, complementar) | mediana igual entre tratamentos | mediana **maior** com IA (menos falhas) | mais testes passando com IA | Wilcoxon pareado, unicaudal | 0,05 | within-subject |
| RQ3 — Estrutura | `cc_media`, `duplicacao_pct` (LOC como controle) | mediana igual entre tratamentos | mediana **difere** entre tratamentos | sem direção fixada a priori | Wilcoxon pareado, bicaudal (um teste por variável) | 0,05 | within-subject |

## Fora do escopo desta issue

- Ameaças à validade (efeito de aprendizado, familiaridade prévia,
  memorização, força do tratamento `com-ia`) — #66.
- Esquema de agregação dos pares e execução dos testes de Wilcoxon — Passo 4
  (S03).
- Seleção e validação dos katas reais — #61 (já concluída em
  [katas.md](katas.md)).
