# Design: gh-tbd-gator-full-minified-horizon

## Context

The proposal carries the author's decisions of 2026-11-11 and his answers of the same day.

- **GATOR.** The full mode of the analysis document is written without whitespace. The distance horizon `TargetDistances.DIST_MAX = 10` becomes the client parameter `distMax`. The document records the horizon only when the parameter is passed. The value is an integer ≥ 1 with no upper bound, and an invalid value stops the run. The GATOR heap is not measured.
- **`rv-static-analysis`.** It exposes the parameter. It also regenerates a stored document whose recorded horizon differs from the requested one. That check reads only the start of the document. It does not compare output modes.
- **`aperv-tool`.** It takes from calibration v6 the parametrized cut of the derive, bounded by the document's horizon. It takes the weight ladder `mop_weights` → `ape.mopWeights` in place of `mop_weight_d1..d3`, and the 512m APE heap in every cell. It does not take the `cal` variant.
- **The MOP coin's ledger budget.** The four MOP variants (`mop`, `as_mop`, `as_mop_llm`, `mop_nolaunch`) stop stating `mop_coin_ledger_max_interactions: 2`, so the coin runs at the jar's default. The author decided this on 2026-11-11, and that it enters this change (D15).
- **`rv-tools` and `rv-android-core`.** The `ape` built-in sets the same 512m before it starts APE, so `aperv:base` and `ape` keep the same heap (the author's answer of 2026-11-11 in the review). The value, the property name and the set with its read-back live once, in rv-android-core.
- **No device run.** The review of 2026-11-11 took the device smoke out: no cell of either tool runs in this change. The change is checked by unit tests, by the GATOR runs, and by offline checks against the code before the change and against the source of the jar it pairs with.
- **Fixtures and coordination.** The `aperv-tool` copy of the cryptoapp fixture is refreshed. The aperv session is told about the `ape` repository's copy when the change closes.
- **Where.** The change is implemented in the worktree `workspace-rv/worktrees-gator/distmax`, on branch `wip/gator-distmax`, created from `modules` at `99572bc0`.

The code as it stands (read on 2026-11-11 at `99572bc0`):

- `JsonReportWriter.write` (`client/.../json/JsonReportWriter.java:104-107`) calls `w.setIndent("  ")` when `compact` is false. That is the only difference in serialisation between the modes. The `compact` flag also decides the `distancePairs` marker (`:130-137`) and, through the enricher, the pair reduction.
- `TargetDistances.DIST_MAX = 10` (`client/.../reach/TargetDistances.java:57`) is read in one place, `reverseBfs` (`:368-390`, the test `d == DIST_MAX`). `reverseBfs` serves both passes: the distance pass in `compute` (`:225`) and the path pass in `paths` (`:309`). The constant also appears in the class Javadoc (`:39`), in `JsonSchema.java:64`, in the log line `RvsecAnalysisClient.java:1657`, and in two tests (`TargetDistancesTest.java:73`, `TargetDistancesCompactTest.java:68-70`).
- `RvsecAnalysisClient` reads its boolean parameters with `Configs.getClientParamCode("<name>=")` (`:328-352`). It has one precedent of a parameter that stops the run: the `mopDir`/`targetsFile` mutex throws `IllegalStateException` at the start of `run` (`:108-113`). GATOR's `Main.main` catches nothing, so the exception ends the JVM with a non-zero status.
- `RVStaticAnalysisConfig` (`modules/rv-static-analysis/src/rv_static_analysis/config.py:114-145`) holds `skip_wtg`, `full_output`, `distance_paths` and `succ_depth: Optional[int]`. `get_tool_command` appends them at `:429-443`, and `__main__.py` declares the options at `:203-223` and maps them at `:388-396`.
- `StaticAnalyzer._execute_command` (`analysis/static/static_analysis.py:470-498`) reuses an existing `<apk_name>.json` unless `_disagreeing_recorded_key` (`:398-438`) finds another scope key. That check parses the whole document through `StaticAnalysisParser`: 2,258 ms on a 48 MB document, by its own docstring.
- Every reader of the document parses JSON. `read_analysis_document` (`rv_android_core/util/analysis_document.py`) uses `ijson` and returns the members as `json.loads` would. `StaticAnalysisParser` reads the members it names. The converter (`compact.py:234-250`) copies every member and inserts `distancePairs` before the first member of `_MEMBERS_AFTER_MARKER` (`distanceTargets`, `components`, …).
- `aperv-tool`'s `tool.py` (sha256 `5e75238c…`) and `derive_mop_artifact.py` (`42e8abf2…`) are byte for byte the files calibration v6 copied from the E7 pin (`rvsec-calibracao/infra/v6/harness/PROVENANCE.md`). Calibration v6 then edited its copies:
  - `86c3cf9`: the parametrized cut, the ladder and the `cal` variant;
  - `667c371`: the heap growth limit of the `cal` variant (D53).
  - Its tests are `tests/v6/test_harness_derive.py` (10 tests) and `tests/v6/test_harness_tool.py` (25 tests).
- **The jar.** `ape-rv.jar` is not versioned in rv-android: `64740c8f` dropped it, and the image builds it from the `ape` repository's default branch (`docker/rvandroid/Dockerfile:27-31`). The `ape` master (`a0fb5c16`, change `gh-tbd-mop-weights-list`) has the code of `e6d1be2b`. Its effects:
  - It reads `ape.mopWeights`, a list of 1 to 10 non-negative integers, and refuses 11 or more with `invalid_type`.
  - It refuses `ape.mopWeightD1..D3` with `retired_key`.
  - At the default ladder `500,400,300` it scores as the E7 jar does (`MopLadderE7EquivalenceTest`).
  - It changes only the `digest` of the MOP cells' `RUN_START` fixtures.
  - The file in the module directory of a checkout (`ape-rv.jar`, sha256 `591a94a8…`, 2026-10-19) is a local leftover outside git, and it only knows the per-level keys.
- **The F1 jar.** The `ape` branch `gh-tbd-mop-defaults-f1` (`a867e471`, a child of `a0fb5c16`, not merged on 2026-11-11) sets the defaults of four MOP keys to calibration v6's finalist F1 (`KeyOwnership.java:210-232`): `ape.mopWeights` `194,146,97` (3 levels, so the derive's cut stays 3), `ape.mopRetireAfter` 10, `ape.mopCoinLedgerMaxInteractions` 4 (1 at `a0fb5c16`, `:224`) and `ape.activityTriggerStagnationStep` 85. The cell fixtures `src/test/resources/cells/*.run_start.json` change only their `digest` between the two commits, and their `params` carry none of the four keys. The `ape` session reports that `a867e471` is final for `src/` and that its merge into the master will have the same `src/` tree.
- `tool.py` states `mop_coin_ledger_max_interactions: 2` (`MOP_COIN_LEDGER_MAX_INTERACTIONS`, `:121-125`) on `mop`, `as_mop`, `as_mop_llm` and `mop_nolaunch` (`:527`, `:545`, `:568-569`, `:582-583`). It entered in `c6865a73` (isolate-guidance-groups D18, 2026-10-19: after `e03igg2` the coin at 2 was the only arm above `ape` in misuses). No cell states the ladder, the retirement or the launcher cadence.

## Architecture

```
operator ── rv-static-analysis analyze|batch [--full-output] [--dist-max N]
               │  argparse: N must be an int ≥ 1, else exit 2 (GATOR not started)
               ▼
          RVStaticAnalysisConfig(dist_max=N)  (Pydantic, ge=1)
               │  StaticAnalyzer: stored <apk>.json? read its distMax from the top
               │    (stop at the first member after the scope block); ≠ requested → regenerate
               │  get_tool_command: … -clientParam distMax=N
               ▼
GATOR JVM ── RvsecAnalysisClient.run
               │  distMax(): absent → null; invalid → IllegalStateException (JVM exits ≠ 0)
               ├─► TargetDistances.compute(…, horizon)   horizon = distMax ?: DEFAULT_DIST_MAX
               ├─► distances.paths(…)                     same horizon
               └─► JsonReportWriter(enricher, compact, paths, distMax)   no indent in either mode
               ▼
          <apk_name>.json  (… class_defs_under_key, [distMax], [distancePairs], distanceTargets …)
               ▼
rv-platform ── ApeRVTool (aperv-tool)
               │  configure(): mop_weights "500;400;300" → (500, 400, 300); bad → ConfigurationError
               │  cut = max(DIST_WEIGHED_MAX, len(ladder))
               │  _derive_mop_artifact: cache <apk>.mop.json | <apk>.cut<c>.mop.json
               │     read_analysis_document(reduce(cut, DIST_K)) → refuse weighedMax < cut
               │     derive(document, cut) → refuse cut > horizon (distMax or 10)
               │  push artifact; ape.properties: ape.mopWeights=500,400,300
               │  Android.set_ape_heap_growth_limit: su 0 setprop dalvik.vm.heapgrowthlimit 512m;
               │     getprop must read 512m
               ▼
          app_process … ape-rv.jar (ape master after the gh-tbd-mop-defaults-f1 merge)

rv-platform ── APETool (rv-tools, `ape`)
               │  push ape.jar and ape.properties
               │  Android.set_ape_heap_growth_limit: the same call, the same 512m
               ▼
          app_process … ape.jar
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `RvsecAnalysisClient.parseDistMax(String)` | Read and check `-clientParam distMax=` | raw parameter | `Integer` or `null`; throws `IllegalStateException` |
| `TargetDistances.compute(…, int horizon)` (both overloads) | Distance pass bounded by `horizon` | call graph, targets, horizon | `TargetDistances` holding `horizon` |
| `TargetDistances.reverseBfs(…, int horizon)` | Reverse BFS stopping at `horizon`, for both passes | callers map, seed | vertex → distance |
| `JsonReportWriter(enricher, compact, paths, Integer distMax)` | Write both modes without whitespace | analysis state | `<apk_name>.json` |
| `JsonReportWriter.writeHeader(…)` | Write the members before `distanceTargets`: package, main activity, the scope members, `distMax` when not null, the marker in compact mode | a `JsonWriter` and plain values | the header tokens |
| `RVStaticAnalysisConfig.dist_max`, `__main__._positive_int` | Carry and bound the horizon | operator | `-clientParam distMax=N` |
| `StaticAnalyzer._recorded_dist_max(path)` | Read the stored document's horizon from its top | `<apk_name>.json` | `int`, or `None` when the top is unreadable |
| `derive(document, …, cut)` | Cut widget and handler lists at `d ≤ cut`; refuse a cut outside `[1, horizon]` | parsed document, cut | artifact dict |
| `ApeRVTool._derive_cut()` | max(`DIST_WEIGHED_MAX`, ladder length) | cell config | `int` |
| `ApeRVTool._derive_mop_artifact` | Cache by cut, reduce at the cut, refuse a document that cannot carry it | task | artifact path |
| `_parse_mop_weights` | Normalise the ladder | DSL string or list | `tuple[int, …]` |
| `Android.set_ape_heap_growth_limit` (rv-android-core) | Set and read back `dalvik.vm.heapgrowthlimit`, for `ApeRVTool` and `APETool` | tool name, device serial | none; raises `RVToolExecutionError` |

## Mapping: Spec → Implementation → Test

| Requirement / invariant | Implementation | Test |
|-------------|---------------|------|
| Distance Horizon Parameter | `TargetDistances` `horizon` field, `reverseBfs` argument, `DEFAULT_DIST_MAX` | `TargetDistancesTest` (pair at 11 with horizon 12, none with 10; paths at horizon 12), `TargetDistancesCompactTest`; the other callers of `compute` (`DistanceKeysEmissionTest`, `LambdaEdgesTest`, `TargetDistancesPathsTest`) pass the horizon |
| The default horizon 10, declared in three places (INV-ANA-99, INV-ANA-102, INV-APV-71) | `TargetDistances.DEFAULT_DIST_MAX`, `rv_static_analysis.config.DEFAULT_DIST_MAX`, `derive_mop_artifact.DEFAULT_DIST_MAX` | `tests/parity/test_distance_pair_constants.py`, extended to the three |
| An Invalid Distance Horizon Stops the Run, INV-ANA-100 | `RvsecAnalysisClient.parseDistMax` | `RvsecAnalysisClientDistMaxTest`; e2e run with `distMax=0`: exit ≠ 0, no file |
| The Document Records a Given Horizon, INV-ANA-99 | `JsonReportWriter.writeHeader`, which `write` calls; it takes no distance-pass input, so the member does not depend on `distanceTargets` | `JsonReportWriterHeaderTest`: member order in both modes, with and without `distMax`, no whitespace (`write` itself needs a Soot Scene, `DistancePairsMarkerTest:11-15`); e2e: the member order of the 5.3 and 5.4 documents |
| `rv-static-analysis` Passes the Distance Horizon | `config.py`, `__main__.py` | `tests/cli/test_dist_max.py` |
| A Stored Artefact Is Reused Only Under Its Own Horizon, INV-ANA-102 | `StaticAnalyzer._recorded_dist_max` + `_execute_command` | `tests/.../test_static_analysis_horizon_reuse.py`: reuse at equal horizon, regenerate at a different one, absent = 10, unreadable top, a document that cannot be opened, truncated document, other mode reused; `tests/integration/test_package_key_end_to_end.py`, whose patched `os.path.isfile` makes an absent document look present |
| Compact and Full Output Modes (MODIFIED), INV-ANA-86 | `JsonReportWriter.write` without `setIndent` | writer test: full output holds no `\n`; e2e: `experimento-gh125/compare_docs.py` between the current fixture and the new full document |
| INV-ANA-101 | default horizon = 10, member only when given | e2e: compact without parameter vs the jar before the change; `distMax=10` vs no parameter |
| Converter keeps `distMax`, INV-ANA-87 | `compact.py` unchanged | `test_compact_converter.py`; e2e: GATOR compact with `distMax=15` vs the converted GATOR full |
| INV-ANA-32 | `JsonSchema.Keys.DIST_MAX`, `_JK.dist_max` | `JsonSchemaKeysTest`, `tests/parity/test_json_keys.py` |
| The Weight Ladder Setting | `_parse_mop_weights`, `APERV_PROPERTY_MAPPING`, `_push_properties` | ported from `tests/v6/test_harness_tool.py`: DSL and list forms, the malformed values, commas in `ape.properties`, `mop_weight_d1` refused |
| ape.properties Composition (MODIFIED): 64 entries | `APERV_PROPERTY_MAPPING` | `test_aperv_tool.py:1210` (count 64) and `:1246-1256` (`mop_weights` in, `mop_weight_d1..d3` out); migration tier: `test_mapping_sweep.py` against the `ape` master's source |
| Weighed Cut Follows the Weight Ladder, INV-APV-70, INV-APV-71 | `_derive_cut`, `derive(cut=)`, `_require_cut(cut, horizon)`, the `distMax` type check | ported from `tests/v6/test_harness_derive.py`, plus: horizon from `distMax`, cut 6 refused at `distMax: 5`, cut 11 refused without `distMax`, a `distMax` of `"15"`, `true` or `0` refused; offline evidence: at cut 3 the old and new derive write the same bytes (task 7.1) |
| A Document That Cannot Carry the Cut Is Refused, INV-APV-71 | `_recorded_weighed_max`, the check in `_derive_mop_artifact` | ported tool tests (compact under a deeper cut, malformed marker) |
| The Cached Artifact Is Named by Its Cut, INV-APV-72 | `_artifact_name` | ported tool tests |
| APE Heap Growth Limit, INV-APV-73 | `Android.set_ape_heap_growth_limit`, called by `ApeRVTool` in every cell before the main command | rv-android-core test: setprop before getprop, a read-back other than `512m` raises; aperv-tool test: every cell calls it after the pushes and before the main command, and a raise stops the command |
| APE Built-in Starts APE With the APE-RV Heap Growth Limit, INV-TOOL-30 | `APETool.execute_tool_specific_logic` calls the same method after the pushes | `tests/builtin/test_ape_tool.py`: the call comes after both pushes and before the command; a raise stops the command |
| Derived MOP Artifact Generation and Caching (MODIFIED) | as above | existing tests stay green at the default cut |
| MOP Artifact Projection and Handler Table (MODIFIED) | `_cut_weighed`, `_cut_events`, `_emit_widgets`, `_emit_handlers` take `cut` | the scenario "a deeper cut keeps the farther targets" |
| ApeRVTool Cell Variants (MODIFIED), ApeRVTool Configuration (MODIFIED): no MOP cell states the ledger budget (D15) | `get_variants()` without `MOP_COIN_LEDGER_MAX_INTERACTIONS`; the mapping entry stays | `test_aperv_tool.py`: the overrides of every variant and the `ape.properties` of the MOP cells and of `mop_nolaunch`; offline evidence: old and new `tool.py` differ only by the ledger line of the four MOP variants (task 7.3) |
| Cell Configuration Matches the Jar's Cell Echo (MODIFIED) | `get_variants()`, `_push_properties` | migration tier `test_cells.py`: `TestLedgerBudget` (no MOP variant states the key, the jar's default is `4`, no MOP fixture carries it, and the jar's default ladder has at most `DIST_WEIGHED_MAX` levels), run against `a867e471` and, as the negative check, against `a0fb5c16` (tasks 7.4 and 7.5) |
| Pairing of `tool.py` with the F1 jar (D13, D15) | `APERV_PROPERTY_MAPPING`, `get_variants()`, `_push_properties` | migration tier with `APE_REPO` on the source of `a867e471`: the cell gate (`test_cells.py`) and the mapping sweep (task 7.4); against the master `a0fb5c16` before the k removal (task 7.2) |

## Goals / Non-Goals

**Goals:**
- Full-mode documents without whitespace and with the same content.
- A horizon chosen per run, recorded in the document when chosen, with a default that leaves the default document unchanged, and no silent fallback for an invalid one.
- A stored document never answers a run that asked for another horizon.
- An `aperv-tool` that can derive and run at the cut a ladder asks for, refuses a document that cannot carry that cut, runs the MOP cells at the jar's calibrated defaults, and pairs with the F1 jar.

**Non-Goals:**
- Choosing the horizon or the ladder of a future analysis or campaign.
- Measuring the GATOR heap of a larger horizon.
- The `cal` variant, the calibration itself, and the defaults `DIST_WEIGHED_MAX = DIST_K = 3` (INV-ANA-88 is untouched).
- Reusing a stored document across output modes, `rv-experiment`, the Docker image, any corpus.

## Decisions

**D1. The indent goes; the `compact` flag stays.** The only edit to serialisation is deleting the `if (!compact) w.setIndent("  ")` block. The flag keeps deciding the marker and the reduction. The alternative was a third mode that keeps the indent, for byte-reproduction of published documents. It was rejected: the author decided that content reproduction is enough.

**D2. One name, `distMax`, at every layer.** The client parameter is `distMax=N`, the document member `distMax`, the Python field `dist_max` and the option `--dist-max`. The Java constant becomes `DEFAULT_DIST_MAX`, renamed rather than aliased (P3). "Horizon" stays a word of the prose.

**D3. The horizon is state of `TargetDistances`.** Both `compute` overloads take `int horizon` and store it in a final field. `reverseBfs` takes it as an argument, and `paths` passes the field, so the path pass repeats the distance pass's searches (INV-ANA-91 and INV-ANA-93 hold for any horizon). A mutable static set by the client was rejected: it would leak between unit tests and make the passes depend on call order.

**D4. The client checks the parameter first thing in `run`.** The package-private static `parseDistMax(String)` returns `null` when the parameter is absent. It returns the value when `Integer.parseInt` accepts it and it is ≥ 1, and throws `IllegalStateException("distMax must be an integer >= 1, got '<raw>'")` otherwise. `run` calls it once, before the mutex check. The client starts only after GATOR has loaded the APK and built the call graph. Checking in `sootandroid`'s `Main.parseArgs` would fail faster, but it would teach the framework one client's parameter. `rv-static-analysis` refuses the value before GATOR starts, so only direct callers pay the late failure. `+5` parses as 5 and is kept.

**D5. `distMax` goes right after `class_defs_under_key`.** In compact mode it comes before `distancePairs`, in full mode before `distanceTargets`. The writer takes `Integer distMax` and writes nothing for `null`. Placed there, the converter needs no change: `_with_marker` inserts `distancePairs` before `distanceTargets` (or before the first later member when the distance pass failed), which is after `distMax`. So `compact(full(distMax=N))` keeps GATOR's member order (INV-ANA-87).

**D6. Python validates at both of its boundaries.** `dist_max: Optional[int] = Field(default=None, ge=1, description=…)` refuses 0 or a negative value. `--dist-max` uses the argparse type `_positive_int`, which raises `argparse.ArgumentTypeError` for a non-integer or a value below 1, so the CLI exits with status 2 before building a config.

**D7. The reference fixture is compared, then regenerated, and the `aperv-tool` copy follows.** `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` is a full-mode document of the current jar (MANIFEST `regenerated_against_jar_sha256: 434e8614…`). Before it is replaced, the new jar's full document of `cryptoapp.apk` is compared with it by content (`experimento-gh125/compare_docs.py`: member order, each member equal after parsing, `transitions` as a multiset). That comparison is the evidence for INV-ANA-86. The document compared is produced by the fixture's own recipe, the one of `scripts/check_signature_file_subset.py`: `jca` specs, default SPARK, no `cgDelegation`, no `codePackage` (`experimento-gtdistmax/scripts/run_fixture_recipe.sh`). The campaign settings of D8 write a different document. Then the fixture is regenerated by the recipe the MANIFEST cites, and the MANIFEST pins are refreshed. `modules/aperv-tool/tests/fixtures/cryptoapp.apk.json` is copied from it byte for byte, and the sha256 its README states is updated.

**D8. The evidence of the end-to-end runs lives in `experimento-gtdistmax/`.** It follows `experimento-gh125/` and `experimento-gtpaths/`. It holds the jar hashes, the runs on `cryptoapp.apk` and `org.musicbrainz.picard.barcodescanner_38.apk` with and without `distMax`, the comparisons, the offline checks of the `aperv-tool` port (group 7), and a `RELATORIO.md`. The second app is barcodescanner because its pairs reach the horizon: its E6 full document has 32 pairs at `d = 10`, and 2 widget or handler pairs at `d = 5` under a cut of 6. GATOR analysed it in 118 s in September. `org.cry.otp_31`, the first choice, stops at `d = 3`, so a horizon of 15 or a deeper cut would change nothing in it. The GATOR runs use the campaign's settings (jca_android, SPARK, `cgDelegation=true`, `RV_STRIP_BUILD_TYPE_SUFFIX=true` where the APK needs it), except the fixture comparison and regeneration, which use the fixture's recipe (D7).

**D9. The `aperv-tool` part is the calibration diff, minus `cal`, plus the horizon.** The starting point is `git -C rvsec-calibracao diff e54e6b5 667c371 -- infra/v6/harness/`. It applies to this repository's files unchanged, because the copies began from the same bytes. What is taken:
- the cut parameter of the derive and its threading through `_cut_weighed`, `_cut_events`, `_emit_widgets` and `_emit_handlers`;
- `_parse_mop_weights`, the mapping `mop_weights` → `ape.mopWeights` and the removal of `mop_weight_d1..d3`;
- `_derive_cut`, `_artifact_name`, `_recorded_weighed_max` and the refusal of a compact document under a deeper cut;
- `PairPolicy.reduce(cut, DIST_K)`;
- `_set_heap_growth_limit`, which moves to rv-android-core as `Android.set_ape_heap_growth_limit` so the `ape` built-in can make the same call (D12).

What is left out: the `cal` variant, the `heap_growth_limit` orchestration key with its validation (D12), and the "Calibration v6 copy" docstring paragraph and per-hunk comments (P4). Their content is rewritten as current-state comments.

Of the 35 calibration tests, 14 test behaviour, and those are ported to `modules/aperv-tool/tests/`. The others cannot be ported as they are:
- some test the `cal` variant or the `heap_growth_limit` key, which are not taken;
- some read `jar_keys.json`;
- some compare with a pinned copy of the E7 code, obtained by `git show` of the calibration's pin commit or from a mounted file.

The pinned comparisons become one-time evidence in `experimento-gtdistmax/` (task 7.1). The old code comes from `git show 99572bc0:`. At cut 3, the old and the new derive must write the same bytes. The old and the new `tool.py` must write the same `ape.properties` for every variant, except the line `ape.mopCoinLedgerMaxInteractions=2`, which the old one writes for the four MOP variants and the new one does not (D15).

**D10. The derive's upper bound is the document's horizon.** Calibration v6 bounded the cut by `CUT_MAX = 10`, "GATOR's BFS horizon". Here `derive()` reads the horizon from the document: `document.get("distMax", DEFAULT_DIST_MAX)`, where `DEFAULT_DIST_MAX = 10` is a derive constant whose comment names `TargetDistances.DEFAULT_DIST_MAX` and INV-ANA-99. `_require_cut(cut, horizon)` raises `DerivationError` naming both values when the cut is not an integer in `[1, horizon]`. `CUT_MAX` does not exist. A `distMax` that is not an `int` ≥ 1 (a `bool` excluded) raises `DerivationError` naming it, checked right after the check that the document is a dict, as the derive does for any section of the wrong type. Without that check a string would reach the comparison and raise `TypeError`. A consequence: a document analysed with `distMax` below 3 refuses the default cut 3. That is the rule the author chose ("no silent truncation"), and such a document has to be re-analysed with a horizon of at least 3 to feed a MOP cell.

**D11. The ladder's length limit is the jar's, 10, and does not follow the horizon.** The jar refuses a ladder of 11 elements (`RunSpecAbortTest.aMalformedLadderAbortsAsATypeErrorOnTheKey`), so `MOP_WEIGHTS_MAX_LEVELS = 10` stays as calibration v6 has it. The effective cut is at most min(10, horizon). A horizon above 10 serves offline readers and the `activityDist` ranking, not the weighed lists.

**D12. The heap limit is one constant and one call, shared by `aperv` and `ape`.** The author chose every aperv cell. Calibration v6 needed a per-variant key because only `cal` carried the limit. Here no cell differs, so the key, its validation and its listing in `APERV_ORCHESTRATION_KEYS` are not taken (P1).

In the review of 2026-11-11 the author gave the `ape` built-in the same 512m. His rule of 2026-10-21 is that `aperv:base` stays the APE, and the two tools already share the teardown grace through one constant (`tools` INV-TOOL-27). Two tools now set the same property to the same value, so the setting lives once, in rv-android-core:
- `APE_HEAP_GROWTH_LIMIT = "512m"` and `HEAP_GROWTH_LIMIT_PROPERTY = "dalvik.vm.heapgrowthlimit"` are in `rv_android_core/constants.py`, beside `TOOL_TEARDOWN_GRACE_S`;
- `Android.set_ape_heap_growth_limit(tool_name, device_name)` (classmethod, `rv_android_core/util/android/android.py`, beside `install_apk` and `grant_permissions`) runs the setprop as root and the getprop, and raises `RVToolExecutionError` naming the tool and the value read back.

`ApeRVTool.execute_tool_specific_logic` calls it after the pushes and before `_build_main_command`. `APETool.execute_tool_specific_logic` calls it after `_push_ape_properties` and before `_build_ape_shell_command`. Both depend on rv-android-core already, and neither depends on the other.

Calibration v6 established the mechanism (D53): an `app_process` VM option left the limit at 192m, while the root `setprop` raised it and the jar logged `Max: 512 MB`. The emulator image is a `userdebug` build with `su`. The property is not persistent and lasts until the emulator stops. The app under test forks from a zygote that read the property at boot, so its heap is expected not to change; calibration v6 records that as an inference from the mechanism, not a measurement (its design, D53 implementation notes).

**D13. The jar is the F1 jar, and the pairing is checked against its source.** The repository carries no jar to replace. Production pairs through the image build (`Dockerfile:27-31`), which compiles the `ape` master. With the k removal (D15), this `tool.py` pairs with the jar of `gh-tbd-mop-defaults-f1` (`a867e471`), which reaches the master by the `ape` session's merge. No jar is built in this change. The pairing is checked by `aperv-tool`'s migration tier, which reads the Java source, not a jar (`tests/migration/jar_tables.py:107-133`). Its cell gate (`test_cells.py`) checks each cell of `get_variants()` against the jar's `RUN_START` fixtures. Its mapping sweep (`test_mapping_sweep.py`) checks every mapped key against the jar's key tables. The tier ran with `APE_REPO` on the master `a0fb5c16` before the k removal (task 7.2). After it, it runs on the source of `a867e471`, extracted with `git -C …/ape archive a867e471` into `experimento-gtdistmax/ape-f1/`, so the `ape` checkout stays on its master (task 7.4). Its ledger test runs once more against `a0fb5c16`, where it must fail on the default 1: that failure is the evidence that the tier tells the two jars apart.

On 2026-11-11, before this change, the tier against `a0fb5c16` failed 11 of 57 tests:
- 2 are the per-level keys `mop_weight_d1..d3`, which this change removes;
- 7 are about `APE_FIXES`;
- 1 is the retired key `llmPercentageNoSubstrate`;
- 1 is the vocabulary size (123 ≠ 125).

The 9 that this change does not touch are recorded, not fixed. On `a867e471` they are compared with this list, and any failure outside it is reported to the author before group 9.

**D15. The MOP cells state no ledger budget.** `tool.py` deletes `MOP_COIN_LEDGER_MAX_INTERACTIONS` and the override `mop_coin_ledger_max_interactions: 2` of `mop`, `as_mop`, `as_mop_llm` and `mop_nolaunch`. `mop_nolaunch` keeps `activity_trigger_enabled: False`, still the `mop` cell's overrides plus one key. The mapping entry `mop_coin_ledger_max_interactions` → `ape.mopCoinLedgerMaxInteractions` stays, because the jar accepts the key and the DSL uses it for ablations.

How the jar resolves an unstated key (`ape` `RunSpec.java`, the same logic at `a0fb5c16` and `a867e471`): every key's effective value is the explicit one or the `KeyOwnership` default, and the plan keeps the keys of the mounted features. `MopParams.coinLedgerMaxInteractions()` returns `has(key) ? integer(key) : 1` (`:1105-1108`), where `has` is true whenever `MOP_COIN` is mounted, so the `1` covers only an absent coin. With the key unstated, a MOP cell runs the jar's default: 4 on `a867e471`, 1 on `a0fb5c16`.

Why it pairs with F1 only: on the F1 jar, keeping the override would run F1's ladder, retirement and cadence with the ledger at 2, a combination calibration v6 never measured; removing it gives the calibrated 4. On `a0fb5c16` alone, removing it gives 1, neither E7's 2 nor F1's 4. So this change and the merge of `gh-tbd-mop-defaults-f1` into the `ape` master must reach the same image build. The `ape` session merges and pushes after this change's commit; the order of the merges and pushes is the author's.

A side effect, in the cells' favour: a DSL ablation `mop_coin_percentage=0` on a MOP cell aborts today, because the stated ledger budget is a non-neutral value of an absent feature. With the key unstated it resolves.

The alternatives were to keep the override, which is the unmeasured combination above, or to set it to 4 on this side, which states a calibrated value twice and pins the harness to one calibration. The author's decision of 2026-11-11 is that the MOP cells run the jar's defaults, and that the removal enters this change: the MODIFIED blocks of "ApeRVTool Execution Flow" and "ape.properties Composition" are already here and would conflict at archive between two concurrent changes, and both edits ship in one image anyway.

**D14. The stored document's horizon is read from its top.** `_recorded_dist_max(path)` walks `ijson.parse` events on the open file. It returns the integer value of the top-level key `distMax` when it meets it. It returns `DEFAULT_DIST_MAX` (10, a constant of `rv_static_analysis/config.py`, pinned to the Java one by the parity test) when it first meets a top-level key in `{distancePairs, distanceTargets, components, reachability, windows, transitions, complete}`. It returns `None` when the file cannot be opened (gone since the existence check, or not readable), is empty, or stops being JSON before either happens; the caller then regenerates with a warning. The reading costs one `ijson` buffer of at most 64 KiB, whatever the document's size. A document cut by a timeout still has an intact top, because GATOR writes the scope members first.

`_execute_command` runs this check before the existing scope-key check, which parses the whole document. When the horizons differ, that parse is skipped. The reuse is kept only when both checks pass. `_stale_reason` runs the two checks in that order and returns why a stored document cannot answer the run, or `None` when it can. The alternative was to carry `distMax` through `StaticAnalysisParser` into `StaticAnalysisData` (`rv-android-core`). It was rejected because it costs a full parse per check and widens a model that several modules share (the author's choice, 2026-11-11).

## API Design

### `RvsecAnalysisClient.parseDistMax(String param) -> Integer` (package-private, static)
- **Postconditions**: `null` for a `null` param; otherwise a value ≥ 1.
- **Errors**: `IllegalStateException` naming `distMax` and the raw value, when `Integer.parseInt` throws or the value is < 1.

### `TargetDistances.compute(…, int horizon)` (both overloads)
- **Preconditions**: `horizon ≥ 1`; otherwise `IllegalArgumentException`, since a test can call it directly.
- **Postconditions**: every recorded pair has `0 ≤ d ≤ horizon`; `horizon()` returns it; `paths` uses it.

### `JsonReportWriter(ReachabilityEnricher enricher, boolean compact, DistancePaths paths, Integer distMax)`
- **Postconditions**: `write` emits no whitespace between tokens in either mode, and emits `"distMax":N` right after `class_defs_under_key` when `distMax != null`.

### `JsonReportWriter.writeHeader(JsonWriter w, String appPackage, String mainActivityName, Map<String, Object> metadata, boolean compact, Integer distMax)` (package-private, static)
- Writes `package`, `mainActivity`, `codePackage`, `codePackageSource`, `class_defs_under_key`, then `distMax` when not `null`, then the `distancePairs` marker when `compact`. `write` calls it right after `beginObject()`, with the enricher's `topLevelMetadata()`. It takes no Soot type, so a unit test can drive it.

### `RVStaticAnalysisConfig.dist_max: Optional[int] = Field(default=None, ge=1)`
- `get_tool_command` appends `["-clientParam", f"distMax={self.dist_max}"]` when not `None`.

### `StaticAnalyzer._recorded_dist_max(result_file: str) -> Optional[int]`
- Returns the recorded horizon (10 when absent), or `None` when the top of the file cannot be read.

### `derive(document: dict, source_file: str = "", source_digest: str = "", cut: int = DIST_WEIGHED_MAX) -> dict`
- **Preconditions**: `cut` is an `int` (not a `bool`) in `[1, document.get("distMax", DEFAULT_DIST_MAX)]`.
- **Postconditions**: widget and handler lists hold every pair at `d ≤ cut`; `activityDist` holds the `DIST_K` nearest; at `cut = DIST_WEIGHED_MAX` the artifact is byte-identical to today's.
- **Errors**: `DerivationError` naming the cut and the horizon.

### `ApeRVTool` additions
- `_parse_mop_weights(value) -> tuple[int, ...]`: 1 to 10 non-negative ints from `"a;b;c"` or a list/tuple; `ConfigurationError` otherwise.
- `_derive_cut() -> int`: max(`DIST_WEIGHED_MAX`, ladder length), `DIST_WEIGHED_MAX` without a ladder.
- `_artifact_name(apk_name, cut) -> str`: `<apk>.mop.json` at 3, `<apk>.cut<c>.mop.json` otherwise.
- `_recorded_weighed_max(document, source_path) -> int | None`: the marker's `weighedMax`, `None` without a marker; `RVToolExecutionError` for a malformed one.

### `Android.set_ape_heap_growth_limit(tool_name: str, device_name: str = "emulator-5554") -> None` (rv-android-core, classmethod)
- Runs `adb -s <device_name> shell su 0 setprop dalvik.vm.heapgrowthlimit 512m`, then `getprop`, both with the values of `rv_android_core.constants`.
- **Errors**: `RVToolExecutionError(tool_name=tool_name)` when the set fails or the read-back is not `512m`, naming the value read back.

## Data Flow

The horizon flows from the operator through the Python config and the GATOR command line to `RvsecAnalysisClient`. The client hands it to `TargetDistances` (both passes) and to `JsonReportWriter` (the member). From the document it is read three ways:
- `StaticAnalyzer` reads it, to decide whether a stored document answers the run;
- `aperv-tool`'s derive reads it, as the cut's upper bound;
- people and offline scripts read it, to interpret a missing pair.

`StaticAnalysisParser` ignores it, and the parsed-copy cache and the converter copy it.

The ladder flows from the cell's overrides through `configure()` to two places: `ape.properties` (`ape.mopWeights`) and the derive's cut. The jar applies the same cut again when it loads the artifact (`ape` D17), so the two sides cannot disagree on the depth when the cell states a ladder. A cell that states none, which is every cell (D15), derives at `DIST_WEIGHED_MAX` while the jar weighs its own default ladder; a default ladder longer than 3 would leave its deeper levels without pairs and raise nothing. The migration tier therefore checks that the jar's default `ape.mopWeights` has at most `DIST_WEIGHED_MAX` levels (3 on `a867e471` and on `a0fb5c16`).

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| argparse usage error, exit 2 | `--dist-max 0` / `ten` | refuse before any work | pass an integer ≥ 1 |
| `pydantic.ValidationError` | `RVStaticAnalysisConfig(dist_max=0)` | refuse at construction | same |
| `IllegalStateException`, JVM exit ≠ 0, no document | direct jar call with an invalid `distMax` | abort before the client computes anything | same |
| warning + regeneration | stored document of another horizon, or an unreadable top | regenerate | none needed |
| `ConfigurationError` | malformed `mop_weights`; an override `mop_weight_d1..d3` | refuse in `configure()`, before the device | write the ladder as `a;b;c` |
| `RVToolExecutionError` | compact document under a deeper cut; malformed marker; cut above the horizon (`DerivationError` wrapped) | refuse, write and push nothing | re-analyse with `--full-output` and a large enough `--dist-max` |
| `RVToolExecutionError` (`aperv` or `ape`) | `setprop` fails or the limit does not read back as `512m` | refuse before the launch | check that the AVD is a `userdebug` build with `su` |
| `DerivationError` (wrapped as `RVToolExecutionError`) | a document whose `distMax` is not an integer ≥ 1 | refuse, write and push nothing | re-analyse the APK |
| `OutOfMemoryError` (GATOR) | a large horizon on a large app | not handled | rerun with more heap or a smaller horizon |

## Risks / Trade-offs

- [An offline script that splits the full document by lines] → none is known in the workspace. The proposal marks the change **BREAKING** so the replication package's readers can be checked there.
- [A full document no longer reproduces the bytes of a published one] → the author accepted content reproduction. `compare_docs.py` is the comparison to use.
- [The 512m heap changes the GC of every aperv and ape run relative to E7, which ran at 192m] → the author chose it for every aperv cell and for `ape`. Calibration v6 judged that it changes the GC, not the agent's logic (its own inference), and the cell echo does not depend on it. Both arms of a comparison change alike.
- [The setprop has not run on a device in this change] → unit tests check the order of the commands and the refusal; calibration v6 ran the same setprop on the campaign AVD (D53). The first device run is the smoke of the next campaign, where a failure aborts every aperv and ape task before it explores, so it cannot pass unnoticed.
- [The F1 jar and this `tool.py` must ship together] → a `tool.py` from before this change only writes the retired keys when an override asks for them, so default cells keep running with the new jar. An override of `mop_weight_d1..d3` aborts at resolution with `retired_key`. After this change an old jar would abort on `ape.mopWeights` when a ladder is passed. The gate is the migration tier run against the F1 source (D13, task 7.4).
- [This `tool.py` with the jar of `a0fb5c16` runs the ledger at 1, and the old `tool.py` with the F1 jar runs it at 2 under F1's other defaults (D15)] → neither aborts, so no run would show it. The migration tier's ledger test fails on any jar whose default is not 4 (task 7.4). This change's commit and the `ape` merge of `gh-tbd-mop-defaults-f1` reach the same image build, and no image is built between the two pushes; the order of the merges and pushes is the author's.
- [Campaign analysis that compares an arm's declared parameters with `RUN_START.params`] → `runspec.attribution_evidence` compares the manifest's `params` with the header's. The jar records a non-default ladder as a JSON array. A manifest that declares the DSL string `"500;400;300"` would not compare equal. No campaign uses a non-default ladder today, and the campaign-analysis code is outside this change.
- [GATOR heap grows with the horizon] → not measured (author's decision). The operator chooses `-Xmx` with the horizon, within the host budget of about 80 GB for concurrent JVMs.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | horizon in both passes; parameter parsing; header member order; the other callers of `compute` | JUnit on string vertices and on `writeHeader` | ~10 |
| Unit (Python, rv-static-analysis) | option, field bound, command, converter pass-through, parser indifference, horizon reuse check | pytest with `--import-mode=importlib -o "addopts="` | ~14 |
| Unit (Python, aperv-tool) | derive cut and horizon bound; malformed `distMax`; ladder; refusals; cache name; mapping count; the heap call in every cell | the 14 behavioural calibration tests, plus the horizon, `distMax` and mapping cases | ~25 |
| Unit (Python, rv-android-core and rv-tools) | the set and read-back, and its refusal; the `ape` built-in calls it after the pushes and before the command | pytest, `Command` mocked | ~4 |
| Parity | `JsonSchema.Keys` = `_JK`; INV-ANA-88 constants and the default horizon in three places; freshness and reachability parity on the regenerated fixture | the whole `tests/parity` suite (~4 min) | existing + 1 |
| End-to-end | INV-ANA-86 by content, INV-ANA-101, INV-ANA-87 with `distMax=15`, invalid value aborts, stored-document reuse by horizon | GATOR on `cryptoapp.apk` and `org.musicbrainz.picard.barcodescanner_38.apk`, evidence in `experimento-gtdistmax/` | ~10 runs |
| Offline, `aperv-tool` port | old and new derive at cut 3 write the same bytes; old and new `tool.py` write the same `ape.properties` for every variant, but for the ledger line of the four MOP variants; the migration tier against the `ape` master's source and then against the F1 source, and its ledger test against both | `git show 99572bc0:`, `APE_REPO`, `git archive a867e471` | 4 checks |

No device run is part of this change. The end-to-end runs and the offline checks come before lint, verify and review.

## Open Questions

None. The four that the first version of this design listed were answered by the author on 2026-11-11:
1. The cache regenerates a stored document whose horizon differs, but not one of the other output mode.
2. The `aperv-tool` copy of the fixture is refreshed.
3. The change is implemented in a worktree.
4. The aperv session is told about the `ape` repository's fixture when the change closes.

The review of the same day added two answers:
5. No device run: the smoke with aperv cells was taken out.
6. The `ape` built-in gets the same 512m (D12).

During the apply, the same day:
7. The removal of the ledger override enters this change (D15).

## Main-spec edits outside the requirements (by hand, at archive)

The archive sync merges the requirement blocks of `specs/analysis/spec.md`, `specs/aperv/spec.md` and `specs/tools/spec.md`. It does not touch a main spec's Data Contracts, Side-Effects or Invariants, so these edits are made by hand in the same commit as the sync. They are given by their text, because the line numbers move. Before appending, grep the repository for every new INV number below. On 2026-11-11 the highest in use were INV-ANA-98, INV-APV-69, INV-DRV-11 and INV-TOOL-29.

### `openspec/specs/analysis/spec.md`

**Data Contracts — Input.** After the `distancePaths` lines, add:

> - `-clientParam distMax=<N>` — GATOR client parameter, the horizon of the distance searches. Absent: 10. Present: `N` SHALL be a value `Integer.parseInt` accepts and SHALL be ≥ 1, otherwise the client aborts (source: `RVStaticAnalysisConfig.get_tool_command` in `modules/rv-static-analysis/src/rv_static_analysis/config.py`, or a direct caller of the GATOR jar)
> - `RVStaticAnalysisConfig.dist_max: Optional[int] = None`, constrained to `≥ 1`, and `--dist-max N` on the `analyze` and `batch` subcommands (source: the operator)

**Data Contracts — Output.** Replace the `targetDistances` line and the full-mode line with:

> - `reachability[].methods[].targetDistances: list[[int, int]]` — in full mode, every pair: `[i, d]`, `i` an index into `distanceTargets`, `1 ≤ d ≤ distMax` (10 when the document carries no `distMax`) for a method that is not itself `c`, and `[i, 0]` for `c` itself; sorted by `i`; the key is omitted when the list would be empty (destination: same). In compact mode (the default) the list is reduced per INV-ANA-85.
> - `<apk_name>.json` in full mode — the document without whitespace, with the members, member order and values of the indented document the client wrote before gh-tbd-gator-full-minified-horizon; the same `transitions` edges, whose order follows identity-hash iteration (INV-ANA-86) (destination: same)

and add, after the compact-mode line:

> - `distMax: int` — top-level, only when the run was given `-clientParam distMax=N`: the value `N`, written right after `class_defs_under_key`, so before `distancePairs` in compact mode and before `distanceTargets` in full mode, in both writes of the run (INV-ANA-99) (destination: offline readers of the document, `StaticAnalyzer`'s reuse check, the `aperv-tool` derive, `rv-static-analysis compact`)

**Data Contracts — Error.** Add:

> - `IllegalStateException` from `RvsecAnalysisClient.run`, naming `distMax` and its value, when `distMax` is present and is not an integer ≥ 1; thrown before the client computes or writes anything, it ends the GATOR JVM with a non-zero status and no document (INV-ANA-100)
> - `rv-static-analysis analyze|batch --dist-max N` with `N` not an integer ≥ 1: argparse usage error, exit status 2, GATOR not started; `RVStaticAnalysisConfig(dist_max=N)` with `N < 1`: `pydantic.ValidationError`

**Side-Effects.** Replace the `File System (analysis cache)` line with:

> - **File System (analysis cache)**: a stored artefact whose recorded key differs from the run's effective key (INV-ANA-70), or whose recorded horizon differs from the run's requested one or cannot be read (INV-ANA-102), is regenerated rather than reused; `--force` discards it before the analysis runs

**Invariants.** Replace INV-ANA-73 and INV-ANA-86, and append INV-ANA-99 to INV-ANA-102 after INV-ANA-98:

> - **INV-ANA-73**: Each distance search MUST be seeded by exactly one app method: a member of C (the app methods in the `directlyReachesTarget` set) or of B. Library methods MUST NOT seed it. `d(t, t) = 0`, `d ≤ distMax`, the run's horizon (`TargetDistances.DEFAULT_DIST_MAX = 10` when the run has no `distMax` parameter), and a method absent from a target's search has no pair for that target.
> - **INV-ANA-86**: In full mode the document SHALL contain no whitespace between tokens (Gson `JsonWriter` with no indent set), and SHALL hold the content of the indented document the client wrote for the same analysis state before gh-tbd-gator-full-minified-horizon: parsed, the two SHALL have the same top-level members in the same order and equal values up to the `transitions` member. Its `transitions` SHALL hold the same edges with the same node ids, and it SHALL NOT carry `distancePairs`. The order of the `transitions` edges follows identity-hash iteration over the WTG edges, which a change in the client's code can move; INV-ANA-79 handles the same phenomenon by comparing node ids by content. In compact mode the document SHALL carry `distancePairs` with the values of `COMPACT_WEIGHED_MAX` and `COMPACT_K`, in both the pre-WTG write and the final write.
> - **INV-ANA-99**: A document SHALL carry the top-level member `distMax` if and only if its run was given the client parameter `distMax`, and its value SHALL be the parameter's value. The member SHALL be in both writes of the run and in both output modes, also when the distance pass failed and `distanceTargets` is absent. A document without `distMax` was computed with the horizon `DEFAULT_DIST_MAX = 10`.
> - **INV-ANA-100**: When the client parameter `distMax` is present and its value is not an integer ≥ 1, the client SHALL NOT compute distances with `DEFAULT_DIST_MAX` or any other horizon in its place: the GATOR JVM SHALL exit with a non-zero status, and the run SHALL write no document.
> - **INV-ANA-101**: For the same analysis state, a run without `distMax` SHALL write, in compact mode, the content of the document written before gh-tbd-gator-full-minified-horizon, and in full mode the content INV-ANA-86 states. A run given `distMax=10` SHALL write the same content plus the member `distMax: 10`. In both comparisons the `transitions` edges SHALL be the same, but their order follows identity-hash iteration and may differ (INV-ANA-86), and window and widget node ids are compared by content (INV-ANA-79).
> - **INV-ANA-102**: `StaticAnalyzer` SHALL NOT reuse a stored `<apk_name>.json` whose recorded horizon (`distMax`, 10 when absent) differs from the run's requested horizon (`dist_max`, 10 when `None`), nor one whose top-level members before the first post-scope member cannot be read. The check SHALL read no further than the first top-level member after the scope block.

### `openspec/specs/aperv/spec.md`

**Purpose.** In the paragraph on behaviour groups, replace the sentence `The one exception is the MOP coin's ledger budget, which the three MOP cells set to 2 on this side while the jar's default stays 1 (author's decision, 2026-10-19).` with:

> No cell states a MOP parameter: the coin's ledger budget, the weight ladder, the retirement and the launcher cadence take the jar's defaults, which on the paired jar are calibration v6's finalist F1 (author's decision, 2026-11-11).

**Data Contracts.** In the `variant dict` line, replace `(the server URL on the two LLM cells and `mop_coin_ledger_max_interactions: 2` on `mop`, `as_mop` and `as_mop_llm`, otherwise empty)` with `(the server URL on the two LLM cells, otherwise empty)`. Replace the line ``ape.properties` lines `ape.mopWeightD1..3`, `ape.mopRetireAfter`, `ape.mopLauncherDmax` only when a DSL override sets them`` with:

> - `ape.properties` lines `ape.mopWeights` (comma-separated), `ape.mopRetireAfter`, `ape.mopLauncherDmax` only when a DSL override sets them (destination: the jar's plan resolution)

and in the `APERV_PROPERTY_MAPPING` line replace `66 entries` with `64 entries`.

**Side-Effects.** Replace the `[Host filesystem]` line of the cached artifact (``one cached `<task.results_dir>/<task.config.apk_name>.mop.json` per (apk, full-JSON digest, format)…``) with:

> - **[Host filesystem]**: one cached artifact per (apk, full-JSON digest, format, cut): `<task.results_dir>/<task.config.apk_name>.mop.json` at cut 3 and `<task.results_dir>/<task.config.apk_name>.cut<c>.mop.json` at any other cut `c` (INV-APV-72), written atomically in canonical bytes and regenerated transparently when missing or stale

and add:

> - **[Device]**: `dalvik.vm.heapgrowthlimit` is set to `512m` as root before every launch and stays so until the emulator stops (INV-APV-73)

**Scenario names.** `openspec validate` and `openspec archive` refuse a MODIFIED block that drops a scenario name the main spec still has, and they have no rename. The delta therefore keeps three old names over the new content of D15. After the sync, rename them in the main spec:
- in "ApeRVTool Cell Variants": `Each cell carries the server URL or the ledger budget, and nothing else` → `Each cell carries the server URL, and nothing else`, and `The MOP cells write the ledger budget` → `The MOP cells write no MOP parameter`;
- in "Cell Configuration Matches the Jar's Cell Echo": `A MOP cell echoes its fixture plus the ledger budget` → `A MOP cell echoes its fixture`.

**Invariants.** Replace INV-APV-47, INV-APV-64, INV-DRV-05 and INV-DRV-10, and append INV-APV-70 to INV-APV-73 after INV-APV-69:

> - **INV-APV-47**: Cache freshness SHALL be keyed on the source digest, the format and the cut. A cached artifact is reused only when its file name is the cell's cut's (INV-APV-72), its recorded `source.digest` equals the SHA-256 of the current full JSON **and** its `formatVersion` equals `FORMAT_VERSION`. Cache state SHALL NOT change what the device receives for a given full JSON, generator and cut.
> - **INV-DRV-05**: Derivation SHALL be deterministic at the byte level: identical full-JSON input bytes and the same cut SHALL yield an identical artifact byte sequence, on any host and in any process.

> - **INV-APV-64**: On a cache miss `_derive_mop_artifact` SHALL read the document in streaming and SHALL keep, of each method's `targetDistances`, after taking the minimum per target, only the pairs at `d ≤ cut` and the `DIST_K` nearest by `(d, i)`, where `cut` is the cell's cut (INV-APV-70). The serialized artifact SHALL be byte-identical to `serialize_canonical(derive(json.load(document), cut=cut))` of the same file.
> - **INV-DRV-10**: Every distance pair `[i, d]` in the artifact SHALL satisfy `0 ≤ i < targets` and `d ≥ 0`. A pair list SHALL hold each index at most once and SHALL be sorted by `d` ascending, then `i` ascending. A widget's or a handler's list SHALL hold exactly the targets of its per-target minima at `d ≤ cut` and no pair beyond it, `cut` being `derive()`'s argument (3 by default). An `activityDist` list SHALL hold the three pairs of smallest `d`, whatever the cut. Every list is cut from the full per-target minima after every merge (listener, collision, dialog, class), never before, and an activity's minima start from its widgets' uncut minima. An empty pair list SHALL NOT be emitted. `targets` and `handlers` SHALL always be emitted.
> - **INV-APV-70**: The cut SHALL be max(`DIST_WEIGHED_MAX`, length of the cell's `mop_weights`), and `DIST_WEIGHED_MAX` when the cell has no ladder. The ladder SHALL hold 1 to 10 non-negative integers, and `ape.properties` SHALL never carry `ape.mopWeightD1..D3`.
> - **INV-APV-71**: No artifact SHALL be derived at a cut the document cannot carry: a cut outside `[1, distMax]` (`distMax` 10 when absent) raises `DerivationError`, as does a `distMax` that is not an integer ≥ 1, and a compact document whose `distancePairs.weighedMax` is below the cut, or whose marker has no integer `weighedMax`, raises `RVToolExecutionError` before `derive()`. In every such case nothing is written or pushed.
> - **INV-APV-72**: An artifact derived at cut `c` SHALL be cached as `<apk_name>.mop.json` when `c = 3` and as `<apk_name>.cut<c>.mop.json` otherwise, and SHALL never be reused for another cut.
> - **INV-APV-73**: Before the `app_process` command of every cell, `dalvik.vm.heapgrowthlimit` SHALL read `APE_HEAP_GROWTH_LIMIT` (`rv_android_core.constants`, `512m`) on the device, set through `Android.set_ape_heap_growth_limit`, the call the `ape` built-in also makes (INV-TOOL-30); when the setprop fails or the read-back differs, the exploration SHALL NOT start.

### `openspec/specs/tools/spec.md`

**Side-Effects.** Replace the `ape` built-in's `Device` line with:

> - **Device**: the `ape` built-in pushes `/data/local/tmp/ape.properties` (INV-TOOL-29) and sets `dalvik.vm.heapgrowthlimit` to `512m` as root (INV-TOOL-30) before each run; the emulator of each task runs with `-read-only -no-snapshot-save` and starts without either, so neither outlives the task.

**Invariants.** Append after INV-TOOL-29:

> - **INV-TOOL-30**: Before starting APE, the `ape` built-in SHALL set `dalvik.vm.heapgrowthlimit` to `APE_HEAP_GROWTH_LIMIT` (`rv_android_core.constants`, `512m`) through `Android.set_ape_heap_growth_limit`, the call `aperv-tool` makes (`aperv` INV-APV-73), and SHALL NOT start APE when the value does not read back. No tool module SHALL define its own copy of the value or of the set.
