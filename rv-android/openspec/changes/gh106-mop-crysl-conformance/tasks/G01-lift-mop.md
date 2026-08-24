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

- [ ] 1.1 `mop/MopLifter.java` — `SpecModel lift(Path, Version)`. Calls `MOPNameSpace.init()` **before each file** (INV-CONF-05). Document at the call site that the measured impact on the corpus is nil and the reason is determinism plus symmetry with the fresh CrySL reader — so a later reader does not delete it as dead code.
- [ ] 1.2 Mark the lifter **not thread-safe** and forbid parallel parsing: `JavaMOPParser` holds its instance in a static field. A comment is not enough — the API takes one path at a time and there is no batch overload that could tempt a `parallelStream`.
- [ ] 1.3 Survive the seven measured parser traps, one guard each, each with the measurement in the comment:
      (a) `BlockStmt.getStmts()` returns **`null`**, not an empty list, for `{ }` — and the corpus has several;
      (b) `MOPNameSpace` is a static global (covered by 1.1);
      (c) `JavaMOPParser` static instance (covered by 1.2);
      (d) `JavaParserAdapter` swallows exceptions from Java blocks — a malformed handler becomes a `null` `BlockStmt` with no warning, so `null` must be distinguished from "absent";
      (e) `getHandlers()` keys arrive lowercased (`@match1` → `"match1"`);
      (f) `BlockStmt` comes from the internal fork, not `com.github.javaparser` — to use the modern parser, re-parse `toString()`;
      (g) `getRetType()` is always `null`; the real return type is `MethodPattern.getType()` inside the `MethodPointCut`.
- [ ] 1.4 Build `Event` with `declIndex` from the AST order, and populate `signatures` by expanding the pointcut over the declared type — this is what makes the alphabet non-disjoint visible downstream.
- [ ] 1.5 `mop/PredicateIdioms.java` — recognise **both** substrates. Substrate A (`ExecutionContext`, arity 1, `equals`-keyed, boolean): `setProperty` → `ENSURES`, `validate` → `REQUIRES`, `remove` → `NEGATES`, `set/unsetObjectAsInAcceptingState` → CrySL accepting-state semantics. Substrate B (`PredicateStore`, arity N, identity-keyed, three-valued): `ensure(Property, bound, values...)` → `ENSURES` of arity ≥ 2, `validate(...)` → `SATISFIED | VIOLATED | NOT_OBSERVED`, `validateAbsent(...)` → the CrySL `!p[...]`.
- [ ] 1.6 Document at `PredicateIdioms` **why substrate A is still required**: the current `jca_android` has zero `ExecutionContext` sites, but the frozen `jca` uses it in all 23 files, and `jca` is the set the published TSE 2023 measurements were taken over. Any historical comparison must read both. Without this note a later reader will delete substrate A as dead.
- [ ] 1.7 `mop/FormulaParser.java` — mini-parser for `ere` and `fsm` text (`Formula.getFormula()` gives raw text). Emit an `Automaton` over labels; G03 lifts it to signatures. `ptltl` is out of scope: no specification of the corpus uses it, and the parser refuses it with a typed error rather than mis-parsing it.
- [ ] 1.8 Stamp `Provenance` (`file:line`) on every event, constraint and predicate reference **at lift time**. Provenance is stamped, never parsed back out of emitted text.
- [ ] 1.9 `MopLiftCorpusTest` — lift all five corpora and assert `215 files, 215 ok, 0 fail`, `905` events, `381` parameters, with the counting rules `spec.getEvents().size()` and `spec.getParameters().size()` asserted as data on the result, not just in the message.
- [ ] 1.10 `test_inv_conf_05_init_per_file` — a spy asserts `MOPNameSpace.init()` was called once per file.
- [ ] 1.11 Test the empty-handler distinction: a specification with `@match { }` lifts to "handler present and empty", not "handler absent". G06 depends on this distinction to refuse `RandomStringPassword`.
- [ ] 1.12 Test both substrates on real files: `jca/MacSpec.mop` yields an arity-1 `GENERATED_MAC` ensure (`ExecutionContext.instance().setProperty(Property.GENERATED_MAC, output)`, `jca/MacSpec.mop:73`); `jca_android/MacSpec.mop` yields a negated `REQUIRES` on the three-valued substrate at `:303`.
- [ ] 1.13 Run `/rv-doc-code` over the new files (or the Java equivalent: Javadoc on every public type, explaining *why* at each of the seven trap guards).
- [ ] 1.14 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-mop -am test` green.

## Closing
G01 closes when 1.1–1.14 are `[x]`.
