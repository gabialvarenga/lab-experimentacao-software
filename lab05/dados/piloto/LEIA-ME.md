# Coleta piloto (S01-08)

Plano reduzido: 5 repetições de cada uma das 12 combinações (2 servidores × 2 níveis de `io_threads` × 3 cargas), 60 execuções em blocos por repetição e em ordem sorteada com a semente 42. Tempos do protocolo (aquecimento 10 s, medição 30 s, pausa 5 s). **Os dados do piloto não entram na análise final.**

```bash
python -m lab05 executar --piloto
python -m lab05 validar --piloto
```

| Arquivo | Conteúdo |
|---|---|
| `piloto.csv` | 60 linhas, formato da S01-07 |
| `registro-piloto.md` | Ambiente e resumo da sessão (gerado pelo executor) |
| `qualidade-piloto.md` | Relatório de qualidade (gerado pelo `validar`) |
| `saidas/*.json` | Saída bruta do `memtier_benchmark` de cada execução |
| `analise/` | Análise do piloto (S01-09; Q3 e análise pareada por bloco na S02-01): `python -m lab05 analisar --piloto`; leitura em [`docs/analise-piloto.md`](../../docs/analise-piloto.md) |

## Condições da coleta (18/11/2026, 20h09 às 21h08)

- Máquina: notebook com Intel Core i7-13620H (16 CPUs lógicas), 23,7 GiB, Windows 11, Docker Desktop 4.67.0 com WSL 2.6.3. **Não é a máquina descrita no protocolo da S01-06** (i5-9300H): a partir do piloto, esta passa a ser a máquina designada (protocolo, seção 2.1).
- Preparação da seção 2.2 conferida antes de começar: na tomada, modo de energia do Windows "Melhor desempenho", suspensão desligada na tomada, só o Claude Code aberto.
- Na primeira tentativa havia quatro contêineres de outro projeto ligados no mesmo Docker. A tentativa foi interrompida na primeira execução e descartada, os contêineres foram parados e o piloto foi rodado do zero. Por isso o protocolo ganhou o item "nenhum outro contêiner no Docker".
- CPUs: dentro da máquina virtual do Docker, os pares de CPUs lógicas irmãs são `0-1`, `2-3`, `4-5` e `6-7`, como na máquina anterior. Servidor (`0-3`) e cliente (`4-7`) não dividem núcleo físico.

## Resultado da validação

- **Sem erros**: 60 de 60 execuções gravadas, nenhuma falha, versões 8.10.3 e 9.1.3, `lat_p99_ms` ≥ `lat_p50_ms` em todas, nenhum erro de conexão do cliente.
- **Tempo total: 59,4 min** (0,99 min por execução). A coleta completa prevista na época, com 30 repetições (360 execuções), levaria cerca de **6 horas**, como previsto no protocolo. A S01-09 fixou 40 repetições (480 execuções, cerca de 8 horas).
- **31 avisos de coeficiente de variação acima de 10%**, em 21 das 36 combinações de `ops_s`, `lat_p50_ms` e `lat_p99_ms`. A `memoria_bytes` é quase constante (CV máximo de 0,04%).

## Investigação dos avisos de CV

A Issue pede investigar a causa antes da coleta completa. Dividindo cada medida pela mediana da sua combinação (para comparar combinações diferentes na mesma escala), a variação aparece **entre blocos, ao longo do tempo**, e não dentro de cada bloco:

| Bloco (repetição) | Horário | `ops_s` relativa (média) | `lat_p99_ms` relativa (média) |
|---|---|---|---|
| 1 | 20h09–20h20 | 0,945 | 1,050 |
| 2 | 20h21–20h32 | 0,842 | 1,228 |
| 3 | 20h33–20h44 | 0,982 | 1,019 |
| 4 | 20h45–20h56 | 1,098 | 0,912 |
| 5 | 20h57–21h07 | 1,072 | 0,940 |

- A correlação entre a ordem da execução e a `ops_s` relativa é 0,55: a máquina ficou cerca de 16% mais lenta no bloco 2 e cerca de 10% mais rápida nos blocos 4 e 5, **em todas as combinações ao mesmo tempo**.
- Retirando o efeito do bloco (cada medida dividida pela mediana relativa do seu bloco), o CV mediano cai de 11,9% para **6,3%** na `ops_s`, de 12,6% para 6,1% na `lat_p50_ms` e de 14,5% para 7,1% na `lat_p99_ms`.
- **Causa provável:** um estado da máquina que mudou durante a coleta, e não um servidor ou uma combinação específica. Candidatos: a máquina virtual do WSL ainda devolvendo memória e CPU depois de parar os contêineres do outro projeto, que eram pesados, logo antes do piloto; tarefas de fundo do Windows; frequência da CPU. O piloto não mediu a frequência nem a carga do Windows, então a causa não pode ser confirmada.
- **Por que o desenho protege a comparação:** como cada bloco tem uma execução de cada combinação, a deriva atinge Redis e Valkey igualmente. Ela não favorece nenhum servidor, mas aumenta a variância e, portanto, o número de repetições necessário (S01-09).

## Ajustes para a coleta completa

1. **Protocolo, seção 2.2:** nenhum outro contêiner ligado (`docker ps` vazio antes de começar), modo de energia do Windows conferido no registro (não só o plano do `powercfg`) e **10 minutos de máquina ociosa** depois de fechar programas ou parar contêineres, antes de começar.
2. **Executor:** o registro de ambiente passou a gravar o modo de energia do Windows 11 e se o notebook está na tomada.
3. **S01-09:** calcular o número de repetições com o CV do piloto **como está (bruto)**, que é o cenário conservador. O ajuste por bloco é só uma explicação da variância e não muda o plano de análise, que está congelado.
