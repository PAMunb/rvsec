# Fechamento das lacunas da análise adversarial — mensagens JavaMOP

**Data:** 2026-08-15
**Natureza:** continuação da análise adversarial. **Nada foi implementado.** Toda a investigação foi
somente-leitura; nenhum emulador foi tocado.
**O que este documento faz:** fecha as três lacunas que a análise anterior registrou como não
resolvidas (`..._FINAL_analise_handoff_prompt.md` §4), acrescenta seis achados que nenhum dos dois
documentos anteriores contém, corrige três pontos da própria análise anterior, e reúne a evidência
que faltava para as quatro decisões de pesquisador — **todas tomadas ao final desta sessão e
registradas em §6**.

**Alvo da linhagem:** `20260815_javamop_mensagens_FINAL.md` (o documento de design, 521 linhas) e
`20260815_javamop_mensagens_FINAL_analise.md` (a análise adversarial, 645 linhas).

**Método.** Cinco agentes de verificação com recortes disjuntos — auditoria do §4 contra os quatro
relatórios originais; limite de payload do logcat contra fontes do AOSP; matriz de consumidores;
aridade `args()` e estado do Estudo 03; conformidade OpenSpec — mais medições próprias sobre os dois
datasets, sobre as tabelas de transição dos monitores compilados e sobre as `.mop` dos dois
conjuntos. **Toda conclusão de agente que sustenta decisão foi medida diretamente antes de
entrar aqui**; onde a medição corrigiu o agente, está registrado em §5.

---

## 1. Veredito

A análise anterior concluía que o documento alvo estava pronto para virar issues *depois* de três
correções estruturais. **Essa conclusão se mantém, e o conteúdo das correções mudou.**

O fechamento das lacunas produziu dois resultados de sinal oposto. **A favor do documento alvo:** a
consolidação da §4 é melhor do que se supunha. Lendo os quatro relatórios inteiros — 581 itens —
**77,5 % foram transportados**, muitos com `arquivo:linha` literais que só uma leitura linha a linha
produz. A alegação "without filtering" (`FINAL:25`) é falsa, mas a perda é limitada: 10,5 % ausentes,
12,0 % carregados com perda. **Contra:** a perda não é aleatória. **Some sistematicamente o que a
validação externa mediu por conta própria, e sobrevive o que ela corrigiu** — e as medições perdidas
são justamente o insumo que dimensiona as mudanças C-*. O caso mais grave é o **default de D-F, que
prescreve o classificador cuja saída medida contradiz os números publicados** (§2.1, item 1).

Os dois bloqueios que a análise anterior deu como abertos **estão destravados**: D-C tem resposta
factual (as corridas finais do Estudo 03 não começaram) e o orçamento residual que a §2.3 declarava
impossível **é parcialmente produzível hoje, offline** — 30,5 % do volume mudo são registros que não
deveriam existir, mensuráveis por pareamento de sítios sem corrida de calibração.

E o custo de duas mudanças subiu por evidência nova: a **matriz de consumidores** da §7.3 erra por
três formatos de `errors.csv` vivos, um congelado por sha256 sob a auditoria e já ilegível pelo parser
de produção (§3.6); e a **regra de reparo de C-1a**, como escrita, apagaria 66,6 % das linhas legíveis
do corpus (§3.2).

## 2. As três lacunas do handoff, fechadas

### 2.1 Lacuna 1 — o §4 contra os quatro originais: **fechada por leitura integral; a lista de extração agora existe**

Esta é a lacuna que o handoff classificava como "a correção mais cara e a que mais afeta a
confiabilidade do §4". Ela foi fechada do único jeito que fecha: **lendo os quatro relatórios
inteiros**, item a item, e casando cada item contra o `FINAL.md` lido inteiro. O artefato que nunca
existiu — a lista de extração — está agora em `docs/20260815_javamop_extracao/`, um arquivo por
relatório, com `arquivo:linha` da fonte e o destino no FINAL para cada item.

#### Duas retratações antes dos números

**Primeira.** Uma versão anterior desta seção afirmou que "111 dos 225 IDs do §4 não podem ter
referente". **Falso, e retirado.** O número vinha de um denominador contado em apenas três blocos por
relatório (116 itens). A leitura integral encontra **581 itens** nas quatro fontes — cinco vezes
mais. Os IDs de índice alto apontam para tabelas de verificação que aquela contagem ignorou; os que
testei (`c-A39`→`claude:207`, `c-A42`→`:253`, `c-A43`→`:198`, `c-B18`→`:272`, `c-C35`→`:377`) todos
resolvem para conteúdo real. O agente do `gpt5_codex` chegou à mesma conclusão de forma independente:
*"nenhum ID alto é fantasma"* — as classes se alimentam de todo o §3 do relatório, não só das §4/§5.
Retirada junto a acusação de que `FINAL:99-102` mente: a frase diz "the IDs used inside each report's
**extraction**", os IDs da passagem de extração, e lida assim é exata.

**Segunda.** Afirmei que o falso negativo do `KeyGeneratorSpec` (`gemini:208`, item `B04`)
"desapareceu, 0 ocorrências". **Falso.** Ele sobrevive como o token opaco `D11` na lista de reparos do
C-4 (`FINAL:359`), porque `D11` no plano original (`20260815_javamop_mensagens.md:923`) **é** esse
defeito: *"`KeyGeneratorSpec.mop:47`, `MessageDigestSpec.mop:55` — Condition tests
`currentAlgorithmInstance`, not `alg` → false negative"*. O mesmo vale para o `B03` (KPG NPE), que
aparece em `FINAL:359,422,466`. Eu greppei `currentAlgorithmInstance` e "false negative", ambos
ausentes, e concluí sumiço. **O defeito real é mais estreito e continua valendo:** quem lê o FINAL vê
`D11` numa lista e não tem como saber que é um falso negativo, em que arquivo, nem que o gemini o
confirmou por inspeção direta — e no §4 ele é atribuído via `c-C34` com status `U` e a glosa *"audit
items cited by neither doc"*, quando o gemini o citou.

#### O resultado da leitura integral

| relatório | itens enumerados | carregados | parciais | ausentes |
|---|---|---|---|---|
| `gpt5_codex` (480 linhas) | 202 | 166 | 16 | 20 |
| `claude_fable5` (751 linhas) | 193 | 148 | 23 | 22 |
| `deepseek_v4_flash` (237 linhas) | 113 | 84 | 16 | 13 |
| `gemini36flash` (286 linhas) | 73 | 52 | 15 | 6 |
| **total** | **581** | **450 (77,5 %)** | **70 (12,0 %)** | **61 (10,5 %)** |

**Veredito sobre o "without filtering" de `FINAL:25`: é falso, mas a perda é limitada e mensurável.**
Três de cada quatro itens chegaram. Um em dez sumiu. Um em oito chegou perdendo a parte que o
distinguia. Não é uma consolidação descuidada — o agente do `codex` registra que as dez anomalias sem
rótulo daquele relatório chegaram **todas**, sete delas com `arquivo:linha` literais, *"o que só é
possível com leitura linha a linha"*. É uma consolidação boa com um viés sistemático, descrito
abaixo.

#### O viés: sobrevivem as refutações, somem as medições próprias

O padrão que atravessa os quatro relatórios é que **o que a validação externa mediu por conta própria
some com muito mais frequência do que o que ela corrigiu**. Nove das treze ausências do deepseek são
números que ele mediu; seis das vinte do codex idem. O efeito colateral está registrado pelo agente
do deepseek: *"o FINAL só carregou as [medições] refutadas, enviesando F9 para 'o plano errou tudo'"*.

Isso importa porque as medições perdidas são precisamente o insumo que as mudanças C-* precisam para
serem dimensionadas.

#### As doze ausências que mudam trabalho

Agrupadas por qual mudança elas afetam. Todas com a linha da fonte, todas confirmadas por busca de
duas formulações.

**Contaminam D-F e o C-0:**

1. **O default de D-F prescreve o classificador cuja saída medida contradiz os números publicados.**
   `FINAL:296` recomenda *"pairing + full-package own-code + explicit vendor list incl. `okio.`"*.
   `deepseek:76` mediu exatamente essas variantes: lista do plano = 78,49 %; **+`okio` = 82,67 %**
   (não 85,44 %); 88,01 % só reproduz com chave de pacote de **2 segmentos**, e **pacote completo =
   89,82 %**. Dos seis números, **o único que aparece no FINAL é o 85,44 %** — o único que a fonte diz
   não reproduzir. Como o D-F manda registrar as definições *antes* de publicar número e o C-0
   entrega o classificador como código, C-0 implementado assim produzirá 82,67 %/89,82 %, e nada
   avisa da descontinuidade.
2. **`okhttp3.Platform` = 35.828 linhas = 36,93 %** do dataset (`deepseek:78`), o maior estrato único
   de terceiros — o alicerce empírico de toda a discussão de atribuição. Ausente.
3. **A fatia `unknown` é plana entre ferramentas (71,2–74,0 %) e entre timeouts (72,5–73,1 %)**
   (`claude:173-176`), logo é propriedade das specs e do pipeline, não do driver. É a refutação medida
   da hipótese de dependência de ferramenta — a que blinda a comparação APE × APE-RV. Ausente.

**Dimensionam C-3 e o gate G-6:**

4. **A quebra do vocabulário de mensagens por `ErrorType`, medida de forma independente por dois
   relatórios** (`gemini:103-107`, `deepseek:71`): `InvalidSequenceOfMethodCalls` 70.760 linhas /
   **1 mensagem**; `UnsafeAlgorithm` 15.444 / **12 mensagens**; `UnsafeProtocol` 8.802 / 3;
   `InvalidKeyStoreType` 2.005 / 1; `InvalidKeySize` 7 / 2. O FINAL guarda só o agregado "19 distinct
   messages". **É o inventário que diz onde vive a diversidade textual restante — exatamente o que a
   `codes.csv` do C-3 precisa para ser dimensionada.** Ausente nos dois.
5. **O censo de mensagens degeneradas** (`claude:168`): `found .` **8.843** em 5 specs; falta de
   espaço 2.005 (`expecting one ofJCEKS,…`); reticências 109; inconsistência de chaves 9 formas com
   `{}` × 7 sem; `SHA-1`/`SHA1`/`SHA` 2.340. **É a linha de base do portão G-6 e a evidência
   quantitativa do problema que o documento existe para resolver.** Ausente.
6. **`logcat_parser.py:306` casa o Formato 1 por fim de string exato** (`gemini:210`). O C-3 reescreve
   o texto de toda mensagem de todo `@fail`; o parser passa a jogar essas linhas no fallback de
   "malformado". **É o acoplamento direto entre C-3 e o parser que o C-1 mexe em paralelo, e a perda
   seria silenciosa.** Ausente.

**Dimensionam e restringem C-4:**

7. **Os tetos de custo de geração** (`claude:341-349`): 17 eventos = 53 s e 3,3 GB; **18 eventos =
   StackOverflow**; `CipherSpec` foi re-orçada de 17 para 14. Qualquer reparo do C-4 que **adicione**
   eventos esbarra nisso — e é o mesmo teto que o `INV-INS-115` da gh101 codifica. Ausente.
8. **`CipherSpec.mop:72` lê `Property.GENERATED_PRIVATE_KEY`, que nenhuma spec do conjunto escreve**
   (`deepseek:105`; verificado aqui: zero produtores no `jca`). Aresta morta concreta do grafo de
   predicados que o C-5 promete reconectar e não lista. Ausente.
9. **`ViolationRecorder.java:87-105`** (`gemini:74`): o guarda `if ((fileName != null && className
   != null) && …)` avalia falso quando `fileName` é nulo e **desliga o filtro de exclusão de quadros
   inteiro**, não pula um quadro. Compõe-se com a perda de debug info: sem ela, `fileName` é nulo, o
   filtro morre, e o topo de pilha "relevante" — que vira o campo `location` da identidade do
   `ErrorSummary` — pode ser um quadro do próprio runtime. A lista de non-goals do FINAL nomeia
   WS-5.1/5.2/5.8 e pula justamente a WS-5.3. Ausente.
10. **A assimetria de caixa em `CipherTransformationUtil.java:44,45,46,65`** (`gemini:81`, D16):
    `equals` num ramo, `toUpperCase` noutro, dentro da mesma função que decide se uma transformação é
    insegura — e portanto decide `ErrorType` e mensagem. A lista de reparos do C-4 vai de `D11` a
    `D18–D20` e `D35–D40`, pulando D15/D16. Ausente.

**Restringem a decisão D-A, já tomada, e a D-B, ainda pendente:**

11. **A opção "sucessor do `jca`" cria um terceiro livro de conformidade** e colide com a disciplina
    de derivação dos `INV-INS-112/113` (`claude:359-367`). É o custo processual da opção que acabou de
    ser escolhida, e o FINAL o omitiu ao recomendá-la por padrão. Ausente.
12. **5.891 de 6.048 linhas de `UnsafeAlgorithm` nomeiam algoritmos que a api30 não proíbe**
    (`claude:249`, carregado parcialmente com a medição removida) — **97 % da categoria desapareceria
    sob o oráculo api30**. É o número que dá consequência concreta a D-B, a próxima decisão pendente.
    Perdido na compressão.

#### Dois defeitos de transporte, não de conteúdo

13. **A compressão de linhas apaga a segunda confirmação independente.** A linha `g-C1..C17`
    (`FINAL:183`) atribui **um status e uma glosa a 20 conceitos**. Exame um a um: 10 carregados, 8
    parciais, 2 sumidos (D16 e L5f/D42). E o status `R` — "já verificado no review" — é falso para
    oito deles, que o gemini verificou de forma independente abrindo cada arquivo, com veredito
    `CONFIRMED`. O destino `—` também é falso: D07–D09, D10, D11, D18, D20 e D03 aterrissam no C-4.
14. **Os quatro relatórios pedem para não serem citados como certificação, e são.** `codex:7-13` e
    `:478-480` declaram-se de primeiro estágio, não citáveis como certificação enquanto os oito itens
    da sua §8 não forem feitos; `codex:75` diz que concordância entre passes **nunca** vale como
    prova, *"as citações é que valem"*; `claude:681-684` registra o risco de "mesma classe de agente".
    O FINAL faz o oposto, creditando F1/F7/F9/F10 a "ext. 1–4" e marcando dezenas de linhas como `R`
    ou `V+` sem qualificação. Todas essas ressalvas estão ausentes.

#### Dois defeitos substantivos que já estavam registrados e sobrevivem intactos

15. **`FINAL:114` transforma uma refutação em concordância** — a linha do `okio.`/85,44 %, detalhada
    no item 1 acima. Verificada por texto literal contra `deepseek:166`.
16. **O falso negativo do `KeyGeneratorSpec` chega opaco** — item da segunda retratação acima.
    Corroboração medida aqui: `KeyGeneratorSpec` emite **zero linhas** no comp162, que é a assinatura
    observável de um falso negativo.

#### Dois achados menores, e um defeito que aparece nos dois lados

17. **`c-A16` tem ponteiro morto:** manda para §7.2, que não trata do assunto.
18. **`D18` e `D20` são, eles mesmos, defeitos de mensagem — o assunto do documento — e a §7.1 não os
    discute.** Verificados aqui no conjunto congelado: `jca/PBEKeySpecSpec.mop:48-50` testa
    `iterationCount < 10000` e a mensagem diz *"third argument should be >= 1000"* — contradiz a
    própria checagem por um fator de 10, e a mensagem aparece **52 vezes** no comp162;
    `jca/PBEParameterSpecSpec.mop:49` testa restrição de parâmetro e reporta
    `ErrorType.UnsafeAlgorithm`, com a mesma mentira do fator 10.
19. **O precedente interno mais forte do repo está em ambos e some nos dois.** `deepseek:107` aponta o
    comentário verbatim dos autores em `jca/MessageDigestSpec.mop:48-51`: *"We no longer throw errors
    after unsafe instantiation events… Not throwing here eliminates the InvalidSequenceOfMethodCalls
    false positive in bench02.BrokenHashABPSCase1"*. Os autores já diagnosticaram e corrigiram **uma**
    instância do mecanismo dos sítios gêmeos (§3.1), e documentaram o padrão dentro do `jca`. É a
    evidência mais forte disponível de que a classe inteira é reparável do lado da spec. Ausente.

#### Como fechar

A lista de extração existe agora (`docs/20260815_javamop_extracao/`, quatro arquivos). O que falta é
mecânico: substituir a coluna `Item(s)` do §4 por citações `sigla:linha` resolvidas contra esses
arquivos, incorporar as doze ausências que mudam trabalho, e corrigir `FINAL:114` e a linha
`g-C1..C17`. A alegação "without filtering" deve ser trocada por um número honesto — 77,5 % dos itens
transportados, com a lista dos 61 ausentes em apêndice.

#### Nota metodológica

Duas afirmações minhas caíram nesta seção, ambas por eu ter aceitado uma contagem de subagente sem
medir o **denominador**. O aprendizado §7.1 do handoff anterior ("meça antes de aceitar um número,
mesmo de um verificador") precisa da emenda: **verificar uma contagem exige verificar o universo
sobre o qual ela é feita, não só o valor contado.** E a única coisa que fechou de verdade esta lacuna
foi leitura integral — nenhuma amostragem, por mais bem escolhida, teria produzido os 581 itens.

### 2.2 Lacuna 2 — o limite de ~4.068 B do logcat: **fechada; o número está certo, a derivação está errada**

`LOGGER_ENTRY_MAX_PAYLOAD` = **4068 bytes**, verificado literalmente em quatro pontos do AOSP
(`system/logging/liblog/include/log/log.h` em `main`; `log_read.h` em `android-11.0.0_r48` = API 30 e
`android-8.0.0_r36`; `logger.h` em `android-7.0.0_r36`). O valor **4076** é o do Android ≤ 5.1
(`android-5.1.1_r38`), quando o `struct logger_entry` tinha 20 B em vez dos 28 B atuais. O projeto
roda API 30 (`docker/android/Dockerfile:13`, `ARG API_LEVEL=30`), logo o limite é 4068.

Isso invalida a aritmética `4076 − 1 − 6 − 1 = 4068` usada para justificar o número: ela parte do
limite de uma plataforma que não é a alvo e chega ao valor certo por coincidência, contando a mesma
subtração duas vezes. **4068 já é o payload inteiro**; a decomposição real, verificada em
`liblog/logger_write.cpp` (três iovecs: 1 B de prioridade, tag+`\0`, msg+`\0`) e com a tag literal
`RVSEC` de 5 caracteres (`rvsec-logger-logcat/.../ErrorCollector.java:40`), dá **4060 B de orçamento
para `msg`**. O documento está 8 bytes otimista — irrelevante na prática, mas o número citado
confunde camadas.

**Comportamento no corte, verificado.** `android.util.Log.v` não trunca nem divide: repassa a string
inteira a `__android_log_buf_write`. O corte acontece na `liblog`, dentro do processo do app
(`logd_writer.cpp`), que **encurta o iovec corrente e segue com o `writev`** — truncagem silenciosa
da cauda, sem erro, sem descarte, sem split. Como `msg=` é o último campo do envelope proposto, um
estouro produz exatamente envelope sem aspa de fechamento e sem qualquer sinal de que houve corte.
**Requisito derivado: o parser de C-1 tem de tratar aspa não fechada como registro truncado, não
como valor válido.**

**Folga medida** sobre as 97.018 linhas do dataset de referência. A medição da análise anterior
(mediana 131 B, p99 209 B, máximo 349 B) **reproduz exatamente**, mas contava `tag + msg` sem o byte
de prioridade, sem os dois NULs e sem o campo `location` — que existe na linha real do logcat e não
existe no `errors.csv` de 10 colunas. Repondo-o, o payload real fica em mediana 155 B, p99 238 B,
máximo 366 B. Reconstruindo o **envelope proposto** registro a registro:

| | payload | % de 4068 |
|---|---|---|
| mediana | 274 B | 6,7 % |
| p99 | 391 B | 9,6 % |
| máximo observado | **696 B** | **17,1 %** |
| soma de máximos independentes (pessimista, não co-ocorre) | 974 B | 23,9 % |

**Veredito: truncamento não é risco real.** Passaria a ser apenas se `val` recebesse uma string
patológica de ~3,4 KB — e `val` vem da aplicação monitorada e **não tem teto em camada alguma**
(verificado: nem na `.mop`, nem em `ErrorDescription`, nem nos dois coletores, nem nos consumidores
Python). Um `if (val.length() > N)` no `@fail` mais o parser acima eliminam o cenário.

**O risco irmão é mais provável e não está mitigado.** Em
`rvsec-android/rvsec-logger-logcat/.../ErrorCollector.java:38-40` a chamada de escape está
**comentada** — a linha ativa é `Log.v("RVSEC", message)` cru. Um `\n` vindo de valor da aplicação
quebra a linha em duas no logcat, produzindo o registro fabricado que F7 já documenta. O coletor CSV
(`rvsec-logger-csv/.../ErrorCollector.java:42`) *aplica* o escape. Os dois defeitos ficam a três
linhas um do outro, no mesmo arquivo.

**Efeito colateral sobre a auditoria:** este número vinha de `audit/.../pilot/gama_diagnostico.md:99`
marcado `NÃO_VERIFICADO`, e a claim **GAMA-SET-05 foi adjudicada INCONCLUSIVA** com a ação pendente
*"verificar limite e adicionar guarda"* (`pilot/juiz_claims_resolvidos.csv:71`). **A metade
"verificar limite" está resolvida por este documento.**

### 2.3 Lacuna 3 — nada executado em device: **permanece aberta, por decisão**

Nenhuma conclusão deste documento vem de execução em device. Continua valendo o registro da análise
anterior: tudo vem de leitura de fonte, de artefatos gerados já existentes e de datasets já
coletados. A regra do `CLAUDE.md` sobre emuladores foi respeitada integralmente.

### 2.4 Lacunas menores

**Os três scripts sinalizados pela validação externa 4** foram reabertos (§3.6 abaixo). **A
afirmação "dexlib2 only — AspectJ enforces `args` arity"** é verdadeira como semântica da linguagem
AspectJ (`args(int, .., String)` é posicional, com aridade fixada pela ausência de `..`), mas o
documento a trata como não-medível quando **existe medição pareada em árvore**:
`experimento-comp162-ajc/consolidado/mop_diff_ajc_x_dexlib2.csv`, 115 linhas, com
**63 `ambos`, 46 `so_dexlib2`, 6 `so_ajc`** sobre 41 APKs. É evidência direta do viés de sobre-reporte
do dexlib2 que a §5.1 postula, e nenhum dos dois documentos a cita. Ressalva: a granularidade é
`(apk, spec, classe, método, tipo_erro)`, então ela mede o viés agregado, não a aridade de `args()`
isoladamente.

---

## 3. Achados que nenhum dos dois documentos contém

### 3.1 Um quarto das linhas mudas é duplicata de um relatório que já existe legível

Decompondo as 15.714 linhas `unknown` do `experimento-comp162` por sítio
`(spec, class, method, source)`:

| | sítios | linhas mudas |
|---|---|---|
| gêmeos **muda ↔ legível** (o relatório já existe legível na mesma linha) | 101 | **3.950** |
| gêmeos **muda ↔ muda** (dois `ErrorType` mudos, contagem idêntica) | 12 | **838** |
| sítios restantes, só-muda | 183 | 10.926 |

Em **98 dos 101** sítios gêmeos a razão muda:legível é exatamente 1:1, e o total de mudas em sítios
gêmeos (3.950) **iguala o total de linhas legíveis do corpus** (3.950). Os três desvios são de −2,
+1 e +1. O padrão replica no dataset de referência: dos 157 sítios mudos, **todos os 64 sítios que
emitem algo legível também emitem muda** (32.411 mudas gêmeas, 38.349 solitárias). **Não existe um
único sítio exclusivamente legível em nenhum dos dois corpora.**

O mecanismo é o de §2.1 da análise anterior, generalizado: um único evento cujo corpo emite o
relatório de valor **e** cuja transição cai no sink produz duas linhas na mesma linha de código —
uma legível, uma muda. `SSLContextSpec.init` e `MessageDigestSpec.update` são os casos de maior
volume.

**Consequência para C-0 e C-3.** A §2.3 da análise anterior conclui que C-0 não consegue produzir o
orçamento residual porque a atribuição por *evento* é impossível com os dados atuais. Isso continua
verdadeiro. Mas a atribuição por *classe de mecanismo* via pareamento de sítios **é possível hoje,
offline, sem corrida de calibração**, e já separa a maior fatia:

- **4.788 linhas (30,5 %)** são registro que **não deveria existir**. Duas classes: 3.950 em que o
  mesmo defeito já está reportado de forma legível na mesma linha, e 838 em que o mesmo sítio emite
  duas linhas mudas de `ErrorType` diferentes. Trabalho de deleção, com zero design de mensagem.
- **10.926 linhas (69,5 %)** são o resíduo a decompor entre aridade `args()`, órfãos de autômato e
  violações genuínas sem mensagem.

A segunda classe é inteiramente `IvParameterSpecSpec`: 838 linhas = 419 `InvalidSequenceOfMethodCalls`
+ 419 `UnsatisfiedConstraint`, com **contagem idêntica nos 12 sítios**. Uma única violação produz dois
registros mudos de tipos diferentes. Ela foi encontrada porque `claude_fable5:189` a nomeia como uma
das três famílias de gêmeos que **apareceram** no E3 — efeito colateral medido da gh100, cujos nove
eventos restaurados passaram a chegar ao DEX e a afundar no sink. O FINAL registra o sumiço dos
gêmeos antigos de TMF e não o aparecimento dos novos.

Decomposição por spec, com a coluna de órfãos do `jca` congelado ao lado (a informação que o
documento alvo nunca publica):

| spec | mudas | gêmeas | solitárias | eventos órfãos no `jca` | afetada pela aridade `args()` |
|---|---|---|---|---|---|
| SSLContextSpec | 2.916 | 1.464 | 1.452 | `unsafe_protocol` | — |
| SecureRandomSpec | 2.882 | 0 | 2.882 | `c3`, `g4`, `setSeed3` | sim |
| TrustManagerFactorySpec | 2.855 | 61 | 2.794 | `g3` | sim |
| MessageDigestSpec | 2.008 | 1.165 | 843 | `reset` | — |
| CipherSpec | 1.461 | 12 | 1.449 | — | — |
| KeyStoreSpec | 1.136 | 265 | 871 | — | — |
| IvParameterSpecSpec | 838 | 0 | 838 | `c3`, `c4` | — |
| SecretKeySpecSpec | 820 | 820 | 0 | `c3`, `c4` | — |
| KeyManagerFactorySpec | 296 | 0 | 296 | — | sim |
| MacSpec | 145 | 4 | 141 | — | — |
| SignatureSpec | 125 | 39 | 86 | `g3` | — |
| PBEKeySpecSpec | 118 | 118 | 0 | `f1,f2,err1..3` | — |
| KeyPairSpec | 111 | 0 | 111 | — | — |
| KeyPairGeneratorSpec | 3 | 2 | 1 | `initError` | — |
| **total** | **15.714** | **3.950** | **11.764** | 18 em 10 specs | |

(A coluna "gêmeas" acima conta apenas os pares muda↔legível; as 838 de `IvParameterSpecSpec` são
pares muda↔muda e aparecem em "solitárias".)

Três leituras imediatas: `SecretKeySpecSpec` e `PBEKeySpecSpec` são **100 % duplicação** — toda
violação delas já é reportada legivelmente e cada uma vem acompanhada de uma muda; `IvParameterSpecSpec`
é **100 % duplicação de outro tipo**, dois mudos por violação; e o volume restante é concentrado —
**60 dos 195 sítios cobrem 80 %** dele, o que dá a C-3 um alvo finito e enumerável em vez de "15.714
registros".

**Precedente interno para o reparo, achado pela leitura integral do `deepseek:107`.** Os próprios
autores já diagnosticaram e corrigiram uma instância desta classe, e documentaram o padrão dentro do
conjunto congelado — `jca/MessageDigestSpec.mop:48-51`:

> *"We no longer throw errors after unsafe instantiation events, otherwise we would throw
> InvalidSequenceOfMethodCalls in cases like (g3\* g1 | g3\* g2). Not throwing here eliminates the
> InvalidSequenceOfMethodCalls false positive in bench02.BrokenHashABPSCase1"*

É a evidência mais forte disponível de que a classe inteira é reparável do lado da spec, e nenhum dos
dois documentos anteriores a cita.

Medições de contorno, para o registro: 4 specs emitem **só** mudas (`IvParameterSpecSpec`,
`KeyManagerFactorySpec`, `KeyPairSpec`, `SecureRandomSpec`); **9 das 23 specs do `jca` não emitem
nada** no comp162 (`CipherInputStreamSpec`, `CipherOutputStreamSpec`, `DHGenParameterSpecSpec`,
`GCMParameterSpecSpec`, `HMACParameterSpecSpec`, `KeyGeneratorSpec`, `PBEParameterSpecSpec`,
`RandomStringPasswordSpec`, `SecretKeySpec`) — o que dá corpo ao item `c-C34` que o §4 marca `U`; e
o corpus inteiro tem **16 mensagens distintas** (contra 19 no dataset de referência).

### 3.2 A regra de reparo de C-1a, como escrita, apagaria dois terços do que o sistema hoje diz legivelmente

A regra proposta em `FINAL` §8/C-1a é *"drop an advice whose `args` list has no trailing `..` and
whose length ≠ `cc.paramFqns.size()`"*. A análise anterior já dizia que ela é mal-formada por cobrir
vacuamente advices sem cláusula `args()`. **Medido, o custo é muito maior do que aquele registro
sugere.**

Dos 114 after-advices com `call()` no conjunto `jca`, **79 têm `args()` e 16 têm `call()` com
parâmetros e nenhum `args()`** — comprimento 0, que nunca iguala a aridade do wrapper. Entre esses 16
estão precisamente os dois emissores dos maiores blocos legíveis do corpus:

| advice | pointcut | corpo emite | linhas legíveis no comp162 |
|---|---|---|---|
| `SSLContextSpec.init` | `call(void SSLContext.init(KeyManager[],TrustManager[],SecureRandom))`, sem `args()` | `UnsafeProtocol` | **1.466** |
| `MessageDigestSpec.update` | `call(void MessageDigest.update(..))`, sem `args()` | `UnsafeAlgorithm` | **1.163** |

**2.629 de 3.950 linhas legíveis = 66,6 %.** A regra remove as mudas e leva junto dois terços do
sinal. Os outros 14 advices na mesma condição são `MacSpec.update/f1`, `MessageDigestSpec.d2`,
`CipherSpec.wkb1/f2`, `SSLContextSpec.engine`, `KeyStoreSpec.gk1`, `SecureRandomSpec.setSeed1/genSeed/ints`,
`CipherInputStreamSpec.c1`, `CipherOutputStreamSpec.c1/w1`, `HMACParameterSpecSpec.c`.

O reparo mínimo correto tem três requisitos, todos verificáveis em código: filtrar no laço de
agrupamento (`WrapperEmitter.java:270-273`, o ponto da mesclagem da gh100, único lugar onde advice e
overload concreto coexistem); ler `ArgsPC.types()` e não `names()`, porque `names()` descarta o `..`
(`PointcutExpressionParser.java:243-246`) e faz `args(transformation, ..)` parecer aridade-1-fixa; e
**tratar ausência de cláusula `args()` como "sem restrição posicional", nunca como comprimento 0**.

Há ainda um segundo sítio que C-1a não cobre: advices `before` não passam por wrapper
(`WrapperEmitter.java:161-163`), então `KeyStore.load/store` e `SecureRandom.next1/next2` continuam
com aridade não imposta mesmo depois do reparo. Paridade real com AspectJ exige tratar também a
forma-binding em `PointcutMatcher.java:268-271`.

### 3.3 `INV-INS-109` e `INV-INS-110` estão definidos duas vezes, com significados incompatíveis

O spec principal `openspec/specs/instrumentation/spec.md` para em **INV-INS-103**. Os três
invariantes que o documento alvo invoca vivem apenas em deltas de changes ativas — e há colisão:

| ID | gh100 (`specs/instrumentation/spec.md`) | gh101 (`specs/instrumentation/spec.md`) |
|---|---|---|
| INV-INS-109 | `:63` — oráculo Layer-3 chaveado em `(apk, class, method, spec)` | `:43` — conjunto `jca` byte-idêntico + registro de divergência |
| INV-INS-110 | `:65` — o comparador Layer-3 deve parsear a linha do `ErrorCollector.java:37` | `:47` — todo evento declarado deve aparecer no `fsm`/`ere` (órfãos) |
| INV-INS-115 | — | `:55` — teto de 17 eventos por spec |

O gate G-2, a §7.4 e a tarefa C-V(2) citam "INV-INS-110" **no sentido gh101**. Enquanto as duas
changes coexistirem ativas, a citação é ambígua; quando sincronizarem, uma das duas definições terá
de ser renumerada. O primeiro ID livre é **INV-INS-116**.

Isso não é hipotético: é o dano concreto e já consumado de manter duas deltas ativas sobre a mesma
capability — que é exatamente o padrão que a §8 propõe repetir com C-3 e C-4. A causa mecânica é
simples e barata de corrigir: **gh101 está `✓ Complete` com 84/84 tarefas e não foi arquivada**;
gh102 idem, 28/28. Arquivar gh101 (sincronizando `instrumentation`) resolve a localização dos
invariantes e força a resolução da colisão.

### 3.4 A auditoria nunca cobriu o `jca` — o que reenquadra D-A

`audit/.../fase0/pre_registro.md:10` delimita o escopo às **23 specs de `jca_android`**. O conjunto
`jca` congelado nunca passou por auditoria alguma.

Isso muda o argumento de D-A. A opção (ii) — derivar `jca_v2` do `jca` congelado — não parte de um
conjunto neutro: parte de um conjunto **não auditado**, com 18 eventos órfãos verificados, com o
falso negativo do `KeyGeneratorSpec` (§2.1) e com o bug de shadowing do `KeyPairSpec` que a análise
anterior já mostrou ser byte-idêntico nos dois conjuntos. A opção (i) parte de um conjunto auditado
22/22, com defeitos **nomeados, enumerados e com exemplos regressivos executados**, e cujo veredito
REPROVADA é sobre decisões de conformidade em aberto — não sobre reparos ausentes.
`juizglobal_relatorio.md` §10.5 lista as áreas de patch candidatas, e todas são **para
`jca_android`**; a entrada permanente daquela fase é a lista de dez decisões do §7 (= D-H).

Dito de forma direta: "REPROVADA" é mais informação sobre um conjunto, não menos. Escolher (ii)
significa trocar um conjunto cujos defeitos estão catalogados por um cujos defeitos nunca foram
procurados, e re-derivar as 882 linhas que separam os dois (19 de 23 specs diferem; idênticas apenas
`GCMParameterSpecSpec`, `DHGenParameterSpecSpec`, `HMACParameterSpecSpec`, `RandomStringPassword`).

### 3.5 O estado do Estudo 03 destrava D-C

As corridas finais do Estudo 03 **não começaram**. `experimento-comp162/README.md:3` — *"Isto não é o
experimento final do Estudo 03. É um ensaio"* — e o mesmo consta do `manifest.json` e de
`docs/20260812_comp162.md:268`. O plano de prontidão exclui a execução do escopo
(`docs/20260810_plano_prontidao_estudo03.md:4`). O braço AspectJ foi reduzido por portão a 41 dos
162 APKs (`experimento-comp162-ajc/20260813_relatorio_fase_a.md:3-6`). Não existe diretório, compose
ou manifesto de campanha final, e nenhum arquivo de qualquer `experimento-*` é posterior a
2026-08-14.

**Portanto C-1a não invalidaria medição publicada alguma se landasse agora.** Fica registrado como
não determinado: se existe plano escrito da corrida final (só existe o de prontidão), e se ela está
bloqueada por decisão — a pendência P11 (`docs/20260812_registro_execucao_prontidao_e3.md:610-640`,
35 JSON de Phase-7 com WTG truncado) continua aberta e é independente deste trabalho.

### 3.6 A matriz de consumidores: ~78 sítios, e **três** formatos de `errors.csv` vivos

A §7.3 lista 10 entradas, das quais 3 são invariantes, 1 é um agregado sem enumeração ("the campaign
consolidators") e 6 são artefatos de código individualizados. O censo exaustivo encontra **≥ 78
sítios de código distintos em ~55 arquivos** que leem, escrevem ou dependem do formato da mensagem
ou do `errors.csv` — produção Python 19, testes vivos 15 arquivos, `scripts/` 13, `experimento-*/`
11, `.claude/skills/` 1, `audit/` 5, `ase-journal/` 8, Java 13 mais um YAML de oráculo. A alegação de
"uma ordem de grandeza" está confirmada.

**Três headers vivos, não dois.** Censo por leitura do cabeçalho real: **730 arquivos com 10
colunas** (incluindo o dataset do artigo), **54 com 11 colunas** (`source` entre `method` e
`message`, o formato do comp162), e um terceiro formato de 12 colunas **sem `message`**
(`out/run_jca_compare_consolidated/events_fair.csv`, lido por `scripts/derive_l3b_oracle.py:81`).
C-2 criaria o quarto.

**Executado, não deduzido:** `read_errors_csv` do `aperv-tool` **falha hoje** contra o dataset do
artigo publicado —
`ValueError: unexpected errors.csv header [...10 colunas...]; expected [...11 colunas...]` — e passa
contra o comp162. O parser de produção da camada gh103 não lê o dataset em que o artigo se apoia.

**Os consumidores mais graves que a §7.3 não lista**, em ordem de severidade:

1. **`ase-journal/docs/20260806_owasp_cwe_mapping_gen.py:47-54`** — o mapeamento OWASP/CWE do artigo
   publicado deriva `observed_value` por `str.extract(r"but found (.*?)\.?$")` sobre o **texto
   livre**, e usa a tripla `(spec, error_type, observed_value)` como **chave de agregação inteira**
   (`:61`) e como conjunto de artefatos (`:671`). São 28 dicts de mapeamento, dos quais 11 só existem
   porque o regex extraiu um literal (`MD5`, `SHA-1`, `SHA`, `SSL`, `TLS`, `X509`, `AndroidKeyStore`,
   `RSA/ECB/OAEPWithSHA1AndMGF1Padding`, `AES/CBC/PKCS7Padding`, `SHA256WITHRSA`, `NONEWITHRSA`).
   Trocar o texto livre por envelope, ou a parte 5 do `unique_msg` por `code`, esvazia
   `observed_value` em 100 % das linhas e obriga a re-derivar e re-revisar o mapeamento inteiro. E o
   `errors.csv` de origem está sob gate sha256 com `assert` em cinco scripts de auditoria
   (`audit/.../set/set_cons_hist.py:20,72`), então regenerá-lo invalida a auditoria.
2. **`modules/rv-coverage/.../logcat_parser.py:319-350`** — o parser canônico de produção, por
   índice, com `split(",")` sem bound. Não está na §7.3.
3. **`modules/rv-android-core/.../domain/log.py:113,181-187`** — `unique_msg` é a identidade de
   `__hash__`/`__eq__`; qualquer mudança move numericamente `unique_errors` e `mop_errors_unique` em
   `summary.csv`.
4. **`experimento-gov/scripts/consolidate_gov.py:26-37`** — regex **posicional**
   `:\d+,([A-Za-z][A-Za-z0-9]+),` mais vocabulário fechado de 15 literais de tipo. É o mais frágil
   de todos e quebra com envelope **e** com coluna nova.
5. **`.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py:35`** — não é instrumento
   congelado: é o **template que gera cada novo consolidador de campanha**. Classificá-lo como
   "frozen" é categoricamente errado.
6. **`validator/oracles/cryptoapp-oracle.yaml`** — seis substrings do texto livre (`"but found
   MD5."`, `"but found SHA-1."`…) governam o casamento em `TraceComparator.java:596-598`, e portanto
   o gate F1 ≥ 0,98 (`TraceComparator.java:64`). É a **única dependência semântica do texto livre em
   todo o lado Java**, e sua quebra é silenciosa: vira falso negativo, não erro.
7. **`modules/rv-android-core/tests/domain/test_log.py:385-386`** — o teste que ancora a semântica de
   que `but found MD5` e `but found SHA1` são violações **distintas**. É o teste que define o que a
   dedup significa hoje.

**A contradição de `result_processor.py:541-548` é real e maior que a alegada.** O comentário afirma
que *"every known consumer … addresses columns by name … that was verified, not assumed"*. Leem por
índice: `scripts/gh91_compare_consolidation.py:85-90` (tuplas `(0,1,2,3,4,5,8)`, fixadas no header de
10 colunas — no header de 11 o índice 8 é `source`, não `message`, de modo que o script **já compara
a coluna errada** contra qualquer CSV pós-gh89), `:261` e `:267`;
`scripts/regenerate_results/regenerate_container.py:84,246`, que **escreve posicionalmente** 10
colunas declarando em `:68` serem "exact headers from `result_processor.py`" — afirmação falsa desde
que o writer passou a 11; `logcat_parser.py:319-350`; e
`modules/rv-platform/tests/components/test_result_processor.py:451`, que asserta o header como lista
literal ordenada. A §7.1 do documento alvo herda a afirmação falsa.

**Sobre P3:** dos consolidadores ancorados no regex `\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$`, **três estão
sob `scripts/`** (`consolida_comparacao_aperv.py:26`, `regenerate_results/verify.py:46`,
`drive_cryptoapp.py:93` — este último já quebrado, ancorado num formato `[Spec] Type: msg` que não
existe mais), **dois estão modificados na working tree agora** (`experimento-cal/scripts/consolidate_cal.py`,
`verify_iteration.py`) e **um é novo e untracked** (`experimento-comp162-ajc/scripts/consolidate.py`).
A §7.3 chama o conjunto de "frozen". Instrumento de campanha sob `experimento-*/` congela
legitimamente; script vivo sob `scripts/` e template sob `.claude/skills/` não.

---

## 4. Escopo de C-3, medido

O documento alvo afirma cobrir "os 21 `@fail` + 4 sítios não-`@fail`". **Confirmado exatamente:** no
`jca` há 21 `@fail` reais (nenhum em comentário) em 21 arquivos, e **25 chamadas ao construtor de
3 argumentos** de `ErrorDescription` — 21 dentro de `@fail`, 4 fora. São esses 25 que produzem
`message = unknown`.

Mas o conjunto tem **51** chamadas a `new ErrorDescription` no total; as outras 26 usam o construtor
de 4 argumentos e já carregam mensagem. **O critério de aceitação 1 tem duas metades com escopos
diferentes:** "zero linhas com `message = unknown`" exige tocar 25 sítios; "toda linha carrega um
`code`" exige tocar os 51. O documento funde os dois números, e a diferença é o dobro do trabalho.

Nota de contraste, para o dimensionamento de C-4: em `jca_android` os mesmos 21 `@fail` convivem com
**75** chamadas a `ErrorDescription`, e **cinco** `@fail` não têm `__RESET` (contra um único no
`jca`: `KeyPairGeneratorSpec`).

---

## 5. Onde esta análise corrigiu a análise anterior, e a si mesma

Registrado por honestidade metodológica, como a análise anterior fez em seu §8.

1. **O efeito colateral de `SecureRandom` em §4.4(c) da análise anterior é empiricamente vazio.**
   Ela alerta que o reparo de aridade removeria relatórios `UnsafeAlgorithm` **verdadeiros** de
   `SecureRandom.getInstance(alg, provider)`. O mecanismo existe e é visível no artefato gerado
   (`gh101_group8_jca_android/.../MonitorWrappers.java:436-476`, com `g4` de aridade 1 disparando em
   wrappers de 2 e 3 argumentos). Mas medido: `SecureRandomSpec` tem 2.882 linhas no comp162,
   **todas** `InvalidSequenceOfMethodCalls`; zero `UnsafeAlgorithm`, e zero em **784** `errors.csv`
   da árvore inteira. O custo real do reparo está nos 16 advices sem `args()` (§3.2), não ali.
2. **A alegação de "50 sítios vivos com dois status" não se sustenta como enunciada** (§2.1, item 3);
   o defeito documental existe, mas é de atribuição de fonte, não de status contraditório.
3. **Correção a um número desta própria sessão:** ao contar specs que não emitem nada, contei nomes
   de arquivo. O nome declarado nem sempre coincide (`IvParameterSpec.mop` declara
   `IvParameterSpecSpec`). Recontando por nome declarado: **9 das 23**, não 10.
5. **Duas afirmações minhas sobre o §4 caíram, ambas por denominador não verificado** — a dos "111
   IDs sem referente" e a de que o falso negativo do `KeyGeneratorSpec` "desapareceu". Retratadas em
   §2.1, com o que sobrevive de cada uma.
6. **A decomposição de gêmeos de §3.1 estava incompleta.** Eu pareava muda × legível e por isso não
   via a família muda × muda (`IvParameterSpecSpec`, 419 + 419 em 12 sítios de contagem idêntica). A
   classe "registro que não deveria existir" sobe de 3.950 (25,1 %) para **4.788 (30,5 %)**. Achada
   por `claude_fable5:189`, que a nomeia como uma das três famílias que **apareceram** no E3.
7. **A análise anterior verificou "8.371 `found .`" como exato — e é, para o que conta, mas conta o
   fenômeno errado.** Medido aqui: **8.843** linhas terminam em `but found .`, distribuídas por cinco
   specs (TMF 8.371, Signature 234, MessageDigest 156, SSLContext 51, Mac 31). A colisão de wrapper
   pré-gh100, que F11 usa para explicar o fenômeno, cobre a fatia de **uma** spec; as outras 472
   linhas (5,3 %) exibem o mesmo sintoma onde o mecanismo não alcança. O 8.843 foi medido de forma
   independente por `claude_fable5:168` e por `codex:163`, e não chegou a documento nenhum.
4. **A medição de folga de truncamento da análise anterior reproduz, mas subestima o payload real**
   por omitir o campo `location`, ausente do `errors.csv` de 10 colunas e presente na linha de
   logcat (§2.2).

---

## 6. As quatro decisões, tomadas

Decididas pelo pesquisador em 2026-08-15, ao final desta análise. Registradas aqui com a evidência
que as sustenta e com o trabalho que cada uma cria.

### D-A — conjunto sucessor: **(ii), derivado do `jca` congelado**

**Decisão: não mexer em `jca_android`.** O conjunto sucessor (`jca_v2`) sai do `jca` congelado, que
permanece byte-idêntico — `INV-INS-109` no sentido gh101 fica preservado, e a reprodutibilidade de
E2/E3 não é afetada.

A ressalva que esta análise levantou permanece registrada e não foi acatada: a auditoria nunca cobriu
o `jca` (`audit/.../fase0/pre_registro.md:10` delimita o escopo a `jca_android`), de modo que `jca_v2`
nasce de um conjunto cujos defeitos nunca foram procurados sistematicamente. Isso não invalida a
decisão — muda o que ela custa, e o custo está enumerado abaixo.

**Correção de enquadramento que a decisão torna necessária.** As "882 linhas em 19 de 23 specs" que
separam `jca` de `jca_android` mediam o custo de **convergir** para `jca_android`. Esse não é o
objetivo: `jca_v2` = `jca` + reparos nomeados. O escopo real de lane C passa a ser esta lista, toda
ela já medida:

| Reparo | Onde | Evidência |
|---|---|---|
| 18 eventos órfãos em 10 specs | `IvParameterSpec` c3/c4, `KeyPairGeneratorSpec` initError, `MessageDigestSpec` reset, `PBEKeySpecSpec` f1/f2/err1-3, `PBEParameterSpecSpec` c3, `SSLContextSpec` unsafe_protocol, `SecretKeySpecSpec` c3/c4, `SecureRandomSpec` c3/g4/setSeed3, `SignatureSpec` g3, `TrustManagerFactorySpec` g3 | gate G-2 sobre as tabelas compiladas; §2 da análise anterior |
| Falso negativo do `KeyGeneratorSpec` | `jca/KeyGeneratorSpec.mop:47` — condição sobre `currentAlgorithmInstance` em vez de `alg` | §2.1 deste documento; spec emite zero linhas no comp162 |
| Shadowing do `KeyPairSpec` | `jca/KeyPairSpec.mop:19-21` — campo com o nome do parâmetro da spec; `@match` recebe null | §4.5 da análise anterior |
| Quatro defeitos de tradução | Cipher sem `Update+`/`Init+`; `SSLContext.createSSLEngine` declarado `void`; `PBEKeySpec` exige RANDOMIZED em `password` em vez de `salt`; `SecureRandom.end` sem `next2` | §5.3 do documento alvo, confirmado contra os dois oráculos |
| Pointcuts mortos | `SignatureSpec.sign()` (dois sítios) e `TrustManagerFactorySpec.gtm1` (declara retorno `KeyManager[]`, real `TrustManager[]`) | F12; verificado no `.mop` e nas tabelas |
| Único `@fail` sem `__RESET` | `jca/KeyPairGeneratorSpec.mop` | medido: é o único nos dois conjuntos |

**Atalho legítimo, que a decisão não proíbe.** Os 18 órfãos já têm solução trabalhada em
`jca_android` (pós-gh101: zero órfãos). **Ler** aquele conjunto como referência para escrever a linha
de FSM correspondente em `jca_v2` não é mexer nele. O caso `SSLContextSpec` é o exemplo: o estado
`unsafeProtocol` de `jca_android/SSLContextSpec.mop:96-105` é a forma já validada do reparo que
elimina 2.916 linhas mudas.

**Consequência de processo.** Como `jca_v2` não herda cobertura de auditoria alguma, os gates de C-V
deixam de ser conveniência e passam a ser o substituto da auditoria para o conjunto novo. Isso
**promove C-V de "paralela desde o dia 1" a pré-requisito duro de C-4** — e reforça a recomendação de
dividi-la (V-a lint + gate INV-INS-110 primeiro, que é o que C-4 realmente precisa).

**Decisão ainda pendente que esta escolha torna mais urgente:** **D-B** (oráculo). `jca_v2` deriva do
`jca`, cuja âncora é CrySL 1.5.2, não a api30. A regra "api30 para disponibilidade, 1.5.2 para
recomendação, nunca misturados em silêncio" precisa ser afirmada explicitamente para o conjunto novo
antes de qualquer reparo de catálogo em C-4.

### `st=` — **sai do contrato**

**Decisão: remover `st` do envelope.** A gramática de §7.1 passa a ser
`v=1 code=<...> ev=<eventName> obj=<SimpleClass> val='<observado>' exp='<esperado>' msg='<texto>'`.

Razão medida: os índices de estado são atribuídos após a minimização e não seguem a ordem de
declaração — `TrustManagerFactorySpec` declara `start, waitingInit, final` e o gerador produz
`start=0, final=1, waitingInit=2` (`results/gh56-smoke/.../MultiSpec_1RuntimeMonitor.java:8797-8801`).
Uma tabela índice→nome escrita à mão na `.mop` ficaria errada na primeira reedição, **sem que nada
detectasse**, fazendo a mensagem afirmar com confiança o estado errado — pior que `unknown`. Nome de
**evento** não tem esse problema (segue a ordem de declaração e é estável), e é o que C-3 escritura.

Consequências diretas: **O-1 deixa de ser pré-requisito de C-3**; a regra `c-A34` do próprio documento
(*"event names by hand … never state names"*) deixa de estar em contradição com §7.1; e o gate G-6
perde a propriedade sobre `st`, ficando com `code` e `ev`. O par `ev` + `code` continua identificando
o modo de falha sem ambiguidade, que é o objetivo declarado do trabalho.

### D-C — aridade `args()`: **landar agora, com a regra corrigida**

**Decisão: C-1a entra já, antes da campanha final.** As corridas finais do Estudo 03 não começaram
(§3.5), então nenhuma medição publicada é invalidada; e a campanha final deixa de rodar com 3.151
linhas mudas conhecidas e evitáveis (TMF 2.855 + KMF 296).

**A regra do documento alvo não pode entrar como está** — apagaria 66,6 % das linhas legíveis (§3.2).
A regra corrigida tem três cláusulas, todas verificáveis em código:

1. **Ausência de cláusula `args()` significa "sem restrição posicional" — não filtrar.** Nunca tratar
   como comprimento 0. São 16 advices no `jca`, entre eles `SSLContextSpec.init` (1.466 linhas
   legíveis) e `MessageDigestSpec.update` (1.163).
2. **Ler o comprimento de `ArgsPC.types()`, não de `names()`** — `names()` descarta o `..`
   (`PointcutExpressionParser.java:243-246`), fazendo `args(transformation, ..)` parecer aridade-1
   fixa. Reusar o `trailingRest`/`headCount` que já existe em `PointcutMatcher.java:280-288`.
3. **Filtrar no laço de agrupamento `WrapperEmitter.java:270-273`** — único ponto onde advice e
   overload concreto coexistem, e onde `cc.paramFqns.size()` está disponível.

**Teste que fixa a decisão:** um caso que verifique que os 16 advices sem `args()` sobrevivem ao
agrupamento, além do caso positivo (`args(a, *)` não entra no wrapper de 1 argumento).

**Sítio que C-1a não cobre, registrado como escopo declarado de fora:** advices `before` não passam
por wrapper (`WrapperEmitter.java:161-163`), então `KeyStore.load/store` e `SecureRandom.next1/next2`
continuam com aridade não imposta. Paridade real com AspectJ exigiria tratar a forma-binding em
`PointcutMatcher.java:268-271` — fica como trabalho nomeado, não silenciosamente omitido.

**Ordem obrigatória:** fechar antes as tarefas 7.4–7.6 da gh100
(`openspec/changes/gh100-weaver-emission-fidelity/tasks.md:97-99`), que são a verificação e a revisão
de código do mesmo módulo que C-1a edita. Landar C-1a antes faz a verificação da gh100 rodar contra
código de C-1a.

### Ordem de trabalho — **corrigir o documento antes de abrir issues**

**Decisão: nenhuma issue é aberta antes das correções estruturais no documento alvo.** A razão que
pesou: o §4 é citado como fonte por §5–§9, e 111 dos seus 225 IDs não têm referente possível (§2.1);
abrir issues sobre ele propaga as citações fantasma e o erro do `okio`/85,44 %, que o default de D-F
herda diretamente. A correção custa reescrever uma coluna de 70 linhas.

A lista de correções e sua ordem está em §7.

## 7. Ordem de trabalho: corrigir o documento, depois abrir as issues

### 7.1 Correções ao documento alvo, em ordem

Decidida a ordem "corrigir primeiro", esta é a lista, ordenada por quanto cada item contamina o que
vem depois:

1. **Corrigir `FINAL:114`** — a linha do `okio.`/85,44 %. A fonte citada (`d-B2` =
   `deepseek_v4_flash:166`) refuta o número; a linha a registra como concordância. **O default de D-F
   é derivado dela** e prescreve exatamente a lista de prefixos que a fonte não reproduziu. É a
   correção mais barata com maior efeito a jusante.
2. **Reintroduzir o falso negativo do `KeyGeneratorSpec`** (`gemini36flash:208`;
   `jca/KeyGeneratorSpec.mop:47`). É o único falso negativo do corpus, sumiu inteiro da consolidação,
   e agora entra no escopo de lane C por força da decisão D-A.
3. **Incorporar as doze ausências que mudam trabalho** (§2.1), com prioridade para as que
   dimensionam C-3 e C-4: o inventário de mensagens por `ErrorType` (12 das 19 são de um único tipo),
   o censo de mensagens degeneradas (base do G-6), os tetos de geração (17 eventos = 53 s/3,3 GB,
   18 = StackOverflow) e o acoplamento `logcat_parser.py:306`.
4. **Trocar a alegação "without filtering" (`FINAL:25`) por um número honesto** — 581 itens, 77,5 %
   transportados — e anexar a lista dos 61 ausentes. As listas de extração já existem em
   `docs/20260815_javamop_extracao/` (uma por relatório, com `arquivo:linha` e destino no FINAL).
5. **Resolver a coluna `Item(s)` do §4** substituindo os IDs por citações `sigla:linha` contra essas
   listas, e corrigir a linha `g-C1..C17`, cujo status `R` e destino `—` são falsos para oito dos
   vinte conceitos que ela comprime.
6. **Publicar o censo dos 18 eventos órfãos do `jca`** em C-0, com o registro de que a gh101 já os
   reparou em `jca_android` e de que `jca_v2` terá de reparar os mesmos (§6, D-A).
7. **Reescrever a gramática de §7.1**: remover `st` (decidido); remover a proibição de vírgula, que é
   insatisfazível (27,06 % das mensagens têm vírgula, geradas por `String.join(",", …)` dentro do
   conjunto congelado) e desnecessária (os quatro parsers já rejuntam o campo 6+); especificar escape
   para `'`, para o espaço e para `=` — os três com **zero ocorrências hoje**, o que faz qualquer
   teste de propriedade passar vacuamente; e decidir se `ev` entra na identidade de dedup, sem o que
   a dedup descarta exatamente o que a mudança existe para mostrar.
8. **Trocar C-0 de "linha de base" para "orçamento residual"**, com a decomposição gêmeas/solitárias
   de §3.1 — que é produzível hoje, offline — e o reconhecimento de que a atribuição por *evento*
   continua impossível sem corrida de calibração.
9. **Corrigir a §7.3**: os três formatos de `errors.csv` vivos, os consumidores ausentes de §3.6, o
   caminho real do `clock_logcat_join.py`, e a partição honesta entre "congelado" (instrumento de
   campanha sob `experimento-*/`) e "vivo sob P3" (`scripts/`, `.claude/skills/`).
10. **Corrigir a regra de reparo de C-1a** conforme §6/D-C, e o dimensionamento de C-3 conforme §4
   (25 sítios para eliminar `unknown`, 51 para dar `code` a toda linha).
11. **Adicionar o mapeamento `C-x → gh<N>`**, a aresta C-2 → C-3, e desfazer o ciclo D-F/C-0.

### 7.2 Bloqueios de processo, antes da primeira issue

**Não há mapeamento `C-x → gh<N>` em lugar nenhum.** O maior número usado é **103** (arquivada como
`gh103-campaign-analysis-layer`); o primeiro livre é **104**. Antes de abrir qualquer coisa, três
bloqueios de processo precisam de decisão:

1. **A colisão INV-INS-109/110** (§3.3). Arquivar gh101 e gh102 — ambas completas, ambas não
   arquivadas — sincroniza `instrumentation` e força a renumeração. G-2, §7.4 e C-V dependem disso.
2. **Quatro linhas da §8 têm par track/template contraditório** — os templates auto-aplicam o label
   de track: `bug.yml` aplica `track:quick-path` (C-1a e C-4 declaram Full/FF SDD), `enhancement.yml`
   aplica `track:ff-sdd` (C-1 e C-2 declaram Full SDD). E `Documentation+scripts`, declarado em C-0,
   **não existe** como template. A saída prática (editar o label depois de abrir) já foi usada na
   issue #101, mas precisa estar dita.
3. **A §8 nunca marca a capability `aperv`**, embora C-1 e C-2 editem
   `modules/aperv-tool/src/aperv_tool/analysis/violations.py` — e provavelmente também
   `campaign-analysis`, já que `clock_logcat_join.py` (cujo caminho a §7.3 escreve errado; o real é
   `modules/aperv-tool/src/aperv_tool/analysis/clock_logcat_join.py`) é território normativo de
   `INV-CAN-01`/`INV-CAN-18`.

E **C-1a não pode ser "sub-mudança" de C-1**: não existe representação de hierarquia entre changes
neste OpenSpec — `openspec/changes/` é plano, os schemas declaram dependência apenas entre artefatos
de uma mesma change, e nenhum skill conhece relação pai/filho. Ou é um grupo de tarefas dentro de
C-1, ou é uma change autônoma com issue própria. Dado que C-1a é a única das oito com um teste
falhando disponível hoje, autônoma é a opção honesta.

**Sobre a intercalação C-3/C-4 "por arquivo":** a recomendação de sequenciar (ou fundir) se mantém,
mas a razão mais forte não é a alegada. O resume do `/opsx:apply` é por change e não quebra; o que
sustenta a recomendação é (a) a regra de localidade do próprio repo — *"tasks that touch files in the
same module or directory go to the same subagent (avoids merge conflicts)"*, `docs/WORKFLOW.md:329`;
(b) P3, "one commit = one consistent state"; e (c) a colisão de IDs de invariante, que **já
aconteceu** entre gh100 e gh101 exatamente por duas deltas ativas na mesma capability.

---

## 8. O que continua não verificado

- **Nada foi executado em device.** Vale para todo este documento.
- **Os itens do §4 marcados `U` que nenhuma decisão precisou** continuam não reabertos, agora com a
  ressalva mais séria de que seus IDs podem não ter referente localizável (§2.1).
- **`c-C34` está parcialmente fechado:** o limite do logcat foi verificado (§2.2) e as specs de
  emissão zero foram medidas (9 no `jca`/comp162, §3.1), mas "5/14 drive records `unknown`" e "KPG
  NPE aniquila registros" não foram reabertos.
- **A pendência P11 do Estudo 03** (35 JSON de Phase-7 com WTG truncado) é independente deste
  trabalho, continua aberta, e nada no plano de mensagens a observa.
- **A comparação pareada AspectJ × dexlib2** existe (§2.4) mas mede viés agregado por
  `(apk, spec, classe, método, tipo_erro)`; não isola a aridade de `args()`. Isolar exigiria uma
  corrida pareada nova.

---

## 9. Referências

- Linhagem: `docs/20260815_javamop_mensagens*.md` (11 arquivos)
- **Listas de extração produzidas por esta análise:** `docs/20260815_javamop_extracao/{claude_fable5,
  deepseek_v4_flash,gemini36flash,gpt5_codex}.md` — 581 itens enumerados por leitura integral, com
  `arquivo:linha` da fonte e status de transporte para o `FINAL.md`
- Datasets medidos: `/home/pedro/.../ase-journal/dataset/results/errors.csv` (97.018 linhas,
  10 colunas); `experimento-comp162/results/*/*/errors.csv` (8 arquivos, 19.664 linhas, 11 colunas);
  `experimento-comp162-ajc/consolidado/mop_diff_ajc_x_dexlib2.csv` (115 linhas)
- Oráculos de monitor: `results/{gh56-smoke,gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control}/monitors/`
- Specs: `rvsec/rvsec-mop/src/main/resources/{jca,jca_android}/`
- Auditoria: `audit/20260808_validacao_jca_android/` (`fase0/pre_registro.md` = escopo;
  `global/juizglobal_relatorio.md` §10 = veredito; `pilot/` = GAMA-SET-05)
- Estudo 03: `experimento-comp162/README.md`, `docs/20260812_comp162.md`,
  `docs/20260810_plano_prontidao_estudo03.md`, `docs/20260812_registro_execucao_prontidao_e3.md`
- Processo: `docs/WORKFLOW.md`, `openspec/specs/instrumentation/spec.md`,
  `openspec/changes/gh10{0,1,2}-*/`, `.github/ISSUE_TEMPLATE/`
- AOSP: `system/logging/liblog/include/log/log.h` (`main`), `log_read.h`
  (`android-11.0.0_r48`, `android-8.0.0_r36`), `logger.h` (`android-7.0.0_r36`, `android-5.1.1_r38`)
