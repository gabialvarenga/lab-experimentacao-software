# k1 — Consumo de bateria de sensor

Um sensor de campo registra uma sequência de eventos e cada tipo de evento
gasta (ou repõe) bateria a uma taxa fixa por segundo.

Implemente em `solucao.py`:

```python
def consumo_bateria(eventos: list[dict], carga_inicial: float) -> float:
    ...
```

Cada evento é um dicionário com as chaves `tipo` (str) e `duracao_s` (int).

## Taxas, em pontos percentuais por segundo

| tipo | efeito na carga |
|---|---|
| `leitura` | −0,02 por segundo |
| `transmissao` | −0,15 por segundo |
| `espera` | −0,001 por segundo |
| `recarga` | +0,05 por segundo |

## Regras

1. Os eventos são aplicados na ordem em que aparecem na lista.
2. Depois de cada evento a carga é limitada à faixa de `0.0` a `100.0` — ela
   nunca fica negativa nem passa de 100.
3. Um `tipo` fora da tabela levanta `ValueError` com a mensagem
   `tipo desconhecido: <tipo>`.
4. `duracao_s` negativo levanta `ValueError` com a mensagem
   `duração negativa`.
5. O retorno é a carga final arredondada com `round(carga, 2)`.
6. Lista de eventos vazia devolve a carga inicial (arredondada).

## Exemplo

```python
>>> consumo_bateria([{"tipo": "leitura", "duracao_s": 100}], 100.0)
98.0
>>> consumo_bateria([{"tipo": "transmissao", "duracao_s": 1000}], 5.0)
0.0
```
