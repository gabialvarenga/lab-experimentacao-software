# k2 — Tarifa de estacionamento

Calcule quanto um carro paga, dado o horário de entrada e o de saída no mesmo
dia.

Implemente em `solucao.py`:

```python
def calcular_tarifa(entrada: str, saida: str) -> float:
    ...
```

Os horários chegam como texto no formato `"HH:MM"` (24 horas).

## Regras

1. Até **15 minutos** (inclusive) de permanência, a tarifa é `0.0`.
2. Acima disso cobra-se por **hora iniciada**: `R$ 5,00` pela primeira hora
   iniciada e `R$ 3,00` por cada hora iniciada seguinte. "Hora iniciada"
   significa arredondar o total de minutos para cima
   (61 minutos = 2 horas iniciadas).
3. O valor final é limitado a `R$ 25,00` por dia.
4. Se a saída for anterior ou igual à entrada, levante `ValueError` com a
   mensagem `saída anterior à entrada`.
5. Horário fora do formato `HH:MM`, ou com hora fora de `0..23` ou minuto fora
   de `0..59`, levanta `ValueError` com a mensagem `horário inválido: <valor>`.

## Exemplos

```python
>>> calcular_tarifa("08:00", "08:15")
0.0
>>> calcular_tarifa("08:00", "09:00")
5.0
>>> calcular_tarifa("08:00", "09:01")
8.0
>>> calcular_tarifa("08:00", "20:00")
25.0
```
