# JUDGE — Responses to the batch B refutation round

Judge, 2026-08-09. Target objections: `batchB/refutacao_parecer_batchB.md`
(REF-C-01..05). Per protocol §15, one response per objection; the final
decision of the round is issued only after these responses, as
`juiz_sintese_batchB.md` §8. The reviewer's re-executions
(`refutacao_rescore_rerun_batchB.txt`, `refutacao_j1_j2_rerun_batchB.txt`)
were read; his conclusions are not adopted as grounds — every accepted point
below was re-verified by me before acting, and every action taken is listed.
No agent/refutation file was modified; no writes to `fase0/`.

## REF-C-01 — harmonization count ("6" vs 7 claims) — **ACCEPTED** (minor)

**Verification (mine)**: machine diff of `severidade` → `severidade_final`
over FAIL rows, overturns excluded, yields exactly 7 claims: BETA-CIS-06,
BETA-COS-03, BETA-COS-10, BETA-SKY-05, BETA-PBK-05, BETA-PBK-06, GAMA-PBK-04
— the same list §2.2's five rows enumerate. The rev. 1 figure "6 severity
harmonizations" was a wrong count of my own table (5 decisions, 7 claims).

**Adjudication**: accepted in full. No substance moves: each harmonization
stands on the grounds the reviewer himself attacked and found held (executed
FNs J2c/J2g; the J2h conformant-trace composition; the batch A twin
phenomenon; the §4 OMITIDA-without-register trigger). Severity does not enter
the score.

**Action**: the figure of record is corrected in §8.2 to **"5 harmonization
decisions covering 7 claims"**. Rev. 1 §2.2/§3 stand as record with §8
prevailing (batch A convention).

## REF-C-02 — 7 FAIL rows without `fenomeno_id`; published per-phenomenon table contradicts the matrix — **ACCEPTED** (material)

**Verification (mine)**: confirmed by machine — exactly 7 FAIL rows carried an
empty `fenomeno_id` (BETA-CIS-06, BETA-CIS-07, BETA-CIS-08, BETA-COS-07,
BETA-COS-09, BETA-COS-10, BETA-PBK-06), three of them critical; rev. 1
`juiz_rescore_batchB.py` skipped empty IDs, so the published block undercounted
FEN-SET-GENCIPHER-EXTRA (3 vs the matrix's 5), FEN-PBK-RESIDUO (2 vs 3),
FEN-CIS-CTOR1-OMITIDA (3 vs 5) and FEN-CIS-LENOFF (4 vs 6). The reviewer is
right that this violates the machine-readable intent of D-piloto-4 item 3: §3
pointed the reader at the CSV for the per-claim list, and for 3 of the 38
criticals the CSV carried no phenomenon linkage. The root cause is an agent
omission (Beta filed those rows without FEN ids) that I failed to repair at
resolution time — the narrative matrix carried the assignment, the record did
not.

**Adjudication**: accepted as material. It moves no score (phenomenon IDs do
not enter the weighted sums — re-verified: rev. 2 per-spec/SET/aggregate
numbers are byte-identical to rev. 1), no severity, no gate, no verdict — but
it was a genuine matrix-vs-annex contradiction in the published corrective
lens.

**Action (rev. 2, all re-run)**:

1. `juiz_build_csv_batchB.py` now appends a fifth judge column,
   **`fenomeno_id_final`**: the agent's own `fenomeno_id` where filed
   (original agent cells untouched — verified: 0 original cells altered), and
   the judge's assignment for the 7 blank FAIL rows:
   BETA-CIS-06 → FEN-CIS-CTOR1-OMITIDA; BETA-CIS-07 → FEN-CIS-LENOFF;
   BETA-CIS-08 → FEN-SET-GENCIPHER-EXTRA; BETA-COS-07 → FEN-CIS-LENOFF;
   BETA-COS-09 → FEN-SET-GENCIPHER-EXTRA; BETA-COS-10 → FEN-CIS-CTOR1-OMITIDA;
   BETA-PBK-06 → FEN-PBK-RESIDUO — exactly the assignments rev. 1 §1/§2 made
   narratively. A builder assert now fails the build if any FAIL row lacks a
   phenomenon.
2. `juiz_rescore_batchB.py` reads `fenomeno_id_final` (fallback to the agent
   column) and prints the unlinked-FAIL count plus the machine reconciliation
   line.
3. Re-run output (`juiz_rescore_batchB_output.txt`, rev. 2): "(FAIL rows
   without phenomenon linkage: 0)"; FEN-SET-GENCIPHER-EXTRA **5**,
   FEN-PBK-RESIDUO **3**, FEN-CIS-CTOR1-OMITIDA **5** (4 FAIL + 1 INC),
   FEN-CIS-LENOFF **6**; closing line "**critical FAIL claims: 38; phenomena
   with >=1 critical FAIL: 12**" — the headline now reconciles by machine, not
   narrative. All score tables byte-identical to rev. 1 (rev. 1 output remains
   archived verbatim inside `refutacao_rescore_rerun_batchB.txt`).

Rev. 1 → rev. 2 change table: §8.2 of the synthesis.

## REF-C-03 — G5 admission preamble omits the android-37.0 production default — **ACCEPTED** (minor)

**Verification (mine)**: `fase0/toolchain_ambiente.md:106-117` re-read: the
dexlib2 CLI resolves `$ANDROID_HOME/platforms` by lexicographic maximum
(host: `android-37.0`; Docker: `android-36`), no rv-android call-site passes
`--android-jar`, and "Em nenhum dos ambientes o default é android-30". Beta's
G5 measurements used the frozen android-30 jar.

**Adjudication**: accepted as a declaration gap at the place where the
admission decision lives. The reviewer's own analysis is adopted after
checking it: the G5 **FAILs are jar-robust** (SecretKey declares no methods at
any API level in the modeled world; first-call-disjunct and INV-INS-66 are
jar-independent mechanisms — all judge-verified at source in §0.4), so no FAIL
weakens; but the two G5 **PASS** verdicts (KPR, PBK — "capture exhaustive on
API 30") are pinned to a jar the unmodified production default would never
load. The admission decision itself stands (same evidence class batch A used
for G5; the pre-registered INCONCLUSIVE branch is "matcher de produção não
executável", which is not the case here).

**Action**: §8.1 carries the pendency sentence exactly where the G5 verdicts
live: the KPR/PBK G5 PASS and the CIS/COS/SKY G5 FAIL are all annotated
"measured over frozen android-30; the unmodified production dexlib2 default
resolves android-37.0/android-36 (fase0 register) — jar-sensitivity is a
named pendency for the PASSes, and jar-robustness is stated for the FAILs".
Added to the open-pendencies list (§8.4).

## REF-C-04 — GAMA-SET-14 framing unreconciled with BETA-SKY-02 — **ACCEPTED** (minor)

**Verification (mine)**: rev. 1 row 20 indeed closes GAMA-SET-14 citing the
dynamic side ("call() casa subtipos, coerente com BETA-SET-04") while row 9
establishes that for SKY the production dexlib2 dynamic side captures
**nothing** (BETA-SKY-02, judge-verified), and the ajc side is INCONCLUSIVE
(ALFA-SKY-07). The premise "dynamically monitored but statically invisible"
is therefore currently demonstrable on no measured production path for SKY.

**Adjudication**: accepted as a scoping repair. The claim's FAIL stands
unchanged — the mechanism (literal `declaringClass#name` keying, no hierarchy
resolution, `RvsecAnalysisClient:585-586, 628-630`) is a defect of the static
path regardless of what the dynamic side does; on general (non-interface)
targets BETA-SET-04's static-type semantics make the two views mismatched in
the opposite direction as well. What changes is the conditionality of the
specific SKY static-vs-dynamic mismatch: it materializes only if the ajc half
captures interface-typed receivers (named pendency), or if the dexlib2
interface defect (FEN-SKY-ZERO-CAPTURA) is repaired.

**Action**: scoping sentence recorded in §8.2; GAMA-SET-14 resolution,
classification (INCORRETA), severity (major) and dimension unchanged; the CSV
justification already cites BETA-SET-04 coherence and is left as filed, with
§8 prevailing on the conditionality.

## REF-C-05 — provenance asymmetry (SKY gate inherited, note missing) — **ACCEPTED** (minor)

**Verification (mine)**: `jca/SecretKeySpec.mop:25` carries the **same**
`condition(validate(Property.GENERATED_KEY, secretKey))` gate — re-read by me
this session; the jca twin is also channel-less (`ere : e1*`, no `@fail`,
`@match` only). I extended the check to the whole batch, because the routing
consequence the reviewer names (what gh101 must answer for at G11/G13) applies
batch-wide: parameterless CIS/COS (`jca/*.mop:11`), COS `fl` in the loop
(`jca/CipherOutputStreamSpec.mop:19,23`), KPR mandatory-c1 `ere` and
`returning(KeyPair kp)` unbound (`jca/KeyPairSpec.mop:23,41`) are all present
in the `jca` twins too — inherited, pre-gh101. The batch's only critical
phenomenon *introduced by* gh101 is the generatedCipher subsystem
(FEN-SET-GENCIPHER-EXTRA, added by task 5.1 and registered with the misstated
oracle); FEN-SKS-SURROGATE's writer is likewise inherited (the constant
predates the change; edges:64 records it as surrogate).

**Adjudication**: accepted, and generalized: a one-note repair for rows 7-8
would have left the same asymmetry elsewhere.

**Action**: §8.2 carries a compact provenance table over the 12 critical
phenomena (inherited-from-jca vs introduced-by-gh101 vs toolchain), each entry
verified against the `jca` twin bytes this session. No verdict, severity or
classification changes — provenance routes accountability, it does not excuse
the derived set (the audit's oracle is the api30 rule, and gh101's stated
purpose was conformance to it; an inherited divergence left unrepaired and
unregistered still fails its gate).

## Outcome summary

5 objections: **5 accepted** (1 material — REF-C-02 — remediated in rev. 2;
4 minor — figure correction, two declaration/scoping repairs, one provenance
generalization). No objection reached a resolution, a severity of record
beyond the corrected count, a score, a gate or a verdict — consistent with the
reviewer's own conclusion, but established here by my re-verification, not by
adopting his. The final decision of the round is `juiz_sintese_batchB.md` §8.

Files touched by this round (all `juiz_`-prefixed): this document;
`juiz_claims_resolvidos_batchB.csv` (rev. 2, +`fenomeno_id_final`);
`juiz_build_csv_batchB.py` (rev. 2); `juiz_rescore_batchB.py` (rev. 2);
`juiz_rescore_batchB_output.txt` (rev. 2 — rev. 1 output preserved verbatim in
`refutacao_rescore_rerun_batchB.txt`); `juiz_sintese_batchB.md` (§8 appended).
Hashes in §8.5.
