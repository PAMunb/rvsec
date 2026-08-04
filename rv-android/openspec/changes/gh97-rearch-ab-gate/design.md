# Design: Empirical gate for the APE-RV re-architecture merge

## Context

The proposal establishes why the gate exists: the seven stage gates of the APE-RV re-architecture are
host- or JVM-level and none of them measures behaviour on real applications, while two documented
incidents (gh71's silently-inert boost, the 2026-06-19 false catastrophe) show the failure surface in
both directions. This document settles how the measurement is built.

Three facts constrain every decision below, and each was verified in the tree rather than assumed.

**The baseline leg is frozen and cannot be re-run.** `gh96-mop-artifact-derivation` is already
implemented here: `tool.py:1387` derives and pushes `/data/local/tmp/mop-artifact.json`, which the
baseline jar `386ce08d…` — pre-stage-2 and pre-stage-7 — cannot read. Producing any new pre-rewrite
data would require reverting this repository to `5dcf2259…` and maintaining a second image. Leg A is
therefore `experimento-e3-decisiva/per_apk_paired.csv` exactly as it stands, and every design choice
that would require re-measuring the baseline is off the table.

**The image does not build the jar under test.** `docker/rvandroid/Dockerfile:27` runs
`git clone https://github.com/phtcosta/ape.git /tmp/ape` with no `--branch` and no SHA pin — a
deliberate decision (gh71 D3) that keeps the shipped jar current with the `ape` default branch. The
gate is a *merge condition* for the `rearch` line, so at campaign time `rearch` is not merged and the
image's own jar is the default branch's. The jar under test arrives by bind-mount over the same path,
following the `docker/docker-compose.cmpft2.yml` precedent.

**`gh96` changed the monitored-operation substrate on purpose**, and its own design forbids mixing arms
across that cut. Two of the three arms are guided arms. The decision rule is shaped around this rather
than adjusted for it afterwards.

Relevant requirements: FR18/FR19 (tool execution and configuration), FR11/FR13 (violation and coverage
analysis over recorded artifacts), NFR06 (observability), NFR08 (experiment record-keeping).

## Architecture

```
ape-rearch worktree (branch rearch)
        │  mvn package  →  ape-rv.jar  (copied after the Java side completes)
        ▼
modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar
        │  bind-mount :ro over the image's own jar
        ▼
┌───────────────────────────────────────────────────────────────────────┐
│ phtcosta/rvandroid:0.9.3-rearch   ×8 containers                       │
│   rv-experiment → rv-platform → TaskExecutor → aperv-tool             │
│     RV_TOOLS = aperv:<3 arms>@corpus_basis=subset40:<sha256>          │
│     RV_APKS_FILTER = filters/batch_NN.txt  (5 APKs each)              │
│   outputs: tasks.json · *.logcat · *.trace (NDJSON) · *.provenance.json│
└───────────────────────────────────────────────────────────────────────┘
        │
        ▼  experimento-rearch-aperv/scripts/  (copies, adapted)
   preflight_runstart.py → gate before the full campaign
   consolidate.py  ──uses──►  aperv_tool.analysis.trace_ndjson  (gh94)
   verify.py                  (logcat + tasks.json paths unchanged)
   compare.py      ──uses──►  stats_utils.paired_bootstrap_ci
        │
        ▼
   per_apk_paired.csv · tel_proxies.csv · comparison report
        │
        ▼  paired against
   experimento-e3-decisiva/per_apk_paired.csv   (leg A, frozen)
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `ApeRVTool._push_properties` | Appends `ape.corpusBasis` when configured | `_tool_config["corpus_basis"]` | one `ape.properties` line |
| `ApeRVTool.configure` | Validates the basis shape before any device call | `str` | `None` or `ConfigurationError` |
| `scripts/preflight_runstart.py` | Reads `RUN_START` from one trace per arm; three checks | trace paths, manifest | PASS/FAIL report, exit code |
| `scripts/consolidate.py` | Copy of `consolidate_cal.py`, trace parsing on `trace_ndjson` | results tree | `per_apk_paired.csv`, `tel_proxies.csv` |
| `scripts/verify.py` | Copy of `verify_iteration.py`, independent recount | results tree | admissibility report |
| `scripts/compare.py` | G1/G2/G3 over both legs | two `per_apk_paired.csv` | comparison report with CIs |
| `aperv_tool.analysis.trace_ndjson` | NDJSON reader (**gh94's deliverable**) | `.trace` | typed step rows |

## Mapping: Spec → Implementation → Test

| Requirement | Implementation | Test |
|-------------|---------------|------|
| Corpus Basis Provenance — push | `tools/aperv/tool.py::_push_properties` | `test_corpus_basis_line_is_written` |
| Corpus Basis Provenance — validation | `tools/aperv/tool.py::configure` | `test_corpus_basis_malformed_raises_before_push` |
| INV-APV-56 (absent ⇒ omitted) | `tools/aperv/tool.py::_push_properties` | `test_corpus_basis_absent_emits_no_key` |
| INV-APV-57 (never read back) | absence of any reader | `test_no_module_reads_run_start` (source sweep) |
| Pre-flight `props_digest` | `scripts/preflight_runstart.py` | exercised by the smoke, not unit-tested |
| Pre-flight `preset` + `params` | `scripts/preflight_runstart.py` | idem |
| Pre-flight `build.sha` | `scripts/preflight_runstart.py` | idem |
| G1/G2/G3 | `scripts/compare.py` + `stats_utils.paired_bootstrap_ci` | `test_compare_on_synthetic_pairs` |

## Goals / Non-Goals

**Goals**

- Produce a paired, pre-registered comparison of behaviour on real applications between the baseline
  jar and the re-architected jar, and a merge verdict that is not re-specifiable after seeing numbers.
- Isolate the rewrite's effect from `gh96`'s intentional substrate change, by construction.
- Prove that the deployed jar is the one intended and that it resolves arms as intended, before the
  campaign consumes 24 hours of wall-clock.
- Leave the campaign's outputs in the shape the later analysis layer will consume.

**Non-Goals**

- **The analysis layer is out of scope.** It targets the thesis repository, serves a different
  campaign (an E2 redo across 8 tools and 11 configurations with a negative-binomial GLM), and its
  open parameters are freeze items of *that* pre-registration. This change consumes only
  `stats_utils.paired_bootstrap_ci` and produces CSVs the layer can read later.
- **No re-measurement of the baseline.** Leg A is frozen.
- **No repair of `experimento-cal/` or `experimento-e3-decisiva/`.** Both are frozen artifacts.
- **No new arms.** Only the three E3 arms have a baseline; adding `sata` would require a leg-A run
  that does not exist.
- **No emulator management.** `rv-platform` owns the entire lifecycle, without exception.

## Decisions

### D1 — The control arm is the rewrite-isolating channel

`mop_off_llm_off` sets the five monitored-operation weights to `0` and `activity_trigger_enabled` to
`false` (`tool.py:360-366`) while keeping `mop_data` present, so it loads the substrate and scores
nothing by it. `gh96`'s change — the tier reassignment and the 1,232 recovered flagged widgets across
8 applications — enters behaviour only through `mopWeightDirect`/`mopWeightTransitive` and
`activity_has_mop`. Both channels are closed in this arm.

This is measured, not argued: E3 validity gate 1 established `decision_source=MOP == 0` and `mop= == 0`
in every step of that arm across all 40 applications. A different substrate feeding a zero weight
produces the same exploration.

*Alternatives considered.* Buying a clean channel by running a pre-rewrite `sata` baseline (§5.2 of the
discussion): rejected — it costs a repository revert to `5dcf2259…` plus a second image, and delivers
isolation the control arm already provides for free. Declaring an expected direction and magnitude per
monitored-operation outcome and gating on all three arms: rejected — `gh96` broadens the flagged
surface by 33% while flattening the ranking among flagged widgets, so its net effect on *detection* has
no defensible predicted sign, and a pre-registration must not assert one it cannot justify.

### D2 — G2 exists because G1 cannot see the guided path

G1 by construction never exercises monitored-operation-weighted scoring, which is exactly the code
`rearch-03-decision-pipeline` rewrote (the MOP launcher and its counters, the scoring stages). G2
closes that gap without comparing levels across the substrate cut: it asserts that *within the new
campaign*, guidance still does what it demonstrably did in E3 — `mop_on_llm_off` reached 95.5% of
activities against the control's 81.5%, a paired difference of +14.9 pp with CI95 [7.75, 22.04].

A sign-and-CI test on a within-campaign contrast is immune to the confound, because both of its terms
are measured on the same substrate. A rewrite that broke guidance collapses that contrast toward zero;
a substrate that shifted the flagged surface does not change its sign.

`cov_act` is the right outcome for G2 and the wrong one for a two-sided reading: its median is 100.0 in
both guided arms, so the measure is at ceiling. Regression is detectable, improvement is not. G2 is
therefore stated one-sided and its ceiling is recorded in the pre-registration as a declared premise.

### D3 — Two outcomes are reported but do not gate

`crashes` has median 0 in all three arms of E3; a paired bootstrap CI over a near-constant zero vector
decides nothing, and treating it as a gate would manufacture a verdict from noise. `mop_unique` was
flat enough in E3 that the McNemar primary had `n_discordante = 0` in both contrasts. Both are reported
with their CIs — the issue's "report whatever it says" applies — and neither blocks the merge on its
own. This is declared before the campaign, not chosen after seeing which outcome moved.

### D4 — Margins are derived from the baseline, not chosen

"CI excludes zero" alone fails the gate on campaign noise: the documented run-level drift is −0.743 pp
of `cov_mop` at p=0.0099 with no code change at all. The margin per outcome is computed before the
freeze from the replica dispersion already present in leg A —
`experimento-e3-decisiva/results/e3_decisiva_*/coverage.csv` carries `(apk, rep, tool)` granularity, so
the three replicas of every pair are separately readable — and floored at 1.5 pp (twice the documented
drift) for the percentage outcomes. Within-campaign replica dispersion is a lower bound on
between-campaign variability, which is why the floor exists rather than being taken as the estimate.

A blocking finding therefore requires **both** a CI excluding zero in the harmful direction **and**
|Δ| above the derived margin.

### D5 — The grid is identical to E3 by requirement

Leg A's per-application value is the **mean of three replicas** (`consolidate_cal.py:311`). Running
one replica in leg B would make the paired difference asymmetrically noisier — more variance on one
side of a difference that is then tested for being non-zero. That is the mechanism behind the
2026-06-19 false catastrophe, reproduced by design. Three arms × 40 applications × 3 replicas ×
1800 s × 8 containers, ≈24 h, is not a cost preference; it is what makes the comparison legible.

### D6 — Scripts are copied and adapted, never reused in place

`gh94` INV-APV-55 declares `experimento-cal/scripts/*` a frozen-corpus reader that shall not be
migrated, adapted or deleted. The four scripts the gate needs (`consolidate_cal.py`,
`verify_iteration.py`, `multiarm_stats.py`, `stats_utils.py`) are stdlib-only and self-contained —
verified: no `aperv_tool` import, no `get_variants()` call, arms discovered from the results tree — so
`gh95`'s arm retirement does not break them. But they parse the legacy `[APE-*]` trace family, which
the stage-4 jar no longer emits.

The copies live in the campaign directory. **The adaptation is narrow on purpose**: only the
trace-reading paths move onto `aperv_tool.analysis.trace_ndjson`, feeding `tel_proxies.csv`. The
logcat and `tasks.json` paths — which produce every headline outcome and `per_apk_paired.csv` — are
carried over unchanged, so the two legs stay column-identical and aggregation-identical. Anything
else would break the pairing the whole gate rests on.

`stats_utils.py` is copied verbatim: `paired_bootstrap_ci` reads no trace and must be byte-identical
to the routine the E3 analysis used.

### D7 — The pre-flight is the smoke's acceptance criterion

Three checks over the first line of one trace per arm:

1. **`props_digest`** equals the digest computed host-side over the `ape.properties` the harness
   pushed. Proves transport with no mapping ambiguity — the jar read exactly the bytes sent.
2. **`preset`** equals the arm's declared preset, and every `overrides` key appears in `params` with
   its declared value. Proves the jar honoured `ape.preset`. This is the one execution `gh95`
   deferred here, and without it a pre-stage-2 jar would silently collapse every arm to defaults.
3. **`build.sha`** equals the `rearch` commit that was built. This is the load-bearing one: with the
   Dockerfile's unpinned clone and the bind-mount, two jars exist in the container and `RUN_START.build`
   is the only thing that says which one ran. `run-spec` states it plainly — *"No runtime `[APE-BUILD]`
   banner is emitted — `RUN_START.build` is the banner."*

4. **`corpus_basis`** equals the SHA-256 recomputed from `calibracao/subset40.txt`. This check does
   double duty and is the reason it gates rather than merely reports: **an absent `corpus_basis` in
   `RUN_START` means the DSL parameter path is broken**. The value's only route to the device is
   `RV_TOOLS`' `@corpus_basis=…` segment, through `_parse_single_tool_spec` and `configure()`'s fold
   into `overrides`, so if any seam in that chain drops it, the key never reaches `ape.properties` and
   never appears in the echo. The two failure modes are therefore distinct and both blocking:
   *absent* means the parameter never arrived, *mismatched* means it arrived carrying the wrong list.
   Reading the generated `ape.properties` on a local run is a useful pre-check, but the smoke is the
   authoritative verification because it exercises the whole chain the campaign will use.

The pre-flight is an operator script over a recorded trace. It does **not** live in `tool.py` and does
not run on any execution path: `run-spec` INV-RUN-03 declares `RUN_START` write-only at level 0 — *no
runtime component, Java or Python, reads it* — and `gh95` decision D1 restates it on this side. A
runtime echo-vs-intent validator would contradict a level-0 invariant of the other repository.

*Alternative considered.* A separate pre-flight step before the smoke: rejected as duplicated
machinery. The smoke already runs; making its acceptance criterion the pre-flight is one gate instead
of two (P1).

### D8 — The corpus basis travels through the tool DSL

`RV_TOOLS: "aperv:mop_on_llm_off:mop_off_llm_off:mop_on_llm_70@corpus_basis=subset40:<sha256>"`.

`_parse_single_tool_spec` (`modules/rv-experiment/src/rv_experiment/factories/configuration_factory.py:322-327`)
splits on `@` **first** and only then splits the tool part on `:`, so the colon inside the digest
survives in the value. Parameters attach to the whole tool spec, which is correct here — the corpus is
campaign-wide, identical across arms, and must not be frozen into an arm definition, since arms are
corpus-independent by design.

`corpus_basis → ape.corpusBasis` is added to `APERV_PROPERTY_MAPPING`, which is what makes `gh95`'s
DSL fold accept it: `configure()` folds mapped top-level keys into `overrides` and raises on any it
cannot honour, so an unmapped key would be a hard error rather than a silent drop.

*Alternative considered.* A new environment variable read by the tool: rejected — it would put a
platform-level knob into a tool module and duplicate a delivery path that already exists.

### D9 — New image tag, both IDs pinned

`phtcosta/rvandroid:0.9.3-rearch`. Rebuilding `0.9.3` in place makes the two legs indistinguishable by
tag, collides with the issue's first acceptance criterion and with the calibration scaffold's rule that
an image is pinned by tag **and** ID, and is gh71's shape at the image layer. Leg A's image is already
captured — ID `sha256:b2904fdfc3ddfc81ad455abd5e5685ddc97666c9411c4d994fec9111311aedec`, created
2026-08-01T11:47:43-03:00, before the E3 launch — and must be recorded before a `docker prune` removes
it. `:latest` currently points at that same ID, which is a second reason not to reuse a tag.

Both IDs live in the pre-registration document; the journal freezes that document's sha256. The
journal freezes documents, not facts — that is the E3 mechanism and this change does not invent a
second one.

## API Design

### `ApeRVTool.configure(config: dict) -> None`

*Precondition*: called before any device interaction.
*Postcondition*: `_tool_config["corpus_basis"]` is present and shape-valid, or absent.
*Error*: `ConfigurationError` when present and not matching `^[A-Za-z0-9._-]+:[0-9a-f]{64}$`, naming
the key and the rejected value. The tool does not verify that the digest corresponds to any file — it
owns the contract, not the corpus.

### `ApeRVTool._push_properties(..., mop_json_pushed: bool) -> None`

*Postcondition*: the generated `ape.properties` contains `ape.corpusBasis=<value>` when configured,
and contains no line beginning `ape.corpusBasis` otherwise (INV-APV-56).

### `preflight_runstart.py --results <dir> --manifest <json>`

*Precondition*: a completed smoke with at least one trace per arm.
*Postcondition*: a report listing every check with PASS/FAIL; exit 1 on any FAIL.
*Reads*: the first line of each selected `.trace`, parsed with `json.loads` — `RUN_START` is a single
JSON object line from stage 2 onward, so the pre-flight does **not** depend on `gh94`'s reader.

## Data Flow

1. The pre-registration document is written, its margins derived from leg A's replica dispersion, and
   its sha256 frozen in `calibracao/journal.jsonl`. Nothing downstream may change it.
2. The `rearch` jar is built from the `ape-rearch` worktree and copied to
   `modules/aperv-tool/src/aperv_tool/tools/aperv/ape-rv.jar`; the image `0.9.3-rearch` is built and
   pushed; its ID is recorded.
3. The smoke runs. `preflight_runstart.py` reads one trace per arm and gates on the four checks.
4. The campaign runs: 8 containers, each executing all three arms over its own 5 applications, so a
   container failure drops whole pairs rather than half-pairs and resume recovers them cleanly.
5. `verify.py` recounts identities independently; `consolidate.py` produces `per_apk_paired.csv` and
   `tel_proxies.csv`.
6. `compare.py` evaluates G1, G2 and G3 against the frozen plan and emits the report with CIs.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `ConfigurationError` | malformed `corpus_basis` | raise in `configure()` | fix the compose's `RV_TOOLS`; no device was touched |
| Pre-flight `build.sha` mismatch | wrong jar won the mount | fail the gate, exit 1 | rebuild/re-mount; the campaign never starts |
| Pre-flight `preset` mismatch | jar ignored `ape.preset` | fail the gate, exit 1 | the jar predates stage 2 — rebuild from `rearch` |
| Pre-flight `corpus_basis` mismatch | transcribed digest | fail the gate, exit 1 | recompute from `calibracao/subset40.txt` |
| Pre-flight `corpus_basis` **absent** | DSL parameter path dropped it | fail the gate, exit 1 | fall back to a per-arm `overrides` entry (design D8) |
| Task `ERROR`/`FAILED` | transient `adb install` | resume pass (`up -d` re-entry) | identity-based skip of COMPLETED |
| Container exit 137 | OOM | `docker restart` | standing authorization in the monitor |
| Missing arm at consolidation | lost pair | report the count, never silence it | resume; discard only if unrecoverable |

## Risks / Trade-offs

- **The DSL parameter path is unverified end to end for `aperv`.** `_parse_single_tool_spec` emits a
  plural `{"variants": [...]}` shape that the module's own `TODO(FR15)` calls a dead output shape
  against `ToolConfig(variant: str)`. The `@` parameters may not survive that seam. → Two-stage
  mitigation. A local run reading the generated `ape.properties` is the cheap pre-check, run before
  the freeze. The **authoritative** verification is the smoke's pre-flight: an absent `corpus_basis`
  in `RUN_START` is a named, blocking failure mode meaning the parameter never arrived, and it is
  caught over the exact chain the campaign uses rather than over a local approximation of it. If the
  seam is broken, the fallback is a per-arm `overrides` entry set by the campaign's own configuration,
  which costs one more line and no new mechanism.
- **G1 mixes the rewrite with the stage-4 telemetry cost.** One NDJSON record per step costs step time,
  and fewer steps in 1800 s means less coverage. → Recorded as a declared premise: G1 measures the
  rewrite **as delivered**, which is what a merge condition should measure. The isolated telemetry cost
  is the `ape` side's own gate (INV-SNK-13, steps per minute).
- **Between-campaign drift is not controlled.** Days apart, different image, different host load. →
  The derived margin with its 1.5 pp floor exists for exactly this; and the honest statement of the
  residual belongs in the pre-registration's premises, not in a footnote afterwards.
- **`gh96`'s removal of the footprint guard could inflate leg B on applications that used to abort.**
  → Checked against leg A: no application in the corpus has `cov_method < 5` in any arm, so no arm
  aborted on this corpus. Re-confirmed host-side against the guard's threshold before the freeze; if
  any application is affected, it is declared before the campaign, never excluded after.
- **The chain is long and every link is a precondition.** `gh94` applied, `gh95` applied, `ape` stages
  3–7 complete, jar copied, image built and pushed. → Encoded as task ordering, not as prose.

## Testing Strategy

| Layer | What to test | How | Count |
|-------|-------------|-----|-------|
| Unit | `corpus_basis` push, omission, validation | pytest over `_push_properties`/`configure`, no device | ~4 |
| Unit | source sweep proving nothing reads `RUN_START` | grep-based test over `modules/aperv-tool/src` | 1 |
| Unit | G1/G2/G3 arithmetic on synthetic pairs | pytest over `compare.py` with hand-built vectors | ~3 |
| Integration | pre-flight against a real smoke trace | the smoke itself; gates the campaign | 1 gate |
| Campaign | validity gates before any outcome is read | `verify.py` over the full results tree | 4 gates |

CI contract for every pytest invocation: `--import-mode=importlib -o "addopts="`.

## Open Questions

- **The exact margin values** are derived, not chosen, but the derivation runs during the apply phase
  and its output must be reviewed and signed off before the freeze — a derived number is still a
  number someone has to accept.
- **Whether `mop_total` belongs in G1 at all.** It counts violation lines rather than distinct
  violations and is the noisiest of the five; it is included pending the replica-dispersion figures,
  and may be demoted to descriptive on the same evidence that sets the margins. This must be settled
  before the freeze, not after.
