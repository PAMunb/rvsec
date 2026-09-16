# gh114 — consistency review, weaver deferral scan and CrySL adherence

Date: 2026-09-15. Change: `openspec/changes/gh114-weaver-fidelity-nobs-labels/` at commit `9025e557`, not implemented.
Protocol: `evidence/review_protocol.md` (pre-registered before the artifacts were read in depth).
No artifact was edited. Every proposed revision below is a proposal for `/opsx:update`, not an applied change.

Path roots: `<R>` = `rv-android/`; `<W>` = `rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`; `<SET>` = `rvsec/rvsec-mop/src/main/resources/jca_android/`; `<CORE>` = `rvsec/rvsec-core/src/main/java/br/unb/cic/mop/`; `<RULES>` = `RVSec-replication-package/tools/rules/`; `<MON>` = `rvsec-dataset/jca_android/instrument_results/instrument_00/instrument_00/monitors/`; `<CHG>` = the change directory; `I/C/A/P` = the four delta specs of the change.

## 1. Protocol as executed

- Three areas, each reviewed by two independent subagents (A and B) with the same checklist and file lists, no hypotheses, no access to each other's output, and no access to `docs/analise_*` or `docs/handoff/`. Raw outputs: scratchpad `review_{C,T,R}_{A,B}.md` (session-local, not committed).
- Per check: A result, B result, agreement, adjudicated result. Disagreements adjudicated by the orchestrator against the source; rationale in §3.
- Every finding of severity ≥ medium was sent to a refuter subagent instructed to disprove it on the source (`refute_C_1/2.md`, `refute_R_1/2.md`). §4 lists what survived.
- Weaver deferral candidates (area T) are questions, not findings; both reviewers converged on the same set (T-A and T-B), so no refutation pass was run on them.
- Counts: each count in this report names the command that produced it (reviewer report §3/§4, or the orchestrator's own command in §3 here).
- Post-hoc check registered: **T-01-post** — a prose pattern (`future fix|future revision|not yet|for now|unsupported|defensive skip`) over `src/main`, added by both T reviewers after T-01 returned zero hits. Recorded as post hoc; its hits are in §5.

Sources the orchestrator read directly (for adjudication): all seven change artifacts; `<SET>/DigestInputStreamSpec.mop:78-92`, `DigestOutputStreamSpec.mop:84-90`; `<MON>/MultiSpec_1MonitorAspect.aj:464-466,489-490`; `<MON>/MultiSpec_1RuntimeMonitor.java:6555,13853,13856`; `<R>/data/jca_android/divergence_record.csv:1,31,37,46,376`; `<R>/data/jca_android/conformance_record.csv:116-117,119-120`; `<SET>/MacSpec.mop:235-241`, `SignatureSpec.mop:144-151`, `KeyPairSpec.mop:82-98`; `<CORE>/Property.java:92-108`; `<W>/advice-emitter/.../WrapperEmitter.java:24-28,232,336-341`; `<W>/dex-mutator/.../InstructionInjector.java:266-272`; `<W>/cli/.../BatchRunner.java:182`; `<R>/modules/rv-android-core/src/rv_android_core/domain/coverage.py:1030-1035`; `<R>/modules/rv-platform/src/rv_platform/components/result_processor.py` (`get_errors` calls at `:1139,:1178`); `<R>/openspec/specs/platform/spec.md:642-658`; `<R>/openspec/specs/instrumentation/spec.md:248,351,1851,2420-2434,2530-2536`; `<R>/openspec/specs/core/spec.md:1125-1138`; `<R>/openspec/changes/archive/` listing.

## 2. Results per check

### 2.1 Consistency (C)

| ID | A | B | Agreement | Adjudicated | Note |
|---|---|---|---|---|---|
| C-01 | PASS | PASS | agree | PASS | four delta dirs = proposal list |
| C-02 | PASS | PASS | agree | PASS | every proposal item has a requirement |
| C-03 | PASS | PASS | agree | PASS | mapping table `design.md:83-99` |
| C-04 | PASS | PASS | agree | PASS | D1–D14 → tasks |
| C-05 | PARTIAL | PARTIAL | agree | PARTIAL | same four scenarios without a task: `I:161`, `I:263`, `I:131`, `I:359`/`P:179` (A: 4 of 62 scenarios by `c18.py`; B: 4 of 46 — B's denominator excludes the inherited scenarios of the MODIFIED blocks) |
| C-06 | PASS | PASS | agree | PASS | every task traces |
| C-07 | PASS | PASS | agree | PASS | 4/4 MODIFIED+REMOVED headers match base (`c07_c10.py`, `c07_headers.py`) |
| C-08 | PARTIAL | PARTIAL | agree | PARTIAL | INV-PLT-14 five→six files without a design sentence (low) |
| C-09 | PARTIAL | PARTIAL | agree | PARTIAL | base `:248` and `:1851` keep INV-INS-122 live; 7 comment sites unnamed (medium, F-01) |
| C-10 | PASS | PASS | agree | PASS | new IDs fresh and contiguous after INS-158/CORE-62/ANA-71/PLT-37 |
| C-11 | PARTIAL | PARTIAL | agree on substance, differ on count | PARTIAL | 157 citations (both `cites.py`/`c11_cites.py`); gh114-authored: 116/117 hold, 1 not checkable (dexlib2 library line); one authored name drift (task 2.3 site list). Inherited from copied base blocks: B counts 8 current-state citations that no longer hold; A counts 36 by also including the seed-era census citations of `I:314` that the base itself labels "measured on the frozen jca … in the seed". Adjudicated: 8 are drift of current-state claims; the other 28 are historical citations the text declares as such (low). |
| C-12 | FAIL | FAIL | agree | FAIL | task 2.3 (G2) edits `WrapperEmitter.java:232` (G3, same wave) and names sites that construct nothing (F-02) |
| C-13 | PARTIAL | PARTIAL | agree | PARTIAL | unstated deps: G2→G3/G12 (F-02); G11←G10 via `to_dict()` (F-04); G4's `TryCatchSpec` source (F-low-06); G7 trace asserts a code G9 numbers |
| C-14 | PASS | PASS | agree | PASS | only class-loader and API rules; example values are not rules |
| C-15 | PARTIAL | PARTIAL | agree | PARTIAL | gh114-authored: "proven offline regenerator" `design.md:151`; inherited: gh104 "archives first" paragraph `P:37`, "MUST be deleted" `C:41-45`, `I:310` past-state (low) |
| C-16 (a) | PARTIAL | NOT-CHECKABLE | agree | PASS (protocol label) | "A6" is the mandate's label for the export repair; the artifacts never use it and include the export (`proposal.md:38`, `P:31-166`). The gap is in the protocol wording, not the artifacts. |
| C-16 (b)–(p) | PASS ×15 | PASS ×15 | agree | PASS | every §2 decision found verbatim; (m) `experimento-gh104/scripts/gh104_gates.py:172-177` is the only `ENVELOPE_RE` |
| C-17 | PASS | PASS | agree | PASS | removed items absent; additions small and within D6/D12 |
| C-18 | PASS (62/62 format) | PARTIAL (2 without concrete values) | differ | PARTIAL (low) | format holds for all; `I:100-104` and `I:125-129` carry no concrete signature/label — suggestion |
| C-19 | PASS | PASS | agree | PASS | `#114`; FR02/03/11/13/14, NFR06/08 exist in `docs/PRD.md` |
| C-20 | PASS | PASS | agree | PASS | `openspec validate` valid |

### 2.2 Weaver deferral scan (T)

| ID | A | B | Agreement | Adjudicated |
|---|---|---|---|---|
| T-01 | 0 hits (90 files) | 0 hits (90 files; control 65 with `class `) | agree | PASS — no `TODO/FIXME/XXX` in `src/main`; command `rg -n "TODO\|FIXME\|XXX" <W> --glob '!**/target/**' --glob '**/src/main/**'` → exit 1 |
| T-01-post | 3 prose deferrals | 4 prose deferrals + 2 "unsupported" | agree on the union | `DexWeaver.java:452-454`, `:973`; `PointcutMatcher.java:146` (recorded decision); `MonitorInvokeBuilder.java:307-308`; `InstructionInjector.java:387-397` |
| T-02 | listed | listed | agree | 0 hits in the weaver prose; 28 hits in the base spec, all recorded decisions (gh62 deferrals, gh100 Layer-3, `deferred-constant` rows) except `:2536`, which gh114 A1 closes |
| T-03 | listed | listed | agree | every item of the two 27/08 documents mapped |
| T-04 | listed | listed | agree | gh100 OQ4 (register pressure) open; gh104 OQ2/OQ3 → A1; gh105 OQ2 and gh109 risk closed by their own tasks |
| T-05..T-08 | done | done | agree on every candidate | see §5 |

### 2.3 CrySL adherence (R)

| ID | A | B | Agreement | Adjudicated | Note |
|---|---|---|---|---|---|
| R-01 | PASS | PASS | agree | PASS | sha256 `d7bcc019…` matches `README.md:27`; 49/49 per-file OK; `C.UTF-8` gives the `6d92bc6d…` false alarm the README predicts |
| R-02 | PASS relabel | PASS relabel | agree | PASS | rules silent on `null`; `.mop` reads are recorded decisions of 2026-08-22 |
| R-03 | PASS relabel | PASS relabel | agree | PASS | rule predicates the array; loader test is API semantics |
| R-04 | PARTIAL | PARTIAL | agree | PARTIAL | producers verified; consumer list not closed (F-R-01); producer set a subset without stated criterion (F-R-02) |
| R-05 | PASS relabel | PASS relabel | agree | PASS | no `randomized` clause in `SecretKeySpec.crysl`; new read is clause-less (low) |
| R-06 | PARTIAL (medium) | PASS with ambiguity (low) | differ on severity | PARTIAL (medium) | "creation event" undefined for observed-but-refused creations; orchestrator confirmed `g3[] = {0,5,5,5,5,5}` (`<MON>/…:6555`) and `getDefault[] = {0,1,2,3}` (`:13853`): both are self-loops on the start state, so `getInstance(unsafe); init()` fails from state 0. 9 of 45 `@fail` files → medium (F-R-03) |
| R-07 | PASS relabel | PASS relabel | agree | PASS | three oracles agree; `wkb1` note (low) |
| R-08 | FAIL as written | FAIL as written | agree | FAIL | `divergence_record.csv:376` already carries the RSA `oracle-wart` row with the opposite disposition (F-R-04) |
| R-09 | PARTIAL | PASS on substance, record gap | agree on substance | PARTIAL | departure from the array object of predication; no record row planned; `Property.java` javadoc becomes false (F-R-05) |
| R-10 | PARTIAL | FAIL as written | differ on which rows | adjudicated for A | see §3.1 (F-R-06) |
| R-11 | done | done | agree | done | disagreements: A1 (`.mop` vs woven wrapper, recorded `conformance_record.csv:63`), RSA rule vs rule (row 376), digest-stream `after` kind (records vs `.mop`/`.aj`), design "two-parameter specifications" (low) |
| R-12 | done | done | agree | done | §7.10 and §7.17 resolved; §7.3/5/7/8/14 partially and by decision; §7.11 untouched and consistent |
| R-13 | done | done | agree | done | 10 items faithful/relabel-only; 2 departures (RSA, per-element credit); 0 defects against the rules |
| R-14 | PASS with caveat | PASS with caveat | agree | PASS | only the per-element credit moves `(site, event)` pairs among the labels; A1/A5/RSA are declared discontinuities |

## 3. Adjudications

### 3.1 R-10 — which records the A5 repair re-founds
- **A**: the only conformance rows written in no-finally semantics are `conformance_record.csv:116,117,119,120`; they say "an `after ... returning` advice never runs for a call that threw" but `r2`/`w2` are plain `after`; plus `divergence_record.csv:46` records A5 as "not repaired".
- **B**: rows 116–120 concern `after … returning` advices, which A5 leaves unchanged, and must not be rewritten; only row 46 applies.
- **Source**: `<SET>/DigestInputStreamSpec.mop:90` `event r2 after(byte[] data, int offset, int len, DigestInputStream s):` — no `returning`; `DigestOutputStreamSpec.mop:89` likewise; `<MON>/MultiSpec_1MonitorAspect.aj:465` and `:490` are `after (…) :` with no `returning`; `conformance_record.csv:116` reason text: "an `after ... returning` advice never runs for a call that threw".
- **Rationale**: B read the rows' own wording as the fact; the `.mop` and the aspect are the fact. The four rows are mis-attributed today and their reason becomes false after A5 (the body will run on the throwing call, so `offset >= 0` and `length[data] >= offset + len` acquire a reachable violated branch). Row 46 is the record of the decision A5 reverses, and no artifact names it. **A's reading stands; F-R-06 is medium.**

### 3.2 R-06 severity
- A: medium (9 files); B: low (two examples). Orchestrator confirmed the self-loops on the monitor (`:6555`, `:13853`) and that D7 (`design.md:134`) defines creation events only as "the events the automaton starts with", which in every `fsm`/`ere` is the accepting `getInstance`/constructor, not its refused twin. The label would contradict an ALG/FORB report on the same object. **Medium.**

### 3.3 C-11 inherited citations
- A: 36/40 stale; B: 8. The 28 extra are the seed-era census of `I:314`, which the base text (`openspec/specs/instrumentation/spec.md:2434`) itself frames as "measured on the frozen `jca`, carried into `jca_android` by the seed". They are historical by declaration, not current-state claims. **8 drift citations (low); the census paragraph is a P4 suggestion (F-low-03).**

### 3.4 C-16 (a) "A6"
- The mandate labels the export repair "A6"; no artifact uses the label (`rg '\bA6\b'` → 0 in the change). The export is in (`proposal.md:38`, `P:31-166`, `design.md` D12). **PASS; the label belongs to the protocol.**

### 3.5 C-18
- A passes format for 62/62; B flags two scenarios without concrete values (`I:100-104`, `I:125-129`). Both true. **PARTIAL, low, suggestion.**

### 3.6 One-sided medium findings verified by the orchestrator before refutation
- F-03 (wrapper is Java source): `<W>/advice-emitter/.../WrapperEmitter.java:24-25` "Emits `mop/MonitorWrappers.java` — a Java source file"; `:339` `Files.writeString(dir.resolve(WRAPPER_CLASS_NAME + ".java"), …)`. Confirmed.
- F-04 (`to_dict()` reaches `results.json`): `coverage.py:1033` `error_dicts = [error.to_dict() for error in self.errors]`; `result_processor.py:1139` and `:1178` call `get_errors()` for the JSON details. Confirmed.
- F-low-06 (`installTryCatch` requires a `TryCatchSpec`): `InstructionInjector.java:268-271` throws `IllegalArgumentException` when `plan.tryCatchSpec() == null`. Confirmed.
- F-02 (TypeResolver sites): `rg -n "new TypeResolver\(" <W> --glob '!**/target/**' --glob '**/src/main/**'` → `WrapperEmitter.java:232`, `BaksmaliDiffer.java:214`, `BatchRunner.java:182`. Confirmed.

## 4. Findings and refutation

Severity ≥ medium (sent to refuters):

| ID | Area | Type | Severity | Claim (short) | Refutation |
|---|---|---|---|---|---|
| F-01 | C | inconsistency | medium | Base `:248` and `:1851` keep INV-INS-122 as live measure-only; `:1851` also MUSTs a site-by-site enumeration of the effect on `jca` that the delta (`I:11`) declines by decision, with no MODIFIED entry for "The Java SE Specification Set Is Frozen"; 7 comment sites cite INV-INS-122 as measure-only and no task names them | **SURVIVES-WEAKENED.** Spec half holds: the sync skill preserves base content not mentioned in the delta (`.claude/skills/openspec-sync-specs/SKILL.md:52-71,129`) and 16.5 hand-syncs only `## Invariants`; `:1851` explicitly covers weaver repairs. Comment half overstated: 12.3 names `test_dexlib_instrumentation.py:901-958` and 14.2 names `architecture.md:176`; the other five sit in regions tasks 3.1–3.3/12.1–12.2 edit. Corrected claim: only the two base sentences need a MODIFIED entry. |
| F-02 | C | inconsistency + drift | medium | Task 2.3 (G2, wave 1) wires the class-existence predicate "where `TypeResolver` is constructed (`DexWeaver`, `WrapperEmitter`, `MonitorInvokeBuilder`, `AfterThrowingEmitter`)"; the real sites are `WrapperEmitter.java:232` (G3, same wave) and `BatchRunner.java:182` (G12); breaks D14 one-owner-per-file | **SURVIVES.** `TypeResolver` cannot self-wire (`TypeResolver.java:71` holds only imports); 1.2 leaves production at `s -> false`; neither 3.x nor 12.x mentions the wiring, so 2.3 either breaks D14 or leaves A4 inert. Also: `WrapperEmitter.resolveFqn` (`:647-676`), named in `design.md:88`/`I:138`, has no G3 task. |
| F-03 | C | inconsistency | medium | D5 says the after-finally wrapper is "emitted as dexlib2 instructions" and task 3.7 wants "baksmali of a generated wrapper" inside `advice-emitter`; the wrapper is Java source compiled later by `monitor-builder` | **SURVIVES.** `WrapperEmitter.java` has zero dexlib2 instruction code; `advice-emitter/pom.xml:17-44` has no baksmali; its tests assert on source strings (`WrapperEmitterTest.java:120-123`); compilation is a subprocess in `monitor-builder` (`MonitorBuilder.java:13-21`) whose tests compile nothing. The constructor half of D5 is fine (`dex-mutator` has reparse-based try-block tests). The spec scenario `I:173-177` describes a harness that does not exist for wrappers. |
| F-04 | C | inconsistency (unstated dependency) | medium | `value_fingerprint`/`value_class` "included in `to_dict()`" reach `results.json` details; the byte-identity scenario (`P:163-166`, task 11.5) against `data/results/estudo02_regen/estudo02_00/` cannot hold once G10 lands; G11←G10 unstated | **SURVIVES-WEAKENED.** Confirmed: `to_dict` has no filtering (`log.py:175-192`); the stored `estudo02_00/results.json` (20,741 detail entries) carries today's 16 keys. Overstated: the spec scenario is worded against `regenerate_tables.py`, which uses the same `_extract_task_data` (`regenerate_tables.py:56,167,230-233`), so it stays satisfiable; only `tasks.md:139`/`design.md:98` (diff against the stored snapshot) break, and only for `results.json`. Corrected claim: task 11.5 and D12's byte-identity check must exclude the two keys or run before G10; the five CSVs are unaffected. |
| F-R-01 | R | inconsistency | medium | `REPORTED_UPSTREAM` consumer list (`I:250`) claims closure but omits 11 of 15 key-origin `-NOBS-` codes fed by listed producers (`MacSpec.i2`, `SignatureSpec.i1/i2`, `KeyAgreementSpec.init1-4`, `KeyPairSpec.c1`, `TrustAnchorSpec.c1/c3`, `AlgorithmParametersSpec.init`) | **SURVIVES.** Listed producers gate the predicates on `conforms` (`KeyFactorySpec.mop:85-92,111-118`; `SecretKeyFactorySpec.mop:102-109`); the eleven unlisted sites read them under `NOT_OBSERVED` with a `-NOBS-` code; no artifact calls the list partial and `I:187` is universal. The "corpus-derived" clause is not verifiable from the artifacts and is dropped from the claim. |
| F-R-02 | R | gap | medium | Producer set is ~10 of ~22 ENSURES producers that report on their product, with a stated reason only for SecureRandom/KeyGenerator; after the RSA alignment `RSAKeyGenParameterSpec(1024)` → `KEYPAIRGENERATOR-NOBS-00` stays `not-observed` | **SURVIVES** (one example weakened). "Direct producer" is glossed only at `design.md:140` ("constructed specs, factory products, the KeyAgreement secret"), a category that includes the omitted RSA/DSA/DH/OAEP/PBEParameterSpec/MGF1/PKIX specs; all of them report by value and gate the write on `conforms`, and their readers carry `-NOBS-` codes. The RSA scenario holds exactly. Weaker example: KeyStore→TMF/KMF (KeyStore's refusal is an ordering failure, which never marks). |
| F-R-03 | R | inconsistency | medium | "creation event" undefined for observed-but-refused creations (`g3`/`g4`/`getDefault`/`f1`,`f2` in 9 of 45 `@fail` files); `getInstance(unsafe); init()` would be labelled `creation-unobserved` | **SURVIVES-WEAKENED.** Every self-loop confirmed on the monitor; population corrected to 10 files (`KeyStoreSpec.g2`, `<MON>:11532`). But D7's wording "the events the automaton starts with" literally includes the refused twins (`CipherSpec.mop:420-424`, `MacSpec.mop:455`, `SecureRandomSpec.mop:336`), so the plain reading already yields `sequence`. Corrected claim: no artifact defines or enumerates "creation event", no harness trace covers refused creation + use, and the ten files are split across four workers who will each read D7 alone. |
| F-R-04 | R | inconsistency | medium | RSA: `divergence_record.csv:376` already is the `oracle-wart` row, with the opposite disposition; D13/13.3 "add" a row; D-20.4 precedent used wart + `value-decision`; G-CONF would pass on row 376 unchanged | **SURVIVES.** Simulated the `.mop` edit on a scratch copy and ran G-CONF with the parity test's CLI: failures `[]`, verdict `DIVERGENTE` backed by row 376 unchanged (`gh104_gates.py:1489-1491,1511,1596-1597,1972`). "G-CONF SHALL pass" is already true and verifies nothing; the `.mop` comment itself names the missing route ("records a value decision of its own the way D-20 did"). |
| F-R-05 | R | gap | **high** (raised) | Per-element trust-manager credit departs from the rules' array object of predication; no divergence row planned (INV-INS-118); `Property.java:92-108` javadoc becomes false and task 1.3 rewrites only the `REPORTED_UPSTREAM` javadoc | **SURVIVES, STRENGTHENED.** INV-INS-118/141 are gate-enforced by content-keyed hunks (`scripts/gh104_divergence_record.py:146-211`, `tests/parity/test_gh104_specset_gates.py:77-91`): the live run exits 0 on 321 hunks, and a one-line edit at `SSLContextSpec.mop:231` + `TrustManagerFactorySpec.mop:218` produced 4 problems and exit 1. **This applies to every label edit in every seed `.mop` file, not only the credit**; the fragment scheme (`tasks.md:57`) carries codes and traces, not divergence rows, and task 13.3 plans the RSA row only. Task 13.7 ("run all gates") would fail for G6–G9's work as planned. Severity raised to high because it blocks the closing wave. |
| F-R-06 | R | inconsistency | medium | A5 record target: spec `:157`/task 13.3 say "the 58 events"; the actual rows are `conformance_record.csv:116,117,119,120` (mis-attributed as `after … returning`) plus `divergence_record.csv:46`, unnamed | **SURVIVES.** Only those four rows rest on throw semantics; `r2`/`w2` are plain `after`; the reachability reason dies after A5 (nuance: `DigestInputStreamSpec.mop:85-86` has a platform-forbids ground that could keep the `deferred-constant` disposition); `I:155`'s three named events have no such comments; row 46 is named nowhere. |

Adjudication after refutation: 10 of 10 medium findings survive (6 intact, 3 weakened, 1 strengthened to high). No finding was refuted.

Low findings (not sent to refutation; each confirmed by at least one reviewer at the cited line, and by the orchestrator where marked †):

| ID | Area | Type | Claim | Evidence |
|---|---|---|---|---|
| F-low-01 † | C | defect (text) | group ranges "G5–G5 … consumed by G5" and "minus the G5–G5 files"; critical path omits G2 | `tasks.md:57,121,38` |
| F-low-02 | C | inconsistency | INV-PLT-14 restated five→six files (`app_events.csv`) without a design sentence; base `:799` already owns that file | `P:25` vs base `platform/spec.md:184,799`; `result_processor.py:239-244` writes six |
| F-low-03 | C | drift / P4 | 8 inherited current-state citations stale (`ErrorCollector.java:38`→`:71`; `ErrorDescription.java:143`→`:203-204`; `result_processor.py:631/:999/:1038/:1034-1043/:1050-1064`; `regenerate_container.py:244`); inherited migration text now false (`P:37` "archives first", `C:41-45` "MUST be deleted", `I:310` "reported as InvalidSequenceOfMethodCalls") | base `instrumentation/spec.md:2434`, `core/spec.md:1137-1138`, `platform/spec.md:648-658`; archive dir `2026-09-14-gh104-…` exists † |
| F-low-04 | C | inconsistency | two normative scenarios name experiment-local scripts as oracles | `I:131-134` (`branch_target_hooks.py`), `P:163-166` (`regenerate_tables.py`) vs `design.md:114` |
| F-low-05 | C | gap | four scenarios without a task that makes them testable as written; two without concrete values | `I:161-171`, `I:263-266`, `I:359`, `P:179`; `I:100-104`, `I:125-129` |
| F-low-06 † | C | gap | who builds the catch-any `TryCatchSpec` for the constructor after-finally path is unstated (`installTryCatch` requires one; `AfterEmitter` emits none) | `InstructionInjector.java:268-271`; `EmitPlan.java:18,45`; `AfterEmitter.java:17-20`; `tasks.md:86` |
| F-low-07 | C | inconsistency | D14 says `Property.java`/`codes.csv` belong to the closing group; tasks 1.3/1.5 put them in G1; `NEW_SPEC_CONVENTIONS.md:200-207` differs from the fragment scheme | `design.md:161`, `tasks.md:53,55,25-27` |
| F-low-08 | C | inconsistency | small wording: INV-CORE-25 uses `{identity_message}` while the MODIFIED text keeps `{message}` plus a gloss; `vcls` defined as "runtime class of the bound object" (`A:3`) vs comma-joined element classes (`I:270`) | `C:23,30`; `A:3,36`; `I:270` |
| F-low-09 | C | suggestion | P4 wording: "proven offline regenerator", "(replaced binding-form tests)"; D13 hedges ("If G-CONF compares…") on a mechanism that exists (`gh104_gates.py:1511`); proposal Impact omits `experimento-gh104/scripts/gh104_gates.py`; `classExists` predicate input format (dotted vs internal vs descriptor) unspecified | `design.md:151,85,159,124,165-172`; `proposal.md:69` |
| F-low-10 | R | gap | census pins: two clause-less `RANDOMIZED` reads and every `validateAny(REPORTED_UPSTREAM)` read need a `propagation`/label-read disposition; pin delta must come from the graph script | `tasks.md:154`; `test_gh105_predicate_gates.py:1367-1370`; `gh105_predicate_graph.py:1268` |
| F-low-11 | R | suggestion | "platform default" is exact for TMF/SSLContext, approximate for `KeyManagerFactory.init(null, pw)` ("no key store") | `KeyManagerFactorySpec.mop:91-104` |
| F-low-12 | R | suggestion | `application-manager` also catches bundled-provider managers (non-boot loader); proposal gloss "the application's own class" narrower than the rule | `proposal.md:26` vs `I:186` |
| F-low-13 | R | suggestion | `reuse-after-final`: `wkb1` (`wrap`) reaches the same final state as `doFinal` (`<MON>:6563`) and task 8.4 names only "final-operation bodies"; Mac `doFinal; doFinal` (no re-`init`) stays `sequence` | `tasks.md:116`; `Mac.crysl:41`; `<MON>:12023-12029` |
| F-low-14 | R | inconsistency | label name vs mark condition: the mark is also written on a `NOBS` upstream (`I:250`), which the set's vocabulary calls "not a violation" (`PredicateVerdict.java:29-34`); downstream then reads `upstream-refused` after a reach limit | `I:250`; `proposal.md:27` |
| F-low-15 | R | suggestion | A5 also fires acceptance-point ENSURES writes on throwing calls (`KeyAgreementSpec.gs2` marks a buffer a `ShortBufferException` left unfilled); only the report side is declared | `KeyAgreementSpec.mop:311-317`; `I:155-157` |
| F-low-16 | R | inconsistency | design risk names `KeyStoreSpec`/`SSLContextSpec` as "two-parameter specifications"; both are single-parameter; no `.mop` of the set declares two | `design.md:221`; `KeyStoreSpec.mop:30`, `SSLContextSpec.mop:23`; `rg "^[A-Za-z]+Spec\([^)]*,[^)]*\)" <SET>/*.mop` → none |
| F-low-17 | R | suggestion | `gs1`/`gs2` mark via `conforms`, which is not D8's "local `reported` flag" and covers any earlier accusation of the agreement | `KeyAgreementSpec.mop:294-317`; `design.md:140` |
| F-low-18 | R | question | `IvChainJunction.use` with a `null` `AlgorithmParameterSpec` has the same "null = provider default" shape as the three labelled files and stays `not-observed` without evidence — outside the mandate, recorded as a question only | specsheet §7.8; `design.md:147` |
| F-low-19 | T | drift | weaver code and `architecture.md` cite `INV-INS-64/66/69`, which exist only in the archived gh52 delta; `EmitterDispatch.java:61` points at a `LIMITATIONS.md` that lives in `<R>/docs/` | `InstructionInjector.java:94`, `DexWeaver.java:449,480,958`, `<W>/architecture.md:395`; `rg "INV-INS-(64\|66\|69)\b" openspec/specs/` → none |

## 5. Weaver deferral candidates (questions for the researcher, not tasks)

Both T reviewers found the same set; IDs of both are given. "Class" per the researcher's distinction: **R** = repair that does not alter which `(site, event)` pairs are accused; **B** = alters the accused set.

| # | Candidate | Evidence | Still true | Class | Cost / risk | Benefit / how measured | Static check | Overlap with gh114 | Question |
|---|---|---|---|---|---|---|---|---|---|
| 1 (T-A-04, T-B-01) | `shouldWrap` routes every `after` advice, `throwing` included, to the wrapper; the wrapper has no `catch` and maps only `returning`; `TRY_CATCH_WRAP` never reaches a wrapped site | `achados:187-206` | yes: `WrapperEmitter.java:185-187`, `:794-800`, `:833-836` | R today (0 `after … throwing` events in `jca_android`: the 4 `throwing` hits are comments); B the day one is declared | one predicate + one test; trivial | none measurable now; closes a latent path | yes | not covered; delta `I:157` says `after throwing` "keeps its current shape" | leave out, as the delta states? |
| 2 (T-A-05/16, T-B-02) | no per-advice census in `WeaveReport` (13 aggregates); an advice matching zero sites campaign-wide is invisible | `achados:208-229` | yes: `DexWeaver.java:558-565`, `:978-995`; `BatchRunner.java:288-303` | R (measurement) | one map field, aggregation, JSON, one test; ~1 day; low | the number that would have shown A1; verifiable on a synthetic DEX | yes | partially: gh114 adds only `wrapperTargetsUnresolved` | stays out of gh114? |
| 3 (T-A-06, T-B-03) | register-pressure defensive skip (`plansSkippedHighRegister`), comment names the fix | `DexWeaver.java:448-456`; gh100 `design.md:241` | yes | B where non-zero | medium (allocator) | measured 0 on 5 workspace APKs (T-A c11); corpus sum unknown | yes for the decision | not covered | sum the counter over the estudo02 `instrument_results.json` before deciding? |
| 4 (T-A-02 gaps, T-B-04) | five dot→slash converters; gh114 names three; `PointcutMatcher.java:552` (Kotlin suspend owner) is outside D4's reach | `achados:419-454` | yes at all five: `TypeResolver:99,102`, `AndroidClassIndex:223-224`, `InheritanceResolver:155`, `DexWeaver:255`, `PointcutMatcher:552` | R (verification of A4) | 5 unit cases; small | A4 uniform by test | yes | partial | list the five in task 2.3, or leave? |
| 5 (T-A-15, T-B-05) | `resolveFqn` ladder (BUILTIN, wildcard, `java.lang`) stays unverified after D4 | `TypeResolver.java:110-130`; `achados:456-470` | yes; D4 keeps it by decision | B (unknown size) | script over the descriptor vs `android.jar` | count of names reaching unverified rungs | yes | partial | a static count, or leave with one sentence in D4? |
| 6 (T-A-02 (i), T-B-06) | `TypeResolver` javadoc "never probes an external classpath" becomes false after D4; no task rewrites it | `TypeResolver.java:24-27` | yes | doc (P4) | trivial | — | yes | partial | add to task 2.3, as 3.6 does for `AfterEmitter`? |
| 7 (T-A-03, T-B-07) | merged wrapper with plain `after` + `after returning`: the handler must run only the plain-`after` calls; only a single-advice scenario exists | `WrapperEmitter.java:794-800`; `design.md:127` | yes | inside A5; a wrong split alters the accused set | one more shape test | prevents the symmetric error | yes | covered in wording, not in scenario | add one mixed-group scenario/test? |
| 8 (T-B-11) | `divergence_record.csv:45-46` say A4/A5 are "not repaired"; gh114 plans only the RSA row | `divergence_record.csv:45-46` | yes † | records | one edit per row in G13 | record stays truthful | yes | not covered (see F-R-06) | have 13.3 annotate rows 45–46? |
| 9 (T-A-10) | `plansSkippedAliasing` is an indirect A2 signal; comment at `DexWeaver.java:480-483` predates all-`after` wrapping | `DexWeaver.java:480-514` | yes | doc / measurement | comment edit; one sweep column | free cross-check of A2 | yes | not covered | report it in the sweep, reword in 4.3, or leave? |
| 10 (T-A-18) | platform jar chosen by lexicographic maximum (`android-4` beats `android-37`) | `ConfigResolver.java:111-122,170-178`; `LIMITATIONS.md:94-141` | yes | R/B depending on the machine | numeric comparator; trivial | A2/A4 evidence depends on the right jar | yes | not covered | leave as recorded? |
| 11 (T-A-07/08/09/11/13, T-B-08/09/10) | `monitorOwnerFor` fallback; `adviceexecution` vacuous (gh62 frozen); `around` no-op (gh62); gh100 Layer-3 arm (validator, ajc — not proposed); gh105 OQ2 and gh109 risk closed by measurement; `invoke-static/range` unsupported for after-throwing (inert while #1 is inert) | as cited by both reviewers | — | — | — | — | — | — | leave; no question |

## 6. CrySL adherence table

| Item | Rule | `.mop` | Monitor | Classification | Record | Finding |
|---|---|---|---|---|---|---|
| `platform-default` TMF `init(null)` | `TrustManagerFactory.crysl:14,28` (silent on null) | `TrustManagerFactorySpec.mop:146-155`; decision `:102-112` | `init[]={4,3,4,4,4}` `:16369` | relabel only | none needed | — |
| `platform-default` KMF `init(null,pw)` | `KeyManagerFactory.crysl:15,31` | `KeyManagerFactorySpec.mop:121-130`; `:91-104` | `init[]={4,4,3,4,4}` `:10291` | relabel only | none needed | F-low-11 |
| `platform-default` SSLContext ×3 | `SSLContext.crysl:18,32-34` | `SSLContextSpec.mop:222-248`; `:176-185,204-208` | `init[]={3,2,3,3}` `:13856` | relabel only | `divergence_record.csv:279` | — |
| `application-manager` | `SSLContext.crysl:33` (array) | `SSLContextSpec.mop:236-239` | same | relabel only | none | F-low-12 |
| per-element trust-manager credit | `SSLContext.crysl:6,33`; `TrustManagerFactory.crysl:7,33` (array) | `TrustManagerFactorySpec.mop:215-219`; `SSLContextSpec.mop:231-239` | `gtm1[]={4,4,4,2,4}` `:16370` | **departure** (object of predication; kind `predicate-store`/`behavioural`, not one of INV-INS-125's five value kinds) | **none planned** | F-R-05 |
| `upstream-refused` / `REPORTED_UPSTREAM` | ENSURES/REQUIRES chains (`SecretKeySpec.crysl:23,27`, `KeyAgreement.crysl:51`, …) | producers gate writes on the conforming branch (`SecretKeySpecSpec.mop:121-124,187-190`; `KeyFactorySpec.mop:91,117`; `SecretKeyFactorySpec.mop:108`; `KeyAgreementSpec.mop:294-316`; bridges `KeySpec.mop:75-81`, `SecretKeySpec.mop:119-126`) | `ensure` per `(object, Property)` `PredicateStore.java:488-512` | relabel only where wired; enumeration incomplete both ways | census pins `test_gh105_predicate_gates.py:1367,1387` | F-R-01, F-R-02, F-low-14, F-low-17 |
| `random-key-material` | `SecretKeySpec.crysl:23` (no `randomized`) | `SecretKeySpecSpec.mop:110-120,176-186`; `:79-91` | `c1/c2[]={1,2,2}` `:15048-15049` | relabel only; clause-less read | pins move | F-low-10 |
| `creation-unobserved` | ORDER of each rule (`TrustManagerFactory.crysl:22`, `KeyPair.crysl:20`, …) | `@fail` blocks; fsm/ere openings | start-state failures `:16369`, `:11052`, `:13856`, `:6557`, `:12021`; refused-creation self-loops `:6555`, `:10290`, `:13853`, `:15265-15266`; `reset()` clears state + category flags only `:16521-16527` | relabel only; definition gap on 9 files | none needed | F-R-03 |
| `reuse-after-final` | `Cipher.crysl:85`; `Mac.crysl:41` | `CipherSpec.mop:414-418,461-472`; `MacSpec.mop:455` | Cipher `i1/i2` from `end` → 5 `:6556-6557`; Mac from 4 → 5 `:12021-12022` | relabel only, faithful | `divergence_record.csv:94` | F-low-13 |
| RSA `{2048,3072,4096}` | `RSAKeyGenParameterSpec.crysl:15` vs `KeyPairGenerator.crysl:29` | `RSAKeyGenParameterSpecSpec.mop:33-39` | `c1[]={1,2,2}` `:13685` | **departure** (rule vs rule; D-21 evident intent; not one of the five) | **exists with opposite disposition**: `divergence_record.csv:376`; `conformance_record.csv:123` is exponent only | F-R-04 |
| A5 window clauses | (weaver) | 58/202 plain `after` (`rg -n "^\s*event \w+ after\s*\(" <SET>/*.mop \| rg -v "returning\|throwing" \| wc -l` → 58; total events 202) | `.aj:465,490,575,754,907` plain `after` | weaver repair | `conformance_record.csv:116,117,119,120` (mis-attributed); `divergence_record.csv:46` | F-R-06, F-low-15 |
| evidence keys `vfp`/`vcls` | none | every `-NOBS-` `addError` (D10) | `ErrorDescription.java:63-65` leading-key extraction; `ErrorSummary` identity excludes message | faithful (no verdict reads them) | none | — |

Specsheet §7 re-check: item 10 resolved (`application-manager`, credit, `vcls`); item 17 resolved by A5; items 3, 7, 14 partially resolved and the remainder by recorded decision (`I:252`); item 5 untouched and load-bearing for `gs1/gs2`; item 8 resolved for TMF/KMF/SSLContext only; item 11 untouched and consistent.

## 7. Proposed revisions (for `/opsx:update`, none applied)

Pending the refutation pass (§4), the revisions the surviving findings would call for:

1. **F-01** — add `### Requirement: The Java SE Specification Set Is Frozen` under MODIFIED in `I`, rewriting the `:1851` paragraph to record the 2026-09-15 decision (discontinuity declared, not enumerated) and dropping the INV-INS-122 sentence; extend task 16.5 to re-anchor base `:248` to INV-INS-159; name the 7 comment sites in tasks 3.1/12.1–12.3/14.2.
2. **F-02** — restrict task 2.3 to `TypeResolver`; move the wiring of `WrapperEmitter.java:232` to G3 and of `BatchRunner.java:182` to G12 (G12 then also needs G2); fix the site list; state in D4 the predicate's input format (dotted FQN) and the adapter.
3. **F-03** — D5 wrapper bullet: Java source in `MonitorWrappers.java`; task 3.7 asserts the source shape in `advice-emitter`, and the bytecode-shape assertion moves to a `cli`/`monitor-builder` test or to the after-sweep of 15.3.
4. **F-04** — either keep the two fields out of `to_dict()` (they are inside `message`) or restate `P:163-166`/task 11.5 as byte-identical for the five CSVs and `results.json` identical modulo the two keys; state G11←G10.
5. **F-R-01 / F-R-02** — make the rule normative and derive both lists from `predicate_graph.csv` (readers of predicates written by marking producers; ENSURES producers whose write is gated on a value/origin report), minus SecureRandom/KeyGenerator by the stated decision; or keep the enumerations and record, per omitted site/producer, the reason. This is a scope question for the researcher: the 2026-09-15 decision says "direct producers plus the `getEncoded` bridge" and does not define "direct producer".
6. **F-R-03** — D7 and `I:189`: define "creation event" as every event that binds the monitored object through `returning` (constructors, `getInstance*`, `getDefault`), refused and forbidden twins included, and have their bodies set `creationObserved`; add one trace per family asserting `sequence`, not `creation-unobserved`, for `getInstance(unsafe); init()`.
7. **F-R-04** — task 13.3: supersede row 376 (keep the measurement, replace the disposition, add `gh114:9.2`), add a `value-decision` row as D-20.4 did, add the keysize row to `conformance_record.csv` (new, not "updated"); INV-INS-167 names both rows; reconcile INV-INS-125's definition of `oracle-wart` with `NEW_SPEC_CONVENTIONS.md:213-216` or cite D-21 in INV-INS-167.
8. **F-R-05 (high)** — the divergence-record gate is content-keyed per hunk, so every label edit in a seed `.mop` file needs a `divergence_record.csv` row or the gate of task 13.7 fails. Either the fragment scheme (task 1.7, `fragments/codes_g<n>.csv`) also carries the divergence rows each spec worker owes, merged by G13 in 13.3, or G13 writes them from the diff; plus a `predicate-store`/`behavioural` row for the per-element credit (`SSLContextSpec.init`, `TrustManagerFactorySpec.gtm1`); task 1.3 rewrites both `GENERATED_TRUST_MANAGER(S)` javadoc paragraphs.
9. **F-R-06** — task 13.3 names `conformance_record.csv:116,117,119,120` (correct the advice kind and the reason; decide whether the two now-reachable guards get a code or stay `deferred-constant`), `divergence_record.csv:46` (supersede) and rows 45–46 generally, and the two `.mop` comment blocks (`DigestInputStreamSpec.mop:83-85`, `DigestOutputStreamSpec.mop:84`); replace "the 58 events" with the listed rows.
10. Low findings: F-low-01 (fix three ranges), F-low-02 (one sentence in D12), F-low-03/09 (P4 wording, refresh two Java line numbers, drop the gh104 paragraph and the "MUST be deleted" sentence), F-low-04 (name the sweep script and "the file-major output" instead of experiment-local scripts), F-low-05 (one trace `cipher_unknown_key`, an `ErrorDescription` case in 1.4, concrete values for two scenarios, and either a fixture-run task for the `doPhase` scenario or a shape-only rewording), F-low-06 (task 4.5 states that `DexWeaver` builds the catch-any `TryCatchSpec`), F-low-07 (D14 wording), F-low-08 (one formula, one `vcls` definition), F-low-10 (dispositions for the clause-less reads), F-low-11/12 (`codes.csv` label notes), F-low-13 (name `wkb1` in 8.4), F-low-14 (rename or mark only on non-`NOBS`), F-low-15 (one sentence on acceptance-point writes), F-low-16 (replace the risk sentence), F-low-17 (D8 sentence on `conforms`), F-low-19 (outside gh114; note for a later doc pass).

## 8. What this review did not do

- No artifact was edited; no implementation started.
- No comparison, execution or oracle involving the ajc weaver was used or proposed.
- `docs/analise_*` and `docs/handoff/` were not read by the orchestrator or any subagent.
- The frozen `jca` set was not measured.
