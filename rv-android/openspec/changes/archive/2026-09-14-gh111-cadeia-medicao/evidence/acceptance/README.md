# Tasks 1.8 / 1.9 — the D9 acceptance, end to end

**Run 2026-08-30.** Two APKs, two jars each, four logs in this directory. This is the **acceptance**
of INV-ANA-65, not a prediction: it drives the deployed `lib/gator/` jars through the real
`rv-static-analysis` client, so an unbuilt or stale jar fails it. `D9Probe` stays as the ~13 s
prediction and is recorded separately in `evidence/probe/`.

## The command

```bash
D=$RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-FINAL_selected162
MOP=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources/jca

# post leg — the rebuilt jars in lib/gator/
uv run rv-static-analysis analyze --apk "$D/<apk>.apk" --output <dir> \
    --package-detector --mop-dir "$MOP" --analysis-timeout 3600 --skip-wtg

# pre leg — the preserved jars, and --gator-dir MUST point at the in-tree lib/gator-pre
uv run rv-static-analysis analyze --apk "$D/<apk>.apk" --output <other-dir> \
    --package-detector --mop-dir "$MOP" --analysis-timeout 3600 --skip-wtg \
    --gator-dir $PWD/lib/gator-pre \
    --analysis-client-jar $PWD/lib/gator-pre/rvsec-analysis-client.jar
```

Two things about the pre leg are worth writing down, because both cost a run. `--gator-dir` must be
the **in-tree** `lib/gator-pre`: the launcher resolves apktool relatively, as
`pygator/../../apktool/apktool.jar`, so a copy of `gator-pre` placed anywhere else dies with
`Unable to access jarfile …/apktool/apktool.jar` and an empty `/tmp/gator-*/apktool.yml`. And the
pre and post legs need **distinct `--output` directories**: the cache treats mere existence as a hit
(`static_analysis.py:327-335`, *"We do not validate content"*) and the filename carries no key, so an
A/B in one directory answers the second run from the first run's artefact. `--force`, which this
change made real, is the other way out.

`--skip-wtg` turns each leg into minutes instead of an hour and does not touch `reachability`, which
is the only section under test here.

## Both legs executed — neither answered from cache

Every one of the four logs opens with `Executing analysis: ANALYSIS` (`static_analysis.py:338`) and
none contains `Analysis result already exists, skipping` (`:329`). That is the check task 1.9
demands, and it is what makes the pre/post numbers a comparison rather than a re-read.

## The jars

| | `rvsec-gator.jar` | `rvsec-analysis-client.jar` |
|---|---|---|
| pre (`lib/gator-pre/`, preserved at `evidence/jars-pre/`) | `4708d63c2fbc46e1…` | `dab75ca733988aad…` |
| post (`lib/gator/`, built by task 1.5) | `6ce00738bf7ba0d9…` | `df18057eb82abf0b…` |

## Reproducibility inputs

The APKs are the **instrumented** ones — the same corpus the campaign ran, not the originals
(`petals` reports `#AppClasses=3963` instrumented against 3711 original). The `android.jar` is not
fixed by the command: the launcher derives the API level from each APK's own `apktool.yml`
`targetSdkVersion`, so `screenshottile` ran against `android-36` and `untracker` against
`android-37`. (The `D9Probe` runs of task 1.7 are the ones pinned to `android-35`, because there the
platform jar is an explicit argument.)

## Result 1 — the acceptance: `com.github.cvzi.screenshottile_148`

Manifest package `com.github.cvzi.screenshottile.debug`; the detector elects **`com.github.cvzi`**,
an *ancestor* of the code namespace. No D2 anywhere — this is D9 on its own.

| leg | `len(reachability)` | `[RvsecAnalysisClient] Application classes` |
|---|---:|---:|
| pre-change jar | **21** | 21 |
| rebuilt jar | **535** | 535 |

The post artefact records what INV-ANA-66 requires and the pre artefact records none of it — its top
level is the pre-change five members, with `package` alone:

```
codePackage           = com.github.cvzi
codePackageSource     = detector
class_defs_under_key  = 539
generated resource classes in reachability = 0
```

**535, and not 550.** 550 was this task's asserted number until task 1.7 decomposed it. Under the
root-anchored strip the suffix of `com.github.cvzi.screenshottile.R` is `.screenshottile.R`, which
matches nothing anchored at `com.github.cvzi`, so fifteen resource classes stayed inside the
denominator. INV-ANA-71 moves the test to the class name's last segment and they leave; the live run
reproduces the predicted 535 exactly. The gate's ratio is 535/539 = 0.993, far above the 0.15
threshold — and it is not 1.000 because `class_defs_under_key` counts compiled classes while
`reachability` carries the ones the call graph reached.

## Result 2 — the invariance control: `me.zhanghai.android.untracker_9`

| leg | `len(reachability)` | `[RvsecAnalysisClient] Application classes` |
|---|---:|---:|
| pre-change jar | **330** | 330 |
| rebuilt jar | **330** | 330 |

Manifest package `me.zhanghai.android.untracker`, elected key identical to it, and
`class_defs_under_key = 332` in the post artefact — a ratio of 0.994. Invariant across the
rebuild, which is what the control exists to show: this APK's code package **does** match a
`libPackages.txt` pattern and carries **no** build-type suffix, so the demotion loop really runs and
the two guards resolve the same key before and after. Had the repair widened the guard rather than
redirected it, this number would have moved.

`app.pachli_50` was **not** used as the control, and the reason is that it cannot fail: no
`libPackages.txt` pattern matches `app.pachli.*` — the only `app`-initial entries are `apparat.*` —
so the demotion loop never runs for it and it is invariant under any guard whatsoever. The control
has to be an APK whose code package *does* match a pattern and carries *no* build-type suffix, so
that the loop really executes and the pre/post keys coincide. `me.zhanghai.android.untracker` is one
of the six such APKs named in `docs/20260828_d9_colapso_denominador.md:133-135`.

## Cost — what the four legs do and do not compare

**The four legs did not run under one configuration, and an earlier revision of this section drew a
conclusion from them that the configurations do not support.** It asserted, in bold, that the 34×
between `screenshottile`'s two legs was "the repair itself, not noise", on the grounds of "same APK,
same flags, same machine". The flags were not the same: reading the argv of the four logs, the two
`pre` legs carry `-clientParam skipWtg=true` and the two `post` legs carry no such parameter. The
legs differ in **two** variables at once — the jar and the WTG analysis — so the 34× is their
product and decomposes into neither on its own.

There is a second confound in the same numbers. The `post` legs ran 17:09–19:01 and the `pre` legs
18:45–19:16, so `untracker`'s `post` leg spent its last sixteen minutes sharing the machine with a
second GATOR run. Its 3600 s timeout was reached under contention.

| leg | jar | `--skip-wtg` | classes past the guard | wall clock | artefact |
|---|---|---|---:|---:|---|
| `screenshottile` pre | pre | yes | 21 | **91 s** | complete |
| `screenshottile` post | post | no | 535 | **3141 s** | complete, 683 transitions |
| `untracker` pre | pre | yes | 330 | **1748 s** | complete |
| `untracker` post | post | no | 330 | **3600 s — timeout** | truncated: no `complete`, 0 transitions |

## The decomposition, measured 30/08 21:20

Task 3.15's campaign supplies the missing cell, because `com.github.cvzi.screenshottile_148` is a
member of its sample and its treatment leg runs the **same** jar as the acceptance's `post` leg
**with** `--skip-wtg`. The key differs in spelling only — `--strip-build-type-suffix` resolves
`com.github.cvzi.screenshottile` where `--package-detector` elected the ancestor `com.github.cvzi` —
and the two select the same 535 classes, which the equal `reachability` confirms.

| jar | `--skip-wtg` | classes past the guard | wall clock |
|---|---|---:|---:|
| pre | yes | 21 | 91 s |
| **post** | **yes** | **535** | **123.4 s** |
| post | no | 535 | 3141 s |

**At constant flags the guard costs 1.36×, not 34×.** Twenty-one classes to five hundred and
thirty-five — a 25× widening of the protected set — moves the analysis from 91 s to 123 s. What
moves it from 123 s to 3141 s is turning the WTG analysis back on: **25×**, and that is where the
class count is actually spent. The earlier reading, that "the cost of an analysis is set by how many
classes survive the demotion", is wrong as stated. With the WTG off — the configuration under which
`reachability` is the only section anyone is measuring — the leg is nearly insensitive to it.

Task 3.15's own campaign says the same thing from the other side, over twelve APKs: `unchained`
carries 1952 classes and finished in 240 s, while `petals` carries 762 and did not finish at all.
What separates them is APK size, not class count — the whole universe Soot loads into the Scene,
which the guard never sees.

## The control is now symmetric

The imperfection the previous revision recorded is closed. `me.zhanghai.android.untracker_9` was
re-run against the rebuilt jar with `--package-detector --skip-wtg` — the pre leg's exact
configuration — on 30/08 at 21:18:

| leg | jar | `--skip-wtg` | `len(reachability)` | wall clock | artefact |
|---|---|---|---:|---:|---|
| pre | pre | yes | **330** | 1748 s | complete |
| post | post | **yes** | **330** | 2708 s | complete |

Both legs complete, both under one configuration, and the number invariant across the rebuild —
which is what the control exists to show. The 2708 s against 1748 s is contention and not the jar:
the re-run shared the machine with five other GATOR processes from the 3.15 campaign, and the
quantity under test did not move. The truncated 3600 s leg stays in the table above as the record of
how the pair was first obtained; it is no longer what the control rests on.
