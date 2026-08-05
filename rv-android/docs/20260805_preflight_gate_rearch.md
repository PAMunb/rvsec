# Pre-flight report — the `rearch` A/B gate, before the campaign

Task 7.4's deliverable for `gh97-rearch-ab-gate`. This report is the record that the campaign was
allowed to start, and on what evidence. It carries three distinct kinds of statement and labels each
one, because they have different authority:

- **Gating checks** (7.2, 7.2a) — a FAIL here stops the campaign.
- **The `ape` side's delegated device verification** (7.2a) — the same checks, named as what they
  discharge, so a later reader of `rearch-07` can see that what was delegated was actually verified.
- **Recorded, never gating** (7.2b) — evidence harvested for the other repository. Design D11 states
  why: the campaign's own readers go through `aperv_tool.analysis.trace_ndjson` and never touch
  heartbeats, so nothing here can invalidate an outcome this change measures.

Everything below was re-measured on 2026-08-05 from the smoke's stored artifacts, not copied from the
session that produced them. One published number did not survive re-measurement and is corrected in
§5.

---

## 1. What was run

| | |
|---|---|
| Date of the run | 2026-08-05 |
| Vehicle | `experimento-rearch-aperv/docker-compose.smoke.yml`, 1 container |
| Grid | 3 arms × 2 applications × 1 repetition × 300 s = **6 runs** |
| Results | `experimento-rearch-aperv/results_smoke/rearch_aperv_smoke/` |
| Applications | `com.smartpack.packagemanager_79`, `org.liberty.android.freeotpplus_26` |
| Wall clock per run | 355–361 s at a 300 s timeout |

The two applications were **not** picked by `cov_mop`. They were picked by deriving the MOP artifact
host-side and requiring `flagged`, `wtgEdges` and `mopActivities` all positive — `cov_mop` comes from
the RVSEC logcat markers and does not depend on the guidance artifact at all, so it can read high on
an application whose artifact is empty. An earlier smoke was discarded for exactly that reason.

## 2. Identities under test

| Artifact | Value | Checked how |
|---|---|---|
| Jar (leg B) | sha256 `a7eddf5a776ce20f7299911d7d9acb3a0f1342cdc1512b3e28aa00488e582a94` | `sha256sum` on the deployed path |
| Jar build stamp | `9e948102` — the `rearch` worktree commit, **not** master's `c638142` | `RUN_START.build.sha`, all three arms |
| Jar (leg A, preserved) | sha256 `386ce08d1846a4088755a8d755e5b70391af3b42add091d231dbcc52aed24e69` | `backup/gh97-prechange-jar/` |
| Image (leg B) | `phtcosta/rvandroid:0.9.3-rearch` = `sha256:2cc5c3aada3d…` | `docker image inspect` |
| Image (leg A) | `0.9.3` and `latest` both `sha256:b2904fdfc3dd…`, **unmoved** | `docker image inspect` |
| Harness in image | `rearch-counterparts` @ `19ae3da1` | clone inspected inside the image |

**The image is still current with the branch.** `git log --oneline 19ae3da1..HEAD -- rv-android/modules/`
is empty: the 13 commits made since the image was built are artifacts, campaign scaffold and
documentation, none of them harness code. This is the gh71 failure mode and it was re-checked on
2026-08-05 rather than assumed.

## 3. Gating checks — `scripts/preflight_runstart.py` (task 7.2)

Command, re-run on 2026-08-05 against the stored traces:

```bash
uv run python scripts/preflight_runstart.py --results results_smoke --manifest manifest.json
```

**Result: 9 PASS · 0 FAIL · 3 SKIP, exit 0 — `GATE: the campaign starts.`**

| Arm | `props_digest` | `preset`+`params` | `build.sha` | `corpus_basis` |
|---|---|---|---|---|
| `mop_on_llm_off` | SKIP | PASS — `preset=mop`, 4 keys | PASS — `9e948102` | PASS — `subset40:b60903ad…` |
| `mop_off_llm_off` | SKIP | PASS — `preset=mop`, 4 keys, 2 at jar default | PASS — `9e948102` | PASS — `subset40:b60903ad…` |
| `mop_on_llm_70` | SKIP | PASS — `preset=llm_mop`, 9 keys | PASS — `9e948102` | PASS — `subset40:b60903ad…` |

The three SKIPs are all check 1, `props_digest`, and are **by design** — the bar was corrected on
2026-08-05 rather than met. `_push_properties()` writes the file to a temporary path and unlinks it
after the push, so nothing survives for a digest comparison; reconstruction through the tool's own
code path did not reproduce any of the three echoed digests, while the same reconstruction *inside
the campaign image* produced bytes identical to the local tree — which rules out harness/image drift
and leaves the difference unexplained. **That loose end is recorded, not closed.**

It does not need to close. From stage 2 onward the jar aborts before step 1 on an unknown key, a
retired key, or a non-neutral value of an inactive feature, so a run that produced a trace at all has
already passed a stricter check than a digest comparison. What a digest would add over checks 2–4 is
detection of *undeclared* keys — exactly what the jar's own validation refuses.

`corpus_basis` present and matching is the authoritative verdict on the DSL parameter seam of task
2.6: it exercises the whole `RV_TOOLS` → `_parse_single_tool_spec` → `configure()` → `ape.properties`
→ `RUN_START` chain over the configuration the campaign will actually run.

## 4. Gating checks — the `ape` side's delegated device verification (task 7.2a)

**This section is the delegation's record.** Stage `rearch-07`'s own end-to-end smoke, its Docker
verification and the deployed half of its skew drill were removed on the rule that the APE-RV side
executes exactly once, in this change. `rearch-07` 8.1 ("the MOP artifact loads and a boost fires, on
the device") is discharged here and nowhere else.

Measured per run, through `aperv_tool.analysis.trace_ndjson` — the same reader `consolidate.py` and
`verify.py` use, so this is what the analysis will see:

| Application | Arm | `MOP_DATA` | `fmt` | `sourceDigest` | `wtgEdges` | `mopActivities` | steps | boosts | `decision_source=MOP` |
|---|---|---|---|---|---|---|---|---|---|
| smartpack | `mop_off_llm_off` *(control)* | loaded | 1 | `4798542d9844…` | 23 | 8 | 303 | **0** | **0** |
| smartpack | `mop_on_llm_70` | loaded | 1 | `4798542d9844…` | 23 | 8 | 234 | 15 | 2 |
| smartpack | `mop_on_llm_off` | loaded | 1 | `4798542d9844…` | 23 | 8 | 307 | 17 | 15 |
| freeotpplus | `mop_off_llm_off` *(control)* | loaded | 1 | `ffede8bd9a92…` | 86 | 7 | 292 | **0** | **0** |
| freeotpplus | `mop_on_llm_70` | loaded | 1 | `ffede8bd9a92…` | 86 | 7 | 227 | 150 | 66 |
| freeotpplus | `mop_on_llm_off` | loaded | 1 | `ffede8bd9a92…` | 86 | 7 | 273 | 185 | 88 |

Every clause of 7.2a holds, on **both** applications:

- `status=loaded`, `formatVersion=1`, non-empty `sourceDigest` — the three fields that distinguish a
  compact-artifact load from every prior format, and the only device-side evidence that `gh96`'s
  cutover actually took. Six of six runs.
- `wtgEdges > 0` **and** `mopActivities > 0`, so a load that succeeded on an artifact carrying nothing
  is not read as a pass.
- At least one step with a MOP boost on every MOP arm — the guidance mechanism firing, which a green
  `status=loaded` alone does not establish.
- On the control arm, **no boost and no `decision_source=MOP` in any step** — 0 of 303 and 0 of 292.

**The control is not a non-MOP arm.** It declares `"mop_data": "static_analysis"` like the other two
and loads the same artifact — identical `sourceDigest` within each application — with its five scoring
weights at `0`. Design D1 says so in as many words, as does INV-APV-29. So what must not reach the
control is *effect*, not the artifact, and the drill is stated as influence rather than as presence.
This is the same predicate validity gate 9.1 applies to the full campaign: the smoke checks in
miniature what the campaign checks at scale.

No arm reported `status=rejected`, which would have been the deployed skew failure and would have
blocked the campaign.

## 5. A published number that did not survive re-measurement

The 2026-08-05 session's handoff recorded `mop_on_llm_70` on smartpack as **108 steps, 2 boosts, 0
`decision_source=MOP`**. Re-measured from the stored trace: **234 steps, 15 boosts, 2
`decision_source=MOP`**. The `mop_on_llm_off` row of that same table reproduced exactly, so the error
was confined to one row.

The corrected figures are internally consistent three ways — `len(steps)` from the reader, `RUN_END.steps`,
and the heartbeat count in the logcat all read 234 — which the published figure was not. The direction
of the finding is unchanged and in fact strengthened: the guided arm boosts, the control does not.

## 6. Task integrity and coverage (task 7.3)

This also discharges `rearch-03` 8.4, whose "on-device smoke at the next scheduled rebuild" is this
rebuild.

| Application | Arm | State | `method_coverage` | `activities_coverage` | `methods_mop_reachable` | detected errors |
|---|---|---|---|---|---|---|
| smartpack | `mop_off_llm_off` | COMPLETED | 34.84 % | 81.82 % | 51.32 % | 0 |
| smartpack | `mop_on_llm_70` | COMPLETED | 22.19 % | 72.73 % | 26.32 % | 0 |
| smartpack | `mop_on_llm_off` | COMPLETED | 33.07 % | 100.0 % | 48.68 % | 0 |
| freeotpplus | `mop_off_llm_off` | COMPLETED | 28.33 % | 42.86 % | 21.65 % | 0 |
| freeotpplus | `mop_on_llm_70` | COMPLETED | 38.93 % | 100.0 % | 30.30 % | 0 |
| freeotpplus | `mop_on_llm_off` | COMPLETED | 39.40 % | 100.0 % | 31.17 % | 0 |

- **6 / 6 identity-distinct COMPLETED**, counted on `(apk_name, tool_config.name, tool_config.variant,
  repetition, timeout)` — never by grepping `tasks.json` for `COMPLETED`, which double-counts through
  `result.state_transitions[]`. That counting rule was learned from the 2026-06-19 regression.
- **Coverage > 0 on every run**, on all three metrics.
- **Zero `VerifyError`** in any of the six logcats. The instrumented APKs load and verify under ART.
- `coverage.csv` carries **2,852 rows**.

## 7. Recorded, never gating — evidence for the `ape` side (task 7.2b)

**Nothing in this section gates the campaign**, per design D11. It is stated here so a later reader
cannot mistake a heartbeat finding for a passed gate, nor read an absence below as a failure.

### Heartbeats (INV-SNK-14) — breadth across three arms

`gh94` 4.0–4.2 captured the primary record on its own standalone run, which exercised one arm. What
this adds is breadth. Counted four ways, because they fail differently:

| Application | Arm | raw `ApeRvHb` grep | parsed | distinct `s` | `StepRecord`s | distinct step `s` | sets identical | contiguous `1..N` |
|---|---|---|---|---|---|---|---|---|
| smartpack | `mop_off_llm_off` | 303 | 303 | 303 | 303 | 303 | yes | yes |
| smartpack | `mop_on_llm_70` | 234 | 234 | 234 | 234 | 234 | yes | yes |
| smartpack | `mop_on_llm_off` | 307 | 307 | 307 | 307 | 307 | yes | yes |
| freeotpplus | `mop_off_llm_off` | 292 | 292 | 292 | 292 | 292 | yes | yes |
| freeotpplus | `mop_on_llm_70` | 227 | 227 | 227 | 227 | 227 | yes | yes |
| freeotpplus | `mop_on_llm_off` | 273 | 273 | 273 | 273 | 273 | yes | yes |

**No disagreement, and no arm without heartbeats.** The `s` value sets are identical to the
`StepRecord` sets in all six runs, with no gap and no duplicate. The last heartbeat's `t` matches
`RUN_END.t_last_step` — for smartpack `mop_on_llm_off`, `s=307 t=299892` against
`"t_last_step": 299892`. An arm that produced no heartbeat where another did would have been a
difference between arms worth reporting; there is none.

### Sample-trace inventory — discharging `rearch-04` 9.1

| Clause | Status |
|---|---|
| MOP boost present | yes — §4, every MOP arm |
| At least one LLM call on `mop_on_llm_70` | yes — 142 (smartpack), 92 (freeotpplus) |
| Flushed final step | yes — `len(steps)` equals `RUN_END.steps` in all six runs, so the last step reached the file |
| `RUN_END` present | yes — all six, `reason=timeout` |
| LLM **error** | **yes, and this was not expected** — `result=breaker_open` ×2 with `trips` 1 and 2, plus `reason=timeout` ×2, on freeotpplus `mop_on_llm_70` |
| `no_match reason=dead_pair` | **yes, and this was not expected** — 37 across the two `llm_70` runs |

The last two rows are the finding of this section. Design D11 recorded them as "recorded if present
and not gated" on the reasoning that no arm can be made to *guarantee* either inside a reduced-timeout
smoke — the provision fired, and both appeared anyway. `rearch-04` 9.1 can therefore be discharged
**completely** rather than partially, on device evidence, without leaning on `gh94`'s golden-fixture
tests for the two format claims. Those tests remain the right home for the schema-level assertion.

A `dead_pair` record, verbatim and truncated:

```json
{"call":36,"mode":"random","tool":"click","qwen":[889,309],"px":[960,554],
 "result":"no_match","reason":"dead_pair","repair":"missing_y","mcls":"none",
 "ncls":"Button","ndist":41.01,"widgets":12,"tok":[1358,26],"ms":598}
```

**Where the traces are kept**, since they are also `rearch-04` 9.2's input:
`experimento-rearch-aperv/results_smoke/rearch_aperv_smoke/rearch_aperv_smoke/<apk>/<apk>__1__300__aperv:<arm>.trace`,
with a `.ndjson.gz` beside each. This tree is untracked and root-owned; it is never `git add`ed.

### What this section does *not* cover

`rearch-06` 5.1–5.3 (heap series over a 600 s standalone SATA run) is **out of scope** — a different
harness, a different granularity, explicitly not a gate. It is named here so the absence is not later
read as an omission. `rearch-04` 9.1a, the throughput gate, needs the pre-change jar run twice and is
a separate owner task; the smoke ran the new jar only.

## 8. Verdict

**The gate is open.** All gating checks pass: 9 PASS · 0 FAIL · 3 SKIP-by-design on 7.2, and every
clause of 7.2a holding on both applications and all three arms. Task integrity and coverage are clean.
The non-gating evidence of §7 reports no disagreement and two clauses discharged beyond expectation.

The campaign may launch **once the owner gives the explicit go-ahead**, which is a separate decision
from this gate and is not granted by this report.

---

*Re-measured 2026-08-05 from `results_smoke/`. Journal entry: `PREFLIGHT`, `calibracao/journal.jsonl`.*
