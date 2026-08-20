# Auditoria — segunda passada (agente B)

Data: 2026-08-20. Base: `rvsec/rvsec-mop/src/main/resources/{jca,jca_android,jca_android_bug_predicate,generic,generic_new}` (214 `.mop`; cada conjunto jca-family tem 23 `.mop` + 1 `.aj`; `generic_new` 27 `.mop` + 1 `.aj`).
Analisador: `analyze_mop.py` (este diretório) — neutraliza comentários e literais, casa chaves (corpos de evento, handlers `@…`) e parênteses (`condition(...)`), delimita bloco `fsm:`/`ere:`, classifica sítios `validate(Property`/`setProperty(Property`/`remove(Property` por região. Saída bruta: `run2.txt`, `results.json`.

## TAREFA 1 — reprodução dos números da primeira auditoria

| nº alegado | reproduzido | veredito |
|---|---|---|
| `jca_android`: 17 órfãos em 9 specs | 17 em 9 (IvParameterSpec c3,c4; KeyPairGenerator initError; PBEKeySpec err1-3,f1,f2; PBEParameterSpec c3; SSLContext unsafe_protocol; SecretKeySpecSpec c3,c4; SecureRandom c3,g4,setSeed3; Signature g3; TrustManagerFactory g3) | CONFIRMADO |
| `jca`: 18 órfãos em 10 specs | 18 em 10 (os mesmos + MessageDigestSpec `reset`) | CONFIRMADO |
| `jca_android`/`jca`: validate 27, todos em `condition` | 27/27 condition em ambos | CONFIRMADO¹ |
| `jca_android`/`jca`: setProperty 42 body / 7 handler | 42 body + 7 handler (6 `@match`, 1 `@match1`) em ambos | CONFIRMADO |
| `jca_android`/`jca`: remove 8 `@fail` / 1 body | 8 `@fail` + 1 body (`PBEKeySpecSpec` corpo) em ambos | CONFIRMADO |
| `jca_android_bug_predicate`: 0 órfãos | 0 | CONFIRMADO |
| `bug_predicate`: validate 56 (33 condition, 23 fora) | 56 = 33 condition + 18 corpo de evento + 5 corpo de helper (`reportUnrandomized` etc.) | CONFIRMADO |
| `generic`: 1 órfão (`FSM246.mop`, `event_2`) | exatamente 1 | CONFIRMADO |
| `generic_new`: 17 specs sem `fsm`/`ere` | 17 event-only (10 restantes têm `ere`) | CONFIRMADO |

¹ Sutileza que explica por que uma contagem ingênua daria 31, não 27: `KeyPairGeneratorSpec.mop` (nos três conjuntos jca-family) declara um helper **privado chamado `validate(int keySize)`** e o chama 3× dentro de `condition()`. São 4 sítios `validate(` que **não** são leitura de predicado (sem argumento `Property`). O filtro correto é `validate(Property`. O mesmo vale para `remove(`: 10 sítios `.remove(` em `generic`/`generic_new` (Iterator/ListIterator/Map) que nada têm a ver com `ExecutionContext.remove(Property…)`.

## TAREFA 2 — base factual da §8-bis

1. **17 specs event-only em `generic_new`** — CONFIRMADO. Lista: CharSequence_NotInSet, CharSequence_UndefinedHashCode, Closeable_MeaninglessClose, Collection_HashCode, Collections_UnnecessaryNewSetFromMap, Comparable_CompareToNull, Comparable_CompareToNullException, Long_BadParsingArgs, Object_MonitorOwner, Serializable_NoArgConstructor, ServerSocket_Backlog, SortedSet_Comparable, TreeMap_Comparable, TreeSet_Comparable, URLConnection_OverrideGetPermission, URLDecoder_DecodeUTF8, URLEncoder_EncodeUTF8. Bônus: a soma de eventos declarados nelas é **27** — o número de falsos positivos que o plano alega para um gate ingênuo confere.
2. **`generic` não dá verde trivial** — CONFIRMADO: exatamente 1 órfão, `FSM246.mop`, `event_2` (declarado na linha 15, ausente do `fsm` que usa event_1,3,4,5,6,7).
3. **11 arquivos com parâmetro duplicado** — CONFIRMADO, todos no conjunto **`generic`**: FSM119 (r,t), FSM123 (i), FSM133 (j), FSM140 (i), FSM197 (j), FSM206 (j), FSM209 (b,c), FSM224 (s), FSM45 (t), FSM60 (u), FSM69 (c). **Colisão de import em `FSM358.mop`** — CONFIRMADA nas linhas 4 e 6 (`RVMLogging.Level` × `java.util.logging.Level`; a spec declara `FSM358(Level l1, …)`).
4. **Lacunas de design (G-ORDER pular sem regra CrySL; `predicate_graph.csv` vazio = verde; G-PARAM)** — CONFIRMADO que estão escritas na §8-bis do plano (itens 4, 5 e 6 da lista "Seis lacunas"). Nota factual adicional: **nenhuma** das 214 specs atuais tem parâmetro primitivo ou array na lista de parâmetros — o colapso do §7.5 (`byte[]`) é risco *prospectivo* (F3 o introduziria), não estado presente; G-PARAM protege o futuro, não corrige o presente.

## TAREFA 2.5 — candidatas a SÉTIMA lacuna

**S1 (a mais forte) — órfão reverso + evento com nome duplicado no conjunto congelado.**
`jca/GCMParameterSpecSpec.mop` declara `event c1` **duas vezes** (linhas 23 e 34 — a segunda é o construtor de 4 args, claramente destinada a ser `c2`) e o bloco lógico `ere : c1 | c2` (linha 48) referencia **`c2`, que não existe**. Idêntico em `jca_android_bug_predicate/GCMParameterSpecSpec.mop:23,34,48`. O `jca_android` atual já traz `c2` na linha 34 — ou seja, o congelado `jca` e o arquivado divergem estruturalmente do alvo neste ponto. Para a camada de gates: o gate de órfão calculado só como `declarados − usados` passa em silêncio aqui; é preciso também `usados − declarados` (símbolo do autômato sem evento) e tratar o alfabeto como **multiconjunto** (nome declarado 2×). Varredura completa: estes são os únicos 2 casos nos 214 arquivos.

**S2 — sombreamento de nome da API de predicados.** Helpers privados com o mesmo nome dos métodos do `ExecutionContext`: `validate(int)` em `KeyPairGeneratorSpec.mop` (3 conjuntos, 4 sítios cada) e `validate(Object,String)` em `generic_new/TreeMap_Comparable.mop:21,30,41`; mais 10 sítios `.remove(` de coleções em `generic`/`generic_new` (FSM19:11, FSM26:15, FSM29:33, FSM103:15, FSM162:11, FSM226:21, FSM333:12, FSM360:12, ListIterator_Set:22, Map_UnsafeIterator:40). Qualquer gate que conte sítios por nome de método erra; o discriminador obrigatório é o argumento `Property.` (ou o receptor `ExecutionContext.instance()`). A própria diferença 31→27 da auditoria mostra que a armadilha é real dentro do alvo.

**S3 — handler com nome de alias (`@match1`).** Cinco specs por conjunto jca-family usam `alias match1 = <estado>` + handler `@match1` (CipherSpec, SecureRandomSpec, SSLContextSpec, TrustManagerFactorySpec, KeyManagerFactorySpec; ex. `jca_android/CipherSpec.mop:222`). Gate que classifique handlers por nome fixo {`@match`, `@fail`} tem de resolver aliases para estados; senão erra a partição body/handler dos `setProperty` (o 42/7 depende disso).

**Observações menores (não elevadas a lacuna):**
- `creation event` só existe em `generic_new` (10 arquivos) — o parser de alfabeto dos gates precisa aceitar o prefixo.
- No alvo `jca_android`, a lógica dominante é `ere` (18/23; só 5 `fsm`) — G-ACC ("todo acusador tem laço no autômato") precisa de definição para `ere`, onde "laço" não é transição de estado; o plano herda G-ERE da gh104, mas a §8-bis não explicita a assimetria fsm/ere.
- Zero specs sem `@fail` entre as que têm `fsm`; zero arquivos com mais de uma spec; zero eventos sem corpo — três formas que a camada não precisa suportar hoje (mas custaria pouco tolerar).
- 82% multiparamétrico em `generic` confere (97/118 com ≥2 parâmetros).
