# `gh105-preimage` — the specification set as it stood before the wiring

`jca_android/` here is a byte copy of
`rvsec/rvsec-mop/src/main/resources/jca_android/` taken before the first `.mop`
edit of gh105 (task 2.11), commit `3f3bdd1c`. Twenty-three specifications and
`codes.csv`.

It is not a backup in the "in case something breaks" sense. It is the `--a` side
task 8.4 hands to `scripts/gh104_diff_harness.py`, which takes two specification-set
*directories*, regenerates the monitors from each, and reports the behavioural
delta per trace. A diff against the git history would not do: the harness needs a
directory it can point a generator at, and the comparison has to survive the
change's own commits being rewritten or rebased.

The measurements taken over it are in `data/jca_android/gate_baseline.json` and
`data/jca_android/evidence/gate_baseline_report.md` — the state every gh105 gate
is registered against.
