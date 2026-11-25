# Coleta completa (S02-03 e S02-04)

Plano completo: 40 repetições de cada uma das 12 combinações (2 servidores × 2 níveis de `io_threads` × 3 cargas), ou seja, 480 execuções. Elas foram agrupadas em 40 blocos (um por repetição) e rodadas em ordem sorteada com a semente 42. Os tempos seguem o protocolo: aquecimento de 10 s, medição de 30 s e pausa de 5 s. **Estes são os dados da análise final.** O código usado foi o da tag `lab05-coleta-congelada` (commit `d770186`).

```bash
python -m lab05 executar
python -m lab05 validar
```

| Arquivo | Conteúdo |
|---|---|
| `execucoes.csv` | 480 linhas no formato da S01-07; as colunas estão descritas em [`docs/dicionario-dados.md`](../../docs/dicionario-dados.md) |
| `registro-2026-11-24.md` | Ambiente e resumo da sessão (gerado pelo executor) |
| `qualidade-execucoes.md` | Relatório de qualidade (gerado pelo `validar`) |
| `saidas/*.json` | Saída bruta do `memtier_benchmark` de cada execução (480 arquivos) |
| `exemplo/` | Execução curta de exemplo da S01-07. **Não é dado do experimento** (ver o LEIA-ME da pasta) |

## Integridade

SHA-256 de `execucoes.csv`:

```
e7ce9d81f951928c63f2ddd14579e659fe18ae91d797cc3d0a55d3e78355234d
```

O hash é do arquivo com fim de linha LF, que é como ele está no git. Num clone no Windows com `core.autocrlf=true`, o arquivo da pasta pode vir com CRLF e dar outro hash. Para conferir o arquivo do repositório, rode a partir da raiz do repositório:

```bash
git show HEAD:lab05/dados/brutos/execucoes.csv | sha256sum
```

Este CSV é a entrada fixa da análise (S02-06 e S02-07). Se ele mudar depois do merge, o hash acima precisa ser atualizado e a mudança explicada aqui.

## Condições da coleta (24/11/2026, 23h24, a 25/11/2026, 06h51)

- **Máquina:** a designada no protocolo (seção 2.1), a mesma do piloto: Intel Core i7-13620H (16 CPUs lógicas), 23,7 GiB, Windows 11, Docker Desktop 4.67.0 com WSL 2.6.3. O registro de ambiente tem os detalhes.
- **Preparação da seção 2.2, conferida antes de começar:**
  - notebook na tomada e modo de energia "Melhor desempenho" (os dois estão gravados no registro);
  - `docker ps` vazio (os contêineres de outros projetos estavam parados);
  - programas do dia a dia fechados e `git status` limpo;
  - `git describe` igual a `lab05-coleta-congelada`.
- **Teste antes da coleta:** 1 repetição (12 execuções), das 23h01 às 23h14, com 0 falhas e 0 erros na validação. A pasta do teste foi retirada e não faz parte destes dados.
- **Máquina ociosa:** 10 minutos parada (23h14 a 23h24) antes da primeira execução, como pede o protocolo.
- **Horários:** a sessão começou às 23h24min27s; a primeira execução às 23h24min32s; a última terminou às 06h51min20s. Tempo total de 446,8 min (0,84 min por execução, contra 0,99 min no piloto).
- **Eventos:** nenhuma interrupção nem retomada. O intervalo entre o fim de uma execução e o início da próxima ficou entre 5 e 6 s nas 479 transições (pausa de 5 s). Cada execução durou entre 48 e 54 s. Ninguém usou a máquina durante a coleta.

O diário da coleta está na Issue #297.

## Resultado da validação

- **Sem erros e sem avisos.** Das 480 execuções do plano, 480 foram gravadas, sem nenhuma falha (por isso não há `falhas.csv`).
- Versões: 8.10.3 nas 240 execuções do Redis e 9.1.3 nas 240 do Valkey.
- `lat_p99_ms` ≥ `lat_p50_ms` em todas as execuções; não houve valor vazio nem métrica nula.
- Nenhuma execução precisou ser refeita.

## Variabilidade comparada com o piloto

| Métrica | CV mediano no piloto | CV mediano na coleta | CV máximo na coleta |
|---|---|---|---|
| `ops_s` | 11,9% | 0,9% | 2,0% |
| `lat_p50_ms` | 12,6% | 1,1% | 2,2% |
| `lat_p99_ms` | 14,5% | 1,4% | 2,1% |
| `memoria_bytes` | 0,01% | 0,02% | 0,04% |

(O CV é calculado por combinação, sobre as 5 repetições do piloto e as 40 da coleta.)

**Deriva entre blocos.** Para medir a deriva, cada medida foi dividida pela mediana da sua combinação e depois se tirou a média por bloco:

| | Piloto | Coleta |
|---|---|---|
| Faixa de `ops_s` relativa por bloco | 0,842 a 1,098 | 0,987 a 1,005 |
| Faixa de `lat_p99_ms` relativa por bloco | 0,912 a 1,228 | 0,994 a 1,014 |
| Correlação entre ordem e `ops_s` relativa | 0,55 | 0,02 |

A variação entre blocos que marcou o piloto (seção "Investigação dos avisos de CV" em [`../piloto/LEIA-ME.md`](../piloto/LEIA-ME.md)) não se repetiu. Isso combina com a causa provável apontada no piloto: um estado da máquina que mudou durante a coleta, depois de parar contêineres pesados logo antes de começar. Os ajustes de preparação (nenhum contêiner ligado e 10 minutos de máquina ociosa) são a explicação mais provável para a melhora, embora a coleta não tenha medido isso diretamente.

**Consequência para a análise:** com CV de 1% a 2%, o poder das 40 repetições fica bem acima do previsto na S01-09. Aquela conta usou o CV bruto do piloto e chegou a uma diferença detectável de cerca de 14% em `ops_s`. A variância menor não muda o plano de análise, que está congelado: os testes, os tamanhos de efeito e o limiar de 5% continuam os mesmos.
