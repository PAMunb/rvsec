# Deviations from the pre-registration

Register required by the protocol (`docs/20260808_validar_specs_jca_android.md` §4:
"Não altere critérios depois de observar resultados sem registrar a alteração como
desvio do pré-registro"). Each deviation was born from a pilot finding, was proposed
in the judge's synthesis (`pilot/juiz_sintese.md` §6) or in the refutation round
(`pilot/juiz_respostas_refutacao.md`), and is formalized here on 2026-08-09,
**before** the 23-spec round opens. No deviation alters the decision criteria of
`pre_registro.md` section 3, the weights of section 6, or gates G0–G13 — they add
procedures and fix rules the pre-registration did not cover.

## D-piloto-1 — normative reading of ORDER precedence

**Origin**: ALFA-CIP-04 (INCONCLUSIVE — ambiguity of the oracle, not of the spec):
the MetaCrySL grammar (`ConcreteSyntax.rsc:59-70`) inverts the precedence of `,`/`|`
relative to official CrySL, and reading B is degenerate (it excludes normal use).

**Text**: the 23-spec round adopts as the normative reading of ORDER the precedence
of official CrySL (comma outermost), after a single verification against the
upstream Xtext grammar; the MetaCrySL grammar is recorded as divergent. Date,
responsible party and evidence of the verification will be attached to this register
when the verification is executed.

**Status**: rule fixed; the one-time verification was **executed on 2026-08-09** by
the audit orchestrator.

**Evidence of the verification**: upstream grammar
`de.darmstadt.tu.crossing.CrySL/src/de/darmstadt/tu/crossing/CrySL.xtext` from
`github.com/CROSSINGTUD/CryptSL`, pinned at commit `e92f5607` (last commit touching
the file, 2025-08-08), frozen copy at `fase0/upstream_CrySL_e92f5607.xtext`
(sha256 `881c41c2ebf544e9d7e1967c828b12219a67d9f4df18659d9b69ae38bd21b62d`). The
productions at lines 103–121 read: `Order: Sequence`;
`Sequence returns Order: Alternative (op=SequenceOperator right=Alternative)*` with
`SEQUENCE = ','`; `Alternative returns Order: Cardinality (op=AlternativeOperator
right=Cardinality)*` with `ALTERNATIVE = '|'`. The comma is therefore the outermost
(lowest-precedence) operator and `|` binds tighter — reading A, as adopted. The
MetaCrySL grammar (`ConcreteSyntax.rsc:59-70`) stands recorded as divergent from
upstream. Note: commands to reproduce are `curl` of the pinned raw URL plus
`sha256sum`; the fetch date matters because the pin is to the file's last commit,
not to a release tag.

## D-piloto-2 — two standardized per-spec tests, executable in a JVM harness

**Origin**: ALFA-CIP-14a/14b and ALFA-GCM-05 — recurring INCONCLUSIVEs whose
resolution depends on two tests the pre-registration did not foresee and which
require no emulator.

**Text**: two standardized per-spec tests are added: (a) folding×JCA
(case-insensitive resolution of `getInstance`); (b) semantics of `part()` over an
absent component. Both executable in a JVM harness against the frozen
`android.jar`. They alter no decision criteria and no gates; they convert recurring
INCONCLUSIVEs into resolutions.

**Status**: adopted for the 23-spec round. ALFA-CIP-14b is marked in the CSV as a
candidate for reclassification (to DIVERGÊNCIA_EQUIVALENTE_COMPROVADA) if test (a)
demonstrates equivalence; ALFA-GCM-05 depends on the harness over the two
constructors.

## D-piloto-3 — language verdict over the effective automaton

**Origin**: the apparent conflict ALFA-CIP-01/02/03 × BETA-CIP-09 (§1 phenomenon 1):
comparisons with distinct references (CrySL×`.mop` vs `.mop`×artifact) produced
opposite labels for the same phenomenon.

**Text**: the language verdict is now issued over the effective automaton extracted
from the generated artifact (dimension 1 of the semantic model), with the `.mop`
syntax used only as the initial hypothesis. The criterion does not change — this
makes explicit the evidence source the semantic model §6.1 already required.

**Status**: adopted for the 23-spec round.

## D-piloto-4 — claim→dimension assignment, set-wide claims, classification convention

**Origin**: REF-06 (partially accepted) and REF-13 (accepted) from the refutation
round. In the pilot, the assignment of each claim to a score dimension was a
discretionary decision made by the judge at resolution time; 12 `*-SET-*` claims
(about the set/pipeline, not the 2 specs) entered the denominator of a score
presented as "of the pilot" — measured sensitivity of +3.93 points
(`pilot/juiz_rescore.py`); and the `classificacao` column was only normalized in
rev. 2.

**Text** (rules fixed for the 23-spec round):

1. **Assignment at creation, not at resolution**: each claim is assigned to exactly
   one score dimension by the agent that creates it, at creation time, under the
   rule "the dimension is that of the phenomenon the decisive evidence measures".
   The judge does not re-assign after seeing results; disagreement over assignment
   is recorded as a pendency, not corrected ex post.
2. **Set-wide claims scored separately**: claims about the set/pipeline (`SET`
   prefix) enter a set score of their own, outside the denominator of the per-spec
   scores. The per-spec score reports only that spec's claims.
3. **Common phenomenon ID**: claims about the same phenomenon from distinct agents
   cite a phenomenon ID (`FEN-*`), and the judge reports score per claim **and**
   count per phenomenon, avoiding an inflated reading of convergence.
4. **Classification convention (REF-13)**: every claim carries exactly one of the
   six states of the normative matrix (`modelo_semantico.md:92-95`), with detail in
   parentheses. Toolchain/generability measurement claims that verify the chain
   (not a CrySL clause) enter as FIDELIDADE_DEMONSTRADA of the corresponding
   dimension when PASS and INCORRETA (toolchain defect) when FAIL.

**What does not change**: weights and denominator of `pre_registro.md` section 6;
the rule "INCONCLUSIVE stays outside the denominator"; the prohibition of averaging
across agents; the gates. The pilot score is **not** re-summed under these rules —
the published number (55.90, with the caveats declared in `pilot/juiz_sintese.md`
§8.2) remains the pilot's record.

**Status**: adopted for the 23-spec round.

## D-batchA-1 — score presentation for units with empty dimensions

**Origin**: REF-B-02 (material, accepted) from the batch A refutation round: the judge's
first synthesis published an attainable-weight percentage (HMC 32.50/95 = 34.21%; SET
30.00/50 = 60%) as an unregistered convention adopted after seeing which dimensions
lacked claims. Proposed by the judge in `batchA/juiz_sintese_batchA.md` §8.5;
formalized here by the audit orchestrator on 2026-08-09.

**Text**: when a scored unit (spec or SET) has no resolved claims in some dimension,
the score of record is the **raw weighted sum** over the pre-registered weights
(`pre_registro.md` §6), with the unattainable weight explicitly stated. A percentage
normalized over the attainable weight MAY be published only as a labeled derived
reading, never as the score of record.

**What does not change**: weights and denominator rules of `pre_registro.md` §6; the
rule "INCONCLUSIVE stays outside the denominator"; the prohibition of averaging across
agents; the gates.

**Status**: adopted from batch B onward; batch A's rev. 2 already follows it
retroactively (REF-B-02 remediation).

## D-batchB-1 — phenomenon linkage is part of the resolved record

**Origin**: REF-C-02 (material, accepted) from the batch B refutation round: 7 FAIL
rows (including 3 criticals) carried an empty `fenomeno_id` and the rescore script
silently skipped them, so the published per-phenomenon table contradicted the conflict
matrix. Proposed by the judge in `batchB/juiz_sintese_batchB.md` (§8.5); formalized
here by the audit orchestrator on 2026-08-09.

**Text**: every claim resolved FAIL must carry a phenomenon ID in the judge's
consolidated CSV (`fenomeno_id_final`: the agent's ID where filed, the judge's
assignment otherwise), enforced by a build-time assert; the per-phenomenon table is
generated only from that column.

**What does not change**: weights, denominators, the six normative states, the gates,
and D-piloto-4's rule that the judge does not re-assign claim→dimension.

**Status**: adopted from batch C onward; batch B rev. 2 already follows it.

## D-batchC-1 — fail-open severity follows §4's letter; ledger reconciliation

**Origin**: REF-D-01 (material, accepted) from the batch C refutation round: fail-open
phenomena had been resolved at *major* ("major as pattern", batch A practice never
registered) while `pre_registro.md` §4 pre-registers fail-open as *crítica*. Proposed
by the judge in `batchC/juiz_sintese_batchC.md` §8.6; formalized here by the audit
orchestrator on 2026-08-09.

**Text**: fail-open findings (generator or pipeline defects masked by exit 0,
including artifacts that do not compile standalone) are resolved at severity
**crítica** per `pre_registro.md` §4, from batch C onward. The batch A/B records that
resolved fail-open pattern claims at *major* stand as those rounds' records; the G13
consolidation counts the phenomenon family at §4's letter.

**What does not change**: §4's severity definitions (this deviation *enforces* them);
weights, denominators, gates; closed rounds' records.

**Status**: adopted from batch C onward (batch C rev. 2 already follows it); binding
for batch D and the set-level/global phases.

## D-batchD-1 — platform-member evidence admissibility

**Origin**: REF-E-01 (material, accepted) from the batch D refutation round: an agent
javap artifact was host-JDK output mislabeled as android-30 (the known `-classpath`
fallback trap), and a sub-assertion built on it was false. Proposed by the judge in
`batchD/juiz_sintese_batchD.md` §8; formalized here by the audit orchestrator on
2026-08-09.

**Text**: a javap artifact is admissible as platform evidence only if produced over
class files extracted from the frozen jar; artifacts bearing host-trap markers (types
or members absent from the frozen jar, e.g. `SecureRandomParameters`,
`sun.security.*`, `jdk.internal.*`) are inadmissible, and every agent javap artifact
is swept for those markers before the judge consumes it.

**What does not change**: no criteria, weights or gates — this fixes an
evidence-admissibility rule the pre-registration did not cover.

**Status**: adopted for the set-level and global phases (and any future per-spec
re-examination).
