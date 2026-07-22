## Purpose

The Core domain owns `PackageDetector` (`modules/rv-android-core/src/rv_android_core/util/android/package_detector.py`)
and the `App.code_package` property (`domain/app.py`), governed by INV-CORE-18: `package_name`
comes from the manifest, `code_package` is the detected implementation package, and the two differ
in 24.9% of APKs (42/169). Everything downstream that filters classes by application package — static
analysis parsing, coverage attribution, monitored-operation classification — inherits the
correctness of that detection. Until now the detector's accuracy was never measured against a
known-correct reference; it was only diffed against a previous run, which catches regressions but
cannot state how often the detector is right.

This capability adds a **formal evaluation** of package-detection accuracy. It does not change how
detection works. It defines a versioned ground-truth dataset (the correct `code_package` per APK,
each label backed by auditable evidence), a reproducible script that runs the detector over that
dataset and computes precision/recall/F1/accuracy, and a recorded baseline over the current detector
so a future detector change can be measured as a delta against it. The evaluation is established
*before* any detector change so the metric is defined independently of the new implementation
(pre-registration), and so the result is publishable as the formal-accuracy evidence the literature
on Android library/package detection expects (LibD-style manual ground truth; precision/recall/F1).

The ground truth is an oracle **independent of the detector**: the authoritative label is the
F-Droid upstream `applicationId` (knowable because every APK is open-source), cross-checked by the
dominant-dex class-count histogram (an independent structural signal). Scoring the detector against
a relabelled census of its own output would measure self-consistency, not accuracy; assistant and
maintainer labelling is therefore confined to gathering evidence and adjudicating the minority of
APKs where the two independent signals disagree, and that residual dependence is recorded as a
threat to validity. The evaluation is an offline analysis artifact (a script plus versioned data and
a report); it has no effect on the runtime behavior of the detector or of any module that consumes
`code_package`.

## Data Contracts

### Input
- `apks: list[str]` — the 169 APKs of experimento-20260604 (canonical originals under `JOAO/APKs`), via the filter list `experimento-20260604/filters/experiment_apks.txt` — the **experimental** universe (the funnel is 557 static → 193 instrumented → ~169 experimental; the detector is evaluated over the experimental set carried into the misuse study, closing reviewer #65A#1's denominator question).
- `ground_truth: CSV` — per-APK correct `code_package` whose authoritative label is the **F-Droid upstream `applicationId`** (independent of the detector), with the **dominant-dex class-count histogram** as an independent second signal, plus evidence columns (F-Droid repo, manifest components, dex namespace), versioned in the repository.
- `detector_output: PackageDetectionResult` — produced by running `PackageDetector.detect_package(apk)` on each APK (the subject under measurement).

### Output
- `metrics: report` — accuracy (exact + namespace) and precision/recall/F1 of `code_package` against the independent oracle, each with a **Wilson score 95% CI**; **Cohen's κ** (detector vs oracle); the **prefix-vs-set gap**; an app-vs-library confusion matrix; library-mis-pick rate. Reported globally AND conditional on the 42/169 divergent stratum, stratified by `detection_method` and obfuscation status. Consumer: the maintainer and the ASE-journal article (item A-1).
- `baseline: record` — the metrics computed over the current pinned detector, tagged with the detector's git hash, reused to measure the future detector change's delta.

### Side-Effects
- **[Filesystem]**: writes the ground-truth CSV (with evidence), the evaluation script, and the baseline metrics report to versioned locations. No mutation of the detector, of `App`, or of any experiment dataset.

### Error
- The evaluation MUST treat a per-APK detector exception as a recorded error row (not a crash of the whole run), mirroring the existing audit harness behavior.

## Invariants

- **INV-CORE-33**: Every ground-truth label MUST carry at least one auditable evidence field (F-Droid upstream repository, manifest components, or dominant dex namespace). A label without evidence is invalid and MUST NOT be counted in metrics.
- **INV-CORE-36**: The scoring oracle MUST be independent of the detector. The authoritative ground-truth label is the F-Droid upstream `applicationId`, cross-checked by the dominant-dex class-count histogram; a label derived from `PackageDetector`'s own output (even relabelled) MUST NOT be used as the oracle. Assistant/maintainer labelling is limited to evidence-gathering and adjudication of cases where the two independent signals disagree.
- **INV-CORE-34**: The evaluation MUST be reproducible — running the script against the versioned ground truth and the pinned detector MUST yield identical metrics across runs (no nondeterministic sampling in the scored computation).
- **INV-CORE-35**: The recorded baseline MUST be tagged with the detector's git hash; metrics computed against a different detector version MUST NOT overwrite the pinned-detector baseline.

## ADDED Requirements

### Requirement: Package-Detection Accuracy Evaluation

The system SHALL provide a reproducible evaluation of `PackageDetector` accuracy against a
versioned, evidence-backed ground truth, reporting precision/recall/F1/accuracy of the detected
`code_package`, and SHALL record a baseline for the current detector. This evaluation MUST NOT
alter detection behavior (INV-CORE-18 is unchanged).

#### Scenario: Metrics computed against the independent oracle
- **WHEN** the evaluation script runs `PackageDetector.detect_package` over the 169 APKs of experimento-20260604 and compares each `code_package` to the independent oracle (F-Droid `applicationId`, cross-checked by the dex class-count histogram)
- **THEN** it MUST emit accuracy (exact-match and per-namespace) and precision, recall, F1 for `code_package`, each with a **Wilson score 95% confidence interval**, and **Cohen's κ** between detector and oracle
- **AND** it MUST report those metrics both globally AND conditional on the 42/169 divergent stratum (where `code_package ≠ manifest`), since the `same_package` majority trivially agrees with a manifest-anchored oracle
- **AND** it MUST stratify the metrics by `detection_method` (same_package, single_package, common_prefix, most_common, similarity_match, no_consensus, game_engine) AND by obfuscation status
- **AND** it MUST emit an app-vs-library confusion matrix, the library-mis-pick count, and the **prefix-vs-set gap** (fraction of APKs whose app code does not fit a single prefix)

#### Scenario: Ground-truth label is independent and evidence-backed
- **WHEN** a ground-truth row assigns the correct `code_package` for an APK (e.g., `de.readeckapp_900.apk` → `de.readeckapp`, not the merged library `net.openid.appauth`)
- **THEN** the authoritative label MUST be the F-Droid upstream `applicationId`, NOT a relabelling of the detector's output (INV-CORE-36)
- **AND** the row MUST include at least one evidence field justifying the label (F-Droid repository, manifest components, or dominant dex namespace)
- **AND** a row lacking evidence MUST be excluded from the metric computation (INV-CORE-33)

#### Scenario: Maintainer adjudicates signal disagreements (independence preserved)
- **WHEN** the F-Droid `applicationId` and the dex class-count histogram disagree on an APK's correct package
- **THEN** the maintainer MUST adjudicate that APK and record the resolution and its evidence in the dataset
- **AND** the set of adjudicated APKs and the residual single-annotator dependence MUST be declared as a threat to validity in the report
- **AND** APKs where the two independent signals agree MUST NOT require manual labelling

#### Scenario: Baseline recorded over the pinned detector
- **WHEN** the evaluation runs against the current as-of-experiment detector
- **THEN** the resulting metrics MUST be recorded as the baseline, tagged with the detector's git hash (INV-CORE-35)
- **AND** the baseline MUST be reusable to compute the delta of a future detector change without re-labelling the ground truth

#### Scenario: Reproducible scoring
- **WHEN** the evaluation script is run twice against the same versioned ground truth and the same detector
- **THEN** it MUST produce identical metrics both times (INV-CORE-34)
- **AND** a per-APK detector exception MUST be recorded as an error row rather than aborting the run
