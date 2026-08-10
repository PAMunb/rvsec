# ALFA — parecer piloto: `CipherSpec.mop` ↔ `Cipher.cryptsl` (api30)

Agente Alfa (conformidade CrySL e lógica formal) · 2026-08-08 · rodada-piloto, sem leitura cruzada.

**Artefatos (SHA-256, 16 hex):** `CipherSpec.mop` `c9deafb2acb2b2d7` · `Cipher.cryptsl` `a8e7e2d2e33946c5` · `AndroidCipherTransformationUtil.java` `5cb3c05b8e69e7fd` · `ExecutionContext.java` `22dc3540c196a5b1`. Working tree = HEAD `1dd1f4c5` para os auditados (manifesto Fase 0).

**Limitação declarada (obrigatória):** a linguagem MOP foi modelada a partir da **sintaxe** da seção `fsm` do `.mop` (linhas 288–326), assumindo a semântica documentada do plugin FSM (evento sem transição ⇒ categoria `fail`). O autômato **efetivo** do monitor gerado é tarefa de outro agente nesta rodada; todo claim de linguagem é condicional a essa extração (dimensão 1 do modelo semântico exige o artefato).

**Interpretação do ORDER (registro de ambiguidade do oráculo):** a gramática do próprio MetaCrySL (`src/lang/crysl/ConcreteSyntax.rsc:59-70`) declara prioridade `sequence > or` (vírgula liga mais forte), sob a qual o ORDER leria `(Gets, Inits+, w+) | X+` — degenerado: o uso normal `getInstance; init; doFinal` ficaria fora da linguagem (verificado no script: `G I Fw ∉ L(B)`). O CrySL oficial (Xtext) tem `,` como operador mais externo, dando `Gets, Inits+, (w+ | (FINWOU | (updates+, DOFINALS))+)`. Adotei a leitura oficial (A); ver ALFA-CIP-04.

## 1. Log científico (resumo)

1. **Q:** a linguagem do `fsm` inclui/está incluída em L(ORDER) módulo α? **H:** GH101 afirma "language is unchanged" (vs congelado). **T:** regex→NFA→DFA + produto BFS (`alfa_automata_check.py`, determinístico, 1 execução). **E:** `alfa_automata_output.txt`. **R:** dupla inclusão **FALHA nas duas direções**; menores separadores: `G I I` (FP), `G I U U` (FP), `G I W Fw` (FN), `G I W U` (FN). **Incerteza:** fonte é a sintaxe `.mop`. **D:** claims 01–03 FAIL.
2. **Q:** as fusões 24→14 preservam agregado/binding? **T:** tabela α evento a evento contra assinaturas da regra + `instanceof` dos corpos. **R:** partição por aridade coerente; discriminantes recuperam IWOIV×IWIV e as cláusulas por argumento; ressalvas de borda (tipo dinâmico × overload estático; `null`). **D:** claim 05 PASS com ressalvas.
3. **Q:** CONSTRAINTS/REQUIRES/ENSURES traduzidos com o mesmo conjunto de valores? **T:** leitura cláusula a cláusula contra `AndroidCipherTransformationUtil` e `ExecutionContext`. **R:** tabela de transformação transcrita 1:1 nos literais; porém componente vazio, folding, `encmode`, comprimentos, `noCallTo(IWOIV)`, `callTo(iv)`, segunda casa de `generatedKey` divergem/omitem. **D:** claims 07–18.
4. **Q:** o resíduo D-S9 muda a linguagem aceita? **R:** não sobre eventos observados; **sim** sobre traces Java na fronteira de fim de trace (FN terminal) e no diagnóstico (acusação deslocada). **D:** claim 08.

## 2. Matriz normativa

Status: FID = FIDELIDADE_DEMONSTRADA · DIV-EQ = DIVERGÊNCIA_EQUIVALENTE_COMPROVADA · LIM = LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA · OMIT = OMITIDA · INC = INCORRETA · INCON = INCONCLUSIVA.

### 2.1 OBJECTS (22)

| Objeto CrySL | Binding MOP | Status |
|---|---|---|
| transformation | `g1`/`g3` `args(transformation, ..)` | FID |
| encmode | `init2/3/4` 1º arg | FID |
| key | `init4` tipado `Key`; `init2/3` como `Object keyOrCert` + `instanceof` | FID |
| cert | coberto por `keyOrCert` via `!(instanceof Key)` (sem cláusula própria no api30) | FID |
| params (`AlgorithmParameterSpec`) | `init3/4` via `instanceof` | FID |
| param (`AlgorithmParameters`) | bound como `Object`, **sem leitura** (preparedAlg omitido, D-S14) | LIM |
| pre_plaintext / pre_ciphertext | `u1` (arg/ret), `u3` (args) | FID |
| pre_plainBuffer / pre_cipherBuffer | `u5` | FID |
| plainText / cipherText | `f2/f5` (arg/ret), `f1` (ret), `f3` (arg) | FID |
| plainBuffer / cipherBuffer | `f7` | FID |
| ranGen | `init3` (instanceof) / `init4` (posição 4) | FID |
| wrappedKey (arg de `wrap`) | **não** bound; `wkb1` liga o **retorno** — nenhuma cláusula api30 depende do arg | FID |
| offsets/lens (6 ints) | parcialmente bound (`u3`, `f3`, `f5`); só p/ assinatura — constraints de comprimento omitidas (ver c5–c8) | OMIT |

### 2.2 EVENTS e agregados — função α (fusões D-S11, 24→14)

| CrySL | MOP | Discriminante | Veredito sobre a discriminação |
|---|---|---|---|
| g1, g2 (Gets) | `g1`(válida)/`g3`(inválida), 1 pointcut `getInstance(String, ..)` | `condition(isValid)` — split por **constraint**, não por assinatura; `g2` tem 2º arg `_` (anônimo) na regra, fusão fiel | FID (split é codificação da c1; resíduo diagnóstico → ALFA-CIP-06) |
| i1, i3 | `init2` (aridade 2) | aridade | FID |
| i2, i4, i5, i8 | `init3` (aridade 3) | aridade + `instanceof` do 3º (SecureRandom→i2/i8; APSpec→i4; AParams→i5) | FID com 2 ressalvas: (a) o `instanceof` testa tipo **dinâmico**, o overload é **estático** — classe que estenda SecureRandom e implemente APSpec dispararia os dois ramos (FP marginal, só com classe adversarial); (b) 3º arg `null` cai fora de ambos os ramos — sem report (FN de borda) |
| i6, i7 | `init4` (aridade 4) | `instanceof` do 3º | FID (mesmas ressalvas) |
| u1, u2 | `u1` (`update(byte[], ..)` ret `byte[]`) | retorno + aridade via `..` | FID |
| u3, u4 | `u3` (`update(byte[],int,int,byte[], ..)` ret int) | idem | FID |
| u5 | `u5` | — | FID |
| f2, f4 | `f2` (`doFinal(byte[], ..)` ret `byte[]`) | 1º arg nomeado exclui `doFinal()` ✓ | FID |
| f5, f6 | `f5` | `..` no offset final | FID |
| f1 / f3 / f7 | `f1` / `f3` / `f7` | 1:1 | FID |
| w | `wkb1` | 1:1 | FID |
| **iv** | **nenhum** | — | **OMIT** (ALFA-CIP-18) — orçamento usa 14 de 17: havia slot |
| FINWOU × DOFINALS | {f2,f5,f7} × {+f1,f3} | preservado exatamente no FSM (`s2` sem `f1/f3`) | FID |
| IWOIV × IWIV | recuperável por aridade+instanceof, mas **nenhum código consome** a distinção (c2 omitida) | — | OMIT (via c2) |

### 2.3 ORDER

| Claim | Cláusula | Tradução | Status | Evidência | FP/FN |
|---|---|---|---|---|---|
| ALFA-CIP-01 | `Inits+` | `s1 –init→ s2`; `s2` **sem** transição de init | **INC** | `G I I`: CrySL prefixo-viável (de `G I I W`), MOP `@fail` — walk no output do script | **FP** realizável (re-init é uso comum e legal) |
| ALFA-CIP-02 | `updates+` | `s2 –u→ s3`; `s3` **sem** loop de update | **INC** | `G I U U`: MOP `@fail` no 4º evento; CrySL prefixo de `G I U U F1` | **FP** realizável (update em streaming multi-chunk) |
| ALFA-CIP-03 | `w+ \| (…)+` exclusivo | `end` aceita `wkb1`, `f*` e `u*` intercalados | **INC** | `G I W Fw`, `G I Fw W` aceitos pelo MOP; fora de L(CrySL); `G I W U` sem `@fail` | **FN** (mistura wrap×doFinal aceita) |
| ALFA-CIP-04 | precedência do ORDER | leitura (A) adotada; gramática do MetaCrySL implica (B) degenerada | INCON (oráculo) | `ConcreteSyntax.rsc:59-70`; sanity check no script | — (ambiguidade do oráculo, não da spec) |

A alegação de GH101/INV-INS-114 ("the language is unchanged") refere-se ao conjunto **congelado**, que não avaliei; contra o **oráculo CrySL** a linguagem divergia antes e diverge agora. Nota: `s2` sem `f1`/`f3` e `f2` excluindo `doFinal()` estão **corretos** contra o ORDER (FINWOU ⊂ DOFINALS) — verificado no produto.

### 2.4 CONSTRAINTS (25)

| # | Cláusula | Tradução | Status | Nota |
|---|---|---|---|---|
| c1 | part0 ∈ {8 algoritmos} | catálogo `MODES` (util:93-102) | FID | literais 1:1 (folded) |
| c2 | CBC-família ∧ encmode≠1 ⇒ noCallTo(IWOIV) | **nenhuma** | **OMIT** (ALFA-CIP-17) | FN realizável: decrypt CBC via `init(int,Key)` não reporta; não achei registro em `data/gh101/` |
| c3 | CBC-família ∧ encmode=1 ⇒ callTo(iv) | **nenhuma** (`getIV` sem evento) | **OMIT** (ALFA-CIP-18) | registrada só como comentário no spec; slot havia (14<17) |
| c4 | encmode ∈ {1,2,3,4} | nenhuma | OMIT (ALFA-CIP-15) | mitigada: `init` lança `InvalidParameterException` (INFERIDO da API) |
| c5–c8 | 4 constraints de comprimento | nenhuma | OMIT (ALFA-CIP-16) | parcialmente cobertas por exceções da API; c6/c8 são artefatos dúbios do gerador (oráculo cru) |
| c9–c25 | tabela algoritmo/modo/padding (17 cláusulas) | `MODES`/`PADDINGS` (util:92-154) | FID nos literais (ALFA-CIP-14) | conferi as 17 uma a uma: conjuntos idênticos, incl. RSA `""`+ECB e pares sem implicação de padding (AES/ECB etc.) admitidos — fiel ao cru |
| — | componente ausente = irrestrito (decisão do util) | `isValid` retorna cedo p/ mode/pad vazios | **INC** vs oráculo cru (ALFA-CIP-14a) | a regra usa a convenção `""` (RSA c13, ChaCha20 c24 listam `""`); AES/DESede/BLOWFISH/ARC4/AES_128/AES_256 **não** listam `""` ⇒ `"AES"`, `"AES/CBC"` (sem padding), `"ARC4"` violam o cru e o util **aceita** — FN; decisão documentada no javadoc (util:51-56), não em `data/gh101/` |
| — | folding case/hífen | `fold()` (util:251-253) | DIV não comprovada (ALFA-CIP-14b) | aceita `"aes/cbc/pkcs5padding"`, `"OAEPWithSHA1AndMGF1Padding"` que o cru rejeita; equivalência depende da resolução case-insensitive do JCA (INFERIDO, não provado); hífen não funde literais (conferido no conjunto OAEP) |

### 2.5 REQUIRES (6) / NEGATES (0)

| Claim | Cláusula | Tradução | Status | FP/FN |
|---|---|---|---|---|
| ALFA-CIP-07 | `generatedKey[key, part(0,transformation)]` | `validate(GENERATED_KEY\|_PUBLIC\|_PRIVATE, key)` em `condition()` | **OMIT parcial** | 2ª casa (concordância de algoritmo) **não representável**: `ExecutionContext.validate(Property,Object)` é unário (ExecutionContext.java:118-120) e `KeyGeneratorSpec:114` grava sem algoritmo. FN realizável: chave AES em cipher DESede passa. Sem registro em `predicate_omissions.csv` (procurei) |
| ALFA-CIP-08 | idem — colocação em `condition()` | supressão: evento não dispara; init "sai do autômato" | **INC** (deliberada, registrada — D-S9) | FN terminal realizável: `getInstance; init(chave não monitorada)` e fim de trace ⇒ **nenhum report, nunca**; em traces continuados o veredito sobrevive deslocado (`InvalidSequenceOfMethodCalls` no `doFinal`, cláusula e `__LOC` errados). Não é inevitável: os outros 4 REQUIRES desta mesma spec leem no **corpo** exatamente para evitar isso (CipherSpec.mop:75-78) |
| ALFA-CIP-09 | `randomized[ranGen]` | `reportUnrandomized` no corpo; i2/i8 (init3-instanceof), i6/i7 (init4) | FID | direção de report correta; writer `RANDOMIZED` existe (SecureRandomSpec:106-133) |
| ALFA-CIP-10 | CBC-família ∧ encmode=1 ⇒ `preparedIV[params]` | `requiresPreparedIv` (util:211-213, `IV_MODES` = lista da regra incl. PCBC) + leitura no corpo | FID | condição de modo e direção transcritas 1:1 |
| ALFA-CIP-11 | GCM ⇒ `preparedGCM[params]` | `requiresPreparedGcm` (util:221-223), sem condição de direção — igual à regra | FID | — |
| ALFA-CIP-12 | `preparedAlg[param, part0]` | omitida; arg bound, leitura não escrita | **LIM** | produtor (AlgorithmParameters) sem spec no conjunto; registrada (`predicate_omissions.csv` linha preparedAlg, D-S14). FN para i5/i7. Bloqueia aderência total |
| ALFA-CIP-13 | `!macced[_, plainText]` | `reportMacedPlainText` em f2/f5 (únicos que ligam plainText); report quando predicado **vale** (negação correta); projeção na 2ª casa fiel à casa anônima | FID | writer `MACED` em MacSpec:40-44; f7/updates fora da cláusula na própria regra ✓ |

### 2.6 ENSURES (3 + 2 escritas extra)

| Claim | Cláusula | Tradução | Status |
|---|---|---|---|
| ALFA-CIP-19 | `encrypted[pre_ciphertext, pre_plaintext]` after updates; `encrypted[cipherText, plainText]`; `encrypted[cipherBuffer, plainBuffer]` | `setProperty(ENCRYPTED, <saída>)` em u1/u3/u5/f1/f2/f3/f5/f7 | DIV (projeção 1ª casa; 2ª casa perdida — mesmo mecanismo unário de ALFA-CIP-07). Leitor existe (MacSpec:151-180, encrypt-then-mac): a projeção preserva o uso que o conjunto faz |
| ALFA-CIP-20 | *(não existe no oráculo api30)* `generatedCipher[this]` | `setProperty(GENERATED_CIPHER, c)` nos 3 inits, dentro do `condition()` | DIV **extra-oráculo**: ENSURES do api30 tem só os 3 `encrypted` (Cipher.cryptsl:187-194); a escrita é ancorada no CrySL 1.5.2 (registrada em `divergence_record.csv`). Incoerência interna: transformação **insegura** (g3) ainda marca — o acoplamento documentado "ENSURES à REQUIRES" vale para a chave e não para a c1 |
| ALFA-CIP-21 | *(idem)* `WRAPPED_KEY` em wkb1 | escrita sem leitor e sem ENSURES no api30 | LIM (registrada: `predicate_omissions.csv` WRAPPED_KEY) — efeito morto |

### 2.7 Diagnóstico (transversal)

| Claim | Achado | Status |
|---|---|---|
| ALFA-CIP-06 | `g3` → `unsafeAlg`: qualquer init seguinte gera **dupla acusação** (`UnsafeAlgorithm` do corpo + `InvalidSequenceOfMethodCalls` do `@fail`) — "@fail espúrio junto a erro específico" é critério FAIL do pré-registro §3 | INC (diagnóstico) |
| ALFA-CIP-22 | `__RESET` no `@fail` volta a `start`; eventos seguintes (u/f) não têm transição em `start` ⇒ **cascata** de `InvalidSequenceOfMethodCalls` por chamada | INC (diagnóstico, agrava FP-ruído) |
| ALFA-CIP-23 | mensagem de `reportUnsafeTransformation` cita `AES/PCBC/ISO10126Padding` como exemplo esperado — o próprio util **rejeita** (PCBC ∉ modos de AES, c9) | INC (minor, mensagem enganosa) |

## 3. Busca ativa de FP/FN (pares distinguíveis, independentes do pipeline)

| Par de traces (Java, mesmo objeto) | Difere só em | Regra | Spec | Veredito |
|---|---|---|---|---|
| `gI; init(k); doFinal(p)` × `gI; init(k); init(k); doFinal(p)` | re-init | ambos conformes | 2º: fail | **FP** |
| `gI; init(k); update(p); doFinal()` × `…; update(p); update(p); doFinal()` | nº de updates | ambos conformes | 2º: fail | **FP** |
| `gI; init(k); wrap(k2)` × `gI; init(k); wrap(k2); doFinal(p)` | doFinal após wrap | 2º viola | ambos aceitos | **FN** |
| `gI("AES/CBC/PKCS5Padding")…` × `gI("AES")…` | componente ausente | 2º viola (c9, convenção `""`) | ambos aceitos | **FN** |
| `init(kMon)…` × `init(kNãoMon)` e fim de trace | chave monitorada | 2º viola (REQUIRES) | 2º: silêncio | **FN** terminal |
| `keygen AES→k; gI("DESede…"); init(k)…` × mesmo com keygen DESede | concordância alg | 1º viola | ambos passam | **FN** |
| `init(1,k,ivspec)` CBC com IV preparado × não preparado | preparedIV | 2º viola | 2º: report ✓ | concordam (FID) |

## 4. Claims (esquema completo em `alfa_claims.csv`)

Resolvi como FAIL: CIP-01, 02, 03 (linguagem), 06, 22, 23 (diagnóstico), 07, 08 (generatedKey), 14a (componente ausente), 15, 16, 17, 18 (constraints omitidas), 20 (extra-oráculo/incoerência). PASS: 05, 09, 10, 11, 13, 14 (literais), 19 (com projeção registrada), 12/21 (limitações registradas — bloqueiam aderência total). INCONCLUSIVE: 04 (precedência do oráculo), e a condicionalidade de todos os claims de linguagem ao autômato efetivo (outro agente).

**Veredito preliminar de Alfa (dimensões 1, 3, 4, parte da 6): REPROVADA** no estado atual contra o oráculo api30 cru — dois FP demonstráveis de linguagem (re-init, multi-update), um FN de linguagem (mistura wrap×doFinal), FN de constraint (componente ausente; noCallTo/callTo omitidos) e FN de REQUIRES (2ª casa de generatedKey; supressão terminal D-S9). Nada disso depende de execução; tudo reproduzível por `python3 alfa_automata_check.py` + leitura citada por arquivo:linha.
