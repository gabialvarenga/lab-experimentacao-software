# Lab04 — Protocolo de coleta dos dados reais

Protocolo da coleta dos dados reais do Lab04 (itens a e b do enunciado). Fixa o par de testes, a fonte, os grupos, os critérios, o procedimento e a amostragem, e registra a sondagem feita antes de fechar as decisões. As seções citadas entre parênteses referem-se ao enunciado do Lab04; o contexto das sprints está em [planejamento.md](planejamento.md).

Siglas: PR (*Pull Request*); API (*Application Programming Interface*); CSV (*Comma-Separated Values*); UTC (*Coordinated Universal Time*).

## 1. Decisões

| Tema | Decisão |
|---|---|
| Par de testes | P1: t de Welch × Mann-Whitney (enunciado, seção 2, item a) |
| Pergunta | O tempo até o merge de um PR muda quando ele recebe, logo no início, a revisão automática do Copilot? |
| Variável de resposta | Horas entre a abertura do PR (`created_at`) e o merge (`merged_at`) |
| Repositório | `supabase/supabase` |
| Janela | PRs mesclados de 01/08/2026 a 31/10/2026 (UTC) |
| Grupo "com bot" | Autor humano; primeira revisão do Copilot até 1 h após a abertura |
| Grupo "sem bot" | Autor humano; nenhuma revisão do Copilot |
| Tamanho | 30 PRs por grupo (10 por mês de merge), sorteados com semente 42 |
| Fontes | API REST do GitHub (busca e revisões); nenhum dataset de terceiros |

Por que "com bot" é "revisão do Copilot até 1 h": a sondagem de 03/11 (seção 6) mostrou que o revisor chega, em muitos PRs, bem depois da abertura, e que esses PRs são justamente os que ficam abertos mais tempo. Definir o grupo pela presença da revisão em qualquer momento deixaria o bot "causar" PRs lentos só porque PRs lentos têm mais tempo para receber uma revisão. Fixar o grupo pelo que já tinha acontecido 1 h depois da abertura faz os dois grupos partirem do mesmo ponto.

## 2. Definições

| Termo | Definição operacional |
|---|---|
| PR elegível | PR mesclado na janela, com autor de tipo `User` (autores `Bot`, como Dependabot e Renovate, ficam fora) |
| Revisão do Copilot | Revisão em `GET /repos/{repo}/pulls/{n}/reviews` cujo autor é `copilot-pull-request-reviewer[bot]` |
| Horas até a revisão | (`submitted_at` da primeira revisão do Copilot) − `created_at` |
| Horas até o merge | `merged_at` − `created_at`, em horas |
| Mês de merge | Mês de `merged_at` em UTC; é o estrato da amostragem |

## 3. Critérios de inclusão e exclusão

Entram os PRs elegíveis que atendem a todas as condições do respectivo grupo:

| Grupo | Condições |
|---|---|
| `com_bot` | Revisão do Copilot com horas até a revisão ≤ 1; horas até o merge > 1 |
| `sem_bot` | Nenhuma revisão do Copilot; horas até o merge > 1 |

A condição "horas até o merge > 1" vale para os dois grupos. Sem ela, o grupo sem bot receberia PRs mesclados em minutos, que não teriam tido tempo de receber a revisão; isso favoreceria o grupo sem bot por construção.

Ficam fora, e são contados e relatados:

- PRs de autor `Bot`;
- PRs com revisão do Copilot depois de 1 h da abertura (grupo de "revisão tardia");
- PRs com horas até o merge zero, negativas ou ≤ 1.

## 4. Procedimento de coleta

Implementado em `lab04/coleta.py` (Issue S01-04). Todas as chamadas usam o `GITHUB_TOKEN` do ambiente.

1. **Candidatos.** Uma busca por mês de merge e por grupo, na API de busca (`GET /search/issues`, 100 resultados por página):
   - com Copilot: `repo:supabase/supabase is:pr is:merged merged:AAAA-MM-01..AAAA-MM-DD commenter:app/copilot-pull-request-reviewer`
   - sem Copilot: a mesma consulta com `-commenter:app/copilot-pull-request-reviewer`
   - ambas com `-author:app/dependabot -author:app/renovate`; os autores `Bot` que restarem são removidos pelo campo `user.type`.
   A busca devolve no máximo 1.000 resultados por consulta. A divisão por mês mantém todas abaixo desse teto (maior contagem: 640).
2. **Revisões.** Para cada candidato do grupo com bot e para cada PR sorteado do grupo sem bot, `GET /repos/supabase/supabase/pulls/{n}/reviews`. O primeiro envio do Copilot define as horas até a revisão e confirma o grupo; um PR do grupo sem bot que apareça com revisão do Copilot é trocado pelo próximo da lista sorteada.
3. **Ritmo.** Pausa de pelo menos 20 s entre buscas e espera do tempo indicado em `Retry-After` quando a API devolver 403 ou 429. Na sondagem, pausas de 12 s ainda dispararam o limite secundário duas vezes em seis buscas. As respostas ficam em cache em `lab04/dados/reais/cache/` (fora do Git).
4. **Registro.** Data e hora da coleta, consultas usadas, contagens por etapa e quantidade de PRs excluídos em cada critério vão para `lab04/dados/reais/registro-coleta.md`.

## 5. Amostragem

- **Tamanho:** 30 PRs por grupo, 10 por mês de merge (agosto, setembro e outubro). Estratificar por mês mantém os dois grupos com o mesmo período, já que o uso do revisor e o ritmo de merge variam ao longo do tempo.
- **Sorteio:** `numpy.random.default_rng(42)` aplicado à lista ordenada por número de PR de cada grupo e mês, sem reposição.
- **Reserva:** se um mês não tiver 10 PRs elegíveis no grupo com bot, completar com PRs de outros meses do mesmo grupo e registrar a troca. O grupo sem bot é amostrado do mesmo jeito para manter 10 por mês.
- **Ordem:** o sorteio é feito sobre todos os PRs elegíveis, e não sobre os mais recentes.

## 6. Sondagem de 03/11/2026

Feita antes de fixar as decisões, com a API e um script descartável (nada disso entra na amostra final). A tabela resume o que sustentou as escolhas da seção 1.

| Verificação | Resultado |
|---|---|
| PRs mesclados de 01/08 a 31/10, sem autores `dependabot` e `renovate`, sem revisão do Copilot | 1.695 (463 em agosto, 592 em setembro, 640 em outubro, pelo mês de merge) |
| PRs mesclados no mesmo período com algum comentário do Copilot | 189 (66, 54 e 69); 187 com autor humano |
| Revisão do Copilot até 1 h após a abertura | 104 PRs; mediana de 21,3 h até o merge |
| Revisão do Copilot depois de 1 h | 83 PRs; mediana de 91,3 h até o merge |
| PRs sem revisão do Copilot (100 mais recentes) | Mediana de 4,5 h até o merge |
| Login das revisões do Copilot | Só `copilot-pull-request-reviewer[bot]` (235 revisões nos 187 PRs) |
| Outros bots | O CodeRabbit comentou em PRs dos dois grupos, além de Vercel, Supabase e GitHub Actions; o Copilot é o único revisor que difere entre os grupos nas amostras inspecionadas |

A diferença entre as medianas de PRs com revisão rápida (21,3 h), revisão tardia (91,3 h) e sem revisão (4,5 h) mostra que o grupo depende muito de quando a revisão chega. Foi isso que levou à definição de 1 h.

## 7. Dados registrados

`lab04/dados/reais/prs.csv`, uma linha por PR da amostra, com as colunas (a ordem final e as unidades ficam no dicionário de dados da Issue S01-06):

| Coluna | Descrição |
|---|---|
| `numero_pr` | Número do PR no repositório |
| `grupo` | `com_bot` ou `sem_bot` |
| `autor` | Login do autor |
| `criado_em` | `created_at`, UTC, ISO 8601 |
| `mesclado_em` | `merged_at`, UTC, ISO 8601 |
| `horas_ate_merge` | Variável de resposta, em horas |
| `horas_ate_revisao_bot` | Horas até a primeira revisão do Copilot; vazio no grupo `sem_bot` |

## 8. Limitações

- **Seleção dos PRs.** Só PRs mesclados entram; PRs fechados sem merge não aparecem. O tempo até o merge de PRs que nunca são mesclados fica de fora.
- **Atribuição do revisor.** Não se sabe por que o Copilot revisa alguns PRs logo no início e outros não. Se a revisão rápida for pedida para PRs de certos autores, áreas ou tamanhos, a diferença entre os grupos mistura o efeito do bot com o desses fatores.
- **Tamanho do PR.** Não é controlado.
- **Revisão tardia.** Os 83 PRs com revisão depois de 1 h ficam fora, e eles são os mais lentos. O resultado vale para revisão logo no início, não para qualquer revisão do Copilot.
- **Outros revisores.** O CodeRabbit e revisores humanos atuam nos dois grupos e não são controlados.
- **Um repositório e três meses.** O resultado descreve o `supabase/supabase` nesse período; não se generaliza para outros projetos.
- **Papel dos dados reais.** Os dados calibram a simulação e testam, no fim, a recomendação do grupo. A simulação é que mede erro tipo I e poder, porque nos dados reais não se conhece a resposta certa.

## 9. Reprodutibilidade

- **Semente:** 42 (`numpy.random.default_rng(42)`), a mesma do `config.yaml`.
- **Cache:** as respostas da API ficam em `lab04/dados/reais/cache/`, fora do Git; o `prs.csv` e o `registro-coleta.md` são versionados.
- **Comando:** `python -m lab04 coletar`, que precisa de `GITHUB_TOKEN` e fica fora do comando único (que lê o CSV já versionado).
- **Mudanças:** qualquer mudança de janela, de critério ou de repositório exige refazer a coleta e a calibração, e é registrada no `registro-coleta.md`.
