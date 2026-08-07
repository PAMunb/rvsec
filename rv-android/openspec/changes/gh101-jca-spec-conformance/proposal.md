# JCA Specification Conformance, Cipher Tables, and the Predicate Graph

GitHub Issue: #101

## Why

The two JCA specification sets carry defects that no allow-list change can reach. Two events are authored so that they can never behave: `TrustManagerFactorySpec:44` binds `k` instead of the specification parameter and lives in the empty parameter slice, and `SSLContextSpec:46` has no `returning` clause at all. Neither event appears in its own specification's `fsm`, so the generator assigns them `{3,3,3,3}` — transition to `fail` from every state. In the same file, `gtm1` carries three copy-and-paste defects from `KeyManagerFactorySpec`: the wrong `Property` constant, a `TrustManager[][]` binding, and a pointcut declaring a `KeyManager[]` return for `getTrustManagers()`, which never matches.

Those two events are the visible tip. Asserting the automaton-membership invariant over a generated monitor finds **eighteen** events with an all-`fail` transition row, not two: sixteen more, over eight further specifications, all of one shape — an error-reporting event with a negated or violating guard, which reports in its body and was never added to the `fsm`. Most of them bind the monitored object, so every firing produces the report its author intended **and** an `InvalidSequenceOfMethodCalls` on top of it. What that is worth in the published corpus:

| origin | `InvalidSequenceOfMethodCalls` | of the category | of all 97,018 errors |
|---|---:|---:|---:|
| the 8 specifications carrying the sixteen | 23,292 | 32.9% | 24.0% |
| `TrustManagerFactorySpec` and `SSLContextSpec` | 26,525 | 37.5% | 27.3% |
| **together** | **49,817** | **70.4%** | **51.3%** |

The dominant error type of the dataset is therefore produced, in the main, by events that were never meant to judge sequence at all — the concrete mechanism behind the co-emission the investigation measured. All eighteen are repaired in the derived set.

`CipherSpec` is the only one of the 23 without an allow-list of its own. It delegates to `isValid()` in `rvsec-core`, where the mode and padding tables are method locals covering exactly two algorithm families. The derived Android rule admits eight. The result is a set that contradicts itself: `KeyGeneratorSpec` accepts `ChaCha20`, `DESede`, `BLOWFISH` and `ARC4` because the platform publishes them, while any `Cipher.getInstance` over them is reported as misuse. Divergences run in both directions, so this is not conservatism — it is a second hand translation of the rules that the derivation exists to avoid.

The derived set is also not reachable by name. `ExperimentConfig.specification_set` admits `jca`, `generic` and `custom`, so `jca_android` can only be selected by pointing `custom_specs_dir` at its directory. That was tolerable while the two sets were identical outside allow-lists. It is not tolerable once the derived set is the only one carrying the corrections.

The predicate graph is the largest defect by count and the least visible. The translation writes predicates faithfully and almost never reads them: 83% of the CrySL `ENSURES` clauses have a counterpart, only 22% of the `REQUIRES` have a reader, and 20 of the 23 `Property` constants do not function as an edge at all. `SSLContextSpec` reads none of its three `REQUIRES`, so a TLS context assembled from unvalidated key and trust managers raises nothing. Worse, nothing links the constant written to the constant read — at compile time or at runtime — so a wrong constant fails silently, and two already do.

**One thing that is explicitly not a defect, and this change must not "fix" it.** That the diff between `jca` and `jca_android` is allow-list only today is the correct outcome of the derivation, not an oversight. The Android set was **derived** through MetaCrySL rather than translated a second time by hand, and the platform-dependent part of a CrySL rule is precisely the membership constraint: `ORDER`, `REQUIRES`, `ENSURES` and `NEGATES` do not vary with API level. The defects above therefore sit in the platform-independent portion and are present, byte for byte, in both sets. What this change adds on that axis is verification: the derivation anchored ten files to a generated rule and kept thirteen verbatim, of which only three have a stated reason. Re-checking all 23 against the 33 generated rules for API 30 turns a prose traceability table into a conferrable artefact.

**Where the corrections land, and what that costs.** The `jca` set produced numbers that are already published. It is therefore **frozen**: not one byte of `rvsec-mop/src/main/resources/jca`, and not one byte of `CipherTransformationUtil.java`, changes in this change, so exact reproduction of those numbers continues to hold. Every correction lands in `jca_android` alone.

The price is paid in two places and must not be left implicit. First, the `jca` set knowingly keeps its layer-2 defects and the spurious reports they produce — a defect left standing for reproducibility is still a defect, and it is recorded as one rather than quietly tolerated. Second, and more consequential for how results are read: the two sets stop differing along a single axis. Until now a difference in outcome between them could only come from the platform allow-list. After this change it can come from the allow-list **or** from a layer-2 repair present in one set and not the other, and no measurement can separate the two contributions after the fact. That is why the divergence between the sets stops being forbidden and becomes something enumerated: every hunk outside an allow-list is written into a versioned record with the reason it exists, so a later reader can at least see which differences are platform and which are repair.

## What Changes

- **Layer-2 authoring defects, in the derived set.** `TrustManagerFactorySpec`: rename the `g3` binding, add the event to the `fsm`, and correct the three `gtm1` defects at `:62-65`. `SSLContextSpec`: add `returning(SSLContext ctx)` at `:46` and add `unsafe_protocol` to the `fsm`. The `fsm` half is not optional — fixing the binding alone makes every algorithm outside the allow-list emit a spurious `InvalidSequenceOfMethodCalls`. The same repair then closes the **sixteen** further all-`fail` events, in eight specifications, so the derived set ends with none: `IvParameterSpecSpec.c3`/`c4`, `KeyPairGeneratorSpec.initError`, `MessageDigestSpec.reset`, `PBEKeySpecSpec.f1`/`f2`/`err1`/`err2`/`err3`, `PBEParameterSpecSpec.c3`, `SecretKeySpecSpec.c3`/`c4`, `SecureRandomSpec.c3`/`g4`/`setSeed3` and `SignatureSpec.g3`. `PBEKeySpecSpec.f1` and `f2` carry the binding defect as well, so they need both halves.
- **Transformation tables for the derived set, in a class of their own.** A new `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil` transcribes the eight algorithms of the generated API 30 `Cipher` rule with their per-algorithm mode and padding tables. It sits beside the frozen class in the package that already exists, so it reuses the `alg`/`mode`/`pad` parsers by calling them, without an import and without restating them. `jca_android/CipherSpec.mop` reaches it by a static import, so only that one line changes and the five `isValid(...)` call sites stay as they are; the original class is not touched, so the `jca` verdict is preserved by construction rather than by a pinning test.
- **Predicate graph reconnected, in the derived set.** 23 translation defects corrected in `.mop` (including the two wrong constants at `KeyPairSpec.mop:38` and `TrustManagerFactorySpec.mop:65`); 11 edges that need a new `Property` constant added in `rvsec-core` and read in their specifications; 2 deliberate omissions and 1 inexpressible edge recorded with their reason.
- **A guard against silent constant defects.** A test derived from the write/read inventory cross-checks the `Property` constants written against those read, so a wrong constant cannot fail silently again.
- **CrySL conformance re-checked.** Each of the 23 `jca_android` allow-lists is verified against its generated `.cryptsl` rule for API 30, including confirmation that each of the thirteen files kept verbatim is genuinely uncontradicted by any rule. The result is committed as an artefact.
- **The derived set becomes selectable by name.** `specification_set` gains `jca_android`, mapping to its own directory, so the set carrying the corrections stops depending on a `custom` path spelled correctly by hand.
- **Freeze check and divergence record replace the parity check.** Two mechanical criteria instead of one: `jca` and `CipherTransformationUtil.java` are byte-identical to their state at the change's base commit, and every hunk by which the two sets differ outside an allow-list appears in a versioned record with its reason.
- **The consequences recorded.** That the `jca` set retains known defects and the reports they produce; that comparisons across the sets now confound platform allow-lists with layer-2 repairs; and that the derived Android profile models availability rather than recommendation — `MessageDigest` admits `MD5` and `SHA-1` — so a drop in the violation count is not evidence of better code.

## Capabilities

### New Capabilities

None. This change repairs and constrains behaviour the `instrumentation` capability already claims.

### Modified Capabilities

- `instrumentation`: the `Specification Set Support (FR03)` requirement describes the two JCA sets as collections of `.mop` files and enumerates them, but says nothing about what relates them, what may differ between them, what governs their content, or how the Android set is selected. The delta states four things it does not state today: that the Android set is derived from generated CrySL rules and how that derivation constrains it; that the `jca` set is frozen against a published measurement and corrections therefore land in the derived set alone, with the resulting divergence enumerated rather than forbidden; that a `Property` predicate written by one specification and read by another is a contract with a checkable invariant rather than a convention; and that `jca_android` is a first-class value of `specification_set`.

## Impact

**Sibling Java reactor** — most of the source work:

| Path | What changes |
|---|---|
| `rvsec/rvsec-mop/src/main/resources/jca` | **nothing — frozen at the base commit** |
| `rvsec/rvsec-core/.../mop/jca/util/CipherTransformationUtil.java` | **nothing — frozen at the base commit** |
| `rvsec/rvsec-mop/src/main/resources/jca_android` | 23 `.mop`: binding, `fsm`, `gtm1`, predicate-graph edges, the `CipherSpec` import |
| `rvsec/rvsec-core/.../mop/Property.java` | 11 new constants — additive only; no `jca` specification references them, so the frozen set is unaffected |
| `rvsec/rvsec-core/.../mop/jca/util/AndroidCipherTransformationUtil.java` | new: the derived API 30 transformation tables, beside the frozen class |

**Read-only reference**: `MetaCrySL/generated/api30/` (33 `.cryptsl` rules). That tree is not modified by this change.

**`rv-android`**: `rv-experiment`'s `config.py` gains `jca_android` as a `specification_set` value and its directory mapping, with the matching validation. Everything else here is artefacts: the OpenSpec files and the committed conformance, inventory and divergence records.

**Requirements**: FR03 (specification set support), FR01/FR02 indirectly (monitor generation and instrumentation consume these specifications), NFR07. To be confirmed line by line against `docs/PRD.md` during the specs phase.

**Depends on** issue #100, for one thing only: the empirical verification of `TrustManagerFactorySpec` and `SSLContextSpec` needs the wrapper-collision fix (its task 5.3) integrated, because the corrected allow-list is compared against a variable that the collision prevents from being written. Every other part of this change is independent of #100 and does not wait for it.

**Consequence for the record**: the numbers published from the `jca` set were measured against the defective specifications, and this change does not disturb them — the set is frozen and they reproduce exactly. What is recorded instead is the debt that buys it, and the eighteen all-`fail` events put a number on it: the defects remain in the set that produced the published results, and they account for 70.4% of the `InvalidSequenceOfMethodCalls` in those results. Those results are reproducible without being correct, and the two sets no longer differ along a single axis.
