# Session handoff — continue gh101, JCA specification conformance (session 7)

> Paste this whole file as the first message of the new session.

---

## 0. Who you are and where you are

You are Claude Code in the RVSEC / RV-Android research codebase (PhD work of Pedro Costa,
`phtcosta@gmail.com`). Primary working directory:

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

Git branch **`modules`**. Tip when this file was written: `efdd0541`. Session 6 committed
**nothing** — every artefact it produced is uncommitted, and §5 lists it exactly.

**`rv-android` is a subdirectory of the `rvsec` git repository, not a separate repo.** One
`git commit` covers both sides. This is why the freeze check can run `git -C $RVSEC_HOME diff`
over `rvsec/...` paths at all.

`$WS` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`. It is
**not exported** — set it yourself. `RVSEC_HOME` and `ANDROID_HOME` are exported.
**Anything outside `rv-android` must be written with an absolute path** — standing user
instruction, for code, docs and prose alike.

**Path trap.** There is a nested `rvsec` directory. `$RVSEC_HOME` is `$WS/rvsec`, and the
Maven modules live one level below it, so the specifications are at

```
$WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/     <- two `rvsec`
```

Writing `$WS/rvsec/rvsec-mop/...` gets you "File does not exist". Use `$MOP` from §10.

---

## 1. The north star, in one sentence

**The derived `jca_android` set should be as close to the CrySL rules as the mechanism
allows, and every place where it is not should be written down with the reason.**

That is the whole change. Everything else — the freeze, the divergence record, the alphabet
budget, the conformance verdicts — is machinery in service of it. When a decision is
genuinely open, the tie-breaker is: *which option makes the specification say what the rule
says?* And when the mechanism cannot say what the rule says, the answer is never to quietly
say something else — it is to record the gap. Session 6 had exactly that choice twice, and
both times the recorded gap was the deliverable, not the failure.

Two habits follow from it and both are load-bearing:

- **Go to the oracle, not to the translation.** The `.mop` is a secondary source and has
  been wrong before. Read the `.cryptsl`.
- **An `_` in a rule is an anonymous argument, and it licenses a wildcard.** `g2:
  getInstance(transformation, _)` means CrySL itself does not distinguish the overloads, so
  a fused pointcut is the *faithful* translation, not a defect. The same reasoning settled
  `!macced[_, plainText]` in session 6: because the first place is anonymous, projecting the
  two-place predicate onto the second place is exactly what the clause asks.

---

## 2. Read this first: the skill has the method

`.claude/skills/rv-analyze-spec/` (commit `3d093592`) exists so no session re-derives what
took an afternoon to learn. Load it with the `Skill` tool before touching a `.mop`, and read
at least:

- `reference/triangulation.md` — the method. Twelve angles for checking a claim. Short, and
  the part that matters most.
- `reference/generator-pipeline.md` — the generator, the ceiling, every reproducible number.
- `reference/pointcut-semantics.md` — what the weaver actually matches.
- `reference/crysl-to-mop.md` — the alphabet-budget method and the worked `Cipher` example.
- `scripts/README.md` — the two harnesses and how to run them.

Both harnesses drive **production classes**, not re-implementations, and both reproduced
their reference numbers again in session 6. Use them instead of reasoning:

- `CoenableProbe` — prices a property in either notation without generating code.
- `PointcutBudget` — runs the production `PointcutMatcher` over a class's real overloads and
  reports coverage, overlap and leakage.

---

## 3. What the change is, and where it stands

Implement `openspec/changes/gh101-jca-spec-conformance/` — GitHub issue
[#101](https://github.com/PAMunb/rvsec/issues/101).

**58 of 82 tasks complete.** `openspec validate` passes. Groups 1, 2, 3, 3b, 4 and 4b are
**closed**, plus tasks 5.1b and 5.1c. Remaining: 5.1–5.5, and Groups 6, 7, 8, 9.

The task checkboxes are now accurate — session 6 reconciled them against the tree and every
tick has evidence behind it. Do not assume that of any future state without re-checking.

**One decision is owed by the user before task 5.1 can start.** It is in §8 and it is the
first thing to resolve.

---

## 4. Non-negotiable working rules

Read `CLAUDE.md` at the repo root and at `$WS/rvsec/CLAUDE.md` first, then `docs/WORKFLOW.md`.

1. **Follow the OpenSpec workflow rigorously.** Anything under `openspec/changes/gh101-*/`
   goes through the **skills** invoked with the `Skill` tool: `openspec-apply-change`,
   `openspec-update-change`, `openspec-verify-change`, `openspec-sync-specs`,
   `openspec-archive-change`. **Never** hand-write or hand-edit an OpenSpec artefact outside
   a skill that told you to. The `.mop`, Java and Python edits are normal work — the rule is
   about the artefacts. **Ticking a checkbox in `tasks.md` counts as an artefact edit** and
   belongs inside `openspec-apply-change`. Revising `design.md` or `tasks.md` content belongs
   inside `openspec-update-change`.
   `data/gh101/*` is versioned data, **not** an OpenSpec artefact — edit it directly.
2. **The `jca` set is FROZEN** at commit `7e7acb69` (D-S0). Not one byte of `$MOP/jca`, not
   one byte of `$CORE/jca/util/CipherTransformationUtil.java`. Every correction to a
   **specification** lands in `jca_android` alone. You will read the same defective line
   twice and must fix only one copy. D-S10 bounds what the freeze covers.
3. **Do NOT repair `rv-monitor`.** Recorded decision D-S12, taken by the user. Do not
   re-open it.
4. **Do NOT touch the MetaCrySL tree** (`$WS/MetaCrySL`). It belongs to another session.
   `$WS/MetaCrySL/generated/api30/` (33 `.cryptsl`) is **read-only input**. Reading it is
   expected; writing is not. The same goes for the CrySL 1.5.2 corpus at
   `$WS/CryptoAnalysis/CryptoAnalysis/src/main/resources/JavaCryptographicArchitecture/`
   (see §8 — session 6 needed both).
5. **NEVER start, stop or manage Android emulators.** No exceptions. Permanent.
6. **Never add `Co-Authored-By`** or any co-author trailer.
7. **Language**: code, comments, commit messages, issues and OpenSpec artefacts in
   **English**; prose to the user in **Brazilian Portuguese with correct accentuation**.
8. **P1–P4** (`CLAUDE.md`): simplicity; narrative docs that explain *why*; no backward
   compatibility; current-state comments only. **P4 forbids migration commentary in the
   `.mop` files** — a comment says what the automaton does now and why, never "was added in
   task X". Session 6's `.mop` comments are the model: they explain the rule, the mechanism
   and the cost, and never mention a task number.
9. **Terminology**: "MOP" = *monitored operations*, never "security operations".
10. **Read-only**: `$WS/ase-journal/dataset/results`, `$WS/rvsec-dataset`,
    `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/`. Do **not** run `uv run` from
    inside `$WS/rvsec-dataset`. Use plain `python3` for probes outside `rv-android`.
11. Use the session scratchpad for temporary files, never `/tmp` directly. **Always copy a
    `.mop` to the scratchpad before running javamop — it writes the `.rvm` into the source
    directory.**
12. **Commits**: `refs #101` during work, `closes #101` only in the final one. **Commit only
    when the user asks.** The user does ask, often, right after something is finished.
    Nothing from sessions 3–6 is committed yet, so the first commit will be large; stage only
    gh101 paths (`rvsec/rvsec-core`, `rvsec/rvsec-mop/src/main/resources/jca_android`,
    `rv-android/data/gh101`, `rv-android/openspec/changes/gh101-*`, this handoff).
13. **A campaign shares this machine** (load average ~9, ~100 GB RAM free at handoff).
    Generating monitors is fine under `nice -n 15`. Watch `free -g`. Never run
    `mvn install` without checking `pgrep -af mvn` first. `mvn -o -pl rvsec/rvsec-core test`
    is scoped and safe.
14. **Do not `pkill -f logicrepository.Main`** while your own shell command line contains
    that string — session 4 killed its own wrapper that way.
15. **`sleep N` in the foreground is blocked by the harness.** Use `run_in_background: true`
    and wait for the notification, or an `until … done` loop.

---

## 5. Exact state you inherit

Committed: nothing new. HEAD is `efdd0541`, which is the sibling gh100 session's.

Uncommitted, and all of it is yours:

```
rv-android side
 M data/gh101/README.md                                                   (sessions 1–6)
 M data/gh101/divergence_record.csv                                       (sessions 3–6)
 M openspec/changes/gh101-jca-spec-conformance/proposal.md                (session 3)
 M openspec/changes/gh101-jca-spec-conformance/design.md                  (sessions 3, 5, 6)
 M openspec/changes/gh101-jca-spec-conformance/specs/instrumentation/spec.md (sessions 3, 5)
 M openspec/changes/gh101-jca-spec-conformance/tasks.md                   (sessions 3, 5, 6)
 ?? docs/20260807_handoff_gh101_sessao7.md                                (this file)

$RVSEC_HOME (rvsec side)
 M rvsec/rvsec-core/src/main/java/br/unb/cic/mop/ExecutionContext.java    (session 3)
 M rvsec/rvsec-core/src/main/java/br/unb/cic/mop/Property.java            (session 6 — MACED)
 M rvsec/rvsec-core/.../jca/util/AndroidCipherTransformationUtil.java     (sessions 3, 6)
 M rvsec/rvsec-core/src/test/.../AndroidCipherTransformationUtilTest.java (sessions 3, 6)
 ?? rvsec/rvsec-core/src/test/java/br/unb/cic/mop/ExecutionContextTest.java (session 3)
 M rvsec/rvsec-mop/src/main/resources/jca_android/CipherSpec.mop          (session 6)
 M rvsec/rvsec-mop/src/main/resources/jca_android/MacSpec.mop             (sessions 4, 6)
 M rvsec/rvsec-mop/src/main/resources/jca_android/KeyGeneratorSpec.mop    (session 4)
 M rvsec/rvsec-mop/src/main/resources/jca_android/KeyManagerFactorySpec.mop (session 4)
 M rvsec/rvsec-mop/src/main/resources/jca_android/KeyPairGeneratorSpec.mop  (session 4)
 M rvsec/rvsec-mop/src/main/resources/jca_android/KeyPairSpec.mop         (session 3)
 M rvsec/rvsec-mop/src/main/resources/jca_android/KeyStoreSpec.mop        (session 3)
 M rvsec/rvsec-mop/src/main/resources/jca_android/SecretKeySpec.mop       (session 4)
 M rvsec/rvsec-mop/src/main/resources/jca_android/SecretKeySpecSpec.mop   (session 4)
 M rvsec/rvsec-mop/src/main/resources/jca_android/SignatureSpec.mop       (session 3)
 M rvsec/rvsec-mop/src/main/resources/jca_android/TrustManagerFactorySpec.mop (sessions 3, 4)
```

Anything under `openspec/changes/gh100-*` or `rvsec-instrumentation-dexlib2` is **not yours**.

Checks at the moment of handoff, **all run in session 6, all green**:

- Freeze check (INV-INS-109 a): **empty diff**.
- Divergence record (INV-INS-109 b): **104 hunks, all recorded**.
- `tests/parity/test_gh101_specset_gates.py`: **4 passed**.
- `openspec validate gh101-jca-spec-conformance --type change`: **valid**.
- `mvn -o -pl rvsec/rvsec-core test`: **30 tests**, 0 failures.
- Whole derived set generates: **28.3 s / 1.67 GB**; INV-INS-110 reports **no bound event
  with an all-`fail` transition row**.
- The merged monitor **compiles**: `javac` over `MultiSpec_1RuntimeMonitor.java` against
  `rvsec-core/target/classes`, `rvsec-logger-csv/target/classes`, `rv-monitor-rt` and
  `android-30/android.jar` — 57 classes, 0 errors. This is the strongest check short of the
  full reactor build (task 9.1) and it is cheap; run it after every `.mop` edit.

---

## 6. What session 6 did

**Groups 4 and 4b closed, plus tasks 5.1b and 5.1c.**

### `CipherSpec`: 17 events → 14 (tasks 4.6, 4.6a, 4.10, 4.13)

Verified with `PointcutBudget` against all 28 members of `javax.crypto.Cipher` in
`android-30/android.jar`, **before** editing: the three `init` candidates partition all eight
overloads, the five `doFinal` candidates partition all seven, the whole set is pairwise
disjoint, and the unmatched members are exactly `getIV`, `unwrap` and the three `updateAAD`.

| | wall clock | peak RSS |
|---|---:|---:|
| `CipherSpec` alone, 17 events | 53 s | 3.3 GB |
| `CipherSpec` alone, 14 events | **6.9 s** | **1.02 GB** |
| whole derived set, before | 1 m 15.9 s | 2.98 GB |
| whole derived set, after | **28.3 s** | **1.67 GB** |

The 14 events, and which of the rule's events each covers:

| event | pointcut | rule events |
|---|---|---|
| `g1` / `g3` | `Cipher getInstance(String, ..)` | g1, g2 — conforming and non-conforming transformation |
| `init2` | `void init(int, Object+)` | i1, i3 |
| `init3` | `void init(int, Object+, Object+)` | i2, i4, i5, i8 |
| `init4` | `void init(int, Key, Object+, SecureRandom)` | i6, i7 |
| `u1` | `byte[] update(byte[], ..)` | u1, u2 |
| `u3` | `int update(byte[], int, int, byte[], ..)` | u3, u4 |
| `u5` | `int update(ByteBuffer, ByteBuffer)` | u5 |
| `wkb1` | `byte[] wrap(Key)` | w |
| `f1` | `byte[] doFinal()` | f1 |
| `f2` | `byte[] doFinal(byte[], ..)` | f2, f4 |
| `f3` | `int doFinal(byte[], int)` | f3 |
| `f5` | `int doFinal(byte[], int, int, byte[], ..)` | f5, f6 |
| `f7` | `int doFinal(ByteBuffer, ByteBuffer)` | f7 |

Two defects closed at no cost in slots, both **confirmed with the matcher, not by reading**:
the old `doFinal(..)` matched `[f1, f2, f4]`, so a plain `doFinal()` took two transitions;
and the invalid-transformation event was arity-1 `getInstance(String)`, so
`getInstance(transformation, provider)` over an unsafe algorithm fired nothing and was later
misreported as `InvalidSequenceOfMethodCalls`.

Three new reads landed with the bindings: `randomized[ranGen]`, and the two conditional
`preparedIV[params]` / `preparedGCM[params]`. The rule states the last two conditionally on
the mode (and `preparedIV` on the direction as well), so
`AndroidCipherTransformationUtil.requiresPreparedIv(transformation, encmode)` and
`.requiresPreparedGcm(transformation)` hold the rule's mode lists — the `.mop` carries no
second copy of them. Three test cases cover them.

**`REQUIRES generatedKey` was deliberately left in its `condition(...)`**, so the derived set
keeps today's behaviour for that clause: an init over an unvalidated key takes no transition
and the misuse surfaces on the next call. The guard was widened with
`!(keyOrCert instanceof Key)` so the certificate overloads keep firing. That is a change
worth revisiting *as its own decision* — it is the same anti-pattern every other repair in
this set moved away from — but it was out of task 4.6's remit and is flagged here rather than
done silently.

### `MacSpec`: 8 events → 11, and `!macced[_, plainText]` transcribed (D-S13, tasks 5.1b, 5.1c)

The user was given the rule text, the store's shape and the measured cost, and chose to
transcribe rather than record the clause as inexpressible. New `Property.MACED` holds the
**second** place of CrySL's two-place `macced[M, D]`; `GENERATED_MAC` holds the first. The
fused `update(..)` became `uArr` / `uByte` / `uBuf`, and the fused `doFinal` became the rule's
`f1`, `f2`, `f3`. `CipherSpec.f2` and `.f5` read it.

Marks are written at the **doFinal**, not at the update, because CrySL ensures `macced` when
the MAC exists; a `pendingInputs` field holds what was fed until then. Two residues recorded:
`update(ByteBuffer)` marks nothing (no such rule event) and `update(byte)` marks a boxed
primitive, with the `Byte`-cache unsoundness that entails.

### Records (tasks 4.3, 4.4, 4.11, 4.12, 4b.3, 4b.4)

All in `data/gh101/README.md`, each with the command that produced its numbers:

- **The two deliberate omissions** — `generatedCipher[this]` and
  `generatedMessageDigest[this]`, both replaced by `setObjectAsInAcceptingState`. Measured:
  **19 writes, 6 unsets, 0 readers** of `isInAcceptingState` or `hasEnsuredPredicate` in
  *either* set. The mechanism is inert at runtime.
- **`randomized[lSeed]` is inexpressible**, and the reason **changed** after 4b.1 re-keyed
  the store by identity. It now fails in both directions depending on magnitude, and — the
  decisive fact — nothing in the specification ever marks a `long`: the two primitive writes
  are over `int`, and an `Integer` is neither `==` nor `equals` to a `Long`.
- **Identity keying moves 8 of the frozen set's 27 reads**, all towards reporting more. Two
  corrections to D-S10's table: it typed the `SecureRandomSpec` seed reads as a boxed `long`
  and counted them as affected; they are over `byte[]` and are **unaffected**. The count of 8
  is right, the composition was not.
- **The clauses the fusion destroyed and this change does not restore** — `noCallTo(IWOIV)`,
  `callTo(iv)`, and `neverTypeOf(password, String)`, which is in **three** rules
  (`KeyManagerFactory`, `KeyStore`, `PBEKeySpec`) where the task text named two.
- **The generator ceiling**, with reproducing commands and the `n × (2ⁿ − 1)` law.

---

## 7. The two standing questions the user asks

### "o que mudou da spec original para essa e o motivo?"

Every difference is enumerated, one row per diff hunk, in `data/gh101/divergence_record.csv`
— **104 hunks, all recorded**, each with `kind`, a prose `reason` and the task that
introduced it. Checked mechanically in both directions
(`scripts/gh101_divergence_record.py --check`, INV-INS-109 b). Run it before answering from
memory.

| kind | n |
|---|---:|
| `allow-list` | 12 |
| `layer-2-repair` | 52 |
| `predicate-graph` | 39 |
| `cipher-import` | 1 |

### "esta comparando com a spec crysl?"

Yes, and it is the anchor of the whole change — see §1. `data/gh101/conformance_record.csv`
carries a verdict for all 23 derived specifications; `data/gh101/predicate_edges.csv` is the
clause-by-clause comparison. **But which CrySL** is now itself a live question — §8.

---

## 8. THE OPEN DECISION — resolve this before task 5.1

Session 6 went to verify `generatedCipher` before adding the constant and found that
**`grep -l 'generatedCipher\['` over the 33 generated API 30 rules returns nothing.** The
API 30 `Cipher` rule ensures only the three `encrypted[…]`; its `CipherInputStream` rule has
**no `REQUIRES` at all**. In the CrySL 1.5.2 corpus both are present.

`data/gh101/predicate_edges.csv` is anchored to **1.5.2 on purpose** — `ORDER`, `REQUIRES`,
`ENSURES` and `NEGATES` describe API semantics and do not vary with API level, so a
difference there is a translation defect rather than a platform fact. That reasoning still
holds. What is new is that the anchor choice is **load-bearing**: three of Group 5's eleven
edges rest on `generatedCipher` and one on `preparedOAEP`, and neither predicate is named by
any API 30 rule.

Group 5's nine constants, by how many rules of each anchor name them:

| constant | api30 | 1.5.2 | note |
|---|---:|---:|---|
| `preparedAlg` | 2 | 3 | |
| `preparedRSA` | 2 | 2 | |
| `preparedDSA` | 2 | 3 | |
| `cipheredInputStream` | 1 | 1 | api30 *adds* it |
| `cipheredOutputStream` | 1 | 1 | api30 *adds* it |
| `generatedManagerFactoryParameters` | 2 | 4 | api30 keeps both producers, drops the two factory `REQUIRES` |
| `preparedEC` | 1 | 3 | api30 keeps the `REQUIRES` in `KeyPairGenerator` and has **no `ECGenParameterSpec` rule** to produce it |
| `preparedOAEP` | **0** | 3 | |
| `generatedCipher` | **0** | 3 | |

**The options put to the user, unanswered when the session ended:**

1. **Follow 1.5.2** — add all nine as planned, recording that the derivation's own oracle
   does not ask for two of them. Coherent with the anchor the change already declared.
   This was the session's recommendation.
2. **Follow API 30** — drop `generatedCipher` and `preparedOAEP`; Group 5 falls to seven
   constants. This would also turn task 4.3's deliberate omission into a non-omission, since
   the API 30 rule does not ask for that predicate at all.
3. Something else the user prefers.

`preparedEC` is a separate case whichever way this goes: under **both** anchors it would
enter without a producer, because api30 has no `ECGenParameterSpec` rule.

**A methodological warning, because session 6 tripped on it.** The first comparison run was
**one-sided** (1.5.2 minus api30) and reported twelve rules "dropping" predicates, including
`SSLContext`. The symmetric comparison showed most of those are **renames**
(`generatedTrustManagers` → `generatedTrustManager`, `generatedTrustAnchor` →
`generatedCertPathParameters`, `generatedMessageDigest` → `digestedInputStream`) and that
api30 names **more** predicates than 1.5.2 in most rules. The genuine one-sided losses are
`generatedCipher`, `preparedOAEP`, `wrappedKey`, `preparedPBE`, `Mac`'s `generatedKey`
`REQUIRES`, and the two factory `REQUIRES`. The corrected table is in `data/gh101/README.md`.
**Always diff both directions.**

---

## 9. Remaining work, in order

1. **Resolve §8**, then **task 5.1** — the `Property` constants, each landing **with its
   reader** in the same task. Note `SPECCED_KEY` has two writers and still no reader
   anywhere: `SecretKeyFactory` is the only rule that requires it and no `.mop` models it. It
   needs an entry in the deliberate-omission list (task 7.2) or the guard (INV-INS-111,
   task 7.1) fails.
2. **Tasks 5.2–5.5.** For 5.2 the monitor-comparison half is already **done and green**:
   session 6 generated the frozen set's monitor from the current tree and from a
   `git archive` of `7e7acb69` and diffed them — **byte-identical**. What 5.2 still needs is
   the other half: that no `jca` specification references any new constant.
3. **Group 6** — `jca_android` as a `specification_set` value in `rv-experiment`'s
   `config.py`, its test, and the docs that enumerate accepted values.
4. **Group 7** — the write/read guard, the deliberate-omission list, and the five records.
5. **Group 8** — **unblocked**: issue #100's task 5.3 landed (commit `48b57fc5`, repaired by
   merging wrappers rather than widening the key). Task 8.1 no longer needs to be recorded as
   blocked.
6. **Group 9** — verification, including the full reactor build (9.1), for which you must
   coordinate: check `pgrep -af mvn` and the peer sessions first.

Then: tick issue #101's acceptance criteria one by one **before** closing, any criterion not
literally met getting an inline note (`- [x] ~~criterion~~ — superseded by …`), never a silent
tick and never a blank box. Sync the delta spec explicitly with `openspec-sync-specs`
**before** archiving, then `openspec archive gh101-jca-spec-conformance --skip-specs`. Final
commit uses `closes #101`.

---

## 10. Commands

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
WS=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv   # NOT exported
MOP=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources      # note the nested rvsec
CORE=$RVSEC_HOME/rvsec/rvsec-core/src/main/java/br/unb/cic/mop
RULES=$WS/MetaCrySL/generated/api30                     # read-only oracle, API 30
CRYSL152=$WS/CryptoAnalysis/CryptoAnalysis/src/main/resources/JavaCryptographicArchitecture
AJ=$ANDROID_HOME/platforms/android-30/android.jar
S=<your session scratchpad>

# where the change stands
openspec status --change gh101-jca-spec-conformance --json
openspec instructions apply --change gh101-jca-spec-conformance --json
openspec validate gh101-jca-spec-conformance --type change

# INV-INS-109 (a) — the freeze. MUST be empty, at the end of every group.
git -C $RVSEC_HOME diff 7e7acb69 -- \
  rvsec/rvsec-mop/src/main/resources/jca \
  rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java

# INV-INS-109 (b) — every hunk of the set diff needs an entry
uv run python scripts/gh101_divergence_record.py --check
uv run python scripts/gh101_divergence_record.py --refresh > $S/div.csv   # skeleton rows

# the four gates together
uv run pytest tests/parity/test_gh101_specset_gates.py --import-mode=importlib -o "addopts=" -q

# regenerate the records
uv run python scripts/gh101_predicate_inventory.py $MOP/jca_android -o data/gh101/predicate_inventory_jca_android.csv
uv run python scripts/gh101_predicate_edges.py --inventory data/gh101/predicate_inventory_jca_android.csv \
    --edges data/gh101/predicate_edges.csv --counts data/gh101/edge_counts_per_file.csv
uv run python scripts/gh101_conformance_check.py -o data/gh101/conformance_record.csv

# generate the whole derived set and check INV-INS-110  (~28 s since the re-budget)
rm -rf $S/gen && mkdir -p $S/gen/specs $S/gen/out
cp $MOP/jca_android/*.mop $S/gen/specs/
nice -n 15 $RVSEC_HOME/javamop/bin/javamop -d $S/gen/out -merge $S/gen/specs/*.mop
mv $S/gen/specs/*.rvm $S/gen/out/          # javamop leaves .rvm in the SOURCE dir
/usr/bin/time -v nice -n 15 $RVSEC_HOME/rv-monitor/bin/rv-monitor -d $S/gen/out -merge $S/gen/out/*.rvm
uv run python scripts/gh101_monitor_transition_check.py $S/gen/out/MultiSpec_1RuntimeMonitor.java

# COMPILE the generated monitor -- cheap, and it catches what generation does not
RT=$RVSEC_HOME/rv-monitor/rv-monitor-rt/target/rv-monitor-rt-0.9.3-SNAPSHOT.jar
javac -nowarn -proc:none -d $S/compile \
  -cp "$RVSEC_HOME/rvsec/rvsec-core/target/classes:$RVSEC_HOME/rvsec/rvsec-logger-csv/target/classes:$RT:$AJ" \
  $S/gen/out/MultiSpec_1RuntimeMonitor.java
# NOTE: rebuild rvsec-core first when you add a Property constant, or this fails on it.

# ONE specification, timed
mkdir -p $S/one && cp $MOP/jca_android/CipherSpec.mop $S/one/ && cd $S/one
nice -n 15 $RVSEC_HOME/javamop/bin/javamop -d $S/one CipherSpec.mop
/usr/bin/time -v timeout 900 nice -n 15 $RVSEC_HOME/rv-monitor/bin/rv-monitor -d $S/one $S/one/CipherSpec.rvm 2>&1 \
  | grep -Ei 'is generated|Exception in|Elapsed|Maximum resident|Exit status'

# event counts against the ceiling of 17
for f in $MOP/jca_android/*.mop; do printf "%3d  %s\n" $(grep -cE '^\s*event ' $f) $(basename $f); done | sort -rn | head

# the real API, never from memory
javap -classpath $AJ javax.crypto.Cipher | grep -E 'getInstance|init|update|doFinal|wrap|getIV'

# the two anchors, both directions
grep -l 'generatedCipher\[' $RULES/*.cryptsl $CRYSL152/*.crysl

# Java side — one module, no install, safe beside the other session
pgrep -af mvn; cd $RVSEC_HOME && nice -n 15 mvn -o -pl rvsec/rvsec-core test
```

`PointcutBudget` and `CoenableProbe` have their recipes in
`.claude/skills/rv-analyze-spec/scripts/README.md`. The classpath for `PointcutBudget` comes
from `mvn -o -q -pl rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine
dependency:build-classpath -Dmdep.outputFile=$S/pe-cp.txt`; `target/classes` was already
built at handoff.

---

## 11. Coordination with the parallel gh100 session — nothing owed

Session 6 checked, and the concern the session-6 handoff flagged as "ACT ON THIS" is
**resolved without action**:

| concern | status |
|---|---|
| descriptor drift | **moot.** Their task 4.3 pinned `results/gh99_jca_android_monitors/monitors/`, generated 2026-08-06, *before* any gh101 edit. Their 4.2 (red) and 6.2 (green) both ran over those same pinned bytes and are `[x]`. Your renames cannot invalidate them |
| your dependency on them | **satisfied.** Their task 5.3 is `[x]` (`48b57fc5`) — the key could not be widened, so they merged wrappers so the registry is single-valued by construction. Your Group 8 is unblocked |
| file overlap | none — you own `$MOP/jca_android` and `rvsec-core`; they own `rvsec-instrumentation-dexlib2/*` and two Python modules. Stage only your paths |
| Maven | shared reactor and `~/.m2`. Check `pgrep -af mvn` before any build. `mvn -o -pl rvsec/rvsec-core test` is scoped and safe |
| spec sync | you MODIFY *Specification Set Support (FR03)*; they MODIFY a different requirement, so order does not matter. Before syncing, `grep -ln "<Requirement title>" openspec/changes/*/specs/*/spec.md` |
| invariants | INV-INS-109 to 115 are yours, 104 to 108 theirs |
| git | same branch and repository, `refs #101`, stage only your paths, no rebase, no force-push, no reorder |

---

## 12. Decisions already settled — do not re-open

- **D-S0**: `jca` frozen, corrections to *specifications* in the derived set alone. Supersedes
  D1. Bounded by D-S10: the freeze covers what the instrument states, not the runtime it runs on.
- **D-S3 as revised**: the derived Cipher tables live in
  `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil`, a sibling class. Session 6 added
  `requiresPreparedIv` and `requiresPreparedGcm` to it, so the rule's conditional `REQUIRES`
  guards live beside the rule's `CONSTRAINTS` tables and the `.mop` carries no copy.
- **D-S7**: freeze check plus divergence record replace the parity check.
- **D-S8**: `jca_android` becomes a first-class `specification_set` value.
- **D-S9** and its three parts: repair all sixteen all-`fail` events; delete
  `MessageDigestSpec.reset`; uniform repair form, not absorbing states; the 70.4% is a
  **ceiling**, not a cause.
- **D-S10**: the predicate store is keyed by identity, in the shared class; shared code MUST
  NOT branch on the active specification set. (Verified in session 6: one `grep` hit in
  `rvsec-core`, a Javadoc sentence, no runtime branch.)
- **D-S11 as revised**: one event per **distinct binding profile**, not one per rule
  signature. `CipherSpec` budgeted to 14, not transcribed to 24.
- **D-S12**: `rv-monitor` is **not** repaired. The ceiling is a design constraint
  (INV-INS-115) and the alphabet is budgeted under it. The user decided this explicitly.
- **D-S13 (session 6)**: `!macced[_, plainText]` is **transcribed**, not recorded as
  inexpressible. The one-place projection is faithful *for this clause* because its first
  place is anonymous. The user decided this explicitly after being shown the rule text, the
  store's shape and the measured cost.
- D3, D5, D6; the spelling variants stay; case/alias normalisation repaired in the Cipher
  utility only.

---

## 13. Learnings worth carrying

- **Check the same claim from several angles**, and when the angles disagree, the tool wins.
  `reference/triangulation.md` has the full catalogue.
- **Diff both directions.** A one-sided comparison of the two CrySL anchors produced a table
  of twelve rules "dropping" predicates that was mostly renames and mostly wrong. The
  symmetric one took two minutes and gave the real answer.
- **Verify the enumerations in the artefacts against the material.** They are floors, not
  ceilings, and session 6 found three more instances: D-S10 mistyped the `SecureRandomSpec`
  reads, task 4.11 named two `neverTypeOf` rules where there are three, and a `grep -c` for
  `setObjectAsInAcceptingState` silently counted the `unset` calls too. Every count in the
  records now carries the command that produced it — keep that up.
- **Compile the generated monitor.** Generation succeeding proves the `.mop` parses and the
  automaton builds; it does not prove the event bodies compile. `javac` over
  `MultiSpec_1RuntimeMonitor.java` takes seconds and catches a missing constant, a missing
  import or a type error that the full reactor build would find an hour later.
- **Read the generated output before reasoning about `.mop` semantics.** Session 6 confirmed
  from the generated aspect that two events sharing a pointcut share **one advice** that
  dispatches both, each returning early on its own `condition` — which is exactly why a
  conforming/non-conforming pair over one pointcut is safe.
- **`condition(...)` suppresses the transition; a body read does not.** This is the single
  most consequential fact about how a `REQUIRES` is written in this set. A failing guard
  takes no transition, so the misuse surfaces as a sequence violation one call later instead
  of as the unsatisfied requirement it is. Every read session 4 and 6 added sits in a body
  for this reason. The `generatedKey` reads still sit in conditions — see §6.
- **Price the alphabet before designing it.** `n × (2ⁿ − 1)` coenable sets, ceiling 17. It
  decided both `CipherSpec` (14) and `MacSpec` (11).
- **The user pushes back on framing more cautious — or more defeated — than the evidence
  supports**, and has been right every time. Session 6's `!macced` answer changed from
  "record as inexpressible" to "transcribe" precisely because the user asked for the material
  to be opened up first: `me explique isso melhor primeiro`. When putting a choice to the
  user, show the rule text and the measurement, not a summary of them.
- **The user asked for less orchestration, not more.** The groups are linear on purpose. Do
  not fan them out into subagents or workflows.
