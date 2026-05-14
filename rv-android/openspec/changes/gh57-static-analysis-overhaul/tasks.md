<!-- Subagent dispatch hints (revised after consistency audit 2026-05-14):

     Group dependencies (logical):
     - Group 1 (pre-flight) MUST complete before any other group; emits notes/* files consumed by later groups.
     - Group 2 (core windows[] fix + skipWtg) is M1 milestone and is BLOCKING for all later code-touching groups: 4.5 and 5.6 wire new extractors into `extractWindows()` which Group 2 modifies, and Group 7 emits `schemaVersion` inside `writeJson()` which Group 2 modifies.
     - Groups 3, 4, 5, 6 can be DEVELOPED in parallel after Group 2 lands, BUT:
         * Groups 3 and 4 are file-coupled on `RvsecAnalysisClient.java` (Group 3 modifies `enrichFromXml`; Group 4 wires into `extractWindows`). Merge order: 3 → 4 to avoid manual merge conflicts.
         * Group 5 is file-coupled with Group 3 on the same widget object (5.6 unions `entries[]` after `enrichFromXml`). Merge order: 3 → 5.
         * Group 6 modifies a different file (`FlowgraphRebuilder.java`), no file coupling.
     - Group 7 (schema bump + MopData reader) depends on Groups 2, 3, 4, 5, 6 — schema must reflect ALL extractor outputs and ape:MopData.java must read them.
     - Group 8 (acceptance) depends on everything.

     Milestones:
     - M1 = end of Group 2 (windows[] populated; aperv unblocked).
     - M2 = end of Groups 3 + 4 + 5 (XML attribute extensions + programmatic menu + ArrayAdapter MVP shipped).
     - M3 = end of Group 6 with paridade gate PASS (avg ≥ 0.95 AND min ≥ 0.85).
     - M4 = end of Group 8 (full 380-APK ground-truth re-run on `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` originals validates ≥95% windows[] non-empty).

     Critical merge path: 1 → 2 → [3 → 4 → 5 in serial; 6 in parallel] → 7 → 8.
     Shortest MVP (interim build for v3 calibration unblock only): 1 → 2 → tag `gh57-interim-windows-fix` after task 2.10. Full change still finalizes via 3 → 4 → 5 → 6 → 7 → 8.

     Subagent dispatch is appropriate for Groups 4, 5, 6 after Group 3 merges (Group 6 can dispatch right after Group 2 since it touches a different file). This change touches: rvsec-gator Java module + Python rv-static-analysis sweep + external `ape` repo (MopData.java) — 3 build artifacts to sync.
-->

## 1. Pre-flight audits (Phase-0 §7.6–7.11, §16.4)

- [x] 1.1 Soot API availability: verify every Soot 4.7.1 symbol needed by the `MenuExtractor` algorithm (CFG iteration via `UnitGraph`/`ExceptionalUnitGraph`, invoke matching via `InvokeExpr`/`InterfaceInvokeExpr`, constant resolution via `IntConstant`, def-use walk via `AssignStmt` + `Value.equivTo`, `RefType`, `SootMethod.retrieveActiveBody`). Document any divergence in `notes/preflight_soot_api.md` inside the change dir. If >3 signatures are missing or incompatible, escalate Group 4 estimate. **DONE** — see `notes/preflight_soot_api.md`: 0 divergences; Group 4 estimate stands; `MenuExtractor` uses `ExceptionalUnitGraph` to match gator conventions; listener-callback wiring is out of MVP scope (covered by existing `collectWidgets`).
- [x] 1.2 ArrayAdapter corpus scan: decompile 20 stratified APKs from the original-APK corpus at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs`, grep for `new ArrayAdapter|setAdapter\(.*ArrayAdapter|getResources\(\).getStringArray|listOf\(`, classify by pattern, and compute MVP coverage. If MVP coverage <40%, switch Group 5 to full scope (+2–3 days). **DONE** — see `notes/preflight_arrayadapter_corpus.md`: MVP coverage **75% (15/20)**, well above threshold. Group 5 stays at MVP scope. Constructor path dominates (15 APKs) vs `add`/`addAll` (7 APKs) — prioritize task 5.2 over 5.3. Decompiled trees preserved at `/tmp/gh57_corpus_originals/` for Group 5 reference.
- [x] 1.3 Bytecode-scan policy at WTG level: confirm the existing `findDirectMopCallersByBytecodeScan` (RvsecAnalysisClient.java:133) can be refactored into a generic `scanInvokesByPattern(appClasses, predicate) → Set<Edge>` helper without breaking the existing MOP-scan contract. Document the API in `notes/preflight_bytecode_scan.md`. **DONE** — refactor confirmed isomorphic; helper named `scanInvokesInAppClasses(appClasses, InvokeVisitor)` with two view wrappers (MOP-callers, WTG-edges). All 8 properties of BUG-INV-ANA-19 preserved.
- [x] 1.4 Fixture inventory: from the 380-APK original corpus at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` (classified via ground-truth JSONs in `…/APKS_JCA_analise_estatica_soot/`), pick (a) 5 baseline-OK APKs for the `windows[]` partial-path smoke (stratified small/medium/large), (b) 5 baseline-frozen APKs that today produce empty windows, (c) 10 baseline-OK APKs stratified by class count for the Jaccard paridade gate, (d) 1 APK with programmatic `onCreateOptionsMenu` for Group 4, (e) 1 APK with literal `ArrayAdapter` Spinner items for Group 5. Record names + paths in `notes/preflight_fixtures.md`. If (d) or (e) cannot be sourced, escalate to author a synthetic test APK. **DONE** — all 5 fixture roles filled with real **uninstrumented** APKs from the original corpus (no synthetic APK needed). (d) = `app.notesr_59.apk` (OPTIONSMENU with `widgets=[]` in ground-truth JSON); (e) = `com.eanema.graph89_1200.apk` (7 Spinners with `entries=[]`).
- [x] 1.5 JAR sync pre-flight: build the existing `rvsec-analysis-client.jar` and `ape-rv.jar`, record their timestamps as baseline. Document the rebuild commands (`mvn install` paths) in `notes/preflight_build.md`. Note any CogniCrypt session pause coordination (Phase-0 §16.3). **DONE** — both JARs built clean via `mvn install`; baseline timestamps recorded. ⚠️ Surfaced caveat: `ape/ape.jar` (the device-deployable pushed by `install.py`) is NOT refreshed by `mvn install` — it must be `cp target/ape-rv.jar ape.jar` manually. Action item for Group 7 between tasks 7.7 and 7.8.
- [x] 1.6 ~~License attribution~~ — REMOVED. The new classes (`MenuExtractor`, `SpinnerItemExtractor`) are first-party implementations in this project under the existing `rvsec-gator` license (PAMunb). No external code is being ported; no per-class attribution headers are required beyond a normal Javadoc describing the algorithm.
- [ ] 1.7 Baseline wall-clock measurement: time `RvsecAnalysisClient.run()` on 5 large APKs (>50k CG vertices) with `cgDelegation=false` (current behavior). Record per-phase numbers (reachability vs WTG) in `notes/preflight_wallclock.md`. This becomes the comparison point for Group 8 acceptance.

## 2. Core fix — windows[] decoupling + skipWtg (Phase-0 §6 Opção C, §7.1 items 1+2; M1 milestone)

- [ ] 2.1 Modify `RvsecAnalysisClient.writeJson()` (rvsec-gator/client/.../RvsecAnalysisClient.java): in the `else` branch where `wtg == null`, replace `w.name("windows"); w.beginArray().endArray();` with a call to `extractWindows(output, Collections.emptyMap(), null)` followed by `enrichFromXml(...)` and `writeWindows(w, ...)`. Apply the same pattern to the `transitions[]` block (already empty array, leave unchanged).
- [ ] 2.2 Modify `RvsecAnalysisClient.extractWindows()`: wrap the catch-all loop `for (WTGNode node : wtg.getNodes())` (lines ~736–762) in `if (wtg != null)` so it is skipped in the partial path.
- [ ] 2.3 Add `Configs.skipWtg` boolean field (default `false`) and parse from `-clientParam skipWtg=` via `Main.java` argument loop.
- [ ] 2.4 Modify `RvsecAnalysisClient.run()`: after the partial `writeJson` call, branch on `Configs.skipWtg` — when `true`, log `[RvsecAnalysisClient] WTG skipped by client parameter` and return; when `false`, proceed with the existing `WTGBuilder.build()` path.
- [ ] 2.5 Add `--skip-wtg` boolean argument to `scripts/static_analysis_sweep.py` (rv-static-analysis); propagate as `-clientParam skipWtg=true` in the GATOR command. Emit `[SWEEP] skipWtg=true active for this run` once at sweep start when active.
- [ ] 2.6 Unit tests (Java): `RvsecAnalysisClientTest.testPartialJsonHasPopulatedWindows`, `testSkipWtgBypassesBuilder`, `testSchemaVersionFieldOrder` (will fail until Group 7 lands — mark XFAIL).
- [ ] 2.7 Unit tests (Python): `test_sweep_skip_wtg.py` for argparse propagation.
- [ ] 2.8 Build the rvsec-gator JAR (`cd rvsec/rvsec/rvsec-android/rvsec-gator && mvn install`) and run a smoke against the 5 fixture APKs from 1.4(a) and 1.4(b): verify all 10 produce non-empty `windows[]`.
- [ ] 2.9 Run `/rv-test-run rv-static-analysis`.
- [x] 2.11 Fix `rv_static_analysis.config.get_tool_command` to use `sys.executable` instead of literal `"python"`. The previous hardcoded value broke on systems without the `python-is-python3` shim (clean containers, fresh shells, non-Debian distros) — `Command` raised `CommandNotFoundError`, the static analysis silently produced no JSON, and the downstream summary appeared with zeroed coverage metrics (misdiagnosed as a regression of gh57/gh58). `sys.executable` is the uv-managed `.venv/bin/python`, which is guaranteed reachable in any invocation context.
- [x] 2.12 Add a defensive post-condition in `StaticAnalyzer._run_analysis`: after `_execute_command` returns, assert `os.path.isfile(self.analysis_file)` and raise `StaticAnalysisException` if absent. This converts upstream silent failures (e.g. interpreter not found, ErrorHandler-swallowed exceptions) into hard, observable errors before the parser is invoked — consistent with the `StaticAnalysisException` contract documented in `specs/analysis/spec.md` and the FR04 output-validity guarantee.
- [ ] 2.10 **🚩 Marco M1 — desbloqueio funcional do aperv.** Tag `gh57-interim-windows-fix` on the rvsec-gator branch if calibration v3 needs to start before the full change closes.

## 3. Widget XML attribute extensions (Phase-0 §12, item 3)

- [ ] 3.1 Modify `RvsecAnalysisClient.enrichFromXml()` to read four additional attributes from each `<View>`-style XML element: `android:prompt`, `android:spinnerMode`, `android:contentDescription`, `android:tooltipText`. Resolve `@string/<name>` references using the existing `resolveStringReference` helper. Missing attributes map to `null`.
- [ ] 3.2 Update `collectWidgets()` (RvsecAnalysisClient.java:767–818) to seed the four fields with `null` so `enrichFromXml` can overwrite them; remove the existing `widget.put("inputType", "")` + `widget.put("entries", Collections.emptyList())` defaults and replace with `null` for consistency.
- [ ] 3.3 Unit tests: `EnrichFromXmlTest.testSpinnerPromptAndMode`, `testButtonContentDescriptionAndTooltip`, `testMissingAttributeMapsToNull`.
- [ ] 3.4 Add the four fields to `StaticAnalysisParser`'s widget Pydantic model in `modules/rv-static-analysis/src/rv_static_analysis/parser.py` (or wherever widget model lives). Each field is `str | None`.
- [ ] 3.5 Unit tests (Python): `test_widget_model.py::test_parses_v2_attributes_with_nulls`.
- [ ] 3.6 Run `/rv-doc-code` on the modified widget model.
- [ ] 3.7 Run `/rv-test-run rv-static-analysis`.

## 3.5. Inflated OPTIONSMENU items via existing flow graph (cryptoapp gap, D7)

- [ ] 3.5.1 Modify `RvsecAnalysisClient.extractWindows()` in the OPTIONSMENU block (lines ~718-733): replace `window.put("widgets", Collections.emptyList());` with a walk over `menu.getChildren()` (returns the `NMenuItemInflNode` children attached by `FixpointSolver.doMenuInflate`) feeding each child into the existing `collectWidgets(output, child, widgets, visited)` helper. Pattern mirrors the DIALOG block immediately above (lines ~696-715). No new helper class, no new GATOR-side wiring.
- [ ] 3.5.2 Integration smoke: build the rvsec-gator JAR (`cd rvsec/rvsec/rvsec-android/rvsec-gator && mvn install`) and run against `apks_examples/cryptoapp.apk`. Assert `windows[where type=="OPTIONSMENU"].widgets[]` length is 3 (matching the 3 items in `res/menu/cryptoapp_menu.xml`: `menu_item_message_digest`, `menu_item_cipher`, `menu_item_home`).
- [ ] 3.5.3 Unit test: `RvsecAnalysisClientTest.testCryptoappOptionsMenuHasThreeItems` — invoke `extractWindows` against a mocked `GUIAnalysisOutput` that returns an `NOptionsMenuNode` with 3 `NMenuItemInflNode` children, assert serialized widgets length and id/text fields.
- [ ] 3.5.4 Verify that Group 4 (`MenuExtractor` programmatic path) appends to the same `widgets[]` array — the two paths must coexist; no deduplication required (id spaces disjoint by construction).

## 4. Programmatic options-menu extraction via Soot CFG (Phase-0 §12 #3, item 5)

- [ ] 4.1 Create new file `MenuExtractor.java` in `rvsec-gator/client/src/main/java/presto/android/gui/clients/`. Add a class-level Javadoc describing the algorithm (CFG walking of `onCreateOptionsMenu(Menu)`, matching of `Menu.add(...)` / `Menu.addSubMenu(...)` invocations, def-use resolution of arguments). No external attribution required (first-party class).
- [ ] 4.2 Implement `extractItems(SootClass activity) → List<Map<String, Object>>`: locate `onCreateOptionsMenu(Menu)`; build an `ExceptionalUnitGraph` over its body; walk units; for each `InterfaceInvokeExpr` matching `Menu.add(int,int,int,CharSequence)` or `Menu.add(int,int,int,int)`, resolve the four arguments (group id, item id, order, title) via def-use chains; emit a widget entry `{id, groupId, order, text, type: "MenuItem"}`. String-resource arguments (int title-res) resolve through the existing `RvsecAnalysisClient` string-resource helpers.
- [ ] 4.3 Sub-menu support: for `addSubMenu(...)` invocations, emit a submenu widget and perform a CFG-forward walk from the `addSubMenu` return value's def-site, collecting subsequent `SubMenu.add(...)` invocations (matching by receiver equivalence via `Value.equivTo`) into the submenu widget's `items[]`.
- [ ] 4.4 Wrap the entire body retrieval + iteration in try/catch (`RuntimeException`, `OutOfMemoryError`); WARN log on failure; return empty list (INV-ANA-24).
- [ ] 4.5 Wire `MenuExtractor` into `RvsecAnalysisClient.extractWindows()` after the OPTIONSMENU XML-inflated walk from task 3.5.1: for each `NOptionsMenuNode menu`, call `menuExtractor.extractItems(activity)` and **append** the result to the `widgets[]` list already populated by the inflated-items walk (no replacement; the two paths are complementary per D7).
- [ ] 4.6 Unit tests: `MenuExtractorTest.testMenuAddLiteralCharSequence`, `testMenuAddStringResource`, `testSubMenuChain`, `testBodyRetrievalFailureLogsAndContinues`.
- [ ] 4.7 Integration test: run against fixture 1.4(d), verify `windows[type="OPTIONSMENU"].widgets[].items[]` has the expected entries.
- [ ] 4.8 Run `/rv-doc-code` on the new class.

## 5. New feature — programmatic Spinner items via ArrayAdapter dataflow (Phase-0 §12.3 #6, item 5; MVP scope)

- [ ] 5.1 Create new file `SpinnerItemExtractor.java` in `rvsec-gator/client/src/main/java/presto/android/gui/clients/`. Method: `Map<String, List<String>> extractItems(SootClass activity)`.
- [ ] 5.2 Implement pattern 1 (literal constructor): walk activity methods, find `new ArrayAdapter<>(ctx, layoutId, items)` allocation sites via SPARK points-to. Trace `items` def-use chain to `new String[]{...}` or `Arrays.asList("a", "b")` allocation. Find associated `setAdapter` call to identify the Spinner via `findViewById` walk-back.
- [ ] 5.3 Implement pattern 2 (programmatic add): trace `adapter.add(s)` and `adapter.addAll(arr)` invocations on the same adapter receiver. Resolve literal-string arguments. Append to the per-Spinner items list.
- [ ] 5.4 Resilience: catch `RuntimeException`/`OutOfMemoryError` per method; WARN log; skip method (INV-ANA-24).
- [ ] 5.5 Emit coverage telemetry log: `[SpinnerItemExtractor] processed N spinners: X literal-constructor, Y add/addAll, Z unresolved` at end of activity processing.
- [ ] 5.6 Wire into `RvsecAnalysisClient.extractWindows()` after `enrichFromXml`: for each Spinner widget, union the XML-resolved `entries` with the programmatic items (XML first, programmatic appended).
- [ ] 5.7 Unit tests: `SpinnerItemExtractorTest.testLiteralConstructorWithStringArray`, `testAdapterAddCallsAccumulate`, `testXmlAndProgrammaticEntriesCoexist`, `testNonLiteralItemIsLoggedAndSkipped`.
- [ ] 5.8 Integration test: run against fixture 1.4(e), verify Spinner widget `entries[]` contains the expected items.
- [ ] 5.9 Run `/rv-doc-code` on the new class.

## 6. Opção A — FlowgraphRebuilder delegates to SPARK CG (Phase-0 §6 Opção A, item 6; M3 milestone, highest-risk)

- [ ] 6.1 Add `Configs.cgDelegation` boolean field (default `true`). Parse from `-clientParam cgDelegation=` in `Main.java`.
- [ ] 6.2 Refactor the existing `findDirectMopCallersByBytecodeScan` into a generic helper `scanInvokesByPattern(appClasses, predicate) → Set<Edge>` (per pre-flight 1.3). Preserve the existing MOP-scan call site by passing the MOP signature predicate.
- [ ] 6.3 Modify `FlowgraphRebuilder.buildCallGraph()` (lines ~940–1021): wrap the existing CHA-style loop in `if (!Configs.cgDelegation)`. Add the new branch `if (Configs.cgDelegation) { ... }` that queries `Scene.v().getCallGraph().edgesOutOf(src)`, filters by `subSignature == callee.getSubSignature()`, and adds edges to `callgraph.add(source, tgt, s)` (preserving the existing `AndroidCallGraph` populated structure so downstream WTG stages are unaffected).
- [ ] 6.4 Inside the `cgDelegation=true` branch, detect invoke sites whose declared callee class is in SPARK's `IGNORED_CLASSES`; call `scanInvokesByPattern` with the appropriate predicate to recover those edges (INV-ANA-22).
- [ ] 6.5 Unit tests: `FlowgraphRebuilderTest.testCgDelegationTrueQueriesSceneCg`, `testCgDelegationFalsePreservesLegacy`, `testIgnoredClassesEdgesRecoveredViaBytecode`.
- [ ] 6.6 Implement `scripts/wtg_paridade_diff.py`: take two JSON dirs (baseline + candidate), compute Jaccard over `{(src_id, tgt_id, event_type)}` per APK, output per-APK + average Jaccard, exit 0 on PASS (avg≥0.95, min≥0.85), 1 on FAIL.
- [ ] 6.7 Run baseline pass with `cgDelegation=false` on the 10-APK fixture from 1.4(c); save JSONs as `paridade_baseline/`.
- [ ] 6.8 Build the rvsec-gator JAR with the new code, run candidate pass with `cgDelegation=true` (default) on the same 10 APKs; save JSONs as `paridade_candidate/`.
- [ ] 6.9 Execute `scripts/wtg_paridade_diff.py paridade_baseline paridade_candidate --threshold 0.95`. **🚩 Marco M3 — GO/NO-GO.**
  - GO: avg≥0.95 and min≥0.85 → proceed to Group 7.
  - NO-GO: document divergent transitions in `notes/paridade_report.md`; either (a) extend `scanInvokesByPattern` predicate to cover the missed cases and retry, or (b) keep `cgDelegation=false` as the default and ship Group 6 dormant. The feature-flag design (D3) makes this rollback non-destructive.
- [ ] 6.10 Run `/rv-test-run` on the updated Java tests.

## 7. Schema bump + MopData reader update (Phase-0 §7.10, item 7)

- [ ] 7.1 Modify `RvsecAnalysisClient.writeJson()` to emit `w.name("schemaVersion").value("2.0")` immediately after the existing `w.name("package").value(...)` line — second field in the root object (INV-ANA-23).
- [ ] 7.2 Document the JSON schema (informative) in `rv-android/docs/static_analysis_json_v2.md`: list every field with type and nullability. Reference INV-ANA-20..24.
- [ ] 7.3 In the external `ape` repo (`/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape`): modify `MopData.java` to read `schemaVersion` near the top of the JSON parse. Branch on present/absent. For v2.0 fields, use `JsonReader` peek + safe defaults.
- [ ] 7.4 Modify `MopData.java` to parse the four new widget XML fields (`prompt`, `spinnerMode`, `contentDescription`, `tooltipText`), the recursive `items[]` for OPTIONSMENU, and treat them as `null`/empty when reading a v1.0 (legacy) JSON.
- [ ] 7.5 Unit tests in the ape repo (`MopDataTest.java`): `testReadsLegacyV1Json`, `testReadsV2JsonWithAllNewFields`, `testV2JsonWithMissingOptionalFields`.
- [ ] 7.6 Add `scripts/check_jar_sync.sh` to rv-android: verify timestamps of `rvsec-analysis-client.jar` and `ape-rv.jar` are within 10 minutes of each other; warn otherwise.
- [ ] 7.7 Build the `ape-rv.jar` with `mvn install` (NOT `mvn package`) at `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape/`. Then copy `target/ape-rv.jar → ape.jar` so `install.py` deploys the fresh artifact to the device (pre-flight 1.5 surfaced that `ape/ape.jar` is the device-deployable and is NOT refreshed by `mvn install`):
  ```bash
  cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape
  mvn install -DskipTests -q
  cp target/ape-rv.jar ape.jar
  ```
- [ ] 7.8 Run `/rv-test-run rv-static-analysis` (Python-side parser tolerates v2.0 schema field — verify no regression).

## 8. Acceptance — full re-run + final verification (Phase-0 §7.4)

- [ ] 8.1 Run `scripts/check_jar_sync.sh` to confirm both JARs are freshly rebuilt and synchronized.
- [ ] 8.2 Re-run the full 380-APK sweep on the **original** APK corpus at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` (never on `*_DEXLIB`/`*_AJC` instrumented sets — Soot Dexpler crashes on monitor-injected bytecode; project memory `feedback_static_analysis_original_apks_only.md`) using the new JARs with `cgDelegation=true` (default) and without `--skip-wtg`. Estimated wall-clock: ~3–4h in 4 workers (380 APKs vs the previous 190 estimate).
- [ ] 8.3 Post-run analysis: compute `windows[]` non-empty rate over the 380 APKs. **Acceptance: ≥95%.**
- [ ] 8.4 Compute the per-APK wall-clock comparison against the baseline from 1.7. **Acceptance: ≥30% mean reduction on the 5 large APKs.** If <20%, document in `notes/wallclock_report.md` but DO NOT block the change (the windows[] fix is independently justified).
- [ ] 8.5 Aperv smoke: run `uv run rv-experiment run --tools aperv:sata_mop --apks-dir <subset of 3 APKs> --timeout 60` and confirm: (a) no `MopData` parse errors, (b) `scoreWtg` returns non-zero on at least one APK, (c) calibration v2 default objective `0.5×mop + 0.5×method` operates on 3/3 APKs (not degraded to two-score).
- [ ] 8.6 Run `/rv-qa-lint-fix rv-static-analysis`.
- [ ] 8.7 Run `/rv-verify rv-static-analysis`.
- [ ] 8.8 Invoke `/rv-code-reviewer` via Skill tool against the change diff.
- [ ] 8.9 Run `/rv-docs-sync rv-static-analysis` to refresh `CLAUDE.md` and `architecture.md` for the modified analyzer behavior.
- [ ] 8.10 Update Phase-0 doc `rv-android/docs/20260513_gator_analise_wtg.md`: change §9 status from "ready to open change" to "closed by gh57"; cite the merge commit; archive the open-questions Q1–Q5 as resolved or deferred.
- [ ] 8.11 `/opsx:verify` against the change.
- [ ] 8.12 `/opsx:archive` (or `/opsx:sync` then `/opsx:archive --skip-specs` per WORKFLOW.md §6.6).
- [ ] 8.13 Final commit message includes `closes #57`.
