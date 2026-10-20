# Heurística de release corretiva: versões e resultado (S03-02)

A heurística de `metricas/corretiva.py` decide se uma release é corretiva (RQ 03, CFR b; RQ 08, rework rate). Ela foi avaliada contra a dimensão `corretiva` do `dados/rotulagem/consenso.csv` (300 releases, 73 corretivas), com `python -m analise.avaliar_heuristica`. Cada versão tem uma linha em `dados/rotulagem/versoes_heuristica.csv`.

## Resultado

| Versão | Regra | VP | FP | FN | Precisão | Recall | F1 |
|---|---|---|---|---|---|---|---|
| 1 | (A) só o patch muda, ou (B) `fix`, `revert`, `hotfix` ou `bugfix` em algum commit | 71 | 198 | 2 | 0,264 | 0,973 | 0,415 |
| 2 | lê as release notes: sem anúncio de funcionalidade e com sinal de correção (ou só patch) | 53 | 49 | 20 | 0,520 | 0,726 | 0,606 |
| 3 | notas lidas por seção, commits triviais, maioria de commits de correção | 48 | 28 | 25 | 0,632 | 0,658 | **0,644** |

**A meta de F1 ≥ 0,70 não foi atingida.** A Issue permitia no máximo duas versões além da primeira, então a v3 é a final e está em `corretiva.py`. As regras de cada versão estão no cabeçalho do módulo e na coluna `regra` do CSV.

## Causas dos 53 erros da v3

| Erro | Casos | Causa | Exemplos |
|---|---|---|---|
| FN, notas com sinal de funcionalidade | 16 | A release é corretiva para as pessoas porque as correções predominam, mas as notas trazem um título ou item de funcionalidade (`Added`, `Features`, `Security: Added ...`). A regra é binária e não mede o predomínio. | gogs 0.13.4, 0.14.2 e 0.14.3; serverless 4.21.1 e sf-core 4.29.3; tldraw 5.3.2 |
| FN, notas sem sinal | 8 | As notas são só links de download (LLVM) ou apontam para um arquivo externo (bitcoin). Os commits de backport raramente têm `fix` no assunto. | LLVM 21.1.3 a 22.1.2; bitcoin 29.3 |
| FN, sem notas | 1 | O único commit corrige um defeito sem usar uma palavra-chave. | llama.cpp b7078 |
| FP, notas com sinal de correção | 21 | Uma linha com `fix` ou `security` basta, mesmo em releases grandes que também trazem melhorias sem título de seção, ou em boletins mensais de produto. | Pake 3.11.0; supabase 1.26.01 e 1.26.08; prettier 3.9.7; headroom 0.21.32 |
| FP, notas sem sinal | 5 | Só o patch decide, e a release de patch traz mudanças que não são correção. | babel 8.0.1; opencode 1.0.34; VoiceStudio 0.2.6 |
| FP, sem notas descritivas | 2 | As notas são só um link para o changelog e os commits de manutenção passam no teste de patch ou de maioria. | prettier 3.9.5; faiss 1.15.1 |

## Para as ameaças à validade

- **Regras escolhidas depois de ler a amostra.** As palavras-chave e as seções da v2 e da v3 foram definidas olhando exemplos e erros dos mesmos 300 itens usados na avaliação. Não houve conjunto separado de validação, então o F1 de 0,644 tende a ser otimista para repositórios novos.
- **A referência também erra.** O consenso vem de três pessoas lendo notas e commits, com kappa de Fleiss de 0,78 em `corretiva`. Os 55 itens 2-1 mostram que o critério tem zona cinzenta, o que limita o F1 máximo possível.
- **Notas multilíngues e formatos variados.** As regras são em inglês. Notas em chinês, como as do MinerU e do MoneyPrinterTurbo, só entram por palavras em inglês ou pelos commits.
- **A heurística usa só o texto.** Ela não vê o tamanho da mudança no código nem o que as pessoas leem nas páginas da release (anexos, links).
- **Efeito no CFR (b).** Com precisão de 0,63 e recall de 0,66, o `cfr_b` e o `rework_rate` por repositório têm erro nos dois sentidos. Vale reportar a RQ 03 (b) junto do CFR (a) e discutir a diferença.

## Pipeline e cache

A v3 precisa do texto das release notes. O pipeline passou a guardar o campo `body` da lista de releases (`CAMPOS_RELEASE`) e `releases_com_commits` devolve `notas` em cada item. Respostas de releases gravadas por versões antigas do pipeline podem não ter esse campo; nelas `notas` fica `None` e a regra cai no caminho dos commits (sem notas).

No cache usado para congelar o dataset (S03-03), todos os 22.113 deploys da janela dos 300 repositórios têm as notas, então o `cfr_b` e o `rework_rate` do CSV usam a v3 completa. Quem repetir a coleta do zero grava o campo `body` desde o início; quem reutilizar um cache de uma versão antiga do pipeline deve conferir se as releases têm `notas` e, se faltar, apagar do cache só as páginas de `/releases` para baixá-las de novo.
