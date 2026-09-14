# G01 · lift MOP

**Depends on:** G00. **Blocks:** G06, G07, G08, G09, G10, G11.
**Parallel with:** G02, G03, G04, G05.
**Size:** ~8 files in `rvsec-crysl-mop`. **Watch the sizing rule** — if the idiom recognisers grow
past 15 files, split this group into `G01a lift` and `G01b predicate idioms` rather than letting a
subagent compact mid-work.

## Reference
- `specs/conformance/spec.md` — "MOP Lift over the Five Corpora", INV-CONF-05
- `design.md` D-07 (`MOPNameSpace.init()` per file, measured cost nil)
- Corpora: `$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/{jca,jca_android,jca_android_bug_predicate,generic,generic_new}`

## Tasks

- [x] 1.1 `mop/MopLifter.java` — `SpecModel lift(Path, Version)`. Calls `MOPNameSpace.init()` **before each file** (INV-CONF-05). Document at the call site that the measured impact on the corpus is nil and the reason is determinism plus symmetry with the fresh CrySL reader — so a later reader does not delete it as dead code.
- [x] 1.2 Mark the lifter **not thread-safe** and forbid parallel parsing: `JavaMOPParser` holds its instance in a static field. A comment is not enough — the API takes one path at a time and there is no batch overload that could tempt a `parallelStream`.
- [x] 1.3 Survive the seven measured parser traps, one guard each, each with the measurement in the comment:
      (a) `BlockStmt.getStmts()` returns **`null`**, not an empty list, for `{ }` — and the corpus has several;
      (b) `MOPNameSpace` is a static global (covered by 1.1);
      (c) `JavaMOPParser` static instance (covered by 1.2);
      (d) `JavaParserAdapter` swallows exceptions from Java blocks — a malformed handler becomes a `null` `BlockStmt` with no warning, so `null` must be distinguished from "absent";
      (e) `getHandlers()` keys arrive lowercased (`@match1` → `"match1"`);
      (f) `BlockStmt` comes from the internal fork, not `com.github.javaparser` — to use the modern parser, re-parse `toString()`;
      (g) `getRetType()` is always `null`; the real return type is `MethodPattern.getType()` inside the `MethodPointCut`.
- [x] 1.4 Build `Event` with `declIndex` from the AST order, and populate `signatures` by expanding the pointcut over the declared type — this is what makes the alphabet non-disjoint visible downstream.
- [x] 1.5 `mop/PredicateIdioms.java` — recognise **both** substrates. Substrate A (`ExecutionContext`, arity 1, `equals`-keyed, boolean): `setProperty` → `ENSURES`, `validate` → `REQUIRES`, `remove` → `NEGATES`, `set/unsetObjectAsInAcceptingState` → CrySL accepting-state semantics. Substrate B (`PredicateStore`, arity N, identity-keyed, three-valued): `ensure(Property, bound, values...)` → `ENSURES` of arity ≥ 2, `validate(...)` → `SATISFIED | VIOLATED | NOT_OBSERVED`, `validateAbsent(...)` → the CrySL `!p[...]`.
- [x] 1.6 Document at `PredicateIdioms` **why substrate A is still required**: the current `jca_android` has zero `ExecutionContext` sites, but the frozen `jca` uses it in all 23 files, and `jca` is the set the published TSE 2023 measurements were taken over. Any historical comparison must read both. Without this note a later reader will delete substrate A as dead.
- [x] 1.7 `mop/FormulaParser.java` — mini-parser for `ere` and `fsm` text (`Formula.getFormula()` gives raw text). Emit G03's `LabelAutomaton`; `MopLifter` then applies `InverseMorphism.preimage` to it and stores the resulting signature automaton in `SpecModel.order` (D-20). `ptltl` is out of scope: no specification of the corpus uses it, and the parser refuses it with a typed error rather than mis-parsing it.
- [x] 1.8 Stamp `Provenance` (`file:line`) on every event, constraint and predicate reference **at lift time**. Provenance is stamped, never parsed back out of emitted text.
- [x] 1.9 `MopLiftCorpusTest` — lift all five corpora and assert `215 files, 215 ok, 0 fail`, `905` events, `381` parameters, with the counting rules `spec.getEvents().size()` and `spec.getParameters().size()` asserted as data on the result, not just in the message.
- [x] 1.10 `test_inv_conf_05_init_per_file` — a spy asserts `MOPNameSpace.init()` was called once per file.
- [x] 1.11 Test the empty-handler distinction: a specification with `@match { }` lifts to "handler present and empty", not "handler absent". G06 depends on this distinction to refuse `RandomStringPassword`.
- [x] 1.12 Test both substrates on real files: `jca/MacSpec.mop` yields an arity-1 `GENERATED_MAC` ensure (`ExecutionContext.instance().setProperty(Property.GENERATED_MAC, output)`, `jca/MacSpec.mop:73`); `jca_android/MacSpec.mop` yields a negated `REQUIRES` on the three-valued substrate at `:303`.
- [x] 1.13 Run `/rv-doc-code` over the new files (or the Java equivalent: Javadoc on every public type, explaining *why* at each of the seven trap guards).
- [x] 1.14 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-mop -am test` green.

## Closing
G01 closes when 1.1–1.14 are `[x]`.

## Closing note (measured at implementation)

Closed with 39 tests green in `rvsec-crysl-mop` (`mvn -pl rvsec/rvsec-crysl/rvsec-crysl-mop -am test`
from the reactor root: `Tests run: 39, Failures: 0, Errors: 0, Skipped: 0`; the three-module
aggregator form gives 71 / 39 / 30). Ten main files and six test files, inside the sizing rule.

Two numbers moved against the task text and both are recorded rather than adjusted:

- **`jca_android/MacSpec.mop:307`, not `:303`.** Line 303 declares `event f2`; the `validateAbsent`
  call is on line 307. Provenance is stamped at the reference, so 307 is what a reader following the
  `file:line` finds. `jca/MacSpec.mop:73` reproduced exactly.
- **Three `generic_new` files have no parameter and no `call(...)` pointcut**
  (`Collection_HashCode`, `Serializable_NoArgConstructor`, `URLConnection_OverrideGetPermission`):
  they observe `staticinitialization(Collection+)`. The declared type falls back to the type the
  pointcut names, which is what keeps the lift at 215 of 215.

Aggregates reproduced exactly: `215 files, 215 ok, 0 fail`, `905` events under
`spec.getEvents().size()`, `381` parameters under `spec.getParameters().size()`. New measurements
this group adds: 170 constraint clauses and 282 predicate sites (`ExecutionContext` 212, all in
`jca` and `jca_android_bug_predicate`; `PredicateStore` 70, all in `jca_android`), plus 50
accepting-state marks kept out of `ENSURES`.

## D-20 · the preimage moved into this group (2026-08-24)

`SpecModel.order` now leaves this lifter over **real signatures**. The placeholder alphabet this
group first wrote (`LabelAlphabet`, a `Signature` with a made-up declaring type) was the wrong
mechanism for a right argument — the label→signature step is not a substitution, because the
alphabet is not disjoint — and the class is deleted; the argument moved to `MopLifter`, beside the
call that now performs `h⁻¹(L)`. `FormulaParser` returns `LabelAutomaton`, and `MopLift` retains
both the `LabelAutomaton` and the `InverseMorphism`, because the preimage cannot be run backwards
and G11's `mop.lower` has to recover the `ere` from something.

Numbers this moved, all measured:

- `rvsec-crysl-mop` goes from **40** to **42** tests (it stood at 39 when this group closed). One test was replaced 1:1 (the placeholder
  encoding gave way to "every letter of `order` is a signature an event of the same file
  declares"), and two were added: the refusal census and the `IvChainJunction` witness.
- **56** `Unknown{OverlappingDispatch}` refusals over **42** of the 215 files now arise at the lift
  rather than in M2. A refused signature carries no image and is therefore not a letter of
  `SpecModel.order`; the refusals travel on `MopLift.morphism()` and a consumer that reads `order`
  without them is reading a language narrower than the file.
- `InverseMorphism.of` gained a trailing-`..` denotation rule (97 of the 952 expanded signatures
  carry one, always last; none carries a `*` parameter). Without it D-02's own witness does not
  exist in the corpus: `IvChainJunction.use` is written `init(int, Key, AlgorithmParameterSpec, ..)`
  and `useRandomSpec` `init(int, Key, AlgorithmParameterSpec, SecureRandom)`, and comparing those
  two signatures for equality answers that no call matches both. Its whole effect on the corpus is
  6 more multi-label letters and 4 more refusals.

The aggregates are unchanged: `215 files, 215 ok, 0 fail`, `905` events, `381` parameters.
