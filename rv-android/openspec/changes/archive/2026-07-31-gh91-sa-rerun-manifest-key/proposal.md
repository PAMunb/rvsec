# Proposal: gh91-sa-rerun-manifest-key

GitHub Issue: #91

## Why

The `remove-package-detector` change in the `ase-journal` repository re-scopes the paper's
dataset to 164 apps in scope / 163 analysed, keyed on the **neutralised manifest package**
(`Mneut`) instead of on a package inferred at analysis time. Of those 164, 134 already have
a static analysis whose filtering key matches. **The remaining 30 do not, and their
re-analysis is the upstream gate this change exists to release** — `remove-package-detector`'s
task group 0 is blocked waiting for exactly these 30 JSONs, the regenerated CSVs, and a
per-app record.

The key those 30 must be analysed under is the neutralised manifest package, not the raw
applicationId, and the reason is purely factual: **on this corpus the raw applicationId is
unusable as a filter.** These APKs are built from source with `assembleDebug`, and Gradle's
`applicationIdSuffix` appends a build-type segment to the applicationId **without changing
the code's namespace**. In 23 of the 30 APKs listed in `30_apks.csv` the applicationId ends
in `.debug` (20), `.dev` (2) or `.current` (1). The suffix exists in the installable package
identifier, not in class names: `org.fossify.calendar_20.apk` declares
`org.fossify.calendar.debug`, and none of its 2954 analysed classes contains `.debug`.
Filtering on that value would match zero classes and yield an empty analysis that still
reports success.

The `Mneut` values are **not computed here**. They come from the frozen `30_apks.csv`
(byte-identical to `ase-journal/docs/20260730_sa_rerun_164.csv`, sha256
`7ea67f52f69d4d574ef82c9a49d66982a8208bc52bcf6437ecf22445bb388297`), whose `Mneut` column
was derived and validated upstream against adjudicated ground truth. This change consumes
that column verbatim.

## What Changes

This is an **operational change**. It produces data and provenance; it does not modify the
behaviour of any rv-android module.

- **The 30 APKs are re-analysed by invoking GATOR directly.** The driver reads
  `30_apks.csv`, and for each row runs `lib/gator/gator` with
  `-clientParam codePackage=<Mneut>` taken verbatim from the CSV. It does **not** go through
  `rv-static-analysis analyze`, whose only source for that parameter is `App.code_package` —
  the property backed by `PackageDetector`.
- **Input: the uninstrumented APKs of the corpus**,
  `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/APKS/` (348 APKs, all 30 present).
  Never the instrumented copies under `APKS_INSTRUMENTED_*`, which carry woven monitor
  classes and a different class universe.
- **Output: a dedicated, previously non-existent directory**,
  `/home/pedro/desenvolvimento/RV_ANDROID_NOVO_DATASET/SA_RERUN_gh91/`. Installing the new
  JSONs into the corpus is a **manual step performed by the owner, outside this change** —
  see "Handoff" below.
- **A per-app record and a provenance note are produced** for the article's repository: the
  exact argv per APK, the key used, the full key-dependent `sa_*` block, and sha256 pins.
- **No rv-android module is modified.** `App`, `PackageDetector`, `rv-static-analysis`,
  `rv-platform` and `rv-instrumentation-ajc` are untouched. No delta specs accompany this
  change, because no capability's behaviour changes.
- **`rvsec-gator` is not touched and not rebuilt**, honouring the standing rule.
  `RvsecAnalysisClient.java:88-90` resolves
  `filterPackage = (codePackage != null) ? codePackage : manifestPackage`, so passing
  `Mneut` through the parameter it already accepts is all that is required.
- **The dynamic experiment is not re-executed.** Instrumentation was never filtered by
  package (the dexlib2 instrumenter has zero `codePackage` references; capture is tag-only),
  and it was verified upstream that the persisted logcats already carry `RVSEC-COV` events
  for the classes of the new key in all 30 apps (11k–675k events each).

### Explicitly out of scope

**Removing `PackageDetector` is deferred to a separate, later change.** It stays live in
rv-android, and that is accepted. The article removes the package detector from its
methodology **without discussing it at all** — it makes no claim about the detector being a
poor construct — so there is no assertion in the paper that requires a counterpart in the
code. A replacement must serve the whole 348-APK corpus, not the 30 of this re-analysis;
conflating the two is what made the earlier draft of this change incoherent.

## Capabilities

### New Capabilities

None.

### Modified Capabilities

None. No rv-android capability changes behaviour. The scope of this change is data
production and provenance, specified in `design.md` and `tasks.md`.

## Impact

- **Modules**: none modified. New scripts are added under `scripts/` — the re-analysis
  driver, the unattended campaign runner that owns the escalation rounds, and the validation
  gate; they introduce no import into any module and change no existing behaviour.
- **External systems**: `rvsec-gator` and `rvsec-analysis-client.jar` are unchanged and not
  rebuilt.
- **Requirements**: FR04 (static analysis of APKs), FR05 (reachability against MOP
  specifications), FR06 (REACH analysis output) — the outputs are recomputed under a
  different filtering key; the requirements themselves do not change.
- **Data — scope narrows in the multi-module apps.** Measured against the current JSONs
  under both keys, **12 of the 30 shrink, 13 are verified unchanged, and 5 widen** — of the
  widening five, only `org.wikipedia` (0 → 1139) is measurable today; `app.pachli`,
  `com.jerboa`, `net.osmtracker` and `swati4star.createpdf` have predecessor JSONs already
  pre-filtered narrow, so their growth cannot be measured before the re-run. The twelve:
  `org.fossify.paint` 1991 → 108 classes (5.4%), `voicerecorder` 2082 → 199, `keyboard`
  2106 → 223, `math` 2168 → 285, `notes` 2277 → 394, `messages` 2600 → 717, `musicplayer`
  2604 → 721, `calendar` 2954 → 1071, `com.afkanerd.deku` 1385 → 505 (36.5%), `binaryeye`
  403 → 382, `ch.rmy.android.http_shortcuts` 7139 → 7029 (loses `ch.rmy.android.framework.*`),
  `ua.com.radiokot.photoprism` 3029 → 3007 (loses `ua.com.radiokot.license.*`). The fossify
  collapse is `org.fossify.commons` leaving the scope. This makes a **hard gate mandatory**:
  every one of the 30 must keep `sa_reaches_mop = True` with a non-empty reaches-MOP
  denominator, since a narrower scope can push the monitored JCA surface out of the key. A
  failure is not fixable here — it shrinks the paper's 164/163.
- **Cross-repository**: `ase-journal`'s `remove-package-detector` has an upstream-gate task
  group waiting on the regenerated `summary`/`coverage`/`errors` CSVs with sha256 pins, a
  per-app record frozen there as `dataset/pkgdet_validation/sa_rerun_record.csv`, and the
  preserved predecessor JSONs as provenance. The delivery is **two-staged**: this change
  delivers the record, provenance and manifests (task 4.7); the CSVs and the `.pkgdet`
  JSONs exist only after the owner's manual handoff (task group 5), whose delivery (5.5)
  releases the upstream gate in full.

## Handoff — what the owner does manually

This change stops at a fresh directory plus a manifest. Installing the results into the
corpus and regenerating the CSVs are manual steps, deliberately kept outside the automated
scope:

1. Copy the 30 JSONs from `SA_RERUN_gh91/` into
   `RV_ANDROID_NOVO_DATASET/APKS_INSTRUMENTED_jca_dexlib2_experimento-20260706/`, preserving
   each predecessor as `<apk>.json.pkgdet`. **That flat directory is the one the
   consolidation reads** — `experimento-20260706/scripts/consolidate_offline.sh` fixes it as
   `STATIC_DIR`, and `scripts/regenerate_results/regenerate_container.py:114` opens it. The
   copies under `rvsec-dataset/static_analysis/` (345 JSONs) and inside
   `RESULTS/m*/results/exp_*/exp_*/<apk>/` (220 JSONs) are not read by **this** consolidation
   path; whether to keep them in sync is the owner's call. The qualifier matters:
   `rv-platform run --process-results` *does* read the co-located copies, which is why
   upstream 0.1 reads as plausible — see `design.md` §Consolidation.
2. Re-run the consolidation and promote. `design.md` §Consolidation records the exact
   command and the two gotchas that make the obvious alternative wrong.
