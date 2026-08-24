# G08 · M3 constraints

**Depends on:** G01 and G02. **Blocks:** G12.
**Parallel with:** G06, G07, G09, G10, G11.
**Size:** ~5 files in `rvsec-crysl-core`.

## Reference
- `specs/conformance/spec.md` — "M3 Constraint Census by Idiom"
- `design.md` D-06 (one oracle; `api30` abandoned), D-11 (`Unknown`)

## Tasks

- [ ] 8.1 `metric/M3Constraints.java` — classify each rule clause by the idiom that implements it: **A** `Arrays.asList(...)` plus `ConscryptAliasTable.matches(...)`; **B** direct arithmetic in a `condition(...)` or an event body over `args()`-bound variables; **C** a helper method declared inside the specification; **D** an external helper class in `rvsec-core`. Or absent.
- [ ] 8.2 Treat the **injected equality** as part of the semantics, not as decoration. Idiom A tests through `ConscryptAliasTable.matches()` and its 158 lines of aliases, so nine of eleven allow-lists that are literally identical to the rule are in fact **more permissive**. A literal extractor would report "conformant" where the correct verdict is "more permissive". Emit the alias-table dependency per clause; note that it is distributed very unevenly (Signature 55 lines, Cipher 29, Mac 24; **zero** for KeyStore, SSLContext and SecureRandom).
- [ ] 8.3 A clause whose idiom the reader does not recognise emits `Unknown{UnrecognizedConstraint, textoCru, site}` and is counted in the M3 `Unknown` total — **never** as absent. Without this, a minimal-scope extractor reports eleven implemented clauses as missing and the report lies with numbers that look like measurement.
- [ ] 8.4 The families the abandoned `api30` generation erased **do occur in the upstream oracle** and need a declared route each: `instanceOf` (4 clauses, `Cipher.crysl:88` — idiom D, the external transformation helper, and exact at runtime); `alg()`/`mode()`/`pad()` string parts (26 occurrences, all in `Cipher.crysl` — idiom D, the transformation split helper); `notHardCoded` (4 clauses in 4 rules — untranslatable, routed to `Unknown{UntranslatableConstraint}` like `neverTypeOf`). Record each route so a later reader neither adds a speculative recogniser nor counts these clauses absent (the `docs/20260824_mapeamento_mop_crysl.md` matrix carries the per-family statute).
- [ ] 8.5 Emit `Unknown{UntranslatableConstraint, clause, family, site}` for the clauses that are properties of the origin's static type or of `ORDER` symbols rather than of runtime values: the seven `neverTypeOf[..., java.lang.String]` (five rules), the four `notHardCoded[...]`, and `callTo` (`noCallTo` maps — prohibition is safety; the obligation `callTo` does not — liveness without end-of-trace). A comment is not countable and does not enter a metric.
- [ ] 8.6 Declare the counting rule **R1** in code and emit it beside every denominator: one clause per `;` inside `CONSTRAINTS`, comments removed, `&&` conjunctions **not** split. Under other rules the same corpus gives 101/71 (splitting `&&`) or 117/87 (splitting the sides of `=>`), so any upstream number entering a publication needs its rule attached.
- [ ] 8.7 Report **two ceilings separately and never sum them**: the ceiling of the **subject** (clauses in rules with no specification) and of the **instrument** (idioms the extractor does not follow). The former third ceiling — the clauses `api30` lost relative to upstream — is now a method note, not a report line: it measured the corpus D-06 abandoned, and it is what explains *why* it was abandoned.
- [ ] 8.8 Record the `api30` loss as the method note behind D-06: `−33` net clauses across 16 rules under R1, 25 deleted across 12 of the 22 paired rules, classified per clause into deletion, operator corruption or predicate substitution. This goes in the report's method appendix — **not** a test assertion, because the component does not read `api30`.
- [ ] 8.9 `M3ConstraintsTest` asserts the upstream denominator under R1: `80` clauses in the 22 paired rules (`119` across all 49). The numerator is remeasured by the component, with the four `MOP-SEM-BASE` rows of `constraint_table.csv` re-examined against upstream as candidates for *implemented*. The committed `25/55 = 45,5 %` (`api30`-anchored) enters the test only as a **labelled historical reconciliation**, never as the asserted vector.
- [ ] 8.10 Carry the three `api30` corruption modes and their witnesses into the method note / historical appendix — none is a test assertion of the component: deletion on `DHGenParameterSpec` (upstream has `exponentSize < primeSize`, `api30` has nothing, and `jca_android/DHGenParameterSpecSpec.mop` implements it — so the `api30` column reads `MOP-SEM-BASE` while the specification is faithful); operator corruption on `api30/Cipher.cryptsl:131,133,135` (`length(x) <= off` where upstream writes `>=` in all four); predicate substitution on the `length[x] >= off+len; off >= 0; len > 0` triad replaced by `len > off`.
- [ ] 8.11 Assert that a specification faithful to upstream is **not** accused: with the upstream rules as the single oracle (D-06), a clause implemented exactly as upstream writes it can never be counted against the specification — the accusation mode the abandoned `api30` verdicts produced.
- [ ] 8.12 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green.

## Closing
G08 closes when 8.1–8.12 are `[x]`.
