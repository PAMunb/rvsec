# Group 2 — S: seed the successor set `jca_v2`

Tracked checkboxes: `tasks.md` §2. Wave 1; no dependency; Group 7 (E1) and Group 8 (E4) wait for this group’s commit.

## Subagent brief

Create the successor set as a byte-identical copy of the frozen `jca` and make it selectable by name. Read `design.md` D-1 and D-12, the `instrumentation` delta (`Requirement: Successor Specification Set jca_v2`, INV-INS-09/118) and the `experiment` delta. Do not edit anything under `jca/` or `jca_android/`. Do not repair anything in the copy — Groups 6/7/8 do that; the seed must have zero hunks against `jca` except `codes.csv`.

## Files

Java side (git root `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec`):
- `rvsec/rvsec-mop/src/main/resources/jca_v2/` — 23 `.mop` files copied from `rvsec/rvsec-mop/src/main/resources/jca/` (1,912 lines) + `codes.csv` (header `spec,code,error_type,site_kind,event,file_line`, no rows).

Python side (`rv-android/`):
- `modules/rv-experiment/src/rv_experiment/config.py` — `valid_spec_sets` and the directory mapping (gh101 D-S8 lists the six enumeration sites: these two, the `click.Choice`, INV-EXP-03(f), INV-INS-09, the JIT paragraph — the last three are spec text already carried by the deltas).
- `modules/rv-experiment/src/rv_experiment/__main__.py` — `click.Choice` on `--specification-set`.
- `modules/rv-experiment/tests/...` — the JIT-config test file that already covers `jca_android` selection (grep `jca_android` under `modules/rv-experiment/tests/`); add `test_jca_v2_selectable_by_name`; the invalid-value test must list five sets.
- `data/jca_v2/divergence_record.csv` (header as `data/gh101/divergence_record.csv`: copy its header line), `data/jca_v2/conformance_record.csv` (header as `data/gh101/conformance_record.csv`), `data/jca_v2/gate_allowlist.csv` (`set,gate,spec,event_or_state,reason,task`), `data/jca_v2/predicate_omissions.csv` (header as `data/gh101/predicate_omissions.csv`), `data/jca_v2/README.md` (what the set is, base commit of the seed, pointer to the records).
- `scripts/gh104_divergence_record.py` — parametrised copy of `scripts/gh101_divergence_record.py` (169 lines): base directory `jca/`, target `jca_v2/`, record `data/jca_v2/divergence_record.csv`, `--check` exits non-zero on any hunk without an entry.
- `tests/parity/test_gh104_specset_gates.py` — created here with two tests (`test_jca_v2_seed_is_byte_identical_plus_codes` — passes only until Group 7 lands, then is replaced by the hunks-recorded test as the sole invariant; `test_jca_v2_hunks_all_recorded`); Group 6 adds the structural gates to the same file.

## Commands

```bash
cd ../rvsec/rvsec-mop/src/main/resources && cp -r jca jca_v2 && diff -r jca jca_v2 && echo IDENTICAL   # before codes.csv
cd -; uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh101_specset_gates.py -q   # 5 passed, unchanged
uv run rv-experiment run --help | grep -A1 specification-set   # shows jca_v2 among the choices
python3 scripts/gh104_divergence_record.py --check   # 0 unrecorded hunks on the seed
```

## Acceptance

- `diff -r jca jca_v2` differs only by `jca_v2/codes.csv`.
- `--specification-set jca_v2` is accepted by the CLI and resolves to `.../resources/jca_v2/` with no `custom_specs_dir`; an unknown value is rejected with a message listing `jca, jca_android, jca_v2, generic, custom`.
- gh101's five gates still pass (nothing under `jca/` moved).
- `data/jca_v2/` exists with the four records (headers only) and the README.
- One commit: `feat(specs): semeia o conjunto jca_v2 a partir do jca congelado e o registra por nome (refs #104)`.
