# Session handoff — launching the `gh97` campaign and carrying it to its verdict

Paste this whole file as the first message of the new session.

---

## 0. Read this before doing anything

Everything below was measured on **2026-08-05**, late in the session that produced it. Where this
document states a status, treat it as a **starting hypothesis to re-derive**, not as fact. Other
sessions work in both repositories, and this session watched `rearch-04` move from 74/4 to 75/3 while
the conversation was running.

Re-derive from `tasks.md` and `openspec list`, always. §8 has the commands.

### Repositories and branches

| Path | Branch | Role |
|---|---|---|
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android` | `rearch-counterparts` | Python side. **Git root is the parent `rvsec/`**, so paths in `git` commands are prefixed `rv-android/…` |
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape-rearch` | `rearch` | Java side (a `git worktree`). All Java work happens here |
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape` | `master` | The primary APE checkout. **Do not edit it** |

### ⚠ THE ONE THING THAT NEEDS OWNER APPROVAL

**Do not launch the full campaign without the owner saying so explicitly.** They said so in these
words: *"nao execute o experimento final sem eu dar ok"*. Everything up to the launch is prepared;
the launch itself waits.

### Non-negotiable working rules

1. **Never start, stop or manage an Android emulator.** `rv-platform` owns the whole lifecycle. This
   applies to the campaign too: it runs through `docker compose`, never through a manual `emulator`
   or `adb emu kill`. Permanent rule.
2. **Follow the OpenSpec workflow rigorously.** Never create or rewrite an OpenSpec artifact with
   `Write`/`Edit` outside a skill. Enter through the `Skill` tool: `openspec-apply-change`,
   `openspec-update-change`, `openspec-verify-change`, `openspec-sync-specs`,
   `openspec-archive-change`. Two narrow exceptions, both already exercised: ticking a checkbox in
   `tasks.md` **while inside `openspec-apply-change`**, and writing a task's *deliverable* file.
3. **Artifacts commit before code**, in their own `plan(...)` commit, then `feat(...)`/`chore(...)`.
   Subjects use `refs #97`; `closes #97` only when the owner says so. **The owner enforced this
   mid-session** — do not touch code before the artifacts describing it are committed.
4. **Never add a `Co-Authored-By` trailer.** The user is the sole author.
5. **P3**: deleted code is deleted, not disabled — but backed up to `backup/` first. **`backup/` is
   NOT gitignored in this repo**, despite the top-level `CLAUDE.md` saying so. Never `git add` it.
6. `openspec instructions` prints `Invalid 'references' field in config…` before its JSON. Harmless.
7. **`git checkout <rev> -- <path>` and `git stash` are working-tree mutations.** Use
   `git show <rev>:<path>` for read-only inspection.
8. **Two `openspec validate --all` failures are pre-existing**: `gh-tbd-env-vars-architecture` and
   `gh48-project-finalization`. "15 passed, 2 failed" is the clean state.
9. **`openspec` must be run from `rv-android/`**, not from the git root. From `rvsec/` it answers
   `Unknown item 'gh97-rearch-ab-gate'`.
10. **Never `git add` a results tree.** `experimento-rearch-aperv/results*/` is **not** gitignored and
    contains root-owned files from the containers; `git add <dir>` fails with `Permissão negada`.
    Stage explicit file paths only.

---

## 1. Where this stands

**`gh97-rearch-ab-gate` is at 37/61.** Groups 1–6 are **done**. Group 7 (smoke + pre-flight) has
**executed and passed**, but its boxes are **not yet ticked** — that is the first job of the new
session. Groups 8–10 (campaign, validity gates, verdict) are open.

| Change | State | Note |
|---|---|---|
| `gh97-rearch-ab-gate` | **37 / 24** | This session's subject |
| `gh95-thin-python-arms` | 56 / 1 | Only 7.6, owner sign-off. Still carries the `:618` defect (§6) |
| `gh93`, `gh94`, `gh96` | archived | — |

`ape` side, re-derive before citing: `rearch-04` 75/3 (9.1, 9.2 delegated to `gh97` 7.2b; 12.4 its own
archive), `rearch-06` 25/4, `rearch-07` 50/1.

### The artifacts are ready to launch against

- Jar built and deployed: sha256 `a7eddf5a776ce20f7299911d7d9acb3a0f1342cdc1512b3e28aa00488e582a94`,
  from `rearch` commit `9e948102`, **stamped `9e948102`** (not master's `c638142`).
- Image built, **not pushed**: `phtcosta/rvandroid:0.9.3-rearch`, ID
  `sha256:2cc5c3aada3dd741434d78bfb38da4dd87cded80d05ab7967bbbe725e61472d7`, label
  `rvsec.branch=rearch-counterparts`, clone verified inside the image at `19ae3da1`.
- Leg A's tags **unmoved**: `0.9.3` and `latest` both still `sha256:b2904fdf…aedec`.
- Branch pushed: `rearch-counterparts` at `19ae3da1` when the image was built; there are **12 more
  commits since** (§7) that are **not** in the image and do not need to be — they are artifacts,
  campaign scaffold and docs, not harness code. **Verify this claim before launching**; if any commit
  after `19ae3da1` touched `modules/`, the image must be rebuilt and pushed again.
- Campaign compose: **10 containers**, `filters10/`, no `sglang` service (joins the external network),
  jar bind-mount present on all ten.

---

## 2. What to do next, in order

1. **Re-derive §1** in both repos and `git status --porcelain` in both.
2. **Verify the image is still current** against the branch (see the bullet above). This is the gh71
   failure mode and it is cheap to check:
   `git log --oneline 19ae3da1..HEAD -- rv-android/modules/` — if non-empty, rebuild the image.
3. **Tick group 7** via `openspec-apply-change`, with prose recording what each task found. The
   evidence is in §3; re-measure rather than copying the numbers.
4. **7.4 — write the pre-flight report and the `PREFLIGHT` journal entry.** The report is a task
   deliverable (so `Write` is allowed) and it SHALL carry 7.2a's checks named as the `ape` side's
   delegated device verification, plus 7.2b's observations marked recorded-not-gating.
5. **7.2b — append the per-arm heartbeat counts** to
   `openspec/changes/archive/2026-08-05-gh94-ndjson-trace-reader/heartbeat-evidence.md` (the
   **archived** path; the task text was corrected to it this session). Grep each arm's logcat for
   `ApeRvHb`, compare against that run's `StepRecord` count. **Does not gate.**
6. **ASK THE OWNER FOR THE GO-AHEAD**, then launch group 8.
7. **Group 9** — the four validity gates, then `verify.py`, then `consolidate.py`. No outcome is read
   before 9.1–9.5 pass.
8. **Group 10** — `compare.py`, the result document (whatever it says, including a tie), the
   exploratory list, the merge verdict, the `DECIDE` journal entry, then the four closing skill runs.

---

## 3. The smoke ran and passed — evidence for ticking group 7

Command used (results in `experimento-rearch-aperv/results_smoke/`):

```bash
cd experimento-rearch-aperv
docker compose -f docker-compose.smoke.yml up -d
uv run python scripts/preflight_runstart.py --results results_smoke --manifest manifest.json
```

**Configuration**: 1 container, 3 arms × 2 applications × 1 rep × 300 s = 6 runs, ~37 min wall clock.

**7.1 / 7.3 — pass.** 6/6 identities COMPLETED, `coverage.csv` has 2,852 rows, `cov_method` 22–39 %,
`cov_act` up to 100, **0 `VerifyError`**, MOP violations detected (15 and 6 on `smartpack`).

**7.2 — pass on the three trace-verifiable checks**: 9 PASS · 0 FAIL · 3 SKIP, exit 0. The 3 SKIPs are
`props_digest` and are **by design** — see §5, the task text was corrected this session.

**7.2a — passes on both halves**, per arm, on `com.smartpack.packagemanager_79`:

| Arm | MOP_DATA | wtgEdges | mopActivities | flagged | steps | MOP boosts | `decision_source=MOP` |
|---|---|---|---|---|---|---|---|
| `mop_off_llm_off` (control) | loaded, v1, digest | 23 | 8 | 10 | 303 | **0** | **0** |
| `mop_on_llm_70` | loaded, v1, digest | 23 | 8 | 10 | 108 | 2 | 0 |
| `mop_on_llm_off` (reference) | loaded, v1, digest | 23 | 8 | 10 | 307 | **17** | **15** |

This is the first end-to-end device evidence that the re-architecture works: the stage-4 jar won the
bind-mount and emits NDJSON, `gh96`'s compact artifact loads, and MOP guidance fires on the guided arms
and not on the control.

**7.2b — still owed** (heartbeat counts per arm, sample-trace inventory). Does not gate.

---

## 4. What this session did

Twelve commits on `rvsec` (`5c59d821`…`87fea7fe`) plus `822fc6cf` on `ape-rearch`. Groups 6 and 7 in
substance. **Four real defects were found, none of them anticipated by the task text**, and each is
worth carrying because each would have silently invalidated something:

1. **`RVSEC_BRANCH` (task 6.4).** `docker/rvandroid/Dockerfile` declares `ARG RVSEC_BRANCH=modules` and
   clones `PAMunb/rvsec` at that branch. A plain `docker build` would have produced an image with
   **none** of `gh94`/`gh95`/`gh96`/`gh97` — every arm running the canonical harness while the campaign
   recorded it as the re-architected one. gh71's failure moved up a layer, from the jar to the harness.
   The task now passes `--build-arg RVSEC_BRANCH=rearch-counterparts`.
2. **`docker/rvandroid/build.sh` must never be used.** It runs
   `docker build --no-cache -t $IMAGE:0.9.3 -t $IMAGE:latest`, moving both tags that hold **leg A's
   image identity**. The repository's own build script would have destroyed the comparison's
   provenance in the act of building the artifact to be compared.
3. **Design D10's premise was already false.** D10 said task 6.2 would be the first deployment of a
   worktree-built jar. The jar it displaced (`605b4174…`, 13:49 that day, another session) already
   carried `GIT_SHA = c638142` — master's stamp, the documented defect, deployed. Kept as the physical
   counter-example at `backup/gh97-6.2-superseded/`; the `ape` procedure doc's amendment is dated to
   that deployment, not to 6.2.
4. **The smoke had no vehicle.** Group 4 never built one; the README pointed at a section that did not
   exist. `docker-compose.smoke.yml` was written this session.

Plus **amendment 01** to the frozen pre-registration (§6) and the **check-1 resolution** (§5).

---

## 5. The `props_digest` question — settled, do not reopen without reading this

`preflight_runstart.py` has four checks. Check 1 compares `RUN_START.props_digest` against the SHA-256
of the `ape.properties` the harness pushed. **It reports SKIP and that is now the intended state.**

*It cannot pass.* `_push_properties()` writes to a temp file and `os.unlink`s it after the push, so
the bytes sent are not retained. Reconstruction was attempted through the tool's own code path with
the push intercepted; it did **not** reproduce any of the three echoed digests under any plausible
variation of the inputs. The same reconstruction run **inside the campaign image** produced bytes
identical to the local tree — which rules out harness/image drift and leaves the difference
unexplained. **That loose end is real and is recorded rather than closed.** If someone wants to chase
it: instrument a live run with the push intercepted inside the container.

*It does not need to pass.* From stage 2 onward the jar **aborts before step 1** on an unknown key, a
retired key, or a non-neutral value of an inactive feature. A run that produced a trace has already
passed a stricter check than a digest comparison. What the digest would add over checks 2–4 is
detection of *undeclared* keys, which is exactly what the jar's validation refuses.

*Retaining the file was drafted and withdrawn* on the owner's objection — one `.properties` artifact
per task (the device path is fixed, so per-run naming would be required), added to `aperv-tool` to
feed a redundant check. P1 settles it. The delta-spec requirement was removed **before any code was
touched**, which is the order the workflow requires and which the owner enforced explicitly.

Corrected along the way: `inert` in `RUN_START` lists keys of the **effective plan** at neutral values
for inactive features — it is **not** evidence of what the pushed file contained. An earlier inference
that it was is wrong.

---

## 6. Amendment 01 — the partition, and what it cost

The owner set a target of finishing by **10:00 on 2026-08-06**. Measured need was ~23.2 h against
~18.7 h of budget, so the partition was amended from **8 × 5 to 10 × 4** containers.

**Nothing in the statistical grid moved**: 3 arms, 40 applications, 3 replicas, 1800 s, 360 runs, same
binaries, same LLM dose, same model, same bootstrap seed. Two levers were refused on the record:
fewer replicas is the exact 2026-06-19 failure mode this gate exists to prevent, and a shorter timeout
would have broken comparability outright since leg A was measured at 1800 s.

**What it costs, stated and not absorbed**: the filters are no longer byte-identical to leg A's, so an
application no longer runs at the same container index in both legs and container effects stop
cancelling in the paired difference. The pairing **by application**, which G1/G2/G3 rest on, is
untouched.

**Per-run cycle measured on the smoke**: ~1857 s at 1800 s timeout (1800 + ~12 s flush + ~45 s install
and teardown). 36 runs per container × ~31 min ≈ **18.6 h**.

**Journal chain** in `calibracao/journal.jsonl`, all before any outcome existed:

| State | sha256 | When |
|---|---|---|
| `FREEZE-PREREGISTRO` | `c0ac9a7f…` | 2026-08-04, before the jar existed |
| `APENDICE-PROVENIENCIA` | `a0da2273…` | 2026-08-05 17:43 |
| `FREEZE-PREREGISTRO-EMENDA-01` | `594cf04a…` | 2026-08-05 18:27 |

The pre-registration admits **only** registered amendments with a fresh digest beside the original.
Never edit it silently. Its §11 provenance appendix is filled and its §2 declares the rule.

### Two more things worth carrying

**The GPU already holds leg A's sglang.** 12.6 GiB of 15.47 GiB, four days up, serving
`Qwen/Qwen3-VL-4B-Instruct`. A second instance dies in `torch.OutOfMemoryError` before serving — the
smoke proved it. Both compose files now join the external network `experimento-e3-decisiva_default`,
whose `sglang` alias is the hostname the entrypoint's socat bridge targets. This is better than a
workaround: both legs' LLM arms are now served by the **same backend**, which removes a difference
between legs rather than adding one.

**MOP guidance is inert over most of this corpus.** Deriving the artifact host-side over the 40
`.apk.json` of `subset40`: `flagged > 0` in **8/40**, `wtg > 0` in **15/40**, all three of
`flagged`/`wtg`/`mopActivities` together in only **4/40**. The two most-flagged applications in the
corpus (aegis 50, de.blau 42) have an **empty WTG**. This is a property of the corpus, not of the jar.
It changes nothing about the campaign but governs the *reading*: G3 reports displacement and 36 of 40
applications cannot produce any, and a reader would otherwise take that absence for a null result of
the rewrite. Task 10.3 already names it as a post-freeze observation.

**And the trap that cost a smoke: `cov_mop` does not identify an application that exercises the
guidance.** It comes from the RVSEC logcat markers and does not depend on the guidance artifact at
all, so an application can post `cov_mop` 68 % with an entirely empty MOP artifact. To pick one, derive
the artifact and require the three quantities positive.

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

## 8. Files and commands

```
openspec/changes/gh97-rearch-ab-gate/
  tasks.md proposal.md design.md specs/aperv/spec.md

experimento-rearch-aperv/
  docker-compose.yml            # 10 containers, filters10/, external sglang network
  docker-compose.smoke.yml      # the smoke vehicle written this session
  filters/batch_00..07.txt      # leg A's partition — EVIDENCE, do not touch
  filters10/batch_00..09.txt    # leg B's partition (amendment 01)
  manifest.json                 # expected_sha 9e948102, image.id 2cc5c3aa…, containers 10
  results_smoke/                # the smoke's output (untracked, root-owned — never git add)
  scripts/{preflight_runstart,verify,consolidate,compare,monitor.sh,make_manifest}.py

docs/20260804_preregistro_gate_rearch.md   # FROZEN + appendix + amendment 01
calibracao/journal.jsonl                   # the digest chain
backup/gh97-prechange-jar/                 # 386ce08d… — leg A's jar (never git add)
backup/gh97-6.2-superseded/                # 605b4174…, the master-stamped counter-example
backup/gh97-smoke-descartado/              # the first smoke, on the wrong applications
```

```bash
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

# --- re-derive (openspec must run from HERE, not from the git root) ---
openspec list
openspec validate --all            # clean state is "15 passed, 2 failed"
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

# --- tests (the two flags are the CI contract) ---
uv run pytest modules/aperv-tool/tests --import-mode=importlib -o "addopts=" -q
APE_REPO=/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape-rearch \
  uv run pytest modules/aperv-tool/tests/migration --import-mode=importlib -o "addopts=" -q
# without APE_REPO the whole migration tier skips SILENTLY

# --- the campaign (ONLY after the owner's explicit go-ahead) ---
cd experimento-rearch-aperv
docker compose up -d
bash scripts/monitor.sh          # identity-distinct counts; NEVER grep '"state": "COMPLETED"'
```

Counting rule, learned the hard way in 2026-06-19: identity is
`(apk_name, tool_config.name, tool_config.variant, repetition, timeout)` — note `variant` lives under
**`tool_config`**, not directly in `config`. Grepping `COMPLETED` double-counts through
`result.state_transitions[]`.

---

## 9. What NOT to do

- Do **not** launch the campaign without the owner's explicit go-ahead.
- Do **not** move or reuse the `0.9.3` / `latest` image tags, and do not run `docker/rvandroid/build.sh`.
- Do **not** build the image without `--build-arg RVSEC_BRANCH=rearch-counterparts`.
- Do **not** edit the pre-registration except by a registered amendment with a fresh journal digest.
- Do **not** reduce replicas, timeout or corpus to save wall clock. The owner's standing decision is
  that scope is not cut for a deadline; amendment 01 changed parallelism precisely to avoid it.
- Do **not** re-add the retained-`.properties` artifact (§5).
- Do **not** regenerate `tests/migration/arm_effective_baseline.json`.
- Do **not** read any outcome before gates 9.1–9.5 pass.
- Do **not** touch `experimento-cal/` — historical, and a recorded decision forbids editing it.
- Do **not** `git add` `backup/`, `results/` or `results_smoke/`.
