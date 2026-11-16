# Lab05 — Planejamento das Sprints

Planejamento do Lab05 (experimento em software real, em operação e de alto impacto). As seções citadas entre parênteses referem-se ao enunciado do Lab05. O backlog detalhado (Issues com corpo completo) é escrito sprint a sprint: a Sprint 01 está em `docs/issues-s01/`; as Sprints 02 e 03 estão aqui em nível de tabela e são detalhadas no início de cada uma, com o que a sprint anterior ensinar.

Siglas: GQM (*Goal, Question, Metric*); CI (*Continuous Integration*); PR (*Pull Request*); WIP (*Work in Progress*); CSV (*Comma-Separated Values*); IC (intervalo de confiança); ops/s (operações por segundo); p50/p99 (percentis 50 e 99 da latência).

## 1. Calendário

Datas do cronograma da disciplina, confirmadas em 16/11/2026.

| Sprint | Período | Pontos | Entrega (seção 7) |
|---|---|---|---|
| Lab05S01 | 16/11 (seg) a 19/11 (qui): 4 dias | 5 | Proposta: software com evidências dos três critérios, pergunta, caminho, 7 categorias (v1), plano de coleta e de análise, coleta piloto |
| Lab05S02 | 20/11 (sex) a 26/11 (qui): 7 dias, com um fim de semana | 5 | Coleta completa, dados validados e versionados, análise (descritiva, testes, tamanho de efeito), ameaças à validade |
| Lab05S03 | 27/11 (sex) a 03/12 (qui): 7 dias, com um fim de semana | 5 | Impacto, 7 categorias revisadas, conclusões e limitações, rascunho do documento e da apresentação |
| Documento Final e Apresentação | 04/12 (sex) a 17/12 (qui): 2 semanas | 5 | Documento e apresentação de 10 minutos, formato livre (seção 8), em 17/12 |

A S01 é curta (4 dias, começando hoje) e carrega a proposta inteira e a coleta piloto, como a S01 do Lab04. A folga do semestre está no fim: duas semanas entre a S03 e a apresentação, que servem para refinar o documento e ensaiar, não para adiar a coleta.

## 2. Escolha do software

**Redis × Valkey**, aprovado pelo grupo em 16/11/2026. **Pendente: confirmar com o professor que nenhum outro grupo escolheu o mesmo software** (seção 10), porque "Redis × Valkey" está entre os exemplos do enunciado.

O Redis é o armazenamento chave-valor em memória mais usado em produção (cache, sessões, filas, *rate limiting*). Em 2024 o Redis trocou a licença BSD por licenças não *open source*; a Linux Foundation criou o Valkey a partir do Redis 7.2.4, com apoio de AWS, Google Cloud e Oracle. Desde então os dois evoluem separados, e empresas decidem se migram.

### 2.1 Três critérios (seção 2a) — evidências iniciais, a completar em S01-02

| Critério | Redis | Valkey | Fonte (acesso em 16/11/2026) |
|---|---|---|---|
| Real | Site oficial, documentação, imagem oficial `redis` | Site oficial, documentação, imagem `valkey/valkey` | redis.io, valkey.io, Docker Hub |
| Em operação | Versão estável mais recente: 8.10.3 | Versão estável mais recente: 9.2 | Tags do Docker Hub |
| Alto impacto | 11,69 bilhões de *pulls* da imagem oficial | 407,8 milhões de *pulls* | Docker Hub (`library/redis`, `valkey/valkey`) |

A completar em S01-02: posição no DB-Engines, uso no Stack Overflow Developer Survey, oferta gerenciada (AWS ElastiCache e MemoryDB, Google Memorystore) e empresas que anunciaram migração ao Valkey, com link e data de acesso.

## 3. Pergunta, caminho e desenho (proposta; o grupo confirma em S01-03 a S01-06)

### 3.1 Pergunta e GQM

| Nível | Conteúdo |
|---|---|
| Objetivo (Basili) | **Analisar** o Valkey e o Redis **com o propósito de** comparar **com respeito ao** desempenho (vazão e latência) e ao uso de memória **do ponto de vista de** quem opera um cache em produção **no contexto de** cargas típicas de cache executadas em ambiente controlado |
| Pergunta principal | Migrar do Redis para o Valkey muda o desempenho de um cache? |
| Q1 | A vazão (ops/s) difere entre os dois? |
| Q2 | A latência de cauda (p99) difere? |
| Q3 | A diferença depende do uso de *threads* de I/O? |
| Q4 | O uso de memória para o mesmo conjunto de chaves difere? |
| Métricas | ops/s, latência p50 e p99 (ms), memória usada (`used_memory`, bytes) |

### 3.2 Caminho

"Rodar o software no ambiente do grupo" (seção 2b): experimento controlado, com as versões estáveis mantidas de cada servidor, nas imagens oficiais. Toda a carga roda na máquina do grupo; nenhum sistema de terceiros é testado (seção 2, cuidados de ética).

Combinação opcional, se sobrar tempo na S03: analisar dados de operação publicados (notas de versão e anúncios de desempenho do Valkey) para confrontar o que os fornecedores afirmam com o que medimos.

### 3.3 Fatores, variáveis e cargas

| Elemento | Proposta | Decidido em |
|---|---|---|
| Fator principal | Servidor: Redis (8.x estável) × Valkey (9.x estável) | S01-03 |
| Fator secundário | *Threads* de I/O: 1 × 4 (os dois servidores suportam `io-threads`) | S01-03 |
| Cargas (blocos) | SET, GET e mista 80% GET / 20% SET; valor de 100 bytes; 50 clientes; *pipeline* 1 | S01-06 |
| Variáveis de resposta | ops/s (razão), latência p50 e p99 em ms (razão), memória em bytes (razão) | S01-05 |
| Repetições | 30 execuções por combinação (servidor × *threads* × carga), número revisto pelo piloto | S01-09 |
| Ordem | Aleatorizada com semente fixa, alternando servidores, para não confundir efeito do servidor com aquecimento da máquina | S01-06 |
| Controles | Mesma máquina, ligada na tomada, sem outros programas; servidor e cliente em núcleos separados (`--cpuset-cpus`); persistência desligada; aquecimento descartado; *flush* entre execuções | S01-06 |

**Cliente de carga.** Usar o mesmo cliente para os dois servidores, para que a medição não dependa da ferramenta. Opções: `redis-benchmark` da versão 7.2.4 (anterior à separação, vale para os dois) ou `memtier_benchmark`. Decisão em S01-06.

### 3.4 Plano de análise (detalhado em S01-05)

- Descritiva por combinação: mediana, IQR, coeficiente de variação, *outliers*.
- Comparação Redis × Valkey em cada carga: t de Welch e Mann-Whitney (reaproveitados do Lab04), com a escolha justificada pela forma da distribuição observada no piloto.
- Tamanho de efeito: Hedges g, delta de Cliff e razão de medianas com IC por *bootstrap* (a medida de relevância prática).
- Fator *threads*: ANOVA de dois fatores ou modelo equivalente não paramétrico, se a interação for relevante.
- Várias comparações: correção de Holm.
- Poder: o motor de simulação do Lab04 estima, a partir da variabilidade do piloto, quantas repetições bastam para detectar uma diferença de 5%.

### 3.5 Expectativa antes de coletar

A expectativa (qual servidor é mais rápido, em que carga e por quê) é escrita e mesclada em S01-03 **antes** da coleta piloto, como no Lab04. Vale como prova de que a hipótese não foi ajustada aos dados.

## 4. Reaproveitamento dos laboratórios anteriores (seção 4)

| Lab | O que entra no Lab05 |
|---|---|
| Lab01 | Kanban no GitHub Projects e coleta automatizada com registro de execução |
| Lab02 | Desenho de experimento: tratamentos, ordem aleatorizada, controle de variáveis |
| Lab03 | Estrutura do projeto e CI; dicionário de dados; métricas de operação (SLI/SLO como linguagem do impacto) |
| Lab04 | `aplicar_testes` (Welch, Mann-Whitney, tamanho de efeito), motor de simulação para poder e tamanho de amostra, dashboard Streamlit |

Nenhum dado do Lab03 ou do Lab04 é reaproveitado, só código e método.

## 5. Papéis (seção 6)

Sugeridos pelo enunciado e adotados como orientação, não como divisão rígida:

| Papel | Foco |
|---|---|
| A — Planejamento e Método | Critérios, categorias, GQM, hipóteses, ameaças |
| B — Instrumentação e Operação | Ambiente Docker, executor do *benchmark*, coleta, validação |
| C — Análise e Impacto | Descritiva, testes, tamanho de efeito, gráficos, impacto |

Regra mantida dos labs anteriores: cada integrante é Assignee de ao menos uma Issue de código por sprint.

## 6. Sprint 01 — proposta e coleta piloto

### 6.1 Issues

| Issue | Tipo | Papel | Dia | Depende de | Entrega (seção do enunciado) |
|---|---|---|---|---|---|
| S01-01 Criar a estrutura do `lab05/`, dependências, README e CI | código | A | 16/11 | — | Comando único, semente fixa |
| S01-02 Comprovar os três critérios e confirmar o software com o professor | doc | A | 16/11–17/11 | — | 2a: tabela com números e fontes |
| S01-03 Escrever a pergunta, o GQM, as hipóteses e a expectativa | doc | A | 17/11 | S01-02 | 3: GQM, hipóteses, expectativa antes da coleta |
| S01-04 Classificar o estudo nas 7 categorias (v1) | doc | A | 18/11 | S01-03 | 3: categorias com justificativa |
| S01-05 Definir variáveis, métricas, escalas e o plano de análise | doc | C | 17/11–18/11 | S01-03 | 3: escalas, testes, tamanho de efeito, armadilhas de medição |
| S01-06 Montar o ambiente e escrever o protocolo de execução | código | B | 16/11–17/11 | S01-01 | 3: instrumentação e operação; ética |
| S01-07 Implementar o executor do *benchmark* | código | B | 17/11–18/11 | S01-06 | Coleta automatizada em CSV |
| S01-08 Executar a coleta piloto e validar os dados | código | B | 19/11 (manhã) | S01-03, S01-07 | Coleta piloto |
| S01-09 Analisar o piloto e fixar o número de repetições | código | C | 18/11–19/11 | S01-05, S01-08 | Plano de análise testado nos dados do piloto |
| S01-10 Registrar o *snapshot* do quadro da Sprint 01 | processo | — | 19/11 | todas | Kanban |

### 6.2 Carga por dia (3 integrantes, WIP 1)

Cada coluna é um papel; a pessoa de cada papel pode mudar de um dia para o outro.

| Dia | A — Planejamento e Método | B — Instrumentação e Operação | C — Análise e Impacto |
|---|---|---|---|
| 16/11 (seg) | S01-01, depois S01-02 (pedir a confirmação ao professor hoje) | S01-06 (começa: Docker e imagens) | Adapta do Lab04 o código de testes e de poder (base da S01-09) |
| 17/11 (ter) | S01-02 (termina), depois S01-03 | S01-06 (termina), depois S01-07 | S01-05 (começa, já com as perguntas da S01-03) |
| 18/11 (qua) | S01-04 | S01-07 (termina) | S01-05 (termina), depois S01-09 com dados de exemplo |
| 19/11 (qui) | Revisão dos PRs; S01-10 no fim do dia | S01-08 (manhã) | S01-09 com os dados do piloto (tarde) |

Cada papel tem uma Issue de código (A: S01-01; B: S01-06 a S01-08; C: S01-09). Os papéis são orientação: se uma pessoa trocar de papel, a regra de uma Issue de código por integrante continua valendo.

### 6.3 Marcos

1. **Fim de 16/11:** estrutura e CI no `main`; pedido de confirmação enviado ao professor (S01-01, S01-02).
2. **Fim de 17/11:** GQM, hipóteses e expectativa mescladas (S01-03) **antes** de qualquer coleta; ambiente Docker pronto (S01-06).
3. **Fim de 18/11:** executor funcionando para os dois servidores (S01-07); plano de análise e 7 categorias mesclados (S01-04, S01-05).
4. **19/11:** piloto coletado e validado de manhã, analisado à tarde; número de repetições fixado; *snapshot* (S01-08 a S01-10).

### 6.4 Pontos de atenção

| Risco | Efeito | Resposta |
|---|---|---|
| Só 4 dias, com piloto e análise no último dia | Entrega incompleta | Piloto pequeno (5 repetições, poucos minutos); S01-09 começa em 18/11 com dados de exemplo e só troca a entrada em 19/11. Se atrasar, cortar nesta ordem: fator *threads* no piloto, carga mista. Não cortar a expectativa (S01-03) nem o piloto |
| Hora de corte de 19/11 não confirmada (aula à noite) | Menos tempo no último dia | Tratar o meio-dia de 19/11 como prazo do piloto |
| Resposta do professor demorar | Trabalho em software que pode ser recusado | Pedir em 16/11; seguir com as Issues que valem para qualquer software (S01-01, S01-05) até a resposta |
| Outro grupo já escolheu Redis × Valkey | Troca de software no meio da sprint | Confirmar com o professor no primeiro dia (S01-02); plano B: desempenho de e-commerces com Lighthouse |
| Docker Desktop no Windows roda sobre WSL2 | Resultado depende do ambiente (validade externa) | Registrar o ambiente; rodar sempre na mesma máquina; discutir como ameaça |
| Variação entre execuções (temperatura, energia, outros processos) | Ruído maior que a diferença | Tomada, modo de energia fixo, ordem aleatorizada, aquecimento descartado, 30+ repetições |
| *Benchmark* de cada fornecedor favorece o próprio servidor | Viés de instrumentação | Mesmo cliente para os dois |
| Métrica "jogada" (Goodhart) | Otimizar ops/s ignora latência de cauda | Medir p99 e memória junto com a vazão |

## 7. Sprint 02 — 20/11 a 26/11: coleta completa e análise (detalhar no início da sprint)

A coleta completa (S02-02) deve rodar até 22/11 (domingo), para a análise ter de 23/11 a 26/11.

| Issue | Tipo | Papel | Entrega |
|---|---|---|---|
| S02-01 Congelar a configuração do experimento (`config.yaml`) | código | B | Versões, cargas, repetições e semente congeladas antes da coleta |
| S02-02 Executar a coleta completa | código | B | CSV bruto com registro de ambiente |
| S02-03 Validar e versionar os dados; escrever o dicionário de dados | código | B | Dados validados e versionados |
| S02-04 Estatística descritiva e gráficos | código | C | Distribuições por combinação |
| S02-05 Testes de hipótese e tamanho de efeito (Q1, Q2, Q4) | código | C | Tabela de resultados com correção de Holm |
| S02-06 Analisar o fator *threads* de I/O (Q3) | código | A | Interação servidor × *threads* |
| S02-07 Escrever as ameaças à validade (quatro tipos, com mitigação) | doc | A | Conclusão, interna, construto, externa |
| S02-08 Montar o dashboard com os resultados | código | C | Seções de resultados |
| S02-09 Registrar o *snapshot* do quadro da Sprint 02 | processo | — | Kanban |

## 8. Sprint 03 — 27/11 a 03/12: impacto, conclusões e rascunhos (detalhar no início da sprint)

| Issue | Tipo | Papel | Entrega |
|---|---|---|---|
| S03-01 Levantar números públicos de uso com fonte e data | doc | C | Base do impacto |
| S03-02 Estimar o impacto e o que não se pode afirmar | código | C | Ex.: CPU ou custo economizado por milhão de operações; limites de generalização |
| S03-03 Revisar as 7 categorias com justificativa | doc | A | Categorias finais |
| S03-04 Escrever conclusões e limitações | doc | A | Respostas às duas perguntas do enunciado (seção 1) |
| S03-05 Documentar o que foi reaproveitado e o que foi feito de novo | doc | B | Seção 4 do enunciado |
| S03-06 Comando único reproduz coleta, análise e dashboard | código | B | Reprodutibilidade |
| S03-07 Rascunho do documento | doc | todos | Formato decidido pelo grupo |
| S03-08 Rascunho da apresentação | doc | todos | Formato decidido pelo grupo |
| S03-09 Registrar o *snapshot* do quadro da Sprint 03 | processo | — | Kanban |

## 9. Documento Final e Apresentação — 04/12 a 17/12

| Issue | Entrega |
|---|---|
| F-01 Fechar o documento final | Documento revisado até 10/12, uma semana antes da apresentação |
| F-02 Preparar e ensaiar a apresentação de 10 minutos | Ensaios cronometrados entre 11/12 e 16/12; cada integrante capaz de explicar qualquer parte (seção 8) |

Formatos a decidir na S03. Proposta: dashboard Streamlit (reaproveitado do Lab04) como documento, e apresentação como reunião simulada com o CTO de uma empresa que avalia migrar o cache do Redis para o Valkey.

## 10. Processo

| Tema | Decisão |
|---|---|
| WIP | 1 Issue por integrante |
| Definição de pronto | PR mesclado, commits `#<número da Issue> descrição`, CI verde em Issues de código |
| Branches | `<número>-<descrição-curta>` |
| Quadro | [projeto 9](https://github.com/users/gabialvarenga/projects/9); cartões atualizados diariamente; *snapshot* ao fim de cada sprint |
| Nomes das Issues | `S01-xx`, `S02-xx`, `S03-xx` e `F-xx`, com rótulo `lab05` e milestone `Lab05S0x` |
| Criação das Issues | `docs/issues-s0x/criar-issues.ps1`, como no Lab04 |

## 11. Cobertura do enunciado

| Exigência | Onde |
|---|---|
| Software real, em operação, alto impacto, com números e fontes (2a) | S01-02, S03-01 |
| Pergunta e caminho (1, 2b) | S01-03 |
| Ética (2, cuidados) | S01-06 |
| 7 categorias (3) | S01-04, S03-03 |
| GQM, hipóteses, escalas, armadilhas de medição (3) | S01-03, S01-05 |
| Coleta piloto (7, S01) | S01-08, S01-09 |
| Coleta completa, dados validados e versionados (7, S02) | S02-01 a S02-03 |
| Descritiva, testes, tamanho de efeito (3, 7) | S02-04 a S02-06 |
| Ameaças à validade, quatro tipos (3) | S02-07 |
| Reaproveitamento dos labs (4) | Seção 4 deste documento; S03-05 |
| Impacto e o que não se pode afirmar (5) | S03-01, S03-02 |
| Documento e apresentação (8) | S03-07, S03-08, F-01, F-02 |
