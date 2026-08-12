# Stop re-scoping an already-scoped analysis artefact

**GitHub Issue:** #102

## Why

`StaticAnalysisParser` filters the GATOR analysis JSON by `App.code_package` after the producer has already scoped that file. GATOR is invoked with `-clientParam codePackage=<key>` and reports what it removed (`Filtered 4431 classes (libraries/generated) using package: <key>`); the `reachability` member it writes is the resulting method list, which is the whole denominator of coverage. A second filter over that list cannot add information — it can only take some away.

On a corpus whose applications are built with `applicationIdSuffix` it takes all of it away. Since gh98 (`553ae54a`) `App.code_package` returns the declared applicationId, and `io.keepalive.android.debug` is not contained in `io.keepalive.android.MainActivity`, so every class is dropped. Measured on the Estudo 03 corpus (162 APKs): **75 of 162** applications parse to zero classes and zero methods, report `cov_method = cov_act = cov_mop = 0` in every arm despite non-empty traces, and are then excluded by the admissibility criterion that requires non-zero coverage.

The consumer cannot repair this by choosing a better key, because the artefact does not record the key that filtered it (INV-ANA-58) and no heuristic recovers it reliably: `PackageDetector` disagrees with the producer key in 30 of 30 audited applications, and where it elects a longer key it truncates the denominator silently — 7987 classes to 78 for `org.wikipedia_50595`, 3171 to 140 for `com.jerboa_87`. That damage has already reached published measurements, so the fix must remove the question rather than answer it better.

## What Changes

- **BREAKING**: `StaticAnalysisParser.parse_file` and `read_static_analysis_files` no longer accept a package argument. The three call sites stop resolving and passing one.
- `_parse_classes` loads every entry of the `reachability` member. The package filter is deleted, not made conditional.
- `_parse_windows` scopes `ACTIVITY` windows by membership in `reachability` instead of by package prefix. This filter is retained because GATOR scopes `reachability` but not `windows`: 125 of the 162 artefacts carry framework activities (`androidx.activity.ComponentActivity`, `androidx.compose.ui.tooling.PreviewActivity`, `com.canhub.cropper.CropImageActivity`, `leakcanary.internal.activity.LeakActivity`) that must stay out of the `cov_act` denominator. Non-`ACTIVITY` window types keep entering unconditionally, as they do today.
- The producer path is untouched. `RVStaticAnalysisConfig.get_tool_command` keeps passing `-clientParam codePackage=`, and the run keeps recording the key and its origin — whoever *runs* an analysis still chooses the scope.
- **BREAKING**: INV-ANA-03 is removed. The requirement that recorded provenance for the consumption path narrows to the production path only.

Out of scope: `PackageDetector` and `App.code_package` are left alone. Other consumers exist (`rv-instrumentation-ajc` builds its quarantine guard from `code_package`), and removing them is a separate decision.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `analysis`: the rule that scopes parsed classes and windows changes from "filter by the caller's package key" to "the artefact defines its own scope". INV-ANA-03 is removed; the provenance requirement is narrowed to production; the coverage-denominator requirement gains the guarantee that the denominator equals the artefact's `reachability` member.

## Impact

**Modules**

| Module | Change |
|---|---|
| `rv-static-analysis` | `parser/static/static_analysis_parser.py` — the two filter sites and the `parse_file` signature; `analysis/static/static_analysis.py:439` — call site |
| `rv-platform` | `components/static_analysis.py:136` and `components/result_processor.py:269` — call sites; no behavioural code of their own changes |

**Requirements**: FR04, FR05, FR06 (static analysis parsing), FR12 (coverage tracking), NFR06 (measurement fidelity).

**Measured effect on the Estudo 03 corpus**: 75 of 162 applications recover a non-zero denominator; 0 of 215430 classes change scope in the applications that already worked (the class filter is provably a no-op there); the `ACTIVITY` scoping decision is unchanged in 162 of 162 applications across 1526 activities, verified against the producer key.

**Downstream**: the `comp162` campaign is blocked until the corrected parser ships in the runtime image, because it would otherwise measure a wrong denominator in 75 of its 162 applications. Measurements already published from campaigns that ran the detector remain affected by the truncation described above; re-reading them is not part of this change.
