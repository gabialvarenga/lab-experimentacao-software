# Lab04 — Cenário e expectativa

Cenário do Lab04 (item c do enunciado): a pergunta, as hipóteses, o significado dos erros no contexto do problema e a expectativa do grupo, escrita antes de qualquer simulação. Os parâmetros numéricos da simulação saem dos dados reais e são definidos depois (Issue S01-06). A fonte, os grupos e a amostragem estão no [protocolo de coleta](protocolo-coleta.md).

Siglas: PR (*Pull Request*); H₀ e H₁ (hipóteses nula e alternativa); α (nível de significância); IQR (*Interquartile Range*, intervalo interquartil).

**Esta expectativa não é reescrita depois de ver resultados.** Qualquer correção entra como adendo datado na seção 7, sem apagar o texto original. O commit que a introduz precisa ser anterior ao primeiro commit que roda os dois testes sobre dados simulados (Issue S01-08).

## 1. Pergunta

O tempo até o merge de um PR do `supabase/supabase` muda quando ele recebe, em até 1 h após a abertura, a revisão automática do Copilot?

## 2. Hipóteses

Em palavras simples: H₀ diz que a revisão do Copilot não faz diferença no tempo até o merge; H₁ diz que faz diferença, para mais ou para menos.

Os dois testes comparam coisas diferentes, e por isso cada um tem a sua formulação:

| | t de Welch | Mann-Whitney |
|---|---|---|
| O que compara | As médias dos dois grupos | Os postos: com que frequência um PR do grupo com bot demora mais que um PR do grupo sem bot |
| H₀ | μ_com = μ_sem | P(X_com > X_sem) + ½·P(X_com = X_sem) = ½ |
| H₁ (bicaudal) | μ_com ≠ μ_sem | P(X_com > X_sem) + ½·P(X_com = X_sem) ≠ ½ |

X é o tempo até o merge, em horas. Nos dois testes, α = 0,05.

**Na simulação, H₀ verdadeira** significa que os dois grupos vêm da mesma distribuição. Assim as duas hipóteses nulas valem ao mesmo tempo e a taxa de rejeição de cada teste é, de fato, o erro tipo I. Com um efeito δ > 0, o grupo com bot passa a ter a mediana multiplicada por e^δ.

**Nos dados reais**, os dois testes podem discordar sem que nenhum esteja errado, porque respondem a perguntas um pouco diferentes: a média é puxada pelos PRs muito longos, e os postos não.

## 3. Teste bicaudal

O teste é bicaudal. Não há direção estabelecida a priori: a revisão automática pode acelerar o merge, ao dar feedback imediato, ou atrasá-lo, ao gerar comentários que precisam ser resolvidos antes do merge. Um teste unicaudal só seria justificável com uma direção prevista antes de ver os dados, e o grupo não tem essa previsão. Um teste unicaudal também esconderia um efeito na direção oposta. O custo é um pouco menos de poder para detectar um efeito na direção esperada, e o grupo aceita esse custo.

## 4. Erros tipo I e tipo II

| Erro | No cenário | Consequência |
|---|---|---|
| Tipo I (falso positivo) | Concluir que a revisão do Copilot muda o tempo de merge quando não muda | Um time poderia adotar, exigir ou abandonar a revisão automática por causa de uma diferença que não existe |
| Tipo II (falso negativo) | Não perceber um efeito real da revisão do Copilot | O time deixaria de aproveitar um ganho, ou de notar que o bot atrasa os PRs |

**Qual é mais grave.** Para esta pergunta, o grupo considera o erro tipo I mais grave. A conclusão alimentaria uma decisão de processo que afeta todos os PRs futuros, com custo real de mudança, e se baseia numa diferença que não existe. O erro tipo II custa uma oportunidade perdida, e ela pode ser reavaliada com mais dados, o que é fácil de fazer neste cenário (basta esperar mais PRs). O risco do tipo II é grande com ~30 PRs por grupo, e por isso o laboratório mede o poder (Q2) em vez de supor que ele é alto. Se o objetivo fosse detectar um efeito mesmo pequeno (por exemplo, para não perder uma melhoria), o peso se inverteria.

## 5. Expectativa antes de simular

Qual teste o grupo espera que se saia melhor, e por quê. A expectativa é qualitativa; os números dependem dos parâmetros definidos na S01-06. Os cenários são os do [planejamento](planejamento.md), seção 2.2.

**Teste esperado como melhor no cenário real: Mann-Whitney.** O tempo até o merge tem cauda longa à direita (poucos PRs demoram dias). A média é sensível a esses PRs, e o Mann-Whitney usa só a ordem dos valores. O t de Welch continua sendo uma opção razoável se o interesse for exatamente a diferença de médias e o n for grande.

| Cenário | Erro tipo I esperado | Poder esperado | Por quê |
|---|---|---|---|
| C0: normal, n = 30 (controle) | Os dois perto de 5% | Empate técnico, com leve vantagem do Welch | Com dados normais o Welch é o teste mais poderoso; o Mann-Whitney perde pouco (a eficiência assintótica relativa é cerca de 95%) |
| C1: lognormal calibrada nos dados reais, n = 30 | Os dois perto de 5%; o Welch possivelmente um pouco abaixo | Mann-Whitney maior que Welch | Com grupos de mesmo tamanho e mesma forma, a assimetria quase se cancela no erro tipo I, mas a cauda longa aumenta a variância da média e reduz o poder do Welch |
| C2: assimetria forte (σ(log) maior) | Mann-Whitney perto de 5%; Welch se afasta de 5%, provavelmente para baixo | Mann-Whitney bem maior que Welch | Quanto mais pesada a cauda, mais o Welch perde poder e menos a distribuição t descreve a estatística |
| C3: outliers (≈ 5% das observações multiplicadas por ≈ 20, nos dois grupos) | Mann-Whitney perto de 5%; Welch abaixo de 5% | Mann-Whitney maior; o poder do Welch cai muito | Os outliers inflam o desvio-padrão, o que alarga o denominador do t; a ordem dos valores quase não muda |
| C4: amostra pequena (n = 10) | Mann-Whitney em torno de 5%, talvez um pouco abaixo; Welch pode se afastar de 5% | Poder baixo nos dois, com Mann-Whitney igual ou melhor | Com n = 10 a aproximação do Welch é mais frágil; a aproximação normal do Mann-Whitney, com correção de continuidade, tende a ser levemente conservadora |

**Onde a vantagem muda de lado.** O grupo espera que o Welch só seja melhor ou igual em C0 (dados normais). Em C1 a C4 espera o Mann-Whitney igual ou melhor, com a diferença crescendo com a assimetria e com os outliers.

**Efeito de α = 0,01.** O grupo espera que o poder dos dois testes caia, sem inverter a ordem entre eles. O desvio do Welch em relação ao valor nominal tende a ser mais visível no nível de 1%, porque as caudas da estatística são onde a aproximação mais falha.

**Dados reais.** O grupo espera que os dois testes rejeitem H₀ com folga nos dados reais, porque a sondagem do protocolo já mostrou diferença grande entre as medianas dos grupos, e que o tamanho de efeito seja relevante na prática. Se um dos testes não rejeitar, isso será discutido na seção 7 (conclusão) do dashboard.

## 6. Perguntas da apresentação que esta seção sustenta

Perguntas 1 (cenário e hipóteses), 2 (unicaudal ou bicaudal), 8 (erros I e II e qual é mais grave) e 13 (a simulação confirmou o que o grupo esperava?). A resposta à 13 compara a seção 5 com os resultados de G3 e G4.

## 7. Registro e adendos

**Informações já vistas antes de escrever a expectativa.** Para ser transparente sobre o que o grupo já sabia:

- Durante a sondagem do protocolo de coleta (03/11/2026) foram vistas as medianas de tempo até o merge de PRs reais: cerca de 21 h com revisão do Copilot em até 1 h e 4,5 h sem revisão (100 PRs mais recentes, amostra de teste). A expectativa sobre os dados reais acima parte disso.
- Para medir o tempo de execução foi rodado **uma única célula** de simulação (lognormal com σ(log) = 1, n = 30 por grupo, δ = 0, 10.000 repetições), que mostrou erro tipo I de cerca de 3,7% para o Welch e 4,7% para o Mann-Whitney. Nenhuma outra simulação foi rodada. A expectativa para C1 vem da teoria acima, mas o "possivelmente um pouco abaixo" do Welch deve ser lido sabendo disso; a simulação final, com os parâmetros calibrados, é o que vale.

**Adendos.** Nenhum até o momento. Qualquer adendo entra aqui com data e motivo, sem alterar as seções 1 a 6.
