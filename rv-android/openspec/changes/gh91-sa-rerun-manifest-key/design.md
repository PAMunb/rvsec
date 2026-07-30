# Design: gh91-sa-rerun-manifest-key

## Context

The proposal fixes what must happen: re-analyse 30 APKs under the `Mneut` key from
`30_apks.csv`, and deliver the artefacts that release `ase-journal`'s upstream gate. This
document decides how the analysis is invoked, with which parameters, how the result is
validated before anyone touches the corpus, and how it reaches the regenerated CSVs.

The upstream change was verified to be on this path and not an earlier one:
`remove-package-detector`'s `proposal.md:23-28` records the owner's 2026-07-30 second-session
decision for the 164/163 route, and `:164-169` states the resulting dataset. The 133/134
scope discussed in `docs/20260730_verificacao_consistencia_remove_package_detector.md` §3 is
superseded by that same document's §14.3. `30_apks.csv` in this directory is byte-identical
to `ase-journal/docs/20260730_sa_rerun_164.csv` (sha256
`7ea67f52f69d4d574ef82c9a49d66982a8208bc52bcf6437ecf22445bb388297`), 30 rows.

One upstream item is open but does not reach this change: §2.5 of the same document finds a
hole in the neutralisation denylist — `trial` is absent, which costs
`com.phpbg.easysync.trial` — and the upstream recommendation is to leave it out, since
`trial` is a product variant rather than a Gradle build-type suffix. Admitting it would make
the list 31 APKs, not 30. The frozen list stands.

Constraints inherited from standing rules and from the owner's decisions:

- **No rv-android module is modified.** This is what forces D1 below.
- `rvsec-gator` is not modified (standing rule) and needs no modification:
  `RvsecAnalysisClient.java:88-90` resolves
  `filterPackage = (codePackage != null) ? codePackage : manifestPackage`.
- The `Mneut` column is authoritative and MUST NOT be recomputed. It was derived upstream and
  validated against adjudicated ground truth (gate: ≥90% of the adjudicated app code covered,
  zero foreign classes, calibration reproducing the frozen arms P=182/0 and M=88/119).
- The 30 JSONs are produced into a fresh directory. Installing them into the corpus is the
  owner's manual step.

Requirements in play: FR04 (static analysis), FR05 (reachability against MOP specs), FR06
(REACH output), FR14 (offline result processing).

## Architecture

```
30_apks.csv (frozen)          RV_ANDROID_NOVO_DATASET/APKS/  (348 uninstrumented)
   apk_id -> Mneut                        │
        │                                 │
        └──────────►  campaign runner   ◄─┘        rvsec-dataset-sa/logs/<id>.apk.log
                    (gh91_campaign.py)                    │  line 1 = original argv
          rounds 1-2 as capacity tiers, promotion         │  -> tier + measured duration
                            │                             │
                            ▼                             ▼
                     re-analysis driver (gh91_sa_rerun.py)
                            │
                            ▼
                  python lib/gator/gator a ... -clientParam codePackage=<Mneut>
                            │
                            ▼
        SA_RERUN_gh91/<apk>.json   +   logs/<apk>.log   +   REGISTRO.md
                            │
                            ▼
                    validation gate (per APK, mechanised)
                            │
                            ▼
          sa_rerun_record.csv + sha256 manifest + provenance note
                            │
                    ╌╌╌╌╌╌╌╌┴╌╌╌╌╌╌╌╌  manual, owner, outside this change
                            ▼
   APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/   ("STATIC_DIR" of the consolidation)
                            │
                            ▼
        experimento-20260706/scripts/consolidate_offline.sh
          phase 1 validate -> phase 2 regen (run_all.sh: 16 containers ->
          concat_vm -> concat_all) -> phase 3 audit (verify.py --full, C1-C4)
                            │
                            ▼
              {summary,coverage,errors}_regen.csv  --(manual promotion)-->  *_all.csv
```

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| re-analysis driver (`scripts/gh91_sa_rerun.py`) | Run one round: per-APK parameters, memory-budgeted concurrency, resume, argv logging | `30_apks.csv` + the 30 original log lines | JSONs + logs + `_progress/` |
| campaign runner (`scripts/gh91_campaign.py`) | Own the whole unattended run: the two capacity rounds, failure classification, promotion, move-aside before retry, `REGISTRO.md` | the driver | `REGISTRO.md` + a final exit code |
| `lib/gator/gator` | The analysis itself; filters classes by `-clientParam codePackage=` | APK + argv | `<apk>.json` |
| validation gate | Prove each JSON is complete and filtered by the intended key, before anything is copied | `SA_RERUN_gh91/` | pass/fail + deltas |
| record builder | Compute the `sa_*` block offline with `StaticAnalysisParser` | 30 JSONs | `sa_rerun_record.csv` |
| `consolidate_offline.sh` | Regenerate + audit the CSVs from the preserved logcats and the installed JSONs | corpus | `*_regen.csv` + `verification_report.md` |

## Goals / Non-Goals

**Goals:**
- Produce 30 JSONs analysed under `Mneut`, provably so.
- Produce the provenance the article's change needs to unblock.
- Leave the corpus untouched until the owner decides to install the results.

**Non-Goals:**
- Modifying any rv-android module. Explicitly excluded by the owner.
- Removing `PackageDetector`. Deferred to a separate later change.
- Re-running the dynamic experiment. Logcats are reused as-is.
- Re-analysing the other 189 APKs of the corpus.
- Touching `rvsec-gator` or rebuilding `rvsec-analysis-client.jar`.
- Installing the JSONs into the corpus, running the consolidation, or promoting
  `_regen.csv` → `_all.csv`. All manual, owner-performed, recorded here for reference.

## Decisions

**D1 — Invoke GATOR directly; do not go through `rv-static-analysis analyze`.**
The CLI has no `--code-package` (nor `--package`) option: its only source for the filter key
is `App(args.apk).code_package` (`rv_static_analysis/__main__.py:326`), which is backed by
`PackageDetector`. Passing `Mneut` through it would therefore require changing
`rv-android-core`, which is excluded. Invoking GATOR directly needs no change anywhere: the
command that `RVStaticAnalysisConfig.get_tool_command` (`config.py:336-410`) assembles is
fully self-contained, and `codePackage` is just one of its `-clientParam` arguments.
*Alternative rejected*: adding a `--code-package` flag to the CLI. Smaller than a table, but
still an edit to an rv-android module, and it buys nothing the direct invocation does not
already have.

**D2 — The command mirrors what `get_tool_command` builds, verbatim.**

```
<sys.executable> lib/gator/gator a
  -p <RV_ANDROID_NOVO_DATASET/APKS/<id>.apk>
  --client-jar lib/gator/rvsec-analysis-client.jar
  --out SA_RERUN_gh91/<id>.apk.json
  -client RvsecAnalysisClient
  -clientParam mopDir=<RVSEC_HOME>/rvsec/rvsec-mop/src/main/resources/jca
  -cgAlgorithm spark
  --timeout <per-APK>
  --jvm-memory <per-APK, UPPERCASE>
  -clientParam codePackage=<Mneut>
  -clientParam skipWtg=true
  -cgDelegation true
```

Five behaviours of the discarded wrapper the driver MUST replicate, each verified in code:

1. **`--jvm-memory` is upper-cased** — `config.py:390` applies `.upper()`, so GATOR receives
   `32G`, not `32g`.
2. **The timeout is doubled.** Besides GATOR's own `--timeout`, `static_analysis.py:257`
   wraps the call in `Command(..., timeout=analysis_timeout)`. Without an outer subprocess
   timeout a wedged JVM runs forever.
3. **`ANDROID_SDK_HOME` must be exported.** `lib/gator/gator:64` does
   `os.environ['ANDROID_SDK_HOME']` — a bare subscript, `KeyError` if unset. It is
   `ANDROID_SDK_HOME`, **not** `ANDROID_HOME`. Alternatively pass `--sdkpath`.
4. **Resume is by output-file existence.** `_execute_command` (`static_analysis.py:271-289`)
   skips when the output file exists. Note that `--force` cannot be relied on for this: it is
   declared at `rv_static_analysis/__main__.py:193,215` and **never read anywhere** in
   `modules/rv-static-analysis/src/` — a dead flag. The driver implements the skip itself.
5. **The launcher is invoked with `sys.executable`, not a literal `python`** —
   `config.py:359-372`, with the comment explaining why: a bare `python` fails on systems
   where `/usr/bin/python` is absent (clean Debian/Ubuntu, containers).

The post-parse that `rv-static-analysis` performed (`static_analysis.py:418`) becomes a
separate offline step: the `sa_*` numbers are computed from the JSONs with
`StaticAnalysisParser`, which is what `scripts/regenerate_results/regenerate_container.py`
already does.

**D3 — Analysis parameters mirror each APK's own original invocation, plus `--skip-wtg`.**
The original corpus was produced by `rvsec-dataset`'s Phase 7, which calls
`rv-static-analysis analyze` once per APK. The exact argv is preserved in the first line of
every `rvsec-dataset-sa/logs/<id>.apk.log`. Read for the 30 APKs of this change (verified
30/30), those lines fix both a constant set and a **per-APK** pair that must not be flattened.

Constant across all 30, **as recorded in the logs**: `--cg-algorithm spark`,
`--cg-delegation true`, `--mop-dir <RVSEC_HOME>/rvsec/rvsec-mop/src/main/resources/jca`, no
`--succ-depth`, and **no `--skip-wtg`** (absent in 0 of 30). `--force` is also present in all
30 log lines but is meaningless (see D2.4).

Per-APK `(memory, timeout)`:

| memory | timeout | apps |
|---|---|---|
| 120g | 5400 | 1 — `com.jerboa_87.apk` |
| 60g | 3600 | 1 — `app.pachli_50.apk` |
| 56g | 3600 | 1 — `org.wikipedia_50595.apk` |
| 32g | 3600 | 16 |
| 12g | 1800 | 11 |

The re-run MUST read each APK's own pair from its log line rather than apply a single
constant: a flat 1800 s would cut short the 19 APKs that originally needed more. Under
`--skip-wtg` such a run dies during the Soot/spark analysis, before the write, and produces
no JSON at all (`failed_timeout_no_json`) — a loud failure the gate catches. The quieter
case, a file truncated mid-write, is narrow but not impossible, which is why completeness is
judged by the sentinel rather than by whether the file parses (R5).

**`--skip-wtg` is a deliberate NEW deviation, not a preserved constant.** It appears in none
of the 30 original invocations. It is safe for these deliverables because the reprocessing
path consumes only the `reachability` section: an exhaustive sweep of `static_data.<attr>`
across `rv-coverage/src` and `rv-platform/src` returns exactly one attribute, `.classes`;
`Windows()` and `WindowTransitionGraph()` appear only as empty placeholders
(`result_processor.py:286`). It also buys budget: GATOR's write order is
`components → reachability → windows → transitions`, so skipping the WTG returns before the
most expensive tail — and this corpus is timeout-bound. Of the 30, **9 timed out originally**:
5 at 3600 s (`app.pachli`, `ch.rmy.android.http_shortcuts`, `com.darkrockstudios.app.securecamera`,
`com.github.livingwithhippos.unchained`, `it.niedermann.owncloud.notes`), 3 at 1800 s
(`de.markusfisch.android.binaryeye`, `swati4star.createpdf`, `org.glpi.inventory.agent`) and
1 at 5400 s (`com.jerboa`). Those 9 are exactly the 9 that carry `sa_transitions_count = 0`
today — they cleared `reachability` and died building the WTG. Recorded as R2.
*(Caveat for the record: rv-agent's `TransitionManager`/`NavigationGuidance` do consume the
WTG. These 30 JSONs must never feed rv-agent navigation.)*

**D4 — Concurrency is bounded by memory, not by a worker count.**
The host has 123.48 GiB of RAM (`MemAvailable` measured at 115.82 GiB) and 64 cores; five
concurrent workers at `32g` would demand 160 GB. The driver MUST schedule against the sum of
the per-APK memory values under a ≈100 GB cap: 8 × 12g = 96 GB, 3 × 32g = 96 GB; the
`56g`/`60g` APKs run alone within the cap, and the `120g` APK runs alone as a **recorded
exception above it**, justified by R4. The 8 × 12g figure is not a guess — it is
`SA_WORKERS=8`/`SA_JVM_MEMORY=12g` (`rvsec-dataset/config.py:394,397`), the configuration
that ran the original 348-APK sweep on this host. Each APK runs exactly once: the memory
tiers are a disjoint partition of the 30, not repeated passes. No tier ordering is imposed;
mixed packings such as `2×32g + 2×12g` are expected.

Budget: **≈10–11 h worst case**, against 25 h fully serialised. Two clarifications the
earlier draft conflated:

- The **25 h is the sum of timeout ceilings** (90 000 s exactly), not a measured duration.
- The **16.55 h** figure that appears in the upstream material is measured wall clock for the
  original run of these 30 (59 573 s, confirmed from both `rvsec-dataset-sa/_progress/*.json`
  and `ase-journal/dataset/dataset.csv`). Since all 9 timeouts occurred *in the WTG phase*
  and consumed 8.00 h of that 16.55 h, a realistic serial re-run under `--skip-wtg` is likely
  **5–9 h** — roughly the concurrent worst case. The scheduler may therefore buy little. That
  is accepted rather than measured: the smoke is infra-only and cannot settle it, and the
  scheduler is needed regardless — the alternative is not "no scheduler" but a single global
  `(memory, timeout)` pair, which D3 already rules out.

**D5 — Reuse `rvsec-dataset`'s sweeper rather than writing a driver from scratch (P1).**
`rvsec-dataset/src/rvsec_dataset/static_analysis/{sweep,runner}.py` already provides:
per-APK resumable progress (`sweep.py:29,75-106`, atomic via `os.replace`; 348 records on
disk), first-line-argv logging (`runner.py:217` — the very convention D3 reads back), a
memory guard (`sweep.py:353-373`), and per-call memory/timeout override
(`runner.py:174 analyze_one(row, jvm_memory=..., timeout=...)`). What it lacks is **two
pieces, not one**: the scheduler (`run_sweep` applies one global pair to the whole run) and
the argv — `build_command` (`runner.py:63-86`) assembles the `rv-static-analysis analyze`
invocation and must be replaced by the direct-GATOR argv of D2. `analyze_one`'s log capture
(`Popen(stdout=log)`, `runner.py:216-227` — the capture gate 3.3(b) depends on) and its
`sa_status`/`sa_analysis_seconds` classification are reused as-is. The dispatcher also
needs its **own memory guard**: `_concurrency_guard` is only invoked on the uniform
`workers × jvm` path (`sweep.py:576,597`) that the dispatcher replaces, and its API cannot
express heterogeneous packings.
*(Do not copy `_concurrency_guard`'s docstring: it claims "a modest headroom factor" while
the code is a bare `need > free`.)*

**D6 — Output goes to a fresh directory; installation is manual.**
The `.apk.json` does not record its own filtering key — its top-level `package` field is the
*manifest* package regardless of what was passed as `-clientParam codePackage=`. A corpus
analysed under one key is therefore indistinguishable by inspection from one analysed under
another. Writing to `SA_RERUN_gh91/` keeps the two provably separate, and the owner installs
the results into `APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/` — the directory the
consolidation reads — preserving each predecessor as `<apk>.json.pkgdet`.

**D7 — Execution is one unattended campaign script; no human and no model in the loop.**
The run is several sequential rounds spanning a night. Every round decision — which APKs
retry, at which budget, with which concurrency, when to stop — is deterministic and derivable
from what the previous round wrote to disk. Putting that logic in `scripts/gh91_campaign.py`
makes the campaign a `subprocess.wait()`; putting it in an agent loop makes it a
token-burning, non-reproducible one that also cannot survive the session. The campaign is
launched once, in the background, and reports on exit.
*Alternative rejected*: orchestrating the rounds from the session (a workflow, subagents, or
timed polling). It adds no capability the script lacks, cannot be replayed, and makes the
multi-hour GATOR waits the model's problem. Fast, genuinely parallel stages — the per-APK
gate assertions of group 3, building the record in group 4 — remain free to fan out.

**D8 — Durability comes from idempotence, not from detachment.**
`REGISTRO.md` and `_progress/<apk>.json` are flushed after every APK, and re-invoking the
same command must resume exactly where it stopped. That is what survives a power cut, a
reboot, or a bug in the campaign script itself — none of which detaching the process would
help with. The resume path is therefore verified *before* the campaign is launched for the
night (task 2.4), not assumed.

**D9 — Rounds are capacity tiers assigned from the previous run; failures are classified
before any retry is spent.**
Retrying a deterministic failure burns hours to reproduce it. Each APK's outcome is
classified from what the driver already records — `timed_out`, `returncode`, `sa_status`, the
presence of the sentinel, and the log tail:

| Class | Signals | Action |
|---|---|---|
| `COMPLETE` | JSON exists **and** carries `"complete": true` | done; never re-run |
| `TRANSIENT` | outer timeout, GATOR's own timeout (`rc` −50/206), `failed_timeout_no_json`, or `OutOfMemoryError`/`GC overhead limit` in the log tail | promote to the next round |
| `DETERMINISTIC` | non-zero `rc` without a timeout (Soot/apktool/JVM exception), `unparseable`, `failed_no_json` with `rc` 0, or a driver-level exception | **do not retry**; record and report |

**A round is a capacity configuration, and the 30 are pre-assigned to rounds by what Phase 7
already measured about them.** This is the owner's decision and it replaces an earlier draft
in which round 1 held all 30 and later rounds were retry-only. The argument against that
draft is decisive: the previous execution recorded, per APK, both the `(memory, timeout)` it
was given and the wall clock it took. That measurement *is* the assignment. Making an APK
discover its own requirement by failing first would spend 15–60 minutes per APK to learn
something already on disk.

| Round | Config | Budget | Concurrent | Members |
|---|---|---|---|---|
| 1 | `32g` / `3600 s` | 100 g | 3 | **27** — every APK whose Phase 7 tier was 12g or 32g |
| 2 | `120g` / `7200 s` | 100 g | 1 | **3** — `org.wikipedia` (56g), `app.pachli` (60g), `com.jerboa` (120g) — **plus anything promoted out of round 1** |

Concurrency is not configured separately: it falls out of the budget of D4. `3 × 32g = 96 g`
fits under 100 g; a single `120g` job exceeds it and therefore runs alone through the
dispatcher's R4 exception path. The two tiers Phase 7 used below 32g are folded into round 1
because `--jvm-memory` is a bare `-Xmx` with no `-Xms` (R4) — a lazy ceiling, not a
reservation — so giving a 12g APK 32g costs nothing but simplifies the campaign to two
configurations.

**Promotion, not retry-in-place.** An APK that fails round 1 joins round 2 and runs under
*round 2's* configuration. It is never re-attempted under the configuration that already
failed it. There is no round 3: round 2 is the host's memory ceiling, and its 7200 s is above
every pair Phase 7 recorded (max 5400 s) precisely because nothing follows it.

**Order within a round: cheapest first**, by the wall clock Phase 7 measured
(`prior_seconds`, read from `rvsec-dataset-sa/_progress/<apk>.json`). A round then delivers
its quick results early and surfaces a failure early, instead of after the longest job. This
ordering cannot cost wall clock for the exclusive `120g` jobs, which overlap with nothing
regardless of when they start.

Budget from the Phase 7 durations — an over-estimate, since that run included the WTG this
one skips: round 1 ≈ **4.5 h** at 3 concurrent, round 2 ≈ **3.1 h** serial.

**D10 — `REGISTRO.md` is both the audit trail and the live progress view.**
Written incrementally under `SA_RERUN_gh91/`, flushed after **every** APK, so
`tail REGISTRO.md` answers "where is it?" at any moment without touching the running process
and without a second monitoring mechanism. Per APK per round it records: the exact argv,
`jvm_memory`, `timeout`, `sa_status`, wall-clock seconds, `returncode`, `timed_out`, whether
the JSON exists and carries `"complete": true`, the log tail on failure, and the
`TRANSIENT`/`DETERMINISTIC` verdict above. `_progress/<apk>.json` stays as the
machine-readable record; `REGISTRO.md` is the human one, and neither is derived from the
other after the fact.

## Consolidation — the existing pipeline, and the trap

Recorded here because the obvious command is the wrong one.

**Do not use `rv-platform run --process-results`.** `consolidate_offline.sh` opens with the
reason: the consolidation must be rebuilt from the preserved `.logcat` files, *"NÃO dos CSVs
do container — o resume zera T=60/T=180 no CSV, gotcha do `result_processor`"*. Following
that route would silently produce wrong data at the 60 s and 180 s timeouts. It is also not
recursive: `_process_results_standalone` (`rv-platform/__main__.py:472-497`) takes one
directory containing `tasks.json` and writes back into it, while the tree has 16 such
containers.

**The correct entry point already exists**, but needs an override:

```bash
RESULTS_ROOT=/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS \
  bash experimento-20260706/scripts/consolidate_offline.sh
```

The override is mandatory: the script's default `RESULTS_ROOT` is
`RESULTADOS_experimento-20260706/`, a directory that does not exist — the real tree is
`RESULTS/` — and the path guard (`consolidate_offline.sh:48`) aborts with exit 2. Fixing
that stale default (and the same name at `experimento-20260706/README.md:122`) is
experimento-20260706 housekeeping, outside this change.

It fixes `STATIC_DIR` to `APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/`, knows
`TARGET_TOTAL=21681` (5544 + 5544 + 5445 + 5148 across the four VMs), and runs three phases:
validation (COMPLETED dedup by identity + `VerifyError` gate), regeneration
(`scripts/regenerate_results/run_all.sh`: 16 containers → `concat_vm.py` → `concat_all.py`),
and audit (`verify.py --full`, checks C1–C4). Promotion `_regen.csv` → `_all.csv` is a
separate manual step, gated by the audit.

Naming, so the invariants below point at real files: in `RV_ANDROID_NOVO_DATASET/RESULTS/`
the consolidated file is **`summary_all.csv`** (21 681 data rows). In `ase-journal`,
`summary_bck.csv` carries those 21 681 rows (the 219-app *executed* grid) while
`summary.csv` carries 17 919 (the 181-app *analysis* basis). `reduce_to_181.py` must be
re-run to derive the 181-app files from the regenerated `_bck` ones.

## Error Handling

| Error | Source | Strategy | Recovery |
|---|---|---|---|
| Analysis timeout | GATOR / driver | Under `--skip-wtg` the write happens right after `reachability` and GATOR returns, so a timeout lands *before* it: the expected outcome is `failed_timeout_no_json` (no file), not a partial one. Classify and record | Escalate that APK above its original pair — but see R4: for `com.jerboa` there is no memory headroom left |
| JSON without `"complete": true` | truncated write | **Hard stop for that APK.** Do not let the parser's bracket recovery mask it | Re-run with a larger timeout; record the deviation |
| Classes outside `Mneut`, or wrong `Filter package:` line in the log | wrong key reached GATOR | **Hard stop.** The class assertion catches a *wider* wrong key; the log line catches a *narrower* one (gate item 3) | Fix the driver, re-run that APK |
| `sa_reaches_mop = False` after re-analysis | narrower scope pushed the JCA surface out of the key | **Hard stop.** Not fixable here | Report back — it shrinks the paper's 164/163 |
| A retry round silently **skips** a failed APK | resume is by output-file existence, and any JSON left behind — partial or complete-but-superseded — satisfies it | Before each retry the campaign moves that APK's JSON and log aside (keeping them — they are provenance) and re-runs with `--rerun --only <apk>` | See R5 |
| Deterministic failure retried | classifying every failure as a timeout | Classify per D9 before spending a round | Report; do not retry |

## Risks / Trade-offs

- **R1 — The scope narrows sharply in the multi-module apps.** Twelve of the 30 shrink; see
  `proposal.md` §Impact for the measured list. The fossify collapse is `org.fossify.commons`
  leaving the scope. → *Mitigation*: the `sa_reaches_mop` gate catches the case where the
  narrowing removes the monitored surface entirely; the deflation itself is the accepted cost
  of a declared scope and must be stated as a construct limitation wherever these numbers are
  used.
- **R2 — `--skip-wtg` makes the 30 JSONs structurally different beyond the key.**
  `transitions: []` and window ids from the `100000+` fallback range. → *Mitigation*:
  verified irrelevant for coverage and violations, which read `reachability` and the logcat.
  The exposure is smaller than it looks: 9 of the 30 already carry `sa_transitions_count = 0`,
  having timed out before the WTG originally. **Precision matters here**: only
  `sa_transitions_count` is empty by construction. `sa_windows_count` **is populated** —
  `RvsecAnalysisClient.java:165-183` performs the full `writer.write(..., preWtgWindows, null)`
  and only then returns, so the JSON carries components → reachability → windows →
  `transitions: []` → `"complete": true`. The correct caveat is that `sa_windows_count`
  derives from `prepareWindows(output, new HashMap<>(), null)` and may differ from the
  post-WTG set, with fallback window ids. Reporting it as "empty by construction" would
  mislead the paper side into discarding a real measurement. For the record (do not "fix" —
  the gator is not touched): the comment at `RvsecAnalysisClient.java:156-164` claiming the
  pre-WTG write carries "NO sentinel" is stale and wrong — `JsonReportWriter.write()` emits
  the sentinel unconditionally (`JsonReportWriter.java:111`), so under `--skip-wtg` the file
  written already carries `"complete": true`. The writer is authoritative.
  **Measured 2026-07-30 — this is now confirmed, not inferred.** All 30 predecessor JSONs in
  `STATIC_DIR` carry `"complete": true`, *including the 9 that timed out in the WTG*
  (`app.pachli` 2466 classes / 16 811 methods, `ch.rmy.android.http_shortcuts` 7139 / 33 181,
  `com.jerboa` 140 / 515 — all with `transitions` empty **and** the sentinel present). The
  cause is the deliberate pre-WTG write at `RvsecAnalysisClient.java:155-171`, whose own
  comment states the intent: *"Write JSON with reachability FIRST (survives timeout during
  WTG)"*. The smoke (task 2.1) confirms the same on a fresh run: `"complete": true`,
  `transitions: []`, and `windows` populated with 5 entries — the non-emptiness this risk
  insists on.
- **R3 — 5 apps get a *wider* key** (`app.pachli` ⊃ `app.pachli.core`, `org.wikipedia`,
  `net.osmtracker`, `swati4star.createpdf`, `com.jerboa`). → *Mitigation*: numerators already
  exist in the logcats (verified upstream); the per-app record captures the new denominator.
  **Measured caveat**: of the five, only `org.wikipedia` shows a measurable delta in the
  current JSONs (0 → 1139 classes under the CSV's own two keys); the other four are
  pre-filtered narrow, so their growth genuinely cannot be measured before the re-run. And
  `org.wikipedia_50595.apk` carries a provenance defect: `30_apks.csv` records its
  `detected_package` as `org.wikipedia.diff`, but the JSON on disk contains **zero** classes
  under `.diff` and was in fact filtered by `org.wikipedia.feed`. Any "delta against the
  previous JSON" for that app is comparing against a key that was never applied.
- **R4 — The 120g tier is at the edge of the host, and its escalation path is a dead end.**
  `MemAvailable` is 115.82 GiB, below the 120 GiB the `com.jerboa` tier requests; the
  project's own `_concurrency_guard` (`sweep.py:353-373`) computes `need=120 > free=115.8`
  and refuses without `--force`. And since `com.jerboa` is already at 120g/5400, "escalate
  above the original pair" is executable in time but **not in memory**. → *Mitigation*:
  `--jvm-memory` becomes a bare `-Xmx` with no `-Xms` (`lib/gator/gator:76-77`), a lazy
  ceiling rather than a reservation, and the original 120g run completed on this host
  (`_progress/com.jerboa_87.apk.json`: `complete`, 5400.4 s, killed in the WTG, no OOM).
  Furthermore `RvsecAnalysisClient.java:109` calls `extractClasses(filterPackage)` *after*
  `GUIAnalysisOutput` is built, so peak heap is essentially `codePackage`-independent — the
  widening is a runtime and JSON-size risk, not a heap risk. The ladder is therefore **kept
  exactly as Phase 7 recorded it and is not re-derived**. It was calibrated with the WTG
  **enabled**, so under `--skip-wtg` 120g is probably a large over-reservation — but nothing
  available here can measure that safely: the smoke is infra-only on a 4 MB APK, and guessing
  a lower ceiling would risk an OOM in a 5400 s run whose only host-proven configuration is
  the one being replaced. The payoff would be small in any case: `com.jerboa` is one APK, and
  the most a lower ceiling could buy is one extra concurrent job while it runs.

- **R5 — A partial JSON would defeat resume and make the retry rounds a no-op — but the
  window for one is narrow.** The driver resumes by output-file existence (D2.4), and a JSON
  that is partial still *parses*, because the loader repairs truncation via bracket recovery
  (`runner.py:106-127`). If such a file existed, round 2 would skip exactly the APKs round 1
  failed and the campaign would "converge" having analysed nothing.
  **Magnitude, corrected against measurement (2026-07-30).** An earlier draft of this risk
  asserted that a timed-out run *leaves* a partial JSON. That is not what the corpus shows: a
  WTG timeout leaves a **complete** file, sentinel included, because the pre-WTG write has
  already closed and fsynced it (R2). A genuinely partial file requires the kill to land
  inside the write window itself, which is seconds. Under `--skip-wtg` the exposure is smaller
  still: GATOR writes immediately after `reachability` and returns
  (`RvsecAnalysisClient.java:179-183`), so a timeout now lands during the Soot/spark analysis,
  *before* any write — its outcome is `failed_timeout_no_json`, no file at all, which resume
  handles correctly by construction.
  → *Mitigation, unchanged*: the two guards cost a 512-byte read and one `os.replace`, so
  they stay regardless of the reduced probability — the campaign moves the failed APK's JSON
  and log aside before each retry
  and re-runs with `--rerun --only <apk>`; `run_one` additionally pre-cleans its target JSON,
  so `--rerun` is safe. The success criterion is never "it parses" and never `sa_status ==
  complete` alone: it is the `"complete": true` sentinel, which bracket recovery can never
  synthesise — the recovery closes the object at the last `]`, discarding the trailing
  `,"complete":true` by construction.

## Testing Strategy

| Layer | Scope | What it covers |
|---|---|---|
| Smoke | 1 APK, outside the 30 | `apks_examples/cryptoapp.apk` (`br.unb.cic.cryptoapp`, ~4 MB, 6 dex): the driver's plumbing — argv assembly, `ANDROID_SDK_HOME` resolution, client jar + `mopDir`, output path, `"complete": true`, `transitions: []` under `skipWtg=true`, the `Filter package:` line reaching the log, resume + progress record |
| Resume | campaign, no GATOR | Kill the campaign mid-round and re-invoke the identical command: it must pick up where it stopped and must **not** skip an APK whose JSON is partial (R5). Verified before the campaign is launched for the night, since this is the only property that makes an unattended overnight run recoverable |
| Gate (mechanised) | all 30 | The four assertions of §Validation gate |
| Audit | corpus | `verify.py --full` (C1–C4), run by `consolidate_offline.sh` |

The smoke is deliberately **not** one of the 30, and deliberately tiny. Its job is to prove
the driver, not the corpus: a real APK from the list would cost hours and would still
establish nothing the gate does not assert for all 30 afterwards. It writes **outside** the
deliverable directory, so gate assertion 1 keeps counting exactly 30 JSONs. It is also the
cheapest available confirmation of R2's claim that `JsonReportWriter` emits the
`"complete": true` sentinel even when the WTG is skipped.

**Measured 2026-07-30.** The smoke ran in 28.7 s (`rc=0`, `sa_status=complete`) and settled
every item it was designed to settle: the JSON carries `"complete": true`, `transitions: []`
and `windows` with 5 entries; `reachability` holds 16 classes / 106 methods, of which 32
carry `reachesTarget`, so gate 3.5's machinery has a real denominator to read; the log
carries `[RvsecAnalysisClient] Filter package: br.unb.cic.cryptoapp` — the evidence gate
3.3(b) reads back; re-invoking `--smoke` printed `nothing to do`, exercising resume and the
`_progress/` record. The gate's `has_sentinel` returns `True` on that file and `False` on a
20 KB-truncated copy of it, so the completeness check discriminates in practice and not only
in principle.

**The gate was also measured against the 30 predecessor JSONs**, which were analysed under
the *old* key and must therefore fail it. It flags exactly **12** apps on assertion 3.3(a),
matching `proposal.md` §Impact app for app and count for count (`org.fossify.paint` 108,
`voicerecorder` 199, `keyboard` 223, `math` 285, `notes` 394, `messages` 717, `musicplayer`
721, `calendar` 1071, `com.afkanerd.deku` 505, `binaryeye` 382,
`ch.rmy.android.http_shortcuts` 7029, `ua.com.radiokot.photoprism` 3007), while 3.2, 3.4 and
3.5 pass on all 30 as they should. A probe that rewrote one log with the *narrower* key
`app.pachli.core` is caught by 3.3(b) and, as predicted, **not** by 3.3(a) — the precise
reason the assertion has two halves.

No unit tests are added: no module changes.

## Validation gate

Every check runs on `SA_RERUN_gh91/` **before** anything is copied into the corpus. Each is
a script assertion with an exit code, not a checkbox.

1. **Cardinality** — exactly 30 JSONs produced, one per row of `30_apks.csv`.
2. **Completeness** — every JSON carries the `"complete": true` sentinel that
   `JsonReportWriter` emits at the end of `write()`. This is the objective criterion for
   "complete": the parser recovers truncated JSON via bracket repair
   (`static_analysis_parser.py:275-292`), so a partial file parses cleanly and would
   otherwise pass unnoticed.
3. **Key applied** — two assertions per APK: (a) **0 classes outside its `Mneut`** and
   **>0 inside**, using the parser's real semantics (substring match after
   `SignatureNormalizer`, `static_analysis_parser.py:360`); (b) the run's own log carries
   `[RvsecAnalysisClient] Filter package: <Mneut>` — printed at
   `RvsecAnalysisClient.java:105-107` and captured because the driver logs GATOR stdout
   (task 1.5). (b) exists because (a) alone cannot detect a *narrower* wrong key: GATOR
   filters by `startsWith` (`isAppClass`, `RvsecAnalysisClient.java:277-286`), so a run
   filtered by e.g. `app.pachli.core` still yields 0 classes outside `app.pachli` — the
   exact failure mode the current corpus exhibits in the five widening apps. The JSON does
   not record its filtering key; the log does. The JSON's top-level `package` field is
   additionally checked against the expected manifest package, which guards against having
   analysed the wrong APK.
4. **MOP surface preserved** — all 30 keep `sa_reaches_mop = True` with a non-empty
   reaches-MOP denominator. **Hard stop** on any failure. This is computable from the new
   JSON alone (`reachability[].methods[].reachesTarget`) and does not require the
   consolidation to have run.

Additionally recorded, not gated: the observed denominator delta per app against its
predecessor JSON — expected **12 shrink, 13 verified unchanged, 5 widen** (of the five,
only `org.wikipedia` is measurable today; the other four are pre-filtered narrow), with
the caveats of R3.

## Deliverables for the article's repository

Delivered in **two stages** — upstream 0.2 is released in full only after stage 2.

**Stage 1 — produced by group 4, delivered at task 4.7:**

- The per-app record, whose default name and location upstream gives as
  `dataset/pkgdet_validation/sa_rerun_record.csv` — *"name confirmed at apply"*
  (`remove-package-detector/tasks.md:26-27`), so treat it as a default, not as frozen. Beyond
  `apk`, key used, `sa_reaches_mop` and denominator size it MUST carry the exact per-APK argv
  and the full key-dependent block, so the paper side can update `dataset.csv` and recompute
  `sa_mismatch` without re-reading the JSONs: `sa_classes`, `sa_methods`,
  `sa_methods_reachable`, `sa_reaches_mop`, `sa_directly_reaches_mop`, `sa_methods_reaches_mop`,
  `sa_methods_directly_reaches_mop`, `sa_num_activities`, `sa_num_services`,
  `sa_num_receivers`, `sa_num_providers`, `sa_windows_count`, `sa_transitions_count`,
  `sa_components_count`, `sa_analysis_seconds`, `sa_engine` (constant `gator`), and
  `sa_status` from the closed vocabulary the dataset uses: `complete` /
  `partial_empty_reachability` / `failed_timeout_no_json`.
- Provenance: exact command, rv-android commit hash, date, and an explicit note that the
  re-run was WTG-skipped — with R2's precision about which column that actually empties.
- The sha256 manifests of task 4.4: the 30 new JSONs, plus the pre-installation state of
  `STATIC_DIR` (219 JSONs), so the owner's copy step can be proven to have touched exactly
  30 files.

**Stage 2 — produced by the owner's manual group 5, delivered at task 5.5:**

- The regenerated `summary`/`coverage`/`errors` CSVs **with sha256 pins**, so the paper side
  can re-freeze its `_bck` executed record (upstream task 0.3(e)).
- The 30 preserved `<apk>.json.pkgdet` files (created by the copy step 5.1).
