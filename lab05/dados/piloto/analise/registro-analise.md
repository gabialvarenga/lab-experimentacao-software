# Registro da análise — piloto.csv

Gerado por `lab05/analise.py`; não edite à mão. Para refazer, rode o comando abaixo.

| Item | Valor |
|---|---|
| Comando (a partir de `lab05/`) | `python -m lab05 analisar --piloto` |
| SHA-256 de `piloto.csv` (fins de linha LF) | `c1d6461403a0ae6be7d70ffc6c9371e75ff390dff01d0d54dde1c52b1478d7e1` |
| Execuções | 60 |
| Semente | 42 |
| Diferença relevante | 5% (razão de medianas fora de [0,95; 1,05]) |
| α | 0,05, bicaudal, Holm dentro de cada métrica |
| *Bootstrap* | 10000 reamostragens |
| Poder | 80%, 2000 simulações por ponto, cenário de Holm `conservador` |
| Ambiente | Python 3.14.3, numpy 2.5.2, scipy 1.18.1, pandas 3.0.5 |

## Teste principal por métrica (regra 5.1)

| Métrica | Shapiro-Wilk p | Assimetria | Resíduos | Teste principal | Motivo |
|---|---|---|---|---|---|
| `ops_s` | 0,0008 | 0,74 | 60 | mann_whitney | Shapiro-Wilk rejeita a normalidade (p < 0,05) |
| `lat_p50_ms` | 0,0000 | 1,20 | 60 | mann_whitney | Shapiro-Wilk rejeita a normalidade (p < 0,05); |assimetria| > 1 |
| `lat_p99_ms` | 0,0000 | 1,06 | 60 | mann_whitney | Shapiro-Wilk rejeita a normalidade (p < 0,05); |assimetria| > 1 |
| `memoria_bytes` | 0,0000 | 3,01 | 60 | mann_whitney | Shapiro-Wilk rejeita a normalidade (p < 0,05); |assimetria| > 1 |

## Comparações Valkey × Redis

Só para conferir que o código roda: com 5 repetições, o resultado **não é conclusão**.

| Métrica | io_threads | Carga | Razão de medianas | IC de 95% | p principal | p Holm | p sensibilidade | Discordam | Situação |
|---|---|---|---|---|---|---|---|---|---|
| `ops_s` | 1 | get | 1,029 | [0,776; 1,344] | 0,3095 | 0,9286 | 0,7924 | não | inconclusivo |
| `ops_s` | 1 | misto | 0,900 | [0,713; 1,265] | 0,6905 | 1,0000 | 0,6182 | não | inconclusivo |
| `ops_s` | 1 | set | 1,029 | [0,781; 1,209] | 1,0000 | 1,0000 | 0,8661 | não | inconclusivo |
| `ops_s` | 4 | get | 1,438 | [1,208; 1,971] | 0,0079 | 0,0476 | 0,0044 | não | diferença relevante |
| `ops_s` | 4 | misto | 1,604 | [1,333; 1,946] | 0,0079 | 0,0476 | 0,0015 | não | diferença relevante |
| `ops_s` | 4 | set | 1,584 | [1,243; 2,039] | 0,0079 | 0,0476 | 0,0004 | não | diferença relevante |
| `lat_p50_ms` | 1 | get | 0,973 | [0,758; 1,271] | 0,3976 | 1,0000 | 0,8007 | não | inconclusivo |
| `lat_p50_ms` | 1 | misto | 1,101 | [0,796; 1,368] | 0,6752 | 1,0000 | 0,6185 | não | inconclusivo |
| `lat_p50_ms` | 1 | set | 0,962 | [0,826; 1,241] | 1,0000 | 1,0000 | 0,9194 | não | inconclusivo |
| `lat_p50_ms` | 4 | get | 0,679 | [0,508; 0,822] | 0,0079 | 0,0476 | 0,0007 | não | diferença relevante |
| `lat_p50_ms` | 4 | misto | 0,614 | [0,518; 0,782] | 0,0114 | 0,0571 | 0,0002 | não | inconclusivo |
| `lat_p50_ms` | 4 | set | 0,629 | [0,499; 0,804] | 0,0119 | 0,0571 | 0,0006 | não | inconclusivo |
| `lat_p99_ms` | 1 | get | 0,971 | [0,725; 1,309] | 0,5284 | 1,0000 | 0,7824 | não | inconclusivo |
| `lat_p99_ms` | 1 | misto | 1,139 | [0,752; 1,459] | 0,6752 | 1,0000 | 0,6306 | não | inconclusivo |
| `lat_p99_ms` | 1 | set | 0,965 | [0,822; 1,334] | 0,8413 | 1,0000 | 0,8275 | não | inconclusivo |
| `lat_p99_ms` | 4 | get | 0,687 | [0,507; 0,822] | 0,0079 | 0,0476 | 0,0023 | não | diferença relevante |
| `lat_p99_ms` | 4 | misto | 0,618 | [0,511; 0,710] | 0,0119 | 0,0596 | 0,0000 | não | inconclusivo |
| `lat_p99_ms` | 4 | set | 0,626 | [0,461; 0,817] | 0,0119 | 0,0596 | 0,0020 | não | inconclusivo |
| `memoria_bytes` | 1 | get | 0,871 | [0,871; 0,872] | 0,0079 | 0,0476 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 1 | misto | 0,871 | [0,871; 0,871] | 0,0079 | 0,0476 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 1 | set | 0,871 | [0,871; 0,871] | 0,0079 | 0,0476 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 4 | get | 0,875 | [0,875; 0,875] | 0,0079 | 0,0476 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 4 | misto | 0,875 | [0,875; 0,875] | 0,0079 | 0,0476 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 4 | set | 0,875 | [0,874; 0,875] | 0,0079 | 0,0476 | 0,0000 | não | diferença relevante |

## Repetições necessárias para 5% com 80% de poder

Poder da comparação limitante (a de menor poder entre as 6). Grade de n: 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 100, 120, 150, 200, 250, 300.

| Variabilidade | Cenário de Holm | Métrica | Teste | σ de log máximo | n necessário | Poder no n | Limitante |
|---|---|---|---|---|---|---|---|
| bruta | conservador | `ops_s` | mann_whitney | 0,152 | 300 | 88,4% | io_threads 1, misto |
| bruta | conservador | `lat_p50_ms` | mann_whitney | 0,145 | 250 | 85,7% | io_threads 1, misto |
| bruta | conservador | `lat_p99_ms` | mann_whitney | 0,171 | > 300 | 77,8% | io_threads 1, misto |
| bruta | conservador | `memoria_bytes` | mann_whitney | 0,000 | 5 | 100,0% | io_threads 1, get |
| bruta | todas | `ops_s` | mann_whitney | 0,152 | 200 | 86,0% | io_threads 1, misto |
| bruta | todas | `lat_p50_ms` | mann_whitney | 0,145 | 200 | 89,6% | io_threads 1, misto |
| bruta | todas | `lat_p99_ms` | mann_whitney | 0,171 | 250 | 86,2% | io_threads 1, misto |
| bruta | todas | `memoria_bytes` | mann_whitney | 0,000 | 5 | 100,0% | io_threads 1, get |
| sem efeito de bloco | conservador | `ops_s` | mann_whitney | 0,093 | 100 | 81,4% | io_threads 1, misto |
| sem efeito de bloco | conservador | `lat_p50_ms` | mann_whitney | 0,086 | 100 | 89,1% | io_threads 4, get |
| sem efeito de bloco | conservador | `lat_p99_ms` | mann_whitney | 0,120 | 150 | 80,0% | io_threads 1, misto |
| sem efeito de bloco | conservador | `memoria_bytes` | mann_whitney | 0,000 | 5 | 100,0% | io_threads 1, get |

## Diferença detectável com 80% de poder nos n candidatos

Variabilidade bruta, cenário de Holm do config. Diferenças simuladas: 5,0%, 6,0%, 7,0%, 8,0%, 9,0%, 10,0%, 11,0%, 12,0%, 13,0%, 14,0%, 15,0%, 16,0%, 17,0%, 18,0%, 19,0%, 20,0%. "—": nenhuma delas basta.

| Métrica | n = 30 | n = 40 | n = 45 | n = 50 | n = 60 |
|---|---|---|---|---|---|
| `ops_s` | 16,0% | 14,0% | 13,0% | 12,0% | 11,0% |
| `lat_p50_ms` | 15,0% | 13,0% | 12,0% | 12,0% | 11,0% |
| `lat_p99_ms` | 18,0% | 16,0% | 15,0% | 14,0% | 13,0% |
| `memoria_bytes` | 5,0% | 5,0% | 5,0% | 5,0% | 5,0% |
