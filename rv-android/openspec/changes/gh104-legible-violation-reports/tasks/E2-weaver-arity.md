# Group 3 — E2: weaver `args()` arity

Tracked checkboxes: `tasks.md` §3. Wave 1; Java only (sibling reactor); disjoint from every other group. Process prerequisite (gh100 tasks 7.5/7.6) closed on 2026-08-16.

## Subagent brief

Read `design.md` D-6, the `instrumentation` delta (`Requirement: Wrapper Grouping Honours args() Arity`, INV-INS-122) and `openspec/changes/gh100-weaver-emission-fidelity/design.md` D-B1 (why wrappers merge). Red test first, commit the red output, then the repair. Never run an emulator. Run `mvn -q test` inside the submodules, not at the reactor root.

## Files (all under `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`)

| file | lines | what |
|---|---|---|
| `advice-emitter/src/main/java/br/unb/cic/rv/emitter/WrapperEmitter.java` | 758 | grouping loop `:246-274` (write `:270-273`); `firstCallTarget :507-525` ignores `ArgsPC`; `expandCallTarget :326-403` (varargs `:334`, prefix `:378`, arity `:383-387`); `appendWrapperMethod :650-699` fires every advice × monitorCall (`:690-696`); `buildMonitorArgs :701-738`. **Edit**: read the advice's `ArgsPC` from its parsed expression; compute arity from `types()` with trailing `..` = "at least"; in the loop admit the advice iff no `args()` or arity-compatible with `cc.paramFqns.size()`; count exclusions; return them (new small record `EmitResult { List<WrapperEntry> wrappers; int advicesExcludedByArity; }`) |
| `pointcut-engine/.../PointcutMatcher.java` | — | `:268-306` binding-form arity (`matchArgs`, `trailingRest`/`headCount` `:280-286`) — **reuse the helpers, do not edit the inline path** (out of scope, `before` advices bypass wrappers `WrapperEmitter.java:161-163`) |
| `pointcut-engine/.../PointcutExpressionParser.java` | — | `:243-246` — `names()` drops `..`; that is why `types()` is used |
| `pointcut-engine/.../ArgsPC.java` | — | `:49-56` `hasTypeConstraint`, `types()` |
| `cli/src/main/java/br/unb/cic/rv/cli/BatchRunner.java` | — | `:199-201` `counts.put("wrappersGenerated", …)` right after `WrapperEmitter.generate` — add `advicesExcludedByArity` beside it (**not** in `DexWeaver.WeaveReport :978-1008`) |
| `advice-emitter/src/test/java/br/unb/cic/rv/emitter/WrapperMergeTest.java` | 129 | host of the new tests (fixture `adviceOver()` already builds `getInstance(String) && args(algorithm)`; uses the no-index `generate(descriptor, dir)` → `literalFallback`) |
| `cli/src/test/.../ResultsJsonReportingTest.java` | 95 | assert the counter key reaches the JSON |
| regression to keep green | `EmissionParityTest` 135, `EmissionCardinalityTest` 155, `WrapperEmitterTest` 785, `WrapperRegistryGuardTest` 78 (dex-mutator), `MonitorCallsPremiseContractTest` 115 (validator) |

Python: `modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/dexlib_instrumentation.py` `_parse_results_json` (surfaces counters into `weave_counts`) + `modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py`.

## The rule (verbatim source: `docs/20260815_javamop_mensagens_FINAL_analise_lacunas.md:674-684`)

1. Absence of an `args()` clause means "no positional constraint" — never filter, never treat as length 0.
2. Read the length of `ArgsPC.types()`, not `names()`; a trailing `..` means "at least".
3. Filter in the grouping loop of `WrapperEmitter` — the only place advice and concrete overload coexist and `cc.paramFqns.size()` is known.

## Facts to assert in tests (measured on `results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json`, 2026-08-08, byte-identical to `results/gh92_e2e2/monitors/`)

- 115 advices; 97 `after` with `call()`, of which 62 carry `args()`; 18 `before`.
- Exactly **16** `after` advices have a first `call()` with ≥ 1 parameter and no `args()`: `CipherInputStreamSpec_c1`†, `CipherOutputStreamSpec_c1`†, `CipherOutputStreamSpec_w1`, `CipherSpec_wkb1`, `CipherSpec_f2`, `HMACParameterSpecSpec_c`†, `KeyStoreSpec_gk1`, `MacSpec_update`, `MacSpec_f1`, `MessageDigestSpec_update`, `MessageDigestSpec_d2`, `SecureRandomSpec_setSeed1`, `SecureRandomSpec_genSeed`, `SecureRandomSpec_ints`, `SSLContextSpec_init`, `SSLContextSpec_engine` († = constructor advice; never reaches the wrapper path, `WrapperEmitter.java:251-256`; the other 13 must survive).
- Today `TrustManagerFactory_getInstance(String p0)` fires `g1Event`, `g2Event`, `g3Event` (`results/gh101_group8_jca_frozen_control/monitors/mop/MonitorWrappers.java:538-544`) — the positive case: `g2` (`args(alg, provider)`) must not be in the one-argument wrapper after the repair.
- gh100 census for context: `wrappersGenerated 96→84`, 12 wrappers previously discarded (`gh100/design.md:122`).

## Commands

```bash
cd ../rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/advice-emitter && mvn -q test -Dtest=WrapperMergeTest   # red first, then green
cd ../cli && mvn -q test -Dtest=ResultsJsonReportingTest
cd ../dex-mutator && mvn -q test; cd ../validator && mvn -q test
# re-weave the frozen descriptor and read the counters (instr-cli, no device):
java -jar <path to instr-cli.jar> instrument --results-json ... (see BatchRunner usage in gh100 tasks 1.x)
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec && mvn -q install -DskipTests -DskipMopAgent=true   # ~12 min; refreshes rv-android/lib/ and modules/rv-instrumentation-dexlib2/lib/instr-cli.jar
```

## Acceptance

- Two new tests red before, green after; red output committed under `openspec/changes/gh104-legible-violation-reports/evidence/e2_red.txt`.
- `advicesExcludedByArity` present in `instrument_results.json` and in `weave_counts`; on the frozen `jca` descriptor its value is recorded in `evidence/e2_reweave.md` next to `wrappersGenerated`.
- All listed regression tests green; `/rv-verify rv-instrumentation-dexlib2` run and result recorded.
- Delta spec INV-INS-122 satisfied; no change to `PointcutMatcher` inline path.
