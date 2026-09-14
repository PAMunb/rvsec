## Context

GitHub Issue: #113. See `proposal.md` for the motivation and `specs/aperv/spec.md` for the requirement deltas.

This change is small in code and narrow in blast radius, and the design document exists for one reason: the guard being removed was installed deliberately, with a stated rationale, and removing it is only defensible once that rationale is confronted with what the rest of the system already does. The `derive()` docstring justifies the refusal as making "a truncated analysis fail loudly instead of degrading a run into a silently thin substrate". The two halves of that sentence must be separated. Failing loudly on a truncated file is right, and stays. Refusing a *complete* file that merely lacks a WTG is not the same thing, and is what this change stops doing.

Three findings from the `smkjca` session establish the ground the design stands on.

**The producer's two-pass write.** `RvsecAnalysisClient.run()` (module `rvsec-gator`) emits the JSON twice. The first pass writes `components`, `reachability`, `windows` and `transitions: []` with `emitSentinel=false`; `JsonReportWriter` describes that state as an intermediate report which "is valid JSON, but does not claim the analysis finished". Only if `WTGBuilder.build()` returns does a second pass rewrite the file and close it with `"complete": true` after `fsync`. `INV-ANA-20` already requires `windows[]` to be populated in both passes — the first-pass document is designed to be useful.

**Structural integrity is guarded elsewhere.** `JsonReportWriter` opens its output with `new FileOutputStream(outputPath)` and no append flag, which truncates the file to zero on open. A process killed during the second pass therefore leaves a syntactically invalid file, never a parseable mixture of new head and stale tail. `_derive_mop_artifact()` calls `json.loads` on the bytes before `derive()` sees them, so that case is already rejected with `RVToolExecutionError`. The sentinel adds nothing to structural integrity that `json.loads` does not already provide.

**WTG absence is already handled by the final consumer.** On the device, `MopData.hasWtgData()` is `!wtgTransitions.isEmpty()`, and it is the gate on `WtgPass`, `FrontierPass` and `MopFrontierPass`. `MopWidgetPass` and `MenuGatewayPass` gate on `mopData != null` alone; `CoveragePass` and `FormCompletionPass` do not consult `MopData` at all; the activity-trigger launcher reads `mopActivities`. An empty `wtg` therefore disables three of seven scoring passes, locally and by design.

Measured impact on the `jca_android` corpus (164 APKs): 45 documents carry no sentinel, all of them with non-empty `reachability` and `windows` and empty `transitions` — the `complete == true` partition coincides exactly with `transitions > 0`. Of those 45, 18 carry MOP substrate usable without a WTG (16 with flagged widgets, 18 with `mopActivities`). The remaining 27 arm both arms with equivalent configurations, which is a measurable outcome rather than a failed task.

Requirements touched: FR14, FR19, FR21, NFR03.

## Architecture

```
 rvsec-gator (Java, NOT modified)
   RvsecAnalysisClient.run()
     pass 1 ─ components + reachability + windows + transitions:[]   (no sentinel)
     WTGBuilder.build()
     pass 2 ─ same sections, transitions populated, + "complete": true + fsync
                     │
                     ▼  <results_dir>/<apk>.json
 ┌───────────────────────────────────────────────────────────────┐
 │ aperv-tool (Python, MODIFIED)                                  │
 │                                                                │
 │  ApeRVTool._derive_mop_artifact(task)      tool.py:690         │
 │    json.loads(raw) ──► rejects malformed bytes (unchanged)     │
 │    derive(document) ──► derive_mop_artifact.py:204             │
 │        ✗ REMOVED: refuse when "complete" is not True           │
 │        ✓ KEPT:    refuse non-object / missing package /        │
 │                   section of the wrong type                    │
 │    serialize_canonical() ──► atomic temp+rename (unchanged)    │
 └───────────────────────────────────────────────────────────────┘
                     │  <apk>.mop.json  (wtg may be {})
                     ▼  adb push
 ┌───────────────────────────────────────────────────────────────┐
 │ ape-rv.jar (Java, NOT modified)                                │
 │   MopData.hasWtgData() == !wtgTransitions.isEmpty()            │
 │     ├── false ─► WtgPass / FrontierPass / MopFrontierPass OFF  │
 │     └── either ─► MopWidgetPass, MenuGatewayPass,              │
 │                   CoveragePass, FormCompletionPass,            │
 │                   ACTIVITY_TRIGGER unaffected                  │
 └───────────────────────────────────────────────────────────────┘
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `derive_mop_artifact.derive` | Project the full JSON into the explorer-shaped artifact. Loses one precondition. | `document: dict` | `artifact: dict` |
| `ApeRVTool._derive_mop_artifact` | Read bytes, digest, cache, write atomically. **Unchanged.** | `task: Task` | artifact path `str` |
| `MopData.hasWtgData` (jar, unchanged) | Decide whether the WTG-dependent passes run | `wtgTransitions` | `bool` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-DRV-08: `derive()` never branches on `complete` | Deletion of the refusal at `derive_mop_artifact.py:249` | `test_derive_accepts_document_without_sentinel`, `test_derive_accepts_false_sentinel` |
| Projection Contents — absent sentinel does not stop derivation | `derive()` step 1 (structural checks only) | `test_derive_accepts_document_without_sentinel` |
| Projection Contents — false sentinel does not stop derivation | idem | `test_derive_accepts_false_sentinel` |
| Projection Contents — missing package still refuses | `derive()` `package` check, unchanged | existing `test_derive_requires_package` |
| Projection Contents — malformed section still refuses | `derive()` `_require_section`, unchanged | existing malformed-section tests |
| Generation and Caching — failed derivation leaves no artifact | `_derive_mop_artifact()` `finally` unlink, unchanged | `test_failed_derivation_leaves_no_file` (trigger changed) |
| Generation and Caching — WTG-less document arms both arms | `_derive_mop_artifact()` + `derive()` | `test_mop_arm_arms_on_wtgless_document` |
| Device-Only Consumer (`analysis`) — WTG-less analysis still yields an artifact | `derive()` with the refusal gone | `test_derive_accepts_document_without_sentinel`, `test_mop_arm_arms_on_wtgless_document` |
| Device-Only Consumer (`analysis`) — unparseable analysis output still yields no artifact | `_derive_mop_artifact()` `json.loads`, unchanged | existing `test_unparseable_source_raises` |

## Goals / Non-Goals

**Goals:**

- Stop refusing a structurally sound static-analysis document because its WTG stage did not finish.
- Keep every other refusal exactly as it is, so that a genuinely unusable document still fails loudly.
- Express WTG absence where the consumer already looks for it — an empty `wtg` and `stats["wtgEdges"] == 0` — instead of as a task failure.
- Preserve what the two repurposed tests actually verify: a failed derivation writes nothing, and a MOP arm whose derivation fails pushes nothing and never launches the jar.

**Non-Goals:**

- Any change to `ape-rv.jar` or to any Java scoring pass. The device-side handling of an empty WTG is already correct and is the reason this change is safe.
- Any change to `rvsec-gator`, `JsonReportWriter` or the sentinel's producer-side meaning (`INV-ANA-31`). The sentinel keeps being written exactly when it is written today. The `analysis` capability spec is nonetheless edited, because it is where the withdrawn consumer-side precondition was written down — a spec edit with no code behind it.
- Any attempt to fix the `WTGBuilder` stalls that produce the sentinel-less documents in the first place. That is a separate defect with its own evidence (44 of 45 killed by timeout, 40 of them at or before stage 2, 23 already at 3600–5400 s budgets) and its own eventual issue. The two repairs are independent: this one recovers usable data now, that one would recover WTG navigation later.
- Any new provenance field, CSV column or gate. The archived `<apk>.json` already answers, per identity, whether the run had a WTG.
- Any change to `StaticAnalysisParser`, which already reads `complete` as a propagated flag rather than a refusal.

## Decisions

**D1 — Delete the check rather than replace it with a narrower one.**

The alternative considered was keeping a guard that distinguishes "intermediate report" from "interrupted write", for instance by requiring `reachability` and `windows` to be non-empty when the sentinel is absent. It was rejected on two grounds. First, it is unreachable in practice: the interrupted-write case cannot produce a parseable document, because the producer truncates on open, so `json.loads` fails before `derive()` runs. A guard that can never fire is code with no behaviour, which P1 forbids. Second, a non-empty check would be a different assertion wearing the sentinel's clothes — an empty `reachability` on a *sentinel-carrying* document is equally suspect, and nothing today refuses it. Structural checks belong to the sections, and `derive()` already has them.

**D2 — Do not record WTG absence anywhere new.**

The alternative was a flag on the task record or a column in the consolidated CSVs, so that a reader could tell WTG-navigated runs from WTG-less ones. It was rejected because the information already exists twice over: `stats["wtgEdges"]` inside the derived artifact, which is what the device itself reads, and the `transitions` section of the full `<apk>.json`, which `StaticAnalysisComponent` copies next to each identity's results. Adding a third representation would create a synchronization obligation with no new information (P1).

**D3 — Repurpose the two `test_aperv_tool.py` tests instead of deleting them.**

Those tests use `complete: False` only as a convenient way to make `derive()` raise. What they assert — no artifact and no temp file survive a failed derivation; a MOP arm with a failed derivation pushes nothing and never launches the jar — remains true and remains worth pinning. Switching the trigger to a section of the wrong type keeps the assertions and drops the dependency on the removed behaviour. Deleting them would lose coverage that this change does not affect.

**D4 — State the new behaviour as an invariant (INV-DRV-08) rather than only as scenarios.**

The temptation to re-add a sentinel check will recur, because the refusal reads as defensive. An invariant that says `derive()` SHALL NOT branch on `complete` names the prohibition directly, so a future reader meets the decision rather than rediscovering the argument.

## API Design

### `derive(document: dict, source_file: str = "", source_digest: str = "") -> dict`

Signature unchanged. Only the precondition set narrows.

**Preconditions (after this change):**
- `document` is a `dict`
- `document["package"]` is a non-empty `str`
- every section present in `document` is of its expected type

`document["complete"]` is not read.

**Postconditions:**
- Returns a `formatVersion: 1` artifact with all `STAT_FIELDS` counters present.
- When `document["transitions"]` is empty or contains no `click` events, `artifact["wtg"] == {}` and `artifact["stats"]["wtgEdges"] == 0`.
- `mopActivities`, `optionsMenus` and `widgets` are derived from `reachability` and `windows` identically whether or not the sentinel is present — those sections do not depend on the WTG.
- Byte-level determinism (`INV-DRV-05`) is unaffected: two documents differing only in the presence of `complete` now derive to byte-identical artifacts.

**Errors:**
- `DerivationError` — non-object document, missing/empty `package`, section of the wrong type. Never for a missing sentinel.

### `ApeRVTool._derive_mop_artifact(task: Task) -> str`

Unchanged in signature, body and error contract. It continues to catch `DerivationError`, `OSError`, `json.JSONDecodeError` and `MemoryError` and re-raise `RVToolExecutionError`, and continues to unlink any temporary file on every error path.

## Data Flow

1. `StaticAnalysisComponent` copies `<apk>.json` from the corpus into `<results_dir>/<apk_name>.json`. Unchanged.
2. `_derive_mop_artifact()` reads the bytes, computes the SHA-256, and returns the cached `<apk_name>.mop.json` when its `source.digest` matches. Unchanged.
3. On a cache miss, `json.loads(raw)` parses the bytes — the point at which a genuinely interrupted write is rejected.
4. `derive(document)` projects. **The only behavioural change is here**: a document without the sentinel proceeds instead of raising. `transitions: []` flows through `_build_wtg()` to an empty `wtg` and `wtgEdges == 0`.
5. `serialize_canonical()` encodes; the artifact is written temp-then-renamed and pushed to `DEVICE_ARTIFACT_PATH`. Unchanged.
6. On the device, `MopData.load` populates `wtgTransitions` as empty, `hasWtgData()` returns `false`, and the three WTG-dependent scoring passes report `isEnabled() == false`. Unchanged, and the reason step 4 is safe.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `json.JSONDecodeError` | Interrupted producer write leaves invalid bytes | Caught in `_derive_mop_artifact`, re-raised as `RVToolExecutionError` | Re-run the static analysis for that APK |
| `DerivationError` (missing `package`) | Document has no package name | Raised by `derive()`, re-raised as `RVToolExecutionError` | Re-run the static analysis for that APK |
| `DerivationError` (section of the wrong type) | Producer emitted a malformed section | Raised by `derive()`, re-raised as `RVToolExecutionError` | Inspect the JSON; re-run the analysis |
| Absent `"complete"` sentinel | WTG stage did not finish | **No error.** Artifact derived with `wtg == {}` | None needed; the jar disables the WTG passes |
| `OSError` on write | Filesystem failure during artifact write | Caught; temp file unlinked; `RVToolExecutionError` | Retry the task |

## Risks / Trade-offs

**[A run over a WTG-less artifact could be read as a full-substrate run]** → The artifact records `stats["wtgEdges"] == 0` and the archived `<apk>.json` records `transitions: []`, both per identity. Any analysis that needs the distinction can partition on either without new plumbing. The risk is one of reader discipline, not of missing data — and refusing the run does not make readers more careful, it only removes the measurement.

**[Arm contrast may be empty on some newly admitted APKs]** → Of the 45 documents recovered, 27 carry no flagged widget and no `mopActivities`, so `mop_on_llm_off` and `mop_off_llm_off` become equivalent configurations there. This is not a regression introduced by the change: those APKs produce no contrast today either, they simply produce a failed task instead of a measured null. A measured null is the better artifact.

**[The removed guard could be re-added by a future reader who reads the docstring's old rationale]** → INV-DRV-08 states the prohibition and this document records the argument. The docstring is updated in the same commit so no stale promise survives (P4).

**[The underlying `WTGBuilder` stall stays unfixed]** → Explicitly out of scope (see Non-Goals). This change makes its consequences cheaper, not invisible: 45 APKs stop failing, and the ones without substrate remain visibly without substrate.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (`test_derive_mop_artifact.py`) | Absent sentinel derives; false sentinel derives byte-identically; empty `transitions` yields `wtg == {}` and `wtgEdges == 0`; missing `package` and malformed sections still refuse | Pure `derive()` calls on in-memory documents, no I/O | ~4 changed/added |
| Unit (`test_aperv_tool.py`) | Failed derivation leaves no file; MOP arm with failed derivation pushes nothing and never launches the jar — both with the trigger switched to a malformed section | `tmp_path` fixtures with a stubbed device | 2 changed |
| Integration (`test_aperv_tool.py`) | Both `aperv` arms arm on a document with `transitions: []` and no sentinel, and the pushed artifact carries `wtg == {}` | Existing arm-execution harness with a WTG-less source document | 1 added |

CI contract: `pytest --import-mode=importlib -o "addopts="` from the module directory.

## Open Questions

None blocking. One item is deferred by decision rather than unresolved: the `WTGBuilder` stall that produces sentinel-less documents (44 of 45 killed by timeout, 40 at or before stage 2, 23 already at 3600–5400 s) needs its own issue and its own investigation, and nothing in this change depends on its outcome.
