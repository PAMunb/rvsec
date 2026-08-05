# Session handoff — executing the `gh97` campaign and carrying it to its verdict

Paste this whole file as the first message of the new session.

---

## 0. Read this before doing anything

**The objective of this session is to execute the experiment** — launch the campaign, carry it to
360 completed runs, pass the validity gates, and produce the verdict.

Everything below was measured on **2026-08-05**, at the end of the session that produced it. Where
this document states a status, treat it as a **starting hypothesis to re-derive**, not as fact. Other
sessions work in both repositories concurrently — a `gh98-manifest-package-default` change appeared
mid-session while the previous conversation was running. Re-derive from `tasks.md` and `openspec list`,
always. §9 has the commands.

### ⚠ TWO STANDING INSTRUCTIONS FROM THE OWNER

1. **Do not launch the full campaign without the owner saying so explicitly.** Their words:
   *"nao execute o experimento final sem eu dar ok"*. Everything up to the launch is prepared; the
   launch itself waits for the word. Ask, then wait.
2. **Do not set up monitoring automatically. Do not poll, do not schedule wake-ups, do not run
   `watch`.** The owner said: *"nao monte monitores automaticamente, eu falo quando verificar"* — they
   will say when to check. Run `scripts/monitor.sh` **only when asked**, once, and report. This is a
   ~18.6 h campaign; the temptation to babysit it is exactly what is being refused.

### Repositories and branches

| Path | Branch | Role |
|---|---|---|
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android` | `rearch-counterparts` | Python side. **Git root is the parent `rvsec/`**, so paths in `git` commands are prefixed `rv-android/…` |
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape-rearch` | `rearch` | Java side (a `git worktree`). All Java work happens here |
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape` | `master` | The primary APE checkout. **Do not edit it** |

### Non-negotiable working rules

1. **Never start, stop or manage an Android emulator.** `rv-platform` owns the whole lifecycle. This
   applies to the campaign too: it runs through `docker compose`, never through a manual `emulator`
   or `adb emu kill`. Permanent rule, no exceptions, in any context.
2. **Follow the OpenSpec workflow rigorously.** Never create or rewrite an OpenSpec artifact with
   `Write`/`Edit` outside a skill. Enter through the `Skill` tool: `openspec-apply-change`,
   `openspec-update-change`, `openspec-verify-change`, `openspec-sync-specs`,
   `openspec-archive-change`. Two narrow exceptions, both already exercised: ticking a checkbox in
   `tasks.md` **while inside `openspec-apply-change`**, and writing a task's *deliverable* file.
3. **Artifacts commit before code**, in their own `plan(...)` commit, then `feat(...)`/`chore(...)`/
   `docs(...)`. Subjects use `refs #97`; `closes #97` only when the owner says so. **The owner
   enforced this mid-session** — do not touch code before the artifacts describing it are committed.
4. **Never add a `Co-Authored-By` trailer.** The user is the sole author.
5. **P3**: deleted code is deleted, not disabled — but backed up to `backup/` first. **`backup/` is
   NOT gitignored in this repo**, despite the top-level `CLAUDE.md` saying so. Never `git add` it.
6. `openspec instructions` prints `Invalid 'references' field in config…` before its JSON. Harmless —
   strip everything before the first `{` when parsing.
7. **`git checkout <rev> -- <path>` and `git stash` are working-tree mutations.** Use
   `git show <rev>:<path>` for read-only inspection.
8. **Three `openspec validate --all` failures are pre-existing**: `gh-tbd-env-vars-architecture` and
   `gh48-project-finalization` were the two known ones; with `gh98` now present the clean state reads
   **"16 passed, 2 failed"**. Re-derive the count rather than matching a remembered string.
9. **`openspec` must be run from `rv-android/`**, not from the git root. From `rvsec/` it answers
   `Unknown item 'gh97-rearch-ab-gate'`.
10. **Never `git add` a results tree.** `experimento-rearch-aperv/results*/` is **not** gitignored and
    contains root-owned files from the containers; `git add <dir>` fails with `Permissão negada`.
    Stage explicit file paths only.
11. **The shell's working directory persists between tool calls.** A `cd` deep into a results tree in
    one call silently breaks relative paths several calls later. Prefer absolute paths.

---

## 1. Where this stands

**`gh97-rearch-ab-gate` is at 43/61.** Groups 1–7 are **done** — group 7 (smoke + pre-flight) executed,
passed, and was recorded in the previous session. Groups 8 (campaign), 9 (validity gates) and 10
(verdict) are open. **Group 8 is this session's first substantive work, and it needs the owner's word.**

| Change | State | Note |
|---|---|---|
| `gh97-rearch-ab-gate` | **43 / 61** | This session's subject |
| `gh95-thin-python-arms` | 56 / 57 | Only 7.6, owner sign-off. Still carries the `:618` defect (§7) |
| `gh98-manifest-package-default` | new, no tasks | **Another session's.** Do not touch. See §8 |
| `gh93`, `gh94`, `gh96` | archived | — |

`ape` side, re-derive before citing: `rearch-04` 75/3, `rearch-06` 25/4, `rearch-07` 50/1. Note that
`rearch-04` 9.1 is now **fully dischargeable** on this smoke's evidence (§4), which the last reading
of that change did not yet reflect.

### Everything the launch needs is verified in place

All of this was re-measured on 2026-08-05 at the end of the previous session:

- **Jar** deployed: sha256 `a7eddf5a776ce20f7299911d7d9acb3a0f1342cdc1512b3e28aa00488e582a94`, built
  from `rearch` commit `9e948102`, **stamped `9e948102`** (not master's `c638142`).
- **Image** built: `phtcosta/rvandroid:0.9.3-rearch` = `sha256:2cc5c3aada3d…`, label
  `rvsec.branch=rearch-counterparts`, clone verified inside the image at `19ae3da1`.
- **Image is current with the branch** — the gh71 check `git log --oneline 19ae3da1..HEAD --
  rv-android/modules/` is **empty**. The branch is now 15 commits ahead of the image, all of them
  artifacts, campaign scaffold and docs. **Re-run this check before launching**; if it is ever
  non-empty, the image must be rebuilt (§9) and pushed.
- **Leg A's tags unmoved**: `0.9.3` and `latest` both still `sha256:b2904fdf…aedec`.
- **External LLM backend up**: network `experimento-e3-decisiva_default` exists and `sglang-server` is
  `Up 4 days (healthy)`. Both legs' LLM arms are served by the **same** backend, which removes a
  difference between legs rather than adding one. A second sglang instance dies in
  `torch.OutOfMemoryError` — the GPU holds 12.6 of 15.47 GiB already. Do not start one.
- **No `rvandroid` containers running** — clean slate.
- **Campaign compose**: 10 containers (`rearch_aperv_00`…`_09`), `filters10/` (4 APKs each, 40 total),
  no `sglang` service (joins the external network), jar bind-mounted on all ten.
- **Manifest**: `expected_sha 9e948102`, image id `2cc5c3aa…`, containers 10, reps 3, timeout 1800,
  `predicted_identities` **360**, bootstrap seed 42, `corpus_basis`
  `subset40:b60903adf4c8fca07e014e3655db158a220184d112f2f995a181fd98dd3d48d4`.

---

## 2. ⚠ A DEFECT TO FIX BEFORE MONITORING — `scripts/monitor.sh` is stale

**Found 2026-08-05, not yet fixed. Fix it before task 8.2, ideally before the launch.**

Amendment 01 repartitioned the campaign from 8 × 5 to **10 × 4** containers, but `scripts/monitor.sh`
was never updated:

- Line 19: `CONTAINERS="rearch_aperv_00 … rearch_aperv_07"` — **only 8**. The compose file defines ten
  (`container_name` at lines 114–258). Containers `_08` and `_09` would be **invisible to the
  monitor**, undercounting by up to **72 of the 360 runs**.
- Lines 10–11 of the header: *"Each container owns 5 APKs … so a healthy container converges on 45
  tasks."* Under 10 × 4 each container owns **4 APKs** and converges on **36** tasks (4 × 3 arms × 3
  reps). Every container would read as permanently "short of 45".

Together these would make a completed campaign look stuck at 288/360 with all ten containers
apparently failing — a false alarm expensive enough to trigger a pointless resume pass, or worse, to
mask a real shortfall. `EXPECTED=360` is correct and must not change.

This is a code fix in the campaign scaffold. Follow rule 3: it is not an OpenSpec artifact, so it is a
`fix(gh97): …` commit, and no `tasks.md` prose is owed unless you tick something with it.

---

## 3. What to do next, in order

1. **Re-derive §1** — `openspec list`, the two `git status --porcelain`, the identity checks in §9.
2. **Re-run the gh71 image-currency check.** Cheap, and it is the failure mode that has already bitten
   this project twice (once at the jar layer, once at the harness layer).
3. **Fix `scripts/monitor.sh`** (§2). Commit as `fix(gh97): …`.
4. **Check `gh98` does not touch the campaign's `manifest.json`** (§8) before committing 18.6 h to it.
5. **ASK THE OWNER FOR THE GO-AHEAD.** Then, and only then, launch group 8.
6. **Group 8** — launch, monitor **only when asked**, one final resume pass, confirm identity-distinct
   completions equal 360, extract traces **before** any `docker compose down`.
7. **Group 9** — the four validity gates, then `verify.py`, then `consolidate.py`. **No outcome is
   read before 9.1–9.5 pass.**
8. **Group 10** — `compare.py`, the result document (whatever it says, including a tie), the
   exploratory list, the merge verdict, the `DECIDE` journal entry, then the four closing skill runs
   (10.5–10.8).

---

## 4. What the previous session established (group 7)

The smoke ran on 2026-08-05 — 3 arms × 2 applications × 1 rep × 300 s = 6 runs — and everything was
**re-measured from the stored artifacts** rather than trusted from the session that produced it. That
re-measurement changed three things, which is the reason the rule exists.

**The gate is open**: `preflight_runstart.py` reports **9 PASS · 0 FAIL · 3 SKIP, exit 0**,
`GATE: the campaign starts.` `build.sha` reads `9e948102` on all three arms — the bind-mounted stage-4
jar won, gh71 did not recur. `corpus_basis` present and matching on all three, which is the
authoritative verdict on the DSL parameter seam of task 2.6.

**7.2a holds on all three arms of both applications** (the earlier record covered only one):

| Application | Arm | `MOP_DATA` | `wtgEdges` | `mopActivities` | steps | boosts | `decision_source=MOP` |
|---|---|---|---|---|---|---|---|
| smartpack | `mop_off_llm_off` *(control)* | loaded, v1, digest | 23 | 8 | 303 | **0** | **0** |
| smartpack | `mop_on_llm_70` | loaded, v1, digest | 23 | 8 | 234 | 15 | 2 |
| smartpack | `mop_on_llm_off` | loaded, v1, digest | 23 | 8 | 307 | 17 | 15 |
| freeotpplus | `mop_off_llm_off` *(control)* | loaded, v1, digest | 86 | 7 | 292 | **0** | **0** |
| freeotpplus | `mop_on_llm_70` | loaded, v1, digest | 86 | 7 | 227 | 150 | 66 |
| freeotpplus | `mop_on_llm_off` | loaded, v1, digest | 86 | 7 | 273 | 185 | 88 |

Within each application the control's `sourceDigest` is **identical** to the guided arms'. That is what
makes the negative half meaningful: the control received the same artifact and produced no effect from
it. **The control is not a non-MOP arm** — it declares `"mop_data": "static_analysis"` like the others
with its five scoring weights at `0` (design D1, INV-APV-29). What must not reach it is *effect*, not
the artifact. Gate 9.1 applies this same predicate at campaign scale.

**Task integrity**: 6/6 identity-distinct COMPLETED, coverage > 0 on every run and metric, **zero
`VerifyError`**, zero detected errors, `coverage.csv` 2,852 rows.

**Three corrections the re-measurement produced** — carry these, they matter:

1. **A published figure was wrong.** The prior handoff recorded `mop_on_llm_70`/smartpack as 108 steps,
   2 boosts, 0 `decision_source=MOP`. The trace gives **234 / 15 / 2**, consistent three independent
   ways (reader `len(steps)`, `RUN_END.steps`, logcat heartbeat count) where the published figure was
   consistent none. Only that row was stale; `mop_on_llm_off` reproduced exactly.
2. **`rearch-04` 9.1 discharges completely.** Design D11 wrote off an LLM **error** and a
   `no_match reason=dead_pair` as un-guaranteeable inside a reduced-timeout smoke, to be recorded only
   *if present*. **Both appeared** — `result=breaker_open` ×2 (`trips` 1, 2) plus `reason=timeout` ×2,
   and **37 `dead_pair`** across the two `llm_70` runs. So 9.1 rests on device evidence for every
   clause rather than leaning on `gh94`'s golden-fixture tests for the last two.
3. **Heartbeats: no finding.** Raw grep, parsed count, distinct heartbeat `s`, `StepRecord` count and
   distinct step `s` all agree in all six runs, `s` sets identical and contiguous `1..N`. No arm
   produced fewer heartbeats than another. Appended to `gh94`'s **archived** deliverable path.

**Per-run wall clock measured: 355–361 s at a 300 s timeout** — ~57 s of install, flush and teardown
overhead. That is where amendment 01's ~1857 s per run at 1800 s comes from, so the 18.6 h budget rests
on measurement rather than estimate.

Deliverables written: `docs/20260805_preflight_gate_rearch.md` (sha256
`a4b1a7592936feda855210231d09f9577cbfb0962729df5f1b872f07a5b99825`), the `PREFLIGHT` journal entry,
and the `gh94` heartbeat appendix. Commits `b0522d67` (artifacts) then `ceef1c16` (deliverables).

---

## 5. The `props_digest` question — settled, do not reopen without reading this

`preflight_runstart.py` has four checks. Check 1 compares `RUN_START.props_digest` against the SHA-256
of the pushed `ape.properties`. **It reports SKIP and that is the intended state.**

*It cannot pass.* `_push_properties()` writes to a temp file and `os.unlink`s it after the push, so the
bytes sent are not retained. Reconstruction through the tool's own code path with the push intercepted
did **not** reproduce any of the three echoed digests under any plausible variation. The same
reconstruction **inside the campaign image** produced bytes identical to the local tree — which rules
out harness/image drift and leaves the difference unexplained. **That loose end is real and is recorded
rather than closed.** To chase it: instrument a live run with the push intercepted inside the container.

*It does not need to pass.* From stage 2 onward the jar **aborts before step 1** on an unknown key, a
retired key, or a non-neutral value of an inactive feature. A run that produced a trace has already
passed a stricter check. What the digest would add over checks 2–4 is detection of *undeclared* keys —
exactly what the jar's validation refuses.

*Retaining the file was drafted and withdrawn* on the owner's objection: one `.properties` artifact per
task, added to `aperv-tool` to feed a redundant check. P1 settles it. The delta-spec requirement was
removed **before any code was touched**, which is the order the workflow requires.

Corrected along the way: `inert` in `RUN_START` lists keys of the **effective plan** at neutral values
for inactive features — it is **not** evidence of what the pushed file contained.

---

## 6. Amendment 01 — the partition, and what it cost

The owner set a target of finishing by **10:00 on 2026-08-06**. Measured need was ~23.2 h against
~18.7 h of budget, so the partition was amended from **8 × 5 to 10 × 4** containers.

**Nothing in the statistical grid moved**: 3 arms, 40 applications, 3 replicas, 1800 s, 360 runs, same
binaries, same LLM dose, same model, same bootstrap seed. Two levers were refused on the record: fewer
replicas is the exact 2026-06-19 failure mode this gate exists to prevent, and a shorter timeout would
break comparability outright since leg A was measured at 1800 s.

**What it costs, stated and not absorbed**: the filters are no longer byte-identical to leg A's, so an
application no longer runs at the same container index in both legs and container effects stop
cancelling in the paired difference. The pairing **by application**, which G1/G2/G3 rest on, is
untouched.

**Journal chain** in `calibracao/journal.jsonl`, all before any outcome existed:

| State | sha256 | When |
|---|---|---|
| `FREEZE-PREREGISTRO` | `c0ac9a7f…` | 2026-08-04, before the jar existed |
| `APENDICE-PROVENIENCIA` | `a0da2273…` | 2026-08-05 17:43 |
| `FREEZE-PREREGISTRO-EMENDA-01` | `594cf04a…` | 2026-08-05 18:27 |
| `PREFLIGHT` | `a4b1a759…` | 2026-08-05 19:03 |

The pre-registration admits **only** registered amendments with a fresh digest beside the original.
Never edit it silently. Its §11 provenance appendix is filled and its §2 declares the rule.

### MOP guidance is inert over most of this corpus — this governs the *reading*, not the campaign

Deriving the artifact host-side over the 40 `.apk.json` of `subset40`: `flagged > 0` in **8/40**,
`wtg > 0` in **15/40**, all three of `flagged`/`wtg`/`mopActivities` together in only **4/40**. The two
most-flagged applications (aegis 50, de.blau 42) have an **empty WTG**. This is a property of the
corpus, not of the jar. G3 reports displacement and **36 of 40 applications cannot produce any** — a
reader would otherwise take that absence for a null result of the rewrite. Task 10.3 already names it
as a post-freeze observation and it is owed in the write-up.

**And the trap that cost a smoke: `cov_mop` does not identify an application that exercises the
guidance.** It comes from the RVSEC logcat markers and does not depend on the guidance artifact at all,
so an application can post `cov_mop` 68 % with an entirely empty MOP artifact. To pick one, derive the
artifact and require the three quantities positive.

---

## 7. `gh95`'s defect — not `gh97`'s to fix, but it will bite whoever archives `gh95`

The `step_telemetry_enabled` key was removed from `APERV_PROPERTY_MAPPING` (`7902bab4`) and the jar
deleted `Feature.STEP_TELEMETRY`, so the key now aborts plan validation. But `gh95`'s own delta at
`openspec/changes/gh95-thin-python-arms/specs/aperv/spec.md:618` still binds it to `STEP_TELEMETRY`.
Syncing `gh95` as it stands would plant a dead key in the main spec as normative. **Only `:618` needs
fixing**, via `openspec-update-change` on `gh95` — the three main-spec sites die on their own when the
delta syncs. The frozen `arm_effective_baseline.json` still carrying the key is **correct** and must
not be regenerated: it is evidence, excluded by name with its reason.

---

## 8. `gh98-manifest-package-default` — another session's change

It appeared during the previous session with no tasks yet. **It is not this session's work and must not
be touched.** But its name suggests it may alter manifest/package defaults, and this campaign is driven
by `experimento-rearch-aperv/manifest.json`. **Before launching, confirm it does not modify that file
or the `aperv` arm defaults the manifest declares.** A change to arm defaults landing mid-campaign
would silently split the 360 runs across two configurations — undetectable afterwards except as noise.
If it does touch them, raise it with the owner before launching rather than working around it.

---

## 9. Files and commands

```
openspec/changes/gh97-rearch-ab-gate/
  tasks.md proposal.md design.md specs/aperv/spec.md

experimento-rearch-aperv/
  docker-compose.yml            # 10 containers, filters10/, external sglang network
  docker-compose.smoke.yml      # the smoke vehicle
  filters/batch_00..07.txt      # leg A's partition — EVIDENCE, do not touch
  filters10/batch_00..09.txt    # leg B's partition (amendment 01), 4 APKs each
  manifest.json                 # expected_sha 9e948102, image 2cc5c3aa…, containers 10, 360 identities
  results_smoke/                # the smoke's output (untracked, root-owned — never git add)
  scripts/{preflight_runstart,verify,consolidate,compare,make_manifest,multiarm_stats}.py
  scripts/monitor.sh            # ⚠ STALE — 8 containers, see §2
  scripts/test_compare.py

docs/20260804_preregistro_gate_rearch.md   # FROZEN + appendix + amendment 01
docs/20260805_preflight_gate_rearch.md     # the pre-flight report (task 7.4)
calibracao/journal.jsonl                   # the digest chain
backup/gh97-prechange-jar/                 # 386ce08d… — leg A's jar (never git add)
backup/gh97-6.2-superseded/                # 605b4174…, the master-stamped counter-example
backup/gh97-smoke-descartado/              # the first smoke, on the wrong applications
```

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

# --- re-derive (openspec must run from HERE, not from the git root) ---
openspec list
openspec validate --all            # clean state is "16 passed, 2 failed" (gh98 now present)
grep -n "^- \[ \]" openspec/changes/gh97-rearch-ab-gate/tasks.md | cut -c1-140

# --- is the image still current with the branch? (the gh71 check) ---
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec
git log --oneline 19ae3da1..HEAD -- rv-android/modules/     # non-empty => rebuild the image

# --- identities (read-only) ---
sha256sum rv-android/modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar   # a7eddf5a…
sha256sum rv-android/backup/gh97-prechange-jar/ape-rv.jar                       # 386ce08d…
docker image inspect phtcosta/rvandroid:0.9.3        --format '{{.Id}}'   # b2904fdf… MUST NOT MOVE
docker image inspect phtcosta/rvandroid:latest       --format '{{.Id}}'   # b2904fdf… MUST NOT MOVE
docker image inspect phtcosta/rvandroid:0.9.3-rearch --format '{{.Id}}'   # 2cc5c3aa…

# --- LLM backend must already be up; NEVER start a second one ---
docker network ls --filter name=experimento-e3-decisiva
docker ps --filter name=sglang --format '{{.Names}}\t{{.Status}}'   # Up N days (healthy)

# --- if and only if the image must be rebuilt ---
#   NEVER use docker/rvandroid/build.sh — it moves the 0.9.3 and latest tags,
#   which hold leg A's image identity.
docker build --build-arg RVSEC_BRANCH=rearch-counterparts \
  -t phtcosta/rvandroid:0.9.3-rearch -f docker/rvandroid/Dockerfile .

# --- tests (the two flags are the CI contract) ---
uv run pytest modules/aperv-tool/tests --import-mode=importlib -o "addopts=" -q
APE_REPO=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape-rearch \
  uv run pytest modules/aperv-tool/tests/migration --import-mode=importlib -o "addopts=" -q
# without APE_REPO the whole migration tier skips SILENTLY

# --- the campaign (ONLY after the owner's explicit go-ahead) ---
cd experimento-rearch-aperv
docker compose up -d
bash scripts/monitor.sh          # ONLY when the owner asks. Fix §2 first.

# --- gates and verdict, in this order, no outcome read before verify.py is clean ---
uv run python scripts/verify.py
uv run python scripts/consolidate.py     # per_apk_paired.csv, tel_proxies.csv
uv run python scripts/compare.py         # G1, G2, G3 with point estimates and CIs
```

**Counting rule, learned the hard way on 2026-06-19**: identity is
`(apk_name, tool_config.name, tool_config.variant, repetition, timeout)` — note `variant` lives under
**`tool_config`**, not directly in `config`. Grepping `COMPLETED` double-counts through
`result.state_transitions[]`. `tasks.json` is a dict with the runs under the `tasks` key, not a bare list.

**Reading traces**: use `aperv_tool.analysis.trace_ndjson` — the same reader `consolidate.py` and
`verify.py` use. Two gotchas that cost time: `TraceReader` wants the **uncompressed `.trace`** path (it
returns nothing for the `.ndjson.gz`), and its run-level census (`mop_data`, `pipeline`, `llm_ack`) is
populated **while iterating**, so drain the steps first and read the census after. Step records key
their timestamp on `t` and carry no `type`, so a naive `record.get('type')` scan misclassifies them.

---

## 10. What NOT to do

- Do **not** launch the campaign without the owner's explicit go-ahead.
- Do **not** set up automatic monitoring, polling or scheduled wake-ups. The owner says when to check.
- Do **not** move or reuse the `0.9.3` / `latest` image tags, and do not run `docker/rvandroid/build.sh`.
- Do **not** build the image without `--build-arg RVSEC_BRANCH=rearch-counterparts` — without it the
  Dockerfile clones `PAMunb/rvsec` at its default `modules` branch and you get an image with **none**
  of `gh94`/`gh95`/`gh96`/`gh97`, every arm running the canonical harness while the campaign records it
  as the re-architected one.
- Do **not** start a second sglang instance — it dies in `torch.OutOfMemoryError` and the existing one
  is shared with leg A by design.
- Do **not** edit the pre-registration except by a registered amendment with a fresh journal digest.
- Do **not** reduce replicas, timeout or corpus to save wall clock. The owner's standing decision is
  that scope is not cut for a deadline; amendment 01 changed parallelism precisely to avoid it.
- Do **not** re-add the retained-`.properties` artifact (§5).
- Do **not** regenerate `tests/migration/arm_effective_baseline.json`.
- Do **not** read any outcome before gates 9.1–9.5 pass. A failed gate invalidates what it protects,
  and the analysis is not adjusted to route around it.
- Do **not** `docker compose down` before the traces are extracted — device artifacts are ephemeral.
- Do **not** touch `experimento-cal/` — historical, and a recorded decision forbids editing it.
- Do **not** touch `gh98` (§8).
- Do **not** `git add` `backup/`, `results/` or `results_smoke/`.
