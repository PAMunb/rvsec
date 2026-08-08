# Session handoff — continue gh101, JCA specification conformance (session 9)

> Paste this whole file as the first message of the new session.
> **Objective of this session: Group 7.** Everything before it is closed.

---

## 0. Who you are and where you are

You are Claude Code in the RVSEC / RV-Android research codebase (PhD work of Pedro Costa,
`phtcosta@gmail.com`). Primary working directory:

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

Git branch **`modules`**. Tip when this file was written: **`233df18a`** — session 7's commit.
**Session 8's work is NOT committed.** Unlike the last handoff, you inherit a dirty gh101 tree;
§5 lists exactly what is yours. Run `git status` before assuming anything about it: the user
may have committed in between, and if `git log --oneline -1` is no longer `233df18a`, read that
commit before touching anything.

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
budget, the conformance verdicts, and Group 7's guard — is machinery in service of it. When a
decision is genuinely open, the tie-breaker is: *which option makes the specification say what
the rule says?* And when the mechanism cannot say what the rule says, the answer is never to
quietly say something else — it is to record the gap.

Three habits follow from it and all three are load-bearing:

- **Go to the oracle, not to the translation.** The `.mop` is a secondary source and has
  been wrong before. Read the `.cryptsl`.
- **An `_` in a rule is an anonymous argument, and it licenses a wildcard.**
- **A predicate is only addable when both ends of its edge are modelled by a `.mop` in this
  set** (D-S14). A reader without a writer is worse than an open gap: reads live in event
  bodies, so an unsatisfiable requirement reports on *every conforming call*.

Group 7 is the mechanised form of that third habit: it turns "recorded, not approximated"
from a promise into a check that fails.

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

**Group 7 touches no `.mop`.** It writes one Python guard and one data file, and it reads the
specifications. You will probably not need the skill this session — but read it before any
`.mop` edit if the work drifts there.

---

## 3. What the change is, and where it stands

Implement `openspec/changes/gh101-jca-spec-conformance/` — GitHub issue
[#101](https://github.com/PAMunb/rvsec/issues/101).

**68 of 84 tasks complete.** `openspec validate` passes. Groups 1, 2, 3, 3b, 4, 4b, 5 and **6**
are **closed**. Remaining: **Groups 7, 8, 9** — 16 tasks.

The task count grew from 83 to 84 in session 8: task 6.4 was added for the specification
enumerations the original plan had not seen (§6).

The task checkboxes are accurate as of the end of session 8. Do not assume that of any future
state without re-checking.

**No decision is owed by the user.** Group 7 is unblocked and is this session's objective.

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
   *content*, or adding a delta spec, belongs inside `openspec-update-change`.
   `data/gh101/*` is versioned data, **not** an OpenSpec artefact — edit it directly.
2. **The `jca` set is FROZEN** at commit `7e7acb69` (D-S0). Not one byte of `$MOP/jca`, not
   one byte of `$CORE/jca/util/CipherTransformationUtil.java`. Every correction to a
   **specification** lands in `jca_android` alone. D-S10 bounds what the freeze covers.
3. **Do NOT repair `rv-monitor`.** Recorded decision D-S12, taken by the user.
4. **Do NOT touch the MetaCrySL tree** (`$WS/MetaCrySL`). It belongs to another session.
   `$WS/MetaCrySL/generated/api30/` (33 `.cryptsl`) is **read-only input**. Same for the
   CrySL 1.5.2 corpus (47 `.crysl`) at
   `$WS/CryptoAnalysis/CryptoAnalysis/src/main/resources/JavaCryptographicArchitecture/`.
5. **NEVER start, stop or manage Android emulators.** No exceptions. Permanent.
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
    directory.**
12. **Commits**: `refs #101` during work, `closes #101` only in the final one. **Commit only
    when the user asks.** The user does ask, often, right after something is finished. Stage
    only gh101 paths — the working tree holds ~546 other changed files belonging to other
    sessions, and `git add -A` would sweep them in. The path list in §10 is **longer than the
    one session 8 inherited**, because Group 6 touched documentation outside `rv-experiment`.
13. **A campaign shares this machine.** Generating monitors is fine under `nice -n 15`. Watch
    `free -g`. Never run `mvn install` without checking `pgrep -af mvn` first.
    `mvn -o -pl rvsec/rvsec-core test` is scoped and safe.
14. **Do not `pkill -f logicrepository.Main`** while your own shell command line contains
    that string — session 4 killed its own wrapper that way. The same trap makes
    `pgrep -af mvn` match your own wrapper; read the output before concluding a build is
    running.
15. **`sleep N` in the foreground is blocked by the harness.** Use `run_in_background: true`
    and wait for the notification, or an `until … done` loop.
16. **CI contract for pytest**: always `--import-mode=importlib -o "addopts="`. Without them
    conftest isolation breaks across modules and collection fails.
17. **The formatter is `black`, not `ruff`.** `ruff` is not installed; `uv run ruff` fails to
    spawn. Use `.venv/bin/black` and `.venv/bin/flake8` (line length 88, from
    `pyproject.toml`). `__main__.py` already carries ~20 pre-existing `E501`s — flake8 is not
    a gate in this repo, `black` effectively is.

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

**Uncommitted and yours** — all of session 8 (Group 6 plus the artefact repairs):

```
M  rv-android/CLAUDE.md
M  rv-android/README.md
M  rv-android/docker/README.md
M  rv-android/docs/PRD.md
M  rv-android/modules/rv-experiment/CLAUDE.md
M  rv-android/modules/rv-experiment/README.md
M  rv-android/modules/rv-experiment/src/rv_experiment/__main__.py
M  rv-android/modules/rv-experiment/src/rv_experiment/config.py
M  rv-android/modules/rv-experiment/src/rv_experiment/constants.py
M  rv-android/modules/rv-experiment/src/rv_experiment/experiment/workflow/pre_processor.py
M  rv-android/modules/rv-experiment/tests/test_config_jit.py
M  rv-android/modules/rv-experiment/tests/test_config_validation.py
M  rv-android/modules/rv-monitor-generator/README.md
M  rv-android/openspec/changes/gh101-jca-spec-conformance/{proposal,design,tasks}.md
M  rv-android/openspec/changes/gh101-jca-spec-conformance/specs/instrumentation/spec.md
?? rv-android/openspec/changes/gh101-jca-spec-conformance/specs/experiment/spec.md
```

**Uncommitted and NOT yours: ~546 files.** They belong to other sessions (gh100,
`rvsec-instrumentation-dexlib2`, experiment directories, `docs/architecture/*`,
`modules/rvagent-tool/*`). Leave them alone and never stage by wildcard. In particular
`docs/architecture/subsystem-rv-experiment.md` is modified by someone else — it does **not**
enumerate specification sets (checked), so Group 6 did not make it stale and you have no
reason to touch it.

Checks at the moment of handoff, **all run in session 8, all green**:

| check | result |
|---|---|
| Freeze, INV-INS-109 a | **empty diff** |
| Divergence record, INV-INS-109 b | **106 hunks, all recorded** |
| `tests/parity/test_gh101_specset_gates.py` | **4 passed** |
| `openspec validate … --type change` | **valid** |
| Whole `rv-experiment` suite | **252 passed** |
| `black --check` over the touched Python | clean |
| CLI advertises the value | `--specification-set [jca\|jca_android\|generic\|custom]` |

Not re-run in session 8 (unchanged since session 7, and Group 6 touches no specification):
whole-set generation (27.8 s / 1.83 GB, INV-INS-110 clean), `javac` over the generated
monitor (57 classes), `mvn -o -pl rvsec/rvsec-core test` (30 tests), frozen-set monitor
byte-identity.

---

## 6. What session 8 did

**Closed Group 6, and repaired the artefacts it revealed.**

### Group 6 — the derived set is selectable by name (D-S8)

Six sites carry the enumeration of accepted values, not the two the previous handoff named.
Three are code:

| file | site |
|---|---|
| `modules/rv-experiment/src/rv_experiment/constants.py` | `SPEC_SET_JCA_ANDROID = "jca_android"`, added to the family |
| `…/config.py` | `valid_spec_sets`, now built from the constants; the JIT `if/elif` chain, with the `jca_android` branch; four prose sites (field comment, `validate()` docstring citing INV-EXP-03 (f), the mapping comment, the method docstring) |
| `…/__main__.py` | **`click.Choice`** on `--specification-set`, plus two docstrings |

**The `click.Choice` was the substantive find.** It is the gate Click applies *before* any
config object exists, so without it `--specification-set jca_android` is refused however
correct `config.py` is, and D-S8 does not hold. The previous handoff said "all three tasks
live in one file, `config.py`" — it was a floor, not a ceiling.

`pre_processor.py`'s pipeline comment also enumerated the directories and was corrected.

Tests (`test_config_jit.py`, `test_config_validation.py`), all three of them worth their
lines:

- `test_jca_android_spec_set_resolves_paths` — resolves to `…/resources/jca_android` with
  `custom_specs_dir is None`.
- `test_jca_android_spec_set_valid` and `test_near_miss_spec_set_still_rejected` — `validate()`
  runs under `ErrorHandler.handle_errors`, which **logs and absorbs** the `ValueError`
  (`error_handler.py:439-446`, `reraise=False` by default). Every pre-existing test in that
  class is therefore tautological — it asserts the field it just set. The new ones call
  `ExperimentConfig.validate.__wrapped__(config)`, the undecorated function `functools.wraps`
  exposes, so acceptance and rejection are actually asserted.
- `test_jca_spec_set_resolves_paths` was **tightened**: it asserted `"jca" in mop_specs_dir`,
  which `"jca_android"` also satisfies. It now matches the path tail.

Documentation updated (task 6.3): `CLAUDE.md` (said "two distinct specification sets"),
`docs/PRD.md` FR03, `README.md` (3 sites), `docker/README.md`,
`modules/rv-experiment/{CLAUDE.md,README.md}`, `modules/rv-monitor-generator/README.md`.
`.claude/project-info.md` does **not** enumerate — it carries one example path — so it was
correctly left alone. The `rv-experiment-compare` skill passes `--spec-set` through with no
closed list, so it already accepts the new value.

### The artefact repair (new task 6.4)

Three further enumerations live in the **main specs**, and the change's delta covered none of
them, so `openspec-sync-specs` would have left the specifications naming three values while
the code names four — with `config.py`'s validation docstring citing INV-EXP-03 by clause
letter, i.e. a literal contradiction. Fixed through `openspec-update-change`:

- **`specs/instrumentation/spec.md`** — INV-INS-09 restated at the top of the invariants,
  marked as replacing the entry of the same number.
- **`specs/experiment/spec.md`** — a **new capability delta**, the change's second. It carries
  the corrected `specification_set` input contract, INV-EXP-03 restated (with the explicit
  statement that clause (f) stays a *closed* enumeration — widening it must not make it
  accept-anything), and `Just-in-Time Sub-Module Configuration (FR17, NFR05)` as a MODIFIED
  requirement, because its mapping paragraph enumerated three directories. It adds the
  scenario *JIT Configuration for Monitor Generation With the Derived Android Specs* and an
  `AND` on the `jca` scenario requiring the directory to match exactly rather than by prefix.
- **`proposal.md`** — `experiment` added to *Modified Capabilities* with the reason.
- **`design.md`** — D-S8 gained the six-site enumeration and the substring hazard.
- **`tasks.md`** — 6.1 and 6.2 given the sites they were missing, new task 6.4, and the
  header execution note corrected (it said Group 6 touches `config.py`).

The `experiment` delta was created despite `openspec-update-change` normally deferring new
files under a glob artefact to `/opsx:continue`, because the user asked for it explicitly.
No other active change has an `experiment` delta, so it does not collide with gh100.

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
clause-by-clause comparison, anchored to **CrySL 1.5.2** on purpose. D-S14 settles what that
anchor does and does not decide.

---

## 8. THIS SESSION'S OBJECTIVE — Group 7

**Seven tasks.** The guard that makes INV-INS-111 mechanical, the list it reads, and five
records. Run the work through `openspec-apply-change` (rule 1). Tick each checkbox as it lands.

### The list, verified against the material rather than quoted

The pairing snippet in §10, run at the end of session 8, reports **11 constants written and
never read** and **0 read and never written**:

```
DIGESTED, GENERATED_KEY_PAIR, GENERATED_MAC, GENERATED_TRUST_MANAGER, GENERATE_SSL_CONTEXT,
GENERATE_SSL_ENGINE, PREPARED_PBE, SIGNED, SPECCED_KEY, VERIFIED, WRAPPED_KEY
```

Reproduce it with the snippet rather than trusting this paragraph — it is regenerated from
`data/gh101/predicate_inventory_jca_android.csv`, and task 7.4 regenerates that file.
Every one of the eleven needs an entry in the deliberate-omission list (7.2) or the guard
(7.1) fails.

### 7.1 — the guard

`scripts/gh101_predicate_pairing_check.py` (name yours to pick; the four existing scripts are
`gh101_{conformance_check,divergence_record,monitor_transition_check,predicate_inventory,
predicate_edges}.py` — follow their CLI shape, they all take `-o`/paths and exit non-zero on
failure). It reads the committed inventory **and the specifications**, recomputes the pairing
rather than trusting the CSV, and fails on any constant written and neither read nor listed.
D-S5, INV-INS-111.

**Design point session 8 flagged and did not decide:** the omission list must be
*machine-readable* for 7.1 to read it, while what exists today is prose in
`data/gh101/README.md` — sections *"The deliberate omissions, and why one of them is now
closed (tasks 4.3, 5.1)"* (line 233) and *"The eight predicates Group 5 does not add (task
5.1d)"* (line 332). Task 5.4 also requires that the eight predicates of 5.1d "appear in the
omission list", and those are **not** `Property` constants — they were never added — so the
file needs a `kind` column distinguishing *constant written, never read* from *predicate with
no constant*. A CSV beside the inventory, with the prose staying in `README.md` as the
narrative, is the shape that satisfies both 7.2 and 5.4. Confirm it against the two README
sections before writing, and do not let the CSV and the prose drift.

### 7.3 — the guard must be able to fail

Run it against the derived set (must pass) **and** against a scratch copy with a constant
deliberately mistyped (must fail). Copy to the scratchpad; never mutate `$MOP` to test a
check.

### 7.4 — regenerate both inventories

`jca_android` diffed against the Group 1 baseline, where **every** difference must correspond
to a task in this change; `jca` identical to its baseline **byte for byte**. The `jca` one is
the freeze's second witness and a diff there is a defect, not a finding.

### 7.5 to 7.7 — the three records

They go in `data/gh101/` (`README.md` or `frozen_set_debt.md`, matching where their siblings
live), not in an OpenSpec artefact:
- 7.5: the published numbers reproduce exactly because `jca` was frozen, and the debt that
  buys is a set that stays reproducible without being correct (D-S0).
- 7.6: cross-set violation comparisons now confound the platform allow-list with the layer-2
  repairs, and no post-hoc measurement separates them.
- 7.7: the derived Android profile models **availability, not recommendation** —
  `MessageDigest` admits `MD5` and `SHA-1` — so a fall in the violation count across the sets
  is not evidence of better analysed code.

**Verification for this group**: the guard itself, plus the two end-of-group checks that run
after *every* group (INV-INS-109 a and b), plus the four gates.

---

## 9. Remaining work, in order

1. **Group 7** — this session's objective, §8.
2. **Group 8** — **unblocked**: issue #100's task 5.3 landed (commit `48b57fc5`). Empirical
   verification that the corrected `TrustManagerFactorySpec` and `SSLContextSpec` report as
   intended under the derived set, and that the `SSLContextSpec` label stops depending on a
   variable that is never written. If something turns out still to be blocked, record it as
   blocked citing the artefact — **do not substitute a weaker check** (D-S6).
3. **Group 9** — verification, including the full reactor build (9.1), for which you must
   coordinate: check `pgrep -af mvn` and the peer sessions first. Note 9.7 (`/rv-docs-sync`
   for docs Group 6 made stale) is largely absorbed by task 6.3 — re-run the grep in §10
   before concluding there is nothing left.

Then: tick issue #101's acceptance criteria one by one **before** closing, any criterion not
literally met getting an inline note (`- [x] ~~criterion~~ — superseded by …`), never a silent
tick and never a blank box. Sync the delta specs explicitly with `openspec-sync-specs`
**before** archiving — it now has **two** capabilities to sync, `instrumentation` and
`experiment`; the skill enumerates them from the CLI, so it picks both up on its own, but
check that it did. Then `openspec archive gh101-jca-spec-conformance --skip-specs`. Final
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

# ---- Group 7: the write/read pairing, both directions ----
python3 -c "
import csv, collections
rows=list(csv.DictReader(open('data/gh101/predicate_inventory_jca_android.csv')))
W=collections.defaultdict(set); R=collections.defaultdict(set)
for r in rows:
    (W if r['kind']=='WRITE' else R)[r['property']].add(r['spec']) if r['kind'] in ('WRITE','READ') else None
for p in sorted(set(W)|set(R)):
    w,rd=len(W.get(p,())),len(R.get(p,()))
    print(f'{p:30}{w:>3}{rd:>3}', 'WRITE-ONLY' if w and not rd else ('READ-ONLY' if rd and not w else 'ok'))"

# the prose the omission list has to agree with
sed -n '233,340p' data/gh101/README.md      # deliberate omissions (4.3, 5.1) + the eight of 5.1d

# regenerate the records (task 7.4)
uv run python scripts/gh101_predicate_inventory.py $MOP/jca_android -o data/gh101/predicate_inventory_jca_android.csv
uv run python scripts/gh101_predicate_inventory.py $MOP/jca          -o $S/inventory_jca_now.csv
diff $S/inventory_jca_now.csv data/gh101/predicate_inventory_jca.csv && echo "  frozen inventory identical"
uv run python scripts/gh101_predicate_edges.py --inventory data/gh101/predicate_inventory_jca_android.csv \
    --edges data/gh101/predicate_edges.csv --counts data/gh101/edge_counts_per_file.csv
uv run python scripts/gh101_conformance_check.py -o data/gh101/conformance_record.csv

# INV-INS-109 (a) — the freeze. MUST be empty, at the end of every group.
git -C $RVSEC_HOME diff 7e7acb69 -- \
  rvsec/rvsec-mop/src/main/resources/jca \
  rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/CipherTransformationUtil.java

# INV-INS-109 (b) — every hunk of the set diff needs an entry
uv run python scripts/gh101_divergence_record.py --check
uv run python scripts/gh101_divergence_record.py --refresh > $S/div.csv   # skeleton rows

# the four gates together
uv run pytest tests/parity/test_gh101_specset_gates.py --import-mode=importlib -o "addopts=" -q

# Python quality (rule 17 — ruff is NOT installed)
uv run pytest modules/rv-experiment/tests --import-mode=importlib -o "addopts=" -q
.venv/bin/black --check --diff <files>
.venv/bin/flake8 <files> --max-line-length 88

# task 9.7 — anything left enumerating the accepted values?
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
# NOTE: rebuild rvsec-core first when you add a Property constant, or this fails on it.

# Java side — one module, no install, safe beside the other session
pgrep -af mvn; cd $RVSEC_HOME && nice -n 15 mvn -o -pl rvsec/rvsec-core test

# COMMIT — stage only these paths; the tree holds ~546 files that are not yours.
# This list is LONGER than session 8's: Group 6 touched docs outside rv-experiment.
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
  rv-android/docs/20260808_handoff_gh101_sessao9.md
git diff --cached --name-only    # READ IT before committing
```

---

## 11. Coordination with the parallel gh100 session — nothing owed

| concern | status |
|---|---|
| descriptor drift | **moot.** Their tasks ran over monitor bytes pinned on 2026-08-06, before any gh101 edit |
| your dependency on them | **satisfied.** Their task 5.3 is `[x]` (`48b57fc5`); your Group 8 is unblocked |
| file overlap | none — you own `$MOP/jca_android`, `rvsec-core`, `rv-experiment` and (from session 8) the root docs; they own `rvsec-instrumentation-dexlib2/*` and two other Python modules |
| Maven | shared reactor and `~/.m2`. Check `pgrep -af mvn` before any build |
| spec sync | you MODIFY *Specification Set Support (FR03)* and *Just-in-Time Sub-Module Configuration (FR17)*, and restate INV-INS-09 and INV-EXP-03; they MODIFY a different requirement of `instrumentation`. Before syncing, `grep -ln "<Requirement title>" openspec/changes/*/specs/*/spec.md` |
| invariants | INV-INS-109 to 115 are yours, plus the restatements of INV-INS-09 and INV-EXP-03; 104 to 108 are theirs |
| git | same branch and repository, `refs #101`, stage only your paths, no rebase, no force-push, no reorder |

---

## 12. Decisions already settled — do not re-open

- **D-S0**: `jca` frozen, corrections to *specifications* in the derived set alone. Bounded by
  D-S10: the freeze covers what the instrument states, not the runtime it runs on.
- **D-S3 as revised**: the derived Cipher tables live in
  `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil`, a sibling class.
- **D-S5**: the write/read pairing is a guard, not a convention — **this is Group 7**.
- **D-S7**: freeze check plus divergence record replace the parity check.
- **D-S8**: `jca_android` is a first-class `specification_set` value. **Done, Group 6.**
- **D-S9**: repair all eighteen all-`fail` events; uniform repair form; the 70.4% is a
  **ceiling**, not a cause. Corollary that keeps mattering: **a read goes in the event body,
  never in `condition(...)`** — a failing guard takes no transition, so the misuse resurfaces
  as a sequence violation one call later instead of as the unsatisfied requirement it is.
- **D-S10**: the predicate store is keyed by identity, in the shared class; shared code MUST
  NOT branch on the active specification set.
- **D-S11 as revised**: one event per **distinct binding profile**, not one per rule
  signature. `CipherSpec` budgeted to 14.
- **D-S12**: `rv-monitor` is **not** repaired. The ceiling (17 events) is a design constraint
  (INV-INS-115). The user decided this explicitly.
- **D-S13**: `!macced[_, plainText]` is **transcribed**, not recorded as inexpressible.
- **D-S14**: **Group 5 adds `generatedCipher` alone.** A predicate is addable only when its
  producing rule *and* its consuming rules are all modelled by a `.mop` in this set; six of
  the bucket's nine lack a producer here and two lack a consumer anywhere. The eight are
  recorded, not approximated. `generatedMessageDigest` stays omitted under the same criterion.
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
  **frozen `jca`** set. Three angles, one answer. A one-line grep would have given the wrong one.
- **A handoff's list of sites is a floor, never a ceiling.** Session 8's handoff said Group 6
  lived in one file; the gate that decided whether the feature worked at all was a
  `click.Choice` in another. Grep for the *value*, not for the file you were pointed at.
- **`"jca_android"` contains `"jca"`.** Any assertion, guard or grep written as a substring
  match over a path or a set name passes on the derived set as readily as on the frozen one —
  and telling the two apart is the entire point of the value. Match tails and whole tokens.
- **A decorator can make a test assert nothing.** `ErrorHandler.handle_errors` defaults to
  `reraise=False`, so `validate()` logs its `ValueError` and returns. Tests that "check
  validation" by constructing an invalid config and asserting the field are tautologies.
  `functools.wraps` exposes `__wrapped__`; call that when the assertion is about the check.
- **An enumeration in a spec does not degrade gracefully.** It states, closed, that the new
  value does not exist. Grep the *main* specs, not only the delta: an invariant the delta
  never restates survives `openspec-sync-specs` untouched, and INV-INS-09 and INV-EXP-03 both
  enumerate the specification sets while living outside the requirement the delta modifies.
- **Verify enumerations in artefacts against the material.** They are floors, not ceilings.
  Session 7 found `design.md` claiming three edges where the CSV said two; the write-only
  constant count is **eleven**, not the one an earlier handoff named.
- **Two tools that both "diff" do not agree on hunk boundaries.** `diff -U0` and Python's
  `difflib.unified_diff` group adjacent changes differently, and the divergence record is
  keyed by a hash of a hunk's changed lines. Reason about that record with the script's own
  `hunks()` function, never with the shell `diff`.
- **The divergence record's hunk digest is not unique across files.** `24de88ca2fff`
  (`i1 -> final`) occurs in both `KeyManagerFactorySpec.mop` and `TrustManagerFactorySpec.mop`.
  **Key by `(file, hunk)`.**
- **Compile the generated monitor.** Generation succeeding proves the `.mop` parses and the
  automaton builds; it does not prove the event bodies compile. `javac` takes seconds.
- **Read the generated output before reasoning about `.mop` semantics.** A failing
  `condition(...)` returns before the event body — which is what makes "write the predicate
  inside the guard" mean what it should.
- **Event bindings are not specification parameters.** A `.mop`'s indexing parameters come
  from its header; binding a type in an event adds an advice local, not a per-object monitor.
- **Price the alphabet before designing it.** `n × (2ⁿ − 1)` coenable sets, ceiling 17.
- **The user pushes back on framing more cautious — or more defeated — than the evidence
  supports**, and has been right every time. When putting a choice to the user, show the rule
  text and the measurement, not a summary of them.
- **The user asked for less orchestration, not more.** The groups are linear on purpose. Do
  not fan them out into subagents or workflows.
