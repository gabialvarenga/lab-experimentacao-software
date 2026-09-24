# Lab02 — Análise RQ3 (estrutura do código)

Gerado por [`analise/rq3_estatistica.py`](../analise/rq3_estatistica.py),
a partir de `dados/metricas-estaticas.csv` (18 trials, S02). Hipóteses e
teste previsto em [`docs/02-hipoteses.md`](../docs/02-hipoteses.md) (#65):
Wilcoxon pareado **bicaudal**, um teste por variável (`cc_media` e
`duplicacao_pct`), α=0,05, sem direção fixada a priori. Mesmo esquema de
pareamento de [`analise-rq1-rq2.md`](analise-rq1-rq2.md): o par é a
**mediana por integrante por tratamento** (N=3 — Brenda, Carlos,
Gabriela); o bootstrap reamostra no nível de trial (9 `com-ia` vs. 9
`sem-ia`).

## Estatística descritiva

Mediana e IQR (N pequeno — sem média/desvio), nos 9 trials por tratamento:

| Métrica | com-ia | sem-ia |
|---|---:|---:|
| `cc_media` | 4,00 [3,50 ; 6,00] | 6,00 [6,00 ; 7,00] |
| `duplicacao_pct` | 0,00 [0,00 ; 0,00] | 0,00 [0,00 ; 0,00] |
| `loc` (controle) | 18,0 [18,0 ; 20,0] | 20,0 [18,0 ; 23,0] |
| `mi` (aprofundamento) | 60,62 [59,81 ; 61,53] | 60,13 [55,05 ; 64,39] |
| `cc_max` (complementar) | 4,0 [4,0 ; 7,0] | 7,0 [6,0 ; 8,0] |

Outliers pela regra do IQR global (não são erros de coleta, só valores
extremos): `duplicacao_pct` = 35,71; `loc` = 11, 25, 26; `mi` = 73,82 e
75,25 (ambos `carlos` sem-ia, k6 e k1). `cc_media` e `cc_max` não têm
outliers.

## Complexidade ciclomática (`cc_media`)

Pares (mediana por integrante):

| Integrante | com-ia | sem-ia |
|---|---:|---:|
| brenda | 2,75 | 6,00 |
| carlos | 6,00 | 6,00 |
| gabriela | 4,00 | 9,00 |

- **Wilcoxon pareado (bicaudal):** W=0,00, **p=0,5000**, r=−1,000
  (rank-biserial).
- **Bootstrap IC 95% da diferença de mediana (com-ia − sem-ia):**
  **[−5,00 ; 0,00]**.

**Leitura.** Em 2 dos 3 integrantes `com-ia` teve complexidade menor; em
Carlos os dois tratamentos empataram em 6,00. Como a diferença zero é
descartada pelo Wilcoxon, o teste roda com **2 pares efetivos**, e nesse
caso o menor p bicaudal que o desenho poderia produzir é 0,5 — **H0 não
pode ser rejeitada, e nenhum resultado possível nesta amostra rejeitaria**.
O mesmo achado de RQ1 (limite do N=3), só que mais forte aqui por causa do
empate e do teste bicaudal. O tamanho de efeito aponta na mesma direção nos
pares (r=−1) e o bootstrap não é contrário (limite superior em 0,00), mas o
intervalo encosta no zero: **direção consistente com menor complexidade
com IA, sem evidência estatística**.

## Duplicação (`duplicacao_pct`)

- **Wilcoxon:** não computável — a mediana por integrante é 0,0 nos dois
  tratamentos para os três, então a diferença pareada é zero em todos os
  pares. Não é resultado nulo: é **ausência de variação para testar**
  (mesma natureza do achado de RQ2). O IC do bootstrap ([0,00 ; 0,00]) é
  degenerado pelo mesmo motivo, não informa nada.
- **O que a mediana esconde:** 17 dos 18 trials têm duplicação 0%. O único
  com duplicação é `gabriela/k5` **sem-ia**, 35,71%.

| Tratamento | Trials com `duplicacao_pct` > 0 |
|---|---:|
| com-ia | 0 de 9 |
| sem-ia | 1 de 9 |

Um único trial não sustenta nenhuma conclusão sobre o efeito da IA. Além
disso, os arquivos têm ~11 a 26 linhas, então 35,71% corresponde a poucas
linhas repetidas — o percentual é muito sensível ao tamanho do arquivo.
Leitura honesta: **os katas, nesse porte, quase não induzem duplicação, com
ou sem IA**; RQ3 fica sem poder de discriminar por essa variável.

## Índice de Manutenibilidade (`mi`) — aprofundamento

Métrica composta do Radon (0–100, maior = mais manutenível), tratada aqui
como aprofundamento do enunciado, em vez de coluna acessória.

| Integrante | com-ia | sem-ia | com-ia − sem-ia |
|---|---:|---:|---:|
| brenda | 60,62 | 55,05 | +5,57 |
| carlos | 59,81 | 73,82 | −14,01 |
| gabriela | 61,19 | 57,74 | +3,45 |

- **Wilcoxon pareado (bicaudal, exploratório):** W=3,00, **p=1,0000**,
  r=0,000.
- **Bootstrap IC 95% da diferença de mediana:** **[−12,63 ; +6,48]**.
- **Medianas quase iguais** (60,62 com-ia vs. 60,13 sem-ia), mas a
  **dispersão difere muito**: IQR de 1,72 em `com-ia` contra 9,34 em
  `sem-ia`.

**Leitura.** Não há efeito direcional em MI: dois integrantes têm MI maior
com IA, um tem menor (Carlos, sem-ia, cujos dois trials de MI mais alto —
75,25 e 73,82 — puxam a dispersão do grupo). O que aparece é que os
trials `com-ia` concentram-se numa faixa estreita (o IQR vai de 59,81 a
61,53), enquanto `sem-ia` varia mais (IQR de 55,05 a 64,39). O IQR esconde
extremos em `com-ia` (51,85 a 64,31 no total, nos trials de Carlos e
Gabriela), então a homogeneidade é do "miolo" do grupo, não de todos os
trials. Com N=3 isso é uma observação para gerar hipótese, não um achado.

**Por que MI não acompanha a queda de `cc_media`.** Pela fórmula do MI
(171 − 5,2·ln(volume de Halstead) − 0,23·CC − 16,2·ln(LOC), reescalada para
0–100), a complexidade ciclomática entra com peso pequeno; volume e LOC
dominam. Uma diferença de ~2 pontos em `cc_media` mexe pouco no MI, e a
correlação de Spearman `loc` × `mi` nos 18 trials é **−0,54** — parte da
relação de MI com o tamanho é mecânica. Por isso MI precisa ser lido
junto de `loc`, não no lugar de `cc`/duplicação.

## `loc` como controle — lado a lado com `cc` e duplicação

Motivo do controle (enunciado, `01-desenho-experimento.md`): código de IA
poderia só ser mais verboso, sem ser mais complexo de verdade.

| Integrante | `loc` com-ia | `loc` sem-ia | `cc_media` com-ia | `cc_media` sem-ia |
|---|---:|---:|---:|---:|
| brenda | 18 | 20 | 2,75 | 6,00 |
| carlos | 18 | 18 | 6,00 | 6,00 |
| gabriela | 18 | 21 | 4,00 | 9,00 |

- `loc` (Wilcoxon, controle, não é hipótese): W=0,00, p=0,5000; bootstrap
  IC 95% da diferença de mediana **[−5,00 ; +1,00]** — inclui zero.
- **Spearman entre os 18 trials:** `loc` × `cc_media` = −0,10;
  `loc` × `cc_max` = 0,11; `loc` × `duplicacao_pct` = 0,02.

**Leitura.** A hipótese de "IA só gera código mais verboso" **não se
sustenta nesta amostra**: `com-ia` não é maior (mediana 18 contra 20, se
algo, ligeiramente menor). E como `loc` praticamente não se correlaciona
com `cc_media`, a menor complexidade em `com-ia` **não parece ser mero
efeito de tamanho** — os dois pontos abaixo mostram o padrão:

- Carlos: mesmo `loc` (18 = 18) e mesma `cc_media` (6,00 = 6,00) nos dois
  tratamentos — a IA não mudou nem o tamanho nem a complexidade do código
  dele.
- Brenda e Gabriela: `loc` ligeiramente menor com IA (−2 e −3) e `cc_media`
  bem menor (−3,25 e −5,00) — a queda de complexidade é maior que a de
  tamanho.

Ressalva: a diferença de `loc` é de 2 a 3 linhas em arquivos de 18 a 21
linhas, e o IC inclui zero; controle "não mostra verbosidade", não "prova
que não existe".

## Conclusão de RQ3

| Variável | Resultado | Leitura |
|---|---|---|
| `cc_media` | p=0,5000, r=−1,00, IC [−5,00 ; 0,00] | direção a favor de `com-ia`, sem significância possível (N=3 com empate) |
| `duplicacao_pct` | não computável | sem variação; 1 trial de 18 com duplicação (sem-ia) |
| `mi` | p=1,0000, r=0,00, IC [−12,63 ; +6,48] | sem efeito direcional; IQR menor em `com-ia` (observação, não achado) |
| `loc` (controle) | p=0,5000, IC [−5,00 ; +1,00] | `com-ia` não é mais verboso |

O que este desenho consegue dizer sobre RQ3 é descritivo: código `com-ia`
teve complexidade ciclomática menor sem ser mais longo, e não há evidência
de diferença em duplicação nem em manutenibilidade. Nenhum dos testes
formais pode ser significativo com 3 pares — limitação já prevista como
ameaça de conclusão #4 em [`docs/03-ameacas-validade.md`](../docs/03-ameacas-validade.md).
Os gráficos do dashboard (incluindo o de MI) ficam na Issue #123.
