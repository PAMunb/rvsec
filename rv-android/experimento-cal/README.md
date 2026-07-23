# experimento-cal — calibration control scaffold

Control scaffold for the APE-RV LLM calibration campaign (`gh88-cal-llm-control`).
Planning sources: `docs/20260721_plano_calibracao_llm.md` (rev. 3.2) and
`docs/20260721_metodologia_calibracao_loop.md`; capability spec
`openspec/changes/gh88-cal-llm-control/specs/calibration-control/spec.md`.

The campaign chooses the LLM configuration of the `aperv` LLM arm (prompt variant,
sampling parameters, routing regime) across three experiment phases — A (`cala`),
B (`calb`), C (`calc`) — each phase being one or more **iterations** of an eight-state
loop. This scaffold makes every state of that loop a deterministic, auditable
computation: one CLI script per state. It does **not** run experiments and does **not**
walk the state machine itself — transitions are agent-driven, gated by four fixed human
gates (G1–G4). The scaffold only generates, audits, gates, consolidates, verifies, and
analyzes.

## The loop

```
CONFIG-GEN → PRE-FLIGHT → SMOKE → RUN+MONITOR → CONSOLIDATE → VERIFY → ANALYZE → DECIDE
     ↑                                                                            |
     └───────────────── next iteration (or terminal state) ←──────────────────────┘
```

Two of the states are **independent verifiers** (PRE-FLIGHT and VERIFY): by invariant
INV-CAL-04 they share no code path with the producer they check (an agent re-running the
producer's own script is not independence). PRE-FLIGHT re-derives the manifest from
`get_variants()` with its own parser; VERIFY re-greps the raw logcats/traces itself.

## Tracking — "where are we / what runs next?"

Because there is no daemon, any session must be able to pick up the campaign mid-flight.
`status.py` answers that without reconstructing anything by hand — it **derives** the
position (INV-CAL-14) from the transition journal + the `iterN/` artifacts + the phase
configs (never a hand-maintained checklist, which would drift):

```
python3 scripts/status.py            # reads calibracao/journal.jsonl + iter*/ + phases/
```

For each iteration it prints the eight states as done / current / pending, the pending
human gate (G1–G4), the next action (the script to run), and a cross-iteration summary
(phase + DECIDE verdict). It also flags any journal↔artifact inconsistency (a state
journaled without its artifact, or an artifact present without a journal record) so the
agent reconciles it. `status.py` is read-only. After each state completes, record the
transition with `journal.py append` — that append is exactly what keeps `status.py`
truthful for the next session.

## Directory layout

```
experimento-cal/
  phases/<phase>.json      versioned phase inputs (arm list, subset file, reps, timeout,
                           containers, smoke subset, seeds); plan §6 maps 1:1 to cala.json
  scripts/                 one CLI per loop state (+ vendored stats)
  templates/decision.md    DECIDE template the agent instantiates as iterN/decision.md
  tests/                   pytest fixtures + unit tests for the scripts
  iterN/                   per-iteration tree, GENERATED (append-only; never hand-edit)
../calibracao/             campaign-level, outlives iterations:
                           journal.jsonl, <phase>_decision.md, subset40.txt/subset90.txt
```

`iterN/` (produced by CONFIG-GEN): `manifest.json` (the iteration contract),
`artifacts/` (byte snapshots + sha256 of `tool.py`, plus `ape-rv.jar` in Phase B),
`docker-compose.<phase>.yml`, `docker-compose.smoke.yml`, `filters/batch_NN.txt` +
`filters/smoke_NN.txt`, and `results/` (written by the containers at run time).

`calibracao/subset40.txt` (and `subset90.txt` for Phase C) is produced **offline in
Fase 0** (stratified subset selection) and is **not part of this change**. `phases/cala.json`
references it by path; CONFIG-GEN hard-fails until that file lands. Tests use fixture
subsets instead (`tests/conftest.py`).

## Fixed facts (do not drift)

- **Image**: `phtcosta/rvandroid:0.9.3`, ID `87744cd58be9`. All iterations run on this
  one image (INV-CAL-03). Configuration differences enter **only** via `:ro` bind-mounts
  of the per-iteration snapshot artifacts — never a rebuild, never a tag reuse resolving
  to a different ID. PRE-FLIGHT verifies the resolved ID against the manifest.
- **Arms (11)**: ANC1 = `ape:default`, ANC2 = `aperv:sata_mop_act_frontier`,
  A1..A9 = `aperv:cal_a1`..`aperv:cal_a9`. Every arm is a **named variant** resolved from
  `ApeRVTool.get_variants()` — the single source of truth. `@override` is never used to
  distinguish arms (INV-CAL-05: identity strips the `@` suffix, so override-only arms
  collide and are silently skipped on resume).
- **Vendored stats**: `scripts/stats_utils.py` is copied **verbatim** (with a provenance
  header naming the upstream commit) from `../../rvsec-calibracao/scripts/stats_utils.py`.
  `scripts/multiarm_stats.py` imports it locally, from the same directory — no `sys.path`
  insert, no env var, no sibling-repo path at runtime (reproducibility, NFR08). The sibling
  repo is a copy-source at implementation time only.

## Operating procedure — one iteration, state by state

Each state is one script. Run from the repo root. Every script prints a proposed
**journal line**; after the human-visible gate summary, append it with `journal.py` so the
transition is recorded (design decision 8 — journal appends are explicit, auditable actions).

### 1. CONFIG-GEN — `gen_iteration.py`

```
uv run experimento-cal/scripts/gen_iteration.py --phase experimento-cal/phases/cala.json --iter N [--jar PATH]
```
Flags: `--phase` (path to the phase JSON), `--iter N` (iteration number), `--jar PATH`
(optional `ape-rv.jar` to snapshot — Phase B only), `--iter-root` (default
`experimento-cal/`). Resolves each arm's full key dict from `get_variants()`, computes
each arm's expected `[APE-LLM-CONFIG]` fields, snapshots `tool.py` (and the jar) into
`iterN/artifacts/` recording sha256, records `git describe --dirty` of the worktrees, and
emits the run compose (shared `sglang` + N `rvandroid` containers with per-container arm-order
rotation), the smoke compose (90s, 1 rep, 4 APKs, extreme arms), and per-container filters.
Refuses to overwrite an existing `iterN/` (exit 2 — iterations are append-only, INV-CAL-12).

### 2. PRE-FLIGHT — `preflight.py` (independent verifier, gate of G3)

```
uv run experimento-cal/scripts/preflight.py --iter-dir experimento-cal/iterN
```
Independently audits the generated iteration (does **not** import `gen_iteration.py`,
INV-CAL-04): every manifest arm exists in `get_variants()` and matches field-by-field; the
composes' `RV_TOOLS`/timeouts/reps/image/bind-mounts match the manifest; ≥11 distinct
`(tool, variant)` pairs and `arms × |subset| × reps` predicted identities; the sha256 of
every `iterN/artifacts/` file equals the manifest hash; the image tag AND ID are pinned
(INV-CAL-03); the `sglang` service is present with the expected model. Lists each check
PASS/FAIL; **exit 1 on any FAIL**. Remediation for a hash mismatch is to regenerate a new
iteration, never to re-snapshot in place.

### 3. SMOKE — `smoke_check.py` (after `docker compose -f iterN/docker-compose.smoke.yml up`)

```
uv run experimento-cal/scripts/smoke_check.py --iter-dir experimento-cal/iterN
```
Evaluates the completed smoke run (4 APKs × extreme arms, 90s, 1 rep). Per smoke task:
`[APE-LLM-CONFIG]` == manifest field-by-field; `[APE-LLM-CONFIG-ACK] server_model` ==
expected served model; identity COMPLETED with coverage > 0; 0 `VerifyError` in the logcat.
Any mismatch **aborts the iteration** with a report — the scaffold NEVER self-adjusts
configuration; the fix is a human decision. Exit 1 on any mismatch.

### 4. RUN+MONITOR — `monitor.sh` (after `docker compose -f iterN/docker-compose.<phase>.yml up -d`)

```
experimento-cal/scripts/monitor.sh experimento-cal/iterN [--no-resume]
```
Reports progress as identity-distinct non-empty logcats per container (INV-CAL-07 — never
`COMPLETED` string counts). `docker restart`s only containers that exited with code 137
(OOM; standing authorization, INV-CAL-06). Any other exit code, or no progress since the
previous cadence, is **reported only** for a human decision. ERROR/FAILED tasks are
recovered by a resume pass (`docker compose up -d` re-entry — the platform skips COMPLETED
identities and re-runs failed ones). Experiment configuration is NEVER altered mid-run.

### 5. CONSOLIDATE — `consolidate_cal.py`

```
uv run experimento-cal/scripts/consolidate_cal.py --iter-dir experimento-cal/iterN
```
Builds `iterN/per_apk_paired.csv` (one row per APK, one column group per arm — coverage
metrics + MOP counts, reps averaged) and `iterN/tel_proxies.csv` (per arm×APK×rep LLM
telemetry: calls, `time_ms`, tokens, matched/`llm_tap`/`no_match`-by-reason, mode
distribution) by parsing **raw logcats and `.trace` files**, dedup by identity (INV-CAL-08,
anti-gh58 — never trusts per-task CSV fields a resume may have zeroed). May reuse the
d90c1f4 trace grammar (independence binds VERIFY, not CONSOLIDATE).

### 6. VERIFY — `verify_iteration.py` (independent verifier)

```
uv run experimento-cal/scripts/verify_iteration.py --iter-dir experimento-cal/iterN [--sample 10 --seed 42]
```
Re-derives the consolidated counts by an **independent code path** (does **not** import
`consolidate_cal.py`/`consolidate_compare.py`/`analyze_cmpv2_llm.py`, INV-CAL-04): direct
`RVSEC-COV`/`RVSEC` extraction from raw logcats and `[APE-LLM-CONFIG]`/`[APE-LLM-CONFIG-ACK]`
from traces, aggregated per identity by its own logic. Applies the fixed numeric gates
(INV-CAL-09): config-ack == manifest in 100% of LLM tasks; 0 identity collisions; paired
completeness 100% (an APK missing in ≥1 arm is excluded with a written record); per-arm
median `time_ms` ≤ 2× the global median (else the arm is flagged, `time_ms` becomes a
covariate note); re-derivation divergence 0 on integer counts and ≤ 0.01pp on percentages;
plus a seeded ≥10-task hand-count sample compared cell-by-cell with the CSV. Verdict:
`admissible` or `quarantine` (with the excluded metric/arm named).

### 7. ANALYZE — `analyze_iteration.py`

```
uv run experimento-cal/scripts/analyze_iteration.py --iter-dir experimento-cal/iterN
```
Produces `iterN/analysis.md` applying the gates in the pre-declared order (INV-CAL-10):
(1) proxy elimination → (2) trimmed-mean 10% + paired bootstrap B≥10,000 fixed-seed CIs vs
both anchors (raw mean always reported alongside) → (3) mechanistic prediction-vs-observed
(Δactions/task × +46%/action; prediction outside the observed CI95 → flagged "mechanism not
understood"; temperature arms exempt) → (4) between-reps determinism. Statistics via
`multiarm_stats.py` (Friedman+Holm descriptive, rank-biserial) on the vendored
`stats_utils.py`. **Screening SELECTS candidates and NEVER concludes** — no victory
declaration by a screening p-value.

### 8. DECIDE — `templates/decision.md` + `journal.py`

The agent instantiates `templates/decision.md` as `iterN/decision.md`, applying the
declarative per-phase rules: **SCREENING** (Phase A/B) promotes the top 2–3 arms that pass
ALL gates and records the next-iteration config (never concludes on a screening p-value);
**CONFIRMATION** (Phase C) applies the pre-registered GO/NO-GO/INCONCLUSIVE criteria and
STOPS. Then record the transition:
```
uv run experimento-cal/scripts/journal.py append --state DECIDE --iter N --artifact experimento-cal/iterN/decision.md
```

### journal.py (every state)

```
uv run experimento-cal/scripts/journal.py append --state STATE --iter N --artifact PATH [--journal PATH]
```
Appends one JSON line `{ts, iter, state, artifact, sha256}` to `calibracao/journal.jsonl`
(created on first use). Append-only (INV-CAL-11): existing lines are never rewritten, so any
figure cited later traces back through the journal + `iterN/` snapshots to a raw logcat.

## The four human gates (fixed, non-negotiable)

- **G1** — approval of the plan + iteration budget before the loop starts.
- **G2** — any change to the `ape` repository (Phase-B jar changes J1–J4): the scaffold at
  most PROPOSES a diff/spec; it never commits there.
- **G3** — launch of each experiment (`compose up` of a full run): the scaffold prepares
  and asks for go. If the user grants a standing launch authorization, G3 collapses into G1.
- **G4** — ratification of the final Phase-C verdict and the config of the final 181 experiment.

## NEVER (the scaffold's hard prohibitions)

- **No emulator management** — rv-platform owns the entire emulator lifecycle. The scaffold
  never starts/stops/kills an emulator (INV-CAL-13).
- **No mid-run config change** — configuration is NEVER altered during a run (INV-CAL-06);
  a smoke/verify mismatch is reported for a human decision, never self-adjusted.
- **No `ape`-repo edits** — the scaffold does not modify the `ape` repository (gate G2).
- **No touching `backup/`** — exclude it from tools; never modify files there.
- **No `@override` arms** — arms are named variants only (INV-CAL-05).
- **No hand-editing generated files** — composes/filters/manifest are regenerated, never
  patched in place (INV-CAL-01); a discarded iteration keeps its directory as provenance
  (INV-CAL-12).
- **No victory by screening p-value** — screening selects; only Phase C confirms (INV-CAL-10).
- **No image bump / tag reuse** — the pinned `phtcosta/rvandroid:0.9.3` (`87744cd58be9`) is
  the only substrate (INV-CAL-03).

## Tests

```
uv run pytest experimento-cal/tests --import-mode=importlib -o "addopts="
```
The CI flags are mandatory (conftest isolation across modules). `tests/conftest.py` puts
`scripts/` on `sys.path` so the state scripts import as top-level modules, and provides
fixture subset + phase configs so the scripts are testable without containers, an emulator,
or a real subset file.
