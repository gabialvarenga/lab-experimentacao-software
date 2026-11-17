# Lab05 — Software estudado: Redis × Valkey

Evidências dos três critérios do enunciado (seção 2a): software **real**, **em operação** e de **alto impacto**, com números e fontes. Todas as fontes foram acessadas em **17/11/2026**, salvo indicação contrária. Documento da Issue S01-02.

> **Pendente:** confirmação do professor de que nenhum outro grupo escolheu o mesmo software (enunciado, seção 10). Ver a seção 1.

## 1. Confirmação do professor

| Item | Registro |
|---|---|
| Pedido enviado em | _(preencher: data e hora)_ |
| Canal | _(mensagem, e-mail ou aula)_ |
| Texto do pedido | _(colar)_ |
| Resposta do professor | _(colar a resposta e a data; link ou captura de tela, se houver)_ |
| Situação | **Pendente** |

Se o professor recusar (outro grupo já escolheu), abrir a Issue do plano B (desempenho de e-commerces com Lighthouse) e replanejar a sprint, como previsto na Issue #276.

## 2. Objeto de pesquisa e versões

O objeto de pesquisa são os **dois servidores em funcionamento**, nas imagens oficiais do Docker Hub, e não os seus repositórios.

| | Redis | Valkey |
|---|---|---|
| Imagem | [`redis`](https://hub.docker.com/_/redis) (imagem oficial do Docker) | [`valkey/valkey`](https://hub.docker.com/r/valkey/valkey) |
| Versão estável mais recente | **8.10.3** | **9.1.3** |
| Tag fixada | `redis:8.10.3` | `valkey/valkey:9.1.3` |
| Publicação da versão (GitHub) | 26/10/2026 ([release](https://github.com/redis/redis/releases/tag/8.10.3)) | 26/10/2026 ([release](https://github.com/valkey-io/valkey/releases/tag/9.1.3)) |
| Última atualização da imagem | 07/11/2026 | 27/10/2026 |
| Digest do índice multi-arquitetura | `sha256:1f88291b4c57bdf249f02eb085a8669889b2d2954e91d4de5118a5da6b78dd53` | `sha256:3add1a336a920ea54770a001ab6feb3da5fceea96a40373a3a2cd469b815f0b7` |
| Digest de `linux/amd64` | `sha256:e2728231060693472a8efb488dd139a8142a01bd0612ae70429bf5b5be924be1` | `sha256:b94f4063db6015ab2fd39a764c241a107aa176c5e7801742af81f4f8f3cb532a` |
| Base da imagem padrão | Debian trixie (a tag `8.10.3` tem o mesmo digest de `8.10.3-trixie`) | Debian trixie (a tag `9.1.3` tem o mesmo digest de `9.1.3-trixie`) |

Fonte dos digests e das datas: API pública do Docker Hub (`hub.docker.com/v2/repositories/library/redis/tags` e `.../valkey/valkey/tags`), em 17/11/2026. A tag `latest` de cada imagem aponta para o mesmo digest da versão fixada.

Decisões sobre as versões:

- **Valkey 9.1.3, e não 9.2.** O planejamento citava "Valkey 9.2", mas a versão 9.2 ainda é *release candidate*: a última é a `9.2.0-rc2` (04/11/2026), marcada como *pre-release* no [GitHub](https://github.com/valkey-io/valkey/releases), e o site [valkey.io](https://valkey.io/) lista a 9.1.3 como a última versão. Usar uma versão candidata invalidaria o critério "em operação".
- **Redis 8.10.3, e não 8.12.** A `8.12-rc3` (12/11/2026) também é *pre-release*. A 8.10.3 é a estável mais recente no [GitHub](https://github.com/redis/redis/releases) e é para onde aponta a tag `latest` do Docker Hub. O menu de [redis.io](https://redis.io/) ainda exibe "Redis 8.8"; vale a versão do GitHub e do Docker Hub.
- **Tags de patch, não flutuantes.** `9.1` e `8.10` mudam a cada correção. O ambiente (S01-06) usa a tag de patch e confere o digest.
- **Mesma base nos dois:** as duas imagens padrão são Debian trixie, o que reduz a diferença de sistema operacional entre os servidores. As variantes `alpine` ficam fora do estudo.

Se uma nova versão estável sair antes da coleta, **não** atualizar no meio do estudo: as versões e os digests daqui são a entrada da Issue S01-06 e do registro de ambiente do executor (S01-07).

## 3. Os três critérios

| Critério | Redis | Valkey | Fonte (acesso em 17/11/2026) |
|---|---|---|---|
| **Real** | Servidor chave-valor em memória, com site, documentação e imagem oficiais, desde 2009 (a imagem no Docker Hub existe desde 05/06/2014) | Servidor chave-valor em memória sob a Linux Foundation, com site, documentação e imagem próprios (imagem registrada em 02/04/2024) | [redis.io](https://redis.io/), [Docker Hub `redis`](https://hub.docker.com/_/redis), [valkey.io](https://valkey.io/), [Docker Hub `valkey/valkey`](https://hub.docker.com/r/valkey/valkey) |
| **Em operação** | Versão estável 8.10.3, publicada em 26/10/2026; correções contínuas em várias linhas (8.2, 8.4, 8.6, 8.8, 8.10) | Versão estável 9.1.3, publicada em 26/10/2026; correções contínuas nas linhas 7.2, 8.0, 8.1, 9.0 e 9.1 | [Releases do Redis](https://github.com/redis/redis/releases), [releases do Valkey](https://github.com/valkey-io/valkey/releases), [valkey.io](https://valkey.io/) |
| **Alto impacto** | Ver a seção 4 | Ver a seção 4 | Ver a seção 4 |

## 4. Números de impacto

| Indicador | Redis | Valkey | Fonte | Limitação |
|---|---|---|---|---|
| *Pulls* da imagem no Docker Hub | **11.700.985.966** (≈ 11,70 bilhões) | **410.577.702** (≈ 410,6 milhões) | API do Docker Hub: [`library/redis`](https://hub.docker.com/v2/repositories/library/redis/) e [`valkey/valkey`](https://hub.docker.com/v2/repositories/valkey/valkey/), 17/11/2026 | Conta *downloads*, não usuários: CI, testes e contêineres auxiliares inflam o número. A imagem do Redis existe desde 2014 e a do Valkey desde abril de 2024 (cerca de 31 meses), então o acumulado não é comparável |
| Posição no DB-Engines, categoria *Key-value stores* | **1º**, pontuação 163,29 | **12º**, pontuação 3,14 (14º em out/2026 e 21º em nov/2025) | [DB-Engines, ranking de key-value](https://db-engines.com/en/ranking/key-value+store), edição de nov/2026 | É um índice de popularidade (buscas, vagas, menções), não de uso em produção. A categoria é *key-value*, não o ranking geral |
| Stack Overflow Developer Survey | **28,3%** dos respondentes usam Redis, 4º entre os bancos de dados (edição 2026, 3.414 respostas) | **2,4%** (edição 2025; o Valkey não aparece na lista da edição 2026) | [Pesquisa 2026](https://survey.stackoverflow.co/2026/technology/) e [pesquisa 2025](https://survey.stackoverflow.co/2025/technology/) | Amostra de quem responde à pesquisa; as duas edições não são comparáveis diretamente. Confirmar na página o grupo de respondentes do 2,4% (todos ou só profissionais) |
| Oferta gerenciada | Redis Cloud e ofertas em AWS, Azure e Google Cloud, listadas no menu "Deploy" de [redis.io](https://redis.io/) | **Amazon ElastiCache for Valkey**, lançado em 08/10/2024 ([AWS](https://aws.amazon.com/about-aws/whats-new/2024/10/amazon-elasticache-valkey/)); **Google Cloud Memorystore for Valkey**, disponibilidade geral em 18/04/2025 ([Google Cloud](https://cloud.google.com/blog/products/databases/announcing-general-availability-of-memorystore-for-valkey/)) | Páginas oficiais dos fornecedores | É a oferta do fornecedor, não o volume de clientes |
| Empresas que migraram | — | **Aiven** migrou cerca de 15 mil serviços Redis para Valkey ([blog da Aiven, 23/09/2025](https://aiven.io/blog/seamlessly-migrating-15k-redis-servers-to-valkey)) | Blog da própria empresa | Fonte primária, mas com interesse comercial |

**A completar antes de fechar a Issue:** outras migrações com fonte primária (por exemplo, distribuições Linux como Fedora e Alpine, que segundo a imprensa adotaram o Valkey no lugar do Redis; ainda não confirmado em fonte primária) e a oferta gerenciada de Redis na AWS e no Google Cloud com link para a página do produto. Número sem fonte primária entra com a fonte secundária e a limitação indicadas.

## 5. A separação de 2024

Em março de 2024 o Redis deixou a licença BSD de 3 cláusulas e passou a usar duas licenças que a *Open Source Initiative* não reconhece como *open source*: a RSALv2 e a SSPLv1. Em 28/03/2024 a Linux Foundation lançou o Valkey, um *fork* do Redis 7.2 sob a licença BSD de 3 cláusulas, com apoio de empresas como AWS, Google Cloud, Oracle, Ericsson e Snap ([Linux Foundation, 28/03/2024](https://www.linuxfoundation.org/press/linux-foundation-launches-open-source-valkey-community)). Em 01/05/2025, com o Redis 8, o Redis passou a oferecer também a licença AGPLv3, que é *open source* ([blog do Redis, 01/05/2025](https://redis.io/blog/agplv3/)). Desde a separação os dois projetos evoluem de forma independente, e empresas e distribuições decidem entre manter o Redis ou migrar para o Valkey. É essa divergência que motiva a pergunta do Lab05: dois servidores com a mesma origem e o mesmo protocolo se comportam de forma equivalente sob a mesma carga, ou o desempenho já diverge?

## 6. Limitações das fontes

- Números de *pulls* mudam todos os dias; vale a data de acesso. Se forem citados no documento final, repetir a consulta.
- Popularidade (DB-Engines) e pesquisa de desenvolvedores medem interesse e uso declarado, não volume de tráfego em produção.
- O estudo não afirma qual servidor é "melhor" no mundo real: o impacto do resultado é discutido nas Issues S03-01 e S03-02.

## 7. Diferenças em relação a `planejamento.md`

Pontos em que a seção 2.1 do [planejamento](planejamento.md) (PR 285) precisa ser atualizada depois do merge deste documento:

| Item | Planejamento (16/11) | Este documento (17/11) |
|---|---|---|
| Versão do Valkey | 9.2 | **9.1.3** (9.2 ainda é *release candidate*) |
| *Pulls* do Valkey | 407,8 milhões | 410,6 milhões |
| *Pulls* do Redis | 11,69 bilhões | 11,70 bilhões |
| Licença do Redis | "licenças não *open source*" | Desde 01/05/2025 o Redis 8 também oferece AGPLv3, que é *open source* |
