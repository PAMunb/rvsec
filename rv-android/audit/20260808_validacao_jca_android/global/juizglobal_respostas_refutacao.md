# GLOBAL JUDGE — responses to the global refutation round (protocol §15)

Global judge · 2026-08-09 · target of the refutation:
`global/juizglobal_relatorio.md` (rev. 1) + `juizglobal_gates.csv` +
`juizglobal_set_claims_resolvidos.csv` + `juizglobal_build.py`.
Refutation of record: `global/refutacaoglobal_parecer.md` (+
`refutacaoglobal_recount.py`/`_output.txt`, `refutacaoglobal_reexec_log.txt`,
`refutacaoglobal_hashes.txt`). Outcomes: **4 objections, 4 accepted, all
minor; 0 material, 0 blocking. No resolution, severity of record, gate
result, score, or verdict changed.** Each objection's factual anchor was
re-verified by me against the primary record before acting (ledger queries
for REF-G-01/-02 re-run this session; the REF-G-03/-04 texts checked against
`pre_registro.md` §3 row 8 and the api30 `SSLContext.cryptsl` reading already
on record).

---

## REF-G-01 — Gate-row claim-ID citations are round-ambiguous — **ACCEPTED (minor)**

**Fact check (mine, this session)**: the ledger holds `BETA-SET-06` in four
rounds with resolutions FAIL (batchA), FAIL (batchB), PASS (batchC),
INCONCLUSIVE (batchD); `BETA-SET-08` is FAIL in batchB and INCONCLUSIVE in
batchC; `BETA-SET-11` exists only in batchB (INCONCLUSIVE). The refuter is
right on both points: the G6 ground is true only under the intended
(round, claim) mapping, and rev. 1's A4 assert checked token existence
anywhere — it could not catch a wrong-round pointer.

**Action (rev. 2)**:
1. G6 pointers round-qualified in `juizglobal_gates.csv` and report §2:
   `batchD BETA-SET-06; batchC BETA-SET-08; batchB BETA-SET-11`, with the
   explicit note that same-named IDs in other rounds are distinct claims.
2. **A4 hardened** in `juizglobal_build.py`: round-qualified pointers of the
   form `batch<X> CLAIM-ID` are now asserted as (round, claim_id) **pairs**
   against the ledger; unqualified IDs keep the existence-only check, and
   that scope is now declared in the assert's output line.
3. **New assert A6**: the three G6 referents are pinned — each must be
   INCONCLUSIVE in its round of record. Builder re-run: A1–A6 all pass.

**Reach**: none (as the refuter states) — G6 remains INCONCLUSIVE under any
reading; no device evidence exists.

## REF-G-02 — The critical headline over-implies full FEN coverage — **ACCEPTED (minor)**

**Fact check (mine, this session)**: ledger query confirms exactly **9
criticals without canonical FEN** — all pilot derived-parsed (ALFA-CIP-01/02/
03/08/17, ALFA-GCM-03/04, BETA-GCM-04, GAMA-GCM-03) — so "164 (+10) across
50 phenomena" over-implied that all 174 distribute over the 50; and the 8
D-batchC-1 reconciliation rows are indeed counted at §4's letter *in
addition to* the 164 of-record. Both facts were already declared
(consolidation §1.2–§1.3; report §6.2 item 4) — the defect is headline
phrasing, as filed.

**Action (rev. 2)**: report §0.7 and the G13 row (report + gates CSV)
rephrased to the precise form: **"174 critical FAIL claims (164 of-record +
10 pilot derived-parsed), of which 165 link to the 50 critical-carrying
canonical phenomena; 9 pilot criticals remain pilot-local without canonical
FEN (pre-D-piloto-4 record); the 8 D-batchC-1 reconciliation rows are
counted at §4's letter in addition to the 164 of-record."**

**Reach**: none — G13 fails a fortiori under every reading; no count
changed, only the sentence binding them.

## REF-G-03 — G8 FAIL vs INCONCLUSIVE, both defensible — **ACCEPTED (minor; interpretation declared, result unchanged)**

**Response on the merits**: the objection is correct that the §11 corpus —
the pre-registered test object of gate row 8 — was never built, and that a
reader could therefore return INCONCLUSIVE (test not executed) while letting
the observed FP/FN ground G3/G7. I maintain the FAIL, for three reasons now
declared in the gate row itself: (1) `pre_registro.md` §3 row 8's FAIL cell
reads "FP/FN observado" with **no corpus qualifier**, and the executed
drives are reproducible observations of both FP and FN on real monitors over
real JDK objects — the letter is met; (2) the pre-registration's transversal
rule converts absence of evidence into INCONCLUSIVE, never into PASS — but
here there IS adverse executed evidence, and marking a gate INCONCLUSIVE in
its presence would understate the record; (3) choosing INCONCLUSIVE would
change nothing downstream (neither is PASS; both block READY), so the
letter-based reading is also the more informative one. The honesty clause
stands unchanged: the mutation-adequacy half is INCONCLUSIVE, and the drives
are adjudication witnesses, not the §11 suite.

**Action (rev. 2)**: the interpretation sentence added verbatim to the G8
row in the report §2 and `juizglobal_gates.csv` ("INTERPRETATION DECLARED
(REF-G-03): … the alternative reading — INCONCLUSIVE because the
pre-registered test object was never built — is acknowledged and equivalent
for the READY conjunction (neither is PASS)").

**Reach**: none — G8's contribution to the verdict is identical under
either label.

## REF-G-04 — EXEC-SET-23's severity raise entangled with a pending researcher ruling — **ACCEPTED (minor; annotation added, severity of record stands)**

**Response on the merits**: the refuter verified at the api30 source what
§1.1 relied on — `SSLContext.cryptsl` REQUIRES `randomized[sr]` with `sr`
bound by no event (`Init` binds `_`) — and agrees the raise is
precedent-consistent (batch C ALFA-SSL-07 crítica, unrefuted) and
letter-consistent (§4: executed FP on a realizable trace, X1, re-executed by
both of us). The accepted point is presentational: the contingency lived
only in §7 item 4, while the severity decision lives in §1.1 — the reader of
§1.1 must see that the FP reading (and hence the crítica) is conditional on
the researcher's ruling about `randomized[sr]`-with-unbound-`sr`.

**Action (rev. 2)**: contingency annotation added at the point of decision —
report §1.1 (full sentence) and the `juizglobal_build.py` RES comment. The
severity of record remains **crítica**; the resolved CSV is byte-unchanged
(the annotation is a record note, not a data change); a researcher ruling
under §7 item 4 that makes X1's error oracle-faithful **revisits this
severity cleanly** at that point.

**Reach**: none — FAIL under either severity; severity does not enter the
score; no gate or verdict depends on it.

---

## Rev. 1 → rev. 2 change table

| # | File | Change | Objection |
|---|---|---|---|
| 1 | `juizglobal_gates.csv` + report §2 G6 row | G6 pointers round-qualified (`batchD BETA-SET-06; batchC BETA-SET-08; batchB BETA-SET-11`) with distinct-claims note | REF-G-01 |
| 2 | `juizglobal_build.py` | A4 hardened to (round, claim) pair resolution for round-qualified pointers; existence-only scope declared for unqualified IDs; new assert A6 pins the three G6 referents as INCONCLUSIVE in their rounds | REF-G-01 |
| 3 | Report §0.7 + G13 row (report + gates CSV) | Critical headline rephrased: 174 = 164 of-record + 10 derived; 165 link to 50 phenomena; 9 pilot-local; 8 reconciliation rows additional to the 164 | REF-G-02 |
| 4 | Report §2 G8 row + gates CSV | Letter-based FAIL interpretation declared; INCONCLUSIVE alternative acknowledged as equivalent for READY | REF-G-03 |
| 5 | Report §1.1 + builder RES comment | EXEC-SET-23 crítica conditioned on the §7 item 4 researcher ruling (`randomized[sr]` unbound-`sr` reading) | REF-G-04 |
| 6 | Report §9 closing note + new §10 | Refutation-pending note superseded; FINAL DECISION section appended (verdict, final gate matrix, member-5 double derivation, §19 items 1–7 closure, item-8 hand-off) | all |
| 7 | `juizglobal_hashes.txt` | Regenerated over rev. 2 outputs + refutation files | — |

**Invariants across rev. 1 → rev. 2** (machine-checked by the rev. 2
builder): `juizglobal_set_claims_resolvidos.csv` byte-identical; 30 = 22
FAIL / 8 PASS / 0 INC; severities 15/6/1; 20 phenomena; score 15.45; gate
tally 2 PASS / 10 FAIL / 2 INCONCLUSIVE; SET verdict NOT READY.

## Survival statement

The refuter's §2 records that every attack on the substance failed: builder,
arithmetic, gate tallies, five-families/six-instances resolution, RANDOMIZED
split, dedupe finding, G11 anchor drift, G12 source facts, severity-scheme
coherence, score presentation, provenance tags, and — decisively — READY
member 5, which the refuter re-derived byte-for-byte from the frozen record
as an adversarial party. The final decision is issued in
`juizglobal_relatorio.md` §10.
