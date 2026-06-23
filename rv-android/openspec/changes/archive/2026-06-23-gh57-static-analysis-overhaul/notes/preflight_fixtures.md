# Pre-flight 1.4: Test fixture inventory

**Date:** 2026-05-14 (corrected — earlier version used the wrong dataset)
**Task:** Phase-0 §7.11 / tasks.md 1.4
**Scope:** Pick concrete APKs for each fixture role; record paths so Groups 2–8 can reference them without re-deriving.

## Critical correction (2026-05-14)

An earlier version of this note picked all fixtures from `APKS_FINAL_JCA_DEXLIB` — the *instrumented* dataset. Static analysis must run on uninstrumented bytecode (project memory `feedback_static_analysis_original_apks_only.md`). Two consequences:

1. The `.apk` files referenced below come from the **original** corpus at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` (400 APKs).
2. The structural classification (which APKs have populated `windows[]` vs empty) uses the canonical ground-truth JSONs at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_JCA_analise_estatica_soot/` (380 JSONs — 20 lost during the original static-analysis sweep). The JSONs alongside instrumented APKs in `*_DEXLIB/` are not authoritative.

Ground-truth statistics on the 380 JSONs:
- **populated windows: 158 / 380 (41.6%)**
- **empty windows: 222 / 380 (58.4%)**

These differ from the 71.6% empty rate cited in the Phase-0 doc for the 190-APK instrumented subset. The discrepancy is consistent with (a) the 190 subset being intentionally filtered for JCA-reachability / x86 ABI / dexlib2 instrumentability, biasing it toward the larger / harder apps where WTG timeout is more common, and (b) instrumentation slightly worsening Soot's odds. The core diagnosis is unchanged: the WTG phase times out on a large fraction of real-world APKs.

## Method

Read the 380 ground-truth JSONs in `…/APKS_JCA_analise_estatica_soot/`; for each, record (`reachability` count, `windows` count, type-specific widget structure). Classify into baseline-OK (populated windows) and baseline-frozen (empty windows). For each fixture role, pick stratified by reachability-class count and verify the corresponding `.apk` exists in `…/JOAO/APKs/`.

## (a) 5 baseline-OK APKs for `windows[]` partial-path smoke (Group 2, task 2.8)

Stratified by class count.

| Class count | Windows | APK file | Role |
|-------------|---------|----------|------|
| 1 | 2 | `com.nyx.custom_uploader_15.apk` | XS |
| 1 | 2 | `de.quantumphysique.trale_393.apk` | XS |
| 39 | 4 | `com.networkscanner.app_3.apk` | S |
| 45 | 1 | `app.hypostats_58.apk` | S |
| 2564 | 5 | `com.bringyour.network_906996903.apk` | L |

After task 2.1, all 5 MUST produce `windows[]` non-empty on both partial (`wtg=null`) and full (`wtg=full`) write paths.

## (b) 5 baseline-frozen APKs (WTG-timeout victims) — partial-path smoke

Stratified by class count from the 222 empty-windows set.

| Class count | APK file | Role |
|-------------|----------|------|
| 1 | `com.foss.aihub_10.apk` | XS frozen |
| 1 | `com.georgeyt9769.cardabase_2003.apk` | XS frozen |
| 17 | `com.w2sv.filenavigator_18.apk` | S frozen |
| 4309 | `app.pachli_47.apk` | XL frozen |
| 5382 | `com.zhangke.fread_108010.apk` | XXL frozen (largest in corpus) |

After task 2.1, all 5 MUST produce `windows[]` non-empty (the whole point of Opção C). `transitions[]` may remain empty (WTG still times out without Opção A); that is expected and OK.

## (c) 10 baseline-OK APKs for the Jaccard paridade gate (Group 6, task 6.1)

Stratified by class count across the 158 baseline-OK set.

| # | Class count | Windows | APK file |
|---|-------------|---------|----------|
| 1 | 1 | 2 | `com.nyx.custom_uploader_15.apk` |
| 2 | 1 | 7 | `de.computerelite.shockalarm_48.apk` |
| 3 | 1 | 7 | `com.wordtracer.app_22.apk` |
| 4 | 4 | 2 | `com.mouzinho.pokebase_2.apk` |
| 5 | 9 | 15 | `com.blankdev.sidestep_17.apk` |
| 6 | 29 | 1 | `com.dewdrop623.androidcrypt_15.apk` |
| 7 | 56 | 15 | `org.fossify.keyboard_14.apk` |
| 8 | 130 | 23 | `com.akylas.enforcedoze_85.apk` |
| 9 | 244 | 15 | `com.gorden.dayexam_9.apk` |
| 10 | 424 | 2 | `com.anysoftkeyboard.janus_11.apk` |

Jaccard threshold (per spec MODIFIED requirement "Paridade Jaccard WTG-SPARK" scenario): average ≥ 0.95 AND no individual APK < 0.85, computed over `{(source_window_id, target_window_id, event_type)}` tuples.

## (d) 1 APK with programmatic `onCreateOptionsMenu` (Group 4, task 4.7)

**Primary fixture: `app.notesr_59.apk`.**

Evidence from its ground-truth JSON: the OPTIONSMENU windows have `widgets: []` — the classic signature of an activity that declares `onCreateOptionsMenu` but populates the menu programmatically (no XML menu file), so GATOR's interprocedural analysis discovered the window but cannot enumerate the items. After Group 4 lands, the `items[]` array on each OPTIONSMENU MUST have at least one entry.

The corpus contains **32 APKs** with this structural signature; alternative candidates (all from the 158 baseline-OK set, so the rest of the JSON is sound) include `app.passwordstore.agrahn_11602`, `cn.rbc.termuc_11`, `com.akylas.enforcedoze_85`, `com.artifex.mupdf.viewer.app_210`, `com.blankdev.sidestep_17`, `com.cliambrown.pilltime_14`, `com.github.trivialloop.scorehub_6`. Ample selection.

## (e) 1 APK with literal `ArrayAdapter` Spinner items (Group 5, task 5.8)

**Primary fixture: `com.eanema.graph89_1200.apk`** (7 Spinner widgets with `entries: []` in the ground-truth JSON — the strongest single-APK signal in the corpus).

Backup candidates (each with at least 1 Spinner showing `entries: []`): `com.github.trivialloop.scorehub_6`, `cn.rbc.termuc_11`, `com.cliambrown.pilltime_14`, `com.kazumaproject.markdownhelperkeyboard.lite.fdroid_722`, `lu.knaff.alain.saf_sftp_222`, `com.rtneg.kyuubimask_24`. Total: 16 widget instances across 7 APKs.

For (e), Group 5 task 5.8 will use `apktool d` on the chosen APK and grep for `new ArrayAdapter` to confirm the population path is the MVP-targeted literal constructor (and not `getResources().getStringArray()` which is out of MVP scope). The corpus-coverage scan in `preflight_arrayadapter_corpus.md` shows that 75% of stratified originals use the MVP-targeted patterns, so the probability of a productive fixture is high.

## (Smoke fixture for the smallest end of the test pyramid)

`apks_examples/cryptoapp.apk` (in this repo) is the canonical micro-smoke target — small, deterministic, exercises JCA APIs end-to-end. Group 4 / Group 8 tasks use this as the very first sanity check before the larger fixtures above. It is **already an original (uninstrumented) APK** per repo convention.

## (No synthetic APK needed)

Phase-0 §7.11 anticipated authoring a synthetic test APK if (d) or (e) could not be sourced. This pre-flight closes the question with real APKs in both cases — no synthetic APK is required. Estimate for Groups 4 and 5 stands.

## Output

Fixture roster ready for tasks 2.6, 2.8, 4.6, 4.7, 5.7, 5.8, 6.1, 6.7, 6.8, 6.9, 8.2, 8.5. All APK file paths are under `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs/` (originals). Ground-truth JSONs for comparison are under `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_JCA_analise_estatica_soot/`.
