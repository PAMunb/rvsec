# G13b · what dies, conditional part

**Depends on:** G12. **Blocks:** G14.
**Size:** ~2 documents. **No file is deleted in this group.**

The five surviving artifacts are load-bearing CI gates. The criterion for retiring them is *the
ad-hoc dies when the component reproduces its verdict, not when it compiles* — so this group's job is
to **produce the reproduction evidence** and hand the deletion to a follow-up change.

Retiring a gate before the replacement reproduces it loses coverage silently, which is the same class
of failure the gh104 harness exists to catch and which this lineage has already shipped twice.

## The five survivors

| Artifact | Lines | Why it survives this change |
|---|---:|---|
| `scripts/gh105_order_gate.py` | 1 171 | live gate; G10 must reproduce its verdicts first |
| `scripts/gh101_conformance_check.py` | — | live gh101/gh105 gate |
| `scripts/gh104_baseline.py` | — | live gh104 gate |
| `scripts/gh104_gates.py` | — | live gh104 gate |
| `tests/parity/test_gh105_predicate_gates.py` | 2 507 | live pytest gate; its green is the cut criterion |

(The three `gh10{1,4}_*.py` total 4 340 lines.)

## Tasks

- [ ] 13b.1 Run `scripts/gh105_order_gate.py` and the component's M2 over the same corpus at the same commit, and produce a **verdict-by-verdict** comparison table for all 22 mapped specifications.
- [ ] 13b.2 Adjudicate every disagreement with evidence and record the outcome. The gate reads the `ORDER` with inverted precedence in its own history, so a disagreement is at least as likely to be the gate's as the component's — and deciding by measurement rather than by seniority is the point.
- [ ] 13b.3 Run `tests/parity/test_gh105_predicate_gates.py` and the component's M4 over the same corpus, and produce the same verdict-by-verdict table for the predicate gates.
- [ ] 13b.4 Do the same for the three `gh10{1,4}_*.py` scripts that read `.cryptsl`, restricted to the checks that fall inside the component's scope. Here "reproduce their verdict" means reproducing it over the **same historical `.cryptsl` input** they read, stamped as such — not re-deriving it from the upstream oracle, which would compare two different measurements. Some of what they do is outside the component's scope, and saying which is part of the deliverable.
- [ ] 13b.5 Write `docs/<date>_reproducao_portoes_ci_gh106.md`: the tables, the adjudications, and an explicit verdict per gate — *reproduced* or *not yet*.
- [ ] 13b.6 Open the follow-up cleanup issue for the gates marked *reproduced*, citing the evidence document by commit. **Do not delete them here**, even the ones that reproduce cleanly: the deletion is a separate change with its own verification, and bundling it hides it inside a change about something else.
- [ ] 13b.7 Record in `divergence_record.csv` any gate verdict the component **deliberately** does not reproduce, with the reason. A gate that measures something the component decided not to measure is not a failure; it is a scope boundary, and it needs to be written down as one.

## Closing
G13b closes when 13b.1–13b.7 are `[x]`. Closing it with a gate marked *reproduced* but no follow-up
issue open means the retirement will be forgotten.
