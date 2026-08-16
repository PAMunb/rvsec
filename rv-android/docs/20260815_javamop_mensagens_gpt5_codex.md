# First-Stage Independent Validation of the JavaMOP Messages Plan and Its Adversarial Review

**Date:** 2026-08-15  
**Reviewer:** GPT-5 Codex  
**Scope:** read-only validation; no product, JavaMOP specification, audit, article, or experiment artifact was changed.

> **Status and scope qualification:** this report is a first-stage independent validation, not
> the completed scientific protocol requested by
> `20260815_javamop_mensagens_validacao_prompt.md`. It is sufficiently evidenced to block the
> plan's implementation as written and to guide the next verification phase. It is not sufficient
> to close the investigation, certify all 23 JavaMOP specifications, or establish historical
> runtime causality for every CSV stratum. Section 2 records the protocol deviations and §8 lists
> the work still required for a protocol-complete report.

## 1. Executive summary

### Overall verdict

Within the evidence actually examined, the plan is **INCOMPLETE and materially stale**, although
its central diagnosis is sound. The adversarial review is **substantially stronger and mostly
correct**, but it is not an independent proof: several claims are overstated, one stated reason
for dead code is contradicted by current source, and its numerical reproduction is not preserved
as an artifact. This verdict is a justified blocking/prioritisation decision, not a certification
that the full validation protocol has been exhausted.

The plan's durable core is:

1. the three-argument `ErrorDescription` constructor literally supplies `"unknown"`;
2. JavaFSM completes absent transitions into an implicit sink and defines `@fail` as the sink-state predicate;
3. handler text is inserted into a monitor instance method;
4. the reference CSV has 70,760 `unknown` rows, exactly the 70,760 `InvalidSequenceOfMethodCalls` rows.

The plan must nevertheless not be implemented as written. It predates the gh100 weaver repair, ignores gh101 and the `jca_android` rejection, treats a frozen `jca` as editable, misstates some CrySL semantics, assumes a pre-failure state that is unavailable at `@fail`, and proposes schema and identity changes without first changing their recorded contracts.

The review correctly supplies most of those corrections. Three important qualifications remain:

- **Knocked down:** its explanation that `BaseMonitor.getHandlerCallingCode` is dead because `EventDefinition.condition` is never assigned is false in the current tree: the JavaMOP AST constructor explicitly assigns and removes `condition()` from the pointcut. Whether the later rv-monitor branch is unreachable needs a different, end-to-end proof.
- **Knocked down:** its statement that gh100 wrapper merging is behaviorally the direct cause of every corrected empty-value case is too broad. The pre-gh100 collision mechanism is proven for the recorded artifact, but the post-repair runtime effect was not exercised in the cited Layer-3 device arm; gh100 itself records that descriptor/DEX arrival does not prove logcat arrival.
- **Knocked down:** the review labels its CSV pass as independently re-measured but leaves no durable script/output. The figures are independently reproduced here, but the review's own numerical evidence is `MEASURED`, not `PROVEN` or independently reproducible from that report alone.

Three central confirmations are:

- **CONFIRMED:** 97,018 rows, 19 messages, 70,760 `unknown`, and zero counterexamples to `unknown ⇔ InvalidSequenceOfMethodCalls`.
- **CONFIRMED:** missing FSM entries are completed to the extra sink, and `fail condition` tests that sink.
- **CONFIRMED:** Study 03 uses frozen `jca`, keeps gh100's weaver repair, and reverts the identity-keyed `ExecutionContext`; `jca_android` remains NOT READY.

### Recommendation

Use a two-stage programme, but refine the review's T0/T1 split into three gates:

1. **B0 — evidence only:** measure the first Study 03 outputs as the post-gh100 baseline. No implementation.
2. **T0 — contracts and transport:** establish message grammar, explicit synthetic sentinels, parser accounting, collector escaping/null behavior, and a structured dedupe decision. No `.mop` semantic edit.
3. **T1 — authorised successor set:** only after the researcher resolves audit §7 and names a post-E3 set, repair the specification and add event-bearing messages. Treat each automaton/predicate change as a formal-language change, not a textual patch.

Generator/runtime changes (`previousState`, event-name tables, static site IDs, end-of-trace support) should be a later T2 justified by measurements from T1.

## 2. Method

### Protocol and deviations

Three independent subagents were run in parallel:

| Pass | Dimensions | Main evidence opened |
|---|---|---|
| A | V1, V2, V9 | both reports, core/runtime/parser sources, `errors.csv` |
| B | V3, V4, V8 | generator/runtime, generated monitors, CrySL and `.mop`, audit syntheses |
| C | V5, V6, V7 | dexlib2, Python consumers, gh100/gh101, Git and Study 03 records |

This organisation covered all nine dimensions, but it did **not** satisfy the prompt's literal
requirement for at least one context-isolated subagent per dimension. Each subagent covered three
dimensions, so cross-dimension context could influence its conclusions. A protocol-complete run
requires nine isolated passes (or nine explicitly isolated context passes), followed by primary
reopening and contradiction resolution.

The primary reviewer then independently reopened material sources and reran the CSV measurements. Agreement between passes was used only to select discriminating checks, never as proof.

The requested `sequential-thinking` MCP was not available. I did not simulate or claim its use. The replacement was the following concise scientific log per decision:

- **Question:** is the disputed claim observable in source/artifact/data?
- **Hypothesis:** state the plan and review alternatives separately.
- **Test:** reopen the source or execute a read-only measurement.
- **Evidence:** quote `file:line`, or give the exact measured definition.
- **Result:** CONFIRMED / IMPRECISE / WRONG / INCOMPLETE.
- **Uncertainty:** mark unexecuted runtime or unavailable oracle work `NOT_VERIFIED`.
- **Next decision:** retain, rewrite, defer, or reject the proposed work.

No emulator was started or managed. No monitor generation was needed. Temporary computations were executed from standard input and did not modify the tree. The repository was already heavily dirty; all pre-existing changes were preserved.

The following requested activities were deliberately not represented as completed:

- no fresh monitor generation or standalone/merged compilation was executed in scratch;
- no JVM formal harness, mutation corpus, model checker, or language-equivalence checker was run;
- no G10/device replay was run through `rv-experiment` or `rv-platform`;
- V4 discriminated the central disputed cases, but did not independently re-adjudicate every
  claimed false positive and every D01–D50 entry against both the original and api30 oracles;
- the audit's 558 claims and 119 phenomena were not independently reproduced one by one;
- gh100/gh101 history and recorded artifacts were checked, but the full replication package was
  not re-materialised byte-identically;
- the CSV calculations were independently rerun, but this report did not create the durable
  script/hash/output package that the final scientific record should contain.

Consequently, references to “confirmed” below are scoped to the named claim and evidence. They do
not imply that the surrounding subsystem or specification set has been certified.

### Evidence classes

- **PROVEN:** executed and reproduced with a deterministic check in this session.
- **MEASURED:** computed from the named dataset under an explicit definition.
- **OBSERVED_IN_ARTIFACT:** read directly from source, generated artifact, Git, or recorded evidence.
- **INFERRED:** causal interpretation consistent with observations but not experimentally isolated.
- **NOT_VERIFIED:** required evidence was unavailable or execution was out of scope.

## 3. Verdicts by dimension

Path abbreviations in the tables are expanded in §9. Every quoted line was reopened by the primary reviewer or independently by a designated pass; material conclusions were reopened again by the primary reviewer.

### V1 — Cross-factual verification

| Claim | Evidence | Class | Verdict |
|---|---|---|---|
| Three-argument errors become `unknown` | `ErrorDescription.java:34-36`: `this(type, spec, location, "unknown")` | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Message is outside runtime identity | `ErrorDescription.java:132-134`: `expecting is not part of the identity`; `ErrorSummary.java:73-119` compares spec/type/class/method/location | OBSERVED_IN_ARTIFACT | CONFIRMED |
| The behavior is deliberately pinned | `ErrorDescriptionTest.java:179-193`: two different `expecting` values are equal and dedupe to one | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Missing transitions enter a sink | `JavaFSM.java:112,133-142`: default is `countState`, appended sink maps to itself | OBSERVED_IN_ARTIFACT | CONFIRMED |
| `@fail` is the sink predicate | `JavaFSM.java:158`: `fail condition = $state$ == countState` | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Handler body is inserted verbatim after substitutions | `HandlerMethod.java:39-49,81-106`: `__RESET`→`this.reset()` and `ret += handlerCode` | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Event body precedes state/category computation | `BaseMonitor.java:434-454`: `monitoringBody` is emitted before category code | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Direct field names are portable at `@fail` | `BaseMonitor.java:145-165` can select an atomic monitor; `IMonitor.java:19,25` supplies accessors | OBSERVED_IN_ARTIFACT | PLAN WRONG; REVIEW CONFIRMED |
| Pre-fail state is available at `@fail` | `JavaFSM` transitions before category evaluation; only current state and last event accessors exist | OBSERVED_IN_ARTIFACT | WRONG |
| Message must be composed before reset | `BaseMonitor.java:951-970` resets last event, state and flags | OBSERVED_IN_ARTIFACT | CONFIRMED |
| `condition()` is removed from the pointcut and emitted as a prologue | JavaMOP `EventDefinition.java:150-156` assigns/removes it; `RVDumpVisitor.java:47-51` emits `if (!(cond)) return false` | OBSERVED_IN_ARTIFACT | REVIEW CONFIRMED on mechanism |
| `EventDefinition.condition` is never assigned | the same `EventDefinition.java:150-154` explicitly assigns it | OBSERVED_IN_ARTIFACT | REVIEW WRONG |
| `BaseMonitor.java:604-610` is dead | current source contains a condition branch at `:603-610`; no full data-flow proof was executed here | NOT_VERIFIED | REVIEW OVERSTATED |
| Android collector escapes messages | logcat `ErrorCollector.java:36-40` calls raw `Log.v`; escape call is commented | OBSERVED_IN_ARTIFACT | PLAN/REVIEW CONFIRMED |
| Re-enabling the commented call is safe | `ErrorCollector.java:44-49` rebuilds quoted text from original `data`, preserving newline, and would quote the whole CSV line | OBSERVED_IN_ARTIFACT | WRONG |
| JSE collector is fully canonical | CSV collector `:40-43,83-90` escapes only `expecting` but contains the same newline bug | OBSERVED_IN_ARTIFACT | IMPRECISE |
| Parser fabricates generic fields | `logcat_parser.py:305-316,352-368`: `error_type := spec`; Format 3 source is `Unknown Source:1` | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Current writer has eleven columns and source | `result_processor.py:562-575` exact header | OBSERVED_IN_ARTIFACT | CONFIRMED |
| `unique_msg` has five `:::` fields and excludes source | `log.py:90-113` | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Dynamic localisation keeps only one frame | `ViolationRecorder.java:53-59` returns `relevantStack.get(0)` | OBSERVED_IN_ARTIFACT | CONFIRMED |
| It allocates a stack for each attempt | `ViolationRecorder.java:37-38`: `new Exception().getStackTrace()` | OBSERVED_IN_ARTIFACT | CONFIRMED |

Sample coverage exceeded forty reopened locations when the V3–V7 entries below are included.

### V2 — CSV evidence

The reference file was independently parsed with Python's `csv.DictReader`. `error_type` was defined exactly as `unique_msg.split(":::")[3]`.

| Quantity | Definition | Result | Verdict on documents |
|---|---|---:|---|
| Rows | all data rows | 97,018 | both confirmed |
| Apps with errors | distinct `apk` in `errors.csv` | 113 | plan's 163 is incomplete context; 163 belongs to the broader selected corpus |
| Distinct messages | distinct `message` | 19 | confirmed |
| Unknown | `message == "unknown"` | 70,760 (72.93%) | confirmed |
| Biconditional errors | XOR of unknown and InvSeq | 0 | confirmed |
| Pairing shadow | sum of `min(InvSeq, concrete)` per `(apk,rep,tool,spec,class,method)` | 26,152 | plan number confirmed, prose imprecise |
| Co-location shadow | InvSeq rows in groups containing any concrete row | 32,411 | review correction confirmed |
| Time-key groups | `(apk,rep,tool,time,spec,class,method)` | 46,330 total; 20,507 mixed; 32,232 unknown in mixed groups | confirmed, but “event” is stronger than timestamp resolution proves |
| Funnel | distinct `(apk,spec,class,method,message)` then remove unknown then empty found | 661 → 207 → 136 | confirmed |
| Exact ten-column keys | distinct complete rows | 85,257 | confirmed |
| Duplicate excess | sum `(group size - 1)` for exact rows | 11,761 | confirmed definition |
| Largest exact group | maximum exact-row multiplicity | 6 | plan's 3,098 is wrong; review confirmed |
| Empty observed value | message ends `but found .` | 8,843 | confirmed |

The fourth funnel stage is not a stable fact until “third-party” is formally defined. Prefix lists, two-segment package ownership, full-package ownership, shaded dependencies, and generated namespaces answer different questions. Therefore “28 actionable findings”, “73.4% third-party”, and the 3,465× amplification are **WRONG as universal measurements**. They may be outputs of an undisclosed classifier, not reproducible claims.

### V3 — Generator and runtime semantics

| Topic | Evidence/result | Class | Verdict |
|---|---|---|---|
| Sink completion | `JavaFSM.java:112-142,158` | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Persistent `@fail` | sink self-loops; handler categories are evaluated after subsequent events; reset normally re-arms | OBSERVED_IN_ARTIFACT | CONFIRMED, with KPG no-reset volume risk |
| Reset | `BaseMonitor.java:951-970` resets generated local state/flags, not arbitrary specification fields | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Event body order | `BaseMonitor.java:434-454` | OBSERVED_IN_ARTIFACT | CONFIRMED |
| Condition | JavaMOP prologue at `RVDumpVisitor.java:47-51` | OBSERVED_IN_ARTIFACT | plan mechanism wrong; trace-hole conclusion plausible |
| Monitor shape | atomic selection at `BaseMonitor.java:145-165`; portable accessors in `IMonitor.java:15-25` | OBSERVED_IN_ARTIFACT | review confirmed |
| Pre-fail state | not retained by the public monitor interface | OBSERVED_IN_ARTIFACT | WS-1.4 not viable without bookkeeping/generator support |
| Event IDs | generated artifacts enumerate event methods in declaration order | OBSERVED_IN_ARTIFACT | CONFIRMED for present generator, should be contract-tested before hand tables |
| State IDs | produced after minimisation and may merge/renumber symbolic states | OBSERVED_IN_ARTIFACT | hand-written state table rejected |
| Static declarations | raw user declarations and Java modifiers have a valid emission path; example exists in JavaMOP examples | OBSERVED_IN_ARTIFACT | viable, not generated in an RVSEC oracle here |
| `RVM_loc` | commented/threaded fragments exist, but the dexlib2 descriptor call carries only advice arguments | OBSERVED_IN_ARTIFACT | not a re-enable; cross-tool feature |
| End of trace | JavaMOP has `endProgram`/`endObject` mechanisms; RVSEC specs and dexlib2 do not integrate them | OBSERVED_IN_ARTIFACT | plan incomplete; proposed radius is generator + weaver/runtime |

Parameterless/root-slice fan-out and cloning are important but were not re-executed dynamically. Generated entry points and monitor cloning support the mechanism; contamination magnitude remains `INFERRED`.

### V4 — CrySL ↔ `.mop` fidelity

| Case | Reopened evidence | Result |
|---|---|---|
| SecureRandom repeated `nextBytes` | `SecureRandom.crysl:38-39` allows `End*`; `SecureRandomSpec.mop:155-161` omits `next2` from `end` | translation deviation; real false positive |
| Cipher `doFinal()` without update | `Cipher.crysl:75-85` excludes `f1` from `FINWOU` and requires `Update+` before `DoFinal`; `.mop:176-195` mirrors that distinction | plan's “correct common code” claim is wrong; CrySL is intentionally strict |
| Cipher re-init after completion | CrySL `ORDER` has `Init+` only before usage | plan's false-positive label is wrong against its stated oracle |
| KeyPair constructor | original `KeyPair.crysl:19-20` starts with `Con`; api30 uses optional `co?`; frozen `.mop:23-41` requires the constructor and `jca_android` still does | faithful to the original oracle but divergent from api30; documents must name the oracle before calling this a false positive |
| MessageDigest reset | CrySL event/order block contains no reset; `.mop:74-76` declares it but `.mop:108` omits it from ERE | declared-but-unordered translation defect |
| KeyPair private property | `.mop:35-39` stores the private key as `GENERATED_PUBLIC_KEY` | authoring defect, already repaired in derived work |

For every future correction, the oracle class must be recorded as `[jca]`, `[gh101]`, `[tool]`, or `[oracle]`. “More permissive” is not synonymous with “more correct”: availability rules and recommendation rules intentionally differ.

### V5 — Weaver and localisation

| Topic | Evidence/result | Class | Verdict |
|---|---|---|---|
| Pre-gh100 collision | generated `gh92_e2e2/.../MonitorWrappers.java:588-616` contains multiple same-signature TMF wrappers; gh100 records last-write loss and merge | OBSERVED_IN_ARTIFACT | confirmed historical mechanism |
| Truncation | gh100 census records nine dropped events, eight error emitters | OBSERVED_IN_ARTIFACT | plan incomplete; review confirmed |
| Return matching | dexlib2 `PointcutMatcher` compares return descriptors unless wildcard | OBSERVED_IN_ARTIFACT | Signature/TMF pointcut defects are real on Android |
| Debug loss | `RegisterShifter.cloneInstructions` rebuilds instructions/try blocks but not debug items | OBSERVED_IN_ARTIFACT | mechanism confirmed, campaign impact not measured |
| Scope | descriptor exclusions omit common Android/Kotlin/Google/okhttp namespaces; coverage has a divergent filter | OBSERVED_IN_ARTIFACT | confirmed policy split |
| 8,371 empty + 643 X509 | collision + global/root value inheritance predicts both strata and matches pre-fix artifact | OBSERVED + INFERRED CAUSAL | high confidence, not a controlled runtime proof |
| SecureRandom 12,400 | call-site profile and the CrySL/automaton mismatch support missing `next2`; collision does not fit dominant `nextBytes` sites | INFERRED | review's preferred hypothesis is stronger, still not PROVEN without replay |

The review is right to demote debug preservation from “highest-value” to “real but unmeasured”. A static weave-site manifest is a better localisation primitive than expanding the dynamic stack on every violation, provided its ID is stable across instrumentation and joins do not depend on stripped line tables.

### V6 — Python pipeline, contracts, and consumers

| Proposed change | Direct impact |
|---|---|
| Rich free-text message | commas currently survive because Format 2 rejoins `parts[6:]`; newline can become a second RVSEC record; `:::` corrupts the five-part identity contract |
| New CSV columns | breaks exact eleven-column writer tests, `INV-PLT-19`, gh103's exact header reader, and frozen campaign consumers unless a coordinated OpenSpec delta is made |
| Synthetic sentinel | changes generic `unique_msg` values and downstream grouping, but corrects fabricated-data semantics; must be explicit and versioned |
| Message in identity | flips `ErrorDescriptionTest:179-193`, raises cardinality with observed values, and becomes unbounded if object identity appears in text |
| Structured event/clause ID | bounded alternative; requires runtime model, parser/schema and consumer contract changes together |
| Escaping | fixing the helper is safe while dormant; enabling whole-line quoting is incompatible with the current positional parser |
| Dedupe/rate limit | changes counts by design; suppressed totals must be emitted so measurement remains auditable |

The parser's three-format heuristic is not a schema. The gradual path should introduce an explicit format/version marker before adding fields. Until then, keep the human message last, single-line, and free of `:::`.

### V7 — Real state of prior work

| Record | Reopened decision | Verdict |
|---|---|---|
| gh101 design D-S0 | `jca` remains byte-identical; corrections land in `jca_android` | plan incomplete; review confirmed |
| gh101 state | change remains open; task completion does not imply research readiness | review confirmed |
| Global audit §10.1 | `jca_android` NOT READY, 22/22 audited specs rejected | confirmed |
| Global audit §7 | ten researcher rulings remain required | confirmed blocker for specification tier |
| Global audit §9 | message/spec repair list already overlaps WS-1/2/3/7 | confirmed; programmes must merge |
| Study 03 D1 | uses `jca` | confirmed |
| Study 03 D3 | keeps gh100 repair | confirmed |
| Study 03 D4 | reverts `ExecutionContext` to equality semantics | confirmed |
| Study 03 D3 consequence | nine descriptor events restored, but runtime/logcat arrival was not demonstrated | review must preserve this limitation |

Relevant audit findings insufficiently integrated into both documents include fail-closed generation/compile checks, first-disjunct handling, declared-only member lookup, varargs narrowing, nested-type descriptors, explicit `android.jar` selection, and the static-path set mismatch. These can invalidate message interpretation before message quality is considered.

The status wording also needs care: gh101's ledger is 84/84 checked, but the change remains open and its product was subsequently rejected/reverted in part. “Task-complete” is not “READY”, while “unfinished implementation” would also be misleading.

### V8 — Design and proportionality

The original Phase A is internally inconsistent: WS-3.1 changes `rvsec-core`, so it is not specification-only. WS-1 is feasible only in a reduced form: `getLastEvent()` plus a stable event table, existing specification variables, and object class, all composed before reset. Expected continuations require pre-state support. Identity hashes must not enter either message or identity.

The review's T0/T1 cut is directionally right but should be adjusted:

- baseline measurement is B0, not an implementation tier;
- parser sentinel/schema work must be coordinated with gh103 and recorded invariants;
- a format/version discriminator precedes schema extension;
- T1 must merge with the audit repair programme and require formal automaton gates;
- generator/runtime work is a distinct T2, not merely deferred miscellaneous work.

Acceptance criteria should use controlled micro-traces, not only full campaign rows. In particular, CrySL-strict Cipher traces should produce one explanatory violation, not zero.

### V9 — Audit of the adversarial review

The review is considerably better than the plan and openly corrects many of its own predecessor's errors. Still:

1. Its method claim that every decisive citation was reopened is not externally auditable; the numerical scripts were ephemeral.
2. It occasionally replaces one categorical explanation with another before experimental isolation (`SecureRandom` causality; post-merge runtime closure).
3. Its “condition never assigned” rationale is contradicted by current JavaMOP source.
4. Several statements cite generated or audit artifacts as if they were execution proof; these should remain `OBSERVED_IN_ARTIFACT`.
5. It properly marks end-of-trace volume unmeasured, but some neighboring causal statements are not graded with the same restraint.

Verdict: **IMPRECISE but scientifically useful**. It should be amended, not discarded.

## 4. Corrections required

### Corrections to the plan

1. Add gh100, gh101, the global audit, Study 03 decisions, the `jca` freeze, and `e204e2a4`.
2. Replace “next campaign” with an explicit campaign identifier and admissible target set.
3. Distinguish pairing shadow (26,152) from co-location shadow (32,411).
4. Remove 73.4%, 28, 3,465×, and 3,098 unless classifier/key definitions are published.
5. Replace FSMMin completion citations with `JavaFSM.java:112-142`.
6. Rewrite `condition()` as a JavaMOP event-method prologue; do not cite `BaseMonitor:604-610` as the active mechanism.
7. Use `getState()`/`getLastEvent()`; acknowledge the loss of pre-state and atomic monitor shape.
8. Remove the promise to derive expected continuations at `@fail` without new state.
9. Remove Cipher no-update/re-init and KeyPair constructor from the translation-FP list.
10. Attribute pre-gh100 TMF twins/empty values to wrapper collision plus root-slice behavior, not orphan events alone.
11. Mark all `.mop` work inadmissible for frozen Study 03 `jca`.
12. Merge WS-1/2/3/7 with audit §9 rather than opening a competing repair stream.
13. Replace free-text/object-hash identity with a bounded structured failure ID.
14. Add message grammar: one line, no `:::`, explicit version, message last until schema migration.
15. Make schema changes an OpenSpec contract delta covering every consumer.
16. Rewrite acceptance criteria against CrySL and controlled traces.

### Corrections to the review

1. Retract the reason “EventDefinition.condition is never assigned”; prove branch reachability through the complete JavaMOP→RVM model or mark it unresolved.
2. Publish the CSV reproduction script and exact classifier definitions in a durable evidence directory.
3. Grade the 8,371/643 explanation as artifact-backed inference unless a controlled pre-fix replay is executed.
4. Keep the SecureRandom 12,400 attribution `INFERRED` pending G10-SRD-1 or an equivalent controlled replay.
5. State explicitly that gh100 V0/V2 proves descriptor/DEX emission, not logcat delivery.
6. Separate “tasks complete” from “change accepted/archived/ready”.
7. Treat the current writer/header contract as exact, but do not imply it is immutable; it can change through a coordinated spec delta.
8. Add a versioned transport format as a prerequisite to new columns.

## 5. New anomalies and bugs

| Finding | Evidence | Mechanism and consequence | Provenance |
|---|---|---|---|
| Review's dead-code rationale contradicts source | JavaMOP `EventDefinition.java:150-156` | `condition` is assigned and removed from pointcut; the cited reason cannot establish deadness | `[tool]` |
| Null rich message crashes collectors | logcat `ErrorCollector.java:38`; CSV collector `:42`; constructor does not normalise at `ErrorDescription.java:38-43` | `trim()`/escape on null throws inside reporting | `[tool]` |
| Escaper restores removed newline | both collector helpers build quoted result from original `data` | a comma/quote plus newline survives, permitting record injection/fabrication | `[tool]` |
| Fallback parser has no integrity counter | `logcat_parser.py:370-372` | malformed records warn and disappear from quantitative accounting | `[tool]` |
| Runtime identity can collapse distinct raw locations | `ErrorDescriptionTest.java:196-206` documents non-injective location parsing | distinct raw frames can become the same summary; dedupe precedes preservation of raw evidence | `[tool]` |
| Root-slice variable inheritance can make diagnostics stale | handler reset does not clear arbitrary spec fields; parameterless events affect root slice | an event-name message can be accurate while its observed value comes from an earlier/global trace | `[jca]/[tool]` |
| Format 1 discriminator is mutable prose | `logcat_parser.py:305-306` | changing boilerplate silently changes parsing route | `[tool]` |
| Result regenerator still emits ten columns | `$RVA/scripts/regenerate_results/regenerate_container.py:84,237-246` | regenerated files silently lose `source` and violate the current exact eleven-column contract | `[tool]` |
| gh91 comparison assumes the legacy header | `$RVA/scripts/gh91_compare_consolidation.py:85-90` | comparisons can normalize against an obsolete schema | `[tool]` |
| Oracle helper truncates `:::` messages | `$RVA/scripts/rv_oracle_common.py:73-81` | it returns only component 5 while gh103 rejects non-five-part identities, creating inconsistent oracles | `[tool]` |

## 6. Evolutionary plan and validation gates

### Rung 0 — post-gh100 baseline, no changes

Measure the first completed Study 03 outputs using both shadow definitions, per-spec distributions, exact duplication, empty observations, and app/library attribution under one registered classifier. Preserve script, input hash, command, and output. Gate: results reproduce from the evidence package and explicitly identify `jca`, gh100 commit, collector/parser versions, and `ExecutionContext` semantics.

### Rung 1 — message text only

This cannot land in frozen `jca` during Study 03. It may land only in a researcher-authorised post-E3 successor (`jca_android` after audit rulings, or a newly unfrozen successor to `jca`). Use the four-argument constructor in sequence handlers; message fields: version, stable spec, stable event ID/name, object class, and already-scoped values. Use `getLastEvent()`, compose before `__RESET`, prohibit newline/`:::`, and omit identity hashes and “expected” state.

Gate: generate in on-disk scratch, compile monitor, run `rvsec-core` tests, run a controlled micro-APK only through `rv-experiment run`, reparse logcat, and prove one intended record per trace. Record expected count changes.

Formal gate: extract the generated minimized automaton; verify message event-name mapping is total and injective over declared event IDs; every `@fail` trace must emit a nonempty stable failure ID.

### Rung 2 — content and transport contracts

Introduce a versioned structured envelope (prefer key=value with strict escaping over JSON-in-logcat until transport limits are measured), explicit synthetic sentinels, and a structured failure ID in runtime identity. Fix both escape helpers and null behavior. Do not enable whole-line quoting.

Gate: property-based parser tests over commas, quotes, newline, `:::`, Unicode and truncation; exact consumer compatibility matrix; OpenSpec deltas for `INV-CORE-25/41`, `INV-PLT-19`, `INV-ANA-08/46` and gh103.

### Rung 3 — automata and pointcuts

Repair only deviations authorized by CrySL/api30 provenance. Priorities: Signature return types, KPG guard, SRD repeated `next2`, message/condition contradictions, and audit §9 items. Do not “fix” CrySL-strict Cipher/KeyPair behavior without an oracle decision.

Formal gates:

- translate CrySL ORDER and generated minimized `.mop` automata to a shared alphabet;
- check equivalence where semantics are intended identical, otherwise inclusion in the recorded direction;
- verify INV-INS-110: no bound event has an all-sink row;
- produce minimal separating traces for every non-equivalence and execute them in the JVM harness;
- mutation-score the suite by deleting transitions, swapping bindings and return types.

### Rung 4 — predicates

Resolve identity versus equality after `e204e2a4`. Move `condition()` checks into bodies only together with automaton transitions, because a newly emitted failing-predicate event can itself enter the sink. Model required writers, readers, removal scope and aliasing.

Formal gate: bounded/model check the product `automaton × predicate abstraction`; check each REQUIRES edge has a reachable producer or an explicit external assumption; check ENSURES/NEGATES and object/material identity separately; compare CogniCrypt and RVSEC on the same micro-APKs.

### Rung 5 — generator/runtime, only if measured value warrants it

Consider generator-emitted `previousState`, event-name tables, stable weave-site IDs, trace prefixes, and end-of-trace support. Prefer a static per-site manifest joined offline over repeated dynamic stack walks.

Gate: generated source diff, compilation across atomic/synchronized monitor shapes, performance/memory benchmark, exact message invariants, dexlib2 descriptor/weave tests, and controlled process-death semantics. End-of-trace remains prototype-only until measured.

### Rung 6 — readiness

Reuse the audit's READY conjunction rather than inventing a new threshold: per-spec approval, all required gates passing, no unresolved incorrect/omitted claims, counterexamples closed, and reproducible evidence. Add message properties: every violation has stable event/failure ID; distinct semantic failure modes do not collide; free-text changes do not change identity; suppression totals reconcile emitted plus suppressed attempts.

## 7. Brainstorming with cost/radius/risk

| Idea | Basis opened | Cost / radius / risk |
|---|---|---|
| Versioned key=value envelope | parser positional logic and five-part identity | Medium / C+P / migration risk; easier logcat escaping than nested JSON |
| CrySL clause IDs such as `CIP-ORDER-03` | CrySL categories and audit provenance | Medium / S+C+P / requires stable generated clause mapping |
| Generator event names + previous state | JavaFSM tables and missing pre-state | Medium / M / affects all monitor consumers; removes hand-table drift |
| Last-N trace prefix per monitor | monitor has event IDs but no causal context | Medium-high / M+C / memory and sensitive-value risk; store IDs only |
| Static weave-site manifest | dexlib2 has class/method/callee/index in scope | Medium / I+P / stable-ID and obfuscation joins must be designed |
| Structured dedupe key | current free text excluded, object hash unbounded | Medium / C+P / count discontinuity must be declared |
| Suppression with counters | per-process HashSet loses history at restart | Medium / C+P / can hide bursts unless suppressed count is first-class |
| CogniCrypt category mapping | `Typestate`, `RequiredPredicate`, `IncompleteOperation`, constraints | Medium / S+C / category equivalence is not always one-to-one |
| Generate automata/messages from CrySL | repeated manual translation defects | High / generator+S / largest long-term payoff, largest validation burden |
| Diagnostic calibration mode | RV-Monitor internal behavior path exists | Medium / M+I / performance and log-volume risk; never default campaign mode |
| Alphabet minimisation budget | gh101 measured large generation-cost sensitivity | Medium / S+formal tooling / folding can hide semantically distinct events |

## 8. Threats to validity and NOT_VERIFIED items

- This is a **first-stage validation**, not a protocol-complete final audit. Its strongest justified
  use is to block implementation of the stale plan and define the next verification work.
- Three subagents covered V1–V9 in groups of three; the required nine isolated per-dimension passes
  were not performed.
- No emulator/device replay was run. gh100 runtime closure and SecureRandom causal attribution remain unproven.
- No monitor was regenerated; static declaration viability and current event-ID stability were established from source/examples/artifacts, not a fresh RVSEC generation.
- The api30 CrySL corpus was sampled around material disputes, not exhaustively re-adjudicated across all 23 specifications; the existing 558-claim audit remains the wider record.
- D01–D50 were not each independently decided against both CrySL oracles, and the audit's 558
  claims/119 phenomena were not independently replayed.
- No formal equivalence/inclusion, product automaton × predicate check, mutation analysis, or
  standalone monitor compilation was executed; these appear as proposed gates, not achieved ones.
- The gh100/gh101 replication artifacts were inspected but not fully rebuilt and hash-compared in
  this session.
- The CSV measurement commands were ephemeral. A final audit must preserve scripts, input hashes,
  commands and outputs in a durable evidence package.
- Third-party/actionability counts were intentionally not replaced with another arbitrary classifier.
- The requested `sequential-thinking` MCP was unavailable.
- Subagent citations were treated as discovery aids; the primary reviewer reopened the material claims used in the executive conclusion, but not every peripheral audit ledger entry.
- Current uncommitted repository state may differ from the commits described by historical documents. Git provenance was used for history; current source was used for present-tense claims.

### Work required before calling the protocol complete

1. Run nine isolated V1–V9 passes and preserve each evidence ledger with absolute `file:line`
   quotations.
2. Publish durable CSV reproduction scripts, hashes, definitions and outputs, including the
   attribution classifier.
3. Re-adjudicate every material false-positive/defect claim against both original and api30 CrySL,
   explicitly accounting for oracle divergence.
4. Generate and compile the relevant monitors in on-disk scratch, both standalone and merged, and
   validate atomic and synchronized shapes.
5. Re-execute the audit's decisive JVM traces and build the missing differential/mutation corpus.
6. Re-materialise and hash-check the relevant gh100/gh101 evidence paths.
7. Execute the authorised G10 replay through `rv-experiment`/`rv-platform` to decide historical
   runtime causality, especially SecureRandom and post-gh100 logcat arrival.
8. Consolidate contradictions in a second report revision; only then issue a protocol-complete
   final opinion.

## 9. Documents and artifacts used

Principal absolute roots:

- `$RVA` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android`
- `$RVSEC` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec`
- `$WS` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`

Documents and records:

- `$RVA/docs/20260815_javamop_mensagens.md`
- `$RVA/docs/20260815_javamop_mensagens_analise.md`
- `$RVA/docs/20260815_javamop_mensagens_analise_handoff_prompt.md`
- `$RVA/docs/20260815_javamop_mensagens_validacao_prompt.md`
- `$RVA/audit/20260808_validacao_jca_android/global/juizglobal_relatorio.md`
- `$RVA/docs/20260810_plano_prontidao_estudo03.md`
- `$RVA/docs/20260812_comp162.md`
- `$RVA/docs/20260812_registro_execucao_prontidao_e3.md`
- `$RVA/openspec/changes/gh100-weaver-emission-fidelity/`
- `$RVA/openspec/changes/gh101-jca-spec-conformance/`
- `$RVA/openspec/changes/gh103-campaign-analysis-layer/`
- `$RVA/openspec/specs/{core,platform,analysis,instrumentation}/spec.md`

Data and oracles:

- `$WS/ase-journal/dataset/results/errors.csv`
- `$WS/ase-journal/dataset/results/README.md`
- `$WS/Crypto-API-Rules/JavaCryptographicArchitecture/src/*.crysl`
- `$WS/MetaCrySL/generated/api30/*.cryptsl`
- `$RVSEC/rvsec/rvsec-mop/src/main/resources/{jca,jca_android,generic,generic_new}/`
- `$RVA/results/{gh99_jca_android_monitors,gh101_group8_jca_android,gh101_group8_jca_frozen_control,gh92_e2e2,gh56-smoke}/monitors/`

Core sources reopened include:

- `$RVSEC/rvsec/rvsec-core/src/main/java/br/unb/cic/mop/eh/{ErrorDescription,ErrorSummary,ErrorType}.java`
- `$RVSEC/rvsec/rvsec-core/src/test/java/br/unb/cic/mop/eh/ErrorDescriptionTest.java`
- `$RVSEC/rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/logicpluginshells/fsm/JavaFSM.java`
- `$RVSEC/rv-monitor/rv-monitor/src/main/java/com/runtimeverification/rvmonitor/java/rvj/output/monitor/{BaseMonitor,HandlerMethod}.java`
- `$RVSEC/rv-monitor/rv-monitor-rt/src/main/java/com/runtimeverification/rvmonitor/java/rt/ViolationRecorder.java`
- `$RVSEC/javamop/src/main/java/javamop/parser/ast/{mopspec/EventDefinition.java,visitor/RVDumpVisitor.java}`
- `$RVSEC/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/`
- `$RVA/modules/rv-coverage/src/rv_coverage/parser/log/logcat_parser.py`
- `$RVA/modules/rv-android-core/src/rv_android_core/domain/log.py`
- `$RVA/modules/rv-platform/src/rv_platform/components/result_processor.py`
- `$RVA/modules/aperv-tool/src/aperv_tool/analysis/violations.py`

## 10. Final opinion

The evidence completed in this first stage is sufficient for one immediate decision: the message
problem is real and severe, but the plan must **not** be implemented as written, and “replace
`unknown`” is not yet the first safe code change. First preserve a post-gh100 baseline and make the
reporting contract explicit. Then add bounded, structured failure identity and event-bearing text
in an authorised successor specification set, together with formal automaton and predicate checks.
Only after those measurements should shared generator/runtime work be considered.

The plan should be rewritten around that sequence. The adversarial review should be retained as
the main correction record, amended to downgrade its causal inferences, preserve its measurement
scripts, and correct the `EventDefinition.condition` claim. This report must not be cited as a
complete certification of either document or of either JavaMOP set until the eight completion
items in §8 have been executed.
