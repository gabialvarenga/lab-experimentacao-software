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

O piloto roda a grade inteira com 1.000 repetições por célula e semente 42 (`python -m lab04.piloto`, cerca de 15 s) e grava `dados/simulacao/piloto.csv`. A grade foi calibrada nele, com o critério da Issue: a curva de poder de C1 vai de ~5% até perto de 100%.

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
