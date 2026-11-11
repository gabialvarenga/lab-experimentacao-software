# Registro da simulação C0, C1

Gerado por `lab04/simulacao.py`; não edite à mão. Para refazer, rode o comando abaixo.

| Item | Valor |
|---|---|
| Comando (a partir de `lab04/`) | `python -m lab04.simulacao --cenarios C0 C1 --saida dados/simulacao/c0_c1.csv` |
| Cenários | C0, C1 |
| Efeitos | C0: [0.0, 0.2, 0.4, 0.6, 0.8, 1.0]; C1: [0.0, 0.4, 0.8, 1.2, 1.6, 2.0] |
| Repetições por célula | 10000 |
| α | 0.05, 0.01 |
| Semente | 42 |
| SHA-256 do `config.yaml` (fins de linha LF) | `64ca47e7326b15d7f009920facc020a41738b907c6205a68de0f96b8651ea9a0` |
| Linhas do CSV | 48 |
| Mann-Whitney | C0: asymptotic; C1: asymptotic |
| p-valores NaN | welch: 0, mann_whitney: 0 |
| Ambiente | Python 3.12.10, numpy 2.5.4, scipy 1.18.1, pandas 3.1.1 |

## Erro tipo I (δ = 0)

| Cenário | α | Teste | Taxa | IC de Wilson de 95% | α dentro do IC |
|---|---|---|---|---|---|
| C0 | 0.05 | welch | 0.0463 | [0.0424; 0.0506] | sim |
| C0 | 0.05 | mann_whitney | 0.0443 | [0.0404; 0.0485] | não |
| C0 | 0.01 | welch | 0.0089 | [0.0072; 0.0109] | sim |
| C0 | 0.01 | mann_whitney | 0.0071 | [0.0056; 0.0089] | não |
| C1 | 0.05 | welch | 0.0247 | [0.0218; 0.0279] | não |
| C1 | 0.05 | mann_whitney | 0.0467 | [0.0427; 0.0510] | sim |
| C1 | 0.01 | welch | 0.0017 | [0.0011; 0.0027] | não |
| C1 | 0.01 | mann_whitney | 0.0099 | [0.0081; 0.0120] | sim |
