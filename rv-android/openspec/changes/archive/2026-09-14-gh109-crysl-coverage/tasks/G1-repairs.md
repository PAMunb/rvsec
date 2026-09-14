# G1 — Verified repairs (parallel per file, after G0)

Each task edits exactly one file (plus its own `codes.csv` rows where a new accusation site appears).
All evidence anchors were verified this session against the live spec, the expert rule and (where
cited) the generated monitor — design D-18 has the full table. Records land once, in 1.R.

| Task | File | Repair | Anchors |
|---|---|---|---|
| 1.1 R1 | `DHGenParameterSpecSpec.mop` | Remove `condition(exponentSize < primeSize)` (:24); fuse into the `c1` body: accuse `DHGENPARAMETERSPEC-CONSTR-00` when `exponentSize >= primeSize`, write `PREPARED_DH` only on the conforming branch (the `IvParameterSpec` c1 fusion form, :63-78) | rule `:15`; `codes.csv:15` has only ORDER today |
| 1.2 R2 | `KeyPairGeneratorSpec.mop` | Add `initError2` mirroring `initError` (:155-162) over `initialize(int, SecureRandom)`; absorb into the Inits alternative (:184). Alphabet chain (noted for 6.2): map it to **`init2`'s symbol**, the way `initError` is mapped to `init1`'s — `i4` in `order_alphabet_map.csv`, `i2` in `order_alphabet_map_expert.csv`. NOT to `initError`'s own symbol (`i3`/`i1`), which stands for `initialize(int)` and would erase the wrong language | guard at `:101-105` |
| 1.3 R3 | `MessageDigestSpec.mop` | Two halves. **(a)** Replicate in `d1`/`d3` the algorithm check `update`/`d2` already carry (ALG code on the violated branch) so `getInstance("MD5", provider)` + direct `digest()` accuses value, not just ORDER. **(b)** Write `Property.GENERATED_MESSAGE_DIGEST` over the returned `digest` in the bodies of `g1`/`g2`/`g3` — the producer site the transcription omitted; see the section below | (a) checks at `:94-98`, `:123-131`; missing at `d1`/`d3`. (b) rule `MessageDigest.crysl:46`; ledger rows #17, #18, #103 |
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

## 1.3(b) — the producer site for `generatedMessageDigest`

This half is not a repair, and it does not sit in 1.3 because it belongs to R3. It sits here because
it edits the same file, and G1 promised one pass per file — the researcher's call, taken so the
producer exists before G3 opens its consumers.

**What is missing.** `MessageDigest.crysl:46` ensures `generatedMessageDigest[this] after Get`, and
`MessageDigestSpec.mop` writes nothing of the kind — only `Property.DIGESTED`, from `@match`. The
two rules that require the predicate, `DigestInputStream.crysl:33` and `DigestOutputStream.crysl:34`,
are tasks 3.6 and 3.7. Land them over a producer that does not write, and their reads answer
NOT_OBSERVED for every program forever, which is the shape INV-INS-151 refuses and D-24 was written
to forbid.

**Why the plan did not carry it.** The six producer gaps of D-24 were enumerated from the 27 *absent*
rules — predicates whose every producing rule lacks a `.mop`. This one has the opposite shape: the
producing rule is present and paired, and the omission is in the transcription. It is invisible to
that derivation, and it is invisible in the ledger today for a second reason — the three rows that
carry it (`predicate_ledger.csv` #17, #18 on the REQUIRES side, #103 on the ENSURES side) all read
`unmonitored-consumer`/`unmonitored-consumer-side`, each resting on the same sentence: *none of which
has a `.mop`*. Tasks 3.6 and 3.7 make that sentence false. From that moment the honest disposition,
absent this write, is `unmonitored-producer` — a producing rule that has a `.mop` and does not write.

**Where the write goes.** In the bodies of `g1`, `g2` and `g3`, over the `digest` each already binds
in `returning(MessageDigest digest)`:

```java
PredicateStore.instance().ensure(Property.GENERATED_MESSAGE_DIGEST, digest);
```

Three things fix that site rather than another:

- **`after Get`, so the site is the transition and not `@match`.** The file already argues this
  distinction for its sibling predicate: the comment at `:100-112` explains that `digested`'s two
  clauses carry no `after L`, so their acceptance point is the accepting state, which in an `ere` is
  what `@match` names (INV-INS-134). `generatedMessageDigest` does carry an `after L`, so the same
  reasoning puts it in the event body.
- **`g1`/`g2`/`g3` and not `g4`.** The three conforming events are already gated by
  `condition(ConscryptAliasTable.matches("MessageDigest", alg, algorithms))`; `g4` is the
  complementary event over the same pointcut, and its body has just accused
  `MESSAGEDIGEST-ALG-02`. Writing there would hand the stream rules a preparation this very
  specification refused — the conforming-branch-only form R1 applies to `PREPARED_DH`.
- **The `condition()` on those three is intentional and stays.** The general warning of the
  conventions note — a `condition()` compiles to `if (!(guard)) return false;` before body and
  transition, so a construction that breaks it is never accused — does not apply here, because the
  else branch is not silence: it is `g4`, which accuses. Do not "repair" it into a body `if`.

**What it does not touch.** The `g2`/`g3` two-argument guard residue (divergence row F7, gh105 task
10.8(a)) stays deferred. The predicate write is not the provider guard, and adding it does not reopen
that decision.

The constant already exists: `Property.GENERATED_MESSAGE_DIGEST` landed in task 0.7, with a javadoc
that names this gap.

Java edits (1.7, and 1.6/1.8 if helpers move) rebuild the reactor (`mvn clean install -DskipMopAgent
-DskipTests`, JDK 21 prefix) and run the rvsec-core tests; the frozen gates
(`test_gh101_specset_gates.py`) must stay green — `ExecutionContext`, `CipherTransformationUtil`,
`jca/` byte-identical.

## 1.R — Group records pass + harness checkpoint 1

1. `gh104_divergence_record.py --refresh` → fill hunk rows for every edit (kinds from the existing
   vocabulary); `--check` exit 0.
2. `codes.csv` bijection + anchors (message gate) for the new sites (R1, R3, R9).
3. `gh105_predicate_graph.py --emit` (R6/R8 touch predicate sites; 1.3(b) adds one) + placement-census
   re-pin. 1.3(b) is a predicate the set did not write before, so it earns a row of its own — the
   write, its acceptance point and the two reads it unblocks in G3 — and the ledger rows #17/#18/#103
   keep their `unmonitored-consumer*` disposition until 3.6/3.7 land the consumers. Say so in the row,
   or the next reader will take the unchanged disposition for a failed write.

   **Three rows, and a word the write side did not have** (D-24, researcher decision 2026-08-26).
   1.3(b) writes at `g1`, `g2` and `g3`, so it is three rows, and each one draws two findings before
   it is written:

   - **INV-INS-134** (`write:body`, not at the acceptance point) closes on any non-empty `reason`
     (`gh105_predicate_graph.py:1425-1439`). The reason is the clause itself: `MessageDigest.crysl:46`
     ensures `generatedMessageDigest[this] **after Get**`, so the body of the `Get` event *is* the
     acceptance point. It is the same reading of INV-INS-134, inverted, that puts this file's
     `digested` write at `@match`. Registration, not decision.
   - **G-PRED2** (written, read by nobody until G3) does **not** close on the existing vocabulary.
     `RECORDED_WRITE_DISPOSITIONS` holds `omission` and `propagation` (`:1273`), and `omission` is
     documented in the script as *"an `ENSURES`-only dead end"* — no rule requires the predicate.
     That is false here: two rules require it and writing them is this change's plan. **Add
     `unmonitored-consumer` to `RECORDED_WRITE_DISPOSITIONS`** — the read side's own word, mirrored,
     and the one `predicate_ledger.csv` already carries at rows #17, #18 and #103. It does not
     loosen the gate: a reader-less write still has to name why; it can now name the true reason.
   - The `reason` on each of the three rows must carry **both** halves — the `after Get` acceptance
     point *and* the two consumers scheduled for 3.6/3.7 — and must say the disposition is
     **transitory**, retired by 3.R.

   **One existing record is falsified by the extension and is amended in this pass.** The
   `PBEKeySpecSpec.mop` `c1`/`SPECCED_KEY` row states that a reader-less write "closes with
   `omission` or `propagation` and with nothing else … while `unmonitored-consumer` … is a *read*
   disposition and can close no write". That was true of the closure gh105 reached. Add the adendum
   in the file's own `adendum added by task <id>` convention; do not rewrite the sentence's history.
4. Trace pairs for the three accusation-surface changes: R1 (violating `DHGenParameterSpec(1024, 2048)`
   now accuses), R4 (`c1 fl cl` now fails), R9 (`len == 0` now accuses).
5. Addendum to divergence row F7 (gh105 task 10.8(a)): R3 changed `MessageDigestSpec`'s answer on the
   consumption route (`d1`/`d3` now accuse value); the family's `g2`/`g3` guards remain deferred — the
   row's "draws nothing" claim must not survive R3 unamended.
6. **[GEN]** regenerate the monitor (inspect artifact, INV-INS-145) and run
   `RVSEC_HOME=... uv run pytest tests/parity --import-mode=importlib -o "addopts="`.
7. **Harness checkpoint 1**: `gh104_diff_harness.py` pre-G1 vs post-G1 over the 178 traces; classify
   every `introduced/removed/moved` against the task that caused it; commit evidence.
