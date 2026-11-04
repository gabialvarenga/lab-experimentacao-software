# Lab04 — Exemplo simulado: os dois testes aplicados e interpretados

Dois conjuntos simulados, um sem efeito (δ = 0) e um com efeito (δ da calibração), com o t de Welch e o Mann-Whitney aplicados a cada um. Os mesmos dois exemplos alimentam o G2 (S01-10). A pergunta e as hipóteses estão em [cenario.md](cenario.md); a calibração, em [calibracao-lognormal.md](calibracao-lognormal.md).

Siglas: PR (*Pull Request*); H₀ (hipótese nula); IQR (amplitude interquartil).

## 1. Como os exemplos foram gerados

| Item | Exemplo sem efeito | Exemplo com efeito |
|---|---|---|
| Função | `gerador.exemplo_simulado` | `gerador.exemplo_simulado` |
| Família | lognormal | lognormal |
| μ do grupo A (log h) | 2,6739 (o do `com_bot` real) | 2,6739 |
| σ dos dois grupos (log h) | 1,6493 (raiz da média das variâncias de log(horas) dos dois grupos reais) | 1,6493 |
| δ | 0 | 0,3518 (μ do `sem_bot` real − μ do `com_bot` real) |
| Razão de medianas B/A | 1 | e^δ = 1,42 |
| n por grupo | 30 | 30 |
| Semente | 20261104 | 20261105 |

- **Parâmetros.** Vêm do `dados/reais/calibracao.json` final da S01-06, já mesclado. Por isso não houve versão provisória: os exemplos foram gerados direto com a calibração final.
- **Convenção.** A é o grupo `com_bot` e B é o `sem_bot`, como em `testes.py`. O gerador usa um σ só para os dois grupos, e os σ reais são 1,48 e 1,80; o δ reproduz a diferença entre os μ reais.
- **Sementes.** Foram fixadas no código antes de qualquer p-valor ser visto (as datas das entregas, 04/11 e 05/11) e não foram trocadas depois. Cada exemplo foi gerado uma única vez, e o resultado que saiu é o que está abaixo, mesmo sendo pouco ilustrativo (seção 4).
- **Testes.** Welch e Mann-Whitney bicaudais, α = 0,05, de `testes.aplicar_testes`.

Para reproduzir (a partir da pasta `lab04/`):

```python
from lab04 import calibracao, gerador

exemplos = gerador.exemplos_calibrados(calibracao.ler("dados/reais/calibracao.json"))
exemplos["sem_efeito"]["resultado"]
```

## 2. Resultados

Resumo das amostras (horas):

| Exemplo | Grupo | Mediana | Média | Desvio-padrão | Mínimo | Máximo |
|---|---|---|---|---|---|---|
| Sem efeito | A | 10,08 | 28,82 | 41,44 | 0,50 | 180,95 |
| Sem efeito | B | 27,55 | 55,98 | 103,37 | 0,34 | 541,67 |
| Com efeito | A | 20,29 | 57,75 | 81,75 | 0,47 | 315,29 |
| Com efeito | B | 10,27 | 68,71 | 159,23 | 0,79 | 811,75 |

Testes (bicaudais, α = 0,05):

| Medida | Sem efeito | Com efeito |
|---|---|---|
| Welch: t | −1,335 | −0,336 |
| Welch: graus de liberdade | 38,09 | 43,30 |
| Welch: p-valor | 0,190 | 0,739 |
| Mann-Whitney: U (do grupo A) | 358 | 503 |
| Mann-Whitney: p-valor (aproximação normal) | 0,176 | 0,438 |
| Decisão do Welch | não rejeita H₀ | não rejeita H₀ |
| Decisão do Mann-Whitney | não rejeita H₀ | não rejeita H₀ |
| Hedges g (A − B) | −0,340 | −0,086 |
| Delta de Cliff (A em relação a B) | −0,204 | 0,118 |
| Razão de medianas A/B | 0,366 | 1,975 |

## 3. Interpretação

### 3.1 Exemplo sem efeito (δ = 0)

Os dois grupos vêm da mesma distribuição, então H₀ é verdadeira.

- **Welch.** t = −1,335 com 38,09 graus de liberdade, p = 0,190. Como p > 0,05, não rejeita H₀ (médias iguais). O p-valor diz que, se as médias fossem iguais, uma diferença de médias pelo menos tão grande quanto esta apareceria em cerca de 19% das amostras.
- **Mann-Whitney.** U = 358 (a média de U sob H₀, com 30 por grupo, é 450), p = 0,176. Também não rejeita H₀. O p-valor diz que, se os dois grupos tivessem a mesma distribuição, ordens tão desbalanceadas entre os grupos apareceriam em cerca de 18% das amostras.
- **Leitura.** A decisão está certa, porque H₀ é verdadeira. Mas as amostras parecem bem diferentes: a mediana de B (27,6 h) é 2,7 vezes a de A (10,1 h), e a média de B é quase o dobro da de A. É variação de amostragem de uma lognormal com σ ≈ 1,65, e é por isso que o p-valor não é pequeno mesmo com uma diferença tão visível na amostra.

### 3.2 Exemplo com efeito (δ = 0,3518)

B tem mediana 1,42 vez a de A, então H₀ é falsa.

- **Welch.** t = −0,336 com 43,30 graus de liberdade, p = 0,739. Não rejeita H₀.
- **Mann-Whitney.** U = 503, p = 0,438. Não rejeita H₀.
- **Leitura.** Os dois testes não detectam o efeito: é um erro tipo II. Não é surpresa: o efeito, em escala log, é 0,35 para um σ de 1,65, ou seja, só 0,21 desvio-padrão. Na escala log, onde o t seria o teste ideal, o poder com 30 por grupo e esse efeito é de cerca de 13% (cálculo analítico com a t não central); em horas, com a cauda longa, o poder do Welch pode ser menor (quem mede é a simulação, em S02). A amostra ainda trouxe o sinal invertido: a mediana de B (10,3 h) ficou abaixo da de A (20,3 h), embora a verdadeira mediana de B seja maior. Com esse σ, o acaso inverte a ordem das medianas com folga.

### 3.3 O que o p-valor significa e o que não significa

| Significa | Não significa |
|---|---|
| A probabilidade de obter uma estatística pelo menos tão extrema quanto a observada, **se H₀ fosse verdadeira** | A probabilidade de H₀ ser verdadeira |
| Um p-valor pequeno é evidência contra H₀ | Um p-valor grande prova H₀ (no exemplo com efeito, p = 0,74 e a H₀ é falsa) |
| Com α = 0,05, rejeitar H₀ erra em 5% das vezes quando H₀ é verdadeira | O tamanho ou a importância do efeito: para isso servem Hedges g, delta de Cliff e a razão de medianas |

### 3.4 Casos de borda da issue

- **p-valor próximo de 0,05.** Não ocorreu: os menores p-valores são 0,176 e 0,190.
- **Welch e Mann-Whitney discordando.** Não ocorreu: os dois testes têm a mesma decisão nos dois exemplos. Os p-valores do Mann-Whitney são menores que os do Welch (0,176 contra 0,190 e 0,438 contra 0,739), o que combina com a expectativa do cenário C1 de que o Mann-Whitney se sai melhor que o Welch com cauda longa. Dois exemplos não provam isso: quem mede é a simulação em massa (S02).

## 4. Limites do exemplo

- É um único conjunto por cenário, com uma semente fixa. Serve para mostrar o que cada teste calcula e como a decisão sai, não para comparar o desempenho dos testes; para isso há o erro tipo I e o poder, por simulação em massa (S02).
- O exemplo com efeito não rejeita H₀. Foi mantido como saiu: trocar a semente até o teste rejeitar anularia o sentido da semente fixada antes. Ele ilustra bem o erro tipo II e o poder baixo com esse efeito, e o G2 mostra a estatística observada dentro da região de não rejeição.
- O δ vem da diferença observada entre os μ dos dois grupos reais, e o σ é único. Os σ reais são diferentes (1,48 e 1,80), o que a simulação de referência não reproduz; fica como limitação.
