## Context

The handler stamp (gh121, gh124) writes the class of the click listener bound to a view into the
node's `rvsec.click` extra. APE-RV's MOP guide looks that class up in the `handlers` table of the
artifact that `aperv-tool` derives from the GATOR `.apk.json` (`aperv` spec, "MOP Artifact
Projection Contents"). For menu, navigation and toolbar items, androidx `Preference` rows and
AppCompat dialog buttons, the bound listener is a library dispatcher. The table has no record for
a dispatcher, and the derive records no class for the app callback behind it, so the guide gives
these clicks no weight. The proposal gives the measurements (e03igg, sections B, K, N of
`data/e03igg_analysis/out/rp_guidance/RESULTS.md`) and the device A/B (`experimento-stampcb/`,
README "Resultados").

The stamp code this change specifies was written for that A/B and ran in it. At the time of
writing it sits uncommitted in the worktree: `RvsecStamp.callback()`, its helpers, the
`Delegate.clickListener` field, the `kind=callback` log line, and `RvsecStampCallbackTest` with
its fixtures. The A/B's derive was an experiment copy, `experimento-stampcb/mount/treatment/`,
built with `derive_treatment.patch` on top of the branch derive. The change carries both into the
code base with the specification, tests and documentation they lack.

The change is built on branch `isolate-guidance-groups` (c6865a73) of the rvsec repository, by the
researcher's decision of 2026-10-19, and never on `modules`. That branch's
`derive_mop_artifact.py` is byte-identical to the A/B control's, so the derive implemented here is
the one the A/B measured. The ape repository's branch of the same name holds the jar, which this
change does not touch.

FRs: FR02 (APK instrumentation, the stamp option), FR06 (the derived reachability artifact), FR20
(the `aperv:mop` variant whose guide reads the stamp).

## Architecture

```
 app process (device)                                   host
 ─────────────────────                                  ────
 routed setOnClickListener(v, l)                        GATOR .apk.json
   └─ RvsecStamp.stamp → Delegate.clickListener = l       └─ reachability[].methods[].signature
 platform builds v's node                                     │
   └─ Delegate.onInitializeAccessibilityNodeInfo              ▼
        click = class(l)                                 aperv-tool derive_mop_artifact.derive()
        cb = RvsecStamp.callback(v, l)   (reflection)      _handler_events(signature)
        cb != null → click = cb, log kind=callback           onClick(View) | callbacks → "click"
        extras["rvsec.click"] = click                       handlers[class].{mop,dist}.click
              │                                                   │  <apk>.mop.json → device
              ▼                                                   ▼
        APE-RV (UiAutomation) reads rvsec.click ──► MopData.lookup(handlers[class]) ──► dec.mopd
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `RvsecStamp.Delegate.onInitializeAccessibilityNodeInfo` (`rvsec/rvsec-android/rvsec-instrumentation-dexlib2/monitor-builder/src/main/resources/br/unb/cic/rv/builder/stamp/RvsecStamp.java`) | Writes `rvsec.click`, substituting the resolved callback; logs `kind=callback` once per change | the view, the routed listener | node extras, `RVSEC-BIND` line |
| `RvsecStamp.callback(View, Object)` and helpers (`menuCallback`, `optionsMenuCallback`, `preferenceCallback`, `dialogCallback`, `firstAppProvider`, `activityOf`, `appClassOf`, `isAppClass`, `readTyped`) | Resolves the app callback behind a dispatcher (INV-INS-181) | view, listener | class name or `null` |
| `derive_mop_artifact._handler_events` and `HANDLER_METHOD_PATTERN` (`rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`) | Maps a method signature to the events it fills (INV-DRV-11) | Soot signature | tuple of events |
| `derive_mop_artifact.derive` (handler-record loop) | Merges every method of one class and event by OR of flags and minimum per target (unchanged) | `reachability[]` | `handlers` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-INS-181 (resolution order, app-class test) | `RvsecStamp.callback` and helpers | `RvsecStampCallbackTest`, 16 JVM tests: the preference chain (a library candidate does not count; the tree-click step names the declaring class or nothing), the dialog button's `Message.obj`, a menu item's own `mClickListener`, the first app menu provider, the options menu from the activity on (the declaring base class; another parameter list does not count), an app-bound listener, an unresolved `SearchView$5`, a failing read propagating out of `callback`; device: the navigation, navigation-bar and toolbar walk and the view-to-activity step, which call final `View` methods (A/B, task 4.3), and the D10 options-menu result on bitbanana (task 6.5) |
| INV-INS-178 (amended: `rvsec.click` holds the callback) | `Delegate.onInitializeAccessibilityNodeInfo` | device only (`AccessibilityNodeInfo` is a stub on the JVM): scenario "Stamped APKs explored on a device…", run by the A/B (task 4.3) |
| INV-INS-179 (amended: `kind=callback` line once per change) | `Delegate.loggedCallback` | device only (`Log` is a stub on the JVM): the A/B's `kind=callback` lines (task 4.3) |
| INV-INS-177 (no throw) for the lookup | `catch (Throwable)` around `callback` | JVM: a failing read propagates out of `callback` and returns nothing partial (`RvsecStampCallbackTest`); the delegate's catch keeping the class on the node: device (no `mop.RvsecStamp` crash frame in the A/B) |
| INV-DRV-11 (callback methods fill `click`; other parameter lists do not; merge) | `HANDLER_METHOD_PATTERN`, `CALLBACK_PARAMS`, `_handler_events` | `test_derive_mop_artifact.py`: the three new scenarios of the `aperv` delta |
| INV-INS-174/175/176 (weave unchanged) | no change to `StampWeaver` or the emitter | existing `dex-mutator` and `monitor-builder` tests stay green |

## Goals / Non-Goals

**Goals:**
- Name the app callback in `rvsec.click` for menu, navigation and toolbar items, androidx
  preference rows and AppCompat dialog buttons, with no change to the jar.
- Give those callback classes a `click` record in `handlers`.
- Specify the resolution, its limits and the new log line so the A/B code is documented and
  tested.

**Non-Goals:**
- Item-level precision for menus: the stamp names a class, and the static distance is per method.
- A separate `rvsec.callback` key with a jar change ("option 2"): the researcher chose option 1.
- `AdapterView.onItemClick`, `CompoundButton.onCheckedChanged`, `SearchView`, the overflow popup,
  the framework `AlertDialog` and `android.preference`.
- A Material `TabLayout` tab's `onTabSelected`: tab selection does not go through a routed
  `setOnClickListener`, so the tab carries no stamp and the derive records no `onTabSelected`.
- GATOR's `#OptionsMenu` items, which carry ids but no listener; that work belongs to the
  `analise-estatica` session's change.
- Re-instrumenting the Study 03 corpus, rebuilding the image, or running any campaign.

## Decisions

**D1. Overwrite `rvsec.click` (option 1), not a second key (option 2).** The jar already reads
`rvsec.click` and looks it up in `handlers`. With option 1 only the stamp and the derive change,
two owners instead of three, and the artifact keeps `formatVersion: 2`. Option 2 would keep the
dispatcher on the node and keep a class's `onClick(View)` record apart from its callback record,
but it needs a jar change, a new event or record kind, and a new device validation. The measured
case it would protect against did not occur: on the A/B's six APKs the new derive added 408
records and changed none of the 842 existing ones. The researcher chose option 1 on 2026-10-19.

**D2. Resolve when the node is populated, not when the listener is set.** The objects that hold
the app callback are wired after the routed setter has run: the menu item's `MenuItemImpl`, the
navigation view's listener, the preference manager, the dialog's `Message`. At setter time most
of them are still null. `onInitializeAccessibilityNodeInfo` runs each time a client asks for the
node, after the screen is built. The cost is one reflective walk per populated dispatcher-bound
node, cached per class and member in `MEMBERS`.

**D3. Read library fields by name, by reflection, inside the helper's existing `catch`.** The
helper compiles against `android.jar` alone (requirement "The helper ships in the monitor DEX"),
so it cannot reference AppCompat, Material or androidx types. Names are the only handle. A
renamed field yields no callback and the node keeps the dispatcher's class, so the change
degrades to today's behaviour and never to a failure (INV-INS-177). The alternative, weaving new
setters for `setOnMenuItemClickListener`, `setOnPreferenceClickListener` and the like, would add
method references to app DEXes near the 64K ceiling and new weave sites to specify. Reflection
adds none.

**D4. An app class is any class outside `android.`, `androidx.`, `com.google.android.material.`,
`java.` and `kotlin.`.** This is the test that decides both whether to look behind a listener and
whether a candidate counts. It is the same kind of prefix test the Compose Material step uses
(`androidx.`). A third-party library class, such as `com.mikepenz.aboutlibraries.ui.LibsActivity`
in the A/B, counts as an app class. That is acceptable, because the derive gives it a record only
when the static analysis lists it.

**D5. The fragment's `onOptionsItemSelected` is not named; the activity is.** The activity is
reachable from the view's context without walking the fragment manager. When no app class of its
hierarchy declares `onOptionsItemSelected`, the first app `MenuProvider` of its `MenuHostHelper`
is named. This covers the AndroidX menu-provider form the A/B saw in fosdem
(`ExternalBookmarksListFragment$onViewCreated$menuProvider$1`). Naming the right fragment would
need the fragment manager's state at click time, and the guide could still not tell items apart
(D1, Non-Goals).

**D10. The stamp names the class that declares the callback.** The derive keys a `handlers`
record by the class that declares the method (`reachability[].className`). When the stamp named
the concrete activity while a base class declared `onOptionsItemSelected`, or named a preference
fragment that declares no `onPreferenceTreeClick`, the jar's lookup found no record. On the A/B's
36 logcats, 59 of 3,163 `kind=callback` lines named an activity that inherits its options-menu
callback (bitbanana's `BaseAppCompatActivity` subclasses) and 1,411 named a preference fragment
whose row the library handles; both were unlisted, so those nodes fell through to the id key as
before. The options menu therefore resolves to the nearest app class that declares
`onOptionsItemSelected(android.view.MenuItem)`, the parameter list the derive requires, and the
tree-click step counts only an app class that declares `onPreferenceTreeClick(Preference)`. A row
the library handles keeps `Preference$1`, which is what runs. The researcher decided this on
2026-10-19 after the code review; it changes statements of the A/B's stamp, so a device smoke
covers it (task 6.5).

**D6. The derive matches a callback by exact name and parameter list.** A name alone would admit
unrelated methods, such as an app helper `onClick(DialogInterface)` or `onOptionsItemSelected(int)`.
The parameter lists are the framework and library interface signatures. Every method that fills
`click` of a class goes through the existing per-event merge (OR of flags, minimum per target), so
an activity with both `onClick(View)` and `onOptionsItemSelected(MenuItem)` gets one record that
loses neither (INV-DRV-11). The jar keys `handlers` by class and event (`MopData.lookup`, ape
`2cfa8ee2`), so the merge is what it reads.

**D7. No change to `GENERATOR_ID`, `FORMAT_VERSION` or the cache key.** The artifact's shape is
unchanged, so the jar's format gate (`ape` INV-MOP-34) must not move: that would need a jar
release. The host cache is per task (`<results_dir>/<apk>.mop.json`), and an experiment started
after this change derives fresh. See Risks for the one case where an old artifact can be reused.

**D8. A listed callback class with no pair now blocks the id-key fallback.** `MopData.lookup`
takes a listed stamped class as the answer even when it has no pair, and then does not read the
widget's id key. A dispatcher was never listed, so its node fell through to the id key; a
callback class can now stop there. The jar is not changed (D1). The cost was measured on the A/B:
of the 30 widgets with an id-key weight in the control, 1 lost it in the treatment, on 1 step
(`experimento-stampcb/scripts/id_key_loss.py`). That is accepted and stated in the `aperv` delta's
Purpose.

**D9. Base `isolate-guidance-groups`, archived after it.** That change modifies the `aperv`
requirement "MOP Artifact Projection Contents" in full. This change's delta carries its text with
only the `handlers` item and the cryptoapp scenario's `handlers` keys edited and three scenarios
added, so archiving in that order loses nothing. Archiving this change first would overwrite that change's edits of the requirement. Both
sessions confirmed the order with the researcher.

## API Design

### `static String RvsecStamp.callback(View host, Object listener) throws Exception`

- **Pre:** called from `Delegate.onInitializeAccessibilityNodeInfo` for the last non-null click
  listener routed for `host`.
- **Post:** returns the binary name of an app class resolved under INV-INS-181, or `null` when
  the listener is itself an app class, is not a recognised dispatcher, or no candidate is an app
  class.
- **Errors:** may throw from reflection. The caller catches every `Throwable` and keeps the
  listener's class (INV-INS-177).

### `_handler_events(signature: str) -> tuple[str, ...]` (aperv-tool)

- **Pre:** a Soot signature from `reachability[].methods[]`.
- **Post:** `("click",)` for `onClick(android.view.View)` and for the eight callback signatures of
  INV-DRV-11; `("longclick",)` for `onLongClick(android.view.View)`; both events for the two
  Object-returning `invoke` forms; `()` otherwise.
- **Errors:** none; a non-matching signature returns `()`.

## Data Flow

1. The app routes `setOnClickListener(v, l)`. The helper calls the original setter, then
   `stamp()` stores `l` in the view's stamp delegate (`clickListener`) and its class in `click`.
2. A `UiAutomation` client asks for the window. The platform calls the delegate's
   `onInitializeAccessibilityNodeInfo`, which forwards to the chained delegate and then calls
   `callback(v, l)`.
3. A resolved class replaces `click` in `rvsec.click`. A class that differs from the last one
   logged writes `RVSEC-BIND view kind=callback`.
4. On the host, `aperv-tool` derives `<apk>.mop.json` with the callback classes in `handlers` and
   pushes it. The jar's lookup finds the record and weighs the action by its pairs (`dec.mopd`,
   source STAMP).

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `NoSuchFieldException` / `IllegalAccessException` / any `Throwable` in the lookup | a renamed or absent library field, an unexpected object | caught in the delegate (INV-INS-177) | the node keeps the dispatcher's class, as before the change |
| Callback resolved to a third-party class not in `handlers` | D4's prefix test | none needed | the jar finds no record and falls through to the id key, as for an unlisted class today |
| A cached `<apk>.mop.json` from an earlier derive reused | per-task cache key `(digest, formatVersion)` (D7) | stated as a risk | regenerate by deleting the task's `.mop.json` or starting the experiment anew |

## Risks / Trade-offs

- [The guide points at the menu, not the item] → stated in the known limits; the A/B measured
  the guidance gain with this granularity.
- [One shared record retires its targets together] → every item of one menu, and every row of
  one preference screen, carries the same callback class and so the same record. The jar retires
  a record's targets at its d* after the first interactions on that record's key, so a few first
  clicks on any of its items retire together every target at d*, including targets those clicks
  never execute. In the A/B, on vault, `enableBiometrics` and `deleteBiometricSecretKey` were
  retired together this way (`experimento-stampcb/README.md`, "H2.4 Aposentadoria"). Accepted as
  part of the class granularity (D1, Non-Goals); no spec changes for it.
- [A listed callback class with no pair hides the id key] → measured 1 of 30 widgets on the A/B
  (D8); accepted.
- [An experiment started before this change and resumed with the new code reuses each task's old
  `.mop.json`, which lacks the callback records] → stated here and in the task notes. An
  experiment started after the change derives fresh. No campaign is run or resumed by this
  change.
- [Apps whose R8 build renamed the library fields keep the dispatcher] → the sign is a
  dispatcher-bound view with no `kind=callback` line; the indicative corpus count is 148 of 163
  APKs with the names present.
- [The menu, toolbar and dialog paths need a real `View` and cannot be JVM-tested] → they are
  exercised on the device; the A/B logged `kind=callback` for all three families in all six APKs.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (JVM, monitor-builder) | `callback` and its helpers: preference chain with the declaring-class tree-click step, dialog button, a menu item's own listener, first app menu provider, the declaring-class options menu, app-bound and unresolved listeners, a failing read | `RvsecStampCallbackTest` with stub fixtures under `src/test/resources/stamp-fixtures/` | 16 |
| Unit (pytest, aperv-tool) | INV-DRV-11: callback signatures fill `click`; other parameter lists do not; per-class merge | `test_derive_mop_artifact.py`, run with `--import-mode=importlib -o "addopts="` | 3 |
| Regression | The weave and the Compose stamp are unchanged; the derive's other members are unchanged | the full `monitor-builder`, `dex-mutator` and `aperv-tool` suites | existing |
| Device | `kind=callback` delivered, no `mop.RvsecStamp` crash, no `VerifyError` | the A/B ran the stamp before D10; the D10 lookup is covered by one smoke on bitbanana approved by the researcher (task 6.5) | 1 |

## Open Questions

None. The variant (option 1), the base branch and the archive order were decided by the
researcher on 2026-10-19.
