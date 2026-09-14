# G03 · automata core

**Depends on:** G00. **Blocks:** G10, G11.
**Parallel with:** G01, G02, G04, G05.
**Size:** ~7 files in `rvsec-crysl-core`. No dependency on either parser (the module may carry a serialization library for the emitters and JUnit/ArchUnit in test scope); this group in particular needs nothing beyond the JDK.

This is the piece both the comparator and the generator share, and it is the most delicate one in
the change. It is also the only group whose correctness can be established entirely on synthetic
input with closed-form answers — use that.

## Reference
- `specs/conformance/spec.md` — "M2 Order Comparison over the Inverse Morphism", INV-CONF-03
- `design.md` D-02 (why `h⁻¹(L)`), D-10 (witness status)

## Tasks

- [x] 3.1 `automata/Automaton.java` — states, alphabet over `Signature`, transitions with an optional guard, initial and accepting sets. Symbolic over signatures, **not** over labels (INV-CONF-03).
- [x] 3.2 `automata/Determinizer.java` — subset construction. Required for correctness: the Glushkov construction is genuinely non-deterministic for `ORDER con, a?, a`, which produces two `a` edges from the same node. Assert that on a synthetic rule, because no rule in today's corpus exhibits it.
- [x] 3.3 `automata/Minimizer.java` — Hopcroft. Needed so that `a,(b|c)` and `(a,b)|(a,c)` compare equal: they are the same language, and comparing regex ASTs would report a divergence that does not exist.
- [x] 3.4 `automata/ProductSearch.java` — emptiness of `L(A) ∩ complement(L(B))` in both directions, returning the **shortest** witness word or absence. Shortest, because a long witness is unreadable and readability is the whole point of publishing one.
- [x] 3.5 `automata/InverseMorphism.java` — build `h : Σ_sig* → Label*` carrying a signature to the concatenation, **in `declIndex` order**, of every label whose pointcut matches it; then compute `h⁻¹(L)`. Inverse morphism preserves regularity, so the result is an automaton and the comparison stays decidable.
- [x] 3.6 Where a label overlap is separated by a guard that is not statically decidable, `InverseMorphism` returns `Unknown{OverlappingDispatch, labels:[…]}` rather than picking one label. Guessing here is exactly the silent failure the whole taxonomy exists to prevent.
- [x] 3.7 `Witness` construction is centralised here and **always** carries `status` and the list of normalizations applied to reach it (INV-CONF-08). No caller can construct a witness without them.
- [x] 3.8 Synthetic tests with closed-form answers: `ORDER con, a?, a` is non-deterministic and determinizes correctly; `a,(b|c)` ≡ `(a,b)|(a,c)` after minimization; product search finds the known shortest witness on hand-built pairs; `h⁻¹` of a two-label overlap yields the concatenation in declaration order.
- [x] 3.9 Degenerate cases, because they are where automata code dies: empty language, universal language, single-state loop, an alphabet symbol reachable from no state, an accepting set that is empty.
- [x] 3.10 Run the determinizer over the 47 upstream rule automata and **report** how many are already deterministic — a new measurement to emit, not a value to assert (over the abandoned `api30` corpus all 30 were; that figure is method history).
  **Capability built, run deferred:** `Determinizer.census(Collection<Automaton>)` + `Determinizer.COUNTING_RULE` are in place and tested; the run itself needs the CrySL lifter of `rvsec-crysl-crysl`, which `-core` may not depend on, so G10 takes the measurement. This is the one checkbox of the group left open, and it is left open deliberately rather than closed on an unmeasured number.
- [x] 3.11 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green, with the automata suite isolated so it runs in under a second and can be run on every save.

## Closing
G03 closes when 3.1–3.11 are `[x]`.

## Notes on closing

**3.1** — `Automaton` and `Transition` keep the component lists G00 declared; nothing was reshaped,
so the two lifter groups compile unchanged. Three things were added, all additive: the derived
queries `alphabet()`, `transitionsFrom(String)`, `reachableStates()` and `accepts(List<Signature>)`,
and one new validation in the canonical constructor — a transition whose `from` or `to` is outside
`states` is now rejected. The alphabet stays *derived* rather than declared: a letter nothing reads
is in no language, and the one case where the difference is visible (3.9, a symbol reachable from no
state) is representable as an edge leaving a state the initial one cannot reach.

`LabelAutomaton` and `LabelTransition` are new, and they are the only place a label ever appears in
an automaton. A `.mop` formula is written over the names its `event` declarations introduce, so a
lifter has no choice but to build the label language first; INV-CONF-03 governs what is then *kept*,
and what is kept is the signature automaton `InverseMorphism.preimage` produces. Nothing of that
shape is stored in a `SpecModel`, and no field anywhere is a `Map<Label, ?>` — `ModelShapeArchTest`
still passes over the new classes.

**3.2** — guards are opaque to the subset construction: two edges leaving one state on one signature
are non-determinism at the letter level whatever conditions they carry, so they merge. The merged
edge keeps a guard only when every edge that produced it carried the same one, and drops it
otherwise, because a disjunction of guards is not a guard this module has a language to write.

**3.6** — this module has no guard solver, so a guard here is by construction not statically
decidable and any overlap carrying one is refused. `InverseMorphism.of` is the single point that
would consult a solver if one ever existed. `preimage` throws when refusals are present rather than
computing over a gap it has admitted to.

**3.10 — measured on 2026-08-24 by G10 (task 10.2-bis): 47 of 47 already deterministic.** Taken over
the 47 upstream `.crysl` rules that load, from `rvsec-cognicrypt` at `f2f4d3b`, under
`Determinizer.COUNTING_RULE` (R-DET). It is a **new** measurement and not the historical `30 of 30`,
which was taken over the abandoned `api30` corpus. Over the 22 paired rules alone the figure is
22 of 22. The wiring is `M2Order.census(Collection<SpecModel>)`; the number reaches every report
through `M2Order.reportCountingRule(census)`, which prints `47 of 47` with R-DET beside it, and it is
asserted by `M2OrderCorpusTest.test_determinization_census_over_the_upstream_oracle`. Determinization
still runs on every comparison: a rule of the shape `ORDER con, a?, a` is genuinely non-deterministic
and `M2OrderTest.test_determinization_runs_on_a_genuinely_non_deterministic_rule` builds one.

**3.10 — the capability, as G03 left it.** `Determinizer.census(Collection<Automaton>)`
returns `Census{total, alreadyDeterministic, countingRule}` and `Determinizer.COUNTING_RULE` states
the rule: *an automaton counts as already deterministic when no state has two outgoing edges on the
same signature; a partial transition function counts as deterministic; guards are not consulted.*
The run over the 47 upstream rule automata cannot happen here — it needs the CrySL lifter, which
lives in `rvsec-crysl-crysl`, and `-core` depends on neither parser by design. G10 wired it as
described above. One correction to the plan this paragraph carried: the fraction did **not** go into
`M2Result.ruleAutomatonWasDeterministic`, which stays the per-specification boolean its Javadoc
describes — one comparison determinizes one rule automaton, and a corpus-wide fraction stored in a
per-specification record would read `1 of 1` on every row. The fraction is a corpus aggregate and
travels as one, through `M2Order.reportCountingRule`, where INV-CONF-02 can see it beside its rule.
No value is asserted in this group; the historical `30 of 30` was measured over the abandoned
`api30` corpus and is method history, not a target.

**3.11** — the automata suite is isolated by the JUnit tag `@Tag("automata")`, which Surefire
selects from the command line with no pom change:
`mvn -o -f rvsec/rvsec-crysl/pom.xml -pl rvsec-crysl-core test -Dgroups=automata`.
Measured: **39 tests, 0.210 s of test execution** (whole Maven invocation 2.3 s). The full `-core`
suite is **70 tests, 0 failures, 0 errors**.
