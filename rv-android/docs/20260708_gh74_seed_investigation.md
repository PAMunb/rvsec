# gh74 — Seed propagation investigation (issue PAMunb/rvsec#74, point 3)

**Date:** 2026-07-08
**Change:** `gh74-aperv-arm-variants` (task group 5)
**Question (issue #74):** does the APE-RV seed reach the jar, and where is the defect if runs
are non-deterministic despite a configured seed?

## Finding — the defect was rv-android-side, not the jar

The `mop-fairtest` APE-RV jar **honors** a passed seed. Verified by reading
`ape-mop-fairtest/src/main/java/com/android/commands/monkey/Monkey.java` at branch
`mop-fairtest`, HEAD `2f95711`:

| Evidence | Line | Behavior |
|----------|------|----------|
| `if (opt.equals("-s")) { mSeed = nextOptionLong("Seed"); }` | `Monkey.java:886-887` | `-s <n>` is parsed into `mSeed` |
| `if (mSeed == 0) { mSeed = System.currentTimeMillis() + ...; }` | `Monkey.java:670-671` | with no `-s`, the jar self-seeds non-deterministically |
| `mRandom = new Random(mSeed);` | `Monkey.java:697` | Monkey's RNG is seeded |
| `RandomHelper.seed(mSeed);` | `Monkey.java:731` | APE's `RandomHelper` (SATA epsilon-greedy) is seeded |

So a fixed `-s <seed>` makes a run reproducible end-to-end (both `Monkey.mRandom` and APE's
`RandomHelper`). The conditional at :670 means the jar only falls back to a time-based seed
when **no** `-s` is supplied — which is exactly what happened, because rv-android never
emitted `-s`.

**Line-number note:** the change design (`design.md` D6) and spec (INV-APV-18) cite
`Monkey.java:881-882` for the parse site; the verified location on `2f95711` is
`:886-887`. The substance (parse → seed both RNGs) is unchanged; the citation had drifted by
~5 lines. This memo records the verified numbers.

## Root cause and fix

The defect was entirely in `aperv-tool._build_main_command`, which built the `app_process`
argv (`--ape <strategy>`) but never appended `-s <seed>` even when a seed was present in
`_tool_config`. The jar therefore always took the :670 self-seed branch → non-deterministic
runs regardless of the experiment's configured seed.

Closed by **task 3.1** (INV-APV-18): `_build_main_command` now appends `["-s", str(seed)]`
after `--ape <strategy>` when `self._tool_config.get("seed")` is not None. The Monkey `-s`
is distinct from the adb `-s <serial>` at `argv[0]` (different layers). `seed` has no
`APERV_PROPERTY_MAPPING` entry, so it is never written to `ape.properties`
(CLI-only). Tests: `TestSeedPropagation.test_seed_passed_as_dash_s`,
`test_no_seed_omits_dash_s`, `TestArmProperties.test_seed_not_written_to_properties`.

## Issue #74 point 3 — resolution

- Seed-verification criterion: **met**. The jar is correct; no APE-RV-repo issue is needed
  (task 5.2 → **N/A**, no jar divergence found).
- The remaining live cross-check (task 6.4 / R1) re-greps the *built experiment jar's*
  `Config.java`/`Monkey.java` before the paired experiment; this memo already confirms the
  seed path on `2f95711`, the same HEAD the cmpft4 jar is built from.
