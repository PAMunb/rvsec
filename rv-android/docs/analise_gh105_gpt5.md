# Verification report: `gh105-predicate-wiring`

Date: 2026-08-20  
Model: GPT-5 (Codex)  
Reactor HEAD verified: `bd61abea` (the expected anchor)  
Method: direct source inspection, independent parsing/counting, three parallel subagents (D1–D2, D3–D5, D6–D8), OpenSpec validation, and the gh104 spec-set pytest gate. The `sequential-thinking` MCP was not available. No emulator was started or managed. No weave, device campaign, reactor rebuild, or full generator campaign was run. Scratch/cache data was confined to `/tmp`.

## Executive verdict

**BLOCKER: the change is not safe to implement as written.**

The F3 task decomposition is not a faithful ledger of the 35 connectable clauses: it assigns producers and consumers to the wrong predicates, names a nonexistent `preparedPBE`, and leaves roughly fifteen clauses only implicit or misclassified. Worse, the three negated `REQUIRES` clauses have no defined store/verdict semantics, although the old analyzer treats absence as satisfaction and any same-name ensured predicate as failure. `CipherSpec` already has 17 events, while the required binding profiles imply more events and 18 is a hard generator ceiling; the artifacts provide no realizable alphabet map. Finally, F2 migrates reads to the new store before F3 migrates/wires their producers, so conforming calls become `NOT_OBSERVED` accusations during a stage the design calls coherent. These defects can directly produce wrong monitors or make generation impossible.

The change also incompletely supersedes active gh104 requirements, omits the fate of 25 accepting-state calls, contradicts the repository's ban on deprecation annotations, does not actually exclude mixed old/new stores through `custom`, and claims all junction rules are gate-checked although only primitive-array survival has a structural gate.

The underlying direction is supportable: the oracle census, old-analyzer matching semantics, guard/body diagnosis, NEGATES disposition, regular-language basis for G-ORDER, pilot failure modes, and most measured current-state counts were confirmed. Amend the planning artifacts before `/opsx:apply`.

## Findings

| id | dimension | severity | verdict | claim | evidence | recommended amendment |
|---|---|---:|---|---|---|---|
| F-01 | D2/D7 | BLOCKER | REFUTED | F3 provides a faithful topological home for all 35 clauses. | `tasks.md:105-121`; oracle ledger below. `tasks.md:109` says KeyPairGen consumes `randomized`, but the rule is KeyGenerator; `:112-115` misstates generatedKey producers/consumers; `:116-117` names nonexistent `preparedPBE` and omits several real predicates. | Replace §5 by 35 literal clause rows, each with oracle line, producer, consumer, binding profile, mechanism, task, and final event count. |
| F-02 | D5 | BLOCKER | INCOMPLETE | Cipher wiring is feasible under the generator ceiling. | Current `CipherSpec.mop:44-173` declares 17 events. `Cipher.cryptsl:59-79` has eight init binding profiles; replacing the two current init events by eight already implies 23 events. `spec.md:207-211` fixes the hard ceiling at 18. | Add a pre-F2/F3 approved alphabet/binding map with final count ≤17 and successful real-pipeline artifact, or redesign bindings through junction/store without expanding the Cipher alphabet. |
| F-03 | D7 | BLOCKER | REFUTED | F0+F1+F2 is a coherent stage and F2 can precede F3. | `design.md:160-172`, `tasks.md:83-121`. F2 reads `PredicateStore`; producers still write `ExecutionContext` until F3. This contradicts `design.md:248` and INV-INS-144's atomic evidence discipline. | Land each migrated read atomically with all required producers, or make F2 non-activating structural preparation only. |
| F-03A | D2 | BLOCKER | INCOMPLETE | The store contract defines all positive and negated REQUIRES semantics. | Negated clauses: Cipher `!macced` and Mac's two `!encrypted`. `AnalysisSeedWithSpecification.java:389-395` fails on any same-name ensured predicate and otherwise succeeds, without `doPredsMatch`; artifacts expose only positive `validate` and never define this polarity. | Add an invariant, API/caller rule, scenarios, graph polarity and tests: for negated REQUIRES, NOT_OBSERVED satisfies; any same-name ensured entry violates under the old oracle's name-only branch. Distinguish this from NEGATES clauses. |
| F-04 | D2 | MAJOR | INCOMPLETE | The three-valued store encodes exactly the old oracle, no more and no less. | `AnalysisSeedWithSpecification.java:475-513`: empty extracted tracked values leave `predEval=true`; `design.md:133-139` and `spec.md:125-140` classify entry mismatch as VIOLATED and report it. | Define the runtime analogue of imprecise/empty extraction. Either keep it silent/NOT_OBSERVED or explicitly declare and test the deliberate strengthening. |
| F-05 | D7 | MAJOR | REFUTED | Tasks 3.1–3.5 cover all 17 actual orphan accusers. | Independent `.mop` enumeration listed below; `tasks.md:73-79` invents orphans in KeyStore, KeyManagerFactory, MessageDigest and Mac, while omitting actual IvParameterSpec, KeyPairGenerator, PBEParameterSpec and SecretKeySpec entries. | Replace F1 task lists with the exact 17 event names and require G-ACC evidence per row. |
| F-06 | D4 | MAJOR | INCONSISTENT | INV-INS-141 cleanly supersedes the complete active gh104 predicate contract. | gh105 `spec.md:185-191`; gh104 delta `spec.md:197-218`, `:544`, `:562` and INV-INS-123 at `:42` retain incompatible normative statements. | Add explicit MODIFIED requirements for gh104's successor-predicate requirement, specification-set/cross-spec text, and INV-INS-123. |
| F-07 | D4 | MAJOR | INCOMPLETE | All G-PRED collateral is planned. | `gh104_gates.py:1014-1051,1454-1468`; `test_gh104_specset_gates.py:42-51,91-135`; `test_gh104_structural_gates.py:229-238`; task 2.5 names only a generic pytest rewrite. | Name both tests and condition G-PRED execution itself to the frozen `jca`, not merely update recognizers. |
| F-08 | D3 | MAJOR | INCOMPLETE | The MODIFIED Predicate Contract is a faithful complete replacement. | Main requirement has scenario “A predicate's whole set is deleted” (`openspec/specs/instrumentation/spec.md:1826+`); gh105 replacement `spec.md:215-326` omits it. | Restore an adapted scenario: property-wide deletion API is absent and any equivalent use fails compilation/gate. |
| F-09 | D3/D5 | MAJOR | INCOMPLETE | All four junction rules are gate-checked. | `design.md:149-153` claims this; mapping `:81` and tasks 2.1–2.4 provide only G-PARAM for rule (c), not structural checks for (a), (b), or (d). | Add negative fixtures and automated checks for consumer-not-creation, disconnected benign loops, and handler-field state, or weaken the claim and require explicit per-chain review. |
| F-10 | D6/D8 | MAJOR | REFUTED | Adding `@Deprecated` is workflow compliant. | `proposal.md:14`, `design.md:109-113`, `tasks.md:32-33`, INV-INS-132 versus `docs/WORKFLOW.md:252-260` (“No ... deprecation annotations”). | Leave `ExecutionContext` byte-identical; remove annotation/Javadoc tasks unless the researcher explicitly changes WORKFLOW policy. |
| F-11 | D6 | MAJOR | REFUTED | Two predicate stores cannot coexist because configuration excludes mixing. | `design.md:267-268`; main INV-INS-09 only selects a directory, while `custom` accepts an arbitrary directory. | Add validation/import-family exclusion for custom sets or record mixed-store execution as an open risk. |
| F-12 | D7 | MAJOR | INCOMPLETE | The fate of all 134 legacy lines is fully tasked. | 134 includes 25 `setObjectAsInAcceptingState`/`unset...` calls; new API omits them (`design.md:214-216`); no task enumerates their removal/migration. | Add a task and graph/gate evidence accounting for all 25 calls and their behavioral delta. |
| F-13 | D8 | MAJOR | REFUTED | Durable artifacts comply with P4/no migration history. | `docs/WORKFLOW.md:262-266`; historical narratives remain in `design.md:20-24`, delta `spec.md:510-512,567-575,600-605`; task 1.4 requests migration Javadoc. | Keep history in proposal/evidence; rewrite durable normative text as current-state contract and remove migration Javadoc. |
| F-14 | D3 | MINOR | INCONSISTENT | Task 4.3 names eight remaining accuser-less reads. | `tasks.md:90-93` lists seven; the eighth is Cipher `i2`, handled by 4.1 and named in delta `spec.md:429-431`. | Say “remaining seven” and cross-reference Cipher `i2` in 4.1. |
| F-15 | D8 | MINOR | REFUTED | Artifacts are English throughout. | `tasks.md:55` uses “fiação”; “Fase 0” occurs as prose/label. | Replace with “wiring”/“Phase 0” except where quoting an immutable filename. |
| F-16 | D1/D3 | MAJOR | INCONSISTENT | “The set realizes 3” means three of the 35 clause-sites. | `design.md:12` says “3 of 35 ... clauses”; the measured unit behind 3 is realized predicate values/links, while 35 counts consumer clause-sites. Current reads span four Property values and do not establish the asserted clause ratio. | State the exact three realized predicate links with producer/read sites, or remove the cross-unit `3 of 35` claim and report predicate and clause units separately. |

## D1 — factual accuracy

Commands used included the §6.2 greps over the sibling resource tree, a separate oracle parser, direct enum inspection, and source searches. Relevant raw output: reactor HEAD `bd61abea`; `ExecutionContext total 134`; write distribution sums to 49; read distribution sums to 27; remove distribution sums to 9.

| claim checked | verdict | evidence |
|---|---|---|
| 33 api30 rules | CONFIRMED | `ls MetaCrySL/generated/api30/*.cryptsl | wc -l` / independent parser: 33. |
| Oracle census 54 ENSURES / 36 REQUIRES / 2 NEGATES / 32 distinct predicates | CONFIRMED | independent section-aware parser over the 33 rules; literal clauses inspected for the ledger. |
| 19 connectable predicates / 35 connectable REQUIRES clauses / 34 distinct pairs | CONFIRMED | independent oracle graph parse; Mac has two `!encrypted` clauses, producing the duplicate pair. |
| 44 producer→consumer edges | CONFIRMED | independent producer/consumer graph expansion. |
| Oracle arity 59 unary / 31 binary / max 2 | CONFIRMED | parameter-aware parse; `part(0,"/",...)` in Cipher is one CrySL parameter, not multiple arguments. |
| Property enum has 25 values | CONFIRMED | `rvsec-core/.../Property.java:8-54`, 25 constants. |
| 21 values written, 4 read, 49 writes, 27 reads | CONFIRMED | §6.2 `(Property`-discriminating greps; sums 49 and 27; unique sets 21 and 4. |
| 42 body writes / 7 handler writes; all 27 reads in `condition` | CONFIRMED | structural site inventory and generated-monitor spot check. |
| 9 removes = 8 `@fail` + 1 body; 4 use deprecated one-arg overload | CONFIRMED | structural inventory of `jca_android/*.mop`. |
| 18 written-never-read values over 35 sites; only MACED and GENERATED_CIPHER have zero sites | CONFIRMED | write/read set difference plus `Property.java`. |
| 134 ExecutionContext lines = 23+27+49+9+25+1 | CONFIRMED | grep total 134 and category-specific inventory; comment is `MessageDigestSpec.mop:25`. |
| 17 orphan accusers in 9 jca_android specs | CONFIRMED | independent event/automaton enumeration; exact list below. |
| F1 tasks enumerate those 17 | REFUTED (MAJOR) | F-05. |
| jca has 18 orphans in 10 specs; archive has 0 | CONFIRMED | independent analyzer over the three directories. |
| Orphan family sustains 49,817 = 70.4% ISoMC | CONFIRMED | `ase-journal/dataset/results/errors.csv` aggregation and category denominator. |
| `preparedEC` is the only producerless required predicate | CONFIRMED | oracle graph parse. |
| Two NEGATES; only PBEKeySpec removal corresponds in current set | CONFIRMED | `SecretKey.cryptsl`, `PBEKeySpec.cryptsl`; `PBEKeySpecSpec.mop:74`. |
| Generator exact growth `n(2^n−1)`; 17 works under 1 GiB, 18 SOE in `EnableSet.parseSets` | CONFIRMED from primary/raw recorded generation evidence; not rerun | audit-v2 raw generator artifacts and stack trace; gh105 matches main INV-INS-115. |
| Cipher implementation plan stays inside 17-event budget | INCOMPLETE (BLOCKER) | F-02. |
| “3 of 35 clauses are realized” | INCONSISTENT (MAJOR) | F-16; mixes predicate/link and clause-site units without a clause mapping. |

Exact current orphan list derived from the `.mop` declarations and automata: `IvParameterSpec.c3,c4`; `KeyPairGenerator.initError`; `PBEKeySpec.err1,err2,err3,f1,f2`; `PBEParameterSpec.c3`; `SSLContext.unsafe_protocol`; `SecretKeySpecSpec.c3,c4`; `SecureRandom.c3,g4,setSeed3`; `Signature.g3`; `TrustManagerFactory.g3`.

## D2 — CrySL conformance

| claim checked | verdict | evidence |
|---|---|---|
| Predicate equality is by name | CONFIRMED | `CrySLPredicate.equals:41-60`. |
| REQUIRES facts are monotonic per object in the old analyzer | CONFIRMED | `AnalysisSeedWithSpecification.java:72,579-583` only adds ensured predicates. |
| NEGATES is a no-op in this analyzer generation | CONFIRMED | analyzer control flow contains no operative NEGATES removal; two clauses were independently counted. |
| Only String/int/Integer positions are value-tracked | CONFIRMED | `AnalysisSeedWithSpecification.java:564-572`. |
| Tracked values are compared case-insensitively with splitters | CONFIRMED | `AnalysisSeedWithSpecification.java:498-513`. |
| Hybrid store exactly reproduces silence on imprecise extraction | INCOMPLETE (MAJOR) | F-04; empty extraction leaves the old analyzer true. |
| Three states entry+match / mismatch / no entry are internally defined | CONFIRMED | `design.md:133-139`; delta INV-INS-131/133. |
| VIOLATED always agrees with the old static oracle | INCOMPLETE (MAJOR) | runtime mismatch can accuse where old extraction is empty and silent. |
| Negated REQUIRES semantics is defined and oracle-faithful | INCOMPLETE (BLOCKER) | `AnalysisSeedWithSpecification.java:389-395`; no artifact defines absence/same-name behavior for the three negative clauses. |
| ORDER grammar is regular | CONFIRMED | `CrySL.xtext:103-133`: sequence, alternative, grouping and `*`/`+`/`?`. |
| Alphabet mapping is non-bijective and versioned | CONFIRMED | delta `spec.md:166-171,533-545`; `.mop` overload splits justify the caveat. |
| Cipher end-to-end | INCOMPLETE/BLOCKER | Six oracle REQUIRES at `Cipher.cryptsl:172-184`; current mop implements one plus non-oracle alternates; F3 misclassifies families and has no feasible alphabet. |
| SecureRandom end-to-end | CONFIRMED direction | Oracle `ORDER`/predicates `SecureRandom.cryptsl:56,64-77`; current guards/writes are misplaced; `Ends*`, body migration and acceptance writes are appropriate. |
| PBEKeySpec end-to-end | CONFIRMED with task-ledger caveat | Oracle randomized/speccedKey/NEGATES `:38-50`; current removal `PBEKeySpecSpec.mop:74`; proposed object-scoped negate is faithful. |
| Mac end-to-end | REFUTED in task classification | Oracle `preparedHMAC` plus two `!encrypted` at `Mac.cryptsl:78-84`; current mop tests generatedKey; task 5.4 wrongly treats Mac as generatedKey consumer. |
| SSLContext end-to-end | CONFIRMED only when 5.3+5.6 are combined | Oracle requirements `SSLContext.cryptsl:46-52`; current mop has no reads and wrong-named writes; TLS and randomized tasks together cover them, but §5 lacks literal clauses. |
| All 35 clauses have an unambiguous task home | REFUTED (BLOCKER) | Ledger below: about 15 are catch-all, ambiguous, omitted, or misclassified. |
| Both NEGATES are covered | CONFIRMED | task 6.4 retains PBE and records SecretKey as unclosable. |
| The three negated REQUIRES are covered | INCOMPLETE (BLOCKER) | They are not NEGATES: Cipher `!macced`, Mac `!encrypted` twice; §5 is vague and the API contract has no polarity semantics. |

## D3 — internal coherence

| claim checked | verdict | evidence |
|---|---|---|
| INV-INS-130 through 145 each appear in design mapping and tasks | CONFIRMED at coarse traceability level | `design.md:76-90`; tasks groups 1–8. |
| Every invariant has an adequate automated test | INCOMPLETE | INV-INS-136 rules a/b/d lack gates (F-09); INV-INS-145 is manual artifact evidence. |
| Every task traces to a requirement/invariant | CONFIRMED at group level | task comments/references and design mapping; no unrelated implementation task found. |
| Mechanism A/B partition agrees across artifacts | CONFIRMED | proposal:17; design D-2; delta junction requirement; tasks 5.x. |
| Remove disposition agrees (8+1) | CONFIRMED | proposal:19; design D-3; INV-INS-142; task 6.4. |
| Not-observed code lands with first read | CONFIRMED | INV-INS-143 and tasks 4.1+4.2 explicitly same task. |
| G-PRED rescope lands with first migrated file | CONFIRMED as choreography, incomplete as collateral | tasks 2.5 and 4.1; F-07. |
| Counts 35/34, 17/9, 27, 8+1 agree | CONFIRMED except task 4.3 wording | F-14. |
| Every requirement has ≥1 scenario and all use `#### Scenario:` | CONFIRMED | structural heading scan; OpenSpec validation passes. |
| RFC 2119 normative form | CONFIRMED | SHALL/MUST used consistently in normative delta. |
| Both MODIFIED requirements are complete copies | REFUTED | Predicate Contract loses whole-set-deletion scenario (F-08). |

## D4 — gh104 and main-spec consistency

| claim checked | verdict | evidence |
|---|---|---|
| INV-INS-141 resolves INV-INS-128 for jca_android | INCOMPLETE/INCONSISTENT | F-06: active requirement text still demands preservation. |
| G-PRED collateral list is complete | INCOMPLETE (MAJOR) | F-07; execution wiring and a second test are not explicitly planned. |
| `accept_requires` can remain governed by old INV-INS-123 | REFUTED | gh104 INV-INS-123 says jca_android encodes no REQUIRES; gh105 explicitly introduces them. |
| INV-INS-119 envelope remains compatible | CONFIRMED | gh105 accusers retain four-argument envelope and codes. |
| INV-INS-115 generator numbers agree | CONFIRMED | both say 17 under 1 GiB; 18 SOE in parser. |
| INV-INS-111 versus INV-INS-137 | CONFIRMED | INV-INS-137 explicitly realizes successor-set closure with richer graph. |
| gh105 pre-empts gh104 Group 10 | CONFIRMED negative | proposal:40, design:27/101, task 8.7 defer it to joint experiment. |

## D5 — technical feasibility

| claim checked | verdict | evidence |
|---|---|---|
| `ensure`/`negate`/`validate` varargs can represent existing call arities | CONFIRMED | design API and current call-shape inventory; both NEGATES need only bound object plus wildcard semantics. |
| Splitters can be applied by callers in `.mop` bodies | CONFIRMED in principle | Java bodies can compute the String part before store calls; exact per-clause code still belongs in the ledger. |
| `condition` compiles to early boolean return | CONFIRMED | generated control monitor `MultiSpec_1RuntimeMonitor.java:3715` spot check. |
| Therefore three-valued reads must be body-only | CONFIRMED | a guard cannot express reporting while preserving transition. |
| Pilot supports consumer-not-creation | CONFIRMED | `agentI/relatorio.md:28-37`. |
| Pilot supports disconnected benign loops | CONFIRMED | `agentI/relatorio.md:59-63`. |
| Pilot supports primitive-array collapse/Object idiom | CONFIRMED | `agentI/relatorio.md:65-86`; woven production path remains untested (`:97-107`). |
| Fixed-overload caveat appears everywhere material | CONFIRMED | INV-INS-136, junction requirement, design D-2/D-6, proposal. |
| All four rules are mechanically gate-checked | REFUTED/INCOMPLETE | F-09. |
| Cipher's six REQUIRES bindings fit the alphabet | INCOMPLETE (BLOCKER) | F-02. |

## D6 — freeze safety

| path checked | verdict | evidence |
|---|---|---|
| Direct `.mop` edits under frozen `jca` | CONFIRMED excluded | proposal impact/non-goals; tasks 8.2. |
| Shared `ExecutionContext` behavioral edit | CONFIRMED excluded, annotation policy refuted | INV-INS-132 limits content; F-10 shows annotation itself violates WORKFLOW. No `-Werror`-like effect was demonstrated; reactor build would verify compiler behavior. |
| Other shared Java classes used by `jca` | CONFIRMED excluded by invariant wording | INV-INS-132 says every other called class untouched; new store is separate and imported only by jca_android. |
| `codes.csv` leakage to jca | CONFIRMED scoped | proposal/spec output names `jca_android/codes.csv`; no frozen CSV edit planned. |
| Gate collateral changing frozen lock | INCOMPLETE | F-07; retain jca byte lock and explicitly branch by set. |
| Both stores in one process impossible | REFUTED | F-11; `custom` can mix files. |
| `rvsec-mop-defsuses` has no reactor dependents | INCOMPLETE | artifact directs grep/build in task 7.3, but no completed dependency proof exists before implementation. Make successful dependency-tree/reactor build an acceptance precondition. |
| Archived failed set remains untouched | CONFIRMED planned | INV-INS-132 and task 8.2. |

## D7 — completeness, gaps, and risks

| claim checked | verdict | evidence |
|---|---|---|
| All 17 orphans named in F1 | REFUTED (MAJOR) | F-05 and exact list above. |
| Eight accuser-less reads named | INCONSISTENT (MINOR) | F-14. |
| Seven genericity gaps represented | CONFIRMED at contract level | INV-INS-140 covers event-only, compile failures, no-rule, helper shadowing and alias/state forms; GCM negative fixture lines 23/34/48 are carried. |
| 35 written-never-read sites each get a disposition | INCOMPLETE | future graph closure demands a row, but tasks do not enumerate site-by-site dispositions. Add a 35-site companion ledger. |
| 25 accepting-state calls have a disposition | INCOMPLETE (MAJOR) | F-12. |
| Gate scripts handle silent generation failure | CONFIRMED in normative text | G-PARAM and INV-INS-145 require artifact inspection; implementation remains future work. |
| Task order never adds reader before producer | REFUTED (BLOCKER) | F-03. |
| Audit-v2 open items are carried | INCOMPLETE | device key `equals`, woven pilot, and upstream patch are openly deferred; imprecise extraction semantics and Cipher budget are not adequately carried (F-02/F-04). |

## D8 — workflow and principles

| claim checked | verdict | evidence |
|---|---|---|
| P1 no premature abstraction | CONFIRMED for store/graph need; INCOMPLETE for unproven Cipher design | measured arity/identity/closure needs justify classes; F-02 blocks detailed feasibility. |
| P2 self-contained for implementer | REFUTED | incorrect F3 names and catch-all clauses require reconstructing the plan/oracle (F-01). |
| P3 no shims / retirement complete | REFUTED for annotation; INCOMPLETE for retirement | F-10; task 7.3 has future grep/build acceptance. |
| P4 no migration history in durable docs/comments | REFUTED | F-13. |
| Issue/change naming and commit references | CONFIRMED | `gh105-predicate-wiring`, `#105`, `refs #105`, delayed `closes #105`; no Co-Authored-By instruction. |
| English throughout | REFUTED (MINOR) | F-15. |
| OpenSpec artifact sanity | CONFIRMED | `openspec validate`: “Change 'gh105-predicate-wiring' is valid”; status: 4/4 complete. |
| Existing gh104 spec-set gate | CONFIRMED | `UV_CACHE_DIR=/tmp/gh105-uv-cache ... pytest -p no:cacheprovider ...`: 2 passed in 0.25 s. |

## The 35-clause ledger

Oracle clauses were parsed independently from `MetaCrySL/generated/api30`; task homes refer to `tasks.md:105-121`.

| # | rule | REQUIRES clause | artifact home | verdict |
|---:|---|---|---|---|
| 1 | AlgorithmParameters | `preparedAlg[parAr]` | 5.7 catch-all | INCOMPLETE: omitted from prepared family list |
| 2 | AlgorithmParameters | `preparedIV[...]` | 5.5 | CONFIRMED |
| 3 | AlgorithmParameters | `preparedDH[...]` | 5.5 | CONFIRMED |
| 4 | CertPathTrustManagerParameters | `generatedCertPathParameters[params]` | 5.7 catch-all | INCOMPLETE |
| 5 | Cipher | `generatedKey[key, part(...)]` | 5.4 | CONFIRMED semantically; feasibility blocked |
| 6 | Cipher | `randomized[ranGen]` | 5.3 | CONFIRMED semantically; feasibility blocked |
| 7 | Cipher | `preparedAlg[param, part(...)]` | “six rebuilt” 5.4 / omitted 5.5 | INCOMPLETE |
| 8 | Cipher | `!macced[_, plainText]` | only “six rebuilt” | INCOMPLETE: no macced chain named |
| 9 | Cipher | conditional `preparedIV[params]` | 5.1/5.5 | CONFIRMED semantically; feasibility blocked |
| 10 | Cipher | conditional `preparedGCM[params]` | 5.5 | CONFIRMED semantically; feasibility blocked |
| 11 | GCMParameterSpec | `randomized[src]` | 5.3 | CONFIRMED |
| 12 | IvParameterSpec | `randomized[iv]` | 5.1 | CONFIRMED |
| 13 | KeyGenerator | `randomized[ranGen]` | 5.3 implied | INCOMPLETE: omitted/misnamed as KeyPairGen |
| 14 | KeyManagerFactory | `generatedKeyStore[keyStore]` | 5.6 | CONFIRMED |
| 15 | KeyPair | `generatedPrivkey[consPriv]` | 5.4 generatedKey family | INCOMPLETE/MISCLASSIFIED |
| 16 | KeyPair | `generatedPubkey[consPub]` | 5.4 generatedKey family | INCOMPLETE/MISCLASSIFIED |
| 17 | KeyPairGenerator | `preparedDH[params]` | 5.5 | CONFIRMED |
| 18 | KeyPairGenerator | `preparedDSA[params]` | 5.7 catch-all | INCOMPLETE: omitted |
| 19 | KeyPairGenerator | `preparedRSA[params]` | 5.7 catch-all | INCOMPLETE: omitted |
| 20 | Mac | `preparedHMAC[params]` | 5.5 | CONFIRMED |
| 21 | Mac | `!encrypted[output1, _]` | vague “Mac/Key” 5.2 | INCOMPLETE |
| 22 | Mac | `!encrypted[output2, _]` | vague “Mac/Key” 5.2 | INCOMPLETE; duplicate predicate pair must stay two sites |
| 23 | PBEKeySpec | `randomized[salt]` | 5.3 | CONFIRMED |
| 24 | PBEParameterSpec | `randomized[salt]` | 5.3 | CONFIRMED |
| 25 | PKIXBuilderParameters | `generatedKeyStore[keyStore]` | 5.6 | CONFIRMED/implicit |
| 26 | PKIXParameters | `generatedKeyStore[keyStore]` | 5.6 | CONFIRMED/implicit |
| 27 | SSLContext | `generatedKeyManager[kms]` | 5.6 | CONFIRMED |
| 28 | SSLContext | `generatedTrustManager[tms]` | 5.6 | CONFIRMED |
| 29 | SSLContext | `randomized[sr]` | 5.3 | CONFIRMED |
| 30 | SecretKeyFactory | `speccedKey[keySpec, _]` | 5.7 | CONFIRMED |
| 31 | SecretKeySpec | `preparedKeyMaterial[keyMaterial]` | 5.7 catch-all | INCOMPLETE: omitted |
| 32 | SecureRandom | `randomized[seed]` | 5.3 implied | INCOMPLETE: omitted |
| 33 | Signature | `generatedPrivkey[priv]` | 5.4 says generatedKey | INCOMPLETE/MISCLASSIFIED |
| 34 | Signature | `generatedPubkey[pub]` | 5.4 says generatedKey | INCOMPLETE/MISCLASSIFIED |
| 35 | TrustManagerFactory | `generatedKeyStore[keyStore]` | 5.6 | CONFIRMED |

## Open questions for the researcher

1. Should runtime-observed tracked-value mismatch deliberately strengthen the old analyzer when static extraction would be empty/imprecise? If yes, ratify it explicitly as a divergence and specify the evidence/code; if no, add an unknown/not-observed branch.
2. Is `@Deprecated` important enough to amend the repository's explicit no-deprecation policy? The safer freeze-preserving choice is no annotation and byte identity.
3. Will `custom` sets be forbidden from mixing `jca` and `jca_android` machinery, or must mixed-store behavior be supported and tested?
4. Which concrete Cipher alphabet/binding map (≤17 events) is ratified? No F3 implementation should start without that table and a generated monitor.
5. Must the three negated REQUIRES reproduce the old analyzer exactly (absence satisfies; any same-name ensured predicate violates irrespective of argument matching), or is a deliberate stronger value-sensitive rule intended?

## Limitations

- No Android device was used. Concrete-provider key `equals` behavior, including `OpenSSLRSAPublicKey`, remains NOT VERIFIABLE HERE; a device identity/equality probe would verify it.
- The pilot was checked from its specs, reports, generated evidence and driver results, but the production weave path was not rerun. A woven trace pair is still required for each chain.
- The full 214-file generation campaign and reactor rebuild were not run. They remain necessary to establish actual G-PARAM skip counts, dependency-safe retirement of `rvsec-mop-defsuses`, compiler impact, and regenerated monitor integrity.
- The gh104 differential selftest was not rerun because it writes evidence files in the repository, forbidden by this prompt. The read-only spec-set pytest gate passed.
- Published corpus counts validate aggregate claims, not per-event causality. Final per-event conclusions still require generated transition tables and replayed traces.
