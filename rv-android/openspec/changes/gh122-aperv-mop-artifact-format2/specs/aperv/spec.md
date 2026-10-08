## Purpose

The derive (`modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`) turns the full `.apk.json` into the compact MOP artifact APE-RV reads on the device. Format 1 carries one yes/no mark per `(base activity, short id, event)`: +500 when the widget's handler calls a monitored operation in its own body, +300 when it reaches one further down. Study 03 measured three weaknesses of that mark. Reachability saturates: 41 % of handlers reach a target, and on the median E6 screen 67 % of the widgets are marked. One handler is attributed to many widgets: 68.3 % of handlers sit in four keys or more. And 58.6 % of clicked nodes have no resource id, so the key matches nothing (rv-android `docs/20261005_verificacao_plano_gator_compose.md` §3).

Two producer changes answer those weaknesses, and neither reaches the device yet:
- gh120 gives every app method its call-graph distance to each monitored target, as `targetDistances` pairs `[i, d]` that index the document's `distanceTargets` (`analysis` spec, Data Contracts);
- gh121 makes the instrumented app write the binary class name of each widget's click and long-click handler in its accessibility node's extras (`instrumentation` INV-INS-178).

The gh120 design (`:86-87`) leaves the derive to the consumer. The consumer is the `ape` change `llm-coordinate-single-base`, whose design D15 and `static-analysis-entrypoints` delta fix the wire contract of **format 2**. This delta implements that contract:
- the target count;
- per widget and event, the three nearest targets;
- per activity, the three nearest targets, excluding the activity's own constructor;
- a table from handler class to flags and distances, through which the jar reads a gh121 stamp.

It also drops activity constructors from the A′ source 3 of `mopActivitiesAugmented`, which gh120 would otherwise let into every activity.

The two sides are coupled by the version: the jar of `llm-coordinate-single-base` rejects format 1, and every earlier jar rejects format 2. The host cache therefore keys on the format as well as on the source digest, so a format-1 artifact derived before the bump is never pushed again.

The same change adds the two arms that select the jar's new `distance` scoring:
- `mopd_on_llm_off`, the third arm of the minimal family the plan analysis proposes;
- `mopd_on_llm_90`, Study 03's E6 LLM arm under distance scoring.

It also maps the six plan keys the jar added for that scoring.

## Data Contracts

### Input
- `distanceTargets: list[{signature, kind}]` — top-level key of the full `.apk.json`; only its length is read (source: GATOR, gh120)
- `reachability[].methods[].targetDistances: list[[int, int]]` — per-method pairs `[i, d]`, `0 ≤ d ≤ 10`, omitted when empty (source: GATOR, gh120)
- `reachability[].methods[].{name, signature, reachesTarget, directlyReachesTarget}` and `reachability[].{className, componentType}` — as in format 1; `name` now also excludes `<init>`/`<clinit>` from the A′ source 3 and from `activityDist`

### Output
- `*.mop.json` with `formatVersion: 2`, `source.generator: "aperv-derive/2"`, and the new members `targets: int`, `widgets.<a>.<id>.dist: {event: [[i, d], …]}`, `activityDist: {activity: [[i, d], …]}`, `handlers: {class: {mop: {event: flag}, dist: {event: [[i, d], …]}}}` (destination: APE-RV `MopData`, `ape` `llm-coordinate-single-base`)
- `ape.properties` lines `ape.mopScoring=distance` for the two `mopd_*` arms; `ape.mopWeightD1..3`, `ape.mopRetireAfter`, `ape.mopLauncherDmax` only when a DSL override sets them (destination: the jar's plan resolution)

### Side-Effects
- **[Host filesystem]**: every cached format-1 `<apk_name>.mop.json` is overwritten with its format-2 derivation on the first MOP run that reads it

### Error
- No new error. A pair-shaped entry that is malformed is skipped, not raised; a `distanceTargets` that is present and not a list is a `DerivationError` like any section of the wrong type

## Invariants

- **INV-DRV-06** (amended): The artifact SHALL contain no call-graph data: no `reachability` section, no method signature, no call edge, no raw `windows`/`transitions`/`listeners`/`distanceTargets`. It SHALL contain no `*Target` key other than `hasTargetMethods` on receivers and services. That single exception is deliberate: it is the boolean the `targetMethods` signature list compacts to, its name is fixed by the jointly defined wire format, and the jar reads it by that name. Format 2 MAY carry integer target indices and integer distances (`targets`, `dist`, `activityDist`, the `dist` of a `handlers` record) and binary class names (the keys of `handlers`). A target index is joined to its signature only offline, through `source.digest` and the full JSON it names. The full JSON SHALL remain unmodified on the host.
- **INV-DRV-10**: Every distance pair `[i, d]` in the artifact SHALL satisfy `0 ≤ i < targets` and `d ≥ 0`. A pair list SHALL hold each index at most once and at most three pairs, and SHALL be sorted by `d` ascending, then `i` ascending. It is cut from the full per-target minima after every merge (listener, collision, dialog, class), never before. An empty pair list SHALL NOT be emitted. `targets` and `handlers` SHALL always be emitted.
- **INV-APV-05** (amended): `get_variants()` SHALL return a dict whose keys are exactly `default`, `sata`, `sata_mop`, `sata_llm`, `sata_mop_llm`, `mop_on_llm_off`, `mop_off_llm_off`, `mop_on_llm_70`, `mopd_on_llm_off` and `mopd_on_llm_90`, with `default` bound to the same object as `sata` (INV-TOOL-02).
- **INV-APV-42** (amended): The ten surviving variant names are frozen. Its other clauses are unchanged: no rename, divergence only through a new arm name, the 21 documented retirements and their kinds.
- **INV-APV-47** (amended): Cache freshness SHALL be keyed on the source digest and the format. A cached `<apk_name>.mop.json` is reused only when its recorded `source.digest` equals the SHA-256 of the current full JSON **and** its `formatVersion` equals `FORMAT_VERSION`. Cache state SHALL NOT change what the device receives for a given full JSON and generator.

## MODIFIED Requirements

### Requirement: Derived MOP Artifact Generation and Caching (FR19, NFR04)

`ApeRVTool._derive_mop_artifact(task)` SHALL return the host path of the compact MOP artifact for the
task's APK, generating it when needed:

1. Compute the SHA-256 of the current full JSON at `<results_dir>/<apk_name>.json`.
2. When `<results_dir>/<apk_name>.mop.json` exists, its `source.digest` equals `"sha256:" + <hex>`
   **and** its `formatVersion` equals `derive_mop_artifact.FORMAT_VERSION`, reuse it without
   regenerating.
3. Otherwise call `derive()` + `serialize_canonical()` and write the artifact atomically
   (write-temp-then-rename in the same directory). A failed derivation SHALL write nothing.

The artifact is cached next to its source so it is inspectable and diffable, and it is a pure function
of the full JSON and the generator's format (INV-APV-47, INV-DRV-05). The format is part of the cache
key because the digest alone names the input, not the derivation: after a format bump a cached
artifact of the old format matches its source's digest and would be pushed to a jar that rejects it,
and every MOP arm would abort (`ape` INV-MOP-34). This method replaces `_compact_static_analysis_json`,
which is deleted together with its fallback-to-source push: there is no longer any condition under
which the full JSON reaches the device (INV-APV-46).

Derivation failure means the document is structurally unusable, not that the analysis stopped early.
An unreadable or unparseable file fails here through `json.loads` before `derive()` is reached; a
well-formed document that lacks the WTG stage does not fail at all (INV-DRV-08).

#### Scenario: cache hit skips derivation
- **WHEN** `<results_dir>/com.example_1.apk.mop.json` exists carrying
  `source.digest == "sha256:ab12…"` and the SHA-256 of `com.example_1.apk.json` is `ab12…`
- **THEN** `_derive_mop_artifact(task)` SHALL return that path
- **AND** `derive()` SHALL NOT be called

#### Scenario: stale cache regenerates
- **WHEN** the cached artifact records `source.digest == "sha256:ab12…"` but the current full JSON
  hashes to `cd34…`
- **THEN** the artifact SHALL be regenerated and overwritten
- **AND** the pushed bytes SHALL equal a fresh derivation of the current full JSON

#### Scenario: failed derivation leaves no artifact behind
- **WHEN** `derive()` raises `DerivationError` because `document["windows"]` is the string `"none"`
  instead of a list
- **THEN** no `<apk_name>.mop.json` SHALL exist afterwards, and any partially written temporary file
  SHALL be removed
- **AND** `RVToolExecutionError` SHALL be raised carrying the derivation error

#### Scenario: WTG-less document arms both aperv arms
- **WHEN** `<results_dir>/app.pachli_50.apk.json` carries 6336 `reachability` entries, 45 `windows`,
  `transitions: []` and no `complete` key
- **THEN** `_derive_mop_artifact(task)` SHALL return the path of a written `app.pachli_50.apk.mop.json`
- **AND** the task SHALL NOT fail, for the `mop_on_llm_off` arm and for the `mop_off_llm_off` arm alike
- **AND** the artifact SHALL carry `wtg == {}` and `stats["wtgEdges"] == 0`

#### Scenario: cached artifact of an older format regenerates
- **WHEN** `<results_dir>/com.example_1.apk.mop.json` carries `formatVersion: 1` and
  `source.digest == "sha256:ab12…"`, the SHA-256 of `com.example_1.apk.json` is `ab12…`, and
  `FORMAT_VERSION` is 2
- **THEN** `derive()` SHALL be called and the artifact overwritten
- **AND** the pushed artifact SHALL carry `formatVersion: 2`

---

### Requirement: MOP Artifact Projection Contents (FR04, FR05, FR06, FR19)

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
   `deepLinkUri`), `receivers[]`/`services[]` (adding `intentFilters` with `actions` and `categories`
   only, plus the boolean `hasTargetMethods`), `providers[]` (adding `authorities`). `reachesMop` is
   the wire rename of `reachesTarget`. The intent-filter `data` block, `readPermission`,
   `writePermission`, the `targetMethods` signature list and `exported` SHALL NOT be emitted.
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
     a well-typed section. A method the producer marks reaching and gives no `targetDistances` has
     flags and no distance: the derive does not invent one, so a widget whose only reaching handlers
     are such methods is flagged and carries no pair, and the jar scores it without distance.
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
     `<init>` and `<clinit>` are never handler methods. An event's flag is derived from the method's
     own `directlyReachesTarget`/`reachesTarget` on INV-DRV-01's two axes, and its pairs are the
     method's distances; two methods filling one event OR their flags and merge their pairs by the
     minimum per target. A class whose handler methods reach nothing SHALL still be listed, with
     `none` for each of its events and no `dist`: on the device a listed class states that the
     stamped handler reaches no target. The key is the class's binary name as `reachability[].className`
     writes it, which is the `Class.getName()` form gh121 stamps.
   - **K, order, omission** (INV-DRV-10). Every pair list SHALL keep the K = 3 pairs of smallest `d`,
     sorted by `d` ascending, then `i` ascending; merges are applied to the full per-target minima
     before the cut. An event with no pair SHALL have no key in a `dist` map, and an empty `dist` map
     and an `activityDist` entry with no pair SHALL be omitted. `targets` and `handlers` SHALL always
     be emitted, `0` and `{}` when empty. The widget emission filter of item 3 is unchanged: pairs do
     not make an unflagged, metadata-less widget emitted.

Derivation preconditions: the document is an object, carries a non-null `package`, and every section
it does carry is of the expected type; otherwise `DerivationError`. The producer's `"complete": true`
sentinel is NOT a precondition (INV-DRV-08). A document written by the producer's first pass — valid
JSON with populated `reachability` and `windows` per INV-ANA-20, and an empty `transitions` array —
SHALL yield an artifact whose `wtg` is empty, which the device reads through `MopData.hasWtgData()`
to disable the WTG-dependent scoring passes on its own. Structural corruption from a write interrupted
mid-pass is caught earlier, by `json.loads` in `_derive_mop_artifact()`, because the producer truncates
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
- **AND** the `click` pairs SHALL be `[[22,2]]` for `buttonGenerateHash`, `[[0,4],[1,4]]` for
  `btn_cipher_encrypt` and `[[16,3],[17,3],[18,3]]` for `executeButton`
- **AND** `handlers` SHALL have exactly the keys `br.unb.cic.cryptoapp.cipher.CipherActivity$1` and
  `br.unb.cic.cryptoapp.generated.CryptographyActivity$$ExternalSyntheticLambda0`, each with
  `mop == {"click": "transitive"}` and the `click` pairs of its widget
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

#### Scenario: a widget's distance is the minimum over its handlers, cut at three
- **WHEN** a widget's two `click` listeners resolve to methods with `targetDistances`
  `[[2,3],[5,1],[7,4]]` and `[[2,2],[9,6],[11,5]]`
- **THEN** its `dist` SHALL be `{"click": [[5,1],[2,2],[7,4]]}`
- **AND** target 2 SHALL appear once, at the smaller distance 2

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

---

### Requirement: MOP-Activity Sets and OPTIONSMENU Records (FR04)

The generator SHALL emit both activity sets. `mopActivities` is the widget-derived set of INV-DRV-02
and INV-DRV-03. `mopActivitiesAugmented` is the A′ union of three sources: the widget-derived set,
every `components.activities[]` entry with `reachesTarget == true`, and every `reachability[]` class
with `componentType == "activity"` carrying at least one method other than its own `<init>` and
`<clinit>` with `reachesTarget` or `directlyReachesTarget` true. The constructor exclusion is new in
format 2: under gh120 every activity constructor is a boundary target (its D12) and is listed reaching
itself, so without it every activity class would enter the augmented census and the A′ arm would
treat the whole app as MOP-bearing. Both sources contribute base activity names. Both sets SHALL be emitted
in sorted order, and the augmented set SHALL be a superset of the widget-derived one.

`optionsMenus` SHALL carry one record per distinct base activity owning an `OPTIONSMENU` window, with
`hasFlaggedWidget` the OR across that activity's menu windows. The gateway *set* is not shipped: it
depends on which activity set the run selects, so the jar recomputes it from these records, the WTG
view and the selected set.

#### Scenario: A′ union draws from three distinct sources
- **WHEN** the widget-derived set is `{A}`, `components.activities[]` flags `B` with
  `reachesTarget == true`, and `reachability[]` carries class `C` with `componentType == "activity"`
  and one method with `reachesTarget == true`
- **THEN** `mopActivities` SHALL equal `["A"]`
- **AND** `mopActivitiesAugmented` SHALL equal `["A", "B", "C"]`

#### Scenario: augmented set never loses a widget-derived member
- **WHEN** an activity is in the widget-derived set and flagged by no component or reachability source
- **THEN** it SHALL still appear in `mopActivitiesAugmented`

#### Scenario: OPTIONSMENU record reflects the parsed menu widgets
- **WHEN** `MainActivity#OptionsMenu` holds one flagged widget whose `idName` is empty
- **THEN** `optionsMenus` SHALL contain `{"activity": "MainActivity", "hasFlaggedWidget": true}`
- **AND** the emitted `widgets` map SHALL contain no entry for that widget

#### Scenario: an activity reaching only through its constructor stays out of source 3
- **WHEN** `derive()` runs on the gh120 cryptoapp fixture, where `MainActivity`'s only reaching method
  is `<br.unb.cic.cryptoapp.MainActivity: void <init>()>` (boundary target 23)
- **THEN** `mopActivitiesAugmented` SHALL NOT contain `br.unb.cic.cryptoapp.MainActivity`
- **AND** on that fixture `mopActivitiesAugmented` SHALL equal `mopActivities`

---

### Requirement: Canonical Serialization and Provenance (NFR04)

`derive_mop_artifact.serialize_canonical(artifact)` SHALL emit canonical bytes: UTF-8, object keys
sorted lexicographically at every level, separators `,` and `:` with no whitespace, non-ASCII
characters preserved rather than escaped, and deterministic array order — source first-occurrence for
WTG edges and component lists, sorted for the activity sets and the OPTIONSMENU records, and sorted by
`(d, i)` for every distance pair list (INV-DRV-10). Running the
generator twice on the same full-JSON bytes SHALL produce byte-identical output, so the artifact's own
digest is stable and the `source.digest` chain identifies the exact static-analysis input of every run
(INV-DRV-05).

#### Scenario: byte-identical regeneration
- **WHEN** `derive()` + `serialize_canonical()` run twice on the same full JSON in separate processes
- **THEN** the two byte sequences SHALL be identical

#### Scenario: provenance digest matches the input
- **WHEN** an artifact is generated from a full JSON whose SHA-256 is `d`
- **THEN** `source.digest` SHALL equal `"sha256:" + d`
- **AND** `source.file` SHALL be the basename of that JSON

---

### Requirement: ape.properties Generation

`ApeRVTool._push_properties()` SHALL generate an `ape.properties` file and push it to
`/data/local/tmp/ape.properties` on the device. The file SHALL be composed in a fixed order so that
two runs of the same arm produce byte-identical output:

```text
ape.preset=<preset>                                   # always first
ape.mopDataPath=/data/local/tmp/mop-artifact.json     # only when the artifact was pushed
ape.<mapped-override-key>=<value>                     # one line per overrides entry, mapping order
```

Only the entries of `_tool_config["overrides"]` are translated and written. Python-only keys
(`preset` itself apart from the first line, `strategy`, `mop_data`, `seed`, and the three
device-addressing keys) have no mapping entry and never reach
the file. Python bools SHALL be serialized lowercase (`True` → `true`). An `overrides` key with no
`APERV_PROPERTY_MAPPING` entry SHALL raise `ConfigurationError` **in `configure()`**, which is what
makes the rejection precede every `adb push` of the run rather than only the properties push: under
fail-fast a misspelled key would abort on the device anyway, and catching it on the host saves the
emulator time (same rationale as INV-APV-02).

`APERV_PROPERTY_MAPPING` is a pass-through translation table and nothing more (see "Arm Property
Overrides Pass-Through"). It SHALL contain only keys the deployed jar accepts (INV-APV-41). The 56
entries are:

| Python Key | Java Property | Notes |
|------------|--------------|-------|
| `throttle_ms` | `ape.defaultGUIThrottle` | in every preset; an override only when an arm deviates |
| `default_epsilon` | `ape.defaultEpsilon` | exploration |
| `graph_stable_restart_threshold` | `ape.graphStableRestartThreshold` | exploration |
| `state_stable_restart_threshold` | `ape.stateStableRestartThreshold` | exploration |
| `fuzzing_rate` | `ape.fuzzingRate` | `FUZZING` sub-parameter |
| `do_fuzzing` | `ape.doFuzzing` | `FUZZING` activation |
| `throttle_for_activity_transition` | `ape.throttleForActivityTransition` | exploration |
| `max_extra_priority_aliased_actions` | `ape.maxExtraPriorityAliasedActions` | exploration |
| `max_states_per_activity` | `ape.maxStatesPerActivity` | exploration |
| `trivial_activity_rank_threshold` | `ape.trivialActivityRankThreshold` | exploration |
| `do_back_to_trivial_activity` | `ape.doBackToTrivialActivity` | exploration |
| `back_menu_pick_cap` | `ape.backMenuPickCap` | exploration |
| `max_idle_timeout_ms` | `ape.maxIdleTimeoutMs` | arm-neutral tuning knob |
| `foreign_activity_guard` | `ape.foreignActivityGuard` | `FOREIGN_ACTIVITY_GUARD` |
| `tree_package_guard` | `ape.treePackageGuard` | `TREE_PACKAGE_GUARD` |
| `dynamic_epsilon` | `ape.dynamicEpsilon` | `DYNAMIC_EPSILON` |
| `heuristic_input` | `ape.heuristicInput` | `HEURISTIC_INPUT` |
| `fuzz_input_typed` | `ape.fuzzInputTyped` | `TYPED_FUZZ` |
| `form_completion_enabled` | `ape.formCompletionEnabled` | `FORM_COMPLETION` |
| `model_menu_enabled` | `ape.modelMenuEnabled` | `MODEL_MENU` |
| `least_visited_priority_tiebreak` | `ape.leastVisitedPriorityTiebreak` | `LEAST_VISITED_TIEBREAK` |
| `tree_enhancements_enabled` | `ape.treeEnhancementsEnabled` | `TREE_ENHANCEMENTS` |
| `activity_budget_enabled` | `ape.activityBudgetEnabled` | `ACTIVITY_BUDGET` |
| `mop_weight_direct` | `ape.mopWeightDirect` | `MOP` sub-parameter |
| `mop_weight_transitive` | `ape.mopWeightTransitive` | `MOP` sub-parameter |
| `mop_weight_open_menu` | `ape.mopWeightOpenMenu` | `MENU_GATEWAY` activation |
| `mop_weight_wtg` | `ape.mopWeightWtg` | `WTG` activation |
| `mop_activity_source_components` | `ape.mopActivitySourceComponents` | `MOP_ACTIVITY_SOURCE` |
| `mop_frontier_weight` | `ape.mopFrontierWeight` | `MOP_FRONTIER` activation |
| `frontier_boost_weight` | `ape.frontierBoostWeight` | `FRONTIER` activation |
| `activity_trigger_enabled` | `ape.activityTriggerEnabled` | `ACTIVITY_TRIGGER` activation |
| `activity_trigger_stagnation_step` | `ape.activityTriggerStagnationStep` | `ACTIVITY_TRIGGER` sub-parameter |
| `activity_trigger_max_per_run` | `ape.activityTriggerMaxPerRun` | `ACTIVITY_TRIGGER` sub-parameter |
| `component_percentage` | `ape.componentPercentage` | `COMPONENT_TRIGGER` activation |
| `mop_target_pick_cap` | `ape.mopTargetPickCap` | `MOP` sub-parameter |
| `mop_scoring` | `ape.mopScoring` | `MOP` sub-parameter; `"flag"` (jar default) or `"distance"`; set by the two `mopd_*` arms |
| `mop_weight_d1` | `ape.mopWeightD1` | `MOP` sub-parameter, read under `distance` only |
| `mop_weight_d2` | `ape.mopWeightD2` | `MOP` sub-parameter, read under `distance` only |
| `mop_weight_d3` | `ape.mopWeightD3` | `MOP` sub-parameter, read under `distance` only |
| `mop_retire_after` | `ape.mopRetireAfter` | `MOP` sub-parameter, read under `distance` only |
| `mop_launcher_dmax` | `ape.mopLauncherDmax` | `MOP` sub-parameter, read under `distance` only |
| `coverage_boost_weight` | `ape.coverageBoostWeight` | `COVERAGE_BOOST` activation |
| `llm_url` | `ape.llmUrl` | `LLM` activation; required on every LLM-preset arm (INV-APV-38) |
| `llm_on_new_state` | `ape.llmOnNewState` | `LLM_NEW_STATE` activation |
| `llm_on_stagnation` | `ape.llmOnStagnation` | `LLM_STAGNATION` activation |
| `llm_model` | `ape.llmModel` | `LLM` sub-parameter |
| `llm_temperature` | `ape.llmTemperature` | `LLM` sub-parameter |
| `llm_top_p` | `ape.llmTopP` | `LLM` sub-parameter |
| `llm_top_k` | `ape.llmTopK` | `LLM` sub-parameter |
| `llm_timeout_ms` | `ape.llmTimeoutMs` | `LLM` sub-parameter |
| `llm_percentage` | `ape.llmPercentage` | `LLM_RANDOM` activation |
| `llm_percentage_no_substrate` | `ape.llmPercentageNoSubstrate` | `LLM_RANDOM` sub-parameter; the `-1` sentinel is accepted on a plan with no LLM |
| `llm_prompt_variant` | `ape.llmPromptVariant` | `LLM` sub-parameter |
| `llm_max_tokens` | `ape.llmMaxTokens` | `LLM` sub-parameter |
| `llm_snap_tolerance_px` | `ape.llmSnapTolerancePx` | `LLM` sub-parameter; set by `mop_on_llm_70` and `mopd_on_llm_90` |
| `corpus_basis` | `ape.corpusBasis` | deployment provenance, echoed into `RUN_START` and read nowhere ("Corpus Basis Provenance") |

The five weight, retirement and launcher keys are mapped although no arm sets them: they are live
`MOP` sub-parameters of the jar (`llm-coordinate-single-base`, `ape` design D18–D20), and an
ablation sets them through the tool DSL. Under `ape.mopScoring=flag` the jar reports any of them
that a plan states in `RUN_START.inert`, and under `distance` it does the same for
`ape.mopWeightDirect`/`ape.mopWeightTransitive`; inert is not rejected. `step_telemetry_enabled` is not
mapped: the jar removed `ape.stepTelemetryEnabled` (telemetry is always on), and the code had
already dropped the entry this table still listed.

`mop_weight_activity → ape.mopWeightActivity` is deleted: the jar's `KeyOwnership` table lists
`ape.mopWeightActivity` as retired ("dead since mop-fairtest: the weight it named was deleted from
the scorer"), so a properties file carrying it now aborts the run rather than being ignored. No arm
set it.

A key the jar does not recognise is no longer inert. Under stage-2 resolution an unknown key, a
retired key, or a non-neutral value of an inactive feature aborts before step 1 — which is what makes
the mapping's contents a correctness property rather than a tidiness one.

#### Scenario: Preset line comes first
- **WHEN** `_push_properties()` is called for `sata_mop_llm` with the MOP artifact pushed
- **THEN** the first line SHALL be `ape.preset=llm_mop`
- **AND** the second SHALL be `ape.mopDataPath=/data/local/tmp/mop-artifact.json`
- **AND** the only remaining line SHALL be `ape.llmUrl=http://10.0.2.2:30000/v1`

#### Scenario: Empty-override arm writes two lines
- **WHEN** `_push_properties()` is called for `sata_mop` with the MOP artifact pushed
- **THEN** the file SHALL contain exactly `ape.preset=mop` and the `ape.mopDataPath` line
- **AND** no `ape.mopWeight*` line SHALL appear, because those values come from the preset

#### Scenario: Baseline arm writes one line
- **WHEN** `_push_properties()` is called for the `sata` variant
- **THEN** the file SHALL contain exactly `ape.preset=aperv`
- **AND** it SHALL NOT contain `ape.mopDataPath`, `ape.frontierBoostWeight` or `ape.dynamicEpsilon`

#### Scenario: Bools are serialized lowercase
- **WHEN** `_push_properties()` is called for `mop_on_llm_off`
- **THEN** the file SHALL contain `ape.activityTriggerEnabled=true`, not `True`
- **AND** it SHALL contain `ape.mopActivitySourceComponents=true`

#### Scenario: Unmapped override key aborts before push
- **WHEN** an arm's `overrides` contains `frontier_bost_weight` (a typo absent from
  `APERV_PROPERTY_MAPPING`)
- **THEN** `ConfigurationError` SHALL be raised naming the key
- **AND** no `adb push` SHALL have been issued

#### Scenario: Retired jar key is not in the mapping
- **WHEN** `APERV_PROPERTY_MAPPING` is inspected after this change
- **THEN** it SHALL NOT contain `mop_weight_activity`
- **AND** it SHALL contain exactly 56 entries, among them `mop_scoring`, `mop_weight_d1`,
  `mop_weight_d2`, `mop_weight_d3`, `mop_retire_after`, `mop_launcher_dmax` and `corpus_basis`
- **AND** it SHALL NOT contain `step_telemetry_enabled`
- **AND** it SHALL still contain `llm_max_tokens` and `llm_snap_tolerance_px`, which are live
  `Feature.LLM` sub-parameters

#### Scenario: Python-only keys are still excluded
- **WHEN** `_push_properties()` is called for `mop_on_llm_70`, whose `_tool_config` carries
  `strategy`, `mop_data` and `seed`
- **THEN** the properties file SHALL contain none of those three names
- **AND** it SHALL contain `ape.llmSnapTolerancePx=150`, which is an ordinary override

#### Scenario: Distance arm writes the scoring mode
- **WHEN** `_push_properties()` is called for `mopd_on_llm_off` with the MOP artifact pushed
- **THEN** the file SHALL contain `ape.mopScoring=distance`
- **AND** it SHALL contain no `ape.mopWeightD1`, `ape.mopWeightD2`, `ape.mopWeightD3`,
  `ape.mopRetireAfter` or `ape.mopLauncherDmax` line, because the arm takes the jar's defaults
  (500, 400, 300, 3 and 6)

---

### Requirement: ApeRVTool Variants (FR20)

`ApeRVTool` SHALL define named variants as `preset + overrides`. Every variant SHALL consist of a
`preset` name, an `overrides` dict, and Python-only orchestration keys (INV-APV-40).

`get_variants()` SHALL return exactly these **ten** frozen names, carrying **nine** distinct
configurations:

| Variant | preset | mop_data | overrides |
|---|---|---|---|
| `default` | `aperv` | — | _(empty)_ — bound to the same object as `sata` (INV-TOOL-02) |
| `sata` | `aperv` | — | _(empty)_ |
| `sata_mop` | `mop` | `"static_analysis"` | _(empty)_ |
| `sata_llm` | `llm` | — | `llm_url` |
| `sata_mop_llm` | `llm_mop` | `"static_analysis"` | `llm_url` |
| `mop_on_llm_off` | `mop` | `"static_analysis"` | the four reach-package keys |
| `mop_off_llm_off` | `mop` | `"static_analysis"` | the MOP-off set (see "Decisive Run Arm Set") |
| `mop_on_llm_70` | `llm_mop` | `"static_analysis"` | the reach package plus the LLM dose |
| `mopd_on_llm_off` | `mop` | `"static_analysis"` | the reach package plus `mop_scoring="distance"` |
| `mopd_on_llm_90` | `llm_mop` | `"static_analysis"` | Study 03's E6 arm 4 plus `mop_scoring="distance"` |

Four of the nine configurations are one-to-one with the jar's presets and carry nothing but the
deployment-specific server URL where an LLM is involved. Three are the E3 decisive run's arms: a
reference on the reach package, its MOP-off control, and its LLM arm. The last two select the jar's
`distance` MOP scoring (gh122): one on the reference, one on Study 03's E6 LLM arm (see "Decisive
Run Arm Set").

**Arm shape.** An arm's `preset` names one of the four jar-resident vectors; the jar, not Python,
defines what it contains. `overrides` carries only the deltas that distinguish this arm from its
preset — an arm identical to its preset carries an empty dict. Python-only keys stay at the top level
and are never written to `ape.properties`: `strategy` (the `--ape` CLI flag), `mop_data`
(`"static_analysis"` triggers the derived-artifact push, unchanged), `seed`, and the two B3
jar-provenance declarations. The explicit `overrides` sub-dict rather than a flat dict is what keeps
the boundary machine-checkable: everything under `overrides` is translated and written, everything at
the top level is orchestration.

Every LLM-preset arm SHALL carry `llm_url` in its overrides (INV-APV-38) — the preset omits the
deployment-specific server URL while stating the routing gates ON, so its absence aborts resolution.
`throttle_ms` SHALL NOT appear in any arm: the `aperv` preset already states
`ape.defaultGUIThrottle=200`, which every arm used. Ablations SHALL be expressed as named override
sets, never as new presets: the preset vocabulary belongs to the jar.

`sata_mop` is the frozen-corpus name and SHALL NOT be renamed or folded away: 4,096
`aperv:sata_mop.trace` artifacts and 1,066 files under `results/` carry that exact token, so a rename
would orphan every one of those runs from resume and every one of those rows from consolidation. This
is a data-identity constraint, not backward compatibility (INV-APV-42).

#### Retired variants

Twenty-one names are retired. Retiring a name is a decision about the experimental matrix — Python's
authority — and touches no jar mechanism: every key those arms set remains in the mapping, and every
feature they activated remains implemented.

| Retired | Kind | Disposition |
|---|---|---|
| `ape_pure` | never distinct | purity is structural in the jar; `ape.apePureMode` is a retired key that aborts resolution. The comparison with original APE stays anchored on the frozen phase-2 data |
| `bfs` | never distinct | never an agent type; always carried `sata`'s effective configuration |
| `sata_mop_widget` | never distinct | one object under two names; `sata_mop` is the surviving name |
| `sata_mop_act_frontier` | name consolidated | byte-identical to `mop_on_llm_off`; the configuration survives under that name |
| `sata_mop_activity` | finished campaign | an intermediate step of the reach decomposition, superseded by the reach package |
| `random` | finished campaign | the `random` strategy stays in the `configure()` whitelist and remains reachable as `aperv:sata@strategy=random`; what ends is the named arm |
| the six `sata_mop_llm_<prompt>` arms | finished campaign | the gh43 prompt ablation concluded; recorded results are unaffected |
| the nine `cal_a1`…`cal_a9` arms | finished campaign | the Phase-A calibration campaign concluded (VERIFY `ADMISSIBLE`, 2026-07-24) and phases B and C were superseded by the decisive run's pre-registration freeze |

Retirement removes the ability to launch new runs under a name. It does not invalidate recorded
results: those are frozen artifacts, read by frozen-corpus analysis scripts that this change does not
touch.

Every surviving arm's effective configuration after re-expression SHALL be identical to its
pre-change effective configuration (INV-APV-44); any intentional divergence requires owner approval
and a new arm name (INV-APV-42).

#### Scenario: Preset-identity arm carries nothing

- **WHEN** `get_variants()["sata_mop"]` is read
- **THEN** `preset` SHALL be `"mop"` and `overrides` SHALL be empty
- **AND** `mop_data` SHALL be `"static_analysis"` at the top level
- **AND** the same emptiness SHALL hold for `sata` and `default` against the `aperv` preset

#### Scenario: LLM arm carries the server URL and nothing else

- **WHEN** `get_variants()["sata_mop_llm"]` is read
- **THEN** `preset` SHALL be `"llm_mop"` and `overrides` SHALL be exactly
  `{"llm_url": "http://10.0.2.2:30000/v1"}`
- **AND** every variant whose preset is `llm` or `llm_mop` SHALL likewise carry `llm_url`
  (INV-APV-38)

#### Scenario: The reach package survives under the reference arm

- **WHEN** `get_variants()["mop_on_llm_off"]` is read
- **THEN** `preset` SHALL be `"mop"` and `overrides` SHALL contain exactly
  `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_frontier_weight=200`,
  `activity_trigger_enabled=True`
- **AND** no MOP weight key SHALL appear, because the `mop` preset already states
  `ape.mopWeightDirect=500`, `ape.mopWeightTransitive=300`, `ape.mopWeightOpenMenu=250` and
  `ape.mopWeightWtg=200`
- **AND** its effective configuration SHALL equal the baseline entry captured for the retired
  `sata_mop_act_frontier`

#### Scenario: The frozen corpus name keeps resolving

- **WHEN** `get_variants()` is read
- **THEN** `"sata_mop"` SHALL be present
- **AND** a resume over an existing `aperv:sata_mop` result directory SHALL still match its arm
- **AND** `"sata_mop_widget"` SHALL NOT be a key, so there is no alias left to keep in lockstep

#### Scenario: Retired variants are absent

- **WHEN** `get_variants()` is read after this change
- **THEN** the mapping SHALL have exactly ten keys
- **AND** none of `ape_pure`, `bfs`, `random`, `sata_mop_widget`, `sata_mop_activity`,
  `sata_mop_act_frontier`, the six `sata_mop_llm_<prompt>` names or `cal_a1`…`cal_a9` SHALL be among
  them
- **AND** the module SHALL contain no `_APE_PURE_ARM_FLAGS` constant
- **AND** all 21 SHALL appear in the migration arm report as documented retirements carrying their
  kind, not as diffs

#### Scenario: No arm carries a property expansion

- **WHEN** any variant returned by `get_variants()` is inspected
- **THEN** its top-level keys SHALL be drawn only from `preset`, `overrides`, `strategy`, `mop_data`
  and `seed`
- **AND** no variant SHALL carry `expected_jar_git_sha` or `expected_jar_sha256` (INV-APV-59)
- **AND** the module SHALL contain none of `_BASELINE_ARM_FLAGS`, `_MOP_SUBSTRATE`, `_LLM_FLAGS`,
  `_FRONTIER_SUBSTRATE`, `_MOP_OFF_OVERRIDES` or `_CAL_LLM_COMMON`
- **AND** no variant SHALL contain a `throttle_ms` key

---

### Requirement: Decisive Run Arm Set (FR20)

`aperv-tool` SHALL define the three arms of the E3 decisive run and the two distance arms as named
variants, so that each arm's identity comes from its preset and override dict and never from an
undeclared inheritance. The five arms SHALL be:

1. **`mop_on_llm_off`** — reference: MOP guidance on, LLM off. The shared baseline of both contrasts.
2. **`mop_off_llm_off`** — control: MOP guidance off, LLM off. Isolates the effect of MOP guidance
   (the study's central hypothesis).
3. **`mop_on_llm_70`** — LLM arm: MOP guidance on, LLM on at `llm_percentage=0.7`. Isolates the effect
   of adding the LLM.
4. **`mopd_on_llm_off`** — distance arm: the reference with the jar's MOP scoring switched from the
   E6 yes/no mark to the static distance (`mop_scoring="distance"`, `ape` design D18). With the
   `ape` jar of `llm-coordinate-single-base` both this arm and the reference carry the ordered MOP
   shortcut, so arms 2, 1 and 4 are the minimal family the plan analysis proposes (rv-android
   `docs/20261006_analise_rigorosa_plano_guia_mop.md:315-319`: no guidance; the E6 mark plus the
   ordered shortcut; the distance plus the ordered shortcut). Arm 4 against arm 1 isolates the
   distance.
5. **`mopd_on_llm_90`** — distance arm under the LLM: Study 03's E6 arm 4 (`e6_mop_on_llm_90`, defined
   in the Study 03 replication package as E5b's selected arm `e5b_m1_v13_A` key by key with
   `llm_percentage` 0.9; `rvsec_study03/e6/config.py`, `experiments/E5b-inloop/config/tool.py:575-592`)
   plus `mop_scoring="distance"`. It carries the model, engine-facing sampling and dose Study 03
   froze. Its flag-mode counterpart is that replication-package arm, not an arm of this module.

The variant names are normative, not cosmetic: the variant string is the resume identity key and the
consolidation column key, so a rename silently splits a campaign's results.

`mop_on_llm_off` absorbs the retired `sata_mop_act_frontier`: the two carried byte-identical effective
configurations — the ANC2 anchor under two names — so the reference arm is not a newly invented
baseline but the configuration that won the cmpma multi-arm comparison, under the name the decisive
run recorded. With `sata_mop_act_frontier` retired, these five are the only arms in the module that
carry a non-trivial override set; the other four are one-to-one with the jar's presets.

All five SHALL carry `mop_data="static_analysis"` and the frontier substrate (INV-APV-30) — the
control removes MOP guidance, not navigation. Expressed as preset + overrides:

| Arm | preset | overrides |
|---|---|---|
| `mop_on_llm_off` | `mop` | `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_frontier_weight=200`, `activity_trigger_enabled=True` |
| `mop_off_llm_off` | `mop` | `mop_activity_source_components=True`, `frontier_boost_weight=200`, `mop_weight_direct=0`, `mop_weight_transitive=0`, `mop_weight_open_menu=0`, `mop_weight_wtg=0` |
| `mop_on_llm_70` | `llm_mop` | the reference's four, plus `llm_url`, `llm_prompt_variant="v13"`, `llm_percentage=0.7`, `llm_temperature=0`, `llm_snap_tolerance_px=150` |
| `mopd_on_llm_off` | `mop` | the reference's four, plus `mop_scoring="distance"` |
| `mopd_on_llm_90` | `llm_mop` | the reference's four, plus `llm_url`, `llm_prompt_variant="v13"`, `llm_percentage=0.9`, `llm_temperature=0`, `llm_snap_tolerance_px=150`, `llm_model="Qwen/Qwen3-VL-4B-Instruct-FP8"`, `llm_top_p=1.0`, `llm_top_k=-1`, `mop_scoring="distance"` |

The control's shape is fixed by INV-APV-29 and is now expressed jointly by the preset and the
overrides: `mop_data` present and loadable (top-level), all four MOP weights zeroed and
`mop_frontier_weight` at the preset's `0` (so `WTG`, `MENU_GATEWAY` and `MOP_FRONTIER` are inactive at
their neutral values), and `activity_trigger_enabled` at the preset's `false`. `frontier_boost_weight`
stays at `200` deliberately, keeping `FRONTIER` active. The alternatives are worse and were rejected
for reasons that have not changed: pointing `ape.mopDataPath` at a missing file aborts the run, and
omitting `mop_data` kills the generic WTG and frontier passes as collateral, turning the contrast into
"full substrate versus almost none".

Single-factor remains a property of the **effective plan**, and the override dicts now make it
readable directly. Reference minus control is exactly the five MOP weight keys plus
`activity_trigger_enabled`; reference minus LLM arm is exactly the LLM keys, with no exemption. The
two B3 jar declarations that used to be that exemption are gone (INV-APV-59), so the diff no longer
needs an argument about why an extra pair of keys is harmless — the arms differ in the LLM keys and
in nothing else. The distance arms keep the same discipline: `mopd_on_llm_off` minus the reference is
exactly `ape.mopScoring`, and `mopd_on_llm_90` minus `mopd_on_llm_off` is exactly LLM keys.

Neither distance arm states the distance weights, the retirement count or the launcher bound: they
take the jar's defaults (500/400/300 for `d ≤ 1`/`2`/`3`, retirement after 3 first interactions,
launcher bound 6), which are the plan's decision-10 values the `ape` author adopted. An arm that
changed one of them would be a new arm, not an edit of these (INV-APV-42). Both need the jar built
from `llm-coordinate-single-base`: no earlier jar knows `ape.mopScoring`, and stage-2 resolution
aborts on an unknown key.

#### Scenario: Control arm keeps the frontier alive while MOP guidance is off
- **WHEN** `get_variants()["mop_off_llm_off"]` is resolved
- **THEN** `mop_data` SHALL equal `"static_analysis"`
- **AND** `overrides` SHALL contain `mop_weight_direct=0`, `mop_weight_transitive=0`,
  `mop_weight_open_menu=0`, `mop_weight_wtg=0`
- **AND** `overrides` SHALL contain `frontier_boost_weight=200`, so generic WTG and frontier
  navigation stay enabled (INV-APV-30)
- **AND** `mop_frontier_weight` and `activity_trigger_enabled` SHALL be absent from `overrides`,
  taking the `mop` preset's `0` and `false`

#### Scenario: Control arm never omits the static analysis document
- **WHEN** the guard test inspects the control arm's variant dictionary
- **THEN** `mop_data` SHALL be present at the top level
- **AND** the test SHALL fail naming INV-APV-29 if it is absent, because an absent document disables
  `WtgPass` and `FrontierPass` as collateral damage

#### Scenario: Reference and control differ only in MOP keys
- **WHEN** the effective configurations of `mop_on_llm_off` and `mop_off_llm_off` are diffed
- **THEN** the differing keys SHALL be exactly `ape.mopWeightDirect`, `ape.mopWeightTransitive`,
  `ape.mopWeightOpenMenu`, `ape.mopWeightWtg`, `ape.mopFrontierWeight` and
  `ape.activityTriggerEnabled`
- **AND** every other key SHALL be identical, so the contrast is single-factor

#### Scenario: Reference and LLM arm differ only in LLM keys
- **WHEN** the effective configurations of `mop_on_llm_off` and `mop_on_llm_70` are diffed
- **THEN** every differing key SHALL be an `ape.llm*` key
- **AND** the two arms' top-level keys SHALL be identical, neither carrying a jar declaration
  (INV-APV-59)
- **AND** no MOP weight, frontier or exploration key SHALL differ

#### Scenario: Source components flag is explicit in all three arms
- **WHEN** the five arms of this requirement are iterated
- **THEN** each SHALL carry `mop_activity_source_components=True` in its `overrides`
- **AND** none SHALL rely on the `mop` preset's `false`

#### Scenario: Distance arm differs from the reference only in the scoring mode
- **WHEN** the effective configurations of `mop_on_llm_off` and `mopd_on_llm_off` are diffed
- **THEN** the only differing key SHALL be `ape.mopScoring`, `distance` in `mopd_on_llm_off` and the
  jar default `flag` in the reference
- **AND** both SHALL carry `mop_data="static_analysis"` at the top level

#### Scenario: Distance LLM arm is the E6 arm plus the scoring mode
- **WHEN** `get_variants()["mopd_on_llm_90"]["overrides"]` is read
- **THEN** it SHALL equal, key for key, the overrides of the Study 03 arm `e6_mop_on_llm_90` plus
  `mop_scoring="distance"`: `llm_percentage` 0.9, `llm_temperature` 0, `llm_top_p` 1.0,
  `llm_top_k` -1, `llm_model` `"Qwen/Qwen3-VL-4B-Instruct-FP8"`, `llm_prompt_variant` `"v13"`,
  `llm_snap_tolerance_px` 150, `llm_url`, and the reference's four reach-package keys
- **AND** the effective configurations of `mopd_on_llm_off` and `mopd_on_llm_90` SHALL differ only in
  `ape.llm*` keys
