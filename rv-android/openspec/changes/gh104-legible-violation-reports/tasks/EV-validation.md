# Group 6 — EV: validation toolkit (gates, lint, message gate, differential harness)

Tracked checkboxes: `tasks.md` §6. Wave 1; creates NEW files only; hard prerequisite of Group 8. Group 2 creates `tests/parity/test_gh104_specset_gates.py` with its two set-level tests; this group writes the structural gates in a **separate** file, `tests/parity/test_gh104_structural_gates.py`, so the two never merge-conflict.

## Subagent brief

Read `design.md` D-7, the `instrumentation` delta (`Requirement: Executable Structural Gates…`, `Requirement: Differential Harness…`, INV-INS-123/124), `scripts/gh101_monitor_transition_check.py` (98 lines — reuse its monitor parsing, it reads both the `AbstractAtomicMonitor` and `AbstractSynchronizedMonitor` shapes at `:36-45`), `tests/parity/test_gh101_specset_gates.py` (145 lines, five gates — the pattern to follow), `data/gh101/frozen_set_debt.md:69-101` (the 18 orphans, nominal), and gh101 `design.md` D-S9 (why G-2b/absorption is not adopted). Monitor generation: `RVSEC_HOME` set, `TMPDIR` off tmpfs, never in parallel. A gate that reports fewer hits on the frozen `jca` than the baseline below is wrong — the frozen set is the fixture with known answers.

Four gates are new relative to the previous plan: the **corrected G-2**, and **G-ERE**, **G-CONF**, **G-PRED**. The correction matters more than the additions.

## The G-2 correction (task 6.2) — read this before writing any code

G-2 as inherited says: an event whose transition row sends every state to `fail` is an orphan, therefore a defect. On the frozen `jca` it reports **18 events in 10 specifications**. That verdict is wrong for 17 of them.

A CrySL rule has four clause families, and only one of them produces `ORDER` structure. `CONSTRAINTS`, `REQUIRES` and `FORBIDDEN` are **per-call predicates**: they say "this call is wrong on these arguments", not "this call is wrong at this point in the sequence". The natural encoding of such a clause in JavaMOP is exactly an event that leads to `fail` from every state — because the *state* is irrelevant to the accusation. Examples from the 18: `PBEKeySpecSpec.f1/f2` encode `FORBIDDEN: PBEKeySpec(char[]); PBEKeySpec(char[], byte[], int);` of `generated/api30/PBEKeySpec.cryptsl`; `PBEKeySpecSpec.err1` encodes `CONSTRAINTS: iterationCount >= 10000`; `SecretKeySpecSpec.c4` (`length(keyMaterial) >= off + len`), `SecureRandomSpec.g4`, `SignatureSpec.g3`, `TrustManagerFactorySpec.g3`, `SSLContextSpec.unsafe_protocol` encode `CONSTRAINTS … in {…}` allow-lists. They are correct code, and a gate that fails them teaches the reader to ignore the gate. Two of the 18 map to no clause even though they look like these: `PBEKeySpecSpec.err2` tests `RANDOMIZED[password]` where `PBEKeySpec.cryptsl:38-40` requires `randomized[salt]` alone (`:33-35` constrains the iteration count and `neverTypeOf(password, String)`, neither of which `err2` tests), and `SecretKeySpecSpec.c3` tests an algorithm list `SecretKeySpec.cryptsl` does not declare — under a mechanical mapping they are `orphan-without-clause` beside `reset`. And all 17 are correct in what they report, not in what they transition to: each carries an all-`fail` row, so every firing also runs `@fail` and emits a second, unlabelled `InvalidSequenceOfMethodCalls` (measured, deferred — E0 records the corpus ratios).

**The single real orphan is `MessageDigestSpec:74-76 reset`**: an empty-bodied event with no clause of any family behind it in `generated/api30/MessageDigest.cryptsl`. It is also the only orphan of the set with no `condition()` gating it, which is why removing it is behavioural: its generated row is `{4,4,4,4,4}` against a `fail` of 4, so every woven `reset()` accuses. The two other ungated orphans, `PBEKeySpecSpec.f1`/`f2`, encode a `FORBIDDEN` clause and are meant to.

So G-2 takes a second input — the specification's api30 `.cryptsl` — and splits its verdict:

- `orphan-with-clause`: the event maps to a `CONSTRAINTS`/`REQUIRES`/`FORBIDDEN` clause. Reported as a **note**, never a failure. The mapping is by name and by the argument the clause constrains; where the mapping is not mechanical, the allowlist carries it with a reason.
- `orphan-without-clause`: **failure**. Expected count on the frozen `jca` = 3 under the mechanical mapping (`MessageDigestSpec.reset`, `PBEKeySpecSpec.err2`, `SecretKeySpecSpec.c3`); the test pins 3, and any allowlist row that reduces it must name the clause it claims.

`REQUIRES` stays a clearing clause for the `jca` control, where predicates exist; for `jca_android` the classifier accepts `CONSTRAINTS` and `FORBIDDEN` only — the set encodes no `REQUIRES` by construction (D-11), so accepting it would clear an event whose only guard was the predicate that left. Group 2 task 2.3 deletes those declarations; this rule is what catches one that survives.

## Files (create)

- `scripts/gh104_gates.py` — G-2 (two-verdict, per above), G-2a, G-2b′, G-2c, G-2d, G-6′, **G-ERE**, **G-CONF**, **G-PRED**; `--allowlist data/<set>/gate_allowlist.csv`; `--crysl <dir>` for the api30 rules; `--alias data/<set>/alias_table.csv` for the normalisation of G-CONF; JSON report.
- `scripts/gh104_mop_lint.py` — over a set directory: undeclared ERE/FSM symbol; duplicate event name; unbalanced parentheses; three-argument `new ErrorDescription(` (INV-INS-119 — 25 hits on the frozen `jca` by design, zero on `jca_android` after Group 7); a hand-written event-name bookkeeping field or statement, which INV-INS-120 forbids because the generator emits the name (Group 3) and a hand-written index table would desynchronise under any alphabet edit; reserved generator names in `declarations` (`Prop_N_state`, `Prop_N_transition_*`, `pairValue`, `RVM_lastevent`, the event-name table Group 3 adds, `reset`, `getState`, `getLastEvent`, `handleEvent`, `clone`).
- `scripts/gh104_message_gate.py` — numeric literals in a message vs the guarding `condition()`; `codes.csv` ↔ sites bijection; `ErrorType` vs site kind.
- `tests/parity/test_gh104_structural_gates.py` — parametrised over `jca` (fixture monitor `results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java`, 2026-08-08; **not** `results/gh56-smoke/` — it predates the freeze by three months and two source fixes) and `jca_android` (generated in scratch; skipped with a stated reason while Group 2 has not landed, never silently passed).
- `data/jca/gate_allowlist.csv` — names the baseline hits below with reason "frozen set; knowingly retained (data/gh101/frozen_set_debt.md)".
- `rvsec-mop/src/test/java/br/unb/cic/mop/harness/TraceRunner.java` (+ `pom.xml` test scope in `rvsec-mop` — the directory does not exist today) — loads a generated monitor class set (`MultiSpec_1RuntimeMonitor` + `mop/*`), replays a trace file, records per trace: accused (bool), accusing event (`ev=` from the envelope or the `@fail` line), envelope text.
- `scripts/gh104_diff_harness.py` — `run(set_a, set_b, traces_dir, out_dir)`: generates both in scratch, runs `TraceRunner`, classifies per trace `unchanged` / `removed` / `moved` / `introduced`; writes `evidence/harness/<name>.md`. Both classes `removed` and `introduced` can occur on one file (Group 8 task 8.5), and the report lists them per trace.
- `traces/<Spec>.txt` — one line per **API call**, `<Class>.<method>(<args>)` with an optional `-> <name>` binding for the returned object and `<name>.<method>(…)` for calls on it, which `TraceRunner` resolves against **each snapshot's own** pointcuts (not by event name: the two snapshots of one comparison need not share an alphabet — Group 8 renames `c1`→`c2` and deletes `reset`, and the archived `TrustManagerFactorySpec` has `i1`/`i2` where the seed has `init`); ≥ 1 legitimate sequence, 1 per authored violating branch, and the separating traces of `audit/20260808_validacao_jca_android/` (grep `separating` / `traço` under `audit/.../set/`). Write traces for **all 23** specifications of the frozen `jca`, not only the 21 that survive: `SecretKeySpec` and `RandomStringPassword` are on the seed side of every `jca` → `jca_android` comparison, and a comparison with no trace on one side classifies nothing.
- `evidence/harness/selftest.md`.

## The three new gates

**G-ERE — every symbol named in an `ere`/`fsm` expression has an event declaration.** Zero false positives by construction: an undeclared symbol in the expression cannot be anything but a defect. On the frozen `jca` it reports exactly one hit — `GCMParameterSpecSpec:48` references `c2`, and the file declares `c1` twice (`:23`, `:34`) and `c2` never. This is the gate that catches the GCM defect that G-2 cannot see, and Group 8 task 8.1 closes it.

**G-CONF — allow-list conformance.** For each of the 21 specifications of `jca_android`, the `Arrays.asList` allow-list declared in the `.mop` equals the corresponding `CONSTRAINTS … in {…}` set of `MetaCrySL/generated/api30/<Rule>.cryptsl`, modulo the normalisation rule declared by Group 2 task 2.5: comparison is case-insensitive, and an observed value matches a list entry if a row of the alias table maps it there.

Three things about the alias half, because the architecture is deliberate (Group 2 task 2.5):

- The gate reads aliases from **`data/jca_android/alias_table.csv`** — the auditable registry, 158 rows, 114 of them mapping onto an api30 entry. It does **not** parse the Java class.
- Run-time resolution uses a **class in `rvsec-core` that carries the same table as code**, which the `jca_android` specifications name directly (INV-INS-112). Keeping code and registry equal is the job of the Java test Group 2 writes, not of this gate; if that test is missing, say so and fail — a registry nothing is tied to is not evidence.
- The gate **does** assert one thing about the class: no file under `rvsec-mop/src/main/resources/jca/` names it. That is what protects the frozen set's verdicts from this change (INV-INS-112, and the reason the published `jca` measurements stay reproducible).

For the **Cipher** the gate reads the new Java class of Group 2 task 2.8 instead of the `.mop`, because D-b keeps that list in Java. Every difference must have a row in `data/jca_android/conformance_record.csv` or the gate fails; exactly two are expected — the `EC` of task 2.6 and the four ECDSA algorithms of task 2.7, both instances of the `api30-omits` half of the asymmetric rule. The `api30-admits` half produces no divergence row at all: a value the rule admits is simply accepted, and its cost (5,892 `MessageDigestSpec` rows) is recorded in the conformance record as a consequence, not as an exception. On the frozen `jca` the gate is a **report, not an assertion**: it reproduces, row for row, `data/jca_android/constraint_table.csv` (Group 2 task 2.15 — the pivot's summary 74 = 30 CRYSL-NAO-IMPLEMENTADO / 14 IGUAL / 13 MOP-SEM-BASE / 7 MOP-MAIS-PERMISSIVO / 7 DIVERGENTE / 3 MOP-MAIS-RESTRITIVO has no committed row table behind it and an independent reconstruction reached 65, so the table's totals are the number this gate reproduces). Task 6.4 depends on 2.15.

**G-PRED — no `ExecutionContext` in the set.** `jca_android` contains zero occurrences of `ExecutionContext`, `Property.`, `validate(`, `setProperty(` and `.remove(Property`. The frozen `jca` is the negative control at **134** `ExecutionContext` occurrences across its 23 files.

## Baseline the gates must reproduce on the frozen `jca` (measured 2026-08-16)

| gate | definition | expected on `jca` |
|---|---|---|
| G-2 | `∀s: δ(s,e) = fail`, split by CrySL clause | 18 events in 10 specs, of which **15 `orphan-with-clause`** (note) and **3 `orphan-without-clause`** under the mechanical mapping (`MessageDigestSpec.reset`, `PBEKeySpecSpec.err2`, `SecretKeySpecSpec.c3`; failure) — 17/1 only through named allowlist rows. The 18: `IvParameterSpec.c3,c4`; `KeyPairGeneratorSpec.initError`; `MessageDigestSpec.reset`; `PBEKeySpecSpec.f1,f2,err1,err2,err3`; `PBEParameterSpecSpec.c3`; `SSLContextSpec.unsafe_protocol`; `SecretKeySpecSpec.c3,c4`; `SecureRandomSpec.c3,g4,setSeed3`; `SignatureSpec.g3`; `TrustManagerFactorySpec.g3` |
| G-2a | `∀s: δ(s,e) = s` | 1: `SecretKeySpec.e1` |
| G-2b′ | `δ(q0,e) = q0` | 8: `CipherSpec.g3`, `KeyGeneratorSpec.g3`, `KeyManagerFactorySpec.g3`, `KeyPairGeneratorSpec.g3`, `KeyStoreSpec.g2`, `MacSpec.g3`, `MessageDigestSpec.g4`, `SecretKeySpec.e1` |
| G-2c | unreachable from `q0`, or accepting unreachable from it | 1 |
| G-2d | highest state index is not `Category_fail` | 2: `SecretKeySpec`, `RandomStringPasswordSpec` (no `fail` category) |
| G-6′ | `#Prop_N_event_* methods ≠ #Prop_N_transition_* rows` | 1: `GCMParameterSpecSpec` |
| G-ERE | `ere`/`fsm` symbol without an event declaration | 1: `GCMParameterSpecSpec:48` `c2` |
| G-CONF | allow-list vs api30 `CONSTRAINTS` | report only on `jca`: row for row against `constraint_table.csv` (task 2.15); the 74/30-14-13-7-7-3 summary is provisional |
| G-PRED | `ExecutionContext` absent | 134 occurrences (negative control) |

**The `jca_android` expectations are not the same list.** `SecretKeySpec` and `RandomStringPassword` leave the set in Group 2 task 2.2, so their G-2a / G-2b′ / G-2d hits leave with them; `IvParameterSpec.c3/c4`, `PBEKeySpecSpec.err2/err3`, `SecureRandomSpec.c3/setSeed3` and `SecretKeySpecSpec.c3` leave with the predicates (declarations deleted, task 2.3). Write the `jca_android` expectations as **computed from the set**, not as a hard-coded second list, and let Group 7 and Group 8 drive them to their targets (G-2 `orphan-without-clause` = 0, G-6′ = 0, G-ERE = 0, G-CONF green, G-PRED green).

A throwaway implementation that reproduced the G-2..G-6′ numbers exists in the session scratchpad of 2026-08-16 (`structural_gates.py`); re-derive rather than trust it. `scripts/gh101_monitor_transition_check.py results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java` prints the 18 (exit 1).

Lint/message-gate baseline on the frozen `jca`: 25 three-argument sites; `GCMParameterSpecSpec.mop:23,34` duplicate `c1`, `:48` `c2` undeclared; `SecretKeySpecSpec.mop:27-30` unbalanced; zero hand-written bookkeeping (the seed has none and must keep none); literal mismatches `PBEKeySpecSpec.mop:50` (`1000` vs `:48` `10000`) and `PBEParameterSpecSpec.mop:50` (`1000` vs `:46` `10000`) — both against api30's `iterationCount >= 10000`; the three wrong `ErrorType` values of decision D-a (`PBEKeySpecSpec:24,30` `InvalidSequenceOfMethodCalls` where the clause is `FORBIDDEN`, `PBEParameterSpecSpec:49` `UnsafeAlgorithm` where the clause is a `CONSTRAINTS` bound); no `static` declarations in the corpus.

Harness self-test expected — and note **which two sets** it compares. The self-test runs `jca` against the **archived derived set**, `jca_android_bug_predicate` (Group 2 task 2.1 renames it; its content is unchanged and its behaviour is already measured), *not* against the successor `jca_android`. Two reasons: this group runs in wave 1 alongside Group 2, so the successor set may not exist yet when the self-test does; and a self-test needs a comparison whose answer is already known, which is exactly what the archived set gives.

- `TrustManagerFactorySpec`, trace `TrustManagerFactory.getInstance("X509") -> tmf; tmf.init(ks)` → accused at `getInstance` (frozen `g3`, row `{3,3,3,3}`) vs at `init` (archived `i1` — the archived set has no `init` event; its alphabet is `g1,g2,g3,i1,i2,gtm1`, the seed's `g1,g2,g3,init,gtm1` — row `{0,3,3,3}`, `unsafeAlg` state) → **`moved`**. The alphabets differ, which is what the call-keyed trace format exists for.
- `getInstance("PKIX"); init(ks); getTrustManagers()` → not accused in either → **`unchanged`**.

For the record, the same first trace against the *successor* set will classify **`removed`**, because the alias table maps `X509` to `PKIX` (`OpenSSLProvider.java:90`) and the api30 list admits `PKIX` — that is the repair the whole pivot is aimed at, and Groups 7/8 and task 10.5 are where it is observed, not here.

## Commands

```bash
python3 scripts/gh104_gates.py results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1RuntimeMonitor.java \
    --allowlist data/jca/gate_allowlist.csv --crysl ../../MetaCrySL/generated/api30 --alias data/jca_android/alias_table.csv
python3 scripts/gh104_mop_lint.py ../rvsec/rvsec-mop/src/main/resources/jca      # reports the baseline hits
uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh104_structural_gates.py -q
cd ../rvsec/rvsec-mop && mvn -q test -Dtest=TraceRunnerTest
python3 scripts/gh104_diff_harness.py --a ../rvsec/rvsec-mop/src/main/resources/jca --b ../rvsec/rvsec-mop/src/main/resources/jca_android_bug_predicate --traces traces --out evidence/harness/selftest
```

## Acceptance

- The nine gates reproduce the baseline on `jca` exactly and pass with the allowlist; G-2's split is 15 notes / 3 failures under the mechanical mapping, and the classifier's mapping of each of the 15 to its CrySL clause is written into the allowlist file (with `err2` and `SecretKeySpecSpec.c3` listed as clause-less, not force-mapped).
- G-ERE finds `GCMParameterSpecSpec` and nothing else; G-PRED counts 134 on `jca`; G-CONF reads its aliases from `data/jca_android/alias_table.csv` and reports that no `jca/` file names the alias class.
- Lint and message gate report the baseline on `jca`; both are wired into the pytest for `jca_android` (they go green after Groups 7 and 8).
- Harness self-test writes `evidence/harness/selftest.md` with the `moved` verdict for `TrustManagerFactorySpec`, comparing `jca` against the archived `jca_android_bug_predicate`; traces exist for all 23 frozen specifications.
- No emulator, no device: everything here is JVM/pytest. MetaCrySL is read only.
