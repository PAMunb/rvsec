# F2 — the write-only batch B (task 4.14): `KeyStoreSpec`, `KeyGeneratorSpec`, `KeyManagerFactorySpec`, `TrustManagerFactorySpec`, `KeyPairGeneratorSpec`, `DHGenParameterSpecSpec`, `HMACParameterSpecSpec`

The last seven files of Group 4, and the pass that closes three counters. Ten writes and
eleven accepting-state calls — the last eleven of the twenty-five the change was scoped
against. Like task 4.13 the files declare no read at all, so the question is again "who reads
this write?"; unlike task 4.13 the answer is almost never "nobody". Two writes have a live
reader today, five have one scheduled by the ledger, and three are dead ends.

The pass also pays the debt task 4.12 left: it opened an F2 window against the two producers
of `generatedKey` still on the old substrate, and both are here.

## What the seven files hold

| file | writes | accepting-state calls | `@fail` removals |
|---|---|---|---|
| `KeyStoreSpec` | 2 | 2 | 2 |
| `KeyGeneratorSpec` | 1 | 2 | 1 |
| `KeyManagerFactorySpec` | 2 | 2 | 1 |
| `TrustManagerFactorySpec` | 2 | 2 | 2 |
| `KeyPairGeneratorSpec` | 1 | 1 | 1 |
| `DHGenParameterSpecSpec` | 1 | 1 | 0 |
| `HMACParameterSpecSpec` | 1 | 1 | 0 |
| **total** | **10** | **11** | **7** |

## Who reads each write

Measured across all five specification sets and the 33 api30 rules. The `grep` also hit
`jca_android_bug_predicate`, the set the 2026-08-08 audit reproved 22/22; it holds a copy of
the same seed writes and it counts for nothing.

| predicate | clause | reader |
|---|---|---|
| `GENERATED_KEY` (KeyStore, KeyGenerator) | `generatedKey[key, _]` / `[key, alg]` | **live**: `CipherSpec.i2:118` and `SecretKeySpec.e1:79`, both on the new store since 4.1 / 4.12 |
| `GENERATED_KEY_STORE` | `generatedKeyStore[this] after Loads` | ledger #14 and #36 → task **5.9** |
| `GENERATED_KEY_MANAGERS` (`gkm1`) | `generatedKeyManager[kms]` | ledger #28 → task **5.9** |
| `GENERATED_TRUST_MANAGER` (`gtm1`) | `generatedTrustManager[tms]` | ledger #29 → task **5.9** |
| `PREPARED_DH` | `preparedDH[this]` | ledger #17 → task **5.8** |
| `PREPARED_HMAC` | `preparedHMAC[this]` | ledger #21 → task **5.2** |
| `GENERATED_KEY_PAIR` | `generatedKeypair[kp, alg]` | **none** — the last dead end of the design's list |
| `generatedKeyManager[this]`, `generatedTrustManager[this]` | `… after Init` | **none** — the oracle ensures on the factory and no rule asks for it there |

## Where each write goes, read off the generated monitor

| site | clause | transition row · match category | acceptance point |
|---|---|---|---|
| `KeyStoreSpec.load` | `generatedKeyStore[this] after Loads` | `load {5,5,5,2,5,5}` · `state == 2` | `@match` — both routes coincide |
| `KeyStoreSpec.gk1` | `generatedKey[key, _]` | `gk1 {5,5,2,5,2,5}` · `state == 2` | `@match` |
| `KeyGeneratorSpec.gk1` | `generatedKey[key, alg]` | `gk1 {5,5,1,1,1,5}` · `nextstate == 1` | `@match` — only `gk1` reaches it |
| `KeyManagerFactorySpec.init` | `generatedKeyManager[this] after Init` | `init {3,2,3,3}` · `nextstate == 2` | `@match1` — both routes coincide |
| `KeyManagerFactorySpec.gkm1` | `generatedKeyManager[kms]` | `gkm1 {3,3,0,3}` → `start` | **unreachable** |
| `TrustManagerFactorySpec.init` | `generatedTrustManager[this] after Init` | `init {3,3,1,3}` · `nextstate == 1` | `@match1` — both routes coincide |
| `TrustManagerFactorySpec.gtm1` | `generatedTrustManager[tms]` | `gtm1 {3,0,3,3}` → `start` | **unreachable** |
| `KeyPairGeneratorSpec.gen` | `generatedKeypair[kp, alg]` | `gen {4,4,3,4,4}` · `nextstate == 3` | `@match` |
| `DHGenParameterSpecSpec` / `HMACParameterSpecSpec` | `preparedDH[this]` / `preparedHMAC[this]` | — | already at `@match` |

All three `after L` clauses land on the same state as their `@match`, so the handler is both
acceptance points at once — learning 42, three times over.

## The measurement

Probe over the whole `ErrorCollector`, **one process per configuration** (learning 51), with
the two candidate placements written inline between the starting tree's own dispatchers.

| configuration | starting tree | write in **body** | write at **`@match`** |
|---|---|---|---|
| **A** `KeyGenerator.generateKey` → `getEncoded` → `IvParameterSpec` | 1 | **0** | **0** |
| **A2** A plus a second `generateKey()` — rejected by rule and automaton | 2 | **1** | **2** |
| **B** `KeyStore.getKey` → `getEncoded` → `IvParameterSpec` | 1 | **0** | **0** |
| **C** control: a key of no observed origin | 1 | 1 | 1 |
| **D** control: a producer already on the new store (task 4.10) | 0 | 0 | 0 |
| **F** `KeyManagerFactory` — what task 5.9 will read at `[kms]` | `NOT_OBSERVED` | `SATISFIED` | **`NOT_OBSERVED`** |

The probe is auditable in both directions the corollary of learning 27 asks for: **C** accuses
in every column, **D** is silent in every column, and **A** and **B** reach zero in exactly the
columns the pass claims.

**A2 is why the default of INV-INS-134 is kept for the eight reachable sites, and it points the
opposite way from task 4.13's row A2.** There, the acceptance point was unreachable on the
common route and the body write was the one that closed the chain. Here the acceptance point is
reachable on the common route (rows A and B both go to zero under it), and the one program the
two placements separate is one the rule itself rejects — two `generateKey()` on one generator,
against `Gets, Inits?, gk`. Under the acceptance point that key carries no origin predicate and
the consumer says so, which is what CrySL states; the extra report is true.

**F is why the other two sites stay in the body.** An acceptance-point write there does not
cost a report — it does not happen at all, and the predicate ledger #28 wires at task 5.9 would
read `NOT_OBSERVED` from a producer that runs.

## The window task 4.12 opened, closed and witnessed

`SecretKeySpec-keygen-iv.txt` was classified `introduced` from task 4.12 to this pass, and the
report says so in its own line:

```
- `SecretKeySpec-keygen-iv.txt` | introduced | — | IvParameterSpecSpec.c1     (before)
+ `SecretKeySpec-keygen-iv.txt` | unchanged  | — | —                          (after)
```

Its envelope line leaves the report with it. The whole harness goes `introduced` **10 → 9**,
and the nine that remain are the nine deliberate repairs — no window is left open.

The second producer, `KeyStore.getKey()`, had no witness in the corpus, so one was written and
its seed measured **before the edit** (learning 47): `data/gh104/traces/KeyStoreSpec-getkey-iv.txt`
drew the same single `IVPARAMETERSPEC-NOBS-00` on the starting tree, and is silent on the
migrated one. It replays with `unresolved: []` in all three snapshots (learning 52) and is
`unchanged` in the differential harness, which is learning 46 again: the chain works in the
pre-image, where both ends are on the old store, and works again migrated; it was broken only
in the starting tree, which the harness does not contain.

Writing that trace at all took measuring a limitation instead of accepting it (learning 54).
`ks.getKey` on an empty store returns `null`, and the first attempt bound null silently. Probed
on this JVM: **PKCS12** and **JCEKS** accept a `SecretKey` through `setKeyEntry` and return a
real `javax.crypto.spec.SecretKeySpec`; **JKS** refuses it (`Cannot store non-PrivateKeys`);
**BKS** and **AndroidKeyStore** do not exist off Android. The remaining obstacle was the
harness grammar, not the platform: a line without `-> x` dispatches the advices and does **not**
perform the call, so `ks.load(null)` never initialised the store. The trace performs the load
with a `bind` line and dispatches it with a plain one.

## The six decisions (2026-08-22), and the number that decided each

### 1. The seven `@fail` removals travel here, not to task 6.4

All seven are in these files and all seven undo writes this same task migrates, which is
decision 11's criterion and the one tasks 4.6 and 4.9 already used. Three measurements decided
it rather than the precedent alone:

* `PredicateStore` offers no removal at all — INV-INS-131 forbids it the object-blind
  `remove(Property)` the old store had — so the calls cannot be migrated. They can only be
  deleted or left behind.
* Left behind, they are no-ops on a store nothing writes: INV-INS-133 is at zero and both
  readers of `GENERATED_KEY` are on `PredicateStore`, so **no reader of any predicate remains
  on the old substrate in `jca_android`**. Deleting them changes no report, and keeping them
  would be dead code (P3).
* INV-INS-130 requires zero mentions of `ExecutionContext`, checked with `-w` so an import
  counts. Leaving the removals keeps seven files off zero and makes task 4.15 — which requires
  the invariant green — unable to close before task 6.4.

INV-INS-142 and task 6.4 are amended, exactly as task 4.9 already amended them from eight to
seven. Task 6.4 becomes a verification task, the shape task 6.5 already has for 4.6 and 4.9.

### 2. Eight writes at the acceptance point, two in the body with a recorded reason

The measurement is column F above and the transition rows in the table. `gkm1` and `gtm1` leave
the accepting state for `start`, so the acceptance point is not merely a worse placement — it
is no placement. **Cost stated in full**: after a `gkm`/`gtm` — a call the *rule* accepts and
the *automaton* refuses — the body write marks an array the automaton did not accept. That is
the whole of what the recorded reason buys back, and both writes move to `@match` when task 7.1
repairs the automaton.

### 3. `TrustManagerFactorySpec.gtm1` writes the predicate its clause names

The seed wrote `GENERATED_KEY_MANAGERS` at a site whose clause is `generatedTrustManager[tms]`
(`TrustManagerFactory.cryptsl:49`); the file's javadoc carried the same copy, saying
"KeyManagerFactory". This is the shape of decision 36 (`gpr`, task 4.13): the seed's name only
starts to matter when the write changes store, and task **5.9 runs before task 6.2**, so it
would measure ledger #29 against a knowingly wrong producer.

Measured, the correction costs nothing on any tree, for two independent reasons: no
specification of the set reads either constant today, and **the advice has no execution path at
all**. The pointcut declares `getTrustManagers()` returning `KeyManager[]` where the API returns
`TrustManager[]`, both weavers match the return type exactly, and the harness shows it from the
trace side — `tmf.getTrustManagers()` resolves to no pointcut against the current monitor
(`unresolved: ["tmf.getTrustManagers()"]`). That is gh104 8.7, already in
`conformance_record.csv` as measured-not-repaired, and task 6.2 owns it. This is learning 48's
shape a second time: a write relocated onto an event that never fires, and that is correct.

The `@fail` also removed `GENERATED_TRUST_MANAGERS`, a `Property` no site of any set writes. It
leaves with decision 1.

### 4. The two dangling imports leave here

`CipherInputStreamSpec.mop` and `CipherOutputStreamSpec.mop` named `ExecutionContext` once each,
in an import, with zero uses — the two stream rules ensure dead-end predicates for which
`design.md` fabricates no write. No task of Group 4 covered them and task 4.15 requires
INV-INS-130 green. Deleting dead imports cannot change behaviour, and with them the invariant
reaches **zero across the set**.

### 5. Three deliberate-omission records

`generatedKeypair` at `KeyPairGeneratorSpec.gen`, and the two `[this] after Init` halves of
`generatedKeyManager` and `generatedTrustManager`. The inventory is of **sites**, so the record
is per site: the `[kms]`/`[tms]` siblings have a reader scheduled at 5.9 and carry none.

`KeyPairGeneratorSpec.mop:111` is the eleventh and last of the sites `design.md` lists for its
seven dead-end predicates. **After this pass every site on that list is disposed of.** The other
half of the clause, `generatedKeypair[this, _] after co` (`KeyPair.cryptsl:39`), has no site at
all in `KeyPairSpec.c1`; task 4.13 measured it and routed the record to task 5.10, and it is not
duplicated here.

### 6. The `KeyManagerFactory` ordering divergence is fed to task 7.1

`g1 init gkm1` is **accepted** by the api30 ORDER (`Gets, Init, gkm?`) and **rejected** by the
`fsm`, which sends `gkm1` from the accepting state (2) to `start` (0). It is the exact mirror of
the `g1 i1 gtm` divergence G-ORDER already reports against `TrustManagerFactorySpec`, and it is
what makes this pass's `gkm1` write stay in the body.

G-ORDER cannot see it: `KeyManagerFactorySpec` has no rows in `order_alphabet_map.csv` and the
gate says so out loud — `skipped … no rows in the alphabet mapping; G-ORDER never infers one`.
`conformance_record.csv` was read before calling it new; its three `KeyManagerFactorySpec` rows
are about the algorithm allow-list, the deferred `neverTypeOf` constant, and the 8.16
guard-on-field repair. Task 7.1 completes the mapping "for every spec Groups 1-6 touched" and
this task touches it, so the gate will raise it there. Recorded in the task text and in the
site's `reason`; not duplicated into gh104's catalogue.

## What the numbers did

| measure | before 4.14 | after |
|---|---|---|
| accepting-state calls (INV-INS-147) | 11 | **0** ✅ |
| `ExecutionContext` mentions (INV-INS-130) | 9 files | **0** ✅ |
| `remove()` in `@fail` | 7 | **0** ✅ |
| writes off the acceptance point with no reason (INV-INS-134) | 8 | **0** ✅ |
| structural gate findings | 30 | **10** (all G-PRED2, all awaiting Group 5) |
| `write:body` / `write:acceptance` in the graph | 13 / 17 | **7 / 23** |
| rows with `disposition=omission` | 6 | **9** |
| graph rows | 63 | **45** |
| `divergence_record.csv` hunks | 240 | **277**, all recorded |
| corpus traces | 100 | **101**, all committed |
| harness `introduced` | 10 | **9** — the one window closed |

Harness over the 101 traces against `backup/gh105-preimage/jca_android`: **67 unchanged, 19
moved, 9 introduced, 6 removed** (cumulative against the pre-image).

`gh104_gates.py` on the generated monitor: `G-2 0 · G-2a 4 · G-2b' 11 · G-2c 1 · G-2d 2 ·
G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 23`. G-PRED reaches 23 — one per file of the set — which
is the mirror of INV-INS-130 reaching zero: every file of `jca_android` is migrated.

Baseline `--write`: **24 `repaired` lines**, two re-keyed rows entering it. The two are not new
findings but the same two sites under new keys — `KeyStoreSpec load/GENERATED_KEY_STORE` became
`match/GENERATED_KEY_STORE` when the write moved, and `TrustManagerFactorySpec
gtm1/GENERATED_KEY_MANAGERS` became `gtm1/GENERATED_TRUST_MANAGER` when the predicate was
corrected. Both remain G-PRED2 rows awaiting their task-5.9 consumer, like the six that were
already there.

**`git diff --stat -- data/gh105/evidence/harness/` shows two of the twenty-three reports
changed** (learning 53): `f2-KeyStoreSpec.md` gained the new trace, and `f2-SecretKeySpec.md`
lost the `introduced` row. Seven migrated files and eighteen deleted sites moved nothing else,
which is the pass's strongest claim and the one the census could not make.

## Found and not repaired

`codes.csv` anchors `GCMPARAMETERSPEC-ORDER-00` at `GCMParameterSpecSpec.mop:136`, which is a
comment; the `addError` is at `:142`. The mismatch predates this pass — it is there in `HEAD`
too — and the file was not touched by task 4.14. Task **7.2** is the `codes.csv` completeness
pass and owns it; the ten anchors this task did move were re-checked one by one against the
tree, and every other row of the file resolves to an `addError` line.
