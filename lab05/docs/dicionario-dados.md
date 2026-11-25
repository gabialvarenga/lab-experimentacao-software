# Lab05 — Dicionário de dados

Este documento descreve cada coluna e cada campo dos arquivos de uma coleta: `dados/brutos/`, que é a coleta completa usada na análise, e `dados/piloto/`, que tem o mesmo formato. O procedimento de cada execução está no [protocolo](protocolo-execucao.md), seção 6. A classificação das variáveis e as estatísticas permitidas estão no [plano de análise](plano-analise.md), seções 2 e 3. As condições e o hash da coleta completa estão em [`dados/brutos/LEIA-ME.md`](../dados/brutos/LEIA-ME.md).

Siglas: CSV (*Comma-Separated Values*); JSON (*JavaScript Object Notation*); ISO (*International Organization for Standardization*); CV (coeficiente de variação).

## 1. Convenções

- CSV em UTF-8, separado por vírgula, com ponto decimal e cabeçalho na primeira linha. As colunas e a ordem delas são fixas (`COLUNAS` em `lab05/executor.py`). O executor recusa um CSV com outro cabeçalho.
- Uma linha é uma **execução**: a combinação (servidor, `io_threads`, carga, repetição), rodada uma vez num contêiner novo.
- **Medida direta** é lida pronta do cliente ou do servidor. **Medida derivada** é calculada a partir de outras medidas (classificação de Fenton e Pfleeger, como no plano de análise).
- As execuções que falham não entram no CSV: vão para `falhas.csv` (seção 3). Nenhum valor é inventado.

## 2. `dados/brutos/execucoes.csv`

Uma linha por execução concluída. Na coleta completa são 480 linhas: 12 combinações × 40 repetições. O arquivo é gerado por `python -m lab05 executar` e as linhas ficam na ordem em que as execuções rodaram. No piloto, o arquivo equivalente é `dados/piloto/piloto.csv`, com 60 linhas.

### 2.1 Identificação e plano

| Coluna | Tipo | Unidade | Escala | Medida | Origem |
|---|---|---|---|---|---|
| `execucao_id` | texto | — | Nominal | Atribuída | `<servidor>-t<io_threads>-<carga>-r<repeticao com 2 dígitos>`, por exemplo `redis-t1-set-r01`. É único por execução e não depende da ordem sorteada. Também dá o nome ao JSON em `saidas/` |
| `ordem` | inteiro, de 1 a 480 | posição | Ordinal | Atribuída | Posição da execução no plano sorteado com `semente: 42` do `config.yaml`. A ordem é sorteada dentro de cada bloco e os blocos seguem a sequência das repetições. É usada na checagem de deriva (plano de análise, seção 7) |
| `servidor` | texto: `redis` ou `valkey` | — | Nominal | Atribuída | Fator do experimento (variável independente). É também o serviço do `compose.yaml` |
| `versao` | texto | — | Nominal | Direta | Campo `redis_version` (Redis) ou `valkey_version` (Valkey) do `INFO server`, lido depois que o servidor sobe. A validação exige `8.10.3` e `9.1.3`. O Valkey também traz `redis_version:7.2.4` por compatibilidade, e esse campo não é usado |
| `io_threads` | inteiro: `1` ou `4` | threads | Ordinal (2 níveis) | Atribuída | Fator do experimento, passado ao servidor como `--io-threads` pela variável `IO_THREADS` do `compose.yaml`. Entra nos modelos como fator, e não como número |
| `carga` | texto: `set`, `get` ou `misto` | — | Nominal | Atribuída | Bloco do experimento. Corresponde ao `--ratio` do `memtier_benchmark` (SET:GET): `set` = `1:0`, `get` = `0:1`, `misto` = `1:4` |
| `repeticao` | inteiro, de 1 a 40 | — | Ordinal | Atribuída | Número da repetição e, ao mesmo tempo, o **bloco**: cada repetição tem uma execução de cada uma das 12 combinações. É a chave da análise pareada por bloco (adendo da S02-01) |

### 2.2 Métricas (variáveis de resposta)

| Coluna | Tipo | Unidade | Escala | Medida | Origem |
|---|---|---|---|---|---|
| `ops_s` | decimal (2 casas) | operações por segundo | Razão | Direta | `ALL STATS` > `Totals` > `Ops/sec` do JSON da medição de 30 s: total de operações concluídas dividido pelo tempo, como o cliente reporta. É sempre > 0, porque uma execução com 0 operações vira falha. Pergunta Q1 |
| `lat_p50_ms` | decimal (3 casas) | milissegundos | Razão | Derivada | `ALL STATS` > `Totals` > `Percentile Latencies` > `p50.00`: a mediana da latência, tirada do histograma do cliente (`--print-percentiles=50,99`). Pergunta Q2 (descritiva) |
| `lat_p99_ms` | decimal (3 casas) | milissegundos | Razão | Derivada | Mesmo bloco, chave `p99.00`: o percentil 99 da latência. A validação exige `lat_p99_ms` ≥ `lat_p50_ms`. É medida pelo cliente, e não pelo servidor (armadilha 3 do plano de análise). Pergunta Q2 |
| `memoria_bytes` | inteiro | bytes | Razão | Direta | Campo `used_memory` do `INFO memory`, lido com o servidor ainda ligado, depois da medição, com as 100.000 chaves carregadas. É a memória alocada pelo servidor segundo ele mesmo, e não o RSS do processo. Pergunta Q4 |

A latência vem do `memtier_benchmark` já em milissegundos. O cliente arredonda os percentis pela resolução do histograma, por isso os valores se repetem em degraus de cerca de 0,008 ms.

### 2.3 Horários

| Coluna | Tipo | Unidade | Escala | Medida | Origem |
|---|---|---|---|---|---|
| `inicio` | data e hora ISO 8601, com fuso (`-03:00`) e precisão de segundos | — | Intervalar | Direta | Relógio da máquina antes de subir o contêiner (passo 1 do protocolo) |
| `fim` | idem | — | Intervalar | Direta | Relógio da máquina depois de ler a memória (passo 5) e antes de derrubar o contêiner e fazer a pausa |

`fim` − `inicio` cobre a subida, a pré-carga, o aquecimento, a medição e a leitura da memória. Na coleta completa ficou entre 48 e 54 s. Os horários não entram nos testes: servem para conferir interrupções e deriva.

## 3. `falhas.csv`

Este arquivo só existe se alguma tentativa falhou. Na coleta completa ele não existe, porque não houve falha. Cada linha é uma tentativa que falhou. A execução continua pendente e é tentada de novo na próxima chamada do executor.

| Coluna | Tipo | Origem |
|---|---|---|
| `execucao_id`, `ordem`, `servidor`, `io_threads`, `carga`, `repeticao` | como na seção 2 | Execução do plano que falhou |
| `etapa` | texto: `subida`, `versao`, `precarga`, `aquecimento`, `medicao`, `leitura` ou `memoria` | Etapa de `executar_uma` em que houve o erro |
| `erro` | texto | Mensagem do erro (do Docker, do cliente ou da leitura) |
| `inicio`, `fim` | data e hora ISO 8601 | Início da tentativa e momento da falha |

## 4. `saidas/<execucao_id>.json`

Saída bruta do `memtier_benchmark` 2.6.1 (`--json-out-file`) da medição de 30 s de cada execução. O aquecimento não é gravado. Os arquivos são guardados como estão, para que qualquer métrica possa ser conferida ou recalculada.

| Campo | Uso |
|---|---|
| `configuration` | Parâmetros com que o cliente rodou (threads, clientes, `ratio`, tempo, padrão de chaves). Serve para conferir que a execução seguiu o protocolo |
| `run information` | Informações da execução registradas pelo próprio cliente |
| `ALL STATS` > `Totals` > `Ops/sec` | Origem de `ops_s` |
| `ALL STATS` > `Totals` > `Percentile Latencies` > `p50.00`, `p99.00` | Origem de `lat_p50_ms` e `lat_p99_ms` |
| `ALL STATS` > `Totals` > `Percentile Latencies` > `Histogram log format` | Histograma completo da latência (formato HdrHistogram comprimido). Permite calcular outros percentis, se necessário |
| `ALL STATS` > `Sets`, `Gets` | As mesmas estatísticas separadas por tipo de comando. Não são usadas na análise |
| `ALL STATS` > `Totals` > `Connection Errors` | Erros de conexão do cliente. A validação confere que são 0 |
| Demais campos (`Hits/sec`, `Misses/sec`, `KB/sec`, `Average Latency`, `Max Latency`, `Time-Serie`, `CPU Stats`...) | Não são usados na análise e ficam só como registro |

## 5. Relatórios gerados

| Arquivo | Gerado por | Conteúdo |
|---|---|---|
| `registro-<data>.md` (piloto: `registro-piloto.md`) | `executar` | Ambiente da máquina e do Docker, imagens com digest e ID local, SHA-256 do `compose.yaml` e do `config.yaml`, plano e resumo de cada sessão (início, fim, concluídas e falhas). Uma seção nova é acrescentada a cada sessão |
| `qualidade-execucoes.md` (piloto: `qualidade-piloto.md`) | `validar` | Erros e avisos da validação (`lab05/validacao.py`) e, por combinação e métrica, o n, a mediana, o IQR e o CV, com ⚠ quando o CV passa de 10% |
| `LEIA-ME.md` | escrito à mão | Condições da coleta, eventos, resultado da validação, comparação com o piloto e o SHA-256 do CSV |
