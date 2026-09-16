# End-to-end smoke (task 15.4)

```
uv run rv-experiment run --tools ape --specification-set jca_android \
    --apks-dir <scratch>/gh114_smoke/instrumented_apks --timeouts 300 \
    --skip-monitors --skip-instrument --skip-static --name gh114_smoke
```

The four APKs of `smoke_apks.md`, instrumented in task 15.2, one repetition each, budget 300 s
(the researcher's choice). The platform managed the emulator. 2026-09-15, 20:49 to 21:13; every
task `COMPLETED` (`performance.csv`: 368, 352, 350, 355 s).

## What the smoke confirms

**The export finishes and writes its six files.** `coverage.csv`, `errors.csv`, `app_events.csv`,
`summary.csv`, `results.json`, `performance.csv`, all present, one pass over the tasks. `errors.csv`
carries 36 rows over 13 columns; `summary.csv` one row per task over its 17.

**The reports carry the label codes.** Joining `code` with `jca_android/codes.csv`:

| code | rows | label |
|---|---|---|
| `MESSAGEDIGEST-ORDER-02` | 6 | `creation-refused` |
| `TRUSTMANAGERFACTORY-NOBS-02` | 3 | `platform-default` |
| `KEYMANAGERFACTORY-NOBS-02` | 3 | `platform-default` |
| `SSLCONTEXT-NOBS-03` | 3 | `platform-default` |
| `SSLCONTEXT-NOBS-06` | 3 | `platform-default` |
| `CIPHER-NOBS-00` | 3 | `not-observed` |
| `GCMPARAMETERSPEC-NOBS-00` | 2 | `not-observed` |
| `IVCHAINJUNCTION-NOBS-07` | 2 | `upstream-refused` |
| `KEYSTORE-ORDER-00` | 1 | `sequence` |
| `MESSAGEDIGEST-ALG-00/01/02/03` | 10 | `violation` |

Every code in the file exists in `codes.csv`. Six of the seven new labels are exercised by these
four applications in five minutes each: `creation-refused`, `platform-default`, `upstream-refused`
appear beside the unlabelled `not-observed`, `sequence` and `violation`.

**The evidence keys reach `errors.csv` and stay out of the identity.** Two rows carry
`vfp='sha256:ddf0b091019e3d2b'` after `msg` (`GCMPARAMETERSPEC-NOBS-00`, in
`me.diamondforge.tokn_19.apk` at `KeystoreManager.kt:68`), and no row of the file has `vfp` or
`vcls` inside `unique_msg` (INV-CORE-63). The two rows are the same misuse seen twice and share one
`unique_msg`, so `mop_errors_unique` counts them once: `me.diamondforge.tokn_19.apk` has
`mop_errors_total = 8` and `mop_errors_unique = 5`.

**The device log buffer is sized before every capture (INV-CORE-64).** The platform log carries
`Set logcat buffer size 16M on device emulator-5554` once per task, four times, and no WARNING
about the sizing.

## What this smoke did not reach, and is therefore not evidence about

- **`vcls`.** No application passed a trust-manager array with an element of an application class,
  so no row carries `vcls`. Not observed, not a failure; `EvidenceTest` and the harness traces are
  what cover it.
- **Coverage cells.** The run used `--skip-static`, because instrumentation does not read static
  analysis and this smoke is about reports, not coverage. Every `summary.csv` row therefore reads
  `measured = false` with empty coverage cells, which is the declared behaviour of INV-PLT-35, and
  `coverage.csv` holds only its header.
- **`app_events.csv`** holds only its header: the run did not pass `--logcat-diagnostics`, which is
  off by default.
