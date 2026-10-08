## Context

The proposal (#122) moves the compact MOP artifact to format 2. The contract was fixed in the `ape` repository by the change `llm-coordinate-single-base`: its design D15 and its `static-analysis-entrypoints` delta, committed as `093d6ab9`. That change is artifacts only, so neither side is implemented yet. This design states how the rv-android side meets the contract and how the two sides are sequenced.

Today the derive (`modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`) is a pure function, from the full-JSON dict to the artifact dict. It does one pass over `reachability[]` (`_index_reachability`), which yields three indices: the exact-join flags per signature, the D8 lambda recovery per class, and the A′ source-3 activity set. It then does one pass over the widget tree (`_parse_windows`), keys widgets by base activity with a strongest-flag collision rule (`_build_widget_map`), moves dialog widgets to their host (`_rekey_dialogs`), and emits. `tool.py` caches the artifact next to its source and reuses it when `source.digest` matches (`_derive_mop_artifact`, `_cached_artifact_digest`; INV-APV-47).

Facts this design relies on, checked on the gh120 fixture `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` with a scratch prototype outside the repository:
- `distanceTargets` has 27 entries: 23 `direct`, then the 4 activity constructors as `boundary`. 38 methods carry `targetDistances`.
- Every activity `<init>` carries `reachesTarget: true` and `targetDistances [[k, 0]]`, where `k` is its own boundary index.
- The click handlers of the three flagged widgets resolve as follows:
  - `buttonGenerateHash` resolves by exact join to `MessageDigestActivity.generateHash(View)`, an XML `android:onClick` method, with pairs `[[22,2]]`;
  - `btn_cipher_encrypt` resolves to `CipherActivity$1.onClick`, with `[[0,4],[1,4]]`;
  - `executeButton` resolves to `CryptographyActivity$$ExternalSyntheticLambda0.onClick`, with `[[16,3],[17,3],[18,3]]` after the cut of ten pairs.
- Two classes declare a handler method: `CipherActivity$1` and `CryptographyActivity$$ExternalSyntheticLambda0`. Both are `transitive`, not direct.
- With the constructor excluded, `activityDist` is `CipherActivity [[0,2],[1,2]]`, `CryptographyActivity [[12,0],[13,0],[14,0]]` and `MessageDigestActivity [[22,2]]`, and `MainActivity` has none. `MainActivity`'s only reaching method is its `<init>`, so it leaves `mopActivitiesAugmented`.

FRs/NFRs: FR04–FR06 (MOP data from the static analysis), FR19 (tool configuration), FR20 (variants), NFR04 (deterministic artifact bytes).

## Architecture

```
full .apk.json ──► derive()
                    ├─ _index_reachability          flags, lambda recovery, source 3 (no <init>/<clinit>)
                    │                                + distance minima per signature, per lambda class,
                    │                                  per activity class (no <init>/<clinit>)
                    │                                + handler-class records
                    ├─ _parse_windows               widget record + per-event distance minima
                    ├─ _build_widget_map            collisions merge minima; activity minima before the id drop
                    ├─ _rekey_dialogs               dialog minima move with the widgets
                    └─ emit                         _cut_pairs at the wire: K=3, (d, i) order
                    ▼
               *.mop.json (formatVersion 2) ──► tool.py cache (digest + format) ──► device ──► ape MopData
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `derive_mop_artifact._index_reachability` | adds three distance indices, the handler records, and the source-3 constructor exclusion | `reachability[]`, `targets` | flag indices (unchanged), `dist_by_signature`, `lambda_dist_by_class`, `activity_class_dist`, `handler_records`, `activity_classes` |
| `derive_mop_artifact._derive_widget_flags` | per-event minima beside the per-event flags, same tiers | listeners, indices | `(mop, dist_minima, direct, transitive)` |
| `derive_mop_artifact._merge_minima` | the one merge rule: minimum per target, in place | two `dict[int, int]` | the first, updated |
| `derive_mop_artifact._cut_pairs` | the one wire rule: K = 3 pairs, sorted by `(d, i)` | `dict[int, int]` | `list[[i, d]]` |
| `derive_mop_artifact._read_pairs` | validates `targetDistances` entries against `targets` | raw list, `targets` | `dict[int, int]` |
| `tool.ApeRVTool._cached_artifact_identity` | replaces `_cached_artifact_digest`; reads digest and format | cached artifact path | `(digest, formatVersion)` or `None` |
| `tool.APERV_PROPERTY_MAPPING` | six new entries | — | 56 entries |
| `tool.ApeRVTool.get_variants` | two new arms | — | ten names |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| MOP Artifact Projection Contents, item 9 (`targets`, `dist`, `activityDist`, `handlers`) | `derive()`, `_index_reachability`, `_derive_widget_flags`, `_build_widget_map`, `_rekey_dialogs`, `_emit_widgets`, new `_emit_activity_dist`, `_emit_handlers` | `tests/test_derive_mop_artifact.py`: one test per new scenario, the cryptoapp ground truth |
| INV-DRV-10 (pair rules) | `_read_pairs`, `_merge_minima`, `_cut_pairs` | property-style test over random minima: at most 3, sorted, unique, indices in range |
| INV-DRV-06 (amended) | emission only; no signature reaches the wire | the "no Target vocabulary" test extended to `distanceTargets` and signature-shaped strings |
| MOP-Activity Sets, source 3 | `_index_reachability` skips `<init>`/`<clinit>` for `activity_classes` | cryptoapp: `MainActivity` out of `mopActivitiesAugmented` |
| Canonical Serialization | `_cut_pairs` order | the byte-identical regeneration test re-run on the format-2 fixture |
| Derived MOP Artifact Generation and Caching, INV-APV-47 | `_derive_mop_artifact`, `_cached_artifact_identity` | `tests/test_aperv_tool.py`: format-1 cache with matching digest regenerates |
| ape.properties Generation | `APERV_PROPERTY_MAPPING` | count 56, the six keys, no `step_telemetry_enabled`; `mopd_on_llm_off` writes `ape.mopScoring=distance`; `tests/migration/test_mapping_sweep.py` against an ape checkout carrying Part B |
| ApeRVTool Variants, INV-APV-05, INV-APV-42 | `get_variants()` | ten keys; `tests/migration/test_decisive_contrasts.py` with the two new contrasts |
| Decisive Run Arm Set | `get_variants()` | `mopd_on_llm_90` equals the E6 arm 4 keys plus `mop_scoring` |

## Goals / Non-Goals

**Goals:**
- Emit exactly the format-2 artifact of the `ape` contract, byte-deterministic, from any well-typed document, gh120 or not.
- Keep one rule per concern: one merge (minimum per target), one cut (K = 3, `(d, i)`), and one resolution of handler to method, shared by flags and distances.
- Never push a stale format-1 artifact to a format-2 jar.
- Give the campaign the two distance arms and the six keys.

**Non-Goals:**
- A reader or converter for format 1. Earlier artifacts are re-derived, not translated (P3).
- A guard against `.apk.json` files written before gh120. gh120 D9 decided against one, and the `ape` author confirmed on 2026-10-08 that the jar runs such an artifact without distances.
- Campaign instrumentation (`--instrumentation-variant dexlib2 --stamp-handlers`): the Study 03 replication-package side runs it.
- New `stats` counters: the jar's `MOP_DATA` record reports `targets`, the size of `handlers` and the pairs it drops.
- A flag-mode arm at `llm_percentage` 0.9: Study 03's `e6_mop_on_llm_90` lives in the replication package (Open Questions).

## Decisions

### D1. Distances ride the existing indices and the existing join

`_index_reachability` already visits every method once. It gains three maps keyed like the flag indices:
- `dist_by_signature` holds the method's own minima;
- `lambda_dist_by_class` holds, per enclosing class, the minimum over its reaching `lambda$…` methods;
- `activity_class_dist` holds, per base activity of an activity-typed class, the minimum over its methods other than `<init>`/`<clinit>`.

`_derive_listener_flags` resolves a handler once and returns both its flags and its minima, through the same tiers. The exact join comes first and the class recovery runs only on a miss (INV-DRV-09), so the distance of a listener always comes from the method its flag came from. The producer-precedence tier supplies flags and no distance, so on that tier the minima still come from the join.

*Alternative:* a second, distance-only resolution. Rejected: two resolutions of one handler could disagree, and the contract requires "the same exact signature join that gives its flags".

### D2. Minima are kept whole until the wire

Inside the derive a distance set is `dict[int, int]` (target → minimum `d`). Every merge uses `_merge_minima`: listeners of one event, colliding widgets, dialog into host, two methods of one handler class, an activity's widgets and its own methods. `_cut_pairs` turns a set into the wire list at emission and nowhere else. The contract requires merges before the cut (INV-DRV-10): cutting each source to three before merging could drop a target that is fourth in one source and first after the merge.

### D3. Activity minima are accumulated before the empty-id drop

`activityDist` includes widgets that the empty-short-id rule keeps off the wire, which is the same reason INV-DRV-02 gives for the activity sets. `_build_widget_map` therefore folds every parsed widget's minima (all events) into `activity_minima[base]` before the drop and before the collision rule. `_rekey_dialogs` moves a dialog's entry into its host with `_merge_minima` and deletes it, as it does for widgets. An orphan dialog keeps its own key, which names no manifest activity, so its entry is emitted and never read by the launcher. At emission, each activity's widget minima are merged with `activity_class_dist[base]`.

### D4. The handler table comes from `reachability[]` signatures

A method fills a handler event when its signature matches `^<(?P<cls>[^:]+): \S+ (?P<name>onClick|onLongClick|invoke)\((?P<params>[^)]*)\)>$`:
- `onClick` with params `android.view.View` fills `click`;
- `onLongClick` with `android.view.View` fills `longclick` (its return type is `boolean`, which is why the name and params, not the return type, are matched);
- `invoke` with return type `java.lang.Object` and params empty or `java.lang.Object` fills both.

Matching the Object-returning `invoke` follows the contract. It is also the method the Compose runtime calls through `Function0`/`Function1`, so its distance is the distance from the entry the framework enters. A Kotlin lambda's typed `void invoke()` is one call further in and is not listed separately.

The record's key is `reachability[].className`, which is already the binary name gh121 stamps. Each event's flag comes from the method's own two axes (INV-DRV-01). A class whose only matches reach nothing is listed with `none`, because the jar reads "listed" as "this handler reaches no target".

### D5. Pair entries are validated where they are read

`_read_pairs(raw, targets)` keeps an entry only when it is a two-element list of non-bool `int`s with `0 ≤ i < targets` and `d ≥ 0`, and takes the minimum on a repeated index. A malformed entry is skipped, following the module's "noise survivable, structure not" rule. `distanceTargets` is read through `_require_section(document, "distanceTargets", list, [])`, so a non-list is a `DerivationError` like any section of the wrong type, and an absent one gives `targets = 0`. With `targets = 0` every entry fails the range check and no pair is emitted. A September document therefore derives cleanly with no distances.

### D6. The cache key is (digest, format)

`_cached_artifact_digest` becomes `_cached_artifact_identity`, which returns `(source.digest, formatVersion)` or `None`. `_derive_mop_artifact` reuses the cached file only when the pair equals `(digest_of(raw), FORMAT_VERSION)`. Comparing `source.generator` as well was considered and rejected: `formatVersion` is the field the jar gates on (`ape` INV-MOP-34), so it is the field whose mismatch would abort a run.

### D7. The distance arms are deltas of existing arms

- `mopd_on_llm_off` is `mop_on_llm_off`'s override dict plus `mop_scoring: "distance"`.
- `mopd_on_llm_90` is the override dict of Study 03's `e6_mop_on_llm_90` plus `mop_scoring: "distance"`. That dict is E5b's `e5b_m1_v13_A` (`rvsec-study03-replication-package/experiments/E5b-inloop/config/tool.py:575-592`) with `llm_percentage` 0.9 (`src/rvsec_study03/e6/config.py`). It is written out key by key, so this module's arm does not depend on the replication package at run time.

Neither arm states `mop_weight_d1..3`, `mop_retire_after` or `mop_launcher_dmax`. The jar's defaults (500/400/300, 3, 6) are the decision-10 values the `ape` author adopted, and restating a default would be "a delta that is not a delta" (the module's own rule for `mop_off_llm_off`). Both arms keep the reference's frontier substrate and `mop_activity_source_components=True`, so each contrast stays single-factor (scenarios in "Decisive Run Arm Set").

### D8. Sequencing with the `ape` jar

The derive bump and the jar's format-2 reader must reach a campaign together: each jar rejects the other format, and every MOP arm aborts on a mismatch. The mapping sweep (`tests/migration/test_mapping_sweep.py`) also checks every mapped key against `KeyOwnership.java` in the ape checkout named by `$APE_REPO`/`$RVSEC_HOME/ape`. The six keys exist there only once `llm-coordinate-single-base` group 13 is implemented. The task order is therefore:
1. the derive and the cache, which are self-contained and testable now (tasks 1–3);
2. the mapping and the arms, applied against an ape checkout that carries Part B (task 4, gated);
3. no campaign uses a jar older than Part B with this derive.

The derive part can be committed before the jar exists, because nothing deploys it until the campaign image is rebuilt.

## API Design

### `derive(document: dict, source_file: str = "", source_digest: str = "") -> dict`

- **Pre:** unchanged.
- **Post:** the format-2 artifact of "MOP Artifact Projection Contents". It adds the keys `targets: int`, `activityDist: dict[str, list[list[int]]]` and `handlers: dict[str, dict]`, and widgets may carry `dist: dict[str, list[list[int]]]`. `formatVersion == 2` and `source.generator == "aperv-derive/2"`. INV-DRV-05, INV-DRV-06 and INV-DRV-10 hold.
- **Errors:** `DerivationError` as today, plus a `distanceTargets` of the wrong type.

### `_cut_pairs(minima: dict[int, int]) -> list[list[int]]`

- **Post:** `[[i, d] for (d, i) in sorted((d, i) for i, d in minima.items())][:DIST_K]`, with `DIST_K = 3`. Empty when `minima` is empty.

### `_merge_minima(into: dict[int, int], other: dict[int, int]) -> dict[int, int]`

- **Post:** for every `i` of `other`, `into[i] = min(into.get(i, other[i]), other[i])`. It returns `into` and mutates nothing else.

### `ApeRVTool._cached_artifact_identity(artifact_path: str) -> tuple[str, int] | None`

- **Post:** `(source.digest, formatVersion)` of a readable cached artifact, else `None`. A missing field gives `None`, which reads as a cache miss.

## Data Flow

1. `tool.py` reads `<apk>.json` bytes and computes the digest. It reuses `<apk>.mop.json` only when digest and format both match, and otherwise calls `derive()`.
2. `derive()` reads `targets` from `distanceTargets`, builds the flag and distance indices and the handler records in one pass over `reachability[]`, then parses the widget tree. Each listener yields its flags and minima from the same join.
3. `_build_widget_map` keys widgets with flags by strongest rule and minima by merge, and folds every widget's minima into its activity before the id drop. `_rekey_dialogs` moves both.
4. Emission cuts every minima set to K = 3 pairs in `(d, i)` order and omits the empty ones. `serialize_canonical` is unchanged, so key order and array order are what make the bytes stable.
5. The artifact is pushed to `/data/local/tmp/mop-artifact.json`. For a `mopd_*` arm the properties file also carries `ape.mopScoring=distance`.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `DerivationError` | `distanceTargets` present but not a list | refuse, as for any mistyped section | fix the producer output; `RVToolExecutionError` fails the task as today |
| malformed `targetDistances` entry | wrong shape, index out of range, negative `d` | skip the entry | none; a conforming producer emits none |
| document without `distanceTargets` | pre-gh120 `.apk.json` | derive with `targets: 0` and no pair | the corpus hand-off keeps such documents out; the jar runs them without distances |
| cached format-1 artifact | derived before this change | cache miss by format, re-derive | automatic |
| jar without Part B | an older `ape-rv.jar` deployed with this derive | the jar rejects format 2 (`version-mismatch`) and a MOP arm aborts, or rejects `ape.mopScoring` as unknown | deploy the jar of `llm-coordinate-single-base` (D8) |

## Risks / Trade-offs

- **[One-way format coupling]** Format 2 aborts every MOP arm of every jar before Part B. → Mitigation: D8 sequencing. The `ape` change ships its reader in the same window, and the task list gates the arm part on an ape checkout that carries Part B.
- **[The mapping sweep needs the future ape checkout]** `test_mapping_sweep` fails against today's ape `master`, because the six keys are unknown there. → Mitigation: task 4 runs it against `$APE_REPO` pointing at the Part B implementation. Until then the six entries stay out of the mapping.
- **[Bridge `invoke` adds one call]** On a non-indy Kotlin lambda the listed `Object invoke()` is a bridge to the typed one, so its distance is one more than the body's. That is the same one-call offset a D8 wrapper's `onClick` has to its `lambda$…` body, and it measures from the method the framework calls. → Mitigation: none needed. It is stated so a reader of `handlers` distances does not take it for an off-by-one.
- **[Fixture is gh60-shaped with gh120 additions]** The cryptoapp fixture is the gh60 producer output with gh120 fields, not a full gh120 run. → Mitigation: the night analysis of the corpus produces real gh120 documents. Task 6 derives a sample of them and checks INV-DRV-10 and the source-3 exclusion on real data.
- **[The `distance` LLM arm has no flag twin here]** `mopd_on_llm_90`'s flag-mode counterpart is the replication package's `e6_mop_on_llm_90`. → Mitigation: Open Questions.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (derive) | the format-2 scenarios: per-widget minima and cut, lambda recovery distances, collision merge, dialog move, activity minima with the constructor excluded, handler table (including a class reaching nothing and `invoke(Object)`), no-`distanceTargets` document, malformed pairs skipped, source 3 | `tests/test_derive_mop_artifact.py`, synthetic documents plus the cryptoapp fixture | ~14 |
| Unit (pair rules) | INV-DRV-10 over random minima | seeded random dicts, `_cut_pairs` and `_merge_minima` | ~2 |
| Unit (wire hygiene) | INV-DRV-06 amended: no `distanceTargets`, no signature-shaped string, only `hasTargetMethods` contains `Target` | extended existing test | 1 |
| Unit (tool) | cache by format; mapping count and keys; ten variants; `mopd_on_llm_off` properties lines | `tests/test_aperv_tool.py` | ~6 |
| Migration | the mapping sweep and the two new single-factor contrasts | `tests/migration/`, with `APE_REPO` at the Part B checkout | ~3 |
| Regression | every existing aperv-tool test, with the format-1 assertions (`test_derive_mop_artifact.py:388,400,1591`, `test_aperv_tool.py:1500,1547,1926`) moved to format 2 | `pytest --import-mode=importlib -o "addopts=" modules/aperv-tool/tests` | existing |
| Data | derive a sample of the night gh120 corpus documents; check INV-DRV-10, `targets > 0`, and the share of activities in `mopActivitiesAugmented` before and after the exclusion | script in the change folder, read-only on the dataset | 1 run |

## Open Questions

- **Should `aperv-tool` also carry the flag-mode twin of `mopd_on_llm_90` (`mop_on_llm_90`)?** Today the only flag arm at dose 0.9 is the replication package's `e6_mop_on_llm_90`, and the only flag arm of this module under the LLM is `mop_on_llm_70`. A distance-versus-mark contrast under the LLM inside this module needs the twin. Not added, because the author asked for the distance arm only (2026-10-08).
- **Where the campaign turns the stamp on.** The replication-package side instruments the corpus. If it does not pass `--instrumentation-variant dexlib2 --stamp-handlers`, every stamp field is null and the jar falls back to the id key everywhere. The run reports this as `RUN_END.stampNodes == 0`.
