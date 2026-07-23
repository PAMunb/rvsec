<!--
DECIDE-state template (methodology §3.1 step 8; spec "Decision Record and Journal").

The agent instantiates this file as iterN/decision.md at the DECIDE state, filling every
<PLACEHOLDER>. The decision rules below are DECLARATIVE and phase-dependent: keep the
section for the CURRENT phase, delete the other, and never invent a rule not written here.

Phases: SCREENING = Phase A (cala) and Phase B (calb); CONFIRMATION = Phase C (calc).

Placeholders: <ITER>, <PHASE>, <ARMS_PROMOTED>, <VERDICT>, and the per-arm/per-gate blanks.
-->

# Calibration decision — iter<ITER> (<PHASE>)

- **Iteration**: <ITER>
- **Phase**: <PHASE>  <!-- cala | calb | calc -->
- **Phase kind**: <SCREENING | CONFIRMATION>
- **Inputs**: `iter<ITER>/analysis.md`, `iter<ITER>/per_apk_paired.csv`, `iter<ITER>/tel_proxies.csv`, verification verdict `<admissible | quarantine>`
- **Anchors re-measured this run**: ANC1 (`ape:default`), ANC2 (`aperv:sata_mop_act_frontier`), `aperv:cal_a1`

> The decision is made ONLY over data whose VERIFY verdict is `admissible`. If any promoted
> arm's metrics rest on a `quarantine`d cell, name it here and exclude it — a quarantined
> number never drives a promotion.

---

## SCREENING decision rule (Phase A / Phase B)

**Delete this whole section if this is a CONFIRMATION iteration.**

Screening SELECTS candidates; it NEVER concludes. The following prohibition is absolute:

> **Do NOT declare a winner, and do NOT eliminate or promote any arm, on the basis of a
> screening p-value.** With MDE ≈ 3.3pp raw (≈ 2.0pp trimmed) at n=40 and real effects of
> 0.15–2.8pp, a screening p-value cannot discriminate arms (methodology §1 principle 3).
> Confirmatory inference happens ONLY in Phase C. Any sentence here of the form "arm X wins
> because p < …" is a defect and must be removed.

Promotion rule: promote the **top 2–3 arms** that pass **ALL** ANALYZE gates, in the
pre-declared order (INV-CAL-10):

1. **Proxy elimination** — arm survived (no dead-LLM proxy: `llm_tap`/`matched` non-degenerate; time_ms not >2× global median unless flagged as covariate).
2. **Ranking** — trimmed-mean 10% Δcov_mop vs ANC1 and ANC2, with the paired bootstrap
   B≥10,000 fixed-seed CI95 (raw mean reported alongside — never the trimmed mean alone).
3. **Mechanistic prediction-vs-observed** — the arm's predicted Δcov_mop (Δactions/task ×
   +46%/action) falls inside the observed CI95. An arm whose observed effect is outside its
   predicted CI is FLAGGED "mechanism not understood — do not promote without investigation".
   (Temperature arms H3 are exempt from elimination by this gate: descriptive only.)
4. **Determinism** — between-reps identical-trace rate consistent with the arm's regime
   (temp>0 arms: <30% identical target).

Ranking selects on **effect size + mechanistic coherence**, not on significance.

### Per-arm gate table (fill for every non-anchor arm)

| Arm | Δcov_mop vs ANC2 (trimmed / raw) | CI95 | Predicted Δ | Pred in CI? | Proxy OK? | Determinism | Gate verdict |
|-----|----------------------------------|------|-------------|-------------|-----------|-------------|--------------|
| cal_a1 | <..> / <..> | [<..>, <..>] | <..> | <yes/no/flag> | <yes/no> | <..> | <pass/flag/eliminate> |
| cal_a2 | … | … | … | … | … | … | … |
| … | … | … | … | … | … | … | … |

### Promoted arms

- **<ARMS_PROMOTED>**  <!-- 2–3 named variants, e.g. cal_a1, cal_a4, cal_a6 -->
- Rationale (effect + mechanism, per arm): <...>

### Next-iteration config

- **Arms carried forward**: <ARMS_PROMOTED> (+ ANC1, ANC2, cal_a1 always re-measured as anchors).
- **What changes**: <e.g. narrow to the surviving prompt variant; sweep top_p around the best value; add cal_b* arms defined from these survivors in get_variants()>.
- **Phase-B pre-registration** (if leaving Phase A): the hypotheses/predictions for the next
  phase are pre-registered here BEFORE the next run: <...>.
- **Not promoted / rejected** (kept as provenance, not deleted): <arms + one-line reason each>.

---

## CONFIRMATION decision rule (Phase C only)

**Delete this whole section if this is a SCREENING iteration.**

Confirmation APPLIES the pre-registered criteria and **STOPS** — there is no "next
iteration" from a confirmation verdict (the terminal states are winner-confirmed /
budget-exhausted / NO-GO-with-power). Apply the criteria pre-registered in the prior
phase's decision (SESOI 2.0pp, one-sided tests, seeds fixed) with NO post-hoc changes:

- **GO** — the single candidate's one-sided lower CI bound clears the pre-registered SESOI
  (2.0pp) against the anchor, at the pre-registered n (80–100). State the CI, effect size,
  and the throughput×quality partition.
- **NO-GO** — the candidate does not clear SESOI AND the test had adequate power. Report the
  honest ceiling (the achievable upper bound), not a null dressed as failure.
- **INCONCLUSIVE** — SESOI not cleared but power inadequate (CI straddles SESOI). Report the
  n that would be needed; do NOT relabel as NO-GO.

**Verdict**: <VERDICT>  <!-- GO | NO-GO | INCONCLUSIVE -->

- Candidate config: <named variant + full LLM key dict>
- One-sided CI95 vs anchor: [<lower>, <upper>], SESOI = 2.0pp
- Effect size (rank-biserial): <..>
- Throughput × quality partition: <..>
- **STOP.** This verdict is ratified by the human gate G4 and becomes the config of the
  final 181 experiment (out of scope of this campaign). No further calibration iteration.

---

## Journal

After writing this file, record the transition:

```
uv run experimento-cal/scripts/journal.py append --state DECIDE --iter <ITER> \
    --artifact experimento-cal/iter<ITER>/decision.md
```
