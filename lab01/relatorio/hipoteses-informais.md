# Hipóteses informais — Lab01

Documento acumulativo: cada seção corresponde à validação de dados e à
hipótese informal de uma RQ (Issues #9, #10, #11), escrita a partir do
relatório de qualidade de dados (`data/data-quality-report.md`, gerado pelo
script da Issue #28) sobre os 1000 repositórios coletados.

## RQ01 — Sistemas populares são maduros/antigos?

**Métrica:** idade do repositório em anos (`idade_anos`, calculada a partir
de `createdAt`).

### Distribuição, outliers e valores ausentes

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0,01 | 18,35 | 7,72 | 3,51 | 11,34 | 0 | 0/1000 |

- **Ausentes: 0.** Esperado — `createdAt` é um campo obrigatório de qualquer
  repositório real no GitHub, não há como faltar.
- **Outliers: 0.** Mesmo com repositórios variando de poucos dias até quase
  18 anos, a regra do IQR não identificou nenhum valor "fora da curva" — a
  distribuição de idade, apesar de espalhada, é relativamente contínua, sem
  saltos abruptos.
- A metade central dos repositórios (Q1–Q3) tem entre 3,5 e 11,3 anos — uma
  faixa ampla, mas concentrada bem acima de "recém-criado".

### Hipótese informal

Os dados sustentam a hipótese: repositórios populares tendem a ser
**maduros**, não recentes. A mediana de idade de quase 8 anos, e o Q1 já em
3,5 anos, indicam que a maioria dos 1000 repositórios mais estrelados levou
tempo considerável para acumular popularidade — esperado, já que estrelas se
acumulam ao longo do tempo, não instantaneamente. Ao mesmo tempo, a ausência
de outliers e a existência de um mínimo de apenas 0,01 ano (poucos dias)
mostram que a maturidade **não é um requisito rígido**: é possível
repositórios muito jovens entrarem no top 1000 por estrelas, provavelmente
casos de repercussão viral rápida (ex: tutoriais, listas "awesome", ou
repositórios amplificados por redes sociais/comunidades logo após a criação).
Em suma: popularidade correlaciona com maturidade, mas não a exige.

## RQ02 — Sistemas populares recebem muita contribuição externa?

**Métrica:** total de pull requests aceitas (mescladas) (`prs_aceitas`).

### Distribuição, outliers e valores ausentes

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 103.142 | 765,50 | 175 | 3.390 | 123 | 0/1000 |

- **Ausentes: 0.** `pullRequests(states: MERGED).totalCount` sempre retorna
  um número (mesmo que 0), nunca nulo.
- **Outliers: 123 (12,3% dos repositórios).** Uma proporção bem mais alta que
  a de RQ01, consistente com o padrão de distribuição em "cauda longa"
  (*power law*) típico de métricas de contribuição open-source: poucos
  projetos concentram uma quantidade desproporcional de atividade.
- Amplitude enorme: de 0 até 103.142 PRs aceitas — cinco ordens de magnitude
  de diferença entre o menor e o maior valor.

### Hipótese informal

Os dados sustentam a hipótese parcialmente, com uma ressalva importante. A
mediana de ~766 PRs aceitas mostra que o repositório popular "típico" de
fato recebe contribuição externa substancial — não é um número trivial.
Porém, os **123 outliers** (mais de 1 em cada 10 repositórios) revelam que
uma fração significativa dos projetos recebe uma quantidade de contribuição
ordens de magnitude acima do normal, puxando a média muito para cima do que
a mediana sugere. Isso indica que "sistemas populares recebem muita
contribuição" é verdade de forma desigual: existe um pequeno grupo de
"mega-projetos" (provavelmente frameworks e ferramentas amplamente adotadas
pela indústria) que concentra a maior parte da contribuição externa do
conjunto, enquanto a maioria dos repositórios populares recebe contribuição
moderada — real, mas não extraordinária. Há também repositórios populares
com **0 PRs aceitas** (o mínimo observado) — casos legítimos de projetos que
não usam o fluxo de Pull Request do GitHub para contribuições (já
documentado na validação da Issue #1, ex: `torvalds/linux`).

## RQ03 — Sistemas populares lançam releases com frequência?

**Métrica:** total de releases do repositório (`total_releases`,
`releases.totalCount` do schema `Repository`).

### Distribuição, outliers e valores ausentes

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 1.000 | 39,5 | 0 | 148,25 | 94 | 0/1000 |

- **Ausentes: 0.** `releases.totalCount` sempre retorna um número, mesmo 0.
- **Q1 = 0** — pelo menos 25% da amostra nunca usou a feature de Releases do
  GitHub. Olhando a distribuição completa: 280/1000 (28%) têm exatamente 0
  releases.
- **Outliers: 94 (9,4%),** todos no extremo superior — cauda longa também
  aqui, um pequeno grupo de projetos lança releases com muito mais
  frequência que a maioria.
- **Inconsistência de coleta encontrada:** 21 repositórios aparecem com
  exatamente `1.000` releases — número redondo demais para ser coincidência
  entre projetos tão distintos (`electron/electron`, `vercel/next.js`,
  `home-assistant/core`, `langchain-ai/langchain`, entre outros). Conferi 3
  deles direto na API REST (contagem real via paginação, não `totalCount`):

  | Repositório | Coletado (GraphQL) | Real (REST) |
  |---|---|---|
  | `electron/electron` | 1.000 | 1.986 |
  | `vercel/next.js` | 1.000 | 3.810 |
  | `home-assistant/core` | 1.000 | 1.630 |

  Confirmado: o campo `releases.totalCount` da API GraphQL do GitHub trunca
  em 1.000 para conexões muito grandes — limitação da própria API, não erro
  do nosso script de coleta. Os 21 repositórios no teto têm o valor real
  subestimado (em alguns casos, quase 4x menor que o real); o Q3/máximo
  reportados acima são um piso, não o valor verdadeiro, para os projetos
  mais prolíficos da amostra.

### Hipótese informal

A hipótese "sistemas populares lançam releases com frequência" não se
sustenta como afirmação única — os dados apontam para uma distribuição
**bimodal**, dependente do tipo de repositório, não da popularidade em si.
Em uma ponta, 28% da amostra nunca usou a feature de Releases do GitHub:
majoritariamente repositórios de conteúdo, listas curadas e materiais de
estudo (o mesmo perfil de repositório sem PRs documentado em RQ02) — onde
"popular" não implica "versionado". Na outra ponta, projetos de software
ativamente mantidos lançam releases com frequência muito alta, provavelmente
ainda mais alta do que os dados capturam: o teto de 1.000 no campo coletado
esconde que pelo menos `electron/electron` e `vercel/next.js` já ultrapassam
3-4x esse valor. Em suma: popularidade por si só não prediz frequência de
releases — o tipo de conteúdo do repositório é o fator determinante, e a
métrica coletada subestima sistematicamente os casos mais extremos.

## RQ04 — Sistemas populares são atualizados com frequência?

**Métrica:** tempo até a última atualização, em dias
(`dias_desde_atualizacao`, calculado a partir de `pushedAt`).

### Distribuição, outliers e valores ausentes

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 2.448 | 3 | 0 | 49 | 191 | 0/1000 |

- **Ausentes: 0.** `pushedAt` é um timestamp simples, sempre presente — sem
  o problema de teto observado em RQ03.
- Mediana de apenas 3 dias, e 339/1000 (33,9%) repositórios atualizados no
  próprio dia da coleta — a esmagadora maioria do top 1000 por estrelas
  segue com desenvolvimento ativo.
- **Outliers: 191 (19,1%),** todos no extremo superior (repositórios há
  muito tempo sem push). Investigando os mais extremos individualmente,
  todos são casos legítimos de projetos descontinuados, não erro de coleta:

  | Repositório | Dias sem atualização | Motivo plausível |
  |---|---|---|
  | `exacity/deeplearningbook-chinese` | 2.448 (~6,7 anos) | Tradução de livro — conteúdo estático |
  | `GitSquared/edex-ui` | 1.761 | Projeto arquivado pelo autor |
  | `adobe/brackets` | 1.526 | Editor descontinuado pela Adobe (2021) |
  | `atom/atom` | 1.321 | Editor descontinuado pelo próprio GitHub (dez/2022) |
  | `AFNetworking/AFNetworking` | 1.307 | Lib de rede iOS, superada pelo `URLSession` nativo da Apple |

### Hipótese informal

Os dados sustentam a hipótese para a maioria da amostra, com uma minoria
relevante de exceções bem explicáveis. A mediana de apenas 3 dias sem
atualização mostra que popularidade por estrelas, no top 1000, anda junto
com desenvolvimento ativo — consistente com a própria mecânica do GitHub
(busca, trending, descoberta) favorecer projetos com sinais recentes de
vida. Os 191 outliers (quase 1 em cada 5 repositórios), porém, revelam que
estrelas acumuladas **não desaparecem quando o projeto para** — são
"fósseis" que continuam no top 1000 histórico mesmo anos após deixarem de
ser mantidos, como `atom/atom` (descontinuado pelo próprio GitHub) e
`AFNetworking` (superado por uma API nativa da Apple). Isso reforça uma
leitura já sugerida em RQ08: número de estrelas é um indicador de
relevância *histórica* acumulada, não necessariamente de manutenção
*corrente* — as duas coisas costumam andar juntas, mas não são a mesma
coisa.

## RQ05 — Sistemas populares são escritos nas linguagens mais populares?

**Métrica:** linguagem primária do repositório (`linguagem`), comparada
contra o ranking do GitHub Octoverse (fonte definida na Issue #3).

### Distribuição, outliers e valores ausentes

| Categoria | Contagem |
|---|---|
| Python | 229 |
| TypeScript | 174 |
| JavaScript | 110 |
| Go | 76 |
| Rust | 57 |
| *(demais 38 categorias)* | — |
| **Não informado** | 87 |

- **Ausentes: 87 (8,7%).** Não é falha de coleta — são repositórios sem uma
  linguagem de código dominante, geralmente listas/coleções (ex.:
  `sindresorhus/awesome`, já documentado na validação da Issue #3), onde o
  GitHub Linguist não consegue eleger uma linguagem de programação primária
  porque o conteúdo é majoritariamente Markdown/texto.
- Não existe conceito de "outlier" numérico numa variável categórica — a
  distribuição é lida em concentração, não em dispersão.
- Top 5 linguagens concentram 646/1000 (64,6%) da amostra; as outras 38
  categorias dividem os 267 restantes — cauda longa também aqui, entre
  categorias.

### Hipótese informal

Os dados sustentam a hipótese. As três linguagens no topo — Python (229),
TypeScript (174) e JavaScript (110) — são exatamente as que aparecem entre as
mais populares nos relatórios recentes do GitHub Octoverse, a fonte adotada
pelo grupo desde a Issue #3. Juntas, essas três já respondem por mais da
metade (51,3%) da amostra, indicando que popularidade medida por estrelas e
popularidade de linguagem medida por adoção geral caminham juntas — não é
surpresa que projetos escritos nas linguagens mais usadas pela comunidade
tenham mais desenvolvedores propensos a descobri-los, usá-los e estrelá-los.
Os 87 casos "Não informado" não contradizem a hipótese: são majoritariamente
repositórios de conteúdo (listas "awesome", coleções de recursos), uma
categoria de projeto popular no GitHub que não se encaixa na pergunta de
pesquisa por não ser, no sentido estrito, "escrito" em nenhuma linguagem.

## RQ06 — Sistemas populares possuem um alto percentual de issues fechadas?

**Métrica:** razão entre issues fechadas e total de issues
(`razao_issues_fechadas`).

### Distribuição, outliers e valores ausentes

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 1 | 0,86 | 0,67 | 0,97 | 60 | 0/1000 |

- **Ausentes: 0.** `issues.totalCount` e `issues(states: CLOSED).totalCount`
  sempre retornam um número, mesmo que 0 — a divisão por zero é tratada
  explicitamente na métrica (retorna 0, não `NaN`, conforme documentado na
  Issue #3).
- **Outliers: 60 (6%).** Como a métrica é uma razão limitada entre 0 e 1, o
  IQR é estreito (Q1=0,67 a Q3=0,97), então valores nos dois extremos contam
  como outlier: repositórios com razão muito baixa e repositórios com razão
  0 — incluindo o caso já documentado de repositórios que não usam o
  rastreador de Issues do GitHub (`torvalds/linux`, 0/0), que entra como
  outlier técnico, não como sinal de má manutenção.
- Q3 em 0,97 mostra que pelo menos 25% da amostra fecha quase todas as
  issues que recebe.

### Hipótese informal

Os dados sustentam a hipótese com folga. A mediana de 86% de issues fechadas
é um número alto por qualquer critério, e o Q1 em 67% mostra que mesmo o
quarto mais "fraco" da amostra ainda fecha a maioria das suas issues — não há
um grupo grande de projetos populares mal cuidados. Isso é coerente com o
comportamento esperado de projetos que atraem muitos usuários: mais gente
reportando problemas gera mais issues, mas também mais gente no time de
manutenção capaz de triá-las e fechá-las. Os 60 outliers merecem leitura em
duas pontas: de um lado, projetos genuinamente menos ativos apesar da
popularidade (estrela não implica manutenção contínua); do outro, casos como
`torvalds/linux`, onde a razão 0/0 é um artefato de o projeto não usar o
rastreador de Issues do GitHub — a manutenção real acontece por lista de
e-mail, fora do alcance dessa métrica. Sem essa distinção, corre-se o risco
de interpretar "ausência de dado" como "projeto mal cuidado", quando é o
oposto.

## RQ08 (bônus) — Sistemas populares possuem um alto número de forks?

**Métrica:** total de forks (`total_forks`) e, agora que `stargazerCount` foi
adicionado à coleta (Issue #54), a razão fork/estrela (`razao_fork_estrela`)
— a métrica que a hipótese informal original (Issue #4) sempre pediu:
sistemas populares tendem a ter alta razão fork/estrela, indicando não só
popularidade passiva mas reuso ativo do código.

### Distribuição, outliers e valores ausentes

| Métrica | Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|---|
| Total de forks | 38 | 108.902 | 6.403 | 3.624,5 | 10.915,5 | 95 | 0/1000 |
| Total de estrelas | 33.040 | 543.177 | 48.868,5 | 38.662,75 | 72.965,5 | 82 | 0/1000 |
| Razão fork/estrela | 0,0009 | 1,95 | 0,11 | 0,08 | 0,18 | 54 | 0/1000 |

- **Ausentes: 0** nas três colunas — `forkCount` e `stargazerCount` são
  campos simples do schema `Repository`, sempre presentes.
- A razão varia por mais de **2.100x** entre o mínimo e o máximo observados —
  faixa muito mais larga, proporcionalmente, do que a de forks ou estrelas
  isoladas, o que já sugere que a razão depende do *tipo* de repositório, não
  só da popularidade.
- **Extremo superior:** `firstcontributions/first-contributions` (108.440
  forks / 55.685 estrelas, razão 1,95 — quase 2 forks por estrela) e
  `eugenp/tutorials` (razão 1,43). Ambos são repositórios de **tutorial/
  prática**, feitos explicitamente para serem forkados (o próprio README do
  `first-contributions` instrui o leitor a fazer fork como exercício de
  primeira contribuição open-source) — não é popularidade passiva, é o
  oposto: o fork *é* o produto.
- **Extremo inferior:** `hexojs/hexo` (38 forks / 41.773 estrelas, razão
  0,0009) — um gerador de site estático consumido via `npm install`, não
  clonado/modificado pela maioria de quem o usa. Estrela aqui expressa "uso
  a ferramenta", não "quero mexer no código".

### Hipótese informal

Com `stargazerCount` agora coletado, dá pra testar a hipótese original de
verdade — e o resultado é mais nuançado do que uma confirmação simples. A
mediana de 0,11 (cerca de 1 fork a cada 9 estrelas) não é desprezível:
como dar estrela custa um clique e fazer fork exige intenção real de estudar
ou modificar o código, uma conversão de ~11% do "público passivo" pra
"engajamento ativo" já é um sinal de reuso genuíno, não só admiração — nesse
sentido, a hipótese tem apoio. Mas a variação de mais de 2.000x entre os
extremos mostra que **"alta razão fork/estrela" não é uma propriedade
uniforme dos repositórios populares** — é concentrada num tipo específico de
projeto (tutoriais, templates, material de estudo, onde o fork é o próprio
uso pretendido), enquanto ferramentas e bibliotecas consumidas via gerenciador
de pacotes (como o `hexojs/hexo`) mantêm razão baixa mesmo com centenas de
milhares de estrelas. **Resultado: hipótese sustentada parcialmente** — o
efeito de rede via fork existe e é mensurável, mas ele reflete o *tipo* de
repositório popular, não a popularidade em si.

## Métricas extras (Issue #26) — licença, CI/CD e diversidade de linguagens

**Métricas:** licença (`licenca`), presença de pipeline de CI/CD via GitHub
Actions (`possui_ci_cd`), número de linguagens detectadas no repositório
(`total_linguagens`).

### Licença

| Categoria | Contagem |
|---|---|
| MIT License | 394 |
| Apache License 2.0 | 181 |
| Other | 148 |
| GNU General Public License v3.0 | 50 |
| GNU Affero General Public License v3.0 | 48 |
| *(demais 14 categorias)* | — |
| **Não informado** | 84 |

Licenças permissivas (MIT + Apache-2.0) somam 575 repositórios — 57,5% da
amostra —, contra apenas 98 (9,8%) de licenças copyleft fortes (GPLv3 +
AGPLv3). A categoria "Other" (148, 14,8%) não significa licença desconhecida:
na maioria dos casos é uma expressão SPDX não-padrão que o detector do
GitHub não casa com um único template — o mesmo padrão já documentado na
Issue #26 para o `torvalds/linux` (`GPL-2.0 WITH Linux-syscall-note`).

### CI/CD

| Valor | Contagem |
|---|---|
| true | 798 |
| false | 202 |

Quase 80% dos 1000 repositórios têm pelo menos um workflow de GitHub Actions
configurado.

### Número de linguagens

| Mín | Máx | Mediana | Q1 | Q3 | Outliers | Ausentes |
|---|---|---|---|---|---|---|
| 0 | 56 | 5 | 3 | 9 | 48 | 0/1000 |

### Hipótese informal

Os três sinais extras, juntos, apontam pra uma mesma conclusão: sistemas
populares tendem a ter **maturidade de engenharia**, não só popularidade. A
predominância de licenças permissivas (quase 6 em cada 10 repositórios) é
coerente com projetos que buscam adoção ampla, inclusive comercial — licença
restritiva é fricção a menos gente disposta a depender do projeto. A adoção
de CI/CD em quase 80% da amostra reforça isso: é uma prática que só compensa
o investimento quando o projeto já espera volume relevante de contribuições
externas a validar automaticamente (conectando com o que já observamos em
RQ02, sobre contribuição externa). A mediana de 5 linguagens por repositório
mostra que a maioria não é monolinguagem "pura" — o Linguist do GitHub conta
arquivos de build, configuração (YAML, Dockerfile) e scripts auxiliares como
linguagens à parte, então esse número reflete mais a complexidade de um
projeto maduro (infraestrutura de CI/CD, testes, documentação) do que
fragmentação real de código-fonte. Os 48 outliers no topo (até 56 linguagens)
provavelmente são monorepos ou projetos guarda-chuva que hospedam múltiplos
subprojetos.
