# Group 8 — E4: seven structural repairs in `jca_android`

Tracked checkboxes: `tasks.md` §8. Starts after Groups 6 (gates + harness exist) and 7 (every report site already carries its envelope). Six files, seven repairs, one owner per file; sequential execution is fine — this group is small.

## Subagent brief

This is **not** a replay of gh101's hunks. The 51 `layer-2` and 42 `predicate-graph` hunks of `data/gh101/divergence_record.csv` are out of scope: the predicate half no longer exists (Group 2 removed `ExecutionContext` from the set) and the allow-list half was re-derived from the api30 rules directly (Group 2 task 2.4), so replaying `jca_android`'s edits would import decisions this set does not share. There is no `replay_plan.csv`.

What remains are seven defects that are **provable against the CrySL rule or against the Java language**, each one small, each one with a file and line. Read `design.md` D-7 and D-10, the `instrumentation` delta (`Executable Structural Gates`, `Differential Harness`, INV-INS-118/123/124/125), and `MetaCrySL/generated/api30/<Rule>.cryptsl` for the specification you are editing. MetaCrySL is read-only. Do not touch `jca/` or the archived `jca_android_bug_predicate/` — reading the archived file as a reference is fine, reading is not touching.

Per repair: one `data/jca_android/divergence_record.csv` entry (kind + reason + task id), one harness run before/after with the classification written out, and the `codes.csv` bijection preserved (a repair that adds or removes a report site adds or removes its row). Line numbers below are the frozen `jca` seed's; after Group 2 and Group 7 they have moved — locate by symbol, not by number, and record the number you actually edited.

## The seven repairs

### 8.1 `GCMParameterSpecSpec` — the duplicate `c1`

`:22` declares `event c1` for `GCMParameterSpec.new(int, byte[])` and `:33` declares `event c1` **again** for `GCMParameterSpec.new(int, byte[], int, int)`. The `ere` at `:48` reads `c1 | c2`, and `c2` is declared nowhere, so the second constructor is invisible to the automaton and the generated monitor carries two `Prop_1_event_c1` methods against one `c1` transition row — which is precisely the G-6′ hit. `generated/api30/GCMParameterSpec.cryptsl` declares both. **Rename the `:33` declaration to `c2`.** One token. After it: G-6′ = 0 and G-ERE = 0 on this file.

### 8.2 `SecretKeySpecSpec:27-30` — surplus parenthesis

`c1`'s `condition(` opens one group and closes two; compare `c3` at `:44-47`, which is well-formed. Remove the surplus `)`. The lint's unbalanced-parentheses check must go clean on the file. Note that Group 2 task 2.3 has already deleted the `validate(...)` term from this condition and task 2.4 removed the algorithm list it also tested, so what you are balancing is the post-Group-2 text — check first that the condition still has content at all.

### 8.3 `MessageDigestSpec:73` — the dead `reset` event

`event reset` has an empty body and no clause behind it in `generated/api30/MessageDigest.cryptsl` (whose `EVENTS`/`ORDER` do not mention it, and whose `CONSTRAINTS` are `digestAlg in {…}`, `pre_len > pre_off`, `len > off`). It is the **only true `orphan-without-clause`** that gate G-2 reports on the entire frozen set — the other 17 orphans are the correct encoding of `CONSTRAINTS`/`REQUIRES`/`FORBIDDEN`, which never enter an `ORDER`. Delete the event.

### 8.4 `KeyPairGeneratorSpec:26` — `String algorithm` never initialised

The field is declared at `:26` and only written by the `init*` events, but `:70` reads it (`!safeAlgorithms.contains(algorithm)`) on a path that can be reached before any write, so the guard evaluates against `null`. Initialise it (`String algorithm = "";`) or guard the read at `:29`'s `switch`. State which you chose and why in the divergence entry — the two are not equivalent for the report `val` Group 7 wrote at `:72`.

### 8.5 Dead pointcuts — `SignatureSpec:99,:106` and `SSLContextSpec:64`

Return types in the pointcut declarations do not match the JDK signatures, so the pointcuts can never match:

- `SignatureSpec:99` and `:106` declare `sign()` returning `byte`; `java.security.Signature.sign()` returns `byte[]` and `sign(byte[], int, int)` returns `int`.
- `SSLContextSpec:64` declares `createSSLEngine` returning `void`; `javax.net.ssl.SSLContext.createSSLEngine()` returns `SSLEngine`.

Fix the return types so the pointcuts match, or delete the events. The harness before/after will show `introduced` accusations wherever a real call now matches — that is the expected outcome, and each one is recorded, not hidden.

### 8.6 `KeyPairGeneratorSpec:71-72` — unreachable branch

The report at `:71-72` sits after a guard that short-circuits, so it can never fire. Either make it reachable (report before the short-circuit) or remove it; the `codes.csv` row for that site follows whichever you chose. Group 7 already flagged this site as unreachable in its census — cross-check that its entry there and yours here agree.

### 8.7 `KeyGeneratorSpec:47` and `MessageDigestSpec:55` — the guard tests the field, not the argument

Both events bind an algorithm argument and then test the **monitor field** instead:

- `KeyGeneratorSpec:47`: `condition(!safeAlgorithms.contains(currentAlgorithmInstance))` on an event whose `args(alg)` has just bound `alg`.
- `MessageDigestSpec:55`: `condition(!algorithms.contains(currentAlgorithmInstance.toUpperCase()))`, same shape.

The freshly received algorithm is never evaluated; the field holds whatever a previous call left there (or `null` on the first). Swap both to the bound argument. This is the pair the design's D-4 "residues" paragraph names as the reason two events could pass their guards on one call and let dispatch order decide which name the report carries.

## What is explicitly out of scope here

- The 51 `layer-2` and 42 `predicate-graph` gh101 hunks, and the `CipherSpec` 17→14 / `MacSpec` 8→11 alphabet re-budgets that came with them. If a repair above needs a new `Cipher` event, the ceiling still binds (INV-INS-115: 17 events generate in 53 s / 3.3 GB, 18 raise `StackOverflowError`) — none of the seven does.
- `SecretKeySpec` (the null detector) and `RandomStringPassword` — both left the set in Group 2.
- Any allow-list content: that was settled in Group 2 tasks 2.4–2.7 and is held by gate G-CONF.
- Anything in `MetaCrySL`.

## Conformance record (task 8.10)

`data/jca_android/conformance_record.csv` must be complete when this group ends: one row per surviving specification (21), columns as `data/gh101/conformance_record.csv`. There is **one** anchor, the api30 rule (design D-10, single oracle) — do not reintroduce a per-clause availability/recommendation split. Group 2 wrote most of it; you add the rows the seven repairs touch and check that the three entries it owed are there: the `EC` divergence of task 2.6, the four ECDSA algorithms of task 2.7, and the declared cost of the `api30-admits` rule from task 2.4 (5,892 of 6,048 `MessageDigestSpec/UnsafeAlgorithm` rows stop being reported).

## Commands

```bash
python3 scripts/gh104_gates.py <scratch>/MultiSpec_1RuntimeMonitor.java --allowlist data/jca_android/gate_allowlist.csv   # G-2 orphan-without-clause 0; G-6′ 0; G-ERE 0
python3 scripts/gh104_mop_lint.py ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_android      # clean
python3 scripts/gh104_divergence_record.py --check
python3 scripts/gh104_diff_harness.py --a <snapshot before this file's edit> --b ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_android --traces traces --out evidence/harness/e4-<Spec>
grep -c "^\s*event " ../rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/CipherSpec.mop   # ≤ 17; record generation time and RSS
uv run pytest --import-mode=importlib -o "addopts=" tests/parity -q
```

## Acceptance

- All seven repairs landed, each with a divergence entry naming the CrySL clause (or the JDK signature) that proves it is a defect.
- Gates on `jca_android`: G-2 `orphan-without-clause` = 0, G-6′ = 0, G-ERE = 0, G-CONF green, G-PRED green, lint clean; every remaining G-2b′/G-2d hit allowlisted with a reason.
- Harness evidence per file, with `introduced` explicitly named for the two revived pointcuts of 8.5 and `moved`/`removed` named wherever they occur.
- `CipherSpec` still generates within the ceiling (time and memory recorded).
- Conformance record complete (21 rows) and its pytest green.
- One commit per repair or one per file: `fix(jca_android): <o defeito> (refs #104)`.
