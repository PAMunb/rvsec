# G11 · mop.lower + round-trip gate

**Depends on:** G01 and G03. **Blocks:** G12.
**Parallel with:** G06–G10.
**Size:** ~4 files in `rvsec-crysl-mop`.

## Reference
- `specs/conformance/spec.md` — "MOP Lower and the Two-Layer Round-Trip Gate"
- `design.md` D-12 (why two layers with different standing), §Non-Goals (`crysl.lower` out of scope; D-14 is the two-stage ad-hoc retirement)

## Tasks

- [ ] 11.1 `mop/MopLowerer.java` — `SpecModel` → `MOPSpecFile` → `DumpVisitor` → text. **Never `StringBuilder`.** Writing through the technology's own writer is what keeps the emitter honest about what the AST can express.
- [ ] 11.2 `crysl.lower` is **out of scope** (`design.md` §Non-Goals; the spec records the same cut). Record the reason in the package documentation — no known consumer, and the CrySL project ships no formatter, so it would cost ~400 lines of pretty-printer for output nobody reads — so a later reader does not treat its absence as an oversight and add it. The post-oracle-switch reassessment **confirmed** the cut: with `MetaCrySL` abandoned, a generated `.crysl` has no consumer at all.
- [ ] 11.3 `mop/RoundTripGate.java` — **Layer 1 is the gate**: the non-normalized AST checker over the *generated* tree — identifiers unique, formula alphabet ⊆ identifiers, every declared event reachable, every `@match` paired with a `@fail`, every pointcut resolving against `ApiIndex`. Reuse the M0 checker; it is the same piece.
- [ ] 11.4 **Layer 2 is evidence, not the gate**: product search against the rule, with the applied normalizations printed beside the verdict. Document why: an equivalence gate compares the generator's output against the rule *through the same normalization layer the comparator uses*, so it cannot see a defect living inside its own quotient.
- [ ] 11.5 Assert the two failure modes Layer 2 provably cannot catch, each with its corpus witness: **a declared event absent from the `ere`** gains an all-`fail` transition row and accuses every live monitor of the specification when it fires (`PBEKeySpecSpec.mop:26-32` records this having happened) — and it is local, and ε-normalization can even erase it; **`@match` without `@fail`** produces a specification that compiles, runs and never accuses (`SecretKeySpec.mop` and `RandomStringPassword.mop` are exactly that today) — and it is about handlers, so two specifications differing only in the handler have identical languages.
- [ ] 11.6 Round-trip test: lower a `SpecModel` and lift the result; the two models agree on type, objects, events in declaration order, order automaton, constraints and predicates. Report disagreements **per field**, never as one boolean — a boolean tells the implementer nothing about where to look.
- [ ] 11.7 Test that Layer 1 fails a generated specification with an event absent from the `ere` **even when Layer 2 finds the languages equivalent**. This is the test that justifies the two-layer split; without it the split is an assertion.
- [ ] 11.8 Comments are discarded on lower, by the recorded decision that they cannot be faithfully round-tripped. State it in the Javadoc so the loss is declared rather than discovered.
- [ ] 11.9 `RoundTripGateTest` green over at least three real specifications drawn from different formalisms (two `ere`, one `fsm`).
- [ ] 11.10 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-mop -am test` green.

## Closing
G11 closes when 11.1–11.10 are `[x]`.
