# Regenerate experiment 2026-05-08 result CSVs

Reusing the official rv-android logcat parser to regenerate the three
consolidated CSVs (summary, coverage, errors) from the preserved `.logcat`
files. See `docs/20260514_regenerar_planilhas.md` for the full design and
rationale.

## Why

The consolidated CSVs in `RESULTADOS/{summary,coverage,errors}_all.csv` were
produced without `static_data` (bug in `rv_platform.result_processor:177`), so
the coverage spreadsheet has empty `class/method/signature` columns and
`cov_method == cov_rv_method` everywhere. This pipeline reparses each `.logcat`
with the matching `StaticAnalysisData` and emits correct, line-by-line output.

## Files

| File | Role |
|------|------|
| `regenerate_container.py` | Level 1 worker: reparses every `.logcat` in one container directory and writes `summary_regen.csv`, `coverage_regen.csv`, `errors_regen.csv` inside that directory. Uses `multiprocessing.Pool` for per-logcat parallelism. |
| `concat_vm.py`            | Level 2: concatenates the 4 containers of one VM into `RESULTADOS/m<i>/{summary,coverage,errors}_regen.csv` (header-aware). |
| `concat_all.py`           | Level 3: concatenates the 4 VMs into `RESULTADOS/{summary,coverage,errors}_regen.csv`. |
| `run_all.sh`              | Orchestrates levels 1+2+3 locally. Dispatches 16 container jobs in parallel. |
| `verify.py`               | Audits the regenerated CSVs against the raw `.logcat` files. Generates `verification_report.md`. |

## Quick start

```bash
# Preflight: confirm static analysis JSONs are in place
ls /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/APKS_FINAL_JCA_DEXLIB/*.json | wc -l   # expect 190

# Smoke: regenerate one container and verify it
uv run python scripts/regenerate_results/regenerate_container.py \
    /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS/m1/results/exp_00/exp_00 \
    --workers 8
uv run python scripts/regenerate_results/verify.py --container \
    /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS/m1/results/exp_00/exp_00

# Full run (~30-60 min on SSD with 16 cores)
bash scripts/regenerate_results/run_all.sh

# Audit
uv run python scripts/regenerate_results/verify.py --full --compare-errors
```

## What verify.py checks

| Check | Description | Tolerance |
|-------|-------------|-----------|
| C1 | `RVSEC:` count in each `.logcat` == rows in `errors_regen.csv` for that tuple | strict equality |
| C2 | rows in `coverage_regen.csv` <= `RVSEC-COV:` count (deduplicated by signature) | upper bound |
| C3 | `cov_*` on the summary row == `cov_*` on the last chronological coverage row | +-0.01 |
| C4 | number of summary rows == number of `.logcat` files discovered | strict equality |
| C5 | (optional, `--compare-errors`) original `errors_all.csv` vs `errors_regen.csv` | report only |

Verify writes `verification_report.md` next to the consolidated CSVs and exits
0 only if C1, C2, C3, C4 all pass.

## Promotion (after verify passes)

```bash
cd /home/pedro/desenvolvimento/RV_ANDROID_NOVO/JOAO/RESULTADOS
mkdir -p backup_pre_regen
mv {summary,coverage,errors}_all.csv backup_pre_regen/
mv {summary,coverage,errors}_regen.csv .  # renames the consolidated regen files
for f in {summary,coverage,errors}; do
    mv "${f}_regen.csv" "${f}_all.csv"
done
```

The container- and VM-level `_regen.csv` files stay in place for traceability.

## Notes

- `package=""` is passed to `StaticAnalysisParser.parse_file()` because the
  GATOR upstream already filtered classes by the real code_package via
  `PackageDetector`. The JSON's `package` field is the manifest_package and can
  diverge (e.g. `app.dumdum` vs. `io.nekohasekai.sagernet`). See plan §9.
- `cov_class` in `coverage_regen.csv` is the real progressive class coverage
  (`called_classes / total_classes`), matching `summary_regen.cov_class` on the
  last chronological row. (Earlier versions aliased `cov_method` here, replicating
  a since-fixed bug; the offline tool now computes class coverage independently.)
- The `time` column in `errors_regen.csv` is an ordinal index (1, 2, ...);
  matches the convention of the original `errors_all.csv`.
- Does NOT modify any rv-android code. Only consumes public APIs:
  `parse_logcat_file`, `StaticAnalysisParser.parse_file`, `LogcatRepository`.
