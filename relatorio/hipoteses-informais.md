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
