# G10 · M2 order

**Depends on:** G01, G02, G03 and G04. **Blocks:** G12.
**Parallel with:** G06–G09, G11.
**Size:** ~6 files in `rvsec-crysl-core`. **On the critical path** — start it the moment G03 closes.
**Watch the sizing rule**: if the normalization catalogue grows past 15 files, split into
`G10a comparison` and `G10b normalizations`.

## Reference
- `specs/conformance/spec.md` — "M2 Order Comparison over the Inverse Morphism", INV-CONF-10, -13
- `design.md` D-02, D-05
- `data/jca_android/order_alphabet_map.csv` (207 lines at `5fbe8173`), column `disposition`

## Tasks

- [ ] 10.1 `metric/M2Order.java` — compare `h⁻¹(L_mop)` against `L(A_crysl)` by product search in both directions, emitting equivalent / MOP more permissive / MOP more restrictive / incomparable.
- [ ] 10.2 Determinize the rule automaton before comparing. A no-op wherever the rule is already deterministic (G03 3.10 measures how many of the 47 upstream automata are) and it **still runs** — a future `ORDER con, a?, a` is genuinely non-deterministic and would otherwise be compared wrongly and silently.
- [ ] 10.3 `compare/AlphabetMap.java` — read `order_alphabet_map.csv` and expose the `disposition` column. **M2 takes every ε-erasure decision from it** (INV-CONF-10). Delete any code path that infers erasure from automaton shape; the shape criterion is provably insufficient (it does not license erasing `KeyGeneratorSpec.g3`, which loops only at the initial state — what licenses that is N1, valid there by the decidable `MapOfMonitor` criterion).
- [ ] 10.4 An unmapped event with no `disposition` row emits `Unknown` rather than a choice. An erasure the comparator invents is a decision nobody reviewed; an erasure the map declares has an owner, a written reason and provenance, and M2's job is to check it.
- [ ] 10.5 Quote the declared reason verbatim in the emitted verdict, so the erasure travels with its justification instead of pointing at a CSV the reader has to open.
- [ ] 10.6 Label **every** verdict `M2-decl` and attach the statement that a declared-automaton verdict says nothing about what the generated monitor accuses (INV-CONF-13). No unqualified "equivalent" is emitted anywhere.
- [ ] 10.7 Print the set of normalizations applied beside each verdict. A specification that only passes under N3 + N4 is saying something, and hiding which normalizations were used makes two incomparable verdicts look alike.
- [ ] 10.8 Implement the normalization catalogue as named, individually reportable rules: 1:N over aggregates; 1:1 with cross-renumbering; ε-erasure of the negated twin (now *declared*, per 10.3); **N1** parametric slicing (at most one creator event per monitor); **N2** projection of a non-observable symbol (`next(int)` is `protected`); **N3** acceptance ≠ every `alias match*`; **N4** overlapping pointcuts (now a construction step, per D-02, not a post-hoc normalization).
- [ ] 10.9 N1 is **not** a general rule — it is a property of the generated indexing tree, valid per specification by the `MapOfMonitor` criterion. Where it does not hold, M2 must not apply it. Feed this from M0.1 rather than re-deriving it.
- [ ] 10.10 **Recompute the `KeyGeneratorSpec` verdict** (`design.md`, Open Question 1). Its `ere` changed from `(g3* g1+ | g3* g2+) ((init gk1) | gk1)` to `(g3* g1+ | g3* g2+) (((init | initRandom | initRandomSize | initRandomSpec) gk1) | gk1)`, and the published verdict was computed over the first. The alphabet map already maps the four `init*` to the rule's `i1`…`i5`. Report the new verdict and state plainly whether it differs from the published one.
- [ ] 10.11 Re-emit the three verdicts whose automata are byte-identical to the earlier measurement (`MessageDigestSpec`, `SignatureSpec`, `SecureRandomSpec`) with the `M2-decl` label, the normalizations and the witness status. They are **results** rather than re-derivations, and saying so is worth a line.
- [ ] 10.12 Every witness carries `ABSTRACT` or `CONCRETE` and cannot be published with a false-positive claim beside it if `ABSTRACT` (INV-CONF-08). None of the current witnesses was executed; all are `ABSTRACT`.
- [ ] 10.13 `M2OrderTest` — the `SecureRandomSpec` verdict reads `M2-decl: MOP more permissive, under N1 + N2` with an `ABSTRACT` witness; the `CipherSpec` verdict is `INCOMPARÁVEIS` sustained **only** by the `regra \ MOP` direction (`g1 i2 i2 f2`), the other direction having died when gh105 task 6.6 made `f1`/`f2` disjoint.
- [ ] 10.14 Test 10.4: an unmapped event with no disposition row yields `Unknown`, not an erasure.
- [ ] 10.15 Test the overlap path end to end on `jca_android/IvChainJunction.mop`: `h` maps `Cipher.init(int, Key, AlgorithmParameterSpec, SecureRandom)` to `use useRandomSpec` in declaration order, and a non-statically-decidable guard yields `Unknown{OverlappingDispatch, labels: [...]}`.
- [ ] 10.16 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green.

## Closing
G10 closes when 10.1–10.16 are `[x]`.
