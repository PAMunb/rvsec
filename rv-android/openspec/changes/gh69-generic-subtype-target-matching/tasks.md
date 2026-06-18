<!-- Scope: Java (rvsec-mop-extractor + rvsec-gator commons/client), ~6-8 files. Below 20 files →
     no subagent orchestration needed. Critical path: 1 (extractor) → 2 (commons/source + helper) →
     3 (wire 2 match points) → 4 (ordered rebuild + IT on real scene) → 5 (verify + review).
     The rv-* component skills are Python-oriented; Java verification uses mvn/JUnit. /rv-code-reviewer
     is language-agnostic and is retained. Refs: proposal.md, specs/analysis/spec.md (INV-ANA-40..44),
     design.md (D1-D6), ADR docs/adr/0004, risk-register.md (RISK-001 High, RISK-003). GitHub #69. -->

## 1. Extractor: wildcard / `+` / name-pattern (rvsec-mop-extractor) — INV-ANA-40, INV-ANA-41

- [ ] 1.1 `model/MopMethod.java`: add fields `includeSubtypes` and `nameIsPattern` (default false), with constructor/getters; keep className/name/params/signature intact
- [ ] 1.2 `visitor/UsedJcaMethodsVisitor.visit(ImportDeclaration)`: stop discarding `isAsterisk()` imports — register wildcard-import packages (`java.util`, `java.io`, `java.lang`, `java.net`, ...) in a packages map; keep recording explicit imports as today
- [ ] 1.3 `visitor/UsedJcaMethodsVisitor.visit(MethodPointCut)`: (a) strip a trailing `+` from the owner and set `includeSubtypes=true`; (b) resolve simple owner name → FQN via explicit `imports` first, then `Class.forName(pkg + "." + simple)` over the registered wildcard packages, log+skip if unresolvable (D5); (c) detect a trailing-`*` method name and set `nameIsPattern=true`, preserving the pattern (e.g. `add*`)
- [ ] 1.4 Unit test `UsedMethodsGenericTest`: parse the 27 `generic_new` specs → assert target set cardinality > 0, and that e.g. `Collection_UnsynchronizedAddAll` yields `java.util.Collection#addAll` with `includeSubtypes=true`; `add*` yields `nameIsPattern=true` (INV-ANA-40)
- [ ] 1.5 Unit test: parse the 23 `jca` specs → assert 120 targets, all `includeSubtypes=false` and `nameIsPattern=false` (INV-ANA-40 JCA half / INV-ANA-41)
- [ ] 1.6 Run extractor unit tests: `cd ../rvsec/rvsec-mop-extractor && mvn -q test` (paths are relative to the project root `rvsec/rv-android`, where `/opsx:apply` runs; the `rvsec` dir is duplicated in the workspace)

## 2. Matcher model + source + helper (rvsec-gator commons/client) — INV-ANA-41, INV-ANA-42, INV-ANA-43

- [ ] 2.1 `commons/.../target/TargetMethod.java`: add `includeSubtypes` and `nameIsPattern` fields (immutable, default false) + getters; do not change `MatchPolicy` (orthogonal axis — *signature strictness* `LENIENT`/`STRICT`; see design D7 / ADR 0004). Extend `equals`/`hashCode`/`toString` to include the two new fields
- [ ] 2.2 `client/.../target/MopSpecsTargetSource.load()`: propagate `includeSubtypes`/`nameIsPattern` from each `MopMethod` to the `TargetMethod` (INV-ANA-41)
- [ ] 2.3 New `client/.../target/TargetMatching.java` helper: `nameMatches(TargetMethod, String)` (trailing-`*` prefix semantics, D4); `matches(SootMethodRef callSite, TargetMethod, FastHierarchy)` (exact `equals` when `!includeSubtypes`; `nameMatches && canStoreType(callSiteDeclaringType, superType)` when `includeSubtypes`, with degrade-to-`equals`+log when the super-type is absent — INV-ANA-42/43); `forceResolveTargets(Set<TargetMethod>)` via `Scene.v().forceResolve(fqn, SootClass.HIERARCHY)` returning the set actually loaded (INV-ANA-43). Note: the two match points feed different Soot types — `findDirectTargetCallersByBytecodeScan` iterates `SootMethodRef`, but `TargetResolver.resolveInScene` iterates `SootMethod`; expose `matches(...)` so both can call it (e.g. an overload, or `m.makeRef()` / pass declaringClass+name) rather than forcing one signature
- [ ] 2.4 Unit test `TargetMatchingTest`: `canStoreType` class→interface (`ArrayList <: Collection`), interface→interface (`List <: Iterable`); `nameMatches` for `add*` (matches `add`,`addAll`; not `remove`); absent super-type → degrades to `equals` + emits a warning (INV-ANA-42/43)
- [ ] 2.5 Run commons+client unit tests: `cd ../rvsec/rvsec-android/rvsec-gator && mvn -q -pl commons,client test`

## 3. Wire the A2 predicate into the two match points (rvsec-gator client) — INV-ANA-42, INV-ANA-43

- [ ] 3.1 `client/.../target/TargetResolver.resolveInScene`: when seeding the reverse-BFS set, apply `TargetMatching.matches(...)` against the declared super-type (replacing `equals(className) && equals(methodName)`) for `includeSubtypes` targets; keep the exact path for the rest. Call `forceResolveTargets(...)` before building the `FastHierarchy`
- [ ] 3.2 `client/.../RvsecAnalysisClient.findDirectTargetCallersByBytecodeScan` (~:574): match each invoke via `TargetMatching.matches(...)` against declared super-types, NOT against pre-resolved `class#method` keys; preserve `findDirectTargetCallers` (CG-based, ~:447) which consumes the resolved set (INV-ANA-42, BUG-INV-ANA-19)
- [ ] 3.3 Confirm `MopSpecsParityTest` still passes locally (JCA exact path unchanged): `mvn -q -pl client test -Dtest=MopSpecsParityTest` (INV-ANA-35)

## 4. Rebuild (ordered) + integration on the real scene — RISK-001, RISK-003, INV-ANA-44

- [ ] 4.1 Rebuild step 1 — extractor: `cd ../rvsec/rvsec-mop-extractor && mvn clean install -DskipTests` (publishes to `~/.m2` + copies `mop-extractor.jar` to `rv-android/lib/mop-extractor/`) — D6/RISK-003
- [ ] 4.2 Rebuild step 2 — gator: `cd ../rvsec/rvsec-android/rvsec-gator && mvn clean install -DskipTests -pl sootandroid,client -am` (re-bundles the fresh extractor into `rvsec-analysis-client.jar`; `sootandroid` kept in `-pl` to preserve the `FlowgraphRebuilder` arity guard); confirm both JARs copied to `rv-android/lib/gator/` with fresh timestamps
- [ ] 4.3 IT on a small APK against `generic_new`: assert log shows `Loaded N>0 MOP signatures` and `reachesTarget>0`; assert `canStoreType` runs inside the real `RvsecAnalysisClient` scene with **0 degrade warnings** for the `generic_new` owners (RISK-001 — load-bearing gate; the standalone spike does not cover production scene config)
- [ ] 4.4 Schema invariance: diff the JSON key-set of the `generic_new` run vs a `jca` run on the same APK → MUST be identical; only `reachesTarget`/`directlyReachesTarget` values differ (INV-ANA-44)
- [ ] 4.5 Canary (RISK-003): post-rebuild extractor target count for `generic_new` MUST be > 0 — proves the fresh extractor was bundled into the JAR
- [ ] 4.6 Negative E2E (no subtype over-match): on the same IT APK against `generic_new`, assert at least one method that invokes only non-target call sites (declaring type not a subtype of any `generic_new` owner, e.g. `String.length()`) is reported `reachesTarget=false`/`directlyReachesTarget=false`; and that a `remove` call on a subtype receiver does NOT match `add*`. Proves `canStoreType` widening adds zero false positives (false-positive complement of INV-ANA-42) — spec scenario "Non-target call site stays unmatched"

## 5. Verification & review

- [ ] 5.1 Full Java test pass: `mvn -q test` in `rvsec-mop-extractor` and in `rvsec-gator` (extractor unit + `TargetMatchingTest` + `MopSpecsParityTest` green)
- [ ] 5.2 Re-run the Estágio A smoke of the sweep on 5–10 APKs (per `docs/20260611_sweep_generic_new_400.md` §10) → confirm `reachesTarget>0`; do NOT launch the full 400-APK sweep (separate change)
- [ ] 5.3 Invoke `/rv-code-reviewer` via the Skill tool: "Review gh69 generic-subtype-target-matching implementation (extractor + gator matcher A2)"
- [ ] 5.4 Run `/opsx:verify` to validate implementation against specs/analysis/spec.md (INV-ANA-40..44)
- [ ] 5.5 Update `docs/20260617_sa_generic_new.md` §13 status (implemented) and tick the issue #69 acceptance criteria

## Follow-up backlog herdado do gh60 (C2/C3) — NÃO é escopo do gh69

> Parqueado aqui a pedido do usuário (2026-06-17): em vez de abrir issues GitHub agora
> (gh60 tasks 10.1/10.2), o backlog C2/C3 do plano GATOR-targets
> (`docs/20260515_plano_gator_targets_generic.md` §10.2/§10.3) fica registrado nesta change
> ativa de GATOR. **Estes itens NÃO são tarefas do gh69** (sem checkbox, não contam no
> progresso) e não alteram o escopo do gh69 (matching subtype/wildcard). Viram issues GitHub
> quando C2/C3 forem efetivamente iniciados. Lembrete do plano: o analisador estático GATOR
> **só está completo após C2 e C3 mergearem** (gh60 é "C1 de 3").

### C2 — `hardening-package` (bug fixes + observabilidade)

**Title**: GATOR: hardening (cache, menu inheritance, integer-array, dead code expanded) + dual package + observability

- **Summary**: Bug fixes/hardening do review codex gh57 + análise multi-LLM 2026-05-15. Inclui
  dual-package (manifest vs code package) que corrige `am start` nos ~27,5% do corpus com apps
  game-engine/híbridos de pacotes divergentes; warning de fallback de widget-type p/ drift
  pós-ProGuard; sync do README de rv-static-analysis + expor flag CLI `--cg-algorithm`.
- **Scope**:
  - G6.2 cache em `resolveStringReference` (padrão `stringIdNameCache`)
  - G6.3 `findOnCreateOptionsMenu` percorre hierarquia de superclasses (corrige FN de menus em base classes)
  - G6.4 `parseArraysXml` cobre `<integer-array>` e `<array>` — **NOTA: já adiantado no gh60 §12 (G6.4)**; revalidar escopo restante
  - G6.5a-c dead code expandido: `client/.../wtg/model/` + `FlowgraphRebuilder.createDefineIntentContentOpNode` (bloco comentado) + `FlowgraphRebuilder.buildCallGraphLegacy` — **EXCLUÍDO** do dead-code: tem caller vivo em `FlowgraphRebuilder.java:980`; remoção exige decisão arquitetural sobre o branch `cgDelegation`
  - G6.6 log warn em `WidgetType.from_class_name` ao cair em OTHER
  - G11 dual package: campos top-level `manifestPackage` + `codePackage`
  - G5.7-G5.8 sync README (output path, Java version) + expor CLI `--cg-algorithm`
- **Pre-requisite**: C1 (gh60) mergeado/arquivado. Usa o `ReachabilityEnricher`/`JsonReportWriter` decompostos e as chaves JSON pós-rename (`JsonSchema.Keys`/`_JK`).
- **Gates**: paridade-delta por grupo (§5.4 do plano); `G_dual_package` (fixture ≥1 APK híbrido Godot/Unity); `G_menu_inheritance` + `G_integer_array` (fixtures sintéticas); `G_dead_code_flowgraph` zero; `G_widget_type_fallback` emite warning; `G_readme_sync`.
- **Refs**: `closes #<N+1>`, `follows #60`.

### C3 — `agent-enrichment` (JSON enrichment para APE-RV)

**Title**: GATOR: JSON enrichment for agent prioritization (widget/transition reachability + external exit + event types)

- **Summary**: Mover as junções widget×reachability e transition×reachability dos consumidores
  Python (onde a normalização de assinatura de inner-class é frágil) para o `JsonReportWriter`
  do GATOR (que tem acesso à Scene — normalização canônica). Marcar transições de saída externa
  p/ o agente evitar dead-ends (browser/dialer). Corrigir o parser Python p/ reconhecer os 14
  `EventType` (G12 confirmou Cenário A — Java já emite certo, gargalo era o parser).
- **Scope**:
  - G7 emitir `handlerReachesTarget`/`handlerDirectlyReachesTarget` por listener de widget (anotação no `ReachabilityEnricher`; writer continua puro)
  - G8.1 idem por evento de transição (per-event; agregado por-transição `targetReachesTarget` removido do JSON, derivado como `@property target_reaches_target` em `WindowTransition`) — **NOTA: o agregado por-transição, quando existir, DEVE chamar `transition_reaches_target_aggregate`**, pois `target_reaches_target` já é o `@property` de janela do gh60 (D10)
  - G9 marcar `externalExit=True`/`exitKind` p/ transições a `ACTION_VIEW`/`ACTION_SHARE`/`ACTION_DIAL`/`ACTION_SENDTO`/`ACTION_CALL`
  - G12 estender parser Python p/ todo o enum `EventType` (~10 LOC, sem mudança Java — G12.1 confirmou Cenário A)
- **Consumer**: APE-RV (aperv-tool) prioritizer + transition_picker + action_executor (§5.3 do plano); update do consumidor é PR de follow-up (não bloqueia C3).
- **Pre-requisite**: C1 (gh60) mergeado. C2 idealmente mergeado (independência técnica permite review paralelo).
- **Gates**: `G_widget_reachability` + `G_transition_reachability` zero discrepâncias; `G_external_exit` (fixture com ACTION_VIEW/ACTION_SHARE); `G_event_type_coverage` (cryptoapp emite `item_selected` p/ `spinnerMessageDigest`).
- **Final sweep**: pós-merge de C3, sweep 380 APKs com schema final.
- **Refs**: `closes #<N+2>`, `follows #60, #<C2 issue>`.
