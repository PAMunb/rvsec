<!-- Dispatch hints:
     - Group 1 (core reader) must complete first; Groups 2 and 3 depend on it.
     - Groups 2 (parser + cache), 3 (aperv derive) and 4.1–4.3 (platform copy) are independent and can
       run in parallel subagents after Group 1 (4.1–4.3 do not even need Group 1).
     - Task 4.4 needs Group 2. Group 5 (corpus check, peak memory) needs Groups 2 and 3.
     - Group 6 (image + smoke) needs Groups 1–5 and the author's go-ahead to commit and push.
     - Group 7 (lint, verify, review, docs) runs only after the smoke passes (tested code first).
     - Critical path: 1 -> {2, 3} -> 5 -> 6 -> 7. About 15 files in 4 modules: 3 parallel dispatches.
     - Rules: never start emulators by hand (the smoke goes through docker compose / rv-platform);
       corpus documents under rvsec-study03-replication-package/data/raw are read-only and are passed
       to scripts as path arguments; do not json.load a corpus document without checking its size
       (sdmse 9.34 GB); the sum of concurrent host processes' memory stays under ~80 GB; commits use
       `refs #123`, never Co-Authored-By. -->

## 1. Core: streaming reader and digest (design D1, D2, D3)

- [ ] 1.1 Add `ijson` (C backend) to `modules/rv-android-core/pyproject.toml` and the root lock (`uv lock`, `uv sync`); confirm `ijson.backend == "yajl2_c"` in the workspace venv
- [ ] 1.2 RED: `modules/rv-android-core/tests/util/test_analysis_document.py` — the reader equals `json.loads` minus the dropped members on `cryptoapp.apk.json` and `app.notesr_59.apk.json` (copy the fixtures' paths, do not duplicate them); `DROP` omits `distanceTargets` and every `targetDistances`; `reduce(3, 3)` keeps exactly the pairs at `d ≤ 3` plus the 3 nearest by `(d, i)` after the per-target minimum (seeded random property test against a reference built from `json.loads`); truncation at each top-level boundary and inside a nested array reports `truncated=True` and keeps only completed members; non-object root and empty file raise `ValueError`
- [ ] 1.3 GREEN: `modules/rv-android-core/src/rv_android_core/util/analysis_document.py` with `read_analysis_document(path, pairs) -> (dict, truncated)`, `PairPolicy` (`DROP`, `reduce(weighed_max, k)`) and `digest_of_file` moved from `aperv_tool/tools/aperv/derive_mop_artifact.py` (same chunk size and output); import-time check of the C backend; `use_float=True`
- [ ] 1.4 Add `EXTENSION_PARSED_COPY = ".static.json"` beside `EXTENSION_STATIC_ANALYSIS` in `modules/rv-android-core/src/rv_android_core/constants.py`
- [ ] 1.5 Run `/rv-doc-code modules/rv-android-core/src/rv_android_core/util/analysis_document.py`
- [ ] 1.6 Run `/rv-test-run rv-android-core`

## 2. Parser: streaming read and parsed copy (analysis delta; design D4, D5, D7)

- [ ] 2.1 RED: in `modules/rv-static-analysis/tests/parser/static/test_static_analysis_parser.py` add `TestStreamingEquivalence` (model from the streaming parser equals the model from today's `json.loads` path on the fixtures and on every baseline under `tests/resources/baselines/`) and `TestParsedCopyCache` (hit, miss, stale digest, truncated source not cached, unwritable directory returns the model and leaves no partial file); adapt `TestTruncatedJSON` to INV-ANA-81 (complete members kept, member in progress dropped) and record in the test docstring which old cases changed outcome and why
- [ ] 2.2 GREEN: `_load_json` calls `read_analysis_document(path, PairPolicy.DROP)`; `_recover_truncated_json` becomes the handling of `truncated=True` (keep the name; log as today); `parse_file` returns the same model; remove the text read and the bracket repair (P3)
- [ ] 2.3 GREEN: `read_static_analysis_files` — digest the source, reuse `<apk>.static.json` when `source.digest` matches, else stream, write the copy atomically (temp in the same directory + `os.replace`) only when not truncated, then build the model; `parse_file` keeps no cache
- [ ] 2.4 Add the INV-ANA-84 audit test `modules/rv-static-analysis/tests/test_static_copy_audit.py`: no module outside `rv-static-analysis` references the `.static.json` suffix (the test itself and `rv_android_core/constants.py` are the permitted matches)
- [ ] 2.5 Update the parser module docstring and `modules/rv-static-analysis/CLAUDE.md` (reader, copy, truncation rule)
- [ ] 2.6 Run `/rv-test-run rv-static-analysis` (including `tests/parity/test_json_keys.py`: `_JK` keeps `targetDistances`/`distanceTargets`)

## 3. aperv-tool: streaming derive (aperv delta; design D3, D7)

- [ ] 3.1 RED: in `modules/aperv-tool/tests/test_derive_mop_artifact.py` add `test_streaming_byte_identical_*` on `cryptoapp.apk.json` and on a synthetic document whose activity's three nearest targets come from pairs beyond `d = 3` in different methods (the case the reduction must keep); in `tests/test_aperv_tool.py` a truncated document raises `RVToolExecutionError` and leaves no artifact
- [ ] 3.2 GREEN: `_derive_mop_artifact` reads with `read_analysis_document(path, PairPolicy.reduce(DIST_WEIGHED_MAX, DIST_K))`, raises on `truncated=True` or `ValueError`, then `derive()` as today; import `digest_of_file` from `rv_android_core.util.analysis_document` and delete the local definition; update every importer (`git grep digest_of_file`)
- [ ] 3.3 Update the `_derive_mop_artifact` docstring (the 3.1× note becomes the streaming read) and `modules/aperv-tool/CLAUDE.md`
- [ ] 3.4 Run `/rv-test-run aperv-tool`

## 4. rv-platform: copy skip and metric equivalence (platform delta; design D6)

- [ ] 4.1 RED: `modules/rv-platform/tests/components/test_static_analysis.py::TestCopySkip` — identical size and `st_mtime_ns` skips and returns `True`; a replaced source (other size or mtime) is copied; a first copy preserves `st_mtime_ns`
- [ ] 4.2 GREEN: `copy_static_analysis_files` uses `shutil.copy2` and the size + `st_mtime_ns` skip (INV-PLT-39); a skip counts as copied
- [ ] 4.3 Run `/rv-test-run rv-platform`
- [ ] 4.4 (after Group 2) `test_result_processor.py::test_csv_identical_with_and_without_parsed_copy`: process the same task twice, once with no `.static.json` and once with the copy present; `summary.csv` and `coverage.csv` byte-identical; `read_static_analysis_files` still called once per APK (INV-PLT-15)

## 5. Corpus check and peak memory (host; design Testing Strategy)

- [ ] 5.1 Write `openspec/changes/gh123-static-json-streaming-cache/corpus_check.py` (paths as arguments, run with `python -I`): for each given document, model equality between the streaming parser and today's `json.loads` path, and byte identity between the streaming derive and `derive(json.load(...))`. Run it on `org.wikipedia_50595`, `at.techbee.jtx_216000015` and three small Study 03 documents from `rvsec-study03-replication-package/data/raw/e6-corpus/` (one process at a time; the `json.load` side of wikipedia needs ~7 GB). Record in `corpus_check.out.md`
- [ ] 5.2 Write `measure_peak_rss.py` and run it under `/usr/bin/time -v`, one process at a time: streaming parse of wikipedia and sdmse; parse of their `.static.json` copies; streaming derive of wikipedia and sdmse. Record peaks, wall times and copy sizes in `measure_peak_rss.out.md`
- [ ] 5.3 If a measured peak contradicts a scenario threshold (3 GiB for the wikipedia parse and the sdmse derive), bring the numbers to the author and amend the specs through `/opsx:update`, not by hand

## 6. Image and smoke (gate before review)

- [ ] 6.1 Read the gates of the first `e03mini-smoke` run on its three finished containers (jtx, saucenao, vault) and record them in `docs/20261009_e03mini-smoke.md` before any cleanup; then remove its containers and move its results aside (`data/results/e03mini-smoke_*` → `data/results/e03mini-smoke-run1/`)
- [ ] 6.2 With the author's go-ahead: commit (`refs #123`) and push `modules`; rebuild `phtcosta/rvandroid:0.9.5` (`docker/rvandroid/build.sh`) and confirm inside the image that `rv_android_core/util/analysis_document.py` is present and `ijson.backend == "yajl2_c"`
- [ ] 6.3 Re-run `docker/docker-compose.e03mini-smoke.yml` (same 5 APKs × 4 arms, 10 GiB, `restart: "no"`) with the memory sampler `data/e03mini-smoke_mem/sample_mem.sh`
- [ ] 6.4 Gates: 20/20 COMPLETED with `execution_time_seconds ≥ 295`; no `OOMKilled`; one `.static.json` per APK and the copy skipped from the second task on (log); `.mop.json` format 2 with `targets > 0`; `dec.mopd` only in `mopd_on_llm_off`; `RVSEC-OCC`/`RVSEC-BIND` present; 0 `VerifyError`; peak container memory per APK from `mem.tsv`. Record in `docs/20261009_e03mini-smoke.md`

## 7. Lint, verification, review and docs

- [ ] 7.1 Run `/rv-qa-lint-fix rv-android-core`, `/rv-qa-lint-fix rv-static-analysis`, `/rv-qa-lint-fix aperv-tool`, `/rv-qa-lint-fix rv-platform`
- [ ] 7.2 Run `/rv-verify` on the same four modules
- [ ] 7.3 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 7.4 Run `/rv-docs-sync rv-static-analysis` and `/rv-docs-sync aperv-tool`
- [ ] 7.5 Check off the acceptance criteria in the body of #123 (`gh issue view` → edit a copy → `test -s` → `gh issue edit --body-file`)
