# Investigação — o grafo de predicados e o suporte a pointcut designators no weaver dexlib2

**Data:** 2026-08-06 (revisão 4)
**Estado:** investigação concluída, **verificada adversarialmente** (rev. 3, §8) e **re-derivada de forma independente com todos os itens em aberto fechados** (rev. 4, §9). Nada implementado; nenhum `.mop`, nenhuma fonte do weaver, nada sob `$WS/ase-journal/` e nenhum APK ou repositório do dataset foi modificado.

> **Revisão 2** — a rev. 1 registrava em §7 que nenhum APK havia sido tecido e que a cadeia da colisão era derivação, não observação. Os APKs instrumentados da campanha estavam disponíveis o tempo todo em `$APKS`, e o código-fonte dos apps em `$REPOS/`. A §3.7 é nova e converte o principal resultado de derivação em observação, com triangulação fonte → bytecode → dado. Duas afirmações minhas da rev. 1 foram **refutadas pela observação** e estão corrigidas na §3.2.

> **Revisão 3 (verificação adversarial)** — sessão independente re-derivou as 30 alegações (B1–B6, G1–G12, A1–A12) dos artefatos primários; tabela de vereditos na §8. O núcleo sobreviveu inteiro — a colisão, a direção do defeito, a difusão e a datação fail-closed foram **confirmadas e generalizadas** (censo em 219/219 APKs; jar da campanha datado por prova binária). Correções aplicadas nesta revisão: **(a)** manchete da §4.4: 92% → **83%** de `ENSURES` presentes — a própria decomposição (33+1+2+2=38) contradizia o 42; ausentes de `REQUIRES` 27 → **28**; **(b)** §4.2: "43 das 49 escritas sem leitor" → **35**; **(c)** §4.5: 38 → **37** arestas, e o balde "inexpressível" **não é vazio** (`randomized[lSeed]`); **(d)** §4.4: `generatedSSLEngine` tem segundo produtor (`SSLContext.crysl:38`) e nenhum consumidor — a consequência estática vale só para `preparedOAEP`; **(e)** §3.6: a explicação dos 208 `X509` por "versões diferentes do okhttp" estava **errada** — o bytecode do sítio é idêntico nos dois apps; o valor vem da difusão de g3 a partir do literal `"X509"` de `de.duenndns.ssl.MemorizingTrustManager`; **(f)** §3.6: os 421 eventos restantes **ganharam mecanismo verificado** (L3.8 confirmada em bytecode, três rotas de criação não cobertas); **(g)** o corpus tem **219** APKs, não 234 (468 arquivos = 219 `.apk` + 219 `.json` + 30 `.pkgdet`); **(h)** `reset()` tem um chamador (teste); **(i)** o "~6,5×" da §4.7 corrigido; **(j)** referências §3.8→§3.7 e §3.4→§2.3 e frase duplicada da §3.2 corrigidas.

> **Revisão 4 (re-derivação independente + fechamento dos itens em aberto)** — sessão nova re-derivou do zero a colisão (fonte do weaver, fonte do **javamop**, DEX de produção, `errors.csv`), com scripts próprios que não reutilizam nada do scratchpad das rev. 2–3. O núcleo foi **reproduzido número a número**. Novidades desta revisão: **(a)** a causa-raiz da colisão foi localizada na **fonte do javamop** (`$JAVAMOP/output/combinedaspect/event/EventManager.java:91` + `$JAVAMOP/parser/ast/mopspec/MOPParameter.java:22-23`) — deixou de ser inferida da saída; **(b)** um **terceiro defeito**, independente da colisão e de direção oposta: o caminho *inline* do weaver trunca advices fundidos em `monitorCalls.get(0)`, descartando **9 eventos — todos emissores de erro** (§4.8). Ele explica sozinho as **zero** ocorrências de `UnsatisfiedConstraint` e quatro dos specs silenciosos; **(c)** o item (iv) da §8 (herança de estado) está **fechado em código**: `initEvent` clona o monitor da fatia vazia (`sourceLeaf.clone()`, `$MONITOR:17931-17952`); **(d)** §7.4 **quantificada**: ~17.175 dos 18.029 eventos do `TrustManagerFactorySpec` (95,3%) são artefato, e a correção é derivável das tabelas de transição; **(e)** §7.5 **fechada** — o jar da campanha foi o `android-36` do Docker (a campanha **não** foi afetada), mas no host a mesma regra escolhe `android-4`; **(f)** §7.7 **fechada e invertida** — `thread(...)` é absorvido pelo javamop e **não pode** chegar ao matcher; **(g)** §7.6 **fechada** para 12 dos 13 specs silenciosos, com censo de alcançabilidade nos 219 APKs; **(h)** F0.3 **fechada** — 51 sítios `addError`, e `UnsatisfiedConstraint` (8 sítios) nunca dispara; **(i)** achado novo: o `SSLContextSpec` (26.312 eventos, **27,1% do dataset**) sofre a mesma má-atribuição de sítio que o `TrustManagerFactorySpec`, o que a rev. 3 não examinou.

**Continua:** `docs/20260806_plano_specs_jca_android.md` (commit `31f7b883`), fase F0.
**Resolve:** a questão G0 do plano (§3, §5), o item F0.4' e, na rev. 4, **F0.3**.

## Marcadores de confiança

| | significado |
|---|---|
| ✅✅ | verificado contra documentação primária, com URL |
| ✅ | verificado por mim contra fonte do repositório ou dataset, **nesta sessão** |
| ⚠️ | vem de subagente ou relatório anterior, não re-derivado — é pista, não resultado |
| ❌ | verificado e **falso** |

Nenhum ⚠️ foi promovido a ✅ sem re-derivação própria. Onde um subagente e eu chegamos ao mesmo resultado por caminhos diferentes, está marcado ✅ e a dupla derivação está dita.

## Convenção de caminhos

Caminhos **dentro** do `rv-android` são relativos à raiz do projeto. Tudo **fora** dele é absoluto — este relatório cruza cinco árvores irmãs, e caminho relativo entre elas é ambíguo. Para não poluir cada citação, as raízes absolutas ganham abreviaturas, expandidas nesta tabela e em nenhum outro lugar:

| abreviatura | caminho absoluto | o que é |
|---|---|---|
| `$WS` | `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv` | raiz das árvores irmãs |
| `$JAVAMOP` | `$WS/rvsec/javamop/src/main/java/javamop` | fonte do javamop (gerador de aspecto/descritor) |
| `$DEXLIB2` | `$WS/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2` | weaver DEX-nativo (`pointcut-engine`, `advice-emitter`, `dex-mutator`, `descriptor-reader`, `cli`) |
| `$JCA` | `$WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca` | as 23 specs `.mop` do conjunto JCA |
| `$MONITOR` | `$WS/rvsec/rvsec/rvsec-agent/src/main/java/mop/MultiSpec_1RuntimeMonitor.java` | monitor gerado (git-ignored, 2026-07-08) |
| `$CORE` | `$WS/rvsec/rvsec/rvsec-core/src/main/java/br/unb/cic/mop` | `Property.java`, `ExecutionContext.java` |
| `$RESULTS` | `$WS/ase-journal/dataset/results` | `errors.csv`, `coverage.csv` da campanha — **somente leitura** |
| `$APKS` | `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706` | os 219 APKs instrumentados que produziram os dados — **somente leitura** |
| `$REPOS` | `$WS/rvsec-dataset/repos` | código-fonte dos apps do corpus — **somente leitura** |
| `$CRYSL` | `$WS/rvsec-dataset/src/rvsec_dataset/cognicrypt/CrySL-Rules` | as 49 regras CrySL 1.5.2 |

Duas abreviações a mais, para não repetir a raiz em cada citação de linha: um arquivo `.mop` citado só pelo nome (`CipherSpec.mop:66`) está em `$JCA`; um `.crysl` citado só pelo nome (`SecureRandom.crysl:46`) está em `$CRYSL`.

---

## 0. Sumário executivo

Quatro resultados mudam decisões do plano.

**1. A G0 estava mal colocada, e está resolvida por observação direta.** As duas hipóteses concorrentes — colisão de wrappers (L3.1) e binding de parâmetro (L3.2) — **são ambas verdadeiras**, e não competem: agem sobre observáveis diferentes. A colisão decide **se** o algoritmo válido chega a ser registrado (é a causa única do valor vazio); o binding vazio decide **onde** um algoritmo inválido registrado aterrissa (é a causa única do `X509` aparecer em sítios que nunca passaram `X509`). O dilema "ou 100% falso positivo, ou observações genuínas" é falso.

✅ Isto **não é dedução**: a §3.7 desmonta o DEX dos APKs instrumentados da própria campanha e mostra que `TrustManagerFactorySpec_g1Event` está compilado no binário e **não é referenciado por nenhuma instrução**, em 4 de 4 APKs; e que `org/conscrypt/SSLParametersImpl` passa `getDefaultAlgorithm()` no bytecode enquanto os dados registram `X509` naquele sítio — contaminação entre instâncias, demonstrada.

**2. A alegação-manchete sobre PCDs é falsa no estado atual do código.** ❌ Os sete-a-nove designators **não** casam-true em silêncio: `matchNamedRef` **falha fechado** com `UnresolvedNamedRefException` desde `3af5b3aa` (2026-05-29) — **antes** da campanha de julho. A superfície real de match-true silencioso é muito menor e está em outro lugar.

**3. O grafo de predicados está pior do que o relatado, e o defeito é assimétrico.** **83%** das cláusulas `ENSURES` do CrySL têm contrapartida escrita (corrigido na rev. 3 de 92% — ver §4.4); apenas **22% dos `REQUIRES` têm leitura**. A tradução produz predicados com fidelidade e quase não os consome.

**4. (rev. 4) Há um terceiro defeito de weaving, independente dos outros dois e de direção oposta.** ✅ O caminho *inline* do weaver — o que trata construtores, advices `before`, `after-throwing` e `staticinitialization` — lê apenas `monitorCalls.get(0)` de cada advice (`EmitContext.java:50-52`, `MonitorInvokeBuilder.java:238-241`, `StaticInitializationEmitter.java:145-148`), enquanto o caminho de wrapper itera a lista inteira (`WrapperEmitter.java:637`). Quando o javamop **funde** dois eventos num advice, o inline emite o primeiro e **descarta o resto, em silêncio e sem contador**. No descritor de produção são **7 advices truncados e 9 eventos descartados — e todos os 9 são eventos que emitem erro** (§4.8). Consequência direta e verificada: as **8 cláusulas `addError(ErrorType.UnsatisfiedConstraint)` do conjunto `jca` nunca disparam** — zero ocorrências em 97.018 eventos. Enquanto a colisão de wrappers mata o registrador do caso **válido** e fabrica falso positivo, a truncagem inline mata o emissor do caso **inválido** e fabrica **falso negativo**.

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

**O JavaMOP não restringe nada.** Qualquer PCD que o AspectJ aceite é sintaticamente legal num `.mop`. Some-se a isso o fato ✅ de que o `DescriptorWriter` grava a expressão **verbatim, sem filtrar** (`$JAVAMOP/output/descriptor/DescriptorWriter.java:114-117`), e a conclusão é que **toda** a restrição de PCD vive no matcher do dexlib2. É por isso que a §4.1 do plano é uma questão de autoria e não só de engenharia: nada entre o `.mop` e o weaver diz "não".

A página também documenta ✅✅ as quatro variáveis especiais (`__RESET`, `__LOC`, `__SKIP`, `__STATICSIG`) e que `__STATICSIG` devolve um `org.aspectj.lang.Signature` — o que explica o shim em `rvsec-core` (§2.3).

---

## 2. INVESTIGAÇÃO B — matriz de suporte a PCD

### 2.1 A matriz

Derivada da fonte em `$DEXLIB2`. Nesta seção e na §3, nomes de arquivo `.java` citados sem raiz pertencem a `$DEXLIB2` (`PointcutExpressionParser` e `PointcutMatcher` em `pointcut-engine/`, `DexWeaver` em `dex-mutator/`, os `*Emitter` em `advice-emitter/`). Linhas em itálico são as que contradizem o plano.

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
| `thread(...)` (JavaMOP) | ausente do dexlib2 | — | — | — | ✅ **rev. 4:** absorvido pelo javamop como o `condition` — `RemoveThreadVisitor`, `$JAVAMOP/parser/ast/mopspec/EventDefinition.java:117`. **Não chega ao matcher**, logo não cai no `throw`. Risco residual: binding não resolvível → drop **com contador** (§7.7). Uso no corpus: **0** |
| `threadName(...)` (JavaMOP) | ausente do dexlib2 | — | — | — | ✅ **rev. 4 — linha nova:** idem, `RemoveThreadNameVisitor`, `EventDefinition.java:127`. Uso no corpus: **0** |

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

> **Rev. 3 — o "antes da campanha" deixou de ser suposição.** A campanha rodou o `instr-cli.jar` do gh73 (fix `d73ebc41`, 2026-06-30, ~1h antes da instrumentação; bind-mount documentado em `$WS/rvsec-dataset/docs/20260702_phase8-instrumentation-results.md:26`), que é descendente de `3af5b3aa` por 77 commits (`git merge-base --is-ancestor` confirma). Prova independente de documentação: **130 dos 219 APKs instrumentados contêm entradas DEX `037`/`038`/`039`**, e o weaver pré-gh73 estampava `dex035` incondicionalmente — o binário da campanha necessariamente contém o fail-closed. Nenhum commit posterior a `3af5b3aa` reabriu `matchNamedRef` (histórico de `PointcutMatcher.java` verificado commit a commit).

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

✅ `__STATICSIG` aparece 3 vezes, todas em `generic_new`, e é de fato a razão do shim: `$WS/rvsec/rvsec/rvsec-core/src/main/java/org/aspectj/lang/Signature.java` e `ClassSignature.java` são os dois únicos arquivos sob `org/aspectj/` no core.

### 2.4 Um achado não previsto: 23 advices `execution(...)` no aspecto gerado

✅ O `.aj` gerado do `jca` tem **138** advices; o descritor JSON tem **115**. A diferença são 23 advices injetados pelo javamop, um por spec:

```java
after () : execution(* org.apache.maven.surefire.booter.ForkedBooter.runSuitesInProcess(..)) {
    System.err.println("==start KeyPairSpec ==");
```

✅ A origem é `$JAVAMOP/output/combinedaspect/MOPStatistics.java:78`. Alvo: uma classe do **Maven Surefire**, irrelevante para um APK.

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

✅ **Rev. 4 — a regra de fusão deixou de ser inferida da saída e está lida na fonte do javamop.** `$JAVAMOP/output/combinedaspect/event/EventManager.java:62-101` percorre os advices já emitidos e só funde (`advice.addEvent(...)`, `:97`) quando **todas** estas condições valem: mesma posição (`:88`), mesmo `isAround` (`:81`), **`advice.retVal.equals(event.getRetVal())` (`:91`)**, mesmo `throwVal` (`:93`) e pointcuts equivalentes em CNF (`:96`). O predicado decisivo é o `:91`, e `MOPParameter.equals` compara **tipo *e* nome**:

```java
// $JAVAMOP/parser/ast/mopspec/MOPParameter.java:22-23
public boolean equals(MOPParameter param){
    return type.equals(param.getType()) && name.equals(param.getName());
}
```

Logo `returning(TrustManagerFactory mf)` e `returning(TrustManagerFactory k)` — mesmo tipo, nomes diferentes — **falham a igualdade e impedem a fusão**. E `MOPParameters.equals` exige tamanhos iguais (`$JAVAMOP/parser/ast/mopspec/MOPParameters.java:169`), o que explica o segundo caso: o `unsafe_protocol` do `SSLContextSpec` **não tem cláusula `returning` nenhuma** (`$JCA/SSLContextSpec.mop:46`), então seu `retVal` tem tamanho 0 contra 1 do `g1` — nunca funde. Os dois casos de colisão do conjunto `jca` têm, portanto, a **mesma causa-raiz**, num único `if`.

**Passo 2 — o descritor registra os dois.** ✅ Verificado no descritor real (`$DEXLIB2/descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json`; ⚠️→✅ um subagente confirmou que este arquivo é byte-idêntico a saída real do pipeline em `rv-android/data/validacao_ajc/local_A_dex/monitors/`):

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

> **Rev. 4 — censo refeito do zero nos 219 APKs, com script novo (`census4.py`), e o resultado é idêntico.** 219/219 com **96 wrappers** e **as mesmas 10 assinaturas disputadas**; mortos em assinatura disputada: mín. **15**, máx. **22**, mediana **19**; **zero falsificações** (nunca dois wrappers da mesma assinatura ambos vivos; o vivo é sempre o último declarado). A formulação mais limpa do defeito é esta, e é nova:
>
> | wrapper | apps com ≥1 call site |
> |---|---:|
> | `TrustManagerFactory.getInstance(String)` → **`g1`** | **0 / 219** |
> | `TrustManagerFactory.getInstance(String)` → `g3` | **152 / 219** |
> | `SSLContext.getInstance(String)` → **`g1`** | **0 / 219** |
> | `SSLContext.getInstance(String)` → `unsafe_protocol` | **157 / 219** |
>
> Em 219 APKs de produção, os dois wrappers que registram o caso **válido** não são chamados por **nenhum** app, enquanto os que registram o caso **inválido** são chamados por 152 e 157. Não é amostragem: é a chave do mapa.

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

✅ E o `condition(...)` de fato desce para dentro do monitor, não para o pointcut — `$MONITOR:10098-10102`:

```java
final boolean Prop_1_event_g1(String alg, TrustManagerFactory mf) {
    { if ( ! (algorithms.contains(alg)) ) { return false; }
      { trustManagerFactory = mf; currentAlgorithmInstance = alg; } }
```

### 3.4 O outro mecanismo: g3 vive na fatia de parâmetro vazio

✅ `$MONITOR`, comparando os dois despachos:

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

**Triangulação em três níveis.** O código-fonte dos apps do corpus está em `$REPOS/<pkg>_<ver>.apk/`. Para `com.etesync.syncadapter_20700`:

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

### 3.9 A correção — e por que a de uma palavra não basta (rev. 4)

A rev. 3 propôs, na §9.2, renomear o binding `returning` do `g3` de `k` para `mf`. Isso está **certo e é necessário**, mas a rev. 4 mostra que é **metade** da correção, e que a outra spec afetada precisa de um remendo diferente.

**Parte 1 — ligar o parâmetro da spec.** É o que desfaz a fusão perdida e, com ela, os dois mecanismos de uma vez: com o mesmo nome de binding, o `EventManager` funde os advices (§3.1), o weaver registra **um** wrapper com **duas** chamadas de monitor, e o evento passa a ser indexado pelo objeto criado em vez da fatia vazia. Some a colisão **e** some a difusão.

| spec | sítio | hoje | correção |
|---|---|---|---|
| `TrustManagerFactorySpec` | `$JCA/TrustManagerFactorySpec.mop:44` | `returning(TrustManagerFactory k)` | `returning(TrustManagerFactory mf)` |
| `SSLContextSpec` | `$JCA/SSLContextSpec.mop:46` | `event unsafe_protocol after(String protocol):` — **sem `returning`** | `event unsafe_protocol after(String protocol) returning(SSLContext ctx):` |

✅ **A parte 1 não é especulação: o estado-alvo já existe no mesmo artefato de produção.** No DEX de `com.etesync.syncadapter_20700`, o `KeyManagerFactorySpec` — que difere do `TrustManagerFactorySpec` *apenas* por usar `k` de forma consistente em todos os eventos (`$JCA/KeyManagerFactorySpec.mop:20,26,34,42,49,60`) — tem um **único** wrapper carregando as **duas** chamadas de monitor:

```
.method public static javax_net_ssl_KeyManagerFactory_getInstance(Ljava/lang/String;)...
    ... -> KeyManagerFactorySpec_g1Event
    ... -> KeyManagerFactorySpec_g3Event
```

Ou seja: a fusão que a correção pretende produzir é observável hoje, na spec irmã, no binário da campanha.

> **Nota de linhagem (rev. 4).** O parâmetro do `TrustManagerFactorySpec` é `mf` (`:21`), mas o `g3` usa `k` — que é exatamente o nome do parâmetro do `KeyManagerFactorySpec` (`:20`). Some-se a isso os três defeitos de cópia-e-cola já documentados no `gtm1` (§4.3d: constante `GENERATED_KEY_MANAGERS`, binding `TrustManager[][]`, retorno `KeyManager[]`) e o quadro fecha: **o `k` do `g3` é o quarto resíduo da mesma cópia do `KeyManagerFactorySpec`**. A colisão não é um bug independente do weaver — é um copy-paste de spec que o weaver deixou de detectar.

**Parte 2 — pôr o evento do caso inválido na máquina de estados.** ✅ Verificado nas tabelas geradas (`$MONITOR:10004-10008`): nem `g3` (TMF) nem `unsafe_protocol` (SSLContext) aparecem na `fsm`/`ere` das suas specs, então o gerador lhes dá transição para `fail` **em todo estado** (`Prop_1_transition_g3[] = {3,3,3,3}`). Isso significa que, mesmo depois da parte 1, todo algoritmo fora da allow-list produziria o par `UnsafeAlgorithm` + `InvalidSequenceOfMethodCalls` — o segundo espúrio, porque *usar um algoritmo fraco não é uma sequência inválida de chamadas*. A intenção legível do autor é que o evento do caso inválido registre o valor e deixe o `init` reportar; para isso ele precisa levar ao mesmo estado que o `g1`:

```
fsm:
  start [ g1 -> waitingInit
          g2 -> waitingInit
          g3 -> waitingInit ]        // <- acrescentar (idem unsafe_protocol -> s1 no SSLContextSpec)
```

**Parte 3 — o gate no weaver.** As partes 1 e 2 consertam estas duas specs; não consertam a **classe** do defeito. Qualquer spec nova pode recriar a colisão com um nome de binding distraído, e nada — nem no javamop, nem no descritor, nem no weaver — diz "não". Ver §5, item 5.

### 3.10 O mesmo defeito no `SSLContextSpec`, e ele é 27% do dataset (rev. 4)

A rev. 3 tratou o `SSLContextSpec` só pelo lado do valor vazio (51 eventos). ✅ A rev. 4 mediu a spec inteira e o quadro é bem maior:

| spec | eventos | % do dataset | apks | sítios | tipos |
|---|---:|---:|---:|---:|---|
| `SSLContextSpec` | **26.312** | **27,1%** | 62 | 125 | `InvalidSequenceOfMethodCalls` 17.510 · `UnsafeProtocol` 8.802 |
| `TrustManagerFactorySpec` | **18.029** | 18,6% | 64 | 70 | `InvalidSequenceOfMethodCalls` 9.015 · `UnsafeAlgorithm` 9.014 |

Valores reportados pelo `SSLContextSpec`: `TLS` 8.648 · `SSL` 103 · vazio 51 (soma 8.802 ✅).

O ponto: como o `unsafe_protocol` **não liga nenhum parâmetro**, ele escreve na fatia vazia e difunde exatamente como o `g3` do TMF. Logo os **8.802 `UnsafeProtocol` sofrem a mesma má-atribuição de sítio** — o protocolo reportado é o último que passou pela fatia vazia, não necessariamente o daquele contexto.

✅ **Prova direta, num app que exibe dois protocolos distintos.** `de.lukasneugebauer.nextcloudcookbook_62` reporta `SSL` (103) em `OkHttpClientProvider.configureTrustAllCertificates` e `TLS` (162) em `Platform.newSslSocketFactory`. No DEX tecido há exatamente **dois** sítios de `SSLContext.getInstance`, e ambos vão para o wrapper `_2` (o do `unsafe_protocol`; o do `g1` está morto):

| sítio (smali) | argumento | wrapper |
|---|---|---|
| `de/lukasneugebauer/.../OkHttpClientProvider` | `const-string v1, "SSL"` | `javax_net_ssl_SSLContext_getInstance_2` |
| `okhttp3/internal/platform/Platform` (método `newSSLContext`) | `const-string v0, "TLS"` | `javax_net_ssl_SSLContext_getInstance_2` |

Note que o sítio **criador** do `TLS` é `Platform.newSSLContext`, e o sítio **reportado** é `Platform.newSslSocketFactory` — métodos diferentes. Os dois valores disputam a mesma fatia vazia, e qual deles um dado `init` lê depende da ordem. **A atribuição de sítio do `UnsafeProtocol` é uma corrida**, não uma observação.

### 3.11 Quanto custa a colisão — §7.4 fechada por derivação (rev. 4)

O item 4 da §7 (“se algum wrapper morto custa uma violação real”) estava aberto por se supor que exigiria re-executar a campanha. Não exige: o custo é **derivável** das guardas e das tabelas de transição, e a chave é um argumento que o próprio mecanismo fornece.

**O valor vazio prova que o algoritmo era válido.** O wrapper vivo é o do `g3`, cuja guarda é `!algorithms.contains(alg)`; ele dispara em **toda** chamada de 1 argumento. Se o algoritmo passado fosse inválido, o `g3` escreveria esse valor e o relato mostraria o valor, não o vazio. Como o relato é vazio em 8.371 eventos, o `g3` nunca escreveu — logo `!contains(alg)` foi **falsa** — logo **`alg ∈ {PKIX, SunX509}`**. Não é preciso saber o que `getDefaultAlgorithm()` devolve no Android: o dado diz.

**O que aconteceria com a correção, lido nas tabelas** (`$MONITOR:10004-10008`; estados 0=`start`, 1=`final`/`match1`, 2=`waitingInit`, 3=`fail`):

| hoje (g1 morto) | com a correção (g1 vivo, fundido) |
|---|---|
| nada registrado; `currentAlgorithmInstance` fica `""` | `g1` dispara: `transition_g1[0] = 2` (`waitingInit`), grava `alg` |
| `init` a partir de `start`: `transition_init[0] = 3` = **`fail`** → `InvalidSequenceOfMethodCalls` | `init` a partir de `waitingInit`: `transition_init[2] = 1` = `final` → **nenhum erro de sequência** |
| guarda do `init`: `!contains("")` = **verdadeira** → `UnsafeAlgorithm` "found ." | guarda: `!contains("PKIX")` = falsa → **nenhum `UnsafeAlgorithm`** |

**Conta do custo, para o `TrustManagerFactorySpec`:**

| população | eventos | destino com a correção |
|---|---:|---|
| valor vazio (`UnsafeAlgorithm`) | 8.371 | **desaparecem** — algoritmo válido (soma 8.587 com a linha do `X509` difundido) |
| `InvalidSequenceOfMethodCalls` co-emitidos (9.015 − 427 que sobrevivem) | 8.588 | **desaparecem** — `init` passa a ir para `final` |
| `X509` em sítio que passa `getDefaultAlgorithm()` (openhab `Platform` 208 + etesync `SSLParametersImpl` 8) | 216 | **desaparecem** — eram difusão |
| `X509` em sítio que passa o literal (openhab `MemorizingTrustManager` 229, luhmer idem 190, etesync `CertUtils` 8) | 427 | **permanecem**, agora com sítio correto — e ainda assim falso positivo de camada 1 (L1.3) |

**≈17.175 dos 18.029 eventos do `TrustManagerFactorySpec` (95,3%) são artefato de instrumentação** — 17,7% de todo o dataset de 97.018 eventos. E o saldo de **verdadeiros positivos permanece zero**, pelas três razões independentes da §3.8.

> Limite honesto do que isto é: uma previsão derivada das tabelas e das guardas, não uma medição. Ela fica falsificável de forma barata — aplicadas as partes 1 e 2 da §3.9, uma única re-execução do `org.openhab.habdroid_589` e do `com.etesync.syncadapter_20700` decide. O que **não** é previsão é a cadeia causal: essa está observada (§3.7) e lida no código (§3.4, §3.12).

### 3.12 A herança de estado — item (iv) da §8 fechado em código (rev. 4)

A rev. 3 registrou como não verificado “o passo interno do RV-Monitor em que o monitor por-`mf` criado por `init` herda o estado do monitor da fatia vazia”. ✅ **Está no código gerado, não é mais inferência.** São dois trechos complementares:

**(1) o `g3` cria e alimenta a fatia vazia** — `$MONITOR:17865-17896`:

```java
public static final void TrustManagerFactorySpec_g3Event(String alg, TrustManagerFactory k) {
    matchedEntry = TrustManagerFactorySpec__Map;              // a fatia <>
    if (matchedLeaf == null) {
        TrustManagerFactorySpecMonitor created = new TrustManagerFactorySpecMonitor(...);
        matchedEntry.setValue2(created);                       // cria o leaf <>
        enclosingSet.add(created);
    }
    stateTransitionedSet.event_g3(alg, k);                     // difunde ao conjunto inteiro
}
```

**(2) o `init` clona esse leaf ao criar o monitor de um `mf` novo** — `$MONITOR:17931-17952`:

```java
// D(X) createNewMonitorStates:4 when Dom(theta'') = <>
TrustManagerFactorySpecMonitor itmdLeaf = TrustManagerFactorySpec__Map.getValue2();
sourceLeaf = itmdLeaf;
if (sourceLeaf != null) {
    ...
    // D(X) defineTo:6
    TrustManagerFactorySpecMonitor created = (TrustManagerFactorySpecMonitor) sourceLeaf.clone();
```

É o passo `defineTo` do algoritmo D(X) de slicing paramétrico. **Só quando a fatia vazia está ausente** o `init` cai no `new ...Monitor(...)` do `D(X) main:4`.

Isso fecha a contaminação com dois canais distintos, e o segundo é o que explica o caso decisivo:

- **canal A — difusão lateral:** `event_g3` itera o conjunto inteiro e atinge os monitores **já existentes**;
- **canal B — herança por clonagem:** todo monitor criado **depois** nasce com o `currentAlgorithmInstance` da fatia vazia.

✅ **O canal B é o que explica o `openhab`, e a rev. 3 o atribuía ao canal A.** Em `org.openhab.habdroid_589` o `Platform.platformTrustManager` reporta 208 `X509` — mas seu monitor é criado *pelo próprio* `init`, depois de o `MemorizingTrustManager` já ter escrito `"X509"` na fatia vazia. Um monitor recém-criado não poderia ter sido alcançado por uma difusão anterior; ele **herdou por clonagem**. Sem o `sourceLeaf.clone()`, o dado do openhab seria inexplicável.

---

## 4. INVESTIGAÇÃO A — o grafo de predicados

### 4.1 O substrato

✅ `Property.java` tem **23** constantes (linhas 8–30). ✅ `ExecutionContext.java` (147 linhas) é um **singleton estático** sobre um `Map<Property, Set<Object>>`, com três operações que tocam o grafo: `setProperty` (escrita, `:80-87`), `validate` (leitura, `:96-98`), `remove` (`:52-57` em massa — `@Deprecated` — e `:59-66` individual).

Quatro propriedades do substrato limitam o que o grafo pode expressar, todas ✅:

- **Chaveado por `equals`/`hashCode`, não por identidade.** Para `byte[]`/`char[]` isso é identidade de referência na prática — qualquer cópia defensiva perde o predicado. Para `String`, ao contrário, conflate objetos estruturalmente iguais e não relacionados. O grafo não é nem solidamente identitário nem solidamente por valor.
- **Não é thread-safe.** `HashMap`/`HashSet` nus, `instance()` com init preguiçosa não sincronizada.
- **Vaza por construção.** Toda escrita guarda referência **forte** num set estático; só saem por `remove` em handler de falha (9 sítios) ou `reset()` (nunca chamado em produção; um único chamador, em teste — `$WS/rvsec/rvsec/rvsec-agent/src/test/.../bench01/SecureRandomTest.java:19`).
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

**Os baldes não se misturam, e a distinção decide o tipo de correção.** A rev. 2 registrava "nenhuma aresta é inexpressível"; a rev. 3 corrige: o *workaround* do `ExecutionContext` cobre 36 das 37, mas não predicados de proveniência sobre primitivos. A admissão do artigo é real. Verbatim de `$WS/rvsec-paper/rvsec.tex:40-43`, 100% comentado:

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
- ⚠️→✅ `$MONITOR` **não é artefato commitado** — está em `.gitignore`. Mas é **fresco** (2026-07-08, posterior ao `.mop` mais novo), logo é evidência admissível sobre as fontes atuais. O que é commitado (`rvsec-logger-csv/src/main/mop/*.aj`, fevereiro) é que está **velho**.
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

### 4.8 O terceiro defeito: o caminho inline trunca advices fundidos (rev. 4)

Este achado é novo e não decorre de nenhuma hipótese anterior. Ele apareceu ao perguntar por que `ErrorType.UnsatisfiedConstraint` — que tem **8** sítios `addError` no conjunto `jca` (§4.9, F0.3) — tem **zero** ocorrências em 97.018 eventos.

**O mecanismo.** Um advice do descritor pode carregar **mais de uma** chamada de monitor, precisamente quando o javamop fundiu dois eventos (§3.1). Os dois caminhos de emissão do weaver tratam essa lista de forma diferente:

| caminho | trata `monitorCalls` | sítio |
|---|---|---|
| **wrapper** (advices `after` sobre método não-construtor) | ✅ itera a lista inteira | `$DEXLIB2/advice-emitter/.../WrapperEmitter.java:637` |
| **inline** (construtores, `before`, `after-throwing`, `staticinitialization`) | ❌ **só `get(0)`** | `$DEXLIB2/advice-emitter/.../EmitContext.java:50-52`; `MonitorInvokeBuilder.java:238-241` (usado em `:50`, `:136`, `:217`); `AfterThrowingEmitter.java:72`; `StaticInitializationEmitter.java:145-148` |

```java
// EmitContext.java:49-53 -- o comentário admite a premissa que o corpus viola
/** Convenience accessor for the single monitor call typical of a MOP advice. */
public MonitorCallDescriptor primaryMonitorCall() {
    if (advice.getMonitorCalls().isEmpty()) return null;
    return advice.getMonitorCalls().get(0);
}
```

O advice cai no caminho inline sempre que `WrapperEmitter.shouldWrap` é falso (`:138-140` — só `after`) **ou** quando o alvo do `call(...)` é um construtor (`:215-219`, que faz `continue` explícito). Como os *parameter specs* do JCA são todos criados por `new`, é exatamente a família mais dependente de fusão que cai no caminho que trunca.

✅ **Medição no descritor de produção** (`results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json`, 115 advices). O descritor é **estável e datado**: entre os 8 descritores gerados desde junho, **7 são byte-idênticos** (md5 `9f00b835…`), incluindo o de `results/gh73_verify_crypto/` de **2026-06-30** — a véspera da instrumentação da campanha (APKs de 2026-07-01). Medir o de `gh92_e2e2` é, portanto, medir o da campanha. *(O único divergente é `results/gh75_docker_e2e/`, `adb118d2…`, irrelevante aqui.)*

- **17** advices têm mais de uma `monitorCall`;
- **10** deles vão pelo wrapper e são emitidos por inteiro;
- **7** vão pelo inline e são **truncados**, descartando **9 eventos**.

| advice (expressão) | mantido | **descartado** |
|---|---|---|
| `call(public IvParameterSpec.new(byte[])) && args(iv)` | `c1Event` | `c3Event` |
| `call(public IvParameterSpec.new(byte[], int, int)) && args(iv, offset, len)` | `c2Event` | `c4Event` |
| `call(public PBEKeySpec.new(char[], byte[], int, int)) && args(...)` | `c1Event` | `err1Event`, `err2Event`, `err3Event` |
| `call(public PBEParameterSpec.new(byte[], int)) && args(salt, iterationCount)` | `c1Event` | `c3Event` |
| `call(public SecretKeySpec.new(byte[], String)) && args(...)` | `c1Event` | `c3Event` |
| `call(public SecretKeySpec.new(byte[], int, int, String)) && args(...)` | `c2Event` | `c4Event` |
| `call(public SecureRandom.new(byte[])) && args(seed)` | `c2Event` | `c3Event` |

**Os 9 descartados são, sem exceção, os eventos que emitem erro.** Confronte com a contagem da §4.9: os 8 sítios `UnsatisfiedConstraint` do conjunto `jca` estão em `IvParameterSpec` (2), `SecretKeySpecSpec` (2), `PBEKeySpecSpec` (3) e `SecureRandomSpec` (1) — **todos** dentro de eventos descartados. É a explicação completa do zero observado.

✅ **Confirmado no DEX, e no corpus inteiro.** Em `com.etesync.syncadapter_20700`, `IvParameterSpecSpec_c3Event` e `c4Event` estão **definidos** no monitor (`MultiSpec_1RuntimeMonitor.smali:3286` e `:3383`) e têm **zero** `invoke-static` em todo o APK, enquanto `c1Event` é chamado nos sítios esperados (`org/conscrypt/IvParameters.smali:138`, `org/conscrypt/OpenSSLCipher.smali:383`). Um censo de alcançabilidade nos **219/219** APKs (§9, `reachcensus.py`) confirma: **nenhum dos 9 eventos descartados é referenciado a partir de código de aplicação em nenhum APK do corpus**, enquanto os eventos “mantidos” das mesmas specs aparecem em massa (`SecretKeySpecSpec_c1Event` em 193 APKs, `IvParameterSpecSpec_c1Event` em 85, `PBEParameterSpecSpec_c1Event` em 19).

**Por que o mantido é sempre o do caso válido.** `get(0)` preserva a ordem de declaração no `.mop`, e o idioma da tradução é declarar primeiro o evento do caso válido (`c1`, `c2`) e depois o do caso inválido (`c3`, `c4`, `err*`). Some-se isso ao mecanismo da §3.3 e o sistema tem **dois vieses opostos**:

| defeito | quem morre | direção do erro |
|---|---|---|
| colisão de wrappers (*last-writer-wins*) | o registrador do caso **válido** | **falso positivo** |
| truncagem inline (*first-call-wins*) | o emissor do caso **inválido** | **falso negativo** |

Os dois são silenciosos e nenhum tem contador. A §3.3 dizia “o defeito produz falso positivo, nunca falso negativo” — verdade **sobre a colisão**, e é preciso ler assim: o sistema como um todo produz os dois, por caminhos diferentes.

### 4.9 Os 13 specs silenciosos — §7.6 fechada (rev. 4)

✅ Re-derivado de `errors.csv`: das **23** specs `jca`, **10** disparam e **13** nunca disparam. As que disparam: `CipherSpec`, `KeyPairGeneratorSpec`, `KeyPairSpec`, `KeyStoreSpec`, `MacSpec`, `MessageDigestSpec`, `SSLContextSpec`, `SecureRandomSpec`, `SignatureSpec`, `TrustManagerFactorySpec`.

✅ Recontagem dos `addError` (**F0.3, fechada**): **51 sítios** em 21 das 23 specs. Por `ErrorType`, contra o que os dados mostram:

| `ErrorType` | sítios no `.mop` | ocorrências em `errors.csv` |
|---|---:|---:|
| `InvalidSequenceOfMethodCalls` | 23 | 70.760 |
| `UnsafeAlgorithm` | 17 | 15.444 |
| **`UnsatisfiedConstraint`** | **8** | **0** ← §4.8 |
| `UnsafeProtocol` | 1 | 8.802 |
| `InvalidKeyStoreType` | 1 | 2.005 |
| `InvalidKeySize` | 1 | 7 |

As duas specs sem `addError` são `SecretKeySpec.mop` e `RandomStringPassword.mop` — as mesmas duas sem `@fail`.

**A explicação, spec a spec.** Três mecanismos dão conta de 12 das 13; o 13º precisa de dado de runtime que não temos.

| spec | mecanismo | evidência |
|---|---|---|
| `GCMParameterSpecSpec` | **(A)** `fail` inalcançável por construção | `transition_c1 = {1,2,2}`: exigiria um 2º `c1` no mesmo monitor, mas o monitor é chaveado pelo objeto `returning` e cada `new` cria um novo. Tecido em **51/219** APKs — e mesmo assim mudo |
| `DHGenParameterSpecSpec` | **(A)** idem | `transition_c1 = {1,2,2}`, evento único. Tecido em 2/219 |
| `HMACParameterSpecSpec` | **(A)** idem **+ tipo inexistente no Android** | `transition_c = {1,2,2}`; e o import é `javax.xml.crypto.dsig.spec.HMACParameterSpec` (`$JCA/HMACParameterSpecSpec.mop:3`) — ✅ `javax/xml/crypto` **não existe** no `android.jar` (0 entradas; as outras 4 classes de parameter spec existem). Tecido em 2/219 apps, que empacotam uma lib XML-DSig própria |
| `IvParameterSpecSpec` | **(B)** emissores de erro descartados pelo inline (§4.8) **+ (A)** | `c3`/`c4` (`{2,2,2}`, os 2 `UnsatisfiedConstraint`) nunca tecidos; `c1`/`c2` (`{1,2,2}`) não alcançam `fail`. `c1Event` tecido em 85/219 |
| `SecretKeySpecSpec` | **(B)** + **(A)** | `c3`/`c4` descartados; `c1`/`c2` `{1,2,2}`. `c1Event` tecido em **193/219** — a spec mais amplamente tecida do conjunto, e completamente muda |
| `PBEParameterSpecSpec` | **(B)** + **(A)** | `c3` descartado; `c1`/`c2` `{1,2,2}`. Tecido em 19/219 |
| `SecretKeySpec` | **(C)** estruturalmente incapaz | sem `@fail`, `@match` vazio (rev. 3) |
| `RandomStringPasswordSpec` | **(C)** idem | sem `@fail`, `@match` vazio; é propagador de taint (§4.3f) |
| `KeyManagerFactorySpec` | **(C)** o vencedor da colisão registra o caso **válido** | guarda `contains(alg)` (§3.7); 0 linhas no CSV |
| `CipherInputStreamSpec` | **(D)** exposição estática mínima | monitor **não paramétrico** (`CipherInputStreamSpec()`, sem parâmetro) e `fail` bem alcançável (`{3,4,4,4,4}`), mas os wrappers de `read`/`close` têm call site em apenas **13/219** APKs |
| `CipherOutputStreamSpec` | **(D)** idem | wrappers de `write`/`flush`/`close` com call site em **10/219** |
| `KeyGeneratorSpec` | **(D)** idem | `init` inline tecido em 66/219, wrappers com call site em 69/219; `fail` e o `UnsafeAlgorithm` do `gk1` alcançáveis, mas não exercitados |
| `PBEKeySpecSpec` | **(B) parcial — resta lacuna** | `err1`–`err3` descartados (§4.8); sobram `f1`/`f2`, que **transitam para `fail`** (`{3,3,3,3}`) e **estão tecidos** em 20/219 e 1/219 APKs (o wrapper do `c2` tem call site em apenas 2/219). Que não tenham disparado só pode ser explicado por não-execução em runtime — **não fechado por análise estática** |

Em resumo: **(A)** ERE de evento único com monitor chaveado pelo objeto criado → `fail` inalcançável, 3 specs; **(B)** emissores de erro descartados pela truncagem inline, 4 specs; **(C)** incapacidade estrutural declarada, 3 specs; **(D)** API pouco ou nada exercitada, 3 specs. Resta apenas o `PBEKeySpecSpec` com lacuna genuína.

> O mecanismo **(A)** é uma generalização do que a rev. 3 achou só para o `GCMParameterSpecSpec`. Ele merece registro como padrão de tradução, não como bug isolado: **toda spec CrySL cujo `ORDER` é um único evento de construção vira, na tradução para JavaMOP com monitor chaveado pelo objeto construído, uma spec que não pode falhar.** São 3 das 23 no conjunto `jca`.

---

## 5. O gate de PCD (F0.4') — desenho, não implementação

O problema mudou de forma com a §2.2, e o gate deve mudar junto. Ele **não** precisa mais proteger contra nove PCDs que casam-true. Precisa cobrir:

1. **`execution(...)`** — hoje casa a entrada de todo método ignorando a assinatura, sem contador e sem teste que fixe o comportamento. É o único match-true silencioso realmente perigoso.
2. **`within(...)` positivo e `!adviceexecution()`** — match-true silencioso; o segundo descarta a negação por usar `contains` em vez de igualdade.
3. **Os nove que falham fechado** — hoje `throw` no laço principal, mas **`false` silencioso** na sonda do `commonPointcut` (`DexWeaver.java:695-700`). Um gate na geração transforma um abort tardio em erro cedo e legível.
4. **`parseCommonPointcut` devolvendo `null`** — o único caminho **fail-open**: derruba todas as exclusões daquele weave. É o item mais urgente dos quatro.
5. **A colisão de assinatura** — o gate natural é o mesmo `containsKey` que já existe em `DexWeaver.java:208`: falhar alto quando duas entradas disputam uma chave, em vez de sobrescrever.
6. **(rev. 4) A truncagem inline de advices fundidos** — hoje `monitorCalls.get(0)` descarta o resto em silêncio (§4.8). Duas ações, em ordem de custo: **(a)** gate imediato — falhar alto (ou ao menos contar) quando um advice com `monitorCalls.size() > 1` cai no caminho inline; **(b)** correção real — fazer o inline iterar a lista, como o `WrapperEmitter` já faz. É o item de **maior impacto sobre validade** dos seis, porque produz falso negativo: hoje ele apaga uma categoria inteira de erro (`UnsatisfiedConstraint`) sem deixar rastro.
7. **(rev. 4) A escolha silenciosa do `android.jar`** — `ConfigResolver.resolveAndroidJarFromEnv` (`$DEXLIB2/cli/.../ConfigResolver.java:111-127`) escolhe o **máximo lexicográfico** dos diretórios de `$ANDROID_HOME/platforms`, e o driver Python nunca passa `--android-jar` (a lista de argumentos em `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py:394-417` não o inclui). O jar escolhido **não é registrado em log algum**. Gate mínimo: logar o jar resolvido e falhar quando o nome do diretório não for numericamente o maior. Ver §7.5 para o que isso significou na campanha.

Onde: na geração, sobre o **descritor** — é o artefato que o weaver consome e onde a expressão chega verbatim. Custo baixo; evita que qualquer spec de F2/F5 seja tecida errada em silêncio. Os itens 5 e 6 são a exceção: vivem no weaver, porque é lá que a informação de colisão/truncagem existe.

> **Rev. 4 — nota de prioridade.** Dos sete, o item 6 é o único que hoje **apaga** violações reais, e o item 5 é o único que hoje **fabrica** violações falsas. Os dois estão medidos (§3.11, §4.8). Os itens 1–4 são riscos de autoria futura, não defeitos ativos no corpus: nenhuma spec do conjunto usa `execution`, `within` positivo ou `!adviceexecution()` (§2.3).

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
- **F0.4'** → §5 acima, agora com sete itens (dois novos na rev. 4).
- **F0.3** (recontagem dos `addError`) ✅ **resolvida na rev. 4 (§4.9)**: **51 sítios** em 21 das 23 specs, distribuídos em 6 `ErrorType`. O achado que a recontagem produziu não era o número, e sim o confronto com os dados: `UnsatisfiedConstraint` tem **8 sítios e 0 ocorrências**, e a causa está na §4.8.

### §3 — a classificação de ~35.368 eventos

Deixa de ser provisória **para 8.422 eventos** (95,2% da população de valor vazio): são artefato de instrumentação, com mecanismo identificado. Os 421 restantes seguem sem explicação. O restante dos 35.368 não foi tocado por esta investigação.

### §9.2 — reordenar

A correção de allow-list de `TrustManagerFactorySpec` e `SSLContextSpec` **não pode ser a primeira coisa a fazer**: ✅ está verificado que a allow-list é consultada contra uma variável que nunca é escrita. Ordem correta: (1) consertar a colisão no weaver — ou, mais barato, **renomear o binding `returning` de `g3` para `mf`** em `TrustManagerFactorySpec.mop:44`, que faz o javamop fundir os advices como já faz no `KeyManagerFactorySpec`; (2) só então mexer na allow-list.

> Esse segundo caminho é notável: um defeito de infraestrutura (L3.1) tem uma correção de **uma palavra** no `.mop`. Não substitui o conserto do weaver — qualquer spec nova pode recriar a colisão —, mas desbloqueia F2 sem depender da camada 3.

### §9.2 (camada 2) e §9.4 — priorizar pela assimetria

A reconexão do grafo deve ser guiada pelo número da §4.4: o lado `ENSURES` está 83% pronto, o lado `REQUIRES` está em 22%. **O trabalho é quase todo de escrever leituras, não escritas.** Em particular `SSLContextSpec`, cujos três `REQUIRES` estão sem leitura embora as constantes existam — correção de spec, não de desenho.

Para a §9.4, a `KeyGenParameterSpec.Builder` (item 3) ganha peso: é o produtor que falta para `GENERATED_KEY` no keystore de plataforma, e `GENERATED_KEY` é uma das **três** arestas que de fato funcionam.

### §3 e §9.2 — um segundo eixo de correção, de direção oposta (rev. 4)

O plano trata a camada 3 como fonte de **falso positivo**. A §4.8 acrescenta um eixo que ele não tem: a truncagem inline produz **falso negativo**, e apaga uma categoria de erro inteira. Consequências para o ordenamento:

1. Corrigir `monitorCalls.get(0)` no caminho inline é a mudança de **maior retorno por linha** de todo o levantamento: sete advices, nove eventos, quatro specs e uma categoria de `ErrorType` voltam a existir.
2. Ela precisa vir **antes** de qualquer releitura de "specs que não detectam nada": hoje `SecretKeySpecSpec` está tecido em 193 dos 219 APKs e é completamente mudo por esse motivo, não por falta de uso.
3. Ela muda o significado de um número do artigo: "13 de 23 specs nunca disparam" hoje mistura decisão de projeto com defeito de weaving. Depois da §4.9, a leitura correta é **3 incapazes por desenho, 3 inalcançáveis por construção, 4 silenciadas por defeito do weaver, 3 não exercitadas**.

### §9.4 — a `KeyGenParameterSpec.Builder` continua valendo, com uma ressalva (rev. 4)

O item 3 da §9.4 ganha peso pela §4.4, mas a §4.9 acrescenta um alerta: `KeyGeneratorSpec` já está tecido (`init` em 66/219 APKs, wrappers com call site em 34/109) e mesmo assim é mudo. Antes de acrescentar produtor novo para `GENERATED_KEY`, vale confirmar que o caminho de erro existente do `gk1` é alcançável — caso contrário o produtor novo alimentaria uma aresta que ninguém lê, que é precisamente o defeito estrutural da §4.4.

### §12 — uma ameaça nova

A tradução tem **duas** constantes escritas na posição errada (`KeyPairSpec.mop:38`, `TrustManagerFactorySpec.mop:65`) que passaram despercebidas porque o `ExecutionContext` aceita qualquer par `(Property, Object)` sem verificação. **Não há vínculo, nem em compilação nem em runtime, entre a constante escrita e a lida — uma constante errada falha aberta e invisível.** Isso é evidência concreta para a ameaça W3 da tese (tradução manual sem prova de equivalência), hoje em ledger mas ausente de `tex/4_EstudoDeCaso.tex:759-790`.

---

## 7. O que permanece não verificado

Explicitamente, para não ser promovido por descuido:

1. ~~Nenhum APK foi tecido.~~ ✅ **Resolvido em §3.7** — não foi preciso tecer: os APKs instrumentados da própria campanha estavam disponíveis, e a colisão foi observada no DEX de produção em 4 APKs. Passou de derivação a observação.
2. ~~A difusão de g3.~~ ✅ **Resolvido em §3.7, e fechado na rev. 3 também no nível do código**: a cadeia foi rastreada — todo monitor criado é inserido também no set da fatia vazia (`AbstractMonitorSet.add`, `$WS/rvsec/rv-monitor/.../rt/tablebase/AbstractMonitorSet.java:42-45`, append em array simples) e `TrustManagerFactorySpecMonitor_Set.event_g3` (`$MONITOR:3199-3221`) itera **todos** os elementos não terminados. Não é mais inferência.
3. ~~Os 421 eventos.~~ ✅ **Resolvido na rev. 3 (§3.6)** — L3.8 confirmada por bytecode nas três specs: sobrecarga `(String, Provider)` não instrumentada (`Signature` via spongycastle, `Mac` via tink), construtor de subclasse e `clone()` (`MessageDigest`). Toda a população de valor vazio tem mecanismo.
4. ~~Se algum wrapper morto custa uma violação real.~~ ✅ **Resolvido na rev. 4 (§3.11)** — não foi preciso re-executar: o custo é derivável, porque *o próprio valor vazio prova que o algoritmo era válido* (o `g3` é o wrapper vivo e teria escrito qualquer valor inválido). Conta: **≈17.175 dos 18.029 eventos do `TrustManagerFactorySpec` (95,3%)** desapareceriam com a correção; os 427 `X509` de sítio literal permaneceriam, com atribuição correta. Saldo de verdadeiros positivos: continua **zero**. *Ressalva declarada: é previsão derivada de tabelas e guardas, não medição; falsificável com duas re-execuções (§3.11).*
5. ~~Qual `android.jar` as campanhas passadas usaram.~~ ✅ **Resolvido na rev. 4.** Re-derivado: `ConfigResolver.resolveAndroidJarFromEnv` (`$DEXLIB2/cli/src/main/java/br/unb/cic/rv/cli/ConfigResolver.java:111-127`) escolhe por `max()` sobre a **comparação de String** do nome do diretório, e o driver Python nunca passa `--android-jar`. O desfecho depende do ambiente e **a campanha escapou**:
   - **No container** (`docker/android/Dockerfile:24`, `API_LEVEL=30`): as plataformas instaladas são `android-10`…`android-36`; o máximo lexicográfico é **`android-36`** — moderno e adequado. A campanha **não** foi afetada, e isto **elimina** a hipótese de que o `android.jar` explicasse specs silenciosos.
   - **No host**: `$ANDROID_HOME/platforms` contém `android-4` e `android-37.0`; o máximo lexicográfico é **`android-4`** (Android 1.6) — verificado (`max()` em Python sobre a listagem real devolve `android-4`). Qualquer instrumentação local nesta máquina indexa contra a API 4, em silêncio.
   - O defeito é real, latente e **fail-silent** (nenhum log do jar escolhido). Vira o item 7 do gate (§5). A questão **irmã** — qual *jar do weaver* rodou a campanha — segue resolvida pela rev. 3: `instr-cli.jar` do gh73 (`d73ebc41`, 2026-06-30), 77 commits após `3af5b3aa`; prova binária: 130/219 APKs com DEX `037/038/039`.
6. ~~Os 10 specs silenciosos.~~ ✅ **Resolvido na rev. 4 para 12 dos 13 (§4.9)**, por quatro mecanismos: `fail` inalcançável em ERE de evento único (3), emissores de erro descartados pela truncagem inline (4), incapacidade estrutural declarada (3) e API não exercitada (3). **Resta um**: o `PBEKeySpecSpec`, cujos eventos `f1`/`f2` transitam para `fail` e estão tecidos em 20/219 e 1/219 APKs — o silêncio só pode ser não-execução em runtime, e isso não se decide estaticamente.
7. ~~`thread(...)`.~~ ✅ **Resolvido na rev. 4 — e a expectativa da rev. 3 estava invertida.** `thread(...)` **não pode** cair no `throw` do matcher, porque nunca chega lá: `EventDefinition` (`$JAVAMOP/parser/ast/mopspec/EventDefinition.java:113-117`) extrai a variável com `ThreadVarVisitor` e **remove** o `thread(...)` do pointcut com `RemoveThreadVisitor`, exatamente como faz com `condition(...)`. O `resultPointCut` — que é o que o `DescriptorWriter` serializa — já vem sem ele. O mesmo vale para `threadName(...)` (`:127`, `RemoveThreadNameVisitor`), um PCD que a matriz da §2.1 sequer mencionava. O risco residual é **outro e menor**: a variável de thread é excluída da lista `parameters` do advice (`AdviceAndPointCut.java:83`) mas continua nos argumentos da chamada de monitor (`DescriptorWriter.java:137-139`, comentário “*including threadVar*”), de modo que uma spec que usasse `thread(...)` produziria um argumento sem binding resolvível — caindo no drop **com contador** `plansSkippedUnresolvedBinding`, não em abort. ✅ Uso no corpus: **zero** ocorrências de `thread(` nos quatro conjuntos (`jca`, `generic`, `generic_new`, `aspect`).
8. ~~Generalização do censo observado.~~ ✅ **Resolvido na rev. 3 (§3.2)** e **reproduzido de forma independente na rev. 4** (script novo, `census4.py`): mesmos 96 wrappers, mesmas 10 assinaturas disputadas, mortos 15–22 (mediana 19), **zero falsificações**, vencedor sempre o último wrapper declarado.

**Aberto após a rev. 4** — o que fica, explicitamente:

9. **O `PBEKeySpecSpec`** (item 6 acima) — único silêncio sem explicação estática.
10. **Quanto a truncagem inline (§4.8) apagou.** Sabemos que apagou *toda* a categoria `UnsatisfiedConstraint` (8 sítios, 0 eventos) e os emissores de erro de 4 specs. Não sabemos quantas violações **reais** isso representa: ao contrário da colisão, aqui não há relato residual de onde inferir, porque o evento nunca foi tecido. Decide-se com uma re-execução após corrigir o `get(0)` — e essa é a medição de maior valor que resta ao plano.
11. **Se a má-atribuição de sítio do `UnsafeProtocol` altera conclusões do artigo.** A §3.10 prova que a atribuição é uma corrida para os 8.802 eventos do `SSLContextSpec` (27,1% do dataset). Não medimos quantos dos 125 sítios reportados estão errados — exigiria, por app, ordenar os `getInstance` no tempo, e o `errors.csv` só tem granularidade de segundo.
12. **A validade do `InvalidSequenceOfMethodCalls` como métrica.** ✅ Re-derivado na rev. 4: são **70.760 de 97.018 (72,9%)**, e **as 454 tuplas de misuse, todas, têm ao menos uma linha desse tipo**. Combinado com §3.11 (a maior parte das do TMF é co-emissão espúria) e §4.9 (23 dos 51 `addError` são desse tipo), a categoria parece medir mais o acoplamento do gerador do que uso incorreto de API. **Não investigado fora do TMF/SSLContext.**

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

**Higiene verificada:** nada foi escrito em `RV_ANDROID_NOVO_DATASET/` (nenhum arquivo ≥ 2026-08-05; os 30 `.pkgdet` são de 26/06), nem em `$REPOS/` (sem `.git` próprios; o churn em `docs/` é do repo pai, de julho), nem nos `.mop`/weaver (git limpo). O único arquivo tocado sob `$WS/ase-journal/` (`diagramas/rvandroid.drawio`, 06/08 10:18) foi editado no **draw.io desktop** (host `Electron` no cabeçalho) — edição humana na GUI, não atribuível à sessão do relatório.

**O que a rev. 3 não verificou:** (i) o binário exato do jar da campanha não sobreviveu (datação por lineage + assinatura DEX, não por desmontagem; sem hash registrado); (ii) quantas violações deixariam de existir com a colisão corrigida (§7.4 — exige re-execução); (iii) os 10 specs silenciosos sem explicação (§7.6); (iv) o passo interno do RV-Monitor em que o monitor por-`mf` criado por `init` herda o estado do monitor da fatia vazia — a difusão está provada no set e nos dados, mas essa derivação específica segue inferida da semântica do RV-Monitor; (v) `thread(...)` (§7.7); (vi) a re-implementação de `expandCallTarget` do censo "7/9" da §3.2 não foi refeita (tornou-se irrelevante frente ao censo observado em 219 APKs).

---

## 9. Re-derivação independente (revisão 4) — o que foi refeito e o que mudou

Sessão nova, 2026-08-06. **Método:** nada do scratchpad das rev. 2–3 foi reutilizado; scripts novos (`census4.py`, `errors4.py`, `reachcensus.py`), desmontagem própria com `lib/dex2jar/d2j-baksmali.sh` por DEX (as rev. anteriores desmontavam o APK inteiro, o que só alcança `classes.dex` — daí a necessidade de extrair `classes*.dex` um a um). Nenhum subagente: toda leitura de fonte, bytecode e CSV foi feita direto.

### 9.1 Reprodução do núcleo

| alegação | rev. 3 | rev. 4 (independente) | veredito |
|---|---|---|---|
| chave do wrapper ignora o nome; `put` nu; guard não aplicado | `DexWeaver.java:145/159/208` | mesmas linhas, lidas de novo (`registerWrapper`, `expandWrapperReplacementsForApk`) | ✅ **reproduzido** |
| `shouldWrap` = só `after`; nome desambiguado por `nameCounts` | `WrapperEmitter.java:139/484-488` | `:138-140` (`shouldWrap`), `:483-490` (`buildEntry`) | ✅ **reproduzido** |
| `matchNamedRef` falha fechado; `execution`/`within` casam-true | `PointcutMatcher.java:161/509-515/134-138` | lidos verbatim; `matchExecution` de fato só testa `instructionIndex != 0` | ✅ **reproduzido** |
| 5 wrappers de `TrustManagerFactory.getInstance`, com call sites 0/0/1/1/7 | etesync | **idêntico**, contado por script próprio sobre os 3 DEX | ✅ **reproduzido** |
| nenhum `invoke` residual à API real fora dos corpos dos wrappers | corpus | confirmado: os 5 `invoke-static` remanescentes estão todos dentro de `mop/MonitorWrappers.smali` | ✅ **reproduzido** |
| censo: 96 wrappers, 10 assinaturas disputadas, mortos 15–22 (mediana 19), 0 falsificações | 219/219 | **idêntico nos 219/219**, por `census4.py`; vencedor sempre o último declarado; e o wrapper do `g1` tem **0 call sites em 219 apps** contra 152 do `g3` (§3.2) | ✅ **reproduzido e reforçado** |
| `SSLParametersImpl` passa `getDefaultAlgorithm()`, dados dizem `X509` | etesync | confirmado; **e também no openhab** (`Platform.smali:462/465`) | ✅ **reproduzido** |
| 208 `X509` no openhab vêm do literal do `MemorizingTrustManager` | rev. 3 corrigiu a rev. 2 | confirmado no bytecode (`MemorizingTrustManager.smali:1099-1100`: `const-string "X509"`) | ✅ **correção da rev. 3 confirmada** |
| 97.018 / 454 tuplas / 225 `unique_msg` / 8.843 vazios / 5 specs / 71 misuses / 64 apps / 13 specs mudas | `errors.csv` | **todos idênticos** | ✅ **reproduzido** |
| 70.760 `InvalidSequenceOfMethodCalls` (72,9%); 454/454 tuplas co-emitem | `errors.csv` | idêntico | ✅ **reproduzido** |
| os 9 sítios que geram 100% dos 8.422 | rev. 3 | idênticos, com as mesmas contagens (7.174 / 584 / 324 / 219 / 27 / 24 / 19 / 27 / 24) | ✅ **reproduzido** |

### 9.2 O que a rev. 4 acrescenta

| # | achado | tipo | evidência |
|---|---|---|---|
| R1 | causa-raiz da colisão na fonte do javamop (`retVal.equals` compara nome) | **novo** | `$JAVAMOP/output/combinedaspect/event/EventManager.java:91`; `$JAVAMOP/parser/ast/mopspec/MOPParameter.java:22-23` |
| R2 | o `k` do `g3` é o 4º resíduo da cópia do `KeyManagerFactorySpec` | **novo** | comparação dos dois `.mop` + os 3 defeitos já conhecidos do `gtm1` |
| R3 | a correção tem **duas** partes (binding + `fsm`), não uma | **corrige a rev. 3** | tabelas `transition_g3 = {3,3,3,3}` (`$MONITOR:10006`) |
| R4 | o estado-alvo da correção já existe no DEX de produção (KMF fundido) | **novo** | wrapper `javax_net_ssl_KeyManagerFactory_getInstance` chama `g1Event` **e** `g3Event` |
| R5 | §7.4 quantificada: ≈17.175/18.029 (95,3%) do TMF é artefato | **fecha item aberto** | §3.11, derivado das guardas + tabelas |
| R6 | herança por clonagem da fatia vazia (`sourceLeaf.clone()`) | **fecha item (iv)** | `$MONITOR:17931-17952`; e é o canal que explica o openhab, não a difusão lateral |
| R7 | truncagem inline: `monitorCalls.get(0)` descarta 9 eventos, todos de erro | **novo — 3º defeito** | `EmitContext.java:50-52` vs `WrapperEmitter.java:637`; 0 referências nos 219 APKs |
| R8 | `UnsatisfiedConstraint`: 8 sítios, 0 ocorrências — explicado por R7 | **novo** | recontagem F0.3 + `errors.csv` |
| R9 | §7.6 fechada para 12 de 13 specs mudas, por 4 mecanismos | **fecha item aberto** | §4.9 |
| R10 | ERE de evento único ⇒ `fail` inalcançável (padrão, 3 specs) | **generaliza a rev. 3** | `transition = {1,2,2}` em GCM, DHGen, HMAC |
| R11 | `HMACParameterSpec` é `javax.xml.crypto.*`, ausente do `android.jar` | **novo** | 0 entradas `javax/xml/crypto` no `android-36/android.jar` |
| R12 | §7.5 fechada: Docker → `android-36` (campanha ilesa); host → `android-4` | **fecha item aberto** | `docker/android/Dockerfile:24`; `max()` sobre a listagem real |
| R13 | §7.7 fechada e invertida: `thread(...)`/`threadName(...)` são removidos pelo javamop | **corrige a rev. 3** | `$JAVAMOP/parser/ast/mopspec/EventDefinition.java:113-127` |
| R14 | `SSLContextSpec` = 26.312 eventos (27,1%) com a mesma má-atribuição | **novo** | §3.10; app `nextcloudcookbook` com dois protocolos e dois literais no bytecode |
| R15 | F0.3 fechada: 51 sítios `addError`, distribuição por `ErrorType` | **fecha item do plano** | §4.9 |

### 9.3 Correções aplicadas a texto da rev. 3

Nenhuma altera conclusão estrutural. **(a)** §3.3 dizia “o defeito produz falso positivo, nunca falso negativo” — verdade sobre a colisão, mas o sistema produz os dois; a §4.8 registra o outro eixo. **(b)** §7.7 previa que `thread(...)` cairia no `throw`; não cai — não chega ao matcher (R13). **(c)** §7.5 tratava a escolha do `android.jar` como ameaça potencial à campanha; a campanha estava ilesa, e a ameaça é ao host (R12). **(d)** A §3.12 substitui a explicação do openhab por difusão lateral pela explicação por clonagem — a rev. 3 estava certa no efeito e imprecisa no canal (R6). **(e)** A matriz da §2.1 não tinha linha para `threadName(...)`.

### 9.4 Higiene

Nenhuma escrita fora do scratchpad da sessão e deste arquivo: `$APKS` e `$RESULTS` foram abertos somente para leitura (extração de `classes*.dex` para o scratchpad); nenhum `.mop`, nenhuma fonte do weaver ou do javamop foi tocado. As desmontagens intermediárias ficaram em `/tmp/census4work` e no scratchpad.

---

## Fontes

As abreviaturas de raiz (`$WS`, `$JAVAMOP`, `$DEXLIB2`, `$JCA`, `$MONITOR`, `$CORE`, `$RESULTS`, `$APKS`, `$REPOS`, `$CRYSL`) estão expandidas na tabela da seção **Convenção de caminhos**, no topo. Caminhos sem `$` são relativos à raiz do `rv-android`.

- ✅✅ [JavaMOP4 Syntax](https://web.archive.org/web/20190327032914/http://fsl.cs.illinois.edu/index.php/JavaMOP4_Syntax) — gramática BNF, PCDs admitidos, variáveis especiais
- ✅ `$JCA/*.mop` (23 specs) e `MultiSpec_1MonitorAspect.aj` (resíduo de build, 2026-07-08)
- ✅ `$MONITOR` — monitor gerado (git-ignored, 2026-07-08); tabelas de transição, guardas, despacho de eventos e o `sourceLeaf.clone()` da §3.12
- ✅ `$CORE/{Property,ExecutionContext}.java`
- ✅ `$DEXLIB2/` — `pointcut-engine` (`PointcutMatcher`, `PointcutExpressionParser`), `advice-emitter` (`WrapperEmitter`, `EmitContext`, `MonitorInvokeBuilder`, `StaticInitializationEmitter`, `AfterThrowingEmitter`), `dex-mutator` (`DexWeaver`), `descriptor-reader`, `grammar-tests`, `cli` (`ConfigResolver`)
- ✅ `$DEXLIB2/descriptor-reader/src/test/resources/MultiSpec_1MonitorAspect.json` (115 advices)
- ✅ `$JAVAMOP/output/descriptor/DescriptorWriter.java`, `$JAVAMOP/output/combinedaspect/{event/EventManager,event/advice/AdviceAndPointCut,MOPStatistics}.java`, `$JAVAMOP/parser/ast/mopspec/{EventDefinition,MOPParameter,MOPParameters}.java` — **fontes da rev. 4** para a regra de fusão (§3.1) e para o tratamento de `thread(...)` (§7.7)
- ✅ `$CRYSL/` (49 `.crysl`, 1.5.2-jca)
- ✅ `$RESULTS/errors.csv` (97.018 linhas), `coverage.csv`, `cc.csv`, `cc_rv_mapping.csv` — **somente leitura**
- ✅ **`$APKS`** — os 219 APKs instrumentados que produziram os dados do artigo (219 `.apk` + 219 `.json` + 30 `.pkgdet`). Desmontados com `lib/dex2jar/d2j-baksmali.sh`, **por DEX** (`classes*.dex` extraídos um a um — desmontar o `.apk` inteiro só alcança `classes.dex` e perde o `mop/`, que na maioria dos APKs vive no último DEX). Base da §3.7, do censo da rev. 3 e dos três censos da rev. 4. **Somente leitura**
- ✅ **`$REPOS/<pkg>_<ver>.apk/`** — código-fonte dos apps do corpus (348 repositórios). Triangulação da §3.7. **Somente leitura**
- ✅ `results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` — descritor de produção (115 advices, 86.597 B), base da medição da §4.8
- ✅ `docker/android/Dockerfile` e `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` — resolução do `android.jar` (§7.5)
- ✅ `$WS/rvsec-paper/rvsec.tex:40-43` (comentado)

**Scripts da rev. 4** (no scratchpad da sessão, escritos do zero):

| script | o que faz | saída |
|---|---|---|
| `census4.py` | por APK: extrai `classes*.dex`, desmonta cada um, lê `mop/MonitorWrappers`, agrupa wrappers pela assinatura **original** (a chave que `DexWeaver.registerWrapper` usa) e conta os call sites de cada um no APK inteiro | `census4.jsonl` |
| `reachcensus.py` | censo de alcançabilidade sem desmontar: um nome de evento que aparece na tabela de strings de um DEX **que não define o monitor** só pode ser referência, isto é, sítio tecido. Validado contra a desmontagem do etesync | `reachcensus.jsonl` |
| `errors4.py` | re-derivação completa de `errors.csv`: tuplas, `unique_msg`, tipos de erro, população de valor vazio, sítios geradores, valores por sítio, co-emissão | stdout |

Scripts das rev. 2–3, mantidos para rastreabilidade: `G0_census.py`/`.json`, `G0_census_aj.py`/`.json`, `A1_extract.py` + `A1_property_graph.csv`, `A2_parse_crysl.py` + `A2_crysl_crosscheck.csv` + `A2_predicate_graph.csv`, `A3_codegen_survival.md` + `raw_guards.txt`, `A4_errors_analysis.py` + `A4_report.md` + `Q1..Q6_*.csv`, `B2_extract.py` + `B2_pcd_usage.md` + `B2_jca_call_hook_surface.md`, `census.py` + `B3_wrapper_collision.md`. **Nenhum deles foi reutilizado pela rev. 4.**

A matriz de PCD da §2.1 é o único artefato sem arquivo bruto separado — foi derivada em modo somente-leitura e está integralmente reproduzida aqui.
