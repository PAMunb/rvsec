# G1 — Verified repairs (parallel per file, after G0)

Each task edits exactly one file (plus its own `codes.csv` rows where a new accusation site appears).
All evidence anchors were verified this session against the live spec, the expert rule and (where
cited) the generated monitor — design D-18 has the full table. Records land once, in 1.R.

| Task | File | Repair | Anchors |
|---|---|---|---|
| 1.1 R1 | `DHGenParameterSpecSpec.mop` | Remove `condition(exponentSize < primeSize)` (:24); fuse into the `c1` body: accuse `DHGENPARAMETERSPEC-CONSTR-00` when `exponentSize >= primeSize`, write `PREPARED_DH` only on the conforming branch (the `IvParameterSpec` c1 fusion form, :63-78) | rule `:15`; `codes.csv:15` has only ORDER today |
| 1.2 R2 | `KeyPairGeneratorSpec.mop` | Add `initError2` mirroring `initError` (:155-162) over `initialize(int, SecureRandom)`; absorb into the Inits alternative (:184). Alphabet chain (noted for 6.2): map it to **`init2`'s symbol**, the way `initError` is mapped to `init1`'s — `i4` in `order_alphabet_map.csv`, `i2` in `order_alphabet_map_expert.csv`. NOT to `initError`'s own symbol (`i3`/`i1`), which stands for `initialize(int)` and would erase the wrong language | guard at `:101-105` |
| 1.3 R3 | `MessageDigestSpec.mop` | Replicate in `d1`/`d3` the algorithm check `update`/`d2` already carry (ALG code on the violated branch) so `getInstance("MD5", provider)` + direct `digest()` accuses value, not just ORDER | checks at `:94-98`, `:123-131`; missing at `d1`/`d3` |
| 1.4 R4 | `CipherOutputStreamSpec.mop` | `ere: c1 (w1 \| w2 \| fl)+ cl` → `c1 fl* ((w1 \| w2) fl*)+ cl` — flush no longer satisfies the `+`; `c1 fl cl` must now fail (rule `ORDER Con, Write+, Close`) | spec `:62`; rule `:24` |
| 1.5 R5 | `SecretKeySpec.mop` | `call(public byte[] SecretKey.getEncoded())` → `SecretKey+.getEncoded()` (:102-104). **Precondition**: weave one exemplar proving the dexlib2 matcher accepts `+` in owner position (it accepts `Object+` in parameter position; owner position must be shown, not assumed). If it does not, stop and record — the repair moves to a matcher task, not a spec hack | only interface-owned pointcut in the set |
| 1.6 R6 | `CipherSpec.mop` | `:177` splitter → `CipherTransformationNormalizer.alg`; implement D-20.2 (AES_128/AES_256 compare equal to AES in the key×transformation check — in the normalizer, never in the frozen Util) | `Util.alg` raw at `CipherTransformationUtil.java:10-15`; no alias row for `AES_128` (`ConscryptAliasTable.java:101-114`) |
| 1.7 R7 | `CipherTransformationNormalizer.java` (rvsec-core) | `isValid` admits the 8 `PBEWithHmacSHA{224,256,384,512}AndAES_{128,256}` families with CBC/PKCS5 (rule `:90-105`); delete the javadoc deferral sentence (:44-45) — the decision is now taken (D-20.1) | collapse at `:140-152` |
| 1.8 R8 | `KeyGeneratorSpec.mop` | `:215` `ensure(...)` passes `ConscryptAliasTable.canonical("KeyGenerator", generatedKeyAlgorithm)` (D-20.3) | raw write chain `:63 → :172 → :215` |
| 1.9 R9 | `IvParameterSpec.mop` | `:119-121` `len >= 0` → `len > 0` (rule `:19`) + accuse on the violated branch (`IVPARAMETERSPEC-CONSTR-NN`); only `len == 0` is reachable (JDK throws first on the rest — keep the existing comment's analysis, :89-101) | today `len == 0` passes and writes `PREPARED_IV` |
| 1.10 | 8 specs | Optional P3 hygiene: delete the write-only `current*` fields (all but `KeyGeneratorSpec`, which reads its own at `:172`). Skippable without blocking M1 | census in D-18 |

This file is also edited later by `1b.1` (the four guarded reads of D-24), which runs after G2 and
therefore after 1.2 — the two never overlap in time, but the second must be written against the
first's text.

Java edits (1.7, and 1.6/1.8 if helpers move) rebuild the reactor (`mvn clean install -DskipMopAgent
-DskipTests`, JDK 21 prefix) and run the rvsec-core tests; the frozen gates
(`test_gh101_specset_gates.py`) must stay green — `ExecutionContext`, `CipherTransformationUtil`,
`jca/` byte-identical.

## 1.R — Group records pass + harness checkpoint 1

1. `gh104_divergence_record.py --refresh` → fill hunk rows for every edit (kinds from the existing
   vocabulary); `--check` exit 0.
2. `codes.csv` bijection + anchors (message gate) for the new sites (R1, R3, R9).
3. `gh105_predicate_graph.py --emit` (R6/R8 touch predicate sites) + placement-census re-pin.
4. Trace pairs for the three accusation-surface changes: R1 (violating `DHGenParameterSpec(1024, 2048)`
   now accuses), R4 (`c1 fl cl` now fails), R9 (`len == 0` now accuses).
5. Addendum to divergence row F7 (gh105 task 10.8(a)): R3 changed `MessageDigestSpec`'s answer on the
   consumption route (`d1`/`d3` now accuse value); the family's `g2`/`g3` guards remain deferred — the
   row's "draws nothing" claim must not survive R3 unamended.
6. **[GEN]** regenerate the monitor (inspect artifact, INV-INS-145) and run
   `RVSEC_HOME=... uv run pytest tests/parity --import-mode=importlib -o "addopts="`.
7. **Harness checkpoint 1**: `gh104_diff_harness.py` pre-G1 vs post-G1 over the 178 traces; classify
   every `introduced/removed/moved` against the task that caused it; commit evidence.
