# Dicionário de dados do Lab03

Este documento descreve cada coluna dos arquivos de dados do Lab03 (seção 7 do enunciado): nome, tipo, unidade e fórmula ou origem na API. Serve a quem for reproduzir o estudo e comparar resultados com os do grupo.

Os arquivos de `dados/saida/` são a saída do pipeline (`python -m pipeline --config config.yaml`); os de `dados/amostra/` e `dados/rotulagem/` preparam e registram a validação manual. Onde uma coluna depende de uma Issue ainda aberta, o texto diz qual.

## 1. Convenções

| Item | Regra |
|---|---|
| Formato | CSV em UTF-8, separador vírgula, primeira linha com os nomes das colunas |
| Tipos | `texto`, `inteiro`, `decimal` (ponto como separador, precisão completa) e `booleano` (`True` ou `False`) |
| Célula vazia | Valor **indefinido**, e não zero. Cada coluna diz em que caso isso acontece |
| Datas e horas | ISO 8601 em UTC (ex.: `2026-02-14T22:12:56+00:00`) |
| Janela de observação | 01/10/2025 a 30/09/2026, intervalo fechado, 365 dias (≈ 52,14 semanas) |
| Branch | Só o *default branch* de cada repositório |
| Data de um commit | `commit.author.date` |
| Deploy | Release com `draft = false` e `prerelease = false`, publicada na janela (`published_at`) |
| Execução de CI considerada | *Workflow run* com `event = push` no *default branch*, criado na janela |
| Sucesso e falha | `success` é sucesso; `failure`, `timed_out` e `startup_failure` são falha; qualquer outro valor (`cancelled`, `skipped`, `neutral`, `action_required`, `stale` ou vazio) é ignorado |

## 2. `dados/saida/funil.csv`

Tabela do funil de seleção: uma linha por etapa, com quantos repositórios entraram, quantos seguiram e o motivo de descarte dos demais. Cada linha tem `saida ≤ entrada`.

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `etapa` | texto | — | Nome da etapa |
| `entrada` | inteiro | repositórios | Repositórios que chegaram à etapa |
| `saida` | inteiro | repositórios | Repositórios que passaram da etapa |
| `motivo` | texto | — | Por que `entrada − saida` repositórios saíram |

Etapas, em ordem:

| Etapa | Motivo de descarte |
|---|---|
| `Candidatos examinados` | Não examinado: a execução parou no último aprovado. A `entrada` são os candidatos das faixas de estrelas já buscadas |
| `Com GitHub Actions` | Sem Actions (`GET /repos/{owner}/{repo}/actions/workflows` com `total_count = 0`) |
| `Coleta sem erro` | Erro da API em qualquer etapa da coleta; a etapa e o repositório ficam no log |
| `Releases na janela` | Menos de 5 deploys na janela |
| `Runs válidos na janela` | Menos de 50 runs de sucesso ou falha na janela |

`funil_subamostra.csv` (em `dados/coleta/fatia-N/`) tem as mesmas colunas, mas o funil de uma fatia começa nos repositórios do arquivo da fatia, e não nos candidatos da busca.

## 3. `dados/saida/repositorios.csv`

O dataset: uma linha por repositório aprovado no funil. `full_name` é a chave. As colunas aparecem na ordem abaixo.

O `repositorios.csv` versionado tem 30 colunas, na ordem das seções abaixo: as de metadados, contagens, métricas DORA e C1 (3.1 a 3.5), `rework_rate` (3.6) e as 10 de C2 e C3 (3.7). As 10 de C2 e C3 estão **preenchidas** nos 300 repositórios (coleta da Sprint 03, com `coleta.variantes_rq07: true`; seção 3.7). `cfr_b` e `rework_rate` usam a versão 3 da heurística de release corretiva (seção 5.4 e `docs/heuristica-corretiva.md`).

### 3.1 Metadados

| Coluna | Tipo | Unidade | Fórmula ou origem |
|---|---|---|---|
| `full_name` | texto | — | `owner/repo`. Origem: busca `GET /search/repositories` |
| `estrelas` | inteiro | estrelas | `stargazers_count` na data da busca; muda com o tempo |
| `linguagem` | texto | — | `language` da API (linguagem principal). Vazia quando a API não informa |
| `contribuidores` | inteiro | pessoas | Número da última página de `GET /repos/{owner}/{repo}/contributors?per_page=1&anon=true`, o que **inclui contribuidores anônimos**. Vazia quando a API se recusa a contar (resposta 4xx que não seja 404 ou erro da API) |
| `idade_dias` | inteiro | dias | Data de fim da janela (30/09/2026) − data de criação do repositório (`created_at`, em UTC) |

### 3.2 Contagens usadas no critério de inclusão

| Coluna | Tipo | Unidade | Fórmula ou origem |
|---|---|---|---|
| `n_deploys` | inteiro | releases | Releases com `draft` e `prerelease` falsos e `published_at` na janela. Origem: `GET /repos/{owner}/{repo}/releases` |
| `n_runs_validos` | inteiro | runs | Runs de `push` no *default branch*, criados na janela, com `conclusion` de sucesso ou falha. Origem: `GET /repos/{owner}/{repo}/actions/runs` |

### 3.3 Métricas DORA

| Coluna | Tipo | Unidade | Fórmula ou origem | Vazia quando |
|---|---|---|---|---|
| `frequencia_semana` | decimal | deploys por semana | RQ 01: `n_deploys ÷ (365 ÷ 7)` | Nunca (o critério exige ≥ 5 deploys) |
| `lead_time_a_h` | decimal | horas | RQ 02 (a): mediana, entre as releases, de `published_at − data do commit mais antigo` incluído na release | Nenhuma release entra no cálculo |
| `lead_time_b_h` | decimal | horas | RQ 02 (b): mediana, entre **todos** os commits de todas as releases, de `published_at − data do commit` | Nenhuma release entra no cálculo |
| `releases_ignoradas_404` | inteiro | releases | Releases que ficaram fora do lead time porque `GET /repos/{owner}/{repo}/compare/{anterior}...{release}` devolveu 404 (tag apagada ou reescrita) | Nunca (0 quando não houve) |
| `cfr_a` | decimal | fração de 0 a 1 | RQ 03 (a): `falhas ÷ (falhas + sucessos)` sobre os runs, com todos os workflows juntos. Mede falha de **CI**, não falha em produção | Nenhum run de sucesso ou falha |
| `cfr_b` | decimal | fração de 0 a 1 | RQ 03 (b): `releases que falharam ÷ releases avaliadas`, sobre os deploys da janela. Uma release R falha se a release seguinte sai em até 7 dias depois dela e é corretiva em relação a R (heurística de `metricas/corretiva.py`, versão 3). R só é avaliada quando os 7 dias seguintes cabem na janela (`published_at + 7 dias ≤ 30/09/2026`); as dos últimos 7 dias ficam fora do denominador (censura). Uma release seguinte com `compare` 404 não pode ser avaliada como corretiva e conta como não corretiva | Nenhuma release é avaliável (todos os deploys da janela estão nos últimos 7 dias; ocorre em 2 repositórios do dataset) |
| `recuperacao_mediana_h` | decimal | horas | RQ 04: mediana, entre os episódios **completos** de todos os workflows, de `updated_at do sucesso − run_started_at da primeira falha` (ver 3.4) | Nenhum episódio completo |

Regras comuns do lead time: o commit é o de `commit.author.date`; a primeira release do repositório (sem release anterior), a release com `compare` 404 e a release sem commits novos ficam fora do cálculo, nas duas variantes. A release anterior pode estar fora da janela.

### 3.4 Episódios de falha e censura

Os episódios são calculados **dentro de cada workflow**, sobre os runs de sucesso e falha em ordem cronológica. Um episódio começa na primeira falha depois de um sucesso e termina no próximo sucesso do mesmo workflow. Runs ignorados não abrem nem encerram episódios.

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `n_episodios` | inteiro | episódios | Todos os episódios de falha do repositório, **inclusive os censurados** |
| `n_censurados_direita` | inteiro | episódios | Falha sem sucesso posterior até o fim da janela |
| `n_censurados_esquerda` | inteiro | episódios | O workflow já começa a janela falhando, então o início real da falha é desconhecido. Cada episódio conta uma única vez, como censurado à esquerda, mesmo que também não se recupere |

A proporção de episódios censurados é `(n_censurados_direita + n_censurados_esquerda) ÷ n_episodios`. Episódios censurados não são descartados, mas só os completos entram na mediana de `recuperacao_mediana_h`.

### 3.5 Classificação DORA (combinação de referência, C1)

Cada métrica recebe uma nota (Elite 4, High 3, Medium 2, Low 1) pelos cortes abaixo, adaptados do relatório DORA e fixos para toda a turma.

| Métrica | Elite (4) | High (3) | Medium (2) | Low (1) |
|---|---|---|---|---|
| Frequência de deploy | ≥ 7 por semana | ≥ 1 e < 7 por semana | ≥ 1 por mês (≥ 12 ÷ 52,14 ≈ 0,23 por semana) e < 1 por semana | < 1 por mês |
| Lead time (mediana) | < 24 h | 24 h a < 168 h (1 semana) | 168 h a < 720 h (30 dias) | ≥ 720 h |
| CFR | ≤ 0,15 | > 0,15 e ≤ 0,30 | > 0,30 e ≤ 0,45 | > 0,45 |
| Tempo de recuperação (mediana) | < 1 h | 1 h a < 24 h | 24 h a < 168 h | ≥ 168 h |

| Coluna | Tipo | Unidade | Fórmula ou origem |
|---|---|---|---|
| `categoria_c1` | texto | — | `Elite`, `High`, `Medium` ou `Low`: mediana das notas das métricas definidas, arredondada para baixo. C1 usa a frequência por release, o lead time (a), o CFR (a) e a recuperação (`frequencia_semana`, `lead_time_a_h`, `cfr_a`, `recuperacao_mediana_h`) |
| `n_metricas_classificadas` | inteiro | métricas | Quantas das 4 métricas estavam definidas e entraram na mediana (3 ou 4 no dataset). Métrica vazia não recebe nota, em vez de contar como a pior |

### 3.6 Coluna `rework_rate` (RQ 08)

| Coluna | Tipo | Unidade | Fórmula ou origem | Vazia quando |
|---|---|---|---|---|
| `rework_rate` | decimal | fração de 0 a 1 | `releases corretivas ÷ releases avaliadas`, sobre os deploys da janela, com a heurística de `metricas/corretiva.py` (versão 3). Só entram as releases com mensagens de commit conhecidas: a primeira release da história e as de `compare` 404 ficam fora do numerador e do denominador. Diferente do `cfr_b`, conta as próprias releases corretivas, inclusive as publicadas depois do prazo de 7 dias, e não tem censura dos últimos 7 dias | Nenhuma release tem mensagens conhecidas |

### 3.7 Colunas de C2 e C3 (RQ 07)

São calculadas para a análise de sensibilidade da RQ 07 (C2: releases e pré-releases, lead time (b) e CFR (b); C3: tags, lead time (b) e CFR (a); o tempo de recuperação é o de C1 nas três). Ficaram vazias no CSV congelado da Sprint 02 e foram preenchidas na Sprint 03 (S03-07), nos 300 repositórios; as colunas de C1 não mudaram. Definições da #161 (mesclada). A opção `coleta.variantes_rq07` do `config.yaml` liga e desliga a coleta: com `true` (padrão quando ausente e valor atual do repositório) elas são preenchidas; com `false`, o pipeline não consulta a API para elas e as dez colunas saem vazias.

Células vazias que sobram, por falta de dado e não por falha de coleta: `lead_time_b_h_c2`, `cfr_b_c2` e `categoria_c2` ficam vazias em `zed-industries/zed` (a API devolve HTTP 422 numa comparação de tags, e o pipeline deixa essas colunas de C2 vazias), e cinco colunas de C3 ficam vazias em `docling-project/docling` (HTTP 422 nas tags). Esses dois erros não entram no cache, então um rerun só pelo cache também recebe o erro e reproduz as mesmas células vazias. As demais vazias seguem as regras de cada coluna (por exemplo, sem releases corretivas não há tempo de recuperação).

| Coluna | Tipo | Unidade | Fórmula ou origem |
|---|---|---|---|
| `n_prereleases` | inteiro | releases | Pré-releases (`prerelease = true`, `draft = false`) publicadas na janela |
| `n_tags_janela` | inteiro | tags | Tags cuja data (`commit.author.date` do commit apontado) cai na janela. Origem: GraphQL |
| `tags_ignoradas_404` | inteiro | tags | Tags fora do lead time porque o `compare` com a tag anterior devolveu 404 |
| `frequencia_semana_c2` | decimal | deploys por semana | `(n_deploys + n_prereleases) ÷ (365 ÷ 7)` |
| `lead_time_b_h_c2` | decimal | horas | Lead time (b) usando releases e pré-releases como deploys |
| `cfr_b_c2` | decimal | fração de 0 a 1 | CFR (b) usando releases e pré-releases como deploys, com a mesma heurística e a mesma regra de censura do `cfr_b` |
| `frequencia_semana_c3` | decimal | deploys por semana | `n_tags_janela ÷ (365 ÷ 7)` |
| `lead_time_b_h_c3` | decimal | horas | Lead time (b) usando tags como deploys; a data da tag é a do commit apontado |
| `categoria_c2` | texto | — | Classificação com `frequencia_semana_c2`, `lead_time_b_h_c2`, `cfr_b_c2` e `recuperacao_mediana_h` |
| `categoria_c3` | texto | — | Classificação com `frequencia_semana_c3`, `lead_time_b_h_c3`, `cfr_a` e `recuperacao_mediana_h` |

## 4. `dados/amostra/`

Arquivos da sondagem de 11/10/2026, feita antes do download completo dos runs (ver `dados/amostra/README.md`). São uma previsão; o dataset é o `repositorios.csv`.

### 4.1 `sondagem.csv`

Os 774 candidatos examinados, em ordem de estrelas decrescentes.

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `posicao` | inteiro | — | Posição do candidato na busca por estrelas (a partir de 1) |
| `full_name` | texto | — | `owner/repo` |
| `estrelas` | inteiro | estrelas | `stargazers_count` na data da sondagem |
| `usa_actions` | booleano | — | `True` se o repositório tem workflows |
| `deploys_janela` | inteiro | releases | Deploys na janela |
| `runs_validos_previstos` | inteiro | runs | Runs de `push` de sucesso ou falha previstos pelas contagens da API, que param em 2.500 por `status`: **2.500 ou 5.000 significam "pelo menos isso"**. Vazia quando o candidato foi descartado antes da contagem de runs |
| `resultado` | texto | — | `aprovado previsto`, `menos de 5 releases`, `sem Actions` ou `menos de 50 runs` |

### 4.2 `amostra_prevista.csv`

Os 300 primeiros aprovados previstos, que servem de fila fixa para o sorteio da amostra-ouro.

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `ordem` | inteiro | — | De 1 a 300, em ordem de estrelas |
| `posicao` | inteiro | — | Posição do candidato na busca (como em `sondagem.csv`) |
| `full_name` | texto | — | `owner/repo` |
| `estrelas` | inteiro | estrelas | `stargazers_count` na data da sondagem |
| `deploys_janela` | inteiro | releases | Deploys na janela |
| `runs_validos_previstos` | inteiro | runs | Como em `sondagem.csv` (2.500 ou 5.000 indicam "pelo menos isso") |

`fatia-1.txt` a `fatia-3.txt` e `reservas.txt` não são CSV: têm um `owner/repo` por linha, no formato do argumento `--repos` do pipeline (as fatias dividem os 300 repositórios; `reservas.txt` traz os aprovados previstos de 301 a 330).

## 5. `dados/rotulagem/`

Arquivos da validação manual (amostra-ouro). Os critérios de rotulagem, o cegamento e o consenso estão em [protocolo-rotulagem.md](protocolo-rotulagem.md).

### 5.1 `amostra_ouro.csv`

Uma linha por release sorteada dos 65 repositórios (60 da amostra e 5 de reserva), com semente fixa, a partir de `amostra_prevista.csv`.

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `ordem_sorteio` | inteiro | — | Ordem do repositório no sorteio |
| `papel` | texto | — | `amostra`, `reserva`, `substituído` ou `descartado`. Os dois últimos só aparecem se um sorteado saiu do dataset (comando `analise.sorteio` com `--aprovados`) |
| `full_name` | texto | — | `owner/repo` |
| `tag_name` | texto | — | Tag da release sorteada |
| `published_at` | texto | data e hora UTC | Data de publicação da release |
| `url_release` | texto | URL | Página da release no GitHub |
| `url_compare` | texto | URL | Comparação com o deploy anterior. Vazia na primeira release da história do repositório |

### 5.2 `avaliador_1.xlsx`, `avaliador_2.xlsx` e `avaliador_3.xlsx`

Uma planilha por avaliador, com os mesmos 60 repositórios e 300 releases e duas abas. As colunas `full_name`, `url`, `tag_name`, `url_release` e `url_compare` são geradas pelo script; as demais são preenchidas pelo avaliador, sem célula vazia nas colunas de rótulo.

Aba `repositorios` (60 linhas):

| Coluna | Tipo | Valores aceitos |
|---|---|---|
| `full_name` | texto | `owner/repo` |
| `url` | texto | URL do repositório |
| `tipo_projeto` | texto | `biblioteca/framework`, `aplicação/serviço`, `ferramenta CLI`, `outro` |
| `entregas_reais` | texto | `sim`, `não`, `incerto` |
| `observacao` | texto | Texto livre; obrigatória quando `entregas_reais` é `incerto` e quando o rótulo veio da regra de dúvida |

Aba `releases` (300 linhas):

| Coluna | Tipo | Valores aceitos |
|---|---|---|
| `full_name` | texto | `owner/repo` |
| `tag_name` | texto | Tag da release |
| `url_release` | texto | URL da página da release |
| `url_compare` | texto | URL da comparação com a release anterior; vazia na primeira |
| `corretiva` | texto | `sim`, `não` (não aceita `incerto`) |
| `observacao` | texto | Texto livre |

### 5.3 `kappa.csv`, `divergencias.csv` e `consenso.csv`

Gerados por `python -m analise.concordancia` (#160) a partir das três planilhas, depois que as três foram commitadas. O kappa é calculado sobre os **rótulos individuais**, antes do consenso. As três dimensões são `tipo_projeto` e `entregas_reais` (nível repositório, 60 itens cada) e `corretiva` (nível release, 300 itens).

`kappa.csv` (3 linhas, uma por dimensão):

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `dimensao` | texto | — | `tipo_projeto`, `entregas_reais` ou `corretiva` |
| `kappa` | decimal | de −1 a 1 | Kappa de Fleiss entre os três avaliadores (`statsmodels`, `aggregate_raters` e `fleiss_kappa`). Vazio quando todos os itens têm o mesmo rótulo, porque o kappa é 0/0 |
| `interpretacao` | texto | — | Faixa de Landis e Koch (1977): `pobre` (< 0), `leve` (0 a 0,20), `razoável` (0,21 a 0,40), `moderada` (0,41 a 0,60), `substancial` (0,61 a 0,80), `quase perfeita` (0,81 a 1) ou `indefinido` |

`consenso.csv` (uma linha por item e dimensão; 420 linhas: 60 + 60 + 300):

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `dimensao` | texto | — | Dimensão rotulada |
| `full_name` | texto | — | `owner/repo` |
| `tag_name` | texto | — | Tag da release. Vazia nas dimensões de nível repositório |
| `avaliador_1`, `avaliador_2`, `avaliador_3` | texto | — | Rótulo dado por cada avaliador, como na planilha dele |
| `situacao` | texto | — | `3-0` (os três concordam), `2-1` (dois concordam) ou `1-1-1` (os três divergem) |
| `consenso` | texto | — | Rótulo final do item. Na geração, é o rótulo da maioria em `3-0` e `2-1`, e fica **vazio em `1-1-1`**, que é decidido na reunião de consenso (desempate na seção 6 do protocolo). Depois da reunião, é atualizado nos itens em que a decisão difere da maioria |
| `reuniao` | booleano | — | `True` nos itens `1-1-1`, que precisam ser decididos na reunião |
| `justificativa` | texto | — | Vazia na geração. Depois da reunião, traz a justificativa dos itens cuja decisão difere da proposta da maioria e dos itens `1-1-1` |

`divergencias.csv` tem as linhas de `consenso.csv` cuja `situacao` não é `3-0`, **sem** as colunas `consenso` e `justificativa`. Colunas: `dimensao`, `full_name`, `tag_name`, `avaliador_1`, `avaliador_2`, `avaliador_3`, `situacao` e `reuniao`, com o mesmo significado de `consenso.csv`.

O `consenso.csv` versionado já inclui as quatro decisões da reunião de 15/10, que diferem da proposta da maioria e têm `justificativa` preenchida: `jestjs/jest` (`tipo_projeto`), `supabase/supabase` (`entregas_reais`), `babel/babel` `v7.29.3` e `spring-projects/spring-boot` `v4.0.3` (`corretiva`).

### 5.4 `versoes_heuristica.csv`

Gerado por `python -m analise.avaliar_heuristica --versao N` (#168): avalia a heurística de release corretiva (`metricas/corretiva.py`) contra a dimensão `corretiva` do `consenso.csv`, sobre as 300 releases da amostra-ouro. Uma linha por versão testada; rodar de novo a mesma versão substitui a linha dela. A classe positiva é "corretiva".

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `versao` | inteiro | — | Número da versão da heurística |
| `regra` | texto | — | Descrição da regra da versão (resumo; o texto completo está em `docs/heuristica-corretiva.md`) |
| `n` | inteiro | releases | Releases avaliadas (300) |
| `vp`, `fp`, `fn` | inteiro | releases | Verdadeiros positivos, falsos positivos e falsos negativos contra o consenso |
| `precisao` | decimal | de 0 a 1 | `vp ÷ (vp + fp)`. Vazia quando a heurística não marca nenhuma release |
| `recall` | decimal | de 0 a 1 | `vp ÷ (vp + fn)`. Vazio quando o consenso não tem nenhuma corretiva |
| `f1` | decimal | de 0 a 1 | `2·vp ÷ (2·vp + fp + fn)` (média harmônica de precisão e recall) |

Versões registradas no repositório (F1 contra o consenso, em 300 releases):

| Versão | Precisão | Recall | F1 |
|---|---|---|---|
| 1 | 0,264 | 0,973 | 0,415 |
| 2 | 0,520 | 0,726 | 0,606 |
| 3 | 0,632 | 0,658 | 0,644 |

A versão 3 é a usada em `cfr_b`, `rework_rate` e `cfr_b_c2`. Ela não atinge a meta de 0,70 do enunciado, e o resultado entra nas ameaças à validade. As regras de cada versão estão em `docs/heuristica-corretiva.md`.

## 6. Outros arquivos

| Arquivo | Descrição |
|---|---|
| `dados/coleta/fatia-N/repositorios_subamostra.csv` e `funil_subamostra.csv` | Saídas de cada execução da coleta por fatia, com as mesmas colunas do dataset e do funil. Em `estrelas` e `linguagem`, valem os valores do dia da execução, e não os do dia da busca. **Não são o dataset** |
| `dados/snapshots/lab03-s01.csv` | Retrato do quadro do GitHub Projects ao fim da Sprint 01, com uma linha por cartão (colunas abaixo) |

Colunas dos arquivos de `dados/snapshots/`:

| Coluna | Tipo | Descrição |
|---|---|---|
| `numero` | inteiro | Número da Issue ou do *pull request* |
| `titulo` | texto | Título do cartão |
| `tipo` | texto | Tipo do cartão (ex.: `Issue`) |
| `status` | texto | Coluna do quadro (ex.: `Done`) |
| `url` | texto | Endereço do cartão no GitHub |

## 7. `analise/saida/`

Tabelas gravadas pelos scripts de análise (`python -m analise.<nome>`), todas regeradas a partir de `dados/saida/repositorios.csv`. Os `.png` da pasta são figuras e não têm colunas. Os decimais usam ponto, e célula vazia quer dizer que a coluna não se aplica à linha. CFR e proporções estão em fração de 0 a 1.

### 7.1 `descritiva.csv`, `faixas_por_metrica.csv` e `categorias_c1.csv` (RQ 01 a 04)

`descritiva.csv`, uma linha por métrica (`frequencia_semana`, `lead_time_a_h`, `lead_time_b_h`, `cfr_a`, `cfr_b`, `recuperacao_mediana_h` e `proporcao_censurada`):

| Coluna | Tipo | Unidade | Descrição |
|---|---|---|---|
| `metrica` | texto | — | Nome da coluna de `repositorios.csv`, ou `proporcao_censurada` (censurados ÷ `n_episodios` de cada repositório, seção 3.4) |
| `n` | inteiro | repositórios | Repositórios com a métrica definida |
| `n_indefinido` | inteiro | repositórios | Repositórios com a métrica vazia |
| `mediana`, `q1`, `q3` | decimal | unidade da métrica | Mediana e quartis, com interpolação linear |
| `minimo`, `maximo` | decimal | unidade da métrica | Menor e maior valor |

`faixas_por_metrica.csv`, uma linha por métrica: `metrica` (texto) e as colunas `Elite`, `High`, `Medium` e `Low` (inteiros), com os repositórios que caem em cada faixa pelos cortes da seção 3.5, e `indefinido` (inteiro), com os que não têm a métrica. Os valores são lidos do CSV sem perda de precisão: um repositório com 12 releases na janela está exatamente no corte entre *Medium* e *Low*.

`categorias_c1.csv`: `categoria` (`Elite`, `High`, `Medium` ou `Low`) e `n_repositorios` (inteiro), com a distribuição da coluna `categoria_c1`.

### 7.2 `rq05.csv` (RQ 05)

Uma linha por variante do CFR.

| Coluna | Tipo | Descrição |
|---|---|---|
| `variante` | texto | `cfr_a` ou `cfr_b`, correlacionada com `frequencia_semana` |
| `n` | inteiro | Repositórios com os dois valores definidos |
| `n_excluidos` | inteiro | Repositórios fora do par por valor indefinido |
| `n_y_zero` | inteiro | Repositórios com CFR igual a 0, que geram empates (posto médio) |
| `rho` | decimal | ρ de Spearman |
| `p_valor` | decimal | p-valor bilateral de `scipy.stats.spearmanr` |
| `direcao` | texto | `positiva` ou `negativa` |
| `interpretacao` | texto | Magnitude de Cohen (1988): \|ρ\| < 0,1 desprezível; < 0,3 fraca; < 0,5 moderada; senão forte |

### 7.3 `rq06.csv` e `rq06_grupos.csv` (RQ 06)

`rq06.csv`, uma linha por combinação de fator e métrica:

| Coluna | Tipo | Descrição |
|---|---|---|
| `fator` | texto | `linguagem`, `estrelas`, `contribuidores`, `idade` ou `tipo_projeto` (os três do meio em quartis) |
| `metrica` | texto | `frequencia_semana`, `lead_time_a_h`, `cfr_a` ou `recuperacao_mediana_h` |
| `status` | texto | `ok`, ou `sem grupos suficientes` quando restam menos de 2 grupos com ao menos 5 valores (o teste não é feito) |
| `teste` | texto | `kruskal` (3 ou mais grupos) ou `mannwhitney` (2 grupos) |
| `n` | inteiro | Repositórios que entram no teste |
| `n_grupos` | inteiro | Grupos que entram no teste |
| `grupos` | texto | Cada grupo e o seu n, no formato `grupo:n`, separados por `\|` |
| `n_excluidos` | inteiro | Repositórios fora do teste por valor indefinido ou por grupo pequeno |
| `estatistica` | decimal | H do Kruskal-Wallis ou U₁ do Mann-Whitney |
| `p_bruto`, `p_holm` | decimal | p-valor do teste e p-valor corrigido por Holm sobre todos os testes executados |
| `significativo_holm` | lógico | `True` quando `p_holm` < 0,05 |
| `tipo_efeito` | texto | `epsilon2` (ε² = H ÷ (n − 1)) ou `cliff_delta` (δ = 2·U₁ ÷ (n₁·n₂) − 1) |
| `tamanho_efeito` | decimal | Valor do tamanho de efeito |
| `interpretacao_efeito` | texto | Para ε², Tomczak e Tomczak (2014): < 0,01 desprezível; < 0,08 pequeno; < 0,26 médio; senão grande. Para δ, Romano et al. (2006): \|δ\| < 0,147 desprezível; < 0,33 pequeno; < 0,474 médio; senão grande |

`rq06_grupos.csv`, uma linha por grupo de cada fator e métrica: `fator`, `metrica`, `grupo`, `n` (inteiro), `mediana`, `q1` e `q3` (decimais, na unidade da métrica) e `faixa` (texto `mínimo-máximo` do valor do fator no quartil, vazia nos fatores categóricos).

### 7.4 `rq07.csv`, `rq07_metricas.csv`, `rq07_categorias.csv` e `rq07_matrizes.csv` (RQ 07)

`rq07.csv`, uma linha por par de combinações:

| Coluna | Tipo | Descrição |
|---|---|---|
| `combinacao_x`, `combinacao_y` | texto | As duas combinações (`c1`, `c2` ou `c3`) |
| `n` | inteiro | Repositórios com a categoria definida nas duas |
| `n_excluidos` | inteiro | Repositórios fora do par por categoria indefinida |
| `n_mudaram`, `pct_mudanca` | inteiro, decimal | Repositórios que mudam de categoria, e o percentual (de 0 a 100) |
| `n_melhor`, `n_pior` | inteiro | Quantos sobem ou descem de `x` para `y` |
| `n_vizinha` | inteiro | Mudanças de uma só categoria |
| `kappa_linear` | decimal | Kappa de Cohen ponderado linear; vazio quando indefinido (uma só categoria nos dois lados) |
| `interpretacao` | texto | Faixa de Landis e Koch (1977) |

`rq07_metricas.csv`, uma linha por métrica (`frequencia`, `lead_time` ou `cfr`) e par: `metrica`, `combinacao_x`, `combinacao_y`, `n`, `n_mudaram`, `pct_mudanca`, `n_melhor` e `n_pior` (como acima, mas sobre a nota da métrica, e não sobre a categoria geral), e `mediana_x` e `mediana_y` (decimais, a mediana dos valores definidos de cada combinação). Só existe quando o CSV traz as colunas de C2 e C3.

`rq07_categorias.csv`: `combinacao`, `categoria` e `n` (repositórios em cada categoria de cada combinação).

`rq07_matrizes.csv`: matriz de transição de cada par em formato longo, com `combinacao_x`, `combinacao_y`, `de` (categoria em `x`), `para` (categoria em `y`) e `n`.

### 7.5 `rq08.csv` (RQ 08)

Uma linha por métrica (`rework_rate` e `cfr_b`). As colunas do par só são preenchidas na linha do `rework_rate`.

| Coluna | Tipo | Descrição |
|---|---|---|
| `metrica` | texto | `rework_rate` ou `cfr_b` |
| `n`, `n_indefinido`, `n_zero` | inteiro | Repositórios com valor definido, com valor vazio e com valor igual a 0 |
| `mediana`, `q1`, `q3`, `iqr`, `minimo`, `maximo` | decimal | Distribuição da métrica, em fração de 0 a 1 |
| `comparado_com` | texto | Métrica contra a qual o `rework_rate` é comparado (`cfr_b`) |
| `n_pares`, `n_excluidos` | inteiro | Repositórios com as duas métricas definidas, e os que ficam fora |
| `rho`, `p_valor_spearman`, `direcao`, `interpretacao_rho` | decimal, decimal, texto, texto | Correlação de Spearman entre as duas, com a magnitude de Cohen (como em 7.2) |
| `n_maior`, `n_menor`, `n_empates` | inteiro | Pares em que o `rework_rate` é maior, menor ou igual ao CFR (b) |
| `w_mais`, `p_valor_wilcoxon` | decimal | Estatística W⁺ e p-valor do teste de Wilcoxon pareado unilateral (H1: `rework_rate` > `cfr_b`), com os empates descartados |
| `rank_biserial`, `interpretacao_rank_biserial` | decimal, texto | Correlação rank-biserial pareada, como tamanho de efeito, e a sua magnitude |
| `versao_heuristica`, `precisao_heuristica`, `recall_heuristica`, `f1_heuristica` | inteiro, decimal | Versão da heurística de release corretiva e a sua precisão, recall e F1 contra o consenso (seção 5.4). São os mesmos nas duas linhas, porque as duas métricas dependem da mesma heurística |
