# Migration record — arms as `preset + overrides` (gh95)

This directory is the archived evidence of one migration, not a live check. It exists because the
claim "no arm's effective configuration changed when the Python side stopped enumerating jar keys"
is only worth as much as the measurement behind it, and that measurement is one-time by rule
(INV-APV-44): a diff of regenerated configurations against a pre-change baseline answers a question
that can only be asked once, and keeping it running would turn it into a constant-versus-constant
guard that passes forever without checking anything.

## What is here

| File | What it is |
|---|---|
| `arm_effective_baseline.json` | The typed effective configuration of all **29** pre-change arms, captured from the unmodified `tool.py` before the migration began. Carries its own provenance block: the `ape` checkout, its commit, and the SHA-256 of the two jar tables it read |

The script that produced it, `tests/migration/capture_arm_baseline.py`, stays where it is and writes
here — it imports `jar_tables.py` as a package sibling and would not run from this directory. An
archived measurement whose producer was deleted can only be trusted; one whose producer still runs
can be re-derived.

The test that consumed the baseline, `tests/migration/test_arm_regeneration_diff.py`, was deleted at
sign-off. What stayed in `tests/migration/` is the standing part: `jar_tables.py` and
`test_jar_tables.py` (INV-APV-41), `test_mapping_sweep.py`, `test_decisive_contrasts.py`, and
`retirements.py` as the record of which 21 names went and why.

## The result being archived

Executed 2026-08-07 against the `ape` checkout at commit `822fc6cf`:

```
APE_REPO=<ape checkout> pytest tests/migration --import-mode=importlib -o "addopts=" -q
48 passed in 0.49s
```

The regeneration diff was **empty for all 8 surviving arms**. The baseline itself was captured
earlier, at `ape` commit `8416c305`: the jar's source advanced between the two dates and the diff
stayed empty, which is the stronger reading — the arms survived a moving substrate, not a frozen one.

One key is excluded from the diff by name rather than by silence: `ape.stepTelemetryEnabled`. The
baseline records it because the pre-change arms carried it; `ape-rearch ea2d5a65` then deleted
`Feature.STEP_TELEMETRY` outright, so the key now aborts plan validation as unknown, and the Python
side retired it to match. Its absence is the jar's vocabulary moving, not migration drift, and the
exclusion says so at the point where it is applied.

## The residual risk, stated rather than filed away

The whole migration tier **skips silently** when no `ape` checkout resolves — 32 skips, by design,
because CI has no such checkout and failing there would break an unrelated build. A green module test
run is therefore *not* evidence that this gate ran. That is why the executed result and the commit it
ran against are written above, in the record, and not left to the baseline's provenance block alone.
