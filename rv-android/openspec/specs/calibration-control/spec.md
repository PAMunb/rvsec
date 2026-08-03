# calibration-control Specification

## Purpose
`calibration-control` is the control scaffold for the APE-RV LLM calibration campaign (planning docs `docs/20260721_plano_calibracao_llm.md` rev. 3.2 and `docs/20260721_metodologia_calibracao_loop.md`). The campaign selects the LLM configuration (prompt variant, sampling parameters, routing regime) of the `aperv` LLM arm through three experiment phases (A `cala`, B `calb`, C `calc`), each phase being one or more *iterations* of the loop CONFIG-GEN → PRE-FLIGHT → SMOKE → RUN+MONITOR → CONSOLIDATE → VERIFY → ANALYZE → DECIDE.

The capability's job is to make every state of that loop a deterministic, auditable computation. Each state is one CLI script under `experimento-cal/scripts/`; state transitions are driven by an agent following the methodology, with four fixed human gates (G1 plan/budget, G2 any `ape`-repo change, G3 each launch, G4 final verdict). The scripts never launch experiments themselves — they generate, audit, gate, consolidate, verify, and analyze. The two verifier states (PRE-FLIGHT and VERIFY) are *independent by code path*: they re-derive every number they check with their own logic, because an agent re-running the producer's script is not independence.

The scaffold exists to prevent three failure classes that previous campaigns hit: (1) hand-assembled configuration drift (arms whose deployed config silently differs from the intended config — countered by manifest-driven generation plus field-by-field `[APE-LLM-CONFIG]` auditing); (2) resume/identity corruption (override-only arms colliding on the `(apk, tool, variant, rep, timeout)` identity; CSV zeroing on resume — countered by named-variant arms and consolidation from raw logcats, the anti-gh58 rule); (3) unreproducible provenance (results that cannot be traced to a config and artifact hash — countered by per-iteration snapshots and the append-only journal).

Directory layout: `experimento-cal/` holds the scripts, phase configs (`phases/<phase>.json`) and generated per-iteration trees (`iterN/`); `calibracao/` holds campaign-level artifacts that outlive iterations (`journal.jsonl`, phase decision documents, subset files produced offline by Fase 0). All experiment execution runs on the fixed Docker image `phtcosta/rvandroid:0.9.3` (`87744cd58be9`); configuration differences enter exclusively via `:ro` bind-mounts of snapshot artifacts.
## Requirements
### Requirement: Iteration Generation (CONFIG-GEN) (FR08, FR16, NFR08)

`gen_iteration.py` SHALL generate a complete, self-contained iteration tree from a phase config and `get_variants()`. For each arm it SHALL resolve the full key dict from the named variant (arms are never declared in the generator), compute the expected `[APE-LLM-CONFIG]` field set from the resolved keys and `APERV_PROPERTY_MAPPING`, and record the predicted identity count (`arms × |subset| × reps`). It SHALL snapshot the deployment artifacts (`tool.py`; plus `ape-rv.jar` when `--jar` is given) into `iterN/artifacts/` and record their sha256 in the manifest together with `git describe --dirty` of the source worktrees. It SHALL emit the run compose (one shared `sglang` service + N `rvandroid` containers whose `RV_TOOLS` lists all arms with the arm order rotated per container), the smoke compose (smoke arm subset, 90s timeout, 1 rep), and per-container APK filters from the subset file. The `sglang` service's `--model-path` SHALL derive from the phase config's `expected_server_model` — the single source that also populates the manifest's `expected_server_model` — so the model loaded on the GPU and the model the smoke gate expects cannot drift (changing the model is one edit in the phase config).

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

`smoke_check.py` SHALL evaluate a completed smoke run (4 APKs × extreme arms, 90s, 1 rep) against the manifest. Per smoke task it SHALL check: the `[APE-LLM-CONFIG]` trace line equals the manifest's expected fields field-by-field for that arm; the task identity is COMPLETED with coverage > 0; and the logcat contains 0 `VerifyError`. It SHALL additionally prove that the served model matches the manifest's `expected_server_model` by querying the SGLang server's `/v1/models` endpoint (the authoritative source — what the compose `--model-path` actually loaded on the GPU). The `[APE-LLM-CONFIG-ACK] server_model` line SHALL be recorded in the report but SHALL NOT be the model proof: it echoes the client-side request `model` parameter (the `llm_model` sentinel, e.g. `default`), which a single-model SGLang server accepts and routes to the one loaded model, so it reflects the configured request field, not the served model. Any mismatch SHALL abort the iteration with a report — the scaffold NEVER self-adjusts configuration (the fix is a human decision).

#### Scenario: Config-ack field mismatch fails the gate
- **WHEN** arm `cal_a3`'s trace reports `llmOnNewState=true` but the manifest expects `llmOnNewState=false`
- **THEN** `smoke_check.py` SHALL report the arm, field, expected and observed values
- **AND** exit 1

#### Scenario: Served model is proven against the model endpoint, not the ACK echo
- **WHEN** SGLang serves the manifest's `expected_server_model` (e.g. `Qwen/Qwen3-VL-4B-Instruct`) but every arm's `[APE-LLM-CONFIG-ACK] server_model` echoes the `llm_model` sentinel `default` (and arms that never call the LLM emit no ACK at all)
- **THEN** `smoke_check.py` SHALL query SGLang `/v1/models`, confirm the served id equals `expected_server_model`, and PASS the model check
- **AND** the `server_model=default` echo SHALL appear in the report as informational only, never as a mismatch or abort cause

### Requirement: Run Monitoring and Resume Policy (NFR04)

`monitor.sh` SHALL report progress as identity-distinct completed work per container and detect: (a) containers exited with code 137, which it SHALL `docker restart` (standing authorization, INV-CAL-06); (b) containers exited with any other code or without progress since the previous cadence, which it SHALL report only. Recovery of ERROR/FAILED tasks SHALL be a resume pass (`docker compose up -d` re-entry): the platform skips COMPLETED identities and re-runs failed ones. Completion of the run SHALL be declared only from identity-distinct non-empty logcats (INV-CAL-07).

#### Scenario: OOM container is restarted, crashed container is not
- **WHEN** container `cala_03` exits with code 137 and container `cala_05` exits with code 1
- **THEN** the monitor SHALL restart `cala_03` automatically
- **AND** SHALL report `cala_05` for human decision without restarting it

### Requirement: N-Arm Consolidation (FR11, FR14)

`consolidate_cal.py` SHALL build the iteration's consolidated datasets from raw result files, dedup by identity (INV-CAL-08): `per_apk_paired.csv` with one row per APK and one column group per arm (coverage metrics, MOP counts — averaged over reps), and `tel_proxies.csv` with per arm×APK×rep LLM telemetry aggregates (calls, `time_ms`, tokens, matched/`llm_tap`/`no_match` counts by reason, mode distribution) parsed from `.trace` files. Reuse of the existing d90c1f4 trace grammar is permitted here (the independence constraint binds VERIFY, not CONSOLIDATE).

Consolidation SHALL consume only identities whose `timeout` equals the run timeout recorded in `iterN/manifest.json`, excluding the smoke identities the smoke containers (`cala_smoke_*`) write under the same `iterN/results/` tree (90s, 1 rep, the smoke-arm subset). Smoke and run tasks share `(apk, tool, variant, rep)` and differ only in `timeout`; because `per_apk_paired.csv` averages reps within each `(apk, arm)` cell without keying on `timeout`, an un-filtered smoke identity (shorter budget, systematically lower coverage) would pollute the reps-averaged cell of every smoke arm×APK pair. The manifest run timeout is the single source of the filter.

#### Scenario: Duplicate task identities are deduplicated
- **WHEN** `tasks.json` contains two records for identity `(apk_x, aperv, cal_a2, 1, 300)` after a resume
- **THEN** the consolidation SHALL count that identity exactly once, using its logcat-derived metrics

#### Scenario: Smoke identities are excluded by run timeout
- **WHEN** `iterN/results/` holds both a smoke identity `(apk_x, aperv, cal_a1, 1, 90)` and the run identities `(apk_x, aperv, cal_a1, 1, 300)` and `(apk_x, aperv, cal_a1, 2, 300)` for the same APK and arm, and `manifest.json` records the run `timeout` as `300`
- **THEN** the `apk_x` × `aperv:cal_a1` cell of `per_apk_paired.csv` SHALL average only the two 300s reps, and the 90s smoke identity SHALL NOT contribute to any consolidated metric nor to the consolidated identity count

### Requirement: Independent Verification (VERIFY) (NFR06, NFR08)

`verify_iteration.py` SHALL re-derive the consolidated counts by an independent code path (INV-CAL-04): direct extraction of `RVSEC-COV`/`RVSEC` markers from raw logcats and of `[APE-LLM-CONFIG]`/`[APE-LLM-CONFIG-ACK]` lines from traces, aggregated per identity by its own logic. It SHALL re-derive over the same identity scope as consolidation — only identities whose `timeout` equals the manifest run timeout, excluding smoke (read from the manifest by VERIFY's own code, not imported from `consolidate_cal.py`) — so a divergence signals a genuine consolidation error, not a scope mismatch on the smoke-arm cells. It SHALL apply the numeric gates of INV-CAL-09 over 100% of tasks, plus a seeded hand-count sample report (≥10 tasks, fixed seed) compared cell-by-cell with the consolidated CSV. The verdict SHALL be `admissible` or `quarantine` with a written justification naming the excluded metric or arm.

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

### Requirement: Campaign Status Reporting (NFR06)

Because state transitions are agent-driven with no daemon, an agent (or a human) needs to
answer "where is the campaign now, and what runs next?" without reconstructing it by hand.
`status.py` SHALL derive and report the campaign position from the transition journal, the
generated `iterN/` trees, and the phase configs — never from a hand-maintained checklist
(INV-CAL-14). For each iteration it SHALL render the eight-state loop (CONFIG-GEN → …→
DECIDE) with each state marked done / current / pending, where *done* means a journal
transition record for that state corroborated by the state's expected artifact where one
exists (`manifest.json` for CONFIG-GEN, `per_apk_paired.csv` for CONSOLIDATE,
`verification_report.md` for VERIFY, `analysis.md` for ANALYZE, `decision.md` for DECIDE);
a journal record without its expected artifact (or the reverse) SHALL be flagged as an
inconsistency. It SHALL report the pending human gate (G1–G4) if any and the next action
(the script to run), plus a cross-iteration summary (phase, DECIDE verdict, promoted arms).
`status.py` SHALL be read-only.

#### Scenario: Status derives current state and next action
- **WHEN** `status.py` runs after CONFIG-GEN and PRE-FLIGHT of `iter1` are journaled and `iter1/manifest.json` exists but no `iter1/results/` yet
- **THEN** the report SHALL mark CONFIG-GEN and PRE-FLIGHT as done, SMOKE as the current/next state, the pending gate as G3 (launch), and the next action as running the smoke gate
- **AND** an iteration whose journal records VERIFY but whose `iterN/verification_report.md` is absent SHALL be flagged as an inconsistency

