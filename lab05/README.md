# Lab05 — Benchmark controlado de dois servidores em memória

Experimento controlado que compara dois servidores em memória rodando nas mesmas condições (mesma máquina, mesma configuração, mesmo cliente de carga), medindo vazão (ops/s), latência (p50 e p99) e memória. O software estudado ainda será confirmado com o professor (Issue S01-02). O código reaproveita testes de hipótese e o motor de simulação do Lab04, copiados para este laboratório.

> **Estado:** o ambiente (S01-06) e o executor (S01-07) existem; a validação e a análise entram nas próximas Issues.

## Integrantes

- Brenda Evers (1523565)
- Carlos José Gomes Batista Figueiredo (1507022)
- Gabriela Alvarenga Cardoso (1026227)

## GitHub Projects (Kanban)

Board do grupo: [Kanban](https://github.com/users/gabialvarenga/projects/9)

## Como executar

Requer Python 3.12. A partir da raiz do repositório:

```bash
python -m pip install -r lab05/requirements.txt
cd lab05
python -m lab05 --help
pytest
```

O caminho completo é `executar` → `validar` → `analisar`, cada um com as mesmas opções de coleta (`--piloto`, `--saida`, `--nome`). O dashboard (`app`, S02-09) só lê os CSVs gravados.

A semente global fica em `config.yaml` (`semente: 42`) e alimenta a ordem aleatorizada das execuções e as reamostragens.

### Executar o benchmark

Requer o Docker (Docker Desktop com WSL2 no Windows) e a preparação da máquina do [protocolo](docs/protocolo-execucao.md), seção 2.2. A partir de `lab05/`:

```bash
python -m lab05 executar
```

Roda o plano inteiro do `config.yaml` (2 servidores × 2 níveis de `io_threads` × 3 cargas × 40 repetições = 480 execuções, cerca de 8 horas; o número de repetições foi fixado pelo piloto, ver [docs/analise-piloto.md](docs/analise-piloto.md)), em blocos por repetição e em ordem sorteada com a semente. Grava em `dados/brutos/`:

| Arquivo | Conteúdo |
|---|---|
| `execucoes.csv` | Uma linha por execução concluída: `execucao_id`, `ordem`, `servidor`, `versao`, `io_threads`, `carga`, `repeticao`, `ops_s`, `lat_p50_ms`, `lat_p99_ms`, `memoria_bytes`, `inicio`, `fim` |
| `falhas.csv` | Uma linha por tentativa que falhou (etapa e mensagem), sem valor inventado |
| `saidas/<execucao_id>.json` | Saída bruta do `memtier_benchmark` |
| `registro-<data>.md` | Ambiente (versões e digests das imagens, CPU, memória, SO, Docker, WSL, plano de energia) e resumo de cada sessão |

Se a coleta for interrompida (Ctrl+C, queda, suspensão), rodar o mesmo comando retoma de onde parou: o que está no CSV não roda de novo, e as execuções que falharam são tentadas outra vez. O executor recusa retomar se o config mudou (outra semente ou outro plano); nesse caso, use outra pasta de saída.

As opções trocam valores do config só naquela chamada, sem editar o arquivo. O exemplo versionado em `dados/brutos/exemplo/` (12 execuções, 1 repetição, medição de 5 s) foi gerado com:

```bash
python -m lab05 executar --repeticoes 1 --aquecimento 2 --medicao 5 --pausa 1 --saida dados/brutos/exemplo
```

### Coleta piloto e validação

O piloto (S01-08) usa o bloco `piloto` do `config.yaml` (5 repetições, 60 execuções, cerca de 1 hora) e grava `dados/piloto/piloto.csv` e `dados/piloto/registro-piloto.md`. **Não entra na análise final.**

```bash
python -m lab05 executar --piloto
python -m lab05 validar --piloto
```

O `validar` aceita as mesmas opções do `executar` (para descrever a mesma coleta) e grava `qualidade-<nome>.md` ao lado do CSV. Sai com código 1 se houver erro.

| Tipo | Regra |
|---|---|
| Erro | Colunas diferentes das congeladas, valor faltante ou não numérico, métrica ≤ 0, `lat_p99_ms` < `lat_p50_ms`, `fim` antes de `inicio` |
| Erro | Execução repetida, fora do plano ou diferente dele; execução do plano que falta no CSV (com a falha de `falhas.csv` ou como falha não registrada) |
| Erro | Versão do servidor diferente de `versao_esperada`; saída do cliente ausente ou com erros de conexão |
| Aviso | Coeficiente de variação acima de 10% numa combinação; falha que depois foi repetida com sucesso |

O relatório traz também o tempo total da coleta e, por combinação e métrica, n, mediana, IQR e CV.

### Análise

A análise (S01-09; Q3 e análise pareada na S02-01) segue o [plano de análise](docs/plano-analise.md) e roda sem Docker, sobre o CSV de uma coleta. Os parâmetros ficam no bloco `analise` do `config.yaml`, com as decisões fixadas no piloto: o teste principal de cada métrica (`teste_principal`) e o método da Q3 (`metodo_q3`).

```bash
python -m lab05 analisar --piloto
```

Grava em `<pasta da coleta>/analise/`:

| Arquivo | Conteúdo |
|---|---|
| `descritiva.csv` | Por combinação e métrica: n, média, desvio, quartis, IQR, CV e *outliers* contados (não removidos) |
| `teste-principal.csv` | Regra 5.1: Shapiro-Wilk e assimetria dos resíduos, o que a regra daria e o teste usado (`teste_usado`; `origem`: `config` ou `regra`) |
| `comparacoes.csv` | Valkey × Redis em cada uma das 6 combinações: Welch, Mann-Whitney, Holm no teste principal, g de Hedges, delta de Cliff, razão de medianas com IC por *bootstrap*, Levene e a situação da seção 6 |
| `repeticoes.csv` | Repetições necessárias para 5% com 80% de poder, por métrica, na variabilidade bruta e nas sensibilidades |
| `curva-poder.csv` e `diferenca-detectavel.csv` | Poder de cada comparação na grade de n e a menor diferença detectável nos n candidatos (`analise`: `independente` ou `pareada`) |
| `q3.csv` | Q3, por métrica (`ops_s`, `lat_p99_ms`) e carga: interação servidor × `io_threads` pela ART-ANOVA, razão das razões com IC por *bootstrap*, η² parcial, Holm entre as cargas e a ANOVA no log com o bloco como sensibilidade |
| `q3-curva-poder.csv` e `q3-diferenca-detectavel.csv` | Poder da interação da Q3 em cada carga e a menor razão das razões (R − 1) detectável com 80% de poder, com o σ de log da coleta (S02-07) |
| `pareada.csv` | Análise pareada por bloco (sensibilidade): Valkey ÷ Redis dentro de cada repetição, Wilcoxon pareado, Hodges-Lehmann com IC exato, Holm e a situação comparada à do teste principal; pares com execução refeita saem |
| `registro-analise.md` | Comando, parâmetros, hash do CSV de entrada, ambiente e as tabelas principais (determinístico) |

A saída da coleta completa está versionada em `dados/brutos/analise/`, e a interpretação das Q1 a Q4 (tabelas com Holm, situação de cada comparação, a interação da Q3, diferença detectável e expectativa × resultado) está em [docs/resultados.md](docs/resultados.md). As ameaças à validade (conclusão, interna, construto e externa, com mitigação e risco restante) estão em [docs/ameacas-validade.md](docs/ameacas-validade.md).

O poder é estimado por simulação com o motor do Lab04 adaptado: amostras lognormais com o σ de log de cada combinação observado na coleta e Holm aplicado à família de 6 comparações em cada repetição simulada. A opção `--simulacoes` troca o número de simulações por ponto, para uma rodada rápida.

### Gráficos

Os gráficos (S02-05) leem o CSV da coleta e o `comparacoes.csv` do `analisar`, então o `analisar` precisa rodar antes. Eles são feitos em Plotly, em `lab05/graficos.py`, e o dashboard (S02-09) usa as mesmas funções.

```bash
python -m lab05 graficos            # coleta completa
python -m lab05 graficos --piloto
```

Grava em `<pasta da coleta>/analise/figuras/`:

| Arquivo | Conteúdo |
|---|---|
| `g1.html` | G1: distribuição de cada métrica por combinação (Redis e Valkey lado a lado, um painel por métrica) |
| `g2.html` | G2: deriva ao longo da coleta (valor ÷ mediana da combinação, por bloco, com a faixa de ±5%) |
| `g3.html` | G3: razão de medianas Valkey ÷ Redis com IC de 95% por *bootstrap* e faixa de [0,95; 1,05] |
| `g4.html` | G4: interação servidor × `io_threads` (Q3), medianas com 1 e 4 threads por carga, em escala log |
| `apresentacao.html` | Página única para apresentar: números de destaque, as quatro figuras e o texto "como ler" de cada uma. Embute o Plotly.js e abre sem internet |

### Dashboard

O dashboard interativo (S02-09), em Streamlit, reúne o método e os resultados numa página só. A partir de `lab05/`:

```bash
python -m lab05 app                    # sobe o servidor e abre o navegador (http://localhost:8501)
python -m lab05 app --sem-abrir --porta 8600
python -m streamlit run lab05/app.py   # equivalente, sem o subcomando
```

Ctrl+C no terminal encerra o servidor. O app **só lê CSVs**: abrir a página nunca roda o *benchmark*, e não precisa do Docker. Ele lê `dados/brutos/execucoes.csv` e as tabelas de `dados/brutos/analise/` (`comparacoes.csv`, `q3.csv` e `q3-diferenca-detectavel.csv`), então `executar` e `analisar` precisam ter rodado antes. Se um arquivo falta, a seção que depende dele mostra um aviso com o comando que o gera, e as outras seguem funcionando.

| Seção | Conteúdo |
|---|---|
| 1. O software e a pergunta | Redis 8.10.3 × Valkey 9.1.3, a pergunta principal e as perguntas Q1 a Q4 |
| 2. Como medimos | Ambiente, cliente de carga, cargas e desenho das execuções (blocos em ordem sorteada) |
| 3. Dados e deriva | Números de destaque da coleta, G1 (cada métrica por combinação, com escolha das métricas) e G2 (deriva) |
| 4. Resultados das Q1, Q2 e Q4 | G3 (razão Valkey ÷ Redis com IC) e tabela de cada pergunta, com seletor da pergunta |
| 5. A diferença depende das threads? (Q3) | G4, tabela da interação (R, IC, Holm) e a interação detectável |

Impacto, conclusões e a publicação do dashboard ficam para a Sprint 03. O texto de cada seção que cita números os lê das tabelas, então acompanha a análise se ela for refeita. As figuras são as mesmas de `python -m lab05 graficos`. O comando desliga as estatísticas de uso do Streamlit (`--browser.gatherUsageStats false`).

## Estrutura

```
lab05/
    README.md
    config.yaml            # semente global, plano de execuções e parâmetros do cliente de carga
    compose.yaml           # servidores e cliente de carga em contêineres                (S01-06)
    requirements.txt       # dependências Python
    pytest.ini             # pythonpath e pasta de testes
    lab05/                 # pacote Python; `python -m lab05` é o ponto de entrada
        __main__.py        # subcomandos executar, validar e analisar
        analise.py         # análise de uma coleta: tabelas, CSVs e registro             (S01-09)
        config.py          # leitura do config.yaml e criação do gerador (semente)
        ambiente.py        # registro do ambiente (versões, digests, CPU, SO, Docker)   (S01-07)
        executor.py        # plano de execuções, contêineres e cliente de carga         (S01-07)
        leitura.py         # parser da saída do cliente e do INFO do servidor (sem Docker) (S01-07)
        validacao.py       # conferência dos dados coletados e relatório de qualidade  (S01-08)
        descritiva.py      # mediana, IQR e coeficiente de variação (origem: Lab04)     (S01-09)
        testes.py          # Welch, Mann-Whitney, efeito, Holm, bootstrap (origem: Lab04) (S01-09)
        poder.py           # poder e repetições por simulação (origem: motor do Lab04)    (S01-09)
        q3.py              # Q3: interação servidor × io_threads, ART-ANOVA e ANOVA     (S02-01)
        pareada.py         # análise pareada por bloco: Wilcoxon e Hodges-Lehmann       (S02-01)
        graficos.py        # gráficos G1 a G4 e página de apresentação (Plotly)          (S02-05)
        app.py             # dashboard interativo em Streamlit (`python -m lab05 app`)    (S02-09)
    tests/                 # pytest, um arquivo test_<módulo>.py por módulo
        dados/             # saídas reais gravadas (JSON do cliente, INFO dos servidores) para o parser
    dados/
        brutos/            # CSV do executor, uma linha por execução                   (S01-07)
            exemplo/       # execução de exemplo, pequena (12 execuções), versionada
        piloto/            # coleta piloto (S01-08): piloto.csv, registro e relatório de qualidade
    docs/                  # protocolo, plano de análise e demais documentos
```

O CI do Lab05 fica em `.github/workflows/lab05-testes.yml`, na raiz do repositório, e roda os testes desta pasta a cada push e pull request.

Regras da estrutura:

| Regra | Motivo |
|---|---|
| O executor é o único módulo que usa Docker | Os demais rodam sem Docker, inclusive no CI, com as saídas gravadas do cliente de carga |
| O CI não depende de Docker nem de segredos | Qualquer push e pull request roda os testes |
| O código do Lab04 é copiado, com a origem no docstring, e nunca importado de `lab04/` | Cada laboratório roda sozinho |
| Semente única em `config.yaml` | Reprodutibilidade exigida pelo enunciado |
