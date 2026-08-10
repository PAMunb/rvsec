# JUDGE — Responses to the batch-A refutation round

Judge, 2026-08-09. Target of the refutation: `juiz_sintese_batchA.md` (rev. 1),
`juiz_claims_resolvidos_batchA.csv` (rev. 1), `juiz_rescore_batchA.py`. Source:
`batchA/refutacao_parecer_batchA.md` (+ `refutacao_rescore_rerun.txt`,
`refutacao_j1_j2_j3_rerun.txt`). Per protocol §15, one response per objection;
the final decision (`juiz_sintese_batchA.md` §8) is issued only after these.
Each objection was adjudicated on its merits against the parecer's own text —
not against the coordinator's summary.

| Objection | Outcome | Action |
|---|---|---|
| REF-B-01 replication gap | **ACCEPTED** | 12 `juiz_*` evidence files copied into `batchA/`, hashed below |
| REF-B-02 unregistered score presentation | **ACCEPTED (partially, on intent)** | primary presentation reverted to raw sums; normalized demoted to labeled derived reading; deviation **D-batchA-1 PROPOSED** (text in §8.5, not registered by me) |
| REF-B-03 GAMA-SKS-02 contradiction | **ACCEPTED** | severity minor→major (CSV rev. 2); enters G13 must-close |
| REF-B-04 HMC "G5 FAIL*" hybrid | **ACCEPTED** | HMC G5 → PASS (vacuous), vacuity carried by the oracle-bias register; verdict unchanged |
| REF-B-05 §5 preamble misstates gate rule | **ACCEPTED** | corrected in §8.1: gates fail by their §3/§16 criteria; critical INCORRETA/OMITIDA is one sufficient trigger |
| REF-B-06 GAMA-IVP-03 scope qualifier | **ACCEPTED** | state label amended "(provado em JVM, ART pendente G10)" (CSV rev. 2) |
| REF-B-07 routes-vs-agents rhetoric | **ACCEPTED (rhetoric)** | wording corrected in §8; resolutions unchanged (load-bearing routes were executed) |
| REF-B-08 "DOCUMENTADA" provenance | **ACCEPTED** | ALFA-HMC-02 label amended "documentada NESTA RODADA, a referendar pelo pesquisador" (CSV rev. 2) |
| REF-B-09 dimension-5 single-route gap | **ACCEPTED** | gap declared in §8.4; standing two-object test carried to next batches |

No objection reached the five REPROVADA verdicts or any raw score — a conclusion
the reviewer stated and this judge re-derived independently below (the three
material objections were checked for verdict/score reach one by one).

## REF-B-01 — Judge evidence only in ephemeral scratch (material) — ACCEPTED

The objection is factually correct and the fault is mine: `pre_registro.md` §8
places the replication package under `audit/…`, and rev. 1 §7 explicitly declared
the judge scratch ephemeral. The reviewer's independent re-execution
(`refutacao_j1_j2_j3_rerun.txt`) mitigated but does not substitute my own
artifacts. **Remediation executed** — files now in `batchA/` (sha256):

```
284260c782b35b51155977a01f262ad4161068d8740c29e396c544ebb6738fd8  juiz_walk.py            (J1; now takes the gen_* base dir as argv[1] so it replays from regenerated artifacts)
8261d48d8a0f0b6636e9373c586c8bcfb8c737a4cf229d3a2b99d63306b109f8  juiz_walk_output.txt    (J1 full output, ALL PASS)
ebe70ab0ed5984c569738b9ace7a801c7bb891908dd8d76204c3f137ca8ee31c  juiz_JuizDrive.java     (J2 source, package mop)
6dce5236a9ba768a2620ab2cf0fcb6e6a57a86432832b6e797573e6910c985a4  juiz_drive_output.txt   (J2, 3 identical reps)
b18503a07b2aa4e62f778a8f38c3811f1b13710ba9765f5a462744a9d8a86e17  juiz_JuizHmc.java       (J3 source)
561eba933b8e0fcb7c1cf541b606eac559da8bc754b26b7da0227711e5c86d5a  juiz_hmc_output.txt     (J3, 3 identical reps)
bee7f370d2d0b4ddcc737c69777efd8626c85f311c7b21e2d07ad45902376d9f  juiz_gen_kpg_KeyPairGeneratorSpec.rvm
e187009c989a5bbaf64967bc7c0e51daf2a676eceb97f93bd81f7a0ddf634c5a  juiz_gen_kpg_KeyPairGeneratorSpecMonitorAspect.aj
0ee58e37d516943aa376742f0215aa331388abc8cac4759c2d486d0a2c63d47d  juiz_gen_kpg_KeyPairGeneratorSpecMonitorAspect.json
9bc45d18a63ae019937b4b1f7f5cbbaea32f6ae6169207064d4fa8d510c85bdf  juiz_gen_kpg_KeyPairGeneratorSpecRuntimeMonitor.java
dca2ce5edf77848962ce1b32d6d80d806de96dee3a7f4bff0adc55b43c697907  juiz_build_csv.py       (mechanical builder of the consolidated claims CSV)
```

Replication record for `juiz_gen_kpg_*` (generated in judge scratch, frozen
toolchain of `fase0/toolchain_ambiente.md`): input
`jca_android/KeyPairGeneratorSpec.mop`, sha256
`9a2628406a78dd7f3983c5ed352379eb0b9ac0dc6c7379adc05c53000f5ac994` (byte-identical
to the spec tree — verified at copy time and re-verified at publication);
commands: `javamop -d out -merge --emit-descriptor specs/KeyPairGeneratorSpec.mop`;
`mv specs/*.rvm out/`; `rv-monitor -d out -merge out/KeyPairGeneratorSpec.rvm`.
Compile/run for J2/J3:
`javac -cp rvsec-core.jar:rvsec-logger-csv-0.9.3-SNAPSHOT.jar:rv-monitor-rt.jar -d classes
DHGenParameterSpecSpecRuntimeMonitor.java HMACParameterSpecSpecRuntimeMonitor.java
juiz_gen_kpg_KeyPairGeneratorSpecRuntimeMonitor.java juiz_JuizDrive.java juiz_JuizHmc.java`
then `java -cp classes:<same jars> mop.JuizDrive` / `mop.JuizHmc` (×3). Jar hashes
as in `beta_hashes.txt` (`rvsec-core 7b4d72aa…`, `rvsec-logger-csv 6787f411…`,
`rv-monitor-rt 0fa65fbc…`), re-confirmed by the reviewer's rerun.

## REF-B-02 — Unregistered attainable-weight convention (material) — ACCEPTED (partially, on intent)

Accepted on substance: normalizing over the attainable weight is a
cross-dimension aggregation rule that `pre_registro.md` §6 does not define, the
pilot script does not use, and rev. 1 adopted after seeing which dimensions
lacked claims. That is the pattern pre-registration exists to prevent, whatever
the motive. Partially accepted only in this respect: the convention was not
*silent* (rev. 1 printed both numbers and the attainable weight next to every
total), and the direction of "favorability" is not one-sided — it also makes
explicit that HMC's 32.50 is over 95, information the pilot presentation hides.
**Action**: `juiz_rescore_batchA.py` now prints the raw weighted sum as
"PRIMARY (pre-registered presentation)" and the percentage only as a
"derived reading (unregistered…)" tied to a **PROPOSED** deviation; §8.3 of the
synthesis publishes raw sums as the scores of record. Proposed text for
`fase0/desvios.md` is in synthesis §8.5, clearly marked PROPOSED — this judge
does not write to `fase0/` (the orchestrator/researcher registers deviations).
Raw inputs and every subscore are unchanged (re-run verified).

## REF-B-03 — GAMA-SKS-02 severity vs my own classification text (material) — ACCEPTED

The reviewer catches a real internal contradiction: my `classificacao_final`
said "atribuição por cláusula impossível" while `severidade_final` stayed minor
on the mitigant "atribuível a spec+sítio" — and §4 of the pre-registration draws
the minor/major line exactly at attributability ("mensagem subótima, **porém
atribuível**" vs "diagnóstico inatribuível"). SKS's G9 was failed on that same
criterion, and I had already harmonized GAMA-SET-08 upward on the identical
principle (claim severity follows the adjudicated phenomenon). Keeping both
readings was not available to me. Of the two resolutions the reviewer offers, the
first is correct: the record genuinely cannot be attributed to *clause*
(membership vs RANDOMIZED vs length) without re-deriving the inputs — that is
clause-level inattributability, which is what dimension 6 of the semantic model
audits. **Action**: GAMA-SKS-02 raised to **major** (CSV rev. 2); spec+site
attributability stays recorded as a mitigant, not a downgrade; the defect now
sits in the G13 must-close set, where the reviewer correctly notes it must be.
No score effect (severity does not enter the score); SKS verdict unchanged
(REPROVADA via G4/G7 criticals regardless).

## REF-B-04 — HMC "G5 FAIL*" hybrid state (minor) — ACCEPTED

Both prongs are right. Gate vocabulary is PASS/FAIL; "FAIL*" was an unregistered
hybrid doing exactly the work the asterisk concealed. And under the
pre-registered capture criterion, `Esperado(platform) = ∅` satisfies
`Esperado ⊆ Capturado` vacuously — the pre-registration (§1) mandates that
oracle-inherited bias be *registered*, not converted into a spec-side gate
failure. **Action**: HMC **G5 → PASS (vacuous)** in the final gate table (§8.1),
with the vacuity carried where phenomenon 4 already put it: the oracle-bias
register (ALFA-SET-03 / ALFA-HMC-02, unchanged as FAIL claims — they assert the
oracle-profile defect and the spec's platform vacuity, not a capture-criterion
violation; the capture subscore is likewise untouched, since claims keep their
creation dimension per D-piloto-4). Verdict unaffected: HMC remains REPROVADA on
G3/G4/G7/G9, all executed evidence.

## REF-B-05 — §5 preamble states a sufficient condition as the standard (minor) — ACCEPTED

Correct, and the reviewer's reading test is fair: a literal application of the
rev. 1 preamble would pass IVP's G9 and approve IVP, which would be wrong under
the criteria actually applied (pre_registro §3 diagnostics row: FAIL on
"`unknown`" / "atribuição ambígua"; protocol §16 G9). **Action**: §8.1 states the
operative rule — *a gate fails when its pre-registered §3/§16 criteria are met;
a critical INCORRETA/OMITIDA inside the gate is one sufficient trigger among
them* — and marks the three gates failed on non-critical claims (IVP G9 major,
PBE G9 major, SKS G9 now major after REF-B-03). Rev. 1 §5 stays as record;
§8 prevails (pilot precedent).

## REF-B-06 — GAMA-IVP-03 label lacks the JVM scope qualifier (minor) — ACCEPTED

The conversion stands (the reviewer verified the two in-round harnesses), but he
is right that Gama's INCONCLUSIVE hinged expressly on ART and that §3.7 ("never
convert unknown into success") wants the scope *in the state label*, not only in
a side column. **Action**: CSV rev. 2 —
"DIVERGÊNCIA_EQUIVALENTE_COMPROVADA (… via after-returning; **provado em JVM,
ART pendente G10**)". The same qualifier already sat inside ALFA-IVP-02's and
BETA-IVP-04's resolution text; G10-IVP-1 remains a named pendency in §8.4.

## REF-B-07 — "Three routes converge" overstates (minor) — ACCEPTED (rhetoric)

Correct under the pilot's accepted REF-11 lesson: Alfa's and Gama's readings of
the same frozen bytes are one evidence route; the load-bearing routes in matrix
rows 2 and 3 are Beta's executed drives plus my own source/artifact
verification. No resolution changes — none of those resolutions cited
convergence as grounds (each cites the executed or verified evidence) — but the
convergence column's rhetoric was inflationary. **Action**: correction recorded
in §8.2; next batches count evidence routes, not agents, in that column (the
FEN-* counts already do this for claims).

## REF-B-08 — "LIMITAÇÃO_INEVITÁVEL_DOCUMENTADA" — documented by whom? (minor) — ACCEPTED

The reviewer is right that my own §0.6 shows no pre-existing register
(`frozen_set_debt.md`: 0 hits; GAMA-HMC-01: "ausência de registro") — the
documentation is this round's own oracle-bias register, and the bare state name
invites misreading it as a gh101-registered deliberate omission.
`modelo_semantico.md` §7's paradigm case is a GH101-registered limitation;
inevitability is uncontested, provenance was underdeclared. **Action**: CSV
rev. 2 — ALFA-HMC-02 classification now reads "documentada NESTA RODADA:
registro de viés do oráculo criado pela auditoria, a referendar pelo
pesquisador"; §8.4 lists the researcher countersignature as an open pendency.

## REF-B-09 — Dimension-5 coverage effectively single-route for 4/5 specs (minor) — ACCEPTED

Factually exact: Alfa filed dim-5 claims for all five specs, Beta only for HMC,
Gama none — and HMC, the one spec with a second route, is precisely where the
single-route reading-based claims were wrong (ALFA-HMC-05; GAMA-HMC-02's
premise). My post-hoc indexing verification (§0.3) and J1's parametrization walk
close the gap for this batch's four parameterized specs *as judge evidence*, but
the round design should not have needed the judge for it, and rev. 1 never
declared the asymmetry. **Action**: declared in §8.4; the standing two-object
test and the indexing-tree line in the generation manifest (§6 items 1–2) are
carried as adopted process changes for the next batches.

## Rev. 1 → Rev. 2 change table (complete; pilot §8.3 precedent)

| Item | Change | Objection | Score effect |
|---|---|---|---|
| GAMA-SKS-02 | severidade_final minor → **major**; justificativa rewritten to the §4 criterion; enters G13 must-close | REF-B-03 | none (severity does not score) |
| GAMA-IVP-03 | classificacao_final gains "(provado em JVM, ART pendente G10)" | REF-B-06 | none |
| ALFA-HMC-02 | classificacao_final gains "(documentada NESTA RODADA … a referendar pelo pesquisador)" | REF-B-08 | none |
| HMC gate table | G5 "FAIL*" → **PASS (vacuous; oracle bias registered)** | REF-B-04 | none (gates are not scored) |
| §5 preamble | operative gate rule corrected (criteria-driven; critical is one sufficient trigger) | REF-B-05 | none |
| Score presentation | raw weighted sum = PRIMARY; normalized % demoted to labeled derived reading; D-batchA-1 PROPOSED | REF-B-02 | none on inputs/subscores/raw totals (re-run verified) |
| Replication package | 12 judge evidence files published under `batchA/juiz_*` with hashes | REF-B-01 | none |
| Convergence rhetoric | routes ≠ agents correction recorded | REF-B-07 | none |
| Dim-5 coverage gap | declared; process changes carried | REF-B-09 | none |

Re-run after rev. 2 (`python3 juiz_rescore_batchA.py`): every raw number
identical to rev. 1 — DHG 63.33, HMC 32.50 (5 points unattainable), PBE 69.17,
IVP 88.33, SKS 68.83, SET 30.00 (INCOMPLETE, 2 INCONCLUSIVE outside), aggregate
61.07; totals 46 PASS / 48 FAIL / 2 INCONCLUSIVE over 96 claims; 18 critical
claims across 7 phenomena. No resolution (PASS/FAIL/INCONCLUSIVE) changed in
rev. 2; the three CSV changes are severity/label-level.

The final decision of the round is issued in `juiz_sintese_batchA.md` §8.
