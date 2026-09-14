# G09 · M4 predicates

**Depends on:** G01 and G02. **Blocks:** G12.
**Parallel with:** G06, G07, G08, G10, G11.
**Size:** ~5 files in `rvsec-crysl-core`.

M4 is where the judgement columns get a derivable home. That is a named deliverable, not a side
effect of building the graph.

## Reference
- `specs/conformance/spec.md` — "M4 Predicate Graph with Declared Provenance of Judgement", INV-CONF-15
- `design.md` D-06

> **Carimbo do corpus (24/08/2026).** Os alvos e as asserções deste arquivo estão fixados em
> `5fbe8173`, que é **ancestral** do HEAD, não o HEAD. O commit `5bc5c893` reescreveu as listas
> de valor (`Arrays.asList(...)`) de 13 das 24 specs do `jca_android`; as fórmulas `ere`/`fsm`
> ficaram byte a byte idênticas. A nota completa, com as regras de contagem, está em
> `G12-corpus-calibration.md` §"O corpus moveu durante a implementação" — **leia-a antes de
> carimbar qualquer número deste grupo.**

## Tasks

- [x] 9.1 `metric/M4Predicates.java` — build the `ENSURES`/`REQUIRES`/`NEGATES` graph of the specification and of the rule, and compare by **arity, polarity and argument position**. Emit edges present, absent and inverted.
- [x] 9.2 Handle **both substrates**: the new `PredicateStore` in `jca_android` (arity N, identity-keyed, three-valued, with `validateAbsent`) and the old `ExecutionContext` in the frozen `jca` (arity 1, `equals`-keyed, boolean, no `validateAbsent`). Reading only one makes the historical comparison impossible, and the historical comparison is what the published measurements live in.
- [x] 9.3 Record the structural ceiling of substrate A as a property of the **frozen set**, not of the current one: in a file that uses only `ExecutionContext`, a clause of arity 2 or a negated clause is inexpressible however good the specification is. The current `jca_android` has zero `ExecutionContext` sites, so this ceiling no longer binds it.
- [x] 9.4 Emit **both vocabularies** side by side (G04 task 4.4): the site-level `disposition`/`verdict` of `predicate_graph.csv` and the clause-level fidelity class. They describe different objects — the CSV describes a site, the fidelity class describes a clause — and there is no bijection between them.
- [x] 9.4-bis **Fill `CsvEmitter.M4Row`, the row-level contract G04 built.** The committed
  `predicate_graph.csv` schema needs per-row data that is *not* derivable from `M4Result`, which
  carries `List<PredicateRef>` plus two row **counts**. So the metric must hand the emitter one
  `M4Row` per site, each with its `fidelity` (clause-level) and `origin` (`derived`/`inherited`).
  G04 emits `fidelity` and `origin` as two **appended** columns — the committed header stays an
  exact prefix, so `csv.DictReader` in `scripts/` keeps working. **Assert that
  `M4Result.derivedRows`/`inheritedRows` agree with the rows actually handed to the emitter**:
  nothing cross-checks that today, and an aggregate that disagrees with its own rows is the
  failure INV-CONF-15 is about.

- [x] 9.5 Mark every row `derived` or `inherited`, and attach the human-judgement caveat to every aggregate (INV-CONF-15). Publish the derived fraction: it is the honest measure of how much of the manual table the component has actually replaced, and it should rise across the change.
- [x] 9.6 Detect **predicate propagation across type conversions** — a producer that ensures over one object and a consumer that requires over another. Decidable from the graph in two ways: incompatible producer/consumer types, or identity keying over a value that is recreated. This is the class of defect the `RandomStringPassword` bridge exhibits, and it is a finding the component contributes rather than one it inherits.
- [x] 9.7 Every M4 aggregate carries the commit stamp and the counting rule (INV-CONF-02). Emit the measured trajectory of the substrate signature as context — `64/21/5` → `47/26/7` → `28/35/12` → `0/45/19` → `0/70/21` over four days — so a reader sees why the stamp is a requirement rather than a formality.
- [x] 9.8 **Do not publish the four parcels of the `fiéis + fiação + substrato + cobertura` decomposition as scalars.** The structure is correct and the substrate parcel is measurably paid; the other three depend on the judgement columns, which is exactly what 9.5 is resolving. Emit the structure with the commit and the derived fraction; emit the scalars only for rows marked `derived`.
- [x] 9.9 `M4PredicatesTest` — arity, polarity and position compared correctly on hand-built pairs; a `REQUIRES` whose `Property` has no reachable producer is detected from the graph (the case the adjudication recorded as a measured precedent).
- [x] 9.10 Test 9.6 on the known witness: a producer ensuring over a `byte[]` and a consumer requiring over the `char[]` obtained through `String.valueOf(Object).toCharArray()`. The edge is reported broken with the type incompatibility named.
- [x] 9.11 Test that both substrates lift into the same graph shape, so `jca` and `jca_android` are comparable.
- [x] 9.12 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green.

## Measured at closing

Files added, all in `rvsec-crysl-core` except the corpus test:
`core/metric/M4Predicates.java`, `PredicateGraph.java`, `PredicateSiteFacts.java`,
`PredicateSubstrate.java`, `PropagationBridge.java`, `SubstrateTrajectory.java`;
tests `core/metric/M4PredicatesTest.java` (+ `M4Fixtures`) and
`rvsec-crysl-crysl/.../M4PredicateCorpusTest.java` (two tests tagged `oracle-dependent`).

**Corpus stamp.** HEAD is `86a8f178`; the targets are pinned at `5fbe8173`. Re-measured under
`SubstrateTrajectory.COUNTING_RULE` at both: the `jca_android` signature is `0/70/21` at each, and
the **per-file distribution of the 70 sites is identical**, so the substrate did not move under M4.
The five published triples reproduce exactly at their own commits — `64/21/5` (`d64f3a40`),
`47/26/7` (`c12f4689`), `28/35/12` (`f188c55b`), `0/45/19` (`8a33bc41`), `0/70/21` (`5fbe8173`).
**What did move: the `file:line` of the sites, in 13 of the 24 files** (e.g. `MacSpec.mop` 303 → 307,
`SecretKeySpecSpec.mop` 80/134/199 → 110/172/237). A row keyed by provenance alone does not survive
the move; a row keyed by provenance *and* stamp does.

**Counting-rule correction.** `jca` has **85** recognised predicate sites, not the 110 the
`PredicateIdioms` Javadoc cites: 110 is the count of `ExecutionContext.instance()` occurrences and
25 of those are `setObjectAsInAcceptingState`/`unsetObjectAsInAcceptingState`, which are a guard on
an ENSURES and not a predicate. `110 − 25 = 85`, exactly. Both numbers are right under their own
rule; only one of them is M4's.

**M4 over `jca_android` × upstream, at `86a8f178`, with `Judgements.empty()`** (counting rule in
`M4Predicates.COUNTING_RULE`): 23 pairs, **50 present, 53 absent, 0 inverted**, 123 rows,
**103 derived → derived fraction 0.837**. The 23 is a local simple-name approximation of
INV-CONF-11's pairing and is stated as such (it reaches 23 where the rule of record reaches 22,
because `IvChainJunction.mop` declares `Cipher`).

**Propagation bridges: none found in the real corpus.** Both routes need something the current lift
does not supply — a declared type per argument position, or an argument expression that builds a
value at the site — and the corpora write plain identifiers. The graph *locates* the frozen `jca`
bridge (`RANDOMIZED` produced in `RandomStringPassword.mop`, consumed in `PBEKeySpecSpec.mop`) and
refuses to call it broken without evidence; the `byte[]`/`char[]` witness is asserted hand-built
(9.10). Populating `PredicateSiteFacts.argumentTypes` is the `-mop` lift's job, not M4's.

**Substrate ceiling, restated where the corpus contradicted the task text.** Arity > 1 on
`ExecutionContext` is `INEXPRESSIBLE`. A *negated* clause on `ExecutionContext` is **not**: the
frozen set writes it as `condition(! ...validate(p, x))` (`jca/PBEKeySpecSpec.mop:56`) and
`PredicateIdioms` lifts it to `NEGATED`. What substrate A loses is the third value, so that ceiling
is `DEGRADED` and such a site pairs as `PROJETADO`, never as `FIEL`. `jca_android` has zero
substrate-A sites, so neither ceiling binds it.

**Tests run:** `-core` **139**, `-mop` **42**, `-crysl` **62**, `BUILD SUCCESS`, via
`mvn -o -f rvsec/rvsec-crysl/pom.xml test` (JDK 25). G09 contributes 18 + 5 = 23 of those.

## Closing
G09 closes when 9.1–9.12 are `[x]`, **including 9.4-bis** — o contrato de linha que o G04 construiu.
Conferir o intervalo ao fechar (aprendizado nº 18).
