# Lab05 — Benchmark controlado de dois servidores em memória

Experimento controlado que compara dois servidores em memória rodando nas mesmas condições (mesma máquina, mesma configuração, mesmo cliente de carga), medindo vazão (ops/s), latência (p50 e p99) e memória. O software estudado ainda será confirmado com o professor (Issue S01-02). O código reaproveita testes de hipótese e o motor de simulação do Lab04, copiados para este laboratório.

> **Estado:** esqueleto da S01-01. A estrutura, as dependências e o CI existem; o executor, a validação e a análise entram nas próximas Issues.

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

O comando único do laboratório (do plano de execuções ao dashboard) será descrito aqui quando o executor (S01-07) e a análise (S01-09) existirem. Por enquanto os subcomandos `executar`, `validar` e `analisar` só avisam que a etapa ainda não foi implementada.

A semente global fica em `config.yaml` (`semente: 42`) e alimenta a ordem aleatorizada das execuções e as reamostragens.

## Estrutura

```
lab05/
    README.md
    config.yaml            # semente global (o plano de execuções entra na S01-07)
    requirements.txt       # dependências Python
    pytest.ini             # pythonpath e pasta de testes
    lab05/                 # pacote Python; `python -m lab05` é o ponto de entrada
        __main__.py        # subcomandos executar, validar e analisar
        config.py          # leitura do config.yaml e criação do gerador (semente)
        ambiente.py        # registro do ambiente (versões, digests, CPU, SO, Docker)   (S01-07)
        executor.py        # plano de execuções, contêineres e cliente de carga         (S01-07)
        validacao.py       # conferência dos dados coletados                            (S01-08)
        descritiva.py      # mediana, IQR e coeficiente de variação (origem: Lab04)     (S01-09)
        testes.py          # Welch, Mann-Whitney e tamanho de efeito (origem: Lab04)
        poder.py           # poder por simulação (origem: motor do Lab04)
        graficos.py        # gráficos em Plotly
        app.py             # dashboard interativo em Streamlit
    tests/                 # pytest, um arquivo test_<módulo>.py por módulo
    dados/
        brutos/            # CSV do executor, uma linha por execução                   (S01-07)
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
