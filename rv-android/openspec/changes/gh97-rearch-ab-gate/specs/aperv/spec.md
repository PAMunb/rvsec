# Delta: aperv (gh97-rearch-ab-gate)

## Purpose

This delta gives a run the ability to state, inside its own provenance record, which corpus it was
drawn from. Today nothing on this side can answer that question from the artifacts alone. A run's
results directory names one application; the list that application belonged to lives in a campaign
directory, a compose file's bind-mount, or an operator's memory, and the association is reconstructed
after the fact by whoever analyses the data. The cost of that reconstruction is not hypothetical:
this study has counted its analysis basis as 163, 181 and 219 applications in different documents,
and every analysis that spans campaigns has had to re-derive which list each run belonged to before
it could compare anything.

The jar already has the receiving half. Stage 2 of the APE-RV re-architecture declares `ape.corpusBasis`
a resolver-owned key alongside `ape.preset` and `ape.runId`: it is recognised, supplied by the harness,
echoed into `RUN_START.corpus_basis`, and read by nothing. The `run-spec` capability on the `ape` side
carries a scenario written for the harness pushing it. This repository is the missing half — a sweep of
`modules/aperv-tool/src` confirms nothing writes the key, and no other change claims it. It was kept
out of `gh95` deliberately, because a per-run deployment key is not an arm re-expression, and it lands
here because this is the change that pins a corpus by digest and needs every run traceable to the list
it was drawn from.

The design keeps the two responsibilities apart. The value is a **string the caller supplies**, not a
digest the tool computes: `aperv-tool` does not own the corpus list, does not know where it lives, and
should not grow a filesystem dependency on a campaign's layout in order to hash it. What the tool owns
is the contract — the shape of the value, its validation before anything reaches a device, and the
guarantee that an absent basis produces an absent key rather than a defaulted one. Correctness of the
digest itself is established where the corpus actually lives, by recomputing it from the list file and
comparing against `RUN_START.corpus_basis` during the campaign's pre-flight. That is a check against
the file, not a transcription anyone has to trust.

The key is write-only by construction on both sides. `run-spec` INV-RUN-03 declares `RUN_START`
write-only at level 0 — no runtime component, Java or Python, reads it — and `gh95` decision D1 states
that `tool.py` never parses `RUN_START`. Nothing here weakens either: the tool writes the property and
never reads the echo back. Verification is post-hoc analysis over recorded traces, which is the only
place `RUN_START` is ever consumed.

## Data Contracts

### Input
- `corpus_basis: str` — optional key in `ApeRVTool._tool_config`, supplied through the same
  configuration path as any other mapped key. Format `<corpus-id>:<sha256>`, where `<corpus-id>` is a
  short human-readable identifier of the list (e.g. `subset40`) and `<sha256>` is the lowercase
  hexadecimal SHA-256 of the list file's bytes.

### Output
- `ape.corpusBasis=<corpus-id>:<sha256>` — one line appended to the generated `ape.properties`,
  pushed to `/data/local/tmp/ape.properties`. Consumed by the jar's resolver, echoed into
  `RUN_START.corpus_basis`, and read by no runtime component on either side.

### Side-Effects
- **[Device]**: the pushed `ape.properties` gains one line; no other device state changes.
- **[Trace]**: `RUN_START.corpus_basis` becomes present in every trace of the run.

### Error
- `ConfigurationError` — raised by `configure()` when `corpus_basis` is present but does not match
  `^[A-Za-z0-9._-]+:[0-9a-f]{64}$`. Raised before any device interaction, so a malformed basis costs
  no emulator time and produces no partially-configured run.

## Invariants

- **INV-APV-56**: When `corpus_basis` is absent from the tool configuration, `_push_properties()`
  SHALL omit `ape.corpusBasis` from the generated `ape.properties` entirely. It SHALL NOT emit the key
  with an empty, placeholder or defaulted value — the jar's contract is that the key is absent when
  the corpus is unstated, and a defaulted value would assert a provenance the harness does not have.

- **INV-APV-57**: No component of `modules/aperv-tool` SHALL read `RUN_START` — including
  `corpus_basis` — on any execution path. The property is write-only from this side, mirroring
  `run-spec` INV-RUN-03 and `gh95` decision D1. Any verification of the echoed value SHALL be
  post-hoc analysis over a recorded trace, outside `tool.py`.

## ADDED Requirements

### Requirement: Corpus Basis Provenance (FR18, FR19, NFR06)

`ApeRVTool` SHALL accept an optional `corpus_basis` configuration value identifying the application
list a run was drawn from, and `_push_properties()` SHALL write it to the generated `ape.properties`
as `ape.corpusBasis=<value>` when present. The value SHALL be treated as opaque provenance: the tool
validates its shape and passes it through unchanged, and SHALL NOT derive, complete or normalize it.

Validation SHALL occur in `configure()`, before any device interaction, and SHALL reject any value not
matching `^[A-Za-z0-9._-]+:[0-9a-f]{64}$` with `ConfigurationError` naming the offending value. The
two-part shape is what makes the value useful: the identifier is what a human reads in a report, and
the digest is what makes two runs provably drawn from the same list rather than from two lists that
happen to share a name.

When the value is absent the key SHALL be omitted entirely (INV-APV-56). Absence is a legitimate state
— every campaign before this change ran without it, and every standalone invocation still does — and
it SHALL NOT be treated as an error, a warning, or a reason to synthesize a value.

The tool SHALL NOT read the value back from `RUN_START` or from any other artifact at run time
(INV-APV-57). Confirming that the jar received and echoed what was pushed is the campaign pre-flight's
work, performed by an operator script over a recorded trace.

#### Scenario: A configured corpus basis reaches the device

- **WHEN** `configure()` receives `corpus_basis="subset40:4157faa071fae1b405730de6d3fabf3d6821e54830473e98d2c342bffcadd252"` and `_push_properties()` runs for variant `mop_on_llm_off`
- **THEN** the generated `ape.properties` SHALL contain the line `ape.corpusBasis=subset40:4157faa071fae1b405730de6d3fabf3d6821e54830473e98d2c342bffcadd252`
- **AND** the value SHALL be byte-identical to what was configured, with no re-derivation, truncation or case change
- **AND** the run's `RUN_START` SHALL carry `corpus_basis` with that same value

#### Scenario: An unstated corpus produces no key at all

- **WHEN** `_push_properties()` runs for variant `sata` and `corpus_basis` is absent from `_tool_config`
- **THEN** the generated `ape.properties` SHALL NOT contain any line beginning `ape.corpusBasis`
- **AND** no warning SHALL be logged and no placeholder value SHALL be substituted
- **AND** the run SHALL proceed normally, since a standalone invocation has no corpus to state

#### Scenario: A malformed basis fails before the emulator is touched

- **WHEN** `configure()` receives `corpus_basis="subset40"` — an identifier with no digest
- **THEN** it SHALL raise `ConfigurationError` naming the key and the rejected value
- **AND** the error SHALL be raised before any `adb push`, so no device is started and no partially-configured run exists

#### Scenario: A digest that does not match the list is caught by the pre-flight, not by the tool

- **WHEN** a campaign is configured with `corpus_basis="subset40:<digest>"` where `<digest>` is well-formed but was transcribed from a different list, and the pre-flight recomputes the SHA-256 of `calibracao/subset40.txt`
- **THEN** `ApeRVTool` SHALL have pushed the value unchanged, because shape is all it validates
- **AND** the pre-flight SHALL report the mismatch between the recomputed digest and `RUN_START.corpus_basis` and fail the gate
- **AND** no component of `modules/aperv-tool` SHALL have read `RUN_START` in the process
