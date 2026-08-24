# G02 · lift CrySL

**Depends on:** G00. **Blocks:** G07, G08, G09, G10.
**Parallel with:** G01, G03, G04, G05.
**Size:** ~5 files in `rvsec-crysl-crysl`.

## Reference
- `specs/conformance/spec.md` — "CrySL Lift with a Fresh Reader per Rule", INV-CONF-04, -17
- `design.md` D-08 (fresh reader), D-09 (`android.jar` as index), D-19 (the EMF route names and locates)
- Oracle: `$W/rvsec-cognicrypt/CrySL-Rules/` (49 `.crysl`) — the single oracle (D-06)

## Tasks

- [ ] 2.1 `crysl/CryslLifter.java` — `SpecModel lift(Path, Version)`. Constructs a **new** `crysl.parsing.CrySLModelReader` for that rule alone (INV-CONF-04). No overload accepts a shared reader and no field holds one. The rules are read as-is: no lexical normalization exists (the five-substitution normalizer belonged to the abandoned `api30` corpus).
- [ ] 2.2 An ArchUnit rule forbidding a `CrySLModelReader` held in any field of the module. A configuration flag that reintroduces sharing is a flag that will eventually be set; make it impossible instead of discouraged.
- [ ] 2.3 Surface `resource.getErrors()` as `LiftFailure` per file (via the EMF provenance route — D-19), carrying the underlying `CrySLParserException`. A rule that does not load is a **finding**, not an incident: it does not abort the run.
- [ ] 2.4 `crysl/StateMachineAdapter.java` — `StateMachineGraph` → `Automaton` over `Signature` (INV-CONF-03): each `TransitionEdge`'s `CrySLMethod`s supply declaring type, method name and parameter types. Event and aggregate names (`Gets`, `Inits`, …) are **not** part of the comparison alphabet — `crysl/CryslProvenance.java` captures them, plus `file:line` via `NodeModelUtils`, on the EMF route for reporting and provenance only (D-19).
- [ ] 2.5 `crysl/ApiIndex.java` — index `android.jar` by class and by `(class, method, paramTypes)`, using ASM with `SKIP_CODE | SKIP_DEBUG | SKIP_FRAMES`. **Index only.** Document at the class why it is never wired into a parser classpath (INV-CONF-17): the virtual classpath is additive, `URLClassLoader` resolution is parent-first, and `java.base` comes from the module layer, so not even `parent = null` removes the host JDK.
- [ ] 2.6 `CryslLiftOracleTest` — the upstream corpus, un-normalized, gives `ok = 47, fail = 2`; the two failures are `OAEPParameterSpec` (uses the reserved word `alg` as an identifier) and `SSLEngine` (its `ORDER` references an event `cp1` that is declared `ep1`). Both are findings about the upstream files, recorded as such.
- [ ] 2.7 `test_inv_conf_04_order_invariance` — read the 49 upstream rules in 40 shuffled orders and assert `47` every time. The scope leak was measured on the upstream corpus itself — `SecretKey.crysl` read before `Key.crysl` breaks `Key.crysl` — and this is the only test that would catch a reintroduced shared reader.
- [ ] 2.8 `ApiIndexTest` — the index holds 4 750 classes for API 30; `javax.xml.crypto.dsig.spec.HMACParameterSpec` is absent; `java.security.spec.DSAGenParameterSpec` is absent; `javax.crypto.SecretKey.destroy()` resolves only through inheritance, which the index does not follow (a declared limitation, asserted so it stays declared).
- [ ] 2.9 One oracle; corpus identity stamped on every model anyway (INV-CONF-01): the lifter takes the corpus identity as a parameter and stamps it into `Version.corpus`, so a model can never be silently attributed to a corpus that did not produce it.
- [ ] 2.10 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-crysl -am test` green.

## Closing
G02 closes when 2.1–2.10 are `[x]`.
