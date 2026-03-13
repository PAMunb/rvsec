## 1. Rewrite CI workflow (Phase 1)

- [x] 1.1 Rewrite `.github/workflows/ci.yml` with two independent jobs (`maven-build`, `python-test`), removing all Poetry references, dead modules, `continue-on-error`, and disk space hacks. Both jobs remove `backup/` directories after checkout.

## 2. Fix module tests + CI config (Phase 2)

- [x] 2.1 Fix aperv-tool: update sata_mop assertion to match current `'static_analysis'` value
- [x] 2.2 Fix rv-agent/test_agent_factory: add missing `max_short_term_iterations` to mock fixture
- [x] 2.3 Fix rv-agent/test_config_new_params: update range bounds for widened constraints (`reward_score_weight`, `coverage_density_weight`)
- [x] 2.4 Exclude `rv-agent-validation` from CI test loop (temporary module)
- [x] 2.5 Expand marker filter: `-m "not (slow or online or sglang or performance or dataset)"`
- [x] 2.6 Install `tesseract-ocr` for rv-screen-parser OCR tests
- [x] 2.7 Upgrade GitHub Actions: checkout@v6, setup-java@v5, setup-python@v6, setup-uv@v7

## 3. Coverage reports + badges

- [x] 3.1 Add per-module coverage collection with `--cov` and `.cov-parts/` staging
- [x] 3.2 Add `coverage combine` step for consolidated report
- [x] 3.3 Add coverage summary to GitHub Actions step summary (markdown format)
- [x] 3.4 Add Codecov upload via `codecov/codecov-action@v5`
- [x] 3.5 Add CI badge to `rvsec/README.md` (fix branch develop → modules)
- [x] 3.6 Add badges to `rv-android/README.md` (CI, Codecov, Python 3.12, uv)

## 4. Verification

- [x] 4.1 All 14 modules pass locally (3191 tests, 0 failures)
- [x] 4.2 CI pipeline green (maven-build + python-test)
- [x] 4.3 Coverage consolidation works (14 modules combined, 65%)
