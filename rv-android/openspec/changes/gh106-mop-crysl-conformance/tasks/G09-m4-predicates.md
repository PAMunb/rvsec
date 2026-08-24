# G09 · M4 predicates

**Depends on:** G01 and G02. **Blocks:** G12.
**Parallel with:** G06, G07, G08, G10, G11.
**Size:** ~5 files in `rvsec-crysl-core`.

M4 is where the judgement columns get a derivable home. That is a named deliverable, not a side
effect of building the graph.

## Reference
- `specs/conformance/spec.md` — "M4 Predicate Graph with Declared Provenance of Judgement", INV-CONF-15
- `design.md` D-06

## Tasks

- [ ] 9.1 `metric/M4Predicates.java` — build the `ENSURES`/`REQUIRES`/`NEGATES` graph of the specification and of the rule, and compare by **arity, polarity and argument position**. Emit edges present, absent and inverted.
- [ ] 9.2 Handle **both substrates**: the new `PredicateStore` in `jca_android` (arity N, identity-keyed, three-valued, with `validateAbsent`) and the old `ExecutionContext` in the frozen `jca` (arity 1, `equals`-keyed, boolean, no `validateAbsent`). Reading only one makes the historical comparison impossible, and the historical comparison is what the published measurements live in.
- [ ] 9.3 Record the structural ceiling of substrate A as a property of the **frozen set**, not of the current one: in a file that uses only `ExecutionContext`, a clause of arity 2 or a negated clause is inexpressible however good the specification is. The current `jca_android` has zero `ExecutionContext` sites, so this ceiling no longer binds it.
- [ ] 9.4 Emit **both vocabularies** side by side (G04 task 4.4): the site-level `disposition`/`verdict` of `predicate_graph.csv` and the clause-level fidelity class. They describe different objects — the CSV describes a site, the fidelity class describes a clause — and there is no bijection between them.
- [ ] 9.5 Mark every row `derived` or `inherited`, and attach the human-judgement caveat to every aggregate (INV-CONF-15). Publish the derived fraction: it is the honest measure of how much of the manual table the component has actually replaced, and it should rise across the change.
- [ ] 9.6 Detect **predicate propagation across type conversions** — a producer that ensures over one object and a consumer that requires over another. Decidable from the graph in two ways: incompatible producer/consumer types, or identity keying over a value that is recreated. This is the class of defect the `RandomStringPassword` bridge exhibits, and it is a finding the component contributes rather than one it inherits.
- [ ] 9.7 Every M4 aggregate carries the commit stamp and the counting rule (INV-CONF-02). Emit the measured trajectory of the substrate signature as context — `64/21/5` → `47/26/7` → `28/35/12` → `0/45/19` → `0/70/21` over four days — so a reader sees why the stamp is a requirement rather than a formality.
- [ ] 9.8 **Do not publish the four parcels of the `fiéis + fiação + substrato + cobertura` decomposition as scalars.** The structure is correct and the substrate parcel is measurably paid; the other three depend on the judgement columns, which is exactly what 9.5 is resolving. Emit the structure with the commit and the derived fraction; emit the scalars only for rows marked `derived`.
- [ ] 9.9 `M4PredicatesTest` — arity, polarity and position compared correctly on hand-built pairs; a `REQUIRES` whose `Property` has no reachable producer is detected from the graph (the case the adjudication recorded as a measured precedent).
- [ ] 9.10 Test 9.6 on the known witness: a producer ensuring over a `byte[]` and a consumer requiring over the `char[]` obtained through `String.valueOf(Object).toCharArray()`. The edge is reported broken with the type incompatibility named.
- [ ] 9.11 Test that both substrates lift into the same graph shape, so `jca` and `jca_android` are comparable.
- [ ] 9.12 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green.

## Closing
G09 closes when 9.1–9.12 are `[x]`.
