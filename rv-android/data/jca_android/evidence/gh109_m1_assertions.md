# gh109 task 7.2 — the M1 assertions, measured

What the milestone claims about the enlarged `jca_android` set, with the command that
produced each number. Every figure below is a reading of a committed record, so it can be
re-derived by running the command again; none is typed from memory.

Set under measurement: **48 `.mop`**, 49 oracle rules
(`RVSec-replication-package/tools/rules/`, D-16).

## 1. Producer side: no named gap is `unmonitored-producer`

`predicate_ledger.csv`, `REQUIRES` rows of the nine predicates the change set out to close:

| predicate | REQUIRES rows | disposition |
|---|---|---|
| `preparedRSA` | 1 | `wireable` |
| `preparedEC` | 2 | `wireable` |
| `preparedDSA` | 1 | `wireable` |
| `preparedOAEP` | 2 | `wireable` |
| `generatedManagerFactoryParameters` | 2 | `wireable` |
| `preparedDH` | 3 | `wireable` |
| `preparedAlg` | 2 | `wireable` |
| `preparedKeyMaterial` | 2 | `wireable` |
| `generatedMessageDigest` | 2 | `wireable` |

Six of these are the named producer gaps of the proposal; `preparedAlg` closed with G3,
`preparedKeyMaterial` with 4.3, and `generatedMessageDigest` is the write task 1.3(b) added
so that 3.6 and 3.7 would have something to read. **`unmonitored-producer` does not occur
anywhere in the ledger** — INV-INS-151 counts all eight, and the ninth is here because the
same task closed it.

## 2. The whole ledger, so the nine above are read in context

`uv run python scripts/gh105_expert_ledger.py --check` (exit 0; 135 clauses swept):

| section | rows | dispositions |
|---|---|---|
| REQUIRES | 57 | 54 `wireable`, 2 `vacuous`, 1 `unreachable-composition` |
| ENSURES | 76 | 51 `producible`, 20 `unread`, 4 `unmonitored-producer-side`, 1 `unreachable-composition` |
| NEGATES | 2 | 1 `producible`, 1 `unmonitored-producer-side` |

The two `unreachable-composition` rows are the two halves of `preparedHMAC`, reconciled by
task 5.1: the requiring side (row 38) and the producing side (row 80) now agree that a
composition the platform refuses is refused from both ends. The 20 `unread` and the 5
`unmonitored-*-side` rows are properties of the oracle — clauses whose counterpart rule the
49 do not contain, or contain without a `.mop` — and not work this set owes.

## 3. Consumer side (D-24): every write is read or carries a recorded impossibility

`uv run python scripts/gh105_predicate_graph.py --emit` — **0 failing, 0 allow-listed, 21
informative**, over 151 predicate sites of 48 files:

| disposition | sites |
|---|---|
| (none — the name is read by some specification of the set) | 134 |
| `omission` | 16 |
| `propagation` | 1 |

Every one of the 17 carries a written reason. Twelve are the acceptance-point placements
INV-INS-134 governs; the rest are predicates the oracle itself never requires
(`generatedKeypair`, `digested`, `signed`, `verified`, `generatedSSLContext`,
`generatedSSLEngine`, `generatedSSLParameters`, `generatedTrustAnchor`), which is a dead end
of the oracle and not of the specification (INV-INS-137).

**No predicate written by a new specification of this change is unread without such a row.**

## 4. Transitory dispositions: none is standing

Task 7.2 was written expecting to enumerate the transitory dispositions still alive at M1 —
in particular the `unmonitored-consumer` that task 1.R wrote on the three `MessageDigestSpec`
write rows, which 3.R owed. **G3 landed, and the assertion is stronger than the task asked
for: the graph carries no `unmonitored-consumer` row at all.** The only dispositions in the
file are the 16 `omission` and the 1 `propagation` above, and every one of them is
permanent-by-argument rather than owed to a later task.

That is 7.2's half of the claim. The half 7.3 still owes at M2 is the negative one over the
whole change: that no row acquired an `omission` whose recorded reason a landed consumer has
since falsified. One such falsification is already recorded, at 4.R:
`SSLContextSpec.mop/match1/GENERATE_SSL_ENGINE` said the predicate "appears only as this
rule's own ENSURES", and `SSLEngine.crysl:46` is a second ENSURES of it; the `omission`
stands (it still has no consumer) and only the count its reason quoted moved.

## 5. Coverage matrix: no rule without a terminal state

`uv run python scripts/gh109_coverage_matrix.py --check` (exit 0):

**49 rules — 45 `covered`, 3 `na-platform`, 1 `na-value`; 7 carrying an oracle-defect row.**

No rule is in two states and none is in zero. The three `na-platform` are `Cookie`,
`DSAGenParameterSpec` and `HMACParameterSpec`, each with its archive-scan evidence; the
`na-value` is `PasswordAuthentication` (INV-INS-156, both surviving legs recorded with what
its ORDER would still accuse).

## 6. The battery, for the record

| instrument | result |
|---|---|
| `gh104_gates.py` over the generated monitor | `ok: true`, nine gates, 0 failures, 0 skipped |
| `gh104_mop_lint.py` | `{}` on `jca_android`; the frozen `jca` baseline unmoved |
| `gh104_message_gate.py` | `ok: true` |
| `gh104_divergence_record.py --check` | 324 hunks, all recorded; 42 narrative entries |
| `gh105_expert_alphabet.py --check` | exit 0; every spec but the two unmapped by decision |
| `gh105_order_gate.py --sets jca_android` | 38 passed, 0 failed, 8 allow-listed, 2 skipped of 48 |
| `gh105_spec_gates.py --sets jca_android` | G-SIG 218/0 failed (3 skipped, 8 notes), G-FORB 5/0, G-BIND 202/0 failed (3 allow-listed) |
| `tests/parity` (gh104 structural + gh101 freeze + gh104 specset) | 26 passed |
| `tests/parity` (gh109's three files) | 81 passed |
| **[GEN]** merged monitor (INV-INS-145) | 28,299 lines; 48 monitor classes; 46 with a `MapOfMonitor`; compiles clean against `rvsec-core`, `rvsec-logger-csv`, `rv-monitor-rt` and android-30 |
| reactor `rvsec-crysl` | 171 + 59 + 102 (1 skip), 0 failures |
| `tests/parity`, whole suite | 191 passed, 3 failed |

The three that fail are named, and none is this change's: `test_baseline_freshness` (a jar
timestamp), `test_no_legacy_mop::test_repo_is_clean` (findings under `modules/aperv-tool`) and
`test_sentinel_emission` (a `StaticAnalysisParser.parse_file` signature). They were failing
before gh109 opened and they are recorded here so that a later reader does not read three reds
as this change's.

Five that WERE this change's are green as of this pass, all of them G2/G3 debt found by the
battery rather than by a task: `G-2a` (the two `on(boolean)` FORBIDDEN events of the Digest
pair and `KeySpec.ge1`, now carrying allow-list rows with their reasons), `G-2c`/`G-2d`
(`KeySpec`'s unreachable state and absent `fail` category, the state side of the same fact),
`G-ERE` and the lint (49 undeclared symbols that were the words of a comment), and `G-CONF`
(20 clause-level differences, now each carrying a `conformance_record.csv` row that says where
the clause is stated or why it is deferred).

The two specifications without a `MapOfMonitor` are `HMACParameterSpecSpec` (its class exists
on no Android API level) and `RandomStringPasswordSpec` (a junction over static calls). They
were three until this pass: `KeySpec` joined the list at task 2.14 and left it here, which is
what moved the T7 and T8 calibration targets from `3 of 48` to `2 of 48` and the `M0VitalityTest`
list from three names to two. A content pin that moves when the content moves is a pin doing its
work; these were re-measured against the artifact, not adjusted to fit.

Two defects of the set were found by this pass and repaired in it, both of them G2 debt:
`KeySpec.mop`'s header declared `KeySpec(Key key)` while its one event binds `k`, so the
generator keyed the monitor on a name nothing binds and `ge1` broadcast to every live monitor
of the specification (G-BIND, the `SSLParametersSpec` lesson of 4.2); and the `.mop` lint read
the comment standing between `ere : ge1*` and `@match` as part of the formula, reporting 49
undeclared symbols, one per English word.
