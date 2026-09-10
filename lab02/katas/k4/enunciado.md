# k4 — Escala de plantão

Distribua os dias de plantão entre as pessoas de uma equipe, respeitando as
indisponibilidades e mantendo a carga equilibrada.

Implemente em `solucao.py`:

```python
def montar_escala(pessoas: list[dict], dias: list[str]) -> dict:
    ...
```

Cada pessoa é um dicionário com `nome` (str) e `indisponivel` (lista de dias em
que ela não pode assumir plantão; a chave pode estar ausente).

## Regras

1. Cada dia da lista `dias` é atribuído a exatamente uma pessoa, processando os
   dias na ordem em que aparecem.
2. Para cada dia, só concorrem as pessoas disponíveis naquele dia.
3. Entre as disponíveis, fica com o dia quem tiver **menos plantões
   acumulados** até ali.
4. Empate na quantidade de plantões é resolvido pela **ordem alfabética** do
   nome.
5. Se ninguém estiver disponível para um dia, levante `ValueError` com a
   mensagem `sem cobertura para <dia>`.
6. O retorno é um dicionário `nome -> lista de dias`, na ordem em que os dias
   foram atribuídos, e **inclui todas as pessoas**, mesmo as que ficaram sem
   nenhum plantão.

## Exemplo

```python
>>> pessoas = [{"nome": "Ana", "indisponivel": []}, {"nome": "Bia", "indisponivel": []}]
>>> montar_escala(pessoas, ["seg", "ter", "qua", "qui"])
{'Ana': ['seg', 'qua'], 'Bia': ['ter', 'qui']}
```
