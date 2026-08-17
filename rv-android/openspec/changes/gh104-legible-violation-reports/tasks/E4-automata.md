# Group 8 — E4: automata and pointcuts in `jca_v2`

Tracked checkboxes: `tasks.md` §8. Starts after Groups 6 (gates + harness exist) and 7 (every report site already carries its envelope). Per file, one owner at a time. Two subagents on disjoint file halves are allowed only if each appends to its own block of `data/jca_v2/divergence_record.csv` (mark rows with the task id; the check script is order-independent).

## Subagent brief

Read `design.md` D-1, D-7, D-10, D-11; the `instrumentation` delta (`Successor Specification Set`, `Executable Structural Gates`, `Differential Harness`, INV-INS-118/123/124/125); `data/gh101/divergence_record.csv` (106 rows: `layer-2-repair` 51, `predicate-graph` 42, `allow-list` 12, `cipher-import` 1 — you replay the 94 non-`allow-list`, minus three), `data/gh101/README.md` (repair narrative per file; `:546-553` the generator ceiling; `:539` CipherSpec 17→14; `:638-641` MacSpec 8→11), `data/gh101/frozen_set_debt.md`, gh101 `design.md` D-S9 (idiom for violating branches: `unsafeAlg` state in `fsm`, Kleene prefix `g3*` in `ere`; absorption rejected), `audit/20260808_validacao_jca_android/global/juizglobal_gates.csv` and `set/set_cons_fen_registry.csv` (:9 `FEN-SET-GENCIPHER-EXTRA`, :51 `FEN-SSL-RANDOMIZED-EXTRA`, :48 `FEN-KPG-INITERROR-PLACEMENT`, :65 `FEN-D-REGISTER-ANCHOR-DRIFT`). Every edit: no bookkeeping obligation towards `ev=` — the generator emits the event name (Group 3, INV-INS-120), so you may add, rename and remove events freely; what you must keep is the `codes.csv` bijection, adding or removing a row whenever you add or remove a report site; one divergence-record entry per hunk (kind + reason + task); harness before/after per file with the classification written; event count of `CipherSpec` after edit ≤ 17 (INV-INS-115; 18 → `StackOverflowError`); `remove(Property)` one-argument sites replaced (needs a monitor field holding the object). Do not touch `jca/`, `jca_android/`. Read `jca_android/<file>` as reference — reading is not touching.

## Replay plan (94 hunks; three excluded)

| file | non-allow-list hunks (kind) | what to replay | not replayed / extra items |
|---|---|---|---|
| CipherSpec | 28 (layer-2 21, predicate-graph 6, cipher-import 1) | static import → `AndroidCipherTransformationUtil` (task 2.3); alphabet 17→14 (`init` fused into 3 arity-grouped events; `u2/u4/f6/g2` dropped and rows removed; `doFinal()` double-fire `f1/f2/f4`; `getInstance(String, ..)`); `reportUnrandomized`/`reportUnpreparedParams` reads; `MACED` reads in `f2/f5` | **not**: `GENERATED_CIPHER` writes at the 3 inits are kept only if a reader survives — the `CipherInputStreamSpec`/`CipherOutputStreamSpec` reads are excluded (`GENCIPHER-EXTRA`), so record the writes as terminal or drop them (state which); event count after ≤ 17 |
| MacSpec | 11 (predicate-graph 7, layer-2 4) | `!encrypted` reads; `PREPARED_HMAC` body read; alphabet 8→11 (`uArr/uByte/uBuf`, `f1/f2/f3`) with `MACED` writes; two-arg `remove` + `pendingInputs` clear | – |
| TrustManagerFactorySpec | 8 (layer-2 6, predicate-graph 2) | `g3` binding `k`→`mf` + `unsafeAlg` state; `gtm1` four defects (`:62-66`: `TrustManager[][]`→`TrustManager[]`, `KeyManager[]`→`TrustManager[]` in the pointcut, `k`→`mf`, `GENERATED_KEY_MANAGERS`→`GENERATED_TRUST_MANAGERS`); `init` split in 2; monitor field + two-arg removes (`:87,:88`) | – |
| SSLContextSpec | 6 (predicate-graph 3, layer-2 3) | `returning(SSLContext ctx)` on `unsafe_protocol` + `unsafeProtocol` state; `init` reads `GENERATED_KEY_MANAGERS`/`GENERATED_TRUST_MANAGERS` with `UnsatisfiedConstraint` reports; `createSSLEngine` return type `void`→`SSLEngine` (`:64`) | **not**: the `RANDOMIZED` read in `init` (`SSL-RANDOMIZED-EXTRA`, task 3.2) |
| KeyManagerFactorySpec | 5 (layer-2 3, predicate-graph 2) | `init` split 1→2; monitor field; `gkm1` records the array; two-arg `remove` (`:91`); `:57` stores the factory under `GENERATED_KEY_MANAGERS` — use a distinct constant as TMF does | – |
| KeyPairSpec | 5 (predicate-graph) | `gpr` → `GENERATED_PRIVATE_KEY` (`:38`); `generatedKeypair` write; `c1` REQUIRES reads | – |
| SecureRandomSpec | 5 (layer-2) | `c3`, `g4`, `setSeed3` placed; `unsafeInit` state; `g4` `getInstance(String, ..) && args(alg)` (`:76-79`) so 2-arg overloads bind | – |
| SignatureSpec | 5 (predicate-graph 4, layer-2 1) | `g3` placed; `generatedPrivkey` reads in `i1/i2`, `generatedPubkey` in `i4`; `sign()` return types `byte`→`byte[]`/`int` (`:99,:106`) so the pointcuts match | – |
| KeyPairGeneratorSpec | 4 (predicate-graph 3, layer-2 1) | `initError` placed; `preparedDH` reads in `init3/init4`; `String algorithm = "";` (`:26`) or guard `switch` (`:29`); make `:71-72` reachable (report before `validate` short-circuits) or delete it | **not**: the placement residual as landed in gh101 (`FEN-KPG-INITERROR-PLACEMENT`) — place `initError` per the CrySL rule and record why |
| KeyGeneratorSpec | 3 (predicate-graph) | `init` fused → 5 events; `randomized[ranGen]` read; **plus** `g3` `:47` tests `alg` not `currentAlgorithmInstance` | – |
| PBEKeySpecSpec | 3 (layer-2) | `f1/f2` gain `returning(PBEKeySpec s)`; five events enter via Kleene star | – |
| SecretKeySpecSpec | 3 (predicate-graph 2, layer-2 1) | `c3/c4` placed; `SPECCED_KEY` write in `@match`; **plus** parentheses `:27-30` (compare `:44-47`) | – |
| KeyStoreSpec | 2 (predicate-graph) | `gk1` writes `generatedKey/PrivKey/PubKey`; matching removals | – |
| CipherInputStreamSpec, CipherOutputStreamSpec | 1 each (predicate-graph) | — | **not**: `GENERATED_CIPHER` reads (`GENCIPHER-EXTRA`); record |
| IvParameterSpec | 1 (layer-2) | `c3/c4` placed | – |
| MessageDigestSpec | 1 (layer-2) | `reset` event removed (D-S9) | – |
| PBEParameterSpecSpec | 1 (layer-2) | `c3` placed | – |
| SecretKeySpec | 1 (predicate-graph) | NEGATES `generatedKey` after destroy event `d` | **plus** decide: null detector (single `e1`, `ere: e1*`, no `@fail`) becomes a detector per the CrySL rule or is deleted; record |
| GCMParameterSpecSpec | 0 | — | **plus** duplicate `c1` (`:23,:34`) → `c1`/`c2`; `ere : c1 | c2` (`:48`) then valid |
| DHGenParameterSpecSpec, HMACParameterSpecSpec, RandomStringPassword | 0 | — | – |

Also `remove(Property)` one-argument sites (`ExecutionContext.java:52-53` deprecated): `KeyManagerFactorySpec:91`, `TrustManagerFactorySpec:87,88`, `MacSpec:87` — covered above.

## Conformance record (task 8.7)

23 rows, columns as `data/gh101/conformance_record.csv`, plus `anchor_by_clause` per D-10: availability (api30) for Cipher catalogue and keystore types; recommendation (1.5.2) for digests and protocols. gh101's verdict distribution for reference: 10 anchored / 11 uncontradicted / 2 no-anchor / 0 contradicted.

## Commands

```bash
python3 scripts/gh104_gates.py <scratch>/MultiSpec_1RuntimeMonitor.java --allowlist data/jca_v2/gate_allowlist.csv   # target: G-2 0, G-6′ 0
python3 scripts/gh104_mop_lint.py ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_v2   # clean
python3 scripts/gh104_divergence_record.py --check
python3 scripts/gh104_diff_harness.py --a <snapshot before this file's edit> --b ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_v2 --traces traces --out evidence/harness/e4-<Spec>
grep -c "^event " ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_v2/CipherSpec.mop   # ≤ 17; record generation time and RSS
```

## Acceptance

- G-2 = 0 orphans on `jca_v2`; G-6′ = 0; lint clean; remaining G-2b′/G-2d hits allowlisted with reasons; `CipherSpec` generates within the ceiling (time/memory recorded).
- Every hunk in the divergence record; the three excluded gh101 items recorded as `not-replayed` with the audit reference.
- Harness evidence per file with `moved` explicitly named where the D-S9 residue applies (the accusation moves to the next call — recorded, not hidden).
- Conformance record complete (23 rows) and its pytest green.
