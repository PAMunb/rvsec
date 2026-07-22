# Diagnóstico — Paridade `cgDelegation` (M3 = FAIL)

**Data:** 2026-05-15
**Change:** gh57-static-analysis-overhaul
**Marco:** M3 (Group 6.9 — `wtg_paridade_diff.py` gate)
**Veredito:** FAIL (avg Jaccard 0.543; min 0.000 contra thresholds 0.95/0.85)
**Status:** referência para decisão de default `cgDelegation` e escopo de follow-up.

---

## 1. Contexto

O design D3 da gh57 introduziu `Configs.cgDelegation` para deslocar o cálculo do call graph da WTG do caminho legacy (`AndroidCallGraph` populado por `FlowgraphRebuilder.buildCallGraphLegacy` via points-to + CHA fallback) para o caminho SPARK (`Scene.v().getCallGraph()`, já construído pelo Soot). A motivação: a WTG legacy era a fonte dominante de timeouts no GATOR (71.6% dos APKs do dataset experimento-20260508 com `windows[]` vazio — `docs/20260513_analise_gator_window.md`).

A paridade gate M3 mediu o impacto da troca em 10 APKs (`notes/preflight_fixtures.md(c)`) comparando o conjunto de tuplas `{(sourceId, targetId, event_type)}` em `transitions[]` entre os dois modos via Jaccard similarity (`scripts/wtg_paridade_diff.py`).

## 2. Resultado empírico

### 2.1 Performance — ganho substancial e consistente

| APK | base | cand | speedup |
|---|---|---|---|
| `com.blankdev.sidestep_17` | 600s ⏱ | 26s ✓ | **~23×** |
| `de.computerelite.shockalarm_48` | 600s ⏱ | 28s ✓ | **~21×** |
| `com.gorden.dayexam_9` | 600s ⏱ | 169s ✓ | 3.5× |
| `org.fossify.keyboard_14` | 600s ⏱ | 521s ✓ | recuperado |
| `com.mouzinho.pokebase_2` | 531s | 194s | 2.7× |
| `com.wordtracer.app_22` | 123s | 41s | 3.0× |
| `com.nyx.custom_uploader_15` | 73s | 26s | 2.8× |
| `com.akylas.enforcedoze_85` | 41s | 33s | 1.2× |
| `com.dewdrop623.androidcrypt_15` | 41s | 34s | 1.2× |
| `com.anysoftkeyboard.janus_11` | 600s ⏱ | 600s ⏱ | (timeout em ambos) |

4 APKs recuperados de timeout — a hipótese central do D3 (SPARK reuso elimina a fase quadrática do call graph paralelo da WTG) é confirmada.

### 2.2 Paridade semântica — falha categorizada, não aleatória

| APK | base | cand | Jaccard | leitura |
|---|---|---|---|---|
| `dewdrop623.androidcrypt` | 5 | 5 | **1.000** | parity perfeita |
| `enforcedoze` | 97 | 86 | **0.887** | borderline — perdeu 11/97 (~11%) |
| `keyboard` | 0 | 36 | **(ganho)** | baseline timeoutou; candidate completou |
| `sidestep` | 0 | 0 | trivial | baseline timeout, candidate vazia |
| `dayexam` | 0 | 0 | trivial | idem |
| `shockalarm` | 0 | 0 | trivial | idem |
| **`pokebase`** | **4** | **0** | **0.000** | regressão total — RN |
| **`custom_uploader`** | **12** | **0** | **0.000** | regressão total — Flutter |
| **`wordtracer`** | **13** | **0** | **0.000** | regressão total — Capacitor |

**As 3 regressões totais compartilham um padrão**: são apps de **framework híbrido** (RN, Flutter, Capacitor) cujas activities entry-point e listeners de UI são wired através de bridges nativas e lambdas sintéticas (`$$ExternalSyntheticLambda*`).

## 3. Mecanismo da regressão

### 3.0 Arquitetura: dois call graphs, três estágios de dispatch

A análise do GATOR pós-gh51 carrega **dois call graphs estruturalmente independentes** dentro de um mesmo processo Java. Entender essa separação é pré-requisito para ler o resto do diagnóstico.

**Camada 1 — `Scene.v().getCallGraph()` (SPARK CG, do Soot)**

- Tipo: `soot.jimple.toolkits.callgraph.CallGraph` — estrutura genérica do Soot, agnóstica de Android.
- Construído por: pack `cg.spark` do Soot, ativado por `Configs.cgAlgorithm = "spark"` (gh51 D5, default).
- Quem consome: a fase de **reachability** dentro de `RvsecAnalysisClient.run()` (linhas 112–123): `multiSourceBfs(graph, entryPoints)` para `reachable[]`, reverse BFS para `reachesTarget[]`.
- **Não foi mexido pelo gh57.** Continua SPARK sempre, em qualquer modo de `cgDelegation`.

**Camada 2 — `AndroidCallGraph.v()` (singleton específico GATOR)**

- Tipo: `presto.android.gui.wtg.flowgraph.AndroidCallGraph` — indexado por `(SootMethod source, Stmt invokeStmt) → Set<SootMethod tgt>`. A indexação por *call site* (Stmt) é o que diferencia: a WTG precisa saber **qual statement** invocou cada handler para amarrar o evento ao widget que o disparou. O CG do Soot não oferece esse índice diretamente.
- Construído por: `FlowgraphRebuilder.buildCallGraph(method, s)` — iterado sobre todos os invoke statements de todos os métodos de aplicação.
- Quem consome: o `WTGBuilder` e seus 6 estágios subsequentes (lifecycle resolution, event handler resolution, transition emission, etc.).
- **Sempre é populado**, independente do modo. O que muda com `cgDelegation` é *como*.

**Histórico**: o GATOR foi escrito quando o default do Soot ainda era CHA e SPARK não estava maduro para Android. O `AndroidCallGraph` foi modelado para evitar dependência do CG do Soot — toda a lógica de dispatch foi implementada localmente em `FlowgraphRebuilder`, incluindo um points-to próprio (`queryHelper.allVariableValues`) com fallback CHA. O gh57 D3 foi a primeira tentativa de eliminar essa redundância delegando o trabalho ao SPARK.

**Os três estágios de dispatch em `buildCallGraph` (linhas 951–982)**

Para cada invoke statement do app, o método toma o seguinte caminho:

```
(a) Special handling Android-aware — SEMPRE roda, em ambos os modos:
    ├─ isBindImplicitMethodCall(s)  → handleBindImplicitMethodCall(s)
    ├─ isRunBindImplicitMethodCall(s) → handleRunBindImplicitMethodCall(s)
    │   (estes cobrem Thread.start → Runnable.run, AsyncTask.execute → onPreExecute /
    │    doInBackground / onPostExecute, View.post / Activity.runOnUiThread → Runnable,
    │    e registration patterns como setOnClickListener)
    └─ isAsyncMethodCall(s) → handleExecImplicitMethodCall(s)

(b) Static/Special invokes — SEMPRE direto:
    │ Para StaticInvokeExpr e SpecialInvokeExpr, o callee é único (não há dispatch
    │ virtual). Adiciona target direto: callgraph.add(source, callee, s).

(c) Virtual/Interface dispatch — É AQUI QUE OS MODOS DIVERGEM:
    ├─ cgDelegation=true  → buildCallGraphFromSparkCg(source, s)
    │                        consulta Scene.v().getCallGraph().edgesOutOf(s)
    └─ cgDelegation=false → buildCallGraphLegacy(source, s, ie, callee)
                            roda points-to local + CHA fallback
```

(a) e (b) **não dependem** de algoritmo de CG — são modelos hard-coded de semântica de framework Android e dispatch trivialmente resolvido. Por isso permanecem inalterados em ambos os modos.

Toda a divergência entre `cgDelegation=true` e `cgDelegation=false` ocorre em (c). É lá que está o problema.

### 3.0.1 Por que SPARK puro perde edges em frameworks híbridos

SPARK é um algoritmo **points-to** subset-flow whole-program: rastreia, para cada variável local de referência, qual conjunto de allocation sites pode reachá-la. Quando vê `obj.method()`, resolve para as classes concretas dessas alocações e adiciona uma edge por classe.

Esse modelo é sound + relativamente preciso **se o programa está fechado** — i.e., se todas as alocações são feitas em código que SPARK consegue ver. Em Android isso já é semi-quebrado (callbacks de lifecycle são instanciados pelo framework, não pelo app), mas o GATOR mitiga isso via estágio (a) acima — `bindImplicitMethodCall` etc. hardcoda os "atalhos" do framework.

**Em frameworks híbridos esse modelo quebra fundo**:

- **React Native**: listeners de UI são criados no bytecode do app (geralmente como synthetic lambdas geradas pelo D8 — `com.swmansion.…$$ExternalSyntheticLambda0`), mas a **invocação** vem do bridge JS↔native (`com.facebook.react.bridge.ReactInstanceManager.callMethod(...)`). SPARK vê a alocação da lambda mas não consegue rastrear o fluxo até onde ela é eventualmente invocada — a invocação atravessa código do bridge que não está no app.
- **Flutter**: mesma estrutura — listener registrado no app, dispatch via `io.flutter.embedding.engine.dart.DartExecutor.executeDartEntrypoint(...)` que invoca código Dart.
- **Capacitor / Cordova**: dispatch via `com.getcapacitor.Bridge.execute(...)` que faz lookup dinâmico em um dicionário runtime.

O resultado prático: para os invoke statements onde a WTG depende de saber **qual lambda específica é o target de um listener**, SPARK retorna `edgesOutOf(s) = ∅`. Isso quebra três cadeias:

1. A edge `setOnClickListener call site → ExternalSyntheticLambda.onClick(View)` não é materializada.
2. Sem essa edge, o `WTGBuilder` não consegue identificar qual `NObjectNode` é o handler do click.
3. Sem o handler vinculado, a transição não é emitida — e, pior, a activity que hospeda o widget **deixa de ser promovida a WTGNode** (a promoção depende de evidência de "vivacidade" via edges in/out).

Por isso a perda em `pokebase` é total: a MainActivity nem aparece como WTGNode (cai no fallback ID 100000), e nenhuma transition é emitida — nem mesmo as `implicit_home/_power/_rotate_event` que são dependentes apenas de a activity existir como nó da WTG.

### 3.0.2 Por que o CHA fallback do legacy capturava

`buildCallGraphLegacy` faz dois estágios:

1. **Points-to local** (linhas 1045–1066): para cada `NObjectNode` que o queryHelper diz poder chegar ao receiver, faz `hier.virtualDispatch(callee, sc)` e adiciona a edge.
2. **CHA fallback** (linhas 1067–1083): **se points-to não resolveu nada**, e o receiver não é de uma classe activity/GUI/listener (que têm early-return — porque para esses tipos GATOR resolve via Special Handling no estágio (a)), o método **itera todas as concrete subtypes** do tipo declarado via `hier.getConcreteSubtypes(stc)` e adiciona uma edge para cada virtualDispatch resolvido.

O CHA fallback é **over-approximate** — pode adicionar arestas que o runtime nunca exercitará. Mas para o caso do listener-via-lambda-sintética:

- Receiver é declarado como `OnClickListener` (ou `DialogInterface.OnCancelListener` etc).
- SPARK não rastreou a alocação da lambda → points-to local também não rastreia (mesmo algoritmo).
- CHA fallback **itera todas as classes concretas que implementam `OnClickListener`** na hierarquia da aplicação, e adiciona edges para cada uma. Entre elas: `BridgeWebChromeClient$$ExternalSyntheticLambda2.onClick(View)` — pega!
- A WTG, ao consultar o `AndroidCallGraph` para esse call site, vê N targets possíveis (incluindo o lambda real) e ata o evento corretamente.

O custo dessa over-approximation: outras edges spurious (lambdas de classes não relacionadas que também implementam `OnClickListener`). Mas como a WTG só emite transições para handlers que efetivamente apontam para um widget identificado, essas edges spurious tendem a não materializar transições; ficam como ruído no `AndroidCallGraph` mas não poluem o `transitions[]` JSON.

### 3.0.3 O que o follow-up vai fazer

O conserto correto **não é** "reverter para CHA" ou "ficar com SPARK puro". É **combinar os dois**:

```
buildCallGraphFromSparkCg(source, s):
    sparkEdges = Scene.v().getCallGraph().edgesOutOf(s)
    if sparkEdges não vazio:
        adiciona todos
        return                                              # ← caminho rápido (≥90% dos cases)

    # SPARK retornou zero — três estratégias de fallback em ordem:

    declaredClass = s.getInvokeExpr().getMethod().getDeclaringClass()
    if declaredClass está em IGNORED_CLASSES (java.*/android.*/...):
        adiciona declared callee                             # INV-ANA-22 (já implementado)
        return

    # NEW (follow-up): CHA fallback escopado a application classes
    if receiver não é activity/GUI/Listener (mesmo predicate do legacy):
        receiverType = receiver.getType().getSootClass()
        for sub in hier.getConcreteSubtypes(receiverType):
            if sub.getPackageName() ∈ application packages:
                tgt = hier.virtualDispatch(callee, sub)
                if tgt != null: adiciona tgt
```

A diferença chave do legacy: o CHA fallback **só itera classes de aplicação** (filtro por `Configs.appPackageName`), não todas as concrete subtypes do universo Soot. Isso evita o custo O(N) sobre stdlib Kotlin / AndroidX / etc. que seria proibitivo, mantendo o ganho perf que SPARK oferecia para os ≥90% dos call sites onde resolve com precisão.

Hipótese de medição: para os 3 APKs hybrid-framework que falharam o gate, o filtro de application classes mantém o número de subtypes iterados na ordem de dezenas (não milhares) porque as lambdas sintéticas são todas em `com.app.…$$ExternalSyntheticLambda*`. Custo extra esperado: alguns segundos por APK; benefício esperado: paridade restaurada para Jaccard ≥ 0.85 nos casos atualmente em 0.000.

Essa hipótese só será confirmada quando o follow-up `gh<N>-cg-delegation-framework-edges` rodar a paridade gate.

### 3.1 Observação direta — IDs das windows mudam

`RvsecAnalysisClient.extractWindows` (linhas 727–757) atribui `window.id` da seguinte forma:
```java
Integer nodeId = windowNodeIds.get(activity.getName());
window.put("id", nodeId != null ? nodeId : fallbackId++);  // fallbackId starts at 100000
```

O mapa `windowNodeIds` é populado a partir de WTGNodes (linha 173): `windowNodeIds.put(win.getClassType().getName(), win.id);`. Se a WTG não criou node para a activity, o lookup falha e cai no fallback `100000++`.

Empírico:

| APK | Window | baseline id | candidate id | leitura |
|---|---|---|---|---|
| pokebase | MainActivity | 1461 | **100000** | WTG candidate **não criou node** |
| pokebase | BottomSheetDialog | 95596 | 95596 | WTG criou em ambos |
| custom_uploader | MainActivity | 1186 | **100000** | sem WTG node |
| custom_uploader | WebViewActivity | 1204 | **100001** | sem WTG node |
| wordtracer | BridgeActivity | 869 | **100000** | sem WTG node |
| wordtracer | MainActivity | 884 | **100001** | sem WTG node |

**Consequência direta**: sem WTGNode para a activity, qualquer transição com `sourceId` ou `targetId` apontando para ela é dropada pelo WTGBuilder porque não há ponto de ancoragem. Por isso `transitions[]` virou vazio.

### 3.2 Raiz no FlowgraphRebuilder

O dispatch entre os caminhos é (linhas 951–982):

```java
private void buildCallGraph(SootMethod source, Stmt s) {
    // (a) Special handling — preservado em AMBOS os modos
    if (wtgUtil.isBindImplicitMethodCall(s))    { handleBindImplicitMethodCall(s); return; }
    if (wtgUtil.isRunBindImplicitMethodCall(s)) { handleRunBindImplicitMethodCall(s); return; }
    if (wtgUtil.isAsyncMethodCall(s))            { handleExecImplicitMethodCall(s); return; }
    if (ie instanceof StaticInvokeExpr || ie instanceof SpecialInvokeExpr) {
        callgraph.add(source, callee, s); return;
    }
    // (b) Virtual dispatch — divergem aqui
    if (Configs.cgDelegation) buildCallGraphFromSparkCg(source, s);
    else                       buildCallGraphLegacy(source, s, ie, callee);
}
```

A parte (a) — handling especial Thread/AsyncTask/runOnUiThread e binding implícito — é a **mesma** nos dois modos. Logo a divergência está em (b) para receivers de virtualinvoke/interfaceinvoke.

### 3.3 O que o legacy faz que o SPARK delegation não faz

`buildCallGraphLegacy` (linhas 1036–1084) tem dois estágios:

1. **Points-to resolution** (linhas 1045–1066): para cada `NObjectNode` que pode chegar ao receiver, faz `hier.virtualDispatch(callee, sc)`. Se ao menos um target foi encontrado, retorna.
2. **CHA fallback** (linhas 1067–1083): se points-to não resolveu nada, faz dispatch para todos os subtypes concretos via `hier.getConcreteSubtypes(stc)`. **Mas exclui** receivers cuja classe é Activity, GUI class, ou ListenerType.

`buildCallGraphFromSparkCg` (linhas 995–1017) faz apenas:
1. `Scene.v().getCallGraph().edgesOutOf(s)` — usa o resultado já calculado do SPARK.
2. Se SPARK retornou zero arestas E o callee declarado está em `java/javax/sun/android/androidx/dalvik`, adiciona o callee declarado como fallback (INV-ANA-22 recovery).

**Lacuna estrutural**: o fallback CHA do legacy, que ata edges para todos subtypes concretos quando points-to falha, **não é replicado** no caminho SPARK. SPARK por si é mais preciso (faz seu próprio points-to subset-flow ou similar) mas em frameworks híbridos:

- Os receivers de UI são lambdas sintéticas (`com.swmansion.rnscreens.bottomsheet.DimmingViewManager$$ExternalSyntheticLambda0`, `com.getcapacitor.BridgeWebChromeClient$$ExternalSyntheticLambda2`).
- O ponto de alocação dessas lambdas é frequentemente reflection ou registration via bridge nativa — invisível para points-to.
- SPARK não materializa essas arestas; o legacy via CHA fallback (sobre todas as classes do app que implementam `OnClickListener` / `DialogInterface.OnCancelListener` / etc.) **encontrava** o lambda como subtype concreto e adicionava a aresta.

### 3.4 Por que o fallback IGNORED_CLASSES não cobre o caso

O fallback atual (linhas 1019–1032) só dispara se `declaringClass.startsWith("java.|javax.|sun.|android.|androidx.|dalvik.")`. As lambdas sintéticas residem em **classes da aplicação** (`com.swmansion.*`, `com.getcapacitor.*`, `io.flutter.plugins.*`). Logo a recovery é estruturalmente incapaz de adicioná-las.

### 3.5 Por que `pokebase` perdeu transições `implicit_*` também

As transições `implicit_home_event`, `implicit_power_event`, `implicit_rotate_event` em `1461→1461` (baseline) referenciam a **MainActivity como window node**. O WTGBuilder gera essas transições para *toda* activity que é WTG node. Se a MainActivity **não foi promovida a WTG node** (porque o flow graph em candidate não tem as edges que sinalizam "essa activity é live"), nenhuma transição implícita é emitida. Esse fato é coerente com o ID fallback `100000` observado.

A "promoção a WTG node" depende de detecção de:
- Intent-based launching (`startActivity(intent)` cujo target class é resolvido)
- Lifecycle bridging (callbacks `onCreate` invocados via call graph)
- View hierarchy attachment

Em apps RN/Flutter/Capacitor, parte significativa desse wiring atravessa o bridge nativo (`com.facebook.react.bridge.*` para RN, `io.flutter.embedding.engine.*` para Flutter, `com.getcapacitor.Bridge` para Capacitor). SPARK frequentemente não rastreia essas pontes.

### 3.6 Por que enforcedoze ficou no meio (0.887)

`com.akylas.enforcedoze` é Android nativo — não é hybrid. Perdeu 11 de 97 transições. Hipótese (não verificada): as 11 perdidas são listeners de UI registrados via lambdas (`btn.setOnClickListener(v -> ...)`), que SPARK não rastreia mas legacy capturava via points-to. As 86 mantidas são lifecycle e callbacks resolvidos por SPARK normalmente. Esta é uma regressão **quantitativamente menor** mas qualitativamente do mesmo tipo.

### 3.7 Por que `dewdrop623.androidcrypt` deu 1.000

App pequeno, sem framework reativo. Todas as transições são de lifecycle Android canônico (resolvíveis por SPARK). Confirmação de controle: cgDelegation está correto quando o app não depende de wiring de framework híbrido.

## 4. Síntese da causa raiz

```
SPARK call graph não materializa edges para callbacks wired via
synthetic lambdas + native bridges (RN, Flutter, Capacitor, Compose).

Legacy AndroidCallGraph capturava esses casos via CHA fallback
sobre subtypes concretos do tipo declarado do receiver — exceto
para activity/GUI/listener classes (que tinham early-return),
mas o points-to do legacy frequentemente encontrava o lambda
através de upstream tracking que SPARK não faz.

buildCallGraphFromSparkCg substitui esse algoritmo por um único
query a Scene.v().getCallGraph().edgesOutOf(s), sem fallback
estrutural para o caso application-classes-zero-edges.
```

Esta é a **mesma classe de problema** que motivou a investigação `project_gator_ft_investigation.md` (memória 2026-05): SPARK CG limitations em DI/Compose tracing, package detector que falsamente sinalizou apps como tendo zero MOP reachability.

## 5. Análise de trade-offs

### 5.1 Opção A — `cgDelegation=false` como default

**Decisão:** manter SPARK delegation como **opt-in** via `--cg-delegation true`. Default falso preserva a semântica histórica do GATOR.

**Prós**:
- Zero regressão de paridade
- Performance: usuários que sabem que seu corpus não tem framework híbrido podem ativar manualmente e ganhar 2–20×
- Reversível em 1 commit no futuro quando 5.2 estiver pronto
- Não bloqueia gh57 — ship `windows[]` decouple, schema v2, MenuExtractor, SpinnerItemExtractor, XML attrs, D7 inflation, codex fixes

**Contras**:
- O ganho de performance grande **permanece dormente** para o sweep G9 (380 APKs)
- 71.6% dos APKs do dataset experimento-20260508 continuariam com `windows[]` vazio se a calibração v3 rodar sweep com default
  - **Mitigação**: `--skip-wtg` (G2) e a decoupling de `windows[]` (G2) já mantêm `windows[]` populado nos JSONs parciais, então o problema operacional do experimento já foi resolvido **independente** do cgDelegation. O ganho do cgDelegation aqui seria *também* recuperar `transitions[]` para esses 136 APKs.

**Custo**: alterar `Configs.cgDelegation = true` → `false` em uma linha. Atualizar tasks 6.6 e 6.10 com nota explicativa.

### 5.2 Opção B — Portar CHA fallback para `buildCallGraphFromSparkCg`

**Decisão:** abrir follow-up `gh<N>-cg-delegation-framework-edges` com escopo: replicar o CHA-fallback do legacy no caminho SPARK quando `edgesOutOf(s)` retornar zero edges E o receiver não for activity/GUI/listener.

**Esboço da correção** (em `buildCallGraphFromSparkCg`):
```java
// Existing: query SPARK
if (sparkAdded > 0) return;

// New: application-class CHA fallback when SPARK returned nothing.
// Mirrors buildCallGraphLegacy lines 1067–1083 minus the early
// returns for activity/GUI/listener types (which SPARK handles
// directly via lifecycle hooks).
if (!(ie instanceof InstanceInvokeExpr)) return;
Local rcv = jimpleUtil.receiver(ie);
if (rcv == null || !(rcv.getType() instanceof RefType)) return;
SootClass rcvClass = ((RefType) rcv.getType()).getSootClass();
// (We DO run CHA fallback even for listener types here — that's
//  exactly the case SPARK is dropping in hybrid frameworks.)
for (SootClass sub : hier.getConcreteSubtypes(rcvClass)) {
    SootMethod tgt = hier.virtualDispatch(callee, sub);
    if (tgt != null) callgraph.add(source, tgt, s);
}
```

**Riscos**:
- Volta parte da over-approximation que o D3 quis evitar — pode reintroduzir parte do custo perf que cgDelegation eliminou (porém só para call sites onde SPARK falhou, que é minoria).
- Pode adicionar edges espúrios que confundem a WTG (gerando transições false-positive). Mitigação: gate com flag adicional `cgDelegationChaFallback` (default true) e medir paridade novamente.
- A interface de `hier.getConcreteSubtypes(stc)` pode iterar sobre milhares de classes em libs grandes (Kotlin stdlib, AndroidX) — precisa filtrar para app classes apenas, ou impor um teto.

**Custo estimado**: 4–6h investigação + impl + re-rodar paridade gate.

**Critério de sucesso**: paridade gate atinge avg ≥ 0.95 / min ≥ 0.85 nos mesmos 10 APKs.

### 5.3 Opção C — Forçar `cgDelegation=true` mesmo com FAIL

**Decisão:** descartada. Quebra contrato de paridade documentado no D3 e na requirement `cgDelegation Default Behavior`. Calibração v3 não pode adotar um pipeline com transições silenciosamente dropadas em apps de framework híbrido.

## 6. Decisão tomada

**A** (cgDelegation default false) **+ abrir follow-up para B** (CHA fallback no caminho SPARK).

### 6.1 Ações dentro do gh57

1. Alterar `Configs.cgDelegation` default `true → false` (linha única em `sootandroid/.../Configs.java`).
2. Atualizar `design.md` D3 explicando a decisão e referenciando este documento.
3. Atualizar requirement "cgDelegation Default Behavior" no `specs/analysis/spec.md` para refletir default false + cenário "framework híbrido perde transições no candidate até 5.2 fechar".
4. Marcar tasks 6.6 (build), 6.7/6.8/6.9 (paridade) e 6.10 como completas com referência a este diagnóstico.
5. Adicionar nota em `notes/wtg_paridade_report.md` (referenciada em 6.9) com tabela e link aqui.

### 6.2 Escopo do follow-up `gh<N>-cg-delegation-framework-edges`

- Implementar §5.2 (CHA fallback application-class scope).
- Re-rodar paridade gate, exigir avg ≥ 0.95 / min ≥ 0.85.
- Se passar, **ESTUDAR** se default volta a `true` ou se permanece opt-in com documentação.
- Avaliar se o handling Android-aware (Thread.start, AsyncTask, runOnUiThread) precisa de extensão para bridges hybrid: react-native execute method, flutter MethodChannel.invokeMethod, capacitor PluginCall — uma camada de "Hybrid Bridge Handling" simétrica ao Special Handling existente.

### 6.3 Não-escopo deste diagnóstico

- Refactor do `RvsecAnalysisClient` (codex review §Sugestões #1) — segue para `gh<N>-rvsec-client-refactor`.
- Investigação detalhada do enforcedoze (quais 11 transições foram perdidas).
- Inspeção de janus_11 (timeout em ambos os modos — patológico, sem relação com cgDelegation).
- Tentativa de adicionar handling Android-aware para chamadas Compose / DI containers.

## 7. Apêndice — Evidência por APK

### pokebase (RN)

```
BASELINE 4 transitions:
  1461→1461  implicit_home_event
  1461→1461  implicit_power_event
  1461→1461  implicit_rotate_event
  95596→95596  click  <DimmingViewManager$$ExternalSyntheticLambda0: onClick(View)>

CANDIDATE 0 transitions.
windows: id=100000 (fallback) for MainActivity, id=95596 (matched) for Dialog.
```

### custom_uploader (Flutter)

```
BASELINE 12 transitions referenciando id=1186 (MainActivity) e id=1204 (WebViewActivity):
  1204→1204  implicit_power_event
  1204→1204  press_key  <WebViewActivity.onKeyDown>
  1204→1204  implicit_home_event
  1204→1186  implicit_back_event
  1204→1204  implicit_rotate_event
  1186→1204  implicit_on_activity_result  <O0.d.onActivityResult>
  ...

CANDIDATE 0 transitions; windows id=100000 / 100001 (ambos fallback).
```

### wordtracer (Capacitor)

```
BASELINE 13 transitions referenciando id=869 (BridgeActivity), 884 (MainActivity),
e 3 dialog IDs (29922, 29924, 29926):
  29922→29922  dialog_cancel  <BridgeWebChromeClient$$ExternalSyntheticLambda2: onCancel>
  29924→29924  dialog_cancel  <BridgeWebChromeClient$$ExternalSyntheticLambda10: onCancel>
  869→869  implicit_power_event
  869→869  implicit_on_activity_result  <BridgeActivity.onActivityResult>
  ...

CANDIDATE 0 transitions; activities com fallback IDs; dialogs ainda têm IDs originais.
```

## 8. Referências

- Phase-0 doc: `docs/20260513_gator_analise_wtg.md`
- Phase-0 doc (problema empírico): `docs/20260513_analise_gator_window.md`
- Design D3: `openspec/changes/gh57-static-analysis-overhaul/design.md`
- Memória prévia: `project_gator_ft_investigation.md` (gh51 SPARK FT diagnóstico)
- Memória prévia: `project_modernization_research_2026-05-02.md` (RN/Compose tracing gap)
- Código:
  - `rvsec-gator/sootandroid/.../FlowgraphRebuilder.java:940-1084`
  - `rvsec-gator/client/.../RvsecAnalysisClient.java:727-757,170-175`
  - `rv-android/scripts/wtg_paridade_diff.py`
- Output bruto: `/tmp/gh57_paridade_report.json`, `/tmp/gh57_paridade_baseline/`, `/tmp/gh57_paridade_candidate/`
