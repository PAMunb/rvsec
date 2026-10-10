GitHub Issue: #125

## Why

The static-analysis documents of Study 03's E6 corpus (`rvsec-study03-replication-package/data/raw/e6-static-analysis/final/`, 163 APKs, analysed on 2026-10-09) take **24.6 GB**: `eu.darken.sdmse_10705000` is 9.34 GB, `org.wikipedia_50595` 2.16 GB, `at.techbee.jtx_216000015` 2.02 GB, and the median is 4.4 MB. Two things GATOR writes make up almost all of it:

- **Every distance pair up to `d = 10`.** Since gh120 (#120) each app method carries `targetDistances`, its `[i, d]` pair to every target within ten calls. Across the 163 documents that is 358.5 million pairs. The only consumer of the pairs, the `aperv-tool` derive of the MOP artifact (gh122), keeps per method the pairs at `d ≤ DIST_WEIGHED_MAX = 3` and the `DIST_K = 3` nearest targets. 8.11 million of them (2.3 %) meet that rule. gh123 already applies the same reduction while reading (`PairPolicy.reduce` in `rv_android_core/util/analysis_document.py`). That reduction is exact for the derive: a dropped pair has `k` targets ahead of it in its own method, and they stay ahead of it after any merge by the minimum.
- **Two-space indentation** (`JsonWriter.setIndent("  ")`). An indented pair spans four lines and about 70 bytes, against 6 bytes for `[0,8],`.

Measured on 2026-10-10 by streaming the 163 documents and re-serialising them without whitespace: they take 24.62 GB today, 4.13 GB without indentation with every pair kept, and **1.02 GB** without indentation with the pairs reduced. For example, sdmse goes from 9,335 MB to 54.6 MB, wikipedia from 2,160 MB to 22.9 MB, jtx from 2,018 MB to 11.3 MB, and `com.apps.adrcotfas.goodtime_348` from 161 MB to 3.6 MB. gh123 made the size bearable for the readers, which stream the document. The size is still paid when GATOR writes the document, when the campaign copies it into each task, when each task computes its SHA-256, and in the replication package that stores it.

## What Changes

The author's decisions of 2026-10-10 (#125):

- **Compact output is GATOR's default.** `RvsecAnalysisClient` writes the document without indentation. Each method's `targetDistances` holds the pairs at `d ≤ 3` and the 3 nearest targets by `(d, i)`, sorted by `i` as today. `distanceTargets` is written whole, because it is the index space. The compact document carries a top-level marker `distancePairs: {weighedMax: 3, k: 3}` that records the reduction. Both writes use the mode: the pre-WTG write and the final write.
- **Full output on request.** The client parameter `fullOutput=true` makes GATOR write today's document: indented, every pair up to `d = 10`, no marker, byte for byte up to `transitions`, whose edges are the same and come in identity-hash order. The JSONs already published can therefore be reproduced.
- **`rv-static-analysis` exposes the choice.** `RVStaticAnalysisConfig.full_output` (default `False`) and `--full-output` on `analyze` and `batch` append `-clientParam fullOutput=true` to the GATOR command.
- **Offline converter.** A new `rv-static-analysis compact <full.json> <out.json>` subcommand reads a full document in streaming, with the gh123 reader and its reduction. It writes the document GATOR would have written in compact mode from the same analysis: same members and order, same marker, same reduced pairs sorted by `i`, and Gson's compact serialisation. It refuses a truncated or already compact input and never writes over its input.
- **The reduction constants are pinned across languages.** The Java constants, `aperv-tool`'s `DIST_WEIGHED_MAX`/`DIST_K` and the converter's constants are checked equal by a parity test beside `tests/parity/test_json_keys.py`. The marker keys enter `JsonSchema.Keys` and `_JK` (INV-ANA-32).

**Not in this change:** the `windows` and `transitions` sections (the largest compact document, `org.fossify.calendar_20`, keeps 267 of its 269 MB in 525 windows); the format of the MOP artifact (gh122); the readers in `rv-platform` and the streaming reader (gh123), beyond receiving a smaller document; re-analysing or converting the corpus; the Docker image; the replication package; `rv-experiment` and `scripts/static_analysis_sweep.py`, which get the compact default without a new option.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `analysis`: GATOR's output gains the compact (default) and full modes and the `distancePairs` marker. "Per-Target Call-Graph Distance" states which pairs each mode writes. "Shared JSON Schema Keys" gains the marker keys. "Full JSON Remains the Sole Metric Input" makes clear that "full JSON" names the analysis document in either output mode. Two requirements are added: one for the output modes and one for the offline converter.

## Impact

- **Modules:** `rvsec-gator` client (`JsonReportWriter`, `RvsecAnalysisClient.writeReachabilitySection`, `TargetDistances` constants, `JsonSchema.Keys`); `rv-static-analysis` (`config.py` command, `__main__.py` option and `compact` subcommand, a new converter module, `_JK`); `tests/parity` (constants parity). `aperv-tool`, `rv-platform`, `rv-coverage`, `rv-agent` and `rv-android-core` are unchanged in code.
- **Cross-module interface:** the `.apk.json` contract changes in its default form: no whitespace, reduced `targetDistances`, and one new top-level member. `read_analysis_document` and `StaticAnalysisParser` read both forms, and the parsed `StaticAnalysisData` is the same for both, because the parser discards the pairs (INV-ANA-80). The MOP artifact derived from a compact document is byte-identical to the one derived from the full document of the same analysis apart from its `source` object, which names the input file, because the gh123 reduction is exact.
- **Readers that count pairs:** offline scripts that count or rank pairs beyond the reduction need a full document. Example: the replication package's `docs/tmp/sa_quality_20261009/` scripts. The marker tells them which kind of document they hold.
- **Build:** the GATOR jar is rebuilt and installed into `lib/gator/`. The image is rebuilt by the campaign session, outside this change.
- **FR/NFR:** FR04/FR06 (GATOR output), NFR05 (configurable output mode), NFR08 (full mode reproduces published documents).
