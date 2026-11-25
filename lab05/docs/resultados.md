# Lab05 — Resultados das Q1, Q2 e Q4

Este documento traz as respostas às perguntas Q1 (vazão), Q2 (latência de cauda) e Q4 (memória) com a coleta completa. As regras usadas são as do [plano de análise](plano-analise.md), seções 5 e 6, e dos adendos de 19/11 e 23/11. A expectativa é a do [cenário](cenario.md), seção 7. Documento da Issue S02-06.

A Q3 (interação servidor × `io_threads`) fica para a S02-07, e o impacto prático para a S03.

## 1. Dados e comando

| Item | Valor |
|---|---|
| Coleta | [`dados/brutos/execucoes.csv`](../dados/brutos/execucoes.csv): 480 execuções (2 servidores × 2 níveis de `io_threads` × 3 cargas × 40 repetições), descritas no [LEIA-ME](../dados/brutos/LEIA-ME.md) |
| SHA-256 do CSV (LF) | `e7ce9d81f951928c63f2ddd14579e659fe18ae91d797cc3d0a55d3e78355234d` |
| Servidores | Redis 8.10.3 × Valkey 9.1.3 |
| Comando (a partir de `lab05/`) | `python -m lab05 analisar` (cerca de 4 min, determinístico, semente 42) |
| Saídas | [`dados/brutos/analise/`](../dados/brutos/analise/): `comparacoes.csv`, `pareada.csv`, `descritiva.csv`, `diferenca-detectavel.csv` e [`registro-analise.md`](../dados/brutos/analise/registro-analise.md) |
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

Os dois servidores ganham vazão com 4 *threads*, mas em proporções muito diferentes. A pergunta sobre essa interação é a Q3 (S02-07).

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

## 6. Diferença detectável, recalculada com a coleta completa

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

## 7. Análise pareada por bloco (sensibilidade)

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

## 8. Expectativa × resultado

A expectativa está no [cenario.md](cenario.md), seção 7, escrita antes da coleta. Os resultados abaixo estão registrados como saíram, sem reescrever a expectativa.

| Pergunta | Expectativa | Resultado | Leitura |
|---|---|---|---|
| Q1, 1 *thread* | Empate técnico (diferença < 5%) nas três cargas | Valkey de 0,7% a 1,4% mais lento; diferença pequena demais nas três | **Confirmada** no sentido prático: nenhuma diferença chega a 5%. Os dados mostram, porém, uma pequena vantagem real do Redis, que a expectativa não previa |
| Q1, 4 *threads* | Valkey com vazão maior em `set` e `get`, de 5% a 20% a mais, e diferença menor em `misto` | Valkey de 61,5% a 63,2% a mais nas três cargas; a `misto` (63%) fica entre a `get` (62%) e a `set` (63%) | **Direção confirmada, magnitude não:** a diferença é cerca de três vezes o topo da faixa esperada. A diferença menor em `misto` **não se confirmou** |
| Q2, 1 *thread* | p99 sem diferença maior que 5% | Equivalência prática em `get` e `misto`; diferença pequena demais (+1,7%) em `set` | **Confirmada** |
| Q2, 4 *threads* | p99 igual ou menor no Valkey | Valkey de 38% a 39% menor | **Confirmada**, com diferença grande |
| Q2, cargas | p99 de `misto` acima do de `get` nos dois servidores | Acima nos dois servidores e nos dois níveis de *threads*, sempre por um degrau de 0,008 ms (comparação só descritiva, sem teste) | **Confirmada**, mas no limite da resolução do cliente |
| Q4 | Valkey com 10% a 20% menos memória; a memória não depende de `io_threads` nem da carga | Valkey de 12,5% a 12,9% a menos. A carga quase não muda a memória (< 0,03 MiB); com 4 *threads*, os dois usam cerca de 0,53 MiB a mais | **Confirmada** na diferença entre servidores e na carga. **Não confirmada** quanto a `io_threads`: a memória de cada servidor muda com as *threads*, embora a vantagem do Valkey quase não mude (0,871 → 0,875) |

**Diferenças entre o esperado e o observado:**

- **A diferença com 4 *threads* foi muito maior que a esperada.** Com 4 *threads*, o Redis ganhou de 62% a 64% de vazão sobre 1 *thread*; o Valkey ganhou cerca de 168% (medianas de [`descritiva.csv`](../dados/brutos/analise/descritiva.csv)).
  - Isso combina com o anúncio do novo modelo de *threads* de E/S do Valkey 8 ([cenario.md](cenario.md), seção 7).
  - O estudo não mede por que o Redis ganha menos. A comparação dos dois ganhos é a Q3.
- **A vantagem pequena do Redis com 1 *thread*.** A expectativa tratava "empate técnico" como ausência de diferença. Com a variabilidade baixa da coleta, uma diferença de cerca de 1% ficou visível. Pela regra do plano, ela continua sem relevância prática.

## 9. Cuidados de leitura

- **A validade vale para este ambiente.** Os resultados valem para uma máquina com Docker sobre WSL2, valores de 100 bytes, 50 conexões, *pipeline* 1 e 100.000 chaves. Os valores absolutos de ops/s e ms não se transferem para outro ambiente; a ordem entre os servidores e as razões são o resultado (plano, seção 8, armadilha 2).
- **Os tamanhos de efeito padronizados saturam.**
  - Com 4 *threads* e na memória, o δ de Cliff é ±1 (separação total) e o g de Hedges chega às dezenas ou centenas, porque o desvio-padrão é muito pequeno.
  - Esses números só dizem que as distribuições não se sobrepõem.
  - A medida útil do tamanho é a razão de medianas.
- **O p99 é derivado do histograma do cliente e sofre omissão coordenada** (plano, seção 8, armadilhas 3 e 4). Ele vale como comparação relativa entre os servidores, e não como valor absoluto.
- **Possível gargalo do cliente.** A checagem de que o cliente não é o gargalo (plano, seção 7) não foi refeita na coleta completa. Se o cliente limitar a vazão do Valkey com 4 *threads*, a diferença real seria **maior** que a medida, e não menor.
