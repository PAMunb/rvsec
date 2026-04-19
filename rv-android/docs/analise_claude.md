# Análise Crítica — Pré-plano GATOR/Soot 4.7.x

**Data**: 2026-04-19
**Documento analisado**: `docs/20260419_gator.md`
**Spec relacionada**: `openspec/specs/analysis/spec.md`
**Revisor**: Claude (Opus 4.7)

---

## 1. Resumo Executivo

O pré-plano identifica corretamente o problema (SA = 27.6%, causa raiz no `TypeResolver` do Soot 3.3.0 com bytecode Kotlin moderno) e propõe uma direção tecnicamente sólida (opções defensivas + tratamento gracioso + upgrade de Soot). A validação empírica com CogniCrypt 5.0.1 (Soot 4.6.0) é forte evidência de que o upgrade resolve o crash na prática.

Porém, o documento contém **três problemas materiais** que comprometem a execução:

1. **FIX 2 mal-localizado**: o stack trace aponta crash em `CHATransformer.internalTransform → OnFlyCallGraphBuilder` (fase `cg.cha`, **antes** do `wjtp.gui`), enquanto FIX 2 modifica `Flowgraph.java:343` (que só executa **depois** de o call graph estar pronto). Se o crash for de fato no CHA, FIX 2 **não previne nada**. O pré-plano também cita "linha 191" — a posição real é 343.
2. **FIX 1 com afirmações imprecisas**: `set_ignore_resolution_errors` e `throw_analysis_dalvik` **não capturam `InternalTypingException`**; só `jb.sils enabled:false` tem evidência de issue Soot ([#1641](https://github.com/soot-oss/soot/issues/1641)) ligando-o ao trigger do bug. As exclusões `kotlin.*`/`kotlinx.*` são *avoidance*, não *fix*.
3. **FIX 3 subestimado**: o plano estima 4-8h; análise da superfície de API GATOR mostra **3-5 dias** (Options API setters em `Configs.java`, `soot.dexpler.Util` em `EpiccBasedIntentAnalysis.java`, mudança `getMethods() : Chain → List`). A versão alvo correta é **4.7.1** (2025-02-23), não 4.7.0.

**Recomendação**: aplicar FIX 1 (somente `jb.sils enabled:false` + excludes + `no_bodies_for_excluded`) **+** FIX 2 reposicionado para envolver `retrieveActiveBody()` em `Flowgraph.java:274` (e/ou em `RvsecAnalysisClient` se houver lazy CG) **+** FIX 3 com escopo realista. Tratar FIX 3 como **load-bearing** (única intervenção empiricamente validada) e FIX 1/2 como mitigações complementares.

---

## 2. Análise de Consistência

### 2.1 Consistência interna

| Tópico | Status | Observação |
|--------|--------|------------|
| Diagnóstico vs solução | ⚠️ **Inconsistente** | §1.1 mostra stack trace terminando em `CHATransformer.internalTransform`. §1.2 redesenha o fluxo passando pelo `Flowgraph.createOpNode()`. As duas narrativas são incompatíveis: CHA roda na fase `cg.cha` (pré-Flowgraph); a fase `wjtp.gui` (que invoca Flowgraph) só é alcançada se o CG terminar. |
| Numeração de linhas | ❌ **Incorreta** | §1.2 e §4.2 dizem "Flowgraph.java ~linha 191"; o `throw new RuntimeException(e)` real está em **linha 343** (verificado). Linha 191 é `modelOnCreateOrPrepareOptionsMenuAndItsFlowToItemSelected()`. |
| Versão alvo Soot | ⚠️ **Defasada** | §4.3 fala "Soot 4.7.0 mais recente estável". A última estável é **4.7.1** (2025-02-23, fix de build sobre 4.7.0). |
| Tabela §2.3 (versões fragmentadas) | ✅ **Correta** | Confirmado: parent usa `org.soot-oss:4.4.1`; FlowDroid 2.10.0 puxa Soot ~4.3.0; gator usa `ca.mcgill.sable:3.3.0`; client tem exclusion explícita. |
| Tabela §2.1 (comparação CryptoAnalysis vs FlowDroid vs GATOR) | ⚠️ **Parcialmente verificável** | FlowDroid `SootConfigForAndroid.java` (verificado em `develop`) só configura `set_no_bodies_for_excluded(true)` + lista de excludes (`java.*`, `javax.*`, `sun.*`, `android.*`, `androidx.*`, `org.apache.*`, `org.eclipse.*`, `soot.*`) — **não inclui `kotlin.*`**. Outras opções vêm de `AbstractInfoflow`/`SetupApplication`. As alegações sobre CryptoAnalysis precisam ser verificadas no JAR local (`HeadlessAndroidScanner-5.0.1-jar-with-dependencies.jar`). |
| Issues Soot | ✅ **Consistente** | #1071 confirmado **aberto** em 2026-04-19 (não houve PR fundido). #1641 documenta `jb.sils` como gatilho. |

### 2.2 Coerência com a spec `analysis/spec.md`

A spec atual já tem mecanismos para JSON parcial:

- **INV-ANA-06**: parser deve retornar coleções vazias por seção em caso de falha — não propaga exceção.
- **Cenário "Timeout with partial JSON"** + **"components section missing"**: parser tenta recuperar até o último `]` completo.
- Ordem de escrita das seções (reachability → windows → transitions → components) já é "priority order para timeout graceful degradation".

**Implicação**: o problema **não é** o lado Python (já robusto). O problema é o lado Java (GATOR) que **mata o processo antes de produzir QUALQUER JSON**. Os fixes propostos atacam essa lacuna de forma correta em direção, com as ressalvas de §3 abaixo.

A spec **não menciona** falhas em `cg.cha`/`wjtp.gui` nem comportamento esperado quando o Soot crasha pré-emissão. Convém adicionar um cenário cobrindo:

> WHEN GATOR crasha em fase Soot interna (cg.cha, jb.*, wjtp.gui) antes de `RvsecAnalysisClient.run()` ser invocado
> THEN o exit code do wrapper Python deve ser não-zero, o `StaticAnalysisException` MUST ser registrada com a mensagem original do Soot, e nenhum arquivo `.json` deve existir (resultado já tratado como falha pela `StaticAnalyzer`).

### 2.3 Rastreabilidade problema → causa → fix → teste

| Etapa | Rastreável? |
|-------|-------------|
| Sintoma (97/352 SA) | ✅ §1, §1.4 |
| Causa raiz (`ClassHierarchy.typeNode()` retorna null para tipos não mapeados) | ✅ §1.1, confirmada via leitura do código upstream |
| Fix mapeado para causa | ⚠️ FIX 2 não cobre o caminho do stack trace (§3.2) |
| Critério de teste | ⚠️ §6 diz "≥7/10 produzem JSON" mas não nomeia os 10 APKs nem inclui regressão sobre os 97 que já funcionam |

---

## 3. Análise Técnica dos Fixes

### 3.1 FIX 1 — Opções Soot defensivas

A tabela abaixo combina o que o pré-plano afirma com a evidência verificável. Os dois últimos casos representam afirmações **incorretas ou exageradas** no plano original.

| Opção | Plano alega | Evidência | Veredicto |
|-------|-------------|-----------|-----------|
| `-p jb.sils enabled:false` | Evita typing errors no static inlining | Soot [#1641](https://github.com/soot-oss/soot/issues/1641) confirma que `SharedInitializationLocalSplitter` (jb.sils) é gatilho frequente de crashes de typing pós-`jb.tr` | **Provavelmente eficaz** para uma fração dos crashes |
| `-p jb.dae enabled:false` | Evita typing errors em DAE | Sem issue Soot direto. CryptoAnalysis pode ou não usar (não verificado no JAR). DAE roda *antes* de TypeAssigner em alguns paths — desabilitar pode preservar locais que mascaram bug | **Plausível**, evidência fraca |
| `-no-bodies-for-excluded` + `exclude kotlin.*`/`kotlinx.*` | Evita jimplificar stdlib Kotlin | FlowDroid `SootConfigForAndroid` confirma `set_no_bodies_for_excluded(true)` mas **NÃO** inclui `kotlin.*` na lista de excludes (apenas `java.*`, `javax.*`, `android.*`, `androidx.*`, `org.apache.*`, `org.eclipse.*`, `soot.*`, `sun.*`). | **Eficaz como avoidance** — não é "fix" do bug, mas elimina bodies que disparam o crash |
| `set_ignore_resolution_errors(true)` | Trata tipos não-resolvíveis graciosamente | Esta flag controla **resolução de classes ausentes**, não tipagem de inteiros. `InternalTypingException` é lançada **dentro** do `TypeResolver`, fora do escopo desta flag | ❌ **Afirmação incorreta**: não previne o crash documentado |
| `set_throw_analysis(throw_analysis_dalvik)` | Análise de exceções correta para DEX | Resolve casos `UnitThrowAnalysis` (ex.: Soot [#2083](https://github.com/soot-oss/soot/issues/2083)) — **não** o `Integer1Type` | ❌ **Não relacionado** ao crash em questão |

**Risco colateral**: excluir `kotlin.*`/`kotlinx.*` reduz o universo de método para reachability. Para JCA isso é tolerável (JCA é APIs `javax.crypto`/`java.security` chamadas pelo código do app). Para `generic`/`generic_new` (Iterator/Map/InputStream) o impacto pode ser **maior**, porque Kotlin reescreve coleções: muitas iterações sobre `List<T>` no Kotlin viram `kotlin.collections.CollectionsKt$iterator$...`. Recomenda-se **medir** antes de aceitar como custo-benefício.

**Sugestão concreta**: começar com **somente**:
```java
"-p", "jb.sils", "enabled:false",
"-no-bodies-for-excluded",
"-exclude", "kotlin.",
"-exclude", "kotlinx.",
```
Adicionar `jb.dae`, `ignore_resolution_errors`, `throw_analysis_dalvik` apenas se causarem efeito mensurável em testes A/B; caso contrário, ruído de configuração.

### 3.2 FIX 2 — `continue` em vez de `throw`

#### Estrutura do código (verificada)

`Flowgraph.java:267-381` itera classes/métodos/statements. No corpo do statement existem **dois** pontos de invocação relevantes ao crash:

```java
// linha 274 — RETRIEVE BODY (FORA de qualquer try-catch)
Body b = currentMethod.retrieveActiveBody();

// linha 312-320 — try com Soot ClassResolutionFailedException
try {
    if (... .getInvokeExpr().getMethod() == null) { ... }
} catch (SootMethodRefImpl.ClassResolutionFailedException e) { continue; }

// linha 338-344 — try com Exception genérica em createOpNode (FIX 2 alvo)
try {
    opNode = createOpNode(currentStmt);
} catch (Exception e) {
    Logger.verb(...); e.printStackTrace();
    throw new RuntimeException(e);   // ← FIX 2 quer trocar por `continue`
}
```

#### Onde o crash de fato ocorre

O stack trace exibido em §1.1 termina em:
```
soot.jimple.toolkits.callgraph.CHATransformer.internalTransform(CHATransformer.java:51)
```

Isso indica que o crash dispara durante a **construção do call graph** (fase `cg.cha`). No branch `withCHA` do `Main.java:201-218`, esta fase roda **antes** do `wjtp.gui`, ou seja, antes de `Flowgraph.build()` ser invocado. Portanto, **se o crash acontece na fase `cg.cha`, FIX 2 não é executado**, porque `Flowgraph.build()` nunca chega a ser chamado.

Existe um segundo caminho de crash possível: `Flowgraph.java:274` (`retrieveActiveBody()` chamado pelo próprio Flowgraph). Esse caminho está **fora** do try-catch que FIX 2 modifica. Se o crash acontece aqui, FIX 2 também é ineficaz.

O `throw new RuntimeException(e)` na linha 343 só é alcançado quando:
1. CHA não crashou (já passamos da fase `cg.cha`),
2. `retrieveActiveBody()` da linha 274 não crashou,
3. `createOpNode()` da linha 339 dispara exceção.

Esse cenário pode ocorrer em uma fração dos APKs, mas **não é o cenário dominante** representado pelo stack trace mostrado no plano. O log de "exit code 0/1" (§1.3) é compatível com ambos os caminhos — não desambigua.

#### Veredicto

FIX 2 **isolado é insuficiente** para o crash documentado. As três correções alinhadas ao stack trace seriam:

1. **Envolver `retrieveActiveBody()` da linha 274** em `try { Body b = currentMethod.retrieveActiveBody(); } catch (Exception e) { Logger.warn(...); continue; }`. Isso captura o caminho descrito pelo stack trace **se** ele atravessar Flowgraph (improvável dado o trace, mas possível em paths alternativos).
2. **Adicionar try-catch em `RvsecAnalysisClient.run()`** envolvendo cada seção (já alinhado com a spec INV-ANA-06 e o pattern de flush incremental — basta capturar exceção entre `writeReachability`/`writeWindows`/`writeTransitions`/`writeComponents` e prosseguir).
3. **Para o crash em `cg.cha`** (caminho dominante do stack trace): a única mitigação prática é **FIX 1 + FIX 3** (impedir que os bodies problemáticos cheguem ao TypeResolver, ou usar Soot 4.6+ onde o Dexpler é mais robusto). Não há gancho convencional para sobreviver a uma exceção dentro de `OnFlyCallGraphBuilder.processNewMethod` sem patch ao próprio Soot.

A troca proposta no plano (`throw → continue` em `:343`) **não é nociva** e deve ser aplicada — apenas não resolve o caso descrito.

#### Efeito downstream do `continue`

O `Flowgraph` é a base de todas as análises seguintes (Fixpoint, GUIAnalysisOutput, WTGBuilder). Pular um statement perde:

- Edges de fluxo Jimple → Jimple naquele método.
- Possíveis registros de listeners (callbacks de UI dentro do método ignorado).
- Em método com 200 statements e 2 que crasham, perde 1% do flowgraph daquele método.

**Impacto qualitativo**:
- **Reachability**: pouco impacto (call graph é externo ao Flowgraph; usa CG do Scene).
- **Widgets**: impacto moderado se o statement pulado for um `findViewById` ou `setOnClickListener` (Flowgraph extrai listeners interprocedurally).
- **WTG**: pode perder transições de janela se o statement perdido for o que dispara a navegação (`startActivity`).

Para JCA esse trade-off é aceitável; para experimentos que dependem fortemente do WTG (modos `multimode`/`llm_only` com `NavigationGuidance`) há perda mensurável a medir.

### 3.3 FIX 3 — Upgrade Soot 3.3.0 → 4.7.x

#### Versão alvo

A última estável é **4.7.1 (2025-02-23)**. 4.7.0 (2025-02-13) tem um bug menor de build resolvido em 4.7.1. Adotar **4.7.1** diretamente. (4.8.0 ainda é `SNAPSHOT` no `master`.)

#### O bug `Integer1Type` *não* foi corrigido em 4.7.x

Inspecionando o `master` do Soot, `ClassHierarchy.typeNode()` mantém o `throw new InternalTypingException(type)` na fall-through e a mesma cadeia de 5 tipos. Issue [#1071](https://github.com/soot-oss/soot/issues/1071) segue **aberta** sem PR. Issue #1058 também aberta.

A "vantagem" do 4.x é que o **Dexpler** ([6 anos de melhorias](https://github.com/soot-oss/soot/commits/master/src/main/java/soot/dexpler)) emite menos bodies que disparam o caminho problemático. A validação empírica com CogniCrypt 5.0.1 (Soot 4.6.0) registrada em §4.7 do plano confirma esse efeito **na prática**, não que o bug tenha sido corrigido na origem.

**Implicação para o plano**: descrever FIX 3 como "upgrade reduz drasticamente a frequência do crash" (correto) e não como "Soot 4.x não crasha" (impreciso). FIX 2 é load-bearing exatamente porque o bug persiste.

#### Riscos de API verificados em código GATOR

Análise direta dos imports e padrões usados em `rvsec-gator/sootandroid/`:

| Quebra | Local | Severidade | Justificativa |
|--------|-------|-----------|---------------|
| `Options.v().set_force_android_jar(...)` e `set_src_prec(...)` | `Configs.java:235-237` | **CRÍTICO** | API de setters do `Options` foi reestruturada em 4.x; vários setters foram depreciados/removidos. Migrar para `Options.v().parseOptions(args)` ou ajustar para os novos nomes. |
| `soot.dexpler.Util.splitParameters()` / `Util.getType()` | `EpiccBasedIntentAnalysis.java:125-128` | **CRÍTICO** | `soot.dexpler.Util` sofreu refatoração ampla em 4.x. Verificar se as utilities ainda existem na assinatura usada. |
| `SootClass.getMethods() → Chain → List` | `Flowgraph.java:267`, `Hierarchy.java:536` | **MÉDIO** | A retorno mudou de `Chain` para `List` em 4.4+. O código já usa `Lists.newArrayList(c.getMethods()).iterator()` o que é defensivo, mas semântica de iteração precisa ser revalidada. |
| `Scene.v().addBasicClass(..., SootClass.SIGNATURES)` | `PrerunEntrypoint.java:40-50` | **BAIXO** | Constantes preservadas. |
| Phase options (`-p cg cha all-reachable:true`) | `Main.java:206-208` | **BAIXO** | String format de phase options estável entre 3.3 e 4.7. |
| `OnFlyCallGraphBuilder` (uso transitivo) | — | **BAIXO** | Não chamado diretamente pelo GATOR; só indiretamente via `Scene.v().getCallGraph()` em `RvsecAnalysisClient`. |

**APIs preservadas (~126 ocorrências)**: `Scene.v().getSootClass()`, `getApplicationClasses()`, `getClasses()`, `SootMethod.retrieveActiveBody()`, `SootMethod.isConcrete()`, `Body.getUnits()`, todas as classes Jimple (Stmt, Jimple, etc.), `SceneTransformer`, `Pack`, `PackManager`, `Transform`, `IntegerConstantValueTag`, `LineNumberTag`.

#### Estimativa realista de esforço

| Tarefa | Plano | Análise |
|--------|-------|---------|
| Atualizar 5 `pom.xml` | 30 min | ✅ 30 min |
| Migrar Options API setters em `Configs.java` | (não previsto) | **2-4 h** |
| Validar/migrar `soot.dexpler.Util` em EpiccBasedIntentAnalysis | (não previsto) | **2-4 h** |
| Compilação inicial + caça a outros breaks | (não previsto) | **3-6 h** |
| Smoke test em 5 APKs conhecidos (mix funciona/falha) | 30 min | ✅ 1-2 h |
| Regressão nos 97 APKs que hoje funcionam (evitar `cryptoapp.apk` baseline regredir) | (não previsto) | **2-4 h** |
| Eventual fix de comportamento divergente (ex.: contagens de reachable diferentes — spec já tolera ±10%) | (não previsto) | **0-8 h** |
| **Total realista** | **4-8 h** | **3-5 dias** |

O plano subestima por ~5×. Recomendo replanejar a janela.

### 3.4 Interação dos três fixes combinados

Boa notícia: os três fixes são **independentes** e podem ser aplicados em qualquer ordem.

- FIX 1 reduz a *carga* de bodies passados ao TypeResolver.
- FIX 2 reduz o *blast radius* de uma exceção sobrevivente.
- FIX 3 reduz a *frequência* de crashes via Dexpler mais maduro.

Não vejo interação destrutiva. Há um caso particular: aplicar FIX 1 em `cg.cha` (e não só em `jb.*`) não muda nada porque CHA não roda sub-fases jb diretamente — então a opção `jb.sils enabled:false` só tem efeito quando `retrieveActiveBody()` é chamado a posteriori (durante `wjtp.gui`/Flowgraph). Para o caminho do stack trace (CHA), a única defesa de FIX 1 é o **exclude + no_bodies_for_excluded** (que evitam que CHA tente jimplificar bodies de `kotlin.*`).

---

## 4. Impacto na Análise Estática

### 4.1 Por spec set

| Spec set | Métodos monitorados | Impacto FIX 1 (excludes Kotlin) | Impacto FIX 2 (continue) | Impacto FIX 3 (Soot 4.7.1) |
|----------|---------------------|-------------------------------|------------------------|----------------------------|
| **JCA** | `javax.crypto.*`, `java.security.*` | **Mínimo** — chamadas vêm do código do app, não de stdlib Kotlin | Mínimo se método não tiver chamada JCA | **Positivo** — mais APKs analisáveis |
| **generic** | `Iterator`, `InputStream`, `Map` | **Moderado** — Kotlin coleções viram `kotlin.collections.*`; perde reachability nesses paths | Mínimo | **Positivo** — mais APKs analisáveis |
| **generic_new** | (mesma família + adicionais FSM) | **Moderado-Alto** | Mínimo | **Positivo** |

**Recomendação**: medir reachability set para um APK Java puro (que tem ~zero impacto de excludes Kotlin) vs APK Kotlin/Compose representativo, **antes e depois** dos excludes — quantificar a perda.

### 4.2 Quanto à propriedade `reaches_mop`

Como `MopScorer` em `rv-agent` atribui +100 para `directly_reaches_mop=true` e +50 para `reaches_mop=true`, qualquer perda no cálculo de reachability afeta a priorização da exploração LLM-driven. O efeito agregado sobre coverage real é **modesto** se o método "perdido" não chama JCA (e a maioria dos métodos `kotlin.*` não chama). Convém ter um teste de regressão que compare top-10 ações priorizadas antes/depois para 3-5 APKs JCA-pesados.

### 4.3 Quanto ao `withCHA` ON por padrão

A spec menciona que GATOR suporta `-withCHA` "se reachability for insuficiente". O comando padrão da spec inclui `-withCHA`. Como CHA é exatamente onde o crash ocorre (stack trace), uma mitigação **pragmática e barata** seria:

> Tentar primeiro **com** `-withCHA`. Se exit code != 0 (ou crash detectado), retentar **sem** `-withCHA` — perdendo precisão de reachability mas obtendo *algo*.

Isso é compatível com a spec e oferece um fallback seguro. Pode ser implementado na `StaticAnalyzer` (lado Python) sem alterar o GATOR.

---

## 5. Estado da Arte (2026-04-19)

### 5.1 Soot

- **Mantido ativamente** sob `org.soot-oss:soot`. Última estável: **4.7.1** (2025-02-23). `master` em `4.8.0-SNAPSHOT`. Cadência ~2 releases/ano.
- Bug `Integer1Type` (issue [#1071](https://github.com/soot-oss/soot/issues/1071)) **não foi corrigido**. Mesma estrutura `ClassHierarchy.typeNode()` em 3.3.0 e 4.7.x.
- Há issue específica ([#1641](https://github.com/soot-oss/soot/issues/1641)) confirmando que `jb.sils` é fase gatilho de problemas de typing.

### 5.2 SootUp 2.0+

- Liberado 2025-02 (`sootup-core 2.0.0`); frontend Android (`sootup-apk-frontend 2.0.0`) Mar 2025.
- Documentação oficial admite: *"SootUp currently allows one to analyze Android applications with the help of dex2jar, but this is an interim solution as dex2jar is no longer actively maintained, and work is underway on a more robust solution based on Dexpler."* ([fonte](https://deepwiki.com/soot-oss/SootUp/4.3-apk-frontend))
- ServiceNow Security Lab (Nov 2024) avalia: API mais limpa, mas "muita da API ainda não documentada".
- **Veredicto**: **não viável** para o GATOR/rv-android no horizonte da tese (deadline 2026-04-13 já passou; estamos em modo finalização).

### 5.3 FlowDroid 2.15.x

- Última estável: **2.15.1** (Fev/2025). Desenvolvimento em `develop` rastreia Soot `master`.
- `pom.xml` `develop` declara `<soot.version>4.8.0-SNAPSHOT</soot.version>`.
- `SootConfigForAndroid` é mais enxuto do que sugere a tabela §2.1 do plano: configura **apenas** excludes (`java.*`, `javax.*`, `sun.*`, `android.*`, `androidx.*`, `org.apache.*`, `org.eclipse.*`, `soot.*`) + `set_no_bodies_for_excluded(true)`. Outras opções vêm de `AbstractInfoflow`/`SetupApplication`.
- **Não usa fork/patch privado de Soot** — usa upstream.

### 5.4 Alternativas a Soot

- **WALA** + Droidel (`cuplv/droidel`): sem manutenção desde ~2017. Inviável.
- **Doop**: só JVM bytecode, sem frontend APK.
- **OPAL**: sem suporte Android.
- **Androguard** (Python): leitura DEX direta, sem Jimple. Bom para reachability/CFG; **não substitui WTG** nem widgets analisados via interprocedural data flow. Já é o W5 do plano.
- **JADX-based**: decompilador, não framework de análise.

**Conclusão**: Soot continua sendo o único framework Java maduro para análise Jimple-completa de APK em 2026.

### 5.5 CryptoAnalysis 5.0.1

- `pom.xml` declara `<soot.version>4.6.0</soot.version>` — confirmado.
- Sem fork/patch de Soot.
- As opções específicas que `HeadlessAndroidScanner` aplica **não foram inspecionadas no JAR local** durante esta análise. Antes de citar como evidência canônica para FIX 1, **descompactar** `HeadlessAndroidScanner-5.0.1-jar-with-dependencies.jar` e inspecionar a classe `de.fraunhofer.iem.crysl.headlessandroidscanner` (ou similar).

---

## 6. Riscos e Mitigações

### Tabela de risco

| ID | Risco | Probabilidade | Impacto | Mitigação |
|----|-------|---------------|---------|-----------|
| R1 | **FIX 2 não captura o crash do stack trace (CHA path)** | **Alta** | **Alto** | Reposicionar FIX 2 para envolver `retrieveActiveBody()` em `Flowgraph.java:274` E adicionar fallback "retry sem `-withCHA`" no `StaticAnalyzer` Python |
| R2 | **FIX 3 demanda 3-5 dias, não 4-8 h** | **Alta** | Médio | Replanejar janela; usar timebox de 4h só para discovery (compilar e listar erros), depois decidir |
| R3 | **Soot 4.7.x ainda crasha em alguns APKs** (bug não corrigido upstream) | Média | Médio | FIX 2 reposicionado se torna load-bearing; aceitar SA parcial |
| R4 | **Excludes Kotlin perdem reachability em generic/generic_new** | Média | Médio para JCA ✓ ; Alto para generic | Medir antes/depois; se necessário, manter excludes só em modo `--spec-set jca` |
| R5 | **Conflito FlowDroid 2.10.0 + Soot 4.7.1** (FlowDroid 2.10 é de 2022, espera Soot ~4.3.0) | **Alta** | Alto | Atualizar FlowDroid para **2.14.1** (a mesma do CryptoAnalysis 5.0.1, validada com Soot 4.6.0). Ou 2.15.1 se também alinhada com 4.7.1 |
| R6 | **Memória**: Soot 4.x consome mais RAM que 3.x | Média | Médio | Setar `-Xmx16g` em `lib/gator/gator` script |
| R7 | **Race condition #1189** em multi-thread | Baixa | Baixo | Manter `-worker 1` (já é default no GATOR per `Configs.workerNum=1`) |
| R8 | **Regressão nos 97 APKs hoje funcionando** | Média | Alto | Antes de merge: rodar SA paralela completa antes/depois e comparar JSONs (counts de classes, métodos, reachable, transitions). Cenário de spec já tolera ±10% em `reachable`/`reachesMop` mas exige `directlyReachesMop` exato. |
| R9 | **`soot.dexpler.Util.splitParameters` removido em 4.7** | Média | Alto se removido | Verificar; se removido, reescrever `EpiccBasedIntentAnalysis.processIntentExtras()` (essa classe é um cliente analítico que não é o `RvsecAnalysisClient` — pode ser desativado se não usado pela análise unified) |
| R10 | **Pre-plan cita CryptoAnalysis options sem inspecionar JAR** | Baixa | Médio | Inspecionar JAR local antes de basear decisões nele |
| R11 | **Plano não define rollback** | Baixa | Alto se R3+R5 ocorrerem | Branch `gh51-gator-soot47` separada; merge só após validação completa; tag estável anterior preservada |

### Plano de rollback (faltante no original)

1. Trabalhar em branch `gh51-gator-soot47` (separada de `master` e `modules`).
2. Antes de iniciar: rodar SA completa paralela em 100 APKs e salvar baseline JSONs em `data/baselines/sa_pre_gator_upgrade/`.
3. Após cada fase (FIX 1, FIX 2, FIX 3), commit isolado para permitir revert pontual.
4. Critério de merge: `(novos APKs analisáveis) > 50 AND (regressão sobre baseline) < 5 APKs`.
5. Se R5 (FlowDroid quebrar) materializar: reverter FIX 3 e manter FIX 1+FIX 2 — ainda capturam parte do crash em Flowgraph.

---

## 7. Pontos Positivos

1. **Diagnóstico técnico detalhado** com stack trace, fluxo de phases, comparação com FlowDroid/CryptoAnalysis.
2. **Reconhece versões fragmentadas** no parent pom — unificar é genuinamente positivo (ainda mais com `ca.mcgill.sable` deprecado).
3. **Validação empírica** com CogniCrypt 5.0.1 antes de propor (excelente prática).
4. **Identifica módulos deprecados** (rvsec-methods-extractor, rvsec-taint) para limpar antes do upgrade — reduz superfície de quebra.
5. **Estratégia em camadas** (avoidance + graceful degradation + version uplift) é correta em princípio: cada fix ataca o problema em uma camada distinta.
6. **Preserva backward-compatibility consciente** ao notar que NÃO excluir `android.*`/`androidx.*` (diferente do CryptoAnalysis) porque GATOR precisa do framework para WTG. **Decisão técnica correta**.
7. **Analogia explícita com gh50** (instrumentação) ajuda a calibrar expectativas e padroniza o approach (`continue > throw`, `proceedOnError`, etc.).
8. **Lista questões abertas** explicitamente (§9), em vez de esconder dúvidas.
9. **Trade-off WTG documentado** (§5.3) — esclarece que `pure_algorithm` e APE-RV não dependem dele.

---

## 8. Pontos Negativos / Gaps

### P1 — Bloqueantes para execução

1. **Discrepância stack trace ↔ localização do FIX 2**: o crash documentado ocorre em `cg.cha`, não em `Flowgraph.createOpNode`. FIX 2 não cobre esse caminho. Esclarecer ou reposicionar.
2. **Linha errada citada (191 vs 343)**: confunde quem for executar o fix.
3. **Estimativa de esforço de FIX 3 irrealista** (4-8h vs 3-5 dias) — gera planejamento defeituoso.
4. **Versão alvo desatualizada** (4.7.0 vs 4.7.1).
5. **Afirmações imprecisas em FIX 1**: `ignore_resolution_errors` e `throw_analysis_dalvik` não capturam o crash em questão.

### P2 — Importantes mas não bloqueantes

6. **CryptoAnalysis options não verificadas no JAR** — base do FIX 1 é parcialmente pendurada em premissa não inspecionada.
7. **FlowDroid 2.10 ↔ Soot 4.7.1**: incompatibilidade transitiva não tratada (R5). Plano ignora que upgrade Soot pode quebrar `rvsec-reachability` (já comentado no pom, ok) mas também `rvsec-apk` que importa `soot-infoflow-android`.
8. **Sem regressão sobre os 97 APKs** que hoje funcionam — risco de baseline regredir invisivelmente.
9. **Sem plano de rollback** explícito.
10. **Sem mensuração da perda de reachability** em `generic`/`generic_new` por excludes Kotlin.
11. **Sem avaliação de memória** (Soot 4.x mais pesado).
12. **Critério de teste vago** ("≥7/10") sem nomear os 10 APKs.

### P3 — Melhorias de polish

13. **Falta cenário na spec** cobrindo "GATOR crasha em fase Soot interna" (sugerido em §2.2).
14. **Falta proposta de fallback "retry sem -withCHA"** que poderia ser implementado em horas no Python sem tocar o Java.
15. **Tabela §2.1** poderia separar "FlowDroid em SootConfigForAndroid" vs "FlowDroid em AbstractInfoflow/SetupApplication" — hoje sugere que tudo está num lugar.
16. **§4.5 (W5 Androguard)** mistura objetivos: poderia ser change separada para não inflar escopo.

---

## 9. Sugestões de Melhoria Priorizadas

### P1 (críticas — antes de começar)

- **Esclarecer o stack trace**: gerar o crash localmente (rodar GATOR manualmente em 3 APKs Kotlin/Compose: `app.siftrecipes_6.apk`, `ac.mdiq.podcini.X_256.apk`, `app.fluffy_730.apk`) e capturar o stack trace **completo**. Verificar se Flowgraph aparece (ou não). Documentar com data e ambiente.
- **Reescrever FIX 2** para incluir, no mínimo, try-catch em `Flowgraph.java:274` (`retrieveActiveBody`). Considerar também por-seção try-catch em `RvsecAnalysisClient` para garantir que mesmo crashes pós-Flowgraph emitam JSON parcial.
- **Atualizar versão alvo**: Soot **4.7.1** (não 4.7.0) e considerar bump simultâneo de FlowDroid para 2.14.1 (validada com Soot 4.6.0) ou 2.15.1.
- **Replanejar FIX 3** como 3-5 dias: dia 1 (poms + compile + lista de breaks), dia 2 (Options API + Dexpler.Util), dia 3 (compile clean + smoke 5 APKs), dia 4-5 (regressão sobre 97 APKs + ajustes).

### P2 (recomendadas)

- **Adicionar fallback "retry sem -withCHA"** no `StaticAnalyzer` Python como mitigação imediata, antes mesmo do upgrade Soot. Custo: ~2h. Pode reduzir os 27.6% para algo melhor já agora.
- **Inspecionar `HeadlessAndroidScanner-5.0.1-jar-with-dependencies.jar`** (basta `jar xf` + `javap -c`) e listar as opções Soot reais. Substituir as alegações §2.1 do plano com evidência concreta.
- **Comparar reachability** em 3 APKs (Java puro, Kotlin pequeno, Kotlin/Compose grande) **antes e depois** dos excludes Kotlin. Quantificar perda em `reachable`, `reachesMop`, `directlyReachesMop`.
- **Baseline + regressão**: rodar SA paralela pré-fix para os 97 que funcionam, salvar JSONs, comparar pós-fix. Critério: `directlyReachesMop` deve ter ±0 (per spec INV existente); `reachesMop` ±10%.
- **Definir critério de teste explícito**: nomear 10 APKs (mix funciona/falha), métrica binária (produz JSON?), métrica qualitativa (reachable count > 0?).

### P3 (polish)

- **Adicionar cenário na spec** cobrindo crash pré-RvsecAnalysisClient.
- **Separar W5 (Androguard)** em pré-plano dedicado.
- **Adicionar plano de rollback** explícito (branch separada, baseline, critério de merge).
- **Memória**: bumpar `-Xmx16g` em `lib/gator/gator` quando rodar Soot 4.7.1.
- **Documentar `-worker 1`** como invariante — evita race condition #1189.

---

## 10. Conclusão e Recomendação Final

O pré-plano está **na direção certa em estratégia geral**, mas tem **três imprecisões técnicas** que podem comprometer a execução:

1. FIX 2 está mal-localizado para o crash documentado.
2. FIX 1 inclui opções que não atuam sobre `InternalTypingException`.
3. FIX 3 é subestimado em esforço por ~5×.

A validação empírica com CogniCrypt 5.0.1 é a peça mais forte do documento — confirma que **FIX 3 (upgrade Soot)** é o ingrediente load-bearing. FIX 1 e FIX 2 são complementos úteis mas insuficientes isoladamente.

### Recomendação executiva

**Aprovar com revisão**. Antes da execução:

- **Tarefa de discovery (4-8 h)**:
  1. Reproduzir o crash e capturar stack trace completo em 3 APKs.
  2. Inspecionar JAR do CryptoAnalysis 5.0.1.
  3. Implementar fallback "retry sem `-withCHA`" no Python.
  4. Validar que essa mitigação imediata melhora a taxa de SA (mesmo sem upgrade Soot).

- **Decisão go/no-go** após discovery:
  - Se a mitigação Python sozinha levar a SA ≥ 50%, **adiar FIX 3** (tese em finalização, deadline já em 2026-04-13).
  - Se SA continuar < 40%, **aprovar FIX 1 + FIX 2 reposicionado + FIX 3** com timebox de 5 dias.

- **Critério de sucesso**:
  - SA ≥ 200/352 (57%) sem regressão dos 97 atuais.
  - `directlyReachesMop` exato em baseline `cryptoapp.apk`.
  - Tempo médio de SA ≤ 2× baseline.

Recomendo também acoplar este trabalho ao roadmap **#48 (gh48)** com prioridade média (não bloqueante para a entrega da tese, dado que JCA é foco principal e tem impacto mínimo de excludes Kotlin), tratando como **investimento de robustez** e não como bug-fix urgente.

---

## Anexo A — Verificações empíricas executadas

| Verificação | Resultado |
|-------------|-----------|
| `Flowgraph.java` linha do `throw new RuntimeException(e)` | **343** (não 191) |
| Estrutura do try-catch que envolve `createOpNode` | Confirmada (linhas 338-344). `continue` é sintaticamente válido (loop `while (stmts.hasNext())`). |
| Estrutura de `Flowgraph.java:274` (`retrieveActiveBody`) | **Fora** de qualquer try-catch. |
| Fluxo `Main.setupAndInvokeSoot()` (withCHA branch) | `cg.cha` roda antes de `wjtp.gui` → AnalysisEntrypoint → GUIAnalysis → Flowgraph. |
| Versão estável atual do Soot (`org.soot-oss`) | **4.7.1** (2025-02-23). 4.8.0 ainda SNAPSHOT. |
| Status do bug #1071 (Integer1Type) | **Aberto**. Sem PR fundido. Idêntico em 3.3.0 e 4.7.x. |
| FlowDroid `SootConfigForAndroid` (`develop`) | Só configura excludes (sem `kotlin.*`) + `no_bodies_for_excluded`. |
| Fork/patch privado de Soot em CryptoAnalysis | **Não existe** — usa upstream `org.soot-oss:4.6.0`. |
| Exclusão de Soot no `rvsec-gator/client/pom.xml` | Confirmada (exclui ambos `ca.mcgill.sable:soot` e `org.soot-oss:soot`). |
| Soot APIs em risco no GATOR | `Options.v().set_*()` em `Configs.java:235-237`, `soot.dexpler.Util.*` em `EpiccBasedIntentAnalysis.java:125-128`, `getMethods() : Chain → List` em `Flowgraph.java:267` e `Hierarchy.java:536`. |

## Anexo B — Fontes externas consultadas

- [Soot releases](https://github.com/soot-oss/soot/releases) — 4.7.1 confirmado em 2025-02-23.
- [Soot ClassHierarchy.java (master)](https://github.com/soot-oss/soot/blob/master/src/main/java/soot/jimple/toolkits/typing/integer/ClassHierarchy.java) — bug `typeNode()` inalterado.
- [Soot #1071 Integer1Type](https://github.com/soot-oss/soot/issues/1071) — aberto, sem PR.
- [Soot #1641 jb.sils trigger](https://github.com/soot-oss/soot/issues/1641) — confirma fase trigger.
- [SootUp 2.0 releases](https://github.com/soot-oss/SootUp/releases) — Mar/2025.
- [SootUp APK Frontend status](https://deepwiki.com/soot-oss/SootUp/4.3-apk-frontend) — admite limitações Android.
- [SootUp vs Soot, ServiceNow Security Lab](https://securitylab.servicenow.com/research/2024-11-12-sootup-vs-soot/) — Nov/2024.
- [FlowDroid SootConfigForAndroid (develop)](https://github.com/secure-software-engineering/FlowDroid/blob/develop/soot-infoflow-android/src/soot/jimple/infoflow/android/config/SootConfigForAndroid.java) — config real verificada.
- [FlowDroid releases](https://github.com/secure-software-engineering/FlowDroid/releases) — 2.15.1 estável.

---

*Fim da análise*
