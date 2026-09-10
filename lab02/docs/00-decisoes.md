# Lab02 — Decisões de setup

Decisões tiradas na primeira reunião da S01. Servem de base para as outras
tarefas da sprint: scripts de coleta de tempo e de testes, seleção de katas e
desenho do experimento.

## Linguagem

Python, versão 3.12 ou mais nova.

A linguagem acompanha a ferramenta de métricas. O CK só roda em Java; optamos
por Python porque a análise da S03 (Pandas, Matplotlib, Seaborn) já é em Python
e o `pytest` gera um relatório de testes simples de processar para a contagem de
defeitos da RQ2. Escrever katas com testes de aceitação em `pytest` também é
mais rápido do que montar projeto JUnit para cada uma.

## Ferramentas de métricas estáticas

- **Radon** — complexidade ciclomática (`radon cc`), LOC (`radon raw`, campo
  `sloc`) e índice de manutenibilidade (`radon mi`).
- **jscpd** — duplicação de código (`jscpd`), que o Radon não mede. Equivale ao
  PMD CPD citado no enunciado.

A mesma configuração das duas ferramentas vale para todos os trials. Versões
travadas depois de montar o ambiente:

- radon: 6.0.1
- jscpd: 5.2.0

## Assistente de IA

Claude Code (assinatura paga), modelo Claude Sonnet 5. Mesma ferramenta e mesmo
modelo para os três integrantes e em todos os trials do tratamento *com IA*. Os
três precisam ter o Claude Code instalado e autenticado antes da S02.

- No início de cada trial, anotar a versão (`claude --version`) e confirmar o
  modelo em `/model` (`claude-sonnet-5`), para a seção de reprodutibilidade do
  relatório.
- Regras de uso dos tratamentos (`com-ia` pode editar `solucao.py` e rodar os
  testes direto, sem limite de iterações; `sem-ia` com Claude Code fechado e
  autocompletar por IA da IDE desligado) fechadas em
  [01-desenho-experimento.md](01-desenho-experimento.md) (#64), item (D).
- Coluna `prompts` da planilha = número de mensagens enviadas ao agente no
  trial.

## Testes de aceitação

`pytest`. Cada kata tem um `test_aceitacao.py` com um número fixo de casos, que
não pode ser alterado durante o trial. O trial termina quando todos os casos
passam ou quando o tempo acaba.

Relatório usado pelos scripts de coleta:

```
pytest --junitxml=report.xml <kata>/
```

## Ambiente de cada integrante

| Integrante | SO | IDE | Python | Node |
|---|---|---|---|---|
| Brenda | | | | |
| Carlos | | | | |
| Gabriela | Windows 11 Home (build 26200) | VS Code | 3.14.3 | 24.14.0 |

Nos trials sem IA, desligar plugins de IA da IDE (Copilot, Codeium e afins).

## Dados da coleta

Dois arquivos em `lab02/dados/`, ligados por `integrante` + `kata` +
`tratamento`.

### trials.csv

| coluna | valores | descrição |
|---|---|---|
| integrante | brenda, carlos, gabriela | quem fez o trial |
| kata | k1..k6 | identificador do kata |
| tratamento | com-ia, sem-ia | com ou sem assistente |
| ordem | 1..6 | posição do trial na sequência do integrante |
| data_inicio | ISO 8601 | início do trial |
| tempo_segundos | inteiro | tempo até todos os testes passarem; 2100 se o tempo acabar antes |
| censurado | true, false | true quando o trial terminou pelo tempo, sem passar tudo |
| testes_total | inteiro | número de casos de teste do kata |
| testes_passando | inteiro | casos passando no fim do trial |
| prompts | inteiro | interações com a IA (0 quando sem-ia) |
| observacoes | texto | anotações do trial |

Taxa de sucesso e número de testes falhando são calculados na análise a partir
dessas colunas.

### metricas-estaticas.csv

Gerado pelo script de métricas sobre o código final de cada trial.

| coluna | descrição |
|---|---|
| integrante, kata, tratamento | chave; junta com trials.csv |
| loc | linhas de código (radon raw, sloc) |
| cc_media | complexidade ciclomática média por função |
| cc_max | maior complexidade entre as funções |
| mi | índice de manutenibilidade |
| duplicacao_pct | porcentagem de linhas duplicadas |

### Pastas dos trials

```
lab02/trials/<integrante>/<kata>-<tratamento>/
    solucao.py
    report.xml
```

## Parâmetros do experimento

- Tempo por trial: 35 minutos. Pode ser reduzido, com justificativa no
  relatório, nunca aumentado.
- Trial que estoura o tempo entra como censurado (`censurado = true`,
  `tempo_segundos = 2100`). Não descartar.
- Katas: 6 (o mínimo permitido é 4). Número final e distribuição entre os
  integrantes ficam na tarefa de seleção de katas.
- Trials: 3 integrantes x 6 katas = 18, sendo 9 com IA e 9 sem.
- Estatística: mediana e IQR nas tabelas descritivas; Wilcoxon pareado na
  análise inferencial.

## Fora do escopo desta tarefa

Hipóteses, ameaças à validade, seleção e validação das katas, tabela de
contrabalanceamento e detalhamento de variáveis e tratamentos ficam nas outras
issues da S01.
