<!-- Single-module change (aperv-tool), 2 files touched. No subagent orchestration needed.
     Sequential: Group 1 (compaction fn) -> Group 2 (flow wiring) -> Group 3 (E2E) -> Group 4 (close-out).
     Group 3 requires an emulator and the redreader APK — it is the only group that cannot run offline. -->

## 1. Compaction Function

- [x] 1.1 Add `_compact_static_analysis_json(source_path: str) -> str | None` to `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`: `json.load` → dedup `transitions` by whole-entry canonical equality preserving first-occurrence order (D4, D5) → `json.dump` with `separators=(",", ":")` into `tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False)`; return the temp path
- [x] 1.2 Wrap the body in `try/except (json.JSONDecodeError, OSError, MemoryError)`: log a warning naming the source path and cause, remove any temp file already created, return `None` (INV-APV-24); never raise
- [x] 1.3 Add unit test: dedup on `[A, B, A, C, B]` yields exactly `[A, B, C]` (INV-APV-22)
- [x] 1.4 Add unit test: all seven top-level keys (`package`, `mainActivity`, `components`, `reachability`, `windows`, `transitions`, `complete`) survive, and every value other than `transitions` is unchanged (INV-APV-21)
- [x] 1.5 Add unit test: output has no pretty-print whitespace and re-parses to the same document modulo `transitions` dedup
- [x] 1.6 Add unit test: source file is byte-identical after the call (INV-APV-20)
- [x] 1.7 Add unit tests for the degenerate inputs: no `transitions` key (key is not added); `transitions: []` (stays `[]`)
- [x] 1.8 Add unit test: malformed JSON returns `None`, logs a warning, raises nothing, and leaves no temp file behind (INV-APV-24, INV-APV-25)
- [x] 1.9 Add unit tests for the other two caught legs of INV-APV-24, which the design's Error Handling table maps with distinct recovery semantics: `OSError` on temp write (patch `NamedTemporaryFile` to raise) and `MemoryError` on `json.load` (patch `json.load` to raise) — each returns `None`, warns, leaves no temp file
- [x] 1.10 Run `/rv-doc-code modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` — **skill não executada por instrução do usuário (2026-07-16)**
- [x] 1.11 Run `/rv-test-run aperv-tool`

## 2. Execution Flow Wiring

- [x] 2.1 Rewrite Step 1c of `execute_tool_specific_logic()` (`tool.py:773-793`, normative flow step 4 in the spec) per design "Step 1c call shape": compact → `push_path = compacted or static_json` → push → `finally: os.unlink(compacted)` if a temp was made (INV-APV-25); leave the not-found warning branch unchanged
- [x] 2.2 Verify `mop_json_pushed = True` is set on both the compacted and the fallback path, so `ape.mopDataPath` is emitted identically either way
- [x] 2.3 Add unit test: with `mop_data="static_analysis"` and a valid source, the path handed to `_push_file_to_device` is the temp, not the source (mock the push, assert the argument)
- [x] 2.4 Add unit test: when compaction returns `None`, the source path is pushed and `ape.properties` still contains `ape.mopDataPath=/data/local/tmp/static_analysis.json`
- [x] 2.5 Add unit test: with `mop_data` unset (`sata`, `ape_pure`), no compaction is attempted and no static analysis JSON is pushed
- [x] 2.6 Add unit test: no temp file survives the call on either the success or the fallback path (INV-APV-25)
- [x] 2.7 Add unit test: a small (100 KB) JSON is compacted anyway — no size gate on the call path (INV-APV-23)
- [x] 2.8 Add unit test for the assertion added to the retained not-found scenario: with `mop_data="static_analysis"` and NO JSON in `results_dir`, no compaction is attempted (assert `_compact_static_analysis_json` is never called) and the existing warning is emitted — distinct from 2.5, which covers `mop_data` unset
- [x] 2.9 Run `/rv-test-run aperv-tool`

## 3. Empirical Validation (requires emulator)

- [x] 3.1 Offline check: run the compaction function against `org.quantumbadger.redreader_117.apk.json` (50.6 MB) and assert output ≈ 21.0 MB with exactly 7,124 `transitions` entries, below the ~32 MB ceiling
- [x] 3.2 Single-APK E2E: `rv-experiment run` on `redreader` with `aperv:sata_mop_act_frontier`; assert the trace contains `[APE-MOP-DATA] status=loaded` and more than 0 `[APE-STEP]` markers — this is the acceptance evidence that the fairness gap is closed (rv-platform manages the emulator; do not start it manually) — **PASS (2026-07-16)**: `status=loaded ... transitions=7124`, 79 `[APE-STEP]`, trace 1.113.829 bytes; baseline pré-change no mesmo APK (cmpma_02) era `status=rejected reason=too-large size=50615217` com 0 steps e trace de 1.460 bytes. Executado via `docker/docker-compose.gh80.yml` com bind-mount de `tool.py` sobre a img 0.9.2 (a imagem é buildada do branch git e não continha a change).
- [x] 3.3 Confirm in the same run that `<results_dir>/org.quantumbadger.redreader_117.apk.json` is still 50.6 MB and byte-identical (INV-APV-20 under real execution) — **PASS**: `results_dir` JSON em 50.615.217 bytes com SHA-256 `e3c09283a049da22b91d52222557143fb4f5f5545dca954b518ba18ce8674e9c`, idêntico ao baseline pré-run e ao dataset fonte. Nenhum temp `.json` vazado (INV-APV-25).
- [~] 3.4 Sanity check on a normal APK (e.g. `br.unb.cic.cryptoapp`): MOP arm still loads data and explores, confirming no regression on the common path — **DESCOPADA por decisão do usuário (2026-07-16): validar apenas `org.quantumbadger.redreader_117`, não usar cryptoapp.** (`apks_examples/cryptoapp.apk` não tem JSON de static analysis pareado nem pertence ao set dos 181, logo o braço MOP rodaria sem MOP data e não validaria o caminho alterado.)
- [x] 3.5 Record the observed `[APE-MOP-DATA] transitions=N` value before/after for the reproducibility caveat (NFR08) — it will report the unique count from now on — **Medido**: no `redreader` não existe valor pré-change (o arquivo era rejeitado antes do parse, logo nenhum `transitions=N` era emitido); pós-change reporta 7124. Survey nos 181 JSONs do cmpma: 130 têm `transitions>0` e **27 contêm duplicatas** (logo o campo muda nesses 27 e é idêntico nos outros 103). Outlier: redreader 70,7%; segundo maior `dev.ukanth.ufirewall` 30,2%. Registrado em `modules/aperv-tool/CLAUDE.md` (Gotchas).

## 4. Integration & Verification

- [x] 4.1 Run `/rv-qa-lint-fix aperv-tool` — **skill não executada por instrução do usuário (2026-07-16)**
- [x] 4.2 Run `/rv-verify aperv-tool` — **skill não executada por instrução do usuário (2026-07-16)**
- [x] 4.3 Invoke `/rv-code-reviewer` via Skill tool — **skill não executada por instrução do usuário (2026-07-16)**
- [x] 4.4 CLAUDE.md atualizada manualmente (**skill `/rv-docs-sync` não executada por instrução do usuário**) — `modules/aperv-tool/CLAUDE.md` "Configuration Flow" step 2 currently says "MOP variants: pushes static-analysis JSON to `/data/local/tmp/static_analysis.json`"; it needs the compaction step and the temp-file/source-preserved distinction
- [x] 4.5 Record the NFR08 telemetry caveat where it can be acted on later: add it to `modules/aperv-tool/CLAUDE.md` Gotchas (`[APE-MOP-DATA] transitions=N` now reports the unique count; do not compare that field across campaigns spanning this change). Writing it into a future campaign report is out of scope for this change
- [ ] 4.6 Check off every acceptance criterion in issue #80, then close it with `closes #80` in the final commit and move the board card to Done
- [ ] 4.7 Run `/opsx:verify` then `/opsx:archive` for `gh80-compact-static-analysis-json`
