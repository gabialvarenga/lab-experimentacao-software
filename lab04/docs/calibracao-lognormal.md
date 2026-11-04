# Lab04 — Calibração da simulação: por que a lognormal

Justificativa da distribuição usada na simulação de referência (cenário C1, item c do enunciado) e os parâmetros estimados dos dados reais. As colunas dos arquivos citados estão em [dicionario-dados.md](dicionario-dados.md); o código, em `lab04/descritiva.py` e `lab04/calibracao.py`. Tudo se reproduz com `python -m lab04 calibrar`.

Siglas: PR (*Pull Request*); IC (intervalo de confiança); IQR (amplitude interquartil); QQ (quantil-quantil).

## 1. O que os dados mostram

Horas até o merge, 30 PRs por grupo (`dados/reais/descritiva.csv`):

| Grupo | n | Mediana | IQR | Média | Máximo | Assimetria | Outliers (> Q3 + 1,5 × IQR) |
|---|---|---|---|---|---|---|---|
| `com_bot` | 30 | 17,8 h | 50,4 h | 38,7 h | 251,6 h | 2,34 | 2 (6,7%) |
| `sem_bot` | 30 | 17,2 h | 55,4 h | 189,8 h | 4.053,6 h | 5,25 | 3 (10,0%) |

Nos dois grupos a média fica bem acima da mediana, a assimetria é positiva e forte, e os outliers estão todos na cauda direita. Um único PR do grupo sem bot, com 4.053,6 h (cerca de 169 dias), puxa a média do grupo para 189,8 h. Os dois grupos têm medianas muito próximas (17,8 h e 17,2 h), bem diferentes das medianas da sondagem do protocolo (21,3 h e 4,5 h), que usou outra amostra.

## 2. Por que a lognormal

Tempos até um evento são positivos e de cauda longa. A lognormal é a escolha natural: se log(horas) é normal, as horas são positivas, têm mediana e^μ e assimetria positiva, e basta estimar μ e σ. Os dados confirmam o que o descritivo sugere:

| Grupo | Shapiro-Wilk em horas (p) | Correlação do QQ-plot em horas | Shapiro-Wilk em log(horas) (p) | Correlação do QQ-plot em log(horas) | Assimetria de log(horas) |
|---|---|---|---|---|---|
| `com_bot` | 7 × 10⁻⁷ | 0,814 | 0,135 | 0,980 | 0,23 |
| `sem_bot` | 3 × 10⁻¹¹ | 0,480 | 0,113 | 0,970 | 0,92 |

Em horas, a normalidade é rejeitada com folga nos dois grupos. Em log(horas), não é rejeitada (p ≥ 0,05), a correlação do QQ-plot sobe para 0,97 ou mais e a assimetria cai (de 2,34 para 0,23 e de 5,25 para 0,92). O QQ-plot está em [qqplot-lognormal.html](qqplot-lognormal.html): um painel por grupo, quantis da normal no eixo x e horas observadas no eixo y em escala log. Quanto mais perto da reta tracejada (a lognormal ajustada), melhor o ajuste.

**Limites do ajuste.** O grupo `sem_bot` se ajusta pior que o `com_bot`:

- O maior valor (4.053,6 h) está 1,65 unidades de log acima da reta: a cauda direita é mais pesada que a lognormal prevê. A assimetria de 0,92 em log(horas) vai no mesmo sentido.
- Os menores valores dos dois grupos ficam acima da reta (0,9 a 1,1 unidades de log no menor ponto). É efeito do critério do protocolo: só entram PRs com mais de 1 h até o merge, então a cauda esquerda é cortada e a lognormal ajustada atribui probabilidade a tempos que a amostra não contém.
- Com n = 30 o Shapiro-Wilk tem pouco poder, então "não rejeitar" (p = 0,11 e 0,14) não prova a lognormal; o resultado quer dizer que os dados não a contradizem de forma clara. Como o enunciado pede uma distribuição realista, e não exata, o ajuste serve para a calibração.

O ajuste é registrado em `calibracao.json` (campos `ajuste`); se um dia ele ficar ruim (`bom = false`), a calibração segue e o problema aparece ali.

## 3. Parâmetros estimados

`dados/reais/calibracao.json`, IC de 95%:

| Grupo | μ (log h) | IC de μ | σ (log h) | IC de σ (qui-quadrado) | IC de σ (bootstrap) | Mediana implícita e^μ |
|---|---|---|---|---|---|---|
| `com_bot` | 2,674 | 2,122 a 3,226 | 1,479 | 1,178 a 1,988 | 1,179 a 1,699 | 14,5 h |
| `sem_bot` | 3,026 | 2,352 a 3,699 | 1,804 | 1,437 a 2,425 | 1,236 a 2,294 | 20,6 h |

- O valor central (`mu` e `sigma`) é o que entra na simulação de referência (C1); o σ dos dois grupos fica em torno de 1,5 a 1,8, bem acima do σ = 1 usado no teste de tempo de execução citado em [cenario.md](cenario.md).
- Os IC de σ são largos (n = 30): 1,18 a 1,99 e 1,44 a 2,43. Os dois métodos dão o mesmo limite inferior no `com_bot` (1,18), mas o bootstrap é mais curto no superior (1,70 contra 1,99), e no `sem_bot` é mais curto nos dois (1,24 a 2,29 contra 1,44 a 2,43). A reamostragem de 30 valores não cria valores maiores que os observados, e o IC por qui-quadrado supõe log(horas) normal, que é a hipótese da própria lognormal. Por isso o IC por qui-quadrado é o IC de referência, e o bootstrap é só uma conferência.
- A mediana implícita (14,5 h e 20,6 h) fica abaixo da mediana observada no `com_bot` (17,8 h) e acima dela no `sem_bot` (17,2 h). A diferença vem da amostra pequena e do ajuste imperfeito da seção 2, e os ICs de μ dos dois grupos se sobrepõem em grande parte.

## 4. Decisões e casos de borda

| Tema | Decisão |
|---|---|
| Horas = 0 (log indefinido) | Se um grupo tiver alguma hora ≤ 0, soma-se um piso de 0,01 h (cerca de 36 s) a todas as horas do grupo antes do log; o piso usado fica em `piso_somado`. Nos dados reais é 0, porque o protocolo só admite PRs com mais de 1 h até o merge |
| Horas negativas ou ausentes | Erro nos dados: `ValueError` |
| Grupo com poucos PRs | Menos de 3 PRs: erro (não há σ com IC nem teste de normalidade). Entre 3 e 9: calcula, e o campo `aviso` registra que a estimativa é muito imprecisa |
| Ajuste ruim | Registrado em `ajuste.bom`; a calibração segue |
| Semente do bootstrap | A de `config.yaml` (42), compartilhada pelos dois grupos em ordem, para o JSON se reproduzir |
