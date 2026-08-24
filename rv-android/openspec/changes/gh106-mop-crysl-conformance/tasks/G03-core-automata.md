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

- [ ] 3.1 `automata/Automaton.java` — states, alphabet over `Signature`, transitions with an optional guard, initial and accepting sets. Symbolic over signatures, **not** over labels (INV-CONF-03).
- [ ] 3.2 `automata/Determinizer.java` — subset construction. Required for correctness: the Glushkov construction is genuinely non-deterministic for `ORDER con, a?, a`, which produces two `a` edges from the same node. Assert that on a synthetic rule, because no rule in today's corpus exhibits it.
- [ ] 3.3 `automata/Minimizer.java` — Hopcroft. Needed so that `a,(b|c)` and `(a,b)|(a,c)` compare equal: they are the same language, and comparing regex ASTs would report a divergence that does not exist.
- [ ] 3.4 `automata/ProductSearch.java` — emptiness of `L(A) ∩ complement(L(B))` in both directions, returning the **shortest** witness word or absence. Shortest, because a long witness is unreadable and readability is the whole point of publishing one.
- [ ] 3.5 `automata/InverseMorphism.java` — build `h : Σ_sig* → Label*` carrying a signature to the concatenation, **in `declIndex` order**, of every label whose pointcut matches it; then compute `h⁻¹(L)`. Inverse morphism preserves regularity, so the result is an automaton and the comparison stays decidable.
- [ ] 3.6 Where a label overlap is separated by a guard that is not statically decidable, `InverseMorphism` returns `Unknown{OverlappingDispatch, labels:[…]}` rather than picking one label. Guessing here is exactly the silent failure the whole taxonomy exists to prevent.
- [ ] 3.7 `Witness` construction is centralised here and **always** carries `status` and the list of normalizations applied to reach it (INV-CONF-08). No caller can construct a witness without them.
- [ ] 3.8 Synthetic tests with closed-form answers: `ORDER con, a?, a` is non-deterministic and determinizes correctly; `a,(b|c)` ≡ `(a,b)|(a,c)` after minimization; product search finds the known shortest witness on hand-built pairs; `h⁻¹` of a two-label overlap yields the concatenation in declaration order.
- [ ] 3.9 Degenerate cases, because they are where automata code dies: empty language, universal language, single-state loop, an alphabet symbol reachable from no state, an accepting set that is empty.
- [ ] 3.10 Run the determinizer over the 47 upstream rule automata and **report** how many are already deterministic — a new measurement to emit, not a value to assert (over the abandoned `api30` corpus all 30 were; that figure is method history).
- [ ] 3.11 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green, with the automata suite isolated so it runs in under a second and can be run on every save.

## Closing
G03 closes when 3.1–3.11 are `[x]`.
