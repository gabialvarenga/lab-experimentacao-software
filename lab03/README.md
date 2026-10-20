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
| [docs/protocolo-rotulagem.md](docs/protocolo-rotulagem.md) | Critérios de rotulagem da amostra-ouro, regras de cegamento e regra de consenso |
| [docs/dicionario-dados.md](docs/dicionario-dados.md) | Dicionário de dados: nome, tipo, unidade e fórmula ou origem de cada coluna dos CSVs |
| [docs/heuristica-corretiva.md](docs/heuristica-corretiva.md) | Versões da heurística de release corretiva, F1 de cada uma e causas dos erros |

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
        cfr.py             # RQ 03, variantes (a) (S01-10) e (b)                         (S02-03)
        corretiva.py       # heurística de release corretiva, versão 3; rework rate     (S02-03, S03-02)
        validacao.py       # precisão, recall e F1 da heurística                         (S02-03)
        recuperacao.py     # RQ 04                                                       (S01-10)
    tests/                 # pytest, um arquivo test_<módulo>.py por módulo
        conftest.py        # carregamento das fixtures                                   (S01-02)
        fixtures/          # respostas da API e listas escritas à mão (JSON)
    dados/
        cache/             # respostas da API, uma por arquivo (não versionado)
        saida/             # funil.csv, repositorios.csv e o dataset final (versionados)
        amostra/           # amostra prevista pela sondagem, fatias da coleta e reservas (Sprint 02)
        coleta/            # registro da coleta de cada fatia, por integrante (Sprint 02)
        rotulagem/         # planilhas da amostra-ouro, kappa, consenso e versões da heurística (Sprint 02)
        snapshots/         # retrato do quadro do GitHub Projects ao fim de cada sprint
    analise/               # um notebook ou script por RQ, reexecutável a partir do CSV (Sprint 03)
        sorteio.py         # sorteio da amostra-ouro e planilhas de rotulagem              (S02-04)
        concordancia.py    # kappa de Fleiss e consenso da amostra-ouro                    (S02-05)
        avaliar_heuristica.py  # precisão, recall e F1 da heurística de release corretiva (S02-13)
        descritiva.py      # mediana, IQR e faixas DORA das RQ 01 a 04                     (S03-04)
        rq07_sensibilidade.py  # sensibilidade da classificação a C1, C2 e C3 (RQ 07)      (S03-08)
        saida/             # tabelas e figuras das análises (versionadas)
    artigo/                # template SBC (Sociedade Brasileira de Computação)
        main.tex
        secoes/            # introducao.tex, hipoteses-rq01-rq04.tex, hipoteses-rq05-rq08.tex, ...
    docs/                  # planejamento, dicionário de dados, protocolo de rotulagem e heurística corretiva
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
| Exceção: `analise/sorteio.py` lê `dados/cache/` e o `config.yaml` por conta própria, sem importar `pipeline/` | O sorteio precisa das listas de releases, que não estão em `dados/saida/`, e roda sem token, que `config.py` exige. Um teste confere que ele lê o cache como `cliente_http.py` grava |

## Execução

Pré-requisitos: Python 3.12 e um token pessoal do GitHub.

**Token.** Crie um token em *GitHub, Settings, Developer settings, Personal access tokens, Tokens (classic)*, **sem marcar nenhum escopo** (os repositórios são públicos). O pipeline lê o token só da variável de ambiente `GITHUB_TOKEN`; ele **não lê arquivo `.env`**. O token nunca é gravado em arquivo nem em log, e a pasta de cache não o contém.

**Instalação.** Use um ambiente virtual. A instalação das dependências leva alguns minutos.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
cd lab03
python -m pip install -r requirements.txt
```

No Linux ou macOS, ative com `source .venv/bin/activate`. **No Windows, mantenha o repositório e o ambiente virtual em um caminho curto** (por exemplo `C:\lab03`): em pastas muito profundas a instalação falha com `WinError 206` (caminho acima de 260 caracteres).

Execução:

```powershell
$env:GITHUB_TOKEN = "<token>"
python -m pipeline --config config.yaml
```

No Linux ou macOS, use `export GITHUB_TOKEN=<token>` no lugar da primeira linha. Sem a variável `GITHUB_TOKEN`, o comando encerra com uma mensagem e não faz nenhuma chamada. O token não é gravado em arquivo nem em log.

O comando examina os candidatos por estrelas decrescentes, uma faixa de `selecao.faixas_estrelas` por vez, e para no repositório aprovado de número `selecao.alvo_aprovados` do `config.yaml` (300).

`coleta.paralelismo` no `config.yaml` define quantos candidatos são avaliados e quantas requisições ficam em andamento ao mesmo tempo. O resultado é contabilizado na ordem de estrelas, então as saídas são as mesmas com qualquer valor; com 1, a execução é sequencial. Acima de 5 não há ganho, porque o limite passa a ser a cota de 5.000 requisições por hora do token. **Memória:** repositórios com milhares de tags ou de runs têm respostas muito grandes, e dois processos com paralelismo 5 ao mesmo tempo chegaram a esgotar a memória (`MemoryError`) numa máquina de 16 GB. Em máquinas menores, ou ao rodar mais de um processo, use `coleta.paralelismo: 2`.

`coleta.variantes_rq07` (`true` ou `false`; padrão `true` quando ausente) liga ou desliga a coleta das variantes C2 (release e pré-release) e C3 (tag) da RQ 07. Com `false`, o pipeline não consulta a API para elas, as dez colunas delas (`n_prereleases`, `n_tags_janela`, `tags_ignoradas_404`, `frequencia_semana_c2`, `lead_time_b_h_c2`, `cfr_b_c2`, `frequencia_semana_c3`, `lead_time_b_h_c3`, `categoria_c2` e `categoria_c3`) ficam vazias, e as demais colunas e o funil não mudam. Serve para refazer a execução só pelo cache, como no congelamento do dataset da Sprint 02; o `config.yaml` do repositório traz `false`, e a coleta de C2 e C3 da Sprint 03 (S03-07) o liga.

| Argumento | Efeito |
|---|---|
| `--config <arquivo>` | Obrigatório. Caminhos relativos de `caminhos` partem da pasta desse arquivo |
| `--limite N` | Para no N-ésimo aprovado, no lugar de `selecao.alvo_aprovados`. `--limite 5` serve de teste rápido |
| `--repos <arquivo>` | Pula a busca e processa só os repositórios do arquivo, um `owner/repo` por linha, na ordem do arquivo |

Com `--repos`, todos os repositórios do arquivo são processados, a menos que `--limite` seja informado. Linhas em branco são ignoradas; uma linha fora do formato `owner/repo` encerra a execução antes de qualquer chamada; um repositório que não existe mais é descartado como "erro da API".

Se a execução for interrompida (rate limit, queda de rede ou `Ctrl+C`), o mesmo comando continua de onde parou, porque as respostas já obtidas estão em `dados/cache/`. Os CSVs são gravados ao final da execução.

Se a rede cair, o pipeline não descarta repositórios: ele espera a conexão voltar, com novas tentativas a cada 60 segundos, por até 6 horas. Passado esse tempo, encerra com erro e sem gravar as saídas; o mesmo comando continua pelo cache. O motivo "erro da API" no funil fica reservado a respostas de erro do GitHub.

A API devolve no máximo 1.000 workflow runs por consulta. A janela é consultada mês a mês; um mês que atinge o teto é refeito dia a dia, e um dia que atinge o teto, hora a hora. Uma hora que ainda atinge o teto fica truncada e gera um aviso no log.

### Coleta dividida entre máquinas

O cache guarda uma resposta da API por arquivo, com o nome derivado da URL e sem o token. Por isso a coleta pode ser dividida: cada pessoa processa uma parte da lista de candidatos com o próprio token e depois os caches são reunidos.

1. Cada pessoa roda `python -m pipeline --config config.yaml --repos <sua-fatia.txt>`.
2. Cada pessoa compacta a pasta `dados/cache/` e a envia para quem vai gerar as saídas.
3. Quem gera as saídas copia todos os arquivos recebidos para a própria `dados/cache/` (arquivos de mesmo nome são a mesma resposta; qualquer um serve) e roda `python -m pipeline --config config.yaml`, que lê o cache e só chama a API para o que faltar.

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

O `repositorios.csv` tem uma linha por repositório aprovado. Decimais usam ponto e precisão completa; métrica indefinida fica vazia. Nome, tipo, unidade e fórmula de cada coluna deste e dos demais arquivos de dados estão no [dicionário de dados](docs/dicionario-dados.md).

## Teste rápido de replicação

Para conferir a instalação sem gastar a cota do token, rode um único repositório pequeno, com cache vazio:

```powershell
Set-Content -Path um_repo.txt -Value "typicode/json-server" -Encoding ascii
python -m pipeline --config config.yaml --repos um_repo.txt
```

No Linux ou macOS, crie o arquivo com `echo typicode/json-server > um_repo.txt`. Leva cerca de 20 segundos e grava `dados/saida/funil_subamostra.csv` e `dados/saida/repositorios_subamostra.csv` (o `--repos` não sobrescreve as tabelas da amostra). A linha desse repositório deve coincidir com a de `dados/saida/repositorios.csv` em todas as colunas, **exceto `estrelas`** (e, às vezes, `linguagem`), que variam com o dia da coleta. Diferenças em outras colunas indicam que a execução não reproduziu o estudo.

## Reproduzir as análises

Cada script de `analise/` lê só os arquivos de `dados/saida/` (e de `dados/rotulagem/`), sem nova coleta, e grava em `analise/saida/`:

```powershell
python -m analise.descritiva
python -m analise.rq07_sensibilidade
```

| Comando | O que faz | Observações |
|---|---|---|
| `python -m analise.descritiva` | Mediana, IQR e faixas DORA das RQ 01 a 04, com histogramas | Cerca de 10 segundos. As figuras `.png` são regeneradas e o Git as mostra como alteradas, porque o arquivo não sai idêntico byte a byte; as tabelas `.csv` saem iguais |
| `python -m analise.rq07_sensibilidade` | Compara C1, C2 e C3 (% de mudança e kappa ponderado) | Precisa das colunas de C2 e C3 preenchidas em `repositorios.csv`. Com elas vazias, encerra com uma mensagem que aponta a coleta (`coleta.variantes_rq07: true`) |
| `python -m analise.avaliar_heuristica --versao N` | Precisão, recall e F1 da heurística corretiva contra o consenso | Usa o token e a rede (as notas de cada release e os `compare`, cerca de 300 releases) e regrava a linha da versão em `versoes_heuristica.csv` |
| `python -m analise.concordancia` | Kappa de Fleiss e consenso da amostra-ouro | **Veja o aviso abaixo** |

> **Aviso sobre `analise.concordancia`.** O comando regrava `kappa.csv`, `divergencias.csv` e `consenso.csv` só com a regra da maioria. As quatro decisões da reunião de consenso (`jestjs/jest` em `tipo_projeto`, `supabase/supabase` em `entregas_reais`, `babel/babel v7.29.3` e `spring-projects/spring-boot v4.0.3` em `corretiva`) e suas justificativas ficam **só** no `consenso.csv` versionado e na ata (`dados/rotulagem/ata_consenso.md`); regravar o arquivo as perde. O `kappa.csv` sai igual nos dois casos, porque o kappa é calculado antes do consenso. Para reproduzir os kappas sem tocar no consenso, rode o comando numa cópia da pasta (`--pasta`).

## Amostra-ouro

```powershell
cd lab03
python -m analise.sorteio --fila dados/amostra/amostra_prevista.csv
```

O comando sorteia 60 repositórios e 5 reservas da fila congelada e 5 deploys da janela de cada um, com a semente 42 fixa em `analise/sorteio.py`. Ele não usa o token nem a rede: as listas de releases são lidas de `dados/cache/`, então só roda na máquina que tem o cache da coleta, e encerra com uma mensagem se faltar a lista de algum sorteado.

| Argumento | Efeito |
|---|---|
| `--fila <arquivo>` | Obrigatório. CSV com a coluna `full_name`; só as 300 primeiras linhas entram no sorteio |
| `--config <arquivo>` | Config do pipeline, de onde saem a janela e a pasta do cache. Padrão: `config.yaml` |
| `--aprovados <arquivo>` | CSV com a coluna `full_name` (ex.: `dados/saida/repositorios.csv`). Sorteado ausente dele é trocado pela primeira reserva livre, sem novo sorteio |
| `--saida <pasta>` | Pasta das saídas. Padrão: `dados/rotulagem` |
| `--sobrescrever` | Grava mesmo se as saídas já existirem. Sem ele, o comando se recusa, porque regravar uma planilha apaga os rótulos preenchidos |

Saídas em `dados/rotulagem/`:

| Arquivo | Conteúdo |
|---|---|
| `amostra_ouro.csv` | Uma linha por release sorteada dos 65 repositórios (325 linhas): `ordem_sorteio`, `papel`, `full_name`, `tag_name`, `published_at`, `url_release` e `url_compare` |
| `avaliador_1.xlsx` a `avaliador_3.xlsx` | Os 60 repositórios da amostra (aba `repositorios`) e suas 300 releases (aba `releases`), com as colunas e os valores aceitos do [protocolo de rotulagem](docs/protocolo-rotulagem.md) |

`papel` é `amostra` ou `reserva`. Com `--aprovados`, o sorteado que saiu da amostra fica como `substituído`, e a reserva que também saiu, como `descartado`; os dois ficam com uma única linha, sem release, e suas releases não são lidas do cache. `url_compare` compara a release com o deploy anterior e fica vazia na primeira release da história do repositório.

## Testes

```powershell
cd lab03
pytest --cov=metricas --cov-report=term-missing
```

Não precisam de token nem de rede. A suíte tem mais de 570 testes e leva de 1 a 3 minutos; a cobertura exigida do pacote `metricas` é de 80% (o CI reprova abaixo disso).

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
