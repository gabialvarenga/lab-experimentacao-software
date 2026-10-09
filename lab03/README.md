# Lab03 — Mineração de métricas DORA

Pipeline reprodutível que seleciona repositórios open-source populares que usam GitHub Actions, coleta releases, commits e workflow runs pela API (*Application Programming Interface*) REST do GitHub e calcula as métricas DORA (*DevOps Research and Assessment*): frequência de deploy, lead time, CFR (*Change Failure Rate*, taxa de falha de mudanças) e tempo de recuperação.

## Integrantes

- Brenda Evers (1523565)
- Carlos José Gomes Batista Figueiredo (1507022)
- Gabriela Alvarenga Cardoso (1026227)

## GitHub Projects (Kanban)

Board do grupo: [Kanban](https://github.com/users/gabialvarenga/projects/9)

## Documentação

| Documento | Descrição |
|---|---|
| [docs/planejamento.md](docs/planejamento.md) | Calendário, decisões, Issues e fluxo das sprints 01 a 03 |

## Estrutura

```
lab03/
    README.md
    config.yaml            # janela, critérios de inclusão, faixas de busca e caminhos (sem token)
    requirements.txt       # dependências Python
    pytest.ini             # pythonpath e pasta de testes
    pipeline/              # coleta e orquestração; único pacote que acessa a API
        __main__.py        # ponto de entrada: python -m pipeline --config config.yaml   (S01-11)
        config.py          # leitura do config.yaml e do GITHUB_TOKEN                     (S01-11)
        cliente_http.py    # requisições, cache, retomada, rate limit, backoff          (S01-04)
        selecao.py         # busca fatiada, workflows, metadados                         (S01-05)
        runs.py            # workflow runs com subdivisão mensal                         (S01-07)
        funil.py           # critério de inclusão e tabela do funil                      (S01-08)
        releases.py        # releases, tags e commits entre releases                     (S01-09)
    metricas/              # funções puras de cálculo; cobertura mínima de 80%
        janela.py          # semanas da janela e pertinência de datas                    (S01-02)
        lead_time.py       # RQ 02, variantes (a) e (b)                                  (S01-06)
        classificacao.py   # Elite, High, Medium, Low                                    (S01-06)
        conclusao.py       # sucesso, falha ou ignorado por `conclusion`                 (S01-07)
        frequencia.py      # RQ 01                                                       (S01-08)
        cfr.py             # RQ 03 (a); a variante (b) entra na Sprint 02                (S01-10)
        recuperacao.py     # RQ 04                                                       (S01-10)
    tests/                 # pytest, um arquivo test_<módulo>.py por módulo
        conftest.py        # carregamento das fixtures                                   (S01-02)
        fixtures/          # respostas da API e listas escritas à mão (JSON)
    dados/
        cache/             # respostas da API, uma por arquivo (não versionado)
        saida/             # funil.csv, repositorios.csv e o dataset final (versionados)
        rotulagem/         # planilhas da amostra-ouro e consenso (Sprint 02)
    analise/               # um notebook ou script por RQ, reexecutável a partir do CSV (Sprint 03)
    artigo/                # template SBC (Sociedade Brasileira de Computação)
        main.tex
        secoes/            # introducao.tex, hipoteses-rq01-rq04.tex, hipoteses-rq05-rq08.tex, ...
    docs/                  # planejamento e, na Sprint 02, dicionário de dados e protocolo de consenso
```

O CI do Lab03 fica em `.github/workflows/lab03-testes.yml`, na raiz do repositório, e roda os testes desta pasta a cada push.

Regras da estrutura:

| Regra | Motivo |
|---|---|
| `metricas/` não importa `pipeline/` nem `requests`; recebe listas de dicionários com datas em `datetime` UTC e devolve números | Cada função é testada com fixtures, sem rede, e a cobertura de 80% vale só para este pacote (seção 7 do enunciado) |
| `pipeline/` pode importar `metricas/`; a dependência nunca ocorre no sentido inverso | Evita ciclos de importação e mantém o cálculo independente da coleta |
| Somente `cliente_http.py` faz requisições HTTP (*Hypertext Transfer Protocol*); os demais módulos de `pipeline/` recebem `owner` e `repo` e chamam suas funções | Cache, rate limit e *backoff* ficam em um único ponto |
| A conversão das datas da API para `datetime` UTC ocorre na coleta | `metricas/` recebe dados já normalizados |
| `config.py` é o único ponto de leitura do `config.yaml` e do token; os demais módulos recebem os valores como parâmetros | Os módulos são testáveis sem arquivo de configuração nem variável de ambiente |
| `dados/cache/`, o token e os arquivos de compilação do LaTeX ficam fora do Git (`.gitignore`) | O token nunca é commitado (seção 7) e o repositório guarda só o que o grupo replicador usa |
| Análises da Sprint 03 leem apenas `dados/saida/` | Cada análise é reexecutável a partir do CSV, sem nova coleta (seção 10) |

## Execução

Pré-requisitos: Python 3.12 e um token pessoal do GitHub.

```powershell
cd lab03
python -m pip install -r requirements.txt
$env:GITHUB_TOKEN = "<token>"
python -m pipeline --config config.yaml
```

No Linux ou macOS, use `export GITHUB_TOKEN=<token>` no lugar da terceira linha. Sem a variável `GITHUB_TOKEN`, o comando encerra com uma mensagem e não faz nenhuma chamada. O token não é gravado em arquivo nem em log.

O comando examina os candidatos por estrelas decrescentes, uma faixa de `selecao.faixas_estrelas` por vez, e para no 100º repositório aprovado no funil (`selecao.alvo_aprovados` do `config.yaml`).

| Argumento | Efeito |
|---|---|
| `--config <arquivo>` | Obrigatório. Caminhos relativos de `caminhos` partem da pasta desse arquivo |
| `--limite N` | Para no N-ésimo aprovado, no lugar de `selecao.alvo_aprovados`. `--limite 5` serve de teste rápido |
| `--repos <arquivo>` | Pula a busca e processa só os repositórios do arquivo, um `owner/repo` por linha, na ordem do arquivo |

Com `--repos`, todos os repositórios do arquivo são processados, a menos que `--limite` seja informado. Linhas em branco são ignoradas; uma linha fora do formato `owner/repo` encerra a execução antes de qualquer chamada; um repositório que não existe mais é descartado como "erro da API".

Se a execução for interrompida (rate limit, queda de rede ou `Ctrl+C`), o mesmo comando continua de onde parou, porque as respostas já obtidas estão em `dados/cache/`. Os CSVs são gravados ao final da execução.

Saídas em `dados/saida/`:

| Arquivo | Conteúdo |
|---|---|
| `funil.csv` | Repositórios restantes e motivo de descarte em cada etapa da seleção |
| `repositorios.csv` | Metadados e métricas por repositório aprovado |
| `funil_subamostra.csv`, `repositorios_subamostra.csv` | As mesmas tabelas quando o comando roda com `--repos`, para não sobrescrever as da amostra |

Etapas do `funil.csv` (colunas `etapa`, `entrada`, `saida`, `motivo`):

| Etapa | Motivo de descarte |
|---|---|
| Candidatos examinados | Não examinado: a execução parou no último aprovado. A entrada são os candidatos das faixas de estrelas já buscadas |
| Com GitHub Actions | Sem Actions |
| Coleta sem erro | Erro da API em qualquer etapa da coleta; a etapa e o repositório ficam no log |
| Releases na janela | Menos de 5 releases |
| Runs válidos na janela | Menos de 50 runs |

Colunas do `repositorios.csv`, uma linha por repositório aprovado. Decimais usam ponto e precisão completa; métrica indefinida fica vazia.

| Coluna | Conteúdo |
|---|---|
| `full_name` | `owner/repo` |
| `estrelas`, `linguagem`, `contribuidores` | Metadados do repositório; `linguagem` e `contribuidores` ficam vazios quando a API não informa |
| `idade_dias` | Dias entre a criação e o fim da janela |
| `n_deploys`, `n_runs_validos` | Contagens usadas no critério de inclusão |
| `frequencia_semana` | RQ 01: deploys por semana |
| `lead_time_a_h`, `lead_time_b_h` | RQ 02: mediana por release (a) e por commit (b), em horas |
| `releases_ignoradas_404` | Releases fora do lead time porque o `compare` com a anterior devolveu 404 |
| `cfr_a` | RQ 03 (a): fração de runs com falha, de 0 a 1 |
| `recuperacao_mediana_h` | RQ 04: mediana dos episódios completos, em horas |
| `n_episodios`, `n_censurados_direita`, `n_censurados_esquerda` | Episódios de falha e quantos são censurados |
| `categoria_c1` | Classificação DORA com `frequencia_semana`, `lead_time_a_h`, `cfr_a` e `recuperacao_mediana_h` |
| `n_metricas_classificadas` | Métricas definidas que entraram na classificação (até 4) |

## Testes

```powershell
cd lab03
pytest --cov=metricas --cov-report=term-missing
```

## Definições adotadas

| Item | Definição |
|---|---|
| Janela de observação | 01/10/2025 a 30/09/2026, intervalo fechado, datas em UTC |
| Branch | Apenas o *default branch* |
| Deploy | Release com `draft = false` e `prerelease = false` |
| Data de um commit | `commit.author.date` |
| Workflow runs | Apenas `event = push` no *default branch* |
| Sucesso e falha | `success` = sucesso; `failure`, `timed_out`, `startup_failure` = falha; demais valores ignorados |
| Critério de inclusão | ≥ 5 releases e ≥ 50 workflow runs válidos na janela |
| Censura | Episódios sem fim dentro da janela são contados como censurados, não descartados |
