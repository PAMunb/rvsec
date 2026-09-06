## Purpose

This delta narrows one precondition of the MOP artifact derivation: the presence of the producer's `"complete": true` sentinel stops being a condition for generating an artifact, and becomes an ordinary property of the artifact that is generated.

The sentinel is written by `RvsecAnalysisClient` (module `rvsec-gator`) as the last top-level field of the static-analysis JSON, after an explicit `fsync`. The producer writes that JSON in two passes. The first pass emits `components`, `reachability`, `windows` and an empty `transitions` array, and deliberately omits the sentinel — `JsonReportWriter` documents that state as an intermediate report which "is valid JSON, but does not claim the analysis finished". If the WTG stage completes, a second pass rewrites the whole file and closes it with the sentinel. `INV-ANA-20` already requires `windows[]` to be populated in either pass, precisely so the first-pass document stays useful.

`derive()` treated the absent sentinel as proof of a truncated document and refused to derive anything from it. That reading is too broad, and it is expensive: the refusal propagates as `RVToolExecutionError` and fails the whole task, and it does so on **both** `aperv` arms, because `mop_off_llm_off` declares `mop_data: static_analysis` exactly like `mop_on_llm_off` (INV-APV-30 — the control zeroes weights, it does not remove the document). Measured on the `jca_android` corpus of 164 APKs, 45 documents carry no sentinel; 18 of those hold MOP substrate the explorer can use with no WTG at all. In `experimento-smk111` on 2026-08-31 the same refusal cost 12 identities — 2 APKs × 2 `aperv` arms × 3 repetitions — while the `ape` arm ran normally on the same APKs.

Two facts make the relaxation safe rather than permissive. First, structural integrity is already guaranteed elsewhere: `JsonReportWriter` opens its output with `new FileOutputStream(outputPath)` without append, which truncates the file on open, so a process killed during the second pass leaves syntactically invalid JSON — a case `json.loads` in `_derive_mop_artifact()` already rejects before `derive()` is ever called. There is no scenario in which a stale tail survives and still parses. Second, WTG absence is already handled by the final consumer: on the device, `MopData.hasWtgData()` is `!wtgTransitions.isEmpty()`, and it is what enables or disables `WtgPass`, `FrontierPass` and `MopFrontierPass`. An artifact with an empty `wtg` therefore disables three scoring passes locally, while `MopWidgetPass`, `MenuGatewayPass`, `CoveragePass`, `FormCompletionPass` and the activity-trigger launcher keep operating on the substrate the document does carry.

The refusal was, in effect, a host-side duplicate of a device-side guard, and a coarser one: it killed the run instead of disabling three passes. What `derive()` keeps refusing is unchanged — a non-object document, a missing `package`, a section of the wrong type. Nothing partial is ever returned.

No new field, column or gate accompanies this change. The full `<apk>.json` is already archived beside each identity's results by `StaticAnalysisComponent`, and its `transitions` section answers, per run, whether that run had a WTG.

## Data Contracts

### Input
- `document: dict` — the parsed full static-analysis JSON. `document["complete"]` MAY be `True`, `False` or absent; its value no longer gates derivation.
- `document["transitions"]: list` — MAY be empty. An empty list yields an empty `wtg` map.

### Output
- `artifact["wtg"]: dict` — `baseActivity -> [{widget, target}]`. Empty when the document carries no click transitions, whatever the reason.
- `artifact["stats"]["wtgEdges"]: int` — `0` when no click edge survived derivation. This is the machine-readable record of a WTG-less artifact, read on the device by `MopData.hasWtgData()`.

### Side-Effects
- **[Filesystem]**: unchanged — `_derive_mop_artifact()` writes `<results_dir>/<apk_name>.mop.json` atomically (temp then rename) and leaves nothing behind on failure.

### Error
- `DerivationError` — raised by `derive()` when the document is structurally unusable (not an object, missing `package`, a section of the wrong type). The absence or falsity of `complete` is NOT among the causes. No partial artifact is produced; the caller re-raises it as `RVToolExecutionError`.

## Invariants

- **INV-DRV-08**: `derive()` SHALL NOT read `document["complete"]` for any control-flow decision. A document whose sections are well-typed SHALL yield an artifact regardless of the sentinel's presence, falsity or absence. WTG absence SHALL be expressed as an empty `wtg` map with `stats["wtgEdges"] == 0`, never as a refusal.

## MODIFIED Requirements

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
- **WHEN** `derive()` runs on `cryptoapp.apk.gh60-fresh.json`
- **THEN** `mopActivities` SHALL equal
  `{MessageDigestActivity, CipherActivity, CryptographyActivity}` (base names).
  `CryptographyActivity` enters through the D8 recovery: the exact join drops its
  `CryptographyActivity$$ExternalSyntheticLambda0:onClick` wrapper handler and the reaching
  `lambda$setupExecuteButton$0` body restores it. The jar asserts the same three flagged widgets
  when it parses this fixture raw, which is this change's oracle (design D11)
- **AND** `optionsMenus` SHALL contain the `MainActivity` record, and `wtg` SHALL carry the click
  edges from `MainActivity` to both MOP sub-activities
- **AND** `components.activities` SHALL have 4 entries and `components.providers` 1 entry with
  `authorities == "br.unb.cic.cryptoapp.androidx-startup"`, every component `reachesMop == false`
- **AND** `stats.windows` SHALL be 5, `stats.flagged` 3 and `stats.recovered` 1

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
