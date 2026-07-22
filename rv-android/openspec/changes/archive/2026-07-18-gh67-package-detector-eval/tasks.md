<!-- Single-module change (rv-android-core + scripts/data). Sequential; no subagent orchestration.
     Critical path: 1 (ground truth) -> 2 (eval script) -> 3 (baseline run) -> 4 (report) -> 5 (verify).
     Group 1 produces the labelled dataset the rest depends on. -->

## 0. Pre-registration of the eval design (do before any labelling)

- [ ] 0.1 Register the androguard caveat: androguard is pinned at **3.4.0a1** (not 4.1.4); decide and document the dex class-name enumeration path for the histogram oracle (dexlib2 pass or a confirmed 3.4.0a1 DEX API). Eval-only; isolated from the detector (design D-F / Risks)
- [ ] 0.2 State the evaluated universe explicitly: the funnel 557 static → 193 instrumented → ~169 experimental, and that the detector is evaluated over the experimental set carried into the misuse study (closes reviewer #65A#1's denominator question)

## 1. Ground Truth Dataset (independent oracle: F-Droid applicationId + dex histogram)

- [ ] 1.1 Define the ground-truth CSV schema: `apk, code_package, applicationId_fdroid, dex_histogram_top, signals_agree, evidence_kind, evidence, adjudication` at `data/package_detector_eval/ground_truth_exp20260604.csv`
- [ ] 1.2 Populate the authoritative label per APK from the **F-Droid upstream `applicationId`** (`metadata/<applicationId>.yml` / `index-v2.json`) — independent of the detector (INV-CORE-36)
- [ ] 1.3 Compute the **dominant-dex class-count histogram** per APK as the independent second signal; record `signals_agree` (applicationId vs dex-histogram top namespace). This is the dex-body obfuscation signal too (T5 — measures dex-body renaming, NOT manifest components)
- [ ] 1.4 Maintainer adjudicates only the APKs where `signals_agree = false`; record `adjudication` + evidence (INV-CORE-33). APKs where both signals agree need no manual labelling; record the adjudicated set as a threat to validity

## 2. Evaluation Script

- [ ] 2.1 Create `scripts/package_detector_eval.py` with `load_ground_truth(csv) -> dict` (rejects rows lacking evidence — INV-CORE-33)
- [ ] 2.2 Implement `compute_metrics(detections, truth, by=None)`: accuracy (exact + namespace) and precision/recall/F1, each with a **Wilson score 95% CI**; **Cohen's κ** (detector vs oracle); **prefix-vs-set gap**; app-vs-library confusion matrix; mis-pick count. Report globally AND conditional on the 42 divergent stratum (D-B2); support `by=detection_method` and `by=obfuscation_status`. Pure/deterministic (INV-CORE-34). Encode the D-D framing (single-label accuracy primary; P/R/F1 over app-vs-lib binary)
- [ ] 2.3 Implement `run(apks_filter, ground_truth_csv, out_dir)`: invoke `PackageDetector.detect_package` per APK (pinned), join with truth, write JSON + Markdown report and a baseline record tagged with `detector_git_hash` (INV-CORE-35); per-APK exceptions recorded as error rows
- [ ] 2.4 Add unit tests (`modules/rv-android-core/tests/util/test_package_detector_eval.py`): `compute_metrics` on a synthetic fixture with known P/R/F1/accuracy; `load_ground_truth` evidence guard; determinism (INV-CORE-34); baseline hash stamping (INV-CORE-35)
- [ ] 2.5 Run `/rv-doc-code scripts/package_detector_eval.py`
- [ ] 2.6 Run `/rv-test-run rv-android-core`

## 3. Baseline Over the Pinned Detector

- [ ] 3.1 Run the evaluation over the 169 against the pinned detector; produce the baseline metrics
- [ ] 3.2 Reconcile with the audit (`out/package_detector_audit/results.json`): the 4 known mis-picks (readeckapp→appauth, venera/webspace→flutter plugin, whobird→tensorflow) MUST appear in the app-vs-library confusion matrix
- [ ] 3.3 Record the detector git hash alongside the baseline (provenance — INV-CORE-35)

## 4. Report & Threats to Validity

- [ ] 4.1 Write the narrative baseline summary at `docs/20260613_package_detector_baseline.md`: accuracy + Wilson CI, Cohen's κ, per-method AND per-obfuscation stratification, confusion matrix, mis-pick rate, prefix-vs-set gap, all reported globally + conditional on the 42 divergent
- [ ] 4.2 Document threats to validity: (a) **conservative under-count** — cite the code evidence that both downstream gates are inclusion-whitelists (GATOR `RvsecAnalysisClient.isAppClass` `startsWith`; `static_analysis_parser.py:356` substring-keep) and runtime MOP counting (`rv-coverage/.../tracker.py`) is not scoped by `code_package`, so a mis-pick under-counts, never inflates (design D-F); (b) **obfuscation defense = manifest-preservation**, not renaming-rarity (99.62% of obfuscated apps rename, arXiv 2502.04636); (c) adjudicated-APK / single-annotator dependence; (d) pinned-detector vs gh63 (record hash); (e) single-label metric framing (D-D)
- [ ] 4.3 Related-work / positioning notes: cite **CryptoGuard CCS'19 §6.2** (same manifest partition, reports no accuracy → measuring it is above the field bar), **A3Ident ICSME'20** (validated manifest/MainActivity-anchor precedent), **Zhan et al. DOI 10.1145/3324884.3416582** (NOT arXiv:2108.03787); for #65A#4(iii) state our detector imposes an app/lib boundary while CogniCrypt (Soot `isApplicationClass`) does not — and do NOT cite the "CogniCrypt 4-prefix list" (it is a co-author's own R post-processing script, not CogniCrypt behavior)
- [ ] 4.4 Cross-link the result to the ASE-journal article item A-1 and reviewer #65A#1 (do not edit article `.tex` here — handoff note only)

## 5. Verify

- [ ] 5.1 Run `/rv-qa-lint-fix rv-android-core`
- [ ] 5.2 Run `/rv-verify rv-android-core`
- [ ] 5.3 Run `/rv-code-reviewer`
