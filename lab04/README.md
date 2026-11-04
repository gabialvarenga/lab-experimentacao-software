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

`python -m lab04` é o comando único: lê o CSV da coleta, roda as simulações e gera o dashboard em `dashboard/`. Todas as simulações usam a semente fixa de `config.yaml` (`numpy.random.default_rng(42)`), então os resultados se reproduzem.

**Estado atual (Sprint 01):** o comando único é um esqueleto. Cada etapa avisa que ainda não foi implementada e sai com código 1; elas entram nas Issues indicadas em `python -m lab04 --help` e na estrutura abaixo. A coleta pela API (`python -m lab04 coletar`) precisa de `GITHUB_TOKEN` e fica fora do comando único.

Testes:

```bash
cd lab04
python -m pytest --cov=lab04 --cov-report=term-missing --cov-fail-under=80
```

## Documentação

| Documento | Descrição |
|---|---|
| [docs/planejamento.md](docs/planejamento.md) | Calendário, decisões, Issues e fluxo das sprints 01 e 02 e da entrega final |

## Estrutura

```
lab04/
    README.md
    config.yaml            # semente e, a partir da S02-01, cenários, grade de efeitos, repetições e alfas
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
        simulacao.py       # motor: rejeições, IC de Wilson, SeedSequence              (S02-02)
        graficos.py        # g1, g2, g3, g4 em Plotly                                  (S01-09, 10; S02-08, 09)
        dashboard.py       # monta o HTML com as 7 seções                              (S01-11, S02-11)
    tests/                 # pytest, um arquivo test_<módulo>.py por módulo
    dados/
        reais/             # CSV da coleta, calibração e dicionário de dados
        simulacao/         # resultados de Q1, Q2 e Q3 (CSV)
    dashboard/             # HTML gerado
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
