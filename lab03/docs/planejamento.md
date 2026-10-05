# Lab03 — Planejamento das Sprints 01 a 03

Planejamento das sprints 01 a 03 do Lab03 (mineração de métricas DORA, *DevOps Research and Assessment*). As seções citadas entre parênteses referem-se ao enunciado do Lab03.

Siglas: RQ (*Research Question*, questão de pesquisa); CI (*Continuous Integration*, integração contínua); API (*Application Programming Interface*, interface de programação); CFR (*Change Failure Rate*, taxa de falha de mudanças); WIP (*Work in Progress*, trabalho em andamento); CSV (*Comma-Separated Values*, valores separados por vírgula); SBC (Sociedade Brasileira de Computação); HTTP (*Hypertext Transfer Protocol*).

## 1. Calendário

| Sprint | Período | Entrega |
|---|---|---|
| Lab03S01 | 02/10 a 08/10 (execução de 05/10 a 08/10) | Pipeline de coleta para 100 repositórios, testes, CI, introdução com hipóteses |
| Lab03S02 | 09/10 a 15/10 | Amostra ≥ 300 repositórios, métricas em todas as variantes, CSV com dicionário, validação manual, metodologia |
| Lab03S03 | 16/10 a 22/10 | Análise das RQ 01 a RQ 07 e da RQ 08, resultados e discussão |
| Apresentação | 23/10 | — |

## 2. Decisões

### 2.1 Escopo da coleta

As definições operacionais (janela, unidade de deploy, runs, critério de inclusão, censura) estão no [README](../README.md), seção "Definições adotadas".

| Tema | Decisão |
|---|---|
| Amostra da Sprint 01 | 100 repositórios aprovados no funil de seleção |
| Regra da amostra | Candidatos por estrelas decrescentes; a Sprint 02 continua a mesma regra até ≥ 300 aprovados, reaproveitando o cache da Sprint 01 |
| Coleta completa | Início em 09/10, na Sprint 02 |
| Tags | Funções de coleta na Sprint 01 (S01-09); execução na Sprint 02 (S02-03) |

### 2.2 Cálculo das métricas

| Tema | Decisão |
|---|---|
| Release sem commits novos | Fora do lead time; conta na frequência de deploy |
| Classificação DORA | Implementada e testada na Sprint 01 |
| Métrica indefinida na classificação | Categoria pela mediana das notas existentes, arredondada para baixo |
| RQ 07 | Combinações C1, C2 e C3 do enunciado; dados das variantes coletados na Sprint 02 |
| CFR (b) no dataset | Recalculado após o refino da heurística de release corretiva |
| RQ 08 (bônus) | *Rework rate*; evolução temporal é opcional, se sobrar tempo |

### 2.3 Implementação e processo

| Tema | Decisão |
|---|---|
| Linguagem | Python 3.12, com requisições HTTP próprias (`requests`) |
| Artigo | Template SBC em arquivos `.tex` em `lab03/artigo/`, compilados no Overleaf |
| Modelo de Issue | 11 campos |
| Atribuição | Sem papéis fixos: cada Issue é assumida, no dia previsto, por um integrante disponível |
| WIP | 1 Issue por integrante |
| Prazo | Dia indicado na tabela de Issues da sprint, com início e conclusão no mesmo dia |
| Definição de pronto | PR (*Pull Request*) mesclado e commits citando o número da Issue; em Issues de código, PR revisado e CI verde |
| Commits e branches | Mensagem `#<número da Issue> descrição`; branch `<número>-<descrição-curta>`; integração por PR |
| Quadro | GitHub Projects do grupo ([projeto 9](https://github.com/users/gabialvarenga/projects/9)) |

## 3. Sprint 01 — pipeline de coleta para 100 repositórios

### 3.1 Issues

| Issue | Tipo | Dia | Entregas (seção do enunciado) |
|---|---|---|---|
| S01-01 Escrever as hipóteses das RQ 01 a RQ 04 | artigo | 05/10 | Introdução com hipóteses (8, 10) |
| S01-02 Criar a estrutura do projeto e o CI | código | 05/10 | CI do grupo (7, 10) |
| S01-03 Escrever a introdução e as hipóteses das RQ 05 a RQ 08 | artigo | 05/10 | Introdução com hipóteses (8, 10) |
| S01-04 Criar a camada HTTP com cache, retomada e rate limit | código | 05/10 | Cache, retomada, rate limit, *backoff* (7, 10) |
| S01-05 Selecionar candidatos e coletar metadados | código | 06/10 | Seleção por busca fatiada, metadados (4, 10) |
| S01-06 Implementar e testar lead time e classificação DORA | código | 06/10 | Testes com fixtures (7); RQ 02 e classificação (5) |
| S01-07 Coletar workflow runs com subdivisão mensal | código | 06/10 | Workflow runs do *default branch* (4, 10) |
| S01-08 Gerar o funil de seleção e a frequência de deploy | código | 07/10 | Funil (7, 10); RQ 01 (5) |
| S01-09 Coletar releases, tags e commits entre releases | código | 07/10 | Releases, tags e commits (4, 10) |
| S01-10 Implementar e testar CFR (a) e tempo de recuperação | código | 07/10 | Testes com fixtures (7); RQ 03 (a) e RQ 04 (5) |
| S01-11 Integrar o pipeline e executar para 100 repositórios | código | 08/10 | Comando único, 100 repositórios (7, 10) |

### 3.2 Marcos

Cada Issue é assumida no dia previsto por um integrante disponível, com WIP de 1. Em 05/10, com quatro Issues para três integrantes, um integrante conclui duas em sequência. Ao longo da sprint, cada integrante assume ao menos uma Issue de código (seção 10).

1. **Fim de 05/10:** hipóteses (S01-01 e S01-03) commitadas; estrutura e CI (S01-02) e camada HTTP (S01-04) no `main`. Nenhuma chamada real à API ocorre antes disso (seção 8: hipóteses escritas antes de ver os dados).
2. **Fim de 07/10:** todo o código no `main`. A S01-11 integra e executa o pipeline para 100 repositórios em 08/10.

Cada Issue de código define no campo "Interface congelada" as assinaturas usadas por outras Issues. Uma Issue que depende de função ainda não mesclada é desenvolvida contra essa assinatura e testada com dados escritos à mão. A única espera da sprint é a integração (S01-11).

### 3.3 Riscos

| Risco | Efeito | Resposta |
|---|---|---|
| Primeiro marco no dia da criação das Issues (05/10) | Atraso das hipóteses, da estrutura ou da camada HTTP adia as chamadas reais | Issues criadas antes do início do trabalho; S01-02 e S01-04 limitadas aos critérios de aceite |
| Execução dos 100 repositórios concentrada em 08/10 | Rate limit interrompe a execução | Cache e retomada da S01-04; teste prévio com 5 repositórios |
| CI com `--cov-fail-under=80` sobre um módulo `metricas` ainda vazio | CI reprovado nos primeiros PRs (*Pull Requests*) | S01-02 entrega `metricas` com uma função mínima testada |

## 4. Sprint 02 — amostra completa, dataset e validação manual

| Issue | Dias |
|---|---|
| S02-01 Executar a coleta completa e gerar o dataset CSV | 09/10 a 11/10 |
| S02-02 Implementar a heurística corretiva e o CFR (b) | 09/10 a 11/10 |
| S02-03 Coletar e calcular as variantes da RQ 07 (pré-releases e tags) | 09/10 a 11/10 |
| S02-04 Sortear a amostra-ouro e gerar as planilhas de rotulagem | 11/10 |
| S02-05 Rotular a amostra-ouro (avaliador 1) | 12/10 a 13/10 |
| S02-06 Rotular a amostra-ouro (avaliador 2) | 12/10 a 13/10 |
| S02-07 Rotular a amostra-ouro (avaliador 3) | 12/10 a 13/10 |
| S02-08 Calcular o kappa de Fleiss e consolidar o consenso | 14/10 |
| S02-09 Escrever o dicionário de dados e a metodologia da coleta | 14/10 |
| S02-10 Escrever a metodologia: definições operacionais e variantes | 14/10 |
| S02-11 Avaliar a heurística (precisão, recall e F1) e recalcular o CFR (b) | 14/10 a 15/10 |
| S02-12 Escrever a metodologia: funil e protocolo de validação | 15/10 |

As Issues S02-05 a S02-07 são assumidas por integrantes distintos, sem consulta entre eles e sem acesso à saída da heurística (seção 6). A reunião de consenso, em 14/10, é a única etapa que reúne os três. Risco registrado: rotulagem de 300 releases por avaliador em dois dias.

Cegamento: a S02-02 é desenvolvida e testada só com fixtures escritas à mão, e entrega também o script de precisão, recall e F1, testado com rótulos fictícios. A heurística roda sobre dados reais pela primeira vez na S02-11, depois da rotulagem.

Folga do F1: o primeiro F1 sai até o fim de 14/10, logo após o consenso. O dia 15/10 fica para o refino, limitado a duas versões adicionais; se o F1 continuar abaixo de 0,70, o resultado é relatado como achado nas ameaças à validade.

## 5. Sprint 03 — análise

| Issue | Depende de |
|---|---|
| S03-01 Calcular a estatística descritiva das RQ 01 a RQ 04 | — |
| S03-02 Classificar os repositórios na combinação de referência (C1) | — |
| S03-03 Calcular a correlação de Spearman (RQ 05) | — |
| S03-04 Comparar subgrupos por fator (RQ 06) | — |
| S03-05 Executar a análise de sensibilidade (RQ 07) | — |
| S03-06 Calcular o *rework rate* (RQ 08) | — |
| S03-07 Calcular a evolução temporal (RQ 08, opcional) | — |
| S03-08 Escrever resultados e discussão das RQ 01 a RQ 04 | S03-01, S03-02 |
| S03-09 Escrever resultados e discussão das RQ 05, RQ 06 e do *rework rate* | S03-03, S03-04, S03-06 |
| S03-10 Escrever resultados e discussão da RQ 07 (e da evolução temporal, se feita) | S03-05 |

Todas as análises partem do CSV fechado na Sprint 02. As Issues de texto são concluídas até 22/10. As Issues das sprints 02 e 03 são detalhadas no início de cada sprint.
