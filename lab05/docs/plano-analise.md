# Lab05 — Variáveis, métricas, escalas e plano de análise

Plano de análise do Lab05, escrito **antes da coleta completa**: as variáveis com a sua classificação, as escalas e as estatísticas permitidas, o teste e o tamanho de efeito de cada pergunta, a correção para várias comparações, o que conta como diferença relevante na prática e as armadilhas de medição. As perguntas, as hipóteses e a expectativa estão em [cenario.md](cenario.md); o software e as versões, em [software.md](software.md); a classificação do estudo, em [categorias.md](categorias.md). Documento da Issue S01-05.

> **Este plano não muda depois de ver resultados.** O piloto (S01-09) serve para **testá-lo** (as regras da seção 5 são aplicadas a ele) e para estimar o número de repetições. Qualquer correção entra como adendo datado na seção 9, sem apagar o texto original, e antes do primeiro commit com dados da coleta completa. Os dados do piloto **não entram** na análise final.

Siglas: GQM (*Goal, Question, Metric*); IC (intervalo de confiança); IQR (*Interquartile Range*); CV (coeficiente de variação); ANOVA (*Analysis of Variance*); ART (*Aligned Rank Transform*); ops/s (operações por segundo); p50 e p99 (percentis 50 e 99 da latência).

## 1. Unidade de análise e interface congelada

A unidade de análise é **uma execução** do *benchmark* (um contêiner novo, uma combinação de servidor, `io_threads` e carga, uma linha do CSV). Cada métrica é um número por execução; as execuções de uma mesma combinação são as repetições.

A análise usa só estas colunas do CSV bruto (S01-07). Os nomes são a interface congelada com o executor e o dashboard.

| Coluna | Papel | Tipo | Valores / unidade |
|---|---|---|---|
| `servidor` | Fator principal | Texto | `redis`, `valkey` |
| `io_threads` | Fator secundário | Inteiro | `1`, `4` |
| `carga` | Bloco | Texto | `set`, `get`, `misto` |
| `ops_s` | Resposta (Q1, Q3) | Real | ops/s |
| `lat_p50_ms` | Resposta descritiva complementar (Q2) | Real | ms |
| `lat_p99_ms` | Resposta (Q2, Q3) | Real | ms |
| `memoria_bytes` | Resposta (Q4) | Inteiro | bytes |

Outras colunas do CSV (repetição, ordem de execução, registro do ambiente) não entram nos testes, mas a ordem de execução é usada na checagem de deriva da seção 7. Se a S01-07 mudar um nome acima, este plano e `testes.py` mudam juntos.

## 2. Classificação das variáveis

Entidade, atributo interno ou externo, medida direta ou derivada e escala (Fenton e Pfleeger). A **entidade** das variáveis de resposta é o **processo do servidor em execução** sob uma carga; a das variáveis independentes é a **configuração** dessa execução.

| Variável | Papel | Entidade | Atributo | Medida | Escala | Unidade |
|---|---|---|---|---|---|---|
| `servidor` | Independente (fator) | Configuração | — | Atribuída | Nominal | `redis`, `valkey` |
| `io_threads` | Independente (fator) | Configuração | — | Atribuída | Ordinal (2 níveis) | 1, 4 |
| `carga` | Bloco | Configuração | — | Atribuída | Nominal | `set`, `get`, `misto` |
| `ops_s` | Dependente | Servidor em execução | Externo (depende da carga, do cliente e da máquina) | Direta (operações concluídas ÷ tempo, reportada pelo cliente) | Razão | ops/s |
| `lat_p50_ms` | Dependente (descritiva) | Servidor em execução | Externo | **Derivada** (percentil do histograma do cliente) | Razão | ms |
| `lat_p99_ms` | Dependente | Servidor em execução | Externo | **Derivada** (percentil do histograma do cliente) | Razão | ms |
| `memoria_bytes` | Dependente | Servidor com o conjunto de chaves carregado | Interno (propriedade do processo, medida nele mesmo) | Direta (`INFO memory`, `used_memory`) | Razão | bytes |

Observações:

- `io_threads` tem só dois níveis, 1 e 4, e o estudo **não extrapola** para 2 ou 8. Tratá-lo como ordinal ou como razão dá o mesmo resultado com dois níveis; ele entra nos modelos como fator de dois níveis, e não como covariável contínua.
- Todas as respostas têm zero absoluto e razões com sentido (o dobro de ops/s é o dobro), por isso são de razão. Isso permite a **razão de medianas** como tamanho de efeito e a escala logarítmica da Q3.
- A `lat_p99_ms` é derivada do histograma do cliente de carga, e não medida pelo servidor: ver a armadilha 3 da seção 8.

## 3. Estatísticas permitidas por escala

| Escala | Variáveis | Descritiva permitida | Inferência permitida | Não permitido |
|---|---|---|---|---|
| Nominal | `servidor`, `carga` | Contagem, moda | Definem os grupos e os blocos; nenhuma ordem ou distância entre os níveis | Média, mediana, ordenar `redis` e `valkey` como se um fosse "maior" |
| Ordinal | `io_threads` | Contagem, mediana do nível | Comparação entre os 2 níveis, por postos ou por modelo de dois fatores | Interpolar entre 1 e 4 (por exemplo, "2 *threads* dá a média") |
| Razão | `ops_s`, `lat_p50_ms`, `lat_p99_ms`, `memoria_bytes` | Mediana, IQR, média, desvio-padrão, **CV**, razão entre medianas, média geométrica | Testes paramétricos e por postos, tamanho de efeito, razões, escala logarítmica | — |

O CV (desvio-padrão ÷ média) só tem sentido em escala de razão, e é por isso que ele aparece na descritiva destas quatro variáveis e não nas demais.

## 4. Descritiva

Por **combinação** (servidor × `io_threads` × carga) e por métrica: `n`, **mediana**, **IQR** (Q3 − Q1) e **CV**. A mediana e o IQR são o resumo principal, porque a latência e a vazão tendem a ser assimétricas; a média e o desvio-padrão entram como apoio ao Welch. O CV de cada combinação também mede o **ruído do ambiente**: no piloto, um CV alto (acima de 10% é o alerta) sugere ruído da máquina e indica que o número de repetições precisa aumentar. É um alerta, não um critério de exclusão.

Sem remoção de *outliers* por valor. Uma execução só sai da análise se falhar na validação da S01-08 (por exemplo, erros do cliente, servidor reiniciado no meio, versão errada), e nesse caso ela é **repetida**, e não descartada em silêncio.

## 5. Testes e tamanho de efeito por pergunta

Todos os testes são **bicaudais**, com α = 0,05 (ver [cenario.md](cenario.md), seção 5). A comparação das Q1, Q2 e Q4 é feita **dentro de cada combinação de carga e `io_threads`**: 6 comparações Redis × Valkey por pergunta (3 cargas × 2 níveis de `io_threads`). O código vem de `lab04/lab04/testes.py` (Welch, Mann-Whitney, g de Hedges, delta de Cliff e razão de medianas), copiado para `lab05/testes.py`, com `a` = `valkey` e `b` = `redis`; as razões e os tamanhos de efeito são, portanto, **Valkey em relação ao Redis**.

### 5.1 Regra de escolha do teste principal

Welch e Mann-Whitney testam coisas diferentes (médias × postos, ver [cenario.md](cenario.md), seção 4). Para não escolher o teste depois de ver o p-valor, o **teste principal de cada métrica** é decidido **uma vez, no piloto**, e registrado antes da coleta completa:

1. Por métrica, juntar os resíduos de todas as combinações do piloto (cada observação menos a mediana da sua combinação).
2. Se o teste de Shapiro-Wilk **não rejeita** a normalidade desses resíduos (p ≥ 0,05), a assimetria está entre −1 e 1 e o histograma e o gráfico quantil-quantil não mostram bimodalidade, o principal é o **t de Welch** (compara médias).
3. Caso contrário (assimetria forte, cauda pesada ou bimodalidade), o principal é o **Mann-Whitney** (compara postos), com a **razão de medianas** como medida de efeito de destaque.
4. O outro teste é **sempre calculado e reportado** como análise de sensibilidade (como no Lab04), mas **não entra na correção de Holm**. Se os dois discordarem na decisão, a célula é marcada na tabela.

Expectativa (a confirmar no piloto, sem ser regra): a `lat_p99_ms` deve ser assimétrica à direita e cair no Mann-Whitney; a `ops_s` deve ser mais simétrica.

### 5.2 Teste e efeito por pergunta

| Pergunta | Métrica | Comparação | Teste principal | Tamanho de efeito | Justificativa |
|---|---|---|---|---|---|
| Q1 | `ops_s` | Valkey × Redis, em cada uma das 6 combinações | Pela regra 5.1 (Welch ou Mann-Whitney) | g de Hedges (par do Welch), delta de Cliff (par do Mann-Whitney) e **razão de medianas com IC de 95% por *bootstrap*** | Duas amostras independentes; o efeito de interesse é relativo (5%), e a razão de medianas o expressa diretamente |
| Q2 | `lat_p99_ms` | Idem; `lat_p50_ms` só descritiva | Pela regra 5.1 (esperado: Mann-Whitney) | Idem | A cauda é assimétrica; a razão de medianas não é afetada por *outliers* |
| Q3 | `ops_s` e `lat_p99_ms` | **Interação** servidor × `io_threads`, dentro de cada carga | ANOVA de dois fatores sobre o **logaritmo** da métrica, termo de interação; alternativa não paramétrica: **ART-ANOVA** (*Aligned Rank Transform*) | **Razão das razões** R_valkey ÷ R_redis, com IC de 95% por *bootstrap*; η² parcial da interação | Em escala logarítmica a razão vira diferença, e a interação vira o contraste "diferença de diferenças" (ver [cenario.md](cenario.md), seção 4) |
| Q4 | `memoria_bytes` | Valkey × Redis, em cada uma das 6 combinações | Pela regra 5.1 | g de Hedges, delta de Cliff e razão de medianas com IC por *bootstrap* | Mesma estrutura da Q1 |

Detalhes:

- **Q3.** A ANOVA de dois fatores (servidor × `io_threads`) é ajustada **por carga**, no logaritmo natural da métrica, e o que se testa é o termo de interação. Os efeitos principais são reportados, mas a pergunta só se responde pela interação. Os pressupostos (resíduos aproximadamente normais, variâncias semelhantes entre as 4 células) são conferidos no piloto com Shapiro-Wilk, Levene e o gráfico quantil-quantil; se falharem, o teste principal da Q3 passa a ser a ART-ANOVA, **decisão tomada uma vez por métrica**, como em 5.1. A razão das razões é R = (mediana valkey 4 ÷ mediana valkey 1) ÷ (mediana redis 4 ÷ mediana redis 1); R = 1 significa ausência de interação.
- **Bootstrap.** Percentil, 10.000 reamostragens com reposição, **dentro de cada grupo** (as amostras são independentes), IC de 95%, semente global de `config.yaml` (`semente: 42`). Na razão das razões reamostram-se as 4 células independentemente.
- **Magnitude.** Os limites do Lab04: |g| < 0,2 negligível, < 0,5 pequeno, < 0,8 médio, senão grande; |δ| < 0,147 negligível, < 0,33 pequeno, < 0,474 médio, senão grande. A magnitude **descreve** o efeito; a relevância prática vem da seção 6.
- **Variância muito diferente entre servidores.** O Welch continua válido sem variâncias iguais. Registrar a razão entre os desvios-padrão (e o teste de Levene) na tabela, sem trocar de teste por causa disso.
- **Distribuição muito assimétrica ou bimodal no piloto.** Pela regra 5.1, o Mann-Whitney e a razão de medianas passam a ser o principal. Se a bimodalidade vier de dois regimes (por exemplo, execuções com e sem deriva térmica), investigar a causa no piloto antes da coleta, porque a razão de medianas esconde dois regimes.
- **Variância zero.** A `memoria_bytes` com o mesmo conjunto de chaves pode ser quase constante. Se a variância for zero nos dois grupos, o Welch sai NaN (comportamento do `testes.py`) e o g é indefinido; o Mann-Whitney, com todos os valores empatados em cada grupo, tampouco discrimina. Nesse caso a comparação é **descritiva**: razão de medianas, e a decisão de relevância usa o valor observado (a medida é determinística, não há incerteza amostral a quantificar). A célula é marcada como "determinística".

## 6. Várias comparações, α e diferença relevante na prática

**Nível de significância.** α = 0,05, bicaudal.

**Correção de Holm.** São 6 comparações por pergunta nas Q1, Q2 e Q4, e 3 (uma por carga) por métrica na Q3. Cada **pergunta** é uma **família** de hipóteses: a correção de Holm-Bonferroni é aplicada aos p-valores do **teste principal** dentro da família (e não ao teste de sensibilidade), e a decisão é tomada com o p ajustado. O grupo responde a quatro perguntas distintas; corrigir todas as comparações juntas (cerca de 24) aumentaria muito o erro tipo II sem relação com o risco que a Q1, por exemplo, assume por conta da Q4. O erro tipo I continua sendo o mais grave (ver [cenario.md](cenario.md), seção 6), por isso a correção é dentro de cada família e **sempre** aplicada.

**Diferença relevante na prática: 5%.** Fixada **antes da coleta**: uma diferença só é relevante se a **razão de medianas** (Valkey ÷ Redis) estiver a 5% ou mais de 1, isto é, fora de [0,95; 1,05]. Combinando significância e relevância, cada comparação cai em uma de quatro situações, lidas no p ajustado de Holm e no **IC de 95% da razão de medianas**:

| Situação | Condição | Leitura |
|---|---|---|
| **Diferença relevante** | p ajustado < 0,05 **e** IC da razão inteiro fora de [0,95; 1,05] | O servidor difere e a diferença importa na prática |
| **Diferença pequena demais** | p ajustado < 0,05 **e** IC da razão dentro de [0,95; 1,05] | Existe, mas é menor que o limiar prático |
| **Equivalência prática (empate técnico)** | IC da razão **inteiro** dentro de [0,95; 1,05] | Afirma-se "empate técnico" (como na Q1 com 1 *thread*, em [cenario.md](cenario.md), seção 7); **não rejeitar H₀ sozinho não basta** |
| **Inconclusivo** | Os demais casos (IC cruza 0,95 ou 1,05) | Faltam repetições ou o ruído é grande |

Para a Q3, o limiar é o mesmo na razão das razões: a interação é relevante se R estiver fora de [0,95; 1,05].

**Repetições.** O número de repetições (inicialmente 30 por combinação, [cenario.md](cenario.md), seção 3) é revisto no piloto para que o IC da razão de medianas tenha largura compatível com a margem de 5%. Esse cálculo é feito pelo `poder.py`.

## 7. Pressupostos e checagens do piloto

| Pressuposto | Como é garantido | Checagem no piloto |
|---|---|---|
| Independência entre execuções | Contêiner novo a cada execução e ordem aleatorizada com a semente global | Gráfico da métrica contra a ordem de execução (deriva ou autocorrelação) |
| Amostras comparáveis | Mesma máquina, mesma configuração, mesmo cliente, núcleos separados para servidor e cliente | Registro do ambiente em cada execução (S01-07) |
| Pressupostos do Welch e da ANOVA | Não assumidos: a regra 5.1 decide, e o Mann-Whitney e a ART são as alternativas | Shapiro-Wilk, Levene, histograma e quantil-quantil |
| Aquecimento fora da medida | Fase de aquecimento descartada (definida no protocolo, S01-06) | Comparar a primeira e a última parte da execução |
| Cliente não é o gargalo | Cliente com tantas *threads* quanto o servidor (recomendação das duas documentações) | Uso de CPU do cliente abaixo da saturação |

## 8. Armadilhas de medição e como o estudo as evita

1. **Lei de Goodhart (otimizar um número o torna ruim como medida).** Se o estudo olhasse só `ops_s`, uma configuração que ganha vazão à custa de uma latência de cauda pior pareceria melhor. **Como se evita:** nenhuma conclusão sai de uma métrica sozinha; Q1 e Q2 são sempre lidas juntas, e o grupo **não cria um índice composto** que some vazão e latência.
2. **Falácia de McNamara (decidir só pelo que é fácil de medir).** O que não é medido some da conclusão: persistência em disco, durabilidade, latência acima do p99 (p99,9), custo de operação, comportamento com falhas, outras cargas e outros tamanhos de valor. **Como se evita:** a vazão, o p50 e o p99 vêm com a memória, e o relatório final lista, nas ameaças à validade, o que ficou **fora** da medida. O resultado vale para as cargas e o ambiente do estudo, não para "o desempenho" do servidor.
3. **Medida direta × derivada.** `ops_s` e `memoria_bytes` são medidas diretas; a `lat_p99_ms` é **derivada** do histograma do cliente (percentil sobre as latências observadas pelo cliente, não pelo servidor). Ela depende da resolução do histograma e inclui a rede local e a fila do cliente. **Como se evita:** o p99 é calculado **por execução** e as execuções são comparadas entre si; **não se tira a média dos p99** das execuções para reportar um "p99 do servidor" (percentis não se compõem por média). O resumo é a mediana dos p99 por combinação.
4. **Omissão coordenada.** Num cliente de laço fechado (50 clientes, *pipeline* 1), quando o servidor trava, o cliente deixa de enviar requisições, e as latências que seriam altas não são registradas; o p99 sai otimista. **Como se evita:** o mesmo cliente e a mesma carga para os dois servidores, de modo que o viés é comum; a limitação é registrada, e o p99 vale como comparação **relativa** entre servidores, não como valor absoluto.
5. **Resolução da latência e empates.** Em *localhost*, o p50 pode ficar abaixo de 1 ms, perto da resolução do cliente, o que gera valores repetidos. **Como se evita:** o `testes.py` já trata empates (Mann-Whitney assintótico com empates); a resolução do cliente é conferida no piloto.
6. **Memória: `used_memory` × RSS.** O `used_memory` é o que o alocador do servidor contabiliza; o RSS inclui fragmentação e diferenças do alocador, e pode mudar entre os servidores. **Como se evita:** a métrica do estudo é a `used_memory` (medida direta, igual nos dois), lida **depois de carregar o mesmo conjunto de chaves** e antes da carga; o RSS é reportado como complemento e a diferença entre as duas leituras é registrada.
7. **Cliente ou máquina como gargalo.** Se o cliente satura, o `ops_s` mede o cliente, e não o servidor, e esconde o efeito das *threads* de I/O. **Como se evita:** cliente com *threads* proporcionais, núcleos separados e verificação no piloto (seção 7).
8. **Múltiplas comparações e liberdade do analista.** Testar muitas combinações e relatar só as significativas, ou escolher o teste pelo p-valor, infla o erro tipo I. **Como se evita:** este plano congela, antes da coleta, as perguntas, as famílias, o teste principal por regra, o limiar de 5% e a correção de Holm, e o piloto não entra na análise final.
9. **Pseudorreplicação.** Várias medidas do mesmo contêiner não são repetições independentes. **Como se evita:** a unidade de análise é a execução e cada execução usa um contêiner novo.

## 9. Registro e adendos

**Pendências a confirmar (antes do merge).**

- Alinhar os nomes e os tipos das colunas da seção 1 ao CSV definido na S01-07.
- Confirmar com o grupo duas decisões deste plano: a correção de Holm **por pergunta** (seção 6) e o limiar de 5% sobre a razão de medianas também para a memória.
- A ANOVA de dois fatores e a ART-ANOVA pedem um pacote que ainda não está no `requirements.txt` (por exemplo, `statsmodels` para a ANOVA). Definir na issue que implementar a análise (S01-09), com o tratamento dos pressupostos e da ART.

**Adendos.** Nenhum até o momento. Qualquer adendo entra aqui com data e motivo, sem alterar as seções 1 a 8.
