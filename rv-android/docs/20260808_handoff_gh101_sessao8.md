# Session handoff — continue gh101, JCA specification conformance (session 8)

> Paste this whole file as the first message of the new session.
> **Objective of this session: Group 6.** Everything before it is closed.

---

## 0. Who you are and where you are

You are Claude Code in the RVSEC / RV-Android research codebase (PhD work of Pedro Costa,
`phtcosta@gmail.com`). Primary working directory:

```
/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android
```

Git branch **`modules`**. Tip when this file was written: **`233df18a`** — session 7's commit,
which is the **first** gh101 commit and carries every artefact sessions 3 to 7 produced. Unlike
every previous handoff, you inherit a clean gh101 tree: nothing of this change is uncommitted.

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

Writing `$WS/rvsec/rvsec-mop/...` gets you "File does not exist". Session 7 tripped on this
once. Use `$MOP` from §10.

---

## 1. The north star, in one sentence

**The derived `jca_android` set should be as close to the CrySL rules as the mechanism
allows, and every place where it is not should be written down with the reason.**

That is the whole change. Everything else — the freeze, the divergence record, the alphabet
budget, the conformance verdicts — is machinery in service of it. When a decision is
genuinely open, the tie-breaker is: *which option makes the specification say what the rule
says?* And when the mechanism cannot say what the rule says, the answer is never to quietly
say something else — it is to record the gap.

Two habits follow from it and both are load-bearing:

- **Go to the oracle, not to the translation.** The `.mop` is a secondary source and has
  been wrong before. Read the `.cryptsl`.
- **An `_` in a rule is an anonymous argument, and it licenses a wildcard.**

Session 7 added a third, and it is now a recorded decision (D-S14):

- **A predicate is only addable when both ends of its edge are modelled by a `.mop` in this
  set.** A reader without a writer is worse than an open gap: reads live in event bodies, so
  an unsatisfiable requirement reports on *every conforming call*.

---

## 2. Read this first: the skill has the method

`.claude/skills/rv-analyze-spec/` exists so no session re-derives what took an afternoon to
learn. Load it with the `Skill` tool before touching a `.mop`, and read at least:

- `reference/triangulation.md` — the method. Twelve angles for checking a claim. Short, and
  the part that matters most.
- `reference/generator-pipeline.md` — the generator, the ceiling, every reproducible number.
- `reference/pointcut-semantics.md` — what the weaver actually matches.
- `reference/crysl-to-mop.md` — the alphabet-budget method and the worked `Cipher` example.
- `scripts/README.md` — the two harnesses (`CoenableProbe`, `PointcutBudget`) and how to run
  them. Both drive **production classes**, not re-implementations.

**Group 6 touches no `.mop`.** You will probably not need the skill this session — but read
it before any `.mop` edit if the work drifts there.

---

## 3. What the change is, and where it stands

Implement `openspec/changes/gh101-jca-spec-conformance/` — GitHub issue
[#101](https://github.com/PAMunb/rvsec/issues/101).

**64 of 83 tasks complete.** `openspec validate` passes. Groups 1, 2, 3, 3b, 4, 4b and **5**
are **closed**. Remaining: **Groups 6, 7, 8, 9** — 19 tasks.

The task checkboxes are accurate as of `233df18a`. Do not assume that of any future state
without re-checking.

**No decision is owed by the user.** Session 7 resolved the one that was open (§12, D-S14).
Group 6 is unblocked and is this session's objective.

---

## 4. Non-negotiable working rules

Read `CLAUDE.md` at the repo root and at `$WS/rvsec/CLAUDE.md` first, then `docs/WORKFLOW.md`.

1. **Follow the OpenSpec workflow rigorously.** Anything under `openspec/changes/gh101-*/`
   goes through the **skills** invoked with the `Skill` tool: `openspec-apply-change`,
   `openspec-update-change`, `openspec-verify-change`, `openspec-sync-specs`,
   `openspec-archive-change`. **Never** hand-write or hand-edit an OpenSpec artefact outside
   a skill that told you to. Python, Java and `.mop` edits are normal work — the rule is
   about the artefacts. **Ticking a checkbox in `tasks.md` counts as an artefact edit** and
   belongs inside `openspec-apply-change`. Revising `design.md` or `tasks.md` *content*
   belongs inside `openspec-update-change`.
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
7. **Language**: code, comments, commit messages, issues and OpenSpec artefacts in
   **English**; prose to the user in **Brazilian Portuguese with correct accentuation**.
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
    only gh101 paths — the working tree has ~546 other changed files belonging to other
    sessions, and `git add -A` would sweep them in. The exact path list is in §10.
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

---

## 5. Exact state you inherit

**Committed**, in `233df18a`, and this is the whole of gh101 so far:

```
rv-android/data/gh101/{README.md, divergence_record.csv, predicate_inventory_jca_android.csv}
rv-android/docs/20260807_handoff_gh101_sessao7.md
rv-android/openspec/changes/gh101-jca-spec-conformance/{proposal,design,tasks}.md
rv-android/openspec/changes/gh101-jca-spec-conformance/specs/instrumentation/spec.md
rvsec/rvsec-core/src/main/java/br/unb/cic/mop/{ExecutionContext,Property}.java
rvsec/rvsec-core/src/main/java/br/unb/cic/mop/jca/util/AndroidCipherTransformationUtil.java
rvsec/rvsec-core/src/test/java/br/unb/cic/mop/{ExecutionContextTest,...}.java
rvsec/rvsec-mop/src/main/resources/jca_android/*.mop   (13 files)
```

Uncommitted in the tree: **~546 files that are not yours.** They belong to other sessions
(gh100, `rvsec-instrumentation-dexlib2`, experiment directories, docs). Leave them alone and
never stage by wildcard.

Checks at the moment of handoff, **all run in session 7, all green**:

| check | result |
|---|---|
| Freeze, INV-INS-109 a | **empty diff** |
| Divergence record, INV-INS-109 b | **106 hunks, all recorded** |
| `tests/parity/test_gh101_specset_gates.py` | **4 passed** |
| `openspec validate … --type change` | **valid** |
| `mvn -o -pl rvsec/rvsec-core test` | **30 tests**, 0 failures |
| Whole derived set generates | **27.8 s / 1.83 GB**; INV-INS-110 clean |
| Generated monitor compiles (`javac`) | **57 classes, 0 errors** |
| Frozen-set monitor vs. base commit | **byte-identical** (`7eb7ebcd04bb5ccdb634e28925469579`) |
| Inventory pairing | **no constant read without a writer** |

---

## 6. What session 7 did

**Resolved the open anchor decision, and closed Group 5.**

### The decision, and why it turned out not to be about the anchor

Session 6 left an open question: Group 5 planned nine `Property` constants, and two of them
(`generatedCipher`, `preparedOAEP`) are named by **no** API 30 rule while CrySL 1.5.2 names
both. The question was framed as "which anchor".

Checking the material reframed it. The decisive axis is not the anchor but whether **both
ends of the edge are modelled by a `.mop` in this set of 23**:

| predicate | edges | producer rule modelled? | consumer rule modelled? | verdict |
|---|---:|---|---|---|
| `generatedCipher` | 2 | yes (`Cipher`) | yes (both streams) | **added** |
| `preparedAlg` | 1 | no (`AlgorithmParameters`) | yes | no producer |
| `preparedRSA` | 1 | no | yes | no producer |
| `preparedDSA` | 1 | no | yes | no producer |
| `preparedEC` | 1 | no | yes | no producer |
| `preparedOAEP` | 1 | no | yes | no producer |
| `generatedManagerFactoryParameters` | 2 | no (neither) | yes | no producer |
| `cipheredInputStream` | 1 | yes | **no rule requires it, in either anchor** | no consumer |
| `cipheredOutputStream` | 1 | yes | same | no consumer |

`preparedOAEP` is excluded for want of a producer *whichever* anchor is chosen, so the anchor
decides only `generatedCipher`. The user chose: **Group 5 adds `generatedCipher` alone**, and
the other eight are recorded. That is **D-S14**.

### The implementation

- `Property.GENERATED_CIPHER` added, with a javadoc saying why the mark is written at the
  init events.
- `CipherSpec.mop` writes it in all three `init` bodies, **inside the `condition(...)`**, so
  a cipher initialised with an unvalidated key goes unmarked — the rule's own coupling of its
  `ENSURES` to its `REQUIRES`. Verified in the generated monitor (`return false` precedes the
  body).
- `CipherInputStreamSpec.mop` and `CipherOutputStreamSpec.mop`: constructor events gained
  `args(is, ciph)` / `args(os, ciph)` and a body read. **No new events** — both alphabets
  stay at 4 and 5, far under the ceiling of 17.

**Placement was the substantive call, not a detail.** `@match1` fires only at the accepting
state, which needs a `doFinal`. A cipher handed to a `CipherInputStream` has been initialised
and encrypted nothing — the stream makes those calls itself. Marking at the accepting state
would have left *every legitimate stream construction* unsatisfied. The rule says `after
Inits` and that is where it went.

**Closing it reopened task 4.3's deliberate omission, and had to.** The `ENSURES
generatedCipher[this]` was recorded as omitted because `CipherSpec` substituted
`setObjectAsInAcceptingState(cipher)`. That substitute is inert — verified at source, not
from the record: `ExecutionContext.java:153-160` shows `hasEnsuredPredicate` scanning only
`context.values()`, never `acceptingState`, and `isInAcceptingState` has no caller outside
test helpers. Reading against it would have reproduced the same false positive.
`generatedMessageDigest` **stays** omitted under the identical criterion — its consumers are
the `DigestInputStream`/`DigestOutputStream` rules and neither has a `.mop` here.

The accepting-state marker was **left in place**. It is the set-wide convention (nineteen
writes); removing it from `CipherSpec` alone would make that file the exception without
changing behaviour.

### Artefacts revised (through `openspec-update-change`)

`design.md` (new D-S14, `Property` section 10 → 2 constants, two risk lines), `proposal.md`
(edge counts), `tasks.md` (Group 5 rewritten, new task 5.1d), and
`specs/instrumentation/spec.md` — which gained a paragraph and a scenario for the **converse**
of INV-INS-111: *Required predicate has no producer in the set*. The delta had a scenario for
a constant written and never read, and none for the more damaging opposite.

### Records (task 5.1d, in `data/gh101/README.md`)

New section "The eight predicates Group 5 does not add", with the producer/consumer table,
the reproducing commands, why "no producer" forbids the reader rather than merely weakening
it, and what would close the six (seven further specifications — a change of its own). The
deliberate-omissions section was retitled and now records one closed, one standing.

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

## 8. THIS SESSION'S OBJECTIVE — Group 6

**Three tasks. The derived set becomes selectable by name** (D-S8). Today `jca_android` can
only be reached through `specification_set = "custom"` plus a `custom_specs_dir` path, which
is the hazard D-S8 exists to remove: a mistyped or stale path silently selects the
**uncorrected** instrument while the experiment reports as though it ran the corrected one.

All three tasks live in one file, `modules/rv-experiment/src/rv_experiment/config.py`:

- **6.1** Add `"jca_android"` to `valid_spec_sets` (**`config.py:424`**, currently
  `["jca", "generic", "custom"]`) and to the directory mapping in
  `get_monitored_operations_config()` (**`config.py:625`**, the branch chain at
  **`:671-692`**), resolving to `{mop_base_dir}/jca_android/`.
  Note `config.py:377` and `:420` carry prose naming the accepted values (INV-EXP-03 (f)) —
  they must be updated with the list, or the docstring contradicts the code.
- **6.2** Test that `specification_set = "jca_android"` resolves to the derived directory and
  does **not** require `custom_specs_dir`. Existing tests to extend rather than duplicate:
  `modules/rv-experiment/tests/test_config_validation.py` and
  `modules/rv-experiment/tests/test_config_jit.py`; `tests/helpers.py` has the fixtures.
- **6.3** Check which documentation enumerates the accepted values and update what does.
  Confirmed to mention them: **`CLAUDE.md`** and **`docs/PRD.md`**. `.claude/project-info.md`
  did **not** match the grep — verify before editing it.

Run the work through `openspec-apply-change` (rule 1). Tick each checkbox as it lands.

**Verification for this group**: the CI-contract pytest invocation (rule 16) over
`rv-experiment`, plus the two end-of-group checks that run after *every* group (INV-INS-109 a
and b) even though Group 6 touches no specification — they are cheap and they catch an
accidental edit.

---

## 9. Remaining work, in order

1. **Group 6** — this session's objective, §8.
2. **Group 7** — the write/read guard, the deliberate-omission list, and the five records.
   **Read this before planning it:** the handoff for session 7 said `SPECCED_KEY` was the
   constant written without a reader. The regenerated inventory shows **eleven**:
   `DIGESTED`, `GENERATED_KEY_PAIR`, `GENERATED_MAC`, `GENERATED_TRUST_MANAGER`,
   `GENERATE_SSL_CONTEXT`, `GENERATE_SSL_ENGINE`, `PREPARED_PBE`, `SIGNED`, `SPECCED_KEY`,
   `VERIFIED`, `WRAPPED_KEY`. Every one needs an entry in the deliberate-omission list (task
   7.2) or the guard (task 7.1, INV-INS-111) fails. Reproduce the list with the pairing
   snippet in §10 rather than trusting this paragraph.
3. **Group 8** — **unblocked**: issue #100's task 5.3 landed (commit `48b57fc5`).
4. **Group 9** — verification, including the full reactor build (9.1), for which you must
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

# ---- Group 6 ----
uv run pytest modules/rv-experiment/tests/test_config_validation.py \
              modules/rv-experiment/tests/test_config_jit.py \
              --import-mode=importlib -o "addopts=" -q
grep -n 'valid_spec_sets' modules/rv-experiment/src/rv_experiment/config.py   # :424
sed -n '660,695p'          modules/rv-experiment/src/rv_experiment/config.py   # the mapping
grep -rn 'jca_android\|specification_set' CLAUDE.md docs/PRD.md               # task 6.3

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

# the write/read pairing, both directions -- Group 7 depends on this list
python3 -c "
import csv, collections
rows=list(csv.DictReader(open('data/gh101/predicate_inventory_jca_android.csv')))
W=collections.defaultdict(set); R=collections.defaultdict(set)
for r in rows:
    (W if r['kind']=='WRITE' else R)[r['property']].add(r['spec']) if r['kind'] in ('WRITE','READ') else None
for p in sorted(set(W)|set(R)):
    w,rd=len(W.get(p,())),len(R.get(p,()))
    print(f'{p:30}{w:>3}{rd:>3}', 'WRITE-ONLY' if w and not rd else ('READ-ONLY' if rd and not w else 'ok'))"

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

# COMMIT — stage only these paths; the tree holds ~546 files that are not yours
cd $RVSEC_HOME && git add \
  rvsec/rvsec-core \
  rvsec/rvsec-mop/src/main/resources/jca_android \
  rv-android/data/gh101 \
  rv-android/openspec/changes/gh101-jca-spec-conformance \
  rv-android/modules/rv-experiment \
  rv-android/docs/20260808_handoff_gh101_sessao8.md
git diff --cached --name-only | grep -vE '^(rvsec/rvsec-core|rvsec/rvsec-mop/src/main/resources/jca_android|rv-android/(data/gh101|openspec/changes/gh101-|modules/rv-experiment|docs/20260808))' || echo "  clean"
```

---

## 11. Coordination with the parallel gh100 session — nothing owed

| concern | status |
|---|---|
| descriptor drift | **moot.** Their tasks ran over monitor bytes pinned on 2026-08-06, before any gh101 edit |
| your dependency on them | **satisfied.** Their task 5.3 is `[x]` (`48b57fc5`); your Group 8 is unblocked |
| file overlap | none — you own `$MOP/jca_android`, `rvsec-core` and (from Group 6) `rv-experiment`; they own `rvsec-instrumentation-dexlib2/*` and two other Python modules |
| Maven | shared reactor and `~/.m2`. Check `pgrep -af mvn` before any build |
| spec sync | you MODIFY *Specification Set Support (FR03)*; they MODIFY a different requirement, so order does not matter. Before syncing, `grep -ln "<Requirement title>" openspec/changes/*/specs/*/spec.md` |
| invariants | INV-INS-109 to 115 are yours, 104 to 108 theirs |
| git | same branch and repository, `refs #101`, stage only your paths, no rebase, no force-push, no reorder |

---

## 12. Decisions already settled — do not re-open

- **D-S0**: `jca` frozen, corrections to *specifications* in the derived set alone. Bounded by
  D-S10: the freeze covers what the instrument states, not the runtime it runs on.
- **D-S3 as revised**: the derived Cipher tables live in
  `br.unb.cic.mop.jca.util.AndroidCipherTransformationUtil`, a sibling class.
- **D-S7**: freeze check plus divergence record replace the parity check.
- **D-S8**: `jca_android` becomes a first-class `specification_set` value. **This is Group 6.**
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
- **D-S14 (session 7)**: **Group 5 adds `generatedCipher` alone.** A predicate is addable only
  when its producing rule *and* its consuming rules are all modelled by a `.mop` in this set;
  six of the bucket's nine lack a producer here and two lack a consumer anywhere. The eight
  are recorded, not approximated. This also converts task 4.3's `generatedCipher` omission
  into an implemented `ENSURES`, while `generatedMessageDigest` stays omitted under the same
  criterion. The user decided this explicitly after being shown the producer/consumer table.
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
  **frozen `jca`** set, so those tests cannot see a `jca_android` edit at all. Three angles,
  one answer. A one-line grep would have produced the wrong one.
- **Verify enumerations in artefacts against the material.** They are floors, not ceilings.
  Session 7 found `design.md` claiming `generatedCipher` carried three edges of the
  capability-absent bucket when the CSV says two — the third lives in the deliberate-omission
  bucket, which is exactly why closing it reopened task 4.3. And the write-only constant count
  is eleven, not the one the previous handoff named.
- **Two tools that both "diff" do not agree on hunk boundaries.** `diff -U0` and Python's
  `difflib.unified_diff` group adjacent changes differently, and the divergence record is keyed
  by a hash of a hunk's changed lines. Reason about that record with the script's own
  `hunks()` function, never with the shell `diff`.
- **The divergence record's hunk digest is not unique across files.** `24de88ca2fff`
  (`i1 -> final`) occurs in both `KeyManagerFactorySpec.mop` and `TrustManagerFactorySpec.mop`.
  Session 7 keyed an update script by digest alone and silently dropped a row; it was caught
  only because the check ran afterwards. **Key by `(file, hunk)`.** The dropped
  `KeyManagerFactorySpec` row was reconstructed by hand from the live hunk and its sibling and
  attributed to task 4.8 — it is the one row in that file whose prose was not written when the
  edit was made, and it is worth a glance.
- **Compile the generated monitor.** Generation succeeding proves the `.mop` parses and the
  automaton builds; it does not prove the event bodies compile. `javac` takes seconds and
  catches a missing constant, import or type error the reactor build would find an hour later.
- **Read the generated output before reasoning about `.mop` semantics.** Session 7 confirmed
  from `MultiSpec_1RuntimeMonitor.java` that a failing `condition(...)` returns before the
  event body, which is what makes "write the predicate inside the guard" mean what it should.
- **Event bindings are not specification parameters.** A `.mop`'s indexing parameters come from
  its header — `CipherInputStreamSpec()` is one of only two in the set with an empty list — so
  binding `Cipher ciph` in an event adds an advice local, not a per-cipher monitor. The
  precedent was already in the same file (`event r2 after(byte[] arr, int offset, int len)`).
- **Price the alphabet before designing it.** `n × (2ⁿ − 1)` coenable sets, ceiling 17.
- **The user pushes back on framing more cautious — or more defeated — than the evidence
  supports**, and has been right every time. When putting a choice to the user, show the rule
  text and the measurement, not a summary of them. Session 7's reframing of the anchor question
  came from opening the material rather than answering the question as posed.
- **The user asked for less orchestration, not more.** The groups are linear on purpose. Do
  not fan them out into subagents or workflows.
