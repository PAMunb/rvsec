## Purpose

The `dexlib2` instrumenter rewrites the DEX of an APK so that the monitors observe it: it routes call sites to monitor wrappers and inserts coverage at method entry. This delta adds a third, optional rewrite that serves the GUI explorer rather than the monitors: the **handler stamp**. With the stamp on, the instrumented app records, at run time and on the real object, which handler class is bound to each clickable node, and writes that class into the node's `AccessibilityNodeInfo` extras. A testing tool that reads the accessibility tree through `UiAutomation`, as APE-RV does, can then key a node by its handler class instead of by its resource-id.

The reason is measured. APE-RV matches a click to the static analysis by `(activity, resource-id, event)`. In the E6 run of Study 03, 58.6 % of the clicks landed on a node with no `resource-id`; in Compose-only apps no virtual node carries an id the static analysis knows, so 97.4 % of their clicks had no key. Where the id did match, the static widget → handler binding over-assigned: in keys with several handlers only 34.6 % of the assigned handlers ran. A stamp written by the running app on the node it belongs to removes both limits for every node that has a stamp. The distance from a handler method to a monitored operation comes from the static analysis per method, so a key by handler class reuses it without a screen model.

The stamp covers two kinds of node. A **View** gets its listener through a call in the APK (`setOnClickListener`, `setOnLongClickListener`), and the weaver routes that call through a fixed helper, `mop.RvsecStamp`, which makes the original call and then installs a chaining `View.AccessibilityDelegate` that adds the extras whenever the platform builds the node. A **Compose** node is virtual: there is no view per widget and no listener call to route. Compose fills each virtual node from its `SemanticsNode` inside a private method of `AndroidComposeViewAccessibilityDelegateCompat`, and the weaver inserts a call to the helper right after that method returns. The helper reads the clickable modifier's `onClick` lambda by reflection and writes its class into the same extras.

The stamp is an observation, so it is held to two guarantees. It is **off by default**, and off reproduces today's instrumented output byte for byte, which keeps every published measurement reproducible and keeps the corpus instrumented without the stamp unaffected by this change. And when it is on, it **does not change what the app does**: every routed setter performs the original call exactly once, every failure of the stamp logic is caught inside the helper, and the monitors see exactly the events they saw before. The stamp emits no monitor event and does not change what is accused.

The option reaches the Java `instr-cli` through the Python wrapper `rv-instrumentation-dexlib2`, as an explicit configuration field turned into an explicit command-line argument; `rv-experiment` sets that field from its own flag and `RV_*` variable (experiment INV-EXP-40). `instr-cli` run directly also accepts `RVSEC_STAMP_HANDLERS=true` when no option is given. That variable never reaches it through the wrapper, which forwards a fixed environment to the Java process (INV-EXP-30).

The stamp has known limits, recorded in the requirement so that a consumer of the stamp does not read more into it than it says: an XML `android:onClick` stamps the inflater's generic listener class; toolbar, menu and search-widget clicks stamp the library dispatcher; `AlertDialog` buttons and `Preference` rows are not covered. Whether the extras reach a client that reads the tree through `UiAutomation`, as APE-RV does, is checked on a device in this change, against the `RVSEC-BIND` lines; APE-RV reading the stamp is a separate change in the `ape` repository.

## Data Contracts

### Input
- `--stamp-handlers` / `--no-stamp-handlers` — option of every `instr-cli` subcommand (`InstrumentationCli`, scope `INHERIT`). Resolved into `EffectiveConfig.stampHandlers: boolean` by `ConfigResolver`: the option when given; otherwise `RVSEC_STAMP_HANDLERS` (`true`, case-insensitive, turns it on); otherwise off.
- `RVSEC_STAMP_HANDLERS` — environment variable read by `ConfigResolver` only when the option is absent; source: the shell that runs `instr-cli` directly. The Python wrapper does not forward it.
- `stamp_handlers: bool = False` — field of `DexlibInstrumentationConfig` (`modules/rv-instrumentation-dexlib2/src/rv_instrumentation_dexlib2/config.py`); source: the caller that builds the config.
- `RvsecStamp.java` — fixed helper source, a classpath resource of `monitor-builder` (`br/unb/cic/rv/builder/stamp/RvsecStamp.java`), package `mop`; compiles against `android.jar` alone at `-source 1.8`.

### Output
- Woven app `classes*.dex` — with the option on, the setter sites and Compose population sites of INV-INS-176 rewritten; with it off, unchanged (INV-INS-174).
- Monitor DEX — with the option on, carries `mop.RvsecStamp` and its nested classes; with it off, does not.
- `instrument_results.json` `weaveCounts` — with the option on, six more integer keys per APK: `stampClickSites`, `stampLongClickSites`, `stampDelegateSites`, `stampComposeSites`, `stampInvokeSuperSkipped`, `stampOwnerNotView`; with it off, none of them. Consumer: `InstrumentationResults.weave_counts` (passed through unparsed).
- On the device, `AccessibilityNodeInfo` extras of a stamped node: `rvsec.click` and/or `rvsec.longClick`, each a `String` holding a binary class name (`Class.getName()`). Consumer: a client of `UiAutomation` (APE-RV, in a separate change).
- On the device, logcat lines at level `I` under the tag `RVSEC-BIND`:
  - View: `view kind=<click|longClick> node=<accessibility class name or view class> viewClass=<view class> id=<resource name, 0x<hex>, or -> handler=<class or -> obj=<identity hash hex>`
  - Compose: `compose kind=<click|longClick> node=<node class name> semanticsId=<int> id=<view-id resource name or -> bounds=<Rect.toShortString()> handler=<class>[ longClickHandler=<class>]`

### Side-Effects
- **File system (monitor sources)**: with the option on, `StampSourceEmitter.emit` writes `<monitor-src-dir>/mop/RvsecStamp.java`; with it off, `StampSourceEmitter.remove` deletes that file and `<work-dir>/monitor-build/classes/mop/RvsecStamp.class` and `RvsecStamp$*.class` when present. Both directories are shared by the APKs of a batch and by successive runs.
- **Device (accessibility)**: on a view whose listener is routed through the helper, the view's accessibility delegate becomes the stamp delegate, with the delegate the view already had (API ≥ 29) or the app's later delegate chained behind it.
- **Device (logcat)**: `RVSEC-BIND` lines in the `main` buffer. `LogcatManager.default_tags` includes the tag (core INV-CORE-53), so the platform's capture keeps them.

### Error
- None at run time on the device: every `Throwable` raised by stamp logic is caught inside `mop.RvsecStamp` (INV-INS-177). An exception raised by the app's original setter call propagates exactly as without the stamp.
- At instrumentation time, a failure to emit or compile the helper fails the APK's monitor-build phase like any other monitor-build failure, and is reported in `instrument_errors.json`.

## Invariants

- **INV-INS-174**: When the option resolves to off — `--no-stamp-handlers`, or no option and `RVSEC_STAMP_HANDLERS` unset or not `true` — every woven `classes*.dex` and the monitor DEX MUST be byte-identical to the output of the same `instr-cli` command before this change, for the same APK, descriptor and toolchain (`android.jar`, `d8`). This MUST hold when an earlier run with the option on left `mop/RvsecStamp.java` in the monitor source directory or `mop/RvsecStamp*.class` in `<work-dir>/monitor-build/classes`. No `stamp*` key MAY appear in `weaveCounts`. The option resolves to on when the command line carries `--stamp-handlers`, or carries neither form and `RVSEC_STAMP_HANDLERS` is `true` (case-insensitive); `--no-stamp-handlers` MUST win over the variable.
- **INV-INS-175**: With `--stamp-handlers`, each app `classes*.dex` MUST differ from its off counterpart only at (a) the setter sites rewritten under INV-INS-176, where the opcode `invoke-virtual` becomes `invoke-static` (and `invoke-virtual/range` becomes `invoke-static/range`), the method reference becomes the `mop.RvsecStamp` helper of the same name with signature `(Landroid/view/View;<listener type>)V`, and the register list is unchanged; and (b) one `invoke-static mop.RvsecStamp.composeNode(Ljava/lang/Object;Ljava/lang/Object;)V` inserted immediately after each matched Compose population call, together with the branch-target and debug-item relocation that insertion implies. Every `weaveCounts` key that the off run writes MUST have the same value in the on run.
- **INV-INS-176**: A call site is a stamp candidate when its method reference has name and descriptor `setOnClickListener(Landroid/view/View$OnClickListener;)V`, `setOnLongClickListener(Landroid/view/View$OnLongClickListener;)V` or `setAccessibilityDelegate(Landroid/view/View$AccessibilityDelegate;)V`, and it is not in a class of the `mop` package. A candidate MUST be rewritten exactly when its opcode is `invoke-virtual` or `invoke-virtual/range` and its static owner is assignable to `android.view.View` through the APK and framework hierarchy (`InheritanceResolver`). Every candidate MUST be counted exactly once: rewritten ones in `stampClickSites`, `stampLongClickSites` or `stampDelegateSites` by name; `invoke-super` and `invoke-super/range` ones in `stampInvokeSuperSkipped`; virtual ones whose owner is not assignable to `View` or cannot be resolved in `stampOwnerNotView`. A Compose population call is an `invoke-direct`, `invoke-virtual` or their range form whose reference is exactly `Landroidx/compose/ui/platform/AndroidComposeViewAccessibilityDelegateCompat;->populateAccessibilityNodeInfoProperties(ILandroidx/core/view/accessibility/AccessibilityNodeInfoCompat;Landroidx/compose/ui/semantics/SemanticsNode;)V`; the inserted call MUST pass that call's third and fourth registers (info, node) and MUST be counted in `stampComposeSites`. A reference whose owner or name differs in any character, such as one renamed by R8, MUST NOT match.
- **INV-INS-177**: `mop.RvsecStamp.setOnClickListener(View, OnClickListener)` and `setOnLongClickListener(View, OnLongClickListener)` MUST call the original setter on the receiver exactly once, by virtual dispatch, with the original argument, before any stamp logic and outside its `try`; an exception from that call MUST propagate unchanged. `setAccessibilityDelegate(View v, AccessibilityDelegate d)` MUST call `v.setAccessibilityDelegate` exactly once: with the stamp delegate, after chaining `d` behind it, when `v` already carries the stamp delegate and `d` is not that delegate; with `d` otherwise. `composeNode(Object, Object)` MUST NOT throw. Every `Throwable` raised by stamp logic, in the helpers and in the stamp delegate, MUST be caught and not propagated.
- **INV-INS-178**: The stamp delegate MUST forward every one of the ten `View.AccessibilityDelegate` callbacks to the chained app delegate when there is one and to the platform default otherwise, and a callback re-entered while it is being forwarded MUST go to the platform default. In `onInitializeAccessibilityNodeInfo`, after forwarding, it MUST set `rvsec.click` to the `getClass().getName()` of the last non-null click listener routed through the helper for that view, and remove the key when the last routed click listener was `null`; `rvsec.longClick` follows the same rule for long-click listeners. On API ≥ 29 the delegate the view carries when the stamp is first installed MUST be chained; below API 29 it cannot be read, and the stamp delegate replaces it. For a Compose node, `composeNode` MUST write the same keys into the extras of the unwrapped `AccessibilityNodeInfo`, with the handler resolved from the node's unmerged semantics configuration: the `OnClick` / `OnLongClick` action's lambda; its `this$0` modifier node; that node's `onClick` / `onLongClick` field, or `onValueChange` for an `onClick` on a `ToggleableNode`; and the action lambda's own class when no modifier node is reached. A key whose action is absent MUST be removed.
- **INV-INS-179**: The helper MUST write one `RVSEC-BIND` line for a view each time the value of one of its stamp keys changes, and none when a listener of the same class is set again. For Compose it MUST write one line per semantics id each time that id's `click|longClick` pair changes, and none for a node with neither key. The tag MUST be `RVSEC-BIND`; it is neither `RVSEC` nor `RVSEC-COV`, so no reader of those tags (exact tag match) sees the lines.
- **INV-INS-180**: `DexlibInstrumentation._common_cli_args` MUST contain `--stamp-handlers` exactly once when `DexlibInstrumentationConfig.stamp_handlers` is `True`, and MUST be identical to the argument list it builds today when the field is `False` (neither `--stamp-handlers` nor `--no-stamp-handlers`). Both the `instrument` and the `batch` invocations MUST carry it, since both build their arguments through `_common_cli_args`. `_build_subprocess_env` MUST keep forwarding only `PATH`, `HOME`, `JAVA_HOME`, `ANDROID_HOME` and `RVSEC_HOME`.

## MODIFIED Requirements

### Requirement: DEX-Native APK Instrumentation Pipeline

The system MUST provide an alternative to the AspectJ-based instrumentation pipeline that operates exclusively over DEX bytecode using `dexlib2`, eliminating the `dex2jar → ajc → d8` round-trip and the JVMS §4.10.1.9 type-consistency conflict it induces on R8-optimized APKs. This pipeline MUST be implemented as a Maven multi-module Java aggregator `rvsec-instrumentation-dexlib2` at `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/` (sibling of `rvsec-apk`, `rvsec-gator`, etc. under the `rvsec-android` aggregator) wrapped by a Python module `rv-instrumentation-dexlib2` at `rv-android/modules/rv-instrumentation-dexlib2/` (uv workspace member) that exposes the same `instrument_apks(apks_dir, results_dir) → InstrumentationResults` contract used by the legacy pipeline.

The Java side MUST decompose into single-responsibility submodules: `descriptor-reader` (Jackson POJO model for the JSON descriptor), `pointcut-engine` (parser + matcher + type resolver + android.jar overload index), `advice-emitter` (one emitter per advice kind: before, after, after returning, after throwing, staticinitialization, if-guarded, plus a wrapper emitter for register-aliasing-safe replacement), `dex-mutator` (DexWeaver orchestration + InstructionInjector + RegisterAllocator + RegisterShifter, and the optional `StampWeaver` of the handler stamp), `coverage-weaver` (the `execution(* *.*(..))` catch-all with canonical package filter and Soot-style signature formatting), `monitor-builder` (javac + d8 over `MultiSpec_*RuntimeMonitor.java`, `mop.MonitorWrappers.java`, and runtime JARs, plus the `mop.RvsecStamp` helper when the handler stamp is on), `multidex-merger` (apksigner v3 + zipalign), `cli` (Picocli unified entry point), and `validator` (the rigor harness — see separate requirement).

The pipeline MUST consume the JSON descriptor produced by `javamop --emit-descriptor` (see modified Monitor Generation requirement) as its sole source of pointcut/advice semantics. It MUST NOT parse the textual `.aj` output. The descriptor's `imports` list MUST be the authority for resolving simple type names (e.g., `Cipher` → `Ljavax/crypto/Cipher;`) into DEX type descriptors.

The pipeline MUST preserve the multidex structure of the input APK (INV-INS-52) and MUST honor the canonical Coverage exclusion filter (INV-INS-53). When register pressure forces `4-bit` instruction format expansion, the weaver MUST emit the corresponding `from16` / `from32` variants and bump `MethodImplementation.registerCount` accordingly, never silently dropping or skipping advice insertions.

The Python wrapper MUST forward the handler-stamp option of `Requirement: Handler Stamp on the Accessibility Node` as an explicit command-line argument built from its configuration. `DexlibInstrumentationConfig.stamp_handlers` (default `False`) is the only input; when it is `True`, `_common_cli_args` appends `--stamp-handlers`, and when it is `False`, the argument list is the one built without the field (INV-INS-180). The wrapper MUST NOT rely on `instr-cli`'s `RVSEC_STAMP_HANDLERS`: it hands the Java process a fixed environment (INV-EXP-30), and a variable outside that set never reaches `instr-cli`, so the configuration field is the wrapper's only input. `rv-experiment` sets the field from `--stamp-handlers` or `RV_STAMP_HANDLERS` (experiment INV-EXP-40).

#### Scenario: DEX-native instrumentation of an R8-optimized APK previously failing under ajc

- **WHEN** an APK previously known to fail at boot with `VerifyError` under the `ajc` variant (e.g., `hateitorrateit` from the JCA-400 dataset), and the corresponding JSON descriptor is present in `monitor_output_dir`, and `instrumentation_variant == "dexlib2"`
- **THEN** `DexlibInstrumentation.instrument(app, result_dir)` MUST produce a signed APK at `{instrumented_dir}/{app.name}.apk`
- **AND** the instrumented APK hash MUST differ from the original APK hash (preserving INV-INS-06)
- **AND** booting the APK in an emulator MUST NOT raise `VerifyError`
- **AND** RVSEC-COV events MUST be emitted to logcat for app-code methods exercised during the boot sequence
- **AND** all AspectJ business advices in the descriptor that match invocations executed during boot MUST trigger the corresponding monitor event

#### Scenario: Missing descriptor when dexlib2 variant is selected

- **WHEN** `instrumentation_variant == "dexlib2"` and `monitor_output_dir` contains `MultiSpec_1MonitorAspect.aj` and `MultiSpec_1RuntimeMonitor.java` but no `MultiSpec_1MonitorAspect.json`
- **THEN** `DexlibInstrumentation.prepare_instrumentation()` MUST raise `MissingDescriptorError` before any APK processing begins
- **AND** the error message MUST identify the missing JSON file and mention the `--emit-descriptor` flag

#### Scenario: Multidex preservation under DEX-native weaving

- **WHEN** an input APK contains `classes.dex` + `classes2.dex` (two DEX files due to method-id pressure) and `instrumentation_variant == "dexlib2"`
- **THEN** the output APK MUST contain at least `classes.dex` + `classes2.dex` with the same application-class assignment to each DEX
- **AND** if monitor classes (from `MultiSpec_*RuntimeMonitor.java` + `mop.MonitorWrappers.java`) push the host DEX over 65,536 method refs, exactly one additional DEX file MUST be added for the monitor classes
- **AND** the output APK MUST NOT silently merge multidex partitions

#### Scenario: Register-pressure expansion preserves advice insertion

- **WHEN** the weaver injects a monitor call into a method whose register usage would push an instruction beyond Dalvik's 4-bit register-index limit (e.g., needs `v16` or higher in a `12x` `move` form)
- **THEN** `RegisterShifter` MUST expand the affected instructions to the wider format (`22x` `move/from16`, `32x` `move/from16`, etc.)
- **AND** `MethodImplementation.registerCount` MUST be bumped by the number of additional registers consumed
- **AND** the advice insertion MUST NOT be silently skipped due to register pressure

#### Scenario: The wrapper forwards the stamp option when the config asks for it

- **WHEN** `DexlibInstrumentation` is built with `DexlibInstrumentationConfig(stamp_handlers=True, ...)` and instruments `apks_dir` through the `batch` or the `instrument` subcommand
- **THEN** the argument list passed to `java -jar instr-cli.jar` MUST contain `--stamp-handlers` exactly once
- **AND** the environment passed to the subprocess MUST contain no key outside `PATH`, `HOME`, `JAVA_HOME`, `ANDROID_HOME`, `RVSEC_HOME` and the caller's explicit extras

#### Scenario: The wrapper leaves the argument list unchanged when the stamp is off

- **WHEN** `DexlibInstrumentationConfig` is built without `stamp_handlers`, as `rv-experiment`'s `get_dexlib_instrumentation_config` builds it when neither `--stamp-handlers` nor `RV_STAMP_HANDLERS` is set
- **THEN** `stamp_handlers` MUST be `False`
- **AND** `_common_cli_args(output_dir)` MUST contain neither `--stamp-handlers` nor `--no-stamp-handlers`
- **AND** it MUST equal, element by element, the list built for the same config before the field existed

## ADDED Requirements

### Requirement: Handler Stamp on the Accessibility Node

The `dexlib2` instrumenter SHALL offer an optional weave, selected by the `instr-cli` option `--stamp-handlers` and off by default, that makes the instrumented app write the class of the handler bound to each clickable node into that node's `AccessibilityNodeInfo` extras. The weave is independent of the MOP descriptor: it adds no monitor event, changes no site the advice weave touches, and does not change what is accused.

**Off is today's output.** Without the option, the instrumenter SHALL produce byte-identical DEX files and the same `weaveCounts` keys as without this requirement (INV-INS-174). The monitor source directory and the `monitor-build` work directory are shared by every APK of a batch and by successive runs, so a run without the option SHALL remove a `mop/RvsecStamp` source or class file that an earlier run with the option left there; otherwise `MonitorBuilder`, which compiles every `.java` it finds, would put the helper into the monitor DEX of a run that did not ask for it. The option is on when the command line carries `--stamp-handlers`, or, with no option, when `RVSEC_STAMP_HANDLERS=true`; `--no-stamp-handlers` wins over the variable. A run turned on by the variable is recognisable from its output, because the `stamp*` counters exist in `weaveCounts` only when the stamp is on.

**View: routing the setters.** With the option on, `StampWeaver` (`dex-mutator`) SHALL rewrite each stamp candidate of INV-INS-176 into an `invoke-static` of the helper method of the same name in `mop.RvsecStamp`, whose first parameter is the receiver. The rewrite keeps the register list and the instruction size, so branch targets and try ranges are untouched (INV-INS-175). It applies to any owner the hierarchy resolves as a `View` subtype, app, androidx and Material code alike, because a listener set inside a library on a view the app inflated is still the handler of the node the tool clicks. The helper calls the setter by virtual dispatch, so an app subclass that overrides a setter still runs its override. `invoke-super` sites are left alone because they name an implementation the helper cannot call; they are counted. The stamp pass SHALL run after the advice weave and before the coverage weave, over the same mutable method bodies, so that every site it sees is the invoke the app compiled.

**View: what the helper does.** Each setter helper SHALL make the original call exactly once and only then update the stamp, inside `catch (Throwable)` (INV-INS-177). The stamp is a `View.AccessibilityDelegate` installed on the view on its first non-null listener. It forwards all ten delegate callbacks to the delegate the app had set, so the app's own accessibility behaviour is kept, and in `onInitializeAccessibilityNodeInfo` it adds `rvsec.click` and `rvsec.longClick` after forwarding (INV-INS-178). A delegate that wraps the delegate it finds on the view, as `ViewCompat` does, would call back into the stamp delegate; a re-entered callback therefore goes to the platform default. When the app sets its own delegate on a view that already carries the stamp, the helper chains the app's delegate behind the stamp instead of letting it replace the stamp. From API 29 the delegate a view already carries when the stamp is first installed is read with `View.getAccessibilityDelegate()` and chained; that method does not exist below API 29, where the stamp delegate replaces a delegate the app set before the first listener. The campaigns run on API 30.

**Compose: after the node is populated.** A Compose screen has one `AndroidComposeView` and virtual accessibility nodes built from semantics; the app's click handler is a lambda passed to a modifier, not a listener set by a call that can be routed. Compose fills each virtual node in the private method `AndroidComposeViewAccessibilityDelegateCompat.populateAccessibilityNodeInfoProperties`, which cannot be routed through a helper because it is private. With the option on, the weaver SHALL insert, immediately after each call of that exact method, an `invoke-static` of `mop.RvsecStamp.composeNode(info, node)` over the call's own info and node registers; the call returns `void`, so both registers still hold their values. `composeNode` reads the node's unmerged semantics configuration by reflection and resolves the handler as INV-INS-178 states; its parameters are typed `Object` because the helper compiles against `android.jar` alone. The match is on the exact owner, name and descriptor (INV-INS-176): in a build whose Compose internals R8 renamed there is no match, no stamp, and no change to the APK.

**The helper ships in the monitor DEX.** `StampSourceEmitter` (`monitor-builder`) SHALL write the fixed resource `RvsecStamp.java` as `mop/RvsecStamp.java` into the monitor source directory when the option is on, and `MonitorBuilder` compiles and dexes it with the monitors, as it does `mop.Coverage`. The source SHALL compile against `android.jar` alone at Java source level 1.8 and SHALL reference no androidx or Compose type at compile time. Placing the helper in the monitor DEX keeps the app DEXes under the 64K method-reference limit: replacing owner-specific setter references with at most four helper references lowers their method-id count.

**Counters.** With the option on, the instrumenter SHALL add, per APK, `stampClickSites`, `stampLongClickSites`, `stampDelegateSites`, `stampComposeSites`, `stampInvokeSuperSkipped` and `stampOwnerNotView` to `weaveCounts` (INV-INS-176). A zero `stampComposeSites` on an APK that uses Compose is the measurable sign of a renamed library.

**Verification log.** The helper SHALL log every change of a stamp under the logcat tag `RVSEC-BIND` (INV-INS-179), so that the stamp can be checked from a logcat capture without any change to the testing tool; the platform's capture keeps the tag (core INV-CORE-53). The line carries the node's accessibility class, the resource name when there is one, and the handler class; Compose lines also carry the semantics id and the screen bounds.

**Delivery to an accessibility client.** The stamp is useful only if the extras reach the process that reads the accessibility tree. The extras SHALL be readable by a client of `UiAutomation`: for a node whose stamp the helper logged under `RVSEC-BIND`, `AccessibilityNodeInfo.getExtras()` obtained through `UiAutomation` SHALL carry `rvsec.click` / `rvsec.longClick` with the handler class of the node's last `RVSEC-BIND` line, for View and for Compose nodes. This is checked on a device by a minimal probe that connects to `UiAutomation` the way APE-RV does (`app_process`) and prints the `rvsec.*` extras of every node of the current window.

**Known limits.** A stamp names the class of the listener object the app passed, and in three cases that class is not the app's handler or there is no stamp. They are limits of what the stamp says, not defects to repair in this requirement:

- **XML `android:onClick`.** Under AppCompat the inflater sets an `AppCompatViewInflater$DeclaredOnClickListener` through `setOnClickListener`, so the stamp carries that generic class; the app method's name is in its `mMethodName` field, which the helper does not read. In one measured APK (`scep`) this was 42 of 134 `RVSEC-BIND` lines.
- **Library dispatchers.** The toolbar navigation button, menu items and `SearchView` stamp the library's own listener (`ToolbarWidgetWrapper$1`, `ActionMenuItemView`, `SearchView$5`), which hands off to an app callback such as `onOptionsItemSelected`.
- **Not covered.** `AlertDialog` buttons get their listener inside the framework when the dialog is shown, and `Preference` rows inside the preference library's binding; neither passes through a routed setter, so neither is stamped.

A Compose text field reports a Compose-internal handler class, and an activity that implements `View.OnClickListener` for several buttons stamps the activity on all of them; the stamp's granularity is the handler class, not the branch of a `switch` inside it.

#### Scenario: Off reproduces the instrumenter without the stamp byte for byte

- **WHEN** `dev.itsvic.parceltracker_10501000.apk` is instrumented twice with the same `jca_android` descriptor, the same runtime jars, `d8` 35.0.1 and `android-36/android.jar` — once by the `instr-cli.jar` built before this change, and once by this change's `instr-cli.jar` without `--stamp-handlers` and with `RVSEC_STAMP_HANDLERS` unset
- **THEN** each of its DEX files, the monitor DEX included, MUST be byte-identical between the two runs
- **AND** `weaveCounts` for the second run MUST contain no key starting with `stamp`

#### Scenario: The environment fallback turns the stamp on and the negative option wins

- **WHEN** `instr-cli instrument` runs with `RVSEC_STAMP_HANDLERS=true` in its environment and neither `--stamp-handlers` nor `--no-stamp-handlers`
- **THEN** `EffectiveConfig.stampHandlers` MUST be `true` and `weaveCounts` MUST carry the six `stamp*` keys
- **AND** the same command with `--no-stamp-handlers` MUST resolve `stampHandlers` to `false`

#### Scenario: Off after an earlier run with the stamp in the same directories

- **WHEN** a batch first instruments one APK with `--stamp-handlers` and then, with the same `--monitor-src-dir` and `--work-dir`, instruments a second APK without it
- **THEN** `<monitor-src-dir>/mop/RvsecStamp.java` MUST be absent before `MonitorBuilder` runs for the second APK
- **AND** the second APK's monitor DEX MUST contain no class `Lmop/RvsecStamp;` nor any `Lmop/RvsecStamp$...;`

#### Scenario: A View setter in app code is routed and counted

- **WHEN** a method of the app contains `invoke-virtual {v10, v11}, Landroid/widget/Button;->setOnClickListener(Landroid/view/View$OnClickListener;)V` and the APK is instrumented with `--stamp-handlers`
- **THEN** the instruction MUST become `invoke-static {v10, v11}, Lmop/RvsecStamp;->setOnClickListener(Landroid/view/View;Landroid/view/View$OnClickListener;)V`
- **AND** the method's code size, branch targets and try ranges MUST be unchanged
- **AND** `stampClickSites` MUST count that site once

#### Scenario: Sites that are not rewritten are counted

- **WHEN** an APK instrumented with `--stamp-handlers` contains one `invoke-super` of `setOnClickListener(View$OnClickListener)` in a `View` subclass and one `invoke-virtual` of `setOnClickListener(View$OnClickListener)` on an owner the hierarchy does not resolve as a `View`
- **THEN** both instructions MUST be left unchanged
- **AND** `stampInvokeSuperSkipped` MUST be 1 and `stampOwnerNotView` MUST be 1 for those two sites

#### Scenario: On changes only the stamp sites and keeps every MOP counter

- **WHEN** `com.beemdevelopment.aegis_81.apk` is instrumented with and without `--stamp-handlers`, and the two sets of app DEXes are compared after normalising pool indices and offsets
- **THEN** every difference MUST be a rewritten setter site or an inserted `composeNode` call
- **AND** no `invoke-virtual` of one of the three setters on a `View` owner MUST remain in the on output
- **AND** every `weaveCounts` key present in the off run MUST have the same value in the on run

#### Scenario: The original setter runs once and a stamp failure does not reach the app

- **WHEN** an app calls `button.setOnClickListener(listener)` through the routed site and reading the view's delegate throws inside the stamp logic
- **THEN** `button.setOnClickListener(listener)` MUST have been called exactly once on the button, by virtual dispatch
- **AND** the app's next instruction MUST execute as if the call had returned normally
- **AND** when the app's own `setOnClickListener` override throws `IllegalStateException`, that exception MUST reach the app unchanged

#### Scenario: An app delegate set after the listener does not erase the stamp

- **WHEN** on API 30 an app calls `v.setOnClickListener(l)` and then `v.setAccessibilityDelegate(d)` through routed sites, and the platform builds `v`'s accessibility node
- **THEN** `v`'s delegate MUST be the stamp delegate with `d` chained behind it
- **AND** `d.onInitializeAccessibilityNodeInfo` MUST run once for that node
- **AND** the node's extras MUST carry `rvsec.click` = `l.getClass().getName()`

#### Scenario: Clearing a listener removes its key

- **WHEN** an app routes `v.setOnLongClickListener(l)` and later `v.setOnLongClickListener(null)`
- **THEN** a node built after the second call MUST NOT carry `rvsec.longClick`
- **AND** one `RVSEC-BIND` line with `kind=longClick` and `handler=-` MUST be written for the change

#### Scenario: A Compose clickable node is stamped with the app's lambda

- **WHEN** `dev.itsvic.parceltracker_10501000.apk` (Compose 1.7.8, names not renamed) is instrumented with `--stamp-handlers` and the platform populates the virtual node of the floating action button
- **THEN** `stampComposeSites` MUST be 1 for the APK
- **AND** the node's extras MUST carry `rvsec.click` naming an app class, such as `...MainActivityKt$ParcelAppNavigation$6$1$1$$ExternalSyntheticLambda1`
- **AND** one `RVSEC-BIND` line starting with `compose kind=click` MUST be written for that semantics id until its handler pair changes

#### Scenario: A Compose build with renamed internals is left unchanged

- **WHEN** an APK whose `AndroidComposeViewAccessibilityDelegateCompat` was renamed by R8 is instrumented with `--stamp-handlers`
- **THEN** `stampComposeSites` MUST be 0
- **AND** no instruction of that APK MUST differ from the off output except at View setter sites

#### Scenario: The helper source compiles against the platform alone

- **WHEN** `StampSourceEmitter.emit` writes `mop/RvsecStamp.java` and it is compiled with `javac -source 1.8 -target 1.8 -cp android.jar` (android-30)
- **THEN** compilation MUST succeed with no other jar on the classpath
- **AND** `StampSourceEmitter.remove` MUST delete `RvsecStamp.class` and every `RvsecStamp$*.class` and no other class file of the `mop` package

#### Scenario: A UiAutomation client receives the stamp

- **WHEN** an APK instrumented with `--stamp-handlers` is running on API 30, a View button and a Compose clickable node of the current window each have an `RVSEC-BIND` line naming handler classes `H1` and `H2`, and a probe connected through `UiAutomation` walks the window
- **THEN** the probe MUST read `rvsec.click = H1` from the View button's node extras
- **AND** it MUST read `rvsec.click = H2` from the Compose node's extras
