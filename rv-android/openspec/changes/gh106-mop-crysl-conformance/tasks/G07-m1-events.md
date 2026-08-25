# G07 · M1 events

**Depends on:** G01 and G02. **Blocks:** G10 (label alignment), G12.
**Parallel with:** G06, G08, G09, G10, G11.
**Size:** ~3 files in `rvsec-crysl-core`. Small on purpose — M1 is the cheapest metric and it feeds M2.

## Reference
- `specs/conformance/spec.md` — "M1 Event Coverage against the Oracle", INV-CONF-11

## Tasks

- [x] 7.1 `metric/M1Events.java` — compare the set of concrete signatures the `.mop` events match against the set the rule's `EVENTS` declares. Emit coverage **plus both differences**: MOP-only signatures and rule-only signatures.
- [x] 7.2 The emitter refuses a coverage percentage without both lists beside it. A single coverage number is exactly the kind of scalar the reporting discipline of this capability exists to prevent.
- [x] 7.3 Emit the report header that names the oracle — repository and commit — and the pairing rule beside every M1 table (INV-CONF-11).
- [x] 7.4 Produce the label-alignment table M2 consumes: which MOP label corresponds to which rule symbol, derived from the signature-set intersection rather than from name heuristics. No heuristic gets `g3 ↦ gI` or `setSeed1 ↦ s2` right; only the mapping does.
- [x] 7.5 Pairing by declared type: 22 of 24 against the upstream rules, the two unpaired being `IvChainJunction` and `RandomStringPassword` — exactly the two the alphabet map declares as skips, which is a consistency check on the corpus and should be asserted as one.
- [x] 7.6 **The pairing rule is resolved** (`design.md`, Open Question 2): pair the rule's `SPEC` FQN against the type of the specification's declared parameter (the pointcut's declaring type for the two parameterless specifications). Implement it, emit it in every report header (INV-CONF-11), and test it — including the case file-name pairing cannot resolve: `SecretKeySpec.mop` pairs with `SecretKey.crysl` while `SecretKeySpecSpec.mop` pairs with `SecretKeySpec.crysl`. Pairing by file name is forbidden.
- [x] 7.7 `M1EventsTest` on `jca_android/MessageDigestSpec.mop` against upstream `MessageDigest.crysl`: the aggregate `update ↦ {u1..u4}` expansion appears in the alignment, and both difference lists are non-empty and correct.
- [x] 7.8 Test the 22-of-24 pairing and the two declared skips.
- [x] 7.9 `mvn -pl rvsec/rvsec-crysl/rvsec-crysl-core test` green.

## Closing
G07 closes when 7.1–7.9 are `[x]`.
