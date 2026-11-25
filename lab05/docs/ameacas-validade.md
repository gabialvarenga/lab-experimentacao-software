# Lab05 — Ameaças à validade

Ameaças à validade do experimento Redis × Valkey, nos quatro tipos clássicos, cada uma com a mitigação adotada e o risco que sobra. Documento da Issue S02-08, escrito em 25/11/2026, com os números da coleta completa ([`execucoes.csv`](../dados/brutos/execucoes.csv), 480 execuções) e da análise das Q1 a Q4 ([resultados.md](resultados.md)). O que se pode ou não afirmar a partir dos resultados é o assunto da S03-02, e este documento só aponta para ele.

Siglas: CV (coeficiente de variação); IC (intervalo de confiança); p50 e p99 (percentis 50 e 99 da latência); HL (Hodges-Lehmann); WSL2 (*Windows Subsystem for Linux 2*); ART (*Aligned Rank Transform*).

## 1. Como ler

As quatro categorias seguem Wohlin et al. (*Experimentation in Software Engineering*), como no Lab02 e no Lab03:

| Tipo | Pergunta |
|---|---|
| Conclusão | A relação entre os servidores e as métricas pode ser detectada de forma estatisticamente confiável? |
| Interna | A diferença medida vem mesmo do servidor e das *threads* de E/S, e não de outra coisa que variou junto? |
| Construto | O que foi medido (ops/s, p99, `used_memory`) representa o que se quer dizer com "desempenho de um cache"? |
| Externa | O resultado vale fora deste ambiente? |

**Risco restante** é o julgamento do grupo depois da mitigação: **baixo** (não muda nenhuma conclusão), **médio** (pode mudar a magnitude ou a leitura de uma comparação) e **alto** (a conclusão não vale sem a ressalva). Cada ameaça tem uma linha de **evidência** com o número que sustenta o julgamento; onde não há número, o texto diz.

## 2. Resumo

| # | Ameaça | Tipo | Risco restante |
|---|---|---|---|
| C1 | Poder limitado das 40 repetições | Conclusão | Baixo |
| C2 | Muitas comparações e liberdade do analista | Conclusão | Baixo |
| C3 | Pressupostos violados e escolha do teste | Conclusão | Baixo |
| C4 | Resolução da latência (degraus de 0,008 ms) | Conclusão | Médio |
| C5 | Significância estatística sem relevância prática | Conclusão | Baixo |
| I1 | Deriva da máquina ao longo do tempo e ordem das execuções | Interna | Baixo |
| I2 | Mudanças entre o piloto e a coleta | Interna | Baixo |
| I3 | Processos em segundo plano e estado da máquina | Interna | Médio |
| I4 | Configuração padrão de cada imagem e CPU fixada | Interna | Médio |
| I5 | Cliente de carga do fabricante do Redis | Interna | Baixo |
| K1 | Vazão e latência do `memtier_benchmark` como "desempenho" | Construto | Médio |
| K2 | Carga sintética | Construto | Médio |
| K3 | `used_memory` como medida de memória | Construto | Médio |
| K4 | Otimizar só um número (Goodhart) e o que ficou fora da medida | Construto | Médio |
| K5 | Cliente como gargalo, não verificado na coleta | Construto | Alto |
| E1 | Uma máquina, notebook, Docker Desktop sobre WSL2 | Externa | Alto |
| E2 | Duas versões específicas | Externa | Médio |
| E3 | Servidor isolado, sem persistência, em rede local | Externa | Alto |
| E4 | Dois níveis de *threads* e três cargas | Externa | Médio |

## 3. Ameaças à validade de conclusão

### C1. Poder limitado das 40 repetições

- **Ameaça.** Com poucas repetições, uma diferença real pode sair "inconclusiva" (erro tipo II). O piloto, com CV de 12% a 15%, previa 80% de poder só para diferenças a partir de cerca de 14% (vazão), 13% (p50) e 16% (p99) com 40 repetições ([analise-piloto.md](analise-piloto.md), seção 6).
- **Mitigação.** O número de repetições foi fixado por simulação de poder, com Holm e o pior caso de cada família (S01-09). O poder foi recalculado com a variabilidade da coleta completa.
- **Evidência.** O CV mediano da vazão caiu de 11,9% para 0,9%, e o CV máximo é de 2,2% ([LEIA-ME da coleta](../dados/brutos/LEIA-ME.md)). Com 40 repetições, o poder é de cerca de 100% para 5% nas comparações das Q1, Q2 e Q4, e bastam 10 repetições para 5% na vazão e nas latências ([resultados.md](resultados.md), seção 7). Na interação da Q3, a diferença detectável é de 1% a 2% ([resultados.md](resultados.md), seção 6.3). Nenhuma comparação ficou inconclusiva por falta de repetições.
- **Risco restante: baixo.** O poder alto vale para a variabilidade desta coleta. A grade simulada começa em 5%, então a menor diferença detectável das Q1, Q2 e Q4 não foi calculada. A simulação supõe valores contínuos, e a latência não é (C4).

### C2. Muitas comparações e liberdade do analista

- **Ameaça.** Testar muitas combinações e relatar só as significativas, ou escolher o teste pelo p-valor, infla o erro tipo I. São 6 comparações em cada uma das Q1, Q2 e Q4, mais 3 por métrica na Q3.
- **Mitigação.** O plano congelou, antes da coleta, as perguntas, as famílias, o limiar de 5%, o teste principal de cada métrica (Mann-Whitney) e o método da Q3 (ART). A correção de Holm é aplicada dentro de cada pergunta. O piloto não entra na análise final, e os adendos de 19/11 e 23/11 foram registrados antes de qualquer dado da coleta (a coleta começou em 24/11, às 23h24).
- **Evidência.** O `analisar` só registra o que a regra 5.1 daria nos dados da coleta, sem trocar o teste (`teste-principal.csv`, colunas `teste_usado` e `origem`). Nas 24 comparações, o Welch concordou com o Mann-Whitney em todas.
- **Risco restante: baixo.** Uma coisa foi decidida depois de ver os dados: a simulação de poder da Q3 e a grade de diferenças dela (S02-07), que o adendo de 23/11 não detalhou. Ela não muda teste, famílias nem limiar. As famílias do Holm são decisão do grupo, e outra escolha (uma família única para todas as comparações) seria mais conservadora.

### C3. Pressupostos violados e escolha do teste

- **Ameaça.** O Welch e a ANOVA supõem resíduos aproximadamente normais. Se o pressuposto falha e o teste é mantido, o p-valor perde o sentido.
- **Mitigação.** A regra 5.1 decide o teste pelos resíduos (Shapiro-Wilk, assimetria e Levene), e o Mann-Whitney e a ART são as alternativas. Na Q3, a ANOVA com o bloco no modelo é só sensibilidade.
- **Evidência.** Nas Q1, Q2 e Q4, o Shapiro-Wilk rejeita a normalidade dos resíduos nas quatro métricas (p entre 1e-31 e 1e-23), com assimetria de −2,37 na vazão e 3,13 na memória ([`teste-principal.csv`](../dados/brutos/analise/teste-principal.csv)). Na Q3, o Shapiro-Wilk também rejeita (p de 2,9e-24 na vazão e 1,5e-20 no p99). Com o bloco no modelo, a normalidade continua rejeitada (p da ordem de 1e-19), então a ANOVA com bloco também viola o pressuposto, e só a decisão dela é usada ([resultados.md](resultados.md), seção 6.2). O Levene não rejeita variâncias iguais na Q3 em nenhuma carga (menor p = 0,122).
- **Risco restante: baixo.** Os testes escolhidos não dependem da normalidade, e a conclusão é a mesma nos dois métodos. O efeito é de magnitude: os p-valores muito pequenos (1e-49) não valem como grandeza.

### C4. Resolução da latência e empates

- **Ameaça.** O cliente reporta a latência em degraus de 0,008 ms. A medida tem poucos valores distintos (13 no p50 e 29 no p99 nas 480 execuções), e as medianas por combinação assumem poucos valores. Isso gera empates e IC degenerados.
- **Mitigação.** O Mann-Whitney trata empates. A análise pareada (Hodges-Lehmann, IC exato) não depende da mediana, e serve de sensibilidade. A razão de medianas é reportada junto do δ de Cliff.
- **Evidência.** Vários IC por *bootstrap* da razão de medianas se reduzem a um ponto, como [0,612; 0,612], e na Q3 o limite inferior do IC de R coincide com o próprio R nas três cargas do p99. O IC de Hodges-Lehmann da pareada chega às mesmas conclusões ([resultados.md](resultados.md), seções 4 e 8). A única discordância entre a pareada e o teste principal é no p50 com 1 *thread* na carga `get`, em que as medianas são iguais (0,535 ms).
- **Risco restante: médio.** A "equivalência prática" do p99 com 1 *thread* (`get` e `misto`) se apoia em IC que subestimam a incerteza. Os 8 µs de resolução equivalem a 0,8% a 1,7% do valor, da mesma ordem das diferenças entre os servidores com 1 *thread* (0,8% a 1,7% no p99) e bem abaixo do limiar de 5%. As conclusões das Q2 e Q3 com 4 *threads* (diferença de 38% a 51%) não são afetadas.

### C5. Significância estatística sem relevância prática

- **Ameaça.** Com CV de 1%, o teste enxerga diferenças minúsculas, e "significativo" não quer dizer "importante".
- **Mitigação.** O limiar de relevância é de 5% sobre a razão de medianas, e a situação de cada comparação segue a seção 6 do plano. Uma diferença significativa dentro de [0,95; 1,05] é classificada como "diferença pequena demais". O tamanho de efeito é a razão, e não o p-valor.
- **Evidência.** Com 1 *thread*, o Valkey fica de 0,7% a 1,4% abaixo do Redis na vazão: significativo, mas pequeno demais ([resultados.md](resultados.md), seção 3). Com 4 *threads*, a diferença é de 62% a 63%.
- **Risco restante: baixo.** O limiar de 5% é uma escolha do grupo, e não um valor da literatura; outro limiar mudaria a classificação das comparações com 1 *thread* e a memória (12,5% a 12,9%) não mudaria. Os tamanhos de efeito padronizados saturam (δ = ±1, g de Hedges nas dezenas), e por isso a razão é a medida a ler.

## 4. Ameaças à validade interna

### I1. Deriva da máquina ao longo do tempo e ordem das execuções

- **Ameaça.** Temperatura, frequência da CPU e estado do Windows mudam durante as 7,4 horas da coleta. Se um servidor rodasse sempre em momentos diferentes do outro, a deriva viraria "efeito do servidor". No piloto, o bloco 2 ficou cerca de 16% mais lento em todas as combinações.
- **Mitigação.** Cada repetição é um bloco com as 12 combinações em ordem sorteada (semente 42), e o contêiner é novo a cada execução. A preparação do protocolo (seção 2.2) exige tomada, modo de energia "Melhor desempenho", nenhum outro contêiner e 10 minutos de máquina ociosa.
- **Evidência.** Na coleta, a `ops_s` relativa por bloco fica entre 0,987 e 1,005 (no piloto, entre 0,842 e 1,098), e a correlação entre a ordem e a `ops_s` relativa é de 0,02. A autocorrelação de lag 1 das medidas relativas é de 0,02 (vazão) e 0,04 (p99), e a média relativa por faixa de 10 blocos varia de 0,997 a 1,000 na vazão. A posição média de cada servidor dentro do bloco é igual (6,6 para o Redis e 6,4 para o Valkey), e a de cada nível de *threads* também (6,3 e 6,7).
- **Risco restante: baixo.** Não há sinal de deriva nem de dependência entre execuções vizinhas. A melhora em relação ao piloto não foi medida diretamente (I2).

### I2. Mudanças entre o piloto e a coleta

- **Ameaça.** O piloto decidiu o teste principal, o método da Q3 e o número de repetições. Se o ambiente da coleta fosse outro, essas decisões poderiam não valer.
- **Mitigação.** O piloto e a coleta rodaram na mesma máquina (i7-13620H), com a mesma versão do Docker Desktop (4.67.0), do WSL (2.6.3), do kernel (6.6.87.2) e do Python (3.14.3), e com as mesmas imagens pelo *digest*. O executor grava o ambiente de cada coleta, e a tag `lab05-coleta-congelada` fixa o código e a configuração (`d770186`).
- **Evidência.** O que mudou foi a preparação: no piloto, quatro contêineres de outro projeto estavam ligados na primeira tentativa (descartada), e não havia os 10 minutos de ociosidade. O CV mediano da vazão caiu de 11,9% para 0,9%. A verificação do ambiente (S01-06) foi feita em outra máquina (i5-9300H), e as seções do protocolo marcadas como histórico dela não valem para a coleta.
- **Risco restante: baixo.** A explicação mais provável da melhora é a preparação, mas ela não foi testada: a coleta não mediu a causa. O que importa para a validade é que o piloto não enviesou a coleta, e a decisão de n = 40 se revelou conservadora (C1).

### I3. Processos em segundo plano e estado da máquina

- **Ameaça.** Atualizações do Windows, antivírus, sincronização e outros processos competem pela CPU com o servidor e o cliente. A coleta rodou à noite, das 23h24 de 24/11 às 06h51 de 25/11.
- **Mitigação.** Nenhum outro programa aberto, atualizações adiadas, suspensão desligada e ninguém usando a máquina. O registro grava o modo de energia e a alimentação.
- **Evidência.** Nenhuma interrupção. As 480 execuções duraram de 48 s a 54 s, e o intervalo entre uma e a próxima ficou entre 5 s e 6 s nas 479 transições. A correlação entre a posição no bloco e a vazão relativa é de −0,007.
- **Risco restante: médio.** A carga do Windows e a frequência da CPU não foram medidas, então o que explica o ruído restante (CV de 1%) não é conhecido. Um evento curto de fundo poderia afetar uma execução sem deixar rastro além de um valor atípico (a análise conta e não remove os *outliers*).

### I4. Configuração padrão de cada imagem e CPU fixada

- **Ameaça.** O estudo compara duas imagens com as opções do protocolo e o restante no padrão de cada uma. Uma diferença nos padrões (não nas implementações) apareceria como "diferença entre servidores". Além disso, servidor e cliente rodam em CPUs fixas da máquina virtual (`0-3` e `4-7`).
- **Mitigação.** As opções que o protocolo fixa são as mesmas nos dois: persistência desligada, `maxmemory` de 512 MB, `noeviction`, `protected-mode` desligado e `--io-threads`. Foi conferido que o servidor em execução reporta a mesma configuração nos quatro tratamentos. As CPUs `0-3` e `4-7` são pares de núcleos físicos distintos.
- **Evidência.** A conferência está na seção 9.1 do protocolo. O mapeamento das CPUs da máquina virtual para os núcleos do processador (que mistura núcleos de desempenho e de eficiência) não é controlado, mas é o mesmo em todos os tratamentos.
- **Risco restante: médio.** O resultado vale para "as imagens oficiais com esta configuração", e não para os servidores ajustados. Se o mapeamento das CPUs interagir com o número de *threads*, a interação da Q3 teria parte dessa causa.

### I5. Cliente de carga do fabricante do Redis

- **Ameaça.** O `memtier_benchmark` é da empresa do Redis. Se o cliente favorecesse o Redis, o viés apareceria como vantagem dele.
- **Mitigação.** O mesmo cliente, as mesmas opções e a mesma carga nos dois servidores, de modo que qualquer viés é comum. O cliente usa 4 *threads*, como recomendam as documentações dos dois servidores.
- **Evidência.** O resultado favorece o Valkey com 4 *threads* (vazão 62% a 63% acima, p99 38% a 39% abaixo), o que não é o sentido do viés temido. Com 1 *thread*, o Redis fica 0,7% a 1,4% acima, perto do limiar.
- **Risco restante: baixo.** O estudo não testou outro cliente (por exemplo, o `redis-benchmark`), então não se sabe se a ordem entre os servidores muda. A justificativa da escolha está na seção 4 do protocolo.

## 5. Ameaças à validade de construto

### K1. Vazão e latência do `memtier_benchmark` como "desempenho"

- **Ameaça.** `ops_s` é a vazão com um número fixo de conexões (48 clientes, *pipeline* 1), e não a capacidade máxima do servidor. O cliente é de laço fechado: quando o servidor demora, ele envia menos requisições e as latências altas que ocorreriam não são registradas (omissão coordenada). A `lat_p99_ms` é derivada do histograma do cliente e inclui a rede virtual e a fila do cliente.
- **Mitigação.** O mesmo cliente e a mesma carga para os dois servidores, então o viés é comum. O p99 é calculado por execução e resumido pela mediana, sem tirar média de percentis. O p99 vale como comparação **relativa**, e não como valor absoluto.
- **Evidência.** Vazão e latência andam juntas (Q1 e Q2 com o mesmo sinal), como esperado num cliente de laço fechado. A coleta não mediu a latência com carga em taxa fixa.
- **Risco restante: médio.** Um servidor pode parecer melhor em laço fechado e não ser sob uma taxa de chegada fixa. Não se afirma nada sobre latência em produção (S03-02).

### K2. Carga sintética

- **Ameaça.** Chaves e valores sintéticos (valor de 100 bytes, 100.000 chaves, acesso aleatório com `--key-pattern=R:R`, proporções 1:0, 0:1 e 1:4) não representam o tráfego de uma aplicação.
- **Mitigação.** As três cargas cobrem escrita, leitura e uma mistura de 80% de leitura, e a pré-carga deixa todas no mesmo estado inicial. A escolha vem do `cenario.md`.
- **Evidência.** O conjunto ocupa de 14,5 a 17,2 MiB, muito abaixo do `maxmemory` de 512 MB: nunca há remoção de chaves, e a pressão de memória não é testada.
- **Risco restante: médio.** Valores de outros tamanhos, acesso concentrado em poucas chaves, *pipeline* maior e comandos além de GET e SET podem mudar a ordem ou a magnitude. Fica como o que não se pode afirmar (S03-02).

### K3. `used_memory` como medida de memória

- **Ameaça.** O `used_memory` é a memória que o alocador do servidor contabiliza, e não a que o sistema operacional vê (RSS), que inclui fragmentação. Além disso, ele é lido **depois da medição**, e não logo depois da pré-carga, como o plano de análise previa.
- **Mitigação.** O `used_memory` é medida direta, igual nos dois servidores, e é lido com as mesmas 100.000 chaves carregadas. O CV da medida é de 0,02%.
- **Evidência.** A memória de cada servidor muda com as *threads* (cerca de 0,53 MiB a mais com 4), o que o planejamento não esperava; a causa não foi investigada ([resultados.md](resultados.md), seção 5). O RSS **não foi coletado**: o plano de análise (seção 8, item 6) previa reportá-lo como complemento, e isso não foi feito.
- **Risco restante: médio.** A diferença de 12,5% a 12,9% a favor do Valkey vale para o `used_memory`. Se a fragmentação for diferente nos dois, a diferença no RSS pode ser outra. O estudo não afirma nada sobre o custo de memória em produção.

### K4. Otimizar só um número e o que ficou fora da medida

- **Ameaça.** Olhar só `ops_s` (lei de Goodhart) levaria a preferir um servidor que ganha vazão e piora a cauda. Decidir só pelo que é fácil de medir (falácia de McNamara) deixa de fora o que não foi medido.
- **Mitigação.** Nenhuma conclusão sai de uma métrica sozinha. A vazão, o p50, o p99 e a memória são lidos juntos, e **não há índice composto**. A Q3 também olha o p99.
- **Evidência.** Neste experimento as métricas apontam na mesma direção com 4 *threads*, e o resultado não depende de uma só delas.
- **Risco restante: médio.** Ficam **fora** da medida: persistência em disco e durabilidade, latência acima do p99 (p99,9), comportamento com falhas e reinicialização, custo de operação, outros tamanhos de valor, outras estruturas de dados e o consumo de CPU. A conclusão vale para as cargas e o ambiente do estudo, e não para "o desempenho" de cada servidor.

### K5. Cliente como gargalo, não verificado na coleta

- **Ameaça.** Se o cliente saturar, o `ops_s` mede o cliente, e não o servidor, e esconde o efeito das *threads* de E/S.
- **Mitigação.** O cliente usa 4 *threads*, em CPUs separadas das do servidor. O plano de análise previa verificar o uso de CPU do cliente.
- **Evidência.** A verificação **não foi feita nem registrada** na coleta completa (nem no piloto, até onde os registros mostram). Um limite inferior vem dos próprios dados: com 4 *threads*, o cliente sustentou cerca de 235 mil ops/s contra o Valkey, então ele não limita o Redis em cerca de 145 mil ops/s com o mesmo cliente e a mesma carga. Isso é uma inferência, e não uma medição, e supõe que o custo do cliente por operação seja parecido nos dois servidores.
- **Risco restante: alto.** O Valkey com 4 *threads* pode estar perto do teto do cliente. Se estiver, a diferença real é **maior** que a medida, e não menor ([resultados.md](resultados.md), seção 10). A conclusão de direção (Valkey ganha mais com *threads*) se mantém. A magnitude da Q3 (R de 1,63 a 1,66) é um valor mínimo.

## 6. Ameaças à validade externa

### E1. Uma máquina, notebook, Docker Desktop sobre WSL2

- **Ameaça.** Os valores dependem do hardware (i7-13620H, 16 CPUs lógicas), do Windows, do WSL2 e da máquina virtual do Docker, e não de um servidor Linux de produção.
- **Mitigação.** Uma única máquina para toda a coleta, para que a diferença entre servidores não se misture com a diferença entre computadores. O ambiente é registrado (versões, limites, energia) e o Docker e o WSL não foram atualizados durante a coleta.
- **Evidência.** Os valores absolutos de ops/s e ms são deste ambiente. A ordem entre os servidores e as razões são o resultado.
- **Risco restante: alto.** Não se sabe se a razão de 1,6 entre os ganhos com *threads* se mantém em outra máquina ou em Linux nativo. Sem mitigação possível no tempo do laboratório: repetir em outras máquinas é o que aumentaria o nível de evidência ([categorias.md](categorias.md), seção 8, "O que mudaria"). Liga ao "o que não se pode afirmar" da S03-02.

### E2. Duas versões específicas

- **Ameaça.** O resultado vale para Redis 8.10.3 e Valkey 9.1.3. Os dois projetos evoluem de forma independente desde 2024, e uma versão nova pode inverter a ordem em alguma métrica.
- **Mitigação.** As versões foram fixadas por tag e por *digest*, e a coleta não atualizou nada. A escolha das versões estáveis mais recentes está no [software.md](software.md): o Valkey 9.2 e o Redis 8.12 ainda eram candidatos a lançamento.
- **Evidência.** O executor grava a versão de cada execução, e a validação recusa outra versão.
- **Risco restante: médio.** O resultado tem data. Não vale para as versões que vieram depois nem para as anteriores (como o Valkey 8.0 e o Redis 7.2, de que os anúncios dos fornecedores falam).

### E3. Servidor isolado, sem persistência, em rede local

- **Ameaça.** O experimento roda um servidor por vez, sem persistência, sem réplica e sem *cluster*, e o cliente fala com ele pela rede virtual do Docker. Em produção, há disco, réplicas, rede real e concorrência com outros serviços.
- **Mitigação.** Nenhuma: foi uma decisão de escopo, para comparar os servidores sob as mesmas condições e sem ruído de disco e de rede. O protocolo registra que a rede interna é fechada e que o modo protegido é desligado por isso.
- **Evidência.** A latência medida inclui a camada de rede virtual, igual para os dois servidores (protocolo, seção 8).
- **Risco restante: alto.** O resultado não vale para *cluster*, persistência (RDB e AOF), replicação nem rede real. Sem mitigação possível no tempo do laboratório; liga à S03-02.

### E4. Dois níveis de *threads* e três cargas

- **Ameaça.** Só `io_threads` = 1 e 4, e só as cargas `set`, `get` e `misto`. O comportamento com 2, 8 ou mais *threads*, e com outras proporções de leitura e escrita, não foi medido.
- **Mitigação.** Os níveis foram escolhidos pelo planejamento para cobrir "sem *threads* de E/S" e "com *threads*", e o cliente usa 4 *threads*, como as documentações recomendam.
- **Evidência.** A interação da Q3 é a mesma nas três cargas (R de 1,63 a 1,66), então a carga pouco muda o padrão.
- **Risco restante: médio.** Com apenas dois níveis, não se sabe se o ganho continua com 8 *threads* nem se a curva é monotônica. Como o servidor ocupa 4 CPUs (`0-3`), um nível maior exigiria mudar a divisão de CPUs.

## 7. O que fica sem mitigação e para onde segue

| Ameaça | Por que não há mitigação no tempo do laboratório | Segue para |
|---|---|---|
| K5 Cliente como gargalo | A medida de CPU do cliente não foi registrada na coleta. Medir exigiria repetir a coleta (7,4 h) | Resultados, seção 10, e S03-02 |
| K3 RSS não coletado | A coleta já foi feita sem esse campo | S03-02 |
| E1 Uma máquina e E3 sem produção | Exigem outras máquinas, outros ambientes ou medição em produção | S03-02 e S03-04 |
| K2 e E4 Carga e níveis de *threads* | Fora do escopo do plano congelado | S03-02 |

## 8. O que mudou em relação à Issue

- A issue estimava a diferença detectável em cerca de 13% a 16% com 40 repetições. Esse era o número do piloto. Com a variabilidade da coleta, a diferença detectável cai para 5% ou menos nas Q1, Q2 e Q4 e para 1% a 2% na interação da Q3 (C1).
- A deriva entre blocos, que a issue listava como ameaça de conclusão, é tratada em I1: foi uma ameaça real no piloto e quase desapareceu na coleta.
- Ameaças que a issue não listava e entraram: C4 (resolução da latência), I4 (configuração padrão e CPU fixada), I5 (cliente do fabricante do Redis), K5 (cliente como gargalo) e E4 (dois níveis de *threads*).

## 9. Histórico de versões

| Versão | Data | O que mudou |
|---|---|---|
| v1 | 25/11/2026 | Primeira versão, com os números da coleta completa e da análise das Q1 a Q4 |
| v2 | — | Revisão na S03-02 e na S03-03, com o que não se pode afirmar. Registrar aqui o que mudou e por quê |
