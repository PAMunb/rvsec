## Context

GitHub Issue: #104. Proposal: `proposal.md`. This design is written so that someone with none of the session's context can execute the tasks months later; every number in it was re-measured on 2026-08-16 against the artefact it names, and every claim carries the file and line it was read from. Historical analysis lives in `docs/20260816_javamop_mensagens_verificacao.md` (the adversarial verification of the 2026-08-15 lineage), `docs/20260815_javamop_mensagens_FINAL.md` (the design document it corrects), `data/gh101/frozen_set_debt.md`, `openspec/changes/archive/2026-08-16-gh101-jca-spec-conformance/design.md` (D-S0..D-S14, notably D-S9 and D-S10) and `openspec/changes/gh100-weaver-emission-fidelity/design.md` (D-B1). Those documents are not to be edited; they are the record of what was found when it was found.

**The problem, measured.** Published dataset `ase-journal/dataset/results/errors.csv` (10 columns, no `source`): 97,018 rows, 19 distinct messages, 70,760 `unknown` = 72.93 %; 8,843 rows end in `but found .` (TrustManagerFactorySpec 8,371, SignatureSpec 234, MessageDigestSpec 156, SSLContextSpec 51, MacSpec 31). Study-03 trial `experimento-comp162/results/*/*/errors.csv` (8 disjoint shards — 112 distinct APKs, 3 tools × 3 repetitions each, not 8 replicas; 11 columns): 19,664 rows, 15,714 `unknown` = 79.91 %, 296 mute sites of which 101 also emit legible rows (3,950 rows) and 12 emit two error types in lockstep (838 rows, all `IvParameterSpecSpec`); per-spec mute volume SSLContext 2,916 · SecureRandom 2,882 · TMF 2,855 · MessageDigest 2,008 · Cipher 1,461 · KeyStore 1,136. Third-party attribution reproduces at 85.44 % (82,890 rows) only under nine prefixes: `okhttp3.`, `com.google.`, `kotlin.`, `io.ktor.`, `org.bouncycastle.`, `androidx.`, `org.conscrypt.`, `okio.`, `org.spongycastle.` (seven vendors give 78.49 %, +`okio.` 82.67 %).

**The mechanism.** `ErrorDescription.java:34-36` (rvsec-core): the three-argument constructor delegates with the literal `"unknown"`; `toString()` (`:143`) renders `[%s] %s at %s expecting %s`. The logcat `ErrorCollector.java:36-40` emits `getErrorSummary() + "," + getExpecting().trim()` after `errors.add(err)` on a `HashSet` whose identity is `ErrorSummary` (`:73-120`: spec, error, classQualifiedName, methodName, location); the escaping method at `:42-49` is dead code (its call is commented at `:38`). In the frozen `jca` (23 files, 1,912 lines, 134 events): 51 `new ErrorDescription(` = 25 three-argument (21 `@fail` + `IvParameterSpec.mop:48,55` + `PBEKeySpecSpec.mop:24,30`) + 26 four-argument (one commented, `MessageDigestSpec.mop:57-58`); 18 grep hits for `but found` = 16 active field-interpolating sites + `SecureRandomSpec.mop:82` (argument) + the commented `MessageDigestSpec.mop:58` (argument); 21 files with exactly one `@fail`, `RandomStringPassword.mop` and `SecretKeySpec.mop` with none; only `KeyPairGeneratorSpec.mop:110-113` lacks `__RESET`. The event body written in the `.mop` is inlined before the transition in every one of the 134/134 (`jca`) and 140/140 (`jca_android`) generated event methods, so an event that fails its `condition()` never transitions and never triggers `@fail` — the bookkeeping mechanism of E1 is sound.

**Constraints inherited.** `jca` frozen at `7e7acb69` (gh101 D-S0; gate `tests/parity/test_gh101_specset_gates.py`, 5 tests, green). `jca_android` NOT READY (audit `audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md:616-619`, 22/22 REPROVADA; G11 records three defects introduced by gh101: `GENCIPHER-EXTRA` task 5.1, `SSL-RANDOMIZED-EXTRA` task 3.2, `KPG initError` placement). `ExecutionContext` is equality-keyed at HEAD (`e204e2a4`, 2026-08-11, reverted gh101 D-S10; gh101's `data/gh101/README.md:308-317` and tasks 4b.1-4b.4 still describe identity keying — stale, noted here, not rewritten). Generator ceiling: `n × (2ⁿ − 1)` coenable sets; 17 events generate in 53 s / 3.3 GB, 18 raise `StackOverflowError` in `EnableSet.parseSets` (`data/gh101/README.md:546-553`, INV-INS-115); `jca/CipherSpec.mop` has 17 events. gh100's `INV-INS-109/110` were renumbered to 116/117 on 2026-08-16 (`ceb03a9e`) so that the ids cited here carry the gh101 meaning; this change's new invariants start at INV-INS-118. No emulator is ever run by hand; anything device-side is a task that calls `rv-experiment run`.

**Researcher decisions this design encodes (taken 2026-08-15/16, not re-opened here).** D-A: target is `jca_v2` derived from frozen `jca`; `jca_android` untouched. `st=` is out of the envelope. D-C: weaver arity lands now, three-clause rule. D-B: per clause family — api30 for availability, 1.5.2 for recommendation, recorded per spec. `ev` enters the dedupe identity (E6 exists). E4 replays the 94 non-allow-list gh101 hunks minus the three audit-flagged. `generic`/`generic_new` are a written non-goal.

## Architecture

```
                 rvsec-mop/src/main/resources/
                 ├── jca/            frozen (7e7acb69)  ── freeze gate ─┐
                 ├── jca_android/    untouched                          │ divergence
                 └── jca_v2/  ◄── S seed (byte-identical copy) ◄────────┘ record
                        │ E1 messages · E4 automata · E5 predicates       data/jca_v2/
                        ▼
   rv-monitor-generator ──► MultiSpec_1RuntimeMonitor.java ──► EV gates (pytest) · differential harness (JVM)
                        │
   dexlib2 weaver (E2: WrapperEmitter arity) ──► instrumented APK ──► device ──► logcat
                        │
   logcat ErrorCollector (E3: escape, null guard) ──► "RVSEC: spec,class,cls,method,loc,type,<envelope>"
                        │
   rv-coverage logcat_parser (E3: counters, sentinels, truncation) ──► RvErrorLog (+code,event,obj,val,exp,msg)
                        │                                                 │ core: unique_msg (7 parts, one constructor)
   rv-platform result_processor (E3/E6) ──► errors.csv (13 cols) ──► aperv_tool.analysis.violations (E3) ──► E0 baseline
```

### Key Components

| Component | Responsibility | Input | Output |
|---|---|---|---|
| `rvsec-mop/src/main/resources/jca_v2/*.mop` + `codes.csv` | the successor set; every spec-side repair | frozen `jca` (seed) | 23 `.mop` + code table |
| `rv_experiment/config.py` (`valid_spec_sets`, mapping), `rv_experiment/__main__.py` (`click.Choice`) | register `jca_v2` by name | `--specification-set jca_v2` | `RVGeneratorConfig.mop_specs_dir` |
| `data/jca_v2/{divergence_record.csv, conformance_record.csv, gate_allowlist.csv, predicate_omissions.csv}` | the set's records | tasks | gate inputs |
| `WrapperEmitter.java` (`advice-emitter`, 758 l.; grouping loop `:246-274`, write `:270-273`) + `BatchRunner.java:199-201` | arity filter + `advicesExcludedByArity` counter | descriptor JSON | wrappers, results JSON |
| logcat `ErrorCollector.java` (56 l.), csv `ErrorCollector.java` (92 l.), `ViolationRecorder.java:87-105` | escaping, null guard, frame filter | `ErrorDescription` | one logcat line |
| `rv_coverage/parser/log/logcat_parser.py` (466 l.; `_parse_error_message :285-372`) | Format 2 by structure; envelope fields; counters; sentinels; truncation | logcat text | `LogcatRepository` + `ParserDiagnostics` |
| `rv_android_core/domain/log.py` (`RvErrorLog.unique_msg :113`, identity `:181-187`) | the one `unique_msg` constructor (7 parts) | fields | key |
| `rv_platform/components/result_processor.py` (writer `:558-576`, rows `:638-652`, fallbacks `:631,:999,:1038`, swallow `:654-655,:1046-1047`) | 13-column `errors.csv`; counted write failures | repository | `errors.csv`, `results.json` |
| `aperv_tool/analysis/violations.py` (320 l.; `parse_payload :140-160`, `read_errors_csv :239-297`) + `clock_logcat_join.py` (`:364-379,:454-460`) | envelope reader; 13-col header; counters | logcat / `errors.csv` | `ViolationEvent`, diagnostics |
| `scripts/gh104_gates.py` + `tests/parity/test_gh104_specset_gates.py` | G-2/2a/2b′/2c/2d/6′, lint, message-property gate, parametrised by set | generated monitor, `.mop` files | pytest verdicts |
| `scripts/gh104_diff_harness.py` + `rvsec-mop/src/test/java/.../TraceRunner.java` | before/after replay of traces through generated monitors | two set snapshots + `traces/<spec>.txt` | per-trace verdicts (`evidence/harness/`) |
| `scripts/gh104_baseline.py` + `data/gh104/baseline.md` | E0 residual budget with freeze items and envelopes | comp162 (via `read_errors_csv`), article (declared reader) | numbers with numerator/denominator |
| `rvsec-core` `ErrorSummary.java`, `ErrorType.java`, `ErrorDescriptionTest.java` | identity (+`code`,`event`); `RequiredPredicate`, `ForbiddenMethod` | — | — |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|---|---|---|
| Successor set `jca_v2` (INV-INS-09, INV-INS-118) | copy `jca/`→`jca_v2/`; `config.py`, `__main__.py`, INV-EXP-03(f); `data/jca_v2/divergence_record.csv` + `scripts/gh104_divergence_record.py` (parametrised copy of `gh101_divergence_record.py`) | `tests/parity/test_gh104_specset_gates.py::test_jca_v2_hunks_all_recorded`, `modules/rv-experiment/tests/...::test_jca_v2_selectable`; existing freeze test stays green |
| Message envelope (INV-INS-119, 121) | 25 four-arg edits, 17 field→arg, census fixes, `codes.csv` | `test_no_three_argument_site`, `test_codes_csv_bijective`, `test_numeric_literals_match_guard`; harness evidence per file |
| Event-name bookkeeping (INV-INS-120) | `lastEventName` field + first statement per body; `@fail` composes `ev=` before `__RESET` | `.mop` lint `test_every_body_records_its_name`; G-6′ |
| Wrapper arity (INV-INS-122) | `WrapperEmitter.generate` grouping loop; new `EmitReport`/counter → `BatchRunner.counts["advicesExcludedByArity"]`; `_parse_results_json` | `WrapperMergeTest` (+2 cases: `args(a,*)` excluded; the 13 no-`args()` survive), `ResultsJsonReportingTest`, `test_dexlib_instrumentation.py` |
| Collector emission (escape, null guard, frame filter) | logcat `ErrorCollector.escape`, csv parity; `ViolationRecorder.makeRelevantList` | `ErrorCollectorTest` (new, rvsec-logger-logcat), `ViolationRecorderTest` (new, rv-monitor-rt) |
| Structural gates (INV-INS-123) | `scripts/gh104_gates.py` (reads both monitor shapes; reuses `gh101_monitor_transition_check.py` parsing) | `test_gh104_specset_gates.py` parametrised over `jca` (expected 18/1/8/1/2/1) and `jca_v2` |
| Differential harness (INV-INS-124) | `scripts/gh104_diff_harness.py`, `rvsec-mop/src/test` `TraceRunner`, `traces/<spec>.txt` | harness self-test on `jca` vs `jca_android` (`TrustManagerFactorySpec` moved accusation) |
| Predicate reporting (INV-INS-111) | `ErrorType` +2; body reads; `data/jca_v2/predicate_omissions.csv` | `gh101_predicate_pairing_check.py` re-pointed at `jca_v2`; harness |
| Dedupe identity (INV-INS-126) | `ErrorSummary.equals/hashCode` (+`code`,`event`); `ErrorDescriptionTest.hashCodeMatchesEquals` | Java test; `scripts/gh104_identity_discontinuity.py` over comp162 (must be non-zero) |
| Logcat grammar (INV-ANA-08, 62, 63) | `logcat_parser._parse_error_message`, `ParserDiagnostics` | `test_logcat_parser.py` property tests (`,`, `\'`, `\n`, `:::`, 4068-byte cut) |
| `unique_msg` (INV-CORE-25, 41, 56, 57) | `RvErrorLog.unique_msg` only; delete 4 other constructors | `test_log.py`; grep gate `test_unique_msg_built_once` |
| `errors.csv` 13 columns (INV-PLT-19, 30) | `result_processor` writer; counted failures | `test_result_processor.py` header test |
| Envelope readers (INV-CAN-04, 25, 26) | `violations.py`, `clock_logcat_join.py`, `ERRORS_CSV_HEADER` | `test_violations.py` (+4) |
| Baseline (E0) | `scripts/gh104_baseline.py`, `data/gh104/baseline.md` | byte-identical rerun (`test_gh104_baseline_reproduces`) |

## Goals / Non-Goals

**Goals:** every report from `jca_v2` names its event and its observed/expected values in a machine-readable envelope; no report says `unknown` or `but found .`; a merged wrapper fires only arity-compatible advices; the transport counts every discard; the gates run as pytest for any set; the harness makes moved defects visible; per-event attribution reaches `errors.csv` and the dedupe identity, with the discontinuity declared; the frozen `jca` keeps reproducing.

**Non-Goals:** the `generic` and `generic_new` sets (145 files, `Log.v` path, never ran; 11 `generic` files do not compile — duplicated parameter names — and `FSM358.mop:4,6` has an import collision; recorded as debt, see plan `docs/20260815_javamop_mensagens.md:805-817` WS-8); repairing `jca_android`; unfreezing `jca`; re-keying `ExecutionContext` by identity; the absorbing-state repair of the Form-B residue (rejected, gh101 D-S9); the `before`-advice binding-form arity check (`PointcutMatcher.java:268-306`); the generator emitting event names itself (option O-1 — recorded as a follow-up if E1's bookkeeping proves error-prone across a second set); re-measuring the published corpus on device (device validation is one task, on four APKs, not a campaign); end-of-trace detection and localisation options (O-7/O-8).

## Decisions

### D-1 — the successor set is a byte-identical copy of `jca`, and E4 replays gh101's non-allow-list hunks

D-A(ii) fixed the lineage: `jca_v2` derives from `jca`. Two ways to get the repairs gh101 already made: re-derive them from CrySL, or replay the recorded hunks. `data/gh101/divergence_record.csv` names all 106 hunks between `jca_android` and `jca` by file, kind and reason: 51 `layer-2-repair`, 42 `predicate-graph`, 1 `cipher-import`, 12 `allow-list`. The 12 allow-list hunks are the api30 profile and are excluded (that is D-B's territory); the 94 others are repairs whose reason is written down — the 18 all-`fail` events, the `gtm1` four-defect hunk, the `gpr` wrong constant, `CipherSpec` 17→14 (28 hunks in that file), `MacSpec` 8→11 (11), the four `remove(Property)` sites, `MessageDigestSpec.reset` removal. **Decision: replay the 94, minus the three the audit flags as gh101-introduced (`GENCIPHER-EXTRA` — `CipherInputStreamSpec`/`CipherOutputStreamSpec` reading `GENERATED_CIPHER`, task 5.1; `SSL-RANDOMIZED-EXTRA` — `SSLContextSpec.init` reading `RANDOMIZED`, task 3.2; `KPG initError` placement residual), which are recorded in `data/jca_v2/divergence_record.csv` as deliberately not replayed.** Replay is mechanical because every hunk has an id and a reason; the divergence-record script recomputes hunks between `jca_v2` and `jca` and fails on any without an entry, exactly as gh101's does between `jca_android` and `jca`. Re-deriving from CrySL was rejected: it would repeat two weeks of gh101 work to reach the same text, and the audit's per-spec verdicts already tell which of those repairs held.

Cost declared: `CipherSpec` replay includes the alphabet re-budget (17→14 events, then E4's own items must stay ≤ 17 — every new `Cipher` event costs one of the three slots the re-budget frees). `AndroidCipherTransformationUtil` exists at HEAD (gh101 D-S3) and `Property` already carries `GENERATED_CIPHER`/`MACED`, so no shared-Java re-derivation is needed for the replay.

### D-2 — E1 (messages) lands before E4 (automata), with a new written reason

The lineage ordered C-4 → C-3 because "the message names states that C-4 will create". That reason died when `st=` left the envelope (`_lacunas.md:651-666`); the verification (`§6.5`) asks for a new reason or a new order. **Decision: E1 first.** Reasons: (i) E1 is cheap and mechanically verified — 25 four-argument edits, 17 field→argument swaps, ~134 bookkeeping lines, and it makes every later repair *readable*: the differential harness (EV) reports the accusing event by name only once `ev=` exists, so E4's before/after evidence is per event instead of per site; (ii) E1 installs an invariant (INV-INS-120: every body records its name) that the `.mop` lint keeps, so E4 edits under it — an event E4 adds or renames without its bookkeeping line fails the lint at generation time; (iii) both edit the same 23 files, so they never run in parallel per change; they run in parallel **per file** with one owner per file at a time (WORKFLOW §5 locality), and E1's edits are small enough that E4's alphabet changes cost one line each. The alternative — E4 first — leaves the harness blind during the stage that most needs it.

### D-3 — the envelope: `key=value`, commas allowed, `\n`/`:::` forbidden, unclosed quote means truncation

Grammar (fixed by the researcher): `v=1 code=<SPEC>-<KIND>-<NN> ev=<event> obj=<SimpleClass> val='<observed>' exp='<expected>' msg='<text>'`. JSON was rejected in the lineage (braces, commas and quotes in a positional line — `FINAL:199`). The lineage's comma prohibition is dropped: 27.06 % of today's messages contain commas (every `String.join(",", …)` allow-list) and all four consumers already rejoin field 7 (`logcat_parser.py:341-350`; `violations.py:140-160` `split(",", 6)`; `clock_logcat_join.py:454-460`; `TraceComparator.parseObserved`). `\n` splits the logcat line (a second RVSEC line with no structure — a fabricated record); `:::` is the `unique_msg` separator. Escaping: `'` → `\'` inside values (zero occurrences today, so the property tests exercise it synthetically); `\n` → `\\n` by the collector. Truncation: `LOGGER_ENTRY_MAX_PAYLOAD` = 4068 bytes on API 30 (`_lacunas.md:229-269`); measured envelope sizes on the trial: median 274 B, p99 391 B, max 696 B — so truncation is not a volume risk, only a pathological-`val` risk; producer caps `val` at 512 characters, and the parser treats an unclosed final quote as a truncated record (`truncated=True`, counted), never as a value. `code` KIND vocabulary: `ORDER` (`@fail`), `ALG` (algorithm outside allow-list), `CONSTR` (argument constraint), `KEYSIZE`, `KSTYPE`, `PROTO`, `REQ` (RequiredPredicate), `FORB` (ForbiddenMethod); `NN` two digits per spec×kind, listed in `codes.csv` (`spec,code,error_type,site_kind,event,file_line`), bijective with the sites (gate).

### D-4 — event-name bookkeeping is spec-side, one line per body, and the generator is not modified

Option O-1 (make the generator emit `__EVENTNAME`) would touch `rv-monitor` (radius M) and needs a release; the spec-side line is 134 edits in the set this change already edits, and its premise is verified on 274/274 generated methods (the body runs before the transition). Residues, declared: `KeyPairGeneratorSpec` (no `__RESET`) gains one; `KeyGeneratorSpec.g3` (`:47`, field instead of argument) is repaired in E4 so two events cannot pass their guards on one call. Declarations are emitted verbatim into the monitor class (verified on `KeyPairGeneratorSpec`'s private methods), so `String lastEventName = "";` is safe; the names the generator already occupies (`Prop_N_state`, `Prop_N_transition_*`, `pairValue`, `RVM_lastevent`, `reset`, `getState`, `getLastEvent`, `handleEvent`, `clone`) must not be reused — the lint checks. No `static` declaration exists in the corpus, so `static final String[] EVENT_NAMES` is **not** used (unverified premise); a plain string literal per body needs no array.

### D-5 — `ev` and `code` enter the identity; `code` alone would be a no-op

`ErrorSummary.equals` compares (spec, error, class, method, location). Every `jca` spec has ≤ 1 `@fail`, so `code=<SPEC>-ORDER-00` is a function of `spec`: adding it refines nothing for the 72.93 % of records that are `InvalidSequenceOfMethodCalls`. `event` is what separates concurrent causes at one site (e.g. `KeyManagerFactorySpec`'s 296 rows at `TlsUtil.newKeyManager:191` — 9 sites, two candidate causes, inseparable today). Researcher decision: both enter. Consequence accepted and made a gate: the count discontinuity on comp162 (6,344 five-field identities / 19,664 rows, 67.74 % repetition, max 49 per identity, none of it replication — 0 % of the repetition is a shard artefact) is recomputed with `event` from the envelope and must be non-zero, or E6 does not land. E6 is device-side (re-instrumentation) and last.

### D-6 — the weaver arity rule is exactly the three clauses, filtered in the grouping loop, counted, and dexlib2-only

`WrapperEmitter.generate` groups by `registryKey(cc)` (`:133-136`, `declFqn#method(params)return`) at `:270-273`; `firstCallTarget` (`:507-525`) walks the AST for the first `CallPC` and ignores `ArgsPC`; overload expansion (`:326-403`) is driven by the `call()` param specs only. Nothing reads `args()`, so `TrustManagerFactory.getInstance(String)` fires `g1`, `g2`, `g3` (visible in `results/gh101_group8_jca_frozen_control/monitors/mop/MonitorWrappers.java:538-544`). The lineage's first rule ("drop an advice whose `args` list has no trailing `..` and whose length ≠ `cc.paramFqns.size()`", `FINAL:434-438`) would drop the 16 `after` advices with parameters and no `args()` — 2,629 of 3,950 legible rows of the trial (66.6 %; `SSLContextSpec.init` 1,466, `MessageDigestSpec.update` 1,163). Three clauses (`_lacunas.md:674-684`): absent `args()` = no constraint; length of `ArgsPC.types()` not `names()` (`PointcutExpressionParser.java:243-246` drops `..`; reuse `trailingRest`/`headCount` of `PointcutMatcher.java:280-288`); filter in the grouping loop. Counter: `WrapperEmitter.generate` returns only `List<WrapperEntry>` today; it gains a small result record carrying `advicesExcludedByArity`, and `BatchRunner.java:199-201` puts it in `counts` beside `wrappersGenerated` — **not** in `DexWeaver.WeaveReport` (`:978-1008`), which the FINAL named by mistake: the exclusion happens in the emitter, not the mutator. AspectJ enforces `args` arity itself, so the `ajc` variant needs nothing. Denominators the lineage published for this (114 after-advices / 79 with `args()`) do not reproduce on the frozen descriptor (97 / 62); the 16 do, and 3 of them are constructor advices that never reach the wrapper path — 13 are the ones a wrong rule would drop.

### D-7 — gates: G-2 becomes pytest with five structural companions; G-2b is not adopted; the harness is the missing instrument

Measured on the frozen-control monitor: G-2 18 orphans in 10 specs; G-2a 1 (`SecretKeySpec.e1` — a spec whose only event never changes state, i.e. a null detector the existing gate passes); G-2b′ 8 (`CipherSpec.g3`, `KeyGeneratorSpec.g3`, `KeyManagerFactorySpec.g3`, `KeyPairGeneratorSpec.g3`, `KeyStoreSpec.g2`, `MacSpec.g3`, `MessageDigestSpec.g4`, `SecretKeySpec.e1`); G-2c 1; G-2d 2 (`SecretKeySpec`, `RandomStringPasswordSpec` have no `fail` category, so "sink = highest index" is not a violation state there); G-6′ 1 (`GCMParameterSpecSpec`: two `Prop_1_event_c1` methods, one `c1` row; `c2` referenced at `:48`, never declared). Each is a few lines over the same transition tables `gh101_monitor_transition_check.py` already parses (both monitor shapes, `:36-45`). The lineage's G-2b ("out-alphabet of unsafe ⊇ out-alphabet of safe") is not computable: minimisation merges the unsafe state into `start` precisely when the alphabets are equal (`δ(q0,g3)=q0` in `CipherSpec`, `KeyManagerFactorySpec`), and its implied repair — absorption — was rejected in gh101 D-S9 (two repair philosophies; FP traded for FN). Since G-2b′ flags idioms gh101 deliberately copied (`jca_android/SSLContextSpec.mop:95-101` mirrors `KeyManagerFactorySpec.unsafeAlg`), the gates need an allowlist with reasons (`data/<set>/gate_allowlist.csv`) — a hit is a question, not automatically a defect. What no static gate does is compare behaviour: gh100's merge turned 12 discarded wrappers into arity-incompatible advices firing (reported as success, `wrappersGenerated 96→84`); gh101's Group 3/3b turned 18 all-`fail` rows into accusations one call later. Hence the differential harness (INV-INS-124), on the JVM (`rvsec-mop/src/test`, created), with traces per spec; its self-test is `TrustManagerFactorySpec` between `jca` and `jca_android` (the moved accusation is known).

### D-8 — transport: count, don't drop; sentinels, not fabrication; parser recognises Format 2 by structure

Ten silent-discard or scramble points were verified: `logcat_parser.py:268-270` (non-threadtime), `:235-248` (other tag), `:306-316` (Format-1 suffix but regex fails → falls into the comma path and scrambles a comma-bearing line into a JCA record), `:321-350` (Format 2 accepts anything with ≥ 5 commas), `:355-368` (Format 3 without a `.` → warning), `:371-372` (unrecognised → `None`), `:202-203` (`except Exception` → partial repository), `_normalize_frame :87-95`, `result_processor.py:333-338,:654-655,:1046-1047` (task-wide swallow), `clock_logcat_join.py:364-379`. `INV-CAN-04` covers only `aperv_tool.analysis` (`campaign-analysis/spec.md:5`), so `rv-coverage`'s drops are invisible to it; the same `[helper] ::: …` line gives 1 event in `aperv_tool` and 0 in `rv-coverage`. Decision: a `ParserDiagnostics` object with the 13 named counters travels with the repository; no line leaves without incrementing exactly one; the Format-1 fall-through is closed; sentinels (`UNSPECIFIED`, `UNSPECIFIED:0`) replace fabricated values and are counted; `unique_msg` is built in one place (`log.py:113`) — the four other constructors (`result_processor.py:631,:999,:1038`, `regenerate_container.py:244`) are deleted (P3), and the 4-field diagnostic variant (`log.py:269-271`) is unaffected. Consumers that regex the free text are named in the consumer matrix and migrated or declared frozen: `ase-journal/docs/20260806_owasp_cwe_mapping_gen.py:47-54` (`but found (.*?)`), `experimento-gov/scripts/consolidate_gov.py:26-37`, `validator/oracles/cryptoapp-oracle.yaml` (six substrings driving `TraceComparator.java:596-598`), `scripts/rv_oracle_common.py:73-81` (reads `parts[3]/[4]` and is silently wrong on extra `:::`), `.claude/skills/rv-experiment-compare/scripts/consolidate_compare.py:35` (a template). Format recognition of `jca` lines is by structure (comma count), so rewriting the messages does not break the parser; the `endswith("went into an error state.")` coupling (`:306`) is a `generic` concern.

### D-9 — E0 reuses `read_errors_csv` and copies the freeze-item and envelope disciplines; it does not live inside `aperv_tool.analysis`

`aperv_tool.analysis.violations.read_errors_csv` is the canonical `errors.csv` reader (`ERRORS_CSV_HEADER`, raises on mismatch, counts `unique_msg_unparsed`); a fifth ad-hoc reader would repeat the defect E3 closes. But the analysis layer is generic by construction ("no research-question identifier outside `callers/`", "cmp162 is a fixture, not a corpus" — `docs/20260815_gh103_analysis_layer.md:10-16,:112`), so the message baseline is a **script that imports the reader** (`scripts/gh104_baseline.py`), not a module inside the layer. It copies two patterns: freeze items (`FreezeItemUnset` — omitting a definition is an error, not "none"; `:62-84`) for the definitions that decide the numbers (mute = `message.strip()=='unknown'`; site = `(spec,class,method,source)` on comp162 and `(spec,class,method)` on the article, which has no `source`; the nine-prefix classifier; shards not replicas), and `Envelope` (a bare float cannot be emitted; `:18-22`). The article dataset (10 columns) is rejected by `read_errors_csv` by design; E0 declares a separate reader for it and records the instrument discontinuity. Parity ≠ correctness: reproducing a number proves the pipeline unchanged, not the estimator right (`:108-110`).

### D-10 — the oracle rule and the E4 catalogue items

D-B per clause family. Consequence for E4: catalogue-changing items (Cipher families beyond AES/RSA — the frozen `CipherTransformationUtil` covers two families where the api30 rule admits eight, so `KeyGeneratorSpec` accepts `ChaCha20`/`DESede`/`BLOWFISH`/`ARC4` that `Cipher.getInstance` then rejects; keystore types) follow api30 and are entered in `data/jca_v2/conformance_record.csv` as availability; digest and protocol lists stay on 1.5.2 (recommendation), so `MessageDigestSpec` keeps rejecting MD5/SHA-1 — 5,892 of 15,444 `UnsafeAlgorithm` rows of the article (38.15 %) depend on exactly this and stay reported. `jca_v2/CipherSpec` therefore switches its static import to `AndroidCipherTransformationUtil` (the `cipher-import` hunk), which is availability by construction.

### D-11 — E5 under equality keying, and what it does not do

`ExecutionContext` is `HashMap`/`HashSet` at HEAD (`:30-31,:81`). D-S10's eight identity-sensitive reads (`CipherSpec.i2` ×3, `MacSpec.i1/i2`, `SecretKeySpec.e1`, `RandomStringPasswordSpec.vo/gb`; the `SecureRandom` seed reads are `byte[]`, not boxed `long` — `README.md:281-287`) stay equality-keyed; the `generatedCipher` edge (gh101 task 5.1) is not replayed (D-1). E5 adds `RequiredPredicate`/`ForbiddenMethod`, moves reads into bodies with the automaton co-edited (no new orphan — G-2), and either adds producers (`SecretKeyFactory`, `*ParameterSpec`) or records them in `data/jca_v2/predicate_omissions.csv` with the CrySL reason, as `data/gh101/predicate_omissions.csv` does for 20 constants (11 `constant-write-no-read`, 9 `predicate-no-constant`; seven terminal in both anchors: `DIGESTED`, `SIGNED`, `VERIFIED`, `WRAPPED_KEY`, `GENERATE_SSL_CONTEXT`, `GENERATE_SSL_ENGINE`, `GENERATED_KEY_PAIR`). The one-argument `remove(Property)` (`ExecutionContext.java:52-53`, `@Deprecated`, deletes the whole set) is removed at its four `jca` sites (`KeyManagerFactorySpec:91`, `TrustManagerFactorySpec:87,88`, `MacSpec:87`) in E4 as gh101 did (three need a monitor field).

### D-12 — process: one `tasks.md`, per-group execution files, five parallel first-wave subagents

`openspec/schemas/rv-sdd/schema.yaml:162-164` tracks `tasks.md` and only `- [ ]` lines (`:120,:124`); `docs/WORKFLOW.md:443` needs the checkbox ticked immediately after each task for resume; `:1049-1060` detects the artifact by `tasks.md` existing. **Decision: `tasks.md` holds every checkbox and the dispatch hints (HTML comment at the top, `schema.yaml:151-152`, template `tasks.md:1-6`); each group heading points to `tasks/<GROUP>.md`, which holds the file inventory, per-site table, commands, expected values and the subagent brief. A subagent reads only its group file; the orchestrator reads only `tasks.md`.** This is additive — the schema forbids nothing in the change directory — and keeps subagent context small (3–15 files each, `WORKFLOW.md:331`). Groups by independence and locality: E0 (docs+scripts) ∥ S (rv-experiment + new dir) ∥ E2 (Java dexlib2) ∥ E3 (collectors + Python consumers) ∥ EV (new test/script files) — five disjoint file sets, wave 1; E1 after S (two subagents by file halves); E4 after EV and E1 (per file, one owner at a time; divergence-record entries appended per file); E5 after E4; E6 after E1 and E3 (Java `rvsec-core` + Python), can overlap E4/E5. Critical path: S → E1 → E4 → E5. gh100 7.5/7.6 are closed (2026-08-16), so E2 has no process dependency left.

## API Design

### `WrapperEmitter.generate(descriptor, monitorDir[, index]) -> EmitResult`
`EmitResult { List<WrapperEntry> wrappers; int advicesExcludedByArity; }`. Precondition: descriptor parsed. Postcondition: for every group, every admitted advice satisfies `arity(advice) ⊆ paramCount(cc)` under the three clauses; excluded advices are counted, never logged-and-dropped. `BatchRunner` writes `counts["advicesExcludedByArity"]`.

### `ErrorCollector.addError(ErrorDescription err)` (logcat)
Emits one line `summary + "," + escape(expecting)`; `expecting == null` → sentinel envelope; `escape`: `\n`→`\\n`. Never throws for a `null` message.

### `_parse_error_message(message: str) -> RvErrorLog | None` and `LogcatRepository.parser_diagnostics: ParserDiagnostics`
`RvErrorLog` gains `code, event, obj, val, exp, msg: str | None`, `truncated: bool`; every `None` return increments exactly one counter; `parse_logcat_file` re-raises after logging the line number.

### `RvErrorLog.unique_msg -> str`
`f"{class_full_name}:::{method}:::{spec}:::{error_type}:::{code or 'UNSPECIFIED'}:::{event or 'UNSPECIFIED'}:::{message}"` — the only constructor.

### `violations.read_errors_csv(path) -> (rows, CsvDiagnostics)`; `parse_payload(payload) -> ViolationEvent`
13-column header or `ValueError`; seven `:::` parts or `unique_msg_unparsed += 1`; envelope keys parsed; unclosed quote → `shape_ok=False`, `envelope_truncated += 1`.

### `gh104_gates.py run(monitor_java: Path, allowlist: Path) -> GateReport`; `gh104_diff_harness.py run(set_a: Path, set_b: Path, traces: Path, out: Path)`
Both need `RVSEC_HOME`; generation in a scratch dir off tmpfs; the harness returns per-trace verdicts (`accused`, `event`, `envelope`) for both snapshots and a `moved`/`removed`/`unchanged` classification.

## Data Flow

`.mop` (jca_v2) → rv-monitor-generator → `MultiSpec_1RuntimeMonitor.java` (event body: `lastEventName = "g3"; … addError(new ErrorDescription(UnsafeAlgorithm, spec, __LOC, "v=1 code=TMF-ALG-01 ev=g3 …"))`; `@fail`: compose envelope from `lastEventName`, then `__RESET`) → dexlib2 weaver (merged wrapper with arity-compatible advices) → device → `RVSEC: spec,class,cls,method,loc,type,v=1 …` → `logcat_parser` (Format 2 by structure; envelope → fields; counters) → `RvErrorLog` (`unique_msg` 7 parts) → `result_processor` (`errors.csv` 13 columns) → `aperv_tool.analysis.violations` (13-column header; envelope) → E0 baseline / campaign analysis. In parallel: generated monitor → gates (pytest) and harness (JVM) → `evidence/harness/`.

## Error Handling

| Error | Source | Strategy | Recovery |
|---|---|---|---|
| Three-argument `ErrorDescription` in `jca_v2` | lint / message gate | fail | add the envelope; codes.csv entry |
| Body without bookkeeping line, or wrong name | lint | fail | fix the first statement |
| Hunk between `jca_v2` and `jca` without record | `gh104_divergence_record.py --check` | fail | add entry or revert |
| Freeze gate fails on `jca` | existing pytest | fail | move the edit to `jca_v2` |
| Structural gate hit not allowlisted | `test_gh104_specset_gates.py` | fail | repair or allowlist with reason |
| `CipherSpec` > 17 events | generation (`StackOverflowError`) | fail closed | re-budget alphabet (INV-INS-115) |
| Unclosed quote in envelope | parser | `truncated=True`, counted | shorten `val` (cap 512) |
| `\n`/`:::` in a value | parser counter `envelope_forbidden_chars` | keep record, count | fix the producer |
| `null` expecting | collector | sentinel envelope | fix the spec |
| Header ≠ 13 columns | `read_errors_csv` | `ValueError` | use the declared historical reader (E0) |
| Identity discontinuity = 0 | `gh104_identity_discontinuity.py` | E6 blocked | (design flaw — re-open D-5) |
| Wrapper registry collision | `DexWeaver.registerWrapper` (unchanged) | `IllegalStateException` | — |

## Risks / Trade-offs

- [E1 and E4 edit the same 23 files] → per-file ownership, never per-change parallelism; the lint enforces the bookkeeping invariant across E4's alphabet edits.
- [`CipherSpec` at the generator ceiling] → the replay's 17→14 re-budget is prerequisite to any E4 item adding a `Cipher` event; every task in `tasks/E4-automata.md` for that file declares its event count after the edit.
- [G-2b′ flags deliberate idioms] → allowlist with reasons; a hit is a question. The Form-B residue (13 specifications per `frozen_set_debt.md:246`; its own enumeration yields 14–15 — the count is not authoritative) stays recorded, not gated.
- [Replaying gh101 hunks replays gh101's mistakes] → the three audit-flagged items are excluded; the audit's per-spec verdicts (`juizglobal_gates.csv`) are read per file before replay; harness before/after per file.
- [The identity change creates two eras of every dedupe number] → declared, measured (must be non-zero), E6 last and device-side; reports carry the era.
- [Consumers regexing free text break] → consumer matrix names each; the article scripts are declared frozen (they read the published dataset, which does not change).
- [`static` declarations unverified in the generator] → not used (D-4).
- [The `KeyManagerFactorySpec` 296 rows have two candidate causes the record cannot separate] → E1's `ev=` is what separates them; the harness reads it; no gain is credited to E2 for those rows.
- [Device validation] → one task, four APKs from the published campaign (`com.owncloud.android_48000100`, `eu.opencloud.android_9`, `de.luhmer.owncloudnewsreader_196`, `com.etesync.syncadapter_20700` — the ones gh101 task 8.1 used), via `rv-experiment run`, never by hand; the change is complete without it being green, but not without it being run and its result recorded.
- [gh56-smoke monitors predate the freeze] → oracles are always `results/gh101_group8_jca_frozen_control/monitors/` (transition tables identical to gh56-smoke; `KeyManagerFactorySpec.init` guard polarity differs there).

## Testing Strategy

| Layer | What to test | How | Count |
|---|---|---|---|
| Lint / message gate | 3-arg sites, bookkeeping, undeclared symbols, parens, literals vs guard, `codes.csv` bijection | pytest over `jca_v2/*.mop` and `jca` (baseline expectations) | ~8 |
| Structural gates | G-2/2a/2b′/2c/2d/6′ on `jca` (18/1/8/1/2/1) and `jca_v2` | pytest parametrised by set; scratch generation | ~7 |
| Divergence / freeze | every `jca_v2` hunk recorded; `jca` byte-identical | pytest (`gh104_divergence_record.py --check`; existing freeze test) | 2 (+5 existing) |
| Weaver | `args(a,*)` excluded; 13 no-`args()` survive; `..` honoured; counter reaches JSON | `WrapperMergeTest`, `ResultsJsonReportingTest`, `test_dexlib_instrumentation.py` | ~5 |
| Collector / recorder | escaping, null guard, frame filter | new Java tests | ~4 |
| Parser | property tests `,` `\'` `\n` `:::` truncation; counters sum; sentinels; Format-1 no fall-through | `test_logcat_parser.py` | ~10 |
| Core / platform / campaign-analysis | 7-part `unique_msg`; one constructor (grep gate); 13-column header; readers | `test_log.py`, `test_result_processor.py`, `test_violations.py` | ~10 |
| Harness | self-test on `jca` vs `jca_android` (`TrustManagerFactorySpec` moved accusation); per-repair evidence | JVM runner + script | 1 + per task |
| Identity | 7-field `ErrorSummary`; discontinuity on comp162 non-zero | Java test + script | 2 |
| Baseline | byte-identical rerun; freeze items required | pytest | 2 |
| Device | four APKs, `rv-experiment run --specification-set jca_v2` | one task, result recorded | 1 |

## Open Questions

- The exact `code` numbering per spec (`NN`) is assigned when `codes.csv` is written in E1; the gate makes it bijective, so no two sessions can disagree silently.
- Whether `SecretKeySpec` (null detector: single event, no `@fail`, `ere: e1*`) is repaired into a detector or deleted from `jca_v2` — decided in E4 per the CrySL rule, recorded in the divergence record either way.
- Whether option O-1 (generator emits the event name) is opened as a follow-up issue after E1 — decided by the E1 evidence (how many bookkeeping defects the lint caught).
- The main `experiment` spec's Purpose sample (`openspec/specs/experiment/spec.md:87`, `# "jca", "generic", or "custom"`) is a comment in a code sample and is corrected at sync time with the `jca_v2` delta.
