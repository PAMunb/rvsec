# Design: gh88-cal-llm-control

**GitHub Issue**: #88
**Depends on**: `proposal.md`
**Planning sources**: `docs/20260721_plano_calibracao_llm.md` (rev. 3.2), `docs/20260721_metodologia_calibracao_loop.md`

## Context

The calibration campaign runs the loop CONFIG-GEN → PRE-FLIGHT → SMOKE → RUN+MONITOR → CONSOLIDATE → VERIFY → ANALYZE → DECIDE per iteration (methodology §3). This change builds the deterministic half of that loop: one testable script per state, plus the 9 `cal_*` arm variants in `aperv-tool`. State *transitions* remain agent-driven (a Claude session follows the methodology and invokes the scripts), with the fixed human gates G1–G4. This split was chosen during brainstorming: the loop runs ~3 times (Phases A/B/C), so a self-walking state-machine daemon would be speculative infrastructure (P1); what must be deterministic and auditable is each state's computation, not the scheduler.

Current state that constrains the design:

- Task identity is `(apk, tool, variant, rep, timeout)` (`modules/rv-platform/src/rv_platform/platform.py:308-321`) and the `@override` suffix is stripped at `modules/rv-experiment/src/rv_experiment/__main__.py:207` — arms MUST be named variants, never `@override` (plan §4).
- `modules/aperv-tool/src/aperv_tool/tools/aperv/tool.py` defines `APERV_PROPERTY_MAPPING` (line 75), `ARM_DEFINING_KEYS`/`_ARM_DEFINING_EXEMPT` (INV-APV-13/14/17), `_LLM_FLAGS` (line 261 — omits `llm_percentage` and `llm_prompt_variant`), and `get_variants()` (line 360). The INV-APV-14 guard test lives at `modules/aperv-tool/tests/test_aperv_tool.py` (`TestArmVariants`).
- The experiment template is `experimento-20260721/` (self-contained folder: composes with a shared `sglang` service + N `rvandroid` containers, `filters/`, `results/`, `scripts/monitor.sh` with identity-distinct counting, `scripts/analyze_cmpv2_llm.py` trace parser, `scripts/consolidate_compare.py`).
- All iterations run on the fixed image `phtcosta/rvandroid:0.9.3` (`87744cd58be9`); differences enter via `:ro` bind-mounts of `tool.py` (Phase A) and `ape-rv.jar` (Phase B), always sourced from the per-iteration snapshot `iterN/artifacts/`, never from the worktree (plan §4 "Imagem e deploy").
- Statistics primitives are **vendored** into the scaffold: `stats_utils.py` is copied verbatim (provenance header) from `workspace-rv/rvsec-calibracao/scripts/stats_utils.py` (outside `rvsec/`) into `experimento-cal/scripts/`. The sibling repo is a copy-source at implementation time, NOT a runtime import path.

Relevant FRs/NFRs: FR08 (task generation/identity), FR11 (logcat capture/parsing), FR14 (result generation), FR16 (`RV_TOOLS` DSL), FR19/FR20 (external tools / per-tool variants), NFR04 (resilience), NFR05 (configurability), NFR06 (observability), NFR08 (reproducibility).

## Architecture

```
                          (agent-driven transitions, gates G1–G4)
 phases/<phase>.json ──► gen_iteration.py ──► experimento-cal/iterN/
                          │                     ├── manifest.json          (arms, resolved keys, expected config-ack,
                          │                     │                           predicted identities, image ID, artifact hashes)
                          │                     ├── artifacts/             (tool.py [, ape-rv.jar] snapshots + sha256)
                          │                     ├── docker-compose.cala.yml, docker-compose.smoke.yml
                          │                     └── filters/
                          ▼
                     preflight.py  (independent re-derivation: manifest × composes × get_variants() × mounts)
                          ▼
                     compose up (smoke) ──► smoke_check.py  (config-ack field-by-field, served model via /v1/models, cov>0, VerifyError)
                          ▼
                     compose up (run) ──► monitor.sh  (identity-distinct progress; restart only exit-137;
                          │                            resume pass; completion = non-empty logcats per identity)
                          ▼
                     consolidate_cal.py ──► iterN/per_apk_paired.csv + iterN/tel_proxies.csv
                          ▼
                     verify_iteration.py  (independent code path; grep-level re-derivation + gates)
                          ▼
                     analyze_iteration.py ──► iterN/analysis.md   (gates in pre-declared order;
                          │                                        stats via vendored multiarm_stats.py)
                          ▼
                     decision.md (agent-written from template) + journal.py append ──► calibracao/journal.jsonl
```

Directory split: `experimento-cal/` is the self-contained experiment folder (scripts, phase configs, generated `iterN/`); `calibracao/` holds campaign-level artifacts that outlive iterations (journal, phase decision docs `cala_decision.md` etc., subset lists produced offline by Fase 0).

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `tool.py::get_variants()` (extended) | Define the 9 `cal_a1`…`cal_a9` arms; single source of truth for arm configs | — | variant dicts |
| `tool.py::LLM_ARM_KEYS` | Frozen set of ALL LLM keys that every `cal_*` arm must declare explicitly | — | constant |
| `experimento-cal/scripts/gen_iteration.py` | CONFIG-GEN: resolve arms from `get_variants()`, snapshot artifacts, emit manifest + composes + filters | phase config JSON, worktree `tool.py` (+ jar) | `iterN/` tree |
| `experimento-cal/scripts/preflight.py` | PRE-FLIGHT: independent audit; does not import `gen_iteration.py` | `iterN/` tree | PASS/FAIL report |
| `experimento-cal/scripts/smoke_check.py` | SMOKE gate over smoke results/traces/logcats | `iterN/results/` (smoke) | PASS/FAIL report |
| `experimento-cal/scripts/monitor.sh` | RUN+MONITOR cadence: progress by identity, restart exit-137 only, final resume pass | running containers | status lines |
| `experimento-cal/scripts/consolidate_cal.py` | CONSOLIDATE: N-arm consolidation from raw logcats, dedup by identity | `iterN/results/` | `per_apk_paired.csv`, `tel_proxies.csv` |
| `experimento-cal/scripts/verify_iteration.py` | VERIFY: independent re-derivation + numeric gates | `iterN/` (raw logs + CSVs) | admissible/quarantine verdict |
| `experimento-cal/scripts/analyze_iteration.py` | ANALYZE: pre-declared gate order, ranking, prediction-vs-observed | `per_apk_paired.csv`, `tel_proxies.csv`, manifest | `iterN/analysis.md` |
| `experimento-cal/scripts/multiarm_stats.py` | Trimmed-mean + paired bootstrap CIs, Friedman+Holm (N arms) | paired CSV | stats tables (imported by analyze) |
| `experimento-cal/scripts/journal.py` | Append one provenance record per state transition | state, iter, artifact path | `calibracao/journal.jsonl` line |
| `experimento-cal/scripts/status.py` | Derive campaign position (done/current/pending per iteration, pending gate, next action) — read-only, never a hand-maintained file (INV-CAL-14) | `journal.jsonl` + `iterN/` + phase configs | status report |
| `experimento-cal/templates/decision.md` | DECIDE template encoding the declarative per-phase rules | — | copied into `iterN/` |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| aperv: `cal_*` arms (plan §6 table) | `get_variants()` in `modules/aperv-tool/.../tool.py` | `test_cal_arms_match_plan_table` |
| aperv: `LLM_ARM_KEYS` guard (INV-APV-18) | `LLM_ARM_KEYS` constant + variant construction | `test_cal_variants_declare_all_llm_keys` |
| aperv: new mappings (INV-APV-13 extension) | `APERV_PROPERTY_MAPPING` entries | `test_property_mapping_covers_llm_max_tokens_and_snap` |
| calibration-control: manifest generation | `gen_iteration.py` | `test_manifest_resolves_from_get_variants` |
| calibration-control: artifact snapshot + hashes | `gen_iteration.py` | `test_snapshot_hashes_recorded` |
| calibration-control: compose/filter generation, arm rotation | `gen_iteration.py` | `test_compose_rotation_and_filters` |
| calibration-control: pre-flight audit + identity dry-run | `preflight.py` | `test_preflight_detects_mismatch`, `test_identity_dryrun_counts` |
| calibration-control: smoke gates | `smoke_check.py` | `test_smoke_config_ack_field_by_field` |
| calibration-control: monitor/restart/resume policy | `monitor.sh` | manual + fixture dry-run (see Testing) |
| calibration-control: N-arm consolidation | `consolidate_cal.py` | `test_consolidate_dedup_and_pairing` |
| calibration-control: independent verification gates | `verify_iteration.py` | `test_verify_gates_on_fixtures` |
| calibration-control: analysis gate order | `analyze_iteration.py`, `multiarm_stats.py` | `test_multiarm_stats_selftest` |
| calibration-control: journal provenance | `journal.py` | `test_journal_append_schema` |

## Goals / Non-Goals

**Goals:**
- Make Phase A launchable end-to-end up to gate G3 (launch approval) with zero hand-assembled configuration.
- Every number that feeds a decision is re-derivable: manifest ↔ composes ↔ variants audited before launch; consolidated CSVs re-derived by an independent code path after run.
- Provenance: any figure cited later traces to a raw logcat via `journal.jsonl` + `iterN/` snapshots.
- Serve as the calibration campaign's tracking vehicle: `tasks.md` registers every phase (Fase 0, A, B, C) as a milestone with its human gate, and the change closes only when the calibration concludes (final-181 config ratified at G4). Per-iteration loop state stays DERIVED by `status.py` (INV-CAL-14); the tasks track milestones and gates, not loop states.

**Non-Goals:**
- No state-machine daemon; transitions are agent-driven (methodology §3, gates G1–G4).
- No changes to `rv-platform`/`rv-experiment`/`rv-tools`; the scaffold consumes their CLIs. No platform→tool feedback channel.
- No `ape` repo code changes (J1–J4, gate G2 — tracked in the `ape` repo); no micro-Optuna driver (R3). The scaffold *scripts* never launch experiments (launch is the agent's gated action at G3); campaign *execution* is tracked as milestone tasks (groups 10–13), never automated.
- Phase-B arm variants (`cal_b*`) are NOT pre-defined — they depend on Phase-A survivors. They will be added to `get_variants()` under the same `LLM_ARM_KEYS` guard and deployed via the existing snapshot+bind-mount mechanism.

## Decisions

1. **Variants are the single source of truth; the manifest is a resolved echo.** `gen_iteration.py` imports `ApeRVTool.get_variants()` and resolves each arm's full key dict from the variant definition; it never re-declares arm configs. Alternative rejected: arms declared in a standalone YAML consumed by both the generator and `tool.py` — duplicates the arm definition and breaks the existing INV-APV guard machinery, which already enforces explicitness at the variant level.
2. **`LLM_ARM_KEYS` is a new frozen set, not an extension of `ARM_DEFINING_KEYS`.** `ARM_DEFINING_KEYS`/INV-APV-14 govern all non-exempt variants; adding `llm_percentage`/`llm_prompt_variant` there would retroactively invalidate the frozen gh43 exemption logic and non-LLM arms. Instead, a second guard applies only to `cal_*`-prefixed variants: `LLM_ARM_KEYS ⊆ keys(variant)`. The set contains every `llm_*` key in `APERV_PROPERTY_MAPPING` that the Phase-A jar consumes (`llm_url`, `llm_on_new_state`, `llm_on_stagnation`, `llm_model`, `llm_temperature`, `llm_top_p`, `llm_top_k`, `llm_timeout_ms`, `llm_percentage`, `llm_percentage_no_substrate`, `llm_prompt_variant`). `llm_max_tokens`/`llm_snap_tolerance_px` stay out of the set until the Phase-B jar exists (a key the jar ignores would fake explicitness).
3. **`cal_*` arms are built by explicit dict literals on the `sata_mop_act_frontier` substrate** (user decision at review, 2026-07-23, superseding the plan's original widget substrate): the frontier configuration won the cmpma multi-arm comparison (cov_mop 37.75% vs ≤35%, Friedman+Holm), so the algorithmic fallback of every LLM arm — every step the router does not delegate, and every `no_match` return — runs in frontier mode; keeping the widget substrate would handicap the LLM arms against both anchors. Consequences: (a) ANC2 (`sata_mop_act_frontier` without LLM) is the direct paired control isolating the LLM contribution on the same algorithmic base; (b) `cal_a1` carries the cmp_llm LLM-key config (`v13`, p=0.7, temp=0, top_p=0.6, top_k=50, ns=true, stag=true) but is no longer the identical cmp_llm arm — the −2.94pp gap anchor and the mechanistic prediction baselines were measured on the widget substrate, so ANALYZE treats them as cross-substrate estimates until the Phase-A run re-anchors them in-experiment (ANC1/ANC2/cal_a1 re-measure by design). A2–A9 differ from A1 per plan §6. No helper-factory abstraction: 9 explicit dicts differing in 1–4 keys (cal_a5 varies 4: percentage/temperature/top_p/top_k) are more auditable than a parametrized builder (P1; and the diff-vs-A1 is exactly what the experiment varies).
4. **`preflight.py` shares no code with `gen_iteration.py`.** Independence of the verifier is a code-path property (methodology §3.1-2/6): preflight re-parses the generated composes and filters with its own logic, re-imports `get_variants()` directly, recomputes artifact hashes from `iterN/artifacts/`, and re-derives predicted identities from `(apk, tool, variant, rep, timeout)` first principles. Same rule for `verify_iteration.py` vs `consolidate_cal.py`: verify greps `RVSEC-COV`/`RVSEC` markers and `[APE-LLM-CONFIG]`/`[APE-LLM-CONFIG-ACK]` lines directly from raw files and must not import `consolidate_compare.py`/`analyze_cmpv2_llm.py`.
5. **`consolidate_cal.py` MAY reuse the existing parser grammar** (`analyze_cmpv2_llm.py` d90c1f4 grammar for `tel_proxies.csv`) — the independence constraint binds VERIFY, not CONSOLIDATE. This mirrors the cmp* campaigns.
6. **Stats vendored into the scaffold (self-sufficient, no external-repo runtime dependency).** `stats_utils.py` is copied verbatim (with a provenance header naming the `rvsec-calibracao` upstream) into `experimento-cal/scripts/`, and `multiarm_stats.py` imports it from its own directory — no `sys.path` insertion, no env var, no out-of-tree path. `rvsec-calibracao` is a separate git tree outside `rvsec/`; importing it at runtime would make every iteration depend on the state of an unversioned external repo, a reproducibility hole (NFR08) — and the cross-repo relative path is itself brittle. The helper is ~1.6 KB (`holm_mde`, `diff_of_trimmed_means`, `paired_bootstrap_ci`); any additional primitive the ANALYZE loop needs is copied on demand. Alternative rejected: `sys.path`-inserting the sibling repo (the original draft) — it broke on the relative path and coupled the scaffold to an out-of-tree repo. "Copying forks a single source" does not apply here: the source is already external to this git tree, so there is no in-tree single source to fork; vendoring pins the version.
7. **Monitor restarts follow the standing authorization exactly**: `docker restart` only for containers with exit code 137 (OOM); ERROR tasks are recovered by the resume pass (`compose up -d` re-entry, dedup by identity — platform skips COMPLETED, re-runs FAILED). Progress and completion are measured as identity-distinct non-empty logcats under `iterN/results/` (lessons exp20260706 + monitor.sh header), never `COMPLETED` string counts.
8. **Journal writes are explicit calls, not hooks.** Each state script ends by printing the journal line it proposes; the agent appends it via `journal.py` after the human-visible gate summary. Simpler than instrumenting every script with implicit I/O, and keeps the journal append an auditable action.
9. **Phase configs are versioned inputs**: `experimento-cal/phases/cala.json` (arm list = variant names + `ape` builtin, subset file, reps, timeout, containers, smoke arm subset). The plan §6 table maps 1:1 to this file; changing a phase = editing one JSON reviewed at G1/G3.

## API Design

All scripts are argparse CLIs; exit code 0 = PASS, 1 = FAIL (gate scripts), 2 = usage error. Shared conventions: `--iter-dir experimento-cal/iterN`, deterministic output, fixed seeds from the phase config.

```
gen_iteration.py  --phase phases/cala.json --iter N [--jar PATH]
    pre: phase config valid; variants named in it exist in get_variants(); subset file exists
    post: iterN/{manifest.json, artifacts/, docker-compose.cala.yml, docker-compose.smoke.yml, filters/} written;
          manifest records image ID, per-arm resolved dict, expected config-ack fields, predicted identity count,
          sha256 of every snapshot artifact
    error: refuses to overwrite an existing iterN/ (iterations are append-only; a discarded iteration keeps its dir)

preflight.py      --iter-dir DIR
    post: report listing each check (manifest×compose env, manifest×get_variants() field equality,
          ≥11 distinct (tool,variant) identities × |subset| × reps predicted, image pin, artifact hash match,
          sglang service present) with PASS/FAIL each; exit 1 if any FAIL

smoke_check.py    --iter-dir DIR
    post: per smoke arm: [APE-LLM-CONFIG] == manifest field-by-field, identity COMPLETED + cov>0, VerifyError count == 0;
          served model proven via SGLang /v1/models == manifest expected_server_model (the [APE-LLM-CONFIG-ACK]
          server_model echo is logged, not the proof — it reports the client-side llm_model sentinel); exit 1 on any mismatch

monitor.sh        <iter-dir> [--no-resume]     # cadence run by cron/agent; idempotent
consolidate_cal.py --iter-dir DIR              # writes per_apk_paired.csv (one row per APK, one col-group per arm)
                                               # and tel_proxies.csv (per arm×apk×rep LLM telemetry aggregates)
verify_iteration.py --iter-dir DIR [--sample 10 --seed 42]
    post: gates (config-ack 100%; 0 identity collisions; paired completeness 100% — missing APK excluded+logged;
          contention: per-arm median time_ms ≤ 2× global median, else flag+covariate note;
          re-derivation divergence: 0 on integer counts, ≤0.01pp on percentages;
          hand-count sample report for ≥10 seeded tasks); verdict: admissible | quarantine(reason)

analyze_iteration.py --iter-dir DIR
    post: iterN/analysis.md with gate results in pre-declared order:
          (1) proxy elimination, (2) trimmed-mean 10% + paired bootstrap B≥10000 fixed-seed CIs vs ANC1/ANC2
          (raw mean always reported alongside), (3) mechanistic prediction-vs-observed (Δactions × +46%/action;
          divergence = prediction outside the observed CI95; descriptive-only for temperature arms),
          (4) determinism: identical-trace rate between reps (<30% target for temp>0 arms);
          Friedman+Holm descriptive table

journal.py append --state STATE --iter N --artifact PATH
    post: one JSON line {ts, iter, state, artifact, sha256} appended to calibracao/journal.jsonl
```

`manifest.json` schema (informal): `{iteration, phase, image: {tag, id}, dataset: {subset_file, apk_count}, arms: [{name, tool, variant, keys: {...}, expected_config_ack: {...}}], reps, timeout, containers, arm_rotation: [[...]], artifacts: {"tool.py": sha256, "ape-rv.jar": sha256?}, worktree: {rv_android_describe, ape_describe?}, predicted_identities}`.

## Data Flow

1. Phase config + `get_variants()` → `gen_iteration.py` → `iterN/` (manifest is the contract for every later state).
2. `iterN/` → `preflight.py` (reads only generated files + `get_variants()`) → G3 launch decision.
3. Containers write `iterN/results/<name>_NN/.../logcat_*.txt`, `tasks.json`, `.trace` files.
4. Raw results → `consolidate_cal.py` → `per_apk_paired.csv` (analysis input) + `tel_proxies.csv` (proxy gates).
5. Raw results + CSVs → `verify_iteration.py` → admissible/quarantine → gates ANALYZE.
6. CSVs + manifest predictions → `analyze_iteration.py` → `analysis.md` → agent writes `decision.md` from template → `journal.py` records every transition.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| Phase config references unknown variant | `gen_iteration.py` | fail fast, list known `cal_*` names | fix phase config |
| `iterN/` already exists | `gen_iteration.py` | refuse (append-only iterations) | use next N |
| Manifest × compose × variants mismatch | `preflight.py` | FAIL report, per-field diff | regenerate iteration; never hand-edit composes |
| Artifact hash mismatch (worktree drifted after snapshot) | `preflight.py` | FAIL | re-run `gen_iteration.py` as a new iteration |
| Smoke config-ack mismatch | `smoke_check.py` | abort iteration, report; never self-adjust config | human decision (G3 not granted) |
| Container exit 137 | `monitor.sh` | `docker restart` (standing authorization) | automatic |
| Container exited ≠137 / ERROR tasks | `monitor.sh` | report only; final resume pass re-runs FAILED by identity | resume pass |
| Missing APK in ≥1 arm | `verify_iteration.py` | exclude from paired analysis, log exclusion | recorded in verdict |
| Contention >2× median time_ms | `verify_iteration.py` | flag arm, time_ms becomes covariate note | analysis caveat |
| Journal append to missing dir | `journal.py` | create `calibracao/` on first append | automatic |

## Risks / Trade-offs

- [Preflight/verify independence is by convention, not enforced by tooling] → the spec pins it as an invariant; tests assert `verify_iteration.py`/`preflight.py` import neither the generator nor the existing parsers (import-graph check in the test).
- [`get_variants()` as single source means a worktree edit changes arm meaning mid-campaign] → mitigated by design: composes mount the `iterN/artifacts/` snapshot, preflight compares snapshot hash to manifest, and `git describe --dirty` is recorded.
- [Monitor cannot distinguish a hung container from a slow one] → cadence reports identity-progress deltas (pattern from `experimento-20260721/scripts/monitor.sh`); restart-on-stall is NOT automated beyond exit-137 (config-change prohibition), a stalled container is reported for human decision.
- [Multi-arm consolidation is new code on the critical path] → the independent VERIFY re-derivation (integer divergence must be 0) is exactly the guard against consolidation bugs (anti-gh58).
- [Phase-B/C reuse assumptions (jar mount, new `cal_b*` arms) untestable now] → `gen_iteration.py --jar` and manifest jar fields are implemented and unit-tested with a dummy jar file; live validation deferred to Phase B by design.

## Testing Strategy

| Layer | Scope | How |
|-------|-------|-----|
| Unit (aperv-tool) | `cal_*` dicts vs plan §6 table; `LLM_ARM_KEYS` guard; new mappings | extend `modules/aperv-tool/tests/test_aperv_tool.py`; CI flags `--import-mode=importlib -o "addopts="` |
| Unit (scaffold) | generator/preflight/smoke/consolidate/verify/stats/journal on synthetic fixtures (mini results tree with 2 arms × 2 APKs, crafted logcats/traces/tasks.json incl. a deliberate mismatch case) | `experimento-cal/tests/` via pytest with the same CI flags (run manually; not wired into module CI) |
| Integration (dry) | `gen_iteration.py` on the real `phases/cala.json` + real `get_variants()` → `preflight.py` PASS with 11 identities × subset × reps | executed as part of change verification (no containers, no emulator, no experiment) |
| Live | smoke/run/monitor | Phase A/B/C execution — tracked as campaign milestone tasks (groups 11–13), each gated by G3; not part of scaffold unit/integration testing |

## Open Questions

- Exact Java property name for `llm_snap_tolerance_px` (`ape.llmSnapTolerancePx` per plan §7) — final name is decided by the J1 change in the `ape` repo (G2). The mapping line ships with the plan's name and is corrected in the Phase-B iteration if J1 chooses differently (mapping is inert until that jar exists).
- `subset40.txt` does not exist yet (Fase 0 / P3, offline). `phases/cala.json` references it by path; generation of the iteration hard-fails until the file lands. This is an input dependency, not a blocker for implementing/testing the scaffold (tests use fixture subsets).
