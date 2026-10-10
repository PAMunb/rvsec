## Purpose

The handler stamp of the `dexlib2` instrumenter (gh121) writes, into the `AccessibilityNodeInfo` extras of each clickable node, the class of the handler bound to it, so that a testing tool reading the tree through `UiAutomation` can key the node by its handler and take the handler's distance to a monitored operation from the static analysis. For a Compose node the helper `mop.RvsecStamp.composeNode` finds the handler by reflection, starting from the lambda of the node's `OnClick`/`OnLongClick` semantics action. This delta changes only how that lambda is unwrapped to the app's handler. Nothing in the woven bytecode, the counters or the log format changes.

Two compiled shapes of the Compose libraries hid the app's handler from the stamp as gh121 specified it.

The first is the capture field of the action lambda. The stamp reached the clickable modifier node through the field `this$0`, which kotlinc gives the outer instance of a lambda class. From `androidx.compose.foundation` 1.9 the action lambda is an invokedynamic that D8 desugars into a synthetic class (`AbstractClickableNode$$ExternalSyntheticLambdaN`) whose captures are named `f$0`, `f$1`, ...; the node is in `f$0`. Without `this$0` the stamp fell back to the class of the action lambda, a library class that no static-analysis handler table holds. In the Study 03 corpus this shape is in 69 of 163 APKs. `f$0` is a positional name, given to the first capture of any desugared lambda, so the stamp follows it only when the captured object is a foundation clickable node (`AbstractClickableNode` or a subclass). A sweep of the 92 corpus APKs with a Compose clickable node found no other captured `f$0` type that declares an `onClick` or `onLongClick` field. The type check therefore costs no real case, and it keeps an unrelated first capture from being read as a node.

The second is a Material wrapper. Some Material components do not hand the app's callback to the foundation modifier; they pass a lambda of their own that calls it. `Checkbox` passes `{ onCheckedChange(!checked) }`, compiled as `CheckboxKt$Checkbox$1$1` (`$onCheckedChange`, `$checked`) by kotlinc and as `CheckboxKt$$ExternalSyntheticLambda6` (`f$0`, `f$1`) by D8. The node's `onClick` is that wrapper, and the stamp named it. The second unwrap is structural, not a list of components: a handler whose class is in `androidx.compose.material*` and declares exactly one instance field typed as a Kotlin function interface is followed through that field once, and the value is stamped only when its class is outside `androidx.`. The rule reaches the app's callback in `Checkbox` in both compiled forms, and in the `DropdownMenuItem`/`ListItem` variants that take `checked`/`onCheckedChange`. Where the captured function is itself a library lambda, as in the DatePicker and TimePicker cells, the result is an `androidx.` class and the stamp keeps the handler it had. The rule therefore never replaces one `androidx.` class by another, and it attributes a click only to the function the Material wrapper holds.

Both unwraps are observations made inside the helper's existing `catch (Throwable)`; a failure leaves the stamp the gh121 resolution would have produced or no stamp, never an exception in the app.

## Data Contracts

### Input
- `semanticsNode: Object` — the `androidx.compose.ui.semantics.SemanticsNode` passed by the woven call after `populateAccessibilityNodeInfoProperties`; its unmerged `SemanticsConfiguration` holds the `OnClick`/`OnLongClick` `AccessibilityAction`, whose `getAction()` is the action lambda. Read by reflection only.

### Output
- `rvsec.click` / `rvsec.longClick` extras of the unwrapped `AccessibilityNodeInfo`, and `handler=` / `longClickHandler=` of the Compose `RVSEC-BIND` line — a binary class name. Unchanged in form; on a node where a foundation 1.9 action lambda or a Material wrapper is met, the name is now the app's handler class. Consumer: a `UiAutomation` client (APE-RV) and the logcat capture.

### Side-Effects
- None beyond gh121's: reflective field reads on objects of the running app, cached per class and member in the helper's `MEMBERS` map.

### Error
- None at run time on the device: every `Throwable` raised while unwrapping is caught by `composeNode` (INV-INS-177's guarantee for the helper).

## Invariants

- **INV-INS-178** (amended): The stamp delegate MUST forward every one of the ten `View.AccessibilityDelegate` callbacks to the chained app delegate when there is one and to the platform default otherwise, and a callback re-entered while it is being forwarded MUST go to the platform default. In `onInitializeAccessibilityNodeInfo`, after forwarding, it MUST set `rvsec.click` to the `getClass().getName()` of the last non-null click listener routed through the helper for that view, and remove the key when the last routed click listener was `null`; `rvsec.longClick` follows the same rule for long-click listeners. On API ≥ 29 the delegate the view carries when the stamp is first installed MUST be chained; below API 29 it cannot be read, and the stamp delegate replaces it. For a Compose node, `composeNode` MUST write the same keys into the extras of the unwrapped `AccessibilityNodeInfo`, with the handler resolved from the node's unmerged semantics configuration in two steps. **Node step:** for the `OnClick` / `OnLongClick` action, take the action's lambda (`getAction()`); its owner is the value of its `this$0` field when it has one, and otherwise the value of its `f$0` field when that value is an `androidx.compose.foundation.AbstractClickableNode` or an instance of a subclass; the `this$0` value is not checked to be a modifier node. With an owner, the handler is the owner's `onValueChange` field when the key is `onClick` and the owner is a `ToggleableNode`, otherwise, or when that field is null, its `onClick` / `onLongClick` field; with no owner, or when the field read is absent or null, the handler is the lambda itself. **Material step:** when the handler's class name starts with `androidx.compose.material` and that class declares exactly one non-static field whose declared type's name starts with `kotlin.jvm.functions.Function`, read that field once; when its value is non-null and its class name does not start with `androidx.`, the value is the handler; otherwise the handler is unchanged. The key MUST hold the handler's `getClass().getName()`. A key whose action is absent, or whose `getAction()` is null, MUST be removed.

## MODIFIED Requirements

### Requirement: Handler Stamp on the Accessibility Node

The `dexlib2` instrumenter SHALL offer an optional weave, selected by the `instr-cli` option `--stamp-handlers` and off by default, that makes the instrumented app write the class of the handler bound to each clickable node into that node's `AccessibilityNodeInfo` extras. The weave is independent of the MOP descriptor: it adds no monitor event, changes no site the advice weave touches, and does not change what is accused.

**Off is the unstamped output.** Without the option, the instrumenter SHALL produce byte-identical DEX files and the same `weaveCounts` keys as an instrumenter that has no handler-stamp weave (INV-INS-174). The monitor source directory and the `monitor-build` work directory are shared by every APK of a batch and by successive runs, so a run without the option SHALL remove a `mop/RvsecStamp` source or class file that an earlier run with the option left there; otherwise `MonitorBuilder`, which compiles every `.java` it finds, would put the helper into the monitor DEX of a run that did not ask for it. The option is on when the command line carries `--stamp-handlers`, or, with no option, when `RVSEC_STAMP_HANDLERS=true`; `--no-stamp-handlers` wins over the variable. A run turned on by the variable is recognisable from its output, because the `stamp*` counters exist in `weaveCounts` only when the stamp is on.

**View: routing the setters.** With the option on, `StampWeaver` (`dex-mutator`) SHALL rewrite each stamp candidate of INV-INS-176 into an `invoke-static` of the helper method of the same name in `mop.RvsecStamp`, whose first parameter is the receiver. The rewrite keeps the register list and the instruction size, so branch targets and try ranges are untouched (INV-INS-175). It applies to any owner the hierarchy resolves as a `View` subtype, app, androidx and Material code alike, because a listener set inside a library on a view the app inflated is still the handler of the node the tool clicks. The helper calls the setter by virtual dispatch, so an app subclass that overrides a setter still runs its override. `invoke-super` sites are left alone because they name an implementation the helper cannot call; they are counted. The stamp pass SHALL run after the advice weave and before the coverage weave, over the same mutable method bodies, so that every site it sees is the invoke the app compiled.

**View: what the helper does.** Each setter helper SHALL make the original call exactly once and only then update the stamp, inside `catch (Throwable)` (INV-INS-177). The stamp is a `View.AccessibilityDelegate` installed on the view on its first non-null listener. It forwards all ten delegate callbacks to the delegate the app had set, so the app's own accessibility behaviour is kept, except in the wrapping case of the known limits, and in `onInitializeAccessibilityNodeInfo` it adds `rvsec.click` and `rvsec.longClick` after forwarding (INV-INS-178). A delegate that wraps the delegate it finds on the view, as `ViewCompat` does, would call back into the stamp delegate; a re-entered callback therefore goes to the platform default; when the view carried an app delegate before the stamp, that delegate is then no longer called (see Known limits). When the app sets its own delegate on a view that already carries the stamp, the helper chains the app's delegate behind the stamp instead of letting it replace the stamp. From API 29 the delegate a view already carries when the stamp is first installed is read with `View.getAccessibilityDelegate()` and chained; that method does not exist below API 29, where the stamp delegate replaces a delegate the app set before the first listener. The campaigns run on API 30.

**Compose: after the node is populated.** A Compose screen has one `AndroidComposeView` and virtual accessibility nodes built from semantics; the app's click handler is a lambda passed to a modifier, not a listener set by a call that can be routed. Compose fills each virtual node in the private method `AndroidComposeViewAccessibilityDelegateCompat.populateAccessibilityNodeInfoProperties`, which cannot be routed through a helper because it is private. With the option on, the weaver SHALL insert, immediately after each call of that exact method, an `invoke-static` of `mop.RvsecStamp.composeNode(info, node)` over the call's own info and node registers; the call returns `void`, so both registers still hold their values. `composeNode` reads the node's unmerged semantics configuration by reflection and resolves the handler as INV-INS-178 states; its parameters are typed `Object` because the helper compiles against `android.jar` alone. The match is on the exact owner, name and descriptor (INV-INS-176): in a build whose Compose internals R8 renamed there is no match, no stamp, and no change to the APK.

**Compose: from the action lambda to the app's handler.** The clickable modifier node holds the app's lambda in its `onClick` / `onLongClick` field, and the action lambda the node registers in its semantics captures the node. How it captures it depends on how the foundation library was compiled. Up to foundation 1.8 the lambda is a kotlinc class and the node is its outer instance, in `this$0`. From 1.9 the lambda is an invokedynamic desugared by D8 into `AbstractClickableNode$$ExternalSyntheticLambdaN`, and the node is its first capture, in `f$0`. `composeNode` SHALL take the owner from `this$0` when the lambda has that field. Otherwise it SHALL take it from `f$0`, but only when the value is an `androidx.compose.foundation.AbstractClickableNode` or an instance of a subclass, which every foundation 1.9 clickable node is (`ClickableNode`, `CombinedClickableNode`, `ToggleableNode`, `TriStateToggleableNode`, `SelectableNode`). `f$0` names the first capture of any desugared lambda, including a `semantics { onClick(...) }` lambda an app writes itself. Without the type check, an app object that happens to declare an `onClick` field would be read as a node. The `this$0` branch keeps gh121's behaviour and checks no type.

**Compose: through a Material wrapper.** Some Material components pass the foundation modifier a lambda of their own that calls the app's callback: `Checkbox` passes `{ onCheckedChange(!checked) }`, so the node's `onClick` is a Material class. After the handler is resolved — from the node, or as the action lambda itself when there is no node — `composeNode` SHALL apply one more step. When the handler's class is in a package starting with `androidx.compose.material`, and that class declares exactly one non-static field whose declared type is a `kotlin.jvm.functions.Function*` interface, `composeNode` reads that field once. It stamps the value's class when the value is non-null and its class is outside `androidx.`, and otherwise keeps the handler it had. The step is structural, not a list of components, because the wrapper's class name is synthetic and changes between library versions and compilers: the `Checkbox` wrapper is `CheckboxKt$Checkbox$1$1` with `$onCheckedChange` under kotlinc and `CheckboxKt$$ExternalSyntheticLambda6` with `f$0` under D8. A wrapper is followed only one level, and only to a class outside `androidx.`. A click is therefore attributed only to the single function the wrapper holds and calls, and one `androidx.` class is never replaced by another. The check is on the `androidx.` prefix, not on the app: a function whose class is outside `androidx.` but is not the app's, such as a `kotlin.*` or third-party lambda, is stamped as well.

**The helper ships in the monitor DEX.** `StampSourceEmitter` (`monitor-builder`) SHALL write the fixed resource `RvsecStamp.java` as `mop/RvsecStamp.java` into the monitor source directory when the option is on, and `MonitorBuilder` compiles and dexes it with the monitors, as it does `mop.Coverage`. The source SHALL compile against `android.jar` alone at Java source level 1.8 and SHALL reference no androidx or Compose type at compile time. Placing the helper in the monitor DEX keeps the app DEXes under the 64K method-reference limit: replacing owner-specific setter references with at most four helper references lowers their method-id count.

**Counters.** With the option on, the instrumenter SHALL add, per APK, `stampClickSites`, `stampLongClickSites`, `stampDelegateSites`, `stampComposeSites`, `stampInvokeSuperSkipped` and `stampOwnerNotView` to `weaveCounts` (INV-INS-176). A zero `stampComposeSites` on an APK that uses Compose is the measurable sign of a renamed library.

**Verification log.** The helper SHALL log every change of a stamp under the logcat tag `RVSEC-BIND` (INV-INS-179), so that the stamp can be checked from a logcat capture without any change to the testing tool; the platform's capture keeps the tag (core INV-CORE-53). The line carries the node's accessibility class, the resource name when there is one, and the handler class; Compose lines also carry the semantics id and the screen bounds.

**Delivery to an accessibility client.** The stamp is useful only if the extras reach the process that reads the accessibility tree. The extras SHALL be readable by a client of `UiAutomation`: for a node whose stamp the helper logged under `RVSEC-BIND`, `AccessibilityNodeInfo.getExtras()` obtained through `UiAutomation` SHALL carry `rvsec.click` / `rvsec.longClick` with the handler class of the node's last `RVSEC-BIND` line, for View and for Compose nodes. This is checked on a device by a minimal probe that connects to `UiAutomation` the way APE-RV does (`app_process`) and prints the `rvsec.*` extras of every node of the current window.

**Known limits.** A stamp names the class of the listener object the app passed, and in three cases that class is not the app's handler or there is no stamp; in a fourth, the stamp delegate drops an app delegate from the accessibility tree. They are limits of the stamp, not defects to repair in this requirement:

- **XML `android:onClick`.** Under AppCompat the inflater sets an `AppCompatViewInflater$DeclaredOnClickListener` through `setOnClickListener`, so the stamp carries that generic class; the app method's name is in its `mMethodName` field, which the helper does not read. In one measured APK (`scep`) this was 42 of 134 `RVSEC-BIND` lines.
- **Library dispatchers.** The toolbar navigation button, menu items and `SearchView` stamp the library's own listener (`ToolbarWidgetWrapper$1`, `ActionMenuItemView`, `SearchView$5`), which hands off to an app callback such as `onOptionsItemSelected`. AppCompat `AlertDialog` buttons and androidx `Preference` rows are in the same case: `AlertController.setupButtons` sets the dialog's `mButtonHandler` on each button, and `Preference.onBindViewHolder` sets the preference's `mClickListener` on the row's view, both through routed `setOnClickListener` sites, so the stamp names that library listener. These sites are routed in the stamped APKs of the device verification; no such dialog or preference screen was opened there, so their stamp was not observed.
- **Not covered.** The framework `android.app.AlertDialog` and `android.preference` set their listeners in framework code, which is not in the APK and is not rewritten, so their buttons and rows are not stamped.
- **An app delegate set before the stamp, then wrapped.** When a view already carries an app delegate when the stamp is first installed, that delegate is chained (API ≥ 29). If later code reads the view's current delegate — the stamp delegate — wraps it and sets the wrapper, as androidx `ViewCompat` does when it adds or replaces an accessibility action and RecyclerView's item delegate does on an item view that already had a delegate, the helper chains the wrapper in place of the earlier app delegate. The wrapper calls back into the stamp delegate, that re-entered callback goes to the platform default (INV-INS-178), and the earlier app delegate is no longer called. The stamp keys and the wrapper's additions stay on the node; what the earlier delegate added to it, such as the virtual children an `ExploreByTouchHelper` exposes for a Material chip's close icon, is missing from the tree a `UiAutomation` client reads. The app's behaviour outside accessibility is unchanged. The device verification did not exercise this sequence.

The Compose resolution has limits of the same kind:

- **A Material wrapper with more than one function, or holding a library function.** The Material step follows a wrapper only when it captures exactly one function, and stamps the result only when that function's class is outside `androidx.`. A wrapper that captures two functions keeps its own class. So does a wrapper whose function is the library's own, as in the DatePicker day and year cells and the TimePicker clock, which call the picker's internal selection callbacks; there the app reads the chosen value from the picker's state and has no click handler to name.
- **Text-field semantics.** `CoreTextFieldSemanticsModifierNode` and `TextFieldDecoratorModifierNode` register click and long-click actions for focus and the context menu; the node holds no app handler, and the stamp names the Compose-internal action lambda.
- **Renamed Kotlin function interfaces.** The Material step recognises the wrapper's capture by its declared type name, `kotlin.jvm.functions.Function*`. In an app whose build keeps the Compose names but lets R8 rename the Kotlin function interfaces, no field matches, the step does not apply, and the stamp keeps the Material wrapper's class. Nothing fails; the sign is an `androidx.compose.material*` class in the node's `RVSEC-BIND` line.

A Compose text field reports a Compose-internal handler class, and an activity that implements `View.OnClickListener` for several buttons stamps the activity on all of them; the stamp's granularity is the handler class, not the branch of a `switch` inside it.

#### Scenario: Off reproduces the instrumenter without the stamp byte for byte

- **WHEN** `dev.itsvic.parceltracker_10501000.apk` is instrumented twice with the same `jca_android` descriptor, the same runtime jars, `d8` 35.0.1 and `android-36/android.jar` — once by an `instr-cli.jar` built without the handler-stamp weave, and once by the `instr-cli.jar` that has it, without `--stamp-handlers` and with `RVSEC_STAMP_HANDLERS` unset
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

#### Scenario: Super and non-View setter sites are left unchanged and counted

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

#### Scenario: A foundation 1.9 action lambda is unwrapped through f$0

- **WHEN** a node's `OnClick` action lambda is an instance of `androidx.compose.foundation.AbstractClickableNode$$ExternalSyntheticLambda1` with no `this$0` field and `f$0` holding a `ClickableNode` whose `onClick` is an instance of `com.luk.saucenao.MainScreenKt$$ExternalSyntheticLambda43`
- **THEN** `rvsec.click` MUST be `com.luk.saucenao.MainScreenKt$$ExternalSyntheticLambda43`
- **AND** for a `ToggleableNode` in `f$0` with a non-null `onValueChange`, `rvsec.click` MUST name the class of `onValueChange`

#### Scenario: An f$0 that is not a clickable node is not read as one

- **WHEN** a node's `OnClick` action lambda is an app class `com.example.ScreenKt$$ExternalSyntheticLambda0` with no `this$0` field and `f$0` holding an app object of class `com.example.RowState` that declares a non-null field `onClick`
- **THEN** `rvsec.click` MUST be `com.example.ScreenKt$$ExternalSyntheticLambda0`
- **AND** the `onClick` field of the `RowState` object MUST NOT be read

#### Scenario: A Material Checkbox wrapper is unwrapped in both compiled forms

- **WHEN** the handler resolved from the node is an instance of `androidx.compose.material3.CheckboxKt$$ExternalSyntheticLambda6` whose only function-typed field `f$0` holds an instance of `com.example.SettingsKt$$ExternalSyntheticLambda7`, besides a `boolean` field `f$1`
- **THEN** `rvsec.click` MUST be `com.example.SettingsKt$$ExternalSyntheticLambda7`
- **AND** with the handler an instance of `androidx.compose.material3.CheckboxKt$Checkbox$1$1` whose fields are `$checked: boolean` and `$onCheckedChange: Function1` holding an instance of `com.example.SettingsKt$Row$1$1`, `rvsec.click` MUST be `com.example.SettingsKt$Row$1$1`

#### Scenario: A Material wrapper is kept when its function is a library class or it holds two functions

- **WHEN** the handler resolved from the node is an instance of `androidx.compose.material3.DatePickerKt$$ExternalSyntheticLambda12` whose only function-typed field holds an instance of `androidx.compose.material3.DatePickerKt$$ExternalSyntheticLambda3`
- **THEN** `rvsec.click` MUST be `androidx.compose.material3.DatePickerKt$$ExternalSyntheticLambda12`
- **AND** for a handler of class `androidx.compose.material3.SomeKt$$ExternalSyntheticLambda2` declaring two `Function0` fields that hold app lambdas, `rvsec.click` MUST be that `androidx.compose.material3` class
- **AND** the Material step MUST NOT be applied to a handler whose class is outside `androidx.compose.material`, such as `androidx.compose.foundation.text.input.internal.CoreTextFieldSemanticsModifierNode$$ExternalSyntheticLambda12`

#### Scenario: A Compose app on foundation 1.9 stamps app classes on a device

- **WHEN** `com.luk.saucenao_27.apk` (foundation 1.9.5, material3 1.4.0) is instrumented with `--stamp-handlers` by the `instr-cli.jar` of this requirement and explored for 300 s on API 30 by APE-RV with the MOP guide on
- **THEN** no Compose `RVSEC-BIND` line MUST name `androidx.compose.foundation.AbstractClickableNode$$ExternalSyntheticLambda1` or `androidx.compose.material3.CheckboxKt$$ExternalSyntheticLambda6`
- **AND** every app class named by a Compose `RVSEC-BIND` line MUST be a key of the `handlers` table of the APK's derived MOP artifact
- **AND** no crash MUST carry a frame of `mop.RvsecStamp`, and no `VerifyError` MUST be logged
