## Context

The proposal (#125) gives the numbers. The E6 static-analysis documents take 24.62 GB for 163 APKs. 358.5 million `targetDistances` pairs and two-space indentation account for almost all of it, and the only consumer of the pairs keeps 2.3 % of them. gh123 made the readers stream the document and reduce the pairs on the fly (`PairPolicy.reduce` in `modules/rv-android-core/src/rv_android_core/util/analysis_document.py`, used by `ApeRVTool._derive_mop_artifact`). This change moves the same reduction, and the removal of whitespace, into the producer. Full output stays available, byte-identical to today's (NFR08). A converter brings already-produced documents to the compact form without re-running GATOR (NFR04).

Current state of the producer (`rvsec/rvsec-android/rvsec-gator/client/src/main/java/presto/android/gui/clients/`):

- `json/JsonReportWriter.write(...)` opens the file, creates `new JsonWriter(osw)`, calls `w.setIndent("  ")`, and writes the scope members, `distanceTargets` (`writeDistanceTargets`), `components`, `reachability`, `windows`, `transitions` and the sentinel. `RvsecAnalysisClient` calls it twice per run: the pre-WTG write at `:210` and the final write at `:243`.
- `RvsecAnalysisClient.writeReachabilitySection(w, appClasses, output, enricher)` (static, `:1676`) writes each method's `targetDistances` from `enricher.enrichMethod(method)`. The pairs come from `TargetDistances.pairs(m)` as `int[][]`, sorted by `i`.
- `reach/TargetDistances` holds `DIST_MAX = 10`. Each target's reverse BFS records one depth per method, so a method's array has one pair per target.
- `skipWtg` is read with `Configs.getClientParamCode("skipWtg=")` (`RvsecAnalysisClient.skipWtg()`, `:295`).

Consumer side (`modules/rv-static-analysis/src/rv_static_analysis/`): `config.py` builds the GATOR command (`skip_wtg` → `-clientParam skipWtg=true`, `:406`), `__main__.py` has the `analyze` and `batch` subcommands, and `parser/static/static_analysis_parser.py` holds `_JK`. `rv-static-analysis` already depends on `rv-android-core`, where the streaming reader lives.

## Architecture

```
            -clientParam fullOutput=true?            (rv-static-analysis config.py / --full-output)
                         │
                         ▼
RvsecAnalysisClient ── fullOutput() ──► JsonReportWriter(enricher, compact)
                                          │  compact: no setIndent, writeDistancePairs(w)
                                          │  full:    setIndent("  "), no marker
                                          ▼
                     writeReachabilitySection(w, …, enricher, compact)
                                          │  compact: TargetDistances.compact(pairs)
                                          ▼
                                   <apk>.json  (compact by default)
                                          │
        ┌─────────────────────────────────┼─────────────────────────────────┐
        ▼                                 ▼                                 ▼
StaticAnalysisParser (gh123)     aperv-tool derive (gh123)       rv-static-analysis compact
drops pairs → same model         reduces again → same bytes      full <apk>.json → compact bytes
                                                                 (read_analysis_document +
                                                                  PairPolicy.reduce + GsonCompactWriter)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `TargetDistances.COMPACT_WEIGHED_MAX`, `COMPACT_K` (Java) | The reduction's two constants, beside `DIST_MAX` | — | `3`, `3` |
| `TargetDistances.compact(int[][] pairs)` (Java, static, pure) | Keep pairs at `d ≤ 3` or of rank `< 3` by `(d, i)`; return them sorted by `i` | one method's pairs | reduced `int[][]` |
| `RvsecAnalysisClient.fullOutput()` | Read `-clientParam fullOutput=` like `skipWtg()` | client params | `boolean` |
| `JsonReportWriter(enricher, compact)` | Indent or not; write `distancePairs` before `distanceTargets` in compact | mode | the document |
| `JsonReportWriter.writeDistancePairs(w)` (static) | Write `{"weighedMax":3,"k":3}` under `distancePairs` | — | marker |
| `RvsecAnalysisClient.writeReachabilitySection(…, compact)` | Pass each method's pairs through `TargetDistances.compact` when compact | pairs | `targetDistances` |
| `JsonSchema.Keys.DISTANCE_PAIRS`, `WEIGHED_MAX`, `K` + `_JK` | Marker keys on both sides (INV-ANA-32) | — | — |
| `RVStaticAnalysisConfig.full_output` + `--full-output` | Operator's choice → `-clientParam fullOutput=true` | CLI | GATOR command |
| `rv_static_analysis.compact` (new module) | `compact_document(src, dst)` and the Gson-compatible serialiser | full document | compact document |
| `rv-static-analysis compact` subcommand | CLI wrapper, exit codes | paths | exit status |
| `tests/parity/test_distance_pair_constants.py` | Java constants == converter constants == `aperv-tool` constants (INV-ANA-88) | source files | pass/fail |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| INV-ANA-85 (reduction rule, key presence) | `TargetDistances.compact` | `TargetDistancesCompactTest` (Java): spec examples, ties at `d`, fewer than 3 pairs, empty |
| INV-ANA-86 (full byte-identical up to `transitions`, same edges; marker in both writes) | `JsonReportWriter` mode branch; `fullOutput()` | `DistancePairsMarkerTest` (Java, marker writer); e2e on `cryptoapp.apk`: full-mode output vs. the jar before the change |
| INV-ANA-87 (converter == GATOR compact) | `rv_static_analysis.compact` | `test_compact_converter.py` (unit: members, order, marker position, refusals, escapes); e2e: GATOR on `cryptoapp.apk` in both modes, convert the full one, compare |
| INV-ANA-88 (constants parity) | constants in three places | `tests/parity/test_distance_pair_constants.py` |
| INV-ANA-89 (same model, same MOP artifact apart from `source`) | none (property of the reduction) | `test_compact_equivalence.py` (parser) and aperv-tool `test_compact_document_derives_the_same_artifact` (derive, same provenance) on `tests/resources/cryptoapp.apk.json` and its conversion; on 5 E6 documents (incl. wikipedia) through the converter, `experimento-gh125/check_equivalence.py` |
| Output modes requirement: config/CLI | `config.py`, `__main__.py` | `test_config.py` / CLI tests: `full_output` → `-clientParam fullOutput=true`; default → no `fullOutput` |
| Converter requirement: refusals, atomic write | `compact_document`, `main` | `test_compact_converter.py` |
| "Full JSON Remains the Sole Metric Input" (either mode) | none | `summary.csv`/`coverage.csv` equality between a full document and its conversion: rv-platform `TestExecutePipeline::test_csv_identical_from_full_and_compact_documents` |

## Goals / Non-Goals

**Goals:**
- Compact by default in GATOR; full on request, byte-identical to today up to `transitions`, whose edges are the same in identity-hash order.
- A self-describing compact document (`distancePairs`).
- An offline converter whose output equals GATOR's compact output.
- One value for each reduction constant across Java, the converter and `aperv-tool`, enforced by a test.

**Non-Goals:**
- Shrinking `windows` or `transitions` (e.g. `org.fossify.calendar_20` keeps 267 MB of windows).
- Changing the parser, the parsed-copy cache, the derive or the MOP artifact.
- Converting or re-analysing the E6 corpus, rebuilding the image, or editing the replication package. The rep pack decides whether to use the converter.
- A mode option in `rv-experiment` or `scripts/static_analysis_sweep.py`. Both get the compact default.

## Decisions

**D1. The reduction runs in the writer, not in the enricher or in `TargetDistances.pairs`.** `writeReachabilitySection` already receives the pairs from `enricher.enrichMethod`. It applies `TargetDistances.compact` to them when it writes compact output. The enricher and the distance pass stay mode-free, so INV-ANA-73/74 and every existing enricher test are untouched, and the mode lives in one object, the writer. *Alternative:* filter in `TargetDistances.pairs`. That would also cut the pairs every other caller sees, and it would put an output concern into the analysis.

**D2. `compact` is a static pure function over one method's `int[][]`.** It sorts a copy by `(d, i)`, keeps rank `< K` or `d ≤ WEIGHED_MAX`, then sorts the kept pairs by `i`. It needs no merge step: each target's BFS records one depth per method, so the input has at most one pair per `i`. gh123's `_reduce_pairs` merges by minimum first because it must accept any document. The two functions agree on every input GATOR writes.

**D3. The marker is written by the writer, right before `distanceTargets`, in both writes.** It goes early so a streaming reader learns the document's kind before it reaches any pair. It goes after the scope members so that, minus the marker, the compact member order is the full member order. It is written even when the distance pass failed, because it describes how the document was written. A compact document with no `distanceTargets` therefore still says it is compact.

**D4. Full mode is the code path that runs today, untouched.** The only change on that path is a branch that skips the marker and the reduction and keeps `setIndent("  ")`. Identity with the published documents is checked on `cryptoapp.apk`: the jar before the change and the new jar in full mode run on the same APK. Measured on 2026-10-10, the two documents are byte-identical through byte 68,750, where `transitions` begins; `transitions` holds the same 35 edges with the same node ids in another order. Each jar is deterministic with itself (two runs each give one sha256), so the order is a property of the jar's code: `writeTransitionsSection` iterates the WTG's edges in identity-hash order, and the new code moves the allocation sequence that order depends on. INV-ANA-86 therefore states byte identity up to `transitions` and edge identity within it, the comparison INV-ANA-79 already makes for node ids.

**D5. The converter reuses gh123's reader and adds only a serialiser.** `read_analysis_document(src, PairPolicy.reduce(3, 3))` already returns the document with the members in order and the pairs reduced, ordered by `(d, i)`. It never holds the text or a dropped pair. The converter re-sorts each list by `i`, rebuilds the top-level dict with `distancePairs` before `distanceTargets` (or before `components` when `distanceTargets` is absent), and serialises. The serialiser is a small recursive writer: `dict`, `list`, `str`, `int`, `bool` and `None` in Gson's compact form. Strings use Gson's `JsonWriter` escape table with HTML-safe escaping off, as described in the spec. Python's `json.dumps(..., ensure_ascii=False, separators=(",", ":"))` matches that table except for U+2028/U+2029, which Gson escapes and Python does not. The serialiser therefore post-processes the encoded string for those two code points instead of reimplementing the encoder. A `float` reaching the serialiser is a refusal, because GATOR writes only integers and Gson's double formatting would not be reproduced. All 40 of the smallest E6 documents were checked on 2026-10-10 and held no non-integer number.

**D6. The converter holds the reduced document in memory.** It does not stream it out. Its size follows the sections the reduction leaves alone, not the input: measured on 2026-10-10, the peak RSS is 1.9 GiB for `org.fossify.calendar_20` (406 MB in, 269 MB out, almost all `windows`) and 674 MiB for sdmse (9.34 GB in, 54.6 MB out). Holding it keeps the converter a composition of the existing reader and one writer. *Alternative:* an event-level transcoder that writes while it reads. It would need its own state machine for the key order and the pair lists, which is complexity for a size the host absorbs. The peak RSS is recorded in tasks 4.2 and 4.3.

**D7. Refusals are checked before the output is created.** `samefile(src, dst)` is rejected before reading. Truncation and an already compact input (`distancePairs` present) are known after the read, and the output is created only after both checks pass. The write goes to `tempfile.NamedTemporaryFile(dir=dirname(dst), delete=False)`, followed by `os.replace`. On any exception the temporary file is removed.

**D8. The constants are pinned by a parity test, not shared code.** Java cannot import Python. `aperv-tool` cannot be a dependency of `rv-static-analysis` (wrong direction), and the reverse would couple the jar's weights to the producer. The three declarations stay where their owners need them. `tests/parity/test_distance_pair_constants.py` reads `COMPACT_WEIGHED_MAX`/`COMPACT_K` from `TargetDistances.java` by regex, as `test_json_keys.py` reads `JsonSchema.Keys`, imports the converter's constants and `aperv_tool.tools.aperv.derive_mop_artifact.DIST_WEIGHED_MAX`/`DIST_K`, and asserts all three are equal. A drift then fails with the three values named.

## API Design

### Java

```java
// reach/TargetDistances.java
public static final int COMPACT_WEIGHED_MAX = 3;
public static final int COMPACT_K = 3;
/** Pairs at d ≤ COMPACT_WEIGHED_MAX or of rank < COMPACT_K by (d, i), sorted by i. Pure; never null. */
public static int[][] compact(int[][] pairs);

// json/JsonReportWriter.java
public JsonReportWriter(ReachabilityEnricher enricher, boolean compact);
static void writeDistancePairs(JsonWriter w) throws IOException;   // "distancePairs":{"weighedMax":3,"k":3}

// RvsecAnalysisClient.java
private boolean fullOutput();   // Configs.getClientParamCode("fullOutput=") equalsIgnoreCase "true"
public static void writeReachabilitySection(JsonWriter w, Map<…> appClasses, GUIAnalysisOutput output,
        ReachabilityEnricher enricher, boolean compact) throws IOException;
```

### Python

```python
# rv_static_analysis/compact.py
COMPACT_WEIGHED_MAX = 3
COMPACT_K = 3

class CompactRefused(Exception):
    """The input cannot be converted; the message names the input and the reason."""

def compact_document(src: str, dst: str) -> None:
    """Write the compact form of the full document `src` to `dst` (INV-ANA-87).
    Pre: `src` is a complete full-mode document. Post: `dst` replaced atomically.
    Raises CompactRefused (truncated, already compact, non-integer number, same file);
    OSError on I/O; ValueError from read_analysis_document on a non-JSON input."""

def dumps_gson_compact(value) -> str: ...   # the serialiser of D5

# rv_static_analysis/config.py
class RVStaticAnalysisConfig(BaseModel):
    full_output: bool = Field(default=False, description="…appends -clientParam fullOutput=true")
```

The subcommand `compact INPUT OUTPUT` calls `compact_document`. It exits 0 on success. On `CompactRefused`, `ValueError` or `OSError` it prints one line to stderr and exits 1.

## Data Flow

1. `rv-static-analysis analyze` → `get_tool_command` → GATOR command line with or without `-clientParam fullOutput=true`.
2. `RvsecAnalysisClient.run` → `fullOutput()` → `new JsonReportWriter(enricher, !full)` → pre-WTG `write` → WTG → final `write`, both in the same mode.
3. Downstream readers are unchanged. The parser drops pairs, the cache copies the marker, and the derive reduces again, which is the identity on a compact list.
4. Offline: `rv-static-analysis compact full.json out.json` → reader (reduce) → re-sort by `i` → insert marker → serialise → temp file → `os.replace`.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `fullOutput` with a value other than `true`/`false` | GATOR client param | Treated as compact, as `skipWtg` treats non-`true` | Pass `true` |
| Truncated input | converter, `read_analysis_document` returns `truncated=True` | `CompactRefused`, exit 1, no output | Re-run GATOR for that APK |
| Input already compact | converter, `distancePairs` in the read document | `CompactRefused`, exit 1 | None needed |
| Non-integer number | serialiser | `CompactRefused`, exit 1, temp file removed | Report: GATOR wrote something it never wrote before |
| `src` and `dst` are the same file | converter, `os.path.samefile` when `dst` exists | `CompactRefused`, exit 1 | Choose another output |
| Non-JSON input / unreadable file | reader (`ValueError`/`OSError`) | exit 1 with the reader's message | — |

## Risks / Trade-offs

- [An offline reader expects all pairs.] An example is the replication package's `docs/tmp/sa_quality_20261009/` scripts, which count pairs. → The marker lets such a reader detect a compact document. Full mode and the published full documents remain available. The rep pack is told in the hand-off; changing its scripts is outside this change.
- [Gson's escaping differs from the serialiser on an input never seen.] → The escape table is tested code point by code point against Gson's `REPLACEMENT_CHARS`, and the e2e byte comparison on `cryptoapp.apk` exercises the whole path. Signatures and resource names are ASCII in practice.
- [GATOR output not reproducible run to run.] Node ids depend on identity-hash iteration (INV-ANA-79). → The e2e comparison falls back to comparing ids by content, as INV-ANA-79 already does.
- [A future change of `DIST_K`/`DIST_WEIGHED_MAX` in `aperv-tool` would make the compact documents already written insufficient for the derive.] → The parity test fails first. Each compact document records its own `weighedMax`/`k`, so a stale corpus can be identified.
- [Converter memory on the largest document.] → D6; the peak is measured on sdmse during the apply.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit (Java) | `TargetDistances.compact`: spec examples, ties, < 3 pairs, empty; marker writer bytes | JUnit 4, `client/src/test/.../reach/`, `.../json/` | ~8 |
| Unit (Python) | serialiser vs. Gson escapes; converter member order, marker position (with and without `distanceTargets`), pair order by `i`, refusals, atomic write; config/CLI flag | pytest in `modules/rv-static-analysis/tests/` | ~15 |
| Parity | constants equal in three places | `tests/parity/test_distance_pair_constants.py` | 1 |
| Equivalence | parser model and derive bytes, full vs. compact: on the `cryptoapp.apk.json` fixture (converted), and on 5 E6 documents including wikipedia (converted, outputs off the rep pack, read-only input) | pytest (fixture) + a scratch script (E6) | 1 + 5 APKs |
| E2E (host GATOR) | `cryptoapp.apk`: old jar vs. new jar `fullOutput=true` (INV-ANA-86); new jar compact vs. converter(full) (INV-ANA-87) | `rv-static-analysis analyze` on the host, 1 APK, small heap | 3 runs |

All pytest runs use `--import-mode=importlib -o "addopts="`. Java tests run from the reactor root with JDK 21 and **without** `-DskipTests`.

## Open Questions

None. The output modes, the full-mode identity, the marker and the converter were decided by the author on 2026-10-10 (#125).
