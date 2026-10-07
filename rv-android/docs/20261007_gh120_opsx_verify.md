# Verification Report: gh120-gator-distance-hosted-windows

2026-10-07 17:40. Schema `rv-sdd`. Labels: **[conferido]** = opened or run in this session;
**[relato]** = from a subagent or an earlier session's record, not re-opened.

## Summary

| Dimension | Status |
|---|---|
| Completeness | 43/43 tasks; 11 ADDED + 1 MODIFIED requirements (analysis), 2 MODIFIED (aperv) |
| Correctness | 14/14 requirements with implementation; 3 requirements covered by acceptance runs only (by design) |
| Coherence | design followed; D1, D3, D13 and Error Handling updated today to match code |

## Evidence run in this session [conferido]

- GATOR client tests (JDK 21, offline): **239 run, 0 failures** (includes
  `SpinnerItemExtractorTest.adapterCreatedInBothBranches`, added for A3).
- Reactor build with A1 and A3: BUILD SUCCESS; jars in `rv-android/lib/gator` at 17:33.
- Parity suite `tests/parity`: 225 passed, 2 skipped, then the freshness gate after regenerating
  the cryptoapp baseline: green. Baseline content vs the 17:33 jar: identical (methods, widgets,
  transitions, components, `distanceTargets`).
- Python: rv-static-analysis 168 (+ parity keys and window tests: 191 together), aperv-tool and
  rv-android-core window tests 741 passed / 22 skipped.
- `org.cry.otp_31` re-run with the deployed jar (67 s, complete): 5 spinners with 3, 3, 3, 40, 2
  items; windows, transitions, methods and `distanceTargets` equal by content to the 14:59 artefact.
- `openspec validate --strict`: valid.

## Requirement → implementation

| Requirement | Implementation | Test |
|---|---|---|
| Per-Target Call-Graph Distance | `reach/TargetDistances.java` (`DIST_MAX` = 10), `ReachabilityEnricher` (pairs omitted when empty), `JsonReportWriter` (`distanceTargets` omitted only when the pass failed) | `TargetDistancesTest` (6); acceptance 5.3 (equal to the prototype on 3 APKs) and 5.4 (pre-WTG) [relato, verificação final] |
| Boundary Targets | `TargetDistances` (B \ C, `kind: "boundary"`) | `TargetDistancesTest.anEdgeToATargetMakesADirectCallerNotABoundaryOne`, `targetsAreDirectSortedThenBoundarySorted` |
| Lambda Wrapper Edges | `reach/LambdaEdges.java`, called in `RvsecAnalysisClient.run` before `ReachabilityEngine` | `LambdaEdgesTest` (5); cryptoapp baseline wrapper false → true |
| Fragment Windows | `fragment/FragmentHostResolver`, `fragment/FragmentWindows`, `prepareWindows` | acceptance only (no solver harness) |
| Fragment View Flow and ViewBinding | `gui/FragmentViewFlow`, `Flowgraph.createOpNode` hook, `GUIAnalysis` | acceptance only |
| Hosted Windows | `hosted/*`, `MAX_HOSTS` = 20 | acceptance only |
| Repeated Owned Windows | `RvsecAnalysisClient.dropRepeatedOwnedWindows` | `OwnedWindowsTest` |
| Repeated Widget Records | `RvsecAnalysisClient.dropRepeatedWidgets` | `OwnedWindowsTest` (+2) |
| Spinner Items from Array Resources | `SpinnerItemExtractor` (now: union over reaching adapter creations) | `SpinnerItemExtractorTest` (7); cry.otp |
| Parser Recognizes Fragment and Hosted | `_map_window_type`, `WindowType.HOSTED` | parser test (FRAGMENT/HOSTED), `test_window.py` |
| MODIFIED Unified Static Analysis (exclusions) | `Main.java:215-227`: no `-exclude`, `-no-bodies-for-excluded` kept | no automated test (see W1) |
| aperv: Widget MOP Flag Derivation (INV-DRV-09) | `derive_mop_artifact._index_reachability` | `test_listed_wrapper_keeps_its_own_flags`, `test_listed_wrapper_alone_stays_unflagged` |
| aperv: MOP Artifact Projection Contents | derive (cryptoapp ground truth) | `test_derive_cryptoapp_ground_truth` |

## CRITICAL

None.

## WARNING

- **W1. "Kotlin stdlib exclusion impact" has no automated test.** That `presto.android.Main` passes
  no `-exclude` is confirmed only by reading the code (`Main.java:215-227`). The droid_scep call-graph
  numbers come from the 2026-10-07 experiment and were not re-measured on the final build. The
  design (Mapping table) promised a `Main` args test. Recommendation: add the test in the follow-up
  change that handles A4/A6.
- **W2. The `distanceTargets`/`targetDistances` emission has no writer-level unit test.** The design
  mapping names `JsonOutputTest` (keys present, omitted when empty). What exists is the key-parity test
  plus the acceptance artefacts and the regenerated cryptoapp baseline, which carries both keys.
  Recommendation: same follow-up change.
- **W3. Fragment, view-flow and hosted requirements are covered by acceptance runs only.** This
  matches the design (no unit harness for the solver). Fourteen APKs were run;
  faircode, bitbanana, redreader, openbible and fosdem were not.
- **W4. Known limits deferred by the owner (design, Risks).** A4: a `HOSTED` window can sit on a
  concrete base activity outside the manifest. A6: a lambda-edge failure is only logged. Both are
  measured after the corpus run.

## SUGGESTION

From the code review, not acted on (owner decision): two `WidgetCollector` interfaces, three
fragment checks and two Navigation readers; `FragmentWindows.pairs()` and its public `Pair` fields
unused; a per-method `try` in `FragmentViewFlow.link`; `sootandroid/docs/architecture.md` does not
describe the three new solver models (they are in `rvsec-gator/CLAUDE.md`). The two inaccurate
comments (`_JK` on `distanceTargets`, `WindowType.HOSTED`) were fixed today.

## Final assessment

No critical issues. 4 warnings to consider. Ready for archive, with the noted improvements.
