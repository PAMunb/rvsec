# Agente D — segunda passada: colapso da lista de parâmetros com `byte[]`/`int[]`/`char[]`

Data: 2026-08-20. Binários usados:
- javamop: `/home/pedro/.../rvsec/javamop/target/release/javamop/javamop/bin/javamop`
- rv-monitor: `/home/pedro/.../rvsec/rv-monitor/target/release/rv-monitor/bin/rv-monitor`

Specs de teste: `scratchpad/agentD/matrix/<variante>/T.mop` — spec `T(Object a, TYPE b, Object c)`,
2 eventos (`e1` liga `a`+`b` via `target`/`args`; `e2` liga `a`+`c`), `ere: e1 e2`, variando só TYPE.

## TAREFA 1 — matriz de fumaça (medida, não inferida)

| TYPE do meio | rc javamop | mensagem | cabeçalho do `.rvm` | rc rv-monitor | `CachedWeakReference` no monitor |
|---|---|---|---|---|---|
| `byte[]`   | 0 | "T.rvm is generated / TMonitorAspect.aj is generated" | `T()` — **lista INTEIRA apagada** | 0 | **0** (global) |
| `int[]`    | 0 | idem | `T()` — apagada | 0 | **0** (global) |
| `char[]`   | 0 | idem | `T()` — apagada | 0 | **0** (global) |
| `Object[]` | 0 | idem | `T(Object a, Object[] b, Object c)` | 0 | 17 |
| `Object`   | 0 | idem | `T(Object a, Object b, Object c)` | 0 | 17 |
| `String`   | 0 | idem | `T(Object a, String b, Object c)` | 0 | 17 |
| controle `SafeSyncMap.mop` | 0 | sucesso | `SafeSyncMap(Map syncMap, Set mapSet, Iterator iter)` (nota: o `+` de `Set+` é normalizado) | 0 | 28 |

Detalhes medidos que refinam a primeira auditoria:
1. **`char[]` COLAPSA** — agora medido, não mais inferido por analogia. Atinge o `PBEKeySpec`.
2. O colapso apaga a lista **inteira**, inclusive os parâmetros `Object a` e `Object c` que sozinhos
   seriam válidos — um único tipo primitivo-array envenena a lista toda (é um parse all-or-nothing).
3. **Os eventos MANTÊM seus parâmetros** no `.rvm` (`event e1(Object a, byte[] b)`) e o `.aj` ainda
   liga `target(a) && args(b)` e passa `(a, b)` ao monitor — mas o monitor gerado tem
   `matchedEntry = T__Map;` (campo global único, sem indexing tree): os argumentos chegam e são
   ignorados para fatiamento. O colapso é invisível no aspecto; só aparece no cabeçalho do `.rvm`
   e na ausência de `CachedWeakReference`/`IndexingTree` no `*RuntimeMonitor.java`.
4. **Silêncio total no pipeline normal**: javamop não imprime NADA de erro (o `e.printStackTrace()`
   está comentado no código), rc=0, mensagens de sucesso. rv-monitor recebe um `.rvm` já colapsado
   e válido, então também nada acusa.
5. Bônus (reforça R6): até um erro DURO de parse de pointcut (ex.: `java.io.OutputStream+` —
   qualified name + `+` não é aceito) imprime stack trace mas **sai com rc=0**. O rc do javamop é
   inútil como gate; G-PARAM tem de inspecionar o artefato.

## TAREFA 2 — causa raiz (arquivo:linha)

O defeito é uma **assimetria de gramática + catch silencioso**, presente NOS DOIS tradutores:

**javamop** (`.mop` → `.rvm`):
- `src/main/javacc/javamop/parser/main_parser/javamop.jj:1456` — `SimpleTypePattern()`, usado por
  `MOPParameter()` (linha 1369) para os parâmetros da SPEC, só aceita `<IDENTIFIER>|"get"|"set"`
  como cabeça do tipo. `byte`/`int`/`char`... são keywords Java, não IDENTIFIER → `byte[] b` gera
  ParseException. `Object[]` passa porque `Object` é IDENTIFIER e `("[" "]")*` é aceito.
- `javamop.jj:1470` — `TypePattern()`, usado por `AdviceParameter()` para parâmetros de EVENTO,
  aceita explicitamente `"byte"|"short"|"int"|"long"|"float"|"double"|"boolean"|"char"`. Por isso
  os eventos preservam `byte[]` e só a spec colapsa.
- `src/main/java/javamop/parser/JavaParserAdapter.java:320-327` — `convertParameters()`:
  ```java
  try { return parseJavaBubble(paramString).MOPParameters(); }
  catch(Exception e) { /* e.printStackTrace(); */ return null; }
  ```
  O catch engole a ParseException (stack trace COMENTADO) e devolve `null` → a spec é construída
  com lista vazia (`JavaParserAdapter.java:261`) → cabeçalho `T()` no `.rvm`. Este é o ponto exato
  do apagamento silencioso. Não é o resolvedor de tipos nem o dumper (`DumpVisitor.java:354` só
  imprime o que restou).

**rv-monitor** (`.rvm` → monitor) — espelho exato do defeito:
- `rv-monitor/src/main/javacc/.../main_parser/RVMonitorParser.jj:876` — mesmo `SimpleTypePattern()`
  restrito para parâmetros de spec (e mesmo `TypePattern()` permissivo para eventos).
- `rv-monitor/src/main/java/.../rvj/JavaParserAdapter.java:233-240` — mesmo catch devolvendo
  `null`, mas aqui o `e.printStackTrace()` está ATIVO. Medido: alimentando um `.rvm` consertado à
  mão com `T(Object a, byte[] b, Object c)`, o rv-monitor imprime a ParseException, **ainda assim
  gera** `TRuntimeMonitor.java` global (0 CachedWeakReference) e sai com rc=0.

**Existe correção barata a montante? SIM, mas em DOIS lugares, não um.** Um patch só no javamop é
insuficiente: o rv-monitor re-parseia o `.rvm` e colapsaria de novo. Esboço (NÃO aplicado):

1. Em `javamop.jj:1456` e `RVMonitorParser.jj:876`, adicionar à cabeça de `SimpleTypePattern()` um
   ramo para primitivos exigindo pelo menos um `[]` (primitivo nu não tem identidade e não pode
   fatiar):
   ```javacc
   (
     (<IDENTIFIER> | "get" | "set") { ... id = token.image; }
     ("." (<IDENTIFIER>|"get"|"set") { id += "." + token.image; })*
     ("[" "]" { id += "[]"; })*
   |
     ("byte"|"short"|"int"|"long"|"float"|"double"|"boolean"|"char") { ... id = token.image; }
     ("[" "]" { id += "[]"; })+        // + : obriga array
   )
   ["+" { id += token.image; }]
   ```
2. Em ambos os `convertParameters()`, trocar `return null` por relançar (`throw new
   ParseException(...)`) — mata o silêncio de vez, mesmo para tipos futuros não previstos.

Viabilidade downstream: os arrays são reference types; a indexação embrulha o valor em
`CachedWeakReference(Object)` e o código gerado declara o tipo textual (`byte[]` é Java legal). O
caso `Object[]` já passa de ponta a ponta com 17 `CachedWeakReference`, o que evidencia que a
maquinaria de fatiamento aceita arrays — o bloqueio é SÓ léxico/gramatical. Validação obrigatória
do patch: um smoke compile do monitor gerado + o caminho `-emit-descriptor` (dexlib2) com `byte[]`.
O projeto já mantém patch local no javamop (descritor JSON), então há precedente de processo; o
custo real é regenerar javacc e rebuildar o reator (javamop E rv-monitor).

**Impacto na D4**: a premissa "byte[] não pode ser parâmetro de spec" é limitação de toolchain
reparável, não limitação semântica do MOP paramétrico. As opções passam a ser: (i) idioma `Object`
sem tocar toolchain (funciona hoje), (ii) patch duplo de gramática (remove o idioma, declara o tipo
verdadeiro). G-PARAM continua necessário nos dois casos — é ele que pega regressões e o próximo
tipo surpresa.

## TAREFA 3 — o contorno via `Object`

Confirmado no gerado de `matrix/obj/`:
- `TMonitorAspect.aj:40-42`: `pointcut T_e1(Object a, Object b) : call(...) && target(a) && args(b)`
  — liga o argumento `byte[]` do runtime a um parâmetro `Object`.
- `TRuntimeMonitor.java`: fatiamento via `new CachedWeakReference(a|b|c)` alimentando indexing
  trees (17 ocorrências).
- `rv-monitor-rt/.../ref/CachedWeakReference.java:16`: `System.identityHashCode(ref)` cacheado;
  `hashCode()` devolve esse valor; a classe NÃO sobrescreve `equals`.
- Os lookups das tabelas (`RVMBasicRefMapOfSet.java:51` etc., `WeakRefHashTable.java:474`) comparam
  `key == entry.key.get()` — **identidade de referência pura**, nunca `equals`/`hashCode` de
  conteúdo. Arrays Java nem sobrescrevem `hashCode` (herdam identidade), então não existe armadilha
  de hash de conteúdo nem instabilidade quando o array é preenchido in-place (`nextBytes(iv)` muda
  o conteúdo, não a identidade). Indexação por identidade genuína: CONFIRMADA.

Duas ressalvas de uso (refinamentos, não refutações):
1. **Seleção de overload**: `args(b)` com `Object b` casa QUALQUER argumento único, inclusive
   primitivos via autoboxing (ex.: `write(int)` além de `write(byte[])`). O idioma exige fixar o
   overload na assinatura do `call(...)` — como a auditoria já faz em
   `call(void SecureRandom.nextBytes(byte[])) && args(b)`, que está correto. A disciplina precisa
   virar regra do idioma: com parâmetro `Object`, o tipo casa no `call()`, nunca no `args()`.
2. WeakReference: o slice vive enquanto o `byte[]` for fortemente alcançável no app — comportamento
   padrão de qualquer parâmetro de spec, sem diferença para arrays.

## Vereditos

| Item | Veredito | Base |
|---|---|---|
| (a) colapso `byte[]`/`int[]` | **SUSTENTADO** | Matriz: cabeçalho `T()`, 0 CachedWeakReference; controle preserva. Refinado: a lista INTEIRA morre (inclusive params válidos), e o `.aj` continua ligando args — o colapso só é visível no `.rvm`/monitor. |
| (b) `char[]` colapsa? | **SUSTENTADO (agora medido)** | `T()` vazio, 0 CachedWeakReference — a inferência por analogia da 1ª auditoria estava certa. |
| (c) silêncio do erro | **SUSTENTADO e agravado** | javamop: catch com printStackTrace COMENTADO (`JavaParserAdapter.java:323`), rc=0, mensagem de sucesso. Agravante: até parse error duro de pointcut sai com rc=0. rv-monitor imprime stack trace mas gera monitor global e sai rc=0 mesmo assim. |
| (d) contorno via `Object` | **SUSTENTADO com refinamento** | Identidade genuína confirmada (identityHashCode + `==` no lookup; arrays sem hash de conteúdo). Refinamento obrigatório do idioma: fixar o overload no `call()`, pois `args(Object)` casa autoboxing. |
| (e) causa raiz + correção barata | **REFINADO** | Não é "o tradutor apaga": é `SimpleTypePattern()` (spec) vs `TypePattern()` (evento) — gramática assimétrica — mais catch-engole-e-devolve-null, **duplicado em javamop E rv-monitor**. Correção barata existe (2 gramáticas + destravar o catch), com precedente de patch local; patch só no javamop NÃO basta. |
