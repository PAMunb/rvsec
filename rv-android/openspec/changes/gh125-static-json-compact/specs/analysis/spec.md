## Purpose

GATOR's static-analysis document (`<apk_name>.json`, written by `RvsecAnalysisClient` through `JsonReportWriter`) is the coverage denominator of every run and the source of the MOP artifact that APE-RV reads. Since gh120, every app method carries `targetDistances`: its `[i, d]` pair to every target in `distanceTargets` within `DIST_MAX = 10` calls. The writer also indents the document by two spaces, so each pair spans four indented lines. Together the two make the documents of Study 03's E6 corpus take 24.62 GB for 163 APKs (9.34 GB for `eu.darken.sdmse_10705000`), and 358.5 million pairs are stored. The only consumer of the pairs is the `aperv-tool` derive of the MOP artifact. It keeps, per method, the pairs at `d ≤ 3` and the 3 nearest targets, 8.11 million pairs (2.3 %), and gh123 already applies that reduction while reading (`PairPolicy.reduce` in `rv_android_core/util/analysis_document.py`).

This delta moves the reduction to the producer and makes it the default. In **compact** mode GATOR writes the document without whitespace and keeps per method only the pairs the derive can use. A top-level `distancePairs` member records the reduction. In **full** mode, chosen with `-clientParam fullOutput=true`, GATOR writes exactly the document it writes today, so a published document can be reproduced. Measured on the E6 corpus on 2026-10-10, compact output takes 1.02 GB where today's output takes 24.62 GB. Without indentation but with every pair kept, the corpus would take 4.13 GB.

Neither mode changes what the consumers compute. `StaticAnalysisParser` discards the pairs in both cases (INV-ANA-80), so the parsed `StaticAnalysisData` is the same. The reduction is exact for the derive, so the derived MOP artifact is byte-identical apart from its `source` object, which names the file it was derived from. For documents already produced in full form, an offline subcommand `rv-static-analysis compact` writes the compact document GATOR would have written for the same analysis, so a corpus can be shrunk without running GATOR again. GATOR runs on the E6 corpus took 57.5 h of wall clock in September 2026.

"Full" is used in two senses. The full output mode is the one defined here. "The full JSON" in "Full JSON Remains the Sole Metric Input" names the analysis document, in either mode, as opposed to the derived `*.mop.json`.

## Data Contracts

### Input
- `-clientParam fullOutput=true|false` — GATOR client parameter; absent or any value other than `true` (case-insensitive) selects compact (source: `RVStaticAnalysisConfig.build_gator_command` in `modules/rv-static-analysis/src/rv_static_analysis/config.py`)
- `RVStaticAnalysisConfig.full_output: bool = False` and `--full-output` on the `analyze` and `batch` subcommands (source: the operator)
- `<full.json>` — a full-mode document, the input of `rv-static-analysis compact` (source: an earlier GATOR run)

### Output
- `<apk_name>.json` in compact mode — the document without whitespace; the top-level member `distancePairs: {weighedMax: 3, k: 3}` written right before `distanceTargets`; each `reachability[].methods[].targetDistances` reduced by INV-ANA-85 and sorted by `i`; every other member as in full mode (destination: `rv-static-analysis` parser, `aperv-tool` derive, offline analyses)
- `<apk_name>.json` in full mode — today's document: byte for byte up to `transitions`, and the same `transitions` edges, whose order follows identity-hash iteration (INV-ANA-86) (destination: same)
- `<out.json>` — the converter's output, byte-identical to the compact document GATOR writes for the same analysis (INV-ANA-87) (destination: the operator)

### Side-Effects
- **[Host filesystem]**: the converter writes `<out.json>` atomically (a temporary file in the same directory, then a rename) and never opens its input for writing

### Error
- `rv-static-analysis compact` exits with status 1 and one line on stderr, leaving no output file, when the input is truncated, already compact, holds a non-integer number, or resolves to the same file as the output; exit status 2 is argparse's usage error

## Invariants

- **INV-ANA-85**: In compact mode, a method's `targetDistances` SHALL hold exactly the pairs `[i, d]` of its full-mode list with `d ≤ COMPACT_WEIGHED_MAX = 3` or with rank `< COMPACT_K = 3` in the order `(d, i)`, sorted by `i`. The key SHALL be present on a method in compact mode iff it is present on that method in full mode. `distanceTargets` SHALL be identical in both modes.
- **INV-ANA-86**: In full mode the document SHALL be byte-identical to the document the client wrote before this change for the same analysis state up to the `transitions` member, its `transitions` SHALL hold the same edges with the same node ids, and it SHALL NOT carry `distancePairs`. The order of the `transitions` edges follows identity-hash iteration over the WTG edges, which a change in the client's code can move; INV-ANA-79 handles the same phenomenon by comparing node ids by content. Measured on `cryptoapp.apk`: identical through byte 68,750, the 35 edges identical, in another order, and each jar deterministic with itself. In compact mode the document SHALL carry `distancePairs` with the values of `COMPACT_WEIGHED_MAX` and `COMPACT_K`, in both the pre-WTG write and the final write.
- **INV-ANA-87**: For a full-mode document `F` and the compact-mode document `C` that GATOR writes for the same analysis state, `rv-static-analysis compact F` SHALL write `C` byte for byte.
- **INV-ANA-88**: `TargetDistances.COMPACT_WEIGHED_MAX` and `TargetDistances.COMPACT_K` (Java), the converter's constants (`rv-static-analysis`) and `DIST_WEIGHED_MAX` and `DIST_K` (`aperv-tool`) SHALL be pairwise equal. A parity test under `tests/parity/` SHALL fail when any of them differs.
- **INV-ANA-89**: For the same analysis state, the `StaticAnalysisData` parsed from the compact document SHALL equal the one parsed from the full document, and the `*.mop.json` derived from the compact document SHALL be byte-identical to the one derived from the full document apart from its `source` object: `source.digest` is the sha256 of the input file and so names which of the two documents the artifact came from. Given the same provenance, `derive()` writes the same bytes from either document.

## ADDED Requirements

### Requirement: Compact and Full Output Modes of the Analysis Document (FR04, FR06, NFR05, NFR08)

`RvsecAnalysisClient` SHALL read the client parameter `fullOutput` the way it reads `skipWtg`. When the parameter is `true` (case-insensitive) the client SHALL write **full** output: today's document, indented by two spaces, every `targetDistances` pair up to `DIST_MAX = 10`, and no `distancePairs` member (INV-ANA-86). In every other case, including when the parameter is absent, the client SHALL write **compact** output:

- no indentation and no whitespace between tokens (Gson `JsonWriter` with no indent set);
- the top-level member `distancePairs: {"weighedMax": 3, "k": 3}`, written immediately before `distanceTargets`, after the scope members (`package`, `mainActivity`, `codePackage`, `codePackageSource`, `class_defs_under_key`); it is written even when the distance pass failed and `distanceTargets` is absent, because it describes the document, not the pass;
- each method's `targetDistances` reduced to the pairs at `d ≤ COMPACT_WEIGHED_MAX` and the `COMPACT_K` nearest by `(d, i)`, sorted by `i` (INV-ANA-85);
- every other member identical to full mode.

The mode SHALL apply to both writes of a run, the pre-WTG write (INV-ANA-75) and the final write. A run never mixes the two.

The reduction is the one the MOP derive applies (`aperv` D15/D18: the jar weighs a pair only up to `d = 3`, and `activityDist` keeps the 3 nearest), and it is exact for that consumer. A dropped pair has `k` targets ahead of it in its own method, and those targets stay ahead of it after any merge by the minimum distance. Each target's search records one distance per method, so a method's full list already holds one pair per target, and reducing it needs no merge. Because the nearest pair always survives, a method keeps `targetDistances` in compact mode exactly when it carries the key in full mode, and INV-ANA-74 holds in both modes. The constants SHALL be declared in `TargetDistances` beside `DIST_MAX` (INV-ANA-88). The marker keys `distancePairs`, `weighedMax` and `k` SHALL be declared in `JsonSchema.Keys` and `_JK` (INV-ANA-32).

`RVStaticAnalysisConfig` SHALL carry `full_output: bool = False`. When it is `True`, `build_gator_command` SHALL append `-clientParam fullOutput=true`, and otherwise SHALL append nothing for the mode. The `analyze` and `batch` subcommands SHALL expose `--full-output` and set the field. The parser, the parsed-copy cache (INV-ANA-82, INV-ANA-83) and the `aperv-tool` derive SHALL read both modes without being told which mode they read. The cache copies the `distancePairs` member like any other top-level member.

#### Scenario: compact is the default
- **WHEN** `rv-static-analysis analyze --apk cryptoapp.apk` runs without `--full-output`
- **THEN** the GATOR command line SHALL NOT contain `fullOutput`
- **AND** `cryptoapp.apk.json` SHALL contain no newline character
- **AND** its top-level member keys SHALL be, in order, `package`, `mainActivity`, `codePackage`, `codePackageSource`, `class_defs_under_key`, `distancePairs`, `distanceTargets`, `components`, `reachability`, `windows`, `transitions`, `complete`
- **AND** `distancePairs` SHALL equal `{"weighedMax": 3, "k": 3}`

#### Scenario: full output on request
- **WHEN** `rv-static-analysis analyze --apk cryptoapp.apk --full-output` runs
- **THEN** the GATOR command line SHALL contain `-clientParam fullOutput=true`
- **AND** the document SHALL be indented by two spaces, SHALL carry every pair up to `d = 10` and SHALL NOT carry `distancePairs`

#### Scenario: a method far from most targets keeps its three nearest
- **WHEN** a method's full list is `[[0, 7], [1, 5], [2, 9], [3, 6], [4, 10]]`
- **THEN** its compact list SHALL be `[[0, 7], [1, 5], [3, 6]]`

#### Scenario: every pair within three calls is kept
- **WHEN** a method's full list is `[[0, 1], [1, 3], [2, 2], [3, 3], [4, 8]]`
- **THEN** its compact list SHALL be `[[0, 1], [1, 3], [2, 2], [3, 3]]`

#### Scenario: the derive cannot tell the two modes apart
- **WHEN** `aperv-tool` derives the MOP artifact once from the full document and once from the compact document of the same analysis of `org.wikipedia_50595.apk`
- **THEN** the two `*.mop.json` files SHALL be byte-identical apart from `source.digest`, which is the sha256 of each input file
- **AND** the two `StaticAnalysisData` returned by `StaticAnalysisParser` SHALL be equal (INV-ANA-89)

#### Scenario: the reduction constants drift
- **WHEN** `DIST_K` in `aperv_tool/tools/aperv/derive_mop_artifact.py` is changed to 4 while `TargetDistances.COMPACT_K` stays 3
- **THEN** the parity test under `tests/parity/` SHALL fail and name the three values it compared

### Requirement: Offline Conversion of a Full Document to the Compact Form (NFR04, NFR08)

`rv-static-analysis` SHALL provide the subcommand `compact INPUT OUTPUT`, implemented in `modules/rv-static-analysis/src/rv_static_analysis/compact.py`. It SHALL read `INPUT` with `read_analysis_document(INPUT, PairPolicy.reduce(COMPACT_WEIGHED_MAX, COMPACT_K))` from `rv_android_core.util.analysis_document`, sort each reduced `targetDistances` list by `i`, insert `distancePairs` where GATOR writes it, and write `OUTPUT` in Gson's compact form. Members, member order and values stay as read. Strings are escaped as Gson's `JsonWriter` escapes them with HTML-safe escaping off: `"` and `\` with a backslash, `\t`, `\b`, `\n`, `\r` and `\f` in short form, the other code points below U+0020 and U+2028/U+2029 as lowercase `\u00xx`/` `/` `, and every other character as itself in UTF-8. The output SHALL be the compact document GATOR writes for the same analysis (INV-ANA-87).

The converter exists because GATOR is expensive and the documents already exist. Re-analysing the E6 corpus to get compact documents would cost days of machine time, while the converter needs one streaming pass per document. It never holds the input's text or a dropped pair in memory. It does hold the reduced document, so its memory follows the sections the reduction leaves alone: on the E6 corpus the peak was 1.9 GiB of RSS for `org.fossify.calendar_20` (269 MB of output, almost all `windows`) and 674 MiB for the 9.34 GB `eu.darken.sdmse_10705000`.

The converter SHALL refuse, with exit status 1, one line on stderr naming the input and the reason, and no output file left behind:

- an input whose read reports truncation, because a truncated document is not the document GATOR wrote and its compact form would not be one either;
- an input that already carries `distancePairs`;
- an input holding a number that is not an integer, because GATOR writes only integers and Gson's form of a non-integer is not reproduced;
- an `OUTPUT` that resolves to the same file as `INPUT`.

The output SHALL be written to a temporary file in the directory of `OUTPUT` and renamed onto it, so an interrupted conversion leaves either no file or the previous one.

#### Scenario: converting a gh120 document
- **WHEN** `rv-static-analysis compact org.wikipedia_50595.apk.json /tmp/w.json` runs on the 2.16 GB full document
- **THEN** it SHALL exit 0
- **AND** `/tmp/w.json` SHALL parse to the same top-level members as the input in the same order, plus `distancePairs` right before `distanceTargets`
- **AND** every `targetDistances` in `/tmp/w.json` SHALL equal the input's list reduced by INV-ANA-85

#### Scenario: the converter writes what GATOR writes
- **WHEN** GATOR analyses `cryptoapp.apk` once in full mode and once in compact mode, and the full document is converted
- **THEN** the converted document SHALL be byte-identical to GATOR's compact document whenever the two runs gave the same analysis state; otherwise the two SHALL be equal after window and widget node ids are compared by content (INV-ANA-79's rule, since GATOR's ids depend on identity-hash iteration)

#### Scenario: a truncated input is refused
- **WHEN** the input ends inside the `transitions` section
- **THEN** the converter SHALL exit 1 with a message naming the input and the truncation
- **AND** `OUTPUT` SHALL NOT exist afterwards

#### Scenario: a compact input is refused
- **WHEN** the input carries `distancePairs`
- **THEN** the converter SHALL exit 1 with a message saying the input is already compact

#### Scenario: the converter never overwrites its input
- **WHEN** `rv-static-analysis compact a.json a.json` runs
- **THEN** it SHALL exit 1 and `a.json` SHALL be byte-identical to its content before the call

## MODIFIED Requirements

### Requirement: Per-Target Call-Graph Distance (FR06)

The client SHALL compute, after the reachability search and before the pre-WTG write, one reverse breadth-first search per direct caller `c ∈ C` over the call graph with self-loops dropped (the graph the reachability search walks, lambda edges included). The search SHALL stop at depth `DIST_MAX = 10` and SHALL record the depth at which it first visits each app method. C SHALL be the app methods in the `directlyReachesTarget` set, sorted by signature, and SHALL be written as `distanceTargets`; each app method's pairs SHALL be written as `targetDistances` inside its `reachability[].methods[]` entry. The keys SHALL be declared in `JsonSchema.Keys` and `_JK` (INV-ANA-32).

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
- **WHEN** an app method reaches `c` only through a call chain of 11 edges
- **THEN** that method MUST NOT carry a pair for `c`
- **AND** its `reachesTarget` MUST still be `true`

#### Scenario: A distant pair is written only in full mode
- **WHEN** a method is 6 calls from target `i` and 1, 2 and 3 calls from three other targets
- **THEN** the full-mode document MUST carry `[i, 6]` on that method
- **AND** the compact-mode document MUST NOT carry it

#### Scenario: Distance survives a WTG timeout
- **WHEN** the analysis of `org.quantumbadger.redreader_117.apk` is killed by the 1,800 s timeout while `WTGBuilder` runs
- **THEN** the partial `.apk.json` MUST contain `distanceTargets` and every `targetDistances` list
- **AND** it MUST NOT contain the `complete` sentinel (INV-ANA-31)

### Requirement: Full JSON Remains the Sole Metric Input (R9, NFR02)

Every metric computation, gate and offline consolidation path SHALL read the full static-analysis JSON
and logcat exclusively. "The full JSON" is the analysis document `<apk_name>.json` in either output mode
(Requirement: Compact and Full Output Modes of the Analysis Document), as opposed to the derived
`*.mop.json`. The two modes differ only in whitespace, in `distancePairs` and in which `targetDistances`
pairs they carry, and no metric reads any of those. On the host paths that go through
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
