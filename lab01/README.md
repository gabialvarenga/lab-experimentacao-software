# Laboratório de Experimentação de Software — Lab01

[![CI](https://github.com/gabialvarenga/lab-experimentacao-software/actions/workflows/ci.yml/badge.svg)](https://github.com/gabialvarenga/lab-experimentacao-software/actions/workflows/ci.yml)

Repositório do grupo para o Lab01 da disciplina de Laboratório de Experimentação
de Software (PUC Minas), sob orientação do Prof. Danilo Maia.

## Integrantes

- Brenda Evers (1523565)
- Carlos José Gomes Batista Figueiredo (1507022)
- Gabriela Alvarenga Cardoso (1026227)

## Objetivo

Caracterizar os 1.000 repositórios open-source mais populares do GitHub
(por número de estrelas), respondendo às 7 questões de pesquisa do enunciado
sobre maturidade, contribuição externa, frequência de releases, atualizações,
linguagens e percentual de issues fechadas — mais uma RQ08 bônus (efeito de
rede via forks) e 3 métricas extras (licença, CI/CD, número de linguagens).

## GitHub Projects (Kanban)

Board do grupo: [Kanban](https://github.com/users/gabialvarenga/projects/9)

## Relatório

- [Hipóteses informais](relatorio/hipoteses-informais.md) — validação de
  dados (distribuição, outliers, valores ausentes) e hipótese informal por
  RQ, gerado a partir de `data/data-quality-report.md`.
- [Primeira versão do relatório (PDF)](relatorio/Primeira_versao_Relatorio_Laboratorio.pdf)

## Como rodar

Requer um arquivo `.env` (copie de `.env.example`) com `GITHUB_TOKEN`, um
Personal Access Token do GitHub.

```bash
npm install
```

**Coleta dos repositórios** (gera `data/repositories.csv`):

```bash
npm run collect
```

**Snapshot do board**, ao final de cada sprint (gera
`data/snapshots/lab01-<sprint>.csv`, ex: `lab01-s01.csv`):

```bash
npm run snapshot -- <identificador-da-sprint>
# exemplo:
npm run snapshot -- s01
```

O token precisa do escopo `read:project` para o snapshot (além do acesso
padrão a repositórios públicos usado pela coleta) — edite o token em
[github.com/settings/tokens](https://github.com/settings/tokens) e marque
essa permissão caso o script retorne erro de escopo insuficiente.

**Relatório de qualidade de dados** (gera `data/data-quality-report.md` a
partir de `data/repositories.csv`: distribuição, outliers e valores ausentes
por RQ):

```bash
npm run data-quality
```

**Testes e verificação de tipos:**

```bash
npm test
npm run build
```