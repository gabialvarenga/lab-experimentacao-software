# Lab05 — Classificação do estudo nas 7 categorias (v1)

Primeira versão da classificação do Lab05 nas 7 categorias de pesquisa (natureza, objetivos, abordagem, procedimentos, tempo, controle e nível de evidência), com a justificativa de cada uma ligada ao desenho do estudo. O software, as versões e os digests estão em [software.md](software.md); a pergunta, as hipóteses e a expectativa estão em [cenario.md](cenario.md). A versão final é revista na Issue S03-03, depois da coleta e da análise.

> **A conferir com a Aula 8.** As definições abaixo seguem a literatura geral de metodologia de pesquisa. Antes do merge, conferir cada definição com o material da Aula 8 e ajustar o vocabulário, se ele for diferente.

Siglas: GQM (*Goal, Question, Metric*); WSL2 (*Windows Subsystem for Linux 2*); ops/s (operações por segundo); p99 (percentil 99 da latência).

## 1. Resumo

| Categoria | Classificação | Em uma frase |
|---|---|---|
| Natureza | Aplicada | Responde a uma decisão real: migrar um cache do Redis para o Valkey |
| Objetivos | Explicativa | Manipula servidor e *threads* de I/O e mede o efeito na vazão, na latência e na memória |
| Abordagem | Quantitativa | Todas as variáveis de resposta são numéricas e analisadas por testes estatísticos |
| Procedimentos | Experimento controlado, em laboratório | Tratamentos definidos, ordem aleatorizada e ambiente fixo |
| Tempo | Transversal | Medições num período curto, sem acompanhar a evolução dos servidores |
| Controle | Alto sobre as variáveis do estudo, limitado sobre a máquina | O grupo fixa versões, configuração, cliente de carga e ordem; o hardware é um computador pessoal com Docker sobre WSL2 |
| Nível de evidência | Experimento controlado, com validade externa limitada | Boa evidência de causa dentro do ambiente do grupo; não vale como medida de produção |

## 2. Natureza: aplicada

**Definição.** Pesquisa básica busca ampliar o conhecimento sem uma aplicação imediata; pesquisa aplicada busca gerar conhecimento para resolver um problema prático.

**Justificativa.** A pergunta principal é "migrar do Redis para o Valkey muda o desempenho de um cache?" (ver [cenario.md](cenario.md), seção 1). Ela nasce de uma decisão real de quem opera um cache, e o objetivo é apoiar essa decisão. O estudo não propõe uma teoria sobre servidores em memória.

**O que mudaria.** Se o foco fosse entender o mecanismo interno que explica a diferença (por exemplo, o modelo de *threads* de cada servidor), a natureza passaria a ser básica.

## 3. Objetivos: explicativa

**Definição.** Pesquisa exploratória busca familiaridade com um tema pouco conhecido; descritiva registra características de um fenômeno; explicativa identifica fatores que determinam ou contribuem para um fenômeno.

**Justificativa.** O estudo manipula dois fatores (servidor e `io_threads`) e mede o efeito de cada um sobre `ops_s`, `lat_p99_ms` e `memoria_bytes`. A Q3 pergunta se o efeito de um fator depende do outro (interação). Isso é identificar fatores que contribuem para o desempenho, não só descrevê-lo.

**Caso de borda: explicativa ou descritiva?** O estudo mede *quanto* os servidores diferem, mas não explica o *porquê* interno da diferença. O grupo escolhe **explicativa**, porque a manipulação dos fatores com ordem aleatorizada permite atribuir a diferença ao fator, e não apenas descrevê-la. A explicação que o estudo oferece é a do efeito do fator, e não a do mecanismo. Descritiva seria a escolha se o grupo apenas observasse servidores já em uso, sem manipular nada.

**O que mudaria.** Medir um servidor em produção, sem controle dos fatores, seria descritivo. Um estudo preliminar para descobrir quais métricas importam seria exploratório.

## 4. Abordagem: quantitativa

**Definição.** Abordagem quantitativa traduz o fenômeno em números e usa estatística para analisá-lo; qualitativa interpreta significados e percepções; mista combina as duas.

**Justificativa.** Todas as variáveis de resposta (`ops_s`, `lat_p50_ms`, `lat_p99_ms`, `memoria_bytes`) são medidas em escala de razão. A análise usa estatística descritiva, testes de hipótese (t de Welch e Mann-Whitney), tamanho de efeito e correção de Holm, como no plano de [cenario.md](cenario.md), seções 4 e 5.

**O que mudaria.** Entrevistar operadores sobre a experiência de migração seria qualitativo. A combinação opcional da Sprint 03 (comparar o que os fornecedores anunciam com o que foi medido) mantém o estudo quantitativo, porque os anúncios também são números; só uma análise de relatos de usuários o tornaria misto.

## 5. Procedimentos: experimento controlado em laboratório

**Definição.** Os procedimentos técnicos descrevem como os dados são obtidos: pesquisa bibliográfica, documental, levantamento (*survey*), estudo de caso, pesquisa-ação, experimento, entre outros. No experimento, o pesquisador manipula variáveis independentes e observa o efeito nas dependentes.

**Justificativa.** O estudo define tratamentos (servidor × `io_threads`), mede em blocos de carga (`set`, `get`, `misto`), aleatoriza a ordem das execuções com semente fixa e repete cada combinação. Tudo roda no ambiente do grupo, e não em produção, por isso o experimento é de laboratório e não de campo. O objeto são as execuções do *benchmark*, e não pessoas: não há participantes humanos, e a ética se resume a não testar sistemas de terceiros (ver o planejamento, seção 3.2).

**O que mudaria.** Medir o Redis e o Valkey em uma empresa real, sem manipular os fatores, seria um estudo de caso ou um estudo observacional. Ler as notas de versão e os anúncios dos fornecedores seria pesquisa documental.

## 6. Tempo: transversal

**Definição.** Estudo transversal coleta os dados num momento ou período curto; estudo longitudinal acompanha o mesmo fenômeno ao longo do tempo.

**Justificativa.** As execuções ocorrem em poucos dias, com as versões fixadas em 17/11/2026 (Redis 8.10.3 e Valkey 9.1.3). O estudo não acompanha como o desempenho evolui entre versões.

**Observação.** O resultado é válido para essas versões. Uma versão estável nova pode mudar a conclusão, porque os dois projetos evoluem em separado e a vazão e a memória são justamente o que os fornecedores anunciam melhorar a cada versão.

**O que mudaria.** Repetir o experimento a cada versão estável durante um ano seria longitudinal.

## 7. Controle: alto sobre as variáveis do estudo, limitado sobre a máquina

**Definição.** O grau de controle é o quanto o pesquisador determina as condições do estudo: alto no experimento controlado, intermediário no quase-experimento, baixo no estudo observacional.

**Justificativa.** O grupo controla:

- as versões, por digest, e a configuração igual nos dois servidores (persistência desligada, `maxmemory` fixo);
- o mesmo cliente de carga para os dois servidores;
- servidor e cliente em núcleos separados;
- a ordem aleatorizada com semente fixa, o aquecimento descartado e a limpeza das chaves entre execuções;
- as cargas e o número de clientes.

Esses controles estão detalhados no planejamento, seção 3.3, e são fixados na Issue S01-06; esta versão os registra como planejados e a S03-03 os confirma.

**Limites.** O controle é menor sobre o ambiente: o experimento roda em um computador pessoal, com Docker sobre WSL2, em que temperatura, energia e outros processos podem variar. Por isso o grupo escreve "alto sobre as variáveis do estudo" e não só "alto". Os controles de ordem aleatorizada, 30 ou mais repetições e registro do ambiente servem para reduzir esse ruído.

**O que mudaria.** Um servidor dedicado, sem outros processos e com frequência de CPU fixa, aumentaria o controle. Medir em produção reduziria o controle a baixo.

## 8. Nível de evidência e limitações

**Definição.** Os níveis de evidência ordenam os desenhos de estudo pela força com que sustentam uma conclusão causal. Em geral, revisões sistemáticas e experimentos replicados ficam no topo, experimentos controlados e quase-experimentos vêm depois, estudos observacionais abaixo, e a opinião de especialistas na base.

**Classificação.** Experimento controlado. A manipulação dos fatores e a aleatorização da ordem sustentam uma conclusão de causa **dentro do ambiente do grupo**. Não é o topo da hierarquia: o estudo é de uma só máquina, sem replicação independente.

**Limitações que reduzem o nível de evidência:**

| Limitação | Efeito na conclusão |
|---|---|
| Uma única máquina, com Docker sobre WSL2 | Os valores absolutos de ops/s e de latência não se transferem para outro hardware; vale a ordem entre os servidores |
| Carga sintética (valor de 100 bytes, 50 clientes, *pipeline* 1) | Não representa o tráfego de uma aplicação real |
| Duas versões fixas (Redis 8.10.3 e Valkey 9.1.3) | O resultado pode mudar com outras versões |
| Cliente de carga único | O resultado depende da ferramenta, embora o uso do mesmo cliente nos dois reduza o viés |
| Latência p99 é uma medida derivada do histograma do cliente | Menos direta que a vazão e a memória |
| Sem medição em produção | Nada se afirma sobre o comportamento de um cache em uso real |

Essas limitações são discutidas como ameaças à validade (S02-07) e como o que não se pode afirmar (S03-02). Esta versão não as substitui.

**O que mudaria.** Repetir o experimento em outras máquinas, ou por outro grupo, e comparar os resultados aumentaria o nível de evidência. Medir em produção daria evidência observacional, de maior validade externa e menor controle.

## 9. Histórico de versões

| Versão | Data | O que mudou |
|---|---|---|
| v1 | 17/11/2026 | Primeira classificação, antes da coleta. Escrita com as definições da literatura geral, a conferir com a Aula 8 |
| v2 | — | Revisão final na S03-03, com o que a coleta e a análise ensinarem. Registrar aqui o que mudou e por quê |
