GitHub Issue: #123

## Why

gh120 (#120) put every app method's distance to every monitored target in the static-analysis document (`reachability[].methods[].targetDistances`), and the documents grew 100 to 400 times: `org.wikipedia_50595.apk.json` went from 15 MB to 2.16 GB, `at.techbee.jtx_216000015` from 8.9 MB to 2.02 GB, `eu.darken.sdmse_10705000` from 24 MB to 9.34 GB. Every reader of that file at run time loads it whole. In the `e03mini-smoke` run of 2026-10-09 (image `phtcosta/rvandroid:0.9.5` `a2090dac`, 10 GiB containers, `docs/20261009_e03mini-smoke.md`) two containers were OOM-killed (exit 137) in their **first task, the plain `ape` arm**, inside `StaticAnalysisParser.parse_file`: wikipedia went from 3.0 to 10 GiB in about seven seconds of parsing, and sdmse spent 100 s copying its document before the parse killed it. A container with the emulator and a small app already holds 6.3–6.7 GiB, so the parse has about 3 GiB left.

The bytes that do the damage are the ones nobody on this path keeps. `_load_json` reads the file into one string and calls `json.loads` (`static_analysis_parser.py:334-337`), which materialises every `[i, d]` pair as a Python list; the parser then builds `StaticAnalysisData` without them. Coverage reads seven fields per method, `componentType`/`isMain` per class and `codePackage` (`repository_initializer.py:52-71`). And the work is repeated: `StaticAnalysisComponent` copies and parses the document in every task of an APK (`static_analysis.py:120-137`, `:195-209`), `ResultProcessorComponent` parses it once more per APK at the end (`result_processor.py:401-429`), and the `aperv-tool` derive, on a cache miss, `json.load`s it again at 3.1 times its size (gh122 task 7.7) — about 29 GB for sdmse. Without a fix neither sdmse nor wikipedia can run in any arm of the e03mini comparison or of Study 03's E6 campaign.

## What Changes

The author's decisions of 2026-10-09 (#123):

- **Streaming parse.** `StaticAnalysisParser` reads the document with `ijson` (C backend `yajl2_c`) section by section, discarding `distanceTargets` and `targetDistances` as it goes, and returns the same `StaticAnalysisData` it returns today. Truncated documents keep today's contract — every section that was fully written is recovered and `complete` is `False` — through the same `_recover_truncated_json` entry point.
- **Parsed-document cache beside the source.** `read_static_analysis_files(results_dir, apk)` writes, on its first read, `<apk_name>.static.json` next to `<apk_name>.json`: the same document without the two distance members, plus a `source` record (`digest`, `generator`). It reuses it while the recorded digest equals the SHA-256 of the current source, and regenerates it otherwise. Later tasks of the APK and `ResultProcessorComponent` read the small file. Because it is the source document minus members no consumer of `StaticAnalysisData` reads, parsing it yields the identical model.
- **Streaming derive.** `ApeRVTool._derive_mop_artifact` no longer `json.load`s the document. It streams it and keeps, per method, only the distance pairs the format-2 artifact can use: every pair at `d ≤ DIST_WEIGHED_MAX` and the `K` nearest (for `activityDist`). The artifact SHALL be byte-identical to today's derivation of the same document.
- **The task copy is skipped when it would copy the same file.** `copy_static_analysis_files` copies with `shutil.copy2` (preserving mtime) and skips a file whose destination already has the same size and mtime. The document stays in the task directory, where resume and result processing look for it.
- **Spec amendments:** `analysis` — the metric paths read the full JSON or its digest-matched parsed copy, the device-only-consumer requirement names the streaming read as the place an unparseable document fails, and two requirements are added (streaming parse, parsed-document cache); `platform` — a requirement for the skipped copy; `aperv` — the derive's generation-and-caching requirement reads in streaming.

**Not in this change:**
- the shape of the document GATOR writes;
- `rv-agent` / `rv-screen-parser`, beyond receiving the same `StaticAnalysisData`;
- offline scripts (`consolidate_compare.py` `static_covariate`, `gen_compare.py --filter-abi`, `analysis/static_artifact.py`), which keep reading whole documents on the host.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

- `analysis`: the parser reads in streaming and caches its parsed copy keyed by the source digest; "Full JSON Remains the Sole Metric Input" admits the digest-matched copy; "Derived MOP Artifact as a Device-Only Consumer" names the streaming read as the failure point for an unparseable document.
- `platform`: the per-task copy of the static-analysis files preserves mtime and is skipped when the destination is identical.
- `aperv`: "Derived MOP Artifact Generation and Caching" parses the document in streaming and reduces distance pairs on the fly, with a byte-identical artifact.

## Impact

- **Modules:** `rv-static-analysis` (parser, cache, new dependency `ijson`), `rv-platform` (`components/static_analysis.py` copy), `aperv-tool` (`tool.py` `_derive_mop_artifact`, `derive_mop_artifact.py` reading entry point; dependency `ijson`). `rv-android-core` gains the `.static.json` extension constant. No change to `rv-coverage`, `rv-agent`, `rv-screen-parser`, which receive the same `StaticAnalysisData`.
- **Cross-module interface:** `static_analysis_parser.read_static_analysis_files(results_dir, apk)` keeps its signature; its callers (`StaticAnalysisComponent`, `ResultProcessorComponent`) are unchanged in code. INV-PLT-15 (one parse per APK per `execute()`) and INV-PLT-38 hold as written.
- **Disk:** one `<apk_name>.static.json` per APK per results directory, a few MB (the source without distances).
- **Time:** the first task of an APK in a container pays a streaming pass and one SHA-256 of the source; later tasks pay the SHA-256 (the aperv derive already pays it once per task) and a small parse. The copy of a 9 GB document per task disappears after the first.
- **Campaigns:** the image `phtcosta/rvandroid:0.9.5` is rebuilt after this change; `e03mini-smoke` is re-run on the same five APKs as the acceptance gate.
- **FR/NFR:** FR04/FR12 (static data for coverage), FR19 (aperv derive), NFR02 (robustness: graceful degradation and truncation recovery), NFR04 (resource use).
