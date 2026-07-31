# Tasks: gh91-sa-rerun-manifest-key

<!--
Dispatch notes (docs/WORKFLOW.md §5):
- Group 0 is CLOSED: the blocking unknowns were answered from disk and folded into design.md.
- Groups 1-4 are the operational run and are sequential by construction:
  driver (1) -> campaign (2) -> gate (3) -> record and delivery (4).
- The gate (3) is a hard stop. Group 4 MUST NOT start until every assertion in 3 passes.
- Group 5 is the owner's manual handoff, listed for completeness. It is NOT executed by
  this change; it is the instruction sheet the change hands over.
- The only code this change writes lives under `scripts/` (the driver, the campaign runner
  and the gate). No rv-android module is modified, so there are no delta specs and no unit
  tests. Removing PackageDetector is a separate, later change.
- Within group 2, tasks 2.0a-2.0e are code and MUST land before the smoke (2.1); 2.3
  (resume verification) MUST pass before the launch (2.4).
- Critical path: 0 -> 1 -> 2 -> 3 -> 4.
-->

## 0. Blocking unknowns — RESOLVED

- [x] 0.1 Input APKs: `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS/` — 348
      uninstrumented APKs, all 30 present. Line 1 of each
      `rvsec-dataset-sa/logs/<id>.apk.log` names `rvsec-dataset/head_apks/` as the artefact
      Phase 7 analysed; `APKS/` is its content-equivalent (identical filenames and sha256
      for all 348), which is the actual provenance argument. Never the
      `APKS_INSTRUMENTED_*` copies
- [x] 0.2 The JSONs the consolidation reads live in the **flat**
      `RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/` (219
      `.json`, one per app), fixed as `STATIC_DIR` by
      `experimento-20260706/scripts/consolidate_offline.sh` and opened at
      `scripts/regenerate_results/regenerate_container.py:114`. Verified byte-identical to
      the production output in `rvsec-dataset/static_analysis/`. The copies in
      `RESULTS/m*/results/exp_*/exp_*/<apk>/` are NOT read by the consolidation
- [x] 0.3 Gate criteria mapped against `ase-journal/openspec/changes/remove-package-detector/tasks.md`
      group 0. Honest mapping: upstream 0.3(d) (`sa_reaches_mop` for the 30) is gate
      assertion 4; upstream 0.3(a) (21 681-row grid), (b) (MOP columns byte-identical for
      all 219) and (c) (coverage differs only for the 30) are post-consolidation CSV checks,
      covered here by 4.4, 5.3 and 5.4 — not by the validation gate, which runs before any
      CSV exists. 0.3(e) adds sha256 pins + a provenance note; 0.4 gives the record's
      default name. Also confirmed: the upstream change is on the 164/163 path, and
      `30_apks.csv` is byte-identical to the frozen upstream list
- [x] 0.4 `rv-static-analysis analyze` has no `--code-package`/`--package` option — its only
      source for the filter key is `App.code_package`. This is what forces D1 (invoke GATOR
      directly)

## 1. Re-analysis driver

- [x] 1.1 Build the per-APK parameter table by reading line 1 of each
      `rvsec-dataset-sa/logs/<id>.apk.log`. **Constants as recorded in the logs**:
      `--cg-algorithm spark`, `--cg-delegation true`, `--mop-dir <RVSEC_HOME>/rvsec/rvsec-mop/src/main/resources/jca`,
      no `--succ-depth`. Plus each APK's own `(memory, timeout)` — 120g/5400 ×1, 60g/3600 ×1,
      56g/3600 ×1, 32g/3600 ×16, 12g/1800 ×11. Never flatten to a single timeout: 19 of the
      30 need more than 12g/1800
- [x] 1.2 Note that `--skip-wtg` is a **new deliberate deviation**, present in 0 of the 30
      log lines — it is added by this change, not preserved from them. Likewise `--force`
      appears in all 30 log lines but is a dead flag (`rv_static_analysis/__main__.py:193,215`,
      never read); do not carry it and do not rely on it for resume
- [x] 1.3 Write the driver (`scripts/`), preferring to extend
      `rvsec-dataset/src/rvsec_dataset/static_analysis/{sweep,runner}.py` over writing one
      from scratch — it already has per-APK atomic resume, first-line-argv logging and a
      memory guard. Two pieces are new, not one (design D5): the budget-aware scheduler,
      AND replacing `build_command` (`runner.py:63-86`), which assembles the
      `rv-static-analysis analyze` argv, with the direct GATOR argv of design D2;
      `analyze_one`'s `sa_status`/`sa_analysis_seconds` classification is reused as-is.
      One analysis per row of `30_apks.csv`, with `-clientParam codePackage=<Mneut>` read
      verbatim from the CSV
- [x] 1.4 Replicate the four wrapper behaviours (design D2): `--jvm-memory` upper-cased;
      an outer subprocess timeout in addition to GATOR's `--timeout`; `ANDROID_SDK_HOME`
      exported (not `ANDROID_HOME`) or `--sdkpath` passed; resume by output-file existence
- [x] 1.5 Output to `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/`,
      with per-APK logs under `SA_RERUN_gh91/logs/<id>.apk.log` whose first line is the exact
      argv, mirroring the Phase 7 convention. The log MUST also capture GATOR's
      stdout/stderr (as `runner.py:216-227` does via `Popen(stdout=log)`): gate 3.3(b)
      asserts the `[RvsecAnalysisClient] Filter package:` line from it. The corpus is NOT
      touched by this change
- [x] 1.6 Schedule by memory budget rather than worker count — cap the sum of concurrent
      `--jvm-memory` at ≈100 GB on this 123.48 GiB host (8 × 12g = 96 GB, up to 3 × 32g =
      96 GB). The 56g/60g APKs run alone within the cap; the 120g APK runs alone as a
      **recorded exception above it**, justified by design R4 (`-Xmx` with no `-Xms` is a
      lazy ceiling; the original 120g run completed on this host). The dispatcher MUST
      implement its own memory guard: `_concurrency_guard` is only called on the uniform
      `workers × jvm` path (`sweep.py:576,597`) that this dispatcher replaces, and its API
      cannot express heterogeneous packings. Each APK runs exactly once; the tiers partition
      the 30 disjointly. No tier ordering is imposed; mixed packings such as `2×32g + 2×12g`
      are expected. Budget ≈10–11 h worst case

## 2. Run the 30 — one unattended campaign

The run spans a night and MUST complete with no human and no model in the loop (design D7).
Tasks 2.0a–2.0e are code and MUST land before 2.1.

- [x] 2.0a Add per-APK `--jvm-memory` / `--timeout` overrides to `scripts/gh91_sa_rerun.py`.
      The driver currently has none, and the per-round configurations of design D9 cannot
      be expressed without them. They override the pair read from the Phase 7 log, never the
      key: `codePackage` still comes verbatim from `30_apks.csv`
- [x] 2.0b Write `scripts/gh91_campaign.py` — **one** script holding the entire campaign:
      both rounds, the failure classification, the promotion, the reporting, and the final
      exit code. A round is a **capacity configuration**, and the 30 are pre-assigned to
      rounds by the tier Phase 7 measured for them (design D9): round 1 = `32g`/`3600 s`,
      3 concurrent, the 27 APKs whose tier was 12g or 32g; round 2 = `120g`/`7200 s`, one at
      a time, the 3 APKs above 32g. Order within a round is cheapest-first by the Phase 7
      wall clock, so results and failures surface early. Stops early the moment nothing
      retryable remains
- [x] 2.0c Classify every failure as `TRANSIENT` or `DETERMINISTIC` (design D9) before
      spending anything on it. A `TRANSIENT` failure in round 1 is **promoted** into round 2
      and runs under round 2's configuration — never re-attempted under the configuration
      that already failed it, which is what makes a retry worth its hours. A
      `DETERMINISTIC` failure — an analysis exception, an unparseable JSON, a non-zero return
      code without a timeout — is recorded and reported, never retried. Round 2 is the host's
      memory ceiling, so there is nothing to promote out of it
- [x] 2.0d Write `REGISTRO.md` incrementally under `SA_RERUN_gh91/`, **flushed after every
      APK** (design D10). Per APK per round: exact argv, `jvm_memory`, `timeout`, `sa_status`,
      wall-clock seconds, `returncode`, `timed_out`, whether the JSON exists and carries
      `"complete": true`, the log tail on failure, and the TRANSIENT/DETERMINISTIC verdict.
      It is the audit trail **and** the live progress view: `tail REGISTRO.md` must answer
      "where is it?" without touching the running process
- [x] 2.0e Before each retry round, move the failed APK's JSON and log aside — keep them,
      they are provenance — and re-run with `--rerun --only <apk>`. Resume is by output-file
      existence, and a partial JSON still parses (bracket recovery), so any such file left in
      place would make round 2 skip exactly the APK round 1 failed. Measured caveat on the
      magnitude (design R5, corrected 2026-07-30): a WTG timeout leaves a *complete* file, not
      a partial one, and under `--skip-wtg` a timeout lands before any write at all — so the
      window is narrow and this guard is cheap insurance, not the dominant failure mode.
      It stays because it costs one `os.replace`. Never accept "it parses", nor
      `sa_status == complete` on its own, as evidence of completeness — only the
      `"complete": true` sentinel counts

- [x] 2.1 Smoke — **infrastructure only**, on an APK that is deliberately NOT one of the 30:
      `apks_examples/cryptoapp.apk` (`br.unb.cic.cryptoapp`, ~4 MB, 6 dex). It proves the
      driver, not the corpus: argv assembled as design D2, `ANDROID_SDK_HOME` resolved,
      client jar and `mopDir` found, JSON written where expected carrying `"complete": true`,
      `transitions: []` (the WTG is skipped — it is NOT run, here or in the real run), the
      `[RvsecAnalysisClient] Filter package: br.unb.cic.cryptoapp` line captured in the log
      (the very evidence gate 3.3(b) reads back), and resume + the `_progress/` record
      behaving. It MUST write **outside** the deliverable directory, so gate 3.1 keeps
      counting exactly 30 JSONs
- [x] 2.2 Do **NOT** re-derive what each APK needs. The Phase 7 record is the authority, and
      it is used twice: the `(memory, timeout)` pair decides **which round** an APK belongs
      to, and the measured wall clock decides **its order inside that round**. Nothing is
      inferred from the smoke, which is infra-only on a 4 MB APK and measures no
      representative peak; re-deriving blind would risk an OOM in a multi-hour run. A round
      then applies its own configuration to its members, always at or above the tier that put
      them there — no APK ever runs below its known requirement (design D9). This is a
      recorded decision, not an open item
- [ ] 2.3 Verify the resume path **before** launching for the night: kill the campaign
      mid-round, re-invoke the identical command, and confirm it picks up where it stopped
      and does **not** skip an APK whose JSON is partial. Durability comes from idempotence,
      not from detachment (design D8) — this is the only property that makes an unattended
      overnight run recoverable from a power cut, a reboot, or a bug in the campaign itself.
      **Deliberately skipped, 2026-07-30, on the owner's explicit authorisation.** The round
      logic, promotion, ordering and resume are already covered by a 16-assertion simulation
      with GATOR stubbed out; the only path this task would have added is the signal handler
      plus `kill_running()` against real subprocesses. It was never executed — left unchecked
      on purpose rather than marked done. The risk it hedged did not materialise: the run
      completed in one pass with no interruption and no APK re-attempted

- [x] 2.4 Launch the campaign in the background from the session (Bash `run_in_background`),
      so it stays harness-tracked and reports on exit. Do **not** detach it with
      `setsid`/`nohup` — that removes it from tracking and forces exactly the flaky polling
      this design avoids — and do **not** poll it on a timer: the completion notification is
      the monitor. Do not orchestrate the rounds with workflows or subagents; that logic
      lives in the script (design D7). Goal state: 30 JSONs carrying `"complete": true` in
      `SA_RERUN_gh91/`.
      **Executed 2026-07-30 19:42 → 2026-07-31 00:29 BRT, 4.77 h, exit 0.** Round 1 (27 APKs,
      32g/3600 s, 3 concurrent) ran 19:42→22:43 with **zero failures and zero promotions**;
      round 2 (3 APKs, 120g/7200 s, serial) ran 22:43→00:29 — `org.wikipedia` 1235.8 s,
      `app.pachli` 1704.3 s, `com.jerboa` 3395.8 s, all `rc=0`, none timed out. Goal state
      reached: **30/30 carry `"complete": true`**. `_superseded/` is empty, so 2.0e's
      move-aside guard never had to fire and no APK ran twice. Faster than the ~7.5 h
      estimate because the Phase 7 wall clocks it was derived from included the WTG: the
      APKs that had timed out inside the WTG collapsed (`binaryeye` 1800 s → 170 s,
      `swati4star.createpdf` 1800 s → 472 s, `com.afkanerd.deku` 393 s → 147 s), while the
      32g tier, whose cost is in Soot/spark, did not move (`org.fossify.paint` 1728 s →
      1726 s)

- [x] 2.5 On completion: run the group 3 gate, summarise `REGISTRO.md`, and for any APK not
      yet `complete` state whether the failure is DETERMINISTIC (do not retry) or TRANSIENT.
      A TRANSIENT failure that survived round 2 has no round left — round 2 is already the
      host's memory ceiling, so the only remaining lever is time. Report it and **ask** before
      spending another multi-hour run; do not start one unprompted.
      **Nothing to classify.** All 30 `REGISTRO.md` entries are `COMPLETE`, every
      `_progress/<apk>.json` carries `sa_status: complete` with `rc=0` and `timed_out: False`,
      so no APK reached the TRANSIENT/DETERMINISTIC decision at all and no further run was
      proposed

## 3. Validation gate — hard stop before anything is copied

Every assertion below is a script with an exit code, run against `SA_RERUN_gh91/`. Group 4
MUST NOT start until all pass.

- [x] 3.1 Cardinality: exactly 30 JSONs produced, one per row of `30_apks.csv`.
      **PASS.** Its first run FAILED, and the defect was the gate's own: it globbed
      `OUT_DIR/*.json`, which swept in `_campaign_state.json` — the campaign's resume state,
      which design D10 puts in exactly that directory. Fixed without weakening the assertion
      by splitting it in two: the `*.apk.json` set must equal the CSV exactly, and any other
      top-level `.json` must be a declared bookkeeping file. Probed negatively: a planted
      `zz_probe_stray.apk.json` is caught by the first half and a planted `zz_probe_other.json`
      by the second (both removed afterwards; the gate returns 0 again)
- [x] 3.2 Completeness: every JSON carries the `"complete": true` sentinel emitted by
      `JsonReportWriter` at the end of `write()`. Do NOT accept "it parses" as evidence — the
      parser repairs truncated JSON via bracket recovery
      (`static_analysis_parser.py:275-292`), so a partial file parses cleanly.
      **PASS on all 30.** Independently re-checked outside the gate with a strict
      `json.loads` (no bracket recovery) plus the sentinel's presence in the file's last
      bytes, so a truncation the repair path would have hidden could not slip through
- [x] 3.3 Key applied, **per APK, for all 30** — the smoke covers none of them, it runs on an
      APK outside the list — two assertions:
      (a) 0 classes outside its `Mneut` and >0 inside, using the parser's real semantics —
      substring match after `SignatureNormalizer` (`static_analysis_parser.py:360`);
      (b) the run's own log carries `[RvsecAnalysisClient] Filter package: <Mneut>` —
      exactly the intended key. (b) is what catches a *narrower* wrong key: GATOR filters
      by `startsWith`, so every class kept under e.g. `app.pachli.core` also satisfies (a)
      for `app.pachli`. The JSON does not record its filtering key, but the log does.
      **Both halves PASS on all 30.** Independently re-checked: every `reachability`
      class name sits under its `Mneut` (prefix match, 0 outside, >0 inside), each log
      carries exactly one distinct `Filter package:` value and it equals the CSV's `Mneut`,
      and line 1 of each log — the argv actually issued — carries `codePackage=<Mneut>`,
      `skipWtg=true`, `-cgAlgorithm spark`, `-cgDelegation true`, the JCA `mopDir`, and the
      **uninstrumented** `APKS/<apk>` input with no `INSTRUMENTED` path anywhere
- [x] 3.4 Right APK: the JSON's top-level `package` field matches the expected
      `manifest_package` from `30_apks.csv`.
      **PASS on all 30**, and each input APK was additionally confirmed present under
      `APKS/`; three sampled APKs are byte-identical (sha256) to their
      `rvsec-dataset/head_apks/` counterparts, which is the provenance claim task 0.1 rests on
- [x] 3.5 MOP surface preserved: all 30 keep `sa_reaches_mop = True` with a non-empty
      reaches-MOP denominator — **hard stop** on any failure, report back rather than working
      around it. Computable from the new JSON alone
      (`reachability[].methods[].reachesTarget`); does not require the consolidation.
      **PASS on all 30, with margin.** Every app has a non-empty method denominator and at
      least one method carrying `reachesTarget`; the smallest surfaces are
      `com.github.cvzi.screenshottile` (2 of 394 methods) and `net.osmtracker` (12 of 1088),
      the largest `org.wikipedia` (13 578 of 39 950). The paper's 164/163 is not at risk from
      this run
- [x] 3.6 Record the observed denominator delta per app against its predecessor JSON.
      Expected: **12 shrink, 13 verified unchanged, 5 widen** — of the widening five, only
      `org.wikipedia` is measurable today (0 → 1139 under the CSV's own keys);
      `app.pachli`, `com.jerboa`, `net.osmtracker` and `swati4star.createpdf` have
      predecessors already pre-filtered narrow, so their growth cannot be measured before
      the re-run (design R3). Caveat: for `org.wikipedia_50595.apk` the predecessor was
      filtered by `org.wikipedia.feed`, not by the `org.wikipedia.diff` that `30_apks.csv`
      records as its `detected_package` — that comparison is against a key that was never
      applied.

      **Recorded, and the prediction held where it was falsifiable.** The 12 predicted to
      shrink shrank, and the 5 predicted to widen widened — the same five apps, no others:
      `app.pachli` 2466 → 6453, `com.jerboa` 140 → 3171, `org.wikipedia` 1139 → 7987,
      `swati4star.createpdf` 35 → 529, `net.osmtracker` 140 → 232.

      **Deviation from "13 unchanged": 10 of those 13 shrank slightly** (e.g.
      `org.musicbrainz.picard.barcodescanner` 63 → 51, `org.glpi.inventory.agent` 201 → 179,
      `com.antony.muzei.pixiv` 176 → 169); only 3 are literally unchanged
      (`br.com.colman.petals` 1, `com.github.cvzi.screenshottile` 21,
      `com.github.livingwithhippos.unchained` 2). Diffed class-set by class-set against the
      predecessors: across all 30 apps **every class lost is a generated one — `R`, `R$*` or
      `BuildConfig` — 0 non-generated classes lost and 0 losing class carries
      `reachesTarget`**, and no app gained a class it should not have.

      The cause is in the GATOR client, not in this run: `isAppClass`
      (`RvsecAnalysisClient.java:277-286`) takes the suffix **relative to the filter key** and
      drops it only when that suffix is exactly `.R`, `.R$*` or `.BuildConfig`. Under the old
      wide `detected_package` (`org.musicbrainz.picard`) the class
      `org.musicbrainz.picard.barcodescanner.R` has suffix `.barcodescanner.R` and escapes the
      exclusion; under `Mneut` the suffix is `.R` and it is dropped as intended. So the wrong
      key was inflating the coverage denominator with generated classes — exactly what that
      method's own javadoc says it exists to prevent. This **corroborates the change's thesis**
      rather than contradicting it, and it belongs in 4.5's provenance note and 4.6's upstream
      handshake, since the affected `sa_classes`/`sa_methods` counts move for 10 apps whose
      filtering key upstream may assume was equivalent.

      Two rival explanations were checked and ruled out: no rvsec-gator **production** source
      changed between the predecessors (2026-06-26) and the jar rebuild (2026-07-29) — only
      three test files — and the analysed APK bytes are identical (sha256) between `APKS/` and
      `rvsec-dataset/head_apks/`. `--skip-wtg` is also ruled out: the reachability pipeline
      runs at steps 3-5, before `skipWtg()` is ever read at step 6

## 4. Record, provenance and delivery

- [x] 4.1 Compute the `sa_*` block offline from the 30 JSONs with `StaticAnalysisParser`
      (the step `rv-static-analysis` used to perform in-process at `static_analysis.py:418`),
      mirroring what `scripts/regenerate_results/regenerate_container.py` already does.
      **Done via `scripts/gh91_record.py`.** Correction to this task's premise, found at
      apply: `rv-static-analysis`'s `StaticAnalysisParser` is *not* the producer of the
      `sa_*` columns — it parses into domain objects and drops classes whose name does not
      contain `code_package`. The authority for the 17 dataset columns is
      `rvsec-dataset/src/rvsec_dataset/static_analysis/parser.py`, which computes them from
      the raw JSON dict and states exactly that reason in its own module docstring. The
      record imports that module rather than re-deriving the counts, so this record and the
      corpus cannot drift apart silently
- [x] 4.2 Build the per-app record: `apk`, key used, exact argv, `sa_reaches_mop`,
      reaches-MOP denominator size, plus `sa_classes`, `sa_methods`, `sa_methods_reachable`,
      `sa_directly_reaches_mop`, `sa_methods_reaches_mop`, `sa_methods_directly_reaches_mop`,
      `sa_num_activities`/`services`/`receivers`/`providers`, `sa_windows_count`,
      `sa_transitions_count`, `sa_components_count`, `sa_analysis_seconds`, `sa_engine`
      (constant `gator`), and `sa_status` from the dataset's closed vocabulary (`complete` /
      `partial_empty_reachability` / `failed_timeout_no_json`). Upstream's default name is
      `dataset/pkgdet_validation/sa_rerun_record.csv`, "name confirmed at apply" — treat it
      as a default.
      **Written to `SA_RERUN_gh91/record/sa_rerun_record.csv`** — 30 rows × 33 columns, the
      default name kept. Beyond the 17 `sa_*` columns plus `detected_package`/`sa_mismatch`
      it carries `key_used`, `manifest_package`, `csv_detected_package`, `relation`, the
      MOP numerator/denominator explicitly, `round`, `jvm_memory`, `timeout_s`,
      `wall_clock_s`, `returncode`, `timed_out`, the JSON's `json_sha256` and the exact
      argv. Verified after generation: no cell is empty in any row, `sa_status` is
      `complete` and `sa_engine` `gator` in all 30, `sa_reaches_mop` is `True` in all 30,
      `sa_mismatch` is `False` in all 30, and the `sa_methods` /
      `sa_methods_reaches_mop` columns agree with the independent count made during the gate
- [x] 4.3 Flag `sa_transitions_count` as empty by construction under `--skip-wtg`. Do **NOT**
      flag `sa_windows_count` the same way: it is populated
      (`RvsecAnalysisClient.java:165-183` writes the full report before returning). Its
      caveat is different — derived from `prepareWindows(output, new HashMap<>(), null)`, so
      it may differ from the post-WTG set and its window ids are fallback (design R2).
      **Both statements are in the provenance note and both hold in the data**:
      `sa_transitions_count` is 0 in all 30 rows, and `sa_windows_count` is non-zero in all
      30 (2 to 45 windows per app), so the distinction is not merely asserted — it is
      visible in the delivered record
- [x] 4.4 Produce a sha256 manifest of the 30 new JSONs, plus a **pre-installation manifest
      of the current `STATIC_DIR`** (all 219 `.json`) so the owner's copy step can afterwards
      be proven to have touched exactly 30 files and left 189 byte-identical.
      **Done: `manifest_sa_rerun_30.sha256` (30 files) and
      `manifest_static_dir_pre_install.sha256` (219 files).** The pre-installation manifest
      was taken while `STATIC_DIR` still held 219 JSONs and **zero** `.pkgdet` files, i.e.
      genuinely before any group-5 copy
- [x] 4.5 Write the provenance note: exact command per APK, rv-android commit hash, date, and
      the WTG-skipped statement with 4.3's precision.
      **Done: `record/PROVENANCE.md`** — commit, campaign window, input corpus, engine
      configuration, the two differences against the predecessors (key + skipped WTG),
      4.3's precision on windows vs transitions, the generated-class finding from 3.6 with
      its ruled-out rival explanations, and per APK the key, round, memory/timeout, wall
      clock, return code, the JSON's sha256 and the verbatim argv
- [ ] 4.6 Upstream handshake (single point of contact), before delivering: (a) sign-off for
      the `--skip-wtg` deviation — nothing in `remove-package-detector` group 0 authorises
      a configuration deviation, and its gated repair script rewrites
      `sa_windows_count`/`sa_transitions_count` for the 30 from this record (the *choice*
      of `--skip-wtg` is settled — what is missing is the handshake); (b) correction of
      upstream 0.1, whose instructions do not match how the consolidation works: it reads
      the flat `STATIC_DIR` (`consolidate_offline.sh:27`, `regenerate_container.py:114`),
      not the JSON copies in the RESULTS tree, and `rv-platform run --process-results`
      must not be used (design §Consolidation).
      **Both items decided by the owner on 2026-07-31; one action remains, in the other
      repo.**
      (a) **Signed off.** An empty `sa_transitions_count` for the 30 is the expected
      consequence of skipping the WTG and is accepted as such — no WTG campaign will be
      commissioned, and upstream's gated repair script may consume this record as delivered.
      (b) **Path confirmed:** the consolidation runs as
      `RESULTS_ROOT=<...>/RESULTS bash experimento-20260706/scripts/consolidate_offline.sh`,
      **not** `rv-platform run --process-results`.
      Still open, and deliberately not done from here: amending task 0.1 in
      `remove-package-detector/tasks.md`, which lives in `ase-journal` and is that change's
      artefact — nothing in that repo was edited.
      **Correction to the delivered handshake, recorded rather than quietly patched:** its
      first version claimed that swapping the co-located JSONs in the RESULTS tree "would
      change nothing". That is false — `--process-results` reads exactly those files
      (`result_processor.py:220-270`). The document was corrected and re-delivered; the
      accurate objection is the choice of consolidation path, not the JSON's location, and
      the real risk is the silent no-op described in `design.md` §Consolidation
- [x] 4.7 **Deliver stage 1** into `ase-journal`: the per-app record, the provenance note
      and the sha256 manifests — everything group 4 produces — and signal "SA stage
      delivered". This does NOT release upstream 0.2 by itself: the regenerated CSVs and
      the `.pkgdet` files exist only after the owner's group 5, which is stage 2 of the
      delivery (design §Deliverables). Assembling locally is not enough — upstream blocks
      on artefacts "delivered to this repo" (`remove-package-detector/tasks.md:12-14`).
      **Delivered into `ase-journal/dataset/pkgdet_validation/`** as `sa_rerun_record.csv`
      (+ a `.sha256` sidecar, matching that directory's convention),
      `sa_rerun_provenance.md`, `sa_rerun_handshake.md`, `sa_rerun_manifest_30.sha256` and
      `sa_rerun_static_dir_pre_install.sha256`. No pre-existing file was overwritten (checked
      before copying), the copy was verified byte-identical and against its own sha256, and
      nothing was committed in `ase-journal` — the six files sit untracked for the owner.
      **Ordering deviation, recorded rather than hidden:** 4.6 asks for the handshake
      *before* delivering; the artefacts went out with the handshake still open. They are
      uncommitted and removable, so a different answer to 4.6(a) costs only a re-delivery

## 5. Owner's manual handoff — NOT executed by this change

Listed so the instruction sheet is complete and unambiguous. This group is **stage 2 of
the delivery**: only after it do the regenerated CSVs and the `.pkgdet` files exist, and
only their delivery (5.5) releases upstream 0.2 in full.

- [x] 5.1 Copy the 30 JSONs from `SA_RERUN_gh91/` into
      `RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/`,
      preserving each predecessor as `<apk>.json.pkgdet`. Verify against 4.4's manifests that
      exactly 30 files changed and the other **189 are untouched** (189 files over 189 apps —
      that directory holds one JSON per app). Decide separately whether to keep
      `rvsec-dataset/static_analysis/` and the `RESULTS/m*/.../<apk>/` copies in sync; neither
      is read by the consolidation **path this change prescribes** (`consolidate_offline.sh`
      → `regenerate_container.py:114`, which opens `STATIC_DIR`). The co-located copies are
      only read by `rv-platform run --process-results`, which is precisely the route ruled
      out — installing into `STATIC_DIR` is therefore what makes the re-run take effect.
      **Done via `scripts/gh91_install_static.py --install`, 2026-07-31.** The corpus was
      first re-checked against 4.4's pre-installation manifest (`sha256sum -c`, exit 0) to
      prove it had not drifted between the manifest and the copy. The install refuses the
      whole batch before touching anything if any source is missing, any predecessor is
      absent, or any `.pkgdet` already exists — a half-applied install is indistinguishable
      from a corrupted corpus once the proof runs. Predecessor preserved first, then
      overwritten, per app.
      **Proof is three-way and closed against the two manifests**, because P1 and P2 alone
      would still pass if a predecessor had been lost in the process: P1 the 30 installed
      JSONs match `manifest_sa_rerun_30.sha256`; P2 the other 189 are byte-identical to
      `manifest_static_dir_pre_install.sha256`; P3 each `<apk>.json.pkgdet` equals its
      predecessor's pre-install sha256, i.e. it was preserved intact and not merely
      displaced. File-set cardinality is asserted separately (219 `.json`, 30 `.pkgdet`, the
      `.json` set unchanged), so a file that appeared or vanished cannot hide behind a hash
      comparison over the intersection. **All 10 assertions PASS: exactly 30 files changed,
      189 byte-identical.** The optional housekeeping — syncing `rvsec-dataset/static_analysis/`
      and the co-located `RESULTS/m*/.../<apk>/` copies — was deliberately NOT done: neither
      is read by this consolidation path, and leaving them untouched keeps a second,
      independent copy of the predecessors beyond the `.pkgdet` files
- [ ] 5.2 Re-run the consolidation with
      `RESULTS_ROOT=/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/RESULTS bash
      experimento-20260706/scripts/consolidate_offline.sh`. The override is mandatory: the
      script's default `RESULTS_ROOT` points at `RESULTADOS_experimento-20260706/`, which
      does not exist, and the path guard (`consolidate_offline.sh:48`) aborts. Fixing that
      stale default is experimento-20260706 housekeeping, outside this change.
      Do **NOT** use `rv-platform run --process-results`: the consolidation must be rebuilt
      from the preserved `.logcat` files, not from the container CSVs, whose T=60/T=180 rows
      the resume zeroes (`result_processor` gotcha, stated at the top of that script). It is
      also not recursive — the tree has 16 containers, each with its own `tasks.json`
- [ ] 5.3 Check the audit (`verify.py --full`, C1-C4) before promoting `_regen.csv` →
      `_all.csv`. The consolidated grid target is `TARGET_TOTAL=21681`
      (5544 + 5544 + 5445 + 5148); in `RESULTS/` that file is `summary_all.csv`. In
      `ase-journal`, 21 681 rows belong to `summary_bck.csv` (219-app executed grid), while
      `summary.csv` holds 17 919 (181-app analysis basis) — `reduce_to_181.py` must be re-run
      to derive the latter from the regenerated former
- [ ] 5.4 Confirm the MOP error columns/rows are byte-identical for all 219 apps against the
      pre-reprocessing baseline — violations derive from the logcat and are independent of
      the analysis key, so any diff there is a reprocessing bug, not a scope effect
- [ ] 5.5 Deliver stage 2 into `ase-journal`: the regenerated `summary`/`coverage`/`errors`
      CSVs with sha256 pins and the 30 preserved `<apk>.json.pkgdet` files (created at 5.1).
      This is what releases upstream 0.2 in full
