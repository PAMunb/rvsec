<!-- Path conventions used in this tasks file:
     - Java aggregator root: `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` (relative to the rvsec org clone root, which is `<workspace-rv>/rvsec/`). All `pointcut-engine/...`, `advice-emitter/...`, `dex-mutator/...`, `validator/...` paths below are relative to this aggregator root.
     - Python wrapper root: `rv-android/modules/rv-instrumentation-dexlib2/` (relative to the rv-android uv workspace root).
     - Scripts root: `rv-android/scripts/` (relative to the rv-android uv workspace root).
     Both roots live side-by-side under `<workspace-rv>/rvsec/`.
-->

<!-- Subagent dispatch hints (this change touches ~14 files including ValidationCli + script + 2 new tests; no subagent orchestration required):
     - Group 1 (Pointcut + Match) must complete first — Groups 2 and 3 depend on it.
     - Group 2 (Emitter) depends on Group 1.
     - Group 3 (Tests) depends on Groups 1 and 2; task 3.5 (Layer3MandatoryTest) further depends on 4.1/4.2.
     - Group 4 (Validator gate) is mostly independent of Groups 1-3 but MUST land before task 3.5.
     - Group 5 (Build + smoke) integrates everything — must run after 1-4.
     - Group 6 (Sampled re-run + docs) closes the loop.
     - Critical path: 1 → 2 → 3.1-3.4 → 4 → 3.5 → 3.6 → 5 → 6. -->

## 1. Pointcut + Match foundation

- [ ] 1.1 Read `docs/20260514_erro.md` §3 and §5 end-to-end to anchor the patch in the validated root-cause analysis.
- [ ] 1.2 Extend `Match` (`pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/Match.java`):
  - Add one new immutable field `public final boolean isConstructor`, populated by the `buildCallMatch` rewrite (see D3 — both `CallPC.isConstructor()` and the `<init>` opcode/method-name predicate must agree before this is set to `true`). The existing field `matchedAgainst` (of type `PointcutExpression`, NOT a `CallPC`) remains as the debugging/audit reference; the new boolean is the predicate consumed by `MonitorInvokeBuilder.resolveReturningRegister`.
  - Update the constructor signature and `Match.empty(pe)` factory to accept/initialise the new field (factory passes `false`).
  - **Update `PointcutMatcher.mergeBindings` (`PointcutMatcher.java:312-317`)** — the existing `new Match(args, target, pe)` 3-arg call becomes `new Match(args, target, pe, left.isConstructor || right.isConstructor)`. Without this update the module does not compile (B1). Rationale for the OR: when two pointcuts are combined (`call(...) && args(...)`), the constructor classification comes from whichever side identified the invoke kind; both sides agreeing on `false` keeps the merged Match non-constructor.
  - Document the `$return` synthetic key in the Javadoc for `argBindings`. The map already accepts arbitrary string keys, so no map-shape change is required.
- [ ] 1.3 Rewrite `PointcutMatcher.buildCallMatch` (`rvsec-instrumentation-dexlib2/pointcut-engine/src/main/java/br/unb/cic/rv/pointcut/PointcutMatcher.java`, lines 175-202):
  - Drop `cp.isConstructor()` from `treatAsZeroOffset`; the predicate becomes `isStaticInvoke` alone.
  - Capture `targetRegister = regs[0]` for constructor when **both** `cp.isConstructor() == true` AND `mr.getName().equals("<init>")` agree (D3 defence-in-depth — the opcode-only predicate is insufficient because `invoke-direct` is also used for private non-constructor methods and `super.<init>` chaining). For virtual instance invokes (non-static, non-constructor), capture `targetRegister = regs[0]` unconditionally.
  - **API surface change (B2)**: `buildCallMatch` requires access to the surrounding instruction stream to peek `idx+1`. Two ripple changes follow:
    - **`Context` (`PointcutMatcher.java:321-336`)**: add field `final List<? extends Instruction> instructions` plus constructor param. Today `Context` carries only `instruction` (current) + `instructionIndex` + `totalInstructions`.
    - **`PointcutMatcher.match` public API (`PointcutMatcher.java:63-68`)**: add parameter `List<? extends Instruction> instructions` and forward it to the `new Context(...)` call. This is a public-API breaking change — grep for all callers (`grep -rn "PointcutMatcher\\b.*\\.match(" rvsec-instrumentation-dexlib2/` + any caller in `dex-mutator` / `advice-emitter`) and update each to pass the method's instruction list. The matcher operates over `org.jf.dexlib2.iface.Instruction`, NOT `BuilderInstruction` (B3 — typing as `BuilderInstruction` would improperly couple `pointcut-engine` to the `dexlib2-builder` module).
    - `buildCallMatch` reads `instructions` from `Context`; signature becomes `buildCallMatch(CallPC, MethodReference, int[] regs, boolean isStaticInvoke, List<? extends Instruction> instructions, int invokeIndex)`.
  - After matching, when `!match.isConstructor` and `invokeIndex + 1 < instructions.size()`, inspect `instructions.get(invokeIndex + 1)`; if opcode ∈ `{MOVE_RESULT, MOVE_RESULT_OBJECT, MOVE_RESULT_WIDE}`, cast to `OneRegisterInstruction` and place its destination register into the local `paramRegs` map under the synthetic key `"$return"`. The `paramRegs` map is the internal variable in `buildCallMatch` that is wrapped into the returned `Match.argBindings`, so the key surfaces as `match.argBindings.get("$return")` to all downstream consumers. For `MOVE_RESULT_WIDE` (long/double), the destination register pair occupies `vN+vN+1`; the synthetic key stores the low register `vN` — the wide-pair contiguity is the caller's responsibility (existing `RegisterShifter` INV-INS-26 already guarantees it for emitted code).
- [ ] 1.4 Re-run existing tests in `pointcut-engine/src/test/`: `mvn -pl pointcut-engine test`. Verify no caller of `PointcutMatcher.match(...)` is missing the new `instructions` argument (compilation surface).

## 2. Emitter binding resolution

- [ ] 2.1 Add a package-private static method `MonitorInvokeBuilder.resolveReturningRegister(Match match)` (`advice-emitter/src/main/java/br/unb/cic/rv/emitter/MonitorInvokeBuilder.java`):
  - Return `match.targetRegister` when `match.isConstructor == true && match.targetRegister >= 0` (reading the new boolean field added by task 1.2 — keeps `MonitorInvokeBuilder` free of `pointcut-engine` descriptor types).
  - Otherwise return `match.argBindings.get("$return")` (may be `null`; the synthetic key is populated by the `buildCallMatch` peek in task 1.3).
- [ ] 2.2 Rewrite `resolveBindings` (~L141-194):
  - Delete `map.putIfAbsent(p.getName(), 0)` entirely.
  - Replace with: `Integer reg = resolveReturningRegister(match); if (reg != null) map.put(p.getName(), reg);`
  - Apply the same pattern to `args(n)` and `target(n)` resolution — never inject literal `0` for unresolved names.
- [ ] 2.3 Rewrite `registersFor` (~L103-128) — replace `regs[i] = r != null ? r : 0;` with a guard that returns `null` (return type changes from `int[]` to `int[] | null`, i.e. `@Nullable int[]`) when any name is unresolved. Document the new contract in the method Javadoc: "returns `null` to signal the caller to skip this emission site; never throws". Callers MUST handle `null` by skipping the emission and incrementing `plansSkippedUnresolvedBinding`.
- [ ] 2.4 Extend the `DexWeaver.WeaveReport` record (nested record declared inside `dex-mutator/src/main/java/br/unb/cic/rv/mutator/DexWeaver.java` around L527) with a new `int plansSkippedUnresolvedBinding` component; update the only `new WeaveReport(...)` construction call in `DexWeaver` (around L406) to pass the new counter; update the report serialisation that surfaces in `instrument_results.json` to include the new field. Update every existing reference to the record's constructor that fails to compile after the component is added (run `mvn -pl dex-mutator compile` to discover them — known external consumer: `cli/BatchRunner.java:171-214` aggregates accessors of the record and serialises into `instrument_results.json`; verify the JSON serialiser handles the new component automatically or extend the writer).
  - **Thread-safety**: `DexWeaver` processes classes sequentially within a single `weaveAll(...)` call (no internal parallelism today). The new counter is incremented from the same thread that drives the per-class loop, so a plain `int` component reconstructed via `with` semantics (`new WeaveReport(..., oldCounter + 1)`) is safe. If a future change introduces parallel class weaving (Non-Goal), the counter must migrate to `LongAdder` and aggregation must be lifted out of the record — document this constraint as a comment on the field.
- [ ] 2.5 Update each of the five emitters (`BeforeEmitter`, `AfterEmitter`, `AfterReturningEmitter`, `AfterThrowingEmitter`, `StaticInitializationEmitter`) to handle a `null` return from `buildInvoke` — log `WARN` with advice name + binding name, increment the counter, skip the site. The funnel pattern means the change is mostly in the shared call-site of `MonitorInvokeBuilder.buildInvoke`.

## 3. Unit tests (cross-product + regression)

- [ ] 3.1 Create `pointcut-engine/src/test/java/br/unb/cic/rv/pointcut/PointcutMatcherConstructorTest.java` — JUnit5 `@ParameterizedTest`:
  - constructor with no move-result (no `$return`, `targetRegister = regs[0]`, arg offset 1)
  - virtual instance with `move-result-object` (captures `$return`, `targetRegister = regs[0]`, arg offset 1)
  - virtual instance without move-result (no `$return`, `targetRegister = regs[0]`, arg offset 1)
  - static with `move-result-wide` (captures `$return`, `targetRegister = -1`, arg offset 0) — assert that for `long`/`double` return types the synthetic key `$return` stores the low register `vN` of the wide pair `(vN, vN+1)`, and that the monitor signature's primitive type position resolves to `vN`
  - static without move-result (no `$return`, `targetRegister = -1`, arg offset 0)
  - private `invoke-direct` non-`<init>` (`cp.isConstructor()==false`, `targetRegister = regs[0]`, arg offset 1, `match.isConstructor == false`) — guards D3 against the false friend
  - **`super.<init>` chain** (`cp.isConstructor()==false` because the descriptor targets the user-class constructor, not the superclass; `match.isConstructor == false`, `targetRegister = regs[0]`, arg offset 1) — covers Codex risk-row "super-`<init>` chaining"
  - **descriptor-disagree edge case** (`cp.isConstructor() == true` but `MethodReference.name != "<init>"`, e.g. malformed descriptor) — assert `match.isConstructor == false`, `targetRegister = regs[0]` (virtual fallback path), no receiver-capture under constructor semantics. Validates D3 two-predicate gate in defence-in-depth direction.
- [ ] 3.2 Create `advice-emitter/src/test/java/br/unb/cic/rv/emitter/MonitorInvokeBindingTest.java` — JUnit5 `@ParameterizedTest` covering the cross-product `{Before, After, AfterReturning, AfterThrowing, StaticInit} × {constructor, virtual, static} × {args, target, returning, throwing}`. For each valid combination:
  - Build a synthetic `AdviceDescriptor` + `Match`.
  - Invoke `buildInvoke`.
  - Assert the emitted invoke's register array matches the monitor signature by **register-to-type correspondence**.
  - **Type-source independence (critical to close the gh52-smoke gap)**: the "expected type per register" MUST come from a hand-written `Map<Integer, String> expectedTypeByRegister` declared as a fixture constant (e.g. `Map.of(3, "[B", 0, "Ljava/lang/String;", 4, "Ljavax/crypto/spec/SecretKeySpec;")`), NOT from any helper that re-parses the monitor signature with the same logic the builder uses. Without an independent type source, the assertion validates internal self-consistency — exactly the failure mode by which the original bug passed gh52's smoke. Document the fixture's type table at the top of the test class with a short comment explaining the independence requirement.
  - **Enumerate invalid combinations explicitly** at the top of the test class (e.g. `StaticInit × constructor`, `Before × returning`, `AfterReturning × throwing`, …) so the implementer filters a priori rather than via `assumeTrue`-skip. After filtering, expected useful count is ~24 cases (design.md Testing Strategy).
- [ ] 3.3 Add the `SecretKeySpec.<init>` + `returning(spec)` case to `dex-mutator/src/test/java/br/unb/cic/rv/mutator/DexWeaverConstructorAdviceTest.java`. Assert the emitted invoke is `invoke-static {v3, v0, v4}, ...c1Event([B,String,SecretKeySpec)V`.
- [ ] 3.4 **Coverage extensions to existing tests** (close P1 gaps from adversarial review):
  - `MonitorInvokeBindingTest`: add cases for `args(name)` unresolved (paralela ao caso de `returning` unresolved já coberto): a parameter name appearing in `args(...)` but absent from `Match.argBindings` MUST trigger `registersFor` returning `null` and the counter must increment.
  - `MonitorInvokeBindingTest`: add a case for `returning(name)` combined with high-register allocation (`>v15`), forcing `Format35c → 3rc` escalation. Verify the register passed for the binding name is preserved through the escalation and matches the monitor signature.
  - `DexWeaverConstructorAdviceTest`: add `IvParameterSpec.<init>` case (documented in `docs/20260514_erro.md:§2.4` as one of the VerifyError-affected classes) to ensure parity with `SecretKeySpec.<init>`.
- [ ] 3.5 Create `validator/src/test/java/br/unb/cic/rv/validator/Layer3MandatoryTest.java`:
  - cryptoapp deviation with `--mandatory` → exit code `1` (NOT `2` — `Report.exitCode()` returns `0` or `1` only; see D6 in `design.md`)
  - cryptoapp full match with `--mandatory` → exit code `0`
  - non-cryptoapp APK without oracle → diagnostic mode, exit code `0` (no mandatory flag passed)
- [ ] 3.6 Run `mvn test` at the aggregator level; assert all new tests pass and no existing tests regress. Note: `Layer3MandatoryTest` (task 3.5) depends on the `--mandatory` flag introduced in tasks 4.1/4.2 — run 3.5 only after Group 4 lands. The original "Group 4 independent of 1-3" hint is inaccurate; 4.1/4.2 must precede 3.5.

## 4. Validator gate (must complete before task 3.5)

- [ ] 4.1 Extend the `layer3` subcommand of `ValidationCli` (`validator/src/main/java/br/unb/cic/rv/validator/ValidationCli.java`, around L208 — `@Command(name = "layer3", ...)`) with a new option `--mandatory` (boolean, default `false`). When the flag is set and the subcommand detects any deviation from the oracle for the validated APK set, the resulting `Report` MUST be constructed with `passed=false`, so `Report.exitCode()` returns `1` (current contract — `validator/Report.java:44-46` only emits `0` or `1`; see D6 in `design.md`). Without `--mandatory`, the subcommand emits `Report(passed=true)` on deviation (diagnostic mode unchanged). Subcommand structure is picocli; do NOT add a top-level CLI option.
- [ ] 4.2 `layer3` operates in two modes today: `analyze` (single-rep, `--apks` + `--oracles`) and `batch` (per-(apk,rep,tool,spec) CSV emission via `--batch --ajc-results --dexlib2-results --output-csv`). The runner (`run_phase5_validators.sh:114-117`) currently invokes `layer3 --batch`. Decision: `--mandatory` is honoured in **both modes**:
  - In `analyze` mode, `--mandatory` flips a per-APK deviation to `Report(passed=false)`.
  - In `batch` mode, `--mandatory` flips any per-(apk, spec) deviation found while writing the CSV to `Report(passed=false)`, in addition to emitting the full CSV (CSV emission is unconditional, regardless of pass/fail).
  - Document both behaviours in the subcommand `@Command(description=...)` text.
- [ ] 4.3 Update `rv-android/scripts/run_phase5_validators.sh`:
  - **Parameterise the hardcoded workspace paths** (L38-44): `THRESHOLDS` default, `REPO_ROOT`, `VALIDATOR_DIR` currently point to `rvsec-gh52-instr-dexlib2/...`. Replace with derivation from the script's own location: `SCRIPT_DIR=$(dirname "$(readlink -f "$0")"); REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"; VALIDATOR_DIR="$REPO_ROOT/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/validator"`. Allow override via env vars (`RVSEC_REPO_ROOT`, `RVSEC_VALIDATOR_DIR`) for backwards-compatibility with operators who maintain side-by-side clones.
  - Detect whether any APK in the dex result directory matches `cryptoapp` (e.g. `find "$DEX_DIR"/instrumented_apks -name 'cryptoapp*.apk' | head -1`).
  - When present, append `--mandatory` to the `layer3 --batch` invocation at L114. Document inline (comment in the script) that the flag triggers `Report(passed=false)` on cryptoapp deviation, propagating through the existing `run_layer` exit-code aggregator (`rc==1 → GATES_FAILED`).
  - **Add automatic `plansSkippedUnresolvedBinding` guard** (closes P1 from adversarial review — replaces task 5.5 manual check):
    ```bash
    # After cryptoapp instrumentation completes, before running validators:
    skipped=$(jq -r '.plansSkippedUnresolvedBinding // 0' "$DEX_DIR/instrument_results.json")
    if [[ "$skipped" -gt 0 ]] && find "$DEX_DIR/instrumented_apks" -name 'cryptoapp*.apk' -print -quit | grep -q .; then
      echo "[runner] FAIL: plansSkippedUnresolvedBinding=$skipped on cryptoapp run"
      exit 1
    fi
    ```
  - Propagate `ValidationCli` exit code via the existing `run_layer` aggregator. No additional plumbing needed.
- [ ] 4.4 Run the script against a recent successful result directory (no cryptoapp) and confirm it still exits `0` — regression check for parameterised paths and conditional `--mandatory`.

## 5. Build + cryptoapp smoke gate

- [ ] 5.1 Rebuild the Java aggregator from the parent `rvsec/rvsec-android/` directory: `cd ../rvsec/rvsec-android && mvn -pl rvsec-instrumentation-dexlib2 -am install -DskipTests=false` (or equivalent — module paths in this tasks file are relative to the aggregator root `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`, NOT to the `rv-android` uv workspace). Confirm `instr-cli.jar` is produced and auto-copied to `modules/rv-instrumentation-dexlib2/lib/` via the D9 auto-copy plugin.
- [ ] 5.2 Confirm the Python wrapper picks up the new jar: `uv run python -c "from rv_instrumentation_dexlib2.dexlib_instrumentation import DexlibInstrumentation; print(DexlibInstrumentation)"`.
- [ ] 5.3 Run the cryptoapp smoke gate (replace emulator management with `rv-experiment` — never invoke `emulator` manually, see CLAUDE.md):
  ```bash
  .venv/bin/rv-experiment run \
    --tools ape --timeout 300 --repetitions 1 \
    --apks-dir apks_examples \
    --instrumentation-variant dexlib2 \
    --specification-set jca \
    --name gh56-smoke
  ```
- [ ] 5.4 Run the validator with the new gate. The script requires **≥3 positional arguments** (`<ajc_results> <dex_results> <output_dir>`; see `scripts/run_phase5_validators.sh:30-33`). For a single-pipeline run, point the ajc slot at the same dex results (the script's Layer 2 diff degrades gracefully — see Layer 2 source for behaviour when ajc==dex):
  ```bash
  scripts/run_phase5_validators.sh results/gh56-smoke results/gh56-smoke results/gh56-smoke/validator-reports
  ```
  Assert exit code `0`, oracle 8 / 8 (with the two pivotal events `#7 KeyPair.<init>` and `#8 SecretKeySpec.<init>` explicitly captured — these are the events that exercise the bug path; see `spec.md` Cryptoapp Oracle requirement), zero `VerifyError` strings in the `.trace` files.
- [ ] 5.5 Automated check absorbed into task 4.3 (jq-based counter guard). Manual `cat instrument_results.json` step removed.

## 6. Sampled re-run + acceptance closure

- [ ] 6.1 **Stratified sample (replaces top-10-only — closes selection-bias gap)**: pick 9 APKs total from the 2026-05-08 campaign by `VerifyError` count from `experimento-20260508/` consolidated results, stratified as:
  - **Top-3** (highest VerifyError count) — hot-spots; high probability the bug fix exercises here.
  - **Median-3** (around the 50th percentile of the 116-APK affected slice) — tests "average" effect of the fix.
  - **Tail-3** (lowest non-zero VerifyError count, i.e. APKs where the bug manifested only sparsely) — surfaces patterns that may diverge from hot-spots (e.g. `args(name)` unresolved, R8-obfuscated `<init>`, Tink/Okio internals).
  Document the 9 chosen APKs by package name + VerifyError count in `RISKS.md`.
- [ ] 6.2 Run a single-timeout (300s), single-repetition campaign on the 9 APKs with `--instrumentation-variant dexlib2` and the JCA spec set. **Also re-run the same 9 APKs through the pre-fix instrumentation** (checkout the parent commit of the gh56 implementation, run identical command, save to `results/gh56-baseline-9apks`) to obtain a paired delta.
- [ ] 6.3 Three assertions on the post-fix run:
  - Grep every `.trace` file for `VerifyError`. Confirm count is `0`.
  - **Event-count delta**: for each of the 9 APKs, count `RVSEC-VIOL` events in pre-fix vs post-fix traces; expect monotone increase (post ≥ pre) — a decrease signals regression in exploration, not just absence of `VerifyError`. Document the per-APK delta table in `RISKS.md`.
  - **Coverage delta**: same logic for `cov_method` from `summary.csv`; expect non-decrease (post-fix should not lose coverage relative to pre-fix).
  If `VerifyError > 0`, triage: if the failure family is binding-related, expand the change; if orthogonal (e.g. Format35c `>v15`), record in `RISKS.md` as a deferred residual and proceed.
- [ ] 6.4 Document the full-campaign re-run decision in `RISKS.md`: cost (~85 h GCP for 4 VMs × 18.267 tasks), benefit (RQ3 representativeness for the ASE journal). Default: defer full re-run; ship the change with the sampled slice as the acceptance evidence.
- [ ] 6.5 Record an Architecture Decision Record at `openspec/changes/gh56-instr-binding-correctness/ADR-NAMED-BINDING-CONTRACT.md` capturing D1-D7 with concrete examples (D1: bindings by name; D2: `$return` in `argBindings`; D3: two-predicate constructor gate; D4: cryptoapp-only mandatory gate; D5: observable `plansSkippedUnresolvedBinding`; D6: `Report(passed=false) → exit 1`, no new exit code; D7: `List<? extends Instruction>` propagation through `Context`).
- [ ] 6.6 Record a risk register at `openspec/changes/gh56-instr-binding-correctness/RISKS.md` covering the seven risks in `design.md §"Risks / Trade-offs"` (Fix#1 false-friend; Fix#2 coincidence-on-`v0`; ape exploration false positive; new VerifyError family in stratified slice; full-campaign re-run cost; circular type-matching in fixture; 8/8 binary gate ambiguity vs wrapper regression — and the `IvParameterSpec` coverage caveat).
- [ ] 6.7 Run `/rv-qa-lint-fix` on any touched Python file (validator scripts, if applicable).
- [ ] 6.8 Run `/rv-verify` on `rv-instrumentation-dexlib2` (Python module) and confirm all tests pass; run `mvn test` at the Java aggregator and confirm zero regressions.
- [ ] 6.9 Invoke `/rv-code-reviewer` via the Skill tool to review the Java diff and the Python wrapper changes.
- [ ] 6.10 Run `/opsx:verify` to confirm implementation matches the delta spec.
- [ ] 6.11 Update GitHub Issue #56 acceptance checkboxes (tick each criterion as it is met).
- [ ] 6.12 Run `/opsx:archive` to sync the delta spec into `openspec/specs/instrumentation/spec.md` and move the change to `archive/`.
- [ ] 6.13 Commit with `closes #56` in the final commit message. Move the Kanban card to Done via `gh project item-edit`.
