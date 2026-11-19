# Relatório de qualidade — piloto.csv

Gerado por `python -m lab05 validar` (regras em `lab05/validacao.py`).

## Resultado

- **Sem erros**; 31 aviso(s).
- Execuções no plano: 60; gravadas: 60; tentativas com falha em `falhas.csv`: 0.
- Tempo total (primeiro início ao último fim): 59,4 min; duração média de uma execução: 0,89 min.

## Erros

Nenhum.

## Avisos

- CV de `ops_s` em redis, io_threads 1, carga get: 11,8% (acima de 10%)
- CV de `lat_p50_ms` em redis, io_threads 1, carga get: 12,2% (acima de 10%)
- CV de `lat_p99_ms` em redis, io_threads 1, carga get: 14,7% (acima de 10%)
- CV de `ops_s` em redis, io_threads 1, carga misto: 13,8% (acima de 10%)
- CV de `lat_p50_ms` em redis, io_threads 1, carga misto: 14,6% (acima de 10%)
- CV de `lat_p99_ms` em redis, io_threads 1, carga misto: 16,3% (acima de 10%)
- CV de `lat_p99_ms` em redis, io_threads 1, carga set: 10,6% (acima de 10%)
- CV de `ops_s` em redis, io_threads 4, carga get: 12,0% (acima de 10%)
- CV de `lat_p50_ms` em redis, io_threads 4, carga get: 11,0% (acima de 10%)
- CV de `lat_p99_ms` em redis, io_threads 4, carga get: 14,1% (acima de 10%)
- CV de `ops_s` em redis, io_threads 4, carga set: 12,1% (acima de 10%)
- CV de `lat_p50_ms` em redis, io_threads 4, carga set: 12,2% (acima de 10%)
- CV de `lat_p99_ms` em redis, io_threads 4, carga set: 15,3% (acima de 10%)
- CV de `ops_s` em valkey, io_threads 1, carga get: 11,7% (acima de 10%)
- CV de `lat_p50_ms` em valkey, io_threads 1, carga get: 12,5% (acima de 10%)
- CV de `lat_p99_ms` em valkey, io_threads 1, carga get: 14,4% (acima de 10%)
- CV de `ops_s` em valkey, io_threads 1, carga misto: 15,8% (acima de 10%)
- CV de `lat_p50_ms` em valkey, io_threads 1, carga misto: 14,9% (acima de 10%)
- CV de `lat_p99_ms` em valkey, io_threads 1, carga misto: 18,5% (acima de 10%)
- CV de `ops_s` em valkey, io_threads 1, carga set: 11,9% (acima de 10%)
- CV de `lat_p50_ms` em valkey, io_threads 1, carga set: 12,7% (acima de 10%)
- CV de `lat_p99_ms` em valkey, io_threads 1, carga set: 17,1% (acima de 10%)
- CV de `ops_s` em valkey, io_threads 4, carga get: 15,5% (acima de 10%)
- CV de `lat_p50_ms` em valkey, io_threads 4, carga get: 14,3% (acima de 10%)
- CV de `lat_p99_ms` em valkey, io_threads 4, carga get: 14,1% (acima de 10%)
- CV de `ops_s` em valkey, io_threads 4, carga misto: 13,1% (acima de 10%)
- CV de `lat_p50_ms` em valkey, io_threads 4, carga misto: 14,3% (acima de 10%)
- CV de `lat_p99_ms` em valkey, io_threads 4, carga misto: 11,1% (acima de 10%)
- CV de `ops_s` em valkey, io_threads 4, carga set: 11,4% (acima de 10%)
- CV de `lat_p50_ms` em valkey, io_threads 4, carga set: 13,1% (acima de 10%)
- CV de `lat_p99_ms` em valkey, io_threads 4, carga set: 15,2% (acima de 10%)

## Variabilidade por combinação

Mediana, IQR e coeficiente de variação (CV). CV acima de 10% marcado com ⚠.

| servidor | io_threads | carga | métrica | n | mediana | IQR | CV |
|---|---|---|---|---|---|---|---|
| redis | 1 | get | `ops_s` | 5 | 80.214 | 10.135 | 11,8% ⚠ |
| redis | 1 | get | `lat_p50_ms` | 5 | 0,591 | 0,072 | 12,2% ⚠ |
| redis | 1 | get | `lat_p99_ms` | 5 | 1,087 | 0,160 | 14,7% ⚠ |
| redis | 1 | get | `memoria_bytes` | 5 | 17.426.272 | 1.056 | 0,0% |
| redis | 1 | misto | `ops_s` | 5 | 74.647 | 14.607 | 13,8% ⚠ |
| redis | 1 | misto | `lat_p50_ms` | 5 | 0,631 | 0,136 | 14,6% ⚠ |
| redis | 1 | misto | `lat_p99_ms` | 5 | 1,151 | 0,312 | 16,3% ⚠ |
| redis | 1 | misto | `memoria_bytes` | 5 | 17.425.072 | 560 | 0,0% |
| redis | 1 | set | `ops_s` | 5 | 75.378 | 8.461 | 9,6% |
| redis | 1 | set | `lat_p50_ms` | 5 | 0,631 | 0,064 | 9,8% |
| redis | 1 | set | `lat_p99_ms` | 5 | 1,151 | 0,120 | 10,6% ⚠ |
| redis | 1 | set | `memoria_bytes` | 5 | 17.400.608 | 1.408 | 0,0% |
| redis | 4 | get | `ops_s` | 5 | 110.784 | 19.564 | 12,0% ⚠ |
| redis | 4 | get | `lat_p50_ms` | 5 | 0,399 | 0,064 | 11,0% ⚠ |
| redis | 4 | get | `lat_p99_ms` | 5 | 1,023 | 0,168 | 14,1% ⚠ |
| redis | 4 | get | `memoria_bytes` | 5 | 17.982.800 | 2.896 | 0,0% |
| redis | 4 | misto | `ops_s` | 5 | 107.324 | 11.602 | 8,6% |
| redis | 4 | misto | `lat_p50_ms` | 5 | 0,415 | 0,048 | 9,2% |
| redis | 4 | misto | `lat_p99_ms` | 5 | 1,047 | 0,016 | 7,6% |
| redis | 4 | misto | `memoria_bytes` | 5 | 17.984.592 | 1.680 | 0,0% |
| redis | 4 | set | `ops_s` | 5 | 121.687 | 20.011 | 12,1% ⚠ |
| redis | 4 | set | `lat_p50_ms` | 5 | 0,367 | 0,072 | 12,2% ⚠ |
| redis | 4 | set | `lat_p99_ms` | 5 | 0,919 | 0,176 | 15,3% ⚠ |
| redis | 4 | set | `memoria_bytes` | 5 | 17.959.040 | 2.800 | 0,0% |
| valkey | 1 | get | `ops_s` | 5 | 82.557 | 8.310 | 11,7% ⚠ |
| valkey | 1 | get | `lat_p50_ms` | 5 | 0,575 | 0,056 | 12,5% ⚠ |
| valkey | 1 | get | `lat_p99_ms` | 5 | 1,055 | 0,104 | 14,4% ⚠ |
| valkey | 1 | get | `memoria_bytes` | 5 | 15.180.384 | 2.816 | 0,0% |
| valkey | 1 | misto | `ops_s` | 5 | 67.172 | 10.728 | 15,8% ⚠ |
| valkey | 1 | misto | `lat_p50_ms` | 5 | 0,695 | 0,104 | 14,9% ⚠ |
| valkey | 1 | misto | `lat_p99_ms` | 5 | 1,311 | 0,304 | 18,5% ⚠ |
| valkey | 1 | misto | `memoria_bytes` | 5 | 15.180.640 | 3.264 | 0,0% |
| valkey | 1 | set | `ops_s` | 5 | 77.595 | 2.809 | 11,9% ⚠ |
| valkey | 1 | set | `lat_p50_ms` | 5 | 0,607 | 0,032 | 12,7% ⚠ |
| valkey | 1 | set | `lat_p99_ms` | 5 | 1,111 | 0,048 | 17,1% ⚠ |
| valkey | 1 | set | `memoria_bytes` | 5 | 15.155.888 | 4.224 | 0,0% |
| valkey | 4 | get | `ops_s` | 5 | 159.349 | 45.056 | 15,5% ⚠ |
| valkey | 4 | get | `lat_p50_ms` | 5 | 0,271 | 0,064 | 14,3% ⚠ |
| valkey | 4 | get | `lat_p99_ms` | 5 | 0,703 | 0,152 | 14,1% ⚠ |
| valkey | 4 | get | `memoria_bytes` | 5 | 15.735.616 | 1.728 | 0,0% |
| valkey | 4 | misto | `ops_s` | 5 | 172.150 | 42.797 | 13,1% ⚠ |
| valkey | 4 | misto | `lat_p50_ms` | 5 | 0,255 | 0,072 | 14,3% ⚠ |
| valkey | 4 | misto | `lat_p99_ms` | 5 | 0,647 | 0,112 | 11,1% ⚠ |
| valkey | 4 | misto | `memoria_bytes` | 5 | 15.734.592 | 1.536 | 0,0% |
| valkey | 4 | set | `ops_s` | 5 | 192.780 | 21.655 | 11,4% ⚠ |
| valkey | 4 | set | `lat_p50_ms` | 5 | 0,231 | 0,024 | 13,1% ⚠ |
| valkey | 4 | set | `lat_p99_ms` | 5 | 0,575 | 0,112 | 15,2% ⚠ |
| valkey | 4 | set | `memoria_bytes` | 5 | 15.708.432 | 1.600 | 0,0% |
