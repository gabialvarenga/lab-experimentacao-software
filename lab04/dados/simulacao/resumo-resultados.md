# Resumo dos resultados da simulação

Gerado por `lab04/resultados.py`; não edite à mão. Para refazer: `python -m lab04.resultados` (a partir de `lab04/`).

## Erro tipo I (δ = 0)

Critério: **liberal** se o limite inferior do IC de Wilson de 95% está acima de α; **conservador** se o limite superior está abaixo de α; **ok** se o IC contém α. `Desvio` é taxa − α em pontos percentuais.

| Cenário | α | Teste | Taxa | IC de Wilson de 95% | Desvio (p.p.) | Classificação |
|---|---|---|---|---|---|---|
| C0 | 0,05 | Welch | 4,63% | [4,24%; 5,06%] | -0,37 | ok |
| C0 | 0,05 | Mann-Whitney | 4,43% | [4,04%; 4,85%] | -0,57 | conservador |
| C0 | 0,01 | Welch | 0,89% | [0,72%; 1,09%] | -0,11 | ok |
| C0 | 0,01 | Mann-Whitney | 0,71% | [0,56%; 0,89%] | -0,29 | conservador |
| C1 | 0,05 | Welch | 2,47% | [2,18%; 2,79%] | -2,53 | conservador |
| C1 | 0,05 | Mann-Whitney | 4,67% | [4,27%; 5,10%] | -0,33 | ok |
| C1 | 0,01 | Welch | 0,17% | [0,11%; 0,27%] | -0,83 | conservador |
| C1 | 0,01 | Mann-Whitney | 0,99% | [0,81%; 1,20%] | -0,01 | ok |
| C2 | 0,05 | Welch | 1,98% | [1,72%; 2,27%] | -3,02 | conservador |
| C2 | 0,05 | Mann-Whitney | 4,86% | [4,46%; 5,30%] | -0,14 | ok |
| C2 | 0,01 | Welch | 0,06% | [0,03%; 0,13%] | -0,94 | conservador |
| C2 | 0,01 | Mann-Whitney | 0,85% | [0,69%; 1,05%] | -0,15 | ok |
| C3 | 0,05 | Welch | 1,61% | [1,38%; 1,88%] | -3,39 | conservador |
| C3 | 0,05 | Mann-Whitney | 4,96% | [4,55%; 5,40%] | -0,04 | ok |
| C3 | 0,01 | Welch | 0,09% | [0,05%; 0,17%] | -0,91 | conservador |
| C3 | 0,01 | Mann-Whitney | 1,05% | [0,87%; 1,27%] | +0,05 | ok |
| C4 | 0,05 | Welch | 1,54% | [1,32%; 1,80%] | -3,46 | conservador |
| C4 | 0,05 | Mann-Whitney | 4,35% | [3,97%; 4,77%] | -0,65 | conservador |
| C4 | 0,01 | Welch | 0,04% | [0,02%; 0,10%] | -0,96 | conservador |
| C4 | 0,01 | Mann-Whitney | 0,74% | [0,59%; 0,93%] | -0,26 | conservador |

## Poder (α = 0,05)

Vantagem = poder do Mann-Whitney − poder do Welch, em pontos percentuais (positivo: Mann-Whitney à frente). `empate` quando a diferença não passa de 1,96 erros-padrão. Os resultados de α = 0,01 estão em `poder.csv`.

| Cenário | Efeito δ | Welch | Mann-Whitney | Vantagem (p.p.) | Melhor |
|---|---|---|---|---|---|
| C0 | 0,2 | 11,53% | 10,83% | -0,70 | empate |
| C0 | 0,4 | 33,20% | 31,44% | -1,76 | Welch |
| C0 | 0,6 | 63,03% | 60,06% | -2,97 | Welch |
| C0 | 0,8 | 86,55% | 84,30% | -2,25 | Welch |
| C0 | 1 | 96,64% | 95,94% | -0,70 | Welch |
| C1 | 0,4 | 6,43% | 13,96% | +7,53 | Mann-Whitney |
| C1 | 0,8 | 17,47% | 41,71% | +24,24 | Mann-Whitney |
| C1 | 1,2 | 36,68% | 76,86% | +40,18 | Mann-Whitney |
| C1 | 1,6 | 53,91% | 94,91% | +41,00 | Mann-Whitney |
| C1 | 2 | 68,56% | 99,41% | +30,85 | Mann-Whitney |
| C2 | 0,4 | 3,78% | 11,26% | +7,48 | Mann-Whitney |
| C2 | 0,8 | 9,13% | 31,08% | +21,95 | Mann-Whitney |
| C2 | 1,2 | 19,24% | 60,17% | +40,93 | Mann-Whitney |
| C2 | 1,6 | 30,86% | 83,98% | +53,12 | Mann-Whitney |
| C2 | 2 | 42,92% | 95,87% | +52,95 | Mann-Whitney |
| C3 | 0,4 | 3,73% | 13,25% | +9,52 | Mann-Whitney |
| C3 | 0,8 | 9,40% | 39,07% | +29,67 | Mann-Whitney |
| C3 | 1,2 | 19,11% | 71,44% | +52,33 | Mann-Whitney |
| C3 | 1,6 | 31,87% | 91,74% | +59,87 | Mann-Whitney |
| C3 | 2 | 41,50% | 98,87% | +57,37 | Mann-Whitney |
| C4 | 0,4 | 2,47% | 7,24% | +4,77 | Mann-Whitney |
| C4 | 0,8 | 4,67% | 15,45% | +10,78 | Mann-Whitney |
| C4 | 1,2 | 9,07% | 29,36% | +20,29 | Mann-Whitney |
| C4 | 1,6 | 15,25% | 48,42% | +33,17 | Mann-Whitney |
| C4 | 2 | 22,09% | 67,67% | +45,58 | Mann-Whitney |

## Quem lidera em cada cenário

| Cenário | α | Líder | Efeitos Welch / Mann-Whitney / empate | Vantagem média (p.p.) | Maior vantagem (p.p.) | em δ |
|---|---|---|---|---|---|---|
| C0 | 0,05 | Welch | 4 / 0 / 1 | -1,68 | -2,97 | 0,6 |
| C0 | 0,01 | Welch | 4 / 0 / 1 | -2,08 | -3,86 | 0,8 |
| C1 | 0,05 | Mann-Whitney | 0 / 5 / 0 | +28,76 | +41,00 | 1,6 |
| C1 | 0,01 | Mann-Whitney | 0 / 5 / 0 | +37,77 | +63,11 | 2 |
| C2 | 0,05 | Mann-Whitney | 0 / 5 / 0 | +35,29 | +53,12 | 1,6 |
| C2 | 0,01 | Mann-Whitney | 0 / 5 / 0 | +35,07 | +73,37 | 2 |
| C3 | 0,05 | Mann-Whitney | 0 / 5 / 0 | +41,75 | +59,87 | 1,6 |
| C3 | 0,01 | Mann-Whitney | 0 / 5 / 0 | +42,39 | +79,94 | 2 |
| C4 | 0,05 | Mann-Whitney | 0 / 5 / 0 | +22,92 | +45,58 | 2 |
| C4 | 0,01 | Mann-Whitney | 0 / 5 / 0 | +13,67 | +34,05 | 2 |

## Onde a vantagem de poder muda de lado

**Ao longo do efeito, dentro de um cenário:** nenhum. Em cada cenário o mesmo teste lidera em todos os efeitos em que há diferença.

- **Entre cenários, α = 0,05:** em C0 lidera Welch; o líder muda em C1 (Mann-Whitney), C2 (Mann-Whitney), C3 (Mann-Whitney), C4 (Mann-Whitney).
- **Entre cenários, α = 0,01:** em C0 lidera Welch; o líder muda em C1 (Mann-Whitney), C2 (Mann-Whitney), C3 (Mann-Whitney), C4 (Mann-Whitney).
