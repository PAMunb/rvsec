# Análise adversarial do documento FINAL de mensagens JavaMOP

**Data:** 2026-08-15
**Alvo:** `docs/20260815_javamop_mensagens_FINAL.md` (521 linhas)
**Natureza:** revisão adversarial independente. **Nada foi implementado.** Toda a investigação foi
somente-leitura.

**Método.** Seis agentes de verificação independentes, cada um com um recorte disjunto (weaver
dexlib2; gerador JavaMOP/RV-Monitor; specs `.mop` contra os dois oráculos CrySL; camada de
transporte e consumidores; consistência interna e fidelidade à linhagem; conformidade de processo e
viabilidade do plano), mais medições próprias sobre os datasets (`ase-journal`, `experimento-comp162`)
e sobre as tabelas de transição dos monitores compilados. Onde os agentes divergiram do documento ou
entre si, as medições próprias arbitraram — três conclusões de agente foram descartadas por esse
critério e estão registradas em §8.

**Escopo do que esta análise não faz.** Não reabre os quatro relatórios de validação externa contra
o §4 do documento alvo item a item (a lacuna está caracterizada em §5, não resolvida). Não verifica
o `~4.068 B` de limite do logcat contra fontes do Android. Não executa nada em device.

**Linhagem citada.** Todos em `rv-android/docs/`. Os prefixos de ID usados inline (`c-`, `d-`, `g-`,
`x-`) são os do §4 do documento alvo, e resolvem assim:

| Arquivo | Papel | Prefixo em §4 |
|---|---|---|
| `20260815_javamop_mensagens_FINAL.md` | **alvo desta análise** | — |
| `20260815_javamop_mensagens.md` | o plano (causa-raiz L1–L8, WS-1..8, D-1..8, D01–D50) | — |
| `20260815_javamop_mensagens_analise.md` | revisão adversarial do plano ("o review") | `R` |
| `20260815_javamop_mensagens_analise_handoff_prompt.md` | brief dado à revisão adversarial | — |
| `20260815_javamop_mensagens_validacao_prompt.md` | brief dado aos quatro LLMs externos | — |
| `20260815_javamop_mensagens_claude_fable5.md` | validação externa 1 | `c-` |
| `20260815_javamop_mensagens_deepseek_v4_flash.md` | validação externa 2 | `d-` |
| `20260815_javamop_mensagens_gemini36flash.md` | validação externa 3 | `g-` |
| `20260815_javamop_mensagens_gpt5_codex.md` | validação externa 4 | `x-` |

Ressalva que §5 desenvolve: esse mapeamento resolve o **prefixo**, não o **item**. Os IDs `A/B/C` do
§4 não existem em nenhum dos quatro originais, então `d-B2` identifica o relatório mas não uma linha
localizável nele. Onde esta análise cita um item, cita também o conteúdo medido, para não depender do
ID.

---

## 1. Veredito

A **camada factual do documento é forte e honesta**. A **camada de design contém dois defeitos que
invalidam o mecanismo proposto em §7.2**. E o documento **não identifica a maior fonte isolada de
`unknown` do próprio conjunto que o Estudo 03 executa**.

Como insumo de Fase 0 ele está pronto para virar issues *depois* de três correções estruturais
(§2, §3.1, §5 final) — não antes.

---

## 2. O achado ausente: a maior fonte de `unknown` não é a que o documento nomeia

Executando o **próprio gate G-2 do documento** (`INV-INS-110`: nenhum evento vinculado pode ter
linha de transição inteiramente para o estado de falha) sobre as tabelas dos monitores compilados:

| Conjunto | Artefato | Eventos órfãos | Specs afetadas |
|---|---|---|---|
| **`jca` (congelado — o que o Estudo 03 roda)** | `results/gh56-smoke/monitors/MultiSpec_1RuntimeMonitor.java` | **18** | **10 de 23** |
| `jca_android` pré-gh101 | `results/gh99_jca_android_monitors/...` | 18 | 10 de 23 |
| `jca_android` pós-gh101 | `results/gh101_group8_jca_android/...` | **0** | — |

Os 18 eventos órfãos do `jca`:

```
IvParameterSpecSpec      c3, c4              PBEParameterSpecSpec  c3
KeyPairGeneratorSpec     initError           SecretKeySpecSpec     c3, c4
MessageDigestSpec        reset               SecureRandomSpec      c3, g4, setSeed3
PBEKeySpecSpec           f1, f2, err1,       SignatureSpec         g3
                         err2, err3          TrustManagerFactorySpec g3
SSLContextSpec           unsafe_protocol
```

O documento afirma apenas, em §7.4, *"INV-INS-110 must hold (already true in `jca_android`)"*. Ele
**nunca registra que o `jca` congelado viola o invariante 18 vezes**, nem que a gh101 já reparou
todas elas. Cada evento órfão é um produtor garantido de `unknown`: por F1 (completação por sink),
todo disparo cai no sink e aciona `@fail`.

### 2.1 `SSLContextSpec` — 2.916 linhas mudas por dois eventos de FSM ausentes

`jca/SSLContextSpec.mop:70-82` declara os estados `start [g1, g2]`, `s1 [init]`, `end [engine]`. O
evento `unsafe_protocol` (`:46-51`) **não aparece em nenhuma linha**, e compila para:

```java
// results/gh56-smoke/monitors/MultiSpec_1RuntimeMonitor.java:7349
static final int Prop_1_transition_unsafe_protocol[] = {3, 3, 3, 3};   // todo estado -> sink
```

Traço do fluxo dominante `SSLContext.getInstance("TLS")` → `init(...)`:

1. `unsafe_protocol` dispara (a allowlist é só `TLSV1.2`/`TLSV1.3`) → `start` → sink → **muda #1** + `__RESET`
2. `init` a partir de `start` → sink → **muda #2**, e o corpo de `init` (`:54-60`) emite o relatório `UnsafeProtocol` legítimo

Dois mudos por fluxo. Evidência por sítio em `experimento-comp162` (8 arquivos, 19.664 linhas):

| Sítio | Mudas (`InvalidSequenceOfMethodCalls`) | Relatórios (`UnsafeProtocol`) |
|---|---|---|
| `Platform.kt:75` | 533 | — |
| `Platform.kt:76` | 648 | — |
| `Platform.kt:168` | 477 | 479 |
| `Platform.kt:194` | 410 | 410 |
| `Platform.kt:197` | 225 | 225 |
| **total da spec** | **2.916** | **1.466** |

Os sítios de `getInstance` produzem muda sem relatório; os de `init` produzem muda **e** relatório na
mesma linha. 2 × 1.466 = 2.932 ≈ 2.916.

**São 2.916 mudas — mais que as 2.855 que §5.1 atribui ao seu achado principal.** E o reparo custa
duas linhas de FSM: nenhuma mudança de weaver, nenhuma decisão D-C, nenhuma reinstrumentação.
`jca_android/SSLContextSpec.mop:96-105` já contém esse reparo (estado `unsafeProtocol`).

Há aqui uma **inversão de prioridade**: §5.1 elege como achado principal um defeito que exige
mudança no weaver, uma decisão de pesquisador em aberto e reinstrumentação — enquanto volume
comparável sai de um defeito de autômato já resolvido no outro conjunto.

### 2.2 Consequência para D-A

Divergência medida entre os conjuntos: **19 de 23 specs diferem, ~880 linhas alteradas** (idênticas:
`GCMParameterSpecSpec`, `DHGenParameterSpecSpec`, `HMACParameterSpecSpec`, `RandomStringPassword`).

O default recomendado em D-A é a opção **(ii)** — derivar `jca_v2` do `jca` congelado, *"inheriting
gh101's divergence-record discipline"*. Isso herda a **metodologia**, não os **reparos**: significa
partir de um conjunto com 18 eventos órfãos e re-derivar ~880 linhas que a gh101 já fez.

A justificativa dada é de prazo (*"(ii) se as decisões §7 da auditoria não forem iminentes"*). Mas o
veredito REPROVADA da auditoria é sobre **decisões de conformidade em aberto**, não sobre reparos
ausentes. Trocar espera por re-implementação de autômatos é trocar atraso por exatamente a classe de
defeito que o documento inteiro estuda.

**Recomendação: inverter o default de D-A para (i)**, reservando (ii) para o caso em que as decisões
§7 sejam recusadas, e não meramente adiadas. Ressalva honesta: isso é sobre *ponto de partida*, não
um atestado de prontidão — a auditoria reprova `jca_android` 22/22 e há problemas reais nele (§4.4,
§4.5).

### 2.3 Lacuna adicional: não existe orçamento residual, e C-0 não consegue produzi-lo

§1 nomeia três mecanismos por trás do `unknown` (autômatos, defeitos de weaver, camada de
reportagem). Mas os dois primeiros produzem registros que **não deveriam existir**, não registros que
precisam de mensagem melhor. Só o terceiro é problema de mensagem. O documento nunca calcula a
divisão do volume.

Consequências:

- **C-3 está sem dimensionamento.** É a mudança mais cara do plano (21 arquivos editados à mão,
  sequenciados contra C-4 nos mesmos arquivos) e é escopada sem saber quantos registros precisa
  explicar. Depois de C-1a e C-4, a população residual pode ser fração pequena das 15.714 de hoje.
- **A métrica não é comparável através do reparo.** O denominador de "% `unknown`" é encolhido de
  propósito por C-1a e C-4. Se os registros falso-positivos somem, a proporção pode **subir** com o
  sistema melhorando. O documento declara discontinuidade de contagem para a dedup de C-2, mas não
  para esta, que é maior.
- **O critério de aceitação 1 é satisfazível por deleção**, e o critério 3 persegue deleção
  ativamente. Os critérios não distinguem explicar de remover.

E há um bloqueio estrutural: as 15.295 linhas mudas colapsam em apenas **296 sítios distintos**
`(spec, class, method, source)`, todas com `message = unknown`. A atribuição só é possível por
*sítio*, nunca por *evento* — porque o nome de evento ausente é precisamente o defeito medido. Onde
os sítios separam mecanismos (o caso `SSLContextSpec`, §2.1), funciona; no caso geral, não.
**C-0 como escrito não consegue produzir os números que dimensionariam C-3.**

Recomendação: C-0 deve entregar um **orçamento residual** — decomposição das 15.714 em (i) aridade
`args()`, (ii) cada defeito de tradução nomeado, (iii) órfãos de §2, (iv) violações genuínas que
precisam de mensagem — com o escopo de C-3 derivado de (iv). Isso exige uma corrida de calibração com
nome de evento (O-1/O-2), que passa a ser pré-requisito de C-0, não opção posterior.

---

## 3. Defeitos bloqueantes de design

### 3.1 `st=<stateOrClause>` é inimplementável do lado do `.mop`

A suposição central de §7.2 — *"o corpo do evento roda antes da transição"* — **é verdadeira**,
verificada nas duas formas de monitor. O gerador emite, nesta ordem: prólogo da condição, corpo do
usuário, `RVM_lastevent`, transição, flags de categoria (`BaseMonitor.java:394-461`). Prova no
artefato (`gh101_group8_jca_frozen_control/.../MultiSpec_1RuntimeMonitor.java`):

```java
:8841   { trustManagerFactory = mf; currentAlgorithmInstance = alg; }   // corpo do usuário
:8848   RVM_lastevent = 0;
:8850   Prop_1_state = Prop_1_transition_g1[Prop_1_state];              // transição
```

Mas `getState()` devolve um **inteiro atribuído pelo gerador, e a numeração não segue a ordem de
declaração**:

| Spec | Ordem declarada no `.mop` | Índices gerados |
|---|---|---|
| `TrustManagerFactorySpec` | `start, waitingInit, final` | `start=0, final=1, waitingInit=2, sink=3` |
| `SecureRandomSpec` | `start, init, end` | `start=0, end=1, init=2` |

Os índices são atribuídos **após a minimização** e mudam a cada edição do `.mop`. `stateBefore` só
pode carregar um inteiro instável e sem nome.

Isso colide com a regra que o próprio documento adota em c-A34 — *"event names by hand … **never**
state names"*. §7.1 pede nome de estado; §4 proíbe. **Um dos dois tem que cair:** ou O-1 (gerador
emite `__PREVSTATE`) vira pré-requisito de C-3, ou `st` sai do contrato.

### 3.2 Três caminhos produzem mensagem confiantemente errada — pior que `unknown`

1. **Prólogo da condição antes do corpo.** javamop emite `if(!(cond)) return false;` *antes* do corpo
   do usuário (`RVDumpVisitor.java:47-51`; artefato `:8837-8839`). Num evento reprovado na condição,
   `lastEventName`/`stateBefore` **nunca são escritos**; o chamador ignora o booleano e re-testa
   flags obsoletas.
2. **`KeyPairGeneratorSpec` não tem `__RESET`.** Verificado: é o **único** `@fail` sem ele nos dois
   conjuntos (`jca/KeyPairGeneratorSpec.mop:110-113`). Sem reset a flag nunca limpa e o handler
   re-dispara nomeando o evento *anterior*. **Nenhuma mudança em §8 é dona desse reparo**, embora o
   documento o verifique em c-A39 e novamente em §5.2.
3. **Clones herdam a escrituração.** `clone()` é `super.clone()` raso
   (`BaseMonitor.java:760-769`); slices novos nascem como clone do slice-raiz (artefato `:16186`) e
   herdam `lastEventName`, `stateBefore`, estado e flags. Nem `clone()` nem `reset()` limpam campos
   declarados pelo usuário. O documento estabelece esse mecanismo como F5 e o usa para explicar
   contaminação em outro lugar, mas não o aplica aos campos que propõe criar.

### 3.3 `EVENT_NAMES` é redundante e G-1 não detecta o defeito real

Se cada corpo escreve `lastEventName = "<nome>"` literal, o array não é usado por nada — o design o
introduz e depois o contorna. Pior: `GCMParameterSpecSpec` tem **dois eventos ambos chamados `c1`**
(ids 0 e 1; a desambiguação `c1_3`/`c1_4` existe só no aspecto e no descritor JSON, nunca no
monitor). Ambos escreveriam o mesmo nome, e o gate G-1 (`length == getNumberOfEvents()`)
**passa mesmo assim**. G-1 precisa de checagem de distinção, não de comprimento.

Nota de viabilidade: **nenhum `.mop` da árvore declara campo `static` hoje** — os únicos `static` são
`import static`. A gramática suporta em todos os estágios, mas a viabilidade continua não demonstrada
empiricamente. G-1 aqui faz trabalho real, não cerimônia.

### 3.4 A gramática de §7.1: a proibição de vírgula é insatisfazível e desnecessária

- **Insatisfazível:** 27,06 % das mensagens de produção (26.251 de 97.018) contêm vírgula, geradas
  estruturalmente por `String.join(",", …)` em ≥11 sítios `.mop` — dentro do `jca` **congelado**,
  onde §3 proíbe edição.
- **Desnecessária:** os quatro parsers existentes já rejuntam o campo 6+
  (`logcat_parser.py:348`, `TraceComparator.java:91-111`, `clock_logcat_join.py:454`,
  `violations.py:141`). O split posicional só quebra se a vírgula cair nos campos 0–5, que o envelope
  não toca.
- **Auto-contradição:** "sem vírgula nos valores" e "valores entre aspas `'`" não podem ser ambos
  normativos. Se vírgulas são proibidas, as aspas são decoração; se as aspas são o mecanismo,
  vírgulas são permitidas. O documento não diz qual vale, e adia para "se os testes de propriedade
  de C-1 mostrarem que é necessário" — empurrando a decisão central de transporte para a
  implementação.
- **O conjunto de restrições nomeia os caracteres errados:** `{sem \n, sem :::, sem ,}` não menciona
  o **espaço** (o separador de pares, onipresente nos valores reais), o **`'`** (o delimitador de
  valor — 0 ocorrências hoje, então o teste de propriedade passa vacuamente e o risco embarca) nem o
  **`=`**. E `obj=`/`ev=`/`st=` ficam sem aspas, sem regra, numa assimetria não explicada.
- **A rejeição de JSON não discrimina:** o argumento dado ("chaves/vírgulas/aspas numa linha
  posicional") aplica-se literalmente ao `key=value` escolhido. O argumento real seria tamanho e
  legibilidade em logcat, que o documento não faz.
- **`exp` e `msg` duplicam-se:** o texto livre de hoje *é* `"expecting one of {…} but found X."`,
  isto é, `exp` + `val` reescritos. Carregar os três triplica o lugar onde o mesmo fato pode divergir.

Medição de folga de truncamento (reconstruindo o payload das 97.018 linhas): mediana 131 B, p99
209 B, máximo 349 B, contra o limite de ~4.068 B. O envelope roughly dobra isso (~630 B no pior caso,
≈16 % do limite). **Truncamento não é o problema** — mas `msg` é o último campo, então um corte
produz envelope não terminado, e `val` vem da aplicação e não tem teto em nenhum dos coletores.

### 3.5 A identidade de deduplicação anula o objetivo da mudança

`ErrorSummary` identifica por `(spec, error, class, method, location)` — `ev`, `st` e `val` ficam
**fora**. O coletor é `if (errors.add(err))`. Logo, dois eventos ofensores diferentes na mesma linha
colapsam num registro só, e quem sobrevive é ordem de chegada — exatamente a patologia que
`ErrorDescription.java:132-134` já documenta para `expecting`:

> *"`expecting` is not part of the identity, so two reports of the same violation that differ only in
> the expected value are one record, and which of the two survives an in-JVM `HashSet` is arrival
> order."*

O propósito declarado do trabalho é nomear o evento ofensor; a dedup descarta todos menos o primeiro
por linha. §7.1 não enfrenta isso. Ou `ev` entra na identidade, ou o contrato precisa dizer que `ev`
é "um dos eventos ofensores naquela linha", não "o" evento.

Nota relacionada: o critério de aceitação 1 (*"zero linhas com `message = unknown`"*) fica vacuamente
satisfazível emitindo `msg='unknown'` dentro de um envelope bem formado. A segunda metade do critério
(*"every row carries a `code`"*) é a que mede algo.

### 3.6 A matriz de consumidores está incompleta em cerca de uma ordem de grandeza

§7.3 lista ~10 consumidores. Não listados, e que quebram **em silêncio**:

- **9 consolidadores de experimento** ancorados em `r"\bRVSEC\s*:\s*([A-Za-z]+Spec,.+)$"`
  (`experimento-comp162/scripts/consolidate.py:46`, `experimento-cal/scripts/consolidate_cal.py:75`,
  `verify_iteration.py:56`, `experimento-rearch-aperv/scripts/{consolidate,verify}.py`,
  `experimento-comp162-ajc/scripts/consolidate.py:59`,
  `experimento-20260721/scripts/consolidate_compare.py:35`). §7.3 chama-os de "frozen"; **dois estão
  modificados na working tree agora**, e C-0 planeja estender esse mesmo diretório.
- `experimento-gov/scripts/consolidate_gov.py:29` — regex posicional `:\d+,([A-Za-z][A-Za-z0-9]+),`
  mais vocabulário fechado de 15 literais.
- `scripts/gh91_compare_consolidation.py:85-90` — tupla de índices `(0,1,2,3,4,5,8)`, fixada no
  header de **10 colunas**. Já está obsoleta.
- **`ase-journal/docs/20260806_owasp_cwe_mapping_gen.py:49`** — deriva `observed_value` por
  `str.extract(r"but found (.*?)\.?$")` e tem ~15 linhas com `observed_value=="MD5"/"SHA-1"/"TLS"`.
  **O mapeamento OWASP/CWE do artigo é derivado por regex sobre o texto livre.** Substituir a parte 5
  por `code` o destrói.
- `summary.csv` / `mop_errors_unique`, `results.json`, `RvErrorLog.__hash__`, os gates sha256
  congelados, `v_errors.py` (que *afirma* a forma de 5 partes), e um quarto parser independente de
  7 campos em `v_d4_d5_deepparse.py:77-96`.

Existem hoje **dois headers `errors.csv` vivos** — 10 colunas (dataset do artigo,
`regenerate_container.py:84`, `gh91_compare_consolidation.py`) e 11 colunas
(`result_processor.py:562`, `violations.py:63`) — e `read_errors_csv` **já falha** contra o dataset do
artigo. C-2 criaria um terceiro. O design pressupõe uma linha de base para migrar; existem duas, e a
mais antiga é a do artigo publicado.

Contradição direta no código: `result_processor.py:543-548` afirma que *"every known consumer
addresses columns by name … that was verified, not assumed"*. `gh91_compare_consolidation.py:90` lê
por índice. A afirmação é falsa, e §7.1 a herda.

---

## 4. Correções factuais ao documento

### 4.1 `c-A16` está sub-classificado

Marcado `U (count)` em §4; é **V+ exato**. Medição sobre `experimento-comp162`:

```
error types entre as linhas `unknown`:
  InvalidSequenceOfMethodCalls   15.295
  UnsatisfiedConstraint             419      (IvParameterSpecSpec)
                                 -------
                                  15.714  = 79,91 % de 19.664
```

A equivalência `unknown ⇔ InvSeq` vale no dataset de referência (bicondicional perfeito, 70.760) e
**quebra** no E3. §1 mistura os dois datasets numa frase; a equivalência está corretamente atada ao
dataset de referência, mas o leitor a carrega adiante.

### 4.2 O denominador de "≈21 %" nunca é publicado

3.151/19.664 = 16,02 % ✓ para "≈16 % de todas as linhas". Para "≈21 % dos
`InvalidSequenceOfMethodCalls`": 3.151/15.714 = 20,05 %, e 3.151/15.295 = **20,6 %**. Só o segundo
chega a ≈21 % — e 15.295 é um denominador que o documento nunca publica, derivado de um item que ele
mesmo marca `U`.

Recomendação: publicar o denominador em C-0.

### 4.3 A atribuição de §5.1 não é de 100 %

`TrustManagerFactorySpec.g3` também é órfão (`Prop_1_transition_g3[] = {3,3,3,3}`), então os 61 fluxos
`UnsafeAlgorithm` já geram tríades mudas que o reparo de aridade não toca (~6 % das 2.855). Para KMF,
que tem linha `g3 -> unsafeAlg` e 0 linhas `UnsafeAlgorithm`, a atribuição de 100 % vale.

Além disso, o traço de §5.1 lista `g2`, `init`, `getTrustManagers` — mas F12 estabelece que `gtm1`
nunca casa (declara retorno `KeyManager[]`, real `TrustManager[]`; `getTrustManagers` aparece em
**0 de 90** `MonitorWrappers.java` gerados). A terceira muda é quase certamente `g3`, não `gtm1`.
§5.1 e F12 se contradizem.

### 4.4 A regra de reparo proposta é mal-formada como escrita

*"drop an advice whose `args` list has no trailing `..` and whose length != `cc.paramFqns.size()`"*:

- Cobre vacuamente advices **sem** cláusula `args()` (comprimento 0), derrubando `Mac.update`,
  `MessageDigest.update`, `Cipher.doFinal`, `KeyStore.load/store` — visíveis hoje em
  `MonitorWrappers.java:329-341`. Precisa ser explicitamente escopada a advices que carregam `ArgsPC`.
- Precisa ser lida sobre `ArgsPC.types()`, não `names()`: `..` é excluído de `names`
  (`PointcutExpressionParser.java:243-246`), então `args(transformation, ..)` leria como
  comprimento-2-sem-`..` e apagaria `jca_android/CipherSpec` g1/g3 dos wrappers que aquela spec foi
  escrita para cobrir.
- **Efeito colateral não declarado:** `SecureRandomSpec.mop:76-79` é `args(alg)`, comprimento 1, e
  hoje dispara nos wrappers de aridade 2 emitindo `UnsafeAlgorithm` **verdadeiros** para
  `SecureRandom.getInstance(badAlg, provider)`. O reparo os remove. §5.1 afirma que a mudança altera
  *"what the frozen `jca` reports (fewer mutes) without changing what it says"* — aqui ela muda o que
  diz.
- `KeyStore` está seguro (ambos `args(ksType)`, 1 = 1), como o documento afirma.

Correção menor de redação: *"arity is never enforced"* é forte demais. A aridade do `call()` **é**
imposta (`WrapperEmitter.java:383-387`, `PointcutMatcher.java:371-376`); o que nunca é imposto é a
aridade posicional de `args()`, porque `matchArgs` retorna cedo em `PointcutMatcher.java:269-271` e
porque o `advice-emitter` **nunca referencia `ArgsPC`** — este último é o sítio preciso do reparo, e
o documento não o nomeia.

### 4.5 Escopo e classificação

- **`KeyPairSpec` shadowing está sub-escopado.** `jca_android/KeyPairSpec.mop:19-21` é
  **byte-idêntico** em `jca/KeyPairSpec.mop:19-21`, e o artefato congelado reproduz o bug
  (`gh101_group8_jca_frozen_control/.../MultiSpec_1RuntimeMonitor.java:5659,5664`). É um fato que
  afeta o conjunto congelado, num documento cujo §3 diz que nada toca o `jca`.
- **Segundo pointcut `sign` morto não listado:** `jca/SignatureSpec.mop:105-106` declara
  `public byte sign(byte[],int,int)`, retorno real `int`. O critério 7.6.6 não é atingível corrigindo
  só `s1`.
- **Catálogo PBEWithHmac mal classificado.** `CipherTransformationUtil.java:44,49,67` só aceita
  `"AES"`/`"RSA"`; todo `PBEWithHmacSHA*AndAES_*` que o oráculo do `jca` admite (`Cipher.crysl:90-96`)
  é rejeitado → falso `UnsafeAlgorithm`. Contra 1.5.2 isso é **defeito de tradução**, não escolha de
  oráculo — e como vive em Java compartilhado, o escopo de reparo de §7.4 não o alcança. O espelho
  para `jca_android` (api30 admite `ChaCha20`, `AES_128`, `ARC4`, `DESede`, `BLOWFISH`, `AES_256`,
  `AES/ECB`; o mesmo Java rejeita) não é listado em lugar nenhum.
- **`KeyPair co?` em `jca_android` não é decisão em aberto, é inconsistência existente.** Aquele
  conjunto reproduz catálogos api30 em todas as outras specs mas mantém o construtor obrigatório de
  1.5.2 (`KeyPairSpec.mop:61`) — exatamente o estado "never mixed silently" que D-B proíbe.
- **`updateAAD` ausente dos dois conjuntos**, tornando `noCallTo[AADUpdate]` (`Cipher.crysl:118`)
  inexequível; e a precedência de `Cipher.crysl:85` (`|` liga mais fraco que `,`) precisa ser fixada
  antes de G-3 poder afirmar qualquer direção de inclusão.

### 4.6 Erros pontuais de fato

| Onde | Documento diz | Verificado |
|---|---|---|
| F2 | `__ACTIVITY` entre as substituições do handler | só é substituído em ações de evento (`BaseMonitor.java:364-365`), não em handlers |
| F14c / §5.2 | sintaxe `default -> S` | é `default <State>`, **sem `->`** (`FSMParser.jj:149`) |
| §5.2 | duplicatas viram `c1_1`, `c1_2` | viram `c1_3`/`c1_4` (contador global) e **fundem num único evento** no monitor |
| §5.1 | cita `WrapperEmitter.java:379` | `:379` é linha em branco; a linha substantiva é `:378` |
| §5.1 | "same for … SecureRandom" (g1/g2/g3) | SecureRandom dispara **g4**, não g3 (`g3` é `getInstanceStrong()`) |
| §5.1 | rótulo "E3 evidence" | os números vêm de `experimento-comp162`, não de `experimento-e3-decisiva` (onde KMF = 0) |
| §5.1 | breakdown `Platform.kt` 534 + 1.179 + 647 | soma 2.360 contra 2.855 mudas; 495 linhas não atribuídas |
| §4 / §10 | "`generic_new` 39" | correto, mas conta **sítios `Log.v`**, não arquivos (são 27 `.mop`); §10 remove a unidade e o número fica ao lado de "`Property` 25" como se fosse contagem de spec |
| §8 (prosa) | "C-3 e C-4 editam os mesmos 21 arquivos" | 21 é contagem de **sítios `@fail`**; o conjunto tem **23** `.mop`, e C-4 edita arquivos sem `@fail` |
| §5.3 | api30 SecureRandom "same" | api30 é `Ins, Seeds?, Ends*` com alfabeto renomeado (`ne` no lugar de `nI`) — o veredito sobrevive, o mapa de alfabeto de G-3 não |

Confirmados como corretos e exatos: 97.018 / 70.760 / 72,93 % / 19 mensagens; 19.664 / 15.714 /
79,91 %; TMF 2.916 = 2.855 + 61; 8.371 `found .`; 98 = 55 + 39 + 4; "21 `@fail` + 4 sítios
não-`@fail`" (idêntico nos dois conjuntos); 15/23 e 18/23 de monitores atômicos; `.aj` git-ignored
(`rvsec/rvsec-mop/.gitignore:2`); todos os quatro defeitos de tradução de §5.3 contra os dois
oráculos.

---

## 5. Defeitos metodológicos

**O §4 não é auditável no nível de item.** Os quatro relatórios-fonte enumeram **116 itens**; §4 cita
**225 IDs** num esquema `A/B/C` que **nenhuma fonte usa**. O artefato intermediário que criou esses
IDs — a "passagem de extração independente" mencionada no cabeçalho — **não está na tabela de
linhagem**. Como §4 se declara *"the map from each original item to its status"*, essa função está
inoperante para quem levar o documento adiante.

Isso se soma a uma tensão que o próprio cabeçalho cria: um documento intitulado **FINAL**, declarado
como o que vai ser implementado, afirmando que *"the consolidation should be redone against the four
originals"*. E o "reproduz sem filtrar" não pode ser verdade em sentido forte — uma passagem de
extração **é** um filtro.

Defeitos concretos que decorrem disso:

1. **9 IDs somem da numeração contígua** apesar do "without filtering": `d-A16`, `d-A19`, `d-A21`,
   `g-A3`, `x-A15`, `x-A18`, `x-A19`, `x-A20`, `x-A24`.
2. **`okio.` / 85,44 % é registrado como concordância quando a fonte o refuta.** A linha cita `d-B2`,
   que diz o oposto (mede 82,67 %, marca 85,44 % como não reproduzível) — e o default de **D-F herda
   o erro**.
3. **`c-B2`/`c-C1` é marcado `V+`** embora o escopo tenha sido cortado de 11/23 specs para 3/23 entre
   a fonte e §5.1. Deveria ser `V±`.
4. **F10 promove um item `U` a "estabelecido".** A afirmação *"revert unrecorded in
   `data/gh101/README.md`"* aparece em §2 (a seção de fatos verificados) citando "review §0" — mas o
   review §0 diz o contrário (*"gh101 records it and stays open"*), e §4 marca o item como
   `U (not re-opened)`.
5. **Compressão de linhas destrói rastreabilidade.** Linhas como `g-C1..C17` (17 itens),
   `d-C1, d-C2, d-C4..C10` (9 itens) e `c-A6..A15, d-A2..A5, …` (~20 itens) recebem **um** status e
   **uma** glosa. Um status não pode estar correto para 17 itens heterogêneos, e é justamente onde
   itens perdem seu caráter distintivo (o falso **negativo** do `KeyGeneratorSpec` de gemini B04
   desaparece inteiramente; `currentAlgorithmInstance` não aparece no documento).
6. **Itens `V+` sem dono.** `c-A39` (KPG re-reporta por falta de `__RESET`) é confirmado duas vezes e
   **nenhuma mudança o repara**. `c-C35` (coletor não sincronizado) aponta para C-2, cujas tarefas não
   contêm trabalho de sincronização.
7. **Mesmo fato com dois status:** "50 sítios vivos" é `R` numa linha e `U (not re-opened)` em outra.

---

## 6. Plano §8 — viabilidade e processo

### 6.1 C-V não é uma mudança, é um programa

Seis artefatos, três linguagens, dois toolchains: linter `.mop`; gate pytest sobre tabelas geradas nas
duas formas; **compilador CrySL `ORDER`→regex→DFA com verificação de inclusão bidirecional e extração
de traços separadores mínimos**; mutation runner; árvore de teste JVM; **suíte micro-APK** mais
CogniCrypt como oráculo externo.

Agravantes verificados:

- `rvsec/rvsec-mop/pom.xml` tem **17 linhas, zero `<dependencies>`, sem junit, sem surefire**. Criar
  `src/test` não é criar diretório: é montar infraestrutura de teste num módulo que nunca compilou
  Java.
- **CogniCrypt não existe na árvore** (`find -iname "*cognicrypt*"` → nada; só prosa).
- As fontes dos micro-APKs não estão em `apks_examples/` (que contém um único binário,
  `cryptoapp.apk`); as fontes Gradle estão em `examples/cryptoapp/`, e **não há pipeline que as
  construa** — o rv-experiment instrumenta APKs prontos.

E C-V bloqueia C-2, C-3, C-4 e quatro dos oito critérios de aceitação. É simultaneamente o maior e o
mais a montante do grafo — a forma clássica de uma mudança que não termina e trava quatro outras.

**Split recomendado**, que sai da própria tabela de dependências (C-3 precisa só de G-1/G-6):

- **V-a** (Quick Path, Python, dias): lint `.mop` + gate INV-INS-110. Desbloqueia C-3 rápido; a
  semente já existe (`scripts/gh101_monitor_transition_check.py`).
- **V-b** (Full SDD, semanas): inclusão ORDER→DFA + traços separadores + mutação, escopado a **uma**
  spec primeiro, com critério de aceitação "a ferramenta reproduz os traços separadores que a
  auditoria já achou". Se não reproduz, a ferramenta está errada — e você descobre em uma spec, não
  em 23.
- **V-c** (Java): a árvore de teste do `rvsec-mop`, cuja primeira tarefa honesta é "adicionar junit +
  surefire e ter um teste trivial verde".
- **V-d**: adiar suíte micro-APK e CogniCrypt. Nenhum é necessário para C-3 ou C-4.

**G-6 deve sair de C-V e ir para C-3**, onde o código que ele testa é escrito. Como está, C-V precisa
construir teste de propriedade para código inexistente, e C-2 precisa passar num gate sobre um campo
que só C-3 produz.

### 6.2 G-3 sobre-promete

- `L(A_crysl)` só a partir de `ORDER` é codificação **parcial** de CrySL (ignora CONSTRAINTS,
  REQUIRES/ENSURES e fluxo de objetos). Não sustenta "no false accept / no false reject" sem
  qualificação — sustenta "no que diz respeito a ordenação de chamadas". Um G-3 verde será lido como
  conformidade.
- O **mapa de alfabeto "declarado por spec"** é escrito à mão, e é exatamente onde os defeitos de
  tradução vivem (as quatro linhas de §5.3 são erros de rótulo/linha). Um mapa manual pode codificar
  o mesmo erro que deveria detectar. Deveria ser derivado mecanicamente do bloco EVENTS da regra,
  falhando fechado em rótulo sem correspondência ou ambíguo — o que entrega os pointcuts mortos de
  F12 de graça.
- A extração precisa incluir a completação por sink (F1), ou a comparação de linguagens não está bem
  definida. O documento não diz que inclui.
- **Crédito:** extrair o lado `.mop` das **tabelas geradas** e não do texto-fonte é escolha
  excelente — pega exatamente o descarte silencioso de símbolos que F14d documenta.

### 6.3 C-3 antes de O-1

O gatilho de O-1 é *"C-3 mostrar que a escrituração é propensa a erro nos 21 arquivos ou um segundo
conjunto aparecer"*. Ambas as cláusulas já estão satisfeitas antes de C-3 começar: o documento já
contém o bug de shadowing do `KeyPairSpec` (a classe exata de defeito que declarar campos à mão
produz), e o default de D-A já contempla um segundo conjunto. O gatilho é auto-realizável.

Custo assimétrico: O-1 é classificado raio `M (small, additive)`; C-3 são 21 edições manuais com
boilerplate defensivo replicado, cada uma precisando de G-1/G-6/G-8, sequenciadas contra C-4 nos
mesmos arquivos. A mudança de gerador plausivelmente é mais barata **e** elimina a contenção
C-3/C-4 inteira.

Existe um contra-argumento legítimo que o documento **não faz**: mexer no gerador bifurca um
toolchain cuja versão está fixada para reprodutibilidade de E2/E3. Se é essa a razão, ela precisa
estar escrita — hoje a decisão é tomada implicitamente pelo cronograma.

Recomendação mínima: fazer C-3 em **duas ou três** specs à mão, fixar a gramática do envelope e o
formato do `codes.csv`, e então reavaliar O-1 com evidência real.

### 6.4 A intercalação C-3/C-4 "por arquivo" é incompatível com a máquina

- Dois `tasks.md` sobre um estado de árvore quebram o resume do `/opsx:apply`, que casa checkpoint
  com estado de código.
- Dois delta specs na mesma capability: quem arquivar segundo funde sua delta sobre um spec principal
  que já absorveu a primeira, e nenhuma das duas foi escrita contra esse estado. O skill de sync não
  tem tratamento de conflito.
- Um commit com as duas coisas viola P3 (*"one commit = one consistent state"*) e referencia duas
  issues.

As opções coerentes são **fundir** C-3 e C-4 por conjunto, ou **sequenciar C-4 → C-3**. A segunda é o
que a causalidade já exige: a mensagem nomeia estados que C-4 vai criar e apagar.

### 6.5 Grafo e processo

- O ASCII, a tabela e a prosa discordam sobre a aresta C-0→C-1 (a prosa diz "começam juntos", a
  tabela diz que C-1 depende de C-0).
- `D-C` aponta para `C-1` quando bloqueia `C-1a`.
- **Falta a aresta C-2 → C-3:** C-2 depende de G-6, que testa o `code` que só C-3 produz. Isso torna
  C-2 transitivamente dependente de D-A, o que o plano não reconhece.
- **D-F bloqueia C-0 e é implementado por C-0** (ciclo, resolúvel na prática, mas o grafo está errado).
- D-E e D-F também bloqueiam C-2, sem constar.
- §3, a legenda de lanes e a linha de C-3 discordam três vias sobre se lane C depende de D-H.
- **Não há mapeamento `C-x → gh<N>` em lugar nenhum**, embora o cabeçalho declare que cada mudança
  vira uma issue e um diretório `gh<N>-<nome>`. Toda referência cruzada de §8/§9 vira re-chaveamento
  manual. É a omissão mais barata de corrigir e a mais provável de causar deriva. `C-1a` como
  sub-mudança de `C-1` também não tem representação no OpenSpec.
- **Quatro linhas geram contradição entre track escolhido e label auto-aplicado** pelos templates
  (C-1a, C-1, C-2, C-4). `Documentation+scripts` não é um template existente.
- A **legenda de raio vem do documento que este declara superado**
  (`20260815_javamop_mensagens.md:637`) e usa valores que ela não define (`none`, `S-test`).
- **INV-INS-109/110/115 só existem dentro de deltas não arquivados** — `openspec/specs/instrumentation/spec.md`
  para em INV-INS-103. G-2, o gate de C-3 e §7.4 dependem de texto de contrato que o spec principal
  não contém. gh100 tem 3 tarefas de verificação abertas sobre o mesmo arquivo que C-1a edita.
- `aperv` é uma capability real que o plano nunca marca, embora C-1 e C-2 editem
  `modules/aperv-tool/.../violations.py`.
- Caminho errado: `aperv-tool/clock_logcat_join.py` está em
  `modules/aperv-tool/src/aperv_tool/analysis/clock_logcat_join.py`.

### 6.6 Critérios de aceitação (§7.6)

Três dos oito não são mensuráveis como escritos: o **3** e o **4** dependem da suíte micro-APK, que
C-V só entrega como *especificação*; o **8** define READY como a conjunção da auditoria, que falha em
**quatro de cinco membros** e cujo backlog §9 o plano explicitamente declina de agendar. O critério 8
faz a condição de saída do plano depender de um corpo de trabalho que o plano não contém — precisa
ser renegociado.

O critério **6** ("ramo de assinatura alcança `@match`; evento SSL engine dispara") é o mais forte da
lista: binário, observável, atado a defeitos concretos.

### 6.7 P3

A **discontinuidade de contagem declarada está correta** — é substituição completa com a quebra
semântica explícita, que é o que P3 pede, e `ErrorDescriptionTest` é reescrito, não mantido em
paralelo.

O que **viola P3** é *"every consumer either accepts the grammar or is listed as frozen"*: "listado
como congelado" é um shim implementado em documento. Instrumentos experimentais (`experimento-*/`)
congelam legitimamente — o próprio gate da gh101 articula o princípio (*"altering it after the fact
invalidates the reproduction of every result"*). Mas scripts vivos em `scripts/` sob P3 se atualizam
ou vão para `backup/`. §7.3 põe `rv_oracle_common.py` e "os consolidadores de campanha" na mesma
frase; a lista precisa ser partida em duas.

---

## 7. Recomendações, em ordem de prioridade

1. **Publicar o censo dos 18 eventos órfãos do `jca` em C-0** e reconhecer que a gh101 já os reparou.
   É a classe de defeito mais barata, mais volumosa e já resolvida do corpus.
2. **Inverter o default de D-A para (i)**, ou justificar explicitamente por que re-derivar ~880 linhas
   é preferível a herdá-las.
3. **Resolver `st=`**: ou O-1 vira pré-requisito de C-3, ou `st` sai do contrato (§3.1).
4. **Dar dono ao `__RESET` do `KeyPairGeneratorSpec`** antes de qualquer escrituração spec-side, e
   tratar prólogo-de-condição e herança-por-clone como requisitos de §7.2 (§3.2).
5. **Reescrever a gramática de §7.1**: remover a proibição de vírgula, especificar escape para `'` e
   para o espaço, e decidir se `ev` entra na identidade de dedup — sem isso a dedup descarta o que a
   mudança existe para mostrar (§3.4, §3.5).
6. **Dividir C-V** em V-a/V-b/V-c/V-d e mover G-6 para C-3 (§6.1).
7. **Trocar C-0 de "linha de base" para "orçamento residual"**, reconhecendo que ele precisa de uma
   corrida de calibração com nome de evento para atribuir por mecanismo (§2.3).
8. **Sequenciar C-4 → C-3** (ou fundi-las), abandonando a intercalação por arquivo (§6.4).
9. **Republicar §4** contra os quatro originais ou renumerá-lo pela enumeração das fontes; corrigir
   `okio.`/85,44 %, rebaixar `c-B2`/`c-C1` para `V±`, promover `c-A16` para `V+ (419)`, remover a
   afirmação de revert de F10 (§5).
10. **Adicionar o mapeamento `C-x → gh<N>`**, a aresta C-2 → C-3, e desfazer o ciclo D-F/C-0 (§6.5).

---

## 8. Onde esta análise corrigiu seus próprios verificadores

Registrado por honestidade metodológica: três conclusões de agente foram descartadas por medição
direta.

1. *"15.714 / 79,9 % não reproduz"* — **reproduz exatamente**. O agente contou
   `InvalidSequenceOfMethodCalls` (15.295) em vez de linhas `unknown` (15.714). O documento está certo.
2. *"`SSLContextSpec` sozinha (2.916) excede TMF sozinha"* como refutação dos números de TMF — os dois
   números são 2.916 mas medem coisas diferentes (InvSeq da SSLContext × total de linhas da TMF).
   Coincidência numérica. O ponto substantivo sobrevive, e por outra via (§2.1).
3. *"`generic_new` 39 não bate com a árvore"* — 39 conta sítios `Log.v`, não arquivos. A crítica
   válida é menor e está em §4.6.

---

## 9. Referências

- Documento alvo e linhagem: ver a tabela no cabeçalho (nove arquivos em `rv-android/docs/`)
- Trabalho anterior citado: `openspec/changes/gh10{0,1,2,3}-*/`, `rv-android/data/gh101/README.md`
- Auditoria do `jca_android`: `docs/20260808_validar_specs_jca_android.md`,
  `audit/20260808_validacao_jca_android/` (§7 = as dez decisões de D-H; §10 = veredito REPROVADA;
  `fase0/pre_registro.md` §7 = a conjunção READY do critério 8)
- Estudo 03: `docs/20260810_plano_prontidao_estudo03.md`, `docs/20260812_comp162.md`,
  `docs/20260812_registro_execucao_prontidao_e3.md`
- Processo: `docs/WORKFLOW.md`, `docs/SDD.md`, `openspec/specs/README.md`,
  `openspec/specs/instrumentation/spec.md`, `.claude/AGENTS.md`, `CLAUDE.md`
- Datasets medidos: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ase-journal/dataset/results/errors.csv`
  (97.018 linhas, 10 colunas); `rv-android/experimento-comp162/results/*/*/errors.csv`
  (8 arquivos, 19.664 linhas, 11 colunas)
- Oráculos de monitor: `rv-android/results/{gh56-smoke,gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control}/monitors/`
- Specs: `rvsec/rvsec-mop/src/main/resources/{jca,jca_android}/`
- CrySL 1.5.2: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/Crypto-API-Rules/JavaCryptographicArchitecture/src/`
- MetaCrySL api30: `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/MetaCrySL/generated/api30/`
- Gerador: `rv-monitor/`, `javamop/`; weaver: `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`
- Runtime: `rvsec/rvsec-core/`, `rvsec/rvsec-logger-csv/`, `rvsec/rvsec-android/rvsec-logger-logcat/`
