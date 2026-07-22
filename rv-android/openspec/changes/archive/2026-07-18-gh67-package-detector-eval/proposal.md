## Why

The `PackageDetector` (rv-android-core) resolves the implementation `code_package` from APK
components and differs from the manifest package in 24.9% of APKs (42/169, INV-CORE-18). Its
accuracy has never been measured formally: the only validation today is a regression-style diff
against a prior run. An empirical audit of the 169 APKs of experimento-20260604
(`out/package_detector_audit/`) found 4 confirmed library mis-picks (4 apps / 3 libraries:
readeckapp→`net.openid.appauth`, venera & webspace→a Flutter plugin, whobird→`org.tensorflow.lite`;
`passwordstore` is NOT a mis-pick), and the state-of-the-art literature on Android package/library
detection (`docs/20260613_pesquisa_package_detection_sota.md`) establishes that rigorous evaluation
requires a labelled ground truth and precision/recall/F1 metrics. This change builds that evaluation
and records a baseline over the *current* pinned detector — deliberately before any detector change —
so the measurement is not biased by knowing the new implementation, and so the result satisfies the
formal-accuracy obligation (item A-1) of the ASE-journal article plan.

This directly answers reviewer **#65A#1** (verbatim: *"The heuristic package-detection algorithm's
effectiveness (e.g., recall, accuracy) is not reported, and it is unclear if the algorithm was
applied to all 557 apps or only the 103"*) and feeds **#65A#4(iii)** (app-vs-library scope of the
CogniCrypt comparison). The field precedent is **CryptoGuard (CCS'19, §6.2)**, which uses the same
manifest-package partition and reports *no* accuracy at all — so measuring this boundary places the
work above the field bar, not below it. **A3Ident (ICSME'20)** is the validated precedent for the
manifest/MainActivity anchor (our single-prefix detector is an instance of it). GitHub Issue: #67.

## What Changes

- Add a reproducible package-detection accuracy evaluation: a script that runs `PackageDetector`
  over the labelled dataset and computes accuracy (exact + namespace-tolerant) and
  precision/recall/F1 of `code_package` against ground truth, with **Wilson score confidence
  intervals** and **Cohen's κ** (detector vs independent oracle), stratified by `detection_method`
  **and** by obfuscation status, plus an app-vs-library confusion matrix, the library-mis-pick rate,
  and the **prefix-vs-set gap** (how often a single prefix is insufficient and a set of app packages
  would be needed — the number that decides whether the future Option D set-ification is warranted).
  Reuses the audit harness in `out/package_detector_audit/`. Metrics MUST also be reported
  **conditional on the 42/169 divergent stratum**, because the 99 `same_package` APKs trivially
  agree with any manifest-anchored oracle and inflate a global number.
- State the **evaluated universe (denominator) explicitly** to close #65A#1: the funnel
  557 candidate apps (static analysis) → 193 instrumented → ~169 experimental, and that the detector
  is evaluated over the experimental set actually carried into the misuse study (not the 557).
- Add a versioned ground-truth dataset for the 169 APKs of experimento-20260604 whose **authoritative
  backbone is the F-Droid upstream `applicationId`** (knowable because every APK is open-source —
  an oracle *independent* of the detector), with the **dominant-dex class-count histogram as an
  independent second signal** feeding Cohen's κ. Assistant/maintainer labelling is demoted to
  evidence-gathering and adjudication of ambiguous cases only; it is NOT the scoring oracle. Each
  row carries auditable evidence (F-Droid repo + manifest components + dex namespace).
- Record a baseline metrics report over the current pinned detector, reusable to measure the
  delta of the future detector change (issue for the manifest-affinity improvement, gated on this).
- Declare threats to validity: (a) the **conservative-undercount property** — a wrong pick is an
  inclusion-whitelist miss at both downstream gates (GATOR `isAppClass` `startsWith`;
  `static_analysis_parser` substring-keep) and runtime MOP violation counting is not scoped by
  `code_package`, so a mis-pick *under*-counts misuses, never inflates them; (b) the obfuscation
  defense rests on **manifest-preservation** (R8 keeps manifest-declared components, so the
  detector's *input* is clean) — NOT on "renaming is rare" (false in the field: 99.62% of obfuscated
  apps rename identifiers, arXiv 2502.04636); (c) single-annotator dependence for ambiguity
  adjudication; (d) pinned detector vs the gh63 version.
- No change to `PackageDetector` behavior. No structural dex signatures (LibScout/LibD-style),
  residual subtraction, A3Ident-lite, or detector replacement — out of scope, future work.

## Capabilities

### New Capabilities
<!-- none: this change adds no new runtime capability; it measures an existing one -->

### Modified Capabilities
- `core`: add a requirement that package-detection accuracy is formally evaluable against a
  versioned, evidence-backed ground truth (precision/recall/F1/accuracy, stratified by detection
  method), with a recorded baseline for the current detector. Companion to INV-CORE-18 (which
  defines `code_package` vs `package_name`). No change to detection behavior itself.

## Impact

- **rv-android-core**: home of `util/android/package_detector.py` and `domain/app.py`
  (`App.code_package`, INV-CORE-18). The evaluation reads the detector's public API; it does not
  modify it.
- **analysis domain** (consumer): static-analysis parsers receive `code_package` for class
  filtering (analysis spec §6, FR04–FR06). Detection accuracy bounds the correctness of that
  filtering — this evaluation quantifies that bound but changes nothing in the analysis pipeline.
- **Artifacts/data**: new evaluation script, a versioned ground-truth CSV with evidence, and a
  baseline metrics report. Reuses `out/package_detector_audit/run_audit.py` + `results.json`.
  Dataset: the 169 APKs of experimento-20260604 (canonical originals under `JOAO/APKs`).
- **Dependencies**: androguard (already a core dependency, pinned at **3.4.0a1** — NOT 4.1.4) covers
  manifest-component evidence used by the detector. The **dex class-count histogram oracle is new
  code**, not a free in-process capability: enumerating dex class names for the histogram needs an
  explicit dexlib2-based pass (or an androguard DEX API confirmed available on 3.4.0a1). This is an
  eval-only dependency on the analysis side; it does not touch the detector.
- **Provenance**: the ASE-journal pinned copy of the detector is NOT re-synced; the baseline is
  recorded against the as-of-experiment detector (record the git hash). Relates to FR33–FR37
  (core infrastructure) and the analysis FRs it feeds.
