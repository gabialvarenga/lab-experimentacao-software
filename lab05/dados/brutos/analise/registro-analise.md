# Registro da análise — execucoes.csv

Gerado por `lab05/analise.py`; não edite à mão. Para refazer, rode o comando abaixo.

| Item | Valor |
|---|---|
| Comando (a partir de `lab05/`) | `python -m lab05 analisar` |
| SHA-256 de `execucoes.csv` (fins de linha LF) | `e7ce9d81f951928c63f2ddd14579e659fe18ae91d797cc3d0a55d3e78355234d` |
| Execuções | 480 |
| Semente | 42 |
| Diferença relevante | 5% (razão de medianas fora de [0,95; 1,05]) |
| α | 0,05, bicaudal, Holm dentro de cada métrica |
| *Bootstrap* | 10000 reamostragens |
| Poder | 80%, 2000 simulações por ponto, cenário de Holm `conservador` |
| Ambiente | Python 3.14.3, numpy 2.5.2, scipy 1.18.1, pandas 3.0.5, statsmodels 0.15.0 |

## Teste principal por métrica (regra 5.1)

"Regra": o que a regra dá nestes dados. "Usado": o teste das comparações (`config`: decisão fixa do piloto).

| Métrica | Shapiro-Wilk p | Assimetria | Resíduos | Regra | Motivo | Usado |
|---|---|---|---|---|---|---|
| `ops_s` | 0,0000 | -2,37 | 480 | mann_whitney | Shapiro-Wilk rejeita a normalidade (p < 0,05); |assimetria| > 1 | mann_whitney (config) |
| `lat_p50_ms` | 0,0000 | 0,83 | 480 | mann_whitney | Shapiro-Wilk rejeita a normalidade (p < 0,05) | mann_whitney (config) |
| `lat_p99_ms` | 0,0000 | -0,66 | 480 | mann_whitney | Shapiro-Wilk rejeita a normalidade (p < 0,05) | mann_whitney (config) |
| `memoria_bytes` | 0,0000 | 3,13 | 480 | mann_whitney | Shapiro-Wilk rejeita a normalidade (p < 0,05); |assimetria| > 1 | mann_whitney (config) |

## Comparações Valkey × Redis

40 repetições por combinação.

| Métrica | io_threads | Carga | Razão de medianas | IC de 95% | p principal | p Holm | p sensibilidade | Discordam | Situação |
|---|---|---|---|---|---|---|---|---|---|
| `ops_s` | 1 | get | 0,991 | [0,987; 0,995] | 0,0003 | 0,0005 | 0,0009 | não | diferença pequena demais |
| `ops_s` | 1 | misto | 0,993 | [0,989; 0,996] | 0,0003 | 0,0005 | 0,0004 | não | diferença pequena demais |
| `ops_s` | 1 | set | 0,986 | [0,982; 0,991] | 0,0000 | 0,0000 | 0,0000 | não | diferença pequena demais |
| `ops_s` | 4 | get | 1,615 | [1,608; 1,620] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `ops_s` | 4 | misto | 1,628 | [1,623; 1,635] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `ops_s` | 4 | set | 1,632 | [1,627; 1,638] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `lat_p50_ms` | 1 | get | 1,000 | [1,000; 1,015] | 0,0068 | 0,0068 | 0,0102 | não | diferença pequena demais |
| `lat_p50_ms` | 1 | misto | 1,015 | [1,000; 1,015] | 0,0001 | 0,0002 | 0,0001 | não | diferença pequena demais |
| `lat_p50_ms` | 1 | set | 1,015 | [1,000; 1,015] | 0,0000 | 0,0000 | 0,0001 | não | diferença pequena demais |
| `lat_p50_ms` | 4 | get | 0,604 | [0,604; 0,604] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `lat_p50_ms` | 4 | misto | 0,588 | [0,588; 0,614] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `lat_p50_ms` | 4 | set | 0,614 | [0,614; 0,614] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `lat_p99_ms` | 1 | get | 1,008 | [0,996; 1,008] | 0,1275 | 0,2551 | 0,1912 | não | equivalência prática |
| `lat_p99_ms` | 1 | misto | 1,008 | [0,992; 1,008] | 0,3483 | 0,3483 | 0,5083 | não | equivalência prática |
| `lat_p99_ms` | 1 | set | 1,017 | [1,000; 1,017] | 0,0002 | 0,0005 | 0,0011 | não | diferença pequena demais |
| `lat_p99_ms` | 4 | get | 0,614 | [0,614; 0,625] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `lat_p99_ms` | 4 | misto | 0,618 | [0,618; 0,618] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `lat_p99_ms` | 4 | set | 0,612 | [0,612; 0,612] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 1 | get | 0,871 | [0,871; 0,871] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 1 | misto | 0,871 | [0,871; 0,871] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 1 | set | 0,871 | [0,871; 0,871] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 4 | get | 0,875 | [0,875; 0,875] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 4 | misto | 0,875 | [0,875; 0,875] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |
| `memoria_bytes` | 4 | set | 0,875 | [0,875; 0,875] | 0,0000 | 0,0000 | 0,0000 | não | diferença relevante |

## Repetições necessárias para 5% com 80% de poder

Poder da comparação limitante (a de menor poder entre as 6). Grade de n: 5, 10, 15, 20, 25, 30, 35, 40, 45, 50, 60, 70, 80, 100, 120, 150, 200, 250, 300.

| Variabilidade | Cenário de Holm | Métrica | Teste | σ de log máximo | n necessário | Poder no n | Limitante |
|---|---|---|---|---|---|---|---|
| bruta | conservador | `ops_s` | mann_whitney | 0,018 | 10 | 99,3% | io_threads 1, set |
| bruta | conservador | `lat_p50_ms` | mann_whitney | 0,020 | 10 | 97,6% | io_threads 1, set |
| bruta | conservador | `lat_p99_ms` | mann_whitney | 0,019 | 10 | 97,9% | io_threads 1, set |
| bruta | conservador | `memoria_bytes` | mann_whitney | 0,000 | 5 | 100,0% | io_threads 1, get |
| bruta | todas | `ops_s` | mann_whitney | 0,018 | 5 | 90,8% | io_threads 1, set |
| bruta | todas | `lat_p50_ms` | mann_whitney | 0,020 | 5 | 82,7% | io_threads 1, set |
| bruta | todas | `lat_p99_ms` | mann_whitney | 0,019 | 5 | 84,0% | io_threads 1, set |
| bruta | todas | `memoria_bytes` | mann_whitney | 0,000 | 5 | 100,0% | io_threads 1, get |
| sem efeito de bloco | conservador | `ops_s` | mann_whitney | 0,018 | 10 | 99,4% | io_threads 1, set |
| sem efeito de bloco | conservador | `lat_p50_ms` | mann_whitney | 0,020 | 10 | 97,8% | io_threads 1, set |
| sem efeito de bloco | conservador | `lat_p99_ms` | mann_whitney | 0,019 | 10 | 98,3% | io_threads 1, set |
| sem efeito de bloco | conservador | `memoria_bytes` | mann_whitney | 0,000 | 5 | 100,0% | io_threads 1, get |

## Diferença detectável com 80% de poder nos n candidatos

Cenário de Holm do config. Independente: Mann-Whitney com a variabilidade bruta. Pareada: Wilcoxon pareado com a variabilidade sem a deriva entre blocos (n = pares). Diferenças simuladas: 5,0%, 6,0%, 7,0%, 8,0%, 9,0%, 10,0%, 11,0%, 12,0%, 13,0%, 14,0%, 15,0%, 16,0%, 17,0%, 18,0%, 19,0%, 20,0%. "—": nenhuma delas basta.

| Métrica | Análise | n = 30 | n = 40 | n = 45 | n = 50 | n = 60 |
|---|---|---|---|---|---|---|
| `ops_s` | independente | 5,0% | 5,0% | 5,0% | 5,0% | 5,0% |
| `ops_s` | pareada | 5,0% | 5,0% | 5,0% | 5,0% | 5,0% |
| `lat_p50_ms` | independente | 5,0% | 5,0% | 5,0% | 5,0% | 5,0% |
| `lat_p50_ms` | pareada | 5,0% | 5,0% | 5,0% | 5,0% | 5,0% |
| `lat_p99_ms` | independente | 5,0% | 5,0% | 5,0% | 5,0% | 5,0% |
| `lat_p99_ms` | pareada | 5,0% | 5,0% | 5,0% | 5,0% | 5,0% |
| `memoria_bytes` | independente | 5,0% | 5,0% | 5,0% | 5,0% | 5,0% |
| `memoria_bytes` | pareada | 5,0% | 5,0% | 5,0% | 5,0% | 5,0% |

## Q3: interação servidor × io_threads

Método principal pela regra 5.1 aplicada aos resíduos do modelo de dois fatores no log, juntados por métrica; sensibilidade: ANOVA no log com o bloco (repetição). Holm entre as 3 cargas de cada métrica. R = razão das razões, (valkey 4 ÷ valkey 1) ÷ (redis 4 ÷ redis 1). 40 repetições por combinação.

| Métrica | Shapiro-Wilk p | Assimetria | Levene p (menor) | Regra | Motivo | Usado |
|---|---|---|---|---|---|---|
| `ops_s` | 0,0000 | -1,96 | 0,1217 | art | Shapiro-Wilk rejeita a normalidade (p < 0,05); |assimetria| > 1 | art |
| `lat_p99_ms` | 0,0000 | -0,30 | 0,1957 | art | Shapiro-Wilk rejeita a normalidade (p < 0,05) | art |

| Métrica | Carga | Método | R | IC de 95% | p interação | p Holm | η² parcial | p com bloco | Discordam | Situação |
|---|---|---|---|---|---|---|---|---|---|---|
| `ops_s` | get | art | 1,630 | [1,620; 1,637] | 0,0000 | 0,0000 | 0,750 | 0,0000 | não | diferença relevante |
| `ops_s` | misto | art | 1,640 | [1,632; 1,649] | 0,0000 | 0,0000 | 0,751 | 0,0000 | não | diferença relevante |
| `ops_s` | set | art | 1,655 | [1,645; 1,664] | 0,0000 | 0,0000 | 0,755 | 0,0000 | não | diferença relevante |
| `lat_p99_ms` | get | art | 0,609 | [0,609; 0,625] | 0,0000 | 0,0000 | 0,755 | 0,0000 | não | diferença relevante |
| `lat_p99_ms` | misto | art | 0,613 | [0,613; 0,623] | 0,0000 | 0,0000 | 0,756 | 0,0000 | não | diferença relevante |
| `lat_p99_ms` | set | art | 0,602 | [0,602; 0,612] | 0,0000 | 0,0000 | 0,759 | 0,0000 | não | diferença relevante |

## Análise pareada por bloco (sensibilidade)

Valkey ÷ Redis dentro de cada repetição; Wilcoxon pareado no log das razões, Hodges-Lehmann com IC exato, Holm entre as 6 comparações de cada métrica. Pares com execução refeita (em `falhas.csv`) saem. "Principal" é a situação do Mann-Whitney (comparações acima).

| Métrica | io_threads | Carga | Pares | Excluídos | Razão HL | IC | Cobertura | p Wilcoxon | p Holm | Situação | Principal |
|---|---|---|---|---|---|---|---|---|---|---|---|
| `ops_s` | 1 | get | 40 | 0 | 0,993 | [0,989; 0,997] | 95,02% | 0,0007 | 0,0014 | diferença pequena demais | diferença pequena demais |
| `ops_s` | 1 | misto | 40 | 0 | 0,993 | [0,988; 0,997] | 95,02% | 0,0024 | 0,0024 | diferença pequena demais | diferença pequena demais |
| `ops_s` | 1 | set | 40 | 0 | 0,986 | [0,981; 0,990] | 95,02% | 0,0000 | 0,0000 | diferença pequena demais | diferença pequena demais |
| `ops_s` | 4 | get | 40 | 0 | 1,614 | [1,608; 1,619] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `ops_s` | 4 | misto | 40 | 0 | 1,630 | [1,625; 1,635] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `ops_s` | 4 | set | 40 | 0 | 1,633 | [1,628; 1,637] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `lat_p50_ms` | 1 | get | 40 | 0 | 1,007 | [1,000; 1,008] | 95,02% | 0,0796 | 0,0796 | equivalência prática | diferença pequena demais |
| `lat_p50_ms` | 1 | misto | 40 | 0 | 1,007 | [1,007; 1,015] | 95,02% | 0,0024 | 0,0047 | diferença pequena demais | diferença pequena demais |
| `lat_p50_ms` | 1 | set | 40 | 0 | 1,015 | [1,007; 1,015] | 95,02% | 0,0000 | 0,0001 | diferença pequena demais | diferença pequena demais |
| `lat_p50_ms` | 4 | get | 40 | 0 | 0,609 | [0,604; 0,617] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `lat_p50_ms` | 4 | misto | 40 | 0 | 0,601 | [0,596; 0,601] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `lat_p50_ms` | 4 | set | 40 | 0 | 0,601 | [0,601; 0,614] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `lat_p99_ms` | 1 | get | 40 | 0 | 1,004 | [1,000; 1,008] | 95,02% | 0,0844 | 0,1688 | equivalência prática | equivalência prática |
| `lat_p99_ms` | 1 | misto | 40 | 0 | 1,000 | [0,996; 1,008] | 95,02% | 0,2484 | 0,2484 | equivalência prática | equivalência prática |
| `lat_p99_ms` | 1 | set | 40 | 0 | 1,012 | [1,004; 1,017] | 95,02% | 0,0003 | 0,0009 | diferença pequena demais | diferença pequena demais |
| `lat_p99_ms` | 4 | get | 40 | 0 | 0,621 | [0,617; 0,624] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `lat_p99_ms` | 4 | misto | 40 | 0 | 0,616 | [0,613; 0,618] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `lat_p99_ms` | 4 | set | 40 | 0 | 0,614 | [0,611; 0,617] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `memoria_bytes` | 1 | get | 40 | 0 | 0,871 | [0,871; 0,871] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `memoria_bytes` | 1 | misto | 40 | 0 | 0,871 | [0,871; 0,871] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `memoria_bytes` | 1 | set | 40 | 0 | 0,871 | [0,871; 0,871] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `memoria_bytes` | 4 | get | 40 | 0 | 0,875 | [0,875; 0,875] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `memoria_bytes` | 4 | misto | 40 | 0 | 0,875 | [0,875; 0,875] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
| `memoria_bytes` | 4 | set | 40 | 0 | 0,875 | [0,875; 0,875] | 95,02% | 0,0000 | 0,0000 | diferença relevante | diferença relevante |
