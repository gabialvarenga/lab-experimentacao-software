# Lab02 — Desenho do experimento (Passo 1)

Espinha do desenho experimental. Hipóteses formais entram em
[02-hipoteses.md](02-hipoteses.md) (#65) e ameaças à validade em
[03-ameacas-validade.md](03-ameacas-validade.md) (#66) — aqui ficam as
variáveis, tratamentos, tipo de projeto, contrabalanceamento e a escolha de
métricas por RQ (GQM), a partir do que já foi decidido em
[00-decisoes.md](00-decisoes.md) (#59) e [katas.md](katas.md) (#61).

> **Atualização — de volta às 6 katas:** a seleção original (#61) validou 6
> katas de dificuldade equivalente. Por causa do prazo curto, o grupo havia
> reduzido temporariamente para 4 (k1..k4), mas o professor exigiu as 6
> katas completas, então k5 e k6 foram restauradas do histórico do
> repositório — ver `katas.md` para o detalhamento. Isso muda de volta a
> quantidade de medições (G) e a tabela de contrabalanceamento abaixo; os
> demais itens (B, C, D, F, GQM) não dependem do número de katas e continuam
> valendo como escritos originalmente.

## (B) Variáveis dependentes

Uma por RQ, todas já ligadas a um script de coleta existente — nenhuma
inventada aqui:

| Variável | Coluna | Script |
|---|---|---|
| Tempo até verde | `tempo_segundos` (`trials.csv`) | `cronometro.py` (#60) |
| Testes passando | `testes_total`, `testes_passando`, `taxa_sucesso` | `contagem_testes.py` (#63) |
| Estrutura do código | `loc`, `cc_media`, `cc_max`, `mi`, `duplicacao_pct` | `metricas_estaticas.py` (#62) |

## (C) Variável independente

Uso ou não do assistente de IA (Claude Code) na resolução do kata —
`tratamento`, com dois níveis: `com-ia` / `sem-ia`.

## (D) Tratamentos

`docs/00-decisoes.md` deixou em aberto ("a fechar antes da S02") se o Claude
Code pode rodar os testes e editar arquivos por conta própria durante o
trial. Fecho essa decisão aqui, já que é exatamente o que este item pede.

**`com-ia`:** Claude Code com acesso ao diretório do kata (enxerga o
enunciado e `test_aceitacao.py`), **pode editar `solucao.py` diretamente e
rodar os testes por conta própria**, sem limite de iterações além dos 35
minutos do time-box.

- **Por quê permitir edição/execução direta, e não só sugestão:** restringir
  o Claude Code a um papel de "autocomplete" mediria uma ferramenta
  diferente da que o grupo realmente escolheu usar (#59). Um agente que lê o
  repositório e roda comandos é mais forte que um chatbot de copiar e colar
  — essa diferença de força fica registrada como ameaça à validade (#66),
  não escondida ou neutralizada artificialmente.

**`sem-ia`:** Claude Code fechado; autocompletar por IA da IDE desligado
(Copilot, Codeium e afins, já listado em `00-decisoes.md`). Documentação
oficial e busca convencional continuam permitidas — só o assistente de IA
generativa é removido, não o acesso à internet.

## (F) Tipo de projeto experimental

Crossover *within-subject*, contrabalanceado: cada integrante passa pelos
dois tratamentos, em katas diferentes.

**Por quê:** controla a variação individual de habilidade — a comparação
central é sempre a mesma pessoa consigo mesma (com IA vs. sem IA), nunca uma
pessoa contra outra. Isso troca a ameaça de "diferença de habilidade entre
integrantes" por uma nova: **efeito de aprendizado** entre katas sucessivos
(a pessoa pode ficar mais rápida só por já ter feito o kata anterior, não
pela IA). Mitigado pelo contrabalanceamento de ordem abaixo.

## Tabela de contrabalanceamento

Duas propriedades garantidas pela tabela, não deixadas ao acaso:

1. **Nenhum kata é sempre com IA ou sempre manual** entre os 3 integrantes —
   senão a dificuldade do próprio kata se confundiria com o efeito do
   tratamento.
2. **Tratamento alternado dentro da sequência de cada integrante** (não é
   "as 2 com IA primeiro, depois as 2 sem IA") — senão o efeito de
   aprendizado se confundiria com o efeito do tratamento.

`k1`..`k6` são os katas reais já selecionados e documentados em `katas.md`
(#61) — tabela idêntica à de lá, repetida aqui como parte do desenho formal.
As ordens 1–4 de cada integrante já foram executadas sob o desenho reduzido
(4 katas) e são mantidas como estão — só as ordens 5–6 (k5, k6) são novas.

| integrante | ordem | kata | tratamento |
|---|---|---|---|
| brenda | 1 | k1 | com-ia |
| brenda | 2 | k2 | sem-ia |
| brenda | 3 | k3 | com-ia |
| brenda | 4 | k4 | sem-ia |
| brenda | 5 | k5 | com-ia |
| brenda | 6 | k6 | sem-ia |
| carlos | 1 | k3 | sem-ia |
| carlos | 2 | k2 | com-ia |
| carlos | 3 | k1 | sem-ia |
| carlos | 4 | k4 | com-ia |
| carlos | 5 | k6 | sem-ia |
| carlos | 6 | k5 | com-ia |
| gabriela | 1 | k4 | com-ia |
| gabriela | 2 | k3 | sem-ia |
| gabriela | 3 | k1 | com-ia |
| gabriela | 4 | k2 | sem-ia |
| gabriela | 5 | k6 | com-ia |
| gabriela | 6 | k5 | sem-ia |

Cobertura por kata (nenhum preso a um único tratamento):

| kata | com-ia | sem-ia |
|---|---|---|
| k1 | 2 | 1 |
| k2 | 1 | 2 |
| k3 | 1 | 2 |
| k4 | 2 | 1 |
| k5 | 2 | 1 |
| k6 | 1 | 2 |

## (G) Quantidade de medições

Atualizado em `00-decisoes.md` após a restauração das 6 katas: 3 integrantes
× 6 katas = **18 trials**, 9 com IA e 9 sem — a tabela acima é a distribuição
concreta desse total.

## Seleção e justificativa das métricas por RQ (GQM)

Qual métrica candidata do enunciado é usada em cada RQ, e por quê:

**RQ1 — tempo:**
- *Primária:* tempo até verde (mediana por tratamento, não média — N
  pequeno e sensível a outlier, já convenção em `00-decisoes.md`).
- *Exploratória, não obrigatória:* nº de prompts (coluna `prompts` de
  `trials.csv`) — natural de logar com um agente de chat, cada mensagem é
  um turno discreto.

**RQ2 — defeitos:**
- *Primária:* taxa de sucesso (%) — normaliza katas com número diferente de
  casos de teste. É por isso que `contagem_testes.py` (#63) usa o total
  *real* do kata (contado no `test_aceitacao.py` original), não o do
  relatório de uma execução que não compilou — um trial censurado com erro
  de sintaxe não pode aparecer com um denominador menor e distorcer a taxa.
- *Complementar:* nº absoluto de testes falhando.

**RQ3 — estrutura do código:**
- *Primária:* complexidade ciclomática média (Radon `cc`).
- *Controle obrigatório:* LOC — código gerado por IA pode ser mais verboso;
  reportar complexidade/duplicação sem normalizar por LOC pode enganar.
- Duplicação (%) também coletada, mesmo peso que complexidade.
- *Aprofundamento opcional:* Índice de Manutenibilidade (Radon `mi`), métrica
  composta — mais robusta que olhar cada métrica isolada.

**Nota geral:** mediana e IQR nas tabelas descritivas em vez de média e
desvio-padrão (N pequeno — 9 trials por tratamento no total, 1 a 2 por kata),
com Wilcoxon pareado na análise inferencial (S03) — já convenção do
enunciado e de `00-decisoes.md`.

## Próximos passos (fora do escopo desta issue)

- Hipóteses nula/alternativa por RQ — #65
- Ameaças à validade (efeito de aprendizado, familiaridade prévia, força do
  tratamento `com-ia`, memorização) — #66
