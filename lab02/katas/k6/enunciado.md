# k6 — Ranking de trilhas

Ordene trilhas por uma pontuação ponderada, para montar uma lista de sugestões.

Implemente em `solucao.py`:

```python
def ranking_trilhas(trilhas: list[dict], pesos: dict, limite: int | None = None) -> list[str]:
    ...
```

Cada trilha é um dicionário com `nome` (str), `distancia_km` (float),
`desnivel_m` (int) e `nota` (float, de 0 a 5).

## Regras

1. A pontuação de uma trilha é:

   ```
   distancia_km * pesos["distancia"] + desnivel_m * pesos["desnivel"] + nota * pesos["nota"]
   ```

   arredondada com `round(pontuacao, 3)`.
2. Peso ausente no dicionário `pesos` vale `0`.
3. São descartadas antes da ordenação as trilhas com `nota` fora da faixa de
   `0` a `5` (inclusive) e as com `distancia_km` menor ou igual a zero.
4. O resultado é a lista de **nomes**, da maior para a menor pontuação.
5. Empate na pontuação é resolvido pela **ordem alfabética** do nome.
6. Se `limite` for informado, devolva no máximo essa quantidade de nomes. Se for
   `None`, devolva todos.

## Exemplo

```python
>>> trilhas = [
...     {"nome": "Pedra Alta", "distancia_km": 5.0, "desnivel_m": 200, "nota": 4.0},
...     {"nome": "Vale Fundo", "distancia_km": 8.0, "desnivel_m": 100, "nota": 3.0},
... ]
>>> ranking_trilhas(trilhas, {"distancia": 2, "desnivel": 0.01, "nota": 10})
['Pedra Alta', 'Vale Fundo']
```
