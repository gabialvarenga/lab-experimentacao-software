# Execução de exemplo do executor (S01-07)

Saída de uma chamada curta do executor, para mostrar o formato do CSV e do registro e servir de origem das saídas reais usadas nos testes do parser (`tests/dados/`):

```bash
python -m lab05 executar --repeticoes 1 --aquecimento 2 --medicao 5 --pausa 1 --saida dados/brutos/exemplo
```

**Não são dados do experimento.** Foram gerados em 18/11/2026 numa máquina que não é a designada no protocolo (outro processador, com 16 CPUs lógicas), sem a preparação da seção 2.2 (plano de energia "Equilibrado") e com medição de 5 s em vez de 30 s. Não devem entrar na análise nem no piloto (S01-08).

O SHA-256 do `compose.yaml` no registro é anterior a uma mudança só de comentário (a linha da variável `SAIDAS` no cabeçalho), feita depois desta execução.

| Arquivo | Conteúdo |
|---|---|
| `execucoes.csv` | 12 execuções (1 de cada combinação), na ordem sorteada com a semente 42 |
| `saidas/*.json` | Saída bruta do `memtier_benchmark` de cada execução |
| `registro-2026-11-18.md` | Ambiente e resumo da sessão |
