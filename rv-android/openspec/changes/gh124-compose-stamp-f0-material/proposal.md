GitHub Issue: #124

## Why

In most Compose apps of the Study 03 corpus, the Compose handler stamp of #121 does not name the app's handler. The cause is two independent gaps in `RvsecStamp.composeHandler` (instrumentation INV-INS-178). The guide MOP of APE-RV keys a Compose click by the stamped class and matches it against the `handlers` table of the static analysis, which holds only app classes. A stamp that names a library class therefore never matches, and the guide does not act on that click. The flag × distance comparison planned for `e03mini` and E6 v2 cannot measure distance on those nodes until both gaps are closed and the corpus is instrumented again.

**Gap 1 — the `f$0` capture.** The stamp reaches the clickable modifier node through the `this$0` field of the `OnClick`/`OnLongClick` action lambda. That field exists when the Compose foundation library was compiled by kotlinc into a lambda class (`AbstractClickableNode$applySemantics$1`, foundation 1.6–1.8). From foundation 1.9 the lambda is an invokedynamic that D8 desugars into `AbstractClickableNode$$ExternalSyntheticLambdaN`, and the node sits in the field `f$0`. With no `this$0`, the stamp names the library lambda itself. Measured on the corpus bytecode (`data/e03mini_a2/survey.csv`), this happens in 69 of 163 APKs: 38 of 50 compose-only, 29 of 37 mixed, and 2 view-only with embedded Compose. A device A/B on `com.luk.saucenao_27` and `at.techbee.jtx_216000015` compared the jar in the repository with a copy that also reads `f$0` (`docs/20261009_e03mini-smoke.md`, "Achado 2"). With the copy, `stampHits` rose from 0 to 85–367, the guide decided 34–77 steps, and every app class the stamp named was in `handlers`.

**Gap 2 — a Material component wraps the app's callback.** Once the stamp reaches the node, the node's `onClick` can be a lambda of the Material library that calls the app's callback, not the app's callback itself. Material3 and Material `Checkbox` pass `{ onCheckedChange(!checked) }` to `triStateToggleable`. In the kotlinc form the lambda is `CheckboxKt$Checkbox$1$1`, with fields `$onCheckedChange: Function1` and `$checked: Z`. In the D8 form it is `CheckboxKt$$ExternalSyntheticLambda6`, with `f$0: Function1` and `f$1: Z`. The stamp names the Material class. App code calls `Checkbox` in 55 APKs (material3) and 3 (material), in both compiled forms. Gap 2 is therefore not limited to the APKs of gap 1. In the A/B, 262 of 630 `RVSEC-BIND` lines of saucenao were Checkbox nodes.

A sweep of the 92 corpus APKs with a Compose clickable node bounds the risk of reading `f$0` (`data/e03mini_a2/sweep_stamp/`). Among all calls of `SemanticsPropertiesKt.onClick`/`onLongClick`, library and app, the only captured `f$0` types that declare an `onClick` or `onLongClick` field are `AbstractClickableNode` and `CombinedClickableNode`. Both are what the stamp is meant to reach. In the 16 app-code calls (13 APKs), `f$0` is a `Function0`, a `boolean`, a `View` or an app state class without such a field. The same sweep shows that `Switch`, `RadioButton`, `FilterChip`, `TriStateCheckbox` and `IconToggleButton` pass the app's callback straight to the foundation modifier, so the stamp already names it. The DatePicker and TimePicker cells wrap the picker's own internal callbacks, not an app callback.

## What Changes

- **`f$0` unwrap with a type check.** When the action lambda has no `this$0`, `composeHandler` reads `f$0` and treats it as the clickable node only if it is an `androidx.compose.foundation.AbstractClickableNode` or a subclass. Every foundation 1.9 clickable node is such a subclass: `ClickableNode`, `CombinedClickableNode`, `ToggleableNode`, `TriStateToggleableNode` and `SelectableNode`. From there the resolution is today's: `onValueChange` for a `ToggleableNode` under `onClick`, otherwise `onClick`/`onLongClick`. The `this$0` branch is unchanged, including its absence of a type check.
- **Second unwrap for a Material wrapper.** After the handler object is resolved, as the node's field or as the action lambda itself, the stamp applies one more step. If the handler's class is in a package starting with `androidx.compose.material`, and the class declares exactly one instance field whose declared type is a `kotlin.jvm.functions.Function*` interface, the stamp reads that field once. It names the value's class only if that class is outside `androidx.`; otherwise it keeps the handler it had. The step is not repeated.
- **Known limits updated.** The requirement's known limits state what the second unwrap still does not reach: a Material wrapper with two or more captured functions, a wrapper whose captured function is itself a library lambda (the DatePicker/TimePicker cells), the text-field semantics nodes, which carry no app handler, and an app whose R8 build renamed the Kotlin function interfaces, where the Material step finds no function field and keeps the wrapper's class.
- **Unchanged.** The `.dex` weave of the stamp, its sites and its six `stamp*` counters; the MOP weave and `weaveCounts`; `RVSEC`/`RVSEC-OCC`; `RVSEC-COV`; the `RVSEC-BIND` line format; the View stamp. Only the class name the Compose stamp writes into `rvsec.click`/`rvsec.longClick` and into `handler=`/`longClickHandler=` changes, on nodes where one of the two gaps applies.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `instrumentation`: INV-INS-178 (Compose handler resolution) is amended, and `Requirement: Handler Stamp on the Accessibility Node` gains the two unwrap steps, updated known limits and scenarios for the foundation 1.9 form and the Material wrapper.

## Impact

- **Code:** `RvsecStamp.java` (resource of rvsec `rvsec-instrumentation-dexlib2/monitor-builder`, compiled into the monitor DEX) and a new JVM test of its Compose resolution in `monitor-builder`. The `instr-cli.jar` that the reactor build copies to `rv-android/lib/` changes with it.
- **Python modules:** none. `rv-instrumentation-dexlib2` forwards `--stamp-handlers` exactly as before (INV-INS-180).
- **Consumers:** APE-RV reads `rvsec.click`/`rvsec.longClick` unchanged in form. The stamped class names change on the affected nodes, which is the point of the change. The `handlers` table of the aperv-tool derive already lists app classes declaring `invoke(Object)Object`, the bridge of the `Function1` an app passes as `onCheckedChange`.
- **Measurements:** a corpus instrumented before this change keeps its stamp. Re-instrumenting the Study 03 corpus, rebuilding the image and recording the new corpus in the replication package belong to the campaign and replication-package work, not to this change.
- **FRs/NFRs:** FR02 (APK instrumentation with monitors), the stamp option of FR02.
