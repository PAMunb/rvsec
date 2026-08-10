# JUDGE — Batch B synthesis (CIS, COS, KPR, SKY, PBK)

Judge (LLM-as-a-Judge), round "batch B" of the `jca_android` audit · 2026-08-09.
Role: evidence synthesis — **not** a formal oracle, **not** majority vote. A
reproducible counterexample cannot be dismissed by consensus; a reading-only
claim cannot close a toolchain claim; `INCONCLUSIVE` never becomes approval.
Weights and denominators: `fase0/pre_registro.md` §6, applied under D-piloto-1/2/3/4
and **D-batchA-1** (`fase0/desvios.md` — the raw weighted sum is the score of
record; attainable-% only as a labeled derived reading).

Inputs: `batchB/generation_manifest.md` (20 artifacts, hash-verified by me),
the three agent reports and CSVs (`alfa_*` 45 claims, `beta_*` 52, `gama_*` 36 —
**133 total**), the frozen specs/rules, the gh101 registers, and the production
sources. Claim-by-claim resolution: `batchB/juiz_claims_resolvidos_batchB.csv`
(original columns preserved; `resolucao_juiz`, `classificacao_final`,
`severidade_final`, `justificativa_curta` appended). Mechanical re-sum:
`batchB/juiz_rescore_batchB.py` (§4 tables are its verbatim output,
`juiz_rescore_batchB_output.txt`).

Scope of this round's verdicts: gates **G2, G3, G4, G5, G7, G9**. G6, G8 and
G10 were not executed (device phase later) — they can only ADD defects, never
remove demonstrated ones. G0/G1 were closed in fase 0; G11–G13 are fed by, not
closed by, this round. Batch A rules carried: REF-B-01 (judge evidence preserved
under `batchB/` with hashes — §7), REF-B-05 (gates fail by pre-registered
criteria; critical INCORRETA/OMITIDA is one sufficient trigger, not the only
one), REF-B-07 (routes counted, not agents), REF-B-09 (dimension-5 multi-route).

## 0. Evidence the judge verified or executed himself

All commands reproducible; agent files untouched; judge work in scratch
`<scratchpad>/batchB/juiz/`, decisive files copied to `batchB/juiz_*` (§7).

1. **Freeze**: `sha256sum` over the 5 `.mop`, 5 `.cryptsl` and 20 round
   artifacts — 30/30 equal to `generation_manifest.md` / `fase0/manifest_hashes.md`.
   Production jars = the batch A hashes (rvsec-core `7b4d72aa…`, rvsec-logger-csv
   `6787f411…`, rv-monitor-rt `0fa65fbc…`). android-30 jar `96ccfdc8…`.
2. **Sources read end-to-end** (all five `.mop`, all five api30 `.cryptsl`).
   Confirmed directly: CIS/COS specs are **parameterless** (`.mop:11`) with the
   `GENERATED_CIPHER` body check (`CIS.mop:22-25`, `COS.mop:21-24`) while the
   api30 rules have **no REQUIRES section at all**; COS declares `fl` inside
   `(w1|w2|fl)+` (`.mop:32,36`) while the rule's alphabet has no flush;
   `len > off` (the rules' only CONSTRAINT) transcribed nowhere (r2/w2 bodies
   empty); KPR spec parameter `keyPair` (`:19`), shadowing monitor variable
   `KeyPair keyPair = null` (`:21`), `c1 … returning(KeyPair kp)` binding **no
   spec parameter** (`:29`), `ere: c1 (gpu|gpr)*` (`:61`) vs rule
   `ORDER co?, (pu*, pr*)*` (`KeyPair.cryptsl:27`); SKY gate
   `condition(validate(GENERATED_KEY, secretKey))` (`:25`) vs a rule with no
   REQUIRES and an **unconditional** `ENSURES preparedKeyMaterial` — and **no
   `@fail`, empty `@match`** (`:49-51`); PBK `c1`/`err2` demanding
   `RANDOMIZED(password)` (`:43,:61`) vs `REQUIRES randomized[salt]` only
   (`PBEKeySpec.cryptsl:40`), err1 message "**>= 1000**" vs guard `>= 10000`
   (`:55` vs `:42,:53`), `FORBIDDEN … => c1` (`.cryptsl:16-18`), f1/f2 reporting
   `InvalidSequenceOfMethodCalls` (`:29,:35`), unary `SPECCED_KEY` write (`:47`).
3. **Artifacts**: indexing shapes and transition tables extracted by me from the
   five round `*RuntimeMonitor.java`: CIS/COS = **one static process-global
   monitor** (CIS `:275`, COS `:309`, `AbstractAtomicMonitor`, no indexing
   tree); KPR = `AbstractSynchronizedMonitor` (`:127`), empty-binding `Tuple2`
   (`:306`) + `MapOfMonitor` (`:307`); SKY and PBK per-object `MapOfMonitor`
   (`:225`, `:491`). Tables: CIS `c1={3,4,4,4,4}`, `r1/r2={4,1,4,1,4}`,
   `cl1={4,2,4,4,4}` (fail=4); COS `c1={2,4,4,4,4}`, `w1/w2/fl={4,1,1,4,4}`,
   `cl={4,3,4,4,4}`; KPR `c1={1,2,2}`, `gpu/gpr={2,1,2}` (fail=2, match=1);
   SKY `e1={0,2,2}`, `d={1,2,2}`, **match = state∈{0,1}, no fail category at
   all** (`:88,:138`); PBK carriers `{0,3,3,3}`, `c1={1,3,3,3}`, `c2={3,2,3,3}`
   (fail=3, match=2). SKY suppression prologue (`return false` **before**
   `handleEvent`, `:129-131`) and body-before-transition writes verified. KPR
   shadowing verified in the artifact: local `KeyPair keyPair` in
   `Prop_1_event_c1` (`:179`) shadows the field (`:138`); `Prop_1_handler_match`
   reads the never-assigned field (`:239-244`).
4. **Production toolchain sources** (project rule: file:line before accepting a
   mechanism): `WrapperEmitter.firstCallTarget/findFirstCall` keeps only the
   FIRST `call(...)` of a disjunction (`WrapperEmitter.java:507-526`; the
   comment concedes the corpus assumption); `shouldWrap` = position=="after"
   (`:161-163`); `literalFallback` returns null for non-static targets
   (`:475-498`); `AndroidClassIndex.methods()` iterates **declared** methods
   only (`:115-126`; the hierarchy walk exists only in `isAssignableFrom`,
   `:132-150`); `WrapperEmitter:369` calls exactly that declared-only overload;
   `DexWeaver` INV-INS-66 skips non-constructor inline-AFTER plans
   (`:480-515`, `plansSkippedAliasing++`); subtype expansion covers only
   APK-internal subtypes (`expandWrapperReplacementsForApk`, `:207-231`).
   Diagnostics chain: `ErrorDescription` 3-arg ctor delegates with `"unknown"`
   (`:35-37`); `equals/hashCode` over the summary only, `expecting` excluded —
   the code comment itself names the dedupe consequence (`:108-139`);
   `ErrorSummary` = (spec,error,class,method,location) (`:23-42`);
   `ErrorCollector.addError` dedupes via `Set.add` (`:40-44`). GATOR client
   keying: `getDeclaringClass().getName()+"#"+getName()`, literal set contains,
   no hierarchy resolution (`RvsecAnalysisClient.java:585-586, 613-631`) —
   closes GAMA-SET-14's single route.
5. **Platform**: `javax.crypto.SecretKey` in the frozen android-30 declares NO
   methods (only `serialVersionUID`; javap over class bytes extracted by me);
   the CIS/COS 1-arg constructors are `protected` (same method).
6. **Oracle-wide grep**: `generatedCipher` appears in **0 of the 33** api30
   `.cryptsl` files; CIS/COS/SecretKey rules have no REQUIRES section;
   `Cipher.cryptsl` ENSURES only `encrypted[…]` (`:187-194`).
7. **gh101 registers read**: `divergence_record.csv:2-3` assert "Closes the
   rule's REQUIRES generatedCipher[ciph]" — a REQUIRES the api30 rules do not
   contain (misstated oracle); `:83` (SKY) asserts "a second d or a getEncoded
   after d **fails**" with no note that no `@fail` handler exists and that the
   gate makes ge-after-d unreachable; `conformance_record.csv:16,18,20`;
   `predicate_omissions.csv` rows 3/10/19/20 (GENERATED_KEY_PAIR, SPECCED_KEY,
   cipheredInput/OutputStream — registered, D-S14); `predicate_edges.csv` rows
   2,4,35-37,39 (`missing`), 54-55 (`present`, slot-blind), 64
   (`present-surrogate`, no gate caveat), 65; `README.md:17-18` — edges file is
   the **declared pre-repair baseline "kept as authored"** (decisive for
   BETA-SET-10); README §4.11 registers PBEKeySpec `neverTypeOf` as
   inexpressible (with its own missing-enumeration note); `design.md:190`
   census keyed on `AbstractSynchronizedMonitor`; `tasks.md:81` (PBK f1/f2
   empty-slice repair — the exact class KPR c1 still carries). Absence greps
   re-executed by me: `flush`, `len > off`, `co?`/optional/generateKeyPair,
   parameterless/global monitor, `1000` (outside 10000), KeyPairSpec.c1 — **0
   hits each** across `data/gh101/` and the change tree.
8. **History**: `errors.csv` sha `78023def…` re-verified; independent grep:
   **668** KeyPairSpec lines, all containing `unknown`; **0** lines for
   CIS/COS/PBK spec names — triangulating Gama's four-unit stratification.
9. **J1-B — standard walk test (executed)**: `juiz_walk_batchB.py` parses the
   transition tables from the frozen round artifacts (hash-assert inside) and
   walks them with the verified dispatch semantics (fail categories, `__RESET`,
   global monitor, suppression): **17/17 checks PASS** — CIS 2nd legal stream
   → 3 fails (post-`__RESET` cascade); COS `[c1,fl,cl]` accepted (FN witness)
   and flush-after-close → 1 fail (FP witness); COS 2nd stream → 3 fails;
   KPR `gpu[0]=2` and `[getPublic]` → fail; KPR interleaved getters legal
   (reading A); SKY `d,d` and `d,e1` silent in dead state, accepting {0,1} =
   `ge* d?`; PBK carriers loop at 0, `err1→c2` and `f1→c2` → delayed fail,
   `c1,c2` → match (`juiz_walk_batchB_output.txt`).
10. **J2-B — independent end-to-end drive (executed, 3 byte-identical reps)**:
    `juiz_JuizDriveB.java` compiles the five ROUND monitors unmodified against
    the production jars and drives the generated static event methods with real
    JDK objects (class outside package `mop`): **(J2a)** 2nd CrySL-legal
    CipherInputStream lifecycle → **3 spurious `InvalidSequenceOfMethodCalls`,
    all `expecting=unknown`**, at the three stream-2 lines; **(J2b)** ctor with
    unmarked (oracle-legal) cipher → 1 `UnsatisfiedConstraint` — the
    extra-oracle FP; **(J2c)** COS `[construct,flush,close]` with **no write**
    → 0 errors (executed FN vs `Writes+`); 2nd legal COS cycle → 3-fail
    cascade; flush-after-close → 1 spurious fail (executed FP); **(J2d)**
    `KeyPairGenerator.generateKeyPair()` then `getPublic()` → 1 spurious fail;
    **(J2e)** two legal KeyPair constructions → spurious fail at the 2nd c1 AND
    at kp2's own subsequent `getPublic()` (broadcast + reset contamination);
    `isInAcceptingState(null)=true`, `(kp1)=(kp2)=false` — **@match marks
    null**; **(J2f)** both KPR REQUIRES violated at one line, 2 `addError`
    calls → **1 record** (the private-key clause silenced by dedupe);
    **(J2g)** SKY: unmarked key's `getEncoded` suppressed,
    `RANDOMIZED(enc1)=false` (starved unconditional ENSURES); double-destroy +
    ge-after-destroy → **0 records**; re-marked key in the dead state still
    **writes RANDOMIZED** (body-before-transition); **(J2h)** PBK canonical
    case (user-typed password, SecureRandom salt, iter=10000 — fully
    rule-conformant) → `UnsatisfiedConstraint "first argument should have been
    randomized"` + `SPECCED_KEY=false` + the rule's own mandatory
    `clearPassword` → **spurious `InvalidSequenceOfMethodCalls`** (the residue
    on an oracle-conformant trace); **(J2i)** err1's record carries the false
    text "third argument should be >= 1000"; same-line err1+err2 → 1 record vs
    distinct-lines → 2 (dedupe control) (`juiz_driveB_rep1.txt`; reps 2–3
    sha-identical).
11. **Beta weave measurements conferred**: `beta_weave_all.out` —
    SecretKeySpec section has **0 WrapperEmitter entries** and all 7 owner
    variants UNTOUCHED; `cis_readB`/`cos_writeB` UNTOUCHED with
    `plansSkippedAliasing=1` while the sibling overloads are WRAPPED/INLINE —
    matching the source mechanisms of item 4.

Epistemic labels: **fato medido** (my execution this session), **observado em
artefato** (cited file:line), **inferido**, **histórico** (pre-repair
errors.csv — hypothesis generator only).

## 1. Conflict / convergence matrix

Routes are counted, not agents (REF-B-07): "3 agents" over the same frozen
bytes is one reading route plus the executed routes named.

| # | Phenomenon / Claims | Alfa | Beta | Gama | Conflicting evidence | Discriminating test | Resolution | Residual uncertainty |
|---|---|---|---|---|---|---|---|---|
| 1 | **FEN-STREAMS-MONITOR-GLOBAL** — parameterless CIS/COS ⇒ one process-global monitor; 2nd legal stream cascades — ALFA-CIS-01/COS-01, BETA-CIS-03/COS-04, GAMA-CIS-01/COS-01 (+BETA-SET-05, ALFA-SET-07, GAMA-CIS-03/COS-04 registers) | FAIL crit (executed CIS+COS) | FAIL crit (executed both) | FAIL crit (CIS executed; COS structural) | None on substance; Gama's COS leg was structural-identity only | **J2a + J2c executed by the judge** — COS cascade now executed directly, closing Gama's inference gap | FAIL — INCORRETA critical ×6; unregistered (verified). Batch A FEN-HMC-MONITOR-GLOBAL recurring as "no parameter at all"; the standing indexing-tree check did its job | Weave/device (G6/G10); micro-APK pendencies named |
| 2 | **FEN-SET-GENCIPHER-EXTRA** — `generatedCipher` gate exists in no api30 rule — ALFA-CIS-02/COS-03/SET-06 (FAIL crit/major) × **BETA-CIS-08/COS-09 (PASS "REQUIRES realized")** | FAIL crit | **PASS** | (PASS scoped to report mechanics, GAMA-CIS-05) | **Real conflict**: same clause, opposite labels | Judge grep: `generatedCipher` 0/33; rules have no REQUIRES; divergence rows 2-3 read — they assert a REQUIRES the api30 rule lacks; **J2b executed the FP** | Alfa prevails. **BETA-CIS-08 and BETA-COS-09 overturned PASS→FAIL** (INCORRETA critical): a mechanically correct reader of an extra-oracle clause is not fidelity (batch A DHG precedent); registered ≠ approved, register misstates the oracle. GAMA-CIS-05/COS-05 stay PASS as *scoped diagnostics-mechanics* claims | Researcher may formally reduce scope to the upstream 1.5.2 anchor — until then INCORRETA vs the raw oracle (pre_registro §1) |
| 3 | **FEN-COS-FLUSH** — `fl` in the loop though the rule's alphabet has no flush — ALFA-COS-02 (crit, FP+FN executed), BETA-COS-03 (major, FN executed), GAMA-COS-02 (crit, FP+FN executed) | FAIL crit | FAIL major | FAIL crit | Severity only | J2c executed BOTH directions (FN: write-less cycle accepted; FP: flush-after-close accused) | FAIL — INCORRETA critical ×3; **BETA-COS-03 harmonized major→critical** (§4 has no rarity carve-out; FN executed). Unregistered (flush: 0 hits) | IOException variants on real streams (FP direction only) |
| 4 | **FEN-KPR-CO-OPCIONAL** — `co?` dropped; canonical generator route accused — ALFA-KPR-01, BETA-KPR-02, GAMA-KPR-01 (+GAMA-KPR-07 register; GAMA-KPR-06 history INC) | FAIL crit | FAIL crit | FAIL crit | None | J2d executed by the judge; rule `:27` read; register greps re-run | FAIL — INCORRETA critical; unregistered. **H-KPR-1** (668 historical lines = this FP) stays a *hypothesis*: stratification facts re-verified by me (668/668 InvalidSeq+unknown, 8 keygen sites), causal attribution deferred to the named replay tests — GAMA-KPR-06 INCONCLUSIVE, outside denominator | Replay (G10-KPR-1) |
| 5 | **FEN-KPR-C1-SLICE-VAZIO** — c1 binds no spec parameter ⇒ empty-slice broadcast, cross-instance contamination — ALFA-KPR-02/06, BETA-KPR-03, GAMA-KPR-02 (+ALFA-KPR-08, BETA-SET-06) | FAIL crit | FAIL crit | FAIL crit | None | J2e executed by the judge (both effects); dispatch code verified; gh101's own repaired twin (PBK f1/f2, tasks.md:81) confirmed | FAIL — INCORRETA critical; the gh101-repaired defect class live and unregistered in KPR; census signature present in the artifact | Weave/device |
| 6 | **FEN-KPR-MATCH-NULL** — shadowed `keyPair` ⇒ `@match` marks null — BETA-KPR-04 (major, generator mechanism) × GAMA-KPR-03 (minor, inert instance) | (folded in KPR-07) | FAIL major | FAIL minor | Severity/unit | J2e null probe executed by the judge; artifact `:179` vs `:138` verified | Both stand at their units (batch A instance-vs-pattern precedent): generator-mechanism claim major, inert-instance claim minor. ALFA-KPR-07's clone-copy wording corrected to the shadowed-local mechanism — net effect identical, claim confirmed | Becomes active if any reader of acceptingState is added |
| 7 | **FEN-SKY-GATE-SUPRESSAO** — extra-oracle GENERATED_KEY gate starves the unconditional ENSURES — ALFA-SKY-02, BETA-SKY-04, GAMA-SKY-02 (+GAMA-SKY-04 register) | FAIL crit | FAIL crit | FAIL crit | None (downstream chain read, not driven — named) | J2g executed by the judge (RANDOMIZED withheld); rule verified (no REQUIRES) | FAIL — INCORRETA critical; unregistered (edges:64 carries no gate caveat — verified). FEN-DHG-SUPRESSAO shape on a cross-spec edge | End-to-end downstream accusation (G10-SKY-1) read, not driven |
| 8 | **FEN-SKY-SEM-CANAL** — no @fail, empty @match: spec structurally unable to report — ALFA-SKY-03 (OMITIDA crit), BETA-SKY-05 (INCORRETA major), GAMA-SKY-01 (INCORRETA crit) | FAIL crit | FAIL major | FAIL crit | Severity + classification label | J2g executed by the judge: two realizable oracle violations → 0 records; dead-state RANDOMIZED write also executed | FAIL — critical ×3 (**BETA-SKY-05 harmonized major→critical**: executed FN, §4). Batch A dead-`@fail` minor precedent explicitly inapplicable: here violating traces EXIST and there is no live channel at all. Filed classifications (OMITIDA vs INCORRETA) both defensible states; kept as filed, one phenomenon | destroy() rarity affects magnitude, not existence |
| 9 | **FEN-SKY-ZERO-CAPTURA + FEN-SET-FIRSTCALL-DISJUNCT + FEN-SET-TIPO-ESTATICO** — production dexlib2 capture defects — BETA-SKY-02, BETA-CIS-04/COS-05, BETA-SET-02/03/04 | (ALFA-SKY-07 INC, ajc side) | FAIL crit/major (MEDIDO, production pipeline) | (GAMA-SET-14 static-analysis analogue) | None — Beta's lane; single-source measurements | Judge verified every cited mechanism at source (§0.4) + platform fact (§0.5) + conferred the measured outputs (§0.11) | FAIL — INCORRETA: SKY entirely inert on the production dexlib2 path (critical); read(byte[])/write(byte[]) silently dropped (critical); upcast invisibility unregistered (major). **Decision: these static measurements of the production pipeline inform G5 (dexlib2 half)** — see §5 preamble. ALFA-SKY-07 (ajc half) stays INCONCLUSIVE | ajc half + ART execution (G6/G10); other batches' interface targets unswept |
| 10 | **FEN-PBK-SENHA-EXTRA** — RANDOMIZED(password) demanded; rule requires randomized[salt] only — ALFA-PBK-02, BETA-PBK-04, GAMA-PBK-05 (+GAMA-PBK-06 register) | FAIL crit | FAIL crit | FAIL crit | None | J2h executed by the judge (canonical case accused + ENSURES starved) | FAIL — INCORRETA critical; unregistered (conformance:16 covers only iteration/keylength; conformance:18 concedes the accusation via the RandomStringPassword mitigation); inherited from `jca`, not a gh101 regression — still blocks | Oracle-bias direction recorded (defensible security intent; not the frozen oracle) |
| 11 | **FEN-PBK-RESIDUO** — violating/forbidden construction leaves state 0; the rule's own mandatory `cP` then fails — ALFA-PBK-03 (crit), BETA-PBK-06 (major), GAMA-PBK-04 (major; "refutes pilot H2's decoupling prediction") | FAIL crit | FAIL major | FAIL major | Severity; Gama/Beta hedge: "the trace contains a real misuse" | **J2h**: via phenomenon 10 the residue fires on a **fully oracle-conformant** trace; and the record asserts a sequence violation that did not occur | FAIL — INCORRETA critical ×3 (**BETA-PBK-06 and GAMA-PBK-04 harmonized → critical**, §4). **Pilot H2 update recorded**: the specific+generic pairing the layer-2 repair removed at the violating event *returns in delayed form at cP* — H2's decoupling prediction is refuted for PBK whenever cP is called | Which record survives dedupe under dexlib2 advice order |
| 12 | **FEN-PBK-FORBIDDEN-MAP** — `=> c1` continuation — ALFA-PBK-04 (FAIL major) × BETA-PBK-08 (PASS equivalent detection) × GAMA-PBK-03 (FAIL major, miscategorized) | FAIL | PASS | FAIL | Apparent conflict | Walk `[f1,c2]` → fail (J1-B); f1/f2 bodies read | No contradiction — units differ: detection half (1 report per forbidden ctor) is equivalent → BETA-PBK-08 PASS **scoped**; continuation half (`=> c1`) not honored → ALFA-PBK-04 FAIL major; category/`unknown` half → GAMA-PBK-03 FAIL major. Composite adjudicated across the three | — |
| 13 | **FEN-SET-DEDUPE** — ErrorSummary drops `expecting`; same-__LOC clauses collapse — BETA-SET-07, GAMA-KPR-04, GAMA-PBK-01 | — | FAIL major | FAIL major ×2 | None | Source verified by judge (§0.4); **J2f/J2i executed** (KPR 2→1; PBK controls) | FAIL — INCORRETA major; the surviving clause follows advice order (named threat) | dexlib2 advice order may change the survivor, not the collapse |
| 14 | **FEN-SET-FAIL-UNKNOWN** — every live `@fail` in the batch emits `expecting=unknown` — ALFA-CIS-06/COS-07/KPR-07(part)/SET-08, GAMA-CIS-02/COS-03/KPR-05 | FAIL major | (in report §2) | FAIL major | None | J2 executed across all four live channels | FAIL — INCORRETA major (set-wide pattern of batch A GAMA-IVP-02 class; now 4 of 5 specs + 1 channel-less); G9-decisive everywhere | — |
| 15 | **FEN-PBE-MSG-1000** — "1000" message vs 10000 guard — ALFA-PBK-07, BETA-PBK-05 (minor), GAMA-PBK-02 (major) | FAIL major | FAIL minor | FAIL major | Severity | J2i measured the record text | FAIL — INCORRETA major (**BETA-PBK-05 harmonized minor→major**: batch A twin phenomenon severity); exact twin of batch A's PBE defect | — |
| 16 | **FEN-CIS-CTOR1-OMITIDA + FEN-CIS-LENOFF** — rule clauses omitted — ALFA-CIS-03/04, COS-04/05, BETA-CIS-06/07, COS-07/10, GAMA-CIS-04/COS-06 (+GAMA-CIS-06 INC) | FAIL major | FAIL major/minor | FAIL major / INC | Severity (Beta minor on ctors) | Judge: protected ctors + empty bodies verified; register greps 0 hits | FAIL — OMITIDA major (**BETA-CIS-06/COS-10 harmonized minor→major**: pre_registro §4, clause omitted without deliberate-omission register). GAMA-CIS-06 (subclass realizability) stays INCONCLUSIVE | Subclass-flow frequency in real apps |
| 17 | **gh101 records stale?** — BETA-SET-10 (FAIL, 7 edges rows) | — | FAIL minor | (GAMA registers claims target *other* files) | Batch A precedent directly on point | Judge re-read `README.md:17-18` | **BETA-SET-10 overturned FAIL→PASS**: `predicate_edges.csv` is the declared pre-repair baseline "kept as authored" — exactly the batch A BETA-SET-07 resolution; the friction (semantics live in README) noted again. Gama's OMITIDA claims (GAMA-CIS-03/COS-04/KPR-07/SKY-04/PBK-06, ALFA-KPR-08/SKY-06) target `divergence_record`/`conformance_record` **absences** — different files, different semantics — all CONFIRMED FAIL | Register semantics briefing (batch A §6 item 5) still not in the round packet |
| 18 | **Fail-open family** — BETA-SET-09 (p1/p2/p3/p5/p6) | — | FAIL major | — | None | Probes measured (outputs conferred); p3 (orphaned event → all-fail row = permanent FP source) and p6 (typo'd `epsilon` changes acceptance silently) are NEW shapes vs pilot/batch A registers | FAIL — INCORRETA major (pattern claim). p6 doubles as positive evidence that the frozen SKY artifact realizes `epsilon` correctly | Remaining unprobed shapes |
| 19 | **Closed negatives** — BETA-SKY-07 (no SecretKeySpec×SecretKeySpecSpec collision, no double-fire), GAMA-SET-15 (no newline-escape exposure), BETA-SET-01 (determinism) | — | PASS | PASS | None | Merged compile + weave + runtime (Beta, measured); expecting-literals read by judge in all five specs | PASS — the round-manifest explicit checks are closed with executed/verified evidence | — |
| 20 | **Static-analysis synergy** — GAMA-SET-12/13/14 | — | (BETA-SET-04 dynamic analogue) | FAIL minor/major | Single routes | Judge verified the GATOR-client keying at source (§0.4); extractor CSVs conferred; batch A GAMA-SET-09 verification carried | FAIL — INCORRETA: `jca` default loses exactly the `destroy` target (minor); 6/20 `new` rows unresolvable (major); interface-receiver mismatch (major, single route closed by judge) | Full GATOR invocation not re-run |

## 2. Detailed resolutions — what changed and why

### 2.1 Overturned positions (all by judge-verified evidence, none by vote)

| Claim | From → To | Why |
|---|---|---|
| BETA-CIS-08 | PASS → **FAIL** (INCORRETA, critical) | The claim's premise — "the rule's REQUIRES generatedCipher" — is false for the frozen oracle: the api30 CipherInputStream rule has **no REQUIRES section** and `generatedCipher` exists in **no** api30 rule (judge grep, §0.6). A mechanically correct reader of an extra-oracle clause is INCORRETA vs the raw oracle (pre_registro §1; batch A DHG precedent). The FP is executed (J2b). The gh101 register does not save it: divergence rows 2-3 assert the nonexistent REQUIRES (§0.7) — registered ≠ approved (batch A FEN-SKS-WHITELIST precedent). |
| BETA-COS-09 | PASS → **FAIL** (INCORRETA, critical) | Same premise, same verification, COS twin. |
| BETA-SET-10 | FAIL → **PASS** | `README.md:17-18` (re-verified by me) declares `predicate_edges.csv` the **pre-repair baseline "kept as authored"** — the 7 rows Beta cites as stale (`missing`/`wrong-constant` for edges the frozen set realizes) are exactly that declared semantics. Identical to the batch A BETA-SET-07 overturn. Residual friction (the file's semantics live only in the README) recorded again; batch A §6 item 5 (register briefing) evidently still needed. |

### 2.2 Severity harmonizations (justified; severity does not enter the score)

| Claim(s) | From → To | Justification |
|---|---|---|
| BETA-COS-03 | major → **critical** | The FN (write-less cycle accepted) is executed — by Beta and by me (J2c). Pre_registro §4: FN demonstrable in a realizable trace ⇒ critical; rarity is not a carve-out. Aligns with ALFA-COS-02/GAMA-COS-02. |
| BETA-SKY-05 | major → **critical** | Both realizable ORDER violations executed silent (J2g); no channel exists at all. §4. Aligns with ALFA-SKY-03/GAMA-SKY-01. |
| BETA-PBK-06, GAMA-PBK-04 | major → **critical** | J2h shows the delayed residue firing on a **fully oracle-conformant** trace (via FEN-PBK-SENHA-EXTRA), and even on a violating trace the record asserts a sequence violation that did not occur. §4. Aligns with ALFA-PBK-03. |
| BETA-PBK-05 | minor → **major** | FEN-PBE-MSG-1000 — the batch A twin phenomenon was resolved major; message factually false by 10× on a live reporting path (measured, J2i). |
| BETA-CIS-06, BETA-COS-10 | minor → **major** | Pre_registro §4: a rule clause (`c1`, a declared EVENT) OMITIDA without a deliberate-omission register is major. The realizability note (protected ctor, subclass-only) is retained as a threat, not a severity discount. |

Severity distinction kept: FEN-SET-EOT claims (ALFA-CIS-07/COS-08/PBK-09) stay
**minor** — end-of-trace acceptance is not a declared clause of the rule, so the
§4 "cláusula OMITIDA" trigger does not apply; the pattern is recorded for the
registers instead.

### 2.3 Single-route claims and how they were closed

GAMA-SET-14 (interface-receiver static blindness): closed by my verification of
the literal `declaringClass#name` keying with no hierarchy resolution
(`RvsecAnalysisClient.java:585-586, 628-630`). BETA-SKY-02/BETA-SET-02/03/04
(production dexlib2): every cited mechanism verified at source (§0.4), the
platform fact re-measured (§0.5), and Beta's weave outputs conferred (§0.11).
ALFA-KPR-04 (null-guarded reads): guards verified at `.mop:32/:36`; FN follows
structurally; minor stands with the CrySL-null-semantics caveat. ALFA-SKY-06 /
GAMA-SKY-04 (register rows): rows read by me (§0.7).

### 2.4 Dimension-assignment pendencies (D-piloto-4 item 1 — recorded, not re-assigned)

- FEN-STREAMS-MONITOR-GLOBAL: Alfa filed under `linguagem_formal`, Beta and
  Gama under `bindings_clausulas`.
- FEN-PBK-RESIDUO: Alfa/Gama under `linguagem_formal`, Beta under `diagnostico`.
- FEN-PBK-SENHA-EXTRA: Alfa/Beta under `bindings_clausulas`, Gama under
  `predicados_composicao`.
- FEN-SKY-SEM-CANAL: all three under `diagnostico` (no pendency).

The per-phenomenon counts (§3/§4) are the corrective lens, as in batch A.

### 2.5 Pilot-hypothesis update (recorded per the round instructions)

**H2** ("the derived set decouples the specific-error + spurious-InvalidSeq
pairing") is **refuted in delayed form for PBK**: the pairing no longer occurs
at the violating event (layer-2 repair held — FEN-SET-LAYER2-REPARO, 3 PASS
claims), but returns at the next mandatory event (`cP`), executed by Gama and
re-executed by me (J2h). For KPR the historical data cannot test H2 (no
specific error ever fired — 0 of 258 cells). H1 (zeros decompose per spec) and
H7 (process-restart inflation) stand as used; H-KPR-1 filed as a new named
hypothesis with three discriminating replay tests (GAMA-KPR-06, INCONCLUSIVE).

## 3. Consolidated classification

**Critical phenomena (12), 38 critical claims** (per-claim list in the CSV):

| FEN | Specs | State |
|---|---|---|
| FEN-STREAMS-MONITOR-GLOBAL | CIS, COS (+set) | INCORRETA — executed FP cascade on every 2nd legal stream (J2a/J2c); unregistered; batch A HMC family, now parameterless |
| FEN-SET-GENCIPHER-EXTRA | CIS, COS (+set) | INCORRETA — executed FP (J2b); predicate exists in no api30 rule; register misstates the oracle; 2 Beta claims overturned |
| FEN-COS-FLUSH | COS | INCORRETA — executed FN and FP (J2c); event outside the rule's alphabet breaks both inclusions |
| FEN-KPR-CO-OPCIONAL | KPR | INCORRETA — executed FP on the canonical JCA route (J2d); unregistered; history consistent (hypothesis only) |
| FEN-KPR-C1-SLICE-VAZIO | KPR | INCORRETA — executed broadcast contamination (J2e); the gh101-repaired defect class, live and unregistered |
| FEN-SKY-GATE-SUPRESSAO | SKY | INCORRETA — executed ENSURES starvation (J2g); rule has no REQUIRES; downstream FP chain read |
| FEN-SKY-SEM-CANAL | SKY | OMITIDA/INCORRETA — executed: two realizable violations, zero records (J2g); no channel exists |
| FEN-SKS-SURROGATE (writer) | SKY | INCORRETA — RANDOMIZED aliases preparedKeyMaterial; registered surrogate without equivalence proof; joins batch A |
| FEN-PBK-SENHA-EXTRA | PBK | INCORRETA — executed FP on the canonical PBE use + ENSURES starvation (J2h); unregistered |
| FEN-PBK-RESIDUO | PBK | INCORRETA — executed spurious fail at the rule's own mandatory cP (J2h); D-S10 class; H2 updated |
| FEN-SET-FIRSTCALL-DISJUNCT | CIS, COS (set) | INCORRETA toolchain — read(byte[])/write(byte[]) matched then silently discarded; source verified, measured |
| FEN-SKY-ZERO-CAPTURA | SKY (set) | INCORRETA toolchain — whole spec inert on the production dexlib2 path; three mechanisms verified, measured |

**Major (non-critical) phenomena**: FEN-CIS-CTOR1-OMITIDA and FEN-CIS-LENOFF
(rule clauses omitted, unregistered — CIS and COS); FEN-SET-FAIL-UNKNOWN (every
live `@fail` of the batch emits `expecting=unknown` — G9-decisive);
FEN-PBE-MSG-1000 (batch A twin); FEN-PBK-FORBIDDEN-MAP (continuation +
miscategorization); FEN-SET-DEDUPE (clause identity and multiplicity lost —
executed); FEN-KPR-MATCH-NULL (generator-mechanism half); FEN-SET-GERADOR-SILENCIO
/ BETA-SET-05/06 + ALFA-SET-05/07 (silent generator acceptances, census blind
spots); FEN-SET-TIPO-ESTATICO (unregistered scope reduction); FEN-SET-FAILOPEN
(2 new shapes); FEN-SET-GENERATEDKEY-2A-CASA (PBK speccedKey slot, latent);
register-absence family (GAMA-CIS-03/COS-04/KPR-07/SKY-04/PBK-06, ALFA-KPR-08);
GAMA-SET-13/14 (static path); GAMA-KPR-05 et al. (diagnostics).

**DIVERGÊNCIA_EQUIVALENTE_COMPROVADA**: BETA-PBK-08 (FORBIDDEN detection half,
scoped).

**LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA (PASS, blocks total adherence)**:
cipheredInputStream/cipheredOutputStream no-constant omissions (registered,
D-S14); PBK `neverTypeOf` (registered).

**FIDELIDADE_DEMONSTRADA highlights**: SKY ORDER `ge*, d?` via `(d|epsilon)`
(3 routes + judge walk); SKY NEGATES per-object; KPR predicate-edge repairs
held (gpr constant, REQUIRES reads); PBK layer-2 star prefix held; capture
exact for KPR/PBK under the production weave; no name collision / no
double-fire for SecretKeySpec×SecretKeySpecSpec; generation determinism.

**INCONCLUSIVE (5, outside every denominator, named pendencies)**:
ALFA-SKY-07 (ajc interface matching), BETA-SET-11 (ajc/device, G6/G10),
GAMA-CIS-06 (subclass-flow realizability), GAMA-KPR-06 (H-KPR-1 replay),
GAMA-SET-16 (historical zero-emission of CIS/COS/SKY/PBK).

**Resolution totals**: 133 claims → **40 PASS, 88 FAIL, 5 INCONCLUSIVE**;
38 critical FAILs across the 12 critical phenomena. Position changes: 2
PASS→FAIL, 1 FAIL→PASS (§2.1); 6 severity harmonizations (§2.2). No
counterexample was dismissed; no resolution used agent counting.

## 4. Descriptive scores (pre-registered weights; verbatim from `juiz_rescore_batchB.py`)

Per-spec scores over that spec's resolved claims only; SET separate
(D-piloto-4); **raw weighted sum is the score of record** (D-batchA-1);
denominator = PASS+FAIL, INCONCLUSIVE outside.

| Unit | ling(20) | capt(20) | bind(15) | pred(15) | tool(15) | diag(10) | repr(5) | **Raw (of record)** | Status |
|---|---|---|---|---|---|---|---|---|---|
| CIS | 6.67 (1/3) | 5.00 (1/4 +1INC) | 2.50 (1/6) | 7.50 (2/4) | 15.00 (1/1) | 3.33 (1/3) | 0.00 (0/1) | **40.00** | INCOMPLETE (1 INC) |
| COS | 3.33 (1/6) | 5.00 (1/4) | 0.00 (0/5) | 7.50 (2/4) | 15.00 (1/1) | 3.33 (1/3) | 0.00 (0/1) | **34.17** | COMPLETE |
| KPR | 8.00 (2/5) | 20.00 (1/1) | 0.00 (0/6) | 15.00 (2/2) | 7.50 (1/2) | 0.00 (0/3) | 0.00 (0/2 +1INC) | **50.50** | INCOMPLETE (1 INC) |
| SKY | 20.00 (3/3) | 0.00 (0/1 +1INC) | 5.00 (1/3) | 7.50 (2/4) | 15.00 (2/2) | 0.00 (0/3) | 0.00 (0/2) | **47.50** | INCOMPLETE (1 INC) |
| PBK | 6.67 (2/6) | 20.00 (1/1) | 9.00 (3/5) | 7.50 (2/4) | 15.00 (1/1) | 1.43 (1/7) | 0.00 (0/1) | **59.60** | COMPLETE |

**SET score** (separate): capt 0.00 (0/1), pred 0.00 (0/1), tool 0.00 (0/11
+1INC), diag 3.33 (1/3), repr 5.00 (2/2 +1INC) → **raw 8.33**; unattainable
weight 35 (no ling/bind SET claims); derived reading (labeled, not the record):
8.33/65 = 12.82%; **INCOMPLETE** (2 INCONCLUSIVE outside).

**Batch-B aggregate** (context only; 113 spec claims, SET excluded): ling 7.83
(9/23), capt 7.27 (4/11 +2INC), bind 3.00 (5/25), pred 8.33 (10/18), tool 12.86
(6/7), diag 1.58 (3/19), repr 0.00 (0/7 +1INC) → **40.87**; INCOMPLETE (3 INC).

**Mandatory labels**: descriptive score ≠ probability of correction ≠ verdict;
never rounded to 100; a score never opens a gate. CIS/KPR/SKY and the SET/
aggregate scores are INCOMPLETE (INCONCLUSIVEs outside the denominator).
Context readings: (i) the batch aggregate (40.87) sits well below batch A's
(61.07) — batch B's multi-event lifecycles expose automaton-plane defects the
single-constructor batch A specs could not have; (ii) claim counts overstate
convergent phenomena (FEN-STREAMS-MONITOR-GLOBAL alone carries 10 claims) —
use the §4/§3 per-phenomenon counts; (iii) reprodutibilidade is 0/7 across the
five specs — every spec has at least one unregistered material divergence.

Per-phenomenon resolution counts: verbatim block at the end of
`juiz_rescore_batchB_output.txt` (36 FEN groups after unification).

## 5. Per-spec verdicts (covered scope: G2, G3, G4, G5, G7, G9)

**Operative gate rule** (batch A REF-B-05): a gate fails when its
pre-registered criteria (`pre_registro.md` §3, protocol §16) are met; a
critical INCORRETA/OMITIDA inside the gate is one *sufficient* trigger, not
the only one.

**G5 scope decision (explicit, as the round required)**: Beta's dexlib2
findings are **static measurements of the production pipeline** (the exact
BatchRunner wiring: DescriptorReader → TypeResolver → AndroidClassIndex →
WrapperEmitter → DexWeaver, over the frozen android-30 jar and synthetic DEX).
They are admitted as **G5 evidence for the dexlib2 half of production capture**
— same epistemic footing as batch A's production-matcher measurements — with
the ajc half and ART execution held as named pendencies (G6/G10). They are not
counted as G6 (end-to-end weaving) evidence.

### CipherInputStreamSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean deterministic generation measured; 4 events; coenable saturated (BETA-CIS-01) |
| G3 | **FAIL** | per-instance language broken: process-global monitor, executed 3-FP cascade on the 2nd legal stream (FEN-STREAMS-MONITOR-GLOBAL, J2a) — critical |
| G4 | **FAIL** | the rule's only CONSTRAINT (`len > off`) transcribed nowhere — OMITIDA major, unregistered (ALFA-CIS-04/BETA-CIS-07/GAMA-CIS-04) |
| G5 | **FAIL** | rule event `c1(is)` has no pointcut (OMITIDA major); production dexlib2 silently drops `read(byte[])` — zero-fire of an expected member, critical (BETA-CIS-04); remaining pointcuts exact (BETA-CIS-05) |
| G7 | **FAIL** | extra-oracle GENERATED_CIPHER gate — executed FP vs the raw oracle (FEN-SET-GENCIPHER-EXTRA, J2b) — critical; cipheredInputStream omission registered (LIMITAÇÃO, blocks total adherence, not this gate) |
| G9 | **FAIL** | the spec's only sequencing channel emits `expecting=unknown` on every record (executed, J2a) — criterion "nenhum unknown" |

### CipherOutputStreamSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured (BETA-COS-01) |
| G3 | **FAIL** | global monitor (executed cascade, J2c) AND `fl` outside the rule's alphabet — executed FN (write-less cycle accepted) and FP (flush-after-close accused) (FEN-COS-FLUSH) — two criticals |
| G4 | **FAIL** | `len > off` OMITIDA major, unregistered |
| G5 | **FAIL** | `c1(os)` omitted (major); `write(byte[])` dropped by the production dexlib2 path (critical, BETA-COS-05) |
| G7 | **FAIL** | extra-oracle GENERATED_CIPHER gate (critical, CIS twin) |
| G9 | **FAIL** | `expecting=unknown` on the only sequencing channel (executed) |

### KeyPairSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured (BETA-KPR-01) |
| G3 | **FAIL** | `co?` made mandatory: the canonical `generateKeyPair()` route is spuriously accused at its first getter — executed (J2d), critical, unregistered (FEN-KPR-CO-OPCIONAL); `(pu*,pr*)*` interleaving itself equivalent under reading A (ALFA-KPR-05 PASS) |
| G4 | **FAIL** | c1 binds no spec parameter → empty-slice broadcast, executed cross-instance contamination (J2e) — critical (FEN-KPR-C1-SLICE-VAZIO); null-guarded REQUIRES reads (minor FN); @match marks null (executed) |
| G5 | PASS | capture exact under the production weave: ctor inline, getters wrapped, neighbors free (BETA-KPR-05) |
| G7 | **FAIL** | lifecycle/parametric isolation violated (executed contamination — critical); predicate edges themselves faithful (ALFA-KPR-03/BETA-KPR-06 PASS; GENERATED_KEY_PAIR write-no-read registered) |
| G9 | **FAIL** | every sequencing record `unknown` (executed; 668/668 historical); dedupe silences the second REQUIRES clause at a shared site (executed, J2f) |

### SecretKeySpec.mop / target `javax.crypto.SecretKey` — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured; epsilon accepted by the production ERE plugin (BETA-SKY-01) |
| G3 | PASS | `ere e1* (d|epsilon)` = `ORDER ge*, d?` — dual inclusion at the effective automaton, per-object indexing (3 routes + judge walk J1-B) |
| G4 | **FAIL** | e1 gated by extra-oracle GENERATED_KEY — executed suppression/starvation (J2g) — critical, unregistered (FEN-SKY-GATE-SUPRESSAO) |
| G5 | **FAIL** | the whole spec is inert under the production dexlib2 path: 0 wrappers, all owner variants untouched — measured on the production pipeline, mechanisms judge-verified (FEN-SKY-ZERO-CAPTURA) — critical; ajc half INCONCLUSIVE (named pendency, ALFA-SKY-07) |
| G7 | **FAIL** | unconditional `ENSURES preparedKeyMaterial` starved by the gate (critical); RANDOMIZED surrogate aliasing without equivalence proof (critical, FEN-SKS-SURROGATE writer side); NEGATES edge itself faithful (PASS claims) |
| G9 | **FAIL** | no reporting channel exists at all — both realizable ORDER violations executed silent (J2g) — critical; register row 83 describes an unobservable "fails" (OMITIDA minor) |

### PBEKeySpecSpec — **REPROVADA** (covered scope)

| Gate | Result | Grounds |
|---|---|---|
| G2 | PASS | clean generation measured; 7 events ≤ 17 (BETA-PBK-01) |
| G3 | **FAIL** | delayed residue: a non-advancing construction makes the rule's own mandatory `clearPassword` fail spuriously — executed on an oracle-conformant trace (J2h) — critical (FEN-PBK-RESIDUO); FORBIDDEN `=> c1` continuation not honored (major); valid path itself faithful (ALFA-PBK-01 PASS) |
| G4 | **FAIL** | extra `RANDOMIZED(password)` requirement — the canonical PBE use case accused and starved of SPECCED_KEY, executed (J2h) — critical, unregistered (FEN-PBK-SENHA-EXTRA); guard partition and per-object isolation themselves exact (ALFA-PBK-08 PASS) |
| G5 | PASS | capture exhaustive on API 30: 3 ctors inline (4-arg advice = 4 events), clearPassword wrapped, neighbors free (BETA-PBK-02) |
| G7 | **FAIL** | ENSURES starvation on conformant specs (critical, via G4 phenomenon); `speccedKey[this, keylength]` second slot OMITIDA, register slot-blind (major); randomized[salt] read and NEGATES scope correct (ALFA-PBK-10 PASS) |
| G9 | **FAIL** | false "1000" message (measured); FORBIDDEN reported as `InvalidSequenceOfMethodCalls`+`unknown`; same-__LOC dedupe masks 2 of 3 clauses per site (executed); `@fail` channel `unknown` |

**Batch verdict line**: **5/5 REPROVADA in the covered scope** — every
gate-deciding defect anchored in evidence the judge executed (J1-B/J2-B) or
verified at source/register, over the frozen bytes. Per protocol §16 the set
cannot move toward `READY` from this batch. Cumulative: 12/12 audited specs
(pilot 2, batch A 5, batch B 5) REPROVADA in their covered scopes.

## 6. Observations for batch C (no gate changes)

1. **The indexing-tree check must include "no parameter at all".** Batch A's
   lesson ("verify the spec parameter is bound by every event") caught KPR;
   CIS/COS show the other face — no parameter declared, `AbstractAtomicMonitor`
   global singleton, invisible to the gh101 census signature. One grep over the
   remaining 10 specs for `^<SpecName>()` and for `AbstractSynchronizedMonitor`
   before the batch opens.
2. **Extra-oracle predicate gates are now a 4-instance family** (DHG condition,
   SKS whitelist, SKY GENERATED_KEY gate, PBK RANDOMIZED(password), plus the
   generatedCipher subsystem): grep every remaining spec's `condition(...)` and
   body `validate(...)` against its rule's REQUIRES/CONSTRAINTS section first —
   it is the highest-yield single check in both rounds.
3. **First-call-disjunct sweep**: any remaining spec with a `||` in a `call()`
   pointcut loses the later disjuncts on the production dexlib2 path
   (judge-verified mechanism). Grep `" || call("` over the 10 remaining specs
   and pre-file the capture claims.
4. **Interface-target sweep**: SKY will not be the only interface-owner spec in
   the corpus; `AndroidClassIndex.methods()` declared-only + static-only
   fallback + INV-INS-66 silence the whole spec. Check the remaining specs'
   target classes for interface/inherited members before the batch.
5. **Mandatory-successor residue**: the batch A working assumption "layer-2
   carrier prefixes are benign" holds only when no mandatory event follows.
   PBK's `cP` disproved it. For batch C specs, list every mandatory event
   after a carrier state before scoring language claims.
6. **Register briefing still missing.** BETA-SET-10 repeats batch A's
   BETA-SET-07 misreading of `predicate_edges.csv` baseline semantics — the one
   paragraph recommended in batch A §6 item 5 was not in the round packet and
   cost another wrong claim.
7. **Judge-standard tests generalized well**: the two-object drive (batch A §6
   item 2) decided phenomena 1/5 this round; the walk + drive pair (J1/J2) was
   sufficient to close every table-level and JVM-level conflict without any
   emulator. Keep both as the standing judge tests for batch C.

## 7. Files (judge outputs of record, sha256)

```
fecc43a12566cb8923d1257849c5358911d6e76f8842c49f417a80bd5fe54e23  juiz_walk_batchB.py
611adb6423d760227c439d5586cedf58ec9409dce937aaea48e6254327aa4968  juiz_walk_batchB_output.txt
a860983ce99434333f65d97a6891fc81d45c8cc61f962159afbb27f0a6f68d52  juiz_JuizDriveB.java
ac889f1a81f33d54afac76cfd70f5ac19bfbafbd56ce840090308cb2d12b90c5  juiz_driveB_rep1.txt
d3cfa3e6471d9015ca2ee5502a0c24e77c873f41460868a98e6652c04951a622  juiz_build_csv_batchB.py
b9126262de1abddf98349d7b4af80739d6bd80775f65074acc790ecb961cb35f  juiz_claims_resolvidos_batchB.csv
0209ec20623770ebcd348d4355f2038fbc071882811f77248a7fd402a9d001e2  juiz_rescore_batchB.py
13581232063eaa3f1cbf3ae7b7b2163be2b497d95db203432e9b3a750b192130  juiz_rescore_batchB_output.txt
```

- `juiz_driveB_rep1.txt` is rep 1 of 3; reps 2-3 are sha256-identical
  (`ac889f1a…`) — repetition policy satisfied.
- J2-B compile/run commands: monitors byte-identical to the manifest, compiled
  with `javac -cp rv-monitor-rt.jar:rvsec-core-0.9.3-SNAPSHOT.jar:rvsec-logger-csv-0.9.3-SNAPSHOT.jar`
  (hashes §0.1), run 3× from a scratch working dir.
- Agent primary files consulted: all `batchB/alfa_*`, `beta_*`, `gama_*`;
  `generation_manifest.md`; frozen specs/rules; `data/gh101/*`; production
  sources cited at file:line throughout.

*Next step per protocol §15: adversarial refutation round against this
synthesis; the judge's decision becomes final only after answering each
objection. The must-close set for G13 from this round: 38 critical claims
(12 phenomena) and every major finding, including the register-absence family.*

## 8. Final decision after the refutation round

2026-08-09. Issued after responding to each of the 5 objections of the
independent reviewer (`refutacao_parecer_batchB.md`), as protocol §15
requires — responses in `juiz_respostas_refutacao_batchB.md` (outcomes: **5
accepted** — 1 material, REF-C-02, remediated in rev. 2; 4 minor). The
reviewer independently re-executed J1-B (17/17, byte-identical), J2-B (3 reps,
sha `ac889f1a…` = mine) and the rescore (byte-identical), and reported no
objection reaching verdicts, scores or gates; the adjudication is nonetheless
mine, objection by objection, each re-verified before acting. Sections 1–7
above are the first synthesis (rev. 1) and remain as record; **where wording
or numbers diverge, this section prevails** — the basis is rev. 2 of
`juiz_claims_resolvidos_batchB.csv`.

### 8.1 Final per-spec verdicts and gates

Operative gate rule unchanged (REF-B-05): gates fail on their pre-registered
criteria; a critical INCORRETA/OMITIDA is one sufficient trigger among them.

| Spec | G2 | G3 | G4 | G5 | G7 | G9 | Verdict (covered scope) |
|---|---|---|---|---|---|---|---|
| CipherInputStreamSpec | PASS | FAIL | FAIL | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| CipherOutputStreamSpec | PASS | FAIL | FAIL | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| KeyPairSpec | PASS | FAIL | FAIL | PASS ¹ | FAIL | FAIL | **REPROVADA** |
| SecretKeySpec (SKY) | PASS | PASS | FAIL | FAIL ¹ | FAIL | FAIL | **REPROVADA** |
| PBEKeySpecSpec | PASS | FAIL | FAIL | PASS ¹ | FAIL | FAIL | **REPROVADA** |

¹ **G5 jar-scope annotation (REF-C-03 accepted)**: all G5 dexlib2 evidence was
measured over the frozen android-30 jar (`96ccfdc8…`), while the unmodified
production dexlib2 CLI resolves the platform jar by lexicographic maximum —
android-37.0 on the host, android-36 in Docker — and no rv-android call-site
passes `--android-jar` (`fase0/toolchain_ambiente.md:106-117`). The G5
**FAILs are jar-robust** (interface-with-no-declared-methods,
first-call-disjunct and INV-INS-66 are jar-independent mechanisms,
judge-verified at source); the two G5 **PASSes (KPR, PBK)** are pinned to
android-30 and carry the production-default jar divergence as a named
pendency. The admission decision of §5 (dexlib2 static measurements of the
production pipeline count as G5 evidence; ajc half and ART execution are
G6/G10 pendencies) is confirmed.

Grounds per gate are those of §5, unchanged. Scope statement: **G6 (weaving
end-to-end), G8 (differential/mutation) and G10 (Android execution) were not
executed this round** — they can only ADD defects; the five verdicts hold in
the covered scope G2/G3/G4/G5/G7/G9. `INCONCLUSIVE` never became approval:
the five inconclusive claims stay open as named pendencies (§8.4).

**Batch verdict line (final)**: 5/5 REPROVADA in the covered scope; per
protocol §16 the set cannot move toward `READY` from this batch. Cumulative
across the audit: 12/12 audited specs REPROVADA in their covered scopes.

### 8.2 Corrections of record absorbed from the refutation (rev. 1 → rev. 2)

| # | Change | Origin |
|---|---|---|
| 1 | Figure of record: **"5 severity-harmonization decisions covering 7 claims"** (BETA-CIS-06, BETA-COS-03, BETA-COS-10, BETA-SKY-05, BETA-PBK-05, BETA-PBK-06, GAMA-PBK-04) — rev. 1 §2.1/§3 said "6" | REF-C-01 (accepted); machine-diffed by me |
| 2 | CSV rev. 2: new judge column **`fenomeno_id_final`** (agent value where filed; judge backfill for the 7 blank FAIL rows — assignments in `juiz_respostas_refutacao_batchB.md` and `juiz_build_csv_batchB.py`); builder assert "no FAIL row without phenomenon"; rescore rev. 2 reads it and prints the reconciliation. Per-phenomenon table now matches the matrix by machine: FEN-SET-GENCIPHER-EXTRA **5**, FEN-PBK-RESIDUO **3**, FEN-CIS-CTOR1-OMITIDA **5**, FEN-CIS-LENOFF **6**; closing line "critical FAIL claims: 38; phenomena with ≥1 critical FAIL: 12". **All score tables byte-identical to rev. 1** (rev. 1 output archived verbatim in `refutacao_rescore_rerun_batchB.txt`) | REF-C-02 (accepted, material) |
| 3 | G5 jar-scope annotation of §8.1 (footnote ¹) added where the G5 verdicts live | REF-C-03 (accepted) |
| 4 | GAMA-SET-14 scoping: the SKY static-vs-dynamic mismatch direction is **conditional on the ajc half** (ALFA-SKY-07, INCONCLUSIVE) or on repair of FEN-SKY-ZERO-CAPTURA — on the measured production dexlib2 path the dynamic side captures nothing for SKY, so the mismatch there is "both views blind", not "dynamic sees, static doesn't". The mechanism FAIL (literal keying, no hierarchy resolution) stands unchanged | REF-C-04 (accepted) |
| 5 | **Provenance of the 12 critical phenomena** (generalized from the SKY-gate case; every entry re-verified against the `jca` twin bytes this session): inherited from `jca`, pre-gh101 — FEN-STREAMS-MONITOR-GLOBAL (`jca` CIS/COS also parameterless), FEN-COS-FLUSH (`jca:19,23`), FEN-KPR-CO-OPCIONAL (`jca:41` same ere), FEN-KPR-C1-SLICE-VAZIO (`jca:23` same unbound returning), FEN-SKY-GATE-SUPRESSAO (**`jca/SecretKeySpec.mop:25` same gate**), FEN-SKY-SEM-CANAL (`jca` twin also channel-less), FEN-PBK-SENHA-EXTRA (`jca:38,56`), FEN-PBK-RESIDUO (structural: conditions gate transitions in both sets; the delayed form is exposed by the gh101 star-prefix repair making the immediate pairing disappear), FEN-SKS-SURROGATE (constant predates the change). Introduced by gh101: FEN-SET-GENCIPHER-EXTRA (task 5.1, registered with the misstated api30 oracle). Toolchain (dexlib2, outside both spec sets): FEN-SET-FIRSTCALL-DISJUNCT, FEN-SKY-ZERO-CAPTURA. **Provenance routes G11/G13 accountability; it excuses nothing** — the oracle is the api30 rule and every inherited divergence left unregistered still fails its gate | REF-C-05 (accepted, generalized) |

No resolution, classification, severity of record (beyond the corrected
count), score, gate or verdict changed between rev. 1 and rev. 2.

### 8.3 Final scores (rev. 2 CSV; verbatim from `juiz_rescore_batchB.py` re-run)

Byte-identical to rev. 1 in every score table — the rev. 2 change is the
phenomenon linkage only. **Primary presentation: raw weighted sums
(D-batchA-1).**

| Unit | Raw weighted sum (of record) | Notes |
|---|---|---|
| CIS | **40.00** | INCOMPLETE — 1 INCONCLUSIVE outside denominator |
| COS | **34.17** | COMPLETE |
| KPR | **50.50** | INCOMPLETE — 1 INCONCLUSIVE |
| SKY | **47.50** | INCOMPLETE — 1 INCONCLUSIVE |
| PBK | **59.60** | COMPLETE |
| SET (separate, D-piloto-4) | **8.33** | 35 weight points unattainable (no ling/bind SET claims); labeled derived reading 8.33/65 = 12.82%; INCOMPLETE — 2 INCONCLUSIVE |
| Batch-B aggregate (context) | **40.87** | 113 spec claims, SET excluded; INCOMPLETE — 3 INCONCLUSIVE |

Claim totals: 133 = 40 PASS + 88 FAIL + 5 INCONCLUSIVE; **38 critical FAIL
claims across 12 critical phenomena** (now machine-reconciled — §8.2 item 2).
**Mandatory labels**: descriptive score ≠ probability of correction ≠ verdict;
never rounded to 100; no score opens a gate; CIS/KPR/SKY, SET and the
aggregate are INCOMPLETE; reprodutibilidade is 0/7 across the five specs.

### 8.4 Open pendencies (named)

- **ALFA-SKY-07** (INCONCLUSIVE): ajc `call()` matching of interface-typed
  receivers — decides both the SKY ajc capture half and the GAMA-SET-14
  mismatch direction (§8.2 item 4). G6.
- **BETA-SET-11** (INCONCLUSIVE): ajc weave + ART/device observational
  equivalence; `__LOC` under DEX; after-finally vs wrapper on exceptional
  returns (BETA-SET-08); container android-36 (REF-12, carried). G6/G10.
- **GAMA-CIS-06** (INCONCLUSIVE): subclass-`super()` construction
  realizability for the omitted 1-arg ctors.
- **GAMA-KPR-06** (INCONCLUSIVE): H-KPR-1 — the 668 historical KeyPairSpec
  lines vs the executed co?-FP; three named replay tests (micro-APK ajc+dexlib2,
  paired jca/jca_android replay, campaign-APK DEX inspection).
- **GAMA-SET-16** (INCONCLUSIVE): historical zero-emission of CIS/COS/SKY/PBK;
  same replay battery.
- **android-37.0 production-default divergence** (REF-C-03): the G5 PASSes
  (KPR, PBK) hold for android-30; re-measure under the production default jar
  or pin `--android-jar` in production before G6.
- **G10-SKY-1**: downstream RANDOMIZED-reader accusation chain (read, not
  driven end-to-end).
- **Researcher countersignature**: no researcher scope reduction is on file
  for any extra-oracle clause (generatedCipher subsystem, SKY gate, PBK
  password clause, SKS surrogate family) — pre_registro §7 requires explicit
  reduction, never silent acceptance.
- **G13 must-close set from this round**: the 38 critical claims (12
  phenomena, provenance table §8.2 item 5) and every major finding, including
  the register-absence family (GAMA-CIS-03, GAMA-COS-04, GAMA-KPR-07,
  GAMA-SKY-04, GAMA-PBK-06, ALFA-KPR-08, ALFA-SKY-06) and the census
  blind-spot pair (ALFA-SET-07).

### 8.5 Files of record for the round (rev. 2 hashes)

```
8f315c51a508ab63a4f47c9ce54c386038e9afda70cc33d3f05e03d85f5da58e  juiz_claims_resolvidos_batchB.csv   (rev. 2)
b0e4a95d9dc6218043e656e9479a209361eb56b357956299451235829ff554a4  juiz_build_csv_batchB.py            (rev. 2)
99d28589d22b05f91bec0f060953051b9680a6043867705df38235e44862e094  juiz_rescore_batchB.py              (rev. 2)
4c47ca14b23e8f29add6abe2a724f03b7ba049246388b64dde1568cb9f3cc05f  juiz_rescore_batchB_output.txt      (rev. 2)
fecc43a12566cb8923d1257849c5358911d6e76f8842c49f417a80bd5fe54e23  juiz_walk_batchB.py                 (unchanged)
611adb6423d760227c439d5586cedf58ec9409dce937aaea48e6254327aa4968  juiz_walk_batchB_output.txt         (unchanged)
a860983ce99434333f65d97a6891fc81d45c8cc61f962159afbb27f0a6f68d52  juiz_JuizDriveB.java                (unchanged)
ac889f1a81f33d54afac76cfd70f5ac19bfbafbd56ce840090308cb2d12b90c5  juiz_driveB_rep1.txt                (unchanged)
```

Plus `juiz_respostas_refutacao_batchB.md` (this round's responses). Rev. 1
hashes of the four revised files remain in §7; rev. 1 rescore output is
preserved verbatim inside `refutacao_rescore_rerun_batchB.txt`.

### 8.6 Decision

**Batch B is closed** with **CipherInputStreamSpec, CipherOutputStreamSpec,
KeyPairSpec, SecretKeySpec (target `javax.crypto.SecretKey`) and
PBEKeySpecSpec all REPROVADA in the covered scope (G2, G3, G4, G5, G7, G9)**
— five specs, twelve critical phenomena, thirty-eight critical claims, every
gate-deciding defect anchored in evidence executed by the judge (J1-B, J2-B)
or judge-verified at source/register, independently re-executed by the
refutation reviewer (J1-B byte-identical; J2-B 3 reps hash-identical; rescore
byte-identical). All five refutation objections were accepted and remediated
without any verdict, score or resolution moving. Per protocol §16 the set
cannot move toward `READY`; per pre_registro §7 no divergence was silently
accepted — the extra-oracle clause family awaits explicit researcher scope
reduction or repair. Observations carried to batch C: §6 items 1–7, plus
(from this refutation) the FEN-linkage builder assert as a standing rule and
the provenance column for critical phenomena.

**PROPOSED deviation text (for the researcher/orchestrator; NOT registered by
the judge — nothing was written to `fase0/`):**

> **D-batchB-1 (PROPOSED — phenomenon linkage is part of the resolved record)**:
> "Every claim resolved FAIL must carry a phenomenon ID in the judge's
> consolidated CSV (`fenomeno_id_final`: the agent's ID where filed, the
> judge's assignment otherwise), enforced by a build-time assert; the
> per-phenomenon table is generated only from that column. Origin: REF-C-02,
> batch B refutation round. Adopted from batch C onward; batch B rev. 2
> already follows it."

