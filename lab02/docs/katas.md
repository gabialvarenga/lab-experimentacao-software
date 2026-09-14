# Katas do experimento

Objetos experimentais do Lab02: quatro katas autorais em Python — 2 fáceis, 1
média e 1 difícil —, com suíte de testes de aceitação automatizada.

Seis katas foram escritas e validadas na S01 (ver "Candidatos levantados"
abaixo). Por causa do prazo curto da disciplina, o grupo decidiu reduzir para
as 4 katas mínimas permitidas pelo enunciado, escolhendo três níveis de
dificuldade (2 fáceis, 1 média, 1 difícil) em vez de seis katas de dificuldade
equivalente. As duas katas que não vão ser executadas foram removidas do
repositório; as quatro que ficaram foram renumeradas para `k1`..`k4`.

## Por que katas autorais

O enunciado aponta a memorização como ameaça à validade: se a kata for um
clássico do LeetCode/HackerRank, o assistente de IA reproduz uma solução já
vista no treinamento em vez de efetivamente ajudar, e o tratamento *com IA*
passa a medir "a IA lembra disso?" e não "a IA ajuda a resolver isso?".

Todas as katas foram escritas pelo grupo, com domínios inventados e regras
próprias. Não têm enunciado equivalente publicado, então não há solução
indexada para a IA recuperar de memória.

## Critério de seleção e níveis de dificuldade

O enunciado exige katas de dificuldade comparável entre si dentro de cada
nível — o que muda agora é que o grupo assume três *níveis* declarados (fácil,
média, difícil) em vez de tratar as quatro katas como equivalentes entre si.
Cada kata ainda precisa atender aos critérios abaixo, avaliados na escrita
original das seis katas na S01.

| Critério | Faixa aceita | Obtido |
|---|---|---|
| Nº de casos de teste de aceitação | 8 a 12 | 10 a 11 |
| Nº de regras no enunciado | 5 a 6 | 5 a 6 |
| Conceitos exigidos | apenas biblioteca padrão; varredura linear de uma lista de registros + 3 a 5 regras condicionais + agregação + formatação da saída. Sem recursão, sem estruturas de dados avançadas, sem algoritmos além de percorrer e ordenar | atendido |
| Tempo estimado de resolução manual | 15 a 25 min (fáceis/média) a até 30 min (difícil), dentro do time-box de 35 min | atendido |

O nº de casos de teste é conferido por `scripts/validar_katas.py`. Os demais
critérios foram avaliados na escrita de cada kata.

### As katas selecionadas para o experimento

| kata | nível | função | casos de teste | regras | esboço do que exige |
|---|---|---|---|---|---|
| k1 | fácil | `consumo_bateria` | 10 | 6 | somatório com taxa por tipo, limite de faixa, dois erros |
| k2 | fácil | `validar_lote` | 11 | 5 | validação de formato, três checagens acumuladas em ordem fixa |
| k3 | média | `montar_escala` | 10 | 6 | atribuição gulosa com desempate, filtro de disponibilidade, um erro |
| k4 | difícil | `calcular_tarifa` | 11 | 5 | parsing de `HH:MM`, franquia, cobrança por faixa, teto, dois erros |

Todas têm a mesma forma geral (varrer uma lista de registros, aplicar regras,
agregar, formatar). k1 e k2 já eram as mais simples do grupo original de seis;
k4 é a que exige mais casos de borda (parsing de horário) e foi classificada
como difícil; k3 fica no meio e representa o nível médio. Como o desenho
continua *within-subject* — cada uma das quatro katas é resolvida pelos três
integrantes —, a variação de dificuldade entre katas afeta igualmente os dois
tratamentos dentro de cada kata e não enviesa a comparação com/sem IA; ela só
deixa de ser controlada *entre* níveis, o que é intencional aqui (ver ameaças
à validade abaixo).

**Ameaça à validade adicionada por essa mudança:** com só 1 kata por nível
médio/difícil, RQ1–RQ3 não podem ser quebradas por nível de dificuldade com
significância — a análise por nível é só descritiva. A resposta às RQs continua
válida agregando os 4 katas, porque o pareamento com/sem IA é sempre feito
dentro da mesma kata (o Wilcoxon compara os 12 trials pareados por kata e por
posição, não exige um nível de dificuldade por par).

## Candidatos levantados

Dez ideias foram avaliadas na S01; seis viraram katas prontas. Da reunião de
priorização por prazo, quatro entraram na execução da S02 — as outras duas
foram removidas do repositório.

| # | Candidato | Situação |
|---|---|---|
| 1 | Consumo de bateria de sensor por tipo de evento | **no experimento (k1, fácil)** |
| 2 | Tarifa de estacionamento por hora iniciada, com teto | **no experimento (k4, difícil)** |
| 3 | Mesclagem de leituras de dois sensores com desempate por precisão | descartado por prazo — reduzido para 4 katas |
| 4 | Escala de plantão com indisponibilidade e balanceamento de carga | **no experimento (k3, média)** |
| 5 | Validação de código de lote com dígito verificador | **no experimento (k2, fácil)** |
| 6 | Ranking de trilhas por pontuação ponderada | descartado por prazo — reduzido para 4 katas |
| 7 | Conversor de números romanos | descartado — kata clássico, alto risco de memorização |
| 8 | Contador de frequência de palavras em texto | descartado — muito indexado, variações de *word count* são onipresentes |
| 9 | Fila de impressão com prioridade | descartado — exige estrutura de dados (heap), sai da faixa de dificuldade |
| 10 | Leitor de arquivo `.ini` | descartado — `configparser` da biblioteca padrão trivializa o exercício |

## Distribuição contrabalanceada

Desenho crossover *within-subject*: cada integrante resolve as quatro katas,
duas com IA e duas sem. Cada integrante recebe uma combinação diferente de
"quais katas ficam com IA", e a ordem de execução também é rotacionada, para
controlar efeito de aprendizado e evitar que uma mesma kata caia sempre no
mesmo tratamento ou na mesma posição da sequência.

| ordem | Brenda | Carlos | Gabriela |
|---|---|---|---|
| 1 | k1 · com-ia | k3 · sem-ia | k4 · com-ia |
| 2 | k2 · sem-ia | k2 · com-ia | k3 · sem-ia |
| 3 | k3 · com-ia | k1 · sem-ia | k1 · com-ia |
| 4 | k4 · sem-ia | k4 · com-ia | k2 · sem-ia |

### Conferência do balanceamento

Por integrante — cada um faz exatamente 2 trials em cada tratamento:

| integrante | com-ia | sem-ia |
|---|---|---|
| Brenda | k1, k3 | k2, k4 |
| Carlos | k2, k4 | k3, k1 |
| Gabriela | k4, k1 | k3, k2 |

Por kata — cada kata é resolvida pelos três integrantes, nunca só num
tratamento:

| kata | com-ia | sem-ia |
|---|---|---|
| k1 | 2 | 1 |
| k2 | 1 | 2 |
| k3 | 1 | 2 |
| k4 | 2 | 1 |

Total: **12 trials**, 6 com IA e 6 sem IA. Com três integrantes e dois
tratamentos não é possível dividir cada kata em 1,5/1,5; a divisão 2/1
alternada entre katas fecha o balanço no total do grupo (as duas fáceis
pendem para sem-ia, a difícil pende para com-ia, cancelando entre si).
Nenhuma posição inicial (ordem 1) repete a mesma kata nos três integrantes, o
que ajuda a separar efeito de ordem de efeito de kata específica.

## Estrutura de pastas

```
lab02/
    katas/
        exemplo/            kata de brinquedo, valida o cronômetro; fora do experimento
        k1/ … k4/           as quatro katas do experimento (fácil, fácil, média, difícil)
            enunciado.md         enunciado da kata
            test_aceitacao.py    suíte de aceitação (não pode ser editada no trial)
            solucao_starter.py   esqueleto copiado para o trial como solucao.py
    trials/
        <integrante>/<kata>-<tratamento>/
            solucao.py      código produzido no trial
            report.xml      saída do pytest ao final do trial
```

## Como validar as katas

```bash
python lab02/scripts/validar_katas.py
```

Para cada kata o script confere que a pasta está completa, que a suíte de
aceitação roda pelo pytest sem erro de coleta, e que com o esqueleto vazio
(`solucao_starter.py`) todos os casos falham — nenhum teste passa "de graça".
Também imprime o nº de casos de teste. Sai com código 1 se alguma kata estiver
mal-formada.

Última execução: **4 katas ok**, 10–11 casos de teste, todos falham sem
implementação.

## Como rodar um trial

```bash
python lab02/scripts/cronometro.py --integrante gabriela --kata k4 --tratamento com-ia --ordem 1
```

Consulte a linha do integrante na tabela de distribuição para saber a kata, o
tratamento e a ordem de cada trial.
