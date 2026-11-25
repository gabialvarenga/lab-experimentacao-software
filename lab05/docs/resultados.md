# Lab05 — Resultados das Q1 a Q4

Este documento traz as respostas às perguntas Q1 (vazão), Q2 (latência de cauda), Q3 (interação servidor × `io_threads`) e Q4 (memória) com a coleta completa. As regras usadas são as do [plano de análise](plano-analise.md), seções 5 e 6, e dos adendos de 19/11 e 23/11. A expectativa é a do [cenário](cenario.md), seção 7. Documento das Issues S02-06 (Q1, Q2 e Q4) e S02-07 (Q3, seção 6).

O impacto prático dos resultados fica para a Sprint 03.

## 1. Dados e comando

| Item | Valor |
|---|---|
| Coleta | [`dados/brutos/execucoes.csv`](../dados/brutos/execucoes.csv): 480 execuções (2 servidores × 2 níveis de `io_threads` × 3 cargas × 40 repetições), descritas no [LEIA-ME](../dados/brutos/LEIA-ME.md) |
| SHA-256 do CSV (LF) | `e7ce9d81f951928c63f2ddd14579e659fe18ae91d797cc3d0a55d3e78355234d` |
| Servidores | Redis 8.10.3 × Valkey 9.1.3 |
| Comando (a partir de `lab05/`) | `python -m lab05 analisar` (cerca de 4 min, determinístico, semente 42) |
| Saídas | [`dados/brutos/analise/`](../dados/brutos/analise/): `comparacoes.csv`, `pareada.csv`, `descritiva.csv`, `diferenca-detectavel.csv`, `q3.csv`, `q3-curva-poder.csv`, `q3-diferenca-detectavel.csv` e [`registro-analise.md`](../dados/brutos/analise/registro-analise.md) |
| Figuras | [`apresentacao.html`](../dados/brutos/analise/figuras/apresentacao.html) (S02-05). O G3 mostra as razões desta análise |

## 2. Como ler as tabelas

- **Razão:** Valkey ÷ Redis, calculada sobre as medianas das 40 execuções de cada lado. O IC é de 95%, por *bootstrap*. Na vazão, razão maior que 1 favorece o Valkey; na latência e na memória, razão menor que 1 favorece o Valkey.
- **Teste principal:** Mann-Whitney nas quatro métricas (adendo de 19/11, item 1). A regra 5.1, aplicada de novo à coleta completa, deu o mesmo teste em todas ([`teste-principal.csv`](../dados/brutos/analise/teste-principal.csv)).
- **p Holm:** p ajustado pela correção de Holm entre as 6 comparações de cada pergunta (cada pergunta é uma família).
- **Teste de sensibilidade:** o Welch concordou com o Mann-Whitney nas 24 comparações (`testes_discordam` falso em todas).
- **Situação:** segue a seção 6 do plano, com o limiar de 5%.

| Situação | Quando |
|---|---|
| Diferença relevante | p Holm < 0,05 e o IC inteiro fora de [0,95; 1,05] |
| Diferença pequena demais | p Holm < 0,05 e o IC inteiro dentro de [0,95; 1,05]: a diferença existe, mas fica abaixo de 5% |
| Equivalência prática | IC inteiro dentro de [0,95; 1,05], sem diferença significativa |
| Inconclusivo | IC cruzando 0,95 ou 1,05 |

- **Pareada (HL):** a razão de Hodges-Lehmann e a situação da análise pareada por bloco. A pareada é uma análise de sensibilidade (adendo de 23/11, item 3): não muda a conclusão, que segue o teste principal.

## 3. Q1 — A vazão difere entre os dois servidores?

Métrica: `ops_s`, em milhares de operações por segundo.

| `io_threads` | Carga | Mediana Redis | Mediana Valkey | Valkey ÷ Redis [IC 95%] | p Holm | δ de Cliff | g de Hedges | Situação | Pareada (HL) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | set | 88,0k | 86,7k | **0,986** [0,982; 0,991] | < 0,0001 | −0,78 (grande) | −1,08 | diferença pequena demais | 0,986, diferença pequena demais |
| 1 | get | 89,1k | 88,3k | **0,991** [0,987; 0,995] | 0,0005 | −0,47 (médio) | −0,76 | diferença pequena demais | 0,993, diferença pequena demais |
| 1 | misto | 88,3k | 87,6k | **0,993** [0,989; 0,996] | 0,0005 | −0,47 (médio) | −0,82 | diferença pequena demais | 0,993, diferença pequena demais |
| 4 | set | 142,4k | 232,4k | **1,632** [1,627; 1,638] | < 0,0001 | 1,00 (grande) | 57,37 | diferença relevante | 1,633, diferença relevante |
| 4 | get | 146,4k | 236,5k | **1,615** [1,608; 1,620] | < 0,0001 | 1,00 (grande) | 46,23 | diferença relevante | 1,614, diferença relevante |
| 4 | misto | 144,2k | 234,9k | **1,628** [1,623; 1,635] | < 0,0001 | 1,00 (grande) | 49,73 | diferença relevante | 1,630, diferença relevante |

**Interpretação.**

**Com 1 *thread* de E/S, o Valkey é mais lento que o Redis nas três cargas, mas a diferença é pequena demais para importar.** O Valkey fica de 0,7% a 1,4% abaixo. Os IC ficam inteiros entre 0,98 e 1,00, bem dentro da faixa de 5%. A diferença é estatisticamente real, porque o CV de cerca de 1% deixa o teste sensível a ela. Pela regra do plano, porém, ela fica abaixo do limiar de relevância.

**Com 4 *threads* de E/S, o Valkey entrega cerca de 62% a 63% mais vazão nas três cargas.** Os IC ficam entre 1,61 e 1,64. As 40 execuções do Valkey superam todas as 40 do Redis (δ = 1), e a diferença é relevante.

Os dois servidores ganham vazão com 4 *threads*, mas em proporções muito diferentes. A pergunta sobre essa interação é a Q3 (seção 6).

## 4. Q2 — A latência de cauda difere?

Métrica: `lat_p99_ms`, em ms.

| `io_threads` | Carga | Mediana Redis | Mediana Valkey | Valkey ÷ Redis [IC 95%] | p Holm | δ de Cliff | g de Hedges | Situação | Pareada (HL) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | set | 0,967 | 0,983 | **1,017** [1,000; 1,017] | 0,0005 | 0,48 (grande) | 0,75 | diferença pequena demais | 1,012, diferença pequena demais |
| 1 | get | 0,959 | 0,967 | **1,008** [0,996; 1,008] | 0,2551 | 0,19 (pequeno) | 0,29 | equivalência prática | 1,004, equivalência prática |
| 1 | misto | 0,967 | 0,975 | **1,008** [0,992; 1,008] | 0,3483 | 0,12 (negligível) | 0,15 | equivalência prática | 1,000, equivalência prática |
| 4 | set | 0,783 | 0,479 | **0,612** [0,612; 0,612] | < 0,0001 | −1,00 (grande) | −32,05 | diferença relevante | 0,614, diferença relevante |
| 4 | get | 0,767 | 0,471 | **0,614** [0,614; 0,625] | < 0,0001 | −1,00 (grande) | −40,34 | diferença relevante | 0,621, diferença relevante |
| 4 | misto | 0,775 | 0,479 | **0,618** [0,618; 0,618] | < 0,0001 | −1,00 (grande) | −31,53 | diferença relevante | 0,616, diferença relevante |

A `lat_p50_ms` é só descritiva (plano, seção 5.2). Os p abaixo são ajustados por Holm entre as 6 comparações do p50 e servem só de referência.

| `io_threads` | Carga | Mediana Redis | Mediana Valkey | Valkey ÷ Redis [IC 95%] | p Holm | δ de Cliff | Situação | Pareada (HL) |
|---|---|---|---|---|---|---|---|---|
| 1 | set | 0,543 | 0,551 | **1,015** [1,000; 1,015] | < 0,0001 | 0,63 (grande) | diferença pequena demais | 1,015, diferença pequena demais |
| 1 | get | 0,535 | 0,535 | **1,000** [1,000; 1,015] | 0,0068 | 0,31 (pequeno) | diferença pequena demais | 1,007, equivalência prática |
| 1 | misto | 0,535 | 0,543 | **1,015** [1,000; 1,015] | 0,0002 | 0,47 (médio) | diferença pequena demais | 1,007, diferença pequena demais |
| 4 | set | 0,311 | 0,191 | **0,614** [0,614; 0,614] | < 0,0001 | −1,00 (grande) | diferença relevante | 0,601, diferença relevante |
| 4 | get | 0,303 | 0,183 | **0,604** [0,604; 0,604] | < 0,0001 | −1,00 (grande) | diferença relevante | 0,609, diferença relevante |
| 4 | misto | 0,311 | 0,183 | **0,588** [0,588; 0,614] | < 0,0001 | −1,00 (grande) | diferença relevante | 0,601, diferença relevante |

**Interpretação.**

**Com 1 *thread* de E/S, o p99 dos dois servidores é equivalente na prática.**
- Nas cargas `get` e `misto`, o IC inteiro fica dentro de [0,95; 1,05] e o teste não rejeita H₀: é o caso de **equivalência prática**. Ela é afirmada pelo IC, e não apenas pela falta de significância.
- Na carga `set`, o p99 do Valkey é 1,7% maior (0,983 contra 0,967 ms). A diferença é significativa, mas pequena demais para ser relevante.

**Com 4 *threads* de E/S, o p99 do Valkey é cerca de 38% a 39% menor nas três cargas, e a diferença é relevante.** As distribuições não se sobrepõem (δ = −1).

O p50 segue o mesmo desenho: empate prático com 1 *thread* e cerca de 40% a menos no Valkey com 4 *threads*. Vazão maior e latência menor vêm juntas, como esperado num cliente com número fixo de conexões.

**Resolução da latência.** O cliente de carga reporta a latência em degraus de 0,008 ms, perto de 1% de um p99 em torno de 0,8 ms (plano, seção 8, armadilha 5). Por isso as medianas assumem poucos valores, e alguns IC por *bootstrap* da razão de medianas se reduzem a um ponto, como [0,612; 0,612]. Esses IC subestimam a incerteza. O IC de Hodges-Lehmann da pareada, que usa a razão de cada par, não tem esse problema, e mesmo assim chega às mesmas conclusões: com 4 *threads*, ele fica entre 0,611 e 0,624 no p99 ([`pareada.csv`](../dados/brutos/analise/pareada.csv)).

## 5. Q4 — O uso de memória difere?

Métrica: `memoria_bytes` (`used_memory` depois da pré-carga das 100.000 chaves), em MiB.

| `io_threads` | Carga | Mediana Redis | Mediana Valkey | Valkey ÷ Redis [IC 95%] | p Holm | δ de Cliff | g de Hedges | Situação | Pareada (HL) |
|---|---|---|---|---|---|---|---|---|---|
| 1 | set | 16,59 | 14,45 | **0,871** [0,871; 0,871] | < 0,0001 | −1,00 (grande) | −488,00 | diferença relevante | 0,871, diferença relevante |
| 1 | get | 16,62 | 14,48 | **0,871** [0,871; 0,871] | < 0,0001 | −1,00 (grande) | −564,14 | diferença relevante | 0,871, diferença relevante |
| 1 | misto | 16,62 | 14,48 | **0,871** [0,871; 0,871] | < 0,0001 | −1,00 (grande) | −412,20 | diferença relevante | 0,871, diferença relevante |
| 4 | set | 17,13 | 14,98 | **0,875** [0,875; 0,875] | < 0,0001 | −1,00 (grande) | −1226,61 | diferença relevante | 0,875, diferença relevante |
| 4 | get | 17,15 | 15,01 | **0,875** [0,875; 0,875] | < 0,0001 | −1,00 (grande) | −1081,79 | diferença relevante | 0,875, diferença relevante |
| 4 | misto | 17,15 | 15,01 | **0,875** [0,875; 0,875] | < 0,0001 | −1,00 (grande) | −1166,02 | diferença relevante | 0,875, diferença relevante |

**Interpretação.**

**O Valkey usa de 12,5% a 12,9% menos memória que o Redis para as mesmas 100.000 chaves, nas seis combinações.** Isso dá cerca de 2,1 MiB a menos. A medida quase não varia (CV de 0,02%), por isso os IC ficam praticamente num ponto. Os IC estão em 0,871 com 1 *thread* e 0,875 com 4 *threads*.

Com 4 *threads* de E/S, os dois servidores usam cerca de 0,53 MiB a mais: 558.800 bytes no Redis e 555.170 no Valkey, nas medianas da carga `get`. A diferença absoluta entre eles quase não muda, e a razão sobe um pouco só porque a base aumentou. A causa desse acréscimo não foi investigada (provavelmente estruturas por *thread*).

A carga muda a memória em menos de 0,03 MiB.

## 6. Q3 — A diferença entre os servidores depende das *threads* de E/S?

Métricas: `ops_s` e `lat_p99_ms`. A Q3 pergunta se passar de 1 para 4 *threads* muda a métrica na mesma proporção nos dois servidores. Em cada carga, o termo de interação servidor × `io_threads` é testado no logaritmo da métrica, com a **ART-ANOVA** (método fixado antes da coleta, adendo de 23/11, item 1). Código em `lab05/q3.py`; resultados em [`q3.csv`](../dados/brutos/analise/q3.csv).

- **R** é a razão das razões: (Valkey com 4 ÷ Valkey com 1) ÷ (Redis com 4 ÷ Redis com 1), calculada nas medianas. R = 1 é "sem interação". O IC de 95% vem de *bootstrap*, com as 4 células reamostradas separadamente.
- **p Holm:** p da interação ajustado entre as 3 cargas de cada métrica.
- **η² parcial:** parcela da variância (nos postos da ART) explicada pela interação, dado o resíduo.
- **Situação:** a mesma regra da seção 2, com R no lugar da razão de medianas: relevante se p Holm < 0,05 e o IC de R inteiro fora de [0,95; 1,05].

### 6.1 Resultado

Vazão (`ops_s`):

| Carga | Valkey 4 ÷ 1 | Redis 4 ÷ 1 | R [IC 95%] | p Holm | η² parcial | Situação |
|---|---|---|---|---|---|---|
| set | 2,68 | 1,62 | **1,655** [1,645; 1,664] | 5,2e-49 | 0,755 | diferença relevante |
| get | 2,68 | 1,64 | **1,630** [1,620; 1,637] | 1,2e-48 | 0,750 | diferença relevante |
| misto | 2,68 | 1,63 | **1,640** [1,632; 1,649] | 1,2e-48 | 0,751 | diferença relevante |

p99 (`lat_p99_ms`; menor é melhor, então R < 1 significa que as *threads* reduzem mais o p99 do Valkey):

| Carga | Valkey 4 ÷ 1 | Redis 4 ÷ 1 | R [IC 95%] | p Holm | η² parcial | Situação |
|---|---|---|---|---|---|---|
| set | 0,487 | 0,810 | **0,602** [0,602; 0,612] | 1,3e-49 | 0,759 | diferença relevante |
| get | 0,487 | 0,800 | **0,609** [0,609; 0,625] | 2,2e-49 | 0,755 | diferença relevante |
| misto | 0,491 | 0,801 | **0,613** [0,613; 0,623] | 2,2e-49 | 0,756 | diferença relevante |

**Interpretação.**

**Existe interação, e ela é grande, nas duas métricas e nas três cargas.** A diferença entre os servidores depende do uso de *threads* de E/S.

- **Vazão.** Passar de 1 para 4 *threads* multiplica a vazão do Valkey por cerca de 2,7 (+168%) e a do Redis por cerca de 1,6 (+62% a +64%). O ganho do Valkey é de 1,63 a 1,66 vez o do Redis. Isso é coerente com a Q1: com 1 *thread* os dois servidores empatam na prática (diferença de 0,7% a 1,4%), e com 4 o Valkey fica 62% a 63% acima.
- **p99.** Com 4 *threads*, o p99 do Valkey cai a cerca de metade do valor com 1 *thread* (−51%), e o do Redis cai a cerca de 80% (−20%). O R de 0,60 a 0,61 diz que a redução do Valkey é bem maior que a do Redis.
- **Relevância prática.** Os seis R ficam longe de [0,95; 1,05], e nenhum IC se aproxima da faixa. O caso "interação significativa, mas com R dentro da faixa de 5%" não ocorreu.
- **Concordância.** A ANOVA no log com o bloco (`repeticao`) concorda com a ART em todas as 6 linhas (`testes_discordam` falso). Os p dela (da ordem de 1e-110 a 1e-143) **não devem ser lidos como grandeza**, pelos motivos da seção 6.2: servem só para mostrar que a decisão não depende do método.

**Limites.**
- **IC do p99.** O limite inferior do IC de R coincide com o próprio R nas três cargas (0,602, 0,609, 0,613). É o efeito dos degraus de 0,008 ms do cliente, descrito na seção 4: as medianas assumem poucos valores, e o *bootstrap* da razão de medianas subestima a incerteza. A conclusão não depende dele, porque R fica a cerca de 40% de 1.
- **O estudo mede a interação, não a causa.** Ele não mostra por que o Redis ganha menos com 4 *threads*. A explicação do novo modelo de *threads* de E/S do Valkey é uma hipótese ([cenario.md](cenario.md), seção 7), e não um resultado. Se o cliente de carga limitar a vazão do Valkey com 4 *threads* (seção 10), o R real seria **maior** que o medido.

### 6.2 Pressupostos conferidos na coleta completa

A regra 5.1 foi aplicada aos resíduos do modelo de dois fatores no log (log da métrica menos a média da sua célula, por carga), juntados por métrica: 480 resíduos cada. A decisão do método **não é revista**: o adendo de 23/11 fixou a ART-ANOVA, e o `analisar` só registra o que a regra daria ([`registro-analise.md`](../dados/brutos/analise/registro-analise.md)).

| Métrica | Shapiro-Wilk p | Assimetria | Levene p (por carga: get / misto / set) | Regra dá | Usado |
|---|---|---|---|---|---|
| `ops_s` | 2,9e-24 | −1,96 | 0,122 / 0,888 / 0,145 | ART-ANOVA (Shapiro-Wilk rejeita; \|assimetria\| > 1) | ART-ANOVA |
| `lat_p99_ms` | 1,5e-20 | −0,30 | 0,196 / 0,670 / 0,551 | ART-ANOVA (Shapiro-Wilk rejeita) | ART-ANOVA |

- **A regra deu o mesmo método do piloto.** No piloto, o Shapiro-Wilk também rejeitou (p = 0,0035 e 0,0032), com assimetria dentro de ±1. Na coleta a rejeição é muito mais forte, e a `ops_s` passa a ter assimetria forte e negativa: há execuções ocasionais bem mais lentas que a mediana da célula.
- **Variâncias iguais.** O Levene não rejeita em nenhuma carga (menor p = 0,122 na vazão e 0,196 no p99). O que falha é a forma da distribuição, e não a igualdade das variâncias.
- **Com o bloco no modelo, a normalidade continua rejeitada.** No piloto, os resíduos da ANOVA com o bloco ficaram normais (p = 0,93 e 0,72), porque a deriva entre blocos era a causa da não normalidade. Aqui o Shapiro-Wilk com o bloco rejeita (p = 3,3e-19 na vazão e 1,8e-18 no p99, assimetria −0,88 e −0,77), e a deriva entre blocos quase não existe: a mediana relativa da `ops_s` por bloco vai de 0,994 a 1,004. A não normalidade da coleta vem das caudas dos próprios resíduos, e não da deriva. A causa das execuções lentas não foi investigada.
- **Consequência para a sensibilidade.** O caso de borda da issue previa pressupostos da ANOVA violados na coleta completa e não no piloto: ele ocorreu para a ANOVA com bloco. Como o adendo já manda a ART-ANOVA como principal, a análise segue como fixada. A ANOVA com bloco permanece como sensibilidade, com a ressalva de que ela própria viola o pressuposto, e por isso só a **decisão** dela (rejeitar a ausência de interação) é usada.

### 6.3 Diferença detectável da interação

O número de repetições do piloto foi calculado só para as comparações das Q1, Q2 e Q4 ([analise-piloto.md](analise-piloto.md), seção 7). Para a Q3, a simulação de poder foi feita agora, com a variabilidade da coleta completa ([`q3-diferenca-detectavel.csv`](../dados/brutos/analise/q3-diferenca-detectavel.csv) e [`q3-curva-poder.csv`](../dados/brutos/analise/q3-curva-poder.csv)).

**Método** (`q3.curva_poder_interacao`):
1. Em cada carga, o σ de log é o da coleta, juntando as 4 células (raiz da média das variâncias), com 40 execuções por célula.
2. As amostras são lognormais. Só a célula Valkey × 4 *threads* é deslocada, de modo que R = 1 + diferença.
3. A interação é testada com a ART-ANOVA, em 2.000 simulações por ponto, para diferenças de 0,5% a 10%.
4. Holm entre as 3 cargas, no cenário conservador (só a carga avaliada tem o efeito), como nas comparações das Q1, Q2 e Q4.
5. A diferença detectável é a menor da grade com poder de pelo menos 80%.

| Métrica | Carga | σ de log | R − 1 detectável com 80% de poder | Poder nesse ponto |
|---|---|---|---|---|
| `ops_s` | get | 0,009 | 1,0% | 82,4% |
| `ops_s` | misto | 0,009 | 1,0% | 82,7% |
| `ops_s` | set | 0,014 | 1,5% | 80,7% |
| `lat_p99_ms` | get | 0,012 | 1,5% | 90,1% |
| `lat_p99_ms` | misto | 0,013 | 1,5% | 87,7% |
| `lat_p99_ms` | set | 0,017 | 2,0% | 87,8% |

- **A coleta detecta uma interação de 1% a 2%.** O limiar de relevância do plano é 5%, e o poder já é de 100% a partir de 3,5% nas seis linhas ([`q3-curva-poder.csv`](../dados/brutos/analise/q3-curva-poder.csv)). A interação observada (R − 1 de cerca de 60% na vazão, e 1/R − 1 de cerca de 64% no p99) é dezenas de vezes maior que esse limite.
- **Nenhuma conclusão da Q3 depende de poder.** Não há resultado "inconclusivo" por falta de repetições. Vale o que a seção 7 diz para as outras perguntas: o ruído da coleta ficou bem abaixo do que o piloto previa.
- **Para o p99, o valor é um limite inferior.** A simulação supõe valores contínuos, e o cliente reporta o p99 em degraus de 0,008 ms (1% a 1,7% do valor nas células com 4 *threads*, perto de 0,47 a 0,8 ms). Uma interação de 1,5% a 2% está, portanto, no limite da resolução do cliente, e a diferença detectável real do p99 não deve ser lida como mais precisa que isso.
- **Escopo.** A grade de diferenças está em `q3.DIFERENCAS_DETECTAVEIS`, e não no `config.yaml`, porque o arquivo está congelado para a coleta (tag `lab05-coleta-congelada`).

## 7. Diferença detectável, recalculada com a coleta completa

O piloto previa, para 40 repetições e 80% de poder, uma diferença detectável de cerca de 14% na vazão, 13% no p50, 16% no p99 e 5% na memória na análise independente. Na análise pareada, a previsão era de 9%, 8%, 11% e 5% (adendos de 19/11 e 23/11). Com a variabilidade da coleta completa ([`diferenca-detectavel.csv`](../dados/brutos/analise/diferenca-detectavel.csv) e [`repeticoes.csv`](../dados/brutos/analise/repeticoes.csv)), os números passam a ser estes:

| Métrica | σ de log máximo (combinação) | Repetições para 5% com 80% de poder | Diferença detectável com n = 40, independente e pareada | Previsão do piloto (independente / pareada) |
|---|---|---|---|---|
| `ops_s` | 0,018 (1 *thread*, `set`) | 10 | ≤ 5% (poder ≈ 100%) | 14% / 9% |
| `lat_p50_ms` | 0,020 (1 *thread*, `set`) | 10 | ≤ 5% (poder ≈ 100%) | 13% / 8% |
| `lat_p99_ms` | 0,019 (1 *thread*, `set`) | 10 | ≤ 5% (poder ≈ 100%) | 16% / 11% |
| `memoria_bytes` | 0,0003 (1 *thread*, `get`) | 5 | ≤ 5% (poder ≈ 100%) | 5% / 5% |

O cálculo usa o cenário de Holm conservador e a pior das 6 comparações, como no piloto.

A grade simulada começa em 5%, o limiar do plano. Por isso a tabela diz só que 5% já é detectado com folga, e não qual é a menor diferença detectável.

O motivo da melhora é a variabilidade:
- O CV mediano da vazão caiu de 11,9% no piloto para 0,9% na coleta.
- A deriva entre blocos quase sumiu: a `ops_s` relativa por bloco foi de 0,987 a 1,005, contra 0,842 a 1,098 no piloto ([LEIA-ME](../dados/brutos/LEIA-ME.md)).

**Consequência:** nenhuma comparação ficou inconclusiva por falta de repetições. As diferenças de cerca de 1% com 1 *thread* foram detectadas e classificadas como pequenas demais, e não como inconclusivas, como o piloto previa ([analise-piloto.md](analise-piloto.md), seção 6).

## 8. Análise pareada por bloco (sensibilidade)

Os resultados da pareada estão em [`pareada.csv`](../dados/brutos/analise/pareada.csv), com 40 pares por comparação e nenhum excluído (nenhuma execução refeita).

A pareada e o Mann-Whitney chegam à mesma situação em **23 das 24 comparações**. As razões de Hodges-Lehmann ficam a menos de 1,5 ponto percentual das razões de medianas.

A única discordância é a `lat_p50_ms` com 1 *thread* na carga `get`:

| | Principal (Mann-Whitney) | Pareada (Wilcoxon e Hodges-Lehmann) |
|---|---|---|
| Situação | diferença pequena demais | equivalência prática |
| p Holm | 0,0068 | 0,080 |
| IC da razão | [1,000; 1,015] | [1,000; 1,008] |

As duas leituras concordam no que importa: a diferença fica abaixo de 5%. Elas divergem só sobre se essa diferença de menos de 1,5% é significativa.

O caso de borda da issue sugeria a deriva entre blocos como causa provável de uma discordância. Aqui ela não explica nada, porque a deriva foi mínima nesta coleta. A explicação mais provável é a resolução de 0,008 ms:
- Nessa combinação, as medianas dos dois servidores são iguais (0,535 ms).
- A diferença está em quantas execuções caem no degrau seguinte (0,543 ms).
- O Mann-Whitney capta essa mudança de frequência.
- No Wilcoxon pareado, muitos pares têm diferença zero (empates), e isso reduz o poder.

A `lat_p50_ms` é só descritiva, então a discordância não muda a resposta da Q2. A conclusão segue o teste principal, como manda o adendo.

## 9. Expectativa × resultado

A expectativa está no [cenario.md](cenario.md), seção 7, escrita antes da coleta. Os resultados abaixo estão registrados como saíram, sem reescrever a expectativa.

| Pergunta | Expectativa | Resultado | Leitura |
|---|---|---|---|
| Q1, 1 *thread* | Empate técnico (diferença < 5%) nas três cargas | Valkey de 0,7% a 1,4% mais lento; diferença pequena demais nas três | **Confirmada** no sentido prático: nenhuma diferença chega a 5%. Os dados mostram, porém, uma pequena vantagem real do Redis, que a expectativa não previa |
| Q1, 4 *threads* | Valkey com vazão maior em `set` e `get`, de 5% a 20% a mais, e diferença menor em `misto` | Valkey de 61,5% a 63,2% a mais nas três cargas; a `misto` (63%) fica entre a `get` (62%) e a `set` (63%) | **Direção confirmada, magnitude não:** a diferença é cerca de três vezes o topo da faixa esperada. A diferença menor em `misto` **não se confirmou** |
| Q2, 1 *thread* | p99 sem diferença maior que 5% | Equivalência prática em `get` e `misto`; diferença pequena demais (+1,7%) em `set` | **Confirmada** |
| Q2, 4 *threads* | p99 igual ou menor no Valkey | Valkey de 38% a 39% menor | **Confirmada**, com diferença grande |
| Q2, cargas | p99 de `misto` acima do de `get` nos dois servidores | Acima nos dois servidores e nos dois níveis de *threads*, sempre por um degrau de 0,008 ms (comparação só descritiva, sem teste) | **Confirmada**, mas no limite da resolução do cliente |
| Q3 | Existe interação: os dois ganham vazão com 4 *threads* e o Valkey ganha proporcionalmente mais (R_valkey > R_redis) em `set` e `get` | Interação nas três cargas, na vazão (R de 1,63 a 1,66: Valkey ×2,68, Redis ×1,62 a ×1,64) e no p99 (R de 0,60 a 0,61: Valkey −51%, Redis −20%). Diferença detectável da interação de 1% a 2% | **Confirmada**, inclusive em `misto`, que a expectativa não citava. A magnitude é grande: o ganho do Valkey com 4 *threads* é cerca de 1,6 vez o do Redis. A expectativa não previa o p99, que mostra o mesmo padrão |
| Q4 | Valkey com 10% a 20% menos memória; a memória não depende de `io_threads` nem da carga | Valkey de 12,5% a 12,9% a menos. A carga quase não muda a memória (< 0,03 MiB); com 4 *threads*, os dois usam cerca de 0,53 MiB a mais | **Confirmada** na diferença entre servidores e na carga. **Não confirmada** quanto a `io_threads`: a memória de cada servidor muda com as *threads*, embora a vantagem do Valkey quase não mude (0,871 → 0,875) |

**Diferenças entre o esperado e o observado:**

- **A diferença com 4 *threads* foi muito maior que a esperada.** Com 4 *threads*, o Redis ganhou de 62% a 64% de vazão sobre 1 *thread*; o Valkey ganhou cerca de 168% (medianas de [`descritiva.csv`](../dados/brutos/analise/descritiva.csv)).
  - Isso combina com o anúncio do novo modelo de *threads* de E/S do Valkey 8 ([cenario.md](cenario.md), seção 7).
  - O estudo não mede por que o Redis ganha menos. A comparação dos dois ganhos é a Q3 (seção 6).
- **A vantagem pequena do Redis com 1 *thread*.** A expectativa tratava "empate técnico" como ausência de diferença. Com a variabilidade baixa da coleta, uma diferença de cerca de 1% ficou visível. Pela regra do plano, ela continua sem relevância prática.

## 10. Cuidados de leitura

- **A validade vale para este ambiente.** Os resultados valem para uma máquina com Docker sobre WSL2, valores de 100 bytes, 50 conexões, *pipeline* 1 e 100.000 chaves. Os valores absolutos de ops/s e ms não se transferem para outro ambiente; a ordem entre os servidores e as razões são o resultado (plano, seção 8, armadilha 2).
- **Os tamanhos de efeito padronizados saturam.**
  - Com 4 *threads* e na memória, o δ de Cliff é ±1 (separação total) e o g de Hedges chega às dezenas ou centenas, porque o desvio-padrão é muito pequeno.
  - Esses números só dizem que as distribuições não se sobrepõem.
  - A medida útil do tamanho é a razão de medianas.
- **O p99 é derivado do histograma do cliente e sofre omissão coordenada** (plano, seção 8, armadilhas 3 e 4). Ele vale como comparação relativa entre os servidores, e não como valor absoluto.
- **Possível gargalo do cliente.** A checagem de que o cliente não é o gargalo (plano, seção 7) não foi refeita na coleta completa. Se o cliente limitar a vazão do Valkey com 4 *threads*, a diferença real seria **maior** que a medida, e não menor.
