# Session handoff — monitoring the `gh97` campaign to 360 and carrying it to its verdict

Paste this whole file as the first message of the new session.

---

## 0. Read this first

**The campaign is already running.** It was launched on 2026-08-05 at 16:20 local, on the owner's
explicit go-ahead. Ten containers are executing 360 runs and will finish around **11:00–11:20 on
2026-08-06**. Nothing about the launch needs re-deciding.

**Your job in this session is to start an hourly monitoring loop and keep it running**, then carry
the campaign through its gates to a verdict. This is a change of standing instruction: a previous
session was told *"nao monte monitores automaticamente, eu falo quando verificar"*. **The owner has
now explicitly asked for the loop** — *"vamos criar um loop de hora em hora (ou a cada ~65 minutos)
para verificar o andamento do experimento ... se um container estiver travado deve reiniciar o
container ... dar resume"*. Set it up. The old instruction is superseded for this campaign only.

**Do the first three steps immediately, without asking.** §1 tells you exactly what to run. The
owner wants this to be read-and-execute, so do not re-derive the whole state before starting the
loop — the loop's own first iteration is the verification.

### Repositories and branches

| Path | Branch | Role |
|---|---|---|
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android` | `rearch-counterparts` | Python side. **Git root is the parent `rvsec/`**, so `git` paths are prefixed `rv-android/…` |
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape-rearch` | `rearch` | Java side (a `git worktree`). No Java work is expected this session |
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape` | `master` | The primary APE checkout. **Do not edit it** |

---

## 1. Start here — the three things to do before anything else

### Step 1 — one status pass

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/experimento-rearch-aperv
bash scripts/monitor.sh
```

Expect `running` on all ten and a completed count consistent with §2's cadence table. If the count is
far below what the table predicts, do not panic and do not restart anything yet — read §5 first.

### Step 2 — start the loop

```
/loop 60m Run one monitoring iteration of the gh97 leg-B campaign exactly as specified in
docs/20260805_handoff_gh97_campaign_monitoring.md §4. Report one compact block. Take remediation
action only under the §5 rules. Do not write files, do not commit, do not read any experimental
outcome.
```

Cron has one-minute granularity and cannot express 65 minutes cleanly, so **60 m is the right
choice**: the scheduler adds up to 30 minutes of deterministic jitter to recurring hourly tasks, so
the real cadence lands between 60 and 90 minutes anyway — which is what the owner asked for. Do not
try to force exactly 65.

### Step 3 — tell the owner two things about how the loop actually behaves

Both are properties of session-scoped scheduling, and both are the kind of thing that is discovered
too late if it is not said up front:

1. **The loop only fires while this session is open and idle.** Closing the terminal or letting the
   session exit stops it. It is not a background daemon. `claude --resume` restores an unexpired
   recurring task, but backgrounded Bash and Monitor tasks are never restored.
2. **A fire is skipped, not queued, if it comes due mid-turn.** There is no catch-up: a missed
   interval fires once when Claude next goes idle, not once per missed interval.

The campaign runs ~18 h and the loop expires after 7 days, so expiry is not a concern here.

---

## 2. Where the campaign stands, measured

Launched **2026-08-05 16:20**. Last verified pass **17:32:49 → 20/360 completed, 0 failed**, all ten
containers `running`, SGLang `healthy`.

**Cadence is measured, not estimated.** The `.trace` file is appended continuously during a run, so
the mtime of a finished run's trace marks the moment it ended:

| Container | rep 1 ended | rep 2 ended | Interval |
|---|---|---|---|
| `_00` | 16:55:24 | 17:26:28 | **31 min 04 s** |
| `_04` | 16:56:25 | 17:27:37 | **31 min 12 s** |
| `_09` | 16:57:43 | 17:29:09 | **31 min 26 s** |

That is 1,866 s per run against an 1,800 s timeout — **66 s of install, flush and teardown
overhead**, reproducing the 55–61 s the smoke measured at a 300 s timeout. Dispersion across
containers is 22 s, so no container is straggling.

The **first** run of each container took ~35 min: ~4 min of emulator boot and APK install, paid once
per container, not once per run.

**Projection**: 35 remaining runs × 31.2 min ≈ 18 h 10 min per container, finishing between
**11:03 and 11:16 on 2026-08-06** depending on the container's `RV_DELAY` rung. This is about 1 h to
1 h 15 past the owner's 10:00 target. **Do not propose cutting replicas, timeout or corpus to close
that gap** — the owner's standing decision is that scope is not cut for a deadline, and amendment 01
already changed parallelism precisely so scope would not have to be.

One caveat to carry: the cadence above was measured **only on the `mop_on_llm_off` arm**. Every run
is timeout-bound rather than work-bound, so all three arms should share it — the smoke saw 355–361 s
across all three arms at the same 300 s timeout. The first container turns over to `mop_off_llm_off`
around 21:40; confirm the cadence holds then, and say so if it does not.

### The grid, as the running containers actually received it

```
RV_TIMEOUTS=1800        RV_REPETITIONS=3        RV_SPEC_SET=jca
RV_TOOLS=aperv:mop_on_llm_off:mop_off_llm_off:mop_on_llm_70@corpus_basis=subset40:b60903ad…
```

40 APKs × 3 arms × 3 reps = **360**, matching `manifest.json`'s `predicted_identities`.

### Identities, verified inside the running containers

Verified from **inside** the containers rather than from the host tree, because reading the host tree
is exactly what gh71 got away with:

| Thing | Value |
|---|---|
| Jar inside `rearch_aperv_00` | `a7eddf5a…` — the stage-4 jar stamped `9e948102`, not the image's own master-built jar |
| Image, all ten | `sha256:2cc5c3aada3d…` (`phtcosta/rvandroid:0.9.3-rearch`) |
| `0.9.3` / `latest` tags | both still `b2904fdf…` — leg A's identity, unmoved |
| LLM backend | `Qwen/Qwen3-VL-4B-Instruct`, stock upstream weights, **no fine-tune** |

---

## 3. ⚠ The SGLang provenance fact — protect it

The SGLang container started **`2026-08-01T15:41:36Z`**, two minutes before leg A's decisive run
began (15:43Z), and **has not restarted since**. So the LLM backend is not merely an equivalent
configuration across the two legs — it is numerically the same process holding the same loaded
weights. That retires the backend as a candidate explanation for any difference the gate measures,
which is a stronger claim than the plan originally assumed. It is recorded in `tasks.md` under 8.1.

**Therefore: never restart `sglang-server`, and never start a second one.**

- A restart would destroy the provenance claim above and would have to be recorded as a correction to
  task 8.1, with every run after the restart flagged as served by a different process instance.
- A second instance dies in `torch.OutOfMemoryError` regardless — the GPU holds 12.6 of 15.47 GiB.

If SGLang is ever found unhealthy or down, **stop and report it to the owner**. Do not remediate it
yourself. The `mop_on_llm_70` arm degrades without it, and how to handle already-executed runs is the
owner's call, not a monitoring decision.

---

## 4. The monitoring iteration — exactly what each loop fire does

Run these two commands. **Use absolute paths**: the shell's working directory does not reliably
persist between tool calls, and a relative `find results/…` silently returns nothing from the wrong
directory, which reads as "no activity" and would trigger a false restart.

```bash
# 1. progress
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/experimento-rearch-aperv && bash scripts/monitor.sh

# 2. liveness — how stale is each container's newest artifact?
R=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/experimento-rearch-aperv/results
now=$(date +%s)
for i in 0 1 2 3 4 5 6 7 8 9; do c=rearch_aperv_0$i
  newest=$(find $R/$c -type f -printf '%T@\n' 2>/dev/null | sort -rn | head -1)
  age=$(( now - ${newest%.*} ))
  printf "%-16s newest-file age: %5d s\n" "$c" "$age"
done
```

Report one compact block: completed/failed/pending, container statuses, the staleness column, SGLang
health, and observed cadence against §2's projection. **Do not** write files, commit, or read any
experimental outcome during monitoring.

---

## 5. Remediation — when to act, and what to do

A healthy container writes to its trace **continuously**; all ten measured 0–1 s of staleness while
running. The only legitimate gap is the inter-run window — install, flush, teardown and emulator
turnover, ~66 s of it plus boot.

| Condition | Action |
|---|---|
| Container `running`, age < 300 s | Healthy. Do nothing. |
| Container `running`, age 300–1200 s | Suspicious. **Report, do not act.** Note it so the next iteration can see whether it recovered. |
| Container `running`, age > 1200 s (20 min) | **Stuck. Restart it** — see below. |
| Container `exited` / `not-found` | **Restart it** — see below. |
| `failed` count rises above 0 | Report the count and which identities. Do not silence it. A transient `adb install` failure is expected and is what the final resume pass in 8.3 exists to recover — it is not an emergency. |
| SGLang not `healthy` | **Stop and report to the owner** (§3). Do not restart it. |

The 1200 s threshold is deliberately about two-thirds of a run cycle: far beyond any legitimate
inter-run gap, and short enough that at most one hourly check passes before a genuinely hung
container is caught. Restarting a *healthy* container mid-run throws away up to 30 minutes of work
that resume then has to redo, so the threshold errs against acting.

### How to restart, and why it is safe

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android/experimento-rearch-aperv
docker compose restart rearch_aperv_0N     # one specific hung container
docker compose up -d                       # brings back any exited container; no-op on running ones
```

**Resume is automatic and needs no flag.** The entrypoint execs `rv-experiment run`, which reads
`RV_EXPERIMENT_NAME=rearch_aperv_0N`. `rv-experiment` treats `--name` with an existing `tasks.json` as
an implicit resume and forces `generate_monitors`, `instrument_apks` and `run_static_analysis` to
`False` (INV-EXP-13, `modules/rv-experiment/src/rv_experiment/__main__.py:1231-1268`). rv-platform
handles task-level resume from `tasks.json` independently, so an identity that already COMPLETED is
not re-executed. The compose header documents the same contract.

**Restarting a container is not manual emulator management.** The permanent rule — never start, stop
or manage an Android emulator — stands untouched. `docker compose restart` acts on the container;
`rv-platform` still owns the emulator lifecycle inside it, exactly as it does on a fresh `up -d`.
Never run `emulator`, `adb emu kill`, or any emulator command directly, in any context.

---

## 6. When the campaign reaches 360 — stop the loop, then proceed

Stop the loop (press `Esc` while it waits, or `CronDelete` its ID) once completed + failed reaches
360 and no container is still executing. Then work through the remaining tasks **inside the OpenSpec
workflow** (§7).

- **8.2** Monitoring — tick it with what the loop observed: cadence, any restarts performed and why,
  any failures recovered.
- **8.3** One final resume pass (`docker compose up -d`) to recover transient `adb install` failures,
  then confirm identity-distinct completions equal **360**.
- **8.4** **Extract the traces BEFORE any `docker compose down`.** Device artifacts are ephemeral.
  This is the single most destructive mistake available in this session.
- **Group 9** The four validity gates (9.1–9.4), then `verify.py` (9.5), then `consolidate.py` (9.6).
  **No outcome is read before 9.1–9.5 pass.** A failed gate invalidates what it protects, and the
  analysis is not adjusted to route around it.
- **Group 10** `compare.py`, the result document (whatever it says, including a tie), the exploratory
  list, the merge verdict, a `DECIDE` entry in `calibracao/journal.jsonl`, then the four closing
  skill runs 10.5–10.8.

`gh97-rearch-ab-gate` is at **44/61** as of this handoff (8.1 ticked, committed as `1c4ac319`).

---

## 7. Working rules — non-negotiable

1. **Follow the OpenSpec workflow rigorously.** Never create or rewrite an OpenSpec artifact with
   `Write`/`Edit` outside a skill. Enter through the `Skill` tool: `openspec-apply-change`,
   `openspec-update-change`, `openspec-verify-change`, `openspec-sync-specs`,
   `openspec-archive-change`. Two narrow exceptions, both already exercised: ticking a checkbox in
   `tasks.md` **while inside `openspec-apply-change`**, and writing a task's *deliverable* file.
2. **Artifacts commit before code**, in their own `plan(...)` commit, then `feat(...)`/`fix(...)`/
   `docs(...)`. Subjects use `refs #97`; `closes #97` only when the owner says so.
3. **Never add a `Co-Authored-By` trailer.** The user is the sole author.
4. **Never `git add` a results tree.** `experimento-rearch-aperv/results*/` is **not** gitignored and
   holds root-owned files from the containers; `git add <dir>` fails with `Permissão negada`. Stage
   explicit file paths only. Same for `backup/`, which is **not** gitignored here despite the
   top-level `CLAUDE.md` saying so.
5. **P3**: deleted code is deleted, not disabled — backed up to `backup/` first.
6. **Portuguese is written with correct accents**, even when the owner omits them and even when
   surrounding file content lacks them.
7. `openspec` must be run **from `rv-android/`**, not from the git root. From `rvsec/` it answers
   `Unknown item 'gh97-rearch-ab-gate'`.
8. `openspec instructions` prints `Invalid 'references' field in config…` before its JSON. Harmless —
   strip everything before the first `{` when parsing.
9. **`git checkout <rev> -- <path>` and `git stash` are working-tree mutations.** Use
   `git show <rev>:<path>` for read-only inspection.
10. `openspec validate --all` clean state is **"16 passed, 2 failed"** — `gh-tbd-env-vars-architecture`
    and `gh48-project-finalization` are pre-existing failures. Re-derive rather than matching a
    remembered string.

---

## 8. Learnings that will cost you time if ignored

**Counting identity**, learned the hard way on 2026-06-19: an identity is
`(apk_name, tool_config.name, tool_config.variant, repetition, timeout)` — note `variant` lives under
**`tool_config`**, not directly in `config`. Grepping `COMPLETED` double-counts through
`result.state_transitions[]`. `tasks.json` is a dict with the runs under the `tasks` key, not a bare
list. `scripts/monitor.sh` already counts correctly; do not replace it with a grep.

**Reading traces**: use `aperv_tool.analysis.trace_ndjson`, the same reader `consolidate.py` and
`verify.py` use. `TraceReader` wants the **uncompressed `.trace`** path — it returns nothing for
`.ndjson.gz`. Its run-level census (`mop_data`, `pipeline`, `llm_ack`) is populated **while
iterating**, so drain the steps first and read the census after. Step records key their timestamp on
`t` and carry no `type`, so a naive `record.get('type')` scan misclassifies them.

**Shell working directory does not persist reliably** between tool calls. This already produced one
silent empty result during the previous session. Use absolute paths everywhere.

**`cov_mop` does not identify an application that exercises MOP guidance.** It comes from the RVSEC
logcat markers and does not depend on the guidance artifact at all, so an application can post
`cov_mop` 68 % with an entirely empty MOP artifact. This cost one whole smoke run.

**MOP guidance is structurally inert over most of this corpus** — over the 40 `.apk.json` of
`subset40`, `flagged > 0` in 8/40, `wtg > 0` in 15/40, and all three of `flagged`/`wtg`/
`mopActivities` together in only 4/40. This is a property of the corpus, not of the jar. It is
already owed as an exploratory observation under task 10.3, because G3 reports displacement and 36 of
40 applications cannot produce any — which a reader would otherwise mistake for a null result of the
rewrite.

**`props_digest` reporting SKIP in the pre-flight is the intended state**, settled and closed. Do not
reopen it. The pushed `.properties` bytes are not retained (`_push_properties()` unlinks the temp
file), and from stage 2 onward the jar aborts before step 1 on an unknown key, a retired key, or a
non-neutral value of an inactive feature — so a run that produced a trace already passed a stricter
check. Retaining the file was drafted and withdrawn on the owner's objection under P1.

**`gh95` carries a defect that is not this change's to fix** but will bite whoever archives it: its
delta at `openspec/changes/gh95-thin-python-arms/specs/aperv/spec.md:618` still binds
`step_telemetry_enabled` to a `Feature.STEP_TELEMETRY` the jar deleted, so syncing it as-is would
plant a dead key in the main spec as normative. Only `:618` needs fixing, via `openspec-update-change`
on `gh95`. Do **not** regenerate `tests/migration/arm_effective_baseline.json` — it still carries the
key and that is correct: it is evidence, excluded by name with its reason.

**`gh98-manifest-package-default` is another session's change — do not touch it.** It was checked
against this campaign and does not conflict: its "manifest" is the *Android* manifest
(`App.code_package` returning the declared `applicationId` instead of running `PackageDetector`), and
it touches `rv-android-core`, `rv-experiment`, `rv-static-analysis`, `rv-instrumentation-ajc` and
`rv-platform` — never `experimento-rearch-aperv/manifest.json` or the aperv arm defaults. It also
cannot reach the running campaign: the compose mounts only the jar, `filters10/`, the APKs and
`results/`, so every Python module comes from the frozen image clone at `19ae3da1`.

---

## 9. Files and commands

```
openspec/changes/gh97-rearch-ab-gate/
  tasks.md proposal.md design.md specs/aperv/spec.md

experimento-rearch-aperv/
  docker-compose.yml            # 10 containers, filters10/, external sglang network
  filters/batch_00..07.txt      # leg A's partition — EVIDENCE, do not touch
  filters10/batch_00..09.txt    # leg B's partition (amendment 01), 4 APKs each
  manifest.json                 # expected_sha 9e948102, image 2cc5c3aa…, 10 containers, 360 identities
  results/rearch_aperv_00..09/  # THE CAMPAIGN'S OUTPUT — root-owned, never git add
  scripts/monitor.sh            # fixed for 10 containers in 36af0935
  scripts/{preflight_runstart,verify,consolidate,compare,make_manifest,multiarm_stats}.py

docs/20260804_preregistro_gate_rearch.md   # FROZEN + appendix + amendment 01
docs/20260805_preflight_gate_rearch.md     # the pre-flight report (task 7.4)
docs/20260805_handoff_gh97_campaign_execution.md   # the previous session's handoff
calibracao/journal.jsonl                   # the digest chain
```

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

# re-derive state (openspec must run from HERE, not from the git root)
openspec list
grep -n "^- \[ \]" openspec/changes/gh97-rearch-ab-gate/tasks.md | cut -c1-140

# the campaign
cd experimento-rearch-aperv
bash scripts/monitor.sh
docker compose restart rearch_aperv_0N     # a hung container; resume is automatic
docker compose up -d                       # brings back exited containers

# gates and verdict, in this order — no outcome read before verify.py is clean
uv run python scripts/verify.py
uv run python scripts/consolidate.py       # per_apk_paired.csv, tel_proxies.csv
uv run python scripts/compare.py           # G1, G2, G3 with point estimates and CIs

# tests (the two flags are the CI contract)
uv run pytest modules/aperv-tool/tests --import-mode=importlib -o "addopts=" -q
```

---

## 10. What NOT to do

- Do **not** `docker compose down` before the traces are extracted (task 8.4). Device artifacts are
  ephemeral and this is irreversible.
- Do **not** restart or replace `sglang-server`, and do not start a second one (§3).
- Do **not** start, stop or manage an Android emulator, in any context, ever.
- Do **not** read any outcome before gates 9.1–9.5 pass.
- Do **not** reduce replicas, timeout or corpus to save wall clock, including to meet the 10:00
  target. Report the slip instead.
- Do **not** move or reuse the `0.9.3` / `latest` image tags, and do not run
  `docker/rvandroid/build.sh` — it moves them, and they hold leg A's image identity.
- Do **not** edit the pre-registration except by a registered amendment with a fresh journal digest.
- Do **not** touch `experimento-cal/` — historical, and a recorded decision forbids editing it.
- Do **not** touch `gh98` (§8).
- Do **not** `git add` `backup/`, `results/` or `results_smoke/`.
- Do **not** restart a container that is merely slow. Honour the 1200 s threshold in §5.
