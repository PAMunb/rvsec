# Investigação — o grafo de predicados e o suporte a pointcut designators no weaver dexlib2

**Data:** 2026-08-06 (revisão 3)
**Estado:** investigação concluída e **verificada adversarialmente** por sessão independente (2026-08-06; vereditos na §8). Nada implementado; nenhum `.mop`, nenhuma fonte do weaver, nada sob `ase-journal/` e nenhum APK ou repositório do dataset foi modificado.

> **Revisão 2** — a rev. 1 registrava em §7 que nenhum APK havia sido tecido e que a cadeia da colisão era derivação, não observação. Os APKs instrumentados da campanha estavam disponíveis o tempo todo em `RV_ANDROID_NOVO_DATASET/`, e o código-fonte dos apps em `rvsec-dataset/repos/`. A §3.7 é nova e converte o principal resultado de derivação em observação, com triangulação fonte → bytecode → dado. Duas afirmações minhas da rev. 1 foram **refutadas pela observação** e estão corrigidas na §3.2.

> **Revisão 3 (verificação adversarial)** — sessão independente re-derivou as 30 alegações (B1–B6, G1–G12, A1–A12) dos artefatos primários; tabela de vereditos na §8. O núcleo sobreviveu inteiro — a colisão, a direção do defeito, a difusão e a datação fail-closed foram **confirmadas e generalizadas** (censo em 219/219 APKs; jar da campanha datado por prova binária). Correções aplicadas nesta revisão: **(a)** manchete da §4.4: 92% → **83%** de `ENSURES` presentes — a própria decomposição (33+1+2+2=38) contradizia o 42; ausentes de `REQUIRES` 27 → **28**; **(b)** §4.2: "43 das 49 escritas sem leitor" → **35**; **(c)** §4.5: 38 → **37** arestas, e o balde "inexpressível" **não é vazio** (`randomized[lSeed]`); **(d)** §4.4: `generatedSSLEngine` tem segundo produtor (`SSLContext.crysl:38`) e nenhum consumidor — a consequência estática vale só para `preparedOAEP`; **(e)** §3.6: a explicação dos 208 `X509` por "versões diferentes do okhttp" estava **errada** — o bytecode do sítio é idêntico nos dois apps; o valor vem da difusão de g3 a partir do literal `"X509"` de `de.duenndns.ssl.MemorizingTrustManager`; **(f)** §3.6: os 421 eventos restantes **ganharam mecanismo verificado** (L3.8 confirmada em bytecode, três rotas de criação não cobertas); **(g)** o corpus tem **219** APKs, não 234 (468 arquivos = 219 `.apk` + 219 `.json` + 30 `.pkgdet`); **(h)** `reset()` tem um chamador (teste); **(i)** o "~6,5×" da §4.7 corrigido; **(j)** referências §3.8→§3.7 e §3.4→§2.3 e frase duplicada da §3.2 corrigidas.
**Continua:** `docs/20260806_plano_specs_jca_android.md` (commit `31f7b883`), fase F0.
**Resolve:** a questão G0 do plano (§3, §5), e o item F0.4'.

## Marcadores de confiança

| | significado |
|---|---|
| ✅✅ | verificado contra documentação primária, com URL |
| ✅ | verificado por mim contra fonte do repositório ou dataset, **nesta sessão** |
| ⚠️ | vem de subagente ou relatório anterior, não re-derivado — é pista, não resultado |
| ❌ | verificado e **falso** |

Nenhum ⚠️ foi promovido a ✅ sem re-derivação própria. Onde um subagente e eu chegamos ao mesmo resultado por caminhos diferentes, está marcado ✅ e a dupla derivação está dita.

---

## 0. Sumário executivo

Três resultados mudam decisões do plano.

**1. A G0 estava mal colocada, e está resolvida por observação direta.** As duas hipóteses concorrentes — colisão de wrappers (L3.1) e binding de parâmetro (L3.2) — **são ambas verdadeiras**, e não competem: agem sobre observáveis diferentes. A colisão decide **se** o algoritmo válido chega a ser registrado (é a causa única do valor vazio); o binding vazio decide **onde** um algoritmo inválido registrado aterrissa (é a causa única do `X509` aparecer em sítios que nunca passaram `X509`). O dilema "ou 100% falso positivo, ou observações genuínas" é falso.

✅ Isto **não é dedução**: a §3.7 desmonta o DEX dos APKs instrumentados da própria campanha e mostra que `TrustManagerFactorySpec_g1Event` está compilado no binário e **não é referenciado por nenhuma instrução**, em 4 de 4 APKs; e que `org/conscrypt/SSLParametersImpl` passa `getDefaultAlgorithm()` no bytecode enquanto os dados registram `X509` naquele sítio — contaminação entre instâncias, demonstrada.

**2. A alegação-manchete sobre PCDs é falsa no estado atual do código.** ❌ Os sete-a-nove designators **não** casam-true em silêncio: `matchNamedRef` **falha fechado** com `UnresolvedNamedRefException` desde `3af5b3aa` (2026-05-29) — **antes** da campanha de julho. A superfície real de match-true silencioso é muito menor e está em outro lugar.

**3. O grafo de predicados está pior do que o relatado, e o defeito é assimétrico.** **83%** das cláusulas `ENSURES` do CrySL têm contrapartida escrita (corrigido na rev. 3 de 92% — ver §4.4); apenas **22% dos `REQUIRES` têm leitura**. A tradução produz predicados com fidelidade e quase não os consome.

---

## 1. O que a sintaxe do JavaMOP admite — e por que isso importa

✅✅ Fonte primária: [JavaMOP4 Syntax, FSL/UIUC](https://web.archive.org/web/20190327032914/http://fsl.cs.illinois.edu/index.php/JavaMOP4_Syntax) (página arquivada; a original saiu do ar). Cópia em texto no scratchpad da sessão.

A gramática BNF define:

```
<Event>            ::= ["creation"] "event" <Id> <AspectJ advice> "{" [ <Java Statements> ] "}"
<AspectJ Advice>   ::= [ "strictfp" ] <AspectJ AdviceSpec> [ "throws" <TypeList> ] ":"
                          <Pointcut> [ "&&" <JavaMOP Pointcut> ] "{" <Java Statement> "}"
<JavaMOP Pointcut> ::= "thread" "(" <Id> ")" | "condition" "(" <BooleanExpression> ")" | ...
<Pointcut>         ::= ... <!-- syntax of Pointcut in AspectJ -->
```

O ponto decisivo, verbatim da página: *"`<Pointcut>` and `<AspectJ AdviceSpec>` are both standard AspectJ syntax."*

**O JavaMOP não restringe nada.** Qualquer PCD que o AspectJ aceite é sintaticamente legal num `.mop`. Some-se a isso o fato ✅ de que o `DescriptorWriter` grava a expressão **verbatim, sem filtrar** (`javamop/src/main/java/javamop/output/descriptor/DescriptorWriter.java:114-117`), e a conclusão é que **toda** a restrição de PCD vive no matcher do dexlib2. É por isso que a §4.1 do plano é uma questão de autoria e não só de engenharia: nada entre o `.mop` e o weaver diz "não".

A página também documenta ✅✅ as quatro variáveis especiais (`__RESET`, `__LOC`, `__SKIP`, `__STATICSIG`) e que `__STATICSIG` devolve um `org.aspectj.lang.Signature` — o que explica o shim em `rvsec-core` (§2.3).

---

## 2. INVESTIGAÇÃO B — matriz de suporte a PCD

### 2.1 A matriz

Derivada da fonte em `rvsec-android/rvsec-instrumentation-dexlib2`. Linhas em itálico são as que contradizem o plano.

| PCD | Parseado (nó) | Casado | Emitido | Bindings | Modo de falha |
|---|---|---|---|---|---|
| `call(...)` | ✅ `CallPC` — `PointcutExpressionParser.java:134` | ✅ real: owner exato/`T+`, glob de nome, retorno, aridade, tipos — `PointcutMatcher.java:308-406` | ✅ Before/After/AfterReturning/AfterThrowing | ✅ `arg00..argNN`, `targetRegister`, `$return` — `:412-485` | drop silencioso **com contador** (`plansSkippedUnresolvedBinding`, `DexWeaver.java:439-459`) |
| *`execution(...)`* | ✅ `ExecutionPC` — `Parser:135` | ❌ **stub** — `PointcutMatcher.java:509-515`: única guarda é `instructionIndex != 0`; o `signaturePattern` **nunca é lido** | sem emissor próprio | **nenhum** (`Match.empty`) | **match-true silencioso, sem contador** |
| `staticinitialization(...)` | ✅ `StaticInitPC` — `Parser:139` | ✅ real: gate `<clinit>`, `T+` via `InheritanceResolver` — `:517-529` | ✅ inclui **sintetizar** `<clinit>` — `DexWeaver.java:616-626` | não | skip silencioso, **sem contador** |
| `args(nomes)` / `target(nome)` | ✅ `ArgsPC`/`TargetPC` | true inerte **por desenho** (é binding, não filtro) | — | ✅ indireto, via o `CallPC` irmão | intencional |
| `args(Tipo)` / `target(Tipo)` | ✅ | ✅ real, posicional, `..` e `*`, subtipo | — | não | correto |
| `!within(...)` | ✅ `NotWithinPC` — `Parser:81-85` | ✅ real, padrão de tipo — `:178-184` | — | não | — |
| *`within(...)` positivo* | ✅ `WithinPC` — `Parser:138` | ❌ **true constante** — `:134-138`; `typePattern()` nunca lido | — | não | **match-true silencioso** |
| `if(expr)` | ✅ `IfPC` | true constante no matcher | ✅ 2 formas apenas (`x==null`, `!Thread.holdsLock(x)`) — `IfGuardEmitter.java:52-95` | consome binding existente | **alto** para 3ª forma; **aborta o weave** (não capturado) |
| `adviceexecution()` | ✅ (caso especial) | true constante — `:158-160` | — | não | intencional |
| *`!adviceexecution()`* | ⚠️→✅ `NamedRefPC` lossy — `Parser:100-101` | ❌ o teste `name.contains("adviceexecution")` ainda casa → **a negação é descartada** | — | não | **match-true silencioso** |
| **`withincode`, `initialization`, `preinitialization`, `handler`, `cflow`, `cflowbelow`, `get`, `set`, `this`** | `default:` → `NamedRefPC` — `Parser:142` | ❌❌ **`throw UnresolvedNamedRefException`** — `PointcutMatcher.java:161` | — | — | **alto** no laço principal; **false silencioso** na sonda do `commonPointcut` (`DexWeaver.java:695-700`) |
| `@annotation` e família `@` | ❌ nem parseia (`isIdentPart` exclui `@`) → `PointcutParseException` | — | — | — | drop **com contador** — `parseCached:843-847` engole a exceção, mas o chamador incrementa `plansSkipped` (`DexWeaver.java:406`) |
| `around` | — | — | rejeitado — `EmitterDispatch.java:61-65` | — | vira `plansSkipped++` em `DexWeaver.java:419-424` — **não é alto no weave** |
| `condition(...)` (JavaMOP) | — | — | — | — | absorvido pelo javamop antes do descritor (§2.3) |
| `thread(...)` (JavaMOP) | ausente do dexlib2 | — | — | — | **não documentado, sem teste, sem linha de matriz** |

### 2.2 ❌ A alegação central do plano está errada

O plano (§4.1, §15) afirma que nove PCDs *"caem no `default` do parser → `NamedRefPC` → **match-true** no matcher"*. **Isso é falso no estado atual do código.**

```java
// PointcutMatcher.java:150-162
private Optional<Match> matchNamedRef(NamedRefPC nr, Context ctx) {
    String name = nr.name();
    if ("BaseAspect.notwithin()".equals(name)) { ... }
    if (name.contains("adviceexecution")) { return Optional.of(Match.empty(nr)); }
    throw new UnresolvedNamedRefException(ctx.aspectName, name);   // <-- falha FECHADA
}
```

✅ A própria classe `UnresolvedNamedRefException` documenta a mudança: *"G-decision fail-closed: replaces the round-7 always-match-with-WARN trap"*. ✅ O commit é `3af5b3aa`, **2026-05-29** (`feat(gh62): NamedRefPC resolves BaseAspect.notwithin ... fail-closed`) — anterior à campanha `experimento-20260706`. Logo a alegação não vale nem para o código de hoje nem para os dados do artigo.

> **Rev. 3 — o "antes da campanha" deixou de ser suposição.** A campanha rodou o `instr-cli.jar` do gh73 (fix `d73ebc41`, 2026-06-30, ~1h antes da instrumentação; bind-mount documentado em `rvsec-dataset/docs/20260702_phase8-instrumentation-results.md:26`), que é descendente de `3af5b3aa` por 77 commits (`git merge-base --is-ancestor` confirma). Prova independente de documentação: **130 dos 219 APKs instrumentados contêm entradas DEX `037`/`038`/`039`**, e o weaver pré-gh73 estampava `dex035` incondicionalmente — o binário da campanha necessariamente contém o fail-closed. Nenhum commit posterior a `3af5b3aa` reabriu `matchNamedRef` (histórico de `PointcutMatcher.java` verificado commit a commit).

**Reconciliação da contagem que o brief mandou fazer:** a lista tem **nove** nomes, não sete. Nenhum dos nove casa-true. O número correto de PCDs que casam-true em silêncio é **três**, e são outros: `execution(...)`, `within(...)` positivo e `!adviceexecution()`.

**O risco real é outro, e é pior porque é fail-open.** ✅ `DexWeaver.parseCommonPointcut:856-864` devolve `null` quando o parse falha, e o chamador trata `null` como "sem exclusões" — ou seja, **uma expressão malformada no `commonPointcut` remove todas as exclusões daquele weave**. Isso é degradação fail-open, ao contrário de tudo o mais.

### 2.3 Uso real de PCD nos conjuntos de specs

⚠️→✅ (derivado mecanicamente, script no scratchpad):

| conjunto | arquivos | eventos | ocorrências de PCD |
|---|---:|---:|---:|
| `jca` | 23 `.mop` | 134 | 363 |
| `generic` | 118 `.mop` | 436 | 888 |
| `generic_new` | 27 `.mop` | 61 | 189 |
| `aspect` | 1 `.aj` | 3 | 27 |

`call` 669 · `target` 478 · `args` 211 · `condition` 74 · `within` 24 · `if` 5 · `staticinitialization` 3 · `execution` 1.

❌ **"116 pointcuts, todos `call(...)`" está errado como número.** O correto é **144 ocorrências de `call(`**, **122 assinaturas distintas**, **134 eventos**. Nenhuma métrica derivável dá 116. A afirmação **qualitativa** sobrevive e é o que importa: no `jca` o único PCD de join point é `call`; zero `execution`; zero `thisJoinPoint`.

✅ **Zero PCDs fora do conjunto suportado em qualquer spec.** As únicas ocorrências de `execution`, `within` positivo e pointcut nomeado estão em `aspect/Coverage.aj` — o aspecto de cobertura, não uma spec de RV. ✅ Zero `around` em todo o corpus. ✅ Zero `__SKIP`.

✅ `__STATICSIG` aparece 3 vezes, todas em `generic_new`, e é de fato a razão do shim: `rvsec-core/src/main/java/org/aspectj/lang/Signature.java` e `ClassSignature.java` são os dois únicos arquivos sob `org/aspectj/` no core.

### 2.4 Um achado não previsto: 23 advices `execution(...)` no aspecto gerado

✅ O `.aj` gerado do `jca` tem **138** advices; o descritor JSON tem **115**. A diferença são 23 advices injetados pelo javamop, um por spec:

```java
after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
    System.err.println("==start KeyPairSpec ==");
```

✅ A origem é `javamop/src/main/java/javamop/output/combinedaspect/MOPStatistics.java:78`. Alvo: uma classe do **Maven Surefire**, irrelevante para um APK.

Se chegassem ao weaver seriam catastróficos: `execution(...)` é o stub que casa a entrada de **todo** método. ✅ **Não chegam** — o `DescriptorWriter` não os emite (`grep ForkedBooter` no descritor = 0; a única ocorrência de `execution` no JSON é o substring dentro de `!adviceexecution()` do `commonPointcut`). Portanto ✅ **o match-true de `execution(...)` não é alcançável em produção para o `jca`** — fecha a questão em aberto nº 1 do levantamento. Mas a margem é fina e não é intencional: depende de um filtro do `DescriptorWriter`, não de uma checagem.

---

## 3. A questão G0 — colisão de wrappers × binding de parâmetro

### 3.1 O mecanismo, verificado ponta a ponta

**Passo 1 — o javamop funde ou não funde advices.** ✅ Dois eventos viram **um** advice com duas chamadas de monitor quando coincidem posição, formais, o **nome** do binding `returning(...)` e a expressão do pointcut. Caso contrário viram **dois** advices.

`KeyManagerFactorySpec.mop` — g1, g2 e g3 usam todos `returning(KeyManagerFactory k)`. Fundidos (`MultiSpec_1MonitorAspect.aj:677-682`):

```java
after (String alg) returning (KeyManagerFactory k) : KeyManagerFactorySpec_g1(alg) {
    MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_g1Event(alg, k);
    MultiSpec_1RuntimeMonitor.KeyManagerFactorySpec_g3Event(alg, k);
}
```

`TrustManagerFactorySpec.mop` — g1 usa `returning(TrustManagerFactory mf)` (`:28`) e g3 usa `returning(TrustManagerFactory k)` (`:44`). **Não** fundidos: dois advices, mesmo pointcut.

> Uma diferença de um único token — `mf` contra `k` — decide se a spec é segura ou defeituosa. Não há como um revisor humano ver isso.

**Passo 2 — o descritor registra os dois.** ✅ Verificado no descritor real (`descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json`; ⚠️→✅ um subagente confirmou que este arquivo é byte-idêntico a saída real do pipeline em `rv-android/data/validacao_ajc/local_A_dex/monitors/`):

| índice | `name` | `position` | `expression` | chama |
|---|---|---|---|---|
| 110 | `TrustManagerFactorySpec_g1` | `after` | `call(public static TrustManagerFactory TrustManagerFactory.getInstance(String)) && args(alg)` | `..._g1Event` |
| 112 | `TrustManagerFactorySpec_g1` | `after` | *(byte-idêntica)* | `..._g3Event` |

Nome **igual**, expressão **igual**. O `condition(...)` foi removido do pointcut e rebaixado para dentro do monitor (§3.3), então nada distingue as duas entradas.

**Passo 3 — o weaver colide.** ✅

```java
// WrapperEmitter.java:211  -- itera por ADVICE
for (AdviceDescriptor advice : descriptor.getAdvices()) {
    if (!shouldWrap(advice)) continue;        // :139  -> só "after"
// WrapperEmitter.java:484-488 -- desambigua só o NOME
String baseName = cc.declFqn.replace('.','_') + "_" + cc.methodName;
String wrapperName = count == 0 ? baseName : baseName + "_" + count;
// DexWeaver.java:145-146 -- a CHAVE ignora tudo isso
String key = origClassDesc + "#" + w.originalMethodName + "(" + String.join(",",origParamDescs) + ")" + origReturnDesc;
// DexWeaver.java:159
wrapperReplacements.put(key, wrapperRef);     // LinkedHashMap, put nu
```

Os dois advices ganham **nomes de wrapper distintos** (ambos são compilados para dentro de `mop.MonitorWrappers`) e **uma única entrada de mapa**. `put` é silencioso: sem `containsKey`, sem contador, sem log. O índice 112 (g3) registra por último → **g3 vence, o wrapper de g1 é código morto**.

✅ Detalhe que fecha a leitura de intenção: um guard de dedup para **exatamente esta forma de chave** existe 50 linhas abaixo, em `DexWeaver.java:208` (`if (wrapperReplacements.containsKey(subKey)) continue;`), para o caminho de aliasing de subtipo. Nunca foi aplicado ao registro primário.

### 3.2 O censo

Fiz o censo por três caminhos, o último deles **direto sobre os APKs instrumentados da campanha** (§3.7) — que é o que fecha a questão.

| caminho | resultado |
|---|---|
| meu censo **literal**, sobre o `.aj` de 2026-07-08 (sem expansão de sobrecargas) | 3 chaves colidentes, 3 wrappers mortos — **limite inferior declarado** |
| censo com **expansão real** ⚠️→✅ (re-implementação de `expandCallTarget`→`buildEntry`→`registerWrapper` contra um `android.jar`) | **7 assinaturas, 9 wrappers mortos** |
| ✅ **observado no DEX tecido** de `com.etesync.syncadapter_20700` (§3.7) | **10 assinaturas disputadas, 19 wrappers mortos** naquele APK |

> **Rev. 3 — censo estendido ao corpus inteiro.** A verificação adversarial rodou o censo observado nos **219/219** APKs da campanha: todos têm exatamente **96 wrappers declarados e as mesmas 10 assinaturas disputadas**; em **nenhum** APK um wrapper de g1 tem call site; o vencedor é **sempre o último wrapper declarado** da assinatura (consistente com *last-writer-wins*), e nunca há dois wrappers da mesma assinatura ambos com call sites. Mortos em assinatura disputada: mín. 15, máx. 22, mediana 19 (varia só com o uso da API pelo app). Alcançabilidade alternativa de `g1Event` excluída por varredura: sem reflexão (`const-string` com nomes de wrapper/evento = 0), sem segunda classe de wrappers, sem call site residual não reescrito (os únicos `invoke` diretos a `TrustManagerFactory.getInstance(String)` estão dentro dos corpos dos próprios wrappers). Duas colisões adicionais confirmadas no corpus: `Cipher.doFinal()` (f1 morto, f2 com 230 call sites em 162 APKs) e `SecureRandom.getInstance(String)` (g1/g2 mortos, g4 com 118 call sites).

O censo literal **subestima**, e a razão importa: a chave usa o padrão literal de `call(...)`, mas `getInstance(String, ..)` é expandido pelo `AndroidClassIndex` e o `..` casa **zero ou mais** argumentos — logo g2 gera também um wrapper de **um** argumento, que disputa a mesma chave que g1 e g3. Foi o que a observação mostrou.

Veredito por linha do censo relatado no brief, agora contra o DEX observado:

| Assinatura | relatado | observado (§3.7) | veredito |
|---|---|---|---|
| `TrustManagerFactory#getInstance(String)` | perde g1, g2 · vence g3 | perde g1 (0 call sites), perde g2 (0) · **vence g3 (7)** | ✅ **exato** — e refuta meu próprio censo literal, que dizia que g2 não colidia |
| `SSLContext#getInstance(String)` | perde g1 · vence `unsafe_protocol` | perde g1 (0) · **vence `unsafe_protocol` (3)** | ✅ **exato** |
| `SecureRandom#getInstance(String)` | perde g1, g2 · vence g4 | 6 assinaturas disputadas entre g1/g2/g4; nenhuma exercida neste APK | ✅ **confirmado** estruturalmente |
| `KeyManagerFactory#getInstance(String)` | perde g1, g3 · vence g2 | perde o wrapper g1+g3 **fundido** (0) · **vence g2 (2)** | ⚠️ **parcial** — javamop fundiu g1 e g3 num só advice, então é 1 wrapper morto carregando 2 eventos, não 2 wrappers |

⚠️ Três colisões faltavam no censo relatado (`Cipher#doFinal()` f1→f2 e sobrecargas extras de `SecureRandom.getInstance`), todas confirmadas na observação.

### 3.3 O defeito tem direção — e a direção fabrica falso positivo

✅ Nas duas specs onde a colisão explica o valor vazio, **o advice que morre é sempre o que registra o algoritmo VÁLIDO**:

| spec | advice morto | guarda | advice sobrevivente | guarda |
|---|---|---|---|---|
| `TrustManagerFactorySpec` | `g1` | `condition(algorithms.contains(alg))` | `g3` | `condition(!algorithms.contains(alg))` |
| `SSLContextSpec` | `g1` | `condition(protocols.contains(protocol.toUpperCase()))` | `unsafe_protocol` | `condition(!protocols.contains(...))` |

Isso não é acaso de ordenação: o javamop emite o evento do caso válido primeiro e o do caso inválido depois, e *last-writer-wins* mata sistematicamente o registrador do caso válido. **O defeito produz falso positivo, nunca falso negativo.**

✅ E o `condition(...)` de fato desce para dentro do monitor, não para o pointcut — `MultiSpec_1RuntimeMonitor.java:10098-10102`:

```java
final boolean Prop_1_event_g1(String alg, TrustManagerFactory mf) {
    { if ( ! (algorithms.contains(alg)) ) { return false; }
      { trustManagerFactory = mf; currentAlgorithmInstance = alg; } }
```

### 3.4 O outro mecanismo: g3 vive na fatia de parâmetro vazio

✅ `MultiSpec_1RuntimeMonitor.java`, comparando os dois despachos:

- `TrustManagerFactorySpec_g1Event` (`:17669`) indexa `TrustManagerFactorySpec_mf_Map` — mapa **chaveado pelo parâmetro `mf` da spec**. Fatiamento paramétrico correto.
- `TrustManagerFactorySpec_g3Event` (`:17865`) indexa `TrustManagerFactorySpec__Map` — a **fatia de parâmetro vazio** — e termina em `stateTransitionedSet.event_g3(alg, k)`, isto é, **difunde o evento para o conjunto inteiro de monitores**.

Causa: g3 declara `returning(TrustManagerFactory k)` e `k` **não é** o parâmetro da spec. O mesmo vale para `gtm1`, que usa `target(k)`. Dois dos cinco eventos da spec não ligam o parâmetro monitorado.

✅ E as tabelas de transição (`:10034-10038`) mostram o efeito:

```java
static final int Prop_1_transition_g1[]   = {2, 2, 3, 3};
static final int Prop_1_transition_g3[]   = {3, 3, 3, 3};   // g3 leva a FAIL de QUALQUER estado
static final int Prop_1_transition_init[] = {3, 3, 1, 3};   // init a partir de start(0) -> FAIL(3)
```

(estados: 0 = `start`, 1 = `final`/`match1`, 2 = `waitingInit`, 3 = `fail`)

`g3` não aparece na `fsm` do `.mop` — logo o gerador lhe dá transição para `fail` em todo estado. Combinado com a difusão: **uma única chamada `getInstance` com algoritmo fora da allow-list derruba para `fail` todos os monitores de `TrustManagerFactory` vivos no processo**, e escreve o algoritmo dela em todos.

### 3.5 O veredito

Os dois mecanismos são reais e agem sobre observáveis diferentes. O dilema do brief é falso.

| | causa | observável que produz | veredito sobre os eventos |
|---|---|---|---|
| **(a)** colisão de wrappers | o registrador do caso válido morre | **o valor vazio** | artefato de instrumentação, 100% |
| **(b)** binding vazio + difusão | o registrador do caso inválido difunde | **`X509` em sítios que nunca o passaram** | valor genuíno, **atribuição de sítio falsa** |

Encadeamento sob (a), para `TrustManagerFactory.getInstance("PKIX")` — o que `okhttp3...Platform.platformTrustManager` passa via `getDefaultAlgorithm()`:

1. g1 está morto → nada é registrado.
2. g3 dispara, mas sua guarda é `!contains("PKIX")` = falsa → `return false`, sem transição, sem escrita.
3. `currentAlgorithmInstance` permanece no inicializador `""` (`.mop:24`).
4. `init` é advice **`before`** → `shouldWrap` é falso → caminho inline, **sem wrapper, sem colisão** → dispara normalmente e liga `mf`.
5. Guarda de `init` (`.mop:55`): `!algorithms.contains("")` = **verdadeira** → emite `UnsafeAlgorithm`, *"expecting one of PKIX,SunX509 but found ."* ← **o valor vazio**.
6. `transition_init[0] = 3` = `fail` → emite **também** `InvalidSequenceOfMethodCalls`.

O passo 6 explica ⚠️ o achado estrutural de que **todas** as 454 tuplas de misuse único emitem um `InvalidSequenceOfMethodCalls`: os erros vêm em par.

### 3.6 Confronto com os dados

⚠️→✅ Os cinco specs com valor vazio e seus eventos (8.843 no total, confirmando exatamente o número relatado):

| spec | eventos | colisão no censo? | explicado por (a)? |
|---|---:|---|---|
| `TrustManagerFactorySpec` | 8.371 | ✅ g1 morto | **sim** |
| `SSLContextSpec` | 51 | ✅ g1 morto | **sim** |
| `SignatureSpec` | 234 | ❌ não | **não** |
| `MessageDigestSpec` | 156 | ❌ não | **não** |
| `MacSpec` | 31 | ❌ não | **não** |

**A colisão explica 8.422 de 8.843 — 95,2%.** Os 421 restantes (4,8%) **não** são explicados por ela — e a rev. 3 fechou os dois lados:

- ✅ **A atribuição dos 8.422 agora é por evento, não só por spec.** Os 9 sítios que geram 100% desses eventos (7 do TMF: `Platform.platformTrustManager` 7.174, `TlsUtil.newTrustManager` 584, `Util.platformTrustManager` 324, `TLSConfigBuilderKt.findTrustManager` 219, `AdvancedX509TrustManager.<init>` 27+24, `SSLParametersImpl.createDefaultX509TrustManager` 19; 2 do SSLContext: `HttpClient.getOkHttpClient` 27+24) foram lidos em bytecode de 8 apps distintos: **todos** criam o objeto via `getDefaultAlgorithm()`/literal → sobrecarga de **1 arg** → o wrapper colidido (`_4`/`_2`). Nenhum passa pelas sobrecargas de 2 args (que não perderam a colisão).
- ✅ **Os 421 têm mecanismo verificado — L3.8 confirmada, e não é colisão.** `SignatureSpec` (234, `com.tananaev.passportreader_22`): o spongycastle cria a `Signature` via `ProviderJcaJceHelper.createSignature` → `Signature.getInstance(String, Provider)` **direto, sem wrapper** — a sobrecarga não tem pointcut. `MacSpec` (31, `org.css_apps_m3.password_manager_16`): o tink (`EngineWrapper$TMac`) chama `Mac.getInstance(String, Provider)` direto com provider não nulo. `MessageDigestSpec` (156): 144 via **construtor de subclasse** (`org.kotlincrypto...SHA256 extends MessageDigest`, sem `getInstance` nenhum) e 12 via **`MessageDigest.clone()`** (guava), sem pointcut. Nos três casos `currentAlgorithmInstance` fica no inicializador `""` porque nenhum evento de criação disparou — rota de criação **não coberta**, exatamente a via prevista por L3.8.

**Sobre o argumento decisivo do dossiê.** ⚠️→❌ O dossiê argumenta que `Platform.platformTrustManager` registra 7.174 `EMPTY` e 208 `X509`, e que *"código-fonte idêntico não pode passar dois argumentos diferentes"*. Os dois números estão exatos ✅, e ✅ os 208 `X509` vêm todos de **um único app** (`org.openhab.habdroid_589`), nenhum app exibindo os dois valores naquele sítio. **Correção da rev. 3:** a explicação da rev. 2 ("apps diferentes empacotam versões diferentes do okhttp") estava **errada**. As versões diferem de fato (4.12.0 no openhab, 4.8.1 no etesync), mas o bytecode do sítio é **idêntico** nos dois apps — ambos passam `getDefaultAlgorithm()` ao wrapper `_4` (g3). Os 208 `X509` do openhab são a própria **difusão de (b)**: `de.duenndns.ssl.MemorizingTrustManager.getTrustManager` passa o literal `"X509"` (`const-string v0, "X509"` → wrapper `_4`), g3 difunde para o conjunto inteiro, e o `Platform` que reporta depois lê o valor difundido. O argumento do dossiê sobrevive no nível da fonte; o que varia entre apps é o **estado global do monitor**, não o argumento do okhttp — o mesmo mecanismo do caso `etesync` abaixo, que a rev. 2 explicou corretamente mas deixou de aplicar ao openhab.

**A conclusão do dossiê, porém, sobrevive — por outro caminho.** ⚠️ Em `com.etesync.syncadapter_20700`, no **mesmo segundo registrado**, há `EMPTY` em `Platform.platformTrustManager` e `X509` em `cert4android CertUtils.getTrustManager` e em `conscrypt SSLParametersImpl.createDefaultX509TrustManager`. Um processo, um instante, dois valores. Sob (b) isso é exatamente o esperado: o Conscrypt passa o literal `"X509"`, g3 difunde para todos os monitores, e o discriminador entre os sítios é a **ordem** — quem chamou `init` antes da difusão lê `""`, quem chamou depois lê `"X509"`. O que varia é a observação do monitor, como o dossiê disse; a razão é a difusão de g3, que ele não identificou.

### 3.7 A prova direta — o DEX tecido da campanha

Tudo acima é derivação. **Esta seção é observação.** Os APKs instrumentados que produziram os dados do artigo estão em `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706` (468 arquivos: **219** APKs + 219 `.json` + 30 `.pkgdet` — a rev. 2 dizia "234 APKs" dividindo 468 por 2, sem notar os `.pkgdet`). Desmontei o DEX com `baksmali` e li o resultado. Não é um APK de teste: é o artefato de produção.

**Os wrappers existem, e três disputam a mesma assinatura.** Em `mop/MonitorWrappers` de `com.etesync.syncadapter_20700`:

| método wrapper | assinatura original | chama |
|---|---|---|
| `javax_net_ssl_TrustManagerFactory_getInstance` | `(String)TMF` | `TrustManagerFactorySpec_g1Event` |
| `javax_net_ssl_TrustManagerFactory_getInstance_1` | `(String)TMF` | `..._g2Event` |
| `javax_net_ssl_TrustManagerFactory_getInstance_2` | `(String,String)TMF` | `..._g2Event` |
| `javax_net_ssl_TrustManagerFactory_getInstance_3` | `(String,Provider)TMF` | `..._g2Event` |
| `javax_net_ssl_TrustManagerFactory_getInstance_4` | `(String)TMF` | `..._g3Event` |

**Só um dos três é chamado.** Contagem de `invoke-static` em todo o APK:

```
7  MonitorWrappers;->javax_net_ssl_TrustManagerFactory_getInstance_4(Ljava/lang/String;)   <- g3
1  MonitorWrappers;->javax_net_ssl_TrustManagerFactory_getInstance_3(String,Provider)
1  MonitorWrappers;->javax_net_ssl_TrustManagerFactory_getInstance_2(String,String)
0  MonitorWrappers;->javax_net_ssl_TrustManagerFactory_getInstance(Ljava/lang/String;)     <- g1, MORTO
0  MonitorWrappers;->javax_net_ssl_TrustManagerFactory_getInstance_1(Ljava/lang/String;)   <- g2, MORTO
```

✅ **`TrustManagerFactorySpec_g1Event` nunca é alcançável neste APK.** O método wrapper está compilado dentro do DEX e nenhuma instrução no programa inteiro o referencia. É exatamente o *last-writer-wins* previsto, observado.

✅ **Universal no corpus.** Em `com.etesync.syncadapter_20700`, `org.openhab.habdroid_589`, `eu.opencloud.android_9` e `com.owncloud.android_48000100`, **100%** dos call sites de `TrustManagerFactory.getInstance(String)` vão para o wrapper do g3, e **100%** dos de `SSLContext.getInstance(String)` vão para o wrapper do `unsafe_protocol`. Nenhum, em nenhum APK, alcança o g1.

✅ **Censo observado** (`com.etesync.syncadapter_20700`): 96 wrappers declarados, **10 assinaturas com mais de um wrapper**, **19 wrappers mortos em assinatura disputada**. Três dessas assinaturas têm wrapper vivo *e* mortos — e são as conclusivas, porque provam substituição e não mera ausência de uso:

| assinatura | mortos | vivo |
|---|---|---|
| `TrustManagerFactory.getInstance(String)` | g1 (0), g2 (0) | **g3 (7)** |
| `SSLContext.getInstance(String)` | g1 (0) | **`unsafe_protocol` (3)** |
| `KeyManagerFactory.getInstance(String)` | g1+g3 fundidos (0) | **g2 (2)** |

> Cautela de leitura: "0 call sites" sozinho não prova morte — pode ser que o app simplesmente não use a API. Só as três linhas acima, onde há um vivo ao lado dos mortos, são prova de colisão. As outras sete assinaturas disputadas (todas `SecureRandom`) não são exercidas por este APK.

**E o `KeyManagerFactorySpec` confirma a direção do defeito.** Lá o vencedor é o `g2`, cuja guarda é `contains(alg)` — a **mesma** do g1 —, então o algoritmo válido continua sendo registrado. É por isso que `KeyManagerFactorySpec` **não aparece** na lista de specs com valor vazio (§3.6), enquanto `TrustManagerFactorySpec` e `SSLContextSpec` — cujos vencedores registram só o caso inválido — aparecem. A colisão só produz o valor vazio quando o vencedor é o registrador do caso inválido.

#### O mecanismo completo, num único APK

Os três sítios que os dados apontam estão todos aqui, e todos passam pelo wrapper do g3:

| sítio (smali) | argumento no bytecode | consequência |
|---|---|---|
| `okhttp3/internal/platform/Platform` | `invoke-static TrustManagerFactory->getDefaultAlgorithm()` → `"PKIX"` | guarda de g3 (`!contains`) **falsa** → nada registrado → `init` lê `""` → **EMPTY** |
| `org/conscrypt/SSLParametersImpl` | `invoke-static TrustManagerFactory->getDefaultAlgorithm()` → `"PKIX"` | idem — **e no entanto os dados registram `X509` aqui** |
| `at/bitfire/cert4android/CertUtils` | **`const-string v0, "X509"`** | guarda de g3 **verdadeira** → registra `"X509"` e **difunde** |

✅ **A terceira linha é a prova de (b).** `SSLParametersImpl` passa comprovadamente `getDefaultAlgorithm()`, não `"X509"` — está no bytecode. Ainda assim os dados registram `X509` naquele sítio. O valor só pode ter vindo de outro monitor: é a difusão do g3 pela fatia de parâmetro vazio. **Contaminação entre instâncias, observada.**

**Triangulação em três níveis.** O código-fonte dos apps do corpus está em `rvsec-dataset/repos/<pkg>_<ver>.apk/`. Para `com.etesync.syncadapter_20700`:

```kotlin
// cert4android/src/main/java/at/bitfire/cert4android/CertUtils.kt:22
val tmf = TrustManagerFactory.getInstance("X509")
```

✅ Fonte original (`"X509"` literal) → bytecode tecido (`const-string v0, "X509"` seguido de `invoke-static ..._getInstance_4`) → dado da campanha (`X509` em `errors.csv`). Os três níveis concordam. Isso elimina a possibilidade de o literal ser artefato de desmontagem ou de reescrita do weaver.

Isso resolve o caso `etesync` da §3.6 inteiramente: `CertUtils` passa o literal `"X509"` e difunde; `SSLParametersImpl` lê o valor difundido; `Platform` reportou antes da difusão e leu `""`. Um processo, um segundo, dois valores, três sítios — e o discriminador é a ordem, não o argumento.

> Nota lateral: `at.bitfire.cert4android` passar `"X509"` fixo é o idioma correto no Android (`X509` é alias Conscrypt de `PKIX`, L1.3). Mesmo o único valor "genuinamente observado" é falso positivo de camada 1.

### 3.8 Consequência para o plano

`TrustManagerFactorySpec` não produz nenhum verdadeiro positivo neste dataset, por **três** razões independentes — e só a primeira é consertada mexendo no weaver:

1. os relatos vazios são artefato de (a);
2. os relatos `X509` têm valor real com sítio errado, por (b);
3. `X509` é alias Conscrypt de `PKIX` no Android (L1.3 do plano), então mesmo um `X509` bem atribuído é falso positivo de camada 1.

✅ **E o aviso da §5/F0 do plano está agora verificado, não hipotético, para `TrustManagerFactorySpec` e `SSLContextSpec`:** corrigir a allow-list dessas duas specs **não muda absolutamente nada**, porque a allow-list é consultada contra uma variável que nunca é escrita.

---

## 4. INVESTIGAÇÃO A — o grafo de predicados

### 4.1 O substrato

✅ `Property.java` tem **23** constantes (linhas 8–30). ✅ `ExecutionContext.java` (147 linhas) é um **singleton estático** sobre um `Map<Property, Set<Object>>`, com três operações que tocam o grafo: `setProperty` (escrita, `:80-87`), `validate` (leitura, `:96-98`), `remove` (`:52-57` em massa — `@Deprecated` — e `:59-66` individual).

Quatro propriedades do substrato limitam o que o grafo pode expressar, todas ✅:

- **Chaveado por `equals`/`hashCode`, não por identidade.** Para `byte[]`/`char[]` isso é identidade de referência na prática — qualquer cópia defensiva perde o predicado. Para `String`, ao contrário, conflate objetos estruturalmente iguais e não relacionados. O grafo não é nem solidamente identitário nem solidamente por valor.
- **Não é thread-safe.** `HashMap`/`HashSet` nus, `instance()` com init preguiçosa não sincronizada.
- **Vaza por construção.** Toda escrita guarda referência **forte** num set estático; só saem por `remove` em handler de falha (9 sítios) ou `reset()` (nunca chamado em produção; um único chamador, em teste — `rvsec-agent/src/test/.../bench01/SecureRandomTest.java:19`).
- **`validate` de chave ausente devolve `false`** — ausência de evidência vira evidência de ausência. É por isso que os eventos de erro por `!validate(...)` acusam sempre que a chamada produtora simplesmente não foi instrumentada.

`hasEnsuredPredicate` e `isInAcceptingState` têm **zero chamadores** em `.mop`.

### 4.2 A tabela bipartida — partição

Derivada mecanicamente sobre 85 sítios (49 escritas, 27 leituras, 9 remoções), **todos em `.mop`**; zero em Java. Tabela completa em `scratchpad/A1_property_graph.csv`.

| classe | nº | propriedades |
|---|---:|---|
| **escrita E lida** (aresta viva) | **3** | `GENERATED_KEY`, `GENERATED_PUBLIC_KEY`, `RANDOMIZED` |
| **escrita, nunca lida** | **18** | `DIGESTED`, `ENCRYPTED`, `GENERATED_KEY_MANAGERS`, `GENERATED_KEY_PAIR`, `GENERATED_KEY_STORE`, `GENERATED_MAC`, `GENERATED_TRUST_MANAGER`, `GENERATE_SSL_CONTEXT`, `GENERATE_SSL_ENGINE`, `PREPARED_DH`, `PREPARED_GCM`, `PREPARED_HMAC`, `PREPARED_IV`, `PREPARED_PBE`, `SIGNED`, `SPECCED_KEY`, `VERIFIED`, `WRAPPED_KEY` |
| **lida, nunca escrita** | **1** | `GENERATED_PRIVATE_KEY` |
| nem uma coisa nem outra (só `remove`) | **1** | `GENERATED_TRUST_MANAGERS` |

❌ **"14 das 23 escritas e nunca lidas" está errado — são 18.** O erro é na direção otimista. Somando as outras duas classes, **20 das 23** constantes não funcionam como aresta. **Das 49 escritas, 35 não têm leitor** (corrigido na rev. 3: as três propriedades vivas recebem 3+2+9 = 14 escritas; 49 − 14 = 35 — o "43" da rev. 2 não é reproduzível por nenhuma definição testada).

### 4.3 Verificação das alegações

| # | alegação | veredito |
|---|---|---|
| (a) | 14 de 23 escritas e nunca lidas | ❌ **refutada** — são **18** |
| (b) | `PREPARED_*` (5) sem consumidor; `Cipher.init(int,Key,AlgorithmParameterSpec)` nunca checa o parameter spec | ✅ **confirmada, e o mecanismo é pior**: o `..` de `CipherSpec.mop:66` de fato casa a sobrecarga de 3 args, mas `args(mode, key, ..)` (`:67`) **descarta** o `AlgorithmParameterSpec` — ele nunca entra em escopo, não há o que checar. Pior ainda em `MacSpec.mop:55-59`, onde `params` **é** ligado e mesmo assim `PREPARED_HMAC` não é consultado |
| (c) | `GENERATED_PRIVATE_KEY` sem produtor; `KeyPairSpec.mop:38` escreve a constante errada; guarda em `CipherSpec.mop:72` morta | ✅ **confirmada, linhas exatas.** `:38` é cópia-e-cola de `:32` com o valor trocado e a constante não. **Nuance:** o defeito é parcialmente auto-mascarado — como `gpr` escreve `GENERATED_PUBLIC_KEY` **sobre a chave privada**, o disjunto `:71` ainda aceita. Não há falso positivo; há perda da distinção público/privado que os predicados do CrySL existem para fazer |
| (d) | `GENERATED_TRUST_MANAGERS` nunca escrita; `:65` escreve `GENERATED_KEY_MANAGERS`; só removida em `:88` | ✅ **confirmada, linhas exatas** (verifiquei eu mesmo lendo o `.mop`). O evento `gtm1` carrega **três** defeitos de cópia-e-cola do `KeyManagerFactorySpec`: constante errada (`:65`), binding `TrustManager[][]` (`:62`) e tipo de retorno `KeyManager[]` no pointcut (`:63`), que **nunca casa** a assinatura real `TrustManager[]` |
| (e) | três hubs; `SecureRandomSpec` raiz única de `RANDOMIZED` para seis specs | ✅ **confirmada, com precisão adicional**: `RANDOMIZED` chega a `CipherSpec.i2`/`MacSpec` só **transitivamente** (via `SecretKeySpecSpec` → `GENERATED_KEY`), não diretamente. As seis: `GCMParameterSpecSpec`, `IvParameterSpecSpec`, `PBEKeySpecSpec`, `PBEParameterSpecSpec`, `RandomStringPasswordSpec`, `SecretKeySpecSpec` |
| (f) | `RandomStringPassword.mop` é propagador de taint, não detector | ✅ **confirmada.** Ambos os eventos são leituras guardadas que re-emitem o mesmo predicado no valor derivado; `@match` está **vazio** e **não há `@fail`** — a spec é estruturalmente **incapaz de emitir qualquer erro**. ✅ Nenhuma spec do conjunto detecta credencial fixa; `ErrorType` sequer tem categoria para isso |

✅ Confirmados também os dois defeitos de nome: `IvParameterSpec.mop:17` declara `IvParameterSpecSpec`; `RandomStringPassword.mop:9` declara `RandomStringPasswordSpec`.

### 4.4 Cruzamento com o CrySL 1.5.2 — a assimetria é a manchete

⚠️→✅ 49 regras, 0 cláusulas não parseadas: **76 `ENSURES`, 57 `REQUIRES`, 2 `NEGATES`, 5 `FORBIDDEN`**, 45 predicados distintos. 22 regras têm contrapartida `.mop`.

Sobre as 22 regras mapeadas (84 cláusulas):

| | cláusulas | presentes | ausentes |
|---|---:|---:|---:|
| `ENSURES` | 46 | **38 (83%)** — 33 exatas, 1 suspeita, 2 surrogadas, 2 com constante errada | 8 |
| `REQUIRES` | 36 | **8 (22%)** | **28** |
| `NEGATES` | 2 | 1 | 1 |

> **Rev. 3:** a rev. 2 dizia "42 (92%)", mas a própria decomposição soma 33+1+2+2 = **38** (e 42+8=50 ≠ 46). O correto é 38/46 = **83%**; do lado `REQUIRES`, 8+27=35 ≠ 36 — os ausentes são **28**. A assimetria — a manchete da investigação — permanece: 83% contra 22%.

> **A tradução produz predicados com fidelidade e quase não os consome.** Esse é o defeito estrutural, mais do que qualquer aresta isolada.

Caso mais claro: `SSLContextSpec` não lê **nenhum** dos seus três `REQUIRES` (`generatedKeyManagers`, `generatedTrustManagers`, `randomized`), embora as três constantes existam. Um contexto TLS montado com key/trust managers não validados não levanta nada.

⚠️→✅ Duas regras falham no parser do CrySL e são puladas em silêncio: **`SSLEngine.crysl`** (`:11-12`, referência a um evento `cp1` nunca definido — o upstream corrigiu exatamente isso em `Crypto-API-Rules@d35ab89`, "Fix cp1 to ep1") e **`OAEPParameterSpec.crysl`** (`:8`, objeto chamado `alg` colidindo com a keyword `alg(...)`; campo morto, removido no upstream em `497df73`). **Consequência corrigida na rev. 3:** vale só para **`preparedOAEP`** (produtor único em `OAEPParameterSpec.crysl:25`; consumidores `Cipher.crysl:141` e `AlgorithmParameters.crysl:40`) — `Cipher.crysl:140-141` é insatisfazível também do lado estático. Já **`generatedSSLEngine` tem um segundo produtor** (`SSLContext.crysl:38`, que parseia normalmente) e **nenhuma regra o consome** — a falha do `SSLEngine.crysl` custa as CONSTRAINTS (versão de TLS, cipher suites), não um produtor de predicado.

### 4.5 Classificação das 37 arestas faltantes

*(Rev. 3: o total é **37** — 8 `ENSURES` + 28 `REQUIRES` + 1 `NEGATES` —, não 38; a partição foi re-derivada e o balde (iii) deixou de ser vazio.)*

| balde | nº | razão |
|---|---:|---|
| **(i) defeito de tradução** | **23** | A constante existe, o evento JavaMOP existe, e o idioma é usado em outro lugar do mesmo corpus. Leituras negadas são expressáveis (`IvParameterSpec.mop:46`), leituras guardadas também (`SecretKeySpecSpec.mop:28`), `remove` para o `NEGATES` também. Inclui as **duas constantes erradas** (`KeyPairSpec.mop:38`, `TrustManagerFactorySpec.mop:65`), que são bugs de dois tokens |
| **(i-b) defeito — capacidade ausente** | **11** | O predicado não tem constante nenhuma em `Property.java` (`preparedAlg`, `preparedOAEP`, `generatedCipher`, `preparedRSA/DSA/EC`, `generatedManagerFactoryParameters`; rev. 3 acrescenta `cipheredInputStream` e `cipheredOutputStream` — as specs correspondentes não têm nenhuma chamada a `ExecutionContext`). Separado de (i) porque a correção toca `rvsec-core`, não só um `.mop` |
| **(ii) omissão deliberada** | **2** | Padrão sistemático: todo `ENSURES p[this] after Init/Get` é reescrito como `setObjectAsInAcceptingState(...)` no `@match`. Documentado em `ExecutionContext.java:107-114`. **Ressalva:** a substituição está pela metade — `isInAcceptingState` nunca é lido de um `.mop`, então o conjunto é inerte em runtime |
| **(iii) inexpressível** | **1** | **`randomized[lSeed]`** (`SecureRandom.crysl:46`; `lSeed` é `long`, `:7`). O predicado afirma **proveniência** ("este long saiu de um CSPRNG"), mas o `ExecutionContext` chaveia por `equals` — para um primitivo boxed, pelo **valor**. Nenhuma constante nova conserta isso. A tradução já comete a unsoundness correspondente do lado `ENSURES`: `SecureRandomSpec.mop:115/:128` escrevem `RANDOMIZED` sobre `int`s, e com o cache de `Integer` (−128..127) um único `nextInt()` pequeno marca como aleatório **todo** literal daquele valor no processo |

**Os baldes não se misturam, e a distinção decide o tipo de correção.** A rev. 2 registrava "nenhuma aresta é inexpressível"; a rev. 3 corrige: o *workaround* do `ExecutionContext` cobre 36 das 37, mas não predicados de proveniência sobre primitivos. A admissão do artigo é real. Verbatim de `rvsec-paper/rvsec.tex:40-43`, 100% comentado:

```
%% Although there is no explicit language construct
%% to establish relationships between distinct JavaMOP
%% specifications, which would allow us to mimic the $REQUIRES$ and
%% $ENSURES$ clauses of \csl, it is almost straightforward
```

Uma vez que o `ExecutionContext` existe como canal fora de banda, quase toda aresta restante é escrevível (36 de 37 — a exceção é `randomized[lSeed]`, acima). Inexpressibilidade genuína aparece também **fora** do inventário de arestas: `neverTypeOf[x, java.lang.String]` (7 cláusulas) vive em `CONSTRAINTS` — seção distinta de `REQUIRES`/`ENSURES`, por isso não conta entre as 37 — e é irrecuperável em runtime: quando o pointcut dispara o parâmetro já é `char[]`/`byte[]`, e a origem é fato de fluxo estático.

`notHardCoded` (4 cláusulas) não é modelado diretamente, mas ✅ o `RandomStringPassword.mop` — a única spec **sem** contrapartida CrySL — é um surrogate de taint para ele: `PBEKeySpecSpec.mop:38` exige `validate(RANDOMIZED, password)`, uma leitura que o CrySL **não** pede (`PBEKeySpec.crysl:29` exige só `randomized[salt]`). É invenção da tradução, e a única cobertura que `notHardCoded` tem.

### 4.6 Sobrevivência na codegen

⚠️→✅ **A geração de código está inocentada.** 64 de 64 `condition(...)` sobrevivem para o monitor gerado, zero ausentes, contagem por spec batendo uma a uma. Todos os defeitos estão nos `.mop`, fielmente compilados.

Duas correções às premissas do brief:
- ⚠️→✅ `MultiSpec_1RuntimeMonitor.java` **não é artefato commitado** — está em `.gitignore`. Mas é **fresco** (2026-07-08, posterior ao `.mop` mais novo), logo é evidência admissível sobre as fontes atuais. O que é commitado (`rvsec-logger-csv/src/main/mop/*.aj`, fevereiro) é que está **velho**.
- As guardas vivem **só** no monitor, nunca no aspecto. Uma guarda que falha faz `return false` e **não toma transição** — o que torna o defeito (d) pior que "evento descartado".

Os quatro defeitos de typestate, verificados contra as tabelas geradas:

| | veredito |
|---|---|
| (a) `SecureRandomSpec.next2` fora de `end` | ✅ **confirmado** — `transition_next2 = {3,3,1,3}`, exatamente como alegado. `next1` é `{3,1,1,3}`: segundo `nextBytes()` viola, segundo `nextInt()` não |
| (b) `KeyPairSpec.gpu` de start direto a fail | ✅ **confirmado** — `gpu = {2,1,2}`, fail = 2 |
| (c) `MessageDigestSpec.reset()` fora da `ere` | ✅ **confirmado** — `reset = {4,4,4,4,4}`, fail = 4 |
| (d) `Cipher`/`Mac` `init` com `GENERATED_KEY` insatisfazível | ✅ **fechado na rev. 3** — o *gating* é real, mas **"insatisfazível" é exagero**: `GENERATED_KEY` é escrita sem guarda em três sítios (`KeyGeneratorSpec.mop:67`, `SecretKeySpecSpec.mop:68`, `KeyStoreSpec.mop:71` — rev. 3). Enquadramento correto: estreito, dependente do programa inteiro, e **auto-revogante** — os `@fail` de `KeyGeneratorSpec` (`:75`) e `KeyStoreSpec` (`:79`) a removem; o de `SecretKeySpecSpec` **não** (assimetria nova da rev. 3) |
| (e) `GCMParameterSpecSpec` incapaz de emitir | ✅ **fechado na rev. 3** — as duas alegações de fonte confirmadas (`c1` duplicado, `c2` fantasma), mas a geração **nem falhou nem descartou a spec**: absorveu a duplicata como sobrecarga e **descartou `c2` sem diagnóstico**. `match` é alcançável; `fail` é **inalcançável por construção** (rev. 3): `transition_c1={1,2,2}` exige um segundo `c1` no mesmo monitor, mas o monitor é chaveado pelo próprio objeto `returning` — cada `new` cria instância e monitor novos |

✅ As 23 specs estão presentes no monitor — **ausência na geração não explica nada**. Mas três são estruturalmente incapazes de reportar: `SecretKeySpec` e `RandomStringPasswordSpec` não têm `@fail` (logo nem campo `Category_fail`), e o `fail` do GCM é inalcançável. ⚠️ Os outros 10 specs silenciosos (dos 13) precisam de explicação de runtime.

### 4.7 O que os dados sustentam

✅ Todos re-derivados por script sobre `errors.csv` — e re-derivados de novo, com script independente, na rev. 3:

| alegação | derivado | veredito |
|---|---|---|
| 454 misuses únicos | 454 | ✅ é `(apk, class, method, spec)` distinto — **não** `unique_msg`, que dá 225 |
| 8.843 vazios / 5 specs / 71 misuses / 64 apps | idênticos | ✅ os quatro exatos |
| 7.174 `EMPTY` + 208 `X509` em `platformTrustManager` | idênticos | ✅ exatos (mas ver §3.6 sobre o que provam) |
| 11.620 eventos / 80 misuses / 25 apps (`Cipher`/`Mac`) | 11.620 / 80 / **24** | ✅ (rev. 3) — 24 apps confirmado; 11.620 só fecha restringindo a `InvalidSequenceOfMethodCalls` (todas as linhas `Cipher`+`Mac` dão 11.760); **mecanismo segue indeterminável** pelo CSV |
| 13 de 23 specs nunca disparam | 13 | ✅ |

✅ Achado estrutural relevante para leitura de resultados (re-derivado na rev. 3): **as 70.760 ocorrências de `InvalidSequenceOfMethodCalls` (72,9% do dataset) são sombra de co-emissão** — as 454 tuplas de misuse, **todas as 454**, têm ao menos uma linha `InvalidSequenceOfMethodCalls` para a mesma tupla. E as contagens de evento medem re-disparo, não descoberta: 97.018 linhas para 454 tuplas (≈214×); por combinação executada `(tupla, rep, timeout, tool)` a média é **3,35** eventos (97.018/28.930). *(O "~6,5×" da rev. 2 só é reproduzível como 97.018/454/33, uma normalização que ignora os timeouts e contradiz o próprio parêntese "3×3×11" — número retirado.)* Nuance adicional da rev. 3: os eventos vazios das cinco specs são `UnsafeAlgorithm`, **exceto** os do `SSLContextSpec`, que são `UnsafeProtocol`.

---

## 5. O gate de PCD (F0.4') — desenho, não implementação

O problema mudou de forma com a §2.2, e o gate deve mudar junto. Ele **não** precisa mais proteger contra nove PCDs que casam-true. Precisa cobrir:

1. **`execution(...)`** — hoje casa a entrada de todo método ignorando a assinatura, sem contador e sem teste que fixe o comportamento. É o único match-true silencioso realmente perigoso.
2. **`within(...)` positivo e `!adviceexecution()`** — match-true silencioso; o segundo descarta a negação por usar `contains` em vez de igualdade.
3. **Os nove que falham fechado** — hoje `throw` no laço principal, mas **`false` silencioso** na sonda do `commonPointcut` (`DexWeaver.java:695-700`). Um gate na geração transforma um abort tardio em erro cedo e legível.
4. **`parseCommonPointcut` devolvendo `null`** — o único caminho **fail-open**: derruba todas as exclusões daquele weave. É o item mais urgente dos quatro.
5. **A colisão de assinatura** — o gate natural é o mesmo `containsKey` que já existe em `DexWeaver.java:208`: falhar alto quando duas entradas disputam uma chave, em vez de sobrescrever.

Onde: na geração, sobre o **descritor** — é o artefato que o weaver consome e onde a expressão chega verbatim. Custo baixo; evita que qualquer spec de F2/F5 seja tecida errada em silêncio.

Vale registrar que a matriz existente `docs/aspectj_grammar_coverage.md` está ⚠️ **desatualizada**: cita `PointcutMatcher.java:158-159 (NamedRefPC always-match)` para seis PCDs, e `:158-159` é a escotilha do `adviceexecution` — esses PCDs caem no `throw` de `:161`.

---

## 6. O que isto muda no plano

### §4.1 — reescrever

❌ A tabela de PCD e o parágrafo *"ausentes, e falham em silêncio... → match-true"* estão errados. Substituir pela matriz da §2.1. O risco de autoria **continua real**, mas por três PCDs, não nove — e o pior caminho é o fail-open do `commonPointcut`, que a §4.1 não menciona.

### §15 — corrigir a regra

O item *"Não escrever spec nova com PCD fora de `{call, staticinitialization, args, target, if, !within}`"* **continua válido como prática**, mas a justificativa ("sete PCDs viram match-true silencioso") deve ser trocada: os nove falham fechado; o perigo é `execution(...)`, `within(...)` positivo e `!adviceexecution()`.

### §5 / F0 — parcialmente fechada

- **F0.1** ✅ **resolvida, e por observação, não por reprodução**. A colisão foi vista no DEX tecido da campanha (§3.7): `g1Event` inalcançável em 4/4 APKs, censo observado de 10 assinaturas disputadas / 19 wrappers mortos num APK. **L3.1 e L3.2 não são concorrentes — são complementares.** A §3 do plano ("Aberto (G0)") e o item L3.1/L3.2 da §11 devem ser reescritos. Nota de método para o plano: **a §5 supunha que F0 exigiria re-executar instrumentação; não exigia** — os APKs instrumentados da campanha bastam, e são evidência melhor do que um APK sintético, porque são o artefato que gerou os números do artigo.
- **F0.2** ✅ **resolvida**: os quatro defeitos verificados contra o monitor gerado; (d) e (e) precisam de enquadramento mais fraco que o atual.
- **F0.4'** → §5 acima.
- **F0.3** (recontagem dos `addError`) permanece aberta.

### §3 — a classificação de ~35.368 eventos

Deixa de ser provisória **para 8.422 eventos** (95,2% da população de valor vazio): são artefato de instrumentação, com mecanismo identificado. Os 421 restantes seguem sem explicação. O restante dos 35.368 não foi tocado por esta investigação.

### §9.2 — reordenar

A correção de allow-list de `TrustManagerFactorySpec` e `SSLContextSpec` **não pode ser a primeira coisa a fazer**: ✅ está verificado que a allow-list é consultada contra uma variável que nunca é escrita. Ordem correta: (1) consertar a colisão no weaver — ou, mais barato, **renomear o binding `returning` de `g3` para `mf`** em `TrustManagerFactorySpec.mop:44`, que faz o javamop fundir os advices como já faz no `KeyManagerFactorySpec`; (2) só então mexer na allow-list.

> Esse segundo caminho é notável: um defeito de infraestrutura (L3.1) tem uma correção de **uma palavra** no `.mop`. Não substitui o conserto do weaver — qualquer spec nova pode recriar a colisão —, mas desbloqueia F2 sem depender da camada 3.

### §9.2 (camada 2) e §9.4 — priorizar pela assimetria

A reconexão do grafo deve ser guiada pelo número da §4.4: o lado `ENSURES` está 83% pronto, o lado `REQUIRES` está em 22%. **O trabalho é quase todo de escrever leituras, não escritas.** Em particular `SSLContextSpec`, cujos três `REQUIRES` estão sem leitura embora as constantes existam — correção de spec, não de desenho.

Para a §9.4, a `KeyGenParameterSpec.Builder` (item 3) ganha peso: é o produtor que falta para `GENERATED_KEY` no keystore de plataforma, e `GENERATED_KEY` é uma das **três** arestas que de fato funcionam.

### §12 — uma ameaça nova

A tradução tem **duas** constantes escritas na posição errada (`KeyPairSpec.mop:38`, `TrustManagerFactorySpec.mop:65`) que passaram despercebidas porque o `ExecutionContext` aceita qualquer par `(Property, Object)` sem verificação. **Não há vínculo, nem em compilação nem em runtime, entre a constante escrita e a lida — uma constante errada falha aberta e invisível.** Isso é evidência concreta para a ameaça W3 da tese (tradução manual sem prova de equivalência), hoje em ledger mas ausente de `tex/4_EstudoDeCaso.tex:759-790`.

---

## 7. O que permanece não verificado

Explicitamente, para não ser promovido por descuido:

1. ~~Nenhum APK foi tecido.~~ ✅ **Resolvido em §3.7** — não foi preciso tecer: os APKs instrumentados da própria campanha estavam disponíveis, e a colisão foi observada no DEX de produção em 4 APKs. Passou de derivação a observação.
2. ~~A difusão de g3.~~ ✅ **Resolvido em §3.7, e fechado na rev. 3 também no nível do código**: a cadeia foi rastreada — todo monitor criado é inserido também no set da fatia vazia (`AbstractMonitorSet.add`, `rv-monitor-rt/.../AbstractMonitorSet.java:42-45`, append em array simples) e `TrustManagerFactorySpecMonitor_Set.event_g3` (`MultiSpec_1RuntimeMonitor.java:3199-3221`) itera **todos** os elementos não terminados. Não é mais inferência.
3. ~~Os 421 eventos.~~ ✅ **Resolvido na rev. 3 (§3.6)** — L3.8 confirmada por bytecode nas três specs: sobrecarga `(String, Provider)` não instrumentada (`Signature` via spongycastle, `Mac` via tink), construtor de subclasse e `clone()` (`MessageDigest`). Toda a população de valor vazio tem mecanismo.
4. **Se algum wrapper morto custa uma violação real.** ✅ **Parcialmente resolvido**: está provado que `g1Event` do `TrustManagerFactorySpec` é inalcançável e que os relatos de valor vazio decorrem disso. Não quantifiquei quantas violações *deixariam* de existir com a colisão corrigida — isso exige re-executar a campanha, não só reler o DEX. **Continua aberto.**
5. **Qual `android.jar` as campanhas passadas usaram.** ⚠️ Relatado que `ConfigResolver.java:120-122` escolhe por máximo lexicográfico (`"android-4" > "android-37.0"`) e que o driver Python nunca passa `--android-jar`. Não re-derivado. O censo **observado** (§3.7) contorna a questão para o corpus da campanha. Nota da rev. 3: a questão **irmã** — qual *jar do weaver* rodou a campanha — foi resolvida: o `instr-cli.jar` do gh73 (`d73ebc41`, 2026-06-30), 77 commits **após** `3af5b3aa`; prova binária: 130/219 APKs contêm DEX `037/038/039`, que o weaver pré-gh73 não emitia. O binário exato não sobreviveu no host (sem hash registrado) — a datação é por lineage + assinatura no DEX, não por desmontagem do jar.
6. **Os 10 specs silenciosos** que não têm explicação de geração. **Continua aberto** (o 11º, `KeyManagerFactorySpec`, está explicado: zero linhas no CSV, consistente com o vencedor g2 registrar o caso válido).
7. **`thread(...)`** — existe no javamop, não existe no dexlib2, não tem linha de matriz nem teste. Se alguma spec o usar, cai no `throw`. **Continua aberto.**
8. ~~Generalização do censo observado.~~ ✅ **Resolvido na rev. 3 (§3.2)** — censo rodado nos **219/219** APKs do corpus, com script novo; zero falsificações, padrão uniforme.

---

## 8. Verificação adversarial (revisão 3) — tabela de vereditos

Sessão independente, 2026-08-06. Método: 9 agentes de re-derivação mecânica (fonte, censo em 219 APKs, `errors.csv`, grafo, CrySL, monitor, apresentação, datação do jar, eventos inexplicados) + re-derivação própria do orquestrador para todo item decisivo (nenhum veredito repassa achado de agente sem contraprova: matcher, DexWeaver, descritor 110/112, `errors.csv`, tabelas de transição, bytecode de 8 APKs e os 9 sítios de valor vazio foram lidos também na main). Scripts novos; nada do scratchpad anterior foi reutilizado.

**Legenda:** CONFIRMADA = re-derivada e exata · CORRIGIDA = direção certa, número/detalhe errado (corrigido em lugar nesta revisão) · REFUTADA (parcial) = sub-alegação falsa.

| ID | alegação (resumo) | veredito | evidência decisiva |
|---|---|---|---|
| B1 | descritor grava expressão verbatim; toda restrição no matcher | **CONFIRMADA** | `DescriptorWriter.java:114-117`; filtragem dos advices de estatística é **arquitetural** (dois caminhos de dados), não filtro explícito |
| B2 | fail-closed desde `3af5b3aa`, antes da campanha | **CONFIRMADA e fechada** | `PointcutMatcher.java:161`; jar da campanha = gh73 (`d73ebc41`), 77 commits após; DEX `037/038/039` em 130/219 APKs |
| B3 | superfície match-true = exatamente 3 | **CONFIRMADA** | varredura exaustiva dos `Match.empty` (10 sítios; 3 constantes-true: `:137`, `:159`, `:514`) |
| B4 | `parseCommonPointcut` → `null` = fail-open | **CONFIRMADA** | `DexWeaver.java:856-864`; chamador `:299/:310/:348/:412` casa o advice sozinho |
| B5 | 144 `call(` / 122 assinaturas / 134 eventos; 116 não derivável | **CONFIRMADA** | 144 exige regra tolerante a espaço (`call (` em `PBEKeySpecSpec.mop:22,28`); 122 e 134 re-derivados |
| B6 | 23 advices `ForkedBooter` não chegam à produção | **CONFIRMADA** | 121 descritores de produção com 115 advices e 0 `ForkedBooter`; strings no DEX de 3 APKs = 0 |
| G1 | fusão de advices decidida pelo **nome** do binding | **CONFIRMADA** | `.mop:28` (`mf`) vs `:44` (`k`); `.aj:677-682` (KMF fundido) vs `:1024`/`:1033` (TMF separado) |
| G2 | índices 110/112, expressão byte-idêntica | **CONFIRMADA** | verificado por script; fixture = descritor do pipeline (`cmp` ok, 86.597 B) |
| G3 | mecanismo LWW: chave `:145`, `put` nu `:159`, guard não aplicado `:208` | **CONFIRMADA** | todas as seis citações de linha exatas |
| G4 | censo 3 / 7-9 / 10-19 | **CONFIRMADA e generalizada** | etesync 96/10/19 exato; 219/219 APKs com as mesmas 10 assinaturas; mortos 15–22 (mediana 19) |
| G5 | o advice que morre registra sempre o caso **válido** | **CONFIRMADA** | guardas verificadas nos `.mop` e no monitor; ordem 110<112 e 105<107 nos dois pares |
| G6 | g3 difunde pela fatia vazia; tabelas `{3,3,3,3}`/`{3,3,1,3}` | **CONFIRMADA e promovida** | cadeia lida no código: `AbstractMonitorSet.add` (`:42-45`) + `event_g3` itera `elements[]` (`:3199-3221`); tabelas exatas em `:10034-10038` |
| G7 | (a) e (b) verdadeiras, observáveis distintos; dilema falso | **CONFIRMADA** | ambas agora observadas (G10 + G11/G9) |
| G8 | colisão explica 8.422/8.843 (95,2%) | **CONFIRMADA e fortalecida** | atribuição agora **por evento**: os 9 sítios geradores de 100% dos 8.422 criam via 1 arg colidido (bytecode de 8 apps) |
| G9 | 208 `X509` = 1 app; argumento do dossiê cai | **CORRIGIDA** | fato exato (✅ CSV); explicação "versões do okhttp" **refutada** — bytecode idêntico; origem = literal `"X509"` do `MemorizingTrustManager` difundido por g3 |
| G10 | wrapper de g1 com 0 call sites; g3 com todos | **CONFIRMADA (219/219)** | zero falsificações; sem reflexão, segunda classe ou resíduo não reescrito; vencedor = último declarado, sempre |
| G11 | `SSLParametersImpl` passa `getDefaultAlgorithm()` e os dados dizem `X509` | **CONFIRMADA** | bytecode + CSV; reproduzida também no openhab |
| G12 | KMF colide mas vencedor tem guarda `contains` → sem vazio | **CONFIRMADA** | guardas `:5507/:5525/:5541`; KMF tem **0 linhas** no CSV; nuance: g1+g3 fundidos morrem juntos |
| A1 | substrato: `equals`, sem sync, vaza, `validate` fail-open | **CONFIRMADA** (1 sub-item corrigido) | `reset()` tem 1 chamador, em teste (`SecureRandomTest.java:19`) — "nunca chamado" era falso à letra |
| A2 | partição 3/18/1/1; 85 sítios (49/27/9) | **CONFIRMADA**; "43 de 49" → **35** | partição e totais exatos por dupla derivação; 49−14=35 |
| A3 | `PREPARED_*` sem consumidor; `args(mode,key,..)` descarta; `MacSpec` liga `params` e não lê | **CONFIRMADA** | linhas exatas (`CipherSpec.mop:66-67`, `MacSpec.mop:55-59`) |
| A4 | `KeyPairSpec.mop:38` constante errada; auto-mascarado | **CONFIRMADA** | `:32/:38` e disjunção `CipherSpec.mop:70-73` verificadas |
| A5 | `gtm1` com três defeitos de cópia | **CONFIRMADA** | `:62-65` verbatim; `GENERATED_TRUST_MANAGERS` só em `remove` `:88` |
| A6 | `RandomStringPassword` incapaz de emitir; sem detector de credencial fixa | **CONFIRMADA** | `@match` vazio, sem `@fail`; `ErrorType` (6 valores) sem categoria |
| A7 | 92% `ENSURES` / 22% `REQUIRES` | **CORRIGIDA: 83% / 22%** | 33+1+2+2=38, 38/46=82,6%; ausentes `REQUIRES` = 28; inventário 76/57/2/5/45 reproduzido exato |
| A8 | 2 regras CrySL fora; `preparedOAEP`/`generatedSSLEngine` sem produtor | **METADE** | defeitos e "exatamente 2" confirmados (+ fixes upstream `d35ab89`, `497df73`); consequência vale só para `preparedOAEP` — `generatedSSLEngine` tem 2º produtor e 0 consumidores |
| A9 | 38 arestas: 25/9/2/0-inexpressível | **CORRIGIDA: 37 = 23/11/2/1** | `randomized[lSeed]` é inexpressível (proveniência de primitivo); `neverTypeOf` fora do inventário por estar em CONSTRAINTS — exclusão coerente |
| A10 | codegen inocentada: 64/64 `condition` | **CONFIRMADA** | 64 no `.mop` (com o stray-paren tratado) = 64 guardas no monitor, spec a spec |
| A11 | typestate (a)–(e) | **CONFIRMADA; (d)/(e) fechadas** | tabelas exatas; (e) `fail` inalcançável por chaveamento por objeto; (d) `SecretKeySpecSpec` não revoga |
| A12 | 454 / 8.843-5-71-64 / 13 silenciosas / co-emissão | **CONFIRMADA** (2 retoques) | tudo exato por dupla derivação; 24 apps ✓; "~6,5×" retirado; vazio do SSLContext é `UnsafeProtocol` |

**Defeitos do relatório (rev. 2) por gravidade:** nenhum muda uma conclusão estrutural. (1) *Errados:* manchete 92%→83% (§4.4, aritmética interna inconsistente); explicação dos 208 `X509` por versão de okhttp (§3.6); "43 de 49" (§4.2); 38→37 e "0 inexpressível" (§4.5); consequência de `generatedSSLEngine` (§4.4); "234 APKs" (§3.7). (2) *Sobre-enunciados:* "reset() nunca chamado" (§4.1); "~6,5×" (§4.7); "drop silencioso" do `@annotation` (tem contador). (3) *Apresentação:* três referências §3.8→§3.7, uma §3.4→§2.3, frase duplicada na §3.2 — todos corrigidos nesta revisão.

**Higiene verificada:** nada foi escrito em `RV_ANDROID_NOVO_DATASET/` (nenhum arquivo ≥ 2026-08-05; os 30 `.pkgdet` são de 26/06), nem em `rvsec-dataset/repos/` (sem `.git` próprios; o churn em `docs/` é do repo pai, de julho), nem nos `.mop`/weaver (git limpo). O único arquivo tocado sob `ase-journal/` (`diagramas/rvandroid.drawio`, 06/08 10:18) foi editado no **draw.io desktop** (host `Electron` no cabeçalho) — edição humana na GUI, não atribuível à sessão do relatório.

**O que a rev. 3 não verificou:** (i) o binário exato do jar da campanha não sobreviveu (datação por lineage + assinatura DEX, não por desmontagem; sem hash registrado); (ii) quantas violações deixariam de existir com a colisão corrigida (§7.4 — exige re-execução); (iii) os 10 specs silenciosos sem explicação (§7.6); (iv) o passo interno do RV-Monitor em que o monitor por-`mf` criado por `init` herda o estado do monitor da fatia vazia — a difusão está provada no set e nos dados, mas essa derivação específica segue inferida da semântica do RV-Monitor; (v) `thread(...)` (§7.7); (vi) a re-implementação de `expandCallTarget` do censo "7/9" da §3.2 não foi refeita (tornou-se irrelevante frente ao censo observado em 219 APKs).

---

## Fontes

- ✅✅ [JavaMOP4 Syntax](https://web.archive.org/web/20190327032914/http://fsl.cs.illinois.edu/index.php/JavaMOP4_Syntax) — gramática BNF, PCDs admitidos, variáveis especiais
- ✅ `rvsec-mop/src/main/resources/jca/*.mop` (23) e `MultiSpec_1MonitorAspect.aj` (resíduo de build, 2026-07-08)
- ✅ `rvsec-agent/src/main/java/mop/MultiSpec_1RuntimeMonitor.java` (gerado, git-ignored, 2026-07-08)
- ✅ `rvsec-core/src/main/java/br/unb/cic/mop/{Property,ExecutionContext}.java`
- ✅ `rvsec-android/rvsec-instrumentation-dexlib2/` — `pointcut-engine`, `advice-emitter`, `dex-mutator`, `descriptor-reader`, `grammar-tests`
- ✅ `descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json` (115 advices)
- ✅ `javamop/src/main/java/javamop/output/{descriptor/DescriptorWriter,combinedaspect/MOPStatistics}.java`
- ✅ `rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules/` (49 `.crysl`, 1.5.2-jca)
- ✅ `ase-journal/dataset/results/errors.csv` (97.018), `cc.csv`, `cc_rv_mapping.csv` — **somente leitura**
- ✅ **`/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706`** — os APKs instrumentados que produziram os dados do artigo (219 APKs + 219 `.json` + 30 `.pkgdet`). Desmontados com `lib/dex2jar/d2j-baksmali.sh`; base da §3.7 e do censo de corpus da rev. 3. **Somente leitura** (extração para o scratchpad)
- ✅ **`rvsec-dataset/repos/<pkg>_<ver>.apk/`** — código-fonte dos apps do corpus (348 repositórios). Usado para a triangulação da §3.7. **Somente leitura**
- ✅ `rvsec-paper/rvsec.tex:40-43` (comentado)

Scripts e dados brutos da sessão no scratchpad: `G0_census.py` + `G0_census.json` (censo literal), `G0_census_aj.py` + `G0_census_aj.json` (censo sobre o `.aj` da campanha), `A1_extract.py` + `A1_property_graph.csv`, `A2_parse_crysl.py` + `A2_crysl_crosscheck.csv` + `A2_predicate_graph.csv`, `A3_codegen_survival.md` + `raw_guards.txt`, `A4_errors_analysis.py` + `A4_report.md` + `Q1..Q6_*.csv`, `B2_extract.py` + `B2_pcd_usage.md` + `B2_jca_call_hook_surface.md`, `census.py` + `B3_wrapper_collision.md`.

A matriz de PCD da §2.1 é o único artefato sem arquivo bruto separado — foi derivada em modo somente-leitura e está integralmente reproduzida aqui.
