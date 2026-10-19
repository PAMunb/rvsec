GitHub Issue: none (researcher's decision, 2026-10-19: the change is tracked without an issue)

## Why

Many clicks of a Views app reach app code through a listener that a library binds: a menu or
navigation item, the toolbar's up button, a preference row, or an AppCompat dialog button. For
those views the handler stamp (instrumentation `Requirement: Handler Stamp on the Accessibility
Node`, INV-INS-178) writes the class of that library dispatcher into `rvsec.click`:
`ActionMenuItemView`, `NavigationMenuPresenter$1`, `ToolbarWidgetWrapper$1`, `Preference$1` or
`AlertController$1`. APE-RV's MOP guide looks the stamped class up in the `handlers` table of the
derived artifact, and that table has no record for it. The derive (aperv `handlers`) records only
classes that declare `onClick(View)`, `onLongClick(View)` or `invoke`, so the app callback behind
the dispatcher has no record either. The guide therefore gets no weight from these clicks. The
chain is broken in two places: the stamp and the derive.

The defect was measured on the e03igg campaign (`data/e03igg_analysis/out/rp_guidance/RESULTS.md`,
sections B, K, N):
- 47.6 % of the `RVSEC-BIND kind=click` lines of view-only apps name a library class;
- 616 app callbacks with a target at d ≤ 3 sit in 52 of the 108 Views and mixed APKs, and only 7 of
  them are in the table.

A device A/B tested the fix before this change was opened (`experimento-stampcb/`, README
"Resultados", 6 APKs × 3 repetitions × 300 s of `aperv:mop` per arm, 36/36 tasks):
- the share of steps with a distance weight (`dec.mopd`) rose from 414/5 142 (8.1 %) to 647/5 287
  (12.2 %), and fosdem went from 0 to 5.5 %;
- 289 of the 647 weighted treatment steps fell on a class that only the fixed derive places at
  d ≤ 3;
- no crash had a `mop.RvsecStamp` frame and no `VerifyError` was raised;
- primary misuse sites were equal in five apps and rose from 2 to 3 in one (a library site).

The researcher chose the variant that leaves the jar unchanged ("option 1"): the stamp writes the
app callback's class into the key the jar already reads.

## What Changes

- **Stamp names the app callback.** In `onInitializeAccessibilityNodeInfo`, when the last click
  listener routed through the helper is a library class, the stamp delegate looks for the app
  callback that the dispatcher calls:
  - for a menu item: the item's own click listener, then the listener of the enclosing
    navigation view or bar, the toolbar's menu-item listener or menu providers, and then the
    activity's options menu;
  - for the toolbar's up button: the activity's options menu;
  - for a preference row: the preference's click listener, then its change listener, then the
    preference manager's tree-click listener;
  - for an AppCompat dialog button: the `DialogInterface.OnClickListener` carried by the button's
    message.
  When one is found, its class replaces the dispatcher's class in `rvsec.click`. When none is
  found, the node is stamped as before. Every read is reflective and caught (INV-INS-177).
- **New verification line.** Each time a node's callback changes, the helper writes one
  `RVSEC-BIND view kind=callback` line naming the dispatcher and the callback class.
- **Derive records the callback methods.** The `handlers` table of the aperv-tool derive adds
  these methods to the `click` event of their class:
  - `onOptionsItemSelected`, `onNavigationItemSelected`, `onMenuItemClick` and
    `onMenuItemSelected`, each with a `MenuItem` parameter;
  - `onPreferenceClick` and `onPreferenceTreeClick`, with a `Preference` parameter;
  - `onPreferenceChange`, with `Preference` and `Object` parameters;
  - `onClick(DialogInterface, int)`.
  The existing rule for two methods filling one event (OR of flags, minimum per target) applies
  to them.
- **Known limits updated.** The requirement's known limits name what the stamp still does not
  reach:
  - a fragment's `onOptionsItemSelected` (the activity is named);
  - every MenuProvider after the first;
  - the overflow popup item;
  - `AdapterView.onItemClick` and `CompoundButton.onCheckedChanged`;
  - the framework `android.app.AlertDialog` and `android.preference`;
  - a Material `TabLayout` tab, which carries no stamp, so `onTabSelected` is not named;
  - an app whose R8 build renamed the library fields the stamp reads.
  They also state that a callback's distance is per method, so every item of one menu carries the
  same record.
- **Unchanged.**
  - The `.dex` weave, its sites and its `stamp*` counters.
  - The Compose stamp and `rvsec.longClick`.
  - The `RVSEC-BIND kind=click` lines.
  - The ape-rv jar and the artifact format (`formatVersion` 2).

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `instrumentation`: `Requirement: Handler Stamp on the Accessibility Node` changes in three
  places. INV-INS-178 now lets `rvsec.click` hold the app callback's class instead of a library
  dispatcher. A new invariant states how the callback is resolved. INV-INS-179 covers the
  `kind=callback` line. The known limits and scenarios change with them.
- `aperv`: the `handlers` item of the derive's format-2 contract adds the callback methods to the
  `click` event.

## Impact

- **Java (rvsec reactor):** `RvsecStamp.java`, a resource of
  `rvsec-instrumentation-dexlib2/monitor-builder` compiled into the monitor DEX, and its JVM tests.
  The `instr-cli.jar` that the reactor build copies to
  `rv-android/modules/rv-instrumentation-dexlib2/lib/` changes with it. The module's
  `CLAUDE.md` known-limits text changes too.
- **Python modules:** `aperv-tool` (`derive_mop_artifact.py` and its tests).
  `rv-instrumentation-dexlib2` forwards `--stamp-handlers` exactly as before (INV-INS-180). No
  other module changes.
- **Consumers:**
  - APE-RV reads `rvsec.click` in the same form, and stamped class names change only on
    dispatcher-bound views.
  - A class that the new derive lists now wins the jar's lookup even when it carries no pair, so
    the widget's id key is no longer consulted for that node. Measured in the A/B: 1 of 30
    widgets that had an id-key weight in the control lost it.
- **Measurements:**
  - A corpus instrumented before this change keeps the dispatcher stamp.
  - A derive cached under the old generator is reused only while its format and digest match.
  - Re-instrumenting the Study 03 corpus belongs to the campaign and replication-package work,
    not to this change, and so does recording the defect as a threat to validity for the e03igg
    data.
- **Base and order:** the change is built on branch `isolate-guidance-groups` (c6865a73) of the
  rvsec repository, never on `modules`; the ape repository's branch of the same name holds the
  jar, which this change does not touch. That branch's derive is the one the A/B control ran,
  byte for byte. Its own change, `isolate-guidance-groups`, modifies the requirement "MOP Artifact
  Projection Contents" of the `aperv` spec in full, so this change's `aperv` delta carries that
  text with the `handlers` item and the cryptoapp scenario's `handlers` keys edited, and this change is archived after it.
- **FRs/NFRs:** FR02 (APK instrumentation, stamp option), FR06 (reachability for MOP, the derived
  artifact), FR20 (per-tool variant, the `aperv:mop` guide).
