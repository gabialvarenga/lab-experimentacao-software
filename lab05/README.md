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

O comando único do laboratório (do plano de execuções ao dashboard) será descrito aqui quando a análise (S01-09) existir. Por enquanto `validar` e `analisar` só avisam que a etapa ainda não foi implementada.

A semente global fica em `config.yaml` (`semente: 42`) e alimenta a ordem aleatorizada das execuções e as reamostragens.

### Executar o benchmark

Requer o Docker (Docker Desktop com WSL2 no Windows) e a preparação da máquina do [protocolo](docs/protocolo-execucao.md), seção 2.2. A partir de `lab05/`:

```bash
python -m lab05 executar
```

Roda o plano inteiro do `config.yaml` (2 servidores × 2 níveis de `io_threads` × 3 cargas × 30 repetições = 360 execuções, cerca de 6 horas), em blocos por repetição e em ordem sorteada com a semente. Grava em `dados/brutos/`:

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
        config.py          # leitura do config.yaml e criação do gerador (semente)
        ambiente.py        # registro do ambiente (versões, digests, CPU, SO, Docker)   (S01-07)
        executor.py        # plano de execuções, contêineres e cliente de carga         (S01-07)
        leitura.py         # parser da saída do cliente e do INFO do servidor (sem Docker) (S01-07)
        validacao.py       # conferência dos dados coletados                            (S01-08)
        descritiva.py      # mediana, IQR e coeficiente de variação (origem: Lab04)     (S01-09)
        testes.py          # Welch, Mann-Whitney e tamanho de efeito (origem: Lab04)
        poder.py           # poder por simulação (origem: motor do Lab04)
        graficos.py        # gráficos em Plotly
        app.py             # dashboard interativo em Streamlit
    tests/                 # pytest, um arquivo test_<módulo>.py por módulo
        dados/             # saídas reais gravadas (JSON do cliente, INFO dos servidores) para o parser
    dados/
        brutos/            # CSV do executor, uma linha por execução                   (S01-07)
            exemplo/       # execução de exemplo, pequena (12 execuções), versionada
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
