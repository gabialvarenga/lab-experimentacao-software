# k5 — Validação de código de lote

Um código de lote tem o formato `AAA-9999-X`: três letras, um hífen, quatro
dígitos, um hífen e uma letra verificadora.

Implemente em `solucao.py`:

```python
def validar_lote(codigo: str) -> list[str]:
    ...
```

A função devolve a **lista de códigos de erro** encontrados. Código válido
devolve lista vazia.

## Regras

1. Se o texto não obedecer à forma geral `LLL-DDDD-L` (3 letras, 4 dígitos, 1
   letra, separados por hífen), devolva **apenas** `["FORMATO"]` — as demais
   verificações não são feitas.
2. `"PREFIXO"` — as três primeiras letras não estão todas em maiúsculas.
3. `"SEQUENCIA"` — os quatro dígitos são todos iguais.
4. `"DIGITO"` — a letra verificadora está errada. A correta é a letra do
   alfabeto `ABCDEFGHIJKLMNOPQRSTUVWXYZ` na posição
   `(soma dos quatro dígitos) % 26`, contando de zero.
5. Quando houver mais de um erro, eles vêm nesta ordem: `PREFIXO`,
   `SEQUENCIA`, `DIGITO`.

## Exemplos

```python
>>> validar_lote("ABC-1234-K")     # 1+2+3+4 = 10 -> 'K'
[]
>>> validar_lote("abc-1234-K")
['PREFIXO']
>>> validar_lote("ABC-9999-J")     # 36 % 26 = 10 -> 'K'
['SEQUENCIA', 'DIGITO']
>>> validar_lote("AB-1234-K")
['FORMATO']
```
