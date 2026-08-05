# Proposal: Empirical gate for the APE-RV re-architecture merge

**GitHub Issue**: #97
**Track**: Full SDD
**Merge condition for**: the `phtcosta/ape` `rearch` line (stages `rearch-01`…`rearch-07`), owner
decision of 2026-08-03, roadmap item 8.

## Why

The re-architecture rewrites the run kernel of the tool that produces this project's primary
experimental results, and every one of its seven stage gates is host- or JVM-level. The parity
oracle is decision-level and enters below `adjustActionsByGUITree()` (`StatefulAgent.java:1475-1478`),
so it never executes the scoring pipeline, GUITree building, model release or recovery. No task in
any of the seven changes measures coverage, activities visited, monitored-operation violations or
steps per run on real applications. A gate that does not execute the changed code is green by
construction.

That gap has already cost this project twice, in both directions. In **gh71** a stale jar read the
old schema key, so the monitored-operation boost fired in 0 of 169 applications and 0 of 147,153
evaluations; it surfaced only in post-hoc analysis of a 2,028-task campaign, and a second campaign
was needed to validate the fix. The mitigation then adopted detects a *wrong* jar, not a *worse* one.
In the other direction, on 2026-06-19 an unpaired 16-application smoke showed a "catastrophic"
−4.7 pp drop for `sata_mop` that, paired at n≈70, was an exact tie. Run-level noise alone is
−0.743 pp of `cov_mop` (p=0.0099) between campaigns.

**Half the measurement is already paid for.** The E3 decisive run executed on the roadmap's baseline
commit (`5dcf2259…`, jar `386ce08d…`, image `phtcosta/rvandroid:0.9.3`, ID
`sha256:b2904fdfc3dd…aedec`): 360 runs over 40 applications, three arms, three repetitions, 1800 s,
with `experimento-e3-decisiva/per_apk_paired.csv` and its results tree versioned. The marginal cost
of the gate is one post-rewrite campaign of the same shape.

**One confound is structural and known in advance.** `gh96-mop-artifact-derivation` changed the
monitored-operation substrate's semantics deliberately — flagged widgets rise 3,733 → 4,965 over the
pinned 345-application corpus and every previously flagged widget moves tier — and its own design
forbids mixing arms across that cut. Comparing levels of `cov_mop`, `mop_unique` or `mop_total`
between the two campaigns therefore measures the rewrite and an intentional substrate change added
together. The decision rule below resolves this by construction rather than by adjustment after the
fact, and it is frozen by sha256 before any post-rewrite run starts.

**This is a before/after comparison, not an A/B test.** Leg A is the E3 decisive run of
2026-08-01/02, frozen and not re-runnable; leg B executes days later, on a different image and a
different jar. There is no concurrent or randomised assignment of applications to legs — the pairing
is by application across two campaigns separated in time, and the one confound that matters is
declared in advance and routed around by the choice of arm (D1), not balanced away by design. The
change's name reads "ab" for *leg A / leg B*, the vocabulary used throughout these artifacts; it does
not denote an A/B test, and no claim made here rests on one. Leg A is not a concurrent variant but a
finished experiment — the E3 decisive run of 2026-08-01/02, preserved in `experimento-e3-decisiva/`
— and it is precisely because it had already run that it serves as a baseline rather than as an arm.
The abbreviation does appear in the campaign scaffold's descriptive headers, where `README.md`,
`docker-compose.yml` and `scripts/monitor.sh` each describe leg B of the "A/B gate"; in that sense —
leg A against leg B — it is accurate and is left standing. What is ruled out is the inferential
sense: a reader who read randomised concurrent assignment into the name would credit this gate with
a control it does not have, and would misjudge how much of the difference the confound can explain.

## What Changes

- **A campaign directory**, `experimento-rearch-aperv/`, modelled on `experimento-e3-decisiva/` —
  `README.md`, `docker-compose.yml`,
  `filters10/batch_00..09.txt` (the same deterministic alphabetical split of `calibracao/subset40.txt`,
  in blocks of 4 after amendment 01; leg A's own 8×5 split is preserved untouched in `filters/`),
  a monitor script and its consolidated outputs. The grid is **identical to E3 by requirement, not by
  preference**: the same three arms (`mop_on_llm_off`, `mop_off_llm_off`, `mop_on_llm_70`), the same
  40 applications, 3 repetitions, 1800 s — 10 containers after amendment 01, which changed the
  partition and no element of the grid. The baseline's per-application value is a
  three-replica mean, so a reduced-replica second leg would make the paired difference
  asymmetrically noisier — which is the 2026-06-19 failure mode the gate exists to prevent.

- **The analysis scripts are copied into the campaign directory and adapted**, not reused in place.
  `consolidate_cal.py`, `verify_iteration.py`, `multiarm_stats.py` and `stats_utils.py` are
  stdlib-only and self-contained, but they parse the legacy `[APE-*]` trace family, which the
  stage-4 jar no longer emits. The copies read traces through `analysis/trace_ndjson.py`
  (`gh94`'s deliverable) while their logcat and `tasks.json` paths — the source of every headline
  outcome — stay unchanged, so the two legs remain column- and aggregation-identical. The originals
  under `experimento-cal/scripts/` are not edited, adapted or deleted (`gh94` INV-APV-55).

- **A three-part decision rule, frozen before the campaign.** **G1** (blocking) compares the E3
  baseline against the new campaign on `mop_off_llm_off` alone, paired by application (n=40), over
  `cov_method`, `cov_act`, `cov_mop`, `mop_unique` and `mop_total`. That arm zeroes the five
  monitored-operation weights and disables the activity trigger, so `gh96`'s substrate change cannot
  reach its behaviour — a fact the E3 validity gate already measured (`decision_source=MOP` == 0 and
  `mop=` == 0 in every step). **G2** (blocking) requires the within-campaign contrast
  `mop_on_llm_off` − `mop_off_llm_off` on `cov_act` to remain positive with a CI excluding zero
  (E3: +14.9 pp, CI95 [7.75, 22.04]); it is a sign test on the guidance mechanism, so it survives the
  substrate cut and catches a rewrite that broke monitored-operation guidance. **G3** (descriptive)
  reports the monitored-operation levels of the guided arms beside the expected displacement computed
  host-side before the freeze. Margins are derived from the E3 replica dispersion in
  `experimento-e3-decisiva/results/*/coverage.csv`, floored at 1.5 pp for the percentage outcomes.

- **A blocking pre-flight, executed as the smoke's acceptance criterion.** Three checks read from the
  first line of one trace per arm: `props_digest` equals the digest of the `ape.properties` the
  harness pushed; `preset` equals the arm's declared preset and every override key appears in `params`
  with its declared value; `build.sha` equals the `rearch` commit built. The third is load-bearing —
  `docker/rvandroid/Dockerfile` clones `phtcosta/ape` on its default branch with no SHA pin, and the
  `rearch` jar arrives by bind-mount, so two jars exist in the container and `RUN_START.build`
  is the only discriminator. The pre-flight is a post-hoc read by an operator script and never enters
  `tool.py` or any runtime path: `run-spec` INV-RUN-03 declares `RUN_START` write-only at level 0.
  This also discharges the one execution `gh95` deferred here — the proof that the deployed jar
  honours `ape.preset`.

- **The smoke is the `ape` side's only device execution, so it carries that side's device
  obligations explicitly.** `rearch-07`'s deployed verification is checked here (MOP artifact loaded
  with `formatVersion=1` and a non-empty `sourceDigest`, a boost firing, and nothing of the sort on
  the control arm) and it gates; `rearch-04`'s heartbeat evidence and sample trace are harvested here
  and do **not** gate, because this campaign's readers never look at them. Which obligation is folded,
  which stays a separate owner task and which is out of scope is tabulated in design D11 — including
  the two the smoke cannot honestly cover: the throughput gate needs the pre-change jar, and the heap
  series belongs to a different harness.

- **The build supplies its own revision stamp.** `git-commit-id-maven-plugin` cannot read a git
  worktree's `HEAD` and stamps the main checkout's master instead, which would leave the pre-flight's
  load-bearing check comparing a master-stamped jar against an image whose own jar is built from that
  same master — green, and blind to the failure it exists to catch. The jar is built with the stamp
  passed in and the plugin skipped (design D10).

- **New**: the harness pushes `ape.corpusBasis=<corpus-id>:<sha256>` when a corpus manifest is
  configured, echoed unread in `RUN_START`. The `ape` `run-spec` capability already recognises the
  key and carries the scenario written for the harness pushing it; nothing on this side writes it
  today. It exists because this study has counted its analysis basis as 163, 181 and 219
  applications in different documents, and one hash per run ends the re-derivation.

- **The image is a new tag, `phtcosta/rvandroid:0.9.3-rearch`.** Rebuilding `0.9.3` in place would
  make the two legs indistinguishable by tag, which collides with the issue's first acceptance
  criterion and reproduces gh71's shape at the image layer. Both image IDs are pinned in the
  pre-registration document, whose sha256 is frozen in `calibracao/journal.jsonl` before launch.

- **The result is reported whatever it says**, with its CI, including a tie. The campaign executes
  only after every change lands on both sides, and the gate's verdict is what unblocks the merge of
  `rearch-counterparts` into `modules`.

## Capabilities

### New Capabilities

_None._

### Modified Capabilities

- `aperv`: one **added** requirement covering the corpus-basis property the harness pushes and the
  provenance it records. Nothing else in the capability changes.

**No `calibration-control` delta.** Its requirements are written about `preflight.py`,
`smoke_check.py` and the `iterN/` layout of `experimento-cal/`, which is a finished campaign's
scaffold and a frozen-corpus reader. Broadening them to cover a campaign that copies rather than
reuses them would document the opposite of what happens. The gate's protocol lives in this change's
design, tasks and pre-registration document, which is what the issue's own characterisation calls
for — a measurement instrument, not new system behaviour.

**No `experiment` or `platform` delta.** The campaign runs through `rv-experiment`/`rv-platform`
unchanged, with the emulator lifecycle owned entirely by the platform.

## Impact

**Modules**: `modules/aperv-tool` only — `src/aperv_tool/tools/aperv/tool.py` (`_push_properties`
gains the corpus-basis line) and its tests. The campaign directory and its adapted scripts are
experiment scaffold, not module code.

**Requirements**: FR18 and FR19 (tool execution and configuration) for the pushed property; FR11 and
FR13 (violation and coverage analysis over recorded artifacts) for the consolidation and comparison;
NFR06 (observability) for the pre-flight and provenance; NFR08 for the pre-registration record.

**Spec composition**: the corpus-basis requirement is **ADDED**, not folded into
`ape.properties Generation`. That requirement is already contested by three unsynced changes —
`gh94`, `gh95` and `gh96` all carry MODIFIED blocks over it — and a MODIFIED block replaces the whole
requirement at archive time. An added requirement composes in any archive order.

**Depends on**, and executes only after: `gh94` (its `analysis/trace_ndjson.py` is what the adapted
scripts read, and its gzip collection step applies to the campaign's traces), `gh95` (the arms must
resolve as `preset + overrides` for the pre-flight to have anything to check), `gh96` (already
implemented here; its substrate change is what G1 and G3 are shaped around), and stages
`rearch-03`…`rearch-07` on the `ape` side. The jar is bind-mounted from the `ape-rearch` worktree
after the Java side completes; the image is built and pushed after all of it.

**Timing**: the issue's window — *capture before stage 4, or after `trace_ndjson.py` exists* —
resolves to the second horn. Stages 4 through 7 are unstarted on the `ape` side and the campaign runs
last by design, so the capture is necessarily post-stage-4 and `gh94` is a precondition rather than a
race. The urgency in the issue is about designing and freezing the plan early, not about capturing
early.

**Frozen artifacts**: `experimento-e3-decisiva/` and `docs/20260730_preregistro_corrida_decisiva.md`
are read, never modified. The E3 `README.md` still says the run was not executed, which it was
(2026-08-01 15:43Z → 2026-08-02, 360 runs, results in `docs/20260802_resultados_corrida_decisiva.md`);
that staleness is recorded here rather than repaired, because the directory is a frozen artifact.
