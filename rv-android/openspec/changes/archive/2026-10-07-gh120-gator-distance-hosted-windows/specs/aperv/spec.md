## Purpose

The derive (`modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`) turns the full `.apk.json` into the per-widget flags APE-RV reads on the device. One of its rules exists only to cover a producer gap: a D8 synthetic-lambda wrapper (`X$$ExternalSyntheticLambdaN`) registered as a listener had no call-graph edge to the `lambda$…` body it forwards to, so the producer listed it with `reachesTarget: false` even when the body reached a monitored operation. The derive compensated by recovering every wrapper that missed its reaching-only index from the OR of all reaching `lambda$…` methods of the enclosing class.

That recovery is right on average and wrong per wrapper. In E6 it preserved 601 widgets whose wrapper really leads to a target, and flagged 130 (about 5 % of the 2,681 flagged widgets) whose own body reaches nothing but whose class holds a sibling lambda that does. With the producer now linking each wrapper to its own body (`analysis`, INV-ANA-77), a listed wrapper's flags are its own. The derive therefore consults the class recovery only for wrappers the producer does not list at all, which is what INV-DRV-01 already states ("no exact `reachability[].methods[].signature` match"); the code had used a reaching-only index, so a listed non-reaching wrapper also missed and was recovered.

Fragment and hosted windows (`FRAGMENT`, `HOSTED`, named `Host#Owner`) need no derive change: `_base_activity` already folds any `#` suffix into the host's bucket, and only `DIALOG` windows are re-keyed.

## Data Contracts

### Input
- `reachability[].methods[].{signature, reachesTarget, directlyReachesTarget}` — from the full `.apk.json`; wrappers now carry their own flags (source: GATOR, `analysis` INV-ANA-77)
- `windows[]` of types `ACTIVITY`, `DIALOG`, `OPTIONSMENU`, `FRAGMENT`, `HOSTED` (source: GATOR)

### Output
- `*.mop.json` widget flags — unchanged shape; a listed wrapper whose own flags are false is now `none` instead of inheriting a sibling's flag (destination: APE-RV `MopData`)

### Side-Effects
- None beyond the existing cache write.

### Error
- No new error.

## Invariants

- **INV-DRV-09**: The derive's exact-join index SHALL hold every signature listed in `reachability[].methods[]`, reaching or not; the D8 class recovery SHALL apply only to a wrapper whose signature is absent from that index.

## MODIFIED Requirements

### Requirement: Widget MOP Flag Derivation (FR04, FR06)

The generator SHALL derive each widget's MOP flags from its listeners, per normalized `eventType`,
and OR-aggregate them across listeners (INV-DRV-01). For each listener:

1. When `handlerDirectlyReachesTarget` or `handlerReachesTarget` is non-null, the producer's values
   win: `direct` is `handlerDirectlyReachesTarget is True`, `transitive` is
   `handlerReachesTarget is True or direct`.
2. Otherwise the handler signature is looked up in the index built from `reachability[].methods[]`,
   which SHALL carry, per signature and for **every** listed method, reaching or not, the pair
   (`directlyReachesTarget`, `reachesTarget or directlyReachesTarget`). Duplicate signatures SHALL be
   merged by OR rather than by last-write, so the index does not depend on producer ordering.
3. Only when the signature is absent from `reachability[]` and the handler matches
   `^<(.+?)\$\$ExternalSyntheticLambda\d+:`, the flags SHALL be recovered from the enclosing class's
   reaching `lambda$…` methods, OR-aggregated; when that class has no reaching lambda method the
   widget SHALL NOT be flagged. A wrapper listed in `reachability[]` with both flags `false` SHALL
   keep `(false, false)`: the producer links each wrapper to its own body (`analysis`, INV-ANA-77),
   so a listed wrapper's flags are its own, and recovering it from the class would lend it the flags
   of a sibling lambda. The recovery remains for wrappers the producer does not list at all.

The two axes SHALL NOT be collapsed. `direct` retains the producer's 0-hop meaning — the handler
invokes a monitored operation in its own body — which is what `ape.mopWeightDirect` was defined to
reward, and `transitive` is the any-depth reach implied by it. A listener whose `eventType` is null
contributes to the aggregates and normally produces no wire key, since a null key is unaddressable
by the query side. It has one exception, and the exception is what keeps the projection lossless:
because the jar recomputes a widget's aggregate as the OR over the `mop` map, a widget whose *only*
flagged listeners are null-keyed would lose the flag entirely. In that case, and only that case, the
generator SHALL emit the reserved key `""` — the same key `normalizeEventType("")` produces, so it is
reachable only by a query for the empty event type and shadows no real one.

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

#### Scenario: a null event type folds into the aggregate
- **WHEN** a widget's only flagged listener carries `eventType: null`
- **THEN** the wire map SHALL carry `{"": "transitive"}`, so the jar's OR-over-the-map recompute of
  the aggregate still sees the flag
- **AND** the widget's base activity SHALL be in `mopActivities`

#### Scenario: a null event type adds no key when another event is flagged
- **WHEN** the same widget also carries a flagged `click` listener
- **THEN** the wire map SHALL carry `{"click": "transitive"}` and no `""` key, because the aggregate
  is already recoverable from the keyed entry

#### Scenario: per-event flags are independent
- **WHEN** a widget has a `click` listener reaching a monitored operation and a `long_click` listener
  reaching nothing
- **THEN** the wire map SHALL carry `{"click": "transitive", "longclick": "none"}`
- **AND** the `none` entry SHALL be emitted explicitly, because key presence is what suppresses the
  aggregate fallback on the query side

#### Scenario: a listed wrapper keeps its own flags
- **WHEN** a widget's click listener has handler
  `<com.example.MainActivity$$ExternalSyntheticLambda1: void onClick(android.view.View)>`, listed in
  `reachability` with `reachesTarget: false` and `directlyReachesTarget: false`
- **AND** `com.example.MainActivity` has `lambda$onCreate$0` with `reachesTarget: true`, the body of a
  different wrapper
- **THEN** the widget's `click` entry SHALL be `none`
- **AND** `stats.recovered` SHALL NOT count it

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
   emission filter of item 3, so they remain the numbers the jar's load record reported.

Derivation preconditions: the document is an object, carries a non-null `package`, and every section
it does carry is of the expected type; otherwise `DerivationError`. The producer's `"complete": true`
sentinel is NOT a precondition (INV-DRV-08). A document written by the producer's first pass — valid
JSON with populated `reachability` and `windows` per INV-ANA-20, and an empty `transitions` array —
SHALL yield an artifact whose `wtg` is empty, which the device reads through `MopData.hasWtgData()`
to disable the WTG-dependent scoring passes on its own. Structural corruption from a write interrupted
mid-pass is caught earlier, by `json.loads` in `_derive_mop_artifact()`, because the producer truncates
its output file on open and cannot leave a parseable stale tail.

#### Scenario: cryptoapp derivation matches the known ground truth
- **WHEN** `derive()` runs on the test fixture `cryptoapp.apk.json`, the gh60 producer output for
  `br.unb.cic.cryptoapp` with one field as the gh120 producer emits it: the Execute button's wrapper
  `CryptographyActivity$$ExternalSyntheticLambda0.onClick` carries `reachesTarget: true`
- **THEN** `mopActivities` SHALL equal
  `{MessageDigestActivity, CipherActivity, CryptographyActivity}` (base names).
  `CryptographyActivity` enters through the exact join: the producer links the wrapper to its own
  `lambda$setupExecuteButton$0` body (`analysis` INV-ANA-77), so the wrapper is listed reaching and
  the class recovery is not consulted (INV-DRV-09)
- **AND** `optionsMenus` SHALL contain the `MainActivity` record, and `wtg` SHALL carry the click
  edges from `MainActivity` to both MOP sub-activities
- **AND** `components.activities` SHALL have 4 entries and `components.providers` 1 entry with
  `authorities == "br.unb.cic.cryptoapp.androidx-startup"`, every component `reachesMop == false`
- **AND** `stats.windows` SHALL be 5, `stats.flagged` 3 and `stats.recovered` 0

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
- **THEN** the only key matching `*Target*` anywhere in it SHALL be `hasTargetMethods`
- **AND** it SHALL contain no `reachability`, `windows`, `transitions` or `listeners` section
  (INV-DRV-06)
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

---
