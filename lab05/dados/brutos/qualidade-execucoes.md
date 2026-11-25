# Relatório de qualidade — execucoes.csv

Gerado por `python -m lab05 validar` (regras em `lab05/validacao.py`).

## Resultado

- **Sem erros**; 0 aviso(s).
- Execuções no plano: 480; gravadas: 480; tentativas com falha em `falhas.csv`: 0.
- Tempo total (primeiro início ao último fim): 446,8 min; duração média de uma execução: 0,84 min.

## Erros

Nenhum.

## Avisos

Nenhum.

## Variabilidade por combinação

Mediana, IQR e coeficiente de variação (CV). CV acima de 10% marcado com ⚠.

| servidor | io_threads | carga | métrica | n | mediana | IQR | CV |
|---|---|---|---|---|---|---|---|
| redis | 1 | get | `ops_s` | 40 | 89.097 | 774 | 1,0% |
| redis | 1 | get | `lat_p50_ms` | 40 | 0,535 | 0,000 | 1,0% |
| redis | 1 | get | `lat_p99_ms` | 40 | 0,959 | 0,016 | 1,2% |
| redis | 1 | get | `memoria_bytes` | 40 | 17.425.344 | 2.624 | 0,0% |
| redis | 1 | misto | `ops_s` | 40 | 88.262 | 874 | 0,9% |
| redis | 1 | misto | `lat_p50_ms` | 40 | 0,535 | 0,008 | 1,1% |
| redis | 1 | misto | `lat_p99_ms` | 40 | 0,967 | 0,016 | 1,3% |
| redis | 1 | misto | `memoria_bytes` | 40 | 17.424.896 | 1.856 | 0,0% |
| redis | 1 | set | `ops_s` | 40 | 87.991 | 984 | 1,5% |
| redis | 1 | set | `lat_p50_ms` | 40 | 0,543 | 0,008 | 1,8% |
| redis | 1 | set | `lat_p99_ms` | 40 | 0,967 | 0,008 | 2,1% |
| redis | 1 | set | `memoria_bytes` | 40 | 17.399.992 | 2.872 | 0,0% |
| redis | 4 | get | `ops_s` | 40 | 146.436 | 704 | 0,6% |
| redis | 4 | get | `lat_p50_ms` | 40 | 0,303 | 0,000 | 0,6% |
| redis | 4 | get | `lat_p99_ms` | 40 | 0,767 | 0,008 | 0,9% |
| redis | 4 | get | `memoria_bytes` | 40 | 17.984.144 | 2.464 | 0,0% |
| redis | 4 | misto | `ops_s` | 40 | 144.217 | 965 | 0,9% |
| redis | 4 | misto | `lat_p50_ms` | 40 | 0,311 | 0,000 | 1,1% |
| redis | 4 | misto | `lat_p99_ms` | 40 | 0,775 | 0,008 | 1,4% |
| redis | 4 | misto | `memoria_bytes` | 40 | 17.984.080 | 2.456 | 0,0% |
| redis | 4 | set | `ops_s` | 40 | 142.394 | 1.036 | 0,9% |
| redis | 4 | set | `lat_p50_ms` | 40 | 0,311 | 0,000 | 1,0% |
| redis | 4 | set | `lat_p99_ms` | 40 | 0,783 | 0,008 | 1,5% |
| redis | 4 | set | `memoria_bytes` | 40 | 17.959.632 | 2.584 | 0,0% |
| valkey | 1 | get | `ops_s` | 40 | 88.315 | 1.082 | 0,9% |
| valkey | 1 | get | `lat_p50_ms` | 40 | 0,535 | 0,008 | 0,9% |
| valkey | 1 | get | `lat_p99_ms` | 40 | 0,967 | 0,016 | 1,2% |
| valkey | 1 | get | `memoria_bytes` | 40 | 15.180.832 | 2.928 | 0,0% |
| valkey | 1 | misto | `ops_s` | 40 | 87.642 | 938 | 0,8% |
| valkey | 1 | misto | `lat_p50_ms` | 40 | 0,543 | 0,000 | 0,9% |
| valkey | 1 | misto | `lat_p99_ms` | 40 | 0,975 | 0,008 | 0,9% |
| valkey | 1 | misto | `memoria_bytes` | 40 | 15.180.416 | 2.720 | 0,0% |
| valkey | 1 | set | `ops_s` | 40 | 86.739 | 1.310 | 2,0% |
| valkey | 1 | set | `lat_p50_ms` | 40 | 0,551 | 0,008 | 2,1% |
| valkey | 1 | set | `lat_p99_ms` | 40 | 0,983 | 0,010 | 1,7% |
| valkey | 1 | set | `memoria_bytes` | 40 | 15.155.856 | 2.816 | 0,0% |
| valkey | 4 | get | `ops_s` | 40 | 236.548 | 2.782 | 1,1% |
| valkey | 4 | get | `lat_p50_ms` | 40 | 0,183 | 0,008 | 2,0% |
| valkey | 4 | get | `lat_p99_ms` | 40 | 0,471 | 0,008 | 1,5% |
| valkey | 4 | get | `memoria_bytes` | 40 | 15.736.000 | 3.008 | 0,0% |
| valkey | 4 | misto | `ops_s` | 40 | 234.851 | 2.092 | 0,9% |
| valkey | 4 | misto | `lat_p50_ms` | 40 | 0,183 | 0,008 | 2,1% |
| valkey | 4 | misto | `lat_p99_ms` | 40 | 0,479 | 0,008 | 1,5% |
| valkey | 4 | misto | `memoria_bytes` | 40 | 15.734.976 | 2.432 | 0,0% |
| valkey | 4 | set | `ops_s` | 40 | 232.367 | 2.822 | 0,8% |
| valkey | 4 | set | `lat_p50_ms` | 40 | 0,191 | 0,008 | 2,0% |
| valkey | 4 | set | `lat_p99_ms` | 40 | 0,479 | 0,008 | 1,4% |
| valkey | 4 | set | `memoria_bytes` | 40 | 15.709.680 | 1.888 | 0,0% |
