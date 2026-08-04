# Delta: aperv (gh96-mop-artifact-derivation)

## Purpose

This delta relocates the parse-time semantics of the APE-RV MOP substrate from the device to this
repository. Until now the jar received the full static-analysis JSON and derived, on-device and at
load time, everything the explorer actually consumes: the per-widget MOP flags, the two MOP-activity
sets, the OPTIONSMENU gateway inputs, the click-only WTG view and the component trigger surface. The
call-graph section that dominates the file is never read by the explorer — it exists only as an input
to that derivation. Moving the derivation host-side lets the device receive the *result* instead of
the raw material, which removes the on-device parse of megabytes, removes the footprint guard that
made call-graph-heavy apps abort with 0 steps in MOP arms while the baseline explored normally, and
puts the semantics in pure Python where each rule is a unit test rather than a JSON fixture.

`aperv-tool` is the right home for the generator because it already owns both ends of this path: it
locates the full JSON (`_find_static_analysis_file`), shapes it, pushes it, and writes the property
that tells the jar where it landed. Placing `derive_mop_artifact.py` next to `tool.py` keeps the blast
radius at one module and keeps the derivation code adjacent to the only consumer of its output
contract. The derivation itself is a pure function — full-JSON dict in, compact artifact dict out —
with no I/O, no device interaction and no dependency on the tool object, so the eight relocated rules
are testable in isolation on synthetic fragments.

Two behaviours change beyond relocation, and both are recorded here rather than smuggled in as
"subsumed by the derivation". First, a MOP arm whose static-analysis JSON is absent used to warn and
continue, executing as pure SATA under a MOP arm's label; it now fails the task. Second, the listener
enrichment that `_compact_static_analysis_json` performed on every push is deleted with it, and with
it the redefinition of `handlerDirectlyReachesTarget` (the retired INV-APV-32). That enrichment wrote
the any-depth reach bit into both handler-reach fields, which made the jar take its producer-precedence
branch unconditionally — so `directMop` stopped meaning "the handler calls a monitored operation in
its own body", and the D8 synthetic-lambda recovery, which lives in the other branch, never executed
in production. The generator restores the two axes as the producer defines them and applies the D8
recovery to both, because a rule must hold for any app, not only for the apps measured so far: the
pinned corpus happens to contain no 0-hop handler, but that is a property of those 345 apps, not of
Android.

The full static-analysis JSON is untouched by all of this. It stays byte-identical in
`<results_dir>`, remains the sole input of every metric and offline-consolidation path, and is simply
no longer the thing that travels to the device.

## Data Contracts

### Input
- `<task.results_dir>/<task.config.apk_name>.json` — full static-analysis JSON produced by
  pre-processing; located by `_find_static_analysis_file(task)` (unchanged). Requires
  `complete == true` and a non-null `package` to be derivable.
- `<task.results_dir>/<task.config.apk_name>.mop.json` — previously cached derived artifact, when one
  exists.

### Output
- `<task.results_dir>/<task.config.apk_name>.mop.json` — the derived compact MOP artifact
  (`formatVersion: 1`), canonical bytes, written atomically.
- `/data/local/tmp/mop-artifact.json` — the same bytes on the device (MOP arms only).
- `ape.properties` line `ape.mopDataPath=/data/local/tmp/mop-artifact.json` (MOP arms with a
  successful push only).

### Side-Effects
- **[Host filesystem]**: one cached artifact per (apk, full-JSON digest), regenerated transparently
  when missing or stale. The full JSON is never written to.
- **[Device]**: one pushed file per MOP-arm run.

### Error
- `DerivationError` — raised by `derive()` when the document is structurally unusable (`complete`
  absent or false, missing `package`, a section of the wrong type). No partial artifact is produced.
- `RVToolExecutionError` — raised by `execute_tool_specific_logic()` when a MOP arm has no full JSON,
  when derivation fails, or when the push fails. Non-MOP arms are unaffected.

## Invariants

Numbering note: `INV-APV-38` through `INV-APV-44` are deliberately left free for `gh95-thin-python-arms`,
which the sibling `ape` change already references by number.

- **INV-APV-45**: An arm configured with `mop_data == "static_analysis"` SHALL either push a
  freshly-validated derived artifact and write `ape.mopDataPath`, or fail the task before the jar is
  launched. There SHALL be no execution path in which such an arm launches the jar without
  `ape.mopDataPath` set.
- **INV-APV-46**: The device SHALL only ever receive the derived compact artifact. No code path SHALL
  push the full static-analysis JSON, under any cache state or failure mode.
- **INV-APV-47**: Cache freshness SHALL be digest-based: a cached `<apk_name>.mop.json` is reused only
  when its recorded `source.digest` equals the SHA-256 of the current full JSON. Cache state SHALL
  NOT change what the device receives for a given full JSON.
- **INV-DRV-01**: Widget MOP flags SHALL be derived per listener and per normalized `eventType` and
  OR-aggregated across a widget's listeners. The two axes SHALL remain independent and SHALL NOT be
  collapsed into each other: `direct` is the handler's own `directlyReachesTarget` (a monitored
  operation invoked in the handler's own body) and `transitive` is its `reachesTarget` OR `direct`,
  so `direct` implies `transitive` and the converse does not hold. A producer-supplied
  `handlerReachesTarget`/`handlerDirectlyReachesTarget` pair takes precedence over the local
  cross-reference when either is non-null. A handler with no exact `reachability[].methods[].signature`
  match that is a D8 synthetic-lambda wrapper (`X$$ExternalSyntheticLambdaN`) SHALL be recovered from
  `X`'s reaching `lambda$…` methods, and SHALL NOT be flagged when `X` has no reaching lambda method.
- **INV-DRV-02**: On a `shortId` collision within a base activity the emitted widget SHALL carry the
  strongest MOP flag (direct > transitive > unflagged), ties keeping the first occurrence, so the
  outcome is independent of iteration order. Widgets with an empty short id SHALL NOT be emitted and
  the count of MOP-flagged widgets so dropped SHALL be recorded in `stats.droppedFlaggedNoId`. **A
  MOP-flagged widget SHALL add its base activity to the widget-derived MOP-activity set before the
  empty-short-id drop is applied**: the widget is unscorable, the activity is not.
- **INV-DRV-03**: DIALOG windows SHALL be merged into their host activity — first incoming transition
  wins, `mopRank` collision policy, the dialog's widget-map key is moved and not copied, a flagged
  merge adds the host to the widget-derived activity set, and the dialog class's own activity-set
  entry is retained. WTG edges SHALL be keyed by base source activity with base target activities,
  click events only, exact duplicates removed. Orphan dialogs SHALL be counted in
  `stats.orphanDialogs`.
- **INV-DRV-04**: All `stats` fields SHALL be pure counters over the derivation. Their values SHALL
  NOT influence any emitted set, flag or edge.
- **INV-DRV-05**: Derivation SHALL be deterministic at the byte level: identical full-JSON input bytes
  SHALL yield an identical artifact byte sequence, on any host and in any process.
- **INV-DRV-06**: The artifact SHALL contain no `*Target` key and no call-graph data — no
  `reachability` section, no method signatures, no raw `windows`/`transitions`/`listeners`. The full
  JSON SHALL remain unmodified on the host.
- **INV-DRV-07**: Each emitted activity SHALL carry `deepLinkUri` derived by the rule the jar applies
  today; the intent-filter structure itself SHALL NOT be on the wire.

## ADDED Requirements

### Requirement: Derived MOP Artifact Generation and Caching (FR19, NFR04)

`ApeRVTool._derive_mop_artifact(task)` SHALL return the host path of the compact MOP artifact for the
task's APK, generating it when needed:

1. Compute the SHA-256 of the current full JSON at `<results_dir>/<apk_name>.json`.
2. When `<results_dir>/<apk_name>.mop.json` exists and its `source.digest` equals `"sha256:" + <hex>`,
   reuse it without regenerating.
3. Otherwise call `derive()` + `serialize_canonical()` and write the artifact atomically
   (write-temp-then-rename in the same directory). A failed derivation SHALL write nothing.

The artifact is cached next to its source so it is inspectable and diffable, and it is a pure function
of the full JSON (INV-APV-47, INV-DRV-05). This method replaces `_compact_static_analysis_json`,
which is deleted together with its fallback-to-source push: there is no longer any condition under
which the full JSON reaches the device (INV-APV-46).

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
- **WHEN** `derive()` raises `DerivationError` because the document carries `complete: false`
- **THEN** no `<apk_name>.mop.json` SHALL exist afterwards, and any partially written temporary file
  SHALL be removed
- **AND** `RVToolExecutionError` SHALL be raised carrying the derivation error

---

### Requirement: MOP Artifact Projection Contents (FR04, FR05, FR06, FR19)

`derive_mop_artifact.derive(document)` SHALL produce a `formatVersion: 1` artifact containing exactly
the projection the explorer consumes:

1. **Scalars**: `package` and `mainActivity` copied verbatim from the full JSON.
2. **Provenance**: `source.digest` (`"sha256:" + hex` of the full-JSON bytes), `source.file`
   (basename) and `source.generator` (generator identifier and version).
3. **Widgets** (`widgets.<baseActivity>.<shortId>`): a per-normalized-eventType `mop` map with values
   `none|direct|transitive|both`, plus the consumed metadata fields `inputType`, `hint`, `prompt`,
   `spinnerMode`, `contentDescription`, `tooltipText` and `entries`, each emitted only when non-empty.
   A widget SHALL be emitted only when it is MOP-flagged OR carries at least one metadata field. The
   keys `id`, `type`, `text` and the raw `listeners` array SHALL NOT be emitted. Map keys SHALL be
   pre-normalized (lowercased, `_` and `-` removed), matching the query-side normalization.
4. **Activity sets**: `mopActivities` (widget-derived, per INV-DRV-02 and the dialog promotion of
   INV-DRV-03) and `mopActivitiesAugmented` (the A′ union), both always emitted so the on-device
   `mopActivitySourceComponents` flag keeps selecting between them at run time.
5. **OPTIONSMENU records**: `optionsMenus: [{activity, hasFlaggedWidget}]`, where `hasFlaggedWidget`
   is true when any widget of that menu window is MOP-flagged — tested over the window's parsed
   widgets, before the empty-id drop, for the same reason INV-DRV-02 states.
6. **WTG**: `wtg.<sourceBaseActivity> = [{widget, target}]` per INV-DRV-03. `widgetClass` SHALL NOT be
   emitted.
7. **Components**: `activities[]` (`className`, `isMain`, `exported`, `permission`, `reachesMop`,
   `deepLinkUri`), `receivers[]`/`services[]` (adding `intentFilters` with `actions` and `categories`
   only, plus the boolean `hasTargetMethods`), `providers[]` (adding `authorities`). `reachesMop` is
   the wire rename of `reachesTarget`. The intent-filter `data` block, `readPermission`,
   `writePermission` and the `targetMethods` signature list SHALL NOT be emitted.
8. **Stats**: `windows`, `widgetsTotal`, `flagged`, `droppedFlaggedNoId`, `orphanDialogs`,
   `handlersUnmatched`, `syntheticLambda`, `recovered`, `wtgEdges`, `dedupedTransitions`.
   `widgetsTotal` and `flagged` SHALL count the widget map after the dialog merge and before the
   emission filter of item 3, so they remain the numbers the jar's load record reported.

Derivation preconditions: `document["complete"] is True` and a non-null `package`; otherwise
`DerivationError`. A truncated analysis SHALL never yield an artifact — the completeness sentinel
becomes a generation precondition instead of a device-side check.

#### Scenario: cryptoapp derivation matches the known ground truth
- **WHEN** `derive()` runs on `cryptoapp.apk.gh60-fresh.json`
- **THEN** `mopActivities` SHALL equal `{MessageDigestActivity, CipherActivity}` (base names)
- **AND** `optionsMenus` SHALL contain the `MainActivity` record, and `wtg` SHALL carry the click
  edges from `MainActivity` to both MOP sub-activities
- **AND** `components.activities` SHALL have 4 entries and `components.providers` 1 entry with
  `authorities == "br.unb.cic.cryptoapp.androidx-startup"`, every component `reachesMop == false`
- **AND** `stats.windows` SHALL be 5

#### Scenario: incomplete full JSON refuses to derive
- **WHEN** `derive()` runs on a document whose `complete` key is absent or `false`
- **THEN** `DerivationError` SHALL be raised
- **AND** no artifact SHALL be produced

#### Scenario: no Target vocabulary and no call graph on the wire
- **WHEN** any artifact is generated
- **THEN** it SHALL contain no key matching `*Target*`
- **AND** it SHALL contain no `reachability`, `windows`, `transitions` or `listeners` section
  (INV-DRV-06)

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

---

### Requirement: Widget MOP Flag Derivation (FR04, FR06)

The generator SHALL derive each widget's MOP flags from its listeners, per normalized `eventType`,
and OR-aggregate them across listeners (INV-DRV-01). For each listener:

1. When `handlerDirectlyReachesTarget` or `handlerReachesTarget` is non-null, the producer's values
   win: `direct` is `handlerDirectlyReachesTarget is True`, `transitive` is
   `handlerReachesTarget is True or direct`.
2. Otherwise the handler signature is looked up in the index built from `reachability[].methods[]`,
   which SHALL carry, per signature, the pair (`directlyReachesTarget`, `reachesTarget or
   directlyReachesTarget`). Duplicate signatures SHALL be merged by OR rather than by last-write, so
   the index does not depend on producer ordering.
3. When the exact lookup misses and the handler matches `^<(.+?)\$\$ExternalSyntheticLambda\d+:`, the
   flags SHALL be recovered from the enclosing class's reaching `lambda$…` methods, OR-aggregated;
   when that class has no reaching lambda method the widget SHALL NOT be flagged.

The two axes SHALL NOT be collapsed. `direct` retains the producer's 0-hop meaning — the handler
invokes a monitored operation in its own body — which is what `ape.mopWeightDirect` was defined to
reward, and `transitive` is the any-depth reach implied by it. A listener whose `eventType` is null
contributes to the aggregates but produces no wire key, since a null key is unaddressable by the
query side; the generator SHALL nonetheless emit an aggregate consistent with it.

#### Scenario: producer-supplied flags take precedence
- **WHEN** a listener carries `handlerReachesTarget: true` and `handlerDirectlyReachesTarget: false`
- **AND** the handler's signature is absent from `reachability`
- **THEN** the widget's `click` entry SHALL be `transitive`, not `none`

#### Scenario: direct implies transitive
- **WHEN** the handler's method carries `directlyReachesTarget: true` and `reachesTarget: false` — the
  shape 33 methods across 16 corpus apps actually have
- **THEN** the derived flags SHALL be `direct == true` and `transitive == true`, emitted as `both`
- **AND** no widget SHALL ever be emitted with `direct` set and `transitive` unset

#### Scenario: D8 synthetic-lambda handler is recovered
- **WHEN** a widget's click listener has handler
  `<com.example.MainActivity$$ExternalSyntheticLambda0: void onClick(android.view.View)>` with no
  matching signature in `reachability`
- **AND** `com.example.MainActivity` has a method `lambda$onCreate$0` with `reachesTarget: true`
- **THEN** the widget's `click` entry SHALL be `transitive`
- **AND** `stats.recovered` SHALL count it

#### Scenario: synthetic-lambda wrapper with no reaching lambda stays unflagged
- **WHEN** the same wrapper shape occurs but `com.example.MainActivity` has no `lambda$…` method with
  `reachesTarget` or `directlyReachesTarget` true
- **THEN** the widget SHALL NOT be flagged
- **AND** `stats.syntheticLambda` SHALL count the wrapper while `stats.recovered` SHALL NOT

#### Scenario: per-event flags are independent
- **WHEN** a widget has a `click` listener reaching a monitored operation and a `long_click` listener
  reaching nothing
- **THEN** the wire map SHALL carry `{"click": "transitive", "longclick": "none"}`
- **AND** the `none` entry SHALL be emitted explicitly, because key presence is what suppresses the
  aggregate fallback on the query side

---

### Requirement: Widget Map Keying, Collisions and Activity Marking (FR06)

Widgets SHALL be keyed `baseActivity → shortId`, where the base activity is the window name truncated
at the first `#`. Windows sharing a base activity (an activity and its `#OptionsMenu`, for instance)
SHALL accumulate into the same map under the collision policy of INV-DRV-02.

A MOP-flagged widget SHALL add its base activity to the widget-derived MOP-activity set **before** the
empty-short-id drop is evaluated. Deriving the set from the emitted map instead would silently shrink
it, and the loss cascades into `scoreWtg`, the frontier passes, the `stateMopDensity` floor, the
OPTIONSMENU gateway's second condition and the launcher census — with a normal `status=loaded` in the
trace. The pinned corpus exercises this: 19 apps carry at least one flagged widget with an empty
`idName`, 1,263 such widgets in total.

#### Scenario: a flagged widget with an empty short id still marks its activity
- **WHEN** the only MOP-flagged widget of base activity `com.example.CryptoActivity` carries
  `idName == ""`
- **THEN** the artifact SHALL NOT contain a widget entry for it
- **AND** `stats.droppedFlaggedNoId` SHALL count it
- **AND** `mopActivities` SHALL nevertheless contain `com.example.CryptoActivity` (INV-DRV-02)

#### Scenario: collision keeps the strongest flag regardless of order
- **WHEN** two widgets in the same base activity share `shortId == "btn_ok"`, one unflagged with a
  `hint` and one flagged `direct`
- **THEN** the emitted entry SHALL be the flagged one, whichever appears first in `windows[]`

#### Scenario: equal-rank collision keeps the first occurrence
- **WHEN** two unflagged widgets share `shortId == "btn_ok"`, the first carrying `hint == "user"` and
  the second `hint == "password"`
- **THEN** the emitted entry SHALL carry `hint == "user"`

---

### Requirement: DIALOG Re-Keying and WTG Click View (FR05)

DIALOG windows SHALL be re-keyed to their host activity before the activity sets are finalized, and
the WTG view SHALL be a deduplicated, click-only projection keyed by base source activity
(INV-DRV-03). The five coupled dialog sub-rules are: the host is the source of the **first** incoming
transition whose source window has a name; merging uses the same `mopRank` collision policy as widget
keying; the dialog's widget-map key is **moved**, not copied, so counts do not inflate; a merge that
carried at least one flagged widget promotes the host into the widget-derived activity set; and the
dialog class's own entry in that set is **retained**, because WTG edges into the dialog are keyed by
it and the OPTIONSMENU gateway tests membership of the edge target.

A dialog with no incoming transition is an orphan: it keeps its own key and is counted in
`stats.orphanDialogs`. WTG edges SHALL record `widget` (the transition event's `widgetName`, empty
string when absent) and `target` (the base target activity); exact duplicate edges within a source
SHALL be removed and counted in `stats.dedupedTransitions`.

#### Scenario: flagged dialog promotes its host and moves its widgets
- **WHEN** window `android.app.AlertDialog` has one flagged widget `btn_confirm` and the first
  incoming transition comes from `com.example.MainActivity`
- **THEN** `widgets["com.example.MainActivity"]["btn_confirm"]` SHALL exist
- **AND** `widgets` SHALL have no `android.app.AlertDialog` key
- **AND** `mopActivities` SHALL contain both `com.example.MainActivity` and `android.app.AlertDialog`

#### Scenario: first incoming edge wins
- **WHEN** a DIALOG window has incoming transitions from `ActivityA` and then `ActivityB`
- **THEN** its widgets SHALL merge into `ActivityA`

#### Scenario: orphan dialog keeps its key
- **WHEN** a DIALOG window has no incoming transition
- **THEN** its widget-map key SHALL remain the dialog class
- **AND** `stats.orphanDialogs` SHALL count it

#### Scenario: WTG keeps click edges only, deduplicated, by base activity
- **WHEN** `transitions[]` carries two identical click events from window `MainActivity#OptionsMenu`
  to `CipherActivity` and one `long_click` event between the same pair
- **THEN** `wtg["MainActivity"]` SHALL contain exactly one entry targeting `CipherActivity`
- **AND** `stats.dedupedTransitions` SHALL count the removed duplicate

---

### Requirement: MOP-Activity Sets and OPTIONSMENU Records (FR04)

The generator SHALL emit both activity sets. `mopActivities` is the widget-derived set of INV-DRV-02
and INV-DRV-03. `mopActivitiesAugmented` is the A′ union of three sources: the widget-derived set,
every `components.activities[]` entry with `reachesTarget == true`, and every `reachability[]` class
with `componentType == "activity"` carrying at least one method with `reachesTarget` or
`directlyReachesTarget` true. Both sources contribute base activity names. Both sets SHALL be emitted
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

---

### Requirement: Per-Activity Deep-Link URI (FR19)

Each emitted activity SHALL carry `deepLinkUri`, assembled host-side by the rule the jar applies
today: the first intent-filter that declares `android.intent.action.VIEW` **and** a non-empty scheme
list yields `scheme + "://" + host + path`, where host and path are the filter's first entries or the
empty string when absent. When no filter qualifies the field SHALL be absent, which the dispatcher
reads as "use the explicit-component intent" (INV-DRV-07). The filter structure SHALL NOT be on the
wire.

This field is not optional decoration: the MOP stagnation launcher dispatches `ACTION_VIEW` on it, so
dropping it would make activities reachable only by deep link unopenable while the trace still
reported a normal load.

#### Scenario: deep link derived from the first ACTION_VIEW filter
- **WHEN** an activity declares an intent-filter with `android.intent.action.VIEW` and
  `data.schemes == ["myapp"]`, `data.hosts == ["detail"]`, `data.paths == ["/x"]`
- **THEN** its `deepLinkUri` SHALL be `"myapp://detail/x"`

#### Scenario: ACTION_VIEW without schemes yields no URI
- **WHEN** the only `ACTION_VIEW` filter has an empty scheme list
- **THEN** `deepLinkUri` SHALL be absent

#### Scenario: schemes without ACTION_VIEW yield no URI
- **WHEN** a filter declares `data.schemes == ["myapp"]` but its actions do not include
  `android.intent.action.VIEW`
- **THEN** `deepLinkUri` SHALL be absent

#### Scenario: activity without intent filters yields no URI
- **WHEN** an activity declares no intent-filter at all
- **THEN** `deepLinkUri` SHALL be absent
- **AND** the artifact SHALL carry no `data` block, scheme list, host list or path list

#### Scenario: missing host and path default to empty
- **WHEN** the qualifying filter carries `data.schemes == ["myapp"]` with empty host and path lists
- **THEN** `deepLinkUri` SHALL be `"myapp://"`

---

### Requirement: Canonical Serialization and Provenance (NFR04)

`derive_mop_artifact.serialize_canonical(artifact)` SHALL emit canonical bytes: UTF-8, object keys
sorted lexicographically at every level, separators `,` and `:` with no whitespace, non-ASCII
characters preserved rather than escaped, and deterministic array order — source first-occurrence for
WTG edges and component lists, sorted for the activity sets and the OPTIONSMENU records. Running the
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

### Requirement: Corpus Equivalence Gate for the Parser Cutover

Before the jar's full-JSON parser is deleted, a one-shot equivalence gate SHALL demonstrate over the
pinned corpus (`<workspace>/rvsec-dataset/static_analysis/`, 345 `.apk.json`) that the projections
served by the old parser on the full JSON and by the new parser on the derived artifact are identical:
widget flag maps including per-event entries and aggregates, widget metadata, both activity sets,
OPTIONSMENU gateway sets under both flag states, WTG views, component and provider trigger tuples,
per-activity deep-link URIs including their absent cases, and `package`/`mainActivity`.

The gate's oracle SHALL be the old parser reading the **raw** full JSON, not the enriched copy the
deleted compaction step used to push. The enrichment is a behaviour this change retires (see the
REMOVED requirement below), so comparing against it would prove the distortion rather than the
relocation.

The gate SHALL additionally report how many corpus apps exercise each relocated rule and SHALL fail
when any count is zero. The pinned corpus is known to exercise all four: 19 apps carry flagged
widgets dropped for an empty short id, 10 apps carry recoverable D8 synthetic-lambda handlers, 165
apps carry DIALOG windows, and the A′ union differs from the widget-derived set wherever component or
reachability sources add an activity. The gate is deleted with the old parser once green; what
survives is the per-rule unit suite of this module.

#### Scenario: equivalence over the pinned corpus
- **WHEN** the gate runs over the 345 `.apk.json` of `rvsec-dataset/static_analysis/`
- **THEN** every app SHALL compare equal on every projection listed above
- **AND** any inequality SHALL fail the gate naming the app and the first differing projection

#### Scenario: a rule exercised by no app fails the gate
- **WHEN** the gate reports zero apps exercising D8 synthetic-lambda recovery
- **THEN** the gate SHALL fail
- **AND** the rule's coverage SHALL move to a synthetic fixture in the permanent Python suite, recorded
  as a substitution

---

## MODIFIED Requirements

### Requirement: ApeRVTool Execution Flow (FR18, FR19)

`ApeRVTool.execute_tool_specific_logic(task, app)` SHALL perform the following steps in order:

1. **Extract execution parameters**: Resolve `device_serial` from `task.config.device_id` (default `"emulator-5554"`) and `timeout_seconds` from `task.config.timeout` (default 300).

2. **Push JAR**: Resolve `ape-rv.jar` via `_resolve_jar_path()` and push to `/data/local/tmp/ape-rv.jar` via `_push_file_to_device()`.

3. **Push broadcast catalog**: If `system-broadcast.json` exists in the module directory (`os.path.dirname(__file__)`), push it to `/data/local/tmp/system-broadcast.json`. This catalog provides typed extras for system broadcast intents used by APE-RV's component triggering. If the file is absent, skip (APE-RV degrades gracefully).

4. **Derive and push the MOP artifact** (MOP variants only): When `_tool_config.get("mop_data") == "static_analysis"`, locate `<task.results_dir>/<apk_name>.json` via `_find_static_analysis_file(task)`. **If it is not found, raise `RVToolExecutionError` naming the expected path** — a MOP arm without its static-analysis input is a failed task, never a silently degraded run. If found, obtain the derived artifact via `_derive_mop_artifact(task)` (cache-or-generate; a `DerivationError` is re-raised as `RVToolExecutionError`), push it to `/data/local/tmp/mop-artifact.json`, and set `mop_json_pushed = True`. The full JSON SHALL NOT be pushed under any condition (INV-APV-46).

5. **Push ape.properties**: Generate `ape.properties` from `_tool_config` using `APERV_PROPERTY_MAPPING` to translate Python keys to Java property names. When `mop_json_pushed` is True, include `ape.mopDataPath=/data/local/tmp/mop-artifact.json`. Push to `/data/local/tmp/ape.properties`.

6. **Capture LLM backend provenance** (LLM arms only): query `GET {llm_url}/v1/models` once and record the result in the task output -- see "Per-Run LLM Backend Provenance". A failed query is encoded, never inferred from configuration, and never aborts the run (INV-APV-33).

7. **Build and execute command**: Build the `app_process` command via `_build_main_command()` and execute it, capturing stdout+stderr to `task.result.trace_file` in binary write mode. **Command timeout is `timeout_seconds + 45` seconds** — widened from `+ 15`; see the grace-window rationale below.

8. **Handle timeout**: If `RVCommandTimeoutError` is raised, re-raise as `RVToolTimeoutError` (timeout is the expected exit path for exploration tools). The `RVToolTimeoutError` contract SHALL be stated as `task.config.timeout + 45` seconds wherever it is documented.

9. **Check empty trace**: Call `_check_empty_trace()` and log a warning if the trace file is empty.

**Capture grace window: why 45 s.** The window exists so the agent's teardown can finish writing before the harness kills the capture. The 15 s it replaces is where the losses concentrate: among runs whose teardown completed, the overrun beyond the exploration budget reaches **12,991 ms** with 32 runs stacked against that ceiling and none beyond it — the signature of a hard wall rather than a natural distribution. Runs that lose the dump end inside the model serialization step, before the dump would have run.

This is recorded as a **hypothesis, not a measurement**. The true teardown duration of the runs that were cut is unobservable — that is what censoring means — so the widened window cannot be credited with a predicted recovery rate in advance. It is complementary to, not redundant with, the jar-side reordering (`ape` design D9): the reordering moves the dump ahead of the expensive write, this gives the chain room to finish. The smoke SHALL report the observed teardown durations under the new window so the assumption is checked rather than carried.

The `app_process` invocation SHALL use:
```
adb -s <serial> shell CLASSPATH=/data/local/tmp/ape-rv.jar /system/bin/app_process /system/bin
  com.android.commands.monkey.Monkey -p <package_name>
  --running-minutes <max(1, timeout_seconds // 60)>
  --ape <strategy>
  [-s <seed>]
```

The trailing `-s <seed>` is appended only when a seed is configured. The seed argument itself is owned by change `gh74-aperv-arm-variants` (INV-APV-18), which is implemented in code but whose delta is not yet synced; it is reproduced here so this spec does not freeze the seedless form as the contract.

#### Scenario: Successful APE-RV execution with sata variant
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `strategy="sata"`, timeout=60
- **THEN** `ape-rv.jar` SHALL be pushed to `/data/local/tmp/ape-rv.jar`
- **AND** the adb command SHALL include `--running-minutes 1` and `--ape sata`
- **AND** stdout+stderr SHALL be written to `task.result.trace_file`
- **AND** no static analysis file SHALL be pushed to the device
- **AND** no derivation SHALL be attempted

#### Scenario: sata_mop execution with static analysis JSON present
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `mop_data="static_analysis"`
- **AND** `_find_static_analysis_file(task)` returns a valid path
- **THEN** `_derive_mop_artifact(task)` SHALL return the cached-or-generated `<apk_name>.mop.json`
- **AND** that file SHALL be pushed to `/data/local/tmp/mop-artifact.json`
- **AND** the full JSON SHALL remain byte-identical and SHALL NOT be pushed
- **AND** `ape.properties` SHALL contain `ape.mopDataPath=/data/local/tmp/mop-artifact.json`

#### Scenario: sata_mop execution with static analysis JSON absent
- **WHEN** `execute_tool_specific_logic(task, app)` is called with `mop_data="static_analysis"`
- **AND** no static analysis JSON file is found in `task.results_dir`
- **THEN** `RVToolExecutionError` SHALL be raised naming the expected path
- **AND** the jar SHALL NOT be launched
- **AND** no warn-and-continue path SHALL exist

#### Scenario: sata_mop execution when derivation fails
- **WHEN** the full JSON exists but `derive()` raises `DerivationError`
- **THEN** `RVToolExecutionError` SHALL be raised carrying the derivation error
- **AND** no artifact SHALL be pushed and the jar SHALL NOT be launched

#### Scenario: Broadcast catalog pushed when present
- **WHEN** `system-broadcast.json` exists in the module directory
- **THEN** it SHALL be pushed to `/data/local/tmp/system-broadcast.json`
- **AND** APE-RV SHALL use it for component triggering with typed extras

#### Scenario: Broadcast catalog absent
- **WHEN** `system-broadcast.json` does not exist in the module directory
- **THEN** no broadcast catalog SHALL be pushed
- **AND** execution SHALL continue normally (APE-RV component triggering degrades gracefully)

#### Scenario: Execution timeout
- **WHEN** APE-RV runs for longer than `timeout_seconds + 45` seconds
- **THEN** `RVToolTimeoutError` SHALL be raised and logged
- **AND** the timeout SHALL be re-raised to the caller

#### Scenario: Non-zero exit code from APE-RV
- **WHEN** APE-RV exits with a non-zero exit code (e.g., 211)
- **THEN** execution SHALL NOT raise an error
- **AND** a debug log SHALL be emitted noting the exit code is normal when app crashes are detected

#### Scenario: Empty trace file
- **WHEN** APE-RV execution completes but writes nothing to stdout
- **THEN** a warning log line SHALL contain `"aperv produced empty trace file"`

#### Scenario: Timeout budget includes the widened grace window
- **WHEN** a task is dispatched with an exploration timeout of `T` seconds
- **THEN** the `adb` command SHALL be given `T + 45` seconds before termination
- **AND** `RVToolTimeoutError` SHALL be raised only after `T + 45` seconds, not `T + 15`

#### Scenario: Smoke reports what the window actually cost
- **WHEN** the integration smoke completes
- **THEN** the observed teardown overrun SHALL be reported per run
- **AND** a run whose overrun still reaches the new ceiling SHALL be flagged as evidence the hypothesis was insufficient

#### Scenario: Provenance query does not delay the run
- **WHEN** the `/v1/models` query at step 6 fails or times out
- **THEN** the flow SHALL proceed to step 7
- **AND** the provenance fields SHALL record the failure (INV-APV-33)

---

### Requirement: ape.properties Generation

`ApeRVTool._push_properties()` SHALL generate an `ape.properties` file from `_tool_config` using
`APERV_PROPERTY_MAPPING` and push it to `/data/local/tmp/ape.properties` on the device. Only keys present
in both `_tool_config` and `APERV_PROPERTY_MAPPING` are written; Python-only keys (`strategy`, `mop_data`,
`seed`) have no mapping entry and are excluded automatically.

`APERV_PROPERTY_MAPPING` SHALL contain an entry for every arm-defining key (INV-APV-13), so that a flag set
in a variant dictionary actually reaches the device. The mapping translates Python config keys to Java
property names:

| Python Key | Java Property | Category |
|------------|--------------|----------|
| `throttle_ms` | `ape.defaultGUIThrottle` | Exploration |
| `default_epsilon` | `ape.defaultEpsilon` | Exploration |
| `graph_stable_restart_threshold` | `ape.graphStableRestartThreshold` | Exploration |
| `state_stable_restart_threshold` | `ape.stateStableRestartThreshold` | Exploration |
| `fuzzing_rate` | `ape.fuzzingRate` | Exploration |
| `do_fuzzing` | `ape.doFuzzing` | Exploration |
| `throttle_for_activity_transition` | `ape.throttleForActivityTransition` | Exploration |
| `max_extra_priority_aliased_actions` | `ape.maxExtraPriorityAliasedActions` | Exploration |
| `max_states_per_activity` | `ape.maxStatesPerActivity` | Exploration |
| `trivial_activity_rank_threshold` | `ape.trivialActivityRankThreshold` | Exploration |
| `do_back_to_trivial_activity` | `ape.doBackToTrivialActivity` | Exploration |
| `back_menu_pick_cap` | `ape.backMenuPickCap` | RV exploration (arm-defining) |
| `max_idle_timeout_ms` | `ape.maxIdleTimeoutMs` | arm-neutral (global tuning knob) |
| `foreign_activity_guard` | `ape.foreignActivityGuard` | RV exploration (arm-defining) |
| `tree_package_guard` | `ape.treePackageGuard` | RV exploration (arm-defining) |
| `dynamic_epsilon` | `ape.dynamicEpsilon` | RV exploration (arm-defining) |
| `heuristic_input` | `ape.heuristicInput` | RV exploration (arm-defining) |
| `fuzz_input_typed` | `ape.fuzzInputTyped` | RV exploration (arm-defining) |
| `form_completion_enabled` | `ape.formCompletionEnabled` | RV exploration (arm-defining) |
| `step_telemetry_enabled` | `ape.stepTelemetryEnabled` | RV exploration (arm-defining) |
| `model_menu_enabled` | `ape.modelMenuEnabled` | RV exploration (arm-defining) |
| `least_visited_priority_tiebreak` | `ape.leastVisitedPriorityTiebreak` | RV exploration (arm-defining) |
| `tree_enhancements_enabled` | `ape.treeEnhancementsEnabled` | RV exploration (arm-defining) |
| `activity_budget_enabled` | `ape.activityBudgetEnabled` | RV exploration (arm-defining) |
| `mop_weight_direct` | `ape.mopWeightDirect` | MOP |
| `mop_weight_transitive` | `ape.mopWeightTransitive` | MOP |
| `mop_weight_activity` | `ape.mopWeightActivity` | MOP (inert; back-compat) |
| `mop_weight_open_menu` | `ape.mopWeightOpenMenu` | MOP |
| `mop_weight_wtg` | `ape.mopWeightWtg` | MOP |
| `mop_activity_source_components` | `ape.mopActivitySourceComponents` | MOP reach A′ (arm-defining) |
| `mop_frontier_weight` | `ape.mopFrontierWeight` | MOP reach B (arm-defining) |
| `frontier_boost_weight` | `ape.frontierBoostWeight` | Frontier (arm-defining) |
| `activity_trigger_enabled` | `ape.activityTriggerEnabled` | Component triggering / MOP reach E-min (arm-defining) |
| `component_percentage` | `ape.componentPercentage` | Component triggering |
| `mop_target_pick_cap` | `ape.mopTargetPickCap` | MOP |
| `coverage_boost_weight` | `ape.coverageBoostWeight` | Coverage |
| `llm_url` | `ape.llmUrl` | LLM |
| `llm_on_new_state` | `ape.llmOnNewState` | LLM |
| `llm_on_stagnation` | `ape.llmOnStagnation` | LLM |
| `llm_model` | `ape.llmModel` | LLM |
| `llm_temperature` | `ape.llmTemperature` | LLM |
| `llm_top_p` | `ape.llmTopP` | LLM |
| `llm_top_k` | `ape.llmTopK` | LLM |
| `llm_timeout_ms` | `ape.llmTimeoutMs` | LLM |
| `llm_percentage` | `ape.llmPercentage` | LLM |
| `llm_percentage_no_substrate` | `ape.llmPercentageNoSubstrate` | LLM seam F′ (arm-defining) |
| `llm_prompt_variant` | `ape.llmPromptVariant` | LLM |

When `mop_json_pushed` is True, the properties file SHALL also include
`ape.mopDataPath=/data/local/tmp/mop-artifact.json` (hardcoded device path matching the push
destination). An `ape.*` key the jar does not recognize is ignored by the jar's `Config` loader (a
name-mismatch is inert, not an error).

#### Scenario: Arm-defining flags appear in properties for a baseline arm
- **WHEN** `_push_properties()` is called for the `sata` variant
- **THEN** the generated properties file SHALL contain `ape.frontierBoostWeight=0`
- **AND** it SHALL contain `ape.activityTriggerEnabled=false`
- **AND** it SHALL contain `ape.dynamicEpsilon=true`
- **AND** it SHALL NOT contain `ape.mopDataPath`

#### Scenario: No kill-switch property is written for ape_pure
- **WHEN** `_push_properties()` is called for the `ape_pure` variant
- **THEN** the generated properties file SHALL NOT contain `ape.apePureMode`
- **AND** it SHALL contain `ape.frontierBoostWeight=0` and `ape.activityTriggerEnabled=false`

#### Scenario: No campaign arm writes the retired kill-switch property
- **WHEN** `_push_properties()` is called for `sata_mop_widget` with `mop_json_pushed=True`
- **THEN** the generated properties file SHALL NOT contain `ape.apePureMode`
- **AND** it SHALL contain `ape.mopActivitySourceComponents=false`
- **AND** the run SHALL reach step 1 — a retired key would abort the jar at bootstrap, zeroing the arm's coverage and MOP violations

#### Scenario: Reach-package flags appear in properties for sata_mop_act_frontier
- **WHEN** `_push_properties()` is called for `sata_mop_act_frontier` with `mop_json_pushed=True`
- **THEN** the properties file SHALL contain `ape.mopActivitySourceComponents=true`
- **AND** it SHALL contain `ape.mopFrontierWeight=200` and `ape.activityTriggerEnabled=true`
- **AND** it SHALL contain `ape.mopDataPath=/data/local/tmp/mop-artifact.json`
- **AND** it SHALL NOT contain `ape.triggerMopFirst` (property removed)

#### Scenario: Python-only keys are still excluded
- **WHEN** `_push_properties()` is called for a variant whose `_tool_config` contains `strategy`, `mop_data`, and `seed`
- **THEN** the properties file SHALL NOT contain `strategy`, `mop_data`, or `seed`

---

## REMOVED Requirements

### Requirement: Static Analysis JSON Compaction (FR19, FR04, NFR04)

**Reason**: The requirement exists to make an oversized full JSON fit through the jar's parse-footprint
guard, and both the oversized input and the guard cease to exist. The device now receives the derived
projection, which excludes the call-graph section that dominated the bytes, so `_compact_static_analysis_json`,
its `_index_reaches_target`/`_enrich_listener_reach` helpers, the temporary-file dance and the
fallback-to-source push are deleted entirely — no shim, no size threshold, no reduced form retained
(P3). INV-APV-20 through INV-APV-25 and INV-APV-31 are retired with the mechanism they constrain.

**INV-APV-32 is retired as a behaviour change, not as dead weight, and this is the one deletion here
that alters what the jar computes.** The enrichment wrote
`handlerReachesTarget = handlerDirectlyReachesTarget = reachesTarget(handler)` onto every listener,
which made the jar take its producer-precedence branch on every widget. Two consequences followed:
`directMop` stopped meaning "the handler invokes a monitored operation in its own body" and became a
synonym of the any-depth bit, so every flagged widget scored at `ape.mopWeightDirect`; and the D8
synthetic-lambda recovery, which lives only in the branch the enrichment bypassed, never ran in
production. The generator restores the producer's two axes (INV-DRV-01) and applies the recovery to
both. Measured over the pinned 345-app corpus: flagged widgets rise from 3,733 to 4,965 (the D8
recovery reaching 10 apps, 1,232 widgets), and every widget that was flagged under the enrichment
moves from the direct tier to the transitive tier uniformly — the ordering *among* MOP widgets is
unchanged, the magnitude of the MOP signal relative to other weights is not. The `direct` tier becomes
non-empty exactly when an app has a handler that calls a monitored operation in its own body; no app
in this corpus does, which is a fact about these 345 apps and not a property the rule may assume.

The full JSON's role as the untouched host-side source of truth (the substance of INV-APV-20) is
preserved and restated by the `analysis` delta of this change, so no invariant coverage is lost by
this removal.
