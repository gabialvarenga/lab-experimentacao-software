# k3 — Mesclagem de leituras de sensores

Duas estações enviam leituras do mesmo fenômeno e você precisa consolidar as
duas listas em uma única série.

Implemente em `solucao.py`:

```python
def mesclar_leituras(a: list[dict], b: list[dict]) -> list[dict]:
    ...
```

Cada leitura é um dicionário com as chaves `ts` (int, o instante), `valor`
(float) e `precisao` (int, quanto maior melhor).

## Regras

1. O resultado junta as leituras das duas listas, **ordenado por `ts`**
   crescente.
2. Se o mesmo `ts` aparecer mais de uma vez (dentro da mesma lista ou entre as
   duas), fica só a leitura de **maior `precisao`**.
3. Em caso de empate na `precisao`, prevalece a leitura que veio da lista `a`;
   dentro de uma mesma lista, prevalece a primeira que aparece.
4. Leituras com `valor` igual a `None` são descartadas antes de tudo.
5. As listas recebidas **não podem ser modificadas**, e os dicionários do
   resultado também não podem ser os mesmos objetos das listas de entrada.
6. Duas listas vazias devolvem uma lista vazia.

## Exemplo

```python
>>> a = [{"ts": 2, "valor": 1.0, "precisao": 1}]
>>> b = [{"ts": 1, "valor": 9.0, "precisao": 3}, {"ts": 2, "valor": 5.0, "precisao": 7}]
>>> mesclar_leituras(a, b)
[{'ts': 1, 'valor': 9.0, 'precisao': 3}, {'ts': 2, 'valor': 5.0, 'precisao': 7}]
```
