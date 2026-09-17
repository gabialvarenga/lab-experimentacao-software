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

## `validar_katas.py` — conferência das katas

Para cada kata do experimento, confere que a pasta está completa
(`enunciado.md`, `test_aceitacao.py`, `solucao_starter.py`), que a suíte de
aceitação roda pelo pytest sem erro de coleta, e que com o esqueleto vazio
todos os casos falham — nenhum teste passa sem implementação.

```
python lab02/scripts/validar_katas.py
python lab02/scripts/validar_katas.py --kata k3
python lab02/scripts/validar_katas.py --incluir-exemplo
```

Imprime, por kata, o nº de casos de teste — um dos critérios de equivalência de
dificuldade em `docs/katas.md`. Sai com código 1 se alguma kata estiver
mal-formada, então serve como checagem antes da S02.

## Testes dos próprios scripts

```
cd lab02 && python -m pytest
```

## `metricas_estaticas.py` — métricas estáticas de um trial (RQ3)

Roda sobre o `solucao.py` final de um trial e extrai as métricas
estruturais: complexidade ciclomática (Radon), LOC (Radon) e duplicação de
código (jscpd).

### Antes de rodar

```
python -m pip install -r lab02/requirements.txt
npm install -g jscpd   # ou deixe o npx baixar sob demanda na primeira vez
```

### Rodar um trial

```
python lab02/scripts/metricas_estaticas.py --integrante carlos --kata k1 --tratamento com-ia
```

| parâmetro | valores | descrição |
|---|---|---|
| `--integrante` | nome | quem fez o trial (junto com `--kata`/`--tratamento`, localiza `trials/<integrante>/<kata>-<tratamento>/solucao.py`) |
| `--kata` | id do kata | usado com `--integrante`/`--tratamento` |
| `--tratamento` | `com-ia` \| `sem-ia` | usado com `--integrante`/`--kata` |
| `--lote` | — | roda sobre todos os trials em `trials/` e escreve o CSV consolidado (não combina com `--integrante`) |
| `--csv` | caminho | CSV alternativo (padrão `lab02/dados/metricas-estaticas.csv`) |

### O que acontece

1. Roda `radon cc/raw/mi -j` e `jscpd --reporters json` sobre o `solucao.py`
   do trial (limiares do jscpd reduzidos para `--min-lines 3 --min-tokens
   20`, senão soluções pequenas de kata nunca disparam a detecção padrão).
2. Complexidade ciclomática: média e máximo entre funções/métodos (blocos
   `class` são excluídos, pra não contar a complexidade agregada da classe
   em cima da dos métodos).
3. Em `--lote`, pastas `exemplo-*` são ignoradas (mesmo critério do
   `cronometro.py`) e um trial que falha a medição (ex.: código com erro de
   sintaxe, esperado em trial censurado) é pulado com aviso, não derruba o
   lote inteiro.
4. `--lote` sempre reescreve `metricas-estaticas.csv` do zero — ele é
   derivado de `trials/`, não é coleta incremental como `trials.csv`.

### Colunas de `metricas-estaticas.csv`

`integrante, kata, tratamento, loc, cc_media, cc_max, mi, duplicacao_pct` —
esquema completo em `lab02/docs/00-decisoes.md`.

### Testes do próprio script

```
cd lab02 && python -m pytest
```

Só as funções de parsing/agregação são testadas automaticamente; a
integração com `radon`/`jscpd` de verdade foi validada manualmente contra
trials de amostra (kata de exemplo preenchido, um trial com duplicação
proposital, e um trial com erro de sintaxe proposital para testar a
resiliência do modo lote).

## `contagem_testes.py` — testes de aceitação por trial (RQ2)

Calcula `testes_total`, `testes_passando`, `testes_falhando` e
`taxa_sucesso` a partir do `report.xml` que o `cronometro.py` já grava ao
vivo em cada trial — não roda o pytest de novo.

### Rodar um trial

```
python lab02/scripts/contagem_testes.py --integrante carlos --kata k1 --tratamento com-ia
```

| parâmetro | valores | descrição |
|---|---|---|
| `--integrante` | nome | usado com `--kata`/`--tratamento` |
| `--kata` | id do kata | usado com `--integrante`/`--tratamento` |
| `--tratamento` | `com-ia` \| `sem-ia` | usado com `--integrante`/`--kata` |
| `--lote` | — | roda sobre todos os trials em `trials/` e escreve o CSV consolidado |
| `--csv` | caminho | CSV alternativo (padrão `lab02/dados/contagem-testes.csv`) |

### Por que `testes_total` não vem direto do `report.xml`

Quando `solucao.py` tem erro de sintaxe, o pytest grava `tests="1"
errors="1"` no relatório — a própria falha de coleta contada como um
teste, não os casos reais do kata. Isso deixaria um trial quebrado com
`testes_total` diferente dos outros trials do mesmo kata. Por isso o total
vem da contagem estática de `def test_...` no `test_aceitacao.py` original
do kata (fixo, nunca muda); só `testes_passando` vem do relatório real do
trial. Um trial sem `report.xml` (nem chegou a rodar) conta como 0
passando, sem quebrar o lote.

### Colunas de `contagem-testes.csv`

`integrante, kata, tratamento, testes_total, testes_passando,
testes_falhando, taxa_sucesso`. Separado de `trials.csv` (que fica só com
o registro bruto, gravado ao vivo) — mesma separação de
`metricas-estaticas.csv`.

### Testes do próprio script

```
cd lab02 && python -m pytest
```
