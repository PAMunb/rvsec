# Adversarial refutation — batch B judge synthesis (CIS, COS, KPR, SKY, PBK)

Independent refutation reviewer, round "batch B" · 2026-08-09. Target:
`batchB/juiz_sintese_batchB.md`, `batchB/juiz_claims_resolvidos_batchB.csv` (133
claims), `batchB/juiz_rescore_batchB.py` + output. Everything below was
re-executed or re-read by me this session; auxiliary outputs:
`batchB/refutacao_rescore_rerun_batchB.txt`,
`batchB/refutacao_j1_j2_rerun_batchB.txt`. No agent/judge file was modified.

## 0. What I re-executed (baseline for every objection)

- **Rescore**: `juiz_rescore_batchB.py` re-run — output **byte-identical** to
  `juiz_rescore_batchB_output.txt`. Independent hand-recomputation of all five
  per-spec raw sums, the SET score (attainable 65, derived 12.82% labeled) and
  the aggregate (40.87) confirms the arithmetic.
- **J1-B**: `juiz_walk_batchB.py` re-run — internal freeze asserts passed (5/5
  monitor hashes = `generation_manifest.md`), output **byte-identical**, 17/17
  walk checks counted.
- **J2-B**: `juiz_JuizDriveB.java` recompiled from scratch against the round
  monitors (hash-verified) and the frozen jars (rv-monitor-rt `0fa65fbc…`,
  rvsec-core `7b4d72aa…`, rvsec-logger-csv `6787f411…`), run 3× from clean
  dirs — all three reps sha256 `ac889f1a…` = the published
  `juiz_driveB_rep1.txt`. The 17 recorded errors, the `expecting=unknown`
  lines, `isInAcceptingState(null)=true`, the SKY silences, and the PBK
  conformant-trace FP+residue are all real.
- **CSV integrity**: 133 rows = the exact union of the three agent CSVs
  (45+52+36); **zero** original agent cells altered; the four judge columns are
  strictly appended; position changes are exactly the 3 declared; the six-state
  classification convention holds in both the agent and the judge columns; the
  5 INCONCLUSIVE stayed INCONCLUSIVE (none converted); resolution totals
  40/88/5 and 38 critical FAILs confirmed by independent count.
- **Judge §0 spot-checks** (all confirmed at source/bytes, well beyond the six
  required): `WrapperEmitter.findFirstCall` first-disjunct-only (:517-524, with
  the corpus-assumption comment), `shouldWrap` = after (:161-163),
  `literalFallback` static-only (:475-498); `AndroidClassIndex.methods()`
  declared-only (:115-126) with hierarchy walk only in `isAssignableFrom`
  (:132-150); `DexWeaver` INV-INS-66 (:480-515) and APK-internal-only subtype
  expansion (:207-231); `ErrorDescription.equals/hashCode` over the summary
  with `expecting` excluded (:108-139) and 3-arg ctor `"unknown"` (:35-37);
  `ErrorCollector` `Set.add` dedupe; `RvsecAnalysisClient` literal
  `declaringClass#name` keying (:585-586, :628-630); `javax.crypto.SecretKey`
  in the frozen android-30 jar (`96ccfdc8…`) declares only `serialVersionUID` —
  verified by `javap` **over bytes I extracted from the jar** (not the JDK
  fallback); CIS/COS 1-arg ctors `protected`; `generatedCipher` 0/33 api30
  rules and no REQUIRES in CIS/COS/SecretKey rules; `len > off` untranscribed;
  `errors.csv` (sha `78023def…`) 668 KeyPairSpec lines, 668/668 with `unknown`,
  0 CIS/COS/PBK lines; divergence_record rows 2-3 and 83, README.md:17
  ("before the repairs … kept as authored"), edges row 64, conformance rows
  16/18/20, omissions rows 3/10/19/20, design.md:190, tasks.md 3b.4; SKY
  suppression prologue and empty `@match`/no `@fail` in the frozen artifact;
  KPR shadowed local and null-reading `Prop_1_handler_match`; COS rule ORDER
  `Constructs, Writes+, c` and alphabet without flush; `beta_weave_all.out`
  SKY 7/7 UNTOUCHED and `cis_readB`/`cos_writeB` UNTOUCHED with
  `plansSkippedAliasing=1`.
- **§7 hashes**: all 8 judge files match; agent evidence hash lists
  (alfa_report companion block, gama_report REF-B-01 block, beta_hashes.txt)
  spot-checked and matching (REF-B-01 satisfied).

## 1. Objections

### REF-C-01 — "6 severity harmonizations" is the wrong count: it is 7 claims (minor)

§2.1/§3 declare "6 severity harmonizations (§2.2)". Machine diff of
`severidade` → `severidade_final` over FAIL rows (excluding the two overturns,
whose agent severity was "-") yields **7** harmonized claims: BETA-COS-03,
BETA-SKY-05, BETA-PBK-06, GAMA-PBK-04, BETA-PBK-05, BETA-CIS-06, BETA-COS-10 —
exactly the claims §2.2's five rows themselves list. No reading of §2.2 gives
6 (5 rows, 7 claims). Each individual harmonization is well-grounded in
executed evidence and pre_registro §4 (I attacked each: BETA-COS-03 and
BETA-SKY-05 rest on executed FNs, J2c/J2g; BETA-PBK-06/GAMA-PBK-04 on the
J2h conformant-trace composition, which §4 covers — "FP demonstrable in a
realizable trace" does not require a single-defect trace; BETA-PBK-05 on the
batch A twin; BETA-CIS-06/COS-10 on the §4 OMITIDA-without-register trigger).
Severity does not enter the score, so nothing numeric moves.
**Resolves by**: correcting the figure to 7 claims (or "5 decisions, 7 claims")
in §2.1/§3.

### REF-C-02 — the published per-phenomenon counts contradict the matrix: 7 FAIL claims have no `fenomeno_id` and are invisible to the "corrective lens" (material)

Seven FAIL rows in the resolved CSV carry an **empty** `fenomeno_id`:
BETA-CIS-06, BETA-CIS-07, BETA-COS-07, BETA-COS-10, BETA-PBK-06, and the two
overturned criticals BETA-CIS-08, BETA-COS-09. `juiz_rescore_batchB.py`
silently skips empty IDs (`if not f: continue`), so the per-phenomenon block —
which §4 note (ii) explicitly tells the reader to use instead of claim counts —
**undercounts**:

- `FEN-SET-GENCIPHER-EXTRA`: printed as **3** claims; the matrix (row 2) and
  §3 adjudicate **5** (including both overturned criticals).
- `FEN-PBK-RESIDUO`: printed as **2**; §1 row 11 and §2.2 adjudicate
  **3 criticals** ("INCORRETA critical ×3" including BETA-PBK-06).
- `FEN-CIS-CTOR1-OMITIDA`/`FEN-CIS-LENOFF`: Beta's four claims
  (CIS-06/07, COS-07/10) are excluded, so both phenomena appear thinner than
  row 16 states.

The headline "38 critical claims across the 12 critical phenomena" is
arithmetically correct — my recount reconciles all 38 onto the 12 phenomena —
but only via the narrative assignment in §1/§2, which the machine-readable
record does not carry: §3 says "per-claim list in the CSV", and for 3 of the 38
criticals the CSV does not link the claim to any phenomenon. D-piloto-4 item 3
is the binding rule ("claims about the same phenomenon … cite a phenomenon
ID"); the agent omission was not repaired at resolution time and the published
table inherits it. This is a matrix-vs-annex contradiction in the sense of the
refutation mandate, though it moves no score and no verdict.
**Resolves by**: backfilling the phenomenon linkage for the 7 rows (a judge
column or an errata table is enough — the original agent cells must stay
untouched) and regenerating the per-phenomenon block, or an explicit caveat on
the block naming the 7 unlinked rows.

### REF-C-03 — the G5 admission does not restate that production dexlib2 would not select the measured jar (minor)

The G5 scope decision admits Beta's dexlib2 measurements as "static
measurements of the production pipeline … over the frozen android-30 jar".
`fase0/toolchain_ambiente.md:106-117` records that the production dexlib2 CLI
resolves `$ANDROID_HOME/platforms` by **lexicographic maximum** (android-37.0
on every recorded environment) and that **no rv-android call-site passes
`--android-jar`** — "Em nenhum dos ambientes o default é android-30". The G5
**FAILs are jar-robust** (SecretKey declares no methods at any API level;
first-call-disjunct and INV-INS-66 are jar-independent), but the two G5
**PASS** verdicts (KPR, PBK "capture exhaustive **on API 30**") are pinned to a
jar the production default would never load. The threat is registered in fase0,
so it is not undeclared for the audit as a whole — but the synthesis's G5
preamble, which is where the admission decision lives, does not carry it, and
the per-claim `ameaca` field says only "weave+device pendentes".
For the rest, the admission decision itself survives attack: pre_registro §3
names the production matcher against the real android.jar as the G5 evidence
class ("matcher de produção não executável" being the INCONCLUSIVE branch),
batch A fed G5 with exactly the same evidence class (capture matrices,
batchA §1 row 15), the ajc half and ART are named pendencies, and SKY's
G3 PASS / G5 FAIL is not a contradiction (language of the artifact vs capture
of the pipeline).
**Resolves by**: one sentence in the §5 G5 preamble naming the
android-37-default divergence as a pendency of the admitted evidence.

### REF-C-04 — GAMA-SET-14's consequence framing is not reconciled with BETA-SKY-02 (minor)

Row 20 closes GAMA-SET-14 ("sites **dynamically monitored** but statically
invisible") via the judge's source verification of the literal keying — the
mechanism is real and I re-verified it. But the framing's premise (the dynamic
side captures concrete-receiver `getEncoded`/`destroy` sites) is, for SKY on
the production **dexlib2** path, refuted by the same round's BETA-SKY-02
(spec entirely inert — 0 wrappers), and on ajc it is INCONCLUSIVE
(ALFA-SKY-07). As adjudicated, the static/dynamic mismatch that gives the
claim its G12 relevance is currently demonstrable on **no** measured
production path — it is conditional on the ajc pendency. The FAIL itself
stands (the keying defect exists regardless of the dynamic side), but the
resolution cites "lado dinamico (call() casa subtipos) coerente com
BETA-SET-04" without noting that rows 9 and 20 pull that premise in opposite
directions for SKY.
**Resolves by**: a scoping sentence in row 20 conditioning the mismatch
direction on the ajc half (named pendency), leaving the mechanism FAIL as is.

### REF-C-05 — provenance asymmetry: PBK's extra predicate is labeled "inherited from `jca`", SKY's gate is not (minor)

Row 10 records for FEN-PBK-SENHA-EXTRA: "inherited from `jca`, not a gh101
regression — still blocks". FEN-SKY-GATE-SUPRESSAO gets only "unregistered".
I checked the `jca` twin: `jca/SecretKeySpec.mop:25` carries the **same**
`GENERATED_KEY` condition gate — the SKY gate is equally inherited, and the
gh101 divergence register (row 83) records the *added* `d` event, not the gate,
so "unregistered" is literally true but the provenance note the judge gave PBK
is missing for SKY. Since G11/G13 will consume these rows to decide what gh101
must answer for, the asymmetry has downstream routing consequences (defect of
the derivation vs defect inherited by it).
**Resolves by**: adding the inheritance note to rows 7 and (if applicable after
the same check) 8; no verdict or severity changes.

## 2. Survival statements (areas attacked without result)

1. **Rescore/denominators/D-batchA-1**: re-run byte-identical; hand-recompute
   matches; per-spec excludes SET; INCONCLUSIVE outside every denominator; raw
   sums are the record; the only attainable-% is the labeled SET reading;
   "reprodutibilidade 0/7" matches the CSV (0/1,0/1,0/2+1INC,0/2,0/1) and
   "every spec ≥1 unregistered divergence" holds.
2. **Overturns**: all three are grounded in judge-executed or judge-verified
   evidence (grep 0/33 + no-REQUIRES + J2b for the two PASS→FAIL; README:17
   declared baseline semantics + batch A BETA-SET-07 precedent for the
   FAIL→PASS); Beta's mechanical facts were preserved, only the fidelity label
   flipped; no majority counting anywhere in the synthesis.
3. **Counterexamples**: every executed agent counterexample traced (35+ claims
   walked row-by-row across the three CSVs) is either confirmed, re-executed by
   the judge, or upgraded — none dropped, none dismissed without a
   discriminating test; the one structural-identity gap (GAMA-COS-01) was
   closed by direct execution (J2c), not by analogy.
4. **Classification convention**: six states everywhere; exactly 3
   classification changes = the 3 overturns; no OMITIDA/INCORRETA under PASS;
   no INCONCLUSIVE→PASS.
5. **Scope honesty**: G6/G8/G10 nowhere claimed as executed; all three agent
   reports carry the pendencies; absence-of-firing nowhere converted to
   acceptance (GAMA-SET-16 kept INCONCLUSIVE; silent-generator acceptances
   filed as defects); H-KPR-1 kept a hypothesis with GAMA-KPR-06 INCONCLUSIVE
   and outside the denominator; the H2 update is executed (J2h), correctly
   framed as delayed refutation for PBK only.
6. **Judge §0 self-verifications**: every spot-check I ran (see §0 above)
   confirmed the cited file:line and the cited fact, including the two
   batch A traps (javap JDK fallback avoided; register baseline semantics).
7. **REF-B-01/-05/-07/-09**: judge evidence in `batchB/` with matching hashes;
   gates fail on pre-registered criteria with multiple anchors each (no gate
   rests solely on a contested claim); routes counted, not agents; dimension-5
   coverage is multi-route for all five specs (Beta drives + Gama KPR/CIS
   executed; the one non-executed leg was declared and judge-closed).
8. **Walk/drive**: J1-B 17/17 and J2-B 3-rep determinism reproduce exactly on
   an independent compile; the JVM-vs-ART residue is covered by the declared
   covered-scope (monitor-plane) and the named G6/G10 pendencies.

## 3. Conclusion

Five objections: **0 blocking, 1 material (REF-C-02), 4 minor (REF-C-01,
REF-C-03, REF-C-04, REF-C-05)**. None reaches any per-spec verdict (each
REPROVADA is multiply anchored in evidence I independently re-executed), none
reaches any score (the rescore reproduces byte-identically and by independent
recomputation), and none reaches a gate outcome. REF-C-02 must be answered
because the published per-phenomenon table — the synthesis's own corrective
lens — contradicts the matrix for two critical phenomena; REF-C-01 is a wrong
count in the record; the other three are declaration/framing repairs. Per
protocol §15, the judge's decision becomes final after answering each
objection; on this evidence the 5/5 REPROVADA batch verdict line itself
withstands refutation.

## 4. Files written by this round

- `batchB/refutacao_parecer_batchB.md` (this report)
- `batchB/refutacao_rescore_rerun_batchB.txt` (rescore re-run, byte-identical)
- `batchB/refutacao_j1_j2_rerun_batchB.txt` (J1-B/J2-B re-execution log +
  independent evidence re-checks)
