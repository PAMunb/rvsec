## Context

The proposal (#123) records the failure: gh120 documents of 2–9 GB are read whole by every reader at run time, and the `StaticAnalysisParser` read alone OOM-kills a 10 GiB campaign container in the first task of the plain `ape` arm (`docs/20261009_e03mini-smoke.md`). The readers on the run path are three:

| Reader | When | How today | Peak |
|---|---|---|---|
| `StaticAnalysisParser.parse_file` via `read_static_analysis_files` (`modules/rv-static-analysis/src/rv_static_analysis/parser/static/static_analysis_parser.py:221-337`) | every task (`StaticAnalysisComponent.load_static_data`, `modules/rv-platform/src/rv_platform/components/static_analysis.py:120-137`) and once per APK in `ResultProcessorComponent._resolve_static_data` (`modules/rv-platform/src/rv_platform/components/result_processor.py:401-429`) | `f.read()` + `json.loads` | > 7 GiB on the 2.16 GB wikipedia document (killed) |
| `ApeRVTool._derive_mop_artifact` (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py:759-868`) | MOP arms, on a cache miss of `<apk>.mop.json` | `json.load` from a text handle | 3.1 × file (gh122 7.7): ~29 GB for sdmse |
| `copy_static_analysis_files` (`static_analysis.py:170-245`) | every task | `shutil.copy` of the whole file | 100 s for sdmse's 9.34 GB |

What the readers keep is small. Coverage uses seven fields per method, `componentType`/`isMain` per class and `codePackage` (`modules/rv-android-core/src/rv_android_core/util/android/repository_initializer.py:52-71`); `rv-agent` and `rv-screen-parser` use windows, widgets and transitions. None reads `targetDistances`, and the parser discards it after `json.loads` built it. The derive reads `targetDistances` but merges by the per-target minimum and cuts at emission (`derive_mop_artifact.py:29-38`, `_cut_weighed`, `_cut_nearest`, `DIST_WEIGHED_MAX = 3`, `DIST_K = 3`).

Measured on the host for this design: `ijson` with the `yajl2_c` backend walks `eu.faircode.email_2322.apk.json` (137 MB) at 84 MB/s as a Python loop over events and at 161 MB/s through the C `items` builder; the per-APK statistics of `data/e03mini_static/` read all 163 documents (23 GB) with four `items` passes each in 5 minutes on 10 workers with 156 MB of resident memory.

FR04/FR12 (static data for coverage), FR19 (derive), NFR02 (graceful degradation), NFR04 (resources).

## Architecture

```
apks_dir/<apk>.json ──copy2, skip if same size+mtime──▶ results/<apk>/<apk>.json
                                                         │
               ┌─────────────────────────────────────────┼──────────────────────────────┐
               ▼                                         ▼                              ▼
read_static_analysis_files                    _derive_mop_artifact (aperv)     ResultProcessor
  digest(source) ─ match? ─▶ json.load(<apk>.static.json)   digest ─ match? ─▶ <apk>.mop.json
        │ no                                      │ no
        ▼                                         ▼
  read_analysis_document(drop pairs)        read_analysis_document(reduce pairs)
        │ dict without distances                  │ dict with reduced pairs
        ├──▶ write <apk>.static.json (if not truncated)   derive() → serialize_canonical()
        ▼
  section parsers ──▶ StaticAnalysisData
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `rv_android_core.util.analysis_document.read_analysis_document` (new) | One event pass over the document; builds every member except the ones the caller drops; reduces or drops `targetDistances`; reports truncation | path, `PairPolicy` | `(dict, truncated: bool)` |
| `rv_android_core.util.analysis_document.digest_of_file` (moved from `aperv_tool/tools/aperv/derive_mop_artifact.py`) | Chunked SHA-256 | path | `"sha256:<hex>"` |
| `StaticAnalysisParser._load_json` / `_recover_truncated_json` | Call the reader with `PairPolicy.DROP`; map truncation to INV-ANA-81 | path | dict |
| `StaticAnalysisParser.read_static_analysis_files` | Cache lookup and write of `<apk>.static.json` | results dir, apk | `StaticAnalysisData` |
| `ApeRVTool._derive_mop_artifact` | Call the reader with `PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K)`, strict on truncation | task | artifact path |
| `StaticAnalysisComponent.copy_static_analysis_files` | `copy2`, skip identical destination | task | bool |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|---|---|---|
| analysis: Streaming Read of the Analysis Document; INV-ANA-80 | `analysis_document.read_analysis_document`, `StaticAnalysisParser._load_json` | `rv-android-core/tests/util/test_analysis_document.py::test_equals_json_loads_*`; `rv-static-analysis/tests/parser/static/test_static_analysis_parser.py::TestStreamingEquivalence` |
| INV-ANA-81 (truncation) | `read_analysis_document` truncation report; `_recover_truncated_json` | `TestTruncatedJSON` (updated), `test_analysis_document.py::test_truncation_*` |
| analysis: Parsed-Document Cache; INV-ANA-82, -83 | `read_static_analysis_files`, `_write_parsed_copy` | `test_static_analysis_parser.py::TestParsedCopyCache` |
| INV-ANA-84 (copy read only by the parser) | audit test | `rv-static-analysis/tests/test_static_copy_audit.py` |
| analysis: Full JSON Remains the Sole Metric Input (modified) | unchanged callers | `rv-platform/tests/components/test_result_processor.py::test_csv_identical_with_and_without_parsed_copy` |
| analysis: Derived MOP Artifact as a Device-Only Consumer (modified) | `_derive_mop_artifact` strict read | `aperv-tool/tests/test_aperv_tool.py` (truncated document raises `RVToolExecutionError`) |
| platform: copy skipped when identical; INV-PLT-39 | `copy_static_analysis_files` | `rv-platform/tests/components/test_static_analysis.py::TestCopySkip` |
| aperv: Derived MOP Artifact Generation and Caching (modified); INV-APV-64 | `_derive_mop_artifact`, `PairPolicy.reduce` | `aperv-tool/tests/test_derive_mop_artifact.py::test_streaming_byte_identical_*`; corpus check script (below) |
| Peak-memory scenarios (wikipedia parse, sdmse derive) | — | `openspec/changes/gh123-static-json-streaming-cache/measure_peak_rss.py` + `.out.md` |

## Goals / Non-Goals

**Goals:**
- Read any gh120 document inside a 10 GiB campaign container, in every arm.
- Return the same `StaticAnalysisData` and derive the same `.mop.json` bytes as today.
- Read each large document once per APK per container, not once per task.

**Non-Goals:**
- Changing the document GATOR writes (e.g. a sparser `targetDistances`).
- Changing offline host scripts (`consolidate_compare.py`, `gen_compare.py --filter-abi`, `aperv_tool/analysis/static_artifact.py`).
- Changing `StaticAnalysisData` or any consumer of it.
- Sharing one digest computation between the parser cache and the MOP-artifact cache.

## Decisions

**D1 — One event pass, not section passes and not `json.loads`.** The reader iterates `ijson.parse` (backend `yajl2_c`) once and builds values with a small stack builder. Alternatives: (a) one `ijson.items` pass per top-level section — about twice the throughput per pass (161 vs 84 MB/s measured), but at least four passes, top-level scalars need their own scan, and a truncated file raises in every pass with no way to tell which section was complete; (b) `json.loads` — the status quo. One pass gives INV-ANA-81 an exact meaning (a member is complete iff its closing event was seen) and reads a 9.34 GB document in about two minutes, paid once per APK per container thanks to D4.

**D2 — The reader lives in `rv-android-core`.** Both the parser (`rv-static-analysis`) and the derive (`aperv-tool`) need it, and both already depend on `rv-android-core`; `aperv-tool` does not depend on `rv-static-analysis`. Two copies of an event builder would drift on exactly the edge cases (truncation, skipped subtrees) that matter here. `digest_of_file` moves with it, because the parser cache needs the same digest the MOP cache records; `aperv-tool` imports it from core and its own definition is deleted (P3). `ijson` becomes a dependency of `rv-android-core`.

**D3 — Pair policy as a parameter.** `PairPolicy.DROP` skips the events of `targetDistances` and of `distanceTargets` without building anything. `PairPolicy.reduce(weighed_max, k)` folds each method's `targetDistances` events into per-target minima while streaming (no list of pairs is built) and, at the end of the array, emits `[[i, d], …]` holding the pairs at `d ≤ weighed_max` and the `k` nearest by `(d, i)`; `distanceTargets` is built (it is small, and `derive()` reads its length). The reduction is exact for `derive()` (aperv delta, Purpose). The emitted list is ordered by `(d, i)`; `derive()` reads pairs through `_read_pairs`, which is order-insensitive.

**D4 — The parsed copy is the document minus the distance members.** `<apk>.static.json` holds the dict the parser built under `PairPolicy.DROP`, plus `source: {digest, generator: "rv-static-analysis/1"}`, written with `json.dump` (compact separators) to a temporary file in the same directory and renamed. Reading it is `json.load` (it is small: the corpus document without distances) followed by the same section parsers, so equality of the models (INV-ANA-83) holds by construction rather than by a second serializer. Alternative: pickle the `StaticAnalysisData` — rejected: not inspectable, tied to the Pydantic models' layout, and INV-PLT-15's note against serializing the model applies.

**D5 — The cache key is the source digest.** The author chose it (#123), and it matches the `.mop.json` (INV-APV-47): the copy is a pure function of the source. Cost: one chunked SHA-256 per read (the aperv derive already pays one per MOP task); for sdmse that is a disk-speed read of 9.34 GB, usually from the page cache after the first task. Alternative: size + `st_mtime_ns` — cheaper, but a re-analysed document copied with `copy2` from a source of equal size and preserved time would be answered by the old copy.

**D6 — The task copy compares size and `st_mtime_ns`.** It decides only whether to copy, not whether content is current (that is D5's job), and hashing to decide a copy costs as much as the copy (platform delta).

**D7 — Truncation stays tolerant in the parser and strict in the derive.** The parser keeps INV-ANA-06/31 behaviour through `_recover_truncated_json`; the derive raises `RVToolExecutionError` on any truncated or invalid document, as the analysis spec requires (no artifact from an interrupted write).

## API Design

### `rv_android_core.util.analysis_document.read_analysis_document(path: str, pairs: PairPolicy) -> tuple[dict, bool]`

- **Pre:** `path` names a readable file.
- **Post:** returns the root object as a dict whose members are built exactly as `json.loads` would build them, except `distanceTargets` (absent under `DROP`) and every `reachability[].methods[].targetDistances` (absent under `DROP`, reduced under `reduce`), and a flag that is `True` iff the input ended before the root object closed. Under truncation the dict holds only the top-level members whose closing event was read.
- **Errors:** `OSError` from opening; `ValueError` when the file is empty, its first token is not JSON, or its root is not an object (the parser maps this to `None` → empty model; the derive to `RVToolExecutionError`). Bytes that stop being JSON after the root opened are a truncation: `({}, True)`, or the members completed before them; downstream the outcome is the same (empty or partial model, no copy written, the derive refuses).

### `PairPolicy`

```python
@dataclass(frozen=True)
class PairPolicy:
    drop: bool
    weighed_max: int = 0
    k: int = 0

PairPolicy.DROP = PairPolicy(drop=True)
def reduce(weighed_max: int, k: int) -> PairPolicy: ...
```

### `rv_android_core.util.analysis_document.digest_of_file(path: str) -> str`

Moved unchanged from `derive_mop_artifact.py` (chunked SHA-256, `"sha256:<hex>"`).

### `StaticAnalysisParser.read_static_analysis_files(results_dir: str, apk: str) -> StaticAnalysisData`

Signature unchanged. Adds the cache lookup and write of `<results_dir>/<apk><EXTENSION_PARSED_COPY>` (`EXTENSION_PARSED_COPY = ".static.json"` in `rv_android_core.constants`, beside `EXTENSION_STATIC_ANALYSIS`). Never raises (INV-ANA-06).

## Data Flow

1. Task N of APK A: `copy_static_analysis_files` stats source and destination; equal → skip (D6).
2. `load_static_data` → `read_static_analysis_files`: digest the source; copy present with that digest → `json.load` it → section parsers → model. Else stream with `DROP` → write the copy if not truncated → section parsers → model.
3. MOP arms: `_derive_mop_artifact`: digest; `.mop.json` matches → reuse. Else stream with `reduce(3, 3)` → `derive()` → write.
4. End of container: `ResultProcessorComponent` → `read_static_analysis_files` once per APK → hits the copy.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Truncated document | producer killed mid-write | parser: keep complete members, `complete=False`, do not cache; derive: `RVToolExecutionError` | re-run the analysis |
| Unreadable copy (`*.static.json` corrupt or other digest) | interrupted host, re-analysed source | treat as miss, rewrite | automatic |
| Copy write fails | read-only or full disk | log warning, return the model | none needed |
| `ijson` backend not C | wheel missing | reader asserts `ijson.backend == "yajl2_c"` at import and fails loudly | install the wheel; the Docker image build fails early |

## Risks / Trade-offs

- [The event loop is slower than C `items` per byte (84 vs 161 MB/s)] → paid once per APK per container (D4); sdmse ≈ 2 min against a 300 s task budget that does not include it (it runs before the tool starts, in the task's setup).
- [Two SHA-256 per MOP task (parser cache and `.mop.json`)] → disk-speed, page-cached after the first task; sharing them is a non-goal to keep the two caches independent.
- [The reduced pair count for very dense apps] → counted on 2026-10-09 with `ijson.items` over `reachability` (per-target minimum, then `d ≤ 3` ∪ 3 nearest): jtx keeps 395,630 of 30,922,867 pairs (1.3 %), wikipedia 450,621 of 32,828,700 (1.4 %), sdmse 3,848,622 of 143,185,999 (2.7 %; the `items` pass took 153 s). Even sdmse's kept pairs are a few hundred MB as Python lists; task 5.2 measures the real peaks and the scenario thresholds follow the measurement.
- [Equality of the streamed dict with `json.loads` on numeric edge cases] → the builder uses `ijson`'s `use_float=True` so integers stay `int` and non-integers are `float`, as `json.loads` returns; the equivalence tests compare the dicts directly. Where yajl and `json.loads` disagree the reader follows yajl, measured on 2026-10-10: a lone surrogate escape (`"\ud800"`) becomes `?` with no truncation reported, and an integer beyond 64 bits or a number beyond double range ends the read as a truncation. GATOR writes neither; the module docstring states both.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | Reader equals `json.loads` minus dropped members; truncation at every top-level boundary and inside nested arrays; `reduce` keeps `d ≤ 3` ∪ top-k | synthetic documents + fixtures `cryptoapp.apk.json`, `app.notesr_59.apk.json` | ~15 |
| Unit | Parser model equality streaming vs today (fixtures, baselines in `tests/resources/baselines/`) | existing `TestBaselineEquivalence` + new class | ~6 |
| Unit | Cache hit, miss, stale digest, truncated source not cached, unwritable directory | `tmp_path` | ~6 |
| Unit | Copy skip / copy2 / replaced source | `tmp_path` | ~3 |
| Unit | Derive byte identity streaming vs `json.load` on fixtures | `test_derive_mop_artifact.py` | ~3 |
| Corpus check | Byte identity of the derive and model equality of the parser on wikipedia, jtx and 3 small Study 03 documents; peak RSS of parse and derive on wikipedia and sdmse | script in the change folder, run on the host with paths as arguments (corpus files are inputs, not rules) | 1 script |
| Smoke | `e03mini-smoke` re-run, 5 APKs × 4 arms, 10 GiB containers, image rebuilt | `docker/docker-compose.e03mini-smoke.yml` | 20 tasks |

## Open Questions

None blocking. The memory thresholds of the two peak-memory scenarios are confirmed by the measurement task before implementation is closed.
