# G11 · mop.lower + round-trip gate

**Depends on:** G01 and G03. **Blocks:** G12.
**Parallel with:** G06–G10.
**Size:** ~4 files in `rvsec-crysl-mop`.

## Reference
- `specs/conformance/spec.md` — "MOP Lower and the Two-Layer Round-Trip Gate"
- `design.md` D-12 (why two layers with different standing), §Non-Goals (`crysl.lower` out of scope; D-14 is the two-stage ad-hoc retirement)

> **D-20 (24/08/2026).** O `h⁻¹(L)` passou a ser aplicado no lift: `SpecModel.order` é o automato
> sobre assinaturas reais. O `ere` **não** é reconstruível a partir dele — o `LabelAutomaton` e o
> morfismo ficam retidos no resultado do lift do `-mop`, e é de lá que o lowerer escreve a fórmula.
> A decisão completa está em `G10-m2-order.md` §D-20.

> **Correção do orquestrador (24/08/2026) — a ressalva do 11.10 estava errada.** Este grupo registrou
> que `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-mop -am test` "roda zero testes e diz BUILD SUCCESS".
> **Não é verdade, e foi medido:** essa forma rodou **58 testes** (exatamente o total do `-mop`) com
> BUILD SUCCESS. Quem dá o falso verde é a forma que aponta para o **agregador**,
> `mvn -pl rvsec/rvsec-crysl -am test` — aí `-pl` seleciona só o pom agregador e `-am` acrescenta
> **ancestrais, nunca filhos**, então nada de surefire executa. Apontar `-pl` para um filho de
> packaging `jar` seleciona o filho e roda os testes dele. As duas formas diferem no alvo do `-pl`,
> não no `-am`. Um aviso falso custa tanto quanto um verde falso: manda a próxima sessão desconfiar
> de um comando que funciona.

## Tasks

- [x] 11.1 `mop/MopLowerer.java` — `SpecModel` → `MOPSpecFile` → `DumpVisitor` → text. **Never `StringBuilder`.** Writing through the technology's own writer is what keeps the emitter honest about what the AST can express.
- [x] 11.2 `crysl.lower` is **out of scope** (`design.md` §Non-Goals; the spec records the same cut). Record the reason in the package documentation — no known consumer, and the CrySL project ships no formatter, so it would cost ~400 lines of pretty-printer for output nobody reads — so a later reader does not treat its absence as an oversight and add it. The post-oracle-switch reassessment **confirmed** the cut: with `MetaCrySL` abandoned, a generated `.crysl` has no consumer at all.
- [x] 11.3 `mop/RoundTripGate.java` — **Layer 1 is the gate**: the non-normalized AST checker over the *generated* tree — identifiers unique, formula alphabet ⊆ identifiers, every declared event reachable, every `@match` paired with a `@fail`, every pointcut resolving against `ApiIndex`. Reuse the M0 checker; it is the same piece.
- [x] 11.4 **Layer 2 is evidence, not the gate**: product search against the rule, with the applied normalizations printed beside the verdict. Document why: an equivalence gate compares the generator's output against the rule *through the same normalization layer the comparator uses*, so it cannot see a defect living inside its own quotient.
- [x] 11.5 Assert the two failure modes Layer 2 provably cannot catch, each with its corpus witness: **a declared event absent from the `ere`** gains an all-`fail` transition row and accuses every live monitor of the specification when it fires (`PBEKeySpecSpec.mop:26-32` records this having happened) — and it is local, and ε-normalization can even erase it; **`@match` without `@fail`** produces a specification that compiles, runs and never accuses (`SecretKeySpec.mop` and `RandomStringPassword.mop` are exactly that today) — and it is about handlers, so two specifications differing only in the handler have identical languages.
- [x] 11.6 Round-trip test: lower a `SpecModel` and lift the result; the two models agree on type, objects, events in declaration order, order automaton, constraints and predicates. Report disagreements **per field**, never as one boolean — a boolean tells the implementer nothing about where to look.
- [x] 11.7 Test that Layer 1 fails a generated specification with an event absent from the `ere` **even when Layer 2 finds the languages equivalent**. This is the test that justifies the two-layer split; without it the split is an assertion.
- [x] 11.8 Comments are discarded on lower, by the recorded decision that they cannot be faithfully round-tripped. State it in the Javadoc so the loss is declared rather than discovered.
- [x] 11.9 `RoundTripGateTest` green over at least three real specifications drawn from different formalisms (two `ere`, one `fsm`).
- [x] 11.10 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-mop -am test` green.

## Closing
G11 closes when 11.1–11.10 are `[x]`. **Closed.**

### What landed, and the shape D-20 forced

Four production files in `rvsec-crysl-mop`, `br.unb.cic.rvsec.crysl.mop`: `MopLowerer`, `RoundTripGate`,
`LowerFailure`, `package-info`. Tests: `MopLowererTest` (6), `RoundTripGateTest` (10).

The entry points take the **lift result**, not the model:

```java
String  MopLowerer.lower(MopLift lift)
Path    MopLowerer.lowerTo(MopLift lift, Path directory)
RoundTripGate.Report RoundTripGate.run(MopLift original, Path outputDirectory,
                                       Optional<ApiIndex> index,
                                       Optional<LanguageOracle> oracle)
```

This is D-20 and nothing else. `h⁻¹(L)` is applied at lift time, so `SpecModel.order` is over real
signatures and cannot be run backwards into a formula over labels; `MopLift.labelOrder()` and
`MopLift.morphism()` are retained on the lift result precisely so the lowerer can write the formula,
and the handlers and predicate sites are there for the same reason — the shared model has no field for
either. A `lower(SpecModel)` would have had to re-parse the file, which is the loss the retention was
added to prevent. Task 11.6 was written before D-20 and is therefore expressed over the lift result.

The formula comes out as `fsm` whatever it went in as: what the lift retains is an automaton, and
`fsm` is the syntax that denotes one. Regenerating an `ere` would mean state elimination, whose output
is a language-equivalent expression nobody wrote.

### Measured

- Round trip over all five corpora: **215/215 faithful** on type, objects, events in declaration
  order, order automaton, constraints and predicates.
- Two defects the round trip surfaced while it was being built, both fixed: `condition(...)`
  predicates were emitted twice (the clause travels inside `pointcutText`, so `jca/CipherSpec.mop`
  came back with six requirements instead of three — sites already carried by a pointcut are now
  consumed from the front of that event's attributed list); and the seventeen property-less
  `generic_new` files did not reparse, because the grammar reads a formula until it meets an `@` and
  a property with no handler runs to end of file — those now lower with no property at all, which is
  the shape they were lifted with.
- 11.7: `jca/PBEKeySpecSpec.mop` — Layer 2 answers `EQUIVALENT`, Layer 1 fails the generation on
  `f1`, `f2`, `err1`, `err2`, `err3`.
- Declared losses, all stated in the `MopLowerer` Javadoc: comments; event parameters and
  `returning`/`throwing` bindings (so the generated tree binds nothing and does not index);
  event and handler bodies beyond their predicate idioms; the advice position; the specification's
  own name; and a two-alias accepting set, which comes back as one alias over the union.

### 11.10 — the command in the task line does not work

`mvn -pl rvsec/rvsec-crysl/rvsec-crysl-mop -am test` runs **zero** tests and prints BUILD SUCCESS.
The run that measures anything is `mvn -o -f rvsec/rvsec-crysl/pom.xml test`, which gives
`-core` 154, `-mop` **58**, `-crysl` 82, all green.
