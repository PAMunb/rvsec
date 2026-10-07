## Context

GitHub Issue #121; proposal in `proposal.md`; rationale (Portuguese) in `docs/20261007_variante_a_carimbo_handler.md`. Requirements touched: FR02 (APK instrumentation), NFR04 (resilience), NFR05 (configurability), NFR08 (reproducibility).

APE-RV keys widget guidance by `(activity, resource-id, event)`. In E6, 58.6 % of the clicks were on nodes without a resource-id, and Compose-only apps had no usable key at all. The decision taken on 07/10 (Variante A) is that the instrumented app itself writes the handler class bound to each clickable node into the node's accessibility extras, for View and for Compose, behind an option that is off by default.

Two code bases change:

- **Java, `rvsec/rvsec-android/rvsec-instrumentation-dexlib2`** (Maven, part of the root `rvsec` reactor). A prototype of the whole Java side exists, uncommitted, in the worktree `worktrees-gator/stamp` (branch `wip/instr-stamp`): `dex-mutator/.../StampWeaver.java`, `monitor-builder/.../StampSourceEmitter.java`, the resource `monitor-builder/src/main/resources/br/unb/cic/rv/builder/stamp/RvsecStamp.java` (536 lines), the `cli` wiring (`InstrumentationCli`, `EffectiveConfig`, `ConfigResolver`, `BatchRunner`), and two test classes. Its author measured on 07/10 that, with the option off, parceltracker's 10 DEX files are byte-identical to the corpus instrumentation, and that four APKs with the option on ran 120 s under APE through rv-platform with no crash or `VerifyError`, with real app lambdas in the Compose stamp of parceltracker. Those numbers are a relay of the prototype report, not re-measured here; the verification group of `tasks.md` re-measures them on the ported code.
- **Python, `modules/rv-instrumentation-dexlib2`**. The wrapper builds `instr-cli`'s argument list in `DexlibInstrumentation._common_cli_args` (`dexlib_instrumentation.py:459`) and hands the subprocess a fixed environment in `_build_subprocess_env` (`:633`; `PATH`, `HOME`, `JAVA_HOME`, `ANDROID_HOME`, `RVSEC_HOME`, INV-EXP-30). An environment variable set by a caller therefore never reaches `instr-cli`, which is why the option has to become a config field and an argument.

Two more places change because the campaign has to produce and check the stamp through the normal pipeline:

- **`rv-experiment`** builds the `dexlib2` configuration itself (`ExperimentConfig.get_dexlib_instrumentation_config`, `modules/rv-experiment/src/rv_experiment/config.py`), so it needs a switch of its own to set `stamp_handlers` (D11).
- **The capture allowlist** (`LogcatManager.default_tags`, `modules/rv-android-core/src/rv_android_core/util/android/logcat_manager.py`) has to admit `RVSEC-BIND`, or `adb logcat -s` discards the stamp's verification log on the device (D12).

Constraint from the deadline: the corpus instrumentation for the Study 03 campaign is meant to use the stamp, so the port has to keep the prototype's measured behaviour and change only what the specs require.

## Architecture

```
rv-experiment run --stamp-handlers | RV_STAMP_HANDLERS=true      (direct instr-cli: --stamp-handlers | RVSEC_STAMP_HANDLERS=true)
        │ ExperimentConfig.stamp_handlers → get_dexlib_instrumentation_config
        │ DexlibInstrumentationConfig(stamp_handlers=True)
        ▼
rv-instrumentation-dexlib2 (Python)
  _common_cli_args ──► argv: ... --stamp-handlers
  _build_subprocess_env (unchanged)
        │ subprocess: java -jar lib/instr-cli.jar instrument|batch ...
        ▼
instr-cli (Java)
  InstrumentationCli --stamp-handlers ─► ConfigResolver ─► EffectiveConfig.stampHandlers
  BatchRunner.runPipeline, per APK:
    4a  DexWeaver (advice)                      [unchanged]
    4a' StampWeaver.weave(dex, mutator::forMethod)   only if stampHandlers
          ├─ View setters: invoke-virtual → invoke-static mop.RvsecStamp.<setter>
          └─ Compose: insert invoke-static mop.RvsecStamp.composeNode after populate…
    4b  CoverageWeaver                          [unchanged]
    5a  CoverageSourceEmitter.emit              [unchanged]
    5a' StampSourceEmitter.emit  (on) | StampSourceEmitter.remove (off)
    5b  MonitorBuilder: javac + d8 → monitor DEX (now holds mop.RvsecStamp when on)
    6   MultidexMerger, sign
        │
        ▼
instrumented APK ──► device: RvsecStamp.Delegate / composeNode
                       → AccessibilityNodeInfo extras rvsec.click / rvsec.longClick
                       → logcat RVSEC-BIND ──► captured (default_tags, 5th tag) ──► task .logcat
                       → extras read via UiAutomation:
                           · in this change: StampProbe (app_process) as the tool of a short rv-platform task
                           · later, separate change: APE-RV
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `InstrumentationCli` (`cli/.../InstrumentationCli.java`) | Declares `--stamp-handlers` / `--no-stamp-handlers` (`Boolean`, `negatable`, scope `INHERIT`) | argv | `Boolean stampHandlers` (null when absent) |
| `ConfigResolver` (`cli/.../ConfigResolver.java`) | Resolves the option to a boolean: the option when given; absent → `RVSEC_STAMP_HANDLERS` (`true`, case-insensitive); otherwise `false` | parsed args, environment | `EffectiveConfig.stampHandlers` |
| `EffectiveConfig` (`cli/.../EffectiveConfig.java`) | Record field `boolean stampHandlers` between `enableCoverage` and `keystorePath` | — | — |
| `BatchRunner` (`cli/.../BatchRunner.java`) | Builds `StampWeaver` when on; runs step 4a′; merges the six counters; emits or removes the helper source before `MonitorBuilder` | `EffectiveConfig`, APK | woven DEX, `weaveCounts` |
| `StampWeaver` (`dex-mutator/.../StampWeaver.java`) | Selects and rewrites setter sites; inserts the Compose call; counts | `DexFile`, `Function<Method, MutableMethodImplementation>`, `InheritanceResolver` | `StampReport(click, longClick, delegate, compose, invokeSuperSkipped, ownerNotView)` |
| `StampSourceEmitter` (`monitor-builder/.../StampSourceEmitter.java`) | Writes `mop/RvsecStamp.java` from the classpath resource; removes stale source and class files | monitor source dir, classes dir | file / deletions |
| `mop.RvsecStamp` (resource `RvsecStamp.java`) | Runtime helper: setter helpers, stamp delegate, `composeNode`, `RVSEC-BIND` log | `View` + listener / `(AccessibilityNodeInfoCompat, SemanticsNode)` as `Object` | node extras, log lines |
| `DexlibInstrumentationConfig.stamp_handlers` (`modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/config.py`) | Python switch, default `False` | caller | — |
| `DexlibInstrumentation._common_cli_args` (`.../dexlib_instrumentation.py`) | Appends `--stamp-handlers` when the field is true | config | `List[str]` |
| `rv-experiment run --stamp-handlers/--no-stamp-handlers` (`modules/rv-experiment/src/rv_experiment/__main__.py`) | Resolves flag > `RV_STAMP_HANDLERS` > `False`; aborts with the `ajc` variant | argv, environment | `ExperimentConfig.stamp_handlers` |
| `ExperimentConfig.stamp_handlers`, `get_dexlib_instrumentation_config` (`modules/rv-experiment/src/rv_experiment/config.py`) | Carries the policy; sets `DexlibInstrumentationConfig.stamp_handlers`; recorded in `experiment_config.json` | resolved bool | config |
| `ENV_STAMP_HANDLERS` (`rv_android_core/constants.py`) | Registry constant `"RV_STAMP_HANDLERS"` | — | — |
| `TAG_RVSEC_BIND` (`rv_android_core/util/logging/constants.py`), `LogcatManager.default_tags` | The single host-side spelling of the tag; fifth baseline tag | — | `[RVSEC, RVSEC-COV, ApeRvHb, RVSEC-OCC, RVSEC-BIND]` |
| `StampProbe` (`experimento-smk121/probe/StampProbe.java`, built into `probe.jar` with `javac` + `d8`) | Connects to `UiAutomation` as APE-RV does (`app_process`), as the only client; dumps the first screen, then clicks each of its clickable nodes in turn, dumps the screen reached and goes back (one navigation level) | device | probe dumps, one per step |
| `run_probe.py` (`experimento-smk121/scripts/`) | Registers a probe tool in `ToolRegistry` in-process and runs `rv-platform` once; the tool launches the app, runs the probe, saves its dumps beside the task logcat | stamped APKs | probe dumps, logcats |
| `check_delivery.py`, `dexcmp.py`, `dexnorm.py` (`experimento-smk121/scripts/`) | Compare probe dumps with `RVSEC-BIND` lines; compare DEX files raw and normalised | dumps, logcats, APKs | reports |

## Mapping: Spec → Implementation → Test

| Requirement / invariant | Implementation | Test |
|-------------|---------------|------|
| INV-INS-174 (off is byte-identical; stale helper removed; no `stamp*` keys; resolution with the environment fallback) | `ConfigResolver` (option, then `RVSEC_STAMP_HANDLERS`), `BatchRunner` step 4a′ guard and step 5a′ `remove`, `StampSourceEmitter.remove` | `StampSourceEmitterTest.removeDeletesTheSourceAndOnlyTheStampClasses`; new `ConfigResolverStampTest` (`--stamp-handlers` → true, `--no-stamp-handlers` → false, absent → the test JVM's `RVSEC_STAMP_HANDLERS`); the fallback with the variable set by real `instr-cli` runs (tasks 9.3), since a JUnit test cannot set the process environment and no test-only seam is added; new `BatchRunner` test that an off run writes no `stamp*` key; offline byte comparison of parceltracker against the pre-change `instr-cli.jar` (D13) |
| INV-INS-175 (only stamp sites differ; MOP counters equal) | `StampWeaver.weave` uses `InstructionInjector.replaceInvoke` (size-stable) and one `addInstruction` per Compose site | `StampWeaverTest.viewSettersAreRoutedAndOtherSitesLeftAlone`, `composeNodePopulationIsFollowedByTheStampCall`; offline normalised dexdump diff on aegis on/off (verification group) |
| INV-INS-176 (candidate selection and counting) | `StampWeaver.candidateRef`, `isView`, `isComposePopulate`, `composeCall` | `StampWeaverTest` (extend: one `invoke-super` and one non-View owner counted; `/range` forms; renamed Compose owner → 0) |
| INV-INS-177 (original call once; no throw) | `RvsecStamp.setOnClickListener`, `setOnLongClickListener`, `setAccessibilityDelegate`, `composeNode` | Source-level: `StampSourceEmitterTest.theSourceCompilesAgainstAndroidJarAtJava8`; runtime: device run (verification group). No JVM unit test of the runtime logic: `android.jar` stubs throw, and Robolectric is not a dependency |
| INV-INS-178 (delegate forwarding and extras) | `RvsecStamp.Delegate`, `stamp`, `installed`, `composeStamp`, `composeHandler` | Device run: `RVSEC-BIND` lines and no crash; extras delivery to `UiAutomation` is a known, unverified limit |
| INV-INS-179 (`RVSEC-BIND` lines) | `RvsecStamp.log`, `COMPOSE_LOGGED` | Device run; the lines reach the task `.logcat` through the fifth capture tag |
| Delivery to a `UiAutomation` client (instrumentation "Handler Stamp on the Accessibility Node") | `RvsecStamp.Delegate`, `composeNode` | Probe run (D14): every node with an `RVSEC-BIND` line in the probed window is read with the same handler, View and Compose |
| INV-CORE-53, INV-CORE-67, INV-CORE-37/38, INV-PLT-21 | `TAG_RVSEC_BIND`, `default_tags` | `test_logcat_manager.py` (five-tag command, `test_bind_tag_declared_once`), `rv-platform` `test_logcat.py`, `rv-coverage` `test_bind_lines_change_no_parsed_value` + fixture |
| INV-EXP-40 | `rv-experiment` flag, `ExperimentConfig.stamp_handlers`, `get_dexlib_instrumentation_config`, `ENV_STAMP_HANDLERS` | `rv-experiment` tests: default off, flag on, variable on, negative flag wins, `ajc` aborts, config forwarded, `experiment_config.json` records it; `check_env_vars_drift.py` clean |
| INV-INS-180 (Python argv and env) | `DexlibInstrumentationConfig.stamp_handlers`, `_common_cli_args` | new `test_common_cli_args_forwards_stamp_handlers`, `test_common_cli_args_unchanged_when_stamp_off`, `test_subprocess_env_unchanged_with_stamp_on` in `modules/rv-instrumentation-dexlib2/tests/test_dexlib_instrumentation.py` |
| Modified "DEX-Native APK Instrumentation Pipeline" | as INV-INS-180 | as INV-INS-180 |
| Known limits | documented in spec and module docs | — |

## Goals / Non-Goals

**Goals:**
- Port the prototype's Java side from `wip/instr-stamp` into the `rvsec` tree with the behaviour the specs fix, and with the one correction of D4.
- Forward the option from the Python wrapper as an explicit argument.
- Keep the off output byte-identical to today's, so the existing instrumented corpus and every published measurement stay reproducible.
- Leave the instrumented app's behaviour and the monitors' events unchanged when the option is on.
- Let a campaign ask for the stamp through `rv-experiment`, by flag or by `RV_*` variable, with the policy recorded in the run.
- Capture the stamp's verification log in every run.
- Show on a device that a `UiAutomation` client receives the stamp, View and Compose.

**Non-Goals:**
- APE-RV reading `rvsec.*` extras, `MopData` keyed by handler class, and the derive table handler class → distance (separate changes: `ape` repository; derive in `aperv-tool`).
- The static analysis that yields per-handler distance (#120).
- Reading `AppCompatViewInflater$DeclaredOnClickListener#mMethodName`; stamping `AlertDialog` buttons or `Preference` rows; refining library dispatchers (toolbar, menu, `SearchView`). Possible follow-ups, listed as known limits.
- The `ajc` variant.

## Decisions

**D1 — A separate weave pass, not the wrapper registry.** The advice weaver already replaces call sites through `findWrapperReplacement`, but its registry is keyed to `MonitorWrappers` and gated by the MOP `commonPointcut` class filter. Registering the setters there would make the stamp depend on the descriptor and on that gate, and would mix an observation for the GUI tool into the monitors' wrappers. `StampWeaver` reuses only `InstructionInjector.replaceInvoke` and runs over the same mutable bodies (`mutator::forMethod`). *Alternative:* emit the setters as synthetic advices in the descriptor. Rejected: it changes the descriptor, hence the MOP weave, which breaks INV-INS-175.

**D2 — Pass order: after the advice weave, before the coverage weave.** The stamp sees the invokes as the app compiled them, plus whatever the advice weave left, and coverage instrumentation at method entry is unaffected by a size-stable rewrite. *Alternative:* before the advice weave. Rejected: an advice whose pointcut matched a setter would then see `mop.RvsecStamp` instead of the framework call.

**D3 — The helper is a fixed Java source compiled into the monitor DEX.** It is emitted into `--monitor-src-dir` and built by `MonitorBuilder`, like `mop.Coverage`. This keeps one build path, compiles against the same `android.jar` as the monitors, and places the helper outside the app DEXes, whose method-id count goes down because owner-specific setter references are replaced by at most four helper references (aegis `classes18`: 65,458 → 65,444, relayed). *Alternative:* a prebuilt `.dex` or jar under `lib/`. Rejected: a second artifact to version and keep in sync with the toolchain.

**D4 — `instr-cli` keeps the environment fallback.** With no option, `ConfigResolver` reads `RVSEC_STAMP_HANDLERS`; `true` (case-insensitive) turns the stamp on, and `--no-stamp-handlers` wins over it. This is the prototype's behaviour, kept by the researcher's decision (07/10) for direct use of `instr-cli`. A run turned on by the variable is still recognisable from its output, because the six `stamp*` counters exist in `weaveCounts` only when the stamp is on (D6). The variable does not reach `instr-cli` through the Python wrapper (D5); the pipeline's switch is `rv-experiment`'s own (D11). *Alternative:* the option alone. Rejected by the researcher.

**D5 — Python: one config field, one argument, no environment.** `stamp_handlers: bool = False` on `DexlibInstrumentationConfig`; `_common_cli_args` appends `--stamp-handlers` when it is true and nothing otherwise, so the off argv is unchanged and the Java default carries the meaning. Since both `instrument` and `batch` build their argv through `_common_cli_args`, both carry the option. `_build_subprocess_env` stays as it is (INV-EXP-30). *Alternative:* add `RVSEC_STAMP_HANDLERS` to the forwarded keys. Rejected: the wrapper's environment is fixed (INV-EXP-30), and the pipeline has its own switch (D11).

**D6 — Counters exist only when the option is on.** Writing six zero counters on every off run would change `instrument_results.json` for every APK and defeat the off-is-today guarantee at the JSON level. `InstrumentationResults.weave_counts` is a free `Dict[str, Dict[str, int]]`, so the keys pass through Python without a model change.

**D7 — Any owner assignable to `View`, library code included.** Many clickable views get their listener inside androidx or Material code (adapters, toolbars, chips). Restricting to app packages would leave those nodes without a stamp. The cost is the library-dispatcher limit: the stamp names the library's listener where the library dispatches.

**D8 — Compose form 2: insert after node population.** The alternative, rewriting `Modifier.clickable(…)` call sites to add a `testTag`, depends on Kotlin-mangled names that change between Compose versions, needs `testTagsAsResourceId` at the root, and overwrites an app's own `testTag`. Form 2 is one exact-match site per APK, needs no Compose type at compile time, and fails closed: a renamed library gets no stamp and no change. The prototype checked it on parceltracker (Compose 1.7.8).

**D9 — Stale helper removal when off.** `--monitor-src-dir` and `<work-dir>/monitor-build` are shared across a batch and across runs, and `MonitorBuilder` compiles every `.java` it finds. An on run followed by an off run would otherwise ship the helper in the off APK's monitor DEX. `StampSourceEmitter.remove` deletes `mop/RvsecStamp.java`, `RvsecStamp.class` and `RvsecStamp$*.class`, and nothing else of `mop/`.

**D10 — The `RVSEC-BIND` log is part of the helper, not a separate option.** It lets the stamp be checked from logcat without a tool change, and the line is written only when a stamp value changes (measured 18–231 lines per 120 s run on four APKs, relayed). The platform captures it (D12).

**D11 — `rv-experiment` gets a flag and an `RV_*` variable.** `rv-experiment run` declares `--stamp-handlers/--no-stamp-handlers` with `envvar` resolution through `ENV_STAMP_HANDLERS` (`RV_STAMP_HANDLERS`), as `--strip-build-type-suffix` and `--logcat-diagnostics` do: flag > variable > default `False`. The resolved value goes into `ExperimentConfig.stamp_handlers`, which `get_dexlib_instrumentation_config` forwards to `DexlibInstrumentationConfig.stamp_handlers`, and into `experiment_config.json`. The variable is registered in the core registry, documented, and admitted by `validate_env_vars.sh` (ADR 0001). With `--instrumentation-variant ajc` and the flag on, the command aborts before pre-processing, naming the flag and the variant (INV-EXP-37): the `ajc` variant has no stamp, and a silent no-op would leave a campaign without the stamp it asked for. With `--skip-instrument`, the flag has no effect on the APKs consumed, which were instrumented earlier. *Alternative:* instrument the corpus outside `rv-experiment`. Rejected by the researcher: the run that instruments the corpus is the run that records its provenance.

**D12 — `RVSEC-BIND` is the fifth baseline tag.** `TAG_RVSEC_BIND = "RVSEC-BIND"` is declared once in `rv_android_core/util/logging/constants.py`, and `default_tags` becomes `[TAG_RVSEC, TAG_RVSEC_COV, TAG_APERV_HEARTBEAT, TAG_RVSEC_OCC, TAG_RVSEC_BIND]`. The lines are the app-side record of the stamp: the delivery check (D14) compares the probe's view with them, and an offline analysis can join clicks to handlers by the heartbeat before each line. The cost is 18–231 lines per 120 s run on four APKs (relayed from the prototype), and nothing for an APK instrumented without the stamp. `rv-coverage` dispatches on the exact tag, so the lines are counted as `lines_other_tag` (INV-CORE-67). *Alternative:* an in-process wrapper that extends the tag list only for the check, as the prototype did. Rejected by the researcher: the campaign needs the lines too.

**D13 — Off byte-identity is checked against the instrumenter without this change.** The reference is the `instr-cli.jar` currently in `modules/rv-instrumentation-dexlib2/lib/`, built from `HEAD` without the stamp code, copied aside before the build of this change replaces it. The same APK (`parceltracker`) is instrumented with that jar and with the new jar without the option, with the same descriptor, monitors, runtime jars and toolchain, and every `classes*.dex` is compared byte for byte. *Alternative:* the APK of the instrumented corpus. Rejected: it was produced with other runtime jars (the `ErrorCollector` of gh119 is newer than it), so it differs for reasons unrelated to this change.

**D14 — Delivery is checked by a probe that reads the tree as APE-RV does and navigates one level.** `StampProbe.java` (in `experimento-smk121/probe/`) is compiled against `android-30/android.jar` and dexed with `d8` into `probe.jar`, pushed to `/data/local/tmp`, and run with `app_process`, the mechanism APE-RV uses to obtain a `UiAutomation`; where that API is hidden, the probe reaches it by reflection, following the APE-RV jar. The probe is the task's tool and the only `UiAutomation` client on the device: no APE or APE-RV runs in that task. It dumps the first screen, then, for each clickable node of that screen up to a cap of 20, performs `ACTION_CLICK` on the node, waits for the screen to settle, dumps the screen reached, and goes back with `GLOBAL_ACTION_BACK`, relaunching the launcher activity when the app has left the foreground. Each dump starts with a header holding the device wall-clock time (the logcat `threadtime` clock) and the step (`start`, or the clicked node's class, view-id and bounds), followed by one line per node of the active window: class, view-id resource name, screen bounds, and the `rvsec.click` / `rvsec.longClick` extras. One level reaches the screens a first click opens, where most listeners are bound, without becoming an explorer. `run_probe.py` registers a probe tool in `ToolRegistry` in-process and runs `rv-platform` once over the stamped APKs, so `rv-platform` keeps managing the emulator and the capture; nothing under `modules/` changes for the probe. The tool launches the app, runs the probe, and saves the dumps beside the task's `.logcat`. `check_delivery.py` then pairs each node of each dump with the last `RVSEC-BIND` line for it before that dump's time — by view-id resource name for a View line, by screen bounds for a Compose line — and passes when every paired node shows the same handler, with at least one View and one Compose node paired across the four APKs. *Alternative:* wait for the APE-RV change. Rejected by the researcher: whether the stamp is delivered decides whether this change is worth consuming, so it is checked here. *Alternative:* a probe that reads the first screen only. Rejected by the researcher: one navigation level covers the screens behind the first clicks at little extra cost.

## API Design

### Java

```java
// InstrumentationCli
@Option(names = "--stamp-handlers", negatable = true, scope = INHERIT,
        description = "Route View.setOnClickListener / setOnLongClickListener / "
                    + "setAccessibilityDelegate call sites to mop.RvsecStamp ... Default off.")
Boolean stampHandlers;                       // null when absent

// ConfigResolver: stampHandlers = Boolean.TRUE.equals(args.stampHandlers)

// EffectiveConfig (record): ..., boolean enableCoverage, boolean stampHandlers, Path keystorePath, String logLevel

public final class StampWeaver {
    public StampWeaver(InheritanceResolver inheritance);
    public StampReport weave(DexFile dex, Function<Method, MutableMethodImplementation> forMethod);
    public record StampReport(int clickSites, int longClickSites, int delegateSites,
                              int composeSites, int invokeSuperSkipped, int ownerNotView) {}
}
```
`weave` pre: `forMethod` returns the body shared with the other weaves of the same DEX. Post: INV-INS-175/176. A method whose original body has no candidate is not materialised.

```java
public final class StampSourceEmitter {
    public static Path emit(Path outputDir) throws IOException;            // writes <outputDir>/mop/RvsecStamp.java
    public static void remove(Path sourceDir, Path classesDir) throws IOException;
}
```
`emit` throws `IllegalStateException` when the resource is missing from the jar (a build defect).

```java
package mop;
public final class RvsecStamp {
    public static final String TAG = "RVSEC-BIND";
    public static final String KEY_CLICK = "rvsec.click";
    public static final String KEY_LONG_CLICK = "rvsec.longClick";
    public static void setOnClickListener(View v, View.OnClickListener l);
    public static void setOnLongClickListener(View v, View.OnLongClickListener l);
    public static void setAccessibilityDelegate(View v, View.AccessibilityDelegate d);
    public static void composeNode(Object infoCompat, Object semanticsNode);
}
```
Contracts: INV-INS-177/178/179.

### Python

```python
class DexlibInstrumentationConfig(BaseModel):
    ...
    stamp_handlers: bool = Field(
        default=False,
        description=(
            "Pass --stamp-handlers to instr-cli: route View setter call sites and "
            "Compose node population to mop.RvsecStamp, which writes the handler "
            "class into the node's accessibility extras. Off reproduces the "
            "instrumentation without the stamp byte for byte."
        ),
    )

def _common_cli_args(self, output_dir: Path) -> List[str]:
    ...  # unchanged list
    if self.config.stamp_handlers:
        args.append("--stamp-handlers")
    return args
```

## Data Flow

1. A caller builds `DexlibInstrumentationConfig(stamp_handlers=True, ...)`; `DexlibInstrumentation` builds argv with `--stamp-handlers`.
2. `instr-cli` resolves `stampHandlers=true`. For each APK, after the advice weave of each DEX, `StampWeaver` rewrites setter sites and inserts Compose calls on the shared bodies; the six counters are merged into `weaveCounts`.
3. Before `MonitorBuilder`, `StampSourceEmitter.emit` writes the helper; `javac` + `d8` put it in the monitor DEX; merge and signing are unchanged.
4. On the device, a routed setter calls the framework setter, then installs or updates the stamp delegate. When the accessibility service (UiAutomation) requests the node, the delegate forwards and adds the extras. For Compose, each node population is followed by `composeNode`, which writes the extras of that virtual node.
5. Each stamp change writes one `RVSEC-BIND` line, which the capture keeps (fifth baseline tag).
6. In the verification, `StampProbe` reads the same nodes through `UiAutomation`, and `check_delivery.py` compares what it read with the `RVSEC-BIND` lines.

With `stamp_handlers=False`, step 1 builds today's argv; step 2 skips the pass and writes no counter; step 3 removes any stale helper; the APK is today's.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `Throwable` in stamp logic (reflection miss, `getExtras` failure, unexpected delegate) | `RvsecStamp` on device | caught inside the helper; the node stays as the platform populated it | none needed; missing stamp is visible as a missing `RVSEC-BIND` line |
| Exception from the app's original setter | app code | not caught; propagates as without the stamp | app's own handling |
| Compose internals renamed by R8 | weave time | no match; `stampComposeSites=0` | none; documented limit |
| Missing `stamp/RvsecStamp.java` resource | `StampSourceEmitter.sourceText` | `IllegalStateException`; APK fails in monitor build | rebuild `instr-cli.jar` |
| Helper fails to compile (e.g. platform jar without an API used) | `MonitorBuilder` javac | APK reported in `instrument_errors.json` like any monitor-build failure | fix the resource; the compile test pins android-30 |
| `--stamp-handlers` on an `instr-cli.jar` older than this change | Picocli | unknown-option error, non-zero exit; wrapper demotes per APK | rebuild and copy the jar to `modules/rv-instrumentation-dexlib2/lib/` |
| `--stamp-handlers` with `--instrumentation-variant ajc` | `rv-experiment` entry point | abort before pre-processing, naming flag and variant | choose `dexlib2` or drop the flag |
| Probe cannot obtain a `UiAutomation` (another client connected, hidden API changed) | `StampProbe` on device | probe exits non-zero, dump empty; the check fails | inspect the tool log; nothing else runs a `UiAutomation` client during the probe task |
| A click leaves the app or opens a system dialog | `StampProbe` navigation | `GLOBAL_ACTION_BACK`; relaunch the launcher activity when the app is not in the foreground; the step's dump records the package reached | none; a step outside the app pairs no node |

## Risks / Trade-offs

- [Extras not delivered to `UiAutomation`] → Checked by the probe (D14) against the `RVSEC-BIND` lines. The probe covers the first screen and the screens one click away; deeper screens and a client cache after a listener change on a recycled row are not covered.
- [Below API 29 an app delegate set before the first listener is replaced] → Campaigns run on API 30; documented in INV-INS-178.
- [The stamp names a generic or library class (XML `onClick`, toolbar/menu/`SearchView`)] → Known limit; the consumer must keep the resource-id key as fallback. A `mMethodName` refinement is a possible follow-up.
- [The delegate's re-entry guard is a per-delegate `boolean[]` without synchronisation] → Accessibility callbacks run on the UI thread; a callback from another thread would at worst forward to the platform default once.
- [Monitor DEX gains about 46–70 method ids] → The monitor DEX is separate from the app DEXes; the merger adds a DEX when needed (existing requirement).
- [The Docker instrumentation image clones the repository from GitHub] → An uncommitted port is not in the image; running the corpus through Docker needs the change committed, pushed and the image rebuilt. Committing is Pedro's step, not a task of this change.
- [Byte-identity depends on the toolchain] → The prototype's aegis monitor DEX differed only because the host default `d8` was used; the comparison pins `d8` 35.0.1 and `android-36/android.jar` as the corpus image does.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java, `dex-mutator`) | site selection, rewrite shape, counters, Compose insertion, range forms, renamed owner | `StampWeaverTest` over synthetic DEX built with dexlib2 builders; `android.jar` resolved as in the prototype test | 2 ported + ~4 added |
| Unit (Java, `monitor-builder`) | emit, remove (only stamp classes), compile at `-source 1.8` against android-30 | `StampSourceEmitterTest` | 3 ported |
| Unit (Java, `cli`) | option resolution, constructor arity, no `stamp*` keys when off | new `ConfigResolverStampTest`; extend `ResultsJsonReportingTest`; fix arity in `BatchRunnerSmokeTest` | ~5 |
| Unit (Python) | argv with and without the field; env unchanged | `test_dexlib_instrumentation.py` with mocked `subprocess.run` | 3 |
| Integration (offline) | off byte-identity on parceltracker against the pre-change jar; on/off normalised diff and equal MOP counters on aegis; environment fallback on cryptoapp | `instr-cli instrument` with the corpus command, `dexdump` streamed and normalised, dumps deleted | 2 APKs |
| Unit (Python) | `rv-experiment` flag/variable resolution, `ajc` abort, forwarding, provenance; five-tag capture; `RVSEC-BIND` inert to the parser | `rv-experiment`, `rv-android-core`, `rv-platform`, `rv-coverage` tests | ~12 |
| Integration (device) | no crash/`VerifyError`; `RVSEC-BIND` lines for View and Compose in the captured `.logcat` | `rv-experiment run --stamp-handlers --instrumentation-variant dexlib2 --tools ape --timeouts 120` on 4 APKs; rv-platform manages the emulator | 1 run |
| Integration (device) | delivery of the extras to a `UiAutomation` client | `run_probe.py` over the 4 stamped APKs, then `check_delivery.py` | 1 run |
| Full suites | no regression | `mvn -o ... -pl br.unb.cic:cli -am` with tests (432 in the prototype run); `pytest --import-mode=importlib -o "addopts="` for `rv-instrumentation-dexlib2` | — |

## Open Questions

None open. Resolved by the researcher on 2026-10-07:
- `RVSEC-BIND` is captured, as the fifth baseline tag (D12).
- The campaign turns the stamp on through `rv-experiment`: flag `--stamp-handlers` and variable `RV_STAMP_HANDLERS` (D11).
- `instr-cli` keeps the `RVSEC_STAMP_HANDLERS` fallback (D4).
- Delivery to a `UiAutomation` client is checked in this change, by the probe (D14).
- Off byte-identity is checked against the pre-change `instr-cli.jar` (D13).
