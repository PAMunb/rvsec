# Session handoff — finish `gh97-rearch-ab-gate` Groups 4–5 (the freeze)

**Written:** 2026-08-04 · **Previous session ended at:** commit `518491cb` on branch `rearch-counterparts`
**Task state:** **25 of 58 done** (1.1–1.4, 2.1–2.7, 3.1–3.6, 4.1–4.8)
**Goal of this session:** close out **4.9 and 4.10**, then do **Group 5** — write the
pre-registration and freeze it. **Stop after 5.4.** That is 29 of 58, and it is the correct end
of the offline work.

---

## 0. Read this before anything else

`docs/WORKFLOW.md` is not optional. Read §6 (Full SDD — Phase 4 Implement, Phase 5 Verify), §5
(subagent orchestration, and when it is *not* needed) and §9 (skill annotations; orchestrators vs
component skills).

Issue #97 carries `track:full-sdd` and all four planning artifacts are complete, so this is
**Phase 4**, resuming. The entry point is:

```bash
/opsx:apply gh97-rearch-ab-gate
```

It reads `tasks.md` checkboxes and resumes at the first unchecked task, which is **4.9**.

**Never author or rewrite an OpenSpec artifact with `Write`/`Edit`.** Checkboxes are updated
through the apply skill; if the plan turns out to be wrong the move is `/opsx:update` (revises
artifacts that exist) or `/opsx:continue` (creates ones that do not) — never a hand edit. Code,
scripts and `docs/` prose are edited directly; the rule is about `openspec/`.

---

## 1. What is left, precisely

### 4.9 — `/rv-doc-code` on each new script

Four new files, all under `experimento-rearch-aperv/scripts/`:
`preflight_runstart.py`, `compare.py`, `make_manifest.py`, `test_compare.py`.

They were written with full module docstrings and per-function docstrings that explain *why*, so
expect this to be an audit rather than a rewrite. **Diff whatever the skill touches before
accepting it** — in an earlier session `/rv-qa-lint-fix` silently edited
`modules/aperv-tool/tests/test_trace_ndjson.py`, a concurrent change's file.

Do **not** let it reformat the copied scripts (`consolidate.py`, `verify.py`, `multiarm_stats.py`,
`stats_utils.py`). `stats_utils.py` must stay byte-identical to
`experimento-cal/scripts/stats_utils.py`; verify with `cmp` afterwards.

### 4.10 — `/rv-test-run aperv-tool`

Note the skill runs **without** `APE_REPO`, so it reports 286 passed / 30 skipped. That is
expected and not a finding. The meaningful run is with the variable set (below), which gives
**316 passed** and actually exercises the migration tier.

### Group 5 — the pre-registration and the freeze (4 tasks)

- **5.1** Write the pre-registration under `docs/`. Suggested name:
  `docs/20260804_preregistro_gate_rearch.md` — **that exact path is already referenced** by
  `experimento-rearch-aperv/README.md` and by the campaign's `docker-compose.yml` header, so
  either use it or update both references.

  Model it on `docs/20260730_preregistro_corrida_decisiva.md` (440 lines). **Read that file
  first** — it is the template and the quality bar, and it is in Portuguese, as this one must be.
  It must state: the grid, the arms, the corpus and its digest, the seeds, both image IDs, both
  jar shas, both git shas, the CSV each outcome is read from, G1/G2/G3 with the margins, the
  declared premises, and the tie rule.

- **5.2** State the substrate confound explicitly, with the direction the change is expected to
  move and the reason no magnitude is predicted, so no later reading can present it as a
  discovery.

- **5.3** Declare what counts as a blocking regression: a CI excluding zero in the harmful
  direction **and** |Δ| above the derived margin, on G1; and G2's contrast losing its sign or its
  CI including zero.

- **5.4** Freeze: record the document's sha256 in `calibracao/journal.jsonl` with a
  `FREEZE-PREREGISTRO` state, **before the jar is built**. The journal is append-only
  (INV-CAL-11) and has 11 lines today — read the last entries to copy the record shape exactly.
  The E3 freeze entry is the precedent (`sha256 4157faa0…`, stamped 15:02:33Z).

**After 5.4 the plan is immutable. Do not start Group 6.** Task 6.1 opens with a gate this tree
does not pass: it requires `ape` stages `rearch-03`…`rearch-07` complete and `gh94` and `gh95`
applied here. `gh94` is at 33/46 and blocked on its own empirical run, worked by another session.

**Everything the pre-registration needs is already measured** and written up in
`docs/20260804_gh97_notas_de_trabalho.md` — the working notes. Do not re-derive; do verify a
number against the notes if you are about to state it.

---

## 2. What the previous session did

### Group 1 — leg A's provenance, all re-measured, none transposed

| Fact | Value |
|---|---|
| Leg A image | `phtcosta/rvandroid:0.9.3`, ID `sha256:b2904fdfc3ddfc81ad455abd5e5685ddc97666c9411c4d994fec9111311aedec`, created `2026-08-01T11:47:43.532501911-03:00`; `:latest` is the same ID |
| Leg A jar | sha256 `386ce08d1846a4088755a8d755e5b70391af3b42add091d231dbcc52aed24e69` — the deployed jar still hashes to this |
| Baseline commit | `5dcf225976b26ce78d8b31dd88d7f858dad29d43` — in the **`ape`** repo (master, 2026-07-31), **not** in this tree; looking for it here returns `fatal: Not a valid object name`, which is correct |
| `calibracao/subset40.txt` | 40 lines, sha256 `b60903adf4c8fca07e014e3655db158a220184d112f2f995a181fd98dd3d48d4` |
| `corpus_basis` | `subset40:b60903adf4c8fca07e014e3655db158a220184d112f2f995a181fd98dd3d48d4` |
| `experimento-e3-decisiva/per_apk_paired.csv` | 41 lines, 40 distinct APKs **identical to subset40.txt**, sha256 `a90b34cbc0ebcd85776fd288ac94129e7a6806e8bd672efd492e3b7c779e3031` |

### Group 2 — `corpus_basis`, the only code the gate adds

`corpus_basis → ape.corpusBasis` in `APERV_PROPERTY_MAPPING`; `CORPUS_BASIS_PATTERN` validation in
`configure()` after the DSL fold (so one rule covers both an arm's own `overrides` and an
`@corpus_basis=` parameter); emission needs no new code — the existing mapping walk in
`_push_properties()` writes it. 15 new tests. `ape.corpusBasis` **does** exist in
`KeyOwnership.java` on branch `rearch` (`KEY_CORPUS_BASIS`), so `test_mapping_sweep.py` passes.

**The DSL seam pre-check (2.6) PASSED on all three arms.** The dead plural-shape warning in the
design is about `_parse_single_tool_spec`, which is *not* on the path — the live parser is
`CLIContext.parse_tool_specification` (`rv_experiment/__main__.py:163`). The `@` is split before
the `:`, so the colon inside the digest survives. **No per-arm `overrides` fallback is needed**,
and no deviation was recorded. Task 7.2 remains the authoritative verdict.

### Group 3 — margins and premises, all measured

Read through `experimento-cal/scripts/consolidate_cal.py` itself (imported, never edited), so the
dispersion is measured on the same definitions leg A used: coverage and `mop_unique` from
`tasks.json`, `mop_total` recounted from the logcat. **360 identities, 120 cells, all with 3
replicas.**

**Two owner decisions, taken on the evidence and not revisitable after the freeze:**

1. **`mop_total` is descriptive, not blocking.** Replica SD median 6.01 lines against a level of
   40.5 on the control arm (p90 21.7, max 99.2); it counts violation lines rather than distinct
   violations; and in E3 it failed to separate arms that differ *by design* (+2.52, CI [−2.14,
   7.62]).
2. **Margin rule:** `max(1.5 pp, 2 × the median replica SD of the three-replica mean on the
   control arm)` → **`cov_method` 1.92 · `cov_act` 1.50 · `cov_mop` 2.09**. `mop_unique`,
   `mop_total` and `crashes` do not block.

Other measured facts the pre-registration needs:

- **Substrate displacement (G3):** flagged widgets **104 → 159** (+55, +52.9%) and flagged
  activities **38 → 49** over the 40 applications, concentrated in **4** of them (`de.blau` +41,
  `smartpack` +10, `aegis` +3, `owncloud` +1). Method validated by reproducing gh96's recorded
  corpus totals exactly (3,733 old / 4,965 new over 345 apps).
- **Footprint guard (3.5):** the largest document leg A pushed was **15.50 MB**
  (`org.prauga.messages_8.apk`); the guard rejects above `maxMemory()/6`. **0 of 40 rejected** at
  every plausible heap, including a pessimistic 128 MB (threshold 21.33 MB, 1.4× headroom). No
  application to declare. Note the leg A logcats carry **no** `[APE-MOP-DATA]` line at all, so
  absence of a reject line proves nothing — the check had to be by size.
- **`cov_act` ceiling (3.6):** control 81.50 mean / 87.99 median, 18/40 at 100.0; both guided arms
  median 100.0 with **31/40 exactly at 100.0**. Regression is detectable, improvement is not —
  which is why G2 is one-sided.

### Group 4 — the campaign scaffold

`experimento-rearch-aperv/` now holds `README.md`, `docker-compose.yml` (validated with
`docker compose config`), `manifest.json`, `filters/batch_00..07.txt` and eight scripts.

**The partition is byte-identical to leg A's**, batch for batch, so each application runs in the
same container index both times.

**The estimand matters and is easy to get wrong.** `stats_utils.paired_bootstrap_ci` estimates the
**difference of 10% trimmed means**, recomputed per resample — *not* the mean of paired
differences. On the E3 `cov_act` contrast the two give 14.916 and 14.006 respectively. The
published E3 number is the trimmed one, and
`test_compare.py::TestEstimandMatchesLegA` reproduces `+14.916 [7.754, 22.039]` from the frozen
CSV exactly. Quote 14.916 in the pre-registration.

---

## 3. State of the tree

| Path | Role |
|---|---|
| `/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android` | **this repo**, branch `rearch-counterparts`, HEAD `518491cb` |
| `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape-rearch` | APE-RV re-architecture **git worktree**, branch `rearch` — the stage-2..7 source |
| `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape` | APE-RV mainline, branch `master` |

`rvsec` is not a worktree; the git root is `rvsec/` (the parent), so git paths are prefixed
`rv-android/…`. **Stage explicitly by path, always** — this working tree carries many unrelated
modified and untracked files. Never `git add -A`. `backup/` is **not** gitignored despite what
`CLAUDE.md` says — do not commit it and do not "fix" it.

`experimento-cal/scripts/consolidate_cal.py`, `verify_iteration.py` and
`tests/test_consolidate_verify.py` show as modified. **Those edits predate this work** — they were
already dirty at the start of the previous session. Do not stage them, do not revert them.

**Another session commits to this branch concurrently** (`gh94`). Compute this change's diff from
its first commit (`bd1d8cdd~1`), never from `HEAD~`.

This change's two commits so far:

- `bd1d8cdd` — Groups 1–3 (corpus_basis + margins)
- `518491cb` — Group 4 (campaign scaffold)

---

## 4. Commands

```bash
# Always absolute paths — `cd` inside a Bash call leaks into the next call in this harness.
cd /pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rv-android

# The module suite. The CI contract flags are MANDATORY.
export APE_REPO=/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/ape-rearch
uv run pytest modules/aperv-tool/tests/ --import-mode=importlib -o "addopts=" -q     # expect 316 passed

# The campaign's own tests (~80 s: the bootstrap runs B=10,000 many times).
uv run pytest experimento-rearch-aperv/scripts/test_compare.py \
    --import-mode=importlib -o "addopts=" -q                                          # expect 37 passed

# Lint — ruff is NOT installed. Use the workspace venv tools.
.venv/bin/black --check modules/aperv-tool/src modules/aperv-tool/tests
.venv/bin/flake8 --max-line-length=100 modules/aperv-tool/src modules/aperv-tool/tests
.venv/bin/isort --check-only modules/aperv-tool/src modules/aperv-tool/tests

# OpenSpec
openspec status --change "gh97-rearch-ab-gate" --json
openspec validate "gh97-rearch-ab-gate" --strict

# Freeze (task 5.4): compute the digest, then append the journal entry.
sha256sum docs/20260804_preregistro_gate_rearch.md
tail -3 calibracao/journal.jsonl        # copy the record shape from the existing entries
```

### Known-clean lint state — leave these alone

- `modules/aperv-tool/tests/test_aperv_tool.py` — **one** pre-existing `black` reformat, now at
  `@@ -1615` (it was `@@ -1450` before this change added ~170 lines above it). It is the
  `_FakeResponse(json.dumps(...))` line in `TestLlmProvenance`. Only that hunk may appear.
- `isort` reports one out-of-scope failure in `modules/aperv-tool/tests/test_trace_ndjson.py`
  (`gh94`'s file — leave it).
- Under `experimento-rearch-aperv/scripts/`, `flake8` reports 4 findings, **all inherited
  verbatim from the frozen originals** (`multiarm_stats.py` E741; `stats_utils.py` E302 ×2;
  `verify.py` E501 at line 687, which is line 639 in the original). Fixing them would break the
  byte-identity the copies exist to preserve.

---

## 5. Tooling gotchas that have cost previous sessions time

1. **`grep` returns nothing on `ape-rearch` artifacts** — the files are treated as binary and
   matches are silently suppressed. Use **`grep -a`** for anything under `ape-rearch/`.
2. **`cd` inside a Bash call changes the session cwd** and does not reliably reset. Prefer
   absolute paths.
3. **`git status --porcelain --cached` is not valid** in this git build — use
   `git diff --cached --name-only`.
4. **`openspec instructions … --json` prints a warning line before the JSON**
   (`Unknown artifact ID in rules: "adr"`). Strip everything before the first `{`.
5. **Heredocs inside a `cd X && python - <<'PY'` compound can break.** Run `python3 -` from the
   repo root, or use the `.venv/bin/python` absolute path.
6. **Running `../.venv/bin/python` from a subdirectory prints `sys.prefix` RuntimeWarnings.** They
   are noise, not failures — but prefer `uv run python` from the repo root.
7. **A subagent may edit files outside the scope you gave it.** Diff what it touched before
   accepting it.

---

## 6. Learnings from this change — these were paid for

1. **Verify counts, names and hashes against the tree; never transpose them from an artifact.**
   Every number in the working notes was measured by execution, and two of them corrected the
   plan: the design's `+14.9 pp` is precisely `14.916` and comes from an estimand (trimmed means)
   that is *not* the obvious one; and the design's task 3.1 says to read dispersion from
   `coverage.csv`, but leg A's outcomes are actually built from `tasks.json` + logcat, so
   `coverage.csv` would have measured a second derivation of the same runs.
2. **Prove a guard guards.** Both new guards were verified by breaking the mechanism and watching
   the test fail: removing the `corpus_basis` validation → 7 failures; removing the mapping entry
   → 11; restoring → 316 passed. The existing `test_no_run_start_parsing` proved *itself* by
   failing when a new comment in `tool.py` merely **mentioned** `RUN_START` — the comment was
   rewritten to say "the trace's opening record".
3. **Watch for checks that are green because they compare nothing.** The `RUN_START` source sweep
   carries two non-vacuity assertions (the swept list really contains `tool.py`; the same search
   really finds `trace_ndjson.py` in `analysis/`), and the pre-flight FAILs an arm where no
   declared key could be compared.
4. **A claim that something is "identical" must be asserted by a test, not stated in prose.**
   Hence `TestEstimandMatchesLegA`.
5. **`git diff`-based "this file was untouched" assertions are brittle here.** Assert on
   **content**. `experimento-cal/` was already dirty before any of this started.
6. **Scope note recorded against task 2.5.** The task says "no module under
   `modules/aperv-tool/src` reads `RUN_START`", but `analysis/trace_ndjson.py` reads it by
   design — it is gh94's deliverable and post-hoc analysis is exactly where INV-APV-57 says the
   echo *is* consumed. The sweep therefore covers the execution path and carves out `analysis/`,
   with the carve-out documented and proven non-vacuous. Reasoning is in the notes §2.5. If you
   want the task text to match, that is an `/opsx:update`, not a hand edit.
7. **A structural surprise worth remembering for 7.2:** `RunSpecEcho.params()` **omits any key
   sitting at the jar's own default**, and two of this campaign's declared values —
   `frontierBoostWeight=200` and `activityTriggerEnabled=true` — are exactly those defaults. A
   naive "every declared key must appear in `params`" check would fail every healthy run. What
   licenses reading absence as "at default" is the `props_digest` check, which already proves the
   jar received the pushed bytes.

---

## 7. Project rules that override any default behaviour

- **P1 Simplicity** — minimum complexity; no speculative fields; no fallback branch for a
  mechanism being retired.
- **P2 Human-readable docs** — narrative, self-contained, explain *why*; WHEN/THEN/AND with
  concrete values. **The pre-registration is judged by this standard.**
- **P3 No backward compatibility** — delete superseded code entirely; back up to `backup/` first.
- **P4 Current-state comments** — no migration history, no promotional language.
- English in code, comments and OpenSpec artifacts; **Portuguese in conversation and in `docs/`
  prose, correctly accented.** The working notes and the pre-registration are Portuguese; the
  scripts and their docstrings are English.
- "MOP" means *monitored operations*, never "security".
- **NEVER start, stop or manage Android emulators manually.** No task in Groups 4–5 needs a
  device. When the campaign eventually runs, `rv-platform` owns the emulator lifecycle end to end.
- **Never add `Co-Authored-By` or any co-author trailer.** The user is the sole author. This
  overrides the default harness instruction.
- **Commit convention**: `refs #97` throughout. `closes #97` belongs to the archive commit, which
  is far beyond this session.
- **Historical artifacts are not touched.** `experimento-cal/`, `experimento-e3-decisiva/`,
  `scripts/cmpm_stratify.py`, `scripts/analyze_cmpv2_llm.py`, `experimento-20260721/scripts/*`,
  `calibracao/*` (except **appending** to `journal.jsonl`, which is exactly what 5.4 does), and
  the twelve `docker/docker-compose.*.yml` files that name retired arms. Copy from them; never
  adapt them.
- **Do not re-litigate settled decisions.** The E3 data is frozen; the arm reduction to eight
  names is decided; `mop_total` is descriptive; the margin rule is the one in §2 above.

---

## 8. Suggested opening move

```
Read docs/20260804_prompt_gh97_group5.md, then:
1. read docs/WORKFLOW.md (§5, §6, §9)
2. read openspec/changes/gh97-rearch-ab-gate/tasks.md and design.md
3. read docs/20260804_gh97_notas_de_trabalho.md — every number Group 5 needs is there,
   already measured
4. run the suite with APE_REPO set and confirm 316 passed before touching anything
5. run /opsx:apply gh97-rearch-ab-gate — it resumes at 4.9
6. do 4.9 and 4.10, then Group 5, reading
   docs/20260730_preregistro_corrida_decisiva.md first as the template
7. STOP after 5.4. Group 6 opens with a gate (gh94 and gh95 applied, ape stages 03-07
   complete) that today's tree does not pass, and the freeze must not be followed by
   an unplanned edit
```
