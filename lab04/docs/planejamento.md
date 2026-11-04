# Lab04 — Planejamento das Sprints 01 e 02

Planejamento das sprints 01 e 02 do Lab04 (testes de hipótese por dentro: cenário, simulação e visualização). As seções citadas entre parênteses referem-se ao enunciado do Lab04. A Entrega Final (dashboard completo e apresentação oral) cai no mesmo dia que o fim da Sprint 2 e por isso entra no planejamento dela (seção 4).

Siglas: RQ (*Research Question*); CI (*Continuous Integration*, integração contínua); PR (*Pull Request*); WIP (*Work in Progress*, trabalho em andamento); CSV (*Comma-Separated Values*); IC (intervalo de confiança); API (*Application Programming Interface*).

## 1. Calendário

| Sprint | Período | Pontos | Entrega |
|---|---|---|---|
| Lab04S01 | 03/11 (ter) a 05/11 (qui): 3 dias | 7 | Dados reais, cenário, gerador de dados simulados, os dois testes em um conjunto simulado com interpretação, G1 e G2 — já dentro do dashboard |
| Lab04S02 | 06/11 (sex) a 12/11 (qui): 7 dias, com um fim de semana | 7 | Simulações Q1, Q2 e Q3, G3 e G4 — já dentro do dashboard |
| Entrega Final | 12/11 (qui), no fim da S02 | 6 | Dashboard completo (3) e apresentação oral (3) |

A S01 é curta: o planejamento original de 7 dias foi comprimido em 3 (seção 3), com 11 Issues. A S02 tem 7 dias e carrega também a Entrega Final: o dashboard completo fica pronto em 11/11 e 12/11 é o dia da apresentação. As simulações são baratas (poucos segundos), então a folga vem delas, não de um dia livre no fim.

### 1.1 Viabilidade de prazo (verificada em 03/11/2026)

| Item | Resultado | Consequência |
|---|---|---|
| Token e limite da API | `GITHUB_TOKEN` do `.env` válido; 5.000 requisições/h no REST e 30/min na busca | A coleta de ~60 PRs cabe em minutos |
| Disponibilidade de PRs (busca `is:pr is:merged`, sem PRs de Dependabot e Renovate) | De 01/05/2026 em diante: `supabase/supabase` tem 3.709 PRs mesclados, 257 com revisão do Copilot (~7%). `astral-sh/ruff`: 2.460 mesclados, só 9 com Copilot. `home-assistant/core`: 11.964 mesclados, 11.357 com Copilot (~95%, sem grupo de controle) | `supabase/supabase` é o candidato: sobram PRs dos dois lados. Ruff e Home Assistant não servem para este par |
| Teste da coleta (agosto a outubro de 2026, `supabase/supabase`) | 2 buscas de 100 resultados trouxeram `created_at` e `merged_at` direto: 189 PRs mesclados com revisão do Copilot e 1.695 sem. Tempo até o merge: com bot, mediana 41 h, p25–p75 de 19 a 90 h; sem bot, mediana 4,5 h, p25–p75 de 0,7 a 23 h | A coleta da S01-04 é uma tarefa de horas, não de dias. Os dados são assimétricos (média/mediana 1,8 e 3,5), o que sustenta a lognormal. Esses 200 PRs foram uma amostra de teste (os 100 mais recentes por grupo), não a amostra final |
| Limite secundário da busca | Atingido ao disparar ~40 buscas seguidas com 2 s de pausa; as 2 buscas acima, com 20 s de pausa, passaram | O coletor deve pausar ≥ 10 s entre buscas e obedecer `Retry-After`; não paralelizar |
| Custo da simulação | ~0,25 s por célula de 10.000 repetições (n = 30), ~10 s para a grade inteira | Simulação não é gargalo |

Conclusão: a coleta e as simulações cabem nos prazos. O caminho crítico é humano (escrever o cenário e a expectativa antes de simular, revisar PRs, redigir os textos do dashboard). O risco real está na S01, que tem 3 dias.

Duas observações sobre a espiada nos dados reais feita na verificação: (1) ela serviu para checar viabilidade; a expectativa de qual teste se sai melhor continua sendo sobre a simulação e é escrita em S01-03 antes de rodar qualquer simulação; (2) a diferença de 41 h contra 4,5 h é grande e provavelmente confundida: o revisor automático pode ser pedido em PRs maiores, e PRs que ficam abertos mais tempo têm mais chance de receber a revisão. Isso entra como limitação em S01-02.

## 2. Decisões

### 2.1 Cenário (proposta; o grupo confirma em S01-02)

| Tema | Decisão proposta | Motivo |
|---|---|---|
| Par de testes | **P1: t de Welch × Mann-Whitney** | Tempo até o merge é assimétrico por natureza, o que torna a Q3 natural; a coleta é só consulta à API do GitHub, sem rodar builds locais (P2) nem depender de dataset de terceiros (P5) |
| Pergunta | O tempo até o merge de PRs muda quando um bot de revisão atua no PR? | — |
| H₀ | A distribuição do tempo até o merge é a mesma com e sem bot (em particular, as médias são iguais para o Welch e P(X > Y) = 0,5 para o Mann-Whitney) | Na simulação com H₀ verdadeira os dois grupos saem da mesma distribuição, então as hipóteses nulas dos dois testes valem juntas |
| H₁ | O tempo é diferente com bot (bicaudal) | Não há direção a priori: o bot pode acelerar (feedback imediato) ou atrasar (comentários extras a resolver). Responde à pergunta 2 da apresentação |
| Erro tipo I | Concluir que o bot muda o tempo de merge quando não muda | Rascunho; o grupo decide qual é mais grave (pergunta 8) |
| Erro tipo II | Não perceber um efeito real do bot | — |
| Fonte dos dados | PRs mesclados de um repositório público em que parte dos PRs recebe revisão de bot; ~30 por grupo | Enunciado, item b |

Cuidados na coleta, a registrar como limitação: PRs abertos pelo próprio bot (ex.: Dependabot) entram em outra população e devem ficar de fora; usar a mesma janela de tempo nos dois grupos; só PRs mesclados (PRs fechados sem merge ficam fora e isso é viés de seleção); o tamanho do PR não é controlado.

### 2.2 Simulação

| Tema | Decisão |
|---|---|
| Distribuição de referência | Lognormal com mediana e σ(log) estimados dos dados reais (ajuste por mediana e desvio-padrão de log(tempo)) |
| Efeito | Deslocamento δ na escala log: razão de medianas = e^δ. Com δ = 0 os grupos são idênticos |
| Grade de efeitos | 6 valores começando em 0 (ex.: 0; 0,2; 0,4; 0,6; 0,8; 1,0). A grade final é fixada em S02-01 por um piloto de 1.000 repetições, para a curva de poder do cenário de referência ir de ~5% até perto de 100% |
| Repetições | 10.000 por cenário e efeito (margem de erro de ±0,43 ponto percentual em torno de 5%) |
| Nível de significância | Rejeições contadas em α = 0,05 **e** α = 0,01 na mesma execução. A pergunta 12 da apresentação pede α = 0,01 e assim não é preciso re-simular |
| Testes | `scipy.stats.ttest_ind(equal_var=False)` e `scipy.stats.mannwhitneyu(alternative="two-sided")` |
| Semente | `np.random.SeedSequence(42)` com `spawn` por (cenário, efeito): cada célula tem seu gerador e o resultado não depende da ordem nem de rodar em paralelo |
| Tamanho de efeito (dados reais) | Hedges g (ou d de Cohen) para o Welch; delta de Cliff (ou correlação bisserial por postos) para o Mann-Whitney; razão de medianas como medida de relevância prática |

Cenários da Q3 (cada um roda Q1 e Q2 completos). Os valores exatos são fixados em S02-01.

| Cenário | Como é gerado | Pressuposto violado |
|---|---|---|
| C0 — controle | Normal, n = 30 por grupo | Nenhum; confirma que o código acerta o caso fácil |
| C1 — referência | Lognormal calibrada nos dados reais, n = 30 por grupo | Normalidade, no grau observado nos dados reais |
| C2 — assimetria forte | Lognormal com σ(log) bem acima do real (ex.: 1,5 a 2) | Normalidade da média amostral |
| C3 — outliers | C1 com ~5% das observações multiplicadas por ~20, nos dois grupos | Sensibilidade da média a valores extremos |
| C4 — amostra pequena | C1 com n = 10 por grupo | Aproximação assintótica de ambos os testes |

Opcional se sobrar tempo: variâncias e tamanhos de grupo desiguais. Cuidado: com variâncias diferentes a H₀ "médias iguais" deixa de ser "distribuições iguais", e o Mann-Whitney testa outra coisa; a leitura de erro tipo I muda e precisa ser explicada.

### 2.3 Implementação e dashboard

| Tema | Decisão proposta |
|---|---|
| Linguagem e bibliotecas | Python 3.12, NumPy, SciPy, pandas, Plotly (mesmo `requirements.txt` do Lab03, sem Streamlit) |
| Dashboard | Página HTML estática gerada com Plotly, publicada no GitHub Pages. Sem servidor, sem *cold start* na apresentação, link estável para o topo do dashboard. Alternativa: Streamlit Community Cloud (mais interativo, mas pode hibernar) |
| Separação | A simulação grava CSVs em `dados/`; o dashboard só lê os CSVs. Rodar 10.000 repetições nunca bloqueia a abertura da página |
| Comando único | `python -m lab04` lê o CSV da coleta, roda as simulações e gera o dashboard (a coleta pela API fica em comando à parte). Detalhado no README em S02-13 |
| Gráficos | Mesma cor por teste em todos os gráficos (Welch e Mann-Whitney), título, eixos com nome e unidade, legenda. G3 com IC de Wilson e linha em 5%; G4 uma faceta por cenário |
| Reuso do Lab03 | Nenhum dado nem resultado (o enunciado exige independência). Reaproveitar só o padrão de estrutura, CI e issues |

### 2.4 Processo

| Tema | Decisão |
|---|---|
| Atribuição | Sem papéis fixos: cada Issue é assumida no dia previsto por um integrante disponível, garantindo que cada integrante seja Assignee de ao menos uma Issue de código por sprint (seção 7) |
| WIP | 1 Issue por integrante |
| Definição de pronto | PR mesclado, commits `#<número da Issue> descrição` (commit sem número não conta), CI verde em Issues de código |
| Branches | `<número>-<descrição-curta>` |
| Quadro | GitHub Projects do grupo ([projeto 9](https://github.com/users/gabialvarenga/projects/9)); cartões atualizados diariamente; *snapshot* do quadro ao fim de cada sprint |
| Expectativa antes da simulação | O commit de S01-03 (expectativa por escrito de qual teste vai melhor e por quê) precisa ser anterior ao primeiro commit que roda simulação. Vale como prova na pergunta 13 |
| Nomes das Issues | `S01-xx` e `S02-xx`, com rótulo `lab04` |

## 3. Sprint 01 — 03/11 a 05/11: dados, cenário, gerador, G1 e G2

### 3.1 Issues

| Issue | Tipo | Dia | Depende de | Entregas (seção do enunciado) |
|---|---|---|---|---|
| S01-01 Criar a estrutura do `lab04/`, dependências, README e CI | código | 03/11 | — | Comando único, semente fixa (7) |
| S01-02 Escolher o par e definir o protocolo de coleta | doc | 03/11 | — | Item a e b: par, repositório, definição de "com/sem bot", janela, amostragem aleatória com semente, limitações |
| S01-03 Escrever o cenário: pergunta, H₀/H₁, erros I/II e expectativa | doc | 03/11 | S01-02 | Item c: pergunta, hipóteses, expectativa antes de simular |
| S01-04 Coletar os dados reais e gerar o CSV | código | 03/11–04/11 | S01-02 | Item b: ~30 PRs por grupo, origem e método registrados |
| S01-05 Implementar os dois testes e o tamanho de efeito | código | 03/11 | — | `aplicar_testes(a, b)`: Welch, Mann-Whitney, p-valor, efeito; testes com casos conhecidos |
| S01-06 Descritiva, dicionário de dados e calibração da simulação | código | 04/11 | S01-04 | Mediana, IQR, assimetria, outliers; parâmetros da lognormal com justificativa (item c) |
| S01-07 Implementar o gerador de dados simulados | código | 04/11 | — | `gerar_amostra(cenario, delta, n, rng)`; testes unitários; roda com parâmetros provisórios |
| S01-08 Aplicar os dois testes a um conjunto simulado e interpretar | código | 04/11 (refeito com os parâmetros calibrados em 05/11 de manhã) | S01-03, S01-05, S01-07 | Conjunto simulado com semente fixa; interpretação escrita no resultado |
| S01-09 Construir o G1 (dados reais × simulados) | código | 05/11 | S01-06, S01-07 | Histograma de cada grupo, real ao lado do simulado |
| S01-10 Construir o G2 (estatística sob H₀, região de rejeição, p-valor) | código | 05/11 | S01-05, S01-08 | Curva sob H₀, regiões sombreadas, p-valor do exemplo como área |
| S01-11 Montar o dashboard (seções 1 a 3, links no topo) | código | 05/11 | S01-09, S01-10 | Seções 1 a 3, texto de 2 a 4 frases por gráfico; abre com um comando (4) |

### 3.2 Carga por dia (3 integrantes, WIP 1)

Cada coluna é uma pessoa, sem papéis fixos: quem estiver disponível assume a Issue. A tabela mostra só o encadeamento.

| Dia | Pessoa 1 | Pessoa 2 | Pessoa 3 |
|---|---|---|---|
| 03/11 | S01-01, depois S01-03 | S01-02, depois S01-04 (começa) | S01-05 |
| 04/11 | S01-07 | S01-04 (termina), depois S01-06 | S01-08 (provisória, depois recalibra) |
| 05/11 | S01-09 (G1) | S01-11 (dashboard) | S01-10 (G2) |

Cada integrante assume ao menos uma Issue de código (S01-01, S01-04 e S01-05 já cobrem os três).

### 3.3 Marcos

1. **Fim de 03/11:** estrutura e CI no `main`; par e cenário com expectativa commitados (S01-02, S01-03); funções de teste prontas (S01-05); coleta iniciada. **A S01-03 precisa estar mesclada antes de S01-08**, porque é a prova de que a expectativa veio antes da simulação.
2. **Fim de 04/11:** CSV de dados reais e calibração commitados (S01-04, S01-06); gerador pronto (S01-07); primeiro exemplo simulado (S01-08).
3. **Meio-dia de 05/11:** G1 e G2 abertos em PR. Reservar a tarde para revisão, correção e o dashboard (S01-11).
4. **Fim de 05/11:** PRs mesclados, dashboard abrindo com o comando do README, *snapshot* do quadro.

As Issues de gráfico e de dashboard trabalham contra interfaces congeladas (`g1(dados, simulados) -> figura`, `g2(...) -> figura`), então a S01-11 pode começar a montar o dashboard antes de G1 e G2 chegarem.

### 3.4 Pontos de atenção

| Risco | Efeito | Resposta |
|---|---|---|
| Só 3 dias, com 05/11 concentrando G1, G2 e dashboard | Entrega incompleta | Issues criadas hoje, antes de começar; interfaces congeladas; PRs pequenos |
| Hora de corte de 05/11 não confirmada (aula à noite) | Menos tempo no dia 05 | Tratar o meio-dia de 05/11 como prazo de G1 e G2 |
| Atraso durante a sprint | Escopo maior que o tempo | Cortar nesta ordem: texto longo das seções (refinado na S02), publicação (passa para S02-13), cenário opcional. Não cortar G1, G2, expectativa nem o exemplo simulado |
| Amostra real de ~30 por grupo dá σ(log) instável | Calibração fraca | Registrar o IC do σ; usar o valor central na referência e variar em C2 |
| Primeiro PR no dia 03/11 | CI quebrado trava os demais | S01-01 entrega `pytest` com um teste mínimo passando |
| Exemplo simulado dar "não significativo" por acaso | Texto fraco | Fixar a semente do exemplo antes de ver o p-valor; mostrar dois exemplos (sem efeito e com efeito) |
| G2 com duas estatísticas (t e U/z) | Confusão ao explicar | Um painel por teste, mesma região de 5% e o mesmo exemplo; perguntas 6 e 7 respondidas sobre o painel do Welch |

## 4. Sprint 02 e Entrega Final — 06/11 a 12/11: Q1, Q2, Q3, G3, G4, dashboard completo e apresentação

A Entrega Final (dashboard completo, 3 pontos, e apresentação oral, 3 pontos) cai no mesmo dia que o fim da S02, 12/11. Por isso o dashboard completo, com as 7 seções, precisa estar pronto em 11/11, e 12/11 é o dia da apresentação, não de reserva.

### 4.1 Issues

| Issue | Tipo | Dia | Depende de | Entregas (seção do enunciado) |
|---|---|---|---|---|
| S02-01 Fixar cenários C0 a C4, grade de efeitos, `config.yaml` e formato do CSV de resultados (piloto de 1.000 repetições) | código | 06/11 | Sprint 01 | Q2: ≥ 5 efeitos, começando em zero; Q3: situações |
| S02-02 Implementar o motor de simulação | código | 06/11–07/11 | S02-01 | `simular(cenario, delta, n_rep, rng)`: proporção de rejeições em α = 0,05 e 0,01, IC de Wilson, `SeedSequence.spawn` por célula |
| S02-03 Simular C0 e C1 (Q1 e Q2) | código | 08/11 | S02-02 | 10.000 repetições por célula; CSV em `dados/` |
| S02-04 Simular C2 e C3 (Q3: assimetria e outliers) | código | 08/11 | S02-02 | CSV |
| S02-05 Simular C4 (Q3: amostra pequena) e, se couber, variâncias desiguais | código | 08/11 | S02-02 | CSV |
| S02-06 Verificar a simulação | código | 09/11 | S02-03 a S02-05 | Testes: C0 com n grande ≈ 5%, mesma semente gera o mesmo CSV, erro de Monte Carlo dentro de ±0,43 p.p. |
| S02-07 Consolidar os resultados e classificar cada teste (liberal, conservador ou ok) | código | 09/11 | S02-06 | Tabela única; critério: fora de 5% ± IC de Wilson |
| S02-08 Construir o G3 (erro tipo I por situação) | código | 09/11–10/11 | S02-07 (o formato do CSV já vale desde S02-01) | Q1 e Q3, linha em 5%, barras de erro |
| S02-09 Construir o G4 (curvas de poder) | código | 09/11–10/11 | S02-07 (idem) | Q2 e Q3, uma faceta por cenário, efeito no eixo x com unidade |
| S02-10 Aplicar os dois testes aos dados reais e montar a seção 6 do dashboard | código | 07/11 | Sprint 01 | Tabela: estatística, p-valor, tamanho de efeito e conclusão de cada teste (4, seção 6) |
| S02-11 Atualizar o dashboard com as seções 4 e 5 | código | 10/11 | S02-08, S02-09 | Texto de 2 a 4 frases por gráfico (4) |
| S02-12 Escrever a seção 7 do dashboard: expectativa × resultado e recomendação | doc | 10/11–11/11 | S02-07, S02-10 | O que o grupo esperava × o que encontrou; qual teste usar e quando a escolha mudaria (4, seção 7) |
| S02-13 Comando único regenera dados, simulações e dashboard; publicar no GitHub Pages | código | 11/11 | S02-11 | README, semente fixa, tempo de execução registrado, link e repositório no topo (4, 7) |
| S02-14 Preparar a apresentação: respostas às 15 perguntas, divisão entre os integrantes e ensaio | doc | 11/11 | S02-11, S02-12 | Cada integrante com ≥ 4 perguntas; respostas de ~25 s; ensaio cronometrado em ≤ 7 min (5) |

Em 12/11 não há Issue nova: de manhã, correções finais e *snapshot* do quadro; depois, a apresentação.

### 4.2 Carga por dia (3 integrantes, WIP 1)

| Dia | Pessoa 1 | Pessoa 2 | Pessoa 3 |
|---|---|---|---|
| 06/11 | S02-01 | S02-02 | S02-10 |
| 07/11 | S02-02 (revisão e término, em dupla com a Pessoa 2) | S02-02 (termina) | S02-10 (termina) |
| 08/11 | S02-03 | S02-04 | S02-05 |
| 09/11 | S02-06 | S02-07 | S02-08 |
| 10/11 | S02-09 | S02-11 | S02-12 (começa) |
| 11/11 | S02-13 | S02-12 (termina) | S02-14 |

Cada coluna é uma pessoa, sem papéis fixos. Em 07/11, a Pessoa 1 apoia a S02-02 por revisão: o Assignee continua sendo a Pessoa 2, e a Pessoa 1 pode puxar a próxima Issue da fila se já tiver terminado a S02-01. Ver os pontos de atenção sobre o fim de semana.

### 4.3 Marcos

1. **Fim de 06/11:** `config.yaml` e formato do CSV congelados; mudar parâmetro depois exige refazer as simulações. Os gráficos podem ser desenvolvidos contra esse formato desde 07/11, com dados do piloto.
2. **Fim de 07/11:** seção 6 (dados reais) pronta; motor de simulação mesclado.
3. **Fim de 08/11:** os três CSVs de simulação commitados.
4. **Fim de 09/11:** resultados consolidados e verificados.
5. **Fim de 10/11:** G3, G4 e seções 4 e 5 prontos.
6. **Fim de 11/11:** dashboard completo (7 seções), publicado e abrindo com um comando; respostas das 15 perguntas ensaiadas.
7. **12/11:** correções finais, *snapshot* e apresentação.

### 4.4 Pontos de atenção

| Risco | Efeito | Resposta |
|---|---|---|
| Entrega Final no mesmo dia do fim da S02 | Sem reserva depois de 11/11 | 11/11 é o prazo real do dashboard; 12/11 só recebe correções. Qualquer atraso corta primeiro o cenário opcional e a pergunta extra, nunca o ensaio |
| Sábado e domingo (07 e 08/11) na rota das simulações | Atraso se o grupo não puder trabalhar | A simulação leva segundos; S02-03 a S02-05 podem passar para 09/11 e S02-06/S02-07 para 09/11 e 10/11, comendo a folga, que agora é só 10/11 |
| 15 perguntas em 7 minutos | 15 × 30 s = 7,5 min, acima do limite | Respostas de ~25 s; ensaio cronometrado na S02-14; as perguntas mais complexas (6, 7, 11) com resposta pronta de uma frase |
| Custo da simulação | Medido em 03/11: ~0,25 s por célula de 10.000 repetições (n = 30), grade inteira em poucos segundos | Sem risco de prazo; o CI pode rodar as 10.000 repetições |
| Mann-Whitney com n pequeno usa p-valor exato (n ≤ 8, sem empates) | Teste conservador por discretização, e não por falha do método | Usar n = 10 em C4 e registrar o método (`exact` ou `asymptotic`) |
| Grade de efeitos mal calibrada | Curvas de poder planas em 5% ou já em 100% | Piloto na S02-01; calibrar antes de congelar |
| Mudar parâmetros depois de ver os resultados | Dúvida sobre a validade (pergunta 13) | Congelar o `config.yaml` e citar o commit na conclusão |
| Textos do dashboard só no fim | Seções 4 e 5 sem conclusão | Texto de cada gráfico faz parte da Issue do gráfico, não só da S02-11 |
| GitHub Pages ainda não configurado | Link do topo do dashboard sem destino | Habilitar Pages na S02-01 e usar o link desde a S01-11, mesmo que a página só apareça na S02-13 |
| Apresentação "usando o próprio dashboard" | Internet ou Pages fora do ar na hora | Ter o HTML gerado salvo localmente e abrir com o comando único como plano B |

## 5. Estrutura de pastas proposta

```
lab04/
    README.md              # comando único, dependências, estrutura
    requirements.txt
    pytest.ini
    config.yaml            # semente, repetições, α, cenários, grade de efeitos (S02-01)
    lab04/                 # pacote Python; `python -m lab04` é o ponto de entrada
        __main__.py        # orquestra simulações e dashboard                          (S02-13)
        coleta.py          # coleta de PRs pela API do GitHub                          (S01-04)
        descritiva.py      # mediana, IQR, assimetria, outliers                        (S01-06)
        calibracao.py      # parâmetros da lognormal a partir dos dados reais          (S01-06)
        gerador.py         # gerar_amostra(cenario, delta, n, rng)                     (S01-07)
        testes.py          # Welch, Mann-Whitney, tamanho de efeito                    (S01-05)
        simulacao.py       # motor: rejeições, IC de Wilson, SeedSequence              (S02-02)
        graficos.py        # g1, g2, g3, g4 em Plotly                                  (S01-09, 10; S02-08, 09)
        dashboard.py       # monta o HTML com as 7 seções                              (S01-11, S02-10, S02-11, S02-12)
    tests/                 # pytest, um arquivo test_<módulo>.py por módulo
    dados/
        reais/             # CSV da coleta e dicionário de dados
        simulacao/         # resultados de Q1, Q2 e Q3 (CSV)
    dashboard/             # HTML gerado (publicado)
    docs/                  # planejamento, cenário, protocolo de coleta, respostas orais
```

O CI do Lab04 fica em `.github/workflows/lab04-testes.yml`, na raiz do repositório, nos moldes do `lab03-testes.yml`.

## 6. Cobertura do enunciado

| Exigência | Onde |
|---|---|
| Par de testes, cenário, H₀/H₁, expectativa (a, c) | S01-02, S01-03 |
| Dados reais, origem registrada (b) | S01-04, S01-06 |
| Parâmetros a partir dos dados reais (c) | S01-06 |
| Código dos dados simulados, testes aplicados e interpretação (S01) | S01-05, S01-07, S01-08 |
| G1, G2 dentro do dashboard (S01) | S01-09, S01-10, S01-11 |
| Q1, Q2, Q3 (d) | S02-03 a S02-05 |
| G3, G4 dentro do dashboard (S02) | S02-08, S02-09, S02-11 |
| Seção 6 (dados reais) e seção 7 (conclusão) do dashboard | S02-10, S02-12 |
| Dashboard abre com um comando ou está publicado; links no topo | S02-13 |
| Apresentação oral: 15 perguntas, ≥ 4 por integrante, 7 minutos | S02-14 |
| Comando único e semente fixa (7) | S01-01, S02-13 |
| Pergunta 12 da apresentação (α = 0,01) | S02-02 grava as duas taxas |

## 7. Checagens de processo

- Cada integrante é Assignee de ao menos uma Issue de código por sprint. Conferir no meio de cada sprint (04/11 e 09/11), e se faltar alguém, essa pessoa assume a próxima Issue de código.
- Issues sem Assignee, WIP acima de 1 e cartões desatualizados entram no desconto de até 10% da nota da sprint.
- A ausência de evolução semanal também entra nesse desconto: manter commits e cartões andando ao longo da sprint, e não um único PR no último dia.

## 8. Fora do escopo das sprints (seção 6 do enunciado, opcional)

Com o motor da S02-02 as perguntas abaixo são baratas e podem alimentar a conclusão: poder de cada teste no n real (~30) para o efeito observado; n necessário para 80% de poder; leitura de resultado não significativo (sem efeito × amostra pequena); p-valor × tamanho de efeito. Só começar depois da S02-12, e apenas se sobrar tempo antes do ensaio da S02-14.
