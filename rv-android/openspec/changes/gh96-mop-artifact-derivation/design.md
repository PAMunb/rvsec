# Design: gh96-mop-artifact-derivation

## Context

The proposal establishes *why* the MOP substrate's parse-time semantics move host-side. This document
fixes *how*, and records the decisions that the sibling `ape` change (`rearch-07-compact-static-artifact`)
either left open or got wrong.

Current state on this side: `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` locates the full
static-analysis JSON (`_find_static_analysis_file`, `:885`), reshapes it
(`_compact_static_analysis_json`, `:913` — dedup `transitions`, enrich `listeners[]`, minify), pushes
it to `/data/local/tmp/static_analysis.json` (`:1479`), and writes
`ape.mopDataPath=/data/local/tmp/static_analysis.json` (`:1154`). When the JSON is absent it warns and
continues (`:1494`), so a MOP arm runs as pure SATA under a MOP label.

Current state on the jar side, which is what actually defines the semantics being relocated:
`MopData.load` (`ape-rearch/src/main/java/com/android/commands/monkey/ape/utils/MopData.java`) runs
four passes plus a re-keying pass over the full JSON and derives everything the explorer reads. Every
rule this change relocates is a specific block of that file: the reachability index and the D8
recovery (`:343-404`, `:528-555`), the widget map with its collision policy and the activity marking
(`:410-464`), the WTG click view (`:669-722`), the dialog re-keying (`:877-924`), the A′ union
(`:573-600`), the OPTIONSMENU precompute (`:820-857`), and the handler-join diagnostics (`:610-641`).

Three empirical facts, measured over the pinned corpus (`rvsec-dataset/static_analysis/`, 345
`.apk.json`) during the exploration phase, shape the decisions below:

| Measurement | Value | Consequence |
|---|---:|---|
| Listeners carrying producer-supplied `handlerReachesTarget` | 0 / 168,503 | The producer-precedence branch exists only because `tool.py` enriches; it is otherwise unreachable |
| Methods with `directlyReachesTarget == true` | 546, in 109 apps | The 0-hop bit is real data, not a dead field |
| Listener handlers that are one of those methods | 0 / 168,503 | The `direct` tier is empty *in this corpus* — a property of these apps, not of the rule |
| Methods with `directlyReachesTarget && !reachesTarget` | 33, in 16 apps | Without an explicit OR, a widget could be derived `direct` but not `transitive` |
| Duplicate method signatures with conflicting flags | 0 | Merge policy is unconstrained by data; pick the order-independent one |
| Listeners with a null `eventType` | 0 | The per-event map is lossless in practice; the null case still needs a stated rule |
| Apps with flagged widgets dropped for an empty short id | 19 (1,263 widgets) | AC3 is exercised without `labnex`/`duress` |
| Apps with recoverable D8 synthetic-lambda handlers | 10 (9,252 listener occurrences) | The recovery is exercised |
| Apps carrying DIALOG windows | 165 | Re-keying is exercised |

Constraints: P1 (no speculative structure), P3 (delete, no shims), R9 (frozen metric definitions read
the full JSON only), and the cross-repo rule that the wire format is defined jointly and cut once.
FRs: FR04/FR05/FR06 (consumed), FR18/FR19/FR20 (tool execution). NFR02 (completion sentinel), NFR04
(artifact size), NFR06 (observability).

## Architecture

```text
rv-android (host)                                     ape-rv.jar (device)
─────────────────                                     ───────────────────
rv-static-analysis  (untouched)
  └─► <results_dir>/<apk>.json ──┬─► metric / consolidation paths  (R9: unchanged)
                                 │
                                 ▼
        aperv_tool/tools/aperv/derive_mop_artifact.py   (pure, no I/O)
          derive(document) -> dict
          serialize_canonical(dict) -> bytes
                                 │
                                 ▼
        aperv_tool/tools/aperv/tool.py
          _derive_mop_artifact(task)                  MopData.load(path, pkg, mainAct)
            digest check ─► cache hit ──┐               parses formatVersion=1 only
            else derive + atomic write ─┴──► <apk>.mop.json
          execute_tool_specific_logic()
            MOP arm + no full JSON → RVToolExecutionError
            MOP arm + artifact OK  → adb push ────────► /data/local/tmp/mop-artifact.json
            ape.mopDataPath=/data/local/tmp/mop-artifact.json
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `derive_mop_artifact.derive(document)` | Pure projection of the full JSON into the compact artifact; all eight relocated rules; `Target`→`MOP` rename | `dict` | `dict` |
| `derive_mop_artifact.serialize_canonical(artifact)` | Canonical byte encoding (sorted keys, fixed separators, UTF-8) | `dict` | `bytes` |
| `derive_mop_artifact.DerivationError` | Structural refusal — never a partial artifact | — | exception |
| `ApeRVTool._derive_mop_artifact(task)` | Cache-or-generate `<apk>.mop.json`; digest check; atomic write; raise on failure | `Task` | host path `str` |
| `ApeRVTool.execute_tool_specific_logic` step 4 | Locate, derive, push, flag; fail loud on a MOP arm without input | `Task`, `App` | device push + `mop_json_pushed` |
| `ApeRVTool._push_properties` | Writes `ape.mopDataPath` at the new device path | `_tool_config` | `ape.properties` |

Internal structure of `derive_mop_artifact.py` — one function per relocated rule, so each is a named
unit test rather than a branch inside a monolith:

```
_index_reachability(document)      -> (by_signature, lambda_by_class, activity_classes)
_derive_listener_flags(listener, by_signature, lambda_by_class, stats)
_build_widget_map(windows, ...)    -> (widget_map, flagged_activities, options_menus, stats)
_rekey_dialogs(windows, transitions, widget_map, flagged_activities, stats)
_build_wtg(transitions, windows_by_id, stats)
_augment_activities(flagged, components_activities, activity_classes)
_derive_deep_link_uri(intent_filters)
_project_components(components)
```

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|---|---|---|
| Projection contents | `derive()` | `test_derive_cryptoapp_ground_truth`, `test_derive_rejects_incomplete`, `test_no_target_keys_on_wire` |
| INV-DRV-01 (flags, precedence, D8, direct⇒transitive) | `_derive_listener_flags`, `_index_reachability` | `test_producer_precedence_wins`, `test_direct_implies_transitive`, `test_synthetic_lambda_recovered`, `test_synthetic_lambda_not_recovered_without_lambda`, `test_per_event_flags_independent` |
| INV-DRV-02 (collision rank, empty-id drop, activity marking) | `_build_widget_map` | `test_flagged_empty_id_marks_activity`, `test_collision_keeps_strongest_flag`, `test_collision_tie_keeps_first` |
| INV-DRV-03 (dialog re-keying, WTG view) | `_rekey_dialogs`, `_build_wtg` | `test_dialog_merge_promotes_host`, `test_dialog_first_incoming_edge_wins`, `test_orphan_dialog_keeps_key`, `test_dialog_class_retained_in_activity_set`, `test_dialog_merge_uses_mop_rank`, `test_wtg_click_only_deduped_base_keyed` |
| INV-DRV-04 (stats are pure counters) | all `_*` helpers write to one `stats` dict | `test_stats_do_not_affect_sets` |
| INV-DRV-05 (determinism) | `serialize_canonical` | `test_serialize_canonical_is_byte_stable`, `test_key_order_independent_of_input_order` |
| INV-DRV-06 (no `*Target`, no call graph) | `derive()` output shape | `test_no_target_keys_on_wire` |
| INV-DRV-07 (deep link) | `_derive_deep_link_uri` | `test_deep_link_from_first_action_view`, `test_deep_link_absent_without_scheme`, `test_deep_link_absent_without_action_view`, `test_deep_link_absent_without_filters`, `test_deep_link_empty_host_and_path` |
| A′ union (three sources) | `_augment_activities` | `test_augmented_union_three_sources`, `test_augmented_superset_of_widget_derived` |
| OPTIONSMENU records | `_build_widget_map` | `test_options_menu_record_uses_parsed_widgets` |
| INV-APV-45 (arm arms or fails) | `execute_tool_specific_logic` step 4 | `test_mop_arm_without_json_raises`, `test_mop_arm_derivation_error_raises` |
| INV-APV-46 (only the artifact reaches the device) | step 4 + deletion of the fallback push | `test_full_json_never_pushed` |
| INV-APV-47 (digest cache) | `_derive_mop_artifact` | `test_cache_hit_skips_derivation`, `test_stale_cache_regenerates`, `test_failed_derivation_leaves_no_file` |
| Properties line | `_push_properties` | `test_properties_carry_new_mop_data_path` |
| INV-ANA-53 (no pipeline reads `*.mop.json`) | repository audit | `test_no_module_outside_aperv_tool_reads_mop_json` |
| Corpus equivalence gate | one-shot script + JVM side | `scripts/` gate run, deleted after green |

## Goals / Non-Goals

**Goals**

- One authority for the derivation semantics, in pure Python, with one named test per rule.
- The device receives only what the explorer reads; the on-device parse of call-graph data disappears.
- Every skew direction fails loudly before step 1: no artifact, stale artifact, wrong app, wrong
  format.
- The full JSON stays exactly where and what it is, so no metric moves.

**Non-Goals**

- No change to the producer (`rv-static-analysis`, rvsec-gator) or its schema.
- No change to scoring weights, containment policy, eventType normalization on the query side, or
  trigger selection rules.
- No dual-format support, no adapter, no "push the old JSON if the new one fails" (P3).
- No generalization of the artifact beyond what the explorer consumes — no fields "for later".
- No revival of the `mopWeightDirect` tier by redefinition; if the tier is to discriminate, that is a
  producer-side question, out of scope here.

## Decisions

### D1 — The generator lives in `aperv-tool`, runs lazily at execution time, and caches next to the source

Alternatives: (a) generate during pre-processing in `rv-static-analysis`; (b) generate at push time in
`aperv-tool`. Chosen **(b) with caching**. `aperv-tool` already owns locating, shaping and pushing the
JSON, so the blast radius stays at one module — `rv-platform`, `rv-experiment` and `rv-static-analysis`
are untouched. Generating in pre-processing would put a device-input concern in the analysis pipeline
and would produce the artifact for every app of a campaign regardless of whether any MOP arm runs.
The cache lives at `<results_dir>/<apk_name>.mop.json`, next to its source: inspectable, diffable, and
archived with the run.

### D2 — The derivation semantics are specified under `aperv`, not `analysis`

The sibling `ape` change puts them in its `static-analysis-entrypoints` capability. Here the mapping
from capability to module is the organizing rule, and the generator is `aperv-tool` code: a reader
looking for what `derive_mop_artifact.py` guarantees must find it in the `aperv` spec. The `analysis`
delta therefore carries only the chain-level facts — the artifact is a device-only downstream
consumer, and the full JSON remains the sole metric input.

### D3 — `derive` is a pure function in its own module, not a method on `ApeRVTool`

The rules being relocated are the highest-risk part of this change and the part that must be testable
without a `Task`, a device or a filesystem. A module-level `derive(document) -> dict` takes a parsed
dict and returns a dict; `DerivationError` is defined beside it. `tool.py` owns everything impure:
reading, hashing, atomic writing, pushing, raising `RVToolExecutionError`. This also keeps the
generator importable by the corpus gate without constructing a tool.

### D4 — The two MOP axes stay independent; the enrichment's redefinition is retired

This is the decision that departs from a literal reading of both the current production behaviour and
the `ape` change's prose, so it is stated in full.

`_compact_static_analysis_json` writes `handlerReachesTarget = handlerDirectlyReachesTarget =
reachesTarget(handler)` onto every listener (INV-APV-32). Because `MopData.deriveWidgetMopFlags`
prefers producer-supplied values, that makes the producer-precedence branch fire on every widget:
`directMop` becomes a synonym of the any-depth bit, and the D8 recovery in the other branch never
executes. The enrichment was introduced to make `ape.mopWeightDirect` fire at all, since the
producer's 0-hop bit is false for every handler in the measured corpus.

The generator restores the producer's meaning: `direct` is `directlyReachesTarget` of the handler
itself, `transitive` is `reachesTarget or direct`. Rationale, in order:

1. A normative rule may not encode a corpus observation. That no handler among 168,503 is 0-hop is a
   fact about 345 apps; an app whose `onClick` calls `Cipher.getInstance` directly exists, and it is
   exactly the case `mopWeightDirect` was defined to reward. Under the enrichment that app is
   indistinguishable from one that delegates through five frames.
2. Collapsing the axes makes the wire format lie: the `mop` map's four values (`none|direct|transitive|both`)
   would only ever carry two, and the jar-side scenario asserting that the bits are independent would
   be vacuous.
3. The D8 recovery is a genuine call-graph gap affecting every app built with D8 lambda desugaring —
   61,057 wrapper handlers in the corpus fail the exact join. Keeping it masked to preserve the
   enrichment would delete a general fix to protect a corpus-specific one.

Alternatives considered: **preserve the enrichment inside `derive`** (strict behavioural identity with
today's production, at the cost of items 1–3, and of deleting INV-MOP-30 as dead rather than relocating
it); **union of both** (`direct` from the enrichment, `transitive` including the recovery), which keeps
the 500 tier firing but is neither the producer's semantics nor today's behaviour. Both were rejected
on item 1: the rule must be derivable from the producer's contract alone.

Consequence, stated so it is not discovered later: on the pinned corpus every widget currently flagged
moves from the `mopWeightDirect` tier to `mopWeightTransitive`, uniformly — relative ordering among MOP
widgets is unchanged, the MOP signal's magnitude against other weights is not — and the recovery adds
1,232 flagged widgets across 8 apps. Runs before and after this change are not substrate-comparable,
which is a fact about the change, not a defect of it.

Two robustness rules follow, neither of which the current parser has:

- **`direct` implies `transitive`.** `MopData`'s `bySignature` path stores `reachesTarget` unmodified,
  so the 33 methods (16 apps) with `directlyReachesTarget && !reachesTarget` would derive a widget
  that is direct but not transitive — an incoherent state. The producer-precedence branch already ORs;
  the generator applies the OR on every path.
- **Duplicate signatures merge by OR**, not by last-write. Zero conflicts exist in the corpus, so the
  choice is free; OR is the one that does not depend on producer emission order.

### D5 — A listener with a null `eventType` contributes to the aggregates and emits no key

`normalizeEventType(null)` yields `null` in the jar, and the query side skips the per-event lookup for
a null key, so a null-keyed entry is unreadable through `isDirectMop`/`isTransitiveMop` — it survives
only in the aggregate. A JSON object cannot carry a null key, so the generator drops the key and
still folds the listener into the widget's aggregate flags. Because the jar recomputes the aggregate
as the OR over the `mop` map, this is only lossless when the widget has at least one non-null
`eventType` — the generator therefore emits the reserved key `""` for a widget whose *only* flagged
listeners have a null event type, which is the same key `normalizeEventType("")` produces and is
reachable only by a query for the empty event type. The corpus contains no such listener (0 of
168,503); the rule exists so the behaviour is defined rather than accidental, and it is covered by a
synthetic test.

### D6 — `optionsMenus` carries one record per activity, not per window

The `ape` change specifies one record per `OPTIONSMENU` window. When two windows share a base
activity, the jar's recompute would add the activity if *any* record qualifies — which is exactly the
OR of their `hasFlaggedWidget` values. Emitting one merged record per distinct activity is therefore
observationally identical, and it removes an ordering question from the wire (two records for the same
activity would need a defined order for canonical bytes). Recorded here as a deviation for the `ape`
side to accept; the jar's recompute logic does not change either way.

### D7 — WTG edges are deduplicated; the gate compares the view as a set

`MopData.parseTransitions` appends every click event, duplicates included. Production has not seen
those duplicates since the compaction step began stripping exact-duplicate `transitions` entries
(measured: 27 of 181 apps carried duplicates; `redreader` 70.7%), so deduplication is the current
production behaviour, not a new one. The artifact deduplicates at edge granularity — `(widget, target)`
within a source — and counts removals in `stats.dedupedTransitions`.

This means the equivalence gate cannot compare WTG views as lists when its oracle reads the raw JSON
(D11). It compares them as sets. That is sound only if no consumer reads edge multiplicity; the `ape`
audit states all consumers are set-membership or first-match-fixed-weight, and the gate task requires
that audit to be re-verified rather than trusted.

### D8 — Canonical serialization is `json.dumps` with fixed options, not a custom encoder

`json.dumps(artifact, sort_keys=True, separators=(",", ":"), ensure_ascii=False).encode("utf-8")`.
Sorted keys make object order independent of construction order; fixed separators remove whitespace;
`ensure_ascii=False` keeps text fields as UTF-8 rather than escaping them. Array order is fixed by
construction rather than by sorting where order carries meaning (WTG edges and component lists follow
source first-occurrence; activity sets and `optionsMenus` are sorted). A custom encoder was rejected:
the standard one is deterministic under these options and needs no maintenance.

### D9 — Cache freshness is a digest recorded inside the artifact, and writes are atomic

The artifact records `source.digest = "sha256:<hex>"` of the full-JSON bytes it derived from.
`_derive_mop_artifact` hashes the current full JSON and compares. Alternatives: mtime comparison
(fragile across copies, resumes and containers) or an external sidecar (a second file to keep
consistent). Writes go to a temporary file in the same directory followed by `os.replace`, so a
crash mid-write cannot leave a truncated artifact that a later run would trust.

### D10 — The absent-input path raises rather than degrading

`RVToolExecutionError` naming the expected path. The warn-and-continue it replaces produced runs
labelled as MOP arms that explored as pure SATA, indistinguishable in the results directory from a
real MOP arm — the failure mode with the worst evidence-to-signal ratio in the pipeline. A failed task
is retried by the supervisor and visible in the run summary. Non-MOP arms never enter this branch.

### D11 — The equivalence gate's oracle is the old parser on the **raw** full JSON

The `ape` change assumes the oracle is simply "the old parser on the JSON". Because production pushes
an *enriched* copy, there are two candidate oracles and they differ on 8 apps. Under D4 the raw JSON
is the correct one: the gate must prove that the generator reproduces `MopData`'s semantics, not that
it reproduces the enrichment's distortion. In practice the `ape` gate already reads raw files — the
corpus is producer output that nothing enriches — so this is stated normatively here to prevent a
later "fix" that enriches the oracle to make a divergence disappear.

What the `ape` change does *not* yet record is the consequence: its gate proves equivalence to a
semantics production has not been running. Two amendments follow and must land with this change —
recording the `INV-APV-32` retirement as a behaviour change rather than a subsumed shim, and adding
the direct⇒transitive clause to `INV-DRV-01` (which also invalidates a jar-side scenario asserting
that the two wire bits imply nothing about each other). The corpus path and count need no amendment:
`rearch-07` tasks 1.4/4.1/4.3 and its SHALL scenario already name `rvsec-dataset/static_analysis/`
with 345 apps.

### D12 — The artifact is plain dicts, not a Pydantic model

The repository validates at boundaries with Pydantic, and this is a boundary — but the consumer is a
Java parser, so the enforceable contract is the byte format and the tests that pin it, not a Python
class. A model would add a second definition of the same shape to keep in sync, and would tempt
callers to pass model instances where the canonical bytes are what matters (P1). The shape is pinned
by `test_derive_cryptoapp_ground_truth` and by the `*Target`/call-graph absence test.

## API Design

### `derive(document: dict) -> dict`

**Preconditions**: `document` is a parsed full static-analysis JSON. `document["complete"] is True`
and `document["package"]` is a non-empty string.

**Postconditions**: returns the compact artifact dict per the wire schema (`formatVersion: 1`);
`document` is not mutated; every rule of INV-DRV-01..07 applied. The returned dict contains no
`*Target` key, no `reachability`/`windows`/`transitions`/`listeners` section, and no intent-filter
`data` block.

**Errors**: raises `DerivationError` when `complete` is absent or false, when `package` is missing,
or when a section that must be a list/dict is neither. Never returns a partial artifact. Malformed
*entries* inside a well-typed section are skipped defensively — the producer is an external tool and a
single odd widget must not cost the whole app — and skipped entries are not counted as derivation
failures.

### `serialize_canonical(artifact: dict) -> bytes`

**Preconditions**: `artifact` is the dict returned by `derive`.
**Postconditions**: byte-identical output for equal input, on any host and in any process.
**Errors**: none beyond `TypeError` from a non-serializable value, which would be a generator bug.

### `ApeRVTool._derive_mop_artifact(task: Task) -> str`

**Preconditions**: `_find_static_analysis_file(task)` has returned a path (the caller has already
raised otherwise).
**Postconditions**: returns the path of a `<apk_name>.mop.json` whose `source.digest` matches the
current full JSON. On a cache hit no derivation runs; on a miss the file is written atomically.
**Errors**: `RVToolExecutionError` wrapping `DerivationError`, `OSError` or `json.JSONDecodeError`. No
partial file survives any error path.

### Wire schema (`formatVersion: 1`)

```json
{
  "formatVersion": 1,
  "package": "br.unb.cic.cryptoapp",
  "mainActivity": "br.unb.cic.cryptoapp.MainActivity",
  "source": {"digest": "sha256:…", "file": "cryptoapp.apk.json", "generator": "aperv-derive/1"},
  "widgets": {"<baseActivity>": {"<shortId>": {
      "mop": {"click": "direct", "longclick": "transitive", "scroll": "none"},
      "inputType": "textPassword", "hint": "…", "prompt": "…", "spinnerMode": "…",
      "contentDescription": "…", "tooltipText": "…", "entries": ["…"]}}},
  "mopActivities": ["…"],
  "mopActivitiesAugmented": ["…"],
  "optionsMenus": [{"activity": "…", "hasFlaggedWidget": true}],
  "wtg": {"<sourceBaseActivity>": [{"widget": "…", "target": "…"}]},
  "components": {
    "activities": [{"className": "…", "isMain": false, "exported": true, "permission": null,
                    "reachesMop": false, "deepLinkUri": "myapp://host/path"}],
    "receivers":  [{"className": "…", "isMain": false, "exported": true, "permission": null,
                    "reachesMop": true, "hasTargetMethods": true,
                    "intentFilters": [{"actions": ["…"], "categories": ["…"]}]}],
    "services":   [{"…": "same shape as receivers"}],
    "providers":  [{"className": "…", "isMain": false, "exported": false, "permission": null,
                    "reachesMop": true, "authorities": "…"}]},
  "stats": {"windows": 5, "widgetsTotal": 51, "flagged": 2, "droppedFlaggedNoId": 0,
            "orphanDialogs": 0, "handlersUnmatched": 0, "syntheticLambda": 0, "recovered": 0,
            "wtgEdges": 12, "dedupedTransitions": 0}
}
```

Metadata fields and `entries` are emitted only when non-empty; `deepLinkUri` only when the rule yields
one. `mop` map keys are pre-normalized (lowercased, `_`/`-` removed).

## Data Flow

1. Pre-processing writes `<results_dir>/<apk_name>.json` (unchanged).
2. `execute_tool_specific_logic` step 4, MOP arms only: `_find_static_analysis_file` → raise if absent
   → `_derive_mop_artifact` → cache hit, or `derive` + `serialize_canonical` + atomic write.
3. `adb push <apk_name>.mop.json /data/local/tmp/mop-artifact.json`; `mop_json_pushed = True`.
4. `_push_properties` writes `ape.mopDataPath=/data/local/tmp/mop-artifact.json`.
5. The jar parses only the artifact, recomputes the OPTIONSMENU gateway set from `optionsMenus` + `wtg`
   + the selected activity set, and serves its unchanged query API.
6. Analysis and metric paths read the full JSON and logcat, as before.

## Error Handling

| Error | Source | Strategy | Recovery |
|---|---|---|---|
| Full JSON absent on a MOP arm | `execute_tool_specific_logic` step 4 | `RVToolExecutionError` naming the expected path | Fix pre-processing for that app, or run a non-MOP arm |
| `complete != true` / missing `package` | `derive` | `DerivationError` → `RVToolExecutionError`; nothing written | Re-run static analysis for that app |
| Malformed entry inside a well-typed section | `derive` helpers | Skip the entry defensively; derivation proceeds | None needed; producer noise |
| Unreadable / unparseable full JSON | `_derive_mop_artifact` | `RVToolExecutionError` | Inspect the artifact; producer bug |
| Stale cache (digest mismatch) | `_derive_mop_artifact` | Transparent regeneration | None needed |
| Crash during artifact write | `_derive_mop_artifact` | Atomic rename — the incomplete file is never visible | None needed |
| `adb push` failure | `_push_file_to_device` | `RVToolExecutionError` with exit code and stderr | Device/connection issue; task retried |
| Artifact rejected on device | jar (`MopData.load`) | `status=rejected` → `StopTestingException` before step 1 | Redeploy the coordinated pair |

## Risks / Trade-offs

- [The generator diverges from `MopData`'s semantics on a rule the unit tests do not pin] → the corpus
  gate compares both parsers over 345 real apps pre-cutover, and the permanent suite carries one named
  test per rule, on synthetic fragments where the corpus is thin.
- [The flag-semantics change (D4) makes runs before and after this change non-comparable at the
  substrate level] → stated in the proposal, the spec's REMOVED reason and here, with the measured
  magnitude; no campaign may mix arms across the cut.
- [The gate compares WTG views as sets while the jar's list may carry multiplicity] → the `ape` audit
  claiming no consumer reads multiplicity is re-verified as a gate task, not assumed (D7).
- [The one-shot gate is deleted, so a later regression in a relocated rule is caught only by the unit
  suite] → the suite is enumerated per rule in `tasks.md` and includes the negative cases (a synthetic
  lambda that must *not* be recovered, a filter that must *not* yield a deep link).
- [Two artifacts per app on the host] → kilobytes each, next to a file of megabytes; derivation is
  milliseconds and cached.
- [`stats` are echoed by the jar without recomputation, so a generator bug misreports diagnostics] →
  `stats` never influence a set, flag or edge (INV-DRV-04), and the gate validates the behavioural
  sets independently of them.

## Testing Strategy

| Layer | What to test | How | Count |
|---|---|---|---|
| Unit — derivation rules | One named test per relocated rule, including negative cases: producer precedence, direct⇒transitive, D8 recovery and its refusal, per-event independence, collision rank and tie, empty-id activity marking, five dialog sub-rules, WTG click-only/dedup/base-keying, A′ three sources, OPTIONSMENU records, deep link with its three absent cases | pytest on synthetic fragments | ~24 |
| Unit — projection and format | cryptoapp ground truth, `*Target`/call-graph absence, emission filter, stats granularity, canonical determinism across processes, provenance digest | pytest on the cryptoapp fixture | ~8 |
| Integration — `tool.py` | derive-cache-push order, device path, properties line, absent-JSON raise, derivation-error raise, non-MOP arms untouched, full JSON never pushed, no partial file after failure | pytest with mocked adb | ~8 |
| Audit | No module outside `aperv-tool` reads `.mop.json` | repository grep test | 1 |
| Equivalence (one-shot) | Old parser on the raw full JSON vs new parser on the derived artifact over 345 apps, plus per-rule exercise counts | JVM gate driven jointly with `ape` | 1 × corpus |

CI contract for every pytest invocation: `--import-mode=importlib -o "addopts="`.

## Open Questions

None blocking. Two items are coordination, not design: the `ape` side must accept D6 (one
`optionsMenus` record per activity) and must land the three `rearch-07` amendments of D11 with this
change. Both are recorded as tasks.
