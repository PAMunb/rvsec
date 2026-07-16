# Design: Compact Static Analysis JSON Before Device Push

## Context

See `proposal.md` (GitHub Issue: #80). The MOP-guided `aperv` arms push `<results_dir>/<apk_name>.json` to the device byte-for-byte at `tool.py:773-793`. The Java side rejects any file above roughly 32 MB before parsing (`MopData.java:202`, `PARSE_FOOTPRINT_FACTOR = 6` at `MopData.java:160`, ~192 MB heap). On `org.quantumbadger.redreader_117` the 50.6 MB JSON is rejected and both MOP arms explore for 0 steps while the baselines run normally — a per-app fairness gap measured in the `cmpma` campaign.

Constraints that shape the design:

- **The source file is an archived artifact.** It is re-parsed by offline consolidation and by `ResultProcessorComponent._resolve_static_data` on resume. `StaticAnalysisComponent.load_static_data()` also parses it for the per-method coverage denominator, but that denominator is insensitive to this transform (measured: identical 1,796 classes / 9,333 methods before and after). Preserving the file is about provenance and blast radius, not about protecting a computation.
- **The Java guard is correct and stays.** Aborting rather than exploring without MOP data (rather than mislabelling the arm) is the desired behavior. This change removes the trigger, not the guard.
- **The `ape` repository is read-only here.** Deduplication safety depends on its six `getWtgTransitions`/`wtgTransitions` consumers, but none of them is modified.

Relevant requirements: FR19 (External Tool Support), FR04 (GATOR/WTG), NFR04 (Resilience), NFR08 (Reproducibility).

## Architecture

The change is contained in one module. It inserts a transform between two existing calls in `execute_tool_specific_logic()` at the block the code labels `# Step 1c` (`tool.py:773`), which the spec's normative flow numbers as step 4 — the two labels denote the same block, and adds no new class, no new dependency, and no new public interface.

```
rv-experiment pre-processing
        │  writes <results_dir>/<apk_name>.json  (GATOR/GESDA/REACH)
        ▼
  ┌─────────────────────────────────────────────┐
  │  <results_dir>/<apk_name>.json  (source)    │──────┐
  └─────────────────────────────────────────────┘      │ read-only,
        │ _find_static_analysis_file()                  │ unchanged
        ▼                                               ▼
  ┌──────────────────────────┐          ┌──────────────────────────────────┐
  │ _compact_static_analysis │          │ rv-platform                      │
  │  dedup transitions       │          │ StaticAnalysisComponent          │
  │  + minify → tmp file     │          │  .load_static_data()             │
  └──────────────────────────┘          │  → per-method coverage denominator│
        │ tmp path (or source, on fail) └──────────────────────────────────┘
        ▼
  _push_file_to_device()
        │
        ▼
  /data/local/tmp/static_analysis.json
        │
        ▼
  MopData.java:202  footprint guard (~32 MB)  →  parse  →  MOP arms explore
```

The two arrows out of the source file are the whole point of the design: the left branch is compacted, the right branch is untouched.

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ApeRVTool._find_static_analysis_file` | Locate the source JSON (unchanged) | `Task` | `str \| None` |
| `ApeRVTool._compact_static_analysis_json` | Dedup `transitions` + minify into a temp file | `str` (source path) | `str \| None` (temp path; `None` on failure) |
| `ApeRVTool.execute_tool_specific_logic` Step 1c | Choose push path, push, unlink temp | `Task`, `App` | side-effect: device file |
| `ApeRVTool._push_file_to_device` | adb push (unchanged) | local path, device path | side-effect |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Static Analysis JSON Compaction | `_compact_static_analysis_json()` + Step 1c in `tool.py` | `test_compaction_*` |
| ApeRVTool Execution Flow (MODIFIED) | Step 1c ordering in `execute_tool_specific_logic()` | `test_execute_pushes_compacted_json` |
| INV-APV-20 (source byte-identical) | Compaction writes only to `tempfile.NamedTemporaryFile` | `test_inv_apv_20_source_unmodified` |
| INV-APV-21 (lossless), no projection | Mutate only `d["transitions"]`; `json.dump` the same dict | `test_inv_apv_21_all_top_level_keys_survive` |
| INV-APV-21 (lossless), minification | `separators=(",", ":")` | `test_inv_apv_21_no_pretty_print_whitespace` |
| INV-APV-22 (first-occurrence order) | Ordered accumulation against a `seen` set | `test_inv_apv_22_dedup_preserves_order` |
| INV-APV-23 (unconditional) | No size check on the call path | `test_inv_apv_23_small_json_also_compacted` |
| INV-APV-24 (fallback on failure) | `try/except` returning `None` → caller pushes source | `test_inv_apv_24_malformed_json_falls_back` |
| INV-APV-25 (no temp leak), success path | `finally: if compacted: os.unlink(compacted)` in Step 1c | `test_inv_apv_25_no_temp_leak_success` |
| INV-APV-25 (no temp leak), fallback path | `except` in `_compact_static_analysis_json` unlinks before returning `None` | `test_inv_apv_25_no_temp_leak_fallback` |

## Goals / Non-Goals

**Goals:**

- Bring `redreader`'s device-side JSON under the Java footprint ceiling so the MOP arms explore, closing the per-app fairness gap.
- Shrink every static analysis JSON, lowering device-side heap pressure across the campaign.
- Keep the source JSON byte-identical to the producer's output, preserving it as an archived artifact.
- Fail soft: never turn a compaction problem into a task failure.

**Non-Goals:**

- Fixing the producer (`jca_dexlib2`), which emits the duplicate edges and the pretty-printing. That is the root cause and the right long-term fix, but it requires re-running static analysis across 219 APKs.
- Changing, relaxing, or removing the Java-side footprint guard.
- Field projection (dropping unread sections).
- Anything from the `cmpma` critique's §8 (a launcher-only ablation arm, `--logcat-diagnostics`, dwell-preconditioned `cov_act`). This change does not affect those conclusions either way: it alters which file reaches the device on one app, not how any arm scores.

## Decisions

**D1 — Compact to a temporary file, not in place.**
Alternative considered: compact during `StaticAnalysisComponent.copy_static_analysis_files()`, so the file landing in `results_dir` is already compact and both consumers read it.

It is worth being precise about why this was rejected, because the obvious argument for rejecting it is wrong. The obvious argument is that the file feeds the per-method coverage parser for every arm and every tool, so rewriting it would move the coverage denominator. It would not. The denominator is derived from `reachability`; `transitions` does not contribute to it, and minification is semantically neutral. Measured directly: parsing `org.quantumbadger.redreader_117.apk.json` before and after compaction yields an identical 1,796 classes / 9,333 methods. The parser does materialize `transitions` (130,996 → 64,704 expanded edges), but their only Python consumers live in `rv-agent` (`services/transition_manager.py`, `ui/rvagent_visitor.py`, `strategies/rvagent_strategy/ranking/scorers.py`), which is deprecated and never runs in an `aperv` arm. In-place compaction would, in fact, be semantically invisible to everything in this repository.

The real reasons are narrower and weaker. Compaction is a concern of the device-push path; `copy_static_analysis_files()` runs for every tool, including `monkey` and `ape`, which never push this file — putting it there spends blast radius for nothing (P1). And the source file is an archived experiment artifact: offline consolidation and `_resolve_static_data` on resume re-parse it, so keeping it byte-identical to the producer's output preserves it as ground truth rather than a derived artifact, which matters for provenance in a thesis campaign. Cost: one temp file per MOP task, unlinked immediately.

**D2 — Compact unconditionally, no size threshold.**
Alternative considered: only compact above ~16 MB. Rejected on three grounds. It creates two code paths where the interesting one runs on ~1 app in 181 and is effectively untested in production. It duplicates `PARSE_FOOTPRINT_FACTOR` as a second constant on the Python side, to be kept in sync with a value that lives in another repository. And it forfeits the heap-pressure reduction on the other 180 APKs, which is a real benefit given the 8 OOM events observed across 8 concurrent emulators. The measured cost on the largest JSON in the dataset (`redreader`, 50.6 MB) is ~0.5s end to end — 0.3s `json.load`, 0.1s dedup, 0.1s `json.dumps` — against exploration runs of 60–300s.

**D3 — Fall back to pushing the source on any failure.**
Alternatives considered: (a) fail the task, (b) fall back with a dedicated grep-able marker in the trace. (a) rejected: it converts a compaction problem into an ERROR in one arm only, manufacturing exactly the between-arm asymmetry this change exists to remove. (b) rejected as not worth its own mechanism: the warning already carries the source path into the log and is greppable there, so a separate trace marker buys a stable token and little else. Accepted consequence: if the source is oversized and compaction fails, the guard rejects it and the MOP arm runs 0 steps — the fairness gap returns, visible as a log warning. If that failure mode is ever observed in practice, promoting the warning to a classifiable marker is a cheap follow-up.

**D4 — Dedup by whole-entry canonical equality, not by an explicit key tuple.**
Verified against the data: `transitions` entries carry exactly `sourceId`, `targetId`, `events`, so `json.dumps(entry, sort_keys=True)` is identical to the `(sourceId, targetId, events)` tuple today, and stays correct if the producer adds a field later — an explicit tuple key would silently start collapsing distinct entries. Measured: 24,300 → 7,124 unique on `redreader`.

**D5 — Preserve first-occurrence order.**
`rekeyDialogsToHost` (`MopData.java:884`) takes the first inbound edge and breaks. Edge multiplicity is not a signal for any consumer, but edge *order* is load-bearing for that one. Ordered accumulation costs nothing and removes the question.

**D6 — No field projection.**
Alternative considered: drop sections the tool does not read. Rejected: unnecessary (21 MB already clears the ceiling), and it invites silent schema-drift — a future Java `Pass` that starts reading a projected-away field goes inert with no error.

## API Design

### `_compact_static_analysis_json(self, source_path: str) -> str | None`

Compacts the static analysis JSON into a new temporary file.

- **Preconditions**: `source_path` is an existing, readable file path (guaranteed by `_find_static_analysis_file`).
- **Postconditions on success**: returns the path to a temp file, on the same filesystem semantics as `_push_properties`' temp (`tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)`), containing the same document with `transitions` deduplicated (first-occurrence order) and serialized with `separators=(",", ":")`. `source_path` is unmodified.
- **Postconditions on failure**: returns `None`. Any temp file it created is removed before returning. `source_path` is unmodified. No exception propagates.
- **Errors**: catches `json.JSONDecodeError`, `OSError`, `MemoryError`, logs a warning naming the source path and the cause. Returns `None` rather than raising (INV-APV-24) — the caller treats `None` as "push the source".

No Pydantic model is introduced. The document is an opaque `dict` from `json.load`: modelling it would require a schema for every section the tool does not read, which is the schema-drift risk D6 rejects.

### Step 1c call shape

The caller selects the push path and owns temp lifetime, mirroring the existing `_push_properties` idiom (`tool.py:622-634`, `NamedTemporaryFile(delete=False)` + `unlink` in a `finally`):

```
static_json = self._find_static_analysis_file(task)
if static_json:
    compacted = self._compact_static_analysis_json(static_json)
    push_path = compacted or static_json
    try:
        self._push_file_to_device(push_path, "/data/local/tmp/static_analysis.json", ...)
        mop_json_pushed = True
    finally:
        if compacted:
            os.unlink(compacted)
else:
    <existing warning, unchanged>
```

`mop_json_pushed` is set on both the compacted and the fallback path, so `ape.mopDataPath` is emitted identically — the fallback is invisible to `ape.properties`.

## Data Flow

1. rv-experiment pre-processing writes `<apks_dir>/<apk_name>.json` (GATOR/GESDA/REACH).
2. `StaticAnalysisComponent.copy_static_analysis_files()` copies it to `<results_dir>/` (unchanged by this design).
3. **Branch A (coverage, unchanged)**: `load_static_data()` parses `<results_dir>/<apk_name>.json` → per-method coverage denominator.
4. **Branch B (device, changed)**: `_find_static_analysis_file()` → `_compact_static_analysis_json()` → temp file → `_push_file_to_device()` → `/data/local/tmp/static_analysis.json` → temp unlinked.
5. Device side: `MopData.java:202` footprint guard → parse → `MopScorer` / `FrontierPass` / `MopFrontierPass` / `rekeyDialogsToHost` consume `transitions`.

Branches A and B read the same bytes from step 2; only B transforms them, into a file A never sees.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `json.JSONDecodeError` | Malformed source JSON | Catch, warn, return `None` | Caller pushes the source unchanged |
| `OSError` | Temp file write / disk full / unlink | Catch, warn, return `None` | Caller pushes the source unchanged |
| `MemoryError` | `json.load` of a very large document on the host | Catch, warn, return `None` | Caller pushes the source unchanged; guard then rejects it device-side (fairness gap returns, per D3) |
| `RVToolExecutionError` | `_push_file_to_device` (existing) | Unchanged — propagates | Unchanged |

No new error class (INV-APV-24). The `@ErrorHandler.handle_errors` decorator on `execute_tool_specific_logic` is unaffected: compaction never reaches it.

## Risks / Trade-offs

- **[Dedup safety depends on a read-only sibling repo]** → Certified against all six `getWtgTransitions`/`wtgTransitions` consumers in `ape` (`MopScorer.java:115`, `FrontierPass.java:55`, `StatefulAgent.java:1066`, `MopFrontierPass.java:56,97,109`, `MopData.java:884`, `MopData.java:1000`): all are set-membership or first-match-fixed-weight, hence idempotent to duplicates. `FrontierPass` and `MopFrontierPass` are distinct classes — an earlier draft of this design folded the former into `StatefulAgent.frontierBoost` and undercounted them as five. Order-sensitivity is handled by D5. A future change to any of those consumers that begins treating multiplicity as a signal would invalidate this — recorded in the spec Purpose so the assumption is discoverable.
- **[Telemetry `[APE-MOP-DATA] transitions=N` changes meaning]** (`MopData.java:319`) → Reports the unique count (7,124 vs 24,300 on `redreader`). Arguably more correct, but it breaks direct comparison of that field across campaigns (NFR08). Mitigation: document in the next campaign's report; do not compare that field pre/post.
- **[Silent fallback hides a returning fairness gap]** (accepted, D3) → A compaction failure on an oversized JSON reverts to the §6 behavior with only a warning to show for it. Mitigation available if it bites: promote the warning to a classifiable marker.
- **[Host-side memory during `json.load`]** → Loading a 50 MB JSON costs a few hundred MB in the host Python process, not the emulator. With 8 concurrent containers this is host RAM, not device heap. Measured at ~0.5s end to end for the largest file in the dataset (0.3s of which is `json.load`); if a future dataset ships a much larger JSON, `MemoryError` is caught and degrades per D3.
- **[Per-task recompaction]** → The same JSON is recompacted for each task on the same APK (~0.5s worst case on `redreader`, well under 0.1s typical). Caching across tasks was considered and rejected as premature (P1): the cost is noise against a 60–300s run, and a cache adds invalidation state.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | Dedup semantics (order, exact-equality), minification, key survival, no-`transitions`, empty-`transitions`, malformed → `None`, source unmodified, temp cleanup on both paths | `tmp_path` fixtures with small synthetic JSONs; no device, no adb | ~10 tests |
| Unit (flow) | Step 1c pushes the compacted path; falls back to source on `None`; `mop_json_pushed` set on both paths; no compaction when `mop_data` is unset | Mock `_push_file_to_device`, assert the path argument | ~4 tests |
| Integration (manual, one-off) | `redreader` compacts to ~21 MB and the MOP arm explores > 0 steps | Single-APK `rv-experiment run` with `aperv:sata_mop_act_frontier`; assert trace has > 0 `[APE-STEP]` and `[APE-MOP-DATA] status=loaded` | 1 run |

CI contract per CLAUDE.md: `pytest --import-mode=importlib -o "addopts="`.

The `redreader` integration check is the only claim that cannot be settled offline — it is the one that requires the Java guard to actually accept the file. Everything else is deterministic on synthetic fixtures.

## Open Questions

None blocking. One deferred: whether to fix the producer (`jca_dexlib2`) so it stops emitting 70% duplicate edges and pretty-printing. That would make this compaction step redundant for future datasets, but not for existing ones, and it requires re-running static analysis across 219 APKs. Out of scope here; worth its own issue.
