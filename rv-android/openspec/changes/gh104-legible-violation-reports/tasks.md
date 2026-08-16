<!-- Subagent dispatch hints (this change touches ~70 files across two repositories):
     - Read design.md D-12 first. Every group heading below points to tasks/<GROUP>.md — the per-group
       execution file with the exact file inventory, per-site tables, commands, expected values and the
       subagent brief. A subagent dispatched for a group reads ONLY its group file (plus the spec deltas it
       cites); the orchestrator reads only this file and ticks the boxes here, immediately after each task.
     - Wave 1 (parallel, disjoint file sets, five subagents): Group 1 (E0 baseline: scripts/ + data/gh104/ + docs/),
       Group 2 (S seed: rvsec-mop/jca_v2/ + rv-experiment + data/jca_v2/), Group 3 (E2 weaver: Java dexlib2 only),
       Group 4 (E3 transport: rvsec-core collectors, rv-monitor-rt, rv-coverage, rv-android-core, rv-platform,
       aperv-tool), Group 5 (EV validation: NEW files only — tests/parity/, scripts/gh104_*, rvsec-mop/src/test).
     - Group 6 (E1 messages) starts as soon as Group 2 has committed the seed; it edits only jca_v2/*.mop and
       codes.csv; run it as TWO subagents on disjoint file halves (6.a files A–K, 6.b files M–T; see tasks/E1-messages.md).
     - Group 7 (E4 automata) starts after Groups 5 AND 6 are complete (hard prerequisite: the gates and the harness
       must exist, and the bookkeeping invariant must be installed). Per file, one owner at a time; two subagents on
       disjoint file halves are allowed only if each appends to its own section of data/jca_v2/divergence_record.csv.
     - Group 8 (E5 predicates) after Group 7. Group 9 (E6 identity) after Groups 4 and 6 — it may overlap 7/8
       (rvsec-core ErrorSummary + Python; no .mop file).
     - Group 10 (integration & verification) last, after everything.
     - Critical path: 2 -> 6 -> 7 -> 8 -> 10. Groups 1, 3, 4, 5 are off the critical path.
     - Never start, stop or manage an emulator by hand. Task 10.4 is the only device task and it runs
       `rv-experiment run`. Everything else is JVM/pytest/scripts.
     - Tests: `uv run pytest --import-mode=importlib -o "addopts=" <path>`. Java: `mvn -q test` inside the
       submodule under ../rvsec/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/ (never at the reactor root
       without -pl). Monitor generation needs RVSEC_HOME and TMPDIR off tmpfs. -->

## 1. E0 — Baseline and definitions (`tasks/E0-baseline.md`)

- [ ] 1.1 Write `scripts/gh104_baseline.py`: reads `experimento-comp162/results/*/*/errors.csv` through `aperv_tool.analysis.violations.read_errors_csv` (11-column header accepted only until Group 4 lands — pin the pre-change reader by import path in the script header) and the article dataset through a declared 10-column reader in the same file; every definition (mute row, site 4-tuple vs 3-tuple, nine-prefix classifier, shard) is a required freeze item (`FreezeItemUnset` if absent); every number leaves as an `Envelope` (value, numerator, denominator, definition id)
- [ ] 1.2 Reproduce and record in `data/gh104/baseline.md`: article 97,018 / 19 messages / 70,760 `unknown` = 72.93 % / 8,843 `but found .`; comp162 19,664 / 15,714 mute / 296 sites / 101 mute-legible twin sites (3,950 rows) / 12 mute-mute (838) / per-spec mute top-8 / third-party 78.49–82.67–85.44 % under the three prefix lists; identities 6,344 (five-field) — each with its command
- [ ] 1.3 Register the definitions and the instrument discontinuity (the article dataset has no `source`; `read_errors_csv` rejects it by design) in `data/gh104/definitions.md`
- [ ] 1.4 Add `tests/parity/test_gh104_baseline.py::test_baseline_reproduces_byte_identical` (rerun → identical `baseline.json`) and `::test_freeze_items_required`
- [ ] 1.5 Run `/rv-test-run tests/parity/test_gh104_baseline.py`

## 2. S — Seed the successor set `jca_v2` (`tasks/S-seed.md`)

- [ ] 2.1 Copy `../rvsec/rvsec/rvsec-mop/src/main/resources/jca/` → `jca_v2/` byte-identical (23 files, 1,912 lines); add `jca_v2/codes.csv` with header only; commit as one hunk-free seed
- [ ] 2.2 Register `"jca_v2"` in `modules/rv-experiment/src/rv_experiment/config.py` (`valid_spec_sets`, directory mapping) and the `click.Choice` of `--specification-set` in `rv_experiment/__main__.py`; add the JIT-config test `test_jca_v2_selectable_by_name` and the invalid-value test listing five sets
- [ ] 2.3 Create `data/jca_v2/{divergence_record.csv, conformance_record.csv, gate_allowlist.csv, predicate_omissions.csv}` with headers, and `scripts/gh104_divergence_record.py` (parametrised copy of `scripts/gh101_divergence_record.py`: base = `jca/`, target = `jca_v2/`, `--check` fails on an unrecorded hunk)
- [ ] 2.4 Add `tests/parity/test_gh104_specset_gates.py::test_jca_v2_hunks_all_recorded` and `::test_jca_v2_seed_is_byte_identical_plus_codes` (passes on the seed); confirm the existing five gh101 gates still pass
- [ ] 2.5 Run `/rv-test-run modules/rv-experiment` and `/rv-test-run tests/parity`

## 3. E2 — Weaver `args()` arity (`tasks/E2-weaver-arity.md`)

- [ ] 3.1 Red test first (INV-INS-108 discipline): in `advice-emitter/src/test/.../WrapperMergeTest.java` add `argsArityExcludesTheTwoArgumentAdviceFromTheOneArgumentWrapper` (advice `args(alg)` + advice `args(alg, provider)` over `getInstance(String)` → wrapper fires one) and `advicesWithoutArgsClauseAreNeverFiltered` (the 13 wrapper-path no-`args()` advices of the frozen descriptor survive); commit the red output under `evidence/`
- [ ] 3.2 Implement the three-clause rule in `WrapperEmitter.generate` grouping loop (`:246-274`, write at `:270-273`): read `ArgsPC` from the parsed expression, `types()` length with `trailingRest`/`headCount` semantics, absent `args()` = admit; return an `EmitResult` carrying `advicesExcludedByArity`
- [ ] 3.3 Plumb the counter: `cli/.../BatchRunner.java:199-201` puts `advicesExcludedByArity` in `counts` beside `wrappersGenerated`; `ResultsJsonReportingTest` asserts the key; `modules/rv-instrumentation-dexlib2/.../dexlib_instrumentation.py::_parse_results_json` surfaces it into `weave_counts`; Python test
- [ ] 3.4 Add `argsTrailingRestAdmitsLongerOverloads` (`args(transformation, ..)` on a two-parameter call) and keep `EmissionParityTest`, `EmissionCardinalityTest`, `WrapperRegistryGuardTest`, `WrapperEmitterTest`, `MonitorCallsPremiseContractTest` green (`mvn -q test` in `advice-emitter`, `cli`, `dex-mutator`, `validator`)
- [ ] 3.5 Re-weave the frozen `jca` descriptor (`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json`) and record `advicesExcludedByArity` and `wrappersGenerated` before/after in `evidence/e2_reweave.md`; rebuild `lib/` jars from the reactor root (`mvn -q install -DskipTests -DskipMopAgent=true`, ~12 min) and record the sha256 of `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar`
- [ ] 3.6 Run `/rv-verify rv-instrumentation-dexlib2`

## 4. E3 — Honest transport (`tasks/E3-transport.md`)

- [ ] 4.1 Logcat `ErrorCollector.java` (`rvsec-android/rvsec-logger-logcat`): enable escaping (`\n`→`\\n`, keep commas), `null` expecting → sentinel envelope; align the CSV collector's `escape()`; new `ErrorCollectorTest` (newline, null, comma)
- [ ] 4.2 `ViolationRecorder.makeRelevantList` (`rv-monitor-rt`, `:87-105`): a monitoring-runtime frame with `fileName == null` is excluded, not included; new `ViolationRecorderTest`
- [ ] 4.3 `rv-coverage` `logcat_parser.py`: `ParserDiagnostics` with the 13 counters carried on `LogcatRepository.parser_diagnostics`; envelope fields on `RvErrorLog` (`code, event, obj, val, exp, msg, truncated`); sentinels; unclosed quote → truncated; Format-1 regex failure no longer falls into the comma path; `parse_logcat_file` re-raises with the line number; property tests (`,`, `\'`, `\n` split → `continuation_lines`, `:::`, 4068-byte cut) in `test_logcat_parser.py`
- [ ] 4.4 `rv-android-core` `domain/log.py`: `unique_msg` = seven parts with `code`/`event` (sentinel `UNSPECIFIED`); `test_log.py` updated; grep gate `tests/parity/test_gh104_unique_msg_built_once.py` (only `log.py:RvErrorLog.unique_msg` composes it)
- [ ] 4.5 `rv-platform` `result_processor.py`: 13-column `errors.csv` header (`…,source,code,event,message,unique_msg`); delete the three `unique_msg` fallbacks (`:631,:999,:1038`); count write failures (`:654-655,:1046-1047`) into the task result and log as errors; `test_result_processor.py` header + failure tests
- [ ] 4.6 `aperv-tool` `analysis/violations.py` + `clock_logcat_join.py`: `ERRORS_CSV_HEADER` 13 columns; `unique_msg` seven parts (`code=parts[4]`, `event=parts[5]`); `parse_payload` reads the envelope, `shape_ok=False` + `envelope_truncated`/`envelope_malformed` counters; one payload parser for bundle and run join; `test_violations.py` (+4); update the sha256-pinned fixture manifest only if a fixture changes (it should not — cmp162 stays 11-column and is read by the E0 reader, not here)
- [ ] 4.7 Delete the other `unique_msg` constructors: `scripts/regenerate_results/regenerate_container.py:244` → import from core; fix `scripts/rv_oracle_common.py:73-81` to require seven parts
- [ ] 4.8 Consumer matrix `data/gh104/consumer_matrix.md`: every reader of `message`/`unique_msg`/`errors.csv` named with its verdict (migrated / frozen-with-reason): `logcat_parser`, `log.py`, `result_processor`, `violations.py`, `clock_logcat_join.py`, `rv_oracle_common.py`, `regenerate_container.py`, `TraceComparator.parseObserved`, `validator/oracles/cryptoapp-oracle.yaml`, `ase-journal/docs/20260806_owasp_cwe_mapping_gen.py:47-54` (frozen: reads the published dataset), `experimento-gov/scripts/consolidate_gov.py:26-37`, `.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py:35`, `scripts/gh91_compare_consolidation.py`
- [ ] 4.9 Run `/rv-qa-lint-fix rv-coverage`, `/rv-test-run modules/rv-coverage`, `/rv-test-run modules/rv-android-core`, `/rv-test-run modules/rv-platform`, `/rv-test-run modules/aperv-tool`

## 5. EV — Validation toolkit (`tasks/EV-validation.md`)

- [ ] 5.1 `scripts/gh104_gates.py`: reuse `gh101_monitor_transition_check.py`'s parser (both monitor shapes) and add G-2a, G-2b′, G-2c, G-2d, G-6′; `--allowlist data/<set>/gate_allowlist.csv`; JSON report
- [ ] 5.2 `tests/parity/test_gh104_specset_gates.py`: parametrised over `jca` (frozen control monitor: expect G-2 18 in 10 specs, G-2a 1 `SecretKeySpec.e1`, G-2b′ 8, G-2c 1, G-2d 2, G-6′ 1 `GCMParameterSpecSpec`) with `data/jca/gate_allowlist.csv` naming them, and over `jca_v2` (generated in scratch, `RVSEC_HOME`); a gate reporting fewer than the `jca` baseline fails
- [ ] 5.3 `.mop` lint `scripts/gh104_mop_lint.py` + test: undeclared ERE/FSM symbol (`GCMParameterSpecSpec:48` `c2`), duplicate event name (`GCMParameterSpecSpec:23,34`), unbalanced parentheses (`SecretKeySpecSpec:27-30`), missing bookkeeping first statement (INV-INS-120), three-argument `ErrorDescription` (INV-INS-119), reserved generator names in declarations; on the frozen `jca` the lint must report exactly the known hits and pass on `jca_v2` only after Group 6
- [ ] 5.4 Message-property gate `scripts/gh104_message_gate.py` + test: numeric literals of a message equal those of its guard (INV-INS-121), `codes.csv` bijective with sites, `ErrorType` matches the site kind; on the frozen `jca` it must list `PBEKeySpecSpec:50`, `PBEParameterSpecSpec:50` (1000 vs 10000) and the 25 three-argument sites
- [ ] 5.5 Differential harness: `rvsec-mop/src/test/java/.../TraceRunner.java` (loads a generated `MultiSpec_1RuntimeMonitor` class set, replays a trace file of `spec event(args)` lines, records accusation/event/envelope), `scripts/gh104_diff_harness.py` (generate two snapshots in scratch, run, classify `moved`/`removed`/`unchanged`), `traces/<spec>.txt` for the 23 specifications (≥1 legitimate sequence, 1 per authored violating branch, the audit's separating traces)
- [ ] 5.6 Harness self-test: `jca` vs `jca_android` on `TrustManagerFactorySpec` (`getInstance("X509"); init(ks)` — accusation at `getInstance` before, `init` after → `moved`); commit under `evidence/harness/selftest.md`
- [ ] 5.7 Run `/rv-test-run tests/parity`

## 6. E1 — Legible messages in `jca_v2` (`tasks/E1-messages.md`) — after Group 2; two subagents by file halves

- [ ] 6.1 Lying-message census applied first (precondition, INV-INS-121): `PBEKeySpecSpec:50` and `PBEParameterSpecSpec:50` (`1000`→`10000`), `PBEParameterSpecSpec:49` (`UnsafeAlgorithm`→`UnsatisfiedConstraint`), `PBEKeySpecSpec:24,30` (`InvalidSequenceOfMethodCalls`→`UnsatisfiedConstraint`, forbidden constructor), `SecretKeySpecSpec:48,55` (split algorithm half as `UnsafeAlgorithm`), `MessageDigestSpec:70,92` (list = allow-list `:16`, six entries), `CipherSpec:61,76` (drop the literal `...`; name the utility), `KeyGeneratorSpec:64` and `KeyStoreSpec:68` (space), `MacSpec:62` (verb), `SecretKeySpecSpec:49` (array, not `.length`), leading spaces at `MacSpec:50`, `KeyManagerFactorySpec:55`, `KeyPairGeneratorSpec:72`, `SecretKeySpecSpec:49,56`; note `KeyPairGeneratorSpec:71-72` unreachable (E4 item)
- [ ] 6.2 Field → argument at the 16 field-interpolating `but found` sites (`CipherSpec:61,76`; `KeyGeneratorSpec:64`; `KeyManagerFactorySpec:55`; `KeyPairGeneratorSpec:72`; `KeyStoreSpec:68`; `MacSpec:50,62`; `MessageDigestSpec:70,92`; `SignatureSpec:58,68,78,88`; `SSLContextSpec:58`; `TrustManagerFactorySpec:57`); un-comment and use `MessageDigestSpec:57-58`'s argument form
- [ ] 6.3 Event-name bookkeeping: `String lastEventName = "";` in every declarations block; `lastEventName = "<name>";` as the first statement of all 134 event bodies; `KeyPairGeneratorSpec` `@fail` gains `__RESET`
- [ ] 6.4 Envelopes: the 26 four-argument value sites rewritten to `v=1 code=… ev=… obj=… val='…' exp='…' msg='…'` (val from the bound argument; `val` capped at 512 chars); the 25 three-argument sites (21 `@fail` + `IvParameterSpec:48,55`, `PBEKeySpecSpec:24,30`) get the fourth argument composed from `lastEventName` before `__RESET`, null-guarded; `codes.csv` filled (one row per site, KIND per design D-3)
- [ ] 6.5 Divergence record: one entry per hunk (`scripts/gh104_divergence_record.py --check` green); lint + message gate green on `jca_v2`; G-6′ still reports `GCMParameterSpecSpec` (E4 fixes it) — allowlisted with reason until 7.x
- [ ] 6.6 Generate `jca_v2` monitors in scratch and confirm compilation; harness before/after on every file (seed vs E1) → `evidence/harness/e1-<spec>.md`; classification must be `unchanged` for accusation, changed only in envelope
- [ ] 6.7 Run `/rv-test-run tests/parity`

## 7. E4 — Automata and pointcuts in `jca_v2` (`tasks/E4-automata.md`) — after Groups 5 and 6; per file

- [ ] 7.1 Replay plan: from `data/gh101/divergence_record.csv` list the 94 non-`allow-list` hunks per file, mark the three excluded (`GENCIPHER-EXTRA` — CipherInputStreamSpec/CipherOutputStreamSpec `GENERATED_CIPHER` reads, task 5.1; `SSL-RANDOMIZED-EXTRA` — SSLContextSpec.init `RANDOMIZED` read, task 3.2; `KPG initError` placement) and read the audit's per-spec verdict (`audit/20260808_validacao_jca_android/global/juizglobal_gates.csv`, `set/set_cons_fen_registry.csv`) for each file; write the plan to `data/jca_v2/replay_plan.csv`
- [ ] 7.2 `CipherSpec` (28 hunks: `AndroidCipherTransformationUtil` import; alphabet 17→14; `doFinal` double-fire; `getInstance(String, ..)`; predicate reads/writes minus `GENCIPHER-EXTRA` consumers) — event count after edit ≤ 17 declared; harness before/after; divergence entries
- [ ] 7.3 `MacSpec` (11: `!encrypted` reads, `PREPARED_HMAC`, alphabet 8→11 with `MACED` writes, two-arg `remove`) and `KeyManagerFactorySpec` (5: init split, monitor field, two-arg `remove`) — harness; entries
- [ ] 7.4 `TrustManagerFactorySpec` (8: `g3` binding `k`→`mf` + `unsafeAlg` state; `gtm1` four defects `:62-66`; init split; two-arg `remove`), `SSLContextSpec` (6 minus `SSL-RANDOMIZED-EXTRA`: `returning(SSLContext ctx)` on `unsafe_protocol` + `unsafeProtocol` state; init reads `GENERATED_KEY_MANAGERS`/`GENERATED_TRUST_MANAGERS`; `createSSLEngine` return type `:64`) — harness; entries
- [ ] 7.5 `SecureRandomSpec` (5: `c3`, `g4`, `setSeed3` placed; `unsafeInit`; `g4` overload `:76-79`), `SignatureSpec` (5: `g3` placed; predicate reads; `sign()` return types `:99,:106`), `KeyPairGeneratorSpec` (4 minus placement residual: `initError` placed per audit note; `preparedDH` reads; `String algorithm` initialised `:26`; unreachable `:71-72` branch made reachable or removed), `KeyPairSpec` (5: `gpr` → `GENERATED_PRIVATE_KEY` `:38`; `generatedKeypair`; `c1` reads) — harness; entries
- [ ] 7.6 `KeyGeneratorSpec` (3 + `g3` `:47` tests the argument), `PBEKeySpecSpec` (3: `f1/f2` `returning`; five events via Kleene star), `SecretKeySpecSpec` (3 + parentheses `:27-30`; `c3/c4` placed; `SPECCED_KEY`), `KeyStoreSpec` (2), `IvParameterSpec` (1: `c3/c4` placed), `PBEParameterSpecSpec` (1: `c3` placed), `MessageDigestSpec` (1: `reset` removed), `GCMParameterSpecSpec` (duplicate `c1` → `c1`/`c2`, `ere` fixed), `SecretKeySpec` (null detector: repair or delete per CrySL, recorded) — harness; entries
- [ ] 7.7 Conformance record `data/jca_v2/conformance_record.csv`: 23 rows, anchor per clause family (api30 availability / 1.5.2 recommendation) per design D-10; gate `test_conformance_record_covers_all_twenty_three` re-pointed at `jca_v2`
- [ ] 7.8 Gates green on `jca_v2`: G-2 = 0 orphans; G-6′ = 0; lint clean; `gate_allowlist.csv` carries every remaining G-2b′/G-2d hit with a reason; `CipherSpec` generates (≤ 17 events, time and memory recorded)
- [ ] 7.9 Run `/rv-test-run tests/parity`

## 8. E5 — Predicates (`tasks/E5-predicates.md`) — after Group 7

- [ ] 8.1 `rvsec-core` `ErrorType`: add `RequiredPredicate`, `ForbiddenMethod`; `codes.csv` KIND `REQ`/`FORB`; Java test
- [ ] 8.2 In `jca_v2`, move every predicate read from `condition()` into the event body reporting `RequiredPredicate` with the automaton co-edited (G-2 stays 0); harness before/after per file; divergence entries
- [ ] 8.3 Missing producers: add `SecretKeyFactorySpec` / `*ParameterSpec` specifications or record each in `data/jca_v2/predicate_omissions.csv` with the CrySL reason; `scripts/gh101_predicate_pairing_check.py` parametrised to `jca_v2` and its pytest green
- [ ] 8.4 Record in `data/jca_v2/README.md` the `ExecutionContext` ruling (equality, `e204e2a4`) and the eight identity-sensitive reads that therefore stay as they are
- [ ] 8.5 Run `/rv-test-run tests/parity`

## 9. E6 — Identity (`tasks/E6-identity.md`) — after Groups 4 and 6

- [ ] 9.1 `scripts/gh104_identity_discontinuity.py`: recompute comp162 identities with `event` (from the envelope where present; sentinel otherwise) next to the five-field 6,344; record both in `data/gh104/identity_discontinuity.md`; if equal, stop and re-open design D-5
- [ ] 9.2 `rvsec-core` `ErrorSummary.equals/hashCode` += `code`, `event`; `ErrorDescription` carries them; `ErrorDescriptionTest.hashCodeMatchesEquals` rewritten for seven fields; logcat collector emits them in the envelope (already) — no line-format change
- [ ] 9.3 Confirm `errors.csv` `code`/`event` columns and `unique_msg` parts (Group 4) are fed from the collector line end to end with a recorded logcat fixture; declare the era in `data/gh104/identity_discontinuity.md`
- [ ] 9.4 Rebuild `lib/` jars; run `/rv-test-run modules/rv-coverage` and `/rv-test-run modules/aperv-tool`

## 10. Integration and verification (`tasks/E10-integration.md`)

- [ ] 10.1 Freeze and divergence: existing gh101 five gates green; `test_gh104_specset_gates.py` green on `jca` and `jca_v2`; `jca/` byte-identical to `7e7acb69`
- [ ] 10.2 Run `/rv-qa-lint-fix rv-coverage`, `/rv-qa-lint-fix rv-platform`, `/rv-qa-lint-fix aperv-tool`, `/rv-qa-lint-fix rv-android-core`, `/rv-qa-lint-fix rv-experiment`
- [ ] 10.3 Run `/rv-verify rv-coverage`, `/rv-verify rv-platform`, `/rv-verify aperv-tool`, `/rv-verify rv-android-core`, `/rv-verify rv-experiment`, `/rv-verify rv-instrumentation-dexlib2`
- [ ] 10.4 Device validation, one task, via `uv run rv-experiment run --tools monkey --specification-set jca_v2 --timeouts 180 --apks-dir <dir with com.owncloud.android_48000100, eu.opencloud.android_9, de.luhmer.owncloudnewsreader_196, com.etesync.syncadapter_20700>`: record `unknown` = 0, `but found .` = 0, envelope fields populated, `advicesExcludedByArity` in results JSON, parser counters, in `evidence/device_validation.md` (the platform manages the emulator; no manual emulator command)
- [ ] 10.5 Invoke `/rv-code-reviewer` via Skill tool
- [ ] 10.6 Run `/rv-docs-sync rv-coverage`, `/rv-docs-sync rv-instrumentation-dexlib2`, `/rv-docs-sync aperv-tool` if module docs need updating; update `openspec/specs/experiment/spec.md:87` sample comment at sync time
