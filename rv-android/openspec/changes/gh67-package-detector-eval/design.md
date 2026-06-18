## Context

`PackageDetector` (rv-android-core) is validated today only by a regression diff against a prior
run. The audit of the 169 APKs of experimento-20260604 (`out/package_detector_audit/run_audit.py`,
`results.json`) surfaced 4 library mis-picks but produced no accuracy figure. The SOTA literature
(`docs/20260613_pesquisa_package_detection_sota.md`) requires a labelled ground truth and
precision/recall/F1. This change builds that evaluation and records a baseline over the *current
pinned* detector, before any detector change, so the metric is defined independently of the future
implementation. It implements the spec delta in `specs/core/spec.md` (INV-CORE-33/34/35 and the
Package-Detection Accuracy Evaluation requirement). Relates to FR04–FR06 (analysis consumes
`code_package`) and FR33–FR37 (core). No detector behavior changes (INV-CORE-18 unchanged).

## Architecture

```
experiment_apks.txt (169)   ground_truth_exp20260604.csv
        │                    (oracle: F-Droid applicationId  ┐
        │                     + dex class-count histogram;    │ independent of detector
        │                     assistant labels = evidence only)┘
        ▼                                   │
  PackageDetector.detect_package ──► package_detector_eval.py ──► metrics report + baseline
  (pinned, via androguard APK)         (compare + stratify)        (acc/P/R/F1 + Wilson CI + κ,
        ▲                                                           confusion, mis-pick, prefix-vs-set
        │                                                           gap; conditional on the 42 divergent)
        └──────── reuses out/package_detector_audit/ runner/evidence ───────┘
```

The oracle is **independent of the predictor**: the detector's output (`code_package`) is scored
against the F-Droid upstream `applicationId` (authoritative, knowable from the open-source origin),
cross-checked by the dominant-dex class-count histogram. A Claude/maintainer-labelled census of the
detector's own output would measure self-consistency, not accuracy (refuted as "Option A" in
`docs/20260617_veredito_deteccao_pacote_modulo_primario.md` §4) — assistant labels are therefore
used only to gather evidence and adjudicate the cases where applicationId and the dex histogram
disagree.

### Key Components

| Component | Responsibility | Input | Output |
|-----------|---------------|-------|--------|
| `scripts/package_detector_eval.py::run` | Run detector over the 169, compare to ground truth, compute metrics | apks list, ground-truth CSV | metrics report (JSON + Markdown) |
| `scripts/package_detector_eval.py::load_ground_truth` | Load + validate ground truth (evidence present) | CSV path | dict apk→(label, evidence) |
| `scripts/package_detector_eval.py::compute_metrics` | P/R/F1/accuracy, stratified; confusion matrix | detections, labels | metrics dict |
| `data/package_detector_eval/ground_truth_exp20260604.csv` | Versioned ground truth + evidence columns | — | reference labels |
| `out/package_detector_audit/run_audit.py` (reused) | Detection runner + obfuscation/evidence signals | apks | per-APK detection + components |

## Mapping: Spec → Implementation → Test

| Requirement / Invariant | Implementation | Test |
|-------------|---------------|------|
| Req: Package-Detection Accuracy Evaluation | `scripts/package_detector_eval.py::run/compute_metrics` | `test_eval_metrics_on_fixture` |
| Scenario: Metrics vs ground truth (stratified) | `compute_metrics(..., by="detection_method")` | `test_eval_stratified` |
| Scenario: Evidence-backed labels | `load_ground_truth` rejects rows w/o evidence | `test_ground_truth_requires_evidence` |
| Scenario: Maintainer audit sample | audit-column workflow in CSV; report section | manual (documented protocol) |
| Scenario: Baseline tagged with git hash | `run` stamps `detector_git_hash` into baseline | `test_baseline_records_hash` |
| Scenario: Reproducible scoring | deterministic `compute_metrics` (no sampling in scoring) | `test_eval_deterministic` |
| INV-CORE-33 (evidence present) | `load_ground_truth` guard | `test_ground_truth_requires_evidence` |
| INV-CORE-34 (reproducible) | pure-function scoring | `test_eval_deterministic` |
| INV-CORE-35 (hash-tagged baseline) | `run` write guard | `test_baseline_records_hash` |

## Goals / Non-Goals

**Goals:**
- A reproducible accuracy evaluation of `PackageDetector` with P/R/F1/accuracy, stratified by method.
- A versioned, evidence-backed ground truth for the 169 APKs.
- A baseline over the pinned detector, reusable to measure a future detector change's delta.
- Honest threats-to-validity reporting (single annotator, obfuscation, pinning).

**Non-Goals:**
- Changing `PackageDetector` (Change B / manifest-affinity, future issue).
- Structural dex signatures (LibScout/LibD-style) — future work.
- Adaptive extraction depth (deferred, #68).
- Re-syncing the ASE-journal pinned detector copy.

## Decisions

**D-A — Eval calls the detector directly; reuses the audit harness for evidence, not for scoring.**
The eval script invokes `PackageDetector.detect_package` itself (deterministic, version-pinned)
rather than consuming the transient `out/.../results.json`. It reuses the audit harness's
component-extraction and obfuscation-signal helpers for the *evidence* columns. Why: scoring must be
reproducible from versioned inputs (INV-CORE-34); depending on a temporary `out/` artifact is not.

**D-B — Ground truth is an independent oracle (F-Droid `applicationId` + dex histogram), not a
labelled census of the detector's output.** Using the detector's own output as truth — even
assistant-relabelled and audited — measures self-consistency, not accuracy, because the oracle is
not independent of the predictor (refuted as "Option A" in the main verdict,
`docs/20260617_veredito_deteccao_pacote_modulo_primario.md` §4). The authoritative backbone is the
**F-Droid upstream `applicationId`**: every APK in the corpus is open-source, so its true application
package is knowable from the F-Droid repository (`metadata/<applicationId>.yml` / `index-v2.json`),
independently of what the detector picked. The **dominant-dex class-count histogram** is an
independent second signal: it confirms which namespace actually carries the app's classes and feeds
**Cohen's κ** (detector vs oracle). The assistant/maintainer role is demoted to (a) gathering the
evidence columns and (b) adjudicating the minority of APKs where `applicationId` and the dex
histogram disagree; that residual single-annotator dependence is a declared threat to validity, far
narrower than labelling all 169. This is "residual signal as a cross-check," where TPL recall <50%
does not bite, per the residual-refutation verdict
(`docs/20260617_veredito_abordagem_residual_deteccao_pacote.md` §9b).

**D-B2 — Report metrics conditional on the divergent stratum.** In 99/169 APKs `code_package ==
manifest == applicationId` (`same_package`), so any manifest-anchored oracle agrees trivially and a
global accuracy figure is inflated by those agreements. The eval MUST therefore report the headline
metrics (a) globally and (b) **conditional on the 42/169 divergent APKs** — the only stratum where
the detector makes a non-trivial decision and where the 4 mis-picks live.

**D-C — Baseline over the pinned (as-of-experiment) detector, git-hash tagged.** Provenance: the
experiment dataset and the ASE-journal article were produced with this detector version. The
baseline records its git hash (INV-CORE-35); the gh63 / future versions are measured separately as
deltas. The pinned copy is not re-synced.

**D-D — Primary metric is accuracy (exact + namespace-tolerant); P/R/F1 framed over the app-vs-library
binary decision.** Our task is single-label (one `code_package` per APK), not set retrieval like the
TPL literature, so exact-match accuracy is primary. P/R/F1 is reported over the binary "is the
detected package a correct application package (vs a library mis-pick)", with the confusion matrix
making the 4 mis-picks first-class. Namespace-tolerant match counts a detected package that is an
ancestor/descendant of the truth within the app namespace. Alternative (multi-class over
detection_method correctness) is recorded as a secondary view. This nuance is called out so the
article does not misframe the metric as set-retrieval recall.

**D-E — Statistical apparatus: Wilson score CI + Cohen's κ, doubly stratified; plus the prefix-vs-set
gap.** Point estimates over 169 (and 42) APKs are small samples, so every reported rate carries a
**Wilson score 95% confidence interval** (robust for proportions near 0/1, unlike the normal
approximation). Detector-vs-oracle agreement is reported as **Cohen's κ** with the Landis–Koch
interpretation band. Metrics are stratified by `detection_method` AND by **obfuscation status**. The
eval also computes the **prefix-vs-set gap**: the fraction of APKs whose application code does not
fit under a single namespace prefix (so a *set* of app packages would be required). This gap is the
decision variable for the deferred Option D (set-ification) — it is measured here, not acted on.

**D-F — Threats framing is empirically grounded, not asserted.** Two threats are settled by evidence
and stated as such in the report, not hedged:
- **Conservative under-count (directional).** A wrong package pick *under*-counts misuses; it cannot
  inflate them. Both downstream scoping gates are inclusion-whitelists — GATOR
  `RvsecAnalysisClient.isAppClass` keys on `className.startsWith(filterPackage)`, and
  `static_analysis_parser.py:356` keeps only classes whose name contains `code_package` — so a
  library mis-pick matches ≈0 of the app's real JCA classes and silently shrinks the analysed
  universe. Runtime MOP violation counting (`rv-coverage/.../tracker.py`) is driven by `call()`-
  pointcut weaving + logcat and is **not** scoped by `code_package` at all. There is no
  exclusion-blacklist path, so the "leakage → over-count" failure mode does not occur in this
  pipeline. This makes the "inert error" defense valid and directional.
- **Obfuscation defense rests on manifest-preservation, not renaming-rarity.** R8 preserves
  manifest-declared component names, so the detector's *input* is clean even when the dex *body* is
  renamed; the defense does NOT rely on the (field-false) premise that renaming is rare — 99.62% of
  obfuscated apps rename identifiers (arXiv 2502.04636). The obfuscation metric therefore measures
  **dex-body class renaming** (via the histogram pass), not manifest-component renaming; the existing
  audit's "renamed components 1.2%" figure measures manifest components and must not be reused as a
  dex-body proxy.

## API Design

### `load_ground_truth(csv_path: str) -> dict[str, GroundTruthRow]`
- **Pre**: CSV exists with columns `apk, code_package, evidence_kind, evidence`.
- **Post**: returns one row per APK; raises if any scored row lacks an `evidence` value (INV-CORE-33).
- **Error**: `ValueError` on a label without evidence.

### `compute_metrics(detections: list[Detection], truth: dict, by: str | None) -> Metrics`
- **Pre**: `detections` and `truth` keyed by the same APK identifiers; `truth` carries the
  independent oracle label (F-Droid `applicationId`) and the dex-histogram signal.
- **Post**: returns accuracy (exact + namespace) and precision/recall/F1, each with a **Wilson score
  95% CI**; **Cohen's κ** (detector vs oracle); the **prefix-vs-set gap**; the app-vs-library
  confusion matrix and mis-pick count. Reported globally AND conditional on the divergent stratum
  (D-B2). Optionally stratified by `by` (`detection_method` or `obfuscation_status`). Pure function
  (INV-CORE-34).

### `run(apks_filter: str, ground_truth_csv: str, out_dir: str) -> None`
- **Post**: writes a JSON + Markdown metrics report and a baseline record tagged with
  `detector_git_hash` (INV-CORE-35). Per-APK detector exceptions recorded as error rows.

## Data Flow

`experiment_apks.txt` → for each APK, `androguard.APK` → `PackageDetector.detect_package` →
`Detection(code_package, detection_method, …)`. In parallel, `load_ground_truth` yields the labelled
truth. `compute_metrics` joins on APK id, classifies each as exact / namespace / app-mis-pick /
wrong, stratifies by `detection_method`, and emits the report + baseline.

## Error Handling

| Error | Source | Strategy | Recovery |
|-------|--------|----------|----------|
| `ValueError` (label sans evidence) | `load_ground_truth` | Fail fast — invalid dataset | Add evidence to the CSV row |
| Detector exception on one APK | `detect_package` | Record error row, continue | Inspect APK; excluded from metrics, counted as error |
| APK file missing | runner | Record error row, continue | Restore APK under `JOAO/APKs` |
| Detector git hash mismatch on baseline write | `run` | Refuse to overwrite pinned baseline (INV-CORE-35) | Write to a version-tagged path instead |

## Risks / Trade-offs

- [Oracle not independent of predictor (circularity)] → D-B: authoritative oracle is the F-Droid `applicationId` + dex histogram, not a labelled census of the detector's output; assistant labels only adjudicate disagreements.
- [Obfuscation blinds the dominant-dex-namespace evidence for some APKs] → fall back to F-Droid `applicationId` (always available, open-source) + manifest-component evidence; record which APKs lacked dex-body evidence.
- [Single-label P/R/F1 can be misread as TPL set-retrieval recall] → D-D fixes the framing; accuracy is primary; the prefix-vs-set gap (D-E) is reported separately.
- [Pinned detector ≠ gh63] → baseline git-hash tagged; provenance recorded (INV-CORE-35).
- [Dex class enumeration assumed free in-process] → androguard is pinned at 3.4.0a1; the histogram pass is new code (dexlib2 alternative or a confirmed 3.4.0a1 DEX API), eval-only, isolated from the detector. Register before task 2.
- [Global accuracy inflated by the 99 `same_package` agreements] → D-B2: report conditional on the 42 divergent APKs.

## Testing Strategy

| Layer | Coverage |
|-------|----------|
| Unit | `compute_metrics` on a small synthetic fixture (known P/R/F1/accuracy); `load_ground_truth` evidence guard; determinism; baseline hash stamping |
| Integration | full run over the 169 produces a report; the 4 known mis-picks appear in the confusion matrix; counts reconcile with the audit (`results.json`) |
| Manual (documented) | maintainer audit of the stratified sample + adjudication recorded in the CSV |

## Open Questions

- Final exact definition of the namespace-tolerant match (ancestor only, or ancestor+descendant within app namespace?) — to fix during labelling.
- Stratified-audit sample size for `same_package` beyond the 42 mismatches (all 42 mismatches are mandatory; `same_package` sample size TBD with the maintainer).
- Report location convention: `docs/` (narrative) vs `data/package_detector_eval/` (machine) — propose both: machine metrics in `data/`, narrative baseline summary in `docs/`.
