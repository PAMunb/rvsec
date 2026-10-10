## Context

The handler stamp of gh121 (instrumentation `Requirement: Handler Stamp on the Accessibility Node`, INV-INS-178) resolves a Compose node's handler inside `mop.RvsecStamp.composeHandler`. The class is a fixed Java resource of the rvsec reactor:

`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/monitor-builder/src/main/resources/br/unb/cic/rv/builder/stamp/RvsecStamp.java`

`StampSourceEmitter` writes it into the monitor source directory, and `MonitorBuilder` compiles and dexes it with the monitors. Today, `composeHandler` (lines 243–265) reads `this$0` from the action lambda, reads `onValueChange` or `onClick`/`onLongClick` from that owner, and falls back to the lambda's own class. The proposal records the two shapes it misses: the D8 capture `f$0` in foundation ≥ 1.9, and the Material wrapper around the app's callback. It also records the corpus measurements and the device A/B behind them (`docs/20261009_e03mini-smoke.md`, `data/e03mini_a2/`, `data/e03mini_a2/sweep_stamp/`). FR02 (APK instrumentation with monitors) is the requirement served.

Constraints carried over from gh121:
- The helper compiles against `android.jar` alone at `-source 1.8` and references no androidx, Compose or Kotlin type at compile time. Every library type is recognised by name through reflection.
- Every failure inside the helper is caught (`composeNode` wraps `composeStamp` in `catch (Throwable)`).
- Reflected members are cached per `class#member` in `MEMBERS`, so a lookup costs one map read after the first node of a class.

No Python module changes. The `instr-cli.jar` that the reactor build copies to `rv-android/lib/` is the deliverable consumed by `rv-instrumentation-dexlib2`.

## Architecture

```
populateAccessibilityNodeInfoProperties(info, node)        (Compose, app DEX)
        │  woven invoke-static (unchanged)
        ▼
RvsecStamp.composeNode → composeStamp                       (monitor DEX)
        │  for OnClick / OnLongClick
        ▼
composeHandler(config, key, field)
   1. action lambda  fn = config.get(key).getAction()
   2. owner = read(fn,"this$0")  ?:  clickableNode(read(fn,"f$0"))      ← gap 1
   3. handler = owner? (ToggleableNode && onClick ? onValueChange : field) : fn
   4. handler = materialUnwrap(handler)                                 ← gap 2
   5. return handler.getClass().getName()
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `RvsecStamp.composeHandler` | Node step + Material step for one action key | `SemanticsConfiguration`, action key, field name | handler class name or `null` |
| `RvsecStamp.materialUnwrap` (new, private) | One structural unwrap of an `androidx.compose.material*` wrapper | handler object | the wrapped app function, or the input |
| `RvsecStamp.isA` (existing) | Superclass walk by name | object, class name | boolean |
| `RvsecStamp.read` (existing) | Cached declared-field read up the superclass chain | object, field name | value or `null` |
| `RvsecStampComposeTest` (new, `monitor-builder` test) | Compiles the emitted source with fixture classes and drives `composeHandler` by reflection on the JVM | fixture objects | asserted class names |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-INS-178 node step, `this$0` unchanged | `composeHandler` | `RvsecStampComposeTest.thisZeroOwnerIsReadAsBefore` |
| INV-INS-178 node step, `f$0` on a foundation node | `composeHandler` + `isA(.., AbstractClickableNode)` | `fZeroClickableNodeIsUnwrapped`, `fZeroToggleableReadsOnValueChange`, `fZeroCombinedLongClick` |
| INV-INS-178 node step, `f$0` not a node | `composeHandler` | `fZeroOtherObjectIsNotRead` |
| INV-INS-178 Material step | `materialUnwrap` | `checkboxD8FormIsUnwrapped`, `checkboxKotlincFormIsUnwrapped`, `wrapperOfLibraryFunctionIsKept`, `wrapperWithTwoFunctionsIsKept`, `nonMaterialHandlerIsNotUnwrapped`, `nullFunctionIsKept` |
| Scenario: helper compiles against the platform alone | unchanged | `StampSourceEmitterTest.theSourceCompilesAgainstAndroidJarAtJava8` |
| Scenario: Compose app on foundation 1.9 on a device | whole chain | device smoke (tasks group 4) |

## Goals / Non-Goals

**Goals:**
- Stamp the app's handler on Compose nodes built by foundation ≥ 1.9.
- Stamp the app's callback behind a single-function Material wrapper, in both compiled forms.
- Cover the resolution with JVM tests, which gh121 did not have for Compose.

**Non-Goals:**
- Any change to the woven `.dex` sites, the six `stamp*` counters, the `RVSEC-BIND` line format, the View stamp, the MOP weave, `RVSEC`/`RVSEC-OCC` or `RVSEC-COV`.
- Wrappers with more than one function, library-internal callbacks (DatePicker/TimePicker cells), text-field semantics, Kotlin function interfaces renamed by R8 (kept as known limits).
- Re-instrumenting the Study 03 corpus, rebuilding the Docker image, or recording the corpus in the replication package.
- APE-RV: it reads the same keys.

## Decisions

**D1 — `f$0` is followed only to an `AbstractClickableNode`.** The researcher decided this on 10/10/2026. `f$0` is positional, the first capture of any D8-desugared lambda, so without a check an app's own `semantics { onClick(...) }` lambda that captures an object with an `onClick` field would be read as a node. The corpus sweep found no such object, and every foundation 1.9 clickable node is a subclass of `AbstractClickableNode` (verified in `com.luk.saucenao_27`: `ToggleableNode`, `TriStateToggleableNode` and `SelectableNode` extend `ClickableNode`, which, like `CombinedClickableNode`, extends `AbstractClickableNode`). The check therefore loses no measured case. *Alternative:* follow `f$0` unchecked, as the A/B copy did. It was rejected because it widens the rule beyond what was measured. *Alternative:* add the same check to `this$0`. Not chosen: it was not asked for, and in the older foundation the `this$0` owner can be `ClickableSemanticsNode`, which extends `Modifier$Node` and not `AbstractClickableNode` (verified in `app.plugbrain.android_154`). A check there would regress the 3 APKs of that shape.

**D2 — the Material step is structural.** The researcher decided this on 10/10/2026. The rule applies when the class name starts with `androidx.compose.material`, the class declares exactly one non-static field whose declared type name starts with `kotlin.jvm.functions.Function`, the value is non-null, and the value's class does not start with `androidx.`. Synthetic wrapper names vary by compiler and version (`CheckboxKt$Checkbox$1$1` versus `CheckboxKt$$ExternalSyntheticLambda6`), so a name list would need upkeep per library release. *Alternative:* a list of known wrappers. Rejected for that reason. *Alternative:* keep it as a known limit. The researcher chose to repair it.

- **Declared fields of the handler's class only.** The fields are read with `getDeclaredFields()` of the handler's class only, not its superclasses. Both compiled forms keep their captures on the class itself: kotlinc lambdas extend `kotlin.jvm.internal.Lambda`, whose only field is `arity: int`, and D8 lambdas extend `Object`.
- **The declared type, not the value's class, decides.** Both forms declare the capture as the function interface (`Lkotlin/jvm/functions/Function1;`). Counting declared types is therefore stable whatever the value is.
- **One level, and only out of `androidx.`.** A wrapper whose function is itself a library lambda keeps the outer class. The step never trades one `androidx.` name for another, and never walks a chain. The prefix test does not identify the app: a `kotlin.*` or third-party function outside `androidx.` is stamped too.
- **The step also applies to the action-lambda fallback.** When the node step finds no owner, the handler is the action lambda itself, and the Material step applies to it as to any resolved handler. That is the decision's literal reading ("the resolved handler"). It matters for Material scrims and dropdowns whose action lambda captures one `Function0`. The corpus sweep recorded the declared type of those captures (`Function0`), not the runtime class of their values. When the value is an app lambda (an app's `onDismissRequest`, for example), the click is attributed to it. That lambda is what the scrim click calls. When the value is a library lambda, the `androidx.` check keeps the outer class. The device smoke reports every line where the fallback was unwrapped (task 4.4).

**D3 — JVM tests compile the emitted source with fixture classes.** `composeHandler` touches no Android API: it uses reflection, `isA`, `read` and `call`. The test compiles `RvsecStamp.java`, as `StampSourceEmitter.emit` writes it, against `android.jar` together with small fixture sources compiled in the same `javac` call:
- `androidx.compose.foundation.AbstractClickableNode`, `ClickableNode`, `CombinedClickableNode` and `androidx.compose.foundation.selection.ToggleableNode`, carrying the real field names;
- `kotlin.jvm.functions.Function0`/`Function1` interfaces;
- `androidx.compose.material3.CheckboxKt$$ExternalSyntheticLambda6`, `CheckboxKt$Checkbox$1$1` and a two-function wrapper;
- a fake configuration and action.

The test loads the output with a `URLClassLoader` over `[out, android.jar]` and calls the private static `composeHandler` reflectively. Loading `mop.RvsecStamp` runs only constant and collection initialisers, so the `android.jar` stubs are never invoked. The test is `@EnabledIf("canCompile")` like the existing compile test, so a machine without `android.jar` skips it rather than failing. *Alternative:* test only on a device. That was rejected: the device run cannot reach every branch (the two-function wrapper, the null function, the non-node `f$0`).

**D4 — the device smoke reuses the A/B harness.** The A/B of 10/10 used `data/e03mini_a2/instrument_ab.py` to instrument on the host through `DexlibInstrumentation` with `--stamp-handlers`, then ran image `1f34ddec` with `docker/docker-compose.e03mini-a2.yml` (APE-RV, `flag` and `distance` arms, 300 s). The smoke runs the same way, with the jar built by this change. The APKs:
- `com.luk.saucenao_27` (foundation 1.9.5, Checkbox);
- `at.techbee.jtx_216000015` (1.9, DatePicker/TimePicker);
- one foundation 1.7/1.8 app with Checkbox, `this$0` shape (for example `app.plugbrain.android_154`).

The emulator is managed by rv-platform only.

## API Design

### `private static String composeHandler(Object config, Object key, String field) throws Exception`

Same contract as today, with the two steps of INV-INS-178.
- **Pre:** `config` is a `SemanticsConfiguration` and `key` a `SemanticsPropertyKey`, or `key` is null.
- **Post:** returns `null` when the action is absent or its `getAction()` is null. Otherwise it returns the class name of the handler after the node step and the Material step.
- **Errors:** propagate to `composeNode`, which swallows them.

### `private static Object materialUnwrap(Object handler)`

- **Pre:** `handler` is non-null.
- **Post:** returns `handler` unless all of these hold:
  - `handler.getClass().getName()` starts with `androidx.compose.material`;
  - exactly one non-static declared field has a type name starting with `kotlin.jvm.functions.Function`;
  - that field's value is non-null;
  - the value's class name does not start with `androidx.`.

  When they all hold, it returns that value.
- **Caching:** the field lookup (the single matching `Field`, or none) is cached per class in `MEMBERS` under a dedicated key (`<class>#materialFn`). The structural scan therefore runs once per wrapper class.
- **Errors:** `IllegalAccessException` and similar propagate to `composeNode`.

## Data Flow

Unchanged from gh121, up to the name returned by `composeHandler`. That name is written to the node's extras, and to `COMPOSE_LOGGED` and `RVSEC-BIND` when the `click|longClick` pair of the semantics id changes. A node that now resolves to an app class logs one new `RVSEC-BIND` line for its id, because the pair changed. That is the existing logging rule of INV-INS-179.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `NoSuchFieldException` / missing field | `read` returns `null` for an absent field | treated as "no owner" / "no handler" | falls back as INV-INS-178 states |
| `IllegalAccessException`, `SecurityException`, `InaccessibleObjectException` | `setAccessible` / `Field.get` on the device | propagates to `composeNode` | `catch (Throwable)`; the node keeps the extras the platform wrote, without the stamp |
| `ClassCastException` on a fixture or an unexpected owner | `isA` is name-based and does not cast | not raised | — |

## Risks / Trade-offs

- **[Risk]** A Material wrapper that captures one app function it does not call on click would stamp that function. → The step requires a class in `androidx.compose.material*` with exactly one function capture. The cases met in the corpus (Checkbox, checked DropdownMenuItem and ListItem, picker cells, scrims) either call the captured function on click or hold a library function, which is kept. The smoke lists every unwrapped Material class it sees (task 4.4).
- **[Risk]** A future foundation release could change the capture shape again, for example to a node captured in `f$1`. → The stamp then falls back to the library lambda, as today. A `RVSEC-BIND` line naming `AbstractClickableNode$$ExternalSyntheticLambda*` is the visible sign, and the corpus survey script (`data/e03mini_a2/strict.sh`) detects the shape statically.
- **[Risk]** R8 renames `kotlin.jvm.functions.Function*` in an app that keeps the Compose names. → No declared field matches, the Material step does not apply, and the stamp keeps the wrapper's class; silent but visible as an `androidx.compose.material*` class in `RVSEC-BIND`. Recorded as a known limit.
- **[Trade-off]** The monitor DEX of every stamped APK changes bytes. → Expected: the helper is in the monitor DEX. The app DEXes, the MOP weave and the counters do not change (task 3.2 checks this).

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (JVM) | Node step and Material step, every branch of INV-INS-178's Compose clause | `RvsecStampComposeTest`: emitted source plus fixtures compiled with `android.jar`, reflection | ~11 tests |
| Unit (JVM) | The helper still compiles against the platform alone | existing `StampSourceEmitterTest` | 3 tests (unchanged) |
| Build | Reactor build, `instr-cli.jar` regenerated | `mvn clean install -DskipMopAgent -DskipTests` (JDK 21, `-o`), then module tests | — |
| Instrumentation | Off/on equivalences hold: app DEXes and `weaveCounts` equal to the previous jar on the same APK | instrument saucenao with the old and the new jar, compare app DEXes and counters | 1 APK |
| Device smoke | Compose `RVSEC-BIND` names app classes in `handlers`; no helper crash or `VerifyError` | A/B harness, 3 APKs, `distance` arm, 300 s, 1 rep | 3 runs |

## Open Questions

None.
