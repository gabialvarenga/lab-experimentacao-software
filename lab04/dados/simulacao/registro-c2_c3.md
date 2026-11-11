# Registro da simulação C2, C3

Gerado por `lab04/simulacao.py`; não edite à mão. Para refazer, rode o comando abaixo.

| Item | Valor |
|---|---|
| Comando (a partir de `lab04/`) | `python -m lab04.simulacao --cenarios C2 C3 --saida dados/simulacao/c2_c3.csv` |
| Cenários | C2, C3 |
| Efeitos | C2: [0.0, 0.4, 0.8, 1.2, 1.6, 2.0]; C3: [0.0, 0.4, 0.8, 1.2, 1.6, 2.0] |
| Repetições por célula | 10000 |
| α | 0.05, 0.01 |
| Semente | 42 |
| SHA-256 do `config.yaml` (fins de linha LF) | `64ca47e7326b15d7f009920facc020a41738b907c6205a68de0f96b8651ea9a0` |
| Linhas do CSV | 48 |
| Mann-Whitney | C2: asymptotic; C3: asymptotic |
| p-valores NaN | welch: 0, mann_whitney: 0 |
| Ambiente | Python 3.12.10, numpy 2.5.4, scipy 1.18.1, pandas 3.1.1 |

## Erro tipo I (δ = 0)

| Cenário | α | Teste | Taxa | IC de Wilson de 95% | α dentro do IC |
|---|---|---|---|---|---|
| C2 | 0.05 | welch | 0.0198 | [0.0172; 0.0227] | não |
| C2 | 0.05 | mann_whitney | 0.0486 | [0.0446; 0.0530] | sim |
| C2 | 0.01 | welch | 0.0006 | [0.0003; 0.0013] | não |
| C2 | 0.01 | mann_whitney | 0.0085 | [0.0069; 0.0105] | sim |
| C3 | 0.05 | welch | 0.0161 | [0.0138; 0.0188] | não |
| C3 | 0.05 | mann_whitney | 0.0496 | [0.0455; 0.0540] | sim |
| C3 | 0.01 | welch | 0.0009 | [0.0005; 0.0017] | não |
| C3 | 0.01 | mann_whitney | 0.0105 | [0.0087; 0.0127] | sim |
