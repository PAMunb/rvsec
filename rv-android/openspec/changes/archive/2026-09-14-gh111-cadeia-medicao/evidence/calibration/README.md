# Task 2.5 — denominator gate calibration over the corpus

**Run 2026-08-30**, 61 s over the 162 article APKs, by
`calibrate_denominator_gate.py` in this directory. Input: the DEX headers of each
APK plus its stored `.apk.json`; both terms of the ratio filtered by the client's
own `isAppClass` as INV-ANA-71 rewrites it. Key: the **neutralized** manifest key.

## Verdict — the pass criterion, not just a recorded value

**PASS.** The gate at 0.15 refuses all **4** collapsed artefacts and admits all
**158** others.

| | value | APK |
|---|---:|---|
| `min(admitted)` | **1.0000** | every one of the 158 |
| `max(refused)` | **0.0393** | `com.github.cvzi.screenshottile_148` (21/535) |
| threshold | 0.15 | 3.8x above the refused ceiling, 6.7x below the healthy floor |
| separation | **25.4x** | between the bands |

All 158 healthy artefacts sit at exactly 1.0, which is not a coincidence and is
the reason the threshold is principled rather than tuned: the corrected ratio
*is* the client's own filter re-derived, so a healthy artefact carries precisely
the compiled classes its key covers. Zero admitted APKs sit below 1.0.

The degenerate example task 2.8 pins is `br.com.colman.petals`: **1 of 762**,
ratio 0.0013 — the pipeline count under the post-1.4b filter, not the superseded
raw 771.

## Independent agreement with task 1.7

The compiled-side counts here come from the DEX headers; the probe's came from a
loaded Soot Scene. They agree exactly on all four:

| APK | probe (Scene, post-1.4b) | calibration (DEX headers) |
|---|---:|---:|
| petals | 762 | 762 |
| unchained | 1952 | 1952 |
| feeder | 3578 | 3578 |
| screenshottile | 535 | 535 |

## Why the gate lands warn-only first (task 2.6)

Under the **literal manifest key**, **75 of the 162** have no compiled class at
all. `0/0` is not a low ratio, it is no ratio — it is the zero-universe refusal
of task 2.7 — and a raising gate before D2 supplies a resolving key would abort
46% of the corpus, 71 of them healthy applications.

---

- APKs measured: **162**
- refused (ratio < 0.15): **4**
- admitted (ratio >= 0.15): **158**
- zero compiled universe under the NEUTRALIZED key: 0
- zero compiled universe under the LITERAL MANIFEST key: **75** — the reason task 2.6 lands warn-only
- **min(admitted) = 1.0000**  (app.eduroam.geteduroam_2685.apk, 707/707)
- **max(refused) = 0.0393**  (com.github.cvzi.screenshottile_148.apk, 21/535)

## Refused

| APK | manifest key | neutralized key | parsed | compiled | ratio |
|---|---|---|---:|---:|---:|
| `com.github.livingwithhippos.unchained_60.apk` | `com.github.livingwithhippos.unchained.debug` | `com.github.livingwithhippos.unchained` | 2 | 1952 | 0.0010 |
| `br.com.colman.petals_3040000.apk` | `br.com.colman.petals.debug` | `br.com.colman.petals` | 1 | 762 | 0.0013 |
| `com.nononsenseapps.feeder.play_4025.apk` | `com.nononsenseapps.feeder.debug` | `com.nononsenseapps.feeder` | 6 | 3578 | 0.0017 |
| `com.github.cvzi.screenshottile_148.apk` | `com.github.cvzi.screenshottile.debug` | `com.github.cvzi.screenshottile` | 21 | 535 | 0.0393 |

## Admitted band

Admitted APKs below 1.0: **0**
