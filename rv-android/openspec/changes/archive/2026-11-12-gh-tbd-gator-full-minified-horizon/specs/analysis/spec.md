## ADDED Requirements

### Requirement: Distance Horizon Parameter (FR06, NFR05)

`RvsecAnalysisClient` SHALL read the client parameter `distMax`, and `TargetDistances` SHALL stop every reverse search at that depth: each target's search in the distance pass and the repeated searches of the distance-path pass. Without the parameter the horizon SHALL be `TargetDistances.DEFAULT_DIST_MAX = 10`, declared beside `COMPACT_WEIGHED_MAX` and `COMPACT_K`. The value SHALL have no upper bound.

#### Scenario: no parameter keeps the default horizon
- **WHEN** GATOR runs in full mode without `-clientParam distMax`
- **THEN** no method SHALL carry a pair with `d > 10`

#### Scenario: a larger horizon writes a farther pair
- **WHEN** GATOR runs in full mode with `-clientParam distMax=15`, and an app method `M` reaches `distanceTargets[i]` through a shortest call chain of 12 edges
- **THEN** `M` SHALL carry `[i, 12]`

#### Scenario: a far method appears in the compact document under a larger horizon
- **WHEN** a method's shortest chains reach targets 0, 1, 2 and 3 in 11, 12, 13 and 14 calls, and no other target within 15
- **THEN** in compact mode without `distMax` it SHALL carry no `targetDistances` key
- **AND** in compact mode with `distMax=15` it SHALL carry `[[0, 11], [1, 12], [2, 13]]`

#### Scenario: the parsed data does not depend on the horizon
- **WHEN** the same APK is analysed once without `distMax` and once with `distMax=15`
- **THEN** the two `StaticAnalysisData` returned by `StaticAnalysisParser` SHALL be equal

### Requirement: An Invalid Distance Horizon Stops the Run (FR06, NFR05)

When `distMax` is present and `Integer.parseInt` rejects its value or the value is below 1, `RvsecAnalysisClient.run` SHALL throw `IllegalStateException` with a message naming `distMax` and the value as given, before it computes or writes anything. The GATOR JVM then exits with a non-zero status and the run writes no document. The client SHALL NOT fall back to `DEFAULT_DIST_MAX` (INV-ANA-100).

#### Scenario: an invalid value given to GATOR directly aborts the run
- **WHEN** the GATOR jar runs `RvsecAnalysisClient` with `-clientParam distMax=0`, or with `-clientParam distMax=ten`
- **THEN** `run` SHALL throw `IllegalStateException` whose message contains `distMax` and the given value
- **AND** the JVM SHALL exit with a non-zero status
- **AND** the run SHALL write no document

### Requirement: The Document Records a Given Horizon (FR06, NFR08)

When the run is given `distMax`, the client SHALL write the top-level member `distMax` with its value, right after `class_defs_under_key`, in both writes of the run and in both output modes, also when the distance pass fails (INV-ANA-99). Without the parameter it SHALL write no such member, and a document without it was computed with 10. The key SHALL be declared in `JsonSchema.Keys` and `_JK` (INV-ANA-32).

#### Scenario: a given horizon is recorded in full mode
- **WHEN** GATOR runs in full mode with `-clientParam distMax=15`
- **THEN** the top-level member keys SHALL begin, in order, `package`, `mainActivity`, `codePackage`, `codePackageSource`, `class_defs_under_key`, `distMax`, `distanceTargets`
- **AND** `distMax` SHALL equal `15`

#### Scenario: the horizon sits before the compact marker
- **WHEN** GATOR runs in compact mode with `-clientParam distMax=15`
- **THEN** the top-level member keys SHALL begin, in order, `package`, `mainActivity`, `codePackage`, `codePackageSource`, `class_defs_under_key`, `distMax`, `distancePairs`, `distanceTargets`

#### Scenario: no parameter writes no member
- **WHEN** GATOR runs without `-clientParam distMax`, in either mode
- **THEN** the document SHALL NOT carry a top-level `distMax` member

#### Scenario: the default value passed explicitly adds only the member
- **WHEN** the same APK is analysed once without `distMax` and once with `-clientParam distMax=10`, in the same output mode
- **THEN** the two documents SHALL differ only by the member `distMax: 10`, which only the second carries (INV-ANA-101), window and widget node ids compared by content (INV-ANA-79)

#### Scenario: the member survives a failed distance pass
- **WHEN** GATOR runs with `-clientParam distMax=15` and the distance pass throws, so `distanceTargets` is absent
- **THEN** the document SHALL still carry `distMax: 15` right after `class_defs_under_key`

#### Scenario: the converter keeps the horizon
- **WHEN** `rv-static-analysis compact full.json out.json` runs on a full document written with `-clientParam distMax=15`
- **THEN** `out.json` SHALL carry `distMax: 15` right before `distancePairs`
- **AND** `out.json` SHALL be the compact document GATOR writes with `distMax=15` for the same analysis state (INV-ANA-87)

### Requirement: `rv-static-analysis` Passes the Distance Horizon (NFR05)

`RVStaticAnalysisConfig` SHALL carry `dist_max: Optional[int] = None`, constrained by Pydantic to `≥ 1`. When it is set, `get_tool_command` SHALL append `-clientParam distMax=<value>`; when it is `None`, it SHALL append nothing for the horizon. The `analyze` and `batch` subcommands SHALL expose `--dist-max N`, parsed as an integer ≥ 1. Any other value SHALL be an argparse usage error (exit status 2), and GATOR SHALL NOT be started.

#### Scenario: the option reaches the command
- **WHEN** `rv-static-analysis analyze --apk app.apk --dist-max 15` builds the GATOR command
- **THEN** the command SHALL contain `-clientParam distMax=15`
- **AND** without `--dist-max` it SHALL contain no `distMax` parameter

#### Scenario: an invalid value is refused before GATOR starts
- **WHEN** `rv-static-analysis analyze --apk cryptoapp.apk --dist-max 0` runs, or the same with `--dist-max ten`
- **THEN** the command SHALL exit with status 2 and an argparse message naming `--dist-max`
- **AND** no GATOR process SHALL be started

#### Scenario: the Pydantic boundary refuses a horizon below one
- **WHEN** `RVStaticAnalysisConfig(dist_max=0, ...)` is constructed
- **THEN** it SHALL raise `pydantic.ValidationError`

### Requirement: A Stored Artefact Is Reused Only Under Its Own Horizon (FR04, NFR05)

`StaticAnalyzer._execute_command` SHALL reuse a stored `<apk_name>.json` only when its recorded horizon (`distMax`, 10 when absent) equals the run's (`dist_max`, 10 when `None`). Otherwise it SHALL log a warning naming both, remove the document and run the analysis (INV-ANA-102). It SHALL read the recorded horizon in streaming from the start of the document, stopping at the first top-level member after the scope block. It SHALL NOT compare output modes.

#### Scenario: a stored document of another horizon is regenerated
- **WHEN** `<apk_name>.json` was written with `distMax: 15` and the run asks for `--dist-max 10`, or for no horizon
- **THEN** the run SHALL log a warning naming 15 and 10
- **AND** it SHALL run GATOR and replace the document

#### Scenario: a stored document without the member counts as 10
- **WHEN** `<apk_name>.json` carries no `distMax` and the run asks for `--dist-max 12`
- **THEN** the run SHALL regenerate the document
- **AND** the same document SHALL be reused by a run that asks for no horizon or for `--dist-max 10`

#### Scenario: the same horizon is reused without reading the whole document
- **WHEN** a 2.7 GB `<apk_name>.json` carries `distMax: 15` and the run asks for `--dist-max 15` under the same scope key
- **THEN** the document SHALL be reused
- **AND** the horizon check SHALL stop reading at the top-level member that follows `distMax`

#### Scenario: the output mode is not compared
- **WHEN** a compact `<apk_name>.json` without `distMax` is on disk and the run asks for `--full-output` and no horizon
- **THEN** the document SHALL be reused

#### Scenario: a document whose first members cannot be read is regenerated
- **WHEN** `<apk_name>.json` on disk is empty, or holds bytes that are not JSON before its scope block ends
- **THEN** the run SHALL log a warning naming the file
- **AND** it SHALL run GATOR and replace the document

#### Scenario: a truncated document keeps its horizon readable
- **WHEN** `<apk_name>.json` carries `distMax: 15` and ends inside `transitions` because GATOR timed out, and the run asks for `--dist-max 15`
- **THEN** the horizon check SHALL read 15 and SHALL NOT be the reason the document is regenerated

## MODIFIED Requirements

### Requirement: Per-Target Call-Graph Distance (FR06)

The client SHALL compute, after the reachability search and before the pre-WTG write, one reverse breadth-first search per direct caller `c ∈ C` over the call graph with self-loops dropped (the graph the reachability search walks, lambda edges and empty-site edges included). Each search SHALL visit the callers of a method in the order of their signatures. The order changes no distance, since a breadth-first level does not depend on it; it fixes which of several equally short paths a search finds first, which the distance paths record (INV-ANA-92). The search SHALL stop at depth `distMax`, the run's horizon (Requirement: Distance Horizon Parameter; `DEFAULT_DIST_MAX = 10` when the run has no `distMax` parameter), and SHALL record the depth at which it first visits each app method. C SHALL be the app methods in the `directlyReachesTarget` set, sorted by signature, and SHALL be written as `distanceTargets`; each app method's pairs SHALL be written as `targetDistances` inside its `reachability[].methods[]` entry. The keys SHALL be declared in `JsonSchema.Keys` and `_JK` (INV-ANA-32).

Which of a method's pairs are written depends on the output mode (Requirement: Compact and Full Output Modes of the Analysis Document). Full mode writes every pair the searches recorded. Compact mode, the default, writes the pairs at `d ≤ 3` and the 3 nearest by `(d, i)` (INV-ANA-85). The searches themselves do not depend on the mode.

The reachability search keeps its library seeds, so `reachesTarget` keeps its meaning. The distance is seeded by app methods only, because a distance to a library direct caller says nothing a consumer can act on in the app (INV-ANA-73). C entries carry `kind: "direct"`.

The graph is the whole call graph, not the subgraph induced by app methods. Both were measured on 2026-10-07 on 10 APKs against the E6 traces and gave the same answers on every measure (true-handler rank, click lift, no-bind lift); the whole graph keeps INV-ANA-74, and on `com.password.monitor_102` it finds 102 app methods within 10 calls of a target where the app subgraph finds 6, because app callbacks invoked from library code are paths the app subgraph cuts.

#### Scenario: A handler two calls away from a direct caller
- **WHEN** the app has `A.onClick` → `A.save` → `Crypto.encrypt`, and `Crypto.encrypt` calls `javax.crypto.Cipher.doFinal`, a target
- **THEN** `distanceTargets` MUST contain `<Crypto: byte[] encrypt(byte[])>` at some index `i`
- **AND** `A.onClick` MUST carry `[i, 2]`, `A.save` `[i, 1]` and `Crypto.encrypt` `[i, 0]`, in both output modes

#### Scenario: Library direct callers do not seed the distance
- **WHEN** an app method `Net.connect` calls `okhttp3.OkHttpClient.newCall`, a library method that reaches a target only through library code, and no app method calls a target directly
- **THEN** `distanceTargets` MUST hold exactly `{"signature": "<…Net: void connect()>", "kind": "boundary"}`
- **AND** no library method MUST appear in `distanceTargets`
- **AND** `Net.connect`'s `reachesTarget` MUST be `true`, as before this change

#### Scenario: Distance beyond the cap
- **WHEN** the run has no `distMax` parameter and an app method reaches `c` only through a call chain of 11 edges
- **THEN** that method MUST NOT carry a pair for `c`
- **AND** its `reachesTarget` MUST still be `true`

#### Scenario: Distance within a horizon the run sets
- **WHEN** the run has `-clientParam distMax=15` and an app method reaches `c` only through a call chain of 11 edges
- **THEN** that method MUST carry `[i, 11]` for `c` in full mode

#### Scenario: A distant pair is written only in full mode
- **WHEN** a method is 6 calls from target `i` and 1, 2 and 3 calls from three other targets
- **THEN** the full-mode document MUST carry `[i, 6]` on that method
- **AND** the compact-mode document MUST NOT carry it

#### Scenario: Distance survives a WTG timeout
- **WHEN** the analysis of `org.quantumbadger.redreader_117.apk` is killed by the 1,800 s timeout while `WTGBuilder` runs
- **THEN** the partial `.apk.json` MUST contain `distanceTargets` and every `targetDistances` list
- **AND** it MUST NOT contain the `complete` sentinel (INV-ANA-31)

### Requirement: Distance Paths (FR06, NFR05, NFR08)

`RvsecAnalysisClient` SHALL read the client parameter `distancePaths` as it reads `fullOutput`. When it is `true` (case-insensitive), the client SHALL write `pathMethods` and `distancePaths` right after `reachability`, in both writes of a run (pre-WTG and final) and in both output modes. Otherwise it SHALL write neither. The member names SHALL be declared in `JsonSchema.Keys` and `_JK` (INV-ANA-32).

The paths SHALL be computed by `TargetDistances` in a second pass, after the distances. The pass first determines, for every app method, the pairs the output mode writes:
- every pair in full mode;
- the pairs `TargetDistances.compact` keeps in compact mode.

Then, for each target `i` that one of those pairs names, it repeats the reverse search from target `i`, with the horizon of the distance pass (Requirement: Distance Horizon Parameter), and records, for each method first visited from a callee, that callee. The pass SHALL then follow the recorded callees from each written pair's method down to the target, and SHALL emit each step `[i, v, n]` on those chains once.

`pathMethods` SHALL hold the signatures of the methods that appear in some step, sorted by signature. `distancePaths` SHALL hold the steps with `v` and `n` as indices into it, sorted by `(i, v)`.

The second pass is what keeps the cost of the first unchanged. Compact mode's rank rule needs every target's pairs of a method before it can say which pair survives. Recording predecessors during the first pass would hold one entry per visited method per target for the whole run, library methods included. Repeating only the searches that some written pair needs holds one target's predecessors at a time.

A step says that the search found `n` one call closer to the target than `v`. It does not imply that `v` carries a written pair for `i`: in compact mode an intermediate method's own pair for `i` may be reduced away while a farther method's pair, kept by rank, still passes through it. Library methods appear only in `pathMethods` and in steps, never in `reachability`.

#### Scenario: The path of a handler two calls from a direct caller
- **WHEN** an app has `A.onClick → A.save → Crypto.encrypt`, `Crypto.encrypt` calls the target `javax.crypto.Cipher.doFinal`, `distanceTargets[i]` is `Crypto.encrypt`, and the analysis runs with `distancePaths=true`
- **THEN** `A.onClick` SHALL carry `[i, 2]`
- **AND** `distancePaths` SHALL hold `[i, p(A.onClick), p(A.save)]` and `[i, p(A.save), p(Crypto.encrypt)]`, where `p(x)` is the index of `x` in `pathMethods`

#### Scenario: A path through a library method
- **WHEN** an app method `UI.onClick` calls the library method `kotlinx.coroutines.BuildersKt.launch`, whose graph edges reach the app method `Repo.save`, which is `distanceTargets[j]`, and `UI.onClick` carries `[j, 2]`
- **THEN** `pathMethods` SHALL contain the signature of `kotlinx.coroutines.BuildersKt.launch`
- **AND** the chain from `UI.onClick` SHALL pass through it

#### Scenario: Equally short paths are chosen the same way on every run
- **WHEN** `M` reaches target `i` at distance 2 both through `A` and through `B`, with `A`'s signature sorting before `B`'s
- **THEN** every run over the same call graph SHALL write the step `[i, p(M), p(A)]`
- **AND** no run SHALL write `[i, p(M), p(B)]`

#### Scenario: Compact mode keeps the steps of the kept pairs only
- **WHEN** a method carries, in full mode, pairs at distances 1, 2, 3 and 6 for four targets, and the analysis runs in compact mode with `distancePaths=true`
- **THEN** the pair at distance 6 is not written (INV-ANA-85), and no step SHALL exist that lies only on its chain
- **AND** the chains of the three kept pairs SHALL be complete (INV-ANA-91)

#### Scenario: The parameter off leaves the document as it is
- **WHEN** the same APK is analysed with `distancePaths=true` and without the parameter
- **THEN** the two documents SHALL differ only by `pathMethods` and `distancePaths` (INV-ANA-90)

#### Scenario: `rv-static-analysis` passes the parameter
- **WHEN** `rv-static-analysis analyze app.apk --distance-paths` builds the GATOR command
- **THEN** the command SHALL contain `-clientParam distancePaths=true`
- **AND** without `--distance-paths` it SHALL contain no `distancePaths` parameter

### Requirement: Path Query Subcommand (FR06, NFR05)

`rv-static-analysis` SHALL provide the subcommand `path DOC METHOD [--target I]`, implemented in `modules/rv-static-analysis/src/rv_static_analysis/path_query.py`. It SHALL read `DOC` in one streaming pass of its own with `ijson` (C backend), because `read_analysis_document` drops the path members (INV-ANA-97). From that pass it SHALL keep:
- `distanceTargets`;
- `pathMethods`;
- `distancePaths`;
- the `targetDistances` of the one `reachability[].methods[]` entry whose `signature` equals `METHOD`.

For each pair `[i, d]` of that method, sorted by `i`, or for the one pair with `i = I` when `--target` is given, it SHALL follow the steps from `METHOD` to `distanceTargets[i]`. It SHALL print a header line `[i] d=<d> <target signature>`, then the chain's `d + 1` signatures, one per line, indented by two spaces (INV-ANA-98).

It SHALL exit 1 with one line on stderr naming the document and the reason when:
- the document carries no `distancePaths`;
- `METHOD` has no entry in `reachability`;
- `METHOD` carries no pair for the target `--target` names;
- a chain breaks (a step is missing, or a chain does not have `d` steps): the document does not satisfy INV-ANA-91.

A method with no pair at all exits 0 and prints nothing. It is a valid answer: the method reaches no target within the document's horizon (`distMax`, or 10 when the document does not carry it).

The subcommand exists because the steps are indices into a table and are not readable by eye. Reading them in its own pass keeps the campaign reader's contract unchanged. It holds the method table and the steps, which for a compact document are a few times the size of the pairs (about 0.1 MB for `com.kin.easynotes_14`).

#### Scenario: The chains of a handler
- **WHEN** `rv-static-analysis path cryotp.json "<org.cry.otp.Home$1: void onClick(android.view.View)>"` runs on a document of `org.cry.otp_31.apk` written with `distancePaths=true`, where `Home$1.onClick` carries `[k, 3]` for `HOTP.hmac_sha1`
- **THEN** it SHALL exit 0
- **AND** stdout SHALL contain the line `[k] d=3 <org.cry.otp.HOTP: byte[] hmac_sha1(byte[],byte[])>` followed by the four signatures `Home$1.onClick`, `HOTP.gen`, `HOTP.generateOTP`, `HOTP.hmac_sha1`, each indented by two spaces

#### Scenario: One target requested
- **WHEN** the same command runs with `--target k`
- **THEN** stdout SHALL hold only the block for target `k`

#### Scenario: A document without paths is refused
- **WHEN** the document was written without `distancePaths=true`
- **THEN** the subcommand SHALL exit 1 with a message naming the document and saying that it carries no `distancePaths`

#### Scenario: An unknown method is refused
- **WHEN** `METHOD` names no method in `reachability`
- **THEN** the subcommand SHALL exit 1 with a message naming the method

### Requirement: Full JSON Remains the Sole Metric Input (R9, NFR02)

Every metric computation, gate and offline consolidation path SHALL read the full static-analysis JSON
and logcat exclusively. "The full JSON" is the analysis document `<apk_name>.json` in either output mode
(Requirement: Compact and Full Output Modes of the Analysis Document), as opposed to the derived
`*.mop.json`. The two modes differ only in `distancePairs` and in which `targetDistances`
pairs they carry. A run's horizon changes only `distMax`, the pairs and, when `distancePaths` is on, `pathMethods`
and `distancePaths`. No metric reads any of those. On the host paths that go through
`static_analysis_parser.read_static_analysis_files`, "the full JSON" includes its parsed copy
`<apk_name>.static.json` when the copy's recorded digest matches the source (INV-ANA-82): the copy is the
source document without `distanceTargets` and `targetDistances`, which no metric reads, and it parses to
the same `StaticAnalysisData` (INV-ANA-83). The frozen definitions — *MOP coverage* over
`directly_reaches_mop`, *unique misuse* keyed `(app, class, method, specification)`, and the
app-versus-library split by the `Mneut` prefix test — SHALL be unaffected, because their input is
unchanged.

No metric or analysis code SHALL read a `*.mop.json` artifact (INV-ANA-53). The artifact is a lossy
projection: it carries no `reachability` section, no method signatures, `reachesTarget` renamed to
`reachesMop`, `targetMethods` compacted to a boolean, and dialog widgets merged into host activities.
A metric computed over it would answer a different question under the same name. This SHALL be
enforced by an audit over the repository — a test asserting that no module outside `aperv-tool`
references the `.mop.json` suffix — rather than by convention. The audit test is itself the only
permitted match outside `aperv-tool`.

#### Scenario: metrics unchanged by the presence of an artifact
- **WHEN** the derivation runs for an app and the analysis pipeline then computes its
  `directly_reaches_mop` set
- **THEN** the set SHALL be computed from the full JSON
- **AND** it SHALL be identical to the value computed before this change

#### Scenario: audit catches an analysis path reading the artifact
- **WHEN** any module other than `aperv-tool` references a `.mop.json` path
- **THEN** the audit test SHALL fail naming the file and the reference
- **AND** the audit SHALL treat its own assertion text as the single permitted occurrence

#### Scenario: resume and offline consolidation re-parse the full JSON
- **WHEN** an experiment is resumed and `ResultProcessorComponent` re-resolves static data for an app
- **THEN** it SHALL read `<results_dir>/<apk_name>.json` through `read_static_analysis_files`, which
  answers from `<apk_name>.static.json` when its digest matches and from the source otherwise
- **AND** the presence, absence or staleness of a `*.mop.json` SHALL have no effect on the result

#### Scenario: metrics are the same from the source and from its parsed copy
- **WHEN** `ResultProcessorComponent` processes a task once with no `<apk_name>.static.json` present and
  once with the copy written by an earlier task
- **THEN** `summary.csv` and `coverage.csv` SHALL be byte-identical between the two runs

#### Scenario: metrics are the same from either output mode
- **WHEN** `ResultProcessorComponent` processes the same task once with the full-mode document and once
  with the compact-mode document of the same analysis as `<apk_name>.json`
- **THEN** `summary.csv` and `coverage.csv` SHALL be byte-identical between the two runs

### Requirement: Compact and Full Output Modes of the Analysis Document (FR04, FR06, NFR05, NFR08)

`RvsecAnalysisClient` SHALL read the client parameter `fullOutput` the way it reads `skipWtg`. When the parameter is `true` (case-insensitive) the client SHALL write **full** output: every `targetDistances` pair the searches recorded, up to the run's horizon (Requirement: Distance Horizon Parameter), and no `distancePairs` member (INV-ANA-86). In every other case, including when the parameter is absent, the client SHALL write **compact** output:

- the top-level member `distancePairs: {"weighedMax": 3, "k": 3}`, written immediately before `distanceTargets`, after the scope members (`package`, `mainActivity`, `codePackage`, `codePackageSource`, `class_defs_under_key`) and after `distMax` when the run carries it; it is written even when the distance pass failed and `distanceTargets` is absent, because it describes the document, not the pass;
- each method's `targetDistances` reduced to the pairs at `d ≤ COMPACT_WEIGHED_MAX` and the `COMPACT_K` nearest by `(d, i)`, sorted by `i` (INV-ANA-85);
- every other member identical to full mode.

Both modes SHALL be written with no indentation and no whitespace between tokens (Gson `JsonWriter` with no indent set). The two modes differ in the pairs they keep and in the marker, not in their serialisation. The full mode is not indented because indentation is most of a full document's size: an indented pair spans four lines and about 70 bytes, against about 9 bytes without whitespace, and in the 2.697 GB full document of `org.wikipedia_50595.apk` (measured on 2026-11-11) about 86 % of the bytes were indentation. Every reader of the document parses it as JSON, so none depends on its layout. A full document therefore reproduces the content of a document published in the indented form, compared after parsing, and not its bytes (INV-ANA-86).

The mode SHALL apply to both writes of a run, the pre-WTG write (INV-ANA-75) and the final write. A run never mixes the two.

The reduction is the one the MOP derive applies (`aperv` D15/D18: the jar weighs a pair only up to `d = 3`, and `activityDist` keeps the 3 nearest), and it is exact for that consumer. A dropped pair has `k` targets ahead of it in its own method, and those targets stay ahead of it after any merge by the minimum distance. Each target's search records one distance per method, so a method's full list already holds one pair per target, and reducing it needs no merge. Because the nearest pair always survives, a method keeps `targetDistances` in compact mode exactly when it carries the key in full mode, and INV-ANA-74 holds in both modes. The constants SHALL be declared in `TargetDistances` beside `DEFAULT_DIST_MAX` (INV-ANA-88). The marker keys `distancePairs`, `weighedMax` and `k` SHALL be declared in `JsonSchema.Keys` and `_JK` (INV-ANA-32).

`RVStaticAnalysisConfig` SHALL carry `full_output: bool = False`. When it is `True`, `get_tool_command` SHALL append `-clientParam fullOutput=true`, and otherwise SHALL append nothing for the mode. The `analyze` and `batch` subcommands SHALL expose `--full-output` and set the field. The parser, the parsed-copy cache (INV-ANA-82, INV-ANA-83) and, at its default cut of 3, the `aperv-tool` derive SHALL read both modes without being told which mode they read; a cell whose ladder deepens the cut refuses a compact document (`aperv` INV-APV-71). The cache copies the `distancePairs` member like any other top-level member.

#### Scenario: compact is the default
- **WHEN** `rv-static-analysis analyze --apk cryptoapp.apk` runs without `--full-output`
- **THEN** the GATOR command line SHALL NOT contain `fullOutput`
- **AND** `cryptoapp.apk.json` SHALL contain no newline character
- **AND** its top-level member keys SHALL be, in order, `package`, `mainActivity`, `codePackage`, `codePackageSource`, `class_defs_under_key`, `distancePairs`, `distanceTargets`, `components`, `reachability`, `windows`, `transitions`, `complete`
- **AND** `distancePairs` SHALL equal `{"weighedMax": 3, "k": 3}`

#### Scenario: full output on request
- **WHEN** `rv-static-analysis analyze --apk cryptoapp.apk --full-output` runs
- **THEN** the GATOR command line SHALL contain `-clientParam fullOutput=true`
- **AND** the document SHALL contain no newline character, SHALL carry every pair up to `d = 10` and SHALL NOT carry `distancePairs`

#### Scenario: the full document keeps the content of the indented one
- **WHEN** GATOR analyses `cryptoapp.apk` in full mode with this change's jar, and `modules/rv-static-analysis/tests/resources/cryptoapp.apk.json` is the full-mode document the jar before it wrote for the same APK and target set
- **THEN** the new document SHALL contain no newline character
- **AND** parsed, the two SHALL have the same top-level members in the same order and equal values up to `transitions`, window and widget node ids compared by content (INV-ANA-79)
- **AND** their `transitions` SHALL hold the same edges (INV-ANA-86)

#### Scenario: a method far from most targets keeps its three nearest
- **WHEN** a method's full list is `[[0, 7], [1, 5], [2, 9], [3, 6], [4, 10]]`
- **THEN** its compact list SHALL be `[[0, 7], [1, 5], [3, 6]]`

#### Scenario: every pair within three calls is kept
- **WHEN** a method's full list is `[[0, 1], [1, 3], [2, 2], [3, 3], [4, 8]]`
- **THEN** its compact list SHALL be `[[0, 1], [1, 3], [2, 2], [3, 3]]`

#### Scenario: the derive cannot tell the two modes apart
- **WHEN** `aperv-tool` derives the MOP artifact at its default cut once from the full document and once from the compact document of the same analysis of `org.wikipedia_50595.apk`
- **THEN** the two `*.mop.json` files SHALL be byte-identical apart from `source.digest`, which is the sha256 of each input file
- **AND** the two `StaticAnalysisData` returned by `StaticAnalysisParser` SHALL be equal (INV-ANA-89)

#### Scenario: the reduction constants drift
- **WHEN** `DIST_K` in `aperv_tool/tools/aperv/derive_mop_artifact.py` is changed to 4 while `TargetDistances.COMPACT_K` stays 3
- **THEN** the parity test under `tests/parity/` SHALL fail and name the three values it compared
