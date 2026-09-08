# Scripts do Lab02

## `cronometro.py` — cronometragem e coleta de um trial

Conduz um trial do experimento: cronometra o tempo até todos os testes de
aceitação do kata passarem (*time-to-green*), aplica o time-box de 35 min e
grava uma linha em `lab02/dados/trials.csv`.

### Antes de rodar

```
python -m pip install -r lab02/requirements.txt
```

Cada kata fica em `lab02/katas/<id>/` com:

- `test_aceitacao.py` — testes de aceitação (importam `solucao`);
- `solucao_starter.py` — esqueleto opcional copiado para o trial;
- `enunciado.md`.

### Rodar um trial

```
python lab02/scripts/cronometro.py --integrante gabriela --kata k1 --tratamento sem-ia --ordem 1
```

| parâmetro | valores | descrição |
|---|---|---|
| `--integrante` | `brenda` \| `carlos` \| `gabriela` | quem está resolvendo |
| `--kata` | id da pasta em `katas/` (ex.: `k1`, `exemplo`) | kata do trial |
| `--tratamento` | `com-ia` \| `sem-ia` | com ou sem o Claude Code |
| `--ordem` | inteiro `1..6` | posição do trial na sequência do integrante |
| `--timebox` | minutos (padrão `35`) | só reduzir, com justificativa no relatório; nunca aumentar |
| `--poll` | segundos (padrão `15`) | intervalo entre as checagens automáticas dos testes |
| `--csv` | caminho | CSV alternativo (padrão `lab02/dados/trials.csv`) |

### O que acontece

1. O script cria `lab02/trials/<integrante>/<kata>-<tratamento>/`, copia o
   `test_aceitacao.py` e cria `solucao.py`.
2. Você resolve o kata editando **apenas** o `solucao.py` desse diretório.
   Não edite o `test_aceitacao.py`.
3. A cada `--poll` segundos o script roda os testes e mostra
   `passando/total`. Quando tudo passa, o trial encerra sozinho.
4. Aos 30 min aparece um aviso de "faltam ~5 min". Aos 35 min o trial é
   encerrado como **censurado** (`censurado=true`, `tempo_segundos=2100`).
5. `Ctrl+C` encerra o trial na hora, também como censurado (para quando você
   desiste antes do tempo).
6. No fim, o script pergunta o nº de prompts (só no `com-ia`) e um campo de
   observações, e anexa a linha ao CSV.

### Colunas de `trials.csv`

`integrante, kata, tratamento, ordem, data_inicio, tempo_segundos, censurado,
testes_total, testes_passando, prompts, observacoes` — esquema completo em
`lab02/docs/00-decisoes.md`. As métricas estáticas (LOC, complexidade,
duplicação) ficam em um CSV separado, gerado por outro script.

### Kata de exemplo

`katas/exemplo/` existe só para testar o fluxo do script de ponta a ponta e
**não entra no experimento**. Os trials gerados com ele
(`trials/**/exemplo-*/`) são ignorados pelo git.

### Testes do próprio script

```
cd lab02 && python -m pytest
```
