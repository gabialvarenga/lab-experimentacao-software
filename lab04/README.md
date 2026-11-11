# Lab04 — Testes de hipótese por dentro

Laboratório de simulação que compara dois testes para a mesma pergunta: o t de Welch e o Mann-Whitney (par P1 do enunciado). O grupo gera dados simulados com efeito conhecido, mede o erro tipo I e o poder de cada teste em situações que respeitam ou violam os pressupostos, e apresenta tudo num dashboard. Uma pequena amostra de dados reais (tempo até o merge de PRs, com e sem revisão de bot) calibra a simulação e é testada ao final.

## Integrantes

- Brenda Evers (1523565)
- Carlos José Gomes Batista Figueiredo (1507022)
- Gabriela Alvarenga Cardoso (1026227)

## GitHub Projects (Kanban)

Board do grupo: [Kanban](https://github.com/users/gabialvarenga/projects/9)

## Como executar

Requer Python 3.12. A partir da raiz do repositório:

```bash
python -m pip install -r lab04/requirements.txt
cd lab04
python -m lab04
```

`python -m lab04` é o comando único: lê o CSV da coleta, roda as simulações, gera o dashboard em `dashboard/index.html` e o abre no navegador. Todas as simulações usam a semente fixa de `config.yaml` (`numpy.random.default_rng(42)`), então os resultados se reproduzem.

**Dashboard.** Para gerar só o dashboard e abri-lo no navegador:

```bash
cd lab04
python -m lab04 dashboard              # --sem-abrir: só grava o HTML
```

Leva poucos segundos. O `dashboard/index.html` é um arquivo único, com o Plotly embutido, e abre sem internet (só os links do topo precisam de rede). Ele não é versionado: é regerado pelo comando.

**Estado atual (Sprint 01):** o dashboard tem as seções 1 (cenário), 2 (os dados, G1) e 3 (como os testes funcionam, G2); as seções 4 a 7 aparecem como "em construção" até a Sprint 02. A etapa `simular` ainda não existe: sozinha, ela avisa e sai com código 1; no comando único, ela avisa e o dashboard é gerado mesmo assim.

**Coleta dos dados reais.** A coleta pela API fica fora do comando único, porque precisa de um token do GitHub; o `dados/reais/prs.csv` já está versionado. Para refazê-la:

```bash
export GITHUB_TOKEN=<token>      # PowerShell: $env:GITHUB_TOKEN = "<token>"
cd lab04
python -m lab04 coletar
```

Leva cerca de dez minutos, por causa da pausa de 20 s entre buscas que evita o limite secundário da API. As respostas ficam em `dados/reais/cache/` (fora do Git), então repetir o comando é rápido; apague a pasta para uma coleta nova. O comando regrava `dados/reais/prs.csv` e `dados/reais/registro-coleta.md`. As regras (janela, grupos, critérios e sorteio com semente 42) estão em [docs/protocolo-coleta.md](docs/protocolo-coleta.md).

Testes:

```bash
cd lab04
python -m pytest --cov=lab04 --cov-report=term-missing --cov-fail-under=80
```

## Simulação: cenários, grade e formato do CSV

Os parâmetros da simulação ficam na seção `simulacao` de [config.yaml](config.yaml) e estão **congelados** desde o merge da Issue #236: mudar qualquer valor exige refazer todas as simulações e justificar a mudança. A semente é 42 (`numpy.random.SeedSequence(42)`, com um gerador por célula). Cada célula (cenário × efeito) roda 10.000 repetições, com α = 0,05 e α = 0,01 contados na mesma execução.

### Cenários e grade de efeitos

O grupo A vem de `mu` e `sigma`; o grupo B é o A com o efeito δ (ver `gerador.py`). Em C0, δ é em desvios-padrão; nos demais, δ é somado ao μ da lognormal, e a razão de medianas é e^δ.

| Cenário | Como é gerado | n por grupo | Efeitos δ | Pressuposto violado |
|---|---|---|---|---|
| C0 — controle | normal, μ = 0, σ = 1 | 30 | 0; 0,2; 0,4; 0,6; 0,8; 1,0 (dp) | nenhum |
| C1 — referência | lognormal, μ = 2,6739 e σ = 1,6493 (de `dados/reais/calibracao.json`) | 30 | 0; 0,4; 0,8; 1,2; 1,6; 2,0 (log) | normalidade, no grau dos dados reais |
| C2 — assimetria forte | C1 com σ = 2,0 | 30 | mesma grade de C1 | normalidade da média amostral |
| C3 — outliers | C1 com ~5% das observações × 20, nos dois grupos | 30 | mesma grade de C1 | sensibilidade da média a extremos |
| C4 — amostra pequena | C1 | 10 | mesma grade de C1 | aproximação assintótica dos testes |

Observações sobre os valores:

- O σ de C1 é o σ combinado dos dois grupos (raiz da média das variâncias de log(horas)), porque o gerador usa um σ só; o μ é o do grupo `com_bot`. A calibração tem σ = 1,48 (com bot) e 1,80 (sem bot).
- C2 usa σ = 2,0, o limite superior da faixa de 1,5 a 2 do enunciado da Issue. Em relação ao σ combinado de C1 (1,65) o aumento é de 21%, mas a assimetria populacional sobe de ~65 para ~414.
- C3 sorteia a contaminação por observação (probabilidade 0,05), então a fração de valores multiplicados é 5% em média, para qualquer n.
- C4 tem n = 10 por grupo, acima de 8, então o Mann-Whitney usa o p-valor assintótico (`mw_metodo = asymptotic`), e não o exato.
- O efeito observado nos dados reais (δ ≈ 0,35) fica perto do segundo ponto da grade log (0,4).

### Piloto e calibração da grade

O piloto roda a grade inteira com 1.000 repetições por célula e semente 42 (`python -m lab04.piloto`, alguns segundos) e grava `dados/simulacao/piloto.csv`. A grade foi calibrada nele, com o critério da Issue: a curva de poder de C1 vai de ~5% até perto de 100%.

| δ em C1 (log) | 0 | 0,4 | 0,8 | 1,2 | 1,6 | 2,0 |
|---|---|---|---|---|---|---|
| Mann-Whitney, α = 0,05 | 4,1% | 14,1% | 42,6% | 76,5% | 95,3% | 99,7% |
| Welch, α = 0,05 | 1,5% | 7,2% | 16,6% | 34,7% | 56,3% | 67,2% |

O Welch fica abaixo de 5% em δ = 0 (conservador) e não chega perto de 100% na grade. Isso é resultado da lognormal e não da grade: levá-lo a 100% exigiria efeitos em que o Mann-Whitney ficaria no teto por quase toda a curva. Por isso a grade foi calibrada pelo Mann-Whitney. Em C2 a C4 a curva também não chega a 100% (C4 fica em 66% em δ = 2,0), pelo efeito do próprio cenário. O C0 usa uma grade própria, em desvios-padrão: a de C1 ficaria em ~99% ou 100% a partir do quarto ponto.

### Formato do CSV de resultados

Os CSVs de resultados ficam em `dados/simulacao/` (o do piloto é `piloto.csv`; o das simulações finais, `resultados.csv`). Têm **uma linha por (cenário, efeito, α, teste)**, em UTF-8, com cabeçalho, separador vírgula, ponto decimal e as colunas abaixo. Os gráficos G3 e G4 dependem só deste formato.

| Coluna | Tipo | Descrição |
|---|---|---|
| `cenario` | texto | `C0` a `C4` |
| `delta` | número | efeito δ da célula (desvios-padrão em C0, escala log nos demais) |
| `n` | inteiro | tamanho de cada grupo |
| `n_rep` | inteiro | repetições da célula (1.000 no piloto, 10.000 nas finais) |
| `alfa` | número | nível de significância: `0.05` ou `0.01` |
| `teste` | texto | `welch` ou `mann_whitney` (os nomes de `graficos.CORES_TESTE`) |
| `rejeicoes` | inteiro | repetições com p-valor < `alfa` (p-valor NaN não conta como rejeição) |
| `taxa` | número | `rejeicoes / n_rep`, com 6 casas |
| `ic_inf`, `ic_sup` | número | limites do intervalo de Wilson de 95% para `taxa`, com 6 casas |

Em δ = 0 a `taxa` é o erro tipo I; em δ ≠ 0 é o poder. As linhas saem ordenadas por cenário, efeito, α e teste, na ordem do config, e o arquivo não tem coluna de índice.

Exemplo (primeiras linhas do piloto):

```
cenario,delta,n,n_rep,alfa,teste,rejeicoes,taxa,ic_inf,ic_sup
C0,0.0,30,1000,0.05,welch,43,0.043,0.032079,0.057419
C0,0.0,30,1000,0.05,mann_whitney,45,0.045,0.0338,0.059683
C0,0.0,30,1000,0.01,welch,5,0.005,0.002138,0.011651
```

### Motor de simulação

`lab04/simulacao.py` (S02-02) roda a grade:

- `simular(cenario, delta, n_rep, rng)` roda uma célula (cenário × efeito) e devolve uma linha por (α, teste) nas colunas acima. Gera os pares com `gerador.gerar_lote`, aplica `testes.aplicar_testes_vetorizado` e conta p-valores < α; o intervalo é o de Wilson de 95%.
- `rodar_grade(cfg)` percorre todos os cenários e efeitos do config e grava `simulacao.saida` (10.000 repetições por célula). A grade completa leva cerca de 2 s.
- Cada célula tem o seu gerador, `SeedSequence(42, spawn_key=(i, j))`, com `i` a posição do cenário e `j` a do efeito no config. O resultado não depende da ordem em que as células rodam nem de paralelismo.
- O Mann-Whitney usa o p-valor assintótico com mais de 8 observações por grupo (todos os cenários: n = 30 e 10); o método e a contagem de p-valores NaN (variância zero, que não contam como rejeição e geram aviso) ficam em `tabela.attrs`, porque o formato do CSV é fixo.

### Simulações finais

Cada simulação final roda com `python -m lab04.simulacao`, a partir da pasta `lab04/`: `--cenarios` escolhe os cenários (cada um mantém as sementes que tem na grade inteira) e `--saida` o CSV. Junto do CSV sai o registro `registro-<nome>.md`, com o comando, os parâmetros, a versão das bibliotecas e o SHA-256 do `config.yaml` (com fins de linha em LF) usado. Um teste falha se o `config.yaml` mudar depois da simulação, e outro refaz o comando e compara com o CSV versionado. Se uma execução for interrompida, rode o comando de novo: o resultado é o mesmo e o CSV nunca é editado à mão.

| Issue | Cenários | Comando | CSV |
|---|---|---|---|
| S02-03 | C0 e C1 (Q1 e Q2) | `python -m lab04.simulacao --cenarios C0 C1 --saida dados/simulacao/c0_c1.csv` | `dados/simulacao/c0_c1.csv`, 48 linhas |
| S02-04 | C2 e C3 (Q3: assimetria e outliers) | `python -m lab04.simulacao --cenarios C2 C3 --saida dados/simulacao/c2_c3.csv` | `dados/simulacao/c2_c3.csv`, 48 linhas |
| S02-05 | C4 (Q3: amostra pequena) | `python -m lab04.simulacao --cenarios C4 --saida dados/simulacao/c4.csv` | `dados/simulacao/c4.csv`, 24 linhas |

O `config.yaml` usado nas simulações é o congelado na S02-01 (commit `dc4f478`, PR #261); seu hash está no registro. Resultados de C0 e C1 (poder, α = 0,05, 10.000 repetições):

| δ em C0 (dp) | 0 | 0,2 | 0,4 | 0,6 | 0,8 | 1,0 |
|---|---|---|---|---|---|---|
| Welch | 4,6% | 11,5% | 33,2% | 63,0% | 86,6% | 96,6% |
| Mann-Whitney | 4,4% | 10,8% | 31,4% | 60,1% | 84,3% | 95,9% |

| δ em C1 (log) | 0 | 0,4 | 0,8 | 1,2 | 1,6 | 2,0 |
|---|---|---|---|---|---|---|
| Welch | 2,5% | 6,4% | 17,5% | 36,7% | 53,9% | 68,6% |
| Mann-Whitney | 4,7% | 14,0% | 41,7% | 76,9% | 94,9% | 99,4% |

Resultados de C2 e C3 (poder, α = 0,05, 10.000 repetições; δ em escala log):

| δ em C2 | 0 | 0,4 | 0,8 | 1,2 | 1,6 | 2,0 |
|---|---|---|---|---|---|---|
| Welch | 2,0% | 3,8% | 9,1% | 19,2% | 30,9% | 42,9% |
| Mann-Whitney | 4,9% | 11,3% | 31,1% | 60,2% | 84,0% | 95,9% |

| δ em C3 | 0 | 0,4 | 0,8 | 1,2 | 1,6 | 2,0 |
|---|---|---|---|---|---|---|
| Welch | 1,6% | 3,7% | 9,4% | 19,1% | 31,9% | 41,5% |
| Mann-Whitney | 5,0% | 13,2% | 39,1% | 71,4% | 91,7% | 98,9% |

Em C2 e C3 a hipótese nula é verdadeira em δ = 0: no C3 a contaminação (5% das observações × 20) vale nos dois grupos, inclusive em δ = 0, e A e B têm a mesma distribuição (teste de Kolmogorov-Smirnov sobre log(x) e fração contaminada de ~5% em cada grupo). Nenhum valor simulado overflowa: o máximo, em 10.000 repetições por célula, é da ordem de 10⁶ (σ = 2 e fator 20). Nos dois cenários o Welch é conservador em δ = 0 (taxa abaixo de α) e perde poder para o Mann-Whitney; a leitura é da S02-07.

Resultados de C4, n = 10 por grupo (poder, 10.000 repetições; δ em escala log):

| δ em C4 | 0 | 0,4 | 0,8 | 1,2 | 1,6 | 2,0 |
|---|---|---|---|---|---|---|
| Welch, α = 0,05 | 1,5% | 2,5% | 4,7% | 9,1% | 15,2% | 22,1% |
| Mann-Whitney, α = 0,05 | 4,4% | 7,2% | 15,4% | 29,4% | 48,4% | 67,7% |
| Welch, α = 0,01 | 0,0% | 0,2% | 0,4% | 0,8% | 1,7% | 3,0% |
| Mann-Whitney, α = 0,01 | 0,7% | 1,5% | 4,0% | 10,2% | 21,6% | 37,0% |

**Método do Mann-Whitney em C4.** Com n = 10 por grupo o SciPy usa o p-valor **assintótico** (a regra é: assintótico com mais de 8 observações em cada grupo ou com empates, exato nos demais casos), e não o exato. Isso fica registrado no `registro-c4.md` (`Mann-Whitney | C4: asymptotic`) e em `tabela.attrs["mw_metodo"]`. A lognormal é contínua e não houve empate em nenhuma das 60.000 repetições de C4, então o método é o mesmo em todas. O teste é conservador nesse tamanho: pela distribuição exata de U, o tamanho verdadeiro com n = 10 é 4,33% em α = 0,05 (observado: 4,35%) e 0,68% em α = 0,01 (observado: 0,74%). Com o p-valor exato o tamanho em α = 0,01 seria 0,89%. O Welch fica muito abaixo de α (1,5% e 0,04%).

**C5 (variâncias e tamanhos desiguais) não foi feito.** É opcional na Issue e exigiria acrescentar um cenário ao `config.yaml` congelado, o que mudaria o hash citado nos registros de C0 a C4 e obrigaria a refazê-los, além de o gerador não aceitar variâncias nem tamanhos diferentes entre os grupos. Se for feito depois, o aviso sobre H₀ vale: com variâncias diferentes "médias iguais" deixa de ser "distribuições iguais", e a leitura do erro tipo I muda.

**Erro tipo I de C0 (investigação).** A Issue pede investigar uma taxa de C0 fora de 5% ± 0,43 p.p. com n = 30. Em α = 0,05 o Mann-Whitney deu 4,43% (fora da faixa) e o Welch 4,63% (dentro do IC de Wilson, que contém 0,05); em α = 0,01 o Mann-Whitney deu 0,71%. Não é erro de código nem de semente:

- O Mann-Whitney assintótico com n = 30 por grupo e sem empates tem tamanho verdadeiro de 4,79% em α = 0,05 e 0,92% em α = 0,01 (calculado pela distribuição exata de U): é conservador por construção (correção de continuidade e discretização), e 4,79% está dentro da faixa. A taxa observada de 4,43% fica 1,7 erros-padrão abaixo disso, ruído de Monte Carlo.
- Outras seis sementes, com 10.000 repetições cada, deram 4,5% a 4,9% no Mann-Whitney e 4,8% a 5,1% no Welch. A semente 42 caiu no lado baixo dos dois.
- O p-valor do Mann-Whitney do motor é igual ao de `scipy.stats.mannwhitneyu` linha a linha (conferido nesta investigação, com o método assintótico).

Por isso os parâmetros e a semente ficam como estão (nada é alterado depois de ver os resultados); a classificação de cada teste como liberal, conservador ou ok é da S02-07.

### Resultados consolidados e classificação (S02-07)

`python -m lab04.resultados`, a partir da pasta `lab04/`, junta `c0_c1.csv`, `c2_c3.csv` e `c4.csv` (e um `c5.csv` opcional, se existir) e grava, em `dados/simulacao/`:

| Arquivo | Conteúdo |
|---|---|
| `resultados.csv` | Tabela única, 120 linhas, no formato congelado na S02-01 (a concatenação dos três CSVs) |
| `classificacao.csv` | Erro tipo I (δ = 0) por cenário, α e teste, com o desvio em pontos percentuais e a classificação |
| `poder.csv` | Poder dos dois testes por cenário, efeito e α, com a vantagem do Mann-Whitney sobre o Welch em pontos percentuais |
| `resumo-resultados.md` | As tabelas em texto e a resposta a "onde a vantagem muda de lado" |

**Critério.** Com o intervalo de Wilson de 95% da taxa de erro tipo I e a referência α (5% ou 1%): **liberal** se o limite inferior está acima de α, **conservador** se o limite superior está abaixo de α, **ok** se o intervalo contém α. Com 10.000 repetições o intervalo é estreito (cerca de ±0,4 p.p. em 5%), então um desvio pequeno já classifica; por isso a coluna `desvio_pp` mostra o tamanho do desvio. A vantagem de poder só conta se a diferença passar de 1,96 erros-padrão; senão é `empate`. Os dois testes rodam nas mesmas amostras, então esse critério é conservador.

**Erro tipo I** (20 combinações de cenário, α e teste: 12 conservadoras, 8 ok, nenhuma liberal):

| Cenário | Welch (α = 0,05) | Mann-Whitney (α = 0,05) |
|---|---|---|
| C0 (normal) | ok (4,63%) | conservador (4,43%, desvio de −0,57 p.p.) |
| C1 (lognormal calibrada) | conservador (2,47%) | ok (4,67%) |
| C2 (assimetria forte) | conservador (1,98%) | ok (4,86%) |
| C3 (outliers) | conservador (1,61%) | ok (4,96%) |
| C4 (n = 10) | conservador (1,54%) | conservador (4,35%, desvio de −0,65 p.p.) |

Em α = 0,01 a classificação é a mesma. O Welch se afasta muito do nominal assim que os dados deixam de ser normais (2,5 a 3,5 p.p. abaixo de 5%), e o Mann-Whitney fica a menos de 0,7 p.p. em todos os cenários.

**Onde a vantagem de poder muda de lado.** Dentro de um cenário, nenhuma: o mesmo teste lidera em todos os efeitos em que há diferença. Entre cenários, sim: no controle normal (C0) o Welch lidera, por no máximo 3 p.p. (em α = 0,01, 3,9 p.p.); em C1, C2, C3 e C4 o Mann-Whitney lidera, com vantagem máxima entre 41 e 60 p.p. em α = 0,05. As saídas versionadas são conferidas por teste: se um CSV de simulação mudar, rode o comando de novo.

**G3 (S02-08).** `graficos.g3(resultados)` desenha o erro tipo I de cada teste por cenário (barras agrupadas, linha em 5% e intervalo de Wilson de 95% como barra de erro), a partir de `resultados.csv` ou do `piloto.csv`; `alfa=0.01` desenha o nível de 1%. O texto do gráfico está em `graficos.TEXTO_G3`, e um teste confere os números dele contra a classificação. A inserção no dashboard é a S02-11.

**G4 (S02-09).** `graficos.g4(resultados)` desenha as curvas de poder: uma faceta por cenário, as curvas do Welch e do Mann-Whitney no mesmo gráfico (com símbolos e traços diferentes, para as curvas que quase coincidem em C0 continuarem legíveis) e a linha em 5% como referência; em δ = 0 a curva é o erro tipo I do G3. Cada faceta tem o seu eixo x: em C0 o efeito é δ em desvios-padrão e nos demais cenários os rótulos mostram a razão de medianas (δ está na escala log). O texto do gráfico é `graficos.TEXTO_G4`, e um teste confere os números dele contra `poder.csv`.

### GitHub Pages

O dashboard será publicado em <https://gabialvarenga.github.io/lab-experimentacao-software/> (o mesmo endereço do link no topo do dashboard, `LINK_DASHBOARD` em `dashboard.py`). A publicação é a S02-13; antes dela o endereço pode responder 404. O site é habilitado em Settings > Pages do repositório.

## Documentação

| Documento | Descrição |
|---|---|
| [docs/planejamento.md](docs/planejamento.md) | Calendário, decisões, Issues e fluxo das sprints 01 e 02 e da entrega final |
| [docs/protocolo-coleta.md](docs/protocolo-coleta.md) | Fonte, grupos, critérios, procedimento e amostragem dos dados reais |
| [docs/cenario.md](docs/cenario.md) | Pergunta, hipóteses, erros tipo I e II e expectativa antes de simular |
| [docs/dicionario-dados.md](docs/dicionario-dados.md) | Nome, tipo, unidade e origem de cada coluna dos dados reais |
| [docs/calibracao-lognormal.md](docs/calibracao-lognormal.md) | Descritiva, QQ-plot, justificativa da lognormal e parâmetros calibrados |
| [docs/exemplo-simulado.md](docs/exemplo-simulado.md) | Dois conjuntos simulados (sem e com efeito), os dois testes aplicados e a interpretação |
| [dados/reais/registro-coleta.md](dados/reais/registro-coleta.md) | Consultas, contagens por etapa e trocas da coleta (gerado) |

## Estrutura

```
lab04/
    README.md
    config.yaml            # semente, coleta, calibração e, congelados na S02-01, cenários, grade, repetições e alfas
    requirements.txt       # dependências Python
    pytest.ini             # pythonpath e pasta de testes
    lab04/                 # pacote Python; `python -m lab04` é o ponto de entrada
        __main__.py        # orquestra coleta, simulação e dashboard                   (S02-13)
        config.py          # leitura do config.yaml e criação do gerador (semente)     (S01-01)
        coleta.py          # coleta de PRs pela API do GitHub                          (S01-04)
        descritiva.py      # mediana, IQR, assimetria, outliers                        (S01-06)
        calibracao.py      # parâmetros da lognormal a partir dos dados reais          (S01-06)
        gerador.py         # gerar_amostra e gerar_lote                                (S01-07)
        testes.py          # Welch, Mann-Whitney, tamanho de efeito                    (S01-05)
        piloto.py          # piloto de 1.000 repetições e CSV de exemplo                (S02-01)
        simulacao.py       # motor: rejeições, IC de Wilson, SeedSequence              (S02-02)
        resultados.py      # consolida os CSVs e classifica liberal/conservador/ok     (S02-07)
        graficos.py        # g1, g2, g3, g4 em Plotly                                  (S01-09, 10; S02-08, 09)
        dashboard.py       # monta o HTML com as 7 seções                              (S01-11, S02-11)
    tests/                 # pytest, um arquivo test_<módulo>.py por módulo
    dados/
        reais/             # CSV da coleta, calibração e dicionário de dados
        simulacao/         # resultados de Q1, Q2 e Q3 (CSV)
    dashboard/             # HTML gerado por `python -m lab04 dashboard` (fora do Git)
    docs/                  # planejamento, cenário, protocolo de coleta, respostas orais
```

O CI do Lab04 fica em `.github/workflows/lab04-testes.yml`, na raiz do repositório, e roda os testes desta pasta a cada push e pull request.

Regras da estrutura:

| Regra | Motivo |
|---|---|
| A coleta é o único módulo que acessa a API do GitHub | Os demais rodam sem rede e sem token, inclusive no CI |
| O token vem de `GITHUB_TOKEN` e nunca é commitado | `.env` está no `.gitignore` |
| A simulação grava CSVs e o dashboard só lê CSVs | Rodar 10.000 repetições nunca bloqueia a abertura da página |
| Semente única em `config.yaml` | Reprodutibilidade exigida pelo enunciado |
