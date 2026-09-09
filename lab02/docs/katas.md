# Katas do experimento

Objetos experimentais do Lab02: seis katas autorais em Python, de dificuldade
comparável, com suíte de testes de aceitação automatizada.

## Por que katas autorais

O enunciado aponta a memorização como ameaça à validade: se a kata for um
clássico do LeetCode/HackerRank, o assistente de IA reproduz uma solução já
vista no treinamento em vez de efetivamente ajudar, e o tratamento *com IA*
passa a medir "a IA lembra disso?" e não "a IA ajuda a resolver isso?".

Todas as seis katas foram escritas pelo grupo, com domínios inventados e regras
próprias. Não têm enunciado equivalente publicado, então não há solução
indexada para a IA recuperar de memória.

## Critério de equivalência de dificuldade

O enunciado exige katas de "dificuldade comparável". Uma kata só entrou no
conjunto se atendesse aos quatro critérios abaixo.

| Critério | Faixa aceita | Obtido |
|---|---|---|
| Nº de casos de teste de aceitação | 8 a 12 | 10 a 11 |
| Nº de regras no enunciado | 5 a 6 | 5 a 6 |
| Conceitos exigidos | apenas biblioteca padrão; varredura linear de uma lista de registros + 3 a 5 regras condicionais + agregação + formatação da saída. Sem recursão, sem estruturas de dados avançadas, sem algoritmos além de percorrer e ordenar | atendido |
| Tempo estimado de resolução manual | 15 a 25 min, dentro do time-box de 35 min | atendido |

O nº de casos de teste é conferido por `scripts/validar_katas.py`. Os demais
critérios foram avaliados na escrita de cada kata.

### As katas selecionadas

| kata | função | casos de teste | regras | esboço do que exige |
|---|---|---|---|---|
| k1 | `consumo_bateria` | 10 | 6 | somatório com taxa por tipo, limite de faixa, dois erros |
| k2 | `calcular_tarifa` | 11 | 5 | parsing de `HH:MM`, franquia, cobrança por faixa, teto, dois erros |
| k3 | `mesclar_leituras` | 10 | 6 | junção de listas, dedup com desempate, ordenação, imutabilidade |
| k4 | `montar_escala` | 10 | 6 | atribuição gulosa com desempate, filtro de disponibilidade, um erro |
| k5 | `validar_lote` | 11 | 5 | validação de formato, três checagens acumuladas em ordem fixa |
| k6 | `ranking_trilhas` | 10 | 6 | pontuação ponderada, filtros de descarte, ordenação com desempate, corte |

Todas têm a mesma forma (varrer uma lista de registros, aplicar regras,
agregar, formatar). k1 e k5 são as mais simples do grupo, k2 a que exige mais
casos de borda (parsing de horário); as outras três ficam no meio. Como o
desenho é *within-subject* e cada kata é resolvida pelos três integrantes, a
variação residual de dificuldade entre katas afeta os dois tratamentos e não
enviesa a comparação com/sem IA.

## Candidatos levantados

Dez ideias foram avaliadas; seis entraram.

| # | Candidato | Situação |
|---|---|---|
| 1 | Consumo de bateria de sensor por tipo de evento | **selecionado (k1)** |
| 2 | Tarifa de estacionamento por hora iniciada, com teto | **selecionado (k2)** |
| 3 | Mesclagem de leituras de dois sensores com desempate por precisão | **selecionado (k3)** |
| 4 | Escala de plantão com indisponibilidade e balanceamento de carga | **selecionado (k4)** |
| 5 | Validação de código de lote com dígito verificador | **selecionado (k5)** |
| 6 | Ranking de trilhas por pontuação ponderada | **selecionado (k6)** |
| 7 | Conversor de números romanos | descartado — kata clássico, alto risco de memorização |
| 8 | Contador de frequência de palavras em texto | descartado — muito indexado, variações de *word count* são onipresentes |
| 9 | Fila de impressão com prioridade | descartado — exige estrutura de dados (heap), sai da faixa de dificuldade |
| 10 | Leitor de arquivo `.ini` | descartado — `configparser` da biblioteca padrão trivializa o exercício |

## Distribuição contrabalanceada

Desenho crossover *within-subject*: cada integrante resolve as seis katas, três
com IA e três sem. A ordem das katas é rotacionada entre os integrantes (deslo­
camento de duas posições) para que nenhuma kata caia sempre no mesmo ponto da
sequência, controlando o efeito de aprendizado. O tratamento alterna a cada
posição, e Carlos começa invertido em relação aos outros dois.

| ordem | Brenda | Carlos | Gabriela |
|---|---|---|---|
| 1 | k1 · com-ia | k3 · sem-ia | k5 · com-ia |
| 2 | k2 · sem-ia | k4 · com-ia | k6 · sem-ia |
| 3 | k3 · com-ia | k5 · sem-ia | k1 · com-ia |
| 4 | k4 · sem-ia | k6 · com-ia | k2 · sem-ia |
| 5 | k5 · com-ia | k1 · sem-ia | k3 · com-ia |
| 6 | k6 · sem-ia | k2 · com-ia | k4 · sem-ia |

### Conferência do balanceamento

Por integrante — cada um faz exatamente 3 trials em cada tratamento:

| integrante | com-ia | sem-ia |
|---|---|---|
| Brenda | k1, k3, k5 | k2, k4, k6 |
| Carlos | k2, k4, k6 | k1, k3, k5 |
| Gabriela | k1, k3, k5 | k2, k4, k6 |

Por kata — cada kata é resolvida pelos três integrantes, nunca só num
tratamento:

| kata | com-ia | sem-ia |
|---|---|---|
| k1 | 2 | 1 |
| k2 | 1 | 2 |
| k3 | 2 | 1 |
| k4 | 1 | 2 |
| k5 | 2 | 1 |
| k6 | 1 | 2 |

Total: **18 trials**, 9 com IA e 9 sem IA. Com três integrantes e dois
tratamentos não é possível dividir cada kata em 1,5/1,5; a divisão 2/1
alternada entre katas fecha o balanço no total do grupo. O mesmo vale para a
posição inicial: dois integrantes começam com IA e um começa sem — está
registrado como limitação na análise de ameaças à validade.

## Estrutura de pastas

```
lab02/
    katas/
        exemplo/            kata de brinquedo, valida o cronômetro; fora do experimento
        k1/ … k6/
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

Última execução: **6 katas ok**, 10–11 casos de teste, todos falham sem
implementação.

## Como rodar um trial

```bash
python lab02/scripts/cronometro.py --integrante gabriela --kata k5 --tratamento com-ia --ordem 1
```

Consulte a linha do integrante na tabela de distribuição para saber a kata, o
tratamento e a ordem de cada trial.
