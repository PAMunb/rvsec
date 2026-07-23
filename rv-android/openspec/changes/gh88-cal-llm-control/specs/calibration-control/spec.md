# Capability: calibration-control

## Purpose

`calibration-control` is the control scaffold for the APE-RV LLM calibration campaign (planning docs `docs/20260721_plano_calibracao_llm.md` rev. 3.2 and `docs/20260721_metodologia_calibracao_loop.md`). The campaign selects the LLM configuration (prompt variant, sampling parameters, routing regime) of the `aperv` LLM arm through three experiment phases (A `cala`, B `calb`, C `calc`), each phase being one or more *iterations* of the loop CONFIG-GEN → PRE-FLIGHT → SMOKE → RUN+MONITOR → CONSOLIDATE → VERIFY → ANALYZE → DECIDE.

The capability's job is to make every state of that loop a deterministic, auditable computation. Each state is one CLI script under `experimento-cal/scripts/`; state transitions are driven by an agent following the methodology, with four fixed human gates (G1 plan/budget, G2 any `ape`-repo change, G3 each launch, G4 final verdict). The scripts never launch experiments themselves — they generate, audit, gate, consolidate, verify, and analyze. The two verifier states (PRE-FLIGHT and VERIFY) are *independent by code path*: they re-derive every number they check with their own logic, because an agent re-running the producer's script is not independence.

The scaffold exists to prevent three failure classes that previous campaigns hit: (1) hand-assembled configuration drift (arms whose deployed config silently differs from the intended config — countered by manifest-driven generation plus field-by-field `[APE-LLM-CONFIG]` auditing); (2) resume/identity corruption (override-only arms colliding on the `(apk, tool, variant, rep, timeout)` identity; CSV zeroing on resume — countered by named-variant arms and consolidation from raw logcats, the anti-gh58 rule); (3) unreproducible provenance (results that cannot be traced to a config and artifact hash — countered by per-iteration snapshots and the append-only journal).

Directory layout: `experimento-cal/` holds the scripts, phase configs (`phases/<phase>.json`) and generated per-iteration trees (`iterN/`); `calibracao/` holds campaign-level artifacts that outlive iterations (`journal.jsonl`, phase decision documents, subset files produced offline by Fase 0). All experiment execution runs on the fixed Docker image `phtcosta/rvandroid:0.9.3` (`87744cd58be9`); configuration differences enter exclusively via `:ro` bind-mounts of snapshot artifacts.

## Data Contracts

### Input
- `phases/<phase>.json` — phase definition: arm list (tool + variant names), subset file path, reps, timeout, container count, smoke arm subset, seeds.
- `ApeRVTool.get_variants()` — single source of truth for arm key dicts (`modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py`).
- Worktree `tool.py` (Phase A) and locally built `ape-rv.jar` (Phase B) — snapshot sources.
- `iterN/results/` — raw experiment outputs (logcats, `tasks.json`, `.trace` files) produced by the containers.
- `experimento-cal/scripts/stats_utils.py` — statistical primitives vendored (copied verbatim, provenance header) from `rvsec-calibracao/scripts/stats_utils.py` at implementation time; imported locally, never from the sibling repo at runtime.

### Output
- `iterN/manifest.json` — the iteration contract: image ID, per-arm resolved key dicts, expected `[APE-LLM-CONFIG]` fields, predicted identity count, artifact sha256 hashes, `git describe --dirty` of source worktrees.
- `iterN/artifacts/` — byte snapshots of `tool.py` (and `ape-rv.jar` in Phase B) that composes bind-mount.
- `iterN/docker-compose.<phase>.yml`, `iterN/docker-compose.smoke.yml`, `iterN/filters/` — generated deployment files.
- `iterN/per_apk_paired.csv`, `iterN/tel_proxies.csv` — consolidated outcomes and LLM telemetry proxies.
- `iterN/analysis.md`, `iterN/decision.md` — gated analysis and the phase decision record.
- `calibracao/journal.jsonl` — append-only provenance journal.

### Side-Effects
- **[Docker]**: `monitor.sh` restarts containers with exit code 137 (standing authorization); no other container mutation.
- **[Filesystem]**: scripts write only inside `experimento-cal/iterN/` and `calibracao/`.

### Error
- `SystemExit(1)` — any gate script (preflight, smoke, verify) on gate failure; the report names every failed check.
- `SystemExit(2)` — usage errors (missing phase config, unknown variant, existing `iterN/`).

## Invariants

- **INV-CAL-01**: Composes and filters SHALL be generated from `iterN/manifest.json`, which SHALL itself be resolved from `ApeRVTool.get_variants()`. Hand-editing generated files is prohibited; any manifest×compose divergence is a PRE-FLIGHT FAIL that MUST be fixed by regenerating the iteration.
- **INV-CAL-02**: Every bind-mounted artifact SHALL be sourced from `iterN/artifacts/` (never from a worktree path), and its sha256 SHALL be recorded in the manifest at generation time and re-verified by PRE-FLIGHT.
- **INV-CAL-03**: All iterations SHALL run on the fixed image `phtcosta/rvandroid:0.9.3`. The compose pins the image by **tag**; the image is additionally identified by ID `87744cd58be9`, which PRE-FLIGHT SHALL verify against the resolved image (`docker inspect` / `docker images --no-trunc`), since a 12-char image ID cannot be pinned in a compose `image:` field. No version bump, no tag reuse resolving to a different ID. PRE-FLIGHT SHALL fail on any other image tag, or when the resolved ID does not match the manifest.
- **INV-CAL-04**: `preflight.py` SHALL NOT import `gen_iteration.py`; `verify_iteration.py` SHALL NOT import `consolidate_cal.py`, `consolidate_compare.py`, or `analyze_cmpv2_llm.py`. Verification is independent at the code-path level.
- **INV-CAL-05**: Every arm SHALL be a named variant (or the `ape` builtin tool); the `@override` DSL SHALL NOT be used to distinguish arms (identity `(apk, tool, variant, rep, timeout)` strips the `@` suffix; override-only arms collide and are silently skipped on resume).
- **INV-CAL-06**: During RUN+MONITOR, the only automated container intervention SHALL be `docker restart` of containers with exit code 137. Experiment configuration SHALL NEVER be altered mid-run. Stalled or otherwise-exited containers are reported for human decision.
- **INV-CAL-07**: Run completion SHALL be measured as identity-distinct non-empty logcats under `iterN/results/`, never as counts of the string `COMPLETED` (which double-counts via `state_transitions[]`) and never as task-state tallies alone.
- **INV-CAL-08**: Consolidation SHALL parse raw logcats (and `.trace` files for telemetry), dedup by identity. It SHALL NOT trust per-task CSV fields that a resume pass may have zeroed (anti-gh58).
- **INV-CAL-09**: VERIFY gates are numeric and fixed: `[APE-LLM-CONFIG]`==manifest in 100% of LLM tasks; 0 identity collisions; paired completeness 100% (an APK missing in ≥1 arm is excluded from paired analysis with a written record); per-arm median `time_ms` ≤ 2× the global median (violation → arm flagged, `time_ms` becomes a covariate note); re-derivation divergence 0 on integer counts and ≤ 0.01pp on percentages.
- **INV-CAL-10**: ANALYZE applies gates in the pre-declared order (proxy elimination → trimmed-mean 10% + paired bootstrap B≥10,000 fixed-seed CIs vs anchors → mechanistic prediction-vs-observed → between-reps determinism). Screening SELECTS candidates and never concludes; no victory declaration by screening p-value. The raw mean SHALL always be reported alongside the trimmed mean.
- **INV-CAL-11**: `calibracao/journal.jsonl` is append-only: one JSON record per state transition with `{ts, iter, state, artifact, sha256}`. Existing lines SHALL never be rewritten.
- **INV-CAL-12**: Iterations are append-only: `gen_iteration.py` SHALL refuse to overwrite an existing `iterN/`; a discarded iteration keeps its directory as provenance.
- **INV-CAL-13**: The scaffold SHALL NOT manage emulators (rv-platform owns the lifecycle), SHALL NOT modify the `ape` repository, and SHALL NOT touch `backup/`.

## ADDED Requirements

### Requirement: Iteration Generation (CONFIG-GEN) (FR08, FR16, NFR08)

`gen_iteration.py` SHALL generate a complete, self-contained iteration tree from a phase config and `get_variants()`. For each arm it SHALL resolve the full key dict from the named variant (arms are never declared in the generator), compute the expected `[APE-LLM-CONFIG]` field set from the resolved keys and `APERV_PROPERTY_MAPPING`, and record the predicted identity count (`arms × |subset| × reps`). It SHALL snapshot the deployment artifacts (`tool.py`; plus `ape-rv.jar` when `--jar` is given) into `iterN/artifacts/` and record their sha256 in the manifest together with `git describe --dirty` of the source worktrees. It SHALL emit the run compose (one shared `sglang` service + N `rvandroid` containers whose `RV_TOOLS` lists all arms with the arm order rotated per container), the smoke compose (smoke arm subset, 90s timeout, 1 rep), and per-container APK filters from the subset file.

#### Scenario: Manifest resolves arms from get_variants
- **WHEN** `gen_iteration.py --phase phases/cala.json --iter 1` runs with a phase config listing `ape:default` and the 10 `aperv` arms (`sata_mop_act_frontier`, `cal_a1`…`cal_a9`)
- **THEN** `iter1/manifest.json` SHALL contain 11 arm entries whose `keys` dicts equal the corresponding `get_variants()` dicts field-by-field (the `ape` builtin entry carries its tool defaults)
- **AND** `predicted_identities` SHALL equal `11 × 40 × 2 = 880` for a 40-APK subset with 2 reps

#### Scenario: Artifact snapshot with recorded hash
- **WHEN** generation completes
- **THEN** `iter1/artifacts/tool.py` SHALL be byte-identical to the worktree `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` at generation time
- **AND** `manifest.json.artifacts["tool.py"]` SHALL equal the file's sha256
- **AND** every bind-mount in the generated composes SHALL reference `iter1/artifacts/`, never the worktree path

#### Scenario: Arm-order rotation across containers
- **WHEN** the run compose is generated for 8 containers and 11 arms
- **THEN** container `i` SHALL list the arms in `RV_TOOLS` starting at arm `i mod 11`, wrapping around
- **AND** all containers SHALL contain the same arm set

#### Scenario: Iterations are append-only
- **WHEN** `gen_iteration.py --iter 1` runs and `iter1/` already exists
- **THEN** the script SHALL exit with code 2 without modifying `iter1/`

### Requirement: Pre-Flight Audit (NFR06, NFR08)

`preflight.py` SHALL independently audit a generated iteration before launch (gate of G3). Using its own parsing logic (INV-CAL-04), it SHALL verify: (a) every manifest arm exists in `get_variants()` and the key dicts match field-by-field; (b) the composes' `RV_TOOLS`, timeouts, reps, image reference, and bind-mounts match the manifest; (c) the predicted identities are distinct — at least 11 distinct `(tool, variant)` pairs in Phase A — and total `arms × |subset| × reps`; (d) the sha256 of every file in `iterN/artifacts/` equals the manifest hash; (e) the image is the pinned tag and ID (INV-CAL-03); (f) the `sglang` service is present with the expected model. The report SHALL list every check with PASS/FAIL and exit 1 on any FAIL.

#### Scenario: Tampered compose is detected
- **WHEN** a generated compose's `RV_TOOLS` is hand-edited to drop one arm and `preflight.py --iter-dir iter1` runs
- **THEN** the report SHALL FAIL the manifest×compose check naming the container and the missing arm
- **AND** the exit code SHALL be 1

#### Scenario: Worktree drift after snapshot is detected
- **WHEN** `tool.py` in `iter1/artifacts/` no longer hashes to `manifest.artifacts["tool.py"]`
- **THEN** preflight SHALL FAIL the artifact-hash check
- **AND** the remediation printed SHALL be to generate a new iteration, not to re-snapshot in place

### Requirement: Smoke Gate (NFR06)

`smoke_check.py` SHALL evaluate a completed smoke run (4 APKs × extreme arms, 90s, 1 rep) against the manifest. Per smoke task it SHALL check: the `[APE-LLM-CONFIG]` trace line equals the manifest's expected fields field-by-field for that arm; `[APE-LLM-CONFIG-ACK] server_model` equals the expected served model; the task identity is COMPLETED with coverage > 0; and the logcat contains 0 `VerifyError`. Any mismatch SHALL abort the iteration with a report — the scaffold NEVER self-adjusts configuration (the fix is a human decision).

#### Scenario: Config-ack field mismatch fails the gate
- **WHEN** arm `cal_a3`'s trace reports `llmOnNewState=true` but the manifest expects `llmOnNewState=false`
- **THEN** `smoke_check.py` SHALL report the arm, field, expected and observed values
- **AND** exit 1

### Requirement: Run Monitoring and Resume Policy (NFR04)

`monitor.sh` SHALL report progress as identity-distinct completed work per container and detect: (a) containers exited with code 137, which it SHALL `docker restart` (standing authorization, INV-CAL-06); (b) containers exited with any other code or without progress since the previous cadence, which it SHALL report only. Recovery of ERROR/FAILED tasks SHALL be a resume pass (`docker compose up -d` re-entry): the platform skips COMPLETED identities and re-runs failed ones. Completion of the run SHALL be declared only from identity-distinct non-empty logcats (INV-CAL-07).

#### Scenario: OOM container is restarted, crashed container is not
- **WHEN** container `cala_03` exits with code 137 and container `cala_05` exits with code 1
- **THEN** the monitor SHALL restart `cala_03` automatically
- **AND** SHALL report `cala_05` for human decision without restarting it

### Requirement: N-Arm Consolidation (FR11, FR14)

`consolidate_cal.py` SHALL build the iteration's consolidated datasets from raw result files, dedup by identity (INV-CAL-08): `per_apk_paired.csv` with one row per APK and one column group per arm (coverage metrics, MOP counts — averaged over reps), and `tel_proxies.csv` with per arm×APK×rep LLM telemetry aggregates (calls, `time_ms`, tokens, matched/`llm_tap`/`no_match` counts by reason, mode distribution) parsed from `.trace` files. Reuse of the existing d90c1f4 trace grammar is permitted here (the independence constraint binds VERIFY, not CONSOLIDATE).

#### Scenario: Duplicate task identities are deduplicated
- **WHEN** `tasks.json` contains two records for identity `(apk_x, aperv, cal_a2, 1, 300)` after a resume
- **THEN** the consolidation SHALL count that identity exactly once, using its logcat-derived metrics

### Requirement: Independent Verification (VERIFY) (NFR06, NFR08)

`verify_iteration.py` SHALL re-derive the consolidated counts by an independent code path (INV-CAL-04): direct extraction of `RVSEC-COV`/`RVSEC` markers from raw logcats and of `[APE-LLM-CONFIG]`/`[APE-LLM-CONFIG-ACK]` lines from traces, aggregated per identity by its own logic. It SHALL apply the numeric gates of INV-CAL-09 over 100% of tasks, plus a seeded hand-count sample report (≥10 tasks, fixed seed) compared cell-by-cell with the consolidated CSV. The verdict SHALL be `admissible` or `quarantine` with a written justification naming the excluded metric or arm.

#### Scenario: Re-derivation divergence fails verification
- **WHEN** the independent re-derivation counts 4,213 covered methods for identity `(apk_y, aperv, cal_a1, 2, 300)` and `per_apk_paired.csv` encodes 4,215
- **THEN** the divergence gate (0 on integer counts) SHALL fail
- **AND** the verdict SHALL be `quarantine` citing the identity and both values

#### Scenario: Missing APK breaks paired completeness
- **WHEN** APK `apk_z` has non-empty logcats in 10 arms but none in `cal_a7`
- **THEN** `apk_z` SHALL be excluded from the paired analysis set
- **AND** the exclusion SHALL be recorded in the verification report with the missing arm named

### Requirement: Gated Analysis (ANALYZE) (NFR08)

`analyze_iteration.py` SHALL produce `iterN/analysis.md` applying the gates in the pre-declared order of INV-CAL-10, computing statistics via `multiarm_stats.py` (trimmed-mean 10% summaries with raw means alongside, paired bootstrap B≥10,000 with the phase config seed for CIs vs both anchors, rank-biserial effect sizes, descriptive Friedman+Holm across arms) with primitives from the scaffold's vendored `stats_utils.py` (no runtime dependency on the `rvsec-calibracao` repo). The mechanistic check SHALL compare each arm's predicted Δcov_mop (Δactions/task × the +46%/action factor from the llm-gap diagnosis) with the observed CI95: prediction outside the CI is flagged as "mechanism not understood — do not promote without investigation"; temperature arms (H3) are exempt from elimination by this gate (descriptive only, per plan §6.1 gate 3).

#### Scenario: Analysis reports gates in order with prediction-vs-observed
- **WHEN** `analyze_iteration.py --iter-dir iter1` runs on verified data
- **THEN** `analysis.md` SHALL contain the four gates as ordered sections, each listing eliminated/flagged arms with reasons
- **AND** each arm's mechanistic prediction and observed CI95 SHALL appear side by side

### Requirement: Decision Record and Journal (NFR06, NFR08)

The scaffold SHALL provide `templates/decision.md` encoding the declarative per-phase decision rules (screening: promote the top 2–3 arms that pass all gates; confirmation: apply the pre-registered GO/NO-GO/INCONCLUSIVE criteria and STOP), which the agent instantiates as `iterN/decision.md` at DECIDE. `journal.py append` SHALL write one JSON line per state transition to `calibracao/journal.jsonl` (INV-CAL-11), creating `calibracao/` on first use.

#### Scenario: Journal line schema
- **WHEN** `journal.py append --state VERIFY --iter 1 --artifact iter1/verification_report.md` runs
- **THEN** one line SHALL be appended to `calibracao/journal.jsonl` containing keys `ts`, `iter`, `state`, `artifact`, `sha256`
- **AND** `sha256` SHALL be the hash of the artifact file at append time
- **AND** no existing line SHALL be modified
