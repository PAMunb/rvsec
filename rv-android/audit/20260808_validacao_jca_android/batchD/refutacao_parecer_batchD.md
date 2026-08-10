# REFUTATION — batch D judge synthesis (MAC, MDG, KPG, SRD, SIG) — final batch

Independent adversarial refutation reviewer, round "batch D", 2026-08-09.
Target: `batchD/juiz_sintese_batchD.md` (sha `ceac8799…`),
`juiz_claims_resolvidos_batchD.csv` (sha `4b2269ab…`, 123 claims),
`juiz_rescore_batchD.py` + output. Method: everything re-executed or re-read
from primary sources; no agent/judge file modified; refuter evidence in
`refutacao_reruns_batchD.txt`, `refutacao_javap_trap_batchD.txt`,
`refutacao_rescore_rerun_batchD.txt`. Binding rules applied as frozen:
`fase0/pre_registro.md` §3/§4/§6, `fase0/desvios.md` D-piloto-1..4, D-batchA-1,
D-batchB-1, D-batchC-1; batch C rev. 2 rulings REF-D-02/03/04; protocol §15/§16.

## 0. What was independently re-executed (summary; details in refutacao_reruns_batchD.txt)

- **Rescore**: re-run byte-identical; every table, denominator, weighted sum,
  derived-% and the COMPLETE/INCOMPLETE labels re-derived with my own code —
  exact. 123 = 39 PASS / 81 FAIL / 3 INCONCLUSIVE; **54 critical FAIL claims,
  21 phenomena with ≥1 critical, 34 FEN groups** — all reconfirmed
  independently of the judge's script.
- **Builder**: re-run in scratch, output CSV **byte-identical** to the record;
  the ALFA-SRD-08 parse-time repair verified content-preserving (122 rows
  exact-match on all 14 original columns; the split field re-joins to
  `args(alg,*)` exactly); repair declared in builder and synthesis §7; the
  D-batchB-1 assert is present and passing.
- **J1-D walk**: re-run, exit 0, 46/46, output byte-identical.
- **J2-D drive**: five frozen monitors independently recompiled (javac exit 0
  — the G2 standalone-compile claim verified) and the drive re-run: output
  sha `e136cf4c…` = all three published reps. D1–D9 all reproduced.
- **javap**: all §0.5 member facts re-derived from unzip-extracted android-30
  bytes — all correct.
- **Sources**: every decisive file:line in §0.2 re-read and confirmed
  (MacSpec f3 unbound `target(m)` :176-179 with formals `(byte[],int)` only;
  i1/i2 GENERATED_KEY conditions; SRD `end` block missing `next2` while `init`
  has it; c3 body `sr = r;` only vs the :136-139 comment — divergence real;
  KPG `String algorithm;` uninitialized, `switch(algorithm)` :28-35,
  `initError` on `initialize(int)` only, `gen` disjunct :123, ere, no
  `__RESET`; SIG `byte`-typed sign pointcuts beside `returning(byte[])`;
  MDG 9-entry folded guard). `__RESET` census 4-vs-0 confirmed at both levels.
- **Raw rules**: hashes = manifest; Mac REQUIRES without generatedKey +
  g1=g2 duplicate + arithmetic constraints; SecureRandom `ne = next(numB)`
  (protected on platform) + `randomized[numB]`; Signature `verified[sign]`;
  MDG 6-literal set with MD5/SHA-1/SHA-224 — all as the judge states.
- **Registers**: predicate_edges rows :47/:74-75/:81 as cited; README:148-153
  anchor declaration and its falsified invariance premise confirmed against
  the raw rules; divergence_record rows located; absence greps 0-hit;
  D-S14 capability-absent rows (predicate_omissions:14-17 + spec Group-5
  comment) — the BETA-KPG-05 overturn ground exists.
- **REF-D-04 grep**: re-run; SRD g2/g4 varargs instances confirmed; the
  `|| call(` sweep over `jca_android` returns **exactly** KPG:123, CIS:28,
  COS:27 — the new cross-round finding is accurate and exhaustive, and it is
  routed (§6.7), not re-adjudicated.
- **jca twins**: 5 provenance rows spot-checked (see REF-E-06 for wording).
- **Traceability**: all 123 agent claims present; **0** dropped
  counterexamples; **0** PASS→FAIL; the only flips are the two declared
  overturns; the 3 INCONCLUSIVEs are all agent-filed, none converted; no
  resolution uses agent counting (justificativas cite executed/source
  anchors; ~25 spot-read).
- **Fail-open sweep** (D-batchC-1): every fail-open-shaped FAIL row in the
  CSV (ALFA-MAC-02, ALFA-SIG-01, BETA-SET-04, GAMA-MAC-03, GAMA-KPG-01) is at
  crítica. None left at major.
- **REF-D-03 check** (§2.8): re-verified against the five rules' EVENTS/ORDER
  — every event is covered by an ordered aggregate; no batch D claim depends
  on the INCONCLUSIVE placement choice.
- **Gate consistency**: SIG G4 PASS is consistent with the claim table (SIG
  bindings 4/4 PASS; GAMA-SIG-04 is filed under predicados and lands in G7,
  which FAILs); MDG G7 PASS consistent (pred 1/1; the arithmetic-constraint
  FAIL is filed under bindings → G4 FAIL). KPG-NPE realizability closed by
  measurement, not assumption (kpg_gi2p NEITHER in the conferred capture
  matrix supplies the invisible-creation route D1 simulates).

## 1. Objections

### REF-E-01 (material) — Alfa's "android30" javap artifact is host-JDK output; a false platform assertion inside a CONFIRMADO claim is left unflagged

**Evidence** (`refutacao_javap_trap_batchD.txt`, all executed):
`alfa_javap_android30_batchD.txt:116-118` lists
`getInstance(String, SecureRandomParameters[, String|Provider])`, but the
type `java.security.SecureRandomParameters` **does not exist anywhere in the
frozen android-30 jar** (`unzip -l` 0 hits; javap over the extracted
`SecureRandom.class` shows exactly 3 getInstance overloads); the file's Mac
section lists `sun.security.util.Debug` private fields that the android-30
stub `Mac.class` does not have. The trap reproduces exactly:
`javap -classpath android.jar java.security.SecureRandom` returns the **host
JDK** class (6 SecureRandomParameters hits) because system classes shadow the
classpath. So the artifact is host-JDK content mislabeled android-30 — the
precise "JDK-fallback trap" the judge's own §0.5 names and avoids for his own
facts. Consequences: (i) ALFA-SRD-08's `evidencia_primaria` asserts
"getInstance(String,SecureRandomParameters[,String|Provider]) exist on
android-30" — **false** — and its projected 3-arg FP surface is vacuous on
the frozen platform; the judge resolved the claim CONFIRMADO on independent
and sound grounds (g4 arity, executed born-at-consume FP) but did not flag
the false sub-assertion; (ii) the synthesis nowhere declares the artifact
contamination, leaving a mislabeled evidence file in the record for future
phases (an undeclared threat under §15's "ameaças à validade").
**Reach**: no verdict, no score, no gate — every decisive member fact was
re-derived by the judge from extracted bytes and re-verified by me; the
claim's operative mechanism is independent. **Resolves by**: a scope note in
the judge's responses declaring `alfa_javap_android30_batchD.txt` host-JDK
contaminated (unusable as android-30 evidence), and scoping ALFA-SRD-08's
3-arg sub-claim as host-JDK-only/vacuous on android-30.

### REF-E-02 (minor) — Matrix row 11 miscounts Gama's filed positions

§1 #11 (FEN-C-EMPTY-LABEL) Gama cell reads "FAIL crit ×3 + major"; the CSV
has Gama filed crítica ×2 (GAMA-SET-27, GAMA-SIG-02) + major ×2 (GAMA-MAC-04,
GAMA-MDG-02). The per-phenomenon table (5 FAIL, 3 critical) and all
resolutions are correct; the matrix cell is not. **Resolves by**: correcting
the cell.

### REF-E-03 (minor) — Undeclared within-phenomenon severity asymmetry in FEN-C-EMPTY-LABEL

In FEN-C-GETS-INVISIVEL and FEN-C-CARRIER-SEQFAIL the judge harmonized family
members upward to crítica and explicitly argued the one exception (SRD). In
FEN-C-EMPTY-LABEL, ALFA-SET-14 was upgraded "aligned with GAMA-SET-27" while
GAMA-MAC-04 and GAMA-MDG-02 (same executed mechanism, per-spec) stay major
with no recorded rationale for the asymmetry. Severity moves no score, and
the phenomenon is already critical via 3 claims, so nothing reaches a gate.
**Resolves by**: one recorded line (e.g., per-spec empty-label rows held at
§4's "diagnóstico inatribuível" = major, family criticality carried by the
SET/SIG rows) or harmonization.

### REF-E-04 (minor) — "Generation determinism 20/20" vs "19/19": two numbers for one fact

§1 #19 says "generation determinism 20/20"; §3's FIDELIDADE highlights say
"19/19 byte-identical regeneration"; Beta's report claims "All 19 artifacts"
while `beta_hashes.txt`'s regeneration section lists **20** artifacts matching
the manifest. The judge repeats both numbers without reconciling them or
naming the excluded artifact. The judge's own freeze check (20/20 vs
manifest) is real — I re-hashed it — and G2 does not rest on the regeneration
count, so no gate moves. **Resolves by**: one sentence fixing the
denominator (which artifact, if any, was outside Beta's regeneration
comparison) and aligning §1 #19 with §3.

### REF-E-05 (minor) — "major-pending" not machine-recorded for ALFA-MAC-12

The synthesis and §2.2 place ALFA-MAC-12 at **major-pending** (REF-D-02,
Android-BC probe decides a return to crítica in the global phase), but the
CSV's `severidade_final` records plain "major"; the pending status lives only
in free text (`justificativa_curta`). A mechanical G13/global-phase sweep
over the severity column would lose the trigger. **Resolves by**: recording
`major-pending` (or a pendency flag) in the severity column, as the batch C
rev. 2 record did for the KGN alias line, or declaring the free-text
convention.

### REF-E-06 (minor) — Provenance wording overstates textual identity in two rows

§3 provenance: FEN-KPG-NPE "twin validate identical" — the jca twin's
`validate` has extra cases (`3072`, `"DiffieHellman"`); the NPE mechanism
(switch on the creation-initialized field) is identical, the text is not.
FEN-MAC-F3-UNBOUND "twin f2 byte-same" — the pointcut/args/target header is
byte-same (and it carries the unbound `target(m)`), but the bodies differ
(jca_android adds the ENCRYPTED check + marking). Mechanism-level provenance
holds in both; the wording should scope to it. **Resolves by**: two wording
fixes ("mechanism-identical" / "header byte-same").

### REF-E-07 (minor) — Aggregate line's empty dimension breaks D-batchA-1 symmetry

The context-only aggregate prints "repr 0.00 (0/0)" — an empty dimension
contributing 0.00 inside the raw sum with no unattainable-weight statement —
while per-unit scoring excludes empty dimensions and states their weight
(D-batchA-1). Since the aggregate is labeled context-only and no score of
record is affected, this is presentational. **Resolves by**: printing the
aggregate's unattainable weight (repr 5) like the per-unit lines.

### REF-E-08 (minor) — BETA-SET-07 is host-executable; the pendency framing should say so

Keeping BETA-SET-07 INCONCLUSIVE honors the freeze (all batch D member
matching is android-30-pinned by fase0 decision) and closed-round discipline.
But unlike BETA-SET-06 (device) and GAMA-SRD-02 (device replay), the
android-37.0 jar sits on the frozen host toolchain list — the discriminating
weave needs no emulator. The synthesis names the pendency (§6.7) without
noting it is executable off-device. **Resolves by**: marking BETA-SET-07 as
host-executable in the global-phase battery so it is not deferred as if it
required ART.

## 2. Survival statements (areas that withstood attack)

1. **Rescore, builder, walk, drive**: all four re-executed; byte-identical;
   every count and sum re-derived independently — the arithmetic record is
   exact (54 / 21 / 34; 39-81-3; 17 severity decisions; 2 overturns; 0
   PASS→FAIL).
2. **The CSV repair**: content-preserving, assert-guarded, declared —
   verified field-by-field against all three agent CSVs.
3. **Both overturns**: grounded in artifact/register evidence I re-verified
   (MDG merged-advice order in the batch D `.aj`; D-S14 capability-absent
   rows + Group-5 comment), not in votes; the batch C precedents transfer.
4. **D-batchC-1**: fully honored — every fail-open-shaped FAIL is at crítica.
5. **REF-D-02**: honored in both directions (MAC aliases throw → major-pending;
   MDG folding witnesses resolve on a measured platform → crítica stands); no
   other critical rests on an unrealizable enabling trace — the NPE route's
   realizability is closed by the measured kpg_gi2p NEITHER row.
6. **Gate placements**: KPG NPE under G4 is a declared a-fortiori extension of
   the pre-registered "condition inalcançável" criterion with G5 as enabling
   route — defensible, not a misapplication; SIG G4 PASS and MDG G7 PASS are
   consistent with the claim table; G2 PASS backed by my own javac exit 0 on
   all five.
7. **The register-anchor finding (#14)**: README:148-153 declaration and its
   falsification by ≥3 rows verified against the raw rules — correctly
   confirmed *with scope* rather than treated as a BETA-SET-06 repeat.
8. **The cross-round CIS/COS first-disjunct finding**: grep re-run, accurate,
   exhaustive, and routed to the global phase without reopening batch B.
9. **Scope honesty**: G6/G8/G10 declared unexecuted; H2/H4 closures framed as
   artifact-mechanism closures with historical attribution deferred; H-SRD-1
   held as hypothesis (INCONCLUSIVE); provenance table present (REF-C-05)
   and mechanism-accurate.
10. **Set-level routing (§6)**: RANDOMIZED object/material split, `-merge`
    budget closure, descriptor lint list, fail-crash sweep and G13 must-close
    set all stated as inputs to the next phase, none silently re-adjudicating
    closed rounds.
11. **markAsMaced(null) in f3** — probed as a candidate missed defect;
    it is the deferred-marking design (direct-input branch guarded), covered
    by ALFA-MAC-08's PASS; no ignored counterexample.

## 3. Conclusion

Eight objections: **0 blocking, 1 material (REF-E-01), 7 minor**. None
reaches any of the five REPROVADA verdicts, any gate outcome, any score, or
the critical-phenomena inventory: the material objection concerns evidence
hygiene (a host-JDK-contaminated javap artifact and one false sub-assertion
inside an otherwise sound claim), and every decisive fact it touches was
independently re-derived from extracted android-30 bytes by the judge and
re-verified by me. The judge may issue the final batch D decision after
answering the objections; REF-E-01 and REF-E-05 should produce record
corrections (a declared contamination note; a machine-readable pending
marker) before the record feeds the set-level and global phases.
