# Lab05 — Análise do piloto e número de repetições

Análise da coleta piloto (S01-08) com o código da análise, e escolha do número de repetições da coleta completa. Documento da Issue S01-09, escrito em 19/11/2026; a seção 9 (Q3 e análise pareada por bloco) foi acrescentada na S02-01, em 23/11/2026. As regras vêm do [plano de análise](plano-analise.md); as decisões que ele manda registrar no piloto estão no adendo de 19/11/2026, na seção 9 dele.

> **O resultado do piloto não é conclusão.** Com 5 repetições, as comparações servem só para conferir que o código roda. O piloto decide duas coisas: o teste principal de cada métrica (regra 5.1 do plano) e o número de repetições. Os dados do piloto **não entram** na análise final.

Siglas: CV (coeficiente de variação); IC (intervalo de confiança); IQR (*Interquartile Range*); n (repetições por combinação, isto é, execuções de cada servidor em cada combinação de `io_threads` e carga).

## 1. Dados e comando

- Entrada: [`dados/piloto/piloto.csv`](../dados/piloto/piloto.csv), 60 execuções (2 servidores × 2 níveis de `io_threads` × 3 cargas × 5 repetições), validadas sem erros ([relatório de qualidade](../dados/piloto/qualidade-piloto.md)).
- Comando, a partir de `lab05/` (cerca de 3 minutos, sem Docker):

```bash
python -m lab05 analisar --piloto
```

- Saídas em [`dados/piloto/analise/`](../dados/piloto/analise/): as tabelas em CSV e o [registro](../dados/piloto/analise/registro-analise.md), com o hash do CSV de entrada, os parâmetros e o ambiente. Os parâmetros (5%, α = 0,05, 80% de poder, 10.000 reamostragens do *bootstrap*, 2.000 simulações por ponto) ficam no bloco `analise` do `config.yaml`.
- Código: `descritiva.py`, `testes.py` e `poder.py` em `lab05/lab05/`. O código copiado do Lab04 (`lab04/lab04/descritiva.py`, `testes.py`, `simulacao.py` e `gerador.py`) tem a origem citada no topo de cada módulo.

## 2. Descritiva

Mediana, IQR e CV por combinação e métrica estão em [`descritiva.csv`](../dados/piloto/analise/descritiva.csv) e na tabela do relatório de qualidade. Em resumo, o CV das 12 combinações:

| Métrica | CV mínimo | CV mediano | CV máximo | *Outliers* (contados, não removidos) |
|---|---|---|---|---|
| `ops_s` | 8,6% | 11,9% | 15,8% | 1 |
| `lat_p50_ms` | 9,2% | 12,6% | 14,9% | 3 |
| `lat_p99_ms` | 7,6% | 14,5% | 18,5% | 4 |
| `memoria_bytes` | 0,0% | 0,0% | 0,0% (≤ 0,04%) | 6 |

Na vazão e nas latências, o ruído está acima do alerta de 10% do plano (seção 4) em quase todas as combinações. A causa provável, investigada no S01-08 ([LEIA-ME do piloto](../dados/piloto/LEIA-ME.md)), é uma deriva da máquina **entre blocos**: no bloco 2 (20h21 às 20h32), todas as combinações ficaram cerca de 16% mais lentas. A memória é quase constante; os seus *outliers* são diferenças de poucos quilobytes, sem importância prática.

## 3. Teste principal de cada métrica (regra 5.1)

Por métrica, os resíduos de todas as combinações (cada observação menos a mediana da sua combinação, 60 por métrica) foram juntados e testados:

| Métrica | Shapiro-Wilk p | Assimetria | Teste principal | Motivo |
|---|---|---|---|---|
| `ops_s` | 0,0008 | 0,74 | **Mann-Whitney** | Shapiro-Wilk rejeita a normalidade |
| `lat_p50_ms` | < 0,0001 | 1,20 | **Mann-Whitney** | Shapiro-Wilk rejeita; assimetria > 1 |
| `lat_p99_ms` | < 0,0001 | 1,06 | **Mann-Whitney** | Shapiro-Wilk rejeita; assimetria > 1 |
| `memoria_bytes` | < 0,0001 | 3,01 | **Mann-Whitney** | Shapiro-Wilk rejeita; assimetria > 1 |

- **Critério visual (histograma).** Os resíduos relativos (dividindo pela mediana da combinação) têm um pico central e caudas pesadas, sem dois picos separados. Os pequenos grupos nas pontas, no lado da lentidão (vazão mais baixa e latência mais alta, acima de 18%), vêm quase todos do bloco 2: 6 de 7 na `ops_s` e na `lat_p50_ms`, e 6 de 8 na `lat_p99_ms`. Não são dois regimes de um servidor, e sim a deriva já explicada, que atinge os dois servidores igualmente. O plano pede investigar a causa de uma bimodalidade antes da coleta, e isso foi feito no S01-08.
- **Conferência no logaritmo.** Os resíduos em log, que põem as combinações na mesma escala, também rejeitam a normalidade (p = 0,022, 0,039 e 0,007 para `ops_s`, `lat_p50_ms` e `lat_p99_ms`). A decisão não depende da escala.
- **Decisão registrada:** o **Mann-Whitney** é o teste principal das quatro métricas, com a **razão de medianas** como efeito de destaque. O Welch é sempre calculado e reportado como sensibilidade, sem entrar na correção de Holm. Era a expectativa do plano para a `lat_p99_ms`; a `ops_s` também caiu no Mann-Whitney.

## 4. Testes no piloto (conferência do código)

As 24 comparações Valkey × Redis (4 métricas × 6 combinações) rodaram sem erro, com os dois testes, o g de Hedges, o delta de Cliff, a razão de medianas com IC por *bootstrap*, o Levene e a situação da seção 6 do plano ([`comparacoes.csv`](../dados/piloto/analise/comparacoes.csv)). O que o piloto mostra sobre o código e o desenho, sem valor de conclusão:

- Os dois testes concordaram nas 24 comparações.
- Com 5 repetições, o menor p-valor possível do Mann-Whitney exato é 0,0079; com Holm sobre 6 comparações, ele vira 0,048, no limite de α. Por isso o piloto não tem poder para quase nada, como esperado.
- Com 1 *thread*, os IC de 95% da razão de medianas vão de cerca de 0,71 a 1,46 (de 25% a menos a 45% a mais): todas as comparações saem "inconclusivo".
- A memória tem IC praticamente fechado (variação de poucos quilobytes em 15 a 17 MB): o *bootstrap* e o Mann-Whitney funcionam nela, sem precisar do caso "determinística" do plano.

## 5. Número de repetições por simulação de poder

**Método.** Motor de simulação do Lab04 adaptado (`poder.py`):

1. O σ de log(métrica) de cada combinação é estimado no piloto, juntando os dois servidores pela regra do Lab04 (raiz da média das variâncias). Usa-se a variabilidade **bruta**, como o S01-08 deixou registrado.
2. Para cada n de uma grade (5 a 300), são simuladas 2.000 famílias de 6 comparações, com amostras lognormais e o σ de cada combinação. Na comparação avaliada, o Valkey tem mediana 5% acima da do Redis.
3. Em cada família simulada são aplicados o teste principal (Mann-Whitney) e a correção de Holm, como na análise.
4. **Cenário de Holm conservador:** só a comparação avaliada tem a diferença, e as outras 5 não têm efeito. É o pior caso de Holm, em que a comparação precisa vencer o limiar α/6 sozinha.
5. O poder de uma métrica num n é o da **pior** das 6 comparações, porque o n precisa bastar para a combinação mais ruidosa. O intervalo de Wilson de cada taxa está em [`curva-poder.csv`](../dados/piloto/analise/curva-poder.csv).

**Repetições necessárias para detectar 5% com 80% de poder** ([`repeticoes.csv`](../dados/piloto/analise/repeticoes.csv)):

| Variabilidade | Cenário de Holm | `ops_s` | `lat_p50_ms` | `lat_p99_ms` | `memoria_bytes` |
|---|---|---|---|---|---|
| **Bruta (principal)** | **Conservador** | **300** | **250** | **> 300** | **5** |
| Bruta | Todas as 6 com 5% (otimista) | 200 | 200 | 250 | 5 |
| Sem a deriva entre blocos (sensibilidade) | Conservador | 100 | 100 | 150 | 5 |

Em todas as linhas, a comparação limitante da vazão e das latências é a carga `misto` com 1 *thread*, a combinação mais ruidosa do piloto. Com o n inicial do planejamento (30), o poder para 5% seria de apenas 5% a 8%.

## 6. O caso de borda: 5% não cabe no tempo da S02

**Tempo disponível.** Na S02, a máquina designada pode ficar ligada de 8 a 10 horas para a coleta. No piloto, cada execução levou 0,99 min (60 execuções em 59,4 min); um bloco com as 12 combinações leva cerca de 12 min. Com 250 a 300 repetições, seriam de 50 a 60 horas. Mesmo o cenário mais otimista (sem a deriva entre blocos) pede de 100 a 150 repetições (20 a 30 horas).

**As saídas que a Issue prevê:**

- **Aumentar a duração de cada execução não resolve.** O ruído vem da deriva da máquina entre um bloco e o seguinte, e não do ruído dentro de cada execução (S01-08): uma medição mais longa não remove a deriva e deixa cada bloco mais lento.
- **Cortar uma carga ajuda, mas muda o escopo.** Sem a `misto`, o bloco cai para 8 execuções (cerca de 8 min), a família de Holm cai para 4 comparações e sai a combinação mais ruidosa. É uma decisão sobre as perguntas do estudo, e não só sobre o tempo.

**Opções avaliadas.** Variabilidade bruta e Holm conservador; diferença detectável é a menor diferença com 80% de poder, em passos de 1 ponto percentual ([`diferenca-detectavel.csv`](../dados/piloto/analise/diferenca-detectavel.csv)):

| Opção | Execuções | Coleta | Diferença detectável (`ops_s` / `lat_p50_ms` / `lat_p99_ms`) | Folga em 10 h |
|---|---|---|---|---|
| **A. 3 cargas, n = 40 (escolhida)** | 480 | ~7,9 h | **14% / 13% / 16%** | ~2 h |
| B. 3 cargas, n = 45 | 540 | ~8,9 h | 13% / 12% / 15% | ~1 h |
| C. Sem `misto`, n = 60 | 480 | ~7,9 h | 10% / 9% / 10% | ~2 h |
| D. Sem `misto`, n = 75 | 600 | ~9,9 h | 8% / 8% / 9% | nenhuma |

A memória detecta 5% com qualquer n das opções. As linhas C e D foram calculadas com as mesmas funções, filtrando a carga `misto` do piloto:

```python
import pandas as pd
from lab05 import poder
df = pd.read_csv("dados/piloto/piloto.csv")
sem_misto = df[df["carga"] != "misto"]
curva = poder.curva_poder(sem_misto, "ops_s", (40, 60, 75), [x / 100 for x in range(5, 21)], "mann_whitney", 2000)
print(poder.diferenca_detectavel(curva))
```

**Decisão: 40 repetições por combinação, com as três cargas (opção A).** Justificativa:

1. É o maior n que cabe no limite inferior da janela (8 h). Sobram cerca de 2 h para os 10 minutos de máquina ociosa do protocolo e para repetir execuções que falharem.
2. A opção B ganha só 1 ponto percentual de diferença detectável e deixa cerca de 1 h de folga.
3. As opções C e D detectam diferenças menores, mas tiram a carga `misto` das perguntas Q1 a Q4. Manter o escopo do estudo foi preferido a ganhar precisão.

**O que a decisão significa para a análise final:**

- Com 40 repetições, o estudo tem 80% de poder para diferenças a partir de cerca de **14% na vazão, 13% no p50 e 16% no p99**, e de 5% na memória. Abaixo disso, uma diferença real pode sair "inconclusiva" (erro tipo II). O critério de relevância (5%) e a correção de Holm **não mudam**: muda o que se pode esperar detectar.
- Pelo que o piloto sugere, sem valor de conclusão, as diferenças com 4 *threads* (40% a 60%) e na memória (cerca de 13%) estão acima desses limites. Com 1 *thread*, as diferenças observadas (de cerca de 3% a 14%, a maior na `misto`) estão abaixo ou perto deles.
- A expectativa de **empate técnico com 1 *thread*** ([cenario.md](cenario.md), seção 7) dificilmente será confirmada. A equivalência prática exige o IC inteiro dentro de [0,95; 1,05], o que pede muito mais repetições do que as disponíveis. O resultado mais provável nessas comparações é "inconclusivo", e o relatório deve dizer isso dessa forma, sem tratar "não rejeitar H₀" como empate.
- A S02 deve repetir o cálculo da diferença detectável com o σ observado na coleta completa (o mesmo `analisar`) e reportá-la junto dos resultados. Os ajustes do protocolo depois do piloto (nenhum outro contêiner, 10 minutos de ociosidade, modo de energia conferido) podem reduzir a deriva; nesse caso, a diferença detectável real fica menor que a desta tabela.

## 7. Limitações desta estimativa

- **σ estimado com 5 execuções por servidor.** Cada σ tem 8 graus de liberdade, e o seu IC de 95% vai de cerca de 0,7 a 1,9 vez o valor estimado. Tomar o pior das 6 combinações protege contra subestimar, mas o número de repetições necessário é uma ordem de grandeza, e não um valor exato.
- **Modelo lognormal com o mesmo σ nos dois servidores.** É o modelo do Lab04, coerente com métricas de razão; o piloto não tem tamanho para testar um modelo melhor. A simulação também não reproduz a deriva entre blocos como estrutura: ela entra só como variância.
- **Grade de n e de diferenças.** O n necessário é o menor da grade com 80% de poder (por exemplo, 300 para a `ops_s` pode ser algo entre 251 e 300), e as diferenças detectáveis estão em passos de 1 ponto percentual.
- **Q3 fora deste cálculo.** O número de repetições foi calculado para as comparações das Q1, Q2 e Q4. A interação da Q3 (S02-06) compara 4 células e tem menos poder com o mesmo n; a S02-06 deve reportar a sua própria diferença detectável.

## 8. O que mudou com esta Issue

- `config.yaml`: `plano.repeticoes` de 30 para **40**; novo bloco `analise`.
- [planejamento.md](planejamento.md), seções 3.3, 6.4 e 7: repetições, tempo da coleta completa e o caso de borda.
- [plano-analise.md](plano-analise.md), seção 9: adendo de 19/11/2026 com o teste principal por métrica, o número de repetições, o cenário de Holm da simulação e as pendências que passam para a S02.
- `README.md`: subcomando `analisar` e o tamanho da coleta completa.

## 9. Q3 e análise pareada por bloco (S02-01)

Seção acrescentada em 23/11/2026, antes da coleta completa (S02-02), para decidir o método da Q3 e propor a análise pareada por bloco. As decisões estão no adendo de 23/11/2026 do [plano de análise](plano-analise.md), seção 9. O comando é o mesmo (`python -m lab05 analisar --piloto`, agora cerca de 5 minutos). Saídas novas: [`q3.csv`](../dados/piloto/analise/q3.csv), [`pareada.csv`](../dados/piloto/analise/pareada.csv) e a coluna `analise` em [`diferenca-detectavel.csv`](../dados/piloto/analise/diferenca-detectavel.csv). Código em `q3.py`, `pareada.py` e `poder.py` (`curva_poder_pareada`).

### 9.1 Método da Q3 (regra 5.1 nos resíduos do modelo)

Resíduos do modelo de dois fatores no log, por carga (log da métrica menos a média da sua célula servidor × `io_threads`), juntados por métrica (60 cada):

| Métrica | Shapiro-Wilk p | Assimetria | Levene p (menor das 3 cargas) | Shapiro-Wilk p com o bloco no modelo | Método |
|---|---|---|---|---|---|
| `ops_s` | 0,0035 | −0,43 | 0,78 | 0,93 | **ART-ANOVA** |
| `lat_p99_ms` | 0,0032 | 0,52 | 0,45 | 0,72 | **ART-ANOVA** |

- A normalidade falha; as variâncias e a assimetria passam. Com o bloco (`repeticao`) no modelo, os resíduos ficam normais: o que quebra a normalidade é a deriva entre blocos, a mesma da seção 2.
- **Decisão registrada:** ART-ANOVA como principal nas duas métricas; ANOVA no log com o bloco como sensibilidade.

Resultado no piloto, **só para conferir que o código roda** (5 repetições por célula):

| Métrica | Carga | R (razão das razões) | IC de 95% | p interação (ART) | p Holm | η² parcial | p com bloco | Situação |
|---|---|---|---|---|---|---|---|---|
| `ops_s` | get | 1,40 | [1,06; 2,07] | 0,0040 | 0,0040 | 0,41 | < 0,0001 | diferença relevante |
| `ops_s` | misto | 1,78 | [1,20; 2,42] | 0,0004 | 0,0007 | 0,56 | < 0,0001 | diferença relevante |
| `ops_s` | set | 1,54 | [1,20; 2,19] | 0,0002 | 0,0006 | 0,59 | < 0,0001 | diferença relevante |
| `lat_p99_ms` | get | 0,71 | [0,48; 0,95] | 0,0029 | 0,0029 | 0,43 | < 0,0001 | inconclusivo |
| `lat_p99_ms` | misto | 0,54 | [0,39; 0,80] | 0,0002 | 0,0006 | 0,59 | < 0,0001 | diferença relevante |
| `lat_p99_ms` | set | 0,65 | [0,43; 0,87] | 0,0009 | 0,0018 | 0,51 | < 0,0001 | diferença relevante |

O código roda nas duas métricas, e a ART e a ANOVA com bloco concordam em todas as cargas. O modelo com bloco tem p muito menores, porque tira a deriva dos resíduos. Os valores de R não são conclusão.

### 9.2 Análise pareada por bloco no piloto

As 24 comparações (4 métricas × 6 combinações) rodaram, com 5 pares cada e nenhum par excluído (o piloto não teve falhas). Com 5 pares, o menor p possível do Wilcoxon pareado é 0,0625 e o IC de Hodges-Lehmann cobre no máximo 93,75%. Por isso **todas as comparações pareadas saem "inconclusivo"**, como esperado.

Em 13 das 24 comparações, a situação coincide com a do Mann-Whitney. As 11 diferentes são as que o Mann-Whitney marca como "diferença relevante" (com 4 *threads* e na memória), que a pareada não alcança com 5 pares. Mesmo assim, o IC de Hodges-Lehmann já sai mais estreito que o do *bootstrap* independente: por exemplo, `ops_s` com 1 *thread* e carga `get` dá [0,93; 1,16] na pareada, contra [0,78; 1,34] na independente.

### 9.3 Diferença detectável da análise pareada

A simulação é a mesma da seção 5, agora para o Wilcoxon pareado:

- log das razões normal, com σ_par = √2 · σ, sendo σ o de log de cada combinação **sem a deriva entre blocos**;
- Holm no cenário conservador;
- poder da pior das 6 comparações;
- 2.000 simulações por ponto.

Menor diferença com 80% de poder, em passos de 1 ponto percentual:

| Métrica | Análise | n = 30 | **n = 40** | n = 45 | n = 50 | n = 60 |
|---|---|---|---|---|---|---|
| `ops_s` | independente (Mann-Whitney, bruta) | 16% | **14%** | 13% | 12% | 11% |
| `ops_s` | pareada (Wilcoxon, sem a deriva) | 10% | **9%** | 8% | 8% | 7% |
| `lat_p50_ms` | independente | 15% | **13%** | 12% | 12% | 11% |
| `lat_p50_ms` | pareada | 9% | **8%** | 7% | 7% | 6% |
| `lat_p99_ms` | independente | 18% | **16%** | 15% | 14% | 13% |
| `lat_p99_ms` | pareada | 13% | **11%** | 10% | 10% | 9% |
| `memoria_bytes` | as duas | 5% | **5%** | 5% | 5% | 5% |

- Com as 40 repetições já fixadas, a pareada detecta diferenças cerca de um terço menores que a análise independente. Na vazão e nas latências, ainda fica acima do limiar de 5%.
- **Conferência do σ_par:** o desvio do log das razões medido direto nos pares do piloto (coluna `desvio_log_razao` de `pareada.csv`) tem máximos de 0,108 (`ops_s`), 0,099 (`lat_p50_ms`) e 0,144 (`lat_p99_ms`). São valores abaixo dos σ_par da simulação (0,132, 0,121 e 0,170), então a estimativa é conservadora.
- As limitações da seção 7 também valem aqui: σ estimado com 5 execuções e modelo lognormal com o mesmo σ nos dois servidores.

### 9.4 O que mudou com a S02-01

- `config.yaml`: no bloco `analise`, as decisões fixas `teste_principal` (Mann-Whitney nas quatro métricas) e `metodo_q3` (ART nas duas), que o `analisar` usa na coleta completa.
- `requirements.txt`: `statsmodels`.
- Código: `q3.py` e `pareada.py`, novos; `poder.py` (`curva_poder_pareada`); `analise.py` (saídas novas e as decisões fixas). Testes em `tests/test_q3.py`, `tests/test_pareada.py`, `tests/test_poder.py` e `tests/test_analise.py`.
- Saídas do piloto: `q3.csv` e `pareada.csv`, novos; colunas novas em `teste-principal.csv` (`teste_usado`, `origem`) e em `diferenca-detectavel.csv` (`analise`); seções novas no registro. As demais tabelas não mudaram.
- [plano-analise.md](plano-analise.md), seção 9: adendo de 23/11/2026.
