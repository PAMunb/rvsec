## Purpose

The MOP artifact's handler table stops recording the app callbacks that a library dispatcher calls
(menu, navigation drawer, preference and dialog callbacks). The e03igg4 campaign showed that these
targets drew 11 % of the MOP coin's steps in `mop` and were never followed by a MOP misuse. The
artifact keys the table by class and cannot say which family a handler belongs to, so the cut is made
in the derivation: such a class is simply not listed, and the jar treats a tap stamped with it as it
did before the callback stamp existed. The MOP coin ledger's k = 2 and the distance cut d ≤ 3 are
unchanged, and so is the wire format.

## Data Contracts

### Side-Effects
- **[Artifact cache]**: `<results_dir>/<apk>/<apk>.mop.json` is reused when its `source.digest` and
  `formatVersion` match the current JSON and `FORMAT_VERSION` (2, unchanged). Neither changes with this
  derivation, so a results directory that already holds artifacts derived before this change keeps
  serving them, with the callback classes still listed. A run of this change SHALL use a new results
  directory or delete the cached `*.mop.json` first.

## Invariants

- **INV-DRV-11**: A `reachability[]` method SHALL fill the `click` event of its class's `handlers` record exactly when its name and parameter list are `onClick(android.view.View)` or `java.lang.Object invoke()` / `java.lang.Object invoke(java.lang.Object)`; `onLongClick(android.view.View)` and the two `invoke` forms fill `longclick`. Any other method, including the library-dispatched app callbacks `onOptionsItemSelected`, `onNavigationItemSelected`, `onMenuItemClick`, `onMenuItemSelected`, `onPreferenceClick`, `onPreferenceTreeClick`, `onPreferenceChange` and `onClick(android.content.DialogInterface,int)`, SHALL fill no event. All methods that fill one event of one class SHALL OR their flags and merge their pairs by the minimum per target before the cut of INV-DRV-10, so no method's contribution is lost.

## REMOVED Requirements

### Requirement: MOP Artifact Projection Contents (FR04, FR05, FR06, FR19)
**Reason**: Superseded by "MOP Artifact Projection and Handler Table (FR04, FR05, FR06, FR19)", which carries the same contract without the library-dispatched app callbacks as handler methods; three of its scenarios asserted the callback records and cannot stay.
**Migration**: None — the derivation is rewritten in place (P3); no reader depends on the old requirement name except the cross-reference in the `instrumentation` spec, updated at archive.

## ADDED Requirements

### Requirement: MOP Artifact Projection and Handler Table (FR04, FR05, FR06, FR19)

`derive_mop_artifact.derive(document)` SHALL produce a `formatVersion: 2` artifact containing exactly
the projection the explorer consumes. Format 2 keeps every format-1 member with its meaning (except the
A′ source-3 constructor exclusion of "MOP-Activity Sets and OPTIONSMENU Records") and adds item 9,
which is the wire contract of the `ape` change `llm-coordinate-single-base` (its design D15 and its
`static-analysis-entrypoints` delta). The jar of that change reads format 2 only, and earlier jars
read format 1 only, so the two sides ship together.

1. **Scalars**: `package` and `mainActivity` copied verbatim from the full JSON.
2. **Provenance**: `source.digest` (`"sha256:" + hex` of the full-JSON bytes), `source.file`
   (basename) and `source.generator` (`"aperv-derive/2"`).
3. **Widgets** (`widgets.<baseActivity>.<shortId>`): a per-normalized-eventType `mop` map with values
   `none|direct|transitive|both`, plus the consumed metadata fields `inputType`, `hint`, `prompt`,
   `spinnerMode`, `contentDescription`, `tooltipText` and `entries`, each emitted only when non-empty,
   plus the distance map `dist` of item 9.
   A widget SHALL be emitted only when it is MOP-flagged OR carries at least one metadata field. The
   keys `id`, `type`, `text` and the raw `listeners` array SHALL NOT be emitted. Map keys SHALL be
   pre-normalized (lowercased, `_` and `-` removed), matching the query-side normalization.
4. **Activity sets**: `mopActivities` (widget-derived, per INV-DRV-02 and the dialog promotion of
   INV-DRV-03) and `mopActivitiesAugmented` (the A′ union, without activity constructors in source 3),
   both always emitted so the on-device
   `mopActivitySourceComponents` flag keeps selecting between them at run time.
5. **OPTIONSMENU records**: `optionsMenus: [{activity, hasFlaggedWidget}]`, where `hasFlaggedWidget`
   is true when any widget of that menu window is MOP-flagged — tested over the window's parsed
   widgets, before the empty-id drop, for the same reason INV-DRV-02 states.
6. **WTG**: `wtg.<sourceBaseActivity> = [{widget, target}]` per INV-DRV-03. `widgetClass` SHALL NOT be
   emitted.
7. **Components**: `activities[]` (`className`, `isMain`, `permission`, `reachesMop`,
   `deepLinkUri`), `receivers[]`/`services[]` (adding `intentFilters`, plus the boolean
   `hasTargetMethods`), `providers[]` (adding `authorities`). `reachesMop` is the wire rename of
   `reachesTarget`. Every component of the document SHALL be projected, whatever its `reachesTarget`:
   the jar's component trigger is a STATIC member and its pool reads no MOP data (`ape` D-B13), so a
   receiver, service or provider left off the wire is one the trigger can never fire.
   Each `intentFilters[]` entry SHALL carry `actions` and `categories`, and SHALL carry a reduced
   `data` member `{"schemes": […], "hosts": […], "paths": […], "pathPrefixes": […], "mimeTypes": […]}`,
   taken from the producer's `data` block. A list that is empty SHALL be omitted, and `data` SHALL be
   omitted when all five are empty. The member exists because a receiver or service that filters on a
   scheme or a MIME type matches no intent built from its action alone, so without it the trigger
   fires intents that the platform never delivers. The jar builds one intent from the first scheme,
   host and MIME type, and from the first path, or the first path prefix when the filter declares no
   path, which is why `pathPrefixes` travels and `ports` and `pathPatterns` SHALL NOT be emitted: a
   port is not part of the intent's matching data the jar sets, and a pattern is not a literal path.
   The member is additive: the artifact stays `formatVersion: 2`, and the jar reads its absence as
   "no data". `readPermission`, `writePermission`, the `targetMethods` signature list and `exported`
   SHALL NOT be emitted.
   `exported` is on that list because no consumer reads it and none may: the jar's activity launcher
   is required to ignore export status (the dispatch runs from uid 2000 and opens non-exported
   activities), so keeping the field on the wire would ship a value whose only possible use is
   forbidden.
8. **Stats**: `windows`, `widgetsTotal`, `flagged`, `droppedFlaggedNoId`, `orphanDialogs`,
   `handlersUnmatched`, `syntheticLambda`, `recovered`, `wtgEdges`, `dedupedTransitions`.
   `widgetsTotal` and `flagged` SHALL count the widget map after the dialog merge and before the
   emission filter of item 3, so they remain the numbers the jar's load record reported. Format 2
   adds no counter: the jar's load record reports `targets`, the size of `handlers` and the pairs it
   drops.
9. **Targets and distances** (format 2):
   - **`targets`**: the number of entries of the document's `distanceTargets` (direct targets C,
     followed by boundary targets B \ C; `analysis` spec, `distanceTargets`). Every pair `[i, d]` of
     the artifact SHALL satisfy `0 ≤ i < targets` (INV-DRV-10). No signature and no `kind` is
     emitted: the jar weighs boundary targets as direct ones. A document without `distanceTargets`
     yields `targets: 0` and no pair; nothing refuses it (gh120 design D9 left the September
     artefacts to the corpus hand-off).
   - **The distance of a method.** A method's distance to target `i` is its `targetDistances` entry
     for `i`: 0 when the method is the target, 1–10 otherwise (gh120 `DIST_MAX = 10`); a target
     absent from its entries is unreachable. An entry that is not a pair of integers, whose index is
     outside `[0, targets)` or whose distance is negative is skipped, like any malformed entry inside
     a well-typed section. A method the producer marks reaching and gives no `targetDistances` is
     one whose every target is more than `DIST_MAX` calls away: gh120 computes reach without a depth
     bound and distances with the cut. It has flags and no distance, and the derive does not invent
     one, so a widget or handler whose reaching methods are all that far is flagged and carries no
     pair. Under `distance` scoring that is the weight the exact distance would give, since a target
     at `d ≥ 4` gives none.
   - **The distance of a handler.** A listener's handler SHALL resolve to its method by the same
     exact signature join that gives its flags (INV-DRV-01, INV-DRV-09). A D8 synthetic-lambda wrapper
     absent from that index SHALL resolve by the same class recovery, and its distance to `i` is the
     minimum over the enclosing class's reaching `lambda$…` methods. A listener whose flags come from
     the producer-precedence tier (`handlerReachesTarget`/`handlerDirectlyReachesTarget`) still takes
     its distances from the join, because the producer supplies no distance.
   - **Per widget, `dist: {<event>: [[i, d], …]}`**, beside `mop`, under the same normalized event keys:
     for each target, the minimum over the widget's handlers for that event. A null-event listener
     contributes to the `""` key exactly when `mop` carries `""`. On a `shortId` collision
     (INV-DRV-02) and in the dialog merge (INV-DRV-03) the flags keep the strongest-flag rule while
     the `dist` maps of both widgets SHALL merge by the minimum distance per target.
   - **Per activity, `activityDist: {<base activity>: [[i, d], …]}`**: for each target, the minimum over
     the pairs of every widget of the activity, all events, after the dialog merge and including the
     widgets the empty-short-id rule keeps off the wire, and over the `targetDistances` of the methods
     of the activity's own class (the `reachability[]` entries with `componentType == "activity"` whose
     base name is the activity) **except that class's `<init>` and `<clinit>`**. Launching any activity
     runs its own constructor, and gh120 keeps every activity constructor as a boundary target (its
     D12), so without the exclusion every activity would sit at `d = 0`. A dialog's activity pairs
     move to its host with its widgets.
   - **`handlers: {<binary class name>: {mop: {<event>: flag}, dist: {<event>: [[i, d], …]}}}`**: one
     record per `reachability[]` class that declares a handler method. The handler methods, matched by
     name and parameter list in the method's signature, are `onClick(android.view.View)`, which fills
     `click`; `onLongClick(android.view.View)`, which fills `longclick`; and `java.lang.Object invoke()`
     and `java.lang.Object invoke(java.lang.Object)`, which fill both. A Compose node's stamp is the
     class of a `Function0`, and a toggleable's is the class of its `onValueChange`, a `Function1`
     (`instrumentation` INV-INS-178); the node's extras key, not the method, tells the event.
     The app callbacks that a library dispatcher calls — `onOptionsItemSelected`,
     `onNavigationItemSelected`, `onMenuItemClick`, `onMenuItemSelected`, `onPreferenceClick`,
     `onPreferenceTreeClick`, `onPreferenceChange` and `onClick(android.content.DialogInterface,int)` —
     are not handler methods and fill no event (INV-DRV-11), although the View stamp names their class
     in `rvsec.click` (`instrumentation` INV-INS-181). In the e03igg4 campaign these menu, navigation,
     preference and dialog targets took 798 MOP coin steps in `mop` (11 % of the coin's steps, 90 tasks,
     33 APKs) and no MOP misuse followed any of them, nor any of 800 in `as_mop`; leaving their class
     unlisted gives them no MOP information, for the coin and for SATA's MOP weight alike. The table
     cannot carry the family of a handler, only its class, which is why the cut is made here and not in
     the jar. **Known limit:** the stamp names a class, not a method, so a class that declares one of
     these callbacks and also a View handler method stays listed, and a tap stamped with it reads the
     View handler's record; on the e7 corpus this is 9 of 3109 classes declaring such a callback, in 8
     APKs.
     `<init>` and `<clinit>` are never handler methods. An event's flag is derived from the method's
     own `directlyReachesTarget`/`reachesTarget` on INV-DRV-01's two axes, and its pairs are the
     method's distances; two methods filling one event OR their flags and merge their pairs by the
     minimum per target. A class whose handler methods reach nothing SHALL still be listed, with
     `none` for each of its events and no `dist`: on the device a listed class states that the
     stamped handler reaches no target. The key is the class's binary name as `reachability[].className`
     writes it, which is the `Class.getName()` form gh121 stamps.
   - **Cut, order, omission** (INV-DRV-10). A widget's and a handler's pair list SHALL keep every
     target at `d ≤ 3` and drop every pair at `d ≥ 4`. These are the lists that weigh an action, and
     the jar gives no weight from `d = 4` (`ape` D18). Under the three-pair cut, 4,024 of the 21,485
     targets at `d ≤ 3` of some widget or handler list (18.7 %) sat at `d ≤ 3` in no list after the
     cut, so they could never weigh an action or retire (`ape` D15, amendment of 2026-10-09,
     measured on the 163 round-A gh120 documents). An `activityDist` list SHALL keep the three pairs
     of smallest `d`, because the launcher only orders the activities the census already makes
     eligible. Every list is sorted by `d` ascending, then `i` ascending, and merges are applied to
     the full per-target minima before the cut; an activity starts from its widgets' uncut minima.
     An event with no pair after the cut SHALL have no key in a `dist` map, and an empty `dist` map
     and an `activityDist` entry with no pair SHALL be omitted. `targets` and `handlers` SHALL always
     be emitted, `0` and `{}` when empty. The widget emission filter of item 3 is unchanged: pairs do
     not make an unflagged, metadata-less widget emitted.

Derivation preconditions: the document is an object, carries a non-null `package`, and every section
it does carry is of the expected type; otherwise `DerivationError`. The producer's `"complete": true`
sentinel is NOT a precondition (INV-DRV-08). A document written by the producer's first pass — valid
JSON with populated `reachability` and `windows` per INV-ANA-20, and an empty `transitions` array —
SHALL yield an artifact whose `wtg` is empty, which the device reads through `MopData.hasWtgData()`
to disable the WTG-dependent scoring passes on its own. Structural corruption from a write interrupted
mid-pass is caught earlier, by the parse in `_derive_mop_artifact()`, because the producer truncates
its output file on open and cannot leave a parseable stale tail.

#### Scenario: cryptoapp derivation matches the known ground truth
- **WHEN** `derive()` runs on the test fixture `cryptoapp.apk.json`, a byte copy of the gh120
  baseline `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` (the gh120 producer
  output for `br.unb.cic.cryptoapp`), where the Execute button's wrapper
  `CryptographyActivity$$ExternalSyntheticLambda0.onClick` carries `reachesTarget: true`
- **THEN** `mopActivities` SHALL equal
  `{MessageDigestActivity, CipherActivity, CryptographyActivity}` (base names).
  `CryptographyActivity` enters through the exact join: the producer links the wrapper to its own
  `lambda$setupExecuteButton$0` body (`analysis` INV-ANA-77), so the wrapper is listed reaching and
  the class recovery is not consulted (INV-DRV-09)
- **AND** `optionsMenus` SHALL contain the `MainActivity` record, and `wtg` SHALL carry the click
  edges from `MainActivity` to all three MOP sub-activities
- **AND** `components.activities` SHALL have 4 entries and `components.providers` 1 entry with
  `authorities == "br.unb.cic.cryptoapp.androidx-startup"`, every component `reachesMop == false`
- **AND** `stats.windows` SHALL be 5, `stats.flagged` 3 and `stats.recovered` 0
- **AND** `formatVersion` SHALL be 2, `source.generator` `"aperv-derive/2"` and `targets` 27 (23 direct
  targets, then the 4 activity constructors as boundary targets)
- **AND** the `click` pairs SHALL be `[[22,2]]` for `buttonGenerateHash` and `[[16,3],[17,3],[18,3]]`
  for `executeButton`, the three of its wrapper's ten pairs at `d ≤ 3`
- **AND** `btn_cipher_encrypt` SHALL be emitted with `mop == {"click": "transitive"}` and no `dist`,
  because its handler `CipherActivity$1.onClick` reaches its two targets only at `d = 4`
- **AND** `handlers` SHALL have exactly two keys: `br.unb.cic.cryptoapp.cipher.CipherActivity$1` and
  `br.unb.cic.cryptoapp.generated.CryptographyActivity$$ExternalSyntheticLambda0`, each with
  `mop == {"click": "transitive"}`, the second carrying `dist == {"click": [[16,3],[17,3],[18,3]]}`
  and the first no `dist`; `br.unb.cic.cryptoapp.MainActivity` (its
  `onOptionsItemSelected(android.view.MenuItem)`) and `br.unb.cic.cryptoapp.MainActivity$1` (its
  `onMenuItemClick(android.view.MenuItem)`) SHALL NOT be keys, because those callbacks are not handler
  methods (INV-DRV-11)
- **AND** `activityDist` SHALL be exactly `{CipherActivity: [[0,2],[1,2]], CryptographyActivity:
  [[12,0],[13,0],[14,0]], MessageDigestActivity: [[22,2]]}` (fully qualified keys), with no entry
  for `MainActivity`, whose only reaching method is its own constructor

#### Scenario: absent sentinel does not stop derivation
- **WHEN** `derive()` runs on a document with a valid `package`, well-typed sections, `transitions: []`
  and no `complete` key
- **THEN** an artifact SHALL be returned
- **AND** `artifact["wtg"]` SHALL equal `{}` and `artifact["stats"]["wtgEdges"]` SHALL equal `0`
- **AND** `mopActivities`, `optionsMenus` and `widgets` SHALL be derived from `reachability` and
  `windows` exactly as they would be with the sentinel present

#### Scenario: false sentinel does not stop derivation
- **WHEN** `derive()` runs on the same document with `complete: False` written explicitly
- **THEN** the emitted artifact SHALL be byte-identical to the one derived with the key absent

#### Scenario: missing package still refuses
- **WHEN** `derive()` runs on a document carrying `complete: True` and no `package` key
- **THEN** `DerivationError` SHALL be raised
- **AND** no artifact SHALL be returned

#### Scenario: malformed section still refuses
- **WHEN** `derive()` runs on a document whose `reachability` is the integer `7` instead of a list
- **THEN** `DerivationError` SHALL be raised
- **AND** no artifact SHALL be returned

#### Scenario: no Target vocabulary and no call graph on the wire
- **WHEN** an artifact is generated from a document declaring receivers and services
- **THEN** the only key containing `Target` anywhere in it SHALL be `hasTargetMethods` (the lowercase
  `targets` does not match)
- **AND** it SHALL contain no `reachability`, `windows`, `transitions`, `listeners` or
  `distanceTargets` section, and no string in the shape of a Soot method signature (INV-DRV-06)
- **AND** the check SHALL be exercised against components, not only against a fixture whose
  component lists are empty

#### Scenario: unflagged metadata-less widgets are projected away
- **WHEN** a widget has no MOP-reaching listener and none of `inputType`, `hint`, `prompt`,
  `spinnerMode`, `contentDescription`, `tooltipText`, `entries`
- **THEN** the artifact SHALL NOT contain that widget
- **AND** an unflagged widget carrying a non-empty `hint` SHALL be emitted, because typed input reads it

#### Scenario: stats count the map, not the wire
- **WHEN** a base activity holds 40 widgets after the dialog merge, of which 2 are flagged and 35 are
  unflagged and metadata-less
- **THEN** `stats.widgetsTotal` SHALL be 40 and `stats.flagged` SHALL be 2
- **AND** the emitted `widgets` map for that activity SHALL contain 5 entries

#### Scenario: a widget's distance is the minimum over its handlers, every target within three calls
- **WHEN** a widget's two `click` listeners resolve to methods with `targetDistances`
  `[[2,3],[5,1],[7,4],[8,3]]` and `[[2,2],[9,6],[11,1],[12,3]]`
- **THEN** its `dist` SHALL be `{"click": [[5,1],[11,1],[2,2],[8,3],[12,3]]}`, five pairs
- **AND** target 2 SHALL appear once, at the smaller distance 2
- **AND** targets 7 (`d = 4`) and 9 (`d = 6`) SHALL NOT appear

#### Scenario: a widget whose targets are all four calls or more away carries no pair
- **WHEN** a widget's only `click` listener resolves to a method reaching a target, flagged
  `transitive`, with `targetDistances` `[[0,4],[1,5]]`, and its activity has no other pair
- **THEN** the widget SHALL be emitted with `mop == {"click": "transitive"}` and no `dist`
- **AND** its activity's `activityDist` SHALL be `[[0,4],[1,5]]`, because an activity starts from its
  widgets' uncut minima

#### Scenario: activityDist keeps the three nearest targets
- **WHEN** an activity's widgets carry the `click` pairs `[[1,0],[2,1]]` and `[[3,1],[4,2]]`, and its
  own class's methods carry none
- **THEN** its `activityDist` SHALL be `[[1,0],[2,1],[3,1]]`
- **AND** each widget SHALL keep its own two pairs

#### Scenario: an unlisted wrapper takes its distances from the recovered lambdas
- **WHEN** a click handler `<com.example.MainActivity$$ExternalSyntheticLambda0: void onClick(android.view.View)>`
  is absent from `reachability[]`, and `com.example.MainActivity` has reaching `lambda$onCreate$0`
  with `targetDistances [[4,2]]` and `lambda$onCreate$1` with `[[4,1],[6,3]]`
- **THEN** the widget's `click` pairs SHALL be `[[4,1],[6,3]]`

#### Scenario: colliding widgets merge their distances by the minimum
- **WHEN** two widgets of one base activity share `shortId == "submit"`, the first `direct` on `click`
  with pairs `[[3,0]]`, the second `transitive` with `[[3,1],[5,2]]`
- **THEN** the emitted entry SHALL carry the `direct` flag and the `click` pairs `[[3,0],[5,2]]`

#### Scenario: an activity's own constructor does not count toward its distance
- **WHEN** the only methods of activity class `com.example.A` carrying `targetDistances` are
  `<init>` with `[[23,0]]` and `onResume` with `[[2,5]]`, and its widgets carry no pair
- **THEN** `activityDist["com.example.A"]` SHALL be `[[2,5]]`
- **AND** with `onResume` reaching nothing, `com.example.A` SHALL have no `activityDist` entry

#### Scenario: the handler table lists a class that reaches nothing
- **WHEN** `reachability[]` lists `com.example.ui.ScreenKt$Body$1$1` with one method
  `<com.example.ui.ScreenKt$Body$1$1: java.lang.Object invoke()>`, `reachesTarget: false`
- **THEN** `handlers["com.example.ui.ScreenKt$Body$1$1"]` SHALL be
  `{"mop": {"click": "none", "longclick": "none"}}`, with no `dist`
- **AND** a class declaring `invoke(java.lang.Object)` reaching target 3 at distance 2 SHALL carry
  `dist == {"click": [[3,2]], "longclick": [[3,2]]}`

#### Scenario: a document without distances derives with no target
- **WHEN** `derive()` runs on a well-typed document with no `distanceTargets` key and no
  `targetDistances` on any method
- **THEN** an artifact SHALL be returned with `targets == 0`, `handlers` listing the handler classes
  with flags only, no `dist` on any widget and no `activityDist` entry

#### Scenario: a receiver's intent filter keeps its reduced data
- **WHEN** a document declares a receiver whose `intentFilters` are
  `[{"actions": ["android.intent.action.VIEW"], "categories": [], "data": {"schemes": ["myapp"], "hosts": ["x.org"], "ports": ["80"], "paths": [], "pathPrefixes": ["/a"], "pathPatterns": [], "mimeTypes": ["text/plain"]}}]`
- **THEN** the projected filter SHALL be
  `{"actions": ["android.intent.action.VIEW"], "categories": [], "data": {"schemes": ["myapp"], "hosts": ["x.org"], "pathPrefixes": ["/a"], "mimeTypes": ["text/plain"]}}`
- **AND** it SHALL carry no `ports`, `paths` or `pathPatterns` key
- **AND** a filter whose `data` lists are all empty SHALL carry no `data` member
- **AND** `formatVersion` SHALL still be 2

#### Scenario: components that reach no target are still projected
- **WHEN** a document declares two receivers and one service, all with `reachesTarget: false`
- **THEN** `components.receivers` SHALL have 2 entries and `components.services` 1, each with `reachesMop == false`

---

#### Scenario: the app callbacks behind library dispatchers are not handler methods
- **WHEN** `reachability[]` lists `com.example.app.MainActivity` whose only method is `<com.example.app.MainActivity: boolean onOptionsItemSelected(android.view.MenuItem)>` at distance 2 from target 0, `com.example.app.SettingsFragment$$ExternalSyntheticLambda5` whose only method is `<...: boolean onPreferenceClick(androidx.preference.Preference)>` at distance 1 from target 1, and `com.example.app.Dialogs$$ExternalSyntheticLambda3` whose only method is `<...: void onClick(android.content.DialogInterface,int)>` at distance 3 from target 0
- **THEN** `handlers` SHALL have none of the keys `com.example.app.MainActivity`, `com.example.app.SettingsFragment$$ExternalSyntheticLambda5` and `com.example.app.Dialogs$$ExternalSyntheticLambda3`

#### Scenario: a class with a view listener and an options-menu callback keeps only the view listener
- **WHEN** `com.example.app.MainActivity` declares `onClick(android.view.View)` at distances `{0: 3}`, reaching no target directly, and `onOptionsItemSelected(android.view.MenuItem)` at distances `{0: 1, 2: 2}`, reaching target 0 directly
- **THEN** `handlers["com.example.app.MainActivity"]` SHALL carry `dist.click == [[0, 3]]`
- **AND** its `click` flag SHALL be the one of `onClick(android.view.View)` alone, `transitive`
