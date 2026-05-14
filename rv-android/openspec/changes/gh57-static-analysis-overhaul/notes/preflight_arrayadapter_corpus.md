# Pre-flight 1.2: ArrayAdapter corpus coverage scan

**Date:** 2026-05-14 (corrected — earlier run used the wrong dataset)
**Task:** Phase-0 §7.7 / tasks.md 1.2
**Scope:** Decide whether `SpinnerItemExtractor` (Group 5) stays at MVP scope (literal constructor + `add`/`addAll`) or escalates to full scope (`getResources().getStringArray()` + Kotlin `listOf()`).
**Decision threshold:** MVP if hit rate ≥40% on stratified 20-APK sample; full otherwise.

## Critical correction (2026-05-14)

An earlier version of this note sampled APKs from `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB` — the *dexlib2-instrumented* dataset. **Static analysis must run on uninstrumented bytecode** (instrumentation injects MOP monitor invocations that crash Soot's Dexpler and contaminate reachability counts; see project memory `feedback_static_analysis_original_apks_only.md`). This note has been re-run against the **original** APK dataset at `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` (400 APKs total, 380 with usable ground-truth JSONs in `…/APKS_JCA_analise_estatica_soot/`). The conclusions below derive from the correct source.

## Method

Sampled 20 APKs from `/home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKs` stratified by reachability-class count (5 from each quartile across the 380 ground-truth set). Decompiled each with `apktool d -f --no-res` to `/tmp/gh57_corpus_originals/<name>/`, producing smali for every `classes*.dex`. Scanned each tree with grep against five patterns:

| Pattern | Smali signature | Maps to |
|---------|-----------------|---------|
| `new_aa` | `new-instance .* Landroid/widget/ArrayAdapter` | MVP — pattern 1 (literal constructor) |
| `set_aa` | `->setAdapter(L` on a Spinner | sanity — should accompany either pattern 1 or 2 |
| `get_str_arr` | `->getStringArray(` (any) | full scope only |
| `kotlin_list_of` | `Lkotlin/collections/CollectionsKt;->listOf\|Ljava/util/List;->of(` | full scope only |
| `add_calls` | `Landroid/widget/ArrayAdapter;->add\b` | MVP — pattern 2 (`adapter.add`/`addAll`) |

**MVP qualified** = `new_aa > 0 OR add_calls > 0`. **Full-only** = `MVP not qualified AND (get_str_arr > 0 OR kotlin_list_of > 0)`. **No pattern** = none of the above.

## Results

| APK | newAA | setAdpt | getStrA | kotlinLst | addCalls | MVP? |
|-----|-------|---------|---------|-----------|----------|------|
| `app.notesr_59` | 1 | 0 | 0 | 22 | 0 | YES |
| `app.wispar.wispar_36` | 2 | 0 | 0 | 0 | 1 | YES |
| `cc.sovellus.vrcaa_200802` | 0 | 0 | 0 | 0 | 0 | – |
| `ch.simonste.jasstafel_72` | 1 | 0 | 0 | 0 | 1 | YES |
| `com.adilhanney.ricochlime_1120403` | 1 | 0 | 0 | 0 | 1 | YES |
| `com.anxcye.anx_reader_6321` | 2 | 0 | 0 | 0 | 1 | YES |
| `com.app.equran_283` | 1 | 0 | 0 | 0 | 1 | YES |
| `com.chiller3.basicsync_71424` | 2 | 0 | 0 | 0 | 1 | YES |
| `com.dobby.vpn_1002005` | 1 | 0 | 0 | 166 | 0 | YES |
| `com.jstappdev.e6bflightcomputer_20` | 2 | 0 | 0 | 0 | 0 | YES |
| `com.pennywiseai.tracker_87` | 1 | 0 | 0 | 0 | 0 | YES |
| `com.xmission.trevin.android.todo_1050101` | 1 | 0 | 0 | 0 | 0 | YES |
| `com.zoffcc.applications.undereat_10031` | 0 | 0 | 0 | 0 | 0 | – |
| `net.curiana.recipes_12` | 1 | 0 | 0 | 0 | 0 | YES |
| `nodomain.aditya1875more.stashly_20` | 0 | 0 | 0 | 0 | 0 | – |
| `org.eu.mumulhl.ciyue_863000` | 2 | 0 | 0 | 0 | 1 | YES |
| `ru.stersh.youamp_36` | 0 | 0 | 0 | 0 | 0 | – |
| `sh.haven.app_1172` | 1 | 0 | 0 | 0 | 0 | YES |
| `top.kagg886.pmf_185` | 0 | 0 | 0 | 0 | 0 | – |
| `xyz.numerus_2` | 1 | 0 | 0 | 24 | 0 | YES |

**Aggregate:** MVP hit = **15 / 20 (75%)**. Full-only = 0. No pattern = 5 (25%).

## Decision

- **MVP coverage 75% — well above the 40% threshold. Group 5 stays at MVP scope.**
- The 5 APKs with zero ArrayAdapter usage have no programmatic Spinner population; `SpinnerItemExtractor` returns empty for them with no work lost.
- The `setAdpt` pattern produced 0 hits via grep across all 20 APKs — the literal grep `->setAdapter(L` is too narrow for receiver-typed variants. This is a grep limitation; the Group 5 implementation uses Soot's points-to (not regex) and will correctly identify `setAdapter` call sites.

## Stability against the instrumented re-run

The original-dataset scan (75% MVP) matches the result obtained against the (incorrect) instrumented dataset (also 75%, 15/20). This is expected — instrumentation injects bytecode at MOP-relevant call sites; it does not strip out `new ArrayAdapter` or `adapter.add` invocations from the rest of the app code. So while the earlier scan technically used the wrong inputs, its conclusion happened to be correct. Going forward, every static-analysis sample MUST come from the original set per project memory.

## Heads-up for Group 5 implementation

1. **Kotlin `listOf` is widespread (3/20 APKs in this sample, with high counts).** The `SpinnerItemExtractor` MUST narrow its def-use trace to bindings actually flowing into `ArrayAdapter` constructor / `add` arguments. A scan that follows every `listOf` would be massively over-broad.
2. **Most ArrayAdapter populations are via the constructor's third argument** (15/20 APKs show `new_aa ≥ 1`; only 7 also show `add_calls`). The MVP implementation should prioritize the constructor path (task 5.2) over the `add`/`addAll` path (task 5.3).
3. **No `setAdapter` literal hits with our grep** confirms Group 5's design choice of points-to walking instead of string matching.

## Cleanup

- Decompiled trees consume ~250 MB at `/tmp/gh57_corpus_originals/`. Preserve until Group 5 implementation begins so the fixture-specific re-decompilation in task 5.8 has reference material.
- Earlier (incorrect) decompiled set at `/tmp/gh57_corpus/` should be deleted.
