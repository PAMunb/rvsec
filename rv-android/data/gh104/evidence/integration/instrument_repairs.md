# 10.6 — the three instrument repairs

What this records: the three defects the code review of task 10.6 found in this change's own
instruments, reproduced, repaired, and each repair falsified before it was left green. Written after
`86a8f178`, on 2026-08-24.

All three are the same disease: **an instrument that stopped distinguishing answered "no finding"
instead of saying it could not tell.** It is the third time this change has met it — `caa48643` fixed
it inside one comparison loop, `9cba65ee` fixed it in the harness's accusation identity, and this
fixes it at the verdict level and in two of the harness's replay paths.

---

## 1. The gate suite reported PASS when it had measured nothing

**Reproduced.** A monitor file containing only `public class NothingHere {}`:

```
ok = True   exit = 0
G-2 0 · G-2a 0 · G-2b' 0 · G-2c 0 · G-2d 0 · G-6' 0 · G-ERE 0 · G-CONF 0 · G-PRED 0
skipped = [4 entries, printed to stderr and read by nobody]
```

Nine green gates and a zero exit code over an empty class. `run_gates` set
`report["ok"]` from the failure lists alone; `report["skipped"]` — which every degrading branch in the
file dutifully appends to — was never consulted, and `main()` returned `0 if report["ok"]`.

Two repairs, because the report was blind in two different ways:

- **`ok` now reads `skipped`.** A gate that did not run is not a gate that passed. The two states stay
  distinguishable in the JSON — `skipped` names what did not run, the per-gate `failures` name what
  did — and neither is green.
- **A monitor that declares no property is itself a skip.** The six structural gates read `properties`
  and nothing else, so an empty monitor made each of them report zero hits over zero input without
  recording any skip at all. They now say so, in one entry naming all six.

The `main()` docstring claimed that printing skips to stderr "so that a green run whose gates were
skipped cannot be read as a green run". That was an assertion that had become a lie: the caller reads
the exit code. It now says what the code does.

**After**: empty monitor → `ok = False`, exit 1, five skips.
**Legitimate invocation unchanged**: the documented `jca_android` run gives `skipped = []`, G-CONF 0
failures, G-2a 3 and G-PRED 23 — the pre-D-15 state recorded in the handoff, unmoved.

---

## 2. One narrative record was answering for every clause of its specification

**Reproduced.** `backing_record`'s fourth branch read

```python
if kind in ("api30-omits", "platform-value", "oracle-wart", "spelling-variant") and obj:
```

where `obj` comes from **the row** — the clause being checked — and never from the record entry. So
any divergence row of one of those kinds backed any clause-level difference in the same file.
Measured on the live records, six clauses were backed this way and **two of them were unrelated to
their record**:

| clause | was backed by | which is about |
|---|---|---|
| `CipherSpec` `encmode in {1,2,3,4}` | `oracle-wart` | RSA/ECB padding, and AES `CCM` |
| `KeyGeneratorSpec` `algorithm in {"AES"} => keysize in {128,192,256}` | `spelling-variant` | six `HMAC[-/]SHA*` entries |

Both of those clauses **do** have a correct, clause-level `deferred-constant` entry in
`conformance_record.csv`. The reason the gate was not finding them is the second half of the same
disease, one branch up: `absent_from_mop in clause` is a substring test, and the conformance record
was written against the generated api30 rules while D-15 moved the value oracle to the expert rules,
which spell the same clause differently — `alg in {"AES"} => keySize in {128, 192, 256}` against
`algorithm in {"AES"} => keysize in {128, 192, 256}`, and `encmode in {2, 4, 1, 3}` against
`encmode in {1,2,3,4}`. The literal branch failed, and the loose branch quietly covered for it.

Both repaired:

- **`_clause_shape`** compares two spellings of a clause by what the two oracles cannot disagree
  about: the sets of literal values, lower-cased and order-free, and the operators. The operators are
  kept so that `part(1) in {…} && encmode != 1 => noCallTo(IWOIV)` and its `== 1 => callTo(iv)` twin
  do not collapse into one shape.
- **The narrative branch now requires the row's verdict to be a list difference**
  (`MOP-MAIS-PERMISSIVO`, `MOP-MAIS-RESTRITIVO`, `DIVERGENTE`). All four narrative kinds explain why a
  value list the set carries differs from the list its clause declares. A clause the set never
  implemented has no list to differ, so no narrative row can be its account — its account is a
  `deferred-constant` entry, in the clause-level record. This is what a hunk-keyed record can honestly
  claim, and no more.

**After**: the two bogus backings moved to their correct `deferred-constant` records; the four
legitimate ones (KeyStore `type`, Mac `algorithm`, SSLContext `protocol`, SecretKeySpec `keyAlgorithm`)
stayed; nine further rows found a real clause-level record the substring test had been missing.
G-CONF stays at **0 failures — now for the right reason.**

**Falsified**: with the `encmode` `deferred-constant` row deleted from `conformance_record.csv`,
G-CONF reports **1 failure**, `Cipher.crysl:121 → unbacked`. Before the repair the same deletion
reported nothing, because the `oracle-wart` row rescued it. The record was restored; the CSV is clean.

---

## 3. The harness lost accusations on two replay paths

**3a — an accusation added before a throw.** `TraceRunner.replay` snapshotted the collector, called
`invoke`, and on an exception did `unresolved.add(...); continue;` — skipping the before/after diff
entirely. A handler that reports and *then* throws lost that accusation twice: it never reached
`accusingEvents`, and the next event's `before` snapshot already contained it, so no later event could
report it either. The trace then read `unchanged` while the two sides differed. The diff now runs in a
`finally`.

**3b — a fabricated return value.** `Advice.bind` did
`values.put(returning, produced != null ? produced : target)`: when a trace line named no `-> binding`,
the **receiver** was bound where the **returned** object belongs. For a dispatcher parameter typed
`Object` that flows in silently, and a predicate then stores or validates a value the run never
produced — a verdict manufactured inside the trace rather than measured from it. The fallback is gone;
only what the line produced is bound.

Refusing to replay such a line was implemented and measured first, and rejected: **8,502 replayed
events across the 159 traces name no return value**, so refusing would stop measuring them entirely —
a larger loss of the same kind as the one being repaired. Binding null states what is true, that the
trace did not say; a specification that goes on to use the value raises, and the line is recorded as
unresolved exactly where the value mattered. A trace that wants the value measured must name it.

### What the two repairs move: nothing, measured

`TraceRunner` was run over all 159 traces against the same monitor in three configurations — repaired,
with the `finally` reverted, and with the receiver fallback reintroduced. All three give **159 traces
and 169 event accusations, with identical per-trace accusation sets**:

| configuration | traces | accusations | traces differing from repaired |
|---|---|---|---|
| both repairs | 159 | 169 | — |
| `finally` reverted | 159 | 169 | **0** |
| receiver fallback restored | 159 | 169 | **0** |

Neither loss path is exercised by the current corpus: no handler in the set adds an accusation and
then throws, and no trace's fabricated return value reaches a verdict. **The task 11.9 figures stand
unchanged** — `unchanged 119 · moved 22 · removed 12 · introduced 6`. Both repairs are therefore
defensive: they close paths that are dormant today and would have been silent when they were not.

That is the honest reading, and it is also the reason to keep them. The 11.9 numbers themselves moved
only because `9cba65ee` repaired a loss path that *was* being exercised, and nothing had said so for
months.

---

## Verification after all three

| | |
|---|---|
| `TraceRunnerTest` | **7 passed** |
| `rvsec-core` + `rvsec-mop` | **72 + 7 passed**, BUILD SUCCESS |
| six parity suites (gh101, gh104 specset/structural/baseline/unique_msg, gh105 predicate) | **102 passed**, 95 s |
| `gh104_diff_harness.py --selftest` | exit 0; the three mutations still detected — unchanged 147, removed 3, moved 7, introduced 2 |
| `gh104_divergence_record.py --check` | 285 hunks, all recorded; 16 narrative entries |
| `gh104_mop_lint.py`, `gh104_message_gate.py` | `ok: true` |
