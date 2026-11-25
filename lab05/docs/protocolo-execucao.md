# Lab05 — Protocolo de execução do *benchmark*

Como o ambiente é montado e como cada execução do *benchmark* é feita, para que outro integrante repita o experimento e obtenha as mesmas condições. O que se mede e por quê está em [cenario.md](cenario.md); as versões e os digests das imagens estão em [software.md](software.md). O ambiente é definido em [`../compose.yaml`](../compose.yaml) e usado pelo executor (Issue S01-07).

Siglas: CPU (*Central Processing Unit*); WSL2 (*Windows Subsystem for Linux 2*); ops/s (operações por segundo); p50 e p99 (percentis 50 e 99 da latência); TCP (*Transmission Control Protocol*); RESP (*Redis Serialization Protocol*).

> **Estado (S02-02, 24/11/2026).** Configuração **congelada para a coleta completa**: 40 repetições, aquecimento de 10 s, medição de 30 s, pausa de 5 s, semente 42, imagens pelo *digest*. O piloto (S01-08) e a análise dele (S01-09) confirmaram os valores que eram *proposta*; a verificação da seção 9 foi cumprida. Mudança em `config.yaml` ou `compose.yaml` depois da tag `lab05-coleta-congelada` exige refazer a coleta e registrar o motivo.

## 1. Escopo e ética

- Todo o experimento roda **na máquina do grupo**, em contêineres locais. Nenhum sistema de terceiros é testado e nenhuma carga é enviada pela internet.
- Não há dados pessoais nem participantes humanos: os dados são medições de desempenho de duas imagens oficiais do Docker Hub, com chaves e valores sintéticos.
- Os contêineres não publicam portas na máquina nem na rede local; só se enxergam entre si, na rede interna do Docker. Por isso o modo protegido dos servidores é desligado (não há senha) sem expor nada.
- Nenhum segredo é usado: as imagens são públicas e o CI não roda Docker.

## 2. Ambiente

### 2.1 Máquina designada

Uma única máquina roda todas as execuções, para que a diferença entre os servidores não se misture com a diferença entre computadores.

> **Mudança de máquina (18/11/2026, S01-08).** O piloto foi rodado em outro notebook do grupo, que **passa a ser a máquina designada**: a coleta completa (S02-02) roda nele também. A tabela original, de 17/11, fica abaixo como histórico.

| Item | Máquina designada desde 18/11/2026 |
|---|---|
| Processador | Intel Core i7-13620H, 16 CPUs lógicas (6 núcleos de desempenho com 2 *threads* e 4 de eficiência) |
| Memória | 23,7 GiB; sem `.wslconfig` (limites padrão do WSL) |
| Sistema | Windows 11 (10.0.26200) com WSL 2.6.3; kernel do WSL 6.6.87.2-1 |
| Tipo | Notebook (tem bateria) |
| Docker | Docker Desktop 4.67.0, Docker Engine 29.3.1, Docker Compose 5.1.1 |
| Máquina virtual do Docker | Kernel 6.6.87.2-microsoft-standard-WSL2, 16 CPUs lógicas, 11,5 GiB de memória. Pares de CPUs irmãs `0-1`, `2-3`, `4-5` e `6-7` (lidos em `/sys/devices/system/cpu/*/topology` num contêiner): servidor (`0-3`) e cliente (`4-7`) não dividem núcleo físico, e os valores padrão do `compose.yaml` ficam como estão |

| Item | Valor de referência (17/11/2026, máquina anterior) |
|---|---|
| Processador | Intel Core i5-9300H, 4 núcleos físicos e 8 *threads* lógicas |
| Memória | 15,8 GB; o WSL2 está limitado a 11 GB (`.wslconfig`: `memory=11GB`) |
| Sistema | Windows 11 com WSL2; kernel do WSL 6.18.58.1-1 |
| Tipo | Notebook (tem bateria) |
| Docker | Docker Desktop (pacote 4.99.0 do `winget`; *conferir em Settings → About*), Docker Engine 29.9.3, Docker Compose v5.7.0 (17/11/2026) |
| Máquina virtual do Docker | Kernel 6.18.58.1-microsoft-standard-WSL2, 8 CPUs lógicas, 11,49 GB de memória, `cgroup` v2 (o `cpuset` funciona) |

O executor grava o ambiente de cada coleta em `registro-<data>.md` (versões, digests, CPU, memória, sistema, versão do Docker e do WSL). A tabela acima é o ponto de partida e não substitui esse registro.

### 2.2 Preparação antes de cada coleta

Cumprir todos os itens e anotar o que não for possível:

1. Notebook **ligado na tomada**, durante toda a coleta.
2. Plano de energia fixo no de maior desempenho disponível, e suspensão de tela e do sistema desligada. Anotar o plano usado. O padrão atual é "Equilibrado", que muda a frequência da CPU conforme a carga. No Windows 11, o que vale é o **modo de energia** (Configurações → Energia: "Melhor desempenho"), que se sobrepõe ao plano do `powercfg`; o executor grava os dois no registro, e também se o notebook está na tomada.
3. **Nenhum outro programa aberto**: navegador, editor, mensageiros e sincronização de arquivos fechados. Atualizações do Windows pausadas. **Nenhum outro contêiner no Docker**: `docker ps` vazio antes de começar (no piloto, contêineres de outro projeto estavam ligados e a primeira tentativa foi descartada).
4. Máquina fria e ociosa: esperar **10 minutos** depois de fechar programas, parar contêineres, de uma coleta anterior ou de qualquer tarefa pesada. No piloto, o segundo bloco ficou cerca de 16% mais lento que os demais, provavelmente porque a máquina ainda se acomodava (ver a seção 11).
5. Registrar a hora de início e de fim, para relacionar com eventuais interrupções.
6. Não mexer na máquina durante a coleta.
7. **Sem atualização automática** do Windows nem do Docker Desktop até o fim da coleta (adiar; ver a seção 2.3).
8. Conferir que o commit em uso é o da tag `lab05-coleta-congelada` (`git describe --tags --exact-match`) e que `git status` está limpo em `lab05/`.

### 2.3 Docker sobre WSL2

O Docker Desktop usa o WSL2, que roda uma máquina virtual leve: o resultado depende desse ambiente (ameaça à validade externa, discutida na S02-07). Por isso:

- as versões do Docker Desktop, do Docker Engine e do WSL entram no registro de ambiente;
- os limites de CPU e memória do WSL também (o `.wslconfig` atual limita só a memória);
- a coleta inteira é feita nesse mesmo ambiente, sem atualizar o Docker ou o WSL no meio.

## 3. Servidores

| | Redis | Valkey |
|---|---|---|
| Imagem | `redis:8.10.3` | `valkey/valkey:9.1.3` |
| Digest do índice | `sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53` | `sha256:3add1a336a920ea54770a001ab6feb3da5fceea96a40373a3a2cd469b815f0b7` |
| Programa | `redis-server` | `valkey-server` |

O digest vale mais que a tag. Os digests de `linux/amd64` estão no [software.md](software.md).

**Configuração igual nos dois**, passada por linha de comando no `compose.yaml`:

| Opção | Valor | Motivo |
|---|---|---|
| `--save ""` e `--appendonly no` | persistência desligada | Escrita em disco não faz parte do que se compara e adicionaria ruído |
| `--maxmemory` | `512mb` | Fixo, bem acima do conjunto de chaves (ver seção 5), para nunca haver remoção de chaves |
| `--maxmemory-policy` | `noeviction` | Sem remoção de chaves durante a medição |
| `--io-threads` | `1` ou `4`, conforme o tratamento | É o fator secundário do estudo |
| `--protected-mode` | `no` | A rede é interna e fechada (seção 1) |

As demais opções ficam no padrão de cada imagem. Qualquer configuração fora desta tabela, nos dois ou em um só, é uma diferença entre os tratamentos e precisa ser registrada.

**CPU.** O servidor roda nas CPUs lógicas `0-3` (`--cpuset-cpus`), e o cliente nas `4-7`, para que não disputem os mesmos núcleos. É igual em todos os tratamentos, mesmo com `io-threads` igual a 1, para que só a configuração do servidor varie.

**Conferido com `lscpu -e` no WSL (Ubuntu 24.04, 17/11/2026):** as CPUs lógicas irmãs, que dividem um mesmo núcleo físico, são os pares `0-1`, `2-3`, `4-5` e `6-7`. Logo o servidor (`0-3`) ocupa os núcleos físicos 0 e 1, e o cliente (`4-7`) os núcleos 2 e 3: **servidor e cliente não dividem nenhum núcleo físico**, e os valores padrão do `compose.yaml` ficam como estão. Em compensação, os quatro núcleos físicos ficam todos ocupados, e o Windows e o Docker competem com os dois lados (seção 8).

## 4. Cliente de carga

**Escolha: `memtier_benchmark` 2.6.1**, em contêiner (`redislabs/memtier_benchmark:2.6.1`, fixado por digest no `compose.yaml`), o mesmo para os dois servidores.

| Critério | `redis-benchmark` 7.2.4 | `memtier_benchmark` 2.6.1 |
|---|---|---|
| Carga mista 80% GET e 20% SET | Não há opção no código | `--ratio=1:4` |
| Latência p50 e p99 | Saída em CSV | JSON com percentis (`--json-out-file`, `--print-percentiles`) |
| Número de clientes | `-c` é o total | `-c` é por *thread* |
| Duração | Por número de requisições | Por tempo (`--test-time`) |
| Neutralidade | A 7.2.4 é anterior à separação e vale para os dois | Ferramenta recente, mas fala o protocolo RESP dos dois |

**Justificativa.** O `cenario.md` fixa uma carga mista de 80% GET e 20% SET, que o `redis-benchmark` não faz. O `memtier_benchmark` faz a carga mista, mede por tempo e grava os percentis em JSON. A neutralidade vem de usar o mesmo cliente nos dois servidores; a desvantagem é que a ferramenta é da empresa do Redis, o que fica registrado como ameaça à validade.

**Cliente com várias *threads*.** A documentação de `io-threads` do Redis (`redis.conf` 8.10.3) e a do Valkey (`valkey.conf` 9.1.3) recomendam rodar o cliente com `--threads` igual ao número de *threads* do servidor, senão o ganho não aparece. O cliente usa **4 *threads* nos dois níveis de `io_threads`**.

**Número de clientes: 48.** No `memtier_benchmark`, `-c` conta clientes por *thread*: 4 *threads* × 12 clientes = **48 clientes**. O planejamento previa 50, que não divide por 4. A diferença é pequena e igual em todos os tratamentos.

## 5. Cargas

Parâmetros comuns a todas as cargas:

| Parâmetro | Valor | Opção do `memtier_benchmark` |
|---|---|---|
| Tamanho do valor | 100 bytes | `-d 100` |
| *Pipeline* | 1 | `--pipeline=1` |
| *Threads* do cliente | 4 | `-t 4` |
| Clientes por *thread* | 12 (48 no total) | `-c 12` |
| Conjunto de chaves | 100.000 chaves | `--key-minimum=1 --key-maximum=100000` |
| Padrão de acesso | aleatório | `--key-pattern=R:R` |
| Protocolo | RESP | `--protocol=redis` |
| Servidor e porta | nome do serviço, 6379 | `--server=redis` ou `--server=valkey`, `--port=6379` |

As três cargas do `cenario.md` (coluna `carga` do CSV) diferem só na proporção entre SET e GET:

| `carga` | Descrição | Opção |
|---|---|---|
| `set` | 100% SET | `--ratio=1:0` |
| `get` | 100% GET | `--ratio=0:1` |
| `misto` | 20% SET e 80% GET | `--ratio=1:4` |

> **Proporções com zero.** No código-fonte do cliente (ramo principal, lido em 17/11/2026) a proporção `1:0` só gera SET e a `0:1` só gera GET, e as duas são aceitas porque basta um dos lados ser maior que zero. **A conferir na versão 2.6.1 em execução, na seção 9.**

**Conjunto de chaves.** 100.000 chaves de 100 bytes ocupam poucas dezenas de megabytes, muito abaixo dos 512 MB de `maxmemory`. Com esse tamanho, a diferença de cerca de 20 bytes por chave anunciada para o Valkey 8.1 (ver o `cenario.md`) é mensurável. *Proposta:* o valor é ajustado pelo piloto se a variação da memória entre repetições for pequena demais para ser medida.

## 6. Procedimento de uma execução

Uma execução é uma combinação (servidor, `io_threads`, `carga`, repetição). Cada execução começa com um contêiner novo, para que a memória (`memoria_bytes`) não carregue o estado da execução anterior. É mais estrito que o `FLUSHALL` previsto no planejamento, porque o `FLUSHALL` não devolve ao sistema a memória que o alocador reservou.

| Passo | O que fazer | Comando (exemplo para o Redis) |
|---|---|---|
| 1 | Subir o servidor e esperar ficar pronto | `IO_THREADS=4 docker compose --profile redis up -d --wait redis` |
| 2 | **Pré-carga**: gravar as 100.000 chaves, com uma conexão e acesso sequencial | `docker compose --profile cliente run --rm cliente --server=redis -t 1 -c 1 -d 100 --ratio=1:0 --key-pattern=P:P --key-minimum=1 --key-maximum=100000 -n allkeys` |
| 3 | **Aquecimento**: 10 s da mesma carga da medição, com saída descartada | o comando do passo 4 com `--test-time=10` e sem `--json-out-file` |
| 4 | **Medição**: 30 s, com saída em JSON | `docker compose --profile cliente run --rm cliente --server=redis -t 4 -c 12 -d 100 --pipeline=1 --ratio=<carga> --key-pattern=R:R --key-minimum=1 --key-maximum=100000 --test-time=30 --hide-histogram --print-percentiles=50,99 --json-out-file=/saidas/<execucao_id>.json` |
| 5 | Ler a memória do servidor, ainda ligado | `docker compose exec redis redis-cli INFO memory` (campo `used_memory`) |
| 6 | Parar e remover o contêiner | `docker compose --profile redis down` |
| 7 | Pausa de 5 s para a CPU se acalmar antes da próxima execução | — |

Para o Valkey, trocar `redis` por `valkey` e `redis-cli` por `valkey-cli`. A pré-carga é feita em **todas** as cargas, de modo que todas começam do mesmo estado (100.000 chaves já gravadas): na carga `set` os valores são sobrescritos, na `get` e na `misto` há o que ler.

Aquecimento de 10 s, medição de 30 s e pausa de 5 s foram mantidos pelo piloto (seção 11). A uma execução de cerca de um minuto (0,99 min no piloto), a coleta completa (2 servidores × 2 níveis de `io_threads` × 3 cargas × 40 repetições = 480 execuções) leva em torno de 8 horas, e o piloto (5 repetições, 60 execuções) levou cerca de 1 hora. O número de repetições vem da S01-09 ([analise-piloto.md](analise-piloto.md), seção 6).

**O que se grava.** O executor transforma cada execução em uma linha do CSV (colunas `execucao_id`, `ordem`, `servidor`, `versao`, `io_threads`, `carga`, `repeticao`, `ops_s`, `lat_p50_ms`, `lat_p99_ms`, `memoria_bytes`, `inicio`, `fim`) e guarda a saída bruta do cliente (JSON) em `dados/brutos/saidas/`. Execução que falha (contêiner não sobe, cliente cai) é registrada como falha, sem valor inventado: não entra no CSV, ganha uma linha em `falhas.csv` (etapa e mensagem) e é tentada de novo na próxima chamada do executor. As execuções já gravadas no CSV nunca são repetidas, então uma coleta interrompida é retomada com o mesmo comando.

## 7. Ordem das execuções

A ordem é **aleatorizada com a semente fixa do `config.yaml`** (`semente: 42`), para que o efeito do servidor não se confunda com o aquecimento da máquina ou com a deriva de temperatura. Cada repetição é um **bloco** com uma execução de cada uma das 12 combinações (2 servidores × 2 níveis × 3 cargas), em ordem sorteada dentro do bloco. Assim, qualquer mudança lenta na máquina atinge todas as combinações por igual, e há 40 blocos. A geração do plano está na Issue S01-07.

## 8. Limitações conhecidas do ambiente

- **Docker sobre WSL2 num notebook.** Temperatura, frequência da CPU, energia e outros processos do Windows podem variar. Os controles das seções 2.2 e 7 reduzem esse ruído, mas não o eliminam.
- **Hiperprocessamento e núcleos híbridos.** Na máquina designada (i7-13620H), servidor (`0-3`) e cliente (`4-7`) ocupam 8 das 16 CPUs lógicas da máquina virtual, que são 4 núcleos físicos do ponto de vista dos pares irmãos; as outras 8 ficam para o Windows e o Docker. O processador mistura núcleos de desempenho e de eficiência, e o protocolo **não controla** em quais deles as CPUs `0-7` da máquina virtual caem: isso pode variar a velocidade entre execuções e reduz o ganho observável das *threads* de I/O. Fica como ameaça à validade.
- **Rede.** Servidor e cliente conversam por TCP na rede virtual do Docker, e não por *loopback* direto. A latência medida inclui essa camada, igual para os dois servidores.
- **Valores absolutos.** Os ops/s e a latência não valem para outro hardware; valem a ordem entre os servidores e a razão entre as medianas.

## 9. Verificação do ambiente (antes do merge)

Teste **só de funcionamento**. **Não rodar o cliente de carga contra o servidor nesta etapa nem anotar números de vazão, latência ou memória:** o `cenario.md` registra que ninguém viu esses números antes da expectativa. Se algum número aparecer, registrar como adendo na seção 8 do `cenario.md`.

1. Instalar o Docker Desktop (com o WSL2) e conferir `docker run hello-world`. Anotar as versões na seção 2.1. *(Feito em 17/11/2026.)*
2. Subir cada servidor e conferir que responde e que a configuração é a mesma:

   ```bash
   cd lab05
   IO_THREADS=4 docker compose --profile redis up -d --wait redis
   docker compose exec redis redis-cli ping                    # PONG
   docker compose exec redis redis-cli config get io-threads   # 4
   docker compose exec redis redis-cli config get save         # vazio
   docker compose --profile redis down
   ```

   Repetir com `--profile valkey`, `valkey` e `valkey-cli`, e com `IO_THREADS=1`.
3. Conferir que o cliente existe e conhece as opções, sem conectar a nenhum servidor: `docker compose --profile cliente run --rm cliente --version` e `--help` (procurar `--ratio`, `--test-time`, `--json-out-file`).
4. Conferir com `docker compose --profile redis config` que o `cpuset` e as imagens aparecem como esperado.
5. *(Feito em 17/11/2026, ver a seção 3.)* As CPUs lógicas irmãs foram conferidas com `lscpu -e` no WSL, e os conjuntos de CPU padrão estão corretos.

### 9.1 Resultado da verificação (17 e 18/11/2026)

Feita com `docker compose` a partir de `lab05/`, sem rodar o cliente contra nenhum servidor e sem ler vazão, latência ou memória.

| Verificação | Resultado |
|---|---|
| Imagens baixadas com os digests do `compose.yaml` | Sim: `redis` (213 MB), `valkey/valkey` (174 MB) e `memtier_benchmark` (136 MB). Como foram baixadas por digest, a tag aparece como `<none>` em `docker images` |
| `docker compose config` | Imagens com `@sha256:` e `cpuset` de `0-3` (servidores) e `4-7` (cliente), como esperado |
| `PING` nos quatro tratamentos (`redis` e `valkey`, com `io_threads` 1 e 4) | `PONG` em todos |
| Configuração lida do servidor em execução | Igual nos quatro: `io-threads` = 1 ou 4 conforme o tratamento, `save` vazio, `appendonly` = `no`, `maxmemory` = 536870912, `maxmemory-policy` = `noeviction`, `protected-mode` = `no` |
| `cpuset` do contêiner do servidor e do cliente | `0-3` e `4-7` |
| Versão dos servidores | `redis_version:8.10.3` no Redis; `valkey_version:9.1.3` no Valkey |
| Cliente | `memtier_benchmark` 2.6.1 com as opções `--ratio`, `--test-time`, `--json-out-file`, `--print-percentiles`, `--hide-histogram`, `-d`, `--key-minimum`, `--key-maximum` e `--key-pattern` |
| Contêineres e rede ao final | Todos removidos |

**Observações para o executor (S01-07):**

- **A versão do Valkey vem de `valkey_version`.** O `INFO server` do Valkey 9.1.3 também traz `redis_version:7.2.4`, por compatibilidade. Ler esse campo no Valkey gravaria a versão errada na coluna `versao` do CSV.
- **Execução interrompida.** Durante a verificação, uma execução ficou parada e o contêiner permaneceu no ar por cerca de 22 horas: o computador provavelmente suspendeu. É o motivo do item 2 da seção 2.2 (suspensão desligada) e a razão de o executor poder retomar de onde parou e de remover contêineres antigos antes de começar.
- **Proporções com zero.** `--ratio=1:0` e `--ratio=0:1` foram conferidos só no código-fonte (seção 5). *Confirmado em 18/11/2026* na execução de exemplo do executor (S01-07, `dados/brutos/exemplo/`): na carga `set` o JSON do cliente traz 0 GET, na `get` 0 SET, e a `misto` fica perto de 1 SET para 4 GET; nenhum GET deu *miss*, o que confirma a pré-carga.

## 10. Decisões e o que mudou em relação ao planejamento

| Decisão | Planejamento | Este protocolo | Motivo |
|---|---|---|---|
| Cliente de carga | `redis-benchmark` 7.2.4 ou `memtier_benchmark` | `memtier_benchmark` 2.6.1 | Faz a carga mista e grava os percentis em JSON |
| Clientes | 50 | 48 (4 *threads* × 12) | 50 não divide por 4 *threads* |
| Entre execuções | `FLUSHALL` | Contêiner novo | `FLUSHALL` não devolve a memória do alocador; a Q4 mede memória |
| Ordem | Aleatorizada, alternando servidores | Blocos de 12 combinações em ordem sorteada | Distribui a deriva da máquina por igual |
| Conjunto de chaves | Não definido | 100.000 chaves, pré-carga antes de toda carga | Mesmo estado inicial nas três cargas |
| Máquina (S01-08) | Uma máquina designada | Notebook com i7-13620H, desde o piloto | O piloto foi rodado nele; a coleta completa precisa da mesma máquina |

O planejamento (seção 3.3, no PR 285) deve ser atualizado nos itens acima depois do merge.

## 11. Resultado do piloto (S01-08, 18/11/2026)

Detalhes em [`../dados/piloto/LEIA-ME.md`](../dados/piloto/LEIA-ME.md) e no relatório `../dados/piloto/qualidade-piloto.md`.

| Item | Resultado |
|---|---|
| Execuções | 60 de 60 (5 repetições × 12 combinações), nenhuma falha |
| Validação | Sem erros; 31 avisos de coeficiente de variação acima de 10% |
| Tempo total | 59,4 min (0,99 min por execução): a coleta completa prevista na época (30 repetições, 360 execuções) levaria cerca de 6 horas; com as 40 repetições decididas na S01-09 (480 execuções), cerca de 8 horas |
| Variabilidade | CV mediano de 11,9% (`ops_s`), 12,6% (`lat_p50_ms`) e 14,5% (`lat_p99_ms`); `memoria_bytes` quase constante (CV ≤ 0,04%) |
| Causa dos CV altos | Deriva da máquina entre blocos (bloco 2 cerca de 16% mais lento, blocos 4 e 5 cerca de 10% mais rápidos), igual em todas as combinações. Sem o efeito do bloco, o CV mediano cai para cerca de 6% a 7% |

**Ajustes feitos a partir do piloto:** a seção 2.2 ganhou o `docker ps` vazio, o modo de energia do Windows 11 e os 10 minutos de máquina ociosa; o registro de ambiente passou a gravar o modo de energia e a alimentação; a máquina designada mudou (seção 2.1). Os tempos de aquecimento (10 s), de medição (30 s) e de pausa (5 s) ficam como estão: nenhuma execução falhou e o tempo total coube no previsto. O número de repetições é decidido na S01-09, a partir do CV do piloto.
