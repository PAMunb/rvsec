# D2 sample — task 3.15

This directory holds the measurement attributable to D2, the neutralisation of the build-type suffix in the scope key. Task 3.15 names the sample, the stated baseline and the prediction; this file records what was measured.

- **When:** 30/08/2026, between 20:14 and 22:00, on the host.
- **How:** `run_sample.py`, all legs with `--skip-wtg`.
- **Caps:** `--analysis-timeout` 1800 s for the baseline leg, 5400 s for the treatment leg.
- **Resources:** heap `-Xmx12G`, up to six concurrent GATOR processes.
- **Tabulated:** 14/09/2026, from `legs.jsonl` and `logs/`.

The **baseline leg** uses the default policy: the declared manifest key, which matches no compiled class. The **treatment leg** adds `--strip-build-type-suffix`. The prediction is `compiled_net` from `../calibration/calibration_rows.json`.

In each leg cell, the leading number is `len(reachability)`, followed by the source of the scope key.

- **Baseline, `rc=1` with `0 (manifest)`:** the denominator gate refused the artefact (`DenominatorImplausibleError`), which is the stated baseline.
- **Treatment, `rc=1` with `no JSON`:** "GATOR did not produce output JSON", with no timeout reached and no exception logged.

| APK | predicted `compiled_net` | baseline leg | treatment leg | funnel artefact (key source, `len(reachability)`) | estudo02 (`classes_total`, `measured`) |
|---|---:|---|---|---|---|
| `com.github.livingwithhippos.unchained_60` | 1952 | 0 (manifest), rc=1, 217 s | **1952** (manifest-neutralized), rc=0, 240 s | manifest-neutralized, 1952 | 1952, true |
| `eu.opencloud.android_9` | 2600 | 0 (manifest), rc=1, 280 s | **2600** (manifest-neutralized), rc=0, 274 s | manifest-neutralized, 2600 | 2600, true |
| `com.github.cvzi.screenshottile_148` | 535 | 0 (manifest), rc=1, 102 s | **535** (manifest-neutralized), rc=0, 124 s | manifest-neutralized, 535 | 535, true |
| `com.vrem.wifianalyzer_71` | 343 | 0 (manifest), rc=1, 215 s | **343** (manifest-neutralized), rc=0, 144 s | manifest-neutralized, 343 | 343, true |
| `com.antony.muzei.pixiv_327` | 169 | 0 (manifest), rc=1, 110 s | **169** (manifest-neutralized), rc=0, 80 s | manifest-neutralized, 169 | 169, true |
| `me.testcase.ognarviewer_25` | 134 | 0 (manifest), rc=1, 108 s | **134** (manifest-neutralized), rc=0, 132 s | manifest-neutralized, 134 | 134, true |
| `org.musicbrainz.picard.barcodescanner_38` | 51 | 0 (manifest), rc=1, 81 s | **51** (manifest-neutralized), rc=0, 102 s | manifest-neutralized, 51 | 51, true |
| `app.pachli_50` | 6336 | no JSON, rc=1, 784 s | no JSON, rc=1, 747 s | manifest-neutralized, 6336 | 6336, true |
| `ch.rmy.android.http_shortcuts_1104060001` | 7016 | no JSON, rc=1, 1178 s | no JSON, rc=1, 1177 s | manifest-neutralized, 7016 | 7016, true |
| `com.nononsenseapps.feeder.play_4025` | 3578 | timeout, 1802 s | no JSON, rc=1, 3989 s | manifest-neutralized, 3578 | 3578, true |
| `br.com.colman.petals_3040000` | 762 | timeout, 1801 s | no JSON, rc=1, 3788 s | manifest-neutralized, 762 | 762, true |
| `com.kwasow.musekit_1721768604` | 525 | timeout, 1801 s | no JSON, rc=1, 3694 s | manifest-neutralized, 525 | 525, true |
| `de.grobox.liberario_131` (negative control) | — (0 under either key) | 0 (manifest), rc=1, 90 s — refused under `de.grobox.liberario.debug` | 0 (manifest-neutralized), rc=1, 91 s — refused under `de.grobox.liberario` | not in the corpus | not in the corpus |

Two further rows are not part of the sample:
- **`me.zhanghai.android.untracker_9`**, line 27 of `legs.jsonl`, is the symmetric control of task 1.9 (see `../acceptance/README.md`).
- **`app.pachli_50.treat2.log` and `com.kwasow.musekit_1721768604.treat2.log`** are reruns with `--jvm-memory 32g`. Both stop at "Soot started" and are not in `legs.jsonl`.

## Reading

- **Two-leg protocol: 7 of 12.** Every APK that completed both legs moved from 0 to exactly `compiled_net`, and none moved elsewhere. The task's original threshold of at least 10 of 12 is not met under this protocol.
- **The five failures are the instrument, not D2.**
  - The WTG was off in every leg, so they are not the WTG-timeout family (D-B of `experimento-smk111/VEREDICTO.md`).
  - They include the two largest universes of the sample (7016 and 6336 classes). `../acceptance/README.md` records that the cost separating completed from failed legs is the APK loaded into the Scene, not the classes that survive the guard.
- **Treatment side: 12 of 12** on the production artefacts the dataset funnel wrote for the same APKs.
  - Each has `codePackageSource=manifest-neutralized` and `len(reachability) = compiled_net`.
  - estudo02 consumed them with `measured=true`.
  - The baseline's zero holds over all 75 suffixed APKs on the DEX headers (`calibration_rows.json`, `compiled_net_manifest_key = 0`).
- **Negative control: passed.** It stays at 0 in both legs and is refused by the denominator gate under both keys. D2 removes the `.debug` suffix, and the residual package rename (`de.grobox.transportr`) is caught by INV-ANA-69.

The researcher amended task 3.15 on 14/09/2026 to accept this record instead of a re-run.
