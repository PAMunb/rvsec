# Session handoff — continue gh101, JCA specification conformance (session 10)

> Paste this whole file as the first message of the new session.
> **Objective of this session: Groups 8 and 9 — the last nine tasks.** Everything before them is closed.

---

## 0. Who you are and where you are

You are Claude Code in the RVSEC / RV-Android research codebase (PhD work of Pedro Costa,
`phtcosta@gmail.com`). Primary working directory:

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

Git branch **`modules`**. Tip when this file was written: **`233df18a`** — session 7's commit.
**Sessions 8 and 9 are NOT committed.** You inherit a dirty gh101 tree; §5 lists exactly what
is yours. Run `git status` before assuming anything: the user may have committed in between,
and if `git log --oneline -1` is no longer `233df18a`, read that commit before touching anything.

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

That is the whole change. The freeze, the divergence record, the alphabet budget, the
conformance verdicts, the pairing guard and its omission list are machinery in service of it.
When a decision is genuinely open, the tie-breaker is: *which option makes the specification
say what the rule says?* And when the mechanism cannot say what the rule says, the answer is
never to quietly say something else — it is to record the gap.

Three habits follow from it and all three are load-bearing:

- **Go to the oracle, not to the translation.** The `.mop` is a secondary source and has
  been wrong before. Read the `.cryptsl`.
- **An `_` in a rule is an anonymous argument, and it licenses a wildcard.**
- **A predicate is only addable when both ends of its edge are modelled by a `.mop` in this
  set** (D-S14). A reader without a writer is worse than an open gap: reads live in event
  bodies, so an unsatisfiable requirement reports on *every conforming call*.

Group 7 mechanised the third habit — `scripts/gh101_predicate_pairing_check.py` now fails on
a write with no reader *and* on a read with no writer. Group 8 is the last thing that is not
mechanical: it asks whether the two hot specifications actually report differently now.

---

## 2. Read this first: the skill has the method

`.claude/skills/rv-analyze-spec/` exists so no session re-derives what took an afternoon to
learn. Load it with the `Skill` tool before touching a `.mop`, and read at least:

- `reference/triangulation.md` — the method. Twelve angles for checking a claim. Short, and
  the part that matters most.
- `reference/generator-pipeline.md` — the generator, the ceiling, every reproducible number.
- `reference/pointcut-semantics.md` — what the weaver actually matches.
- `reference/crysl-to-mop.md` — the alphabet-budget method and the worked `Cipher` example.
- `scripts/README.md` — the two harnesses (`CoenableProbe`, `PointcutBudget`). Both drive
  **production classes**, not re-implementations.

**Groups 8 and 9 touch no `.mop`.** Group 8 runs the instrument and reads what it reports;
Group 9 builds, verifies and lints. Read the skill before any `.mop` edit if the work drifts
there — and if it does drift there, that is a finding worth stating, not a task to absorb
silently.

---

## 3. What the change is, and where it stands

Implement `openspec/changes/gh101-jca-spec-conformance/` — GitHub issue
[#101](https://github.com/PAMunb/rvsec/issues/101).

**75 of 84 tasks complete.** `openspec validate` passes. Groups 1, 2, 3, 3b, 4, 4b, 5, 6 and
**7** are **closed**. Remaining: **Groups 8 (2 tasks) and 9 (7 tasks)**.

The task checkboxes are accurate as of the end of session 9. Do not assume that of any future
state without re-checking.

**No decision is owed by the user.** Both remaining groups are unblocked.

---

## 4. Non-negotiable working rules

Read `CLAUDE.md` at the repo root and at `$WS/rvsec/CLAUDE.md` first, then `docs/WORKFLOW.md`.

1. **Follow the OpenSpec workflow rigorously.** Anything under `openspec/changes/gh101-*/`
   goes through the **skills** invoked with the `Skill` tool: `openspec-apply-change`,
   `openspec-update-change`, `openspec-verify-change`, `openspec-sync-specs`,
   `openspec-archive-change`. **Never** hand-write or hand-edit an OpenSpec artefact outside
   a skill that told you to. Python, Java and `.mop` edits are normal work — the rule is
   about the artefacts. **Ticking a checkbox in `tasks.md` counts as an artefact edit** and
   belongs inside `openspec-apply-change`. Revising `design.md`, `proposal.md` or `tasks.md`
   *content*, or adding a delta spec, belongs inside `openspec-update-change`, which
   **confirms every edit with the user before writing**. `data/gh101/*` is versioned data,
   **not** an OpenSpec artefact — edit it directly.
2. **The `jca` set is FROZEN** at commit `7e7acb69` (D-S0). Not one byte of `$MOP/jca`, not
   one byte of `$CORE/jca/util/CipherTransformationUtil.java`. Every correction to a
   **specification** lands in `jca_android` alone. D-S10 bounds what the freeze covers.
3. **Do NOT repair `rv-monitor`.** Recorded decision D-S12, taken by the user.
4. **Do NOT touch the MetaCrySL tree** (`$WS/MetaCrySL`). It belongs to another session.
   `$WS/MetaCrySL/generated/api30/` (33 `.cryptsl`) is **read-only input**. Same for the
   CrySL 1.5.2 corpus (47 `.crysl`) at
   `$WS/CryptoAnalysis/CryptoAnalysis/src/main/resources/JavaCryptographicArchitecture/`.
5. **NEVER start, stop or manage Android emulators.** No exceptions. Permanent. This is
   sharper than usual this session, because **Group 8 needs a device**: the only admissible
   route is `uv run rv-experiment run` / `rv-platform run`, which manage the whole lifecycle
   themselves. No `emulator`, no `adb emu kill`, no `adb install` by hand.
6. **Never add `Co-Authored-By`** or any co-author trailer.
7. **Language**: code, comments, commit messages, issues, OpenSpec artefacts and these
   handoffs in **English**; prose to the user in **Brazilian Portuguese with correct
   accentuation**.
8. **P1–P4** (`CLAUDE.md`): simplicity; narrative docs that explain *why*; no backward
   compatibility; current-state comments only. **P4 forbids migration commentary** — a
   comment says what the code does now and why, never "was added in task X".
9. **Terminology**: "MOP" = *monitored operations*, never "security operations".
10. **Read-only**: `$WS/ase-journal/dataset/results`, `$WS/rvsec-dataset`,
    `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/`. Do **not** run `uv run` from
    inside `$WS/rvsec-dataset`. Use plain `python3` for probes outside `rv-android`.
11. Use the session scratchpad for temporary files, never `/tmp` directly. **Always copy a
    `.mop` to the scratchpad before running javamop — it writes the `.rvm` into the source
    directory.** Same rule for testing a guard: copy the set, never mutate `$MOP`.
12. **Commits**: `refs #101` during work, `closes #101` only in the final one. **Commit only
    when the user asks.** The user does ask, often, right after something is finished. Stage
    only gh101 paths — the working tree holds **~548 other changed files** belonging to other
    sessions, and `git add -A` would sweep them in. Use the path list in §10 verbatim.
13. **A campaign shares this machine.** Generating monitors is fine under `nice -n 15`. Watch
    `free -g`. Never run `mvn install` without checking `pgrep -af mvn` first.
    `mvn -o -pl rvsec/rvsec-core test` is scoped and safe. **Task 9.1 is a full reactor
    build** — that one has to be coordinated, see §8.
14. **Do not `pkill -f logicrepository.Main`** while your own shell command line contains
    that string — session 4 killed its own wrapper that way. The same trap makes
    `pgrep -af mvn` match your own wrapper; read the output before concluding a build is
    running.
15. **`sleep N` in the foreground is blocked by the harness.** Use `run_in_background: true`
    and wait for the notification, or an `until … done` loop. A Group 8 experiment run is
    long — start it in the background and let the notification come.
16. **CI contract for pytest**: always `--import-mode=importlib -o "addopts="`. Without them
    conftest isolation breaks across modules and collection fails.
17. **The formatter is `black`, not `ruff`.** `ruff` is not installed; `uv run ruff` fails to
    spawn. Use `.venv/bin/black` and `.venv/bin/flake8` (line length 88, from
    `pyproject.toml`). **The five `scripts/gh101_*.py` and the gates file were authored at
    ~92 columns and `black --check` would reformat four of them.** Format only the lines you
    write; reformatting a sibling file is diff noise that hides your change. `__main__.py`
    already carries ~20 pre-existing `E501`s — flake8 is not a gate in this repo.

---

## 5. Exact state you inherit

**Committed**, in `233df18a` — everything sessions 3 to 7 produced:

```
rv-android/data/gh101/*                       (9 files: README.md, the CSVs, frozen_set_debt.md,
                                               algorithm_naming.md)
rv-android/scripts/gh101_*.py                 (5: conformance_check, divergence_record,
                                               monitor_transition_check, predicate_edges,
                                               predicate_inventory)
rv-android/tests/parity/test_gh101_specset_gates.py
rv-android/docs/20260807_handoff_gh101_sessao7.md
rv-android/openspec/changes/gh101-jca-spec-conformance/{proposal,design,tasks}.md
rv-android/openspec/changes/gh101-jca-spec-conformance/specs/instrumentation/spec.md
rvsec/rvsec-core/src/main/java/br/unb/cic/mop/{ExecutionContext,Property}.java
rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/AndroidCipherTransformationUtil.java
rvsec/rvsec-core/src/test/java/br/unb/cic/mop/{ExecutionContextTest,...}.java
rvsec/rvsec-mop/src/main/resources/jca_android/*.mop   (13 files)
```

**Uncommitted and yours** — sessions 8 (Group 6) and 9 (Group 7):

```
M  rv-android/CLAUDE.md
M  rv-android/README.md
M  rv-android/docker/README.md
M  rv-android/docs/PRD.md
M  rv-android/data/gh101/README.md                     <- session 9
M  rv-android/data/gh101/frozen_set_debt.md            <- session 9
M  rv-android/modules/rv-experiment/CLAUDE.md
M  rv-android/modules/rv-experiment/README.md
M  rv-android/modules/rv-experiment/src/rv_experiment/{__main__,config,constants}.py
M  rv-android/modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py
M  rv-android/modules/rv-experiment/tests/{test_config_jit,test_config_validation}.py
M  rv-android/modules/rv-monitor-generator/README.md
M  rv-android/tests/parity/test_gh101_specset_gates.py <- session 9, fifth gate
M  rv-android/openspec/changes/gh101-jca-spec-conformance/{proposal,design,tasks}.md
M  rv-android/openspec/changes/gh101-jca-spec-conformance/specs/instrumentation/spec.md
?? rv-android/openspec/changes/gh101-jca-spec-conformance/specs/experiment/spec.md
?? rv-android/data/gh101/predicate_omissions.csv       <- session 9
?? rv-android/scripts/gh101_predicate_pairing_check.py <- session 9
```

**Uncommitted and NOT yours: ~548 files.** They belong to other sessions (gh100,
`rvsec-instrumentation-dexlib2`, experiment directories, `docs/architecture/*`,
`modules/rvagent-tool/*`, ~25 untracked `scripts/*.py` from campaign work). Leave them alone
and never stage by wildcard.

Checks at the moment of handoff, **all run in session 9, all green**:

| check | result |
|---|---|
| Freeze, INV-INS-109 a | **empty diff** |
| Divergence record, INV-INS-109 b | **106 hunks, all recorded** |
| Pairing guard, INV-INS-111 | 25 written, 14 read, **11 recorded omissions** |
| `tests/parity/test_gh101_specset_gates.py` | **5 passed** (four gates plus the new one) |
| `openspec validate … --type change` | **valid** |
| Frozen inventory vs Group 1 baseline | **identical byte for byte** |
| `black`/`flake8` over the new script and the new test | clean |

Not re-run in session 9 (nothing that would move them changed since session 7): whole-set
generation (27.8 s / 1.83 GB, INV-INS-110 clean), `javac` over the generated monitor
(57 classes), `mvn -o -pl rvsec/rvsec-core test` (30 tests), frozen-set monitor byte-identity.
**Group 9 re-runs all of these** — see §8.

---

## 6. What session 9 did — Group 7 closed

### 7.1 the guard, 7.2 the omission list, 7.3 the negative test

`scripts/gh101_predicate_pairing_check.py` enforces INV-INS-111. It **does not trust the
committed inventory**: it imports `inventory_set` from `gh101_predicate_inventory.py`,
recomputes the sites from the `.mop` files, and fails in four classes —

| class | why it is a defect |
|---|---|
| the committed inventory no longer matches the specifications | a stale CSV would quietly decide the answer |
| a constant written, unread and unlisted | the `ENSURES` was transcribed and the `REQUIRES` was not |
| a constant read that nothing writes | the requirement is unsatisfiable, so it reports on every conforming call (D-S14) |
| a listed entry that stopped being true | the record outlived the defect |

**The second failure class is not in INV-INS-111's text.** It was added because D-S14's whole
argument rests on it, it costs three lines, and it is empty today; the docstring says so.
That is a deliberate, declared widening — do not silently remove it, and do not silently
widen anything else the same way without saying so.

`data/gh101/predicate_omissions.csv` — 20 rows, columns `kind, constant, predicate, specs,
reason, task`, two kinds:

- `constant-write-no-read` (11): `DIGESTED`, `GENERATED_KEY_PAIR`, `GENERATED_MAC`,
  `GENERATED_TRUST_MANAGER`, `GENERATE_SSL_CONTEXT`, `GENERATE_SSL_ENGINE`, `PREPARED_PBE`,
  `SIGNED`, `SPECCED_KEY`, `VERIFIED`, `WRAPPED_KEY`.
- `predicate-no-constant` (9): the eight of task 5.1d plus `generatedMessageDigest` from
  task 4.3 — which is what task 5.4 required.

The eleven fall into three reasons, each checked against **both** CrySL anchors rather than
against the `.mop`: terminal in both corpora (7 of them, no rule requires the predicate);
the consuming rule has no `.mop` in this set (`PREPARED_PBE` → `AlgorithmParameters`,
`SPECCED_KEY` → `SecretKeyFactory`/`KeyFactory`); and the clause anonymises the place
(`GENERATED_MAC`, whose only consumer is `!macced[_, plainText]`, and
`GENERATED_TRUST_MANAGER`, where the API 30 rule ensures `generatedTrustManager` of the
factory *and* of the array and `SSLContext` requires only the array).

7.3 ran the guard against a scratch copy with `GENERATED_CIPHER` mistyped in `CipherSpec`:
it failed with both pairing classes at once. The stale-entry and no-reason paths were
exercised too.

### 7.4 both inventories regenerated

`jca` is **identical to its Group 1 baseline byte for byte** — the freeze's second witness.
`jca_android` went from 85 sites to **127 (58 writes, 56 reads, 13 removals)**, and the
attribution table is in `data/gh101/README.md` §"The predicate inventory, after the repairs":
29 reads added, 12 writes added, 4 removals added, 2 writes moved to the right constant, and
3 writes removed with the `CipherSpec` events `u2`/`u4`/`f6` that the alphabet re-budget
dropped. Every one of those sites sits inside a hunk the divergence record already names with
its task, so attribution is mechanical rather than a matter of reading.

The constant classes went from *3 live edges, 18 write-only, 1 read-never-written, 1
removed-only* to *14 live edges, 11 recorded write-only, **0** read-never-written, **0**
removed-only*.

### 7.5 / 7.6 / 7.7 the three records

`frozen_set_debt.md` already carried 7.5 and 7.6 in the two consequences of its opening.
7.7 existed only in `data/gh101/README.md` §"The conformance verdicts" and in the
`instrumentation` delta, so a third consequence was added beside the other two: the derived
profile models **availability, not recommendation**.

### Two things that were corrected in passing

- `data/gh101/README.md` said the divergence record held **100** hunks with kinds 12/52/39/1.
  The record holds **106**, 12/51/42/1. Corrected.
- `design.md` said `Property.java` goes from "23 today, 32 after" — the plan before D-S14 cut
  the nine additions to one. It is **23 → 25** (`GENERATED_CIPHER` by D-S14, `MACED` by D-S13).
  Corrected through `openspec-update-change`, with the user's confirmation, together with the
  guard's input column.

### One decision worth knowing before you touch the records

**`predicate_edges.csv` and `edge_counts_per_file.csv` are the Group 1 yardstick and are
deliberately NOT regenerated.** Session 9 regenerated them following the previous handoff's
command block and reverted. The script carries tables fixed at Group 1 —
`PREDICATE_TO_PROPERTY` has no `generatedCipher`, and `WRONG_CONSTANT` / `DELIBERATE_OMISSION`
are hardcoded — so a regeneration flips the repaired edges to `present` while keeping two
`wrong-constant` verdicts and the `generatedCipher` omission that Groups 4 and 5 closed. It
produces a record that is half true. Worse, `data/gh101/README.md` reproduces "11 edges over
9 predicates" from that file and task 5.1d's decision was taken against it. Task 7.4's text
asks for the **two inventories**, and only those. Both files now say so in the file table.

---

## 7. The two standing questions the user asks

### "o que mudou da spec original para essa e o motivo?"

Every difference is enumerated, one row per diff hunk, in `data/gh101/divergence_record.csv`
— **106 hunks, all recorded**, each with `kind`, a prose `reason` and the task that
introduced it. Checked mechanically in both directions
(`scripts/gh101_divergence_record.py --check`, INV-INS-109 b). Run it before answering from
memory.

### "esta comparando com a spec crysl?"

Yes, and it is the anchor of the whole change — see §1. `data/gh101/conformance_record.csv`
carries a verdict for all 23 derived specifications; `data/gh101/predicate_edges.csv` is the
clause-by-clause comparison, anchored to **CrySL 1.5.2** on purpose and frozen at Group 1;
`data/gh101/predicate_omissions.csv` is every edge that stays open, with the reason. D-S14
settles what the anchor does and does not decide.

---

## 8. THIS SESSION'S OBJECTIVE — Groups 8 and 9

Run the work through `openspec-apply-change` (rule 1). Tick each checkbox as it lands.

### Group 8 — the empirical verification, and it is not relaxed (D-S6)

**It is unblocked.** Issue #100's task 5.3 — the wrapper registry key — landed in commit
`48b57fc5`. Confirm that before starting: `git log --oneline | grep 48b57fc5`, and read the
commit rather than trusting this line.

**8.1** verify empirically that the corrected `TrustManagerFactorySpec` and `SSLContextSpec`
report as intended under the derived set. **8.2** confirm the corrected allow-lists become
observable, in particular that the `SSLContextSpec` label stops depending on a variable that
is never written.

**What the observable actually is**, from `data/gh101/frozen_set_debt.md`
§"Events that accuse unconditionally":

| specification | frozen behaviour in the published campaign | what the repair should change |
|---|---|---|
| `SSLContextSpec` | `unsafe_protocol` never fires, so `currentProtocol` keeps `""` and the `UnsafeProtocol` message reads **`but found .`** — 51 events | the message names the protocol that was used |
| `TrustManagerFactorySpec` | same shape for `UnsafeAlgorithm` — 8,371 events with the empty label | the message names the algorithm |

So 8.2 has a crisp, falsifiable form: **the label stops being empty.** That is cheaper to
observe than a violation count and it is exactly the variable D-S6 names.

**How to run it.** Rule 5 is absolute: you may not touch an emulator. The admissible route is
`uv run rv-experiment run --specification-set jca_android …`, which manages generation,
instrumentation, the emulator lifecycle and collection itself — and which accepts the derived
set by name only because Group 6 landed (D-S8). Start it with `run_in_background: true`
(rule 15) and read `results/<id>/`. A small APK set is enough: the claim is about a label, not
about a rate. `apks_examples/` is the obvious candidate; `docs/WORKFLOW.md` and
`.claude/project-info.md` carry the full CLI.

**If it cannot be run** — the machine is busy with the campaign, the run fails for reasons
outside this change, whatever it is — **record 8.1 as blocked citing the artefact. Do not
substitute a weaker check** (D-S6). A generated-monitor inspection is not the empirical
verification; it is a different claim. Say which one you made.

### Group 9 — verification

- **9.1 full reactor build.** `cd $RVSEC_HOME && mvn install` from the root, both sets
  generating monitors without error. The reactor and `~/.m2` are shared with the gh100
  session: check `pgrep -af mvn` first (and read the output — your own wrapper matches),
  and check `free -g`. `nice -n 15`.
- **9.2** conformance record, 23 of 23, no blanks (INV-INS-113).
- **9.3** freeze check and divergence-record check a final time (INV-INS-109 a and b). Add
  the pairing guard — it is the same class of check and it is now a gate.
- **9.4** `/rv-qa-lint-fix` over the Python touched. Mind rule 17: the gh101 scripts are ~92
  columns and were authored that way; do not let a fixer reformat four files you did not
  write.
- **9.5** `/rv-verify rv-experiment`.
- **9.6** `/rv-code-reviewer` via the `Skill` tool.
- **9.7** `/rv-docs-sync` for anything Group 6 made stale. **Task 6.3 absorbed most of it** —
  re-run the grep in §10 before concluding there is nothing left, and remember
  `docs/architecture/subsystem-rv-experiment.md` is modified by another session and does
  **not** enumerate specification sets, so it is not yours to touch.

Also re-run, at the end, what session 9 did not: whole-set generation with INV-INS-110 clean,
`javac` over the generated monitor, `mvn -o -pl rvsec/rvsec-core test`, frozen-set monitor
byte-identity. §10 has every command.

---

## 9. After Groups 8 and 9

1. Tick issue #101's acceptance criteria one by one **before** closing, any criterion not
   literally met getting an inline note (`- [x] ~~criterion~~ — superseded by …`), never a
   silent tick and never a blank box.
2. Sync the delta specs explicitly with `openspec-sync-specs` **before** archiving — it now
   has **two** capabilities to sync, `instrumentation` and `experiment`; the skill enumerates
   them from the CLI, so it picks both up on its own, but check that it did.
3. `openspec archive gh101-jca-spec-conformance --skip-specs`.
4. Final commit uses `closes #101`.

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

# ---- Group 8: is #100 task 5.3 really in? ----
git -C $RVSEC_HOME log --oneline | grep 48b57fc5
git -C $RVSEC_HOME show 48b57fc5 --stat

# ---- Group 8: the run. BACKGROUND it (rule 15). NEVER touch the emulator (rule 5). ----
uv run rv-experiment run --tools monkey --specification-set jca_android \
  --apks-dir ./apks_examples --timeouts 60 --name gh101_group8
# then read results/<id>/ ; the observable is the LABEL, not the count:
grep -rn "but found \." results/<id>/ | head        # frozen symptom -- must NOT appear
grep -rn "UnsafeProtocol\|UnsafeAlgorithm" results/<id>/ | head

# ---- the four record checks (9.2, 9.3) ----
uv run python scripts/gh101_conformance_check.py -o data/gh101/conformance_record.csv
uv run python scripts/gh101_divergence_record.py --check
uv run python scripts/gh101_predicate_pairing_check.py
git -C $RVSEC_HOME diff 7e7acb69 -- \
  rvsec/rvsec-mop/src/main/resources/jca \
  rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java

# the five gates together
uv run pytest tests/parity/test_gh101_specset_gates.py --import-mode=importlib -o "addopts=" -q

# the inventories -- regenerate and compare (7.4 already did this; 9.3 confirms it holds)
uv run python scripts/gh101_predicate_inventory.py $MOP/jca_android -o data/gh101/predicate_inventory_jca_android.csv
uv run python scripts/gh101_predicate_inventory.py $MOP/jca          -o $S/inventory_jca_now.csv
diff $S/inventory_jca_now.csv data/gh101/predicate_inventory_jca.csv && echo "  frozen inventory identical"
# DO NOT regenerate predicate_edges.csv / edge_counts_per_file.csv -- see §6, last note.

# the write/read pairing by hand, if you want the shape rather than the verdict
python3 -c "
import csv, collections
rows=list(csv.DictReader(open('data/gh101/predicate_inventory_jca_android.csv')))
W=collections.defaultdict(set); R=collections.defaultdict(set)
for r in rows:
    if r['kind'] in ('WRITE','READ'):
        (W if r['kind']=='WRITE' else R)[r['property']].add(r['spec'])
for p in sorted(set(W)|set(R)):
    w,rd=len(W.get(p,())),len(R.get(p,()))
    print(f'{p:30}{w:>3}{rd:>3}', 'WRITE-ONLY' if w and not rd else ('READ-ONLY' if rd and not w else 'ok'))"

# Python quality (rule 17 -- ruff is NOT installed; format only what you wrote)
uv run pytest modules/rv-experiment/tests --import-mode=importlib -o "addopts=" -q
.venv/bin/black --check --diff <files>
.venv/bin/flake8 <files> --max-line-length 88

# task 9.7 -- anything left enumerating the accepted values?
grep -rn 'jca., .generic., .custom\|jca, generic, custom' --include=*.md --include=*.py . \
  | grep -vE '^\./(backup|experimento|results|out|openspec/specs|docs/2026)'

# generate the whole derived set and check INV-INS-110  (~28 s)
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

# Java side -- one module, no install, safe beside the other session
pgrep -af mvn; cd $RVSEC_HOME && nice -n 15 mvn -o -pl rvsec/rvsec-core test
# task 9.1 -- the FULL reactor. Coordinate first.
pgrep -af mvn; free -g; cd $RVSEC_HOME && nice -n 15 mvn install

# COMMIT -- stage only these paths; the tree holds ~548 files that are not yours.
cd $RVSEC_HOME && git add \
  rvsec/rvsec-core \
  rvsec/rvsec-mop/src/main/resources/jca_android \
  rv-android/data/gh101 \
  rv-android/scripts/gh101_*.py \
  rv-android/tests/parity/test_gh101_specset_gates.py \
  rv-android/openspec/changes/gh101-jca-spec-conformance \
  rv-android/modules/rv-experiment \
  rv-android/modules/rv-monitor-generator/README.md \
  rv-android/CLAUDE.md rv-android/README.md rv-android/docs/PRD.md rv-android/docker/README.md \
  rv-android/docs/20260808_handoff_gh101_sessao9.md \
  rv-android/docs/20260808_handoff_gh101_sessao10.md
git diff --cached --name-only    # READ IT before committing
```

---

## 11. Coordination with the parallel gh100 session

| concern | status |
|---|---|
| descriptor drift | **moot.** Their tasks ran over monitor bytes pinned on 2026-08-06, before any gh101 edit |
| your dependency on them | **satisfied.** Their task 5.3 is `[x]` (`48b57fc5`); Group 8 is unblocked |
| file overlap | none — you own `$MOP/jca_android`, `rvsec-core`, `rv-experiment`, `data/gh101`, `scripts/gh101_*` and the root docs; they own `rvsec-instrumentation-dexlib2/*` and two other Python modules |
| Maven | shared reactor and `~/.m2`. Check `pgrep -af mvn` before any build. **Task 9.1 is a full `mvn install`** — coordinate, do not just launch it |
| spec sync | you MODIFY *Specification Set Support (FR03)* and *Just-in-Time Sub-Module Configuration (FR17)*, and restate INV-INS-09 and INV-EXP-03; they MODIFY a different requirement of `instrumentation`. Before syncing, `grep -ln "<Requirement title>" openspec/changes/*/specs/*/spec.md` |
| invariants | INV-INS-109 to 115 are yours, plus the restatements of INV-INS-09 and INV-EXP-03; 104 to 108 are theirs |
| git | same branch and repository, `refs #101`, stage only your paths, no rebase, no force-push, no reorder |

---

## 12. Decisions already settled — do not re-open

- **D-S0**: `jca` frozen, corrections to *specifications* in the derived set alone. Bounded by
  D-S10: the freeze covers what the instrument states, not the runtime it runs on.
- **D-S3 as revised**: the derived Cipher tables live in
  `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil`, a sibling class.
- **D-S5**: the write/read pairing is a guard, not a convention. **Done, Group 7.**
- **D-S6**: the empirical verification is last and is **not relaxed** — **this is Group 8.**
- **D-S7**: freeze check plus divergence record replace the parity check.
- **D-S8**: `jca_android` is a first-class `specification_set` value. **Done, Group 6.**
- **D-S9**: repair all eighteen all-`fail` events; uniform repair form; the 70.4% is a
  **ceiling**, not a cause. Corollary that keeps mattering: **a read goes in the event body,
  never in `condition(...)`** — a failing guard takes no transition, so the misuse resurfaces
  as a sequence violation one call later instead of as the unsatisfied requirement it is.
- **D-S10**: the predicate store is keyed by identity, in the shared class; shared code MUST
  NOT branch on the active specification set.
- **D-S11 as revised**: one event per **distinct binding profile**, not one per rule
  signature. `CipherSpec` budgeted to 14 — and it is exactly 14 today.
- **D-S12**: `rv-monitor` is **not** repaired. The ceiling (17 events) is a design constraint
  (INV-INS-115). The user decided this explicitly.
- **D-S13**: `!macced[_, plainText]` is **transcribed**, not recorded as inexpressible.
  `MACED` holds the second place; `GENERATED_MAC` holds the first and is a recorded omission.
- **D-S14**: **Group 5 adds `generatedCipher` alone.** A predicate is addable only when its
  producing rule *and* its consuming rules are all modelled by a `.mop` in this set; six of
  the bucket's nine lack a producer here and two lack a consumer anywhere. The eight are
  recorded in `predicate_omissions.csv`, not approximated. `generatedMessageDigest` stays
  omitted under the same criterion.
- D3, D5, D6; the spelling variants stay; case/alias normalisation repaired in the Cipher
  utility only.

---

## 13. Learnings worth carrying

- **Check the same claim from several angles**, and when the angles disagree, the tool wins.
  `reference/triangulation.md` has the full catalogue.
- **Verify the mechanism at source before asserting it.** Session 7's record said the
  accepting-state substitute had "0 readers". True of the `.mop` sets — but `grep` also found
  `hasEnsuredPredicate` used throughout the `rvsec-agent` test suite, which looked like a
  contradiction until two more angles settled it: `ExecutionContext.java:153-160` scans only
  `context.values()` and never `acceptingState`, and `rvsec-agent/pom.xml:106` weaves the
  **frozen `jca`** set. Three angles, one answer.
- **A handoff's command block is a convenience, not an instruction.** Session 9's §10 grouped
  the `predicate_edges.csv` regeneration under task 7.4; the task's own text asks only for the
  two inventories, and running the extra command produced a half-true record that had to be
  reverted. **When a command block and a task text disagree, the task text wins.**
- **A record generated from hardcoded tables is a snapshot, not a query.**
  `gh101_predicate_edges.py` carries `PREDICATE_TO_PROPERTY`, `WRONG_CONSTANT` and
  `DELIBERATE_OMISSION` fixed at Group 1. Re-running it after the repairs does not re-derive
  those tables. Know which of your scripts are queries and which are snapshots.
- **Grep the oracle with the oracle's spelling.** `generatedKeypair`, not `generatedKeyPair`;
  a capitalised `P` returns "no consumer anywhere", which is a conclusion, not a null result.
  The same trap: `verified[sign]` in API 30 versus `verified[verified, sign]` in 1.5.2.
- **Prose drifts from the data it summarises.** `data/gh101/README.md` said 100 hunks while
  the record held 106. Recount from the CSV before quoting a number, including one you wrote.
- **A handoff's list of sites is a floor, never a ceiling.** Session 8's handoff said Group 6
  lived in one file; the gate that decided whether the feature worked at all was a
  `click.Choice` in another. Grep for the *value*, not for the file you were pointed at.
- **`"jca_android"` contains `"jca"`.** Any assertion, guard or grep written as a substring
  match over a path or a set name passes on the derived set as readily as on the frozen one.
  Match tails and whole tokens.
- **A decorator can make a test assert nothing.** `ErrorHandler.handle_errors` defaults to
  `reraise=False`, so `validate()` logs its `ValueError` and returns. `functools.wraps`
  exposes `__wrapped__`; call that when the assertion is about the check.
- **An enumeration in a spec does not degrade gracefully.** It states, closed, that the new
  value does not exist. Grep the *main* specs, not only the delta.
- **Verify enumerations in artefacts against the material.** Session 7 found `design.md`
  claiming three edges where the CSV said two; session 9 found it claiming 32 `Property`
  constants where D-S14, in the same document, had settled on 25.
- **Two tools that both "diff" do not agree on hunk boundaries.** `diff -U0` and Python's
  `difflib.unified_diff` group adjacent changes differently, and the divergence record is
  keyed by a hash of a hunk's changed lines. Reason about that record with the script's own
  `hunks()` function, never with the shell `diff`.
- **The divergence record's hunk digest is not unique across files.** `24de88ca2fff`
  (`i1 -> final`) occurs in both `KeyManagerFactorySpec.mop` and `TrustManagerFactorySpec.mop`.
  **Key by `(file, hunk)`.**
- **A guard must be shown to fail.** Passing proves nothing on its own — session 9's 7.3
  mistyped a constant in a scratch copy and watched two failure classes fire. Never mutate
  `$MOP` to test a check.
- **Compile the generated monitor.** Generation succeeding proves the `.mop` parses and the
  automaton builds; it does not prove the event bodies compile. `javac` takes seconds.
- **Read the generated output before reasoning about `.mop` semantics.** A failing
  `condition(...)` returns before the event body.
- **Event bindings are not specification parameters.** A `.mop`'s indexing parameters come
  from its header; binding a type in an event adds an advice local, not a per-object monitor.
- **Price the alphabet before designing it.** `n × (2ⁿ − 1)` coenable sets, ceiling 17.
- **The user pushes back on framing more cautious — or more defeated — than the evidence
  supports**, and has been right every time. When putting a choice to the user, show the rule
  text and the measurement, not a summary of them.
- **The user asked for less orchestration, not more.** The groups are linear on purpose. Do
  not fan them out into subagents or workflows.
