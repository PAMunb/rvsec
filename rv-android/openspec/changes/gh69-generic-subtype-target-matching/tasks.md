<!-- Scope: Java (rvsec-mop-extractor + rvsec-gator commons/client), ~8-10 files — includes
     ReachabilityEngine, which must be extended to carry the declared Set<TargetMethod> to the bytecode
     scan (cascade; see design D-DataFlow §5). Below 20 files → no subagent orchestration needed.
     Critical path: 1 (extractor) → 2 (commons/source + helper) → 3 (wire 2 match points + cascade) →
     4 (ordered rebuild + IT on real scene) → 5 (verify + review).
     The rv-* component skills are Python-oriented; Java verification uses mvn/JUnit. /rv-code-reviewer
     is language-agnostic and is retained. Refs: proposal.md, specs/analysis/spec.md (INV-ANA-40..44),
     design.md (D1-D7), ADR docs/adr/0004, risk-register.md (RISK-001 High, RISK-003). GitHub #69. -->

## 1. Extractor: wildcard / `+` / name-pattern (rvsec-mop-extractor) — INV-ANA-40, INV-ANA-41

- [ ] 1.1 `model/MopMethod.java`: add fields `includeSubtypes` and `nameIsPattern` (default false), with constructor/getters; keep className/name/params/signature intact. **Extend `equals`/`hashCode`/`toString` to include the two new fields** — `MopMethod` lives in a `HashSet<MopMethod>` (`UsedJcaMethodsVisitor.java:24`), so omitting the flags silently dedups two pointcuts that differ only by `+`/name-pattern (verified: current `equals`/`hashCode` use only the 4 original fields)
- [ ] 1.2 `visitor/UsedJcaMethodsVisitor.visit(ImportDeclaration)`: stop discarding `isAsterisk()` imports — register wildcard-import packages (`java.util`, `java.io`, `java.lang`, `java.net`, ...) in a packages map; **seed `java.lang` by default** as defense-in-depth (Java imports it implicitly, so a future spec may omit it; note: every current `generic_new` spec with a `java.lang` owner DOES carry an explicit `import java.lang.*;` — verified 2026-07-09 — so today's owners already resolve via wildcard registration alone); keep recording explicit imports as today
- [ ] 1.3 `visitor/UsedJcaMethodsVisitor.visit(MethodPointCut)`: (a) strip a trailing `+` from the owner and set `includeSubtypes=true`; (b) resolve simple owner name → FQN via explicit `imports` first, then `Class.forName(pkg + "." + simple)` over the registered wildcard packages, log+skip if unresolvable (D5); (c) detect a wildcard method name and set `nameIsPattern=true`, preserving the pattern — handle **all 8** patterns present in `generic_new` (`add*`, `remove*`, `retain*`, `clear*`, `put*`, `offer*`, `write*`, and the **bare `*`** from `call(* Iterator.*(..))`); the bare `*` is stored as pattern `*` and is intentional match-all (D4); (d) constructor pointcuts (`call(Owner.new(..))` — `ServerSocket.new` ×2, `TreeMap.new` ×1) are NOT extracted in this change — log+skip with a notice (documented limitation, design Non-Goals: Soot `<init>` mapping out of scope); `staticinitialization(...)` pointcuts never reach `visit(MethodPointCut)`, so the 3 staticinit-only specs contribute 0 targets by design (INV-ANA-40 scope boundary)
- [ ] 1.4 Unit test `UsedMethodsGenericTest`: parse the 27 `generic_new` specs → assert the **exact** target-set cardinality, pinned at implementation (reference enumeration 2026-07-09: 67 distinct `(owner, method-name)` `call()` pairs excluding the 3 constructor pointcuts; params/flag granularity may raise N — pin the observed N after cross-checking it against this enumeration; N MUST be > 0); that `Collection_UnsynchronizedAddAll` yields `java.util.Collection#addAll` with `includeSubtypes=true` and `add*` yields `nameIsPattern=true`; that the **21 distinct `call()` JDK owners** all resolve with **skip-count == 0** for non-constructor pointcuts (the 3 `Owner.new` pointcuts are expected skips — assert exactly 3 constructor-skip notices); that `Object_MonitorOwner` resolves `java.lang.Object` (via its explicit `import java.lang.*;` wildcard registration); that a **synthetic fixture spec with NO `java.lang` import** still resolves an `Object+` owner (this — not `Object_MonitorOwner` — is what proves the default seeding); and that `Iterator.*` yields the bare-`*` pattern (INV-ANA-40)
- [ ] 1.5 Unit test: parse the 23 `jca` specs → assert 120 targets, all `includeSubtypes=false` and `nameIsPattern=false` (INV-ANA-40 JCA half / INV-ANA-41)
- [ ] 1.6 Run extractor unit tests: `cd ../rvsec/rvsec-mop-extractor && mvn -q test` (paths are relative to the project root `rvsec/rv-android`, where `/opsx:apply` runs; the `rvsec` dir is duplicated in the workspace)

## 2. Matcher model + source + helper (rvsec-gator commons/client) — INV-ANA-41, INV-ANA-42, INV-ANA-43

- [ ] 2.1 `commons/.../target/TargetMethod.java`: add `includeSubtypes` and `nameIsPattern` fields (immutable) + getters; do not change `MatchPolicy` (orthogonal axis — *signature strictness* `LENIENT`/`STRICT`; see design D7 / ADR 0004). Extend `equals`/`hashCode`/`toString` to include the two new fields. **There is exactly one 5-arg constructor** (verified), used by `MopSpecsTargetSource`, `SignatureFileTargetSource`, and ~12 test call sites (`TargetMethodTest`/`TargetResolverTest`). Per P3 (no compat shim): add the two params to the canonical constructor and **update every call site** (~14: `MopSpecsTargetSource` passes the real flags; `SignatureFileTargetSource` + tests pass explicit `false`/`false`). **No delegating 5-arg overload** — migrating all call sites is cheap and keeps a single constructor, so the JCA/STRICT/signature-file paths never reach `canStoreType` (INV-ANA-35)
- [ ] 2.2 `client/.../target/MopSpecsTargetSource.load()`: propagate `includeSubtypes`/`nameIsPattern` from each `MopMethod` to the `TargetMethod` (today it hard-codes `MatchPolicy.LENIENT` with no flags — verified) (INV-ANA-41)
- [ ] 2.3 New `client/.../target/TargetMatching.java` helper:
  - `nameMatches(TargetMethod, String)` — trailing-`*` prefix; bare `*` → prefix `""` matches all; no-`*` → `equals` (D4)
  - `matches(soot.Type callSiteType, String callSiteName, TargetMethod, FastHierarchy)` — **raw `(Type,String)` signature** (decided; closes the prior 3-option open question), so both match points call it with zero allocation (`SootMethod`/`SootMethodRef` both expose `getDeclaringClass().getType()`+`getName()`; no `makeRef()` per Scene method). Evaluate `nameMatches` **first** (short-circuit), then exact `equals` when `!includeSubtypes`, else `canStoreType(callSiteType, superType)` when `includeSubtypes` (INV-ANA-42). `STRICT` param-matching stays in `resolveInScene`, not in the helper
  - `forceResolveTargets(Set<TargetMethod>)` via `Scene.v().forceResolve(fqn, SootClass.HIERARCHY)`; classify an owner as resolved ONLY if `!isPhantom() && resolvingLevel() >= HIERARCHY` (verified: under `allow_phantom_refs=true` an unresolvable type force-resolves to a phantom at `BODIES` level that passes `containsClass` but makes `canStoreType` return a definite, wrong `false` — it does NOT throw, so a try/catch would be dead code). Cache the resolved `superType` `RefType` per target; phantom/absent owners degrade to exact `equals`+log once per owner (INV-ANA-43)
- [ ] 2.4 Unit test `TargetMatchingTest`: `canStoreType` class→interface (`ArrayList <: Collection`) and **interface→interface (`List <: Iterable`** — the only case distinguishing A2 from A1, both forced into the Scene); `nameMatches` for `add*` (matches `add`,`addAll`; not `remove`), `write*`, and the **bare `*`** (matches any name); a non-trailing-`*` pattern → literal `equals` (no crash); **absent super-type AND phantom owner** → both degrade to `equals` + emit a warning (INV-ANA-42/43)
- [ ] 2.4b Unit test `MopSpecsTargetSourceTest` (INV-ANA-41 — the orphan test referenced in design.md but previously missing from tasks): load a `generic_new` fixture → assert the emitted `TargetMethod` set carries `includeSubtypes=true`/`nameIsPattern=true` on the `+`/wildcard entries; load a `jca` fixture → assert all `TargetMethod` carry both flags `false`. This isolates the `MopMethod → TargetMethod` propagation boundary (the extractor tests 1.4/1.5 stop at `MopMethod`)
- [ ] 2.5 Run commons+client unit tests: `cd ../rvsec/rvsec-android/rvsec-gator && mvn -q -pl commons,client test`

## 3. Wire the A2 predicate into the two match points (rvsec-gator client) — INV-ANA-42, INV-ANA-43

- [ ] 3.1 `client/.../target/TargetResolver.resolveInScene`: when seeding the reverse-BFS set, apply `TargetMatching.matches(...)` against the declared super-type (replacing `equals(className) && equals(methodName)`) for `includeSubtypes` targets; keep the exact path for the rest. **`nameMatches` MUST be evaluated before `canStoreType`** — the current `equals(fqn)` fast-reject disappears for subtypes (verified: triple loop `Scene.getClasses()` × methods × targets), so the name short-circuit is the mandatory replacement (RISK-005, this match point too). Call `forceResolveTargets(...)` before building the `FastHierarchy`
- [ ] 3.2 **Cascade + hybrid scan** (verified: `findDirectTargetCallersByBytecodeScan(appClasses, Set<SootMethod>)` (~:574) and `ReachabilityEngine` receive only resolved methods, losing the declared owner + flags; `RvsecAnalysisClient.run()` already holds `targetSpecs` (`Set<TargetMethod>`) in scope):
  - extend `ReachabilityEngine`'s constructor/`run(...)` and `findDirectTargetCallersByBytecodeScan` to also carry `Set<TargetMethod> targetSpecs`, propagated from `run()`
  - make the scan **hybrid**: keep the `Set<String> class#method` key path for `!includeSubtypes` targets (JCA O(1) + parity), and for `includeSubtypes` targets iterate (grouped by distinct super-type) applying `TargetMatching.matches(...)` per invoke against the declared super-type — NOT pre-resolved keys
  - preserve `findDirectTargetCallers` (CG-based, ~:447) which consumes the resolved set (INV-ANA-42, BUG-INV-ANA-19)
- [ ] 3.3 Confirm `MopSpecsParityTest` still passes locally (JCA exact path unchanged): `mvn -q -pl client test -Dtest=MopSpecsParityTest` (INV-ANA-35)

## 4. Rebuild (ordered) + integration on the real scene — RISK-001, RISK-003, INV-ANA-44

- [ ] 4.1 Rebuild step 1 — extractor: `cd ../rvsec/rvsec-mop-extractor && mvn clean install -DskipTests` (publishes to `~/.m2` + copies `mop-extractor.jar` to `rv-android/lib/mop-extractor/`) — D6/RISK-003
- [ ] 4.2 Rebuild step 2 — gator: `cd ../rvsec/rvsec-android/rvsec-gator && mvn clean install -DskipTests -pl sootandroid,client -am` (re-bundles the fresh extractor into `rvsec-analysis-client.jar`; `sootandroid` kept in `-pl` to preserve the `FlowgraphRebuilder` arity guard); confirm both JARs copied to `rv-android/lib/gator/` with fresh timestamps
- [ ] 4.3 IT on a small APK against `generic_new`: assert log shows `Loaded N>0 MOP signatures` and `reachesTarget>0`; assert `canStoreType` runs inside the real `RvsecAnalysisClient` scene with **0 degrade warnings for the 21 `generic_new` super-type owners** — a degrade on any `includeSubtypes=true` owner is a **hard gate that blocks the sweep** (RISK-001; the 21 owners are JDK and MUST force-resolve non-phantom). Log which owners resolved and whether any is phantom (the standalone spike does not cover production scene config)
- [ ] 4.4 Schema invariance: diff the JSON key-set of the `generic_new` run vs a `jca` run on the same APK → MUST be identical; only `reachesTarget`/`directlyReachesTarget` values differ (INV-ANA-44)
- [ ] 4.5 Canary (RISK-003): post-rebuild extractor target count for `generic_new` MUST be > 0 — proves the fresh extractor was bundled into the JAR
- [ ] 4.6 Negative E2E (no over-match) — **name-axis** (because `generic_new` includes `Object+`, every type is a subtype, so a pure "non-subtype" example is impossible; the non-match must come from the method name): on the same IT APK against `generic_new`, assert a subtype-receiver call whose name does NOT match the declared pattern stays `reachesTarget=false`/`directlyReachesTarget=false` — e.g. `java.util.ArrayList.remove(...)` vs `Collection+.add*`, and `java.lang.String.length()` (`String <: Object+` but `length` ∉ {`wait`,`notify`,`notifyAll`}). Confirm `nameMatches` short-circuits before `canStoreType`. Acceptance is spot-check + sampled inspection (honest bounded criterion, not a completeness proof) — spec scenario "Non-target call site stays unmatched"

## 5. Verification & review

- [ ] 5.1 Full Java test pass: `mvn -q test` in `rvsec-mop-extractor` and in `rvsec-gator` (extractor unit + `TargetMatchingTest` + `MopSpecsParityTest` green)
- [ ] 5.2 Re-run the Estágio A smoke on 5–10 APKs (procedure per `docs/20260611_sweep_generic_new_400.md` §10) → confirm `reachesTarget>0`; **APK source updated 2026-07-09**: draw the smoke APKs from the new dataset repo (`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec-dataset`, `apks_original/`) — the generic experiment will run on that corpus, superseding the 400-APK sweep corpus for dataset purposes (note: the rvsec-dataset ROADMAP is currently JCA-only; the generic-experiment planning there is a downstream change, not gh69 scope). Do NOT launch any full sweep (separate change)
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
