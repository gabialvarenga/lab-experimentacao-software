# Lab05 — Cenário, hipóteses e expectativa

Cenário do Lab05: o objetivo, a pergunta, as perguntas de pesquisa ligadas às métricas, as hipóteses e a expectativa do grupo, escrita antes de qualquer coleta. O software, as versões e os digests estão em [software.md](software.md). Escalas, testes e plano de análise ficam para a Issue S01-05, e as categorias da pesquisa para a S01-04.

Siglas: GQM (*Goal, Question, Metric*); H₀ e H₁ (hipóteses nula e alternativa); α (nível de significância); IQR (*Interquartile Range*); ops/s (operações por segundo); p50 e p99 (percentis 50 e 99 da latência); SET e GET (comandos de escrita e de leitura de uma chave).

**Esta expectativa não é reescrita depois de ver resultados.** Qualquer correção entra como adendo datado na seção 8, sem apagar o texto original. O commit que a introduz precisa ser anterior ao primeiro commit que contenha dados do *benchmark* (Issue S01-08).

> **Rascunho para revisão do grupo.** As seções 7 e 8 trazem uma aposta de direção que o grupo deve confirmar ou corrigir antes do merge.

## 1. Objetivo e pergunta principal

| Nível | Conteúdo |
|---|---|
| Objetivo (Basili) | **Analisar** o Valkey e o Redis **com o propósito de** comparar **com respeito ao** desempenho (vazão e latência) e ao uso de memória **do ponto de vista de** quem opera um cache em produção **no contexto de** cargas típicas de cache executadas em ambiente controlado |
| Pergunta principal | Migrar do Redis para o Valkey muda o desempenho de um cache? |

Servidores estudados: `redis:8.10.3` e `valkey/valkey:9.1.3`, nas imagens oficiais (ver [software.md](software.md)). Toda a carga roda na máquina do grupo; nenhum sistema de terceiros é testado.

## 2. Perguntas e métricas

Os nomes Q1 a Q4 e os das colunas são a **interface congelada** usada pelo executor, pela análise e pelo dashboard. As colunas são as do CSV bruto definido na Issue S01-07.

| Pergunta | Texto | Métrica (coluna do CSV) | Unidade | Escala |
|---|---|---|---|---|
| Q1 | A vazão difere entre os dois servidores? | `ops_s` | ops/s | razão |
| Q2 | A latência de cauda difere? | `lat_p99_ms` (a `lat_p50_ms` entra como descritiva complementar) | ms | razão |
| Q3 | A diferença depende do uso de *threads* de I/O? | interação `servidor` × `io_threads` sobre `ops_s` e `lat_p99_ms` | — | razão |
| Q4 | O uso de memória para o mesmo conjunto de chaves difere? | `memoria_bytes` | bytes | razão |

Toda pergunta tem ao menos uma métrica direta. A `lat_p99_ms` é uma medida derivada do histograma do cliente de carga; a `ops_s` e a `memoria_bytes` são medidas diretas (`INFO memory`, campo `used_memory`). O tratamento das armadilhas de medição está na S01-05.

## 3. Fatores e níveis

| Fator | Coluna | Níveis | Papel |
|---|---|---|---|
| Servidor | `servidor` | `redis`, `valkey` | Fator principal |
| *Threads* de I/O | `io_threads` | `1`, `4` | Fator secundário (os dois servidores têm a opção `io-threads`) |
| Carga | `carga` | `set`, `get`, `misto` (80% GET e 20% SET) | Bloco: a comparação é feita dentro de cada carga |

Os valores de `carga` são uma proposta a confirmar com as Issues S01-06 e S01-07, antes de o CSV ser gerado. Os parâmetros da carga (valor de 100 bytes, 50 clientes, *pipeline* 1) e o número de repetições (30 por combinação, revisto pelo piloto) estão no planejamento, seção 3.3, e são fixados na S01-06 e na S01-09.

## 4. Hipóteses

Em palavras simples: H₀ diz que trocar de servidor não muda a métrica; H₁ diz que muda, para mais ou para menos. As hipóteses valem **em cada carga e em cada nível de `io_threads`** (as comparações são feitas dentro de cada combinação). X é a métrica da pergunta.

Os dois testes comparam coisas diferentes, e por isso cada um tem a sua formulação:

| | t de Welch | Mann-Whitney |
|---|---|---|
| O que compara | As médias de X nos dois servidores | Os postos: com que frequência uma execução do Valkey dá X maior que uma do Redis |
| H₀ | μ_valkey = μ_redis | P(X_valkey > X_redis) + ½·P(X_valkey = X_redis) = ½ |
| H₁ (bicaudal) | μ_valkey ≠ μ_redis | P(X_valkey > X_redis) + ½·P(X_valkey = X_redis) ≠ ½ |

| Pergunta | H₀ | H₁ |
|---|---|---|
| Q1 | A vazão (`ops_s`) do Valkey e a do Redis são iguais | São diferentes |
| Q2 | A latência p99 (`lat_p99_ms`) dos dois é igual | É diferente |
| Q3 | Passar de 1 para 4 *threads* de I/O muda a vazão e o p99 na mesma proporção nos dois servidores (sem interação) | Muda em proporção diferente (há interação servidor × *threads*) |
| Q4 | A memória (`memoria_bytes`) usada para o mesmo conjunto de chaves é igual nos dois | É diferente |

Na Q3, a medida de cada servidor é a razão entre a mediana com 4 *threads* e a mediana com 1 *thread*: H₀ é R_redis = R_valkey e H₁ é R_redis ≠ R_valkey. Em escala logarítmica a razão vira diferença, o que permite testar a interação por um modelo de dois fatores. A formulação final do teste está na S01-05. Nas quatro perguntas, α = 0,05, com a correção de Holm para as várias comparações (S01-05).

**Diferença relevante na prática.** Uma diferença estatisticamente significativa só importa se também for grande o bastante para quem opera o cache. A proposta é 5%, fixada na S01-05 antes da coleta completa.

## 5. Teste bicaudal

Os testes são bicaudais. A expectativa da seção 7 tem uma direção, mas ela vem de anúncios dos fornecedores, medidos em cargas e máquinas diferentes das do grupo; por isso o grupo não tem uma direção estabelecida antes dos dados. Um teste unicaudal também esconderia o resultado oposto ao esperado (por exemplo, o Redis ganhar onde se esperava o Valkey), que seria informativo. O custo é um pouco menos de poder para detectar um efeito na direção esperada, e o grupo aceita esse custo.

## 6. Significado dos erros no contexto do cache

| Erro | No cenário | Consequência |
|---|---|---|
| Tipo I (falso positivo) | Concluir que os servidores diferem quando não diferem | Uma equipe poderia migrar de servidor, com custo de operação, por um ganho que não existe |
| Tipo II (falso negativo) | Não perceber uma diferença real | A equipe deixaria de aproveitar um ganho de desempenho ou de memória, ou de notar uma piora |

Para esta pergunta o grupo considera o erro tipo I mais grave, porque uma migração tem custo real e é difícil de desfazer, enquanto o erro tipo II custa uma oportunidade que pode ser reavaliada com mais repetições. O risco do tipo II é controlado pelo piloto (S01-09), que estima o número de repetições necessário para detectar uma diferença de 5%.

## 7. Expectativa antes de coletar

Qual servidor o grupo espera que vá melhor, em qual carga e por quê. É uma expectativa, não uma conclusão: as fontes são anúncios e documentação dos próprios fornecedores, e a confiança é baixa onde as fontes não comparam os dois servidores entre si.

| Pergunta | Expectativa | Confiança | Por quê |
|---|---|---|---|
| Q1, `io_threads` = 1 | Empate técnico (diferença menor que 5%) em `set`, `get` e `misto` | Baixa | Com 1 *thread*, os dois executam comandos e I/O na *thread* principal, e os dois partem do mesmo código (Redis 7.2.4). Cada fornecedor anuncia otimizações de comando próprias, mas nenhuma compara o Redis e o Valkey diretamente |
| Q1, `io_threads` = 4 | **O Valkey tem vazão maior** em `set` e `get`, na ordem de 5% a 20% a mais, e menor diferença em `misto` | Baixa a média | O Valkey 8.0 anuncia até 1,2 milhão de consultas por segundo contra 380 mil da versão anterior, com o novo modelo de *threads* de I/O (cerca de 3 vezes). O Redis 8 anuncia até 112% de ganho (cerca de 2 vezes) com 8 *threads*. O ganho relativo de cada um sobre si mesmo é a única comparação disponível, e o Valkey anuncia o maior |
| Q2 | O p99 acompanha a vazão: sem diferença maior que 5% com 1 *thread*; com 4 *threads*, p99 igual ou menor no Valkey. O p99 de `misto` fica acima do de `get` nos dois | Baixa | Em carga fixa de clientes, maior vazão costuma significar menor tempo de espera na fila. Nenhuma fonte anuncia o p99 dos dois servidores lado a lado |
| Q3 | Existe interação: os dois ganham vazão com 4 *threads* em relação a 1, e o Valkey ganha **proporcionalmente mais** (R_valkey > R_redis) em `set` e `get` | Baixa a média | Mesma base da Q1 com 4 *threads*: o maior ganho anunciado sobre a própria versão anterior é o do Valkey. O ganho só aparece se o cliente de carga também usar várias *threads*, o que as duas documentações recomendam |
| Q4 | **O Valkey usa menos memória** para o mesmo conjunto de chaves, em torno de 10% a 20% a menos para valores de 100 bytes. A memória não depende de `io_threads` nem da carga | Média a alta | A nova tabela de dispersão do Valkey 8.1 reduz o uso em cerca de 20 bytes por par chave-valor, e o Valkey 9.1 anuncia até 20% menos memória para *strings* pequenas. É a expectativa com mais apoio, porque o ganho vem da estrutura de dados e não da carga |

**Diferenças entre os anúncios e o nosso experimento.** Os números dos fornecedores não valem diretamente aqui:

| Aspecto | Anúncios dos fornecedores | Este estudo |
|---|---|---|
| Máquina | Servidores de nuvem (AWS r7g, ARM; CPU Intel multinúcleo no caso do Redis) | Um computador com Docker sobre WSL2, núcleos separados para servidor e cliente |
| *Threads* de I/O | Redis: 8; Valkey: configuração própria do teste | 1 e 4 |
| Carga | Ferramentas e parâmetros próprios de cada fornecedor | Mesmo cliente para os dois; valor de 100 bytes, 50 clientes, *pipeline* 1 |
| O que se compara | Cada servidor contra a sua versão anterior | Redis 8.10.3 contra Valkey 9.1.3, lado a lado |

Por isso o grupo espera diferenças **menores e mais ruidosas** que as anunciadas, e vale a ordem entre os servidores, não os valores absolutos de ops/s.

**Fontes (acesso em 17/11/2026):**

- Valkey 8.0, até 1,2 milhão de QPS contra 380 mil e *threads* de I/O assíncronas: [valkey.io/blog/valkey-8-0-0-rc1](https://valkey.io/blog/valkey-8-0-0-rc1/).
- Valkey 8.1, nova tabela de dispersão e cerca de 20 bytes a menos por par chave-valor: [valkey.io/blog/new-hash-table](https://valkey.io/blog/new-hash-table/) e [valkey.io/blog/valkey-8-1-0-ga](https://valkey.io/blog/valkey-8-1-0-ga/).
- Valkey 9.1, até 20% menos memória para *strings* pequenas: [valkey.io](https://valkey.io/).
- Redis 8, mais de 30 melhorias, até 87% mais rápido em comandos, até 2 vezes a vazão e até 112% de ganho com `io-threads` igual a 8: [redis.io/blog/redis-8-ga](https://redis.io/blog/redis-8-ga/).
- Documentação de `io-threads` (inclui a recomendação de rodar o cliente com `--threads` igual ao número de *threads* do servidor): [`redis.conf` 8.10.3](https://raw.githubusercontent.com/redis/redis/8.10.3/redis.conf) e [`valkey.conf` 9.1.3](https://raw.githubusercontent.com/valkey-io/valkey/9.1.3/valkey.conf).

## 8. Registro e adendos

**Informações já vistas antes de escrever a expectativa.** Para ser transparente sobre o que o grupo já sabia:

- As versões, os digests, a contagem de *pulls* e a posição no DB-Engines, levantados na Issue S01-02 e registrados em [software.md](software.md).
- Os textos dos anúncios listados na seção 7, lidos em 17/11/2026 para escrever esta expectativa. Em particular, o texto do [valkey.io](https://valkey.io/) para a versão 9.1 cita 2,1 milhões de requisições por segundo num servidor e até 20% menos memória para *strings* pequenas.
- Resultados de terceiros que comparam a memória dos dois servidores ou dos dois ao longo das versões e que a busca por esta expectativa apresentou: uma análise da Percona (memória por chave do Valkey caindo de 102,48 para 64,02 bytes entre as versões 7.2.14 e 9.1.1) e um *benchmark* da Momento (Valkey 8.1 com 28% menos memória que o Redis 8.2 em 50 milhões de conjuntos ordenados). Eles reforçam a expectativa da Q4, mas não foram usados como fonte principal.
- Nenhuma execução do *benchmark* com medição de vazão, latência ou memória foi vista pelo grupo até a data. **Confirmar com o integrante responsável pelo ambiente (S01-06) antes do merge**; se tiver havido teste manual, registrar aqui o que foi visto.

**Adendos.** Nenhum até o momento. Qualquer adendo entra aqui com data e motivo, sem alterar as seções 1 a 7.
