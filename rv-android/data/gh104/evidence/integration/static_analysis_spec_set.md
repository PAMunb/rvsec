# 10.0 — the static analysis reads the selected specification set

What this records: the repair of audit finding G12 (`juizglobal_relatorio.md:234`), run on 2026-08-24.

## The defect

`RVStaticAnalysisConfig` defaults `mop_dir` to the literal `resources/jca`
(`modules/rv-static-analysis/src/rv_static_analysis/config.py:199-208`), and
`get_static_analysis_config()` overrode nothing. So every `jca_android` run computed its
monitored-operation targets, its GATOR reachability and its coverage denominator against the
23 frozen `jca` specifications while the APK was instrumented with the successor's — two views of the
same run, disagreeing by construction, with nothing in the record saying which set each came from.

## The repair

The set → directory mapping moves out of `get_monitored_operations_config()` into
`ExperimentConfig.resolve_spec_set_dir(rvsec_root)`, and both consumers call it:

| consumer | what it does with the answer |
|---|---|
| `get_monitored_operations_config()` | `RVGeneratorConfig.mop_specs_dir` — the specs the APK is instrumented with |
| `get_static_analysis_config()` | `RVStaticAnalysisConfig.mop_dir` — the specs the static view is computed over |

One resolution, one mapping. The mapping was not copied: a second copy is exactly how the two views
drifted apart, and a copy would let a future set reach one consumer and not the other.

`targets_file` is untouched. `rv-experiment` never sets it — `grep -rn "targets_file" modules/`
outside `rv-static-analysis/` returns nothing — so the INV-ANA-33 mutex is unaffected, and
`RVStaticAnalysisConfig(...)` is constructed in exactly one place in the whole workspace
(`rv_experiment/config.py:984`).

## The gate

`TestStaticAnalysisSpecSetResolution` in `modules/rv-experiment/tests/test_config_jit.py`, beside
`test_jca_android_spec_set_resolves_paths`:

- `test_static_analysis_config_uses_selected_set` — the four cases of the task: `jca_android` →
  `resources/jca_android`; `jca` → `resources/jca`; `custom` → `custom_specs_dir`; and no
  `targets_file` is passed, so the mutex still belongs to whoever sets one.
- `test_static_analysis_matches_monitor_generation` — for `jca`, `jca_android` and `generic`, the
  `mop_dir` the static analysis receives and the `mop_specs_dir` monitor generation receives are the
  same string. This is the assertion that survives a set being added later.

**Falsified before it was trusted**: with the `mop_dir=` line commented out of
`get_static_analysis_config()`, both tests fail (`2 failed, 16 passed`). Restored, the file is
`18 passed`, and the module is **255 passed** — no other test depended on the old default.

Task 10.4 records, in `evidence/device_validation.md`, the directory the static analysis actually
used on the device run.
