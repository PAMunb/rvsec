# Handler Stamp on the Accessibility Node (View and Compose), Behind an Off-by-Default Flag

GitHub Issue: #121

## Why

APE-RV matches a click to the static analysis by the key `(activity, resource-id, event)`. In the E6 run of Study 03, 58.6 % of the clicks landed on a node without a `resource-id`, and in Compose-only apps no node carries an id the GATOR analysis knows. For those clicks there is no widget guidance at all (`docs/20261007_variante_a_carimbo_handler.md`, §2). Where the id does match, the static widget → handler binding over-assigns: in keys with several handlers only 34.6 % of the assigned handlers ever ran.

The DEX-native instrumenter already rewrites call sites and method entries of the APK it ships. It can also record, at run time and on the real object, which handler class is bound to each clickable node, and put that class into the node's `AccessibilityNodeInfo` extras, which APE-RV already receives through `UiAutomation`. The key then no longer depends on a resource-id, and the binding is observed instead of inferred. The corpus instrumentation for the Study 03 campaign needs the stamp, so the flag has to reach `instr-cli` through the pipeline that instruments the corpus, `rv-experiment` included. And the stamp is useful only if the extras reach the process that reads the tree, so this change checks that delivery on a device instead of leaving it to the APE-RV change.

## What Changes

- **New `instr-cli` option `--stamp-handlers` / `--no-stamp-handlers`, off by default.** With no option, `RVSEC_STAMP_HANDLERS=true` in the environment turns it on, for direct use of `instr-cli`; `--no-stamp-handlers` wins over the variable. With the option off, every woven `classes*.dex` and the monitor DEX are byte-identical to what the instrumenter produces today, and `instrument_results.json` carries exactly the keys it carries today.
- **View stamp.** With the option on, every `invoke-virtual` / `invoke-virtual/range` of `setOnClickListener(View$OnClickListener)`, `setOnLongClickListener(View$OnLongClickListener)` and `setAccessibilityDelegate(View$AccessibilityDelegate)` whose static owner is assignable to `android.view.View` (app, androidx and Material code alike) becomes `invoke-static mop.RvsecStamp.<same name>(View, X)`. `invoke-super` sites and owners that are not a `View` are left unchanged and counted.
- **Compose stamp.** With the option on, right after each `invoke-direct` of `AndroidComposeViewAccessibilityDelegateCompat.populateAccessibilityNodeInfoProperties(I, AccessibilityNodeInfoCompat, SemanticsNode)V`, the weaver inserts `invoke-static mop.RvsecStamp.composeNode(info, node)`. The match is on the exact owner, name and signature; a build whose Compose internals R8 renamed has no match and is left unchanged.
- **Runtime helper `mop.RvsecStamp`.** A fixed Java source shipped as a resource of `monitor-builder`, emitted into `--monitor-src-dir` and compiled into the monitor DEX the same way as `mop.Coverage`. Each setter helper makes the original call exactly once and then updates the stamp inside `catch (Throwable)`. The stamp is a chaining `View.AccessibilityDelegate` that writes `rvsec.click` / `rvsec.longClick` into the node extras. Every change of a stamp is logged under the logcat tag `RVSEC-BIND`. With the option off, a stale helper source or class left in the shared monitor directories by an earlier run is removed.
- **New `weaveCounts` keys, present only with the option on**: `stampClickSites`, `stampLongClickSites`, `stampDelegateSites`, `stampComposeSites`, `stampInvokeSuperSkipped`, `stampOwnerNotView`. MOP counters are unchanged.
- **Python forwarding.** `DexlibInstrumentationConfig` gains `stamp_handlers: bool = False`, and `DexlibInstrumentation._common_cli_args` appends `--stamp-handlers` when it is true. The flag travels as an explicit argument: `_build_subprocess_env` forwards only `PATH`, `HOME`, `JAVA_HOME`, `ANDROID_HOME` and `RVSEC_HOME` (INV-EXP-30), and that stays as it is, so `RVSEC_STAMP_HANDLERS` never reaches `instr-cli` through the wrapper.
- **`rv-experiment` switch.** `rv-experiment run` gains `--stamp-handlers` / `--no-stamp-handlers` and the variable `RV_STAMP_HANDLERS` (flag > variable > default `False`), registered as `ENV_STAMP_HANDLERS` in the core environment registry. `get_dexlib_instrumentation_config` sets `stamp_handlers` from it, and `experiment_config.json` records it. With the `ajc` variant the flag aborts the run, because that variant has no stamp.
- **Capture keeps `RVSEC-BIND`.** `TAG_RVSEC_BIND` joins the four tag constants, and `LogcatManager.default_tags` becomes `RVSEC`, `RVSEC-COV`, `ApeRvHb`, `RVSEC-OCC`, `RVSEC-BIND`. The lines are the app-side record of the stamp, the reference for the delivery check below and for an offline join of clicks to handlers. Like `ApeRvHb` and `RVSEC-OCC`, they are inert to `rv-coverage`.
- **Delivery check on a device.** A minimal Java probe connects to `UiAutomation` the way APE-RV does (`app_process`) and prints the `rvsec.*` extras of every node of the first screen and of each screen one click away: it clicks each clickable node of the first screen in turn, dumps the screen reached and goes back. It is the only `UiAutomation` client (no APE runs in that task), and it runs as the tool of a short `rv-platform` task, so `rv-platform` keeps managing the emulator. The check passes when every node with an `RVSEC-BIND` line in the window is read by the probe with the same handler, for View and for Compose.
- **Verification artefacts in the repository.** The prototype's `dexdump` normalisation and comparison scripts are restored into `experimento-smk121/scripts/`, beside the probe and its runner; nothing the verification needs lives in a temporary directory.
- **Specs describe the stamp and its known limits**: XML `android:onClick` stamps `AppCompatViewInflater$DeclaredOnClickListener`; toolbar, menu and `SearchView` stamp the library dispatcher; `AlertDialog` buttons and `Preference` rows are not covered.

Out of scope: APE-RV reading the stamp and keying by handler class (a separate change in the `ape` repository); the static analysis that produces the per-handler distance (#120); refining `DeclaredOnClickListener` through its `mMethodName` field; `AlertDialog` and `Preference` coverage.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `instrumentation`: a new requirement for the handler stamp of the `dexlib2` instrumenter (the off-by-default option, its environment fallback and its byte-identity guarantee, the View and Compose weave, the runtime helper's contract, the counters, the delivery to a `UiAutomation` client, the known limits), and a modified "DEX-Native APK Instrumentation Pipeline" requirement for the Python wrapper's forwarding of the option.
- `core`: a new requirement for `RVSEC-BIND` in the capture allowlist (INV-CORE-67); INV-CORE-37/38/53 and the capture requirements restated with five tags.
- `platform`: INV-PLT-21, "Capture Flag Threading to LogcatComponent" and "Logcat Capture" restated with `RVSEC-BIND`.
- `experiment`: a new requirement for the `--stamp-handlers` flag and `RV_STAMP_HANDLERS` (INV-EXP-40).

## Impact

- **Java, `rvsec/rvsec-android/rvsec-instrumentation-dexlib2`** (outside the uv workspace, built by the root Maven reactor): `cli` (`InstrumentationCli`, `EffectiveConfig`, `ConfigResolver`, `BatchRunner`), `dex-mutator` (new `StampWeaver`), `monitor-builder` (new `StampSourceEmitter` and the `RvsecStamp.java` resource). The rebuilt `instr-cli.jar` is copied into `rv-android/modules/rv-instrumentation-dexlib2/lib/`.
- **Python, `rv-instrumentation-dexlib2`**: `config.py` (one field), `dexlib_instrumentation.py` (`_common_cli_args`). No change to `rv-instrumentation-core`: `weave_counts` is already a free `Dict[str, Dict[str, int]]`, so the new counter keys pass through unparsed.
- **rv-android-core**: `util/logging/constants.py` (`TAG_RVSEC_BIND`), `util/android/logcat_manager.py` (`default_tags`), `constants.py` (`ENV_STAMP_HANDLERS`), and their tests.
- **rv-experiment**: `__main__.py` (the flag and its resolution), `config.py` (`ExperimentConfig.stamp_handlers`, `get_dexlib_instrumentation_config`), the provenance record, and tests; `README.md` or `.env.example` and `docker/rvandroid/scripts/validate_env_vars.sh` for the variable.
- **rv-platform, rv-coverage**: no code change; the tests that assert the capture command and the inertness of extra tags change.
- **`experimento-smk121/`**: the probe (Java source, build script, an in-process runner that registers it as a tool for one `rv-platform` run), the restored comparison scripts, and the report of the checks.
- **Not changed**: the `ajc` variant, the `.mop` specifications.
- **Device**: an instrumented APK with the option on carries the helper in its monitor DEX (about 46–70 more method ids there) and fewer method ids in the app DEXes, because owner-specific setter references are replaced by at most four helper references.
- **Requirements**: FR02 (APK Instrumentation with Monitors), NFR05 (Configurability: explicit option, default off), NFR04 (Resilience: the stamp never throws into the app), NFR08 (Reproducibility: off is byte-identical to today's output).
