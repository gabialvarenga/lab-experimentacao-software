# Metodologia de coleta — resiliência e teste de estresse (100 → 1000)

Documento de metodologia sobre a engenharia da coleta em si (não sobre RQs —
para hipóteses por RQ, ver [`hipoteses-informais.md`](hipoteses-informais.md)).
Registra dois problemas reais, descobertos rodando contra a API do GitHub de
verdade ao escalar de 100 (S01) para 1000 repositórios (S02), e como foram
resolvidos nas Issues #7 e #8.

## Problema 1 — paginação profunda + campos pesados causa timeout de gateway

**O que foi tentado:** a query única por cursor da S01 (`search`, paginando
com `first`/`after`), só que pedindo `first: 100` em vez de `first: 10`, para
reduzir o número de requisições necessárias para 1000 repositórios.

**O que quebrou:** `502 Bad Gateway` consistente, mesmo depois de reduzir o
tamanho da página. Testes empíricos isolados mostraram que o tamanho de
página sozinho não era a causa raiz:

| `first` | Comportamento isolado (offset 0) |
|---|---|
| 25 | OK, 6-8s |
| 30 | Borderline, 8-10s |
| 35 | Borderline, ~10s |
| 40+ | Falha (502) |

Só que, na paginação real por cursor, mesmo `first: 25` falhava já na 3ª
página (offset 50) — o tempo de resposta cresce com a **profundidade do
cursor**, não só com o tamanho da página:

| `first` | offset 0 | offset 40 | offset 75-80 |
|---|---|---|---|
| 15 | 4,3s | 5,8s | 8,1s |
| 20 | 6,5s | 9,2s | falha (502) |

**Causa raiz:** a busca paginada do GitHub (`search`) fica progressivamente
mais cara de resolver quanto mais fundo o cursor avança, e isso se combina
com o custo de resolver os 8 campos aninhados do `REPO_FIELDS` (issues,
licença, CI/CD, linguagens) por repositório — a soma dos dois estoura o
timeout do gateway bem antes de chegar em 1000. Dois testes de controle
confirmaram que a causa era a combinação, não cada fator isolado:
- Busca **enxuta** (só `nameWithOwner`, sem os campos pesados): testada até
  offset 900, sem nenhuma degradação (~3s estável em todas as páginas).
- Lookup **direto** por nome (`repository(owner, name)`, sem paginação de
  busca): testado em lote de 10 repositórios a partir do offset ~500, mesma
  velocidade que no offset 0 (~3,2s) — sem penalidade de profundidade.

**Solução:** separar a busca em duas fases.
1. **Busca enxuta** — pagina só os nomes (`nameWithOwner`), páginas de 100,
   sem sofrer o problema de profundidade.
2. **Enriquecimento em lote** — usa os nomes coletados para buscar os campos
   completos via `repository(owner, name)` com alias GraphQL, 10 por
   requisição.

**Resultado:** 110 requisições no total (10 da busca + 100 do
enriquecimento), 1000/1000 repositórios coletados sem nenhum erro,
consumindo cerca de 110 pontos de rate limit (de um orçamento de 5000/hora).

## Problema 2 — falha de rede não coberta pelo retry existente

**O que foi tentado:** rodar a coleta completa (1000 repositórios reais)
pela primeira vez, já com a correção do Problema 1 e com retry para erros
HTTP transitórios (502/503/504) e de rate limit (403/429 com `Retry-After`),
implementados na própria Issue #7.

**O que quebrou:** o script morreu no repositório 390/1000 com
`TypeError: fetch failed`, causado por `ECONNRESET` — uma queda de conexão
TCP no meio da requisição, não uma resposta HTTP de erro.

**Causa raiz:** o retry em `client.ts` só cobria erros que chegavam a ter
uma resposta HTTP (checava `error.status`). Uma falha de rede acontece
*antes* de qualquer resposta chegar — a exceção não tem `status`, então caía
fora da condição de retry e derrubava o script inteiro na primeira
ocorrência, não importa em qual dos 1000 repositórios acontecesse.

**Solução:** isolar a chamada `fetch()` num try/catch próprio, marcando
falhas de rede com uma flag distinta (`isNetworkError`) e tratando-as como
retryable — sem misturar com erros de lógica (GraphQL malformado, resposta
sem `data`, token ausente), que continuam falhando direto, para não mascarar
um bug real de configuração ou de query como se fosse uma falha transitória.

**Resultado:** nova execução completa depois da correção — 1000/1000
repositórios, zero erros, zero retries necessários.

## Nota final

Essa mesma paginação em duas fases e o retry com cobertura de falha de rede
são o que sustenta, sem intervenção manual, tanto `data/repositories.csv`
(Issue #8) quanto qualquer futura recoleta ou snapshot de sprint que rode
`npm run collect` contra a API real.
