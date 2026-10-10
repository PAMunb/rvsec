## Purpose

On a cache miss `ApeRVTool._derive_mop_artifact` parsed the full static-analysis document with `json.load` and handed the dict to `derive()`. gh122 measured the peak at 3.1 times the file size (6.28 GB for the 2.02 GB `at.techbee.jtx_216000015` document), which projects to about 29 GB for `eu.darken.sdmse_10705000` (9.34 GB) — three times a campaign container. Almost all of it is `reachability[].methods[].targetDistances`, one `[i, d]` list per method per target within ten calls.

`derive()` uses those pairs in exactly two ways, and both only after merging by the minimum per target: a widget or handler list keeps every pair at `d ≤ DIST_WEIGHED_MAX` (3), and an activity list keeps the `DIST_K` (3) nearest (INV-DRV-10). A pair of one method that is neither within three calls nor among that method's three nearest targets can therefore never appear in the artifact: if it were in an activity's three nearest after the merge, the three targets that beat it inside its own method would beat it in the merge too. This delta reads the document in streaming and keeps, per method, only those pairs, then calls `derive()` unchanged. The artifact is byte-identical to today's; only the memory and the read path change.

## Data Contracts

### Input
- `<results_dir>/<apk_name>.json` — the full document, any size (source: `StaticAnalysisComponent` copy)

### Output
- `<results_dir>/<apk_name>.mop.json` — unchanged contents and format (`formatVersion: 2`) (destination: device, APE-RV `MopData`)

### Side-Effects
- None new.

### Error
- `RVToolExecutionError` — unchanged cases; an unparseable or truncated document now fails in the streaming read instead of in `json.load`.

## Invariants

- **INV-APV-64**: On a cache miss `_derive_mop_artifact` SHALL read the document in streaming and SHALL keep, of each method's `targetDistances`, after taking the minimum per target, only the pairs at `d ≤ DIST_WEIGHED_MAX` and the `DIST_K` nearest by `(d, i)`. The serialized artifact SHALL be byte-identical to `serialize_canonical(derive(json.load(document)))` of the same file.

## MODIFIED Requirements

### Requirement: Derived MOP Artifact Generation and Caching (FR19, NFR04)

`ApeRVTool._derive_mop_artifact(task)` SHALL return the host path of the compact MOP artifact for the
task's APK, generating it when needed:

1. Compute the SHA-256 of the current full JSON at `<results_dir>/<apk_name>.json`, reading the file
   in chunks.
2. When `<results_dir>/<apk_name>.mop.json` exists, its `source.digest` equals `"sha256:" + <hex>`
   **and** its `formatVersion` equals `derive_mop_artifact.FORMAT_VERSION`, reuse it without
   regenerating and without parsing the full JSON.
3. Otherwise read the full JSON in streaming as UTF-8, reducing each method's `targetDistances` to the
   pairs the artifact can carry (INV-APV-64), call `derive()` + `serialize_canonical()` on the result,
   and write the artifact atomically (write-temp-then-rename in the same directory). A failed
   derivation SHALL write nothing.

The method SHALL NOT hold the file's text, nor any `targetDistances` pair that cannot reach the
artifact. A gh120 document is large — up to 9.34 GB in the Study 03 corpus — and a whole-document
parse peaked at 3.1 times the file size (gh122 task 7.7). The digest and the streaming read each read
the file on their own, and a cache hit never parses.

The reduction is exact, not an approximation. `derive()` merges distances by the minimum per target
and cuts only at emission: every pair at `d ≤ DIST_WEIGHED_MAX` for a widget or handler, the
`DIST_K` nearest by `(d, i)` for an activity (INV-DRV-10). A pair dropped by the reduction is beyond
`DIST_WEIGHED_MAX` and has at least `DIST_K` targets ahead of it in its own method; after any merge
those targets are still ahead of it, so it can be in no emitted list.

The artifact is cached next to its source so it is inspectable and diffable, and it is a pure function
of the full JSON and the generator's format (INV-APV-47, INV-DRV-05). The format is part of the cache
key because the digest alone names the input, not the derivation: after a format bump a cached
artifact of the old format matches its source's digest and would be pushed to a jar that rejects it,
and every MOP arm would abort (`ape` INV-MOP-34). This method replaces `_compact_static_analysis_json`,
which is deleted together with its fallback-to-source push: there is no longer any condition under
which the full JSON reaches the device (INV-APV-46).

Derivation failure means the document is structurally unusable, not that the analysis stopped early.
An unreadable, non-UTF-8, unparseable or truncated file fails here, in the streaming read, before
`derive()` is reached; a well-formed document that lacks the WTG stage does not fail at all
(INV-DRV-08).

#### Scenario: cache hit skips derivation
- **WHEN** `<results_dir>/com.example_1.apk.mop.json` exists carrying
  `source.digest == "sha256:ab12…"` and the SHA-256 of `com.example_1.apk.json` is `ab12…`
- **THEN** `_derive_mop_artifact(task)` SHALL return that path
- **AND** `derive()` SHALL NOT be called
- **AND** the full JSON SHALL NOT be parsed

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

#### Scenario: the streaming derivation is byte-identical to the whole-document one
- **WHEN** the artifact of `cryptoapp.apk.json`, and of each of `org.wikipedia_50595`,
  `at.techbee.jtx_216000015` and three smaller Study 03 documents, is derived once by streaming and
  once by `derive(json.load(...))`
- **THEN** the two serialized artifacts SHALL be byte-identical for every document

#### Scenario: the largest corpus document derives inside a campaign container
- **WHEN** `_derive_mop_artifact` derives `eu.darken.sdmse_10705000.apk.json` (9.34 GB) on a cache miss
- **THEN** the process's peak resident memory SHALL stay below 3 GiB
- **AND** the artifact SHALL be written
