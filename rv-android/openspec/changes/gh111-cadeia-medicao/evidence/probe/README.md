# Task 1.7 — D9Probe: the prediction, and the denominator decomposition

**Run 2026-08-30.** Probe: `docs/20260828_d9_colapso_denominador/D9Probe.java`, extended in this
change to print the decomposition the task asks for. Raw output: `d9probe_runs.log`.

```
javac -cp lib/gator/rvsec-gator.jar -d <classes> docs/20260828_d9_colapso_denominador/D9Probe.java
java -Xmx24G -cp <classes>:lib/gator/rvsec-gator.jar D9Probe \
     <apk> <synthesized AndroidManifest.xml> $ANDROID_HOME/platforms/android-35/android.jar \
     lib/gator/libPackages.txt <codePackage>
```

APKs: the **instrumented** corpus at
`RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162`
(petals reports `#AppClasses=3963`, the instrumented figure, against 3711 for the original —
the reproducibility input task 1.8 asks to be named). Manifests synthesized from each artefact's
own `package` + `components.activities`; the activity counts (4 / 3 / 10 / 23 / 35) match the
campaign's, which is what validates the synthesis.

This is a **prediction**, not an acceptance: the probe imports nothing from `presto.android`,
reimplements the demotion predicate and prints both guards without mutating the Scene, so editing
`AnalysisEntrypoint:119` changes its output by zero.

## Predictions — all five confirmed

| APK | scope key | collapsed (manifest guard) | raw (code guard) | predicted |
|---|---|---:|---:|---:|
| `br.com.colman.petals_3040000` | `br.com.colman.petals` | 1 | 771 | 771 ✓ |
| `com.github.livingwithhippos.unchained_60` | `…unchained` | 2 | 1971 | 1971 ✓ |
| `com.nononsenseapps.feeder.play_4025` | `com.nononsenseapps.feeder` | 6 | 3589 | 3589 ✓ |
| `com.github.cvzi.screenshottile_148` | `…screenshottile` | 21 | 550 | 550 ✓ |
| *(control)* `app.pachli_50` | `app.pachli` | 6467 | 6467 | 6467 under both ✓ |

## Decomposition — raw, minus root-anchored generated, minus segment-anchored generated

These are the **delivered** counts. Carry the last column into tasks 2.5 and 8.10; the middle
column is the superseded root-only figure.

| APK / key | raw | generated (root-anchored) | delivered, old rule | generated (last segment) | **delivered, INV-ANA-71** |
|---|---:|---:|---:|---:|---:|
| petals / `br.com.colman.petals` | 771 | 9 | 762 | 9 | **762** |
| unchained / `…unchained` | 1971 | 19 | 1952 | 19 | **1952** |
| feeder / `com.nononsenseapps.feeder` | 3589 | 11 | 3578 | 11 | **3578** |
| screenshottile / `…screenshottile` | 550 | 15 | 535 | 15 | **535** |
| screenshottile / **`com.github.cvzi`** (the detector's key) | 550 | **0** | **550** | **15** | **535** |
| pachli / `app.pachli` | 6467 | 14 | 6453 | 131 | **6336** |

Two rows carry the whole INV-ANA-71 argument.

**`com.github.cvzi`** is the ancestor-key case. Under the root-only rule the suffix of
`com.github.cvzi.screenshottile.R` is `.screenshottile.R`, which matches nothing — so the rule
removed **zero** classes and the delivered count was 550. That 550 is the number task 1.8 used to
pin as this change's D9 acceptance: a denominator with fifteen resource classes inside it. Under
the last-segment rule it is **535**, and 550 is superseded.

**`app.pachli`** is the module-level case: 14 root-anchored, 131 at the last segment — the extra
**117** is exactly the figure the design measured for this APK, one `R` per Gradle module.

Three APKs (petals, unchained, feeder) are unaffected by the widening: their resource classes all
sit at the key's root, which is why the change is invisible in their numbers and why the two rows
above are the ones that had to be measured.
