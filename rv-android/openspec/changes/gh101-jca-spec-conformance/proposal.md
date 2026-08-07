# JCA Specification Conformance, Cipher Tables, and the Predicate Graph

GitHub Issue: #101

## Why

The two JCA specification sets carry defects that no allow-list change can reach. Two events are authored so that they can never behave: `TrustManagerFactorySpec:44` binds `k` instead of the specification parameter and lives in the empty parameter slice, and `SSLContextSpec:46` has no `returning` clause at all. Neither event appears in its own specification's `fsm`, so the generator assigns them `{3,3,3,3}` — transition to `fail` from every state. In the same file, `gtm1` carries three copy-and-paste defects from `KeyManagerFactorySpec`: the wrong `Property` constant, a `TrustManager[][]` binding, and a pointcut declaring a `KeyManager[]` return for `getTrustManagers()`, which never matches.

`CipherSpec` is the only one of the 23 without an allow-list of its own. It delegates to `isValid()` in `rvsec-core`, where the mode and padding tables are method locals covering exactly two algorithm families. The derived Android rule admits eight. The result is a set that contradicts itself: `KeyGeneratorSpec` accepts `ChaCha20`, `DESede`, `BLOWFISH` and `ARC4` because the platform publishes them, while any `Cipher.getInstance` over them is reported as misuse. Divergences run in both directions, so this is not conservatism — it is a second hand translation of the rules that the derivation exists to avoid.

The predicate graph is the largest defect by count and the least visible. The translation writes predicates faithfully and almost never reads them: 83% of the CrySL `ENSURES` clauses have a counterpart, only 22% of the `REQUIRES` have a reader, and 20 of the 23 `Property` constants do not function as an edge at all. `SSLContextSpec` reads none of its three `REQUIRES`, so a TLS context assembled from unvalidated key and trust managers raises nothing. Worse, nothing links the constant written to the constant read — at compile time or at runtime — so a wrong constant fails silently, and two already do.

**One thing that is explicitly not a defect, and this change must not "fix" it.** The diff between `jca` and `jca_android` is allow-list only, and that is the correct outcome. The Android set was **derived** through MetaCrySL rather than translated a second time by hand, and the platform-dependent part of a CrySL rule is precisely the membership constraint: `ORDER`, `REQUIRES`, `ENSURES` and `NEGATES` do not vary with API level. Everything above is therefore corrected identically in **both** sets, and any divergence outside allow-lists would be a regression of the derivation. What this change does add on that axis is verification: the derivation anchored ten files to a generated rule and kept thirteen verbatim, of which only three have a stated reason. Re-checking all 23 against the 33 generated rules for API 30 turns a prose traceability table into a conferrable artefact.

## What Changes

- **Layer-2 authoring defects, in both sets.** `TrustManagerFactorySpec`: rename the `g3` binding, add the event to the `fsm`, and correct the three `gtm1` defects at `:62-65`. `SSLContextSpec`: add `returning(SSLContext ctx)` at `:46` and add `unsafe_protocol` to the `fsm`. The `fsm` half is not optional — fixing the binding alone makes every algorithm outside the allow-list emit a spurious `InvalidSequenceOfMethodCalls`.
- **`isValid` parameterised.** `CipherTransformationUtil` takes its mode and padding tables from the same derivation that produced the Android rules, with the specification set selecting which tables apply. The `jca` behaviour is preserved exactly. The duplicated `PKCS5PADDING` entries and the commented `rsaECBPaddings` block go with it.
- **Predicate graph reconnected.** 23 translation defects corrected in `.mop` (including the two wrong constants at `KeyPairSpec.mop:38` and `TrustManagerFactorySpec.mop:65`); 11 edges that need a new `Property` constant added in `rvsec-core` and read in their specifications; 2 deliberate omissions and 1 inexpressible edge recorded with their reason.
- **A guard against silent constant defects.** A test derived from the write/read inventory cross-checks the `Property` constants written against those read, so a wrong constant cannot fail silently again.
- **CrySL conformance re-checked.** Each of the 23 `jca_android` allow-lists is verified against its generated `.cryptsl` rule for API 30, including confirmation that each of the thirteen files kept verbatim is genuinely uncontradicted by any rule. The result is committed as an artefact.
- **Set parity as a criterion.** After each task group, the diff between the two sets is checked mechanically and must contain allow-list differences only.
- **The replication consequence recorded.** Exact reproduction of the published numbers no longer holds (decision D1), and the derived Android profile models availability rather than recommendation — `MessageDigest` admits `MD5` and `SHA-1` — so a drop in the violation count is not evidence of better code.

## Capabilities

### New Capabilities

None. This change repairs and constrains behaviour the `instrumentation` capability already claims.

### Modified Capabilities

- `instrumentation`: the `Specification Set Support (FR03)` requirement describes the two JCA sets as collections of `.mop` files and enumerates them, but says nothing about what relates them, what may differ between them, or what governs their content. The delta states three things it does not state today: that the Android set is derived from generated CrySL rules and that its only admissible divergence from `jca` is the allow-list; that the platform-independent parts of a specification are corrected in both sets identically; and that a `Property` predicate written by one specification and read by another is a contract with a checkable invariant rather than a convention.

## Impact

**Sibling Java reactor** — all of the source work:

| Path | What changes |
|---|---|
| `rvsec/rvsec-mop/src/main/resources/jca` | 23 `.mop`: binding, `fsm`, `gtm1`, predicate-graph edges |
| `rvsec/rvsec-mop/src/main/resources/jca_android` | the same 23, identically outside allow-lists |
| `rvsec/rvsec-core/.../mop/Property.java` | 11 new constants |
| `rvsec/rvsec-core/.../mop/jca/util/CipherTransformationUtil.java` | `isValid` parameterised; hygiene |

**Read-only reference**: `MetaCrySL/generated/api30/` (33 `.cryptsl` rules). That tree is not modified by this change.

**`rv-android`**: no source change. Only the OpenSpec artefacts and the committed conformance and inventory artefacts live here.

**Requirements**: FR03 (specification set support), FR01/FR02 indirectly (monitor generation and instrumentation consume these specifications), NFR07. To be confirmed line by line against `docs/PRD.md` during the specs phase.

**Depends on** issue #100, for one thing only: the empirical verification of `TrustManagerFactorySpec` and `SSLContextSpec` needs the wrapper-collision fix (its task 5.3) integrated, because the corrected allow-list is compared against a variable that the collision prevents from being written. Every other part of this change is independent of #100 and does not wait for it.

**Consequence for the record**: the numbers published from the `jca` set were measured against the defective specifications. Correcting them in both sets is decision D1, taken with the replication cost accepted and recorded.
