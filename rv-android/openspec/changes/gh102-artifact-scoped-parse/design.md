## Context

`StaticAnalysisParser` re-filters a GATOR artefact that its producer already scoped. The proposal (issue #102) establishes why the second filter cannot help and, on a corpus built with `applicationIdSuffix`, destroys the coverage denominator for 75 of 162 applications.

The design question is narrow but not mechanical, which is why this document exists: one of the two filter sites is dead weight and the other is load-bearing, and telling them apart required evidence rather than reading. The class filter removes nothing legitimate (0 of 215430 parsed classes across the corpus fall outside the producer key), because GATOR scopes `reachability` before writing it. The window filter removes something real (125 of 162 artefacts carry framework activities in `windows`, which GATOR does not scope), so deleting both filters symmetrically would silently inflate `cov_act`.

Constraints. The artefact cannot be changed: it is produced by the Java client in the sibling `rvsec` reactor and the corpus has already been analysed, so any fix must work against artefacts that exist today. The producer path must keep resolving and passing a key (`-clientParam codePackage=`), because choosing a scope is a real decision when an analysis is actually run. `App.code_package` has consumers outside this domain (`rv-instrumentation-ajc`), so it stays.

Requirements: FR04, FR05, FR06 (static analysis parsing), FR12 (coverage tracking), NFR06 (measurement fidelity).

## Architecture

```
PRODUCTION PATH (unchanged)                    CONSUMPTION PATH (this change)
─────────────────────────                      ──────────────────────────────
App.code_package                               <apk>.json  ── already scoped
      │                                              │
      ▼                                              ▼
RVStaticAnalysisConfig.get_tool_command        StaticAnalysisParser.parse_file(path)
  -clientParam codePackage=<key>                     │        (no key parameter)
      │                                              ├── _parse_classes(data)
      ▼                                              │     └── loads reachability whole
GATOR / RvsecAnalysisClient                          ├── _parse_windows(data, classes)
  filters libraries/generated                        │     └── ACTIVITY ⟺ class ∈ reachability
      │                                              └── _parse_transitions(...)
      ▼                                                          │
  <apk>.json  ─────────────────────────────────────────────────► ▼
                                               StaticAnalysisData
                                                     │
                                                     ▼
                                        LogcatRepository (denominator)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `StaticAnalysisParser.parse_file` | Parse an artefact at the scope its producer gave it | `file_path: str` | `StaticAnalysisData` |
| `StaticAnalysisParser._parse_classes` | Load the `reachability` member whole | `data: dict` | `Classes` |
| `StaticAnalysisParser._parse_windows` | Admit non-`ACTIVITY` windows; admit `ACTIVITY` windows present in `reachability` | `data: dict`, `classes: Classes` | `Windows` |
| `StaticAnalysisParser.read_static_analysis_files` | Resolve `<results_dir>/<apk>.json` and delegate | `results_dir: str`, `apk: str` | `StaticAnalysisData` |
| `RVStaticAnalysisConfig.get_tool_command` | Pass the chosen key to GATOR — **unchanged** | `code_package: str` | `list[str]` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-ANA-59 (reachability loaded whole) | `_parse_classes` — package filter deleted | `test_inv_ana_59_reachability_loaded_whole` |
| INV-ANA-59 (denominator equals universe) | `repository_initializer.initialize_repository_from_static_data` (unchanged) | `test_inv_ana_59_denominator_equals_reachability` |
| INV-ANA-60 (ACTIVITY ⟺ ∈ reachability) | `_parse_windows` — membership test replaces prefix test | `test_inv_ana_60_framework_activity_excluded`, `test_inv_ana_60_non_activity_admitted` |
| INV-ANA-61 (no key on consumption path) | signatures of `parse_file`, `read_static_analysis_files` and the 3 call sites | `test_inv_ana_61_no_package_parameter` |
| INV-ANA-58 (narrowed to production) | `RVStaticAnalysisConfig.get_tool_command` + run record — unchanged | existing provenance tests |
| Scenario: applicationId scoping nothing | both filter sites | `test_gh102_applicationid_suffix_full_denominator` |
| REMOVED INV-ANA-03 | grep shows zero call sites passing a package to the parser | `test_inv_ana_61_no_package_parameter` |

## Goals / Non-Goals

**Goals:**
- The parsed universe equals the artefact's `reachability` member, for every artefact, regardless of what the APK declares as its applicationId.
- The activity denominator keeps excluding framework activities, by a rule the artefact can answer.
- The consumption path holds no package key, so no key mismatch can exist there.

**Non-Goals:**
- Removing `PackageDetector` or changing `App.code_package`. Out of scope; other consumers exist.
- Changing the producer path or the artefact format. The fix must work on artefacts already on disk.
- Re-reading or correcting measurements published from campaigns that ran with the detector. That is a separate analysis, noted in the proposal.
- Making the parser validate that an artefact was scoped at all. A corpus analysed with a wrong key is a data-management fact (INV-ANA-58), not something the parser resolves.

## Decisions

**D1 — Delete the class filter rather than make it conditional.** A conditional (`filter only when the key matches something`) would keep the key on the consumption path and keep the failure mode reachable, just rarer. The evidence says the filter has no legitimate work: 0 of 215430 classes across the corpus fall outside the producer key. P3 applies — dead code is deleted, not guarded.

*Alternative considered*: keep the filter and feed it the producer key recovered from provenance logs. Rejected: it requires a per-APK key mechanism that does not exist, the logs are not part of the artefact, and INV-ANA-58 exists precisely because the artefact cannot answer this. It also leaves the consumer able to disagree with the producer, which is the defect.

**D2 — Scope `ACTIVITY` windows by membership in `reachability`, not by a key.** The test is derivable from the artefact alone, so it cannot disagree with the producer. It was verified to reproduce the key-based decision on 1526 of 1526 activities across 162 applications, with zero divergence — so this is a re-derivation of the same decision from a sounder source, not a new policy.

*Alternative considered*: admit every window and let `cov_act` include framework activities. Rejected: it changes the measurement. `app.pachli_50` would go from 27 to 35 activities in the denominator, 8 of them owned by libraries.

*Alternative considered*: filter windows by the set of class names, and also require `componentType == activity`. Rejected as redundant: `_parse_windows` already keys on the window's declared type, and membership in `reachability` is the ownership question being asked.

**D3 — Drop the parameter instead of defaulting it to `None`.** A defaulted parameter would leave 83 call sites free to keep passing a key that is silently ignored, and would leave the signature advertising a capability that no longer exists. Removing it makes every stale call site a loud failure at the moment of the change (P3, P4).

**D4 — Leave the producer path untouched, including the run record.** Whoever runs an analysis still chooses a scope and still records it. Narrowing INV-ANA-58 to production is a documentation change, not a behavioural one: nothing on the production path is edited.

## API Design

### `StaticAnalysisParser.parse_file(file_path: str) -> StaticAnalysisData`

**Preconditions**: none beyond the existing ones — a missing or unreadable path returns empty domain objects, as today.
**Postconditions**: `result.classes` contains one entry per element of `data["reachability"]`, with every method of each entry. `result.windows` contains every non-`ACTIVITY` window plus each `ACTIVITY` window whose normalized class name is a key of `result.classes.classes`.
**Errors**: unchanged (INV-ANA-06 graceful degradation per section).

### `StaticAnalysisParser.read_static_analysis_files(results_dir: str, apk: str) -> StaticAnalysisData`

Resolves `<results_dir>/<apk>.json` and delegates. Module-level `parse_file` and `read_static_analysis_files` singletons mirror the same signatures.

### `_parse_windows(self, data: dict, classes: Classes) -> Windows`

The `package` parameter is removed; `classes` is already passed today (it is used to mark the main activity) and now also supplies the ownership test. Ordering in `parse_file` is unchanged — classes are parsed before windows — so no new dependency is introduced.

## Data Flow

1. `rv-platform` resolves `<results_dir>/<apk>.json` and calls `read_static_analysis_files(results_dir, apk)`. No `App` attribute is read.
2. `parse_file` loads the JSON, then parses sections in the existing order: classes, windows, transitions, components.
3. `_parse_classes` iterates `data["reachability"]`, normalizes each class name, and adds every class and every method. No entry is skipped.
4. `_parse_windows` iterates `data["windows"]`. Non-`ACTIVITY` types are admitted. `ACTIVITY` types are admitted iff `classes.get_clazz(normalized_name)` resolves.
5. `StaticAnalysisData` reaches `CoverageTracker`, which populates `LogcatRepository`; `_calculate_static_totals` counts what it was given, so the denominator is the artefact's own universe.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Missing analysis file | `parse_file` | Warn, return empty `StaticAnalysisData` | Unchanged — coverage reports 0 and the run is judged inadmissible |
| Malformed `reachability` entry | `_parse_classes` | Existing per-section try/except (INV-ANA-06) | Section degrades to empty; other sections survive |
| `ACTIVITY` window absent from `reachability` | `_parse_windows` | Not an error — the window is excluded by design | n/a |
| Stale call site still passing a package | Python | `TypeError` at call time | Fix the call site; D3 makes this deliberate |

## Risks / Trade-offs

- **[An artefact produced with a wrong key still yields a wrong denominator]** → Out of scope by design. The parser consumes the artefact at the producer's scope; a corpus analysed under a bad key is a data-management fact (INV-ANA-58). The change removes the consumer's ability to *add* a second, different error.
- **[An artefact whose `windows` legitimately reference an application activity absent from `reachability`]** → Would be excluded from `cov_act`. Verified not to occur across the corpus (162/162 agreement with the key-based decision). If it ever occurs it means the producer's own reachability sweep missed a declared component, which is a producer defect and should surface as one.
- **[83 test call sites pass a package argument]** → Mechanical breakage, caught at collection. Concentrated in `rv-static-analysis` (77); `rv-agent` (4) and `rv-platform` (2) are small.
- **[Numbers move for the 75 affected applications]** → Intended. Any campaign measured before this change is not comparable to one measured after it for those applications, and the `comp162` plan must say so.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | `_parse_classes` loads every entry; `_parse_windows` admits/excludes per membership; signatures carry no package | Fixture JSONs, including one whose `package` member has a build suffix | ~6 new tests |
| Unit (regression) | The 77 existing parser tests still pass with the parameter removed | Update call sites, assert unchanged expectations | 77 updated |
| Integration | `rv-platform` loads static data and reconstructs on resume without reading `App.code_package` | Existing component tests, call sites updated | 2 updated |
| Corpus verification | The 75 previously-zero applications report a non-zero denominator; the 5 truncation cases report the producer-key denominator | Offline script over the 162 artefacts, comparing parsed counts against the provenance-log key | 1 script |

CI contract applies: `pytest --import-mode=importlib -o "addopts="` per module.

## Open Questions

- Whether the fixture corpus for the new unit tests should be a trimmed real artefact (a few classes from `io.keepalive.android_133.apk.json`, which exercises the suffix case authentically) or a hand-written minimal JSON. Leaning to the trimmed real artefact for the suffix case and hand-written for the window cases, decided at implementation time.
- Whether `docs/PRD.md` FR12 wording needs a companion edit to state that the denominator is the artefact's `reachability` member. Not required by this change; flagged for the docs sync.
