# Relatório de qualidade — execucoes.csv

Gerado por `python -m lab05 validar` (regras em `lab05/validacao.py`).

## Resultado

- **Sem erros**; 0 aviso(s).
- Execuções no plano: 12; gravadas: 12; tentativas com falha em `falhas.csv`: 0.
- Tempo total (primeiro início ao último fim): 5,5 min; duração média de uma execução: 0,42 min.

## Erros

Nenhum.

## Avisos

Nenhum.

## Variabilidade por combinação

Mediana, IQR e coeficiente de variação (CV). CV acima de 10% marcado com ⚠.

| servidor | io_threads | carga | métrica | n | mediana | IQR | CV |
|---|---|---|---|---|---|---|---|
| redis | 1 | get | `ops_s` | 1 | 67.888 | 0 | — |
| redis | 1 | get | `lat_p50_ms` | 1 | 0,679 | 0,000 | — |
| redis | 1 | get | `lat_p99_ms` | 1 | 1,543 | 0,000 | — |
| redis | 1 | get | `memoria_bytes` | 1 | 17.423.856 | 0 | — |
| redis | 1 | misto | `ops_s` | 1 | 66.013 | 0 | — |
| redis | 1 | misto | `lat_p50_ms` | 1 | 0,695 | 0,000 | — |
| redis | 1 | misto | `lat_p99_ms` | 1 | 1,471 | 0,000 | — |
| redis | 1 | misto | `memoria_bytes` | 1 | 17.426.096 | 0 | — |
| redis | 1 | set | `ops_s` | 1 | 68.107 | 0 | — |
| redis | 1 | set | `lat_p50_ms` | 1 | 0,679 | 0,000 | — |
| redis | 1 | set | `lat_p99_ms` | 1 | 1,415 | 0,000 | — |
| redis | 1 | set | `memoria_bytes` | 1 | 17.401.072 | 0 | — |
| redis | 4 | get | `ops_s` | 1 | 176.729 | 0 | — |
| redis | 4 | get | `lat_p50_ms` | 1 | 0,247 | 0,000 | — |
| redis | 4 | get | `lat_p99_ms` | 1 | 0,727 | 0,000 | — |
| redis | 4 | get | `memoria_bytes` | 1 | 17.983.568 | 0 | — |
| redis | 4 | misto | `ops_s` | 1 | 181.056 | 0 | — |
| redis | 4 | misto | `lat_p50_ms` | 1 | 0,239 | 0,000 | — |
| redis | 4 | misto | `lat_p99_ms` | 1 | 0,703 | 0,000 | — |
| redis | 4 | misto | `memoria_bytes` | 1 | 17.982.832 | 0 | — |
| redis | 4 | set | `ops_s` | 1 | 174.506 | 0 | — |
| redis | 4 | set | `lat_p50_ms` | 1 | 0,247 | 0,000 | — |
| redis | 4 | set | `lat_p99_ms` | 1 | 0,751 | 0,000 | — |
| redis | 4 | set | `memoria_bytes` | 1 | 17.958.752 | 0 | — |
| valkey | 1 | get | `ops_s` | 1 | 66.340 | 0 | — |
| valkey | 1 | get | `lat_p50_ms` | 1 | 0,703 | 0,000 | — |
| valkey | 1 | get | `lat_p99_ms` | 1 | 1,543 | 0,000 | — |
| valkey | 1 | get | `memoria_bytes` | 1 | 15.181.408 | 0 | — |
| valkey | 1 | misto | `ops_s` | 1 | 72.827 | 0 | — |
| valkey | 1 | misto | `lat_p50_ms` | 1 | 0,647 | 0,000 | — |
| valkey | 1 | misto | `lat_p99_ms` | 1 | 1,175 | 0,000 | — |
| valkey | 1 | misto | `memoria_bytes` | 1 | 15.177.952 | 0 | — |
| valkey | 1 | set | `ops_s` | 1 | 69.282 | 0 | — |
| valkey | 1 | set | `lat_p50_ms` | 1 | 0,663 | 0,000 | — |
| valkey | 1 | set | `lat_p99_ms` | 1 | 1,335 | 0,000 | — |
| valkey | 1 | set | `memoria_bytes` | 1 | 15.155.440 | 0 | — |
| valkey | 4 | get | `ops_s` | 1 | 284.703 | 0 | — |
| valkey | 4 | get | `lat_p50_ms` | 1 | 0,159 | 0,000 | — |
| valkey | 4 | get | `lat_p99_ms` | 1 | 0,327 | 0,000 | — |
| valkey | 4 | get | `memoria_bytes` | 1 | 15.737.472 | 0 | — |
| valkey | 4 | misto | `ops_s` | 1 | 271.745 | 0 | — |
| valkey | 4 | misto | `lat_p50_ms` | 1 | 0,167 | 0,000 | — |
| valkey | 4 | misto | `lat_p99_ms` | 1 | 0,407 | 0,000 | — |
| valkey | 4 | misto | `memoria_bytes` | 1 | 15.733.440 | 0 | — |
| valkey | 4 | set | `ops_s` | 1 | 280.053 | 0 | — |
| valkey | 4 | set | `lat_p50_ms` | 1 | 0,167 | 0,000 | — |
| valkey | 4 | set | `lat_p99_ms` | 1 | 0,367 | 0,000 | — |
| valkey | 4 | set | `memoria_bytes` | 1 | 15.706.640 | 0 | — |
