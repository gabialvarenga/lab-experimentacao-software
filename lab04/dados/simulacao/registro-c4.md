# Registro da simulação C4

Gerado por `lab04/simulacao.py`; não edite à mão. Para refazer, rode o comando abaixo.

| Item | Valor |
|---|---|
| Comando (a partir de `lab04/`) | `python -m lab04.simulacao --cenarios C4 --saida dados/simulacao/c4.csv` |
| Cenários | C4 |
| Efeitos | C4: [0.0, 0.4, 0.8, 1.2, 1.6, 2.0] |
| Repetições por célula | 10000 |
| α | 0.05, 0.01 |
| Semente | 42 |
| SHA-256 do `config.yaml` (fins de linha LF) | `64ca47e7326b15d7f009920facc020a41738b907c6205a68de0f96b8651ea9a0` |
| Linhas do CSV | 24 |
| Mann-Whitney | C4: asymptotic |
| p-valores NaN | welch: 0, mann_whitney: 0 |
| Ambiente | Python 3.12.10, numpy 2.5.4, scipy 1.18.1, pandas 3.1.1 |

## Erro tipo I (δ = 0)

| Cenário | α | Teste | Taxa | IC de Wilson de 95% | α dentro do IC |
|---|---|---|---|---|---|
| C4 | 0.05 | welch | 0.0154 | [0.0132; 0.0180] | não |
| C4 | 0.05 | mann_whitney | 0.0435 | [0.0397; 0.0477] | não |
| C4 | 0.01 | welch | 0.0004 | [0.0002; 0.0010] | não |
| C4 | 0.01 | mann_whitney | 0.0074 | [0.0059; 0.0093] | não |
