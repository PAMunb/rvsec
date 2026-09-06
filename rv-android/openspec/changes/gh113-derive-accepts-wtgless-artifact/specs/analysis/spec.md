## Purpose

This delta withdraws one precondition that the `analysis` capability records on behalf of a downstream consumer. The static-analysis chain writes `<results_dir>/<apk_name>.json` and closes it with a `"complete": true` sentinel; `aperv-tool` projects that file into the compact `<apk_name>.mop.json` the explorer reads on the device. The requirement below stated that the sentinel is a precondition of that projection — that a document without it SHALL NOT yield an artifact, and that the MOP arm SHALL fail loudly instead of running without MOP guidance.

That statement is withdrawn here, and the same withdrawal is made on the consumer side in the `aperv` delta of this change. It is recorded in both places because the rule is written in both places: the producer capability documents what its output guarantees to a consumer, and the consumer capability documents what it refuses. Leaving either one behind would archive a spec that contradicts the other and contradicts the code.

The reason is that the sentinel does not mean what the precondition assumed. `RvsecAnalysisClient` writes the JSON in two passes. The first pass emits `components`, `reachability`, `windows` and an empty `transitions` array with `emitSentinel=false` — `JsonReportWriter` describes that state as an intermediate report which "is valid JSON, but does not claim the analysis finished". Only when `WTGBuilder.build()` returns does a second pass rewrite the whole file and close it with the sentinel after `fsync`. `INV-ANA-20` already requires `windows[]` to be populated in either pass, precisely so the first-pass document stays useful. A missing sentinel therefore means the WTG stage did not finish, not that the file is truncated.

Structural integrity is unaffected by the withdrawal, because it was never the sentinel that provided it. `JsonReportWriter` opens its output with `new FileOutputStream(outputPath)` and no append flag, which truncates the file on open, so a process killed during the second pass leaves syntactically invalid JSON — a case `json.loads` in `_derive_mop_artifact()` rejects before `derive()` is reached. There is no scenario in which a stale tail survives and still parses. What replaces the refusal is the consumer's own handling of an empty WTG: the derived artifact carries `wtg == {}` and `stats["wtgEdges"] == 0`, and the jar's `MopData.hasWtgData()` disables the three WTG-dependent scoring passes on its own.

The sentinel keeps its producer-side meaning without change. `INV-ANA-31` still requires a successful run to end with `"complete": true` and a truncated one not to carry it; `StaticAnalysisData.complete` still propagates it; the gates that require completeness still filter on it. Nothing in the producer is modified by this change. What changes is that `aperv-tool` stops being one of the consumers that require it.

## MODIFIED Requirements

### Requirement: Derived MOP Artifact as a Device-Only Consumer (FR04, FR05, FR06)

The static-analysis chain SHALL gain exactly one new downstream consumer: the host-side derivation in
`aperv-tool` that projects the full JSON into `<results_dir>/<apk_name>.mop.json`. The derivation
SHALL read the full JSON and SHALL NOT modify it. The artifact SHALL be device input only — pushed by
`aperv-tool`, parsed by the jar, and read by nothing else.

The `"complete": true` sentinel SHALL NOT be a precondition of derivation. A document written by the
producer's first pass — valid JSON with populated `reachability` and `windows` per `INV-ANA-20`, and an
empty `transitions` array — SHALL yield an artifact whose `wtg` is empty and whose
`stats["wtgEdges"]` is `0`, which is how WTG absence reaches the device (`INV-DRV-08` in the `aperv`
capability). The sentinel keeps its producer-side meaning unchanged (`INV-ANA-31`) and remains
available to the consumers that do require completeness; the derivation is no longer one of them. A
genuinely interrupted write is still refused, one step earlier: the producer truncates its output file
on open, so a killed second pass leaves unparseable bytes that fail in `json.loads` before `derive()`
runs.

#### Scenario: derivation leaves the producer output untouched
- **WHEN** `aperv-tool` derives an artifact for `com.example_1.apk`
- **THEN** `<results_dir>/com.example_1.apk.json` SHALL be byte-identical to its content before the
  derivation
- **AND** `<results_dir>/com.example_1.apk.mop.json` SHALL exist alongside it

#### Scenario: WTG-less analysis still yields an artifact
- **WHEN** the full JSON lacks the `"complete": true` sentinel because `WTGBuilder` did not finish, and
  it carries populated `reachability` and `windows` with `transitions: []`
- **THEN** a `*.mop.json` SHALL be produced for that app
- **AND** it SHALL carry `wtg == {}` and `stats["wtgEdges"] == 0`
- **AND** the MOP arm for that app SHALL run, with the jar disabling its WTG-dependent scoring passes
  through `MopData.hasWtgData()`

#### Scenario: unparseable analysis output still yields no artifact
- **WHEN** the full JSON is syntactically invalid because the producer was killed during its second
  write pass, which truncated the file on open
- **THEN** no `*.mop.json` SHALL be produced for that app
- **AND** the failure SHALL be raised by `json.loads` in `_derive_mop_artifact()` as
  `RVToolExecutionError`, before `derive()` is reached

#### Scenario: producer is unaware of the derivation
- **WHEN** static analysis runs for an app
- **THEN** its output SHALL be identical whether or not an artifact is later derived from it
- **AND** no producer code path SHALL read, write or test for a `*.mop.json` (INV-ANA-54)
