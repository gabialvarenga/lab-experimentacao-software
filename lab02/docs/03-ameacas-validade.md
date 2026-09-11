# Lab02 — Ameaças à validade (Passo 1)

Formaliza o item (H) do Passo 1, deixado em aberto em
[01-desenho-experimento.md](01-desenho-experimento.md) (#64). Reaproveita,
sem redefinir, o que já foi decidido em [00-decisoes.md](00-decisoes.md)
(#59), na tabela de contrabalanceamento de `01-desenho-experimento.md`, na
seleção de katas de [katas.md](katas.md) (#61) e nas hipóteses de
[02-hipoteses.md](02-hipoteses.md) (#65) — aqui só a ameaça, sua
classificação e a mitigação já adotada (ou a adotar) ficam registradas.

## Convenção de classificação

Quatro categorias clássicas de desenho experimental (Wohlin et al.):

| Categoria | O que avalia |
|---|---|
| **Interna** | Se o efeito observado é mesmo causado pelo tratamento, e não por alguma outra variável que varia junto com ele. |
| **Externa** | Se o resultado generaliza além do contexto exato do experimento (estes três integrantes, estas seis katas, esta ferramenta). |
| **De construção** | Se o que foi operacionalizado (o tratamento `com-ia`/`sem-ia`, as métricas) mede de fato o conceito teórico pretendido ("a IA ajuda a resolver o problema"), e não outra coisa. |
| **De conclusão** | Se a relação entre tratamento e efeito pode ser detectada de forma estatisticamente confiável, dado o desenho e os dados coletados. |

## 1. Efeito de aprendizado entre katas

**Classificação:** interna.

Um integrante pode ficar mais rápido ou cometer menos erros num kata só por
já ter resolvido os katas anteriores da própria sequência — familiaridade
com o *formato* comum às seis katas (varrer uma lista de registros, aplicar
regras, agregar, formatar; ver `katas.md`) — não por efeito do tratamento.
Sem controle, isso se confundiria com o efeito da IA sempre que o tratamento
`com-ia` calhasse mais tarde na sequência de alguém.

**Mitigação (já implementada):** contrabalanceamento de ordem. A tabela de
`01-desenho-experimento.md` e a de `katas.md` garantem (a) que nenhuma kata
é sempre `com-ia` ou sempre `sem-ia` entre os três integrantes, e (b) que o
tratamento alterna a cada posição da sequência de cada integrante, com
início invertido entre eles — o efeito de aprendizado se distribui pelos
dois tratamentos em vez de favorecer um deles.

## 2. Familiaridade prévia desigual com a ferramenta de IA entre os integrantes

**Classificação:** interna.

O desenho *within-subject* já controla a diferença de habilidade geral de
programação (cada integrante é comparado consigo mesmo). Mas a habilidade
*especificamente com o Claude Code* pode variar entre os três — quem já usa
a ferramenta há mais tempo tende a escrever prompts mais eficazes,
inflando o efeito medido do tratamento `com-ia` para essa pessoa e
diluindo-o para quem começa do zero. Diferente do efeito de aprendizado
(#1), aqui a variável de confusão é externa ao experimento (histórico do
integrante), não algo gerado pela própria sequência de katas.

**Mitigação:** registrar o nível de experiência prévia de cada integrante
com o Claude Code, autorreportado (ex.: novato / intermediário /
experiente), como covariável de contexto. O lugar natural para esse dado é
a tabela "Ambiente de cada integrante" já existente em `00-decisoes.md`
(hoje preenchida só para Gabriela) — preencher essa coluna é ação de
outra issue/sprint, não desta; aqui fica registrada a necessidade e o
uso pretendido: contextualizar, na discussão do relatório final, qualquer
diferença atípica de desempenho entre integrantes que não se explique só
pelo tratamento.

Isso não elimina a ameaça — não há como equalizar experiência prévia
retroativamente — só a torna visível e discutível em vez de silenciosa.

## 3. Vazamento / memorização

**Classificação:** de construção.

Se uma kata for muito conhecida (ex.: um clássico de LeetCode/HackerRank), o
assistente de IA pode reproduzir de memória uma solução vista em seu
treinamento em vez de efetivamente raciocinar sobre o enunciado. Nesse
caso, o tratamento `com-ia` deixa de medir "a IA ajuda a resolver o
problema" — o conceito teórico que a RQ1/RQ2/RQ3 querem capturar — e passa
a medir "a IA reconhece este problema", que é outra coisa. É uma ameaça à
construção porque quebra a correspondência entre o tratamento
operacionalizado e o conceito que ele deveria representar, não uma questão
de causalidade (interna) ou de generalização (externa).

**Mitigação (já implementada):** katas autorais, com domínios inventados e
regras próprias, sem enunciado equivalente publicado — não há solução
indexada para a IA recuperar de memória (`katas.md`, #61, seção "Por que
katas autorais"). Dez candidatos foram avaliados e dois descartados
explicitamente por risco de memorização (conversor de números romanos,
contador de frequência de palavras — ambos "clássicos"/"muito indexados").

**Precedente metodológico do grupo:** a mesma disciplina de não assumir
"popular" ou "conhecido" sem uma referência checável já apareceu no Lab01,
na [issue #3](https://github.com/gabialvarenga/lab-experimentacao-software/issues/3)
(RQ05 — linguagem, RQ06 — issues fechadas), que exigiu documentar uma fonte
externa objetiva (TIOBE/GitHut) antes de classificar uma linguagem como
popular. Aqui o equivalente é não assumir "pouco indexado" apenas por a
kata ser inédita: cada candidato descartado em `katas.md` traz o motivo
concreto de exclusão (kata clássica, tema onipresente), na mesma linha de
justificar a classificação em vez de simplesmente declará-la. Não há
consulta GraphQL nova nem reaproveitamento de código do Lab01 aqui — é só a
mesma prática de fundamentar a afirmação.

## 4. Amostra pequena (3 trials por tratamento por integrante, 18 no total)

**Classificação:** de conclusão.

Com poucos pontos por tratamento, a média e o desvio-padrão são sensíveis a
outliers e testes paramétricos (ex.: teste t) perdem poder ou têm
pressupostos de normalidade difíceis de sustentar com N tão pequeno,
arriscando não detectar um efeito real (ou detectar um espúrio).

**Mitigação (já implementada):** mediana e IQR nas tabelas descritivas em
vez de média e desvio-padrão, e teste de Wilcoxon signed-rank pareado (não
paramétrico) na análise inferencial — convenção já fixada em
`00-decisoes.md` e detalhada por RQ em `02-hipoteses.md` (#65).

## 5. Time-box de 35 min e tratamento de censura

**Classificação:** de conclusão.

Trials que não terminam em 35 minutos são registrados como censurados em
2100s (`00-decisoes.md`), não descartados. Isso evita o viés mais óbvio
(descartar distorceria a comparação a favor do tratamento com mais
falhas), mas não resolve tudo: o Wilcoxon pareado compara diretamente os
valores de `tempo_segundos`, e um trial censurado entra com o teto de 2100s
mesmo que o tempo "real" até verde fosse maior — a magnitude exata da
diferença entre tratamentos fica subestimada sempre que houver censura de
algum dos dois lados do par, mesmo com a direção do efeito preservada.

**Mitigação (já implementada):** regra fixa de censura em vez de descarte,
aplicada identicamente aos dois tratamentos. **Limitação residual a
registrar no relatório final:** se a proporção de trials censurados for
alta ou desigual entre tratamentos, a leitura de RQ1 deve vir acompanhada
da proporção de censura por tratamento, não só da mediana — decisão de
análise para o Passo 4, fora do escopo desta issue.

## Tabela-resumo

| # | Ameaça | Classificação | Mitigação |
|---|---|---|---|
| 1 | Efeito de aprendizado entre katas | Interna | Contrabalanceamento de ordem (tratamento alterna a cada posição; nenhuma kata presa a um tratamento) |
| 2 | Familiaridade prévia desigual com a IA | Interna | Nível de experiência autorreportado por integrante, registrado como covariável de contexto em `00-decisoes.md` |
| 3 | Vazamento / memorização | De construção | Katas autorais, sem enunciado equivalente publicado; candidatos "clássicos" descartados explicitamente |
| 4 | Amostra pequena (3 trials/tratamento/integrante) | De conclusão | Mediana + IQR nos descritivos; Wilcoxon pareado na inferência |
| 5 | Time-box de 35 min e censura | De conclusão | Censura fixa em 2100s em vez de descarte, igual nos dois tratamentos; reportar proporção de censura por tratamento no Passo 4 |

## Fora do escopo desta issue

- Preencher a coluna de experiência prévia com IA na tabela de
  `00-decisoes.md` — ação de coleta, não de desenho.
- Execução dos testes de Wilcoxon e leitura da proporção de censura —
  Passo 4 (S03).
