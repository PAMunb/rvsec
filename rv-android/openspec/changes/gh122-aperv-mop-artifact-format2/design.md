## Context

The proposal (#122) moves the compact MOP artifact to format 2. The contract was fixed in the `ape` repository by the change `llm-coordinate-single-base`: its design D15 and its `static-analysis-entrypoints` delta, committed as `093d6ab9`. That change is artifacts only, so neither side is implemented yet. This design states how the rv-android side meets the contract and how the two sides are sequenced.

Today the derive (`modules/aperv-tool/src/aperv_tool/tools/aperv/derive_mop_artifact.py`) is a pure function, from the full-JSON dict to the artifact dict. It does one pass over `reachability[]` (`_index_reachability`), which yields three indices: the exact-join flags per signature, the D8 lambda recovery per class, and the A′ source-3 activity set. It then does one pass over the widget tree (`_parse_windows`), keys widgets by base activity with a strongest-flag collision rule (`_build_widget_map`), moves dialog widgets to their host (`_rekey_dialogs`), and emits. `tool.py` caches the artifact next to its source and reuses it when `source.digest` matches (`_derive_mop_artifact`, `_cached_artifact_digest`; INV-APV-47).

Facts this design relies on, checked on the gh120 fixture `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` with a scratch prototype outside the repository. The aperv-tool ground-truth fixture `modules/aperv-tool/tests/fixtures/cryptoapp.apk.json` is replaced by a byte copy of that file (sha256 `005d6a19…3d687213`, regenerated with the deployed GATOR in `b21eb15b`), because the gh60 output it held had no `distanceTargets` and could not carry these facts:
- `distanceTargets` has 27 entries: 23 `direct`, then the 4 activity constructors as `boundary`. 38 methods carry `targetDistances`.
- Every activity `<init>` carries `reachesTarget: true` and `targetDistances [[k, 0]]`, where `k` is its own boundary index.
- The click handlers of the three flagged widgets resolve as follows:
  - `buttonGenerateHash` resolves by exact join to `MessageDigestActivity.generateHash(View)`, an XML `android:onClick` method, with pairs `[[22,2]]`;
  - `btn_cipher_encrypt` resolves to `CipherActivity$1.onClick`, with `[[0,4],[1,4]]`. Both pairs are at `d = 4`, so the widget carries no `dist` on the wire (D9);
  - `executeButton` resolves to `CryptographyActivity$$ExternalSyntheticLambda0.onClick`, whose ten pairs hold exactly three at `d ≤ 3`: `[[16,3],[17,3],[18,3]]`.
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
                    └─ emit                         cut at the wire, (d, i) order:
                                                     _cut_weighed (widgets, handlers): every d ≤ 3
                                                     _cut_nearest (activityDist): K = 3
                    ▼
               *.mop.json (formatVersion 2) ──► tool.py cache (digest + format) ──► device ──► ape MopData

tool.py: digest_of_file (chunks) ──► cache hit? ──yes──► reuse, no parse
                                          └─no──► json.load(file) ──► derive()
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `derive_mop_artifact._index_reachability` | adds three distance indices, the handler records, and the source-3 constructor exclusion | `reachability[]`, `targets` | flag indices (unchanged), `dist_by_signature`, `lambda_dist_by_class`, `activity_class_dist`, `handler_records`, `activity_classes` |
| `derive_mop_artifact._derive_widget_flags` | per-event minima beside the per-event flags, same tiers | listeners, indices | `(mop, dist_minima, direct, transitive)` |
| `derive_mop_artifact._merge_minima` | the one merge rule: minimum per target, in place | two `dict[int, int]` | the first, updated |
| `derive_mop_artifact._cut_weighed` | the wire rule of the widget and handler lists: every pair at `d ≤ DIST_WEIGHED_MAX` (3), sorted by `(d, i)` | `dict[int, int]` | `list[[i, d]]` |
| `derive_mop_artifact._cut_nearest` | the wire rule of `activityDist`: the `DIST_K` (3) pairs of smallest `d`, sorted by `(d, i)` | `dict[int, int]` | `list[[i, d]]` |
| `derive_mop_artifact.digest_of_file` | replaces `digest_of(bytes)`: the provenance digest of a file, read in chunks | path | `"sha256:<hex>"` |
| `tool.ApeRVTool._derive_mop_artifact` | hashes, checks the cache, and parses with `json.load` only on a miss; holds no copy of the file's bytes | task | artifact path |
| `derive_mop_artifact._read_pairs` | validates `targetDistances` entries against `targets` | raw list, `targets` | `dict[int, int]` |
| `tool.ApeRVTool._cached_artifact_identity` | replaces `_cached_artifact_digest`; reads digest and format | cached artifact path | `(digest, formatVersion)` or `None` |
| `tool.APERV_PROPERTY_MAPPING` | six new entries | — | 56 entries |
| `tool.ApeRVTool.get_variants` | two new arms | — | ten names |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| MOP Artifact Projection Contents, item 9 (`targets`, `dist`, `activityDist`, `handlers`) | `derive()`, `_index_reachability`, `_derive_widget_flags`, `_build_widget_map`, `_rekey_dialogs`, `_emit_widgets`, new `_emit_activity_dist`, `_emit_handlers` | `tests/test_derive_mop_artifact.py`: one test per new scenario, the cryptoapp ground truth |
| INV-DRV-10 (pair rules) | `_read_pairs`, `_merge_minima`, `_cut_weighed`, `_cut_nearest` | property-style test over random minima: sorted, unique, indices in range; `_cut_weighed` keeps exactly the minima at `d ≤ 3`, `_cut_nearest` at most 3; the scenarios "a widget whose targets are all four calls or more away carries no pair" and "activityDist keeps the three nearest targets" |
| INV-DRV-06 (amended) | emission only; no signature reaches the wire | the "no Target vocabulary" test extended to `distanceTargets` and signature-shaped strings |
| MOP-Activity Sets, source 3 | `_index_reachability` skips `<init>`/`<clinit>` for `activity_classes` | cryptoapp: `MainActivity` out of `mopActivitiesAugmented` |
| Canonical Serialization | the `(d, i)` order of `_cut_weighed` and `_cut_nearest` | the byte-identical regeneration test re-run on the format-2 fixture |
| Derived MOP Artifact Generation and Caching, INV-APV-47 | `_derive_mop_artifact`, `_cached_artifact_identity`, `digest_of_file` | `tests/test_aperv_tool.py`: format-1 cache with matching digest regenerates; a cache hit never calls `json.load`; `digest_of_file` equals the SHA-256 of the bytes on a file longer than one chunk |
| ape.properties Generation | `APERV_PROPERTY_MAPPING` | count 56, the six keys, no `step_telemetry_enabled`; `mopd_on_llm_off` writes `ape.mopScoring=distance`; `tests/migration/test_mapping_sweep.py` against an ape checkout carrying Part B |
| ApeRVTool Variants, INV-APV-05, INV-APV-42 | `get_variants()` | ten keys; `tests/migration/test_decisive_contrasts.py` with the two new contrasts |
| Decisive Run Arm Set | `get_variants()` | `mopd_on_llm_90` equals the E6 arm 4 keys plus `mop_scoring` |

## Goals / Non-Goals

**Goals:**
- Emit exactly the format-2 artifact of the `ape` contract, byte-deterministic, from any well-typed document, gh120 or not.
- Keep one rule per concern: one merge (minimum per target), one order (`(d, i)`), one cut per kind of list (`d ≤ 3` for the lists that weigh an action, K = 3 for `activityDist`), and one resolution of handler to method, shared by flags and distances.
- Hold no copy of the full JSON's bytes while it is parsed and derived.
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

Inside the derive a distance set is `dict[int, int]` (target → minimum `d`). Every merge uses `_merge_minima`: listeners of one event, colliding widgets, dialog into host, two methods of one handler class, an activity's widgets and its own methods. `_cut_weighed` and `_cut_nearest` (D9) turn a set into the wire list at emission and nowhere else. The contract requires merges before the cut (INV-DRV-10). Cutting each source to three before merging could drop a target that is fourth in one source and first after the merge. Cutting a widget's set at `d ≤ 3` before the activity merge would drop pairs that `activityDist` must still rank.

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

### D9. Two cuts: every weighed pair on widgets and handlers, the three nearest on activities

The contract first cut every list to the three nearest pairs. On 2026-10-09 the author changed the cut of the widget and handler lists to "every target at `d ≤ 3`" (`ape` D15, amendment of 2026-10-09; evidence in `ape` `openspec/changes/llm-coordinate-single-base/evidence/format2_gaps/`). The aperv session measured it on the 163 round-A gh120 documents, derived with this change's `derive()`:
- with three pairs per list, 4,024 of the 21,485 targets that lie at `d ≤ 3` on some widget or handler list before the cut lie at `d ≤ 3` on no such list after it (18.7 %); over every list, `activityDist` included, 9,158 of 27,671 (33 %, in 98 apps). Such a target can never give an action a weight, and the jar retires only targets on the wire, so it never retires either;
- a pair at `d ≥ 4` gives no weight (`ape` D18), so the new cut drops nothing the jar uses;
- the artifacts barely grow. With every widget and handler list cut at `d ≤ 3`, the median artifact is 34 KB (34 KB before), the largest 1.9 MB (1.97 MB, `com.celzero.bravedns`), and the 162 artifacts 15.2 MB in all (14.6 MB). The longest list holds 798 targets (median 1, 90th percentile 7), and the jar's `MopData.PairReader` reads a list of any length.

`activityDist` keeps the three nearest pairs. The launcher only orders the activities the census already makes eligible (`ape` D20), and a cut at the launcher's bound `d ≤ 6` would carry 211 thousand pairs, about 0.8 MB on the largest app, for an ordering key. The activity merge starts from the widgets' uncut minima (D2, D3), so a widget whose targets are all at `d ≥ 4` carries no `dist` and still counts toward its activity.

Two functions express the two rules: `_cut_weighed(minima)` keeps every pair at `d ≤ DIST_WEIGHED_MAX` (3), and `_cut_nearest(minima)` keeps the `DIST_K` (3) nearest. Both sort by `(d, i)`. An event whose list is empty after the cut has no key, and a `dist` map left empty is omitted, on widgets and on handler records alike. The handler record itself stays, with its flags: on the device a listed class still states what the stamped handler reaches.

*Alternatives:* keep three pairs. Rejected by the measurement above. Cut every list at `d ≤ 6`, which the aperv session also measured: the largest artifact grows to 13 MB (`jtx`) and the 162 artifacts to 60 MB, for pairs the jar does not weigh.

### D10. The source is hashed in chunks and parsed from the file

Today `_derive_mop_artifact` reads the full JSON into one `bytes` object, hashes it, and passes it to `json.loads`; the object stays referenced until `derive()` returns. The aperv session measured the peak resident memory of that path, one fresh process per document, at about 4.1 times the file size (median over the documents above 100 MB; 7.1 times for wikipedia): 8.9 GB → 36.4 GB in 161 s (`sdmse`), 2.06 GB → 14.6 GB (wikipedia), 1.92 GB → 7.9 GB (`jtx`). The 90th percentile of the round-A documents is 1.27 GB, and the median 42 MB.

The method now does three things in order:
- it computes the digest with `digest_of_file(path)`, which streams the file through `hashlib.file_digest`;
- it checks the cache, so a hit returns without parsing anything;
- on a miss, it parses with `json.load` from a UTF-8 text handle.

`digest_of_file` replaces `digest_of(bytes)`, so the digest convention stays defined in one place.

`json.load` still reads the file's text whole before it parses. What disappears is the `bytes` copy held through the parse and the derivation, and the decode of those bytes into a second copy during `json.loads`. The saving is therefore about one file size of a peak of about four. That is an estimate; task 7.7 measures it. A file that is not UTF-8 raises `UnicodeDecodeError`, a `ValueError`, which fails the task through the same path as an unparseable file. A conforming producer writes UTF-8.

*Alternatives:* a streaming parser (`ijson`). Not now: `derive()` reads `distanceTargets` before `reachability[]` and `windows`, so it needs the sections in an order the file does not guarantee. It would also add a dependency. Caching the artifact per APK outside the task directory: it touches rv-platform's per-task layout and is out of scope (Risks).

## API Design

### `derive(document: dict, source_file: str = "", source_digest: str = "") -> dict`

- **Pre:** unchanged.
- **Post:** the format-2 artifact of "MOP Artifact Projection Contents". It adds the keys `targets: int`, `activityDist: dict[str, list[list[int]]]` and `handlers: dict[str, dict]`, and widgets may carry `dist: dict[str, list[list[int]]]`. `formatVersion == 2` and `source.generator == "aperv-derive/2"`. INV-DRV-05, INV-DRV-06 and INV-DRV-10 hold.
- **Errors:** `DerivationError` as today, plus a `distanceTargets` of the wrong type.

### `_cut_weighed(minima: dict[int, int]) -> list[list[int]]`

- **Post:** `[[i, d] for (d, i) in sorted((d, i) for i, d in minima.items()) if d <= DIST_WEIGHED_MAX]`, with `DIST_WEIGHED_MAX = 3`. Empty when no target lies at `d ≤ 3`.

### `_cut_nearest(minima: dict[int, int]) -> list[list[int]]`

- **Post:** `[[i, d] for (d, i) in sorted((d, i) for i, d in minima.items())][:DIST_K]`, with `DIST_K = 3`. Empty when `minima` is empty.

### `digest_of_file(path: str) -> str`

- **Post:** `"sha256:" + hex`, equal to the SHA-256 of the file's bytes, read in chunks.
- **Errors:** `OSError` when the file cannot be read.

### `_merge_minima(into: dict[int, int], other: dict[int, int]) -> dict[int, int]`

- **Post:** for every `i` of `other`, `into[i] = min(into.get(i, other[i]), other[i])`. It returns `into` and mutates nothing else.

### `ApeRVTool._cached_artifact_identity(artifact_path: str) -> tuple[str, int] | None`

- **Post:** `(source.digest, formatVersion)` of a readable cached artifact, else `None`. A missing field gives `None`, which reads as a cache miss.

## Data Flow

1. `tool.py` computes the digest of `<apk>.json` in chunks. It reuses `<apk>.mop.json` only when digest and format both match, and otherwise parses the file with `json.load` and calls `derive()`.
2. `derive()` reads `targets` from `distanceTargets`, builds the flag and distance indices and the handler records in one pass over `reachability[]`, then parses the widget tree. Each listener yields its flags and minima from the same join.
3. `_build_widget_map` keys widgets with flags by strongest rule and minima by merge, and folds every widget's minima into its activity before the id drop. `_rekey_dialogs` moves both.
4. Emission cuts each widget and handler minima set to its pairs at `d ≤ 3`, and each activity set to its three nearest pairs, all in `(d, i)` order, and omits the empty ones. `serialize_canonical` is unchanged, so key order and array order are what make the bytes stable.
5. The artifact is pushed to `/data/local/tmp/mop-artifact.json`. For a `mopd_*` arm the properties file also carries `ape.mopScoring=distance`.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `DerivationError` | `distanceTargets` present but not a list | refuse, as for any mistyped section | fix the producer output; `RVToolExecutionError` fails the task as today |
| malformed `targetDistances` entry | wrong shape, index out of range, negative `d` | skip the entry | none; a conforming producer emits none |
| document without `distanceTargets` | pre-gh120 `.apk.json` | derive with `targets: 0` and no pair | the corpus hand-off keeps such documents out; the jar runs them without distances |
| cached format-1 artifact | derived before this change | cache miss by format, re-derive | automatic |
| source not UTF-8 | `json.load` on the text handle raises `UnicodeDecodeError` | caught with the parse errors; `RVToolExecutionError` fails the task | fix the producer output; GATOR writes UTF-8 |
| jar without Part B | an older `ape-rv.jar` deployed with this derive | the jar rejects format 2 (`version-mismatch`) and a MOP arm aborts, or rejects `ape.mopScoring` as unknown | deploy the jar of `llm-coordinate-single-base` (D8) |

## Risks / Trade-offs

- **[One-way format coupling]** Format 2 aborts every MOP arm of every jar before Part B. → Mitigation: D8 sequencing. The `ape` change ships its reader in the same window, and the task list gates the arm part on an ape checkout that carries Part B.
- **[The mapping sweep needs the future ape checkout]** `test_mapping_sweep` fails against today's ape `master`, because the six keys are unknown there. → Mitigation: task 4 runs it against `$APE_REPO` pointing at the Part B implementation. Until then the six entries stay out of the mapping.
- **[Bridge `invoke` adds one call]** On a non-indy Kotlin lambda the listed `Object invoke()` is a bridge to the typed one, so its distance is one more than the body's. That is the same one-call offset a D8 wrapper's `onClick` has to its `lambda$…` body, and it measures from the method the framework calls. → Mitigation: none needed. It is stated so a reader of `handlers` distances does not take it for an off-by-one.
- **[The fixture is one small app]** The cryptoapp fixture is a full gh120 run, but of one app with 27 targets and two handler classes. → Mitigation: task 5.1 derives a sample of the Study 03 v2 analysis (round A, gh120 GATOR) and checks INV-DRV-10, `targets > 0` and the source-3 exclusion on real data.
- **[Reaching without a distance means farther than `DIST_MAX`]** The producer can mark a method reaching and give it no `targetDistances`. The cause is in gh120's two searches over one call graph:
  - `reachesTarget` comes from an unbounded reverse search (`ReachabilityEngine`);
  - `targetDistances` comes from one reverse search per target, cut at `DIST_MAX = 10` (`TargetDistances.java:50,176`).

  Every path to a target passes through an app method that is a direct or boundary target, so a reaching method with no pair is one whose every target is more than 10 calls away. The data show the cut: in the affected apps the minimum distance piles up at d = 9–10 (nerdcalci: 250 at 9, 453 at 10, and 1,943 reaching methods with no pair), while healthy apps decay to zero well before 10 (aegis: 1 at 8, none at 9 or 10).

  The derive does not invent a distance, so a widget or handler whose reaching methods are all that far is flagged and has no pair. Under `mop_scoring: distance` that gives the same result as the exact distance would: a target at d ≥ 4 gives no weight, and the launcher counts d ≤ `mopLauncherDmax` (6) only. No decision of the jar changes. What is lost is the difference between "farther than 10" and "unknown", which matters only to an offline reader.

  Size, over the 92 round-A documents (`reach_without_distance.out.md`):
  - Compose apps (21): 686 of 1,314 reaching handler methods (52.2 %) have no pair, all in 8 apps and most of each app (nerdcalci 299/328, stutter 76/77), because a Compose click runs through the Compose runtime and every library call counts.
  - View-only apps (71): 101 of 3,955 (2.6 %), mostly treehouses and keepalive, where Kotlin coroutines play the same role.

  In those 8 Compose apps the `mopd_*` arms therefore give almost no click a MOP weight while the flag arms give them +300. That is the distance scoring doing what it is for, and the Study 03 analysis must read the flag-vs-distance contrast with it in mind. → Mitigation: none needed on this side. The producer contract should state the invariant ("`reachesTarget` without `targetDistances` ⇔ every target farther than `DIST_MAX`"); that belongs to the next gh120 producer change.
- **[Host memory of the derive and the per-task copy]** D10 removes the `bytes` copy, but the parse still holds the document's text and its parsed form. The largest round-A document (8.9 GB) peaked at 36.4 GB before D10, so a few such derives running at once can exhaust the host. Two costs stay outside this module:
  - rv-platform (`static_analysis.py`, the copy into `task.results_dir`) copies the full JSON into every task's results directory, 8.9 GB per task for `sdmse`;
  - the cache lives in that same directory, so every task derives its own artifact. The digest cache helps only when the same task resumes.

  Reading the code shows this; the directory layout at run time was not checked. → Mitigation: none in this change. A per-APK cache outside the task directory, or a streaming parse, would be a later change if the author wants one. Task 7.7 measures what D10 saves.
- **[The `distance` LLM arm has no flag twin here]** `mopd_on_llm_90`'s flag-mode counterpart is the replication package's `e6_mop_on_llm_90`. → Mitigation: Open Questions.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (derive) | the format-2 scenarios: per-widget minima and cut, lambda recovery distances, collision merge, dialog move, activity minima with the constructor excluded, handler table (including a class reaching nothing and `invoke(Object)`), no-`distanceTargets` document, malformed pairs skipped, source 3 | `tests/test_derive_mop_artifact.py`, synthetic documents plus the cryptoapp fixture | ~14 |
| Unit (pair rules) | INV-DRV-10 over random minima, both cuts | seeded random dicts, `_cut_weighed`, `_cut_nearest` and `_merge_minima` | ~3 |
| Unit (source read) | `digest_of_file` equals the SHA-256 of the bytes on a file longer than one chunk; a cache hit never calls `json.load` | `tests/test_derive_mop_artifact.py`, `tests/test_aperv_tool.py` | 2 |
| Memory | peak RSS of the derive path before and after D10 on one round-A document (`jtx`, 1.92 GB), one fresh process per run, on a copy | `/usr/bin/time -v`, a read-only script kept in the change folder | 2 runs |
| Unit (wire hygiene) | INV-DRV-06 amended: no `distanceTargets`, no signature-shaped string, only `hasTargetMethods` contains `Target` | extended existing test | 1 |
| Unit (tool) | cache by format; mapping count and keys; ten variants; `mopd_on_llm_off` properties lines | `tests/test_aperv_tool.py` | ~6 |
| Migration | the mapping sweep and the two new single-factor contrasts | `tests/migration/`, with `APE_REPO` at the Part B checkout | ~3 |
| Regression | every existing aperv-tool test, with the format-1 assertions (`test_derive_mop_artifact.py:388,400,1591`, `test_aperv_tool.py:1500,1547,1926`) moved to format 2 | `pytest --import-mode=importlib -o "addopts=" modules/aperv-tool/tests` | existing |
| Data | derive a sample of the Study 03 v2 gh120 documents (round A); check INV-DRV-10 (both cuts), `targets > 0`, and the share of activities in `mopActivitiesAugmented` before and after the exclusion; over all 92, measure the reaching methods with no pair, Compose vs View-only | `real_data_check.py` (re-run after D9 on the same 23 documents) and `reach_without_distance.py` in the change folder, run on copies; the originals are never written | 3 runs |

## Open Questions

- **Should `aperv-tool` also carry the flag-mode twin of `mopd_on_llm_90` (`mop_on_llm_90`)?** Today the only flag arm at dose 0.9 is the replication package's `e6_mop_on_llm_90`, and the only flag arm of this module under the LLM is `mop_on_llm_70`. A distance-versus-mark contrast under the LLM inside this module needs the twin. Not added, because the author asked for the distance arm only (2026-10-08).
- **Where the campaign turns the stamp on.** The replication-package side instruments the corpus. If it does not pass `--instrumentation-variant dexlib2 --stamp-handlers`, every stamp field is null and the jar falls back to the id key everywhere. The run reports this as `RUN_END.stampNodes == 0`.
