# Session handoff — continue gh101, JCA specification conformance (session 3)

> Paste this whole file as the first message of the new session.

---

## 0. Who you are and where you are

You are Claude Code in the RVSEC / RV-Android research codebase (PhD work of Pedro
Costa, `phtcosta@gmail.com`). Primary working directory:

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

Git branch **`modules`**. Tip when this file was written: `a0f43833`.

**`rv-android` is a subdirectory of the `rvsec` git repository, not a separate
repo.** One `git commit` covers both sides. This is why the freeze check can run
`git -C $RVSEC_HOME diff` over `rvsec/...` paths at all.

`$WS` = `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv`.
`RVSEC_HOME` is exported and points at `$WS/rvsec`. **Anything outside `rv-android`
must be written with an absolute path** — standing user instruction, for code, docs
and prose alike.

**Path trap that cost time in session 2.** There is a nested `rvsec` directory.
`$RVSEC_HOME` is `$WS/rvsec`, and the Maven modules live one level below it, so the
specifications are at

```
$WS/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android/     <- two `rvsec`
```

Writing `$WS/rvsec/rvsec-mop/...` gets you "File does not exist". Use `$MOP` from
§7 and you will not hit it.

A sibling session implements `gh100-weaver-emission-fidelity` on this same branch.
Do not rebase, force-push or reorder. Stage only your own paths. §8 covers the one
real coupling and the one thing you must relay to the user.

---

## 1. What this session must finish

Implement the rest of `openspec/changes/gh101-jca-spec-conformance/` — GitHub issue
[#101](https://github.com/PAMunb/rvsec/issues/101). **Progress: 35 of 64 tasks.**
Groups 1, 2, 3 and 3b are done and committed. Groups 4 to 9 remain. Start with
Group 4; §5 has the whole map already derived, so you do not have to rediscover it.

---

## 2. Non-negotiable working rules

Read `CLAUDE.md` at the repo root and at `$WS/rvsec/CLAUDE.md` first, then
`docs/WORKFLOW.md`.

1. **Follow the OpenSpec workflow rigorously.** Anything under
   `openspec/changes/gh101-*/` goes through the **skills** invoked with the
   `Skill` tool: `openspec-apply-change`, `openspec-update-change`,
   `openspec-verify-change`, `openspec-sync-specs`, `openspec-archive-change`.
   **Never** hand-write or hand-edit an OpenSpec artefact outside a skill that told
   you to. The `.mop`, Java and Python edits are normal work — the rule is about
   the artefacts. (Ticking a checkbox in `tasks.md` counts as an artefact edit and
   belongs inside `openspec-apply-change`.)
2. **The `jca` set is FROZEN** at commit `7e7acb69` (decision D-S0). Not one byte of
   `$MOP/jca`, not one byte of `$CORE/jca/util/CipherTransformationUtil.java`.
   Every correction lands in `jca_android` alone. You will read the same defective
   line twice and must fix only one copy; the freeze check exists to catch the urge.
3. **Do NOT touch the MetaCrySL tree** (`$WS/MetaCrySL`). It belongs to another
   session. `$WS/MetaCrySL/generated/api30/` (33 `.cryptsl`) is **read-only input**
   and is the oracle this change conforms to.
4. **NEVER start, stop or manage Android emulators.** No exceptions. Permanent.
5. **Never add `Co-Authored-By`** or any co-author trailer.
6. **Language**: code, comments, commit messages, issues and OpenSpec artefacts in
   **English**; prose to the user in **Brazilian Portuguese with correct
   accentuation**.
7. **P1–P4** (`CLAUDE.md`): simplicity; narrative docs that explain *why*; no
   backward compatibility; current-state comments only. In particular **P4 forbids
   migration commentary in the `.mop` files** — a comment says what the automaton
   does now and why, never "was added in task X".
8. **Terminology**: "MOP" = *monitored operations*, never "security operations".
9. **Read-only**: `$WS/ase-journal/dataset/results`, `$WS/rvsec-dataset`,
   `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/`. Do **not** run `uv run`
   from inside `$WS/rvsec-dataset` — it rebuilds that project's `.venv`. Use plain
   `python3` for probes outside `rv-android`.
10. Use the session scratchpad for temporary files, never `/tmp` directly.
11. **Commits**: `refs #101` during work, `closes #101` only in the final one.
12. **A campaign is occupying this machine** (load average was ~17 in session 2, a
    session named `rodar-SA-AND-INSTRUMENT`). Generating monitors is fine — two
    short JVMs, run them under `nice -n 15`. Ask before anything heavier. Never run
    `mvn install` without checking `pgrep -af mvn` first.

---

## 3. What session 2 did

Two commits, both green on every gate.

### `497e1c22` — the artefacts absorbed a reopened scope

`openspec-update-change` folded in the decision to repair all sixteen remaining
all-`fail` events, adding **Group 3b** between Groups 3 and 4. It is inserted, not
renumbered, so every group number already cited in issue #101, in `design.md` and
in the gh100 coordination keeps pointing at the same work. Decision **D-S9** in
`design.md` records the whole thing.

### `a0f43833` — Group 3b, the sixteen events

`scripts/gh101_monitor_transition_check.py` now reports **18 offenders on the
frozen set** and **none on the derived set**. That closed task 3.4 as well.

Fourteen of the sixteen took a Kleene prefix on the violating branch, three took
new rows in the `fsm` `SecureRandomSpec` already had, and one was deleted:

| file | events | how |
|---|---|---|
| `IvParameterSpec.mop` | `c3`, `c4` | `ere : (c3 \| c4)* (c1 \| c2)` |
| `SecretKeySpecSpec.mop` | `c3`, `c4` | `ere : (c3 \| c4)* (c1 \| c2)` |
| `PBEParameterSpecSpec.mop` | `c3` | `ere : c3* (c1 \| c2)` |
| `PBEKeySpecSpec.mop` | `f1`,`f2`,`err1`,`err2`,`err3` | `ere : (f1\|f2\|err1\|err2\|err3)* c1 c2`, **plus** `returning(PBEKeySpec s)` on `f1` and `f2` |
| `KeyPairGeneratorSpec.mop` | `initError` | `initError*` in both init positions |
| `SignatureSpec.mop` | `g3` | `(g3* g1 \| g3* g2) (...)` |
| `SecureRandomSpec.mop` | `c3`, `g4`, `setSeed3` | new `unsafeInit` state; `setSeed3 -> end` |
| `MessageDigestSpec.mop` | `reset` | **event removed** |

Fourteen new rows in `data/gh101/divergence_record.csv` (40 total, all recorded),
and `data/gh101/frozen_set_debt.md` gained two sections.

---

## 4. Three decisions session 2 made that you must not re-open

These were all put to the user before any of them was executed, and all three
changed what got written.

### D-S9a — `MessageDigestSpec.reset` is deleted, not placed

It was the only one of the sixteen that is not a violating branch. The generated
`api30/MessageDigest.cryptsl` declares `getInstance`, `update` and `digest` and
models no `reset` **at all** — so CogniCrypt ignores `reset()` calls entirely. The
`.mop` event had an empty body, wrote and read no property, reported nothing, and
was absent from the `ere`, so the all-`fail` row was the whole of its effect.
Placing it would mean deciding, without the rule's support, where `reset()` sits in
the order. (MetaCrySL *does* model `reset` for a different family, the BouncyCastle
digests in `samples/bc/AbstractMessageDigest.cryptsl` — and even there it is
declared in `EVENTS` and left out of the `ORDER`, the same defect one level up.)

### D-S9b — the repair form is uniform with Group 3, and is NOT stricter than it

The tempting repair is an **absorbing state**: the violating event poisons the
object and nothing afterwards can accuse it. It was considered and **rejected**.

Reading the `unsafeAlg` that task 3.1 had already committed showed it admits `g1`,
`g2` and `g3` and nothing else — so `TrustManagerFactory.getInstance("BAD")`
followed by `.init(keyStore)` still reaches `fail`. The same holds for `CipherSpec`,
`KeyManagerFactorySpec`, `MacSpec`, `KeyGeneratorSpec`, `KeyStoreSpec` and
`MessageDigestSpec`. **The accusation-one-call-later is a property of the whole
set, not of the files Group 3b touched.** Adopting absorption for a few files would
have left two repair philosophies in one set, and it trades a false positive for a
false negative (after poisoning, `sign()` with no `update()` goes unreported).

Consequence: **no automaton was re-derived by hand**, and the residue is recorded
in `frozen_set_debt.md` under "The residue both sets keep". **No issue has been
opened for it** — the user declined that option; it stays their call, like the two
rule gaps in `algorithm_naming.md`.

### D-S9c — the 70.4% is a ceiling, not a cause

`@fail` emits no message naming the event that triggered it, so `errors.csv` cannot
attribute an `InvalidSequenceOfMethodCalls` to a specific event. The figure says
the dominant error type is **concentrated in ten specifications, every one of which
carries an unconditional accuser** — it does not say the eighteen produced them.
`MessageDigestSpec` also accuses `digest()` with no preceding `update()`, which is
ordinary code. Splitting the 49,817 would need the corpus re-measured, which is an
explicit non-goal. `proposal.md`, `design.md` and `frozen_set_debt.md` all now say
"ceiling"; **do not let it drift back to a causal claim.**

The numbers, reproduced exactly in session 2 from
`$WS/ase-journal/dataset/results/errors.csv` (the error type lives in `unique_msg`,
field 4 of the `:::` composite, **not** in `message`):

| origin | `InvalidSequenceOfMethodCalls` | of category | of all 97,018 |
|---|---:|---:|---:|
| the 8 specifications carrying the sixteen | 23,292 | 32.9% | 24.0% |
| `TrustManagerFactorySpec` + `SSLContextSpec` | 26,525 | 37.5% | 27.3% |
| **together** | **49,817** | **70.4%** | **51.3%** |

---

## 5. Group 4 — already mapped, nothing written yet

`.mop` only, `jca_android` only. **20 edges over ten files**, all using `Property`
constants that already exist (the nine new ones are Group 5). Source of truth:
`data/gh101/predicate_edges.csv` filtered on `group == "4"`, and
`data/gh101/edge_counts_per_file.csv` for the per-file count.

| file | n | edges (CrySL clause → where it goes) |
|---|---:|---|
| `KeyPairSpec.mop` | 4 | `ENSURES generatedKeypair[this]` after `c1`; `ENSURES generatedPrivkey[retPriv]` after `gpr`; `REQUIRES generatedPrivkey[consPriv]` and `generatedPubkey[consPub]` read in `c1` |
| `CipherSpec.mop` | 4 | `REQUIRES randomized[ranGen]`, `!macced[_, plainText]`, `preparedIV[params]`, `preparedGCM[params]` |
| `MacSpec.mop` | 3 | `REQUIRES preparedHMAC[params]` on `i2`; `!encrypted[output1,_]` and `!encrypted[output2,_]` on `f1`/`f2` |
| `KeyStoreSpec.mop` | 2 | `ENSURES generatedPrivkey[key]` and `generatedPubkey[key]`, both in `gk1` |
| `SignatureSpec.mop` | 2 | `REQUIRES generatedPrivkey[priv]` on `i1`/`i2`; `generatedPubkey[pub]` on `i4` |
| `KeyGeneratorSpec.mop` | 1 | `REQUIRES randomized[ranGen]` on `init` |
| `KeyManagerFactorySpec.mop` | 1 | `REQUIRES generatedKeyStore[keyStore]` on `init` |
| `KeyPairGeneratorSpec.mop` | 1 | `REQUIRES preparedDH[params]` on `init3`/`init4` |
| `SecretKeySpec.mop` | 1 | `NEGATES generatedKey[this] after d` |
| `SecretKeySpecSpec.mop` | 1 | `ENSURES speccedKey[this]` |

**`KeyPairSpec.mop:38` is the wrong-constant defect the change names explicitly**:
`gpr` writes `Property.GENERATED_PUBLIC_KEY` over the *private* key — a copy of
`:32` with the value changed and the constant not. It is one of the four edges, not
an extra.

Three of the twenty are not one-line edits, and knowing this in advance saves a
false start:

- **`KeyGeneratorSpec.init` and `KeyManagerFactorySpec.init`** each fuse several
  overloads into one disjunctive pointcut and bind nothing but `target(k)`, so the
  argument the `REQUIRES` needs is unreachable. Use the idiom **task 3.1 already
  established** in `TrustManagerFactorySpec.init`: bind the single argument as
  `Object` and discriminate by type in the body. Read that file first; it is the
  worked example.
- **`SecretKeySpec.mop` has no `destroy` event at all**, so `NEGATES
  generatedKey[this] after d` has nowhere to be written. Add it, and put it in the
  automaton in the same edit — `ere : e1* d?`, which is exactly the rule's
  `ORDER ge*, d?`. An event added without a place in the automaton is the defect
  Group 3b just removed (INV-INS-110).

**Where a `REQUIRES` read goes.** In the **event body**, never as a
`condition(...)` guard. Task 3.2 recorded why and it is load-bearing: a failing
guard takes no transition, which silently removes the event from the automaton and
turns the *next* legitimate call into a sequence violation. Report an
`ErrorType.UnsatisfiedConstraint` naming which predicate was not established, the
way `SSLContextSpec` and `TrustManagerFactorySpec` now do.

Tasks 4.3 and 4.4 are records, not code: the two deliberate omissions (including
that the accepting-state mechanism they rest on is never read from any `.mop` and
is therefore inert at runtime), and `randomized[lSeed]` as inexpressible — a
provenance predicate over a primitive cannot be represented by a map keyed on
`equals`, and the write side is unsound too, because marking small `int` values as
randomised marks every equal literal in the process through the boxed-integer cache.

---

## 6. Remaining work after Group 4

- **Group 5** — new vocabulary. **9** new `Property` constants closing **11** edges
  (`generatedCipher` carries three, `generatedManagerFactoryParameters` two):
  `preparedAlg`, `preparedOAEP`, `generatedCipher`, `preparedRSA`, `preparedDSA`,
  `preparedEC`, `generatedManagerFactoryParameters`, `cipheredInputStream`,
  `cipheredOutputStream`. The enum goes 23 → 32, in
  `$CORE/Property.java`. **Each constant lands with its reader, in the same task** —
  a constant added without a reader is the defect this change exists to remove, and
  task 7.1's guard will fail on it. Task 5.2 also asks you to confirm the additions
  are invisible to the frozen set: no `jca` specification names any new constant,
  and the monitor generated from `jca` is unchanged against the base commit.
- **Group 6** — `jca_android` as a first-class `specification_set` value in
  `modules/rv-experiment/src/rv_experiment/config.py` (`:424` values, `:671`
  mapping). The only Python in `rv-android`. Check `CLAUDE.md`, `docs/PRD.md` and
  `.claude/project-info.md` for enumerations of the accepted values.
- **Group 7** — the write/read guard derived from the inventory (INV-INS-111, the
  last invariant still unverified), the deliberate-omission list as versioned data,
  regeneration of both inventories, and four record entries.
- **Group 8** — empirical verification, blocked on gh100 task 5.3. If it has not
  landed, **record as blocked citing the artefact; do not substitute a weaker
  check** (D-S6).
- **Group 9** — verification, lint, `/rv-verify rv-experiment`,
  `/rv-code-reviewer`, `/rv-docs-sync`.

Then: tick issue #101's acceptance criteria one by one **before** closing, any
criterion not literally met getting an inline note
(`- [x] ~~criterion~~ — superseded by …`), never a silent tick and never a blank
box. Sync the delta spec explicitly with `openspec-sync-specs` **before**
archiving, then `openspec archive gh101-jca-spec-conformance --skip-specs`. Final
commit uses `closes #101`.

---

## 7. Commands

```bash
cd /home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
MOP=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources      # note the nested rvsec
CORE=$RVSEC_HOME/rvsec/rvsec-core/src/main/java/br/unb/cic/mop
RULES=$WS/MetaCrySL/generated/api30                      # read-only oracle

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
uv run python scripts/gh101_divergence_record.py --refresh   # skeleton for new hunks

# the four gates together
uv run pytest tests/parity/test_gh101_specset_gates.py --import-mode=importlib -o "addopts=" -q

# regenerate the records
uv run python scripts/gh101_predicate_inventory.py $MOP/jca_android -o data/gh101/predicate_inventory_jca_android.csv
uv run python scripts/gh101_predicate_edges.py --inventory data/gh101/predicate_inventory_jca_android.csv \
    --edges data/gh101/predicate_edges.csv --counts data/gh101/edge_counts_per_file.csv
uv run python scripts/gh101_conformance_check.py -o data/gh101/conformance_record.csv

# generate monitors from a set and check INV-INS-110  (S = your scratchpad)
rm -rf $S/gen && mkdir -p $S/gen/specs $S/gen/out
cp $MOP/jca_android/*.mop $S/gen/specs/
nice -n 15 $RVSEC_HOME/javamop/bin/javamop -d $S/gen/out -merge $S/gen/specs/*.mop
mv $S/gen/specs/*.rvm $S/gen/out/          # javamop leaves .rvm in the SOURCE dir
nice -n 15 $RVSEC_HOME/rv-monitor/bin/rv-monitor -d $S/gen/out -merge $S/gen/out/*.rvm
uv run python scripts/gh101_monitor_transition_check.py $S/gen/out/MultiSpec_1RuntimeMonitor.java

# Java side — one module, no install, safe beside the other session
cd $RVSEC_HOME && mvn -o -pl rvsec/rvsec-core test
```

Always copy the `.mop` to the scratchpad before running javamop: **it writes `.rvm`
into the source directory.** Generating both sets takes well under a minute even
with the machine loaded.

---

## 8. Coordination with the parallel gh100 session

| concern | status |
|---|---|
| file overlap | none — you own `$MOP/jca_android` and `rvsec-core`; they own `$DEXLIB2/*` and two Python modules |
| dependency | one, yours on them: your Group 8 waits on their task 5.3 |
| Maven | shared reactor and `~/.m2`. Do not run `mvn install` while they build. `mvn -o -pl rvsec/rvsec-core test` is scoped and safe. Check `pgrep -af mvn` first |
| **descriptor drift — STILL UNRESOLVED** | their tasks 4.2/4.3/6.2 run V2 against **`jca_android`**, the set you are editing, and their 4.3 pins the descriptor and monitor sources. As of session 2 those had not run. **Their session was not alive** (`ListAgents` showed only `calibracao` and `rodar-SA-AND-INSTRUMENT`), so nobody was told. Ask the user to relay it, or message the session if `ListAgents` now shows it |
| spec sync | you MODIFY *Specification Set Support (FR03)*; they MODIFY a different requirement, so order does not matter. Before syncing, `grep -ln "<Requirement title>" openspec/changes/*/specs/*/spec.md` to confirm nothing else claims yours |
| invariants | INV-INS-109 to 113 are yours, 104 to 108 theirs |
| git | same branch and same repository, `refs #101`, stage only your paths, no rebase |

---

## 9. Decisions already settled — do not re-open

- **D-S0**: `jca` frozen, corrections in the derived set alone. Supersedes D1.
- **D-S3 as revised**: the derived Cipher tables live in
  `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil`, a sibling class in the
  existing package.
- **D-S7**: freeze check plus divergence record replace the parity check.
- **D-S8**: `jca_android` becomes a first-class `specification_set` value.
- **D-S9** and its three parts (§4): repair all sixteen; delete `reset`; uniform
  repair form, not absorbing states; the 70.4% is a ceiling.
- D3 (both sides on the same CrySL release), D5 (no conditioning by API level),
  D6 (uniform anchoring).
- **The spelling variants stay.** The translation-added spellings (`HMAC-SHA256`,
  `HMAC/SHA256`, `HMACSHA256`, `SHA256`) are kept and declared as translation
  artefacts, not removed.
- **Case/alias normalisation is repaired in the Cipher utility only.** The nine
  other call sites are recorded in `data/gh101/algorithm_naming.md`, not fixed.

---

## 10. Open questions that are the user's

- Whether to open GitHub issues for the findings recorded but not raised: the
  one-call-later residue (§4, D-S9b, thirteen specifications), and the two rule gaps
  in `algorithm_naming.md` — `X509` for `(Trust|Key)ManagerFactory` (6 apps) and
  `RSA/NONE/NoPadding` for `Cipher`, both absent from every list in the chain
  because neither CrySL nor MetaCrySL models provider **aliases**.
- Whether the deliberate upstream deviations in the `Cipher` rule (`NoPadding` and
  `PKCS1Padding` for RSA) are corrected or recorded. Transcribed as authored for
  now, which is what D-S4 requires.
- Whether the two deliberate predicate-graph omissions stay omissions. The
  substitution they rest on is half-built: `isInAcceptingState` is never read from
  any `.mop`, so the mechanism is inert at runtime.
- The board card for #101 is in "No Status" and cannot be moved from here — the `gh`
  token lacks the `project` scope. Only the user can run `gh auth refresh -s project`.

---

## 11. Learnings worth carrying

- **The enumerations in the artefacts are floors, not ceilings.** `gtm1` had four
  defects where three were listed; the all-`fail` pattern had eighteen events where
  two were listed. Verify counts against the material with a script, not against the
  prose that motivated them.
- **Run every new check against the frozen set first.** Its answer is independently
  known, so it is the baseline that tells you whether the check itself is complete.
  The transition checker passed the frozen set until it was taught that events
  landing in the empty parameter slice generate an `AbstractSynchronizedMonitor`
  rather than an `AbstractAtomicMonitor` — which is exactly where the defective
  events lived. **A check that passes too easily is a bug in the check.**
- **Read the code that is already committed before proposing a stricter standard.**
  Session 2 nearly hand-derived four automata to eliminate a residue that Group 3's
  own approved repair leaves standing. Ten minutes reading `TrustManagerFactorySpec`
  and `CipherSpec` turned a large risky change into a set of one-line edits.
- **Check whether the set already has an idiom for your problem.** The `g3*` prefix
  in `MacSpec`, `KeyGeneratorSpec`, `KeyStoreSpec` and `MessageDigestSpec` was the
  answer to fourteen of the sixteen events, and `MessageDigestSpec`'s own comment
  explains why it exists. The same will be true in Group 4: `TrustManagerFactorySpec`
  is the worked example for the fused-pointcut split.
- **The generated rule is the authority, including when it is silent.** `reset` was
  deleted because the rule models no `reset`, not because it looked useless.
- **Ask when the scope or the standard changes, not after.** Session 2 put three
  decisions to the user before executing any of them, and all three changed the
  outcome. The user engages with a precise question and a recommendation; they do
  not want a status check-in.
- **The user asked for less orchestration, not more.** The groups are linear on
  purpose. Do not fan them out into subagents or workflows.
