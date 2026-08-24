<!-- Subagent dispatch hints:
     - Group 1 (G00 Foundation) must complete first — Groups 2-6 all depend on it, and it is small
       on purpose: the four poms plus the types only. Fixing the types early is what unlocks the
       parallelism; nothing else in this change gates as much for as little work.
     - Groups 2-6 (G01 lift MOP, G02 lift CrySL, G03 automata core, G04 outputs, G05 CLI+reactor)
       are independent of one another and run in parallel after Group 1. Group 14 (G13a, the
       unconditional backup move) is independent of everything and runs from day one.
     - Groups 7 (G06 M0) and 12 (G11 mop.lower) unlock after Group 2 alone — they do not wait for G02.
     - Groups 8, 9, 10 (G07 M1, G08 M3, G09 M4) unlock after Groups 2 AND 3, and are mutually
       independent: three parallel dispatches.
     - Group 11 (G10 M2) needs Groups 2, 3 and 4 — it is the longest chain and sits on the critical path.
     - Group 13 (G12 calibration) integrates everything: it must run after Groups 5, 7-12.
     - Group 15 (G13b) runs after Group 13 — the CI gates die only once the component reproduces them.
     - Group 16 (G14) is final verification and runs last.
     - Critical path: G00 -> {G01, G02, G03} -> G10 -> G12 -> G13b -> G14.
     - Maximum parallelism after G00: 6 tracks. After G01+G02: 6 metric/lower tracks.
     - This change creates ~45 new Java files across 4 Maven modules plus test resources —
       use subagent orchestration (6-8 parallel dispatches at the widest point).
     - Sizing rule (WORKFLOW.md §5): each group is 3-15 files. Two exceptions are declared rather
       than hidden: G00 creates ~24 files, but every one is a single record or sealed interface, so
       a subagent holds declarations and not implementations; and G01 and G10 are the likeliest to
       exceed 15 during implementation — split those rather than letting a subagent compact. -->

# Tasks: gh106-mop-crysl-conformance

**This file is the orchestrator.** Each group below carries **one** checkbox, and the detailed work
list for that group lives in `tasks/G<NN>-<name>.md`. Those files are supporting material of the
change, in the same standing as `risk-register.md`: the `rv-sdd` schema tracks `tasks.md` and only
`tasks.md` (`apply: tracks: tasks.md`), so the checkboxes here are what `/opsx:apply` and
`openspec status` read, and the checkboxes inside a group file are the work list of whoever executes
that group.

**Closing rule.** A group's checkbox here becomes `[x]` **only when every checkbox in its group file
is `[x]`.** Marking a group closed with open items in its file breaks the resume protocol: a later
session reading only this file would believe the work is done.

**Prerequisites already met** (executed 2026-08-24, before this change existed — see
`docs/20260824_medicoes_pre_change_conformidade.md`):

- **P1** — the 129 signature lines and the 155 checked signatures remeasured under a fresh
  `CrySLModelReader` per rule. They are **141** and **141** over the abandoned `api30` corpus; redone
  over the upstream oracle: **215** lines in both modes, `diff` with and without `android.jar` empty,
  `ApiCheck` decomposing `175/29/5/6`. Closed.
- **P2** — the gh104 differential harness run against the five global specifications, with four
  authored negative controls. Closed, and its result is what motivates G06 (M0) separating three
  causes of silence rather than one.

## Dependency graph

```
G00 ─┬─ G01 ─┬──────────────────── G06 ──┐
     │       ├─ (with G02) ─────── G07 ──┤
     │       ├─ (with G02) ─────── G08 ──┤
     │       ├─ (with G02) ─────── G09 ──┤
     │       ├─ (with G03, G04) ── G10 ──┼── G12 ── G13b ── G14
     │       └─ (with G03) ─────── G11 ──┤
     ├─ G02 ────────────────────────────┤
     ├─ G03 ────────────────────────────┤
     ├─ G04 ────────────────────────────┤
     └─ G05 ────────────────────────────┘

G13a ── independent of everything, from day one

Critical path:  G00 → {G01, G02, G03} → G10 → G12 → G13b → G14
```

| Group | File | Depends on | Parallel with |
|---|---|---|---|
| G00 Foundation | [tasks/G00-foundation.md](tasks/G00-foundation.md) | — | G13a |
| G01 lift MOP | [tasks/G01-lift-mop.md](tasks/G01-lift-mop.md) | G00 | G02–G05 |
| G02 lift CrySL | [tasks/G02-lift-crysl.md](tasks/G02-lift-crysl.md) | G00 | G01, G03–G05 |
| G03 automata core | [tasks/G03-core-automata.md](tasks/G03-core-automata.md) | G00 | G01, G02, G04, G05 |
| G04 outputs | [tasks/G04-outputs.md](tasks/G04-outputs.md) | G00 | G01–G03, G05 |
| G05 CLI + reactor | [tasks/G05-cli-reactor.md](tasks/G05-cli-reactor.md) | G00 | G01–G04 |
| G06 M0 vitality | [tasks/G06-m0-vitality.md](tasks/G06-m0-vitality.md) | G01 | G07–G11 |
| G07 M1 events | [tasks/G07-m1-events.md](tasks/G07-m1-events.md) | G01, G02 | G06, G08–G11 |
| G08 M3 constraints | [tasks/G08-m3-constraints.md](tasks/G08-m3-constraints.md) | G01, G02 | G06, G07, G09–G11 |
| G09 M4 predicates | [tasks/G09-m4-predicates.md](tasks/G09-m4-predicates.md) | G01, G02 | G06–G08, G10, G11 |
| G10 M2 order | [tasks/G10-m2-order.md](tasks/G10-m2-order.md) | G01, G02, G03, G04 | G06–G09, G11 |
| G11 mop.lower + round-trip | [tasks/G11-mop-lower-roundtrip.md](tasks/G11-mop-lower-roundtrip.md) | G01, G03 | G06–G10 |
| G12 corpus calibration | [tasks/G12-corpus-calibration.md](tasks/G12-corpus-calibration.md) | G04, G05, G06–G11 | — |
| G13a what dies (unconditional) | [tasks/G13a-what-dies-unconditional.md](tasks/G13a-what-dies-unconditional.md) | — | everything |
| G13b what dies (conditional) | [tasks/G13b-what-dies-conditional.md](tasks/G13b-what-dies-conditional.md) | G12 | — |
| G14 final verification | [tasks/G14-final-verification.md](tasks/G14-final-verification.md) | all | — |

## 1. G00 · Foundation — the four poms and the types only

Blocks everything and is small on purpose. Four `pom.xml` (parent + `-core` + `-mop` + `-crysl`),
`guava.version` overridden, `slf4j-simple` excluded, `scala.version` **not** overridden, registration
in `rvsec/rvsec/pom.xml` `<modules>`; and in `-core` **only the types**: `SpecModel` with a
**per-corpus** `Version{corpus, SourceStamp{repository, commit, data}}` (the input spans two git
repositories plus the SDK, so one scalar commit would misattribute an upstream number), `Label` as a distinct
type so INV-CONF-03 is machine-checkable, `Event` with `declIndex`, `Constraint`, `PredicateRef`,
`Provenance`, the sealed five-member `Unknown` hierarchy, and the result types of the five metrics
with `Witness{status: ABSTRACT|CONCRETE}`. Fixing these types is what releases six parallel tracks
the next day.

- [ ] 1.1 G00 closed — every checkbox in [tasks/G00-foundation.md](tasks/G00-foundation.md) is `[x]`

## 2. G01 · lift MOP

`SpecExtractor` → `SpecModel`; `MOPNameSpace.init()` per file; the seven measured parser traps; both
predicate substrates (`ExecutionContext` and `PredicateStore`); the `ere`/`fsm` mini-parser;
`file:line` provenance on every item.

- [ ] 2.1 G01 closed — every checkbox in [tasks/G01-lift-mop.md](tasks/G01-lift-mop.md) is `[x]`

## 3. G02 · lift CrySL

A fresh `CrySLModelReader` per rule with no sharing option; **no lexical normalization of any kind**;
`StateMachineGraph` → automaton; the EMF provenance route (`resource.getErrors()`, names, `file:line`
— D-19); the single upstream oracle (`CrySL-Rules`, 47 of 49).

- [ ] 3.1 G02 closed — every checkbox in [tasks/G02-lift-crysl.md](tasks/G02-lift-crysl.md) is `[x]`

## 4. G03 · automata core

NFA/DFA, determinization, minimization, product search, the inverse morphism `h⁻¹(L)`, and the
shortest witness carrying its status and its normalizations.

- [ ] 4.1 G03 closed — every checkbox in [tasks/G03-core-automata.md](tasks/G03-core-automata.md) is `[x]`

## 5. G04 · outputs

JSON; CSV in the schemas of `data/jca_android/*.csv`; Markdown evidence in the shape of
`data/gh104/evidence/*.md`; **a commit stamp and a counting rule on every emitted table**, enforced
rather than conventional.

- [ ] 5.1 G04 closed — every checkbox in [tasks/G04-outputs.md](tasks/G04-outputs.md) is `[x]`

## 6. G05 · CLI + reactor

`main`, the three subcommands (`compare`, `lower`, `calibrate`), and the reactor integration test
that asserts the effective pom rather than trusting a silent build. `rvsec-mop-extractor` is the
template **by shape**, not by code.

- [ ] 6.1 G05 closed — every checkbox in [tasks/G05-cli-reactor.md](tasks/G05-cli-reactor.md) is `[x]`

## 7. G06 · M0 vitality

Does it index? Is the accusation site reachable? Does the pointcut resolve against `android.jar`?
Plus the non-normalized AST checker. Emits `Unknown{UnresolvedSignature}`, refuses before M1–M4, and
**separates the three causes of silence** that P2 measured.

- [ ] 7.1 G06 closed — every checkbox in [tasks/G06-m0-vitality.md](tasks/G06-m0-vitality.md) is `[x]`

## 8. G07 · M1 events

Sets of concrete signatures; coverage plus **both** differences; feeds the label alignment M2 uses.

- [ ] 8.1 G07 closed — every checkbox in [tasks/G07-m1-events.md](tasks/G07-m1-events.md) is `[x]`

## 9. G08 · M3 constraints

Idioms A/B/C/D; the injected equality (`ConscryptAliasTable.matches`) as part of the semantics rather
than decoration; `Unknown{UntranslatableConstraint}`; **two ceilings reported separately, never
summed** — the upstream denominator is 80 over the 22 paired rules (R1), and the numerator is
remeasured, not carried over from the `api30`-anchored table.

- [ ] 9.1 G08 closed — every checkbox in [tasks/G08-m3-constraints.md](tasks/G08-m3-constraints.md) is `[x]`

## 10. G09 · M4 predicates

The `ENSURES`/`REQUIRES`/`NEGATES` graph by arity, polarity and argument position; both substrates
(the new one in `jca_android`, the old one in the frozen `jca`); every row marked derived or
inherited; detection of predicate propagation across type conversions.

- [ ] 10.1 G09 closed — every checkbox in [tasks/G09-m4-predicates.md](tasks/G09-m4-predicates.md) is `[x]`

## 11. G10 · M2 order

`h⁻¹(L_mop)` vs `L(A_crysl)` in both directions; **consumes the `disposition` column** of
`order_alphabet_map.csv` instead of inferring erasure; every verdict labelled `M2-decl`; every witness
`ABSTRACT`/`CONCRETE` with its normalizations printed. Includes recomputing the `KeyGeneratorSpec`
verdict, whose published value was computed over an automaton that no longer exists.

- [ ] 11.1 G10 closed — every checkbox in [tasks/G10-m2-order.md](tasks/G10-m2-order.md) is `[x]`

## 12. G11 · mop.lower + round-trip gate

`SpecModel` → `MOPSpecFile` → `DumpVisitor`, never `StringBuilder`. The gate in two layers: (1) the
non-normalized AST checker as the gate, (2) product search as evidence with the normalizations
printed beside each verdict.

- [ ] 12.1 G11 closed — every checkbox in [tasks/G11-mop-lower-roundtrip.md](tasks/G11-mop-lower-roundtrip.md) is `[x]`

## 13. G12 · corpus calibration — the gate that stops the component being born wrong

The component must reproduce **eight** targets before its output is treated as measurement, and every
target's route must be one the component **does not produce** — two of the eight as first drafted
were the component's own rule, and a gate built on those cannot fail (`risk-register.md` RISK-006). A disagreement is a finding: measure both sides and adjudicate with
evidence. **Never adjust the component until the numbers agree** — the cheapest way to pass a
calibration gate is to break the instrument.

- [ ] 13.1 G12 closed — every checkbox in [tasks/G12-corpus-calibration.md](tasks/G12-corpus-calibration.md) is `[x]`

## 14. G13a · what dies, unconditional part

Back up the six `ORDER` comparators and the seven CrySL readers under `audit/20260808_*` (13 files,
one counted in both categories). Independent of every other group and runnable from day one, because
nothing in CI depends on them.

- [ ] 14.1 G13a closed — every checkbox in [tasks/G13a-what-dies-unconditional.md](tasks/G13a-what-dies-unconditional.md) is `[x]`

## 15. G13b · what dies, conditional part

The CI gates (`scripts/gh105_order_gate.py`, the three `gh10{1,4}_*.py`, and
`tests/parity/test_gh105_predicate_gates.py`) are **not** deleted here. This group records the
reproduction evidence and schedules their retirement in a follow-up cleanup change. The criterion:
*the ad-hoc dies when the component reproduces its verdict, not when it compiles.*

- [ ] 15.1 G13b closed — every checkbox in [tasks/G13b-what-dies-conditional.md](tasks/G13b-what-dies-conditional.md) is `[x]`

## 16. G14 · final verification

The full work list — lint, reactor build with tests enabled, `/rv-verify`, `/rv-code-reviewer`,
`/rv-docs-sync` — lives in the group file, like every other group.

- [ ] 16.1 G14 closed — every checkbox in [tasks/G14-final-verification.md](tasks/G14-final-verification.md) is `[x]`
