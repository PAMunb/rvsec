# 10.2 / 10.3 — lint and verification

What this records: the `/rv-qa-lint-fix` and `/rv-verify` passes of 2026-08-24, run over the five
modules of task 10.2 and the six of task 10.3, at `d631f228` plus this change's working tree.

## 10.2 — `/rv-qa-lint-fix`

| module | autoflake | isort | black | files changed |
|---|---|---|---|---|
| `rv-coverage` | — | — | 9 unchanged | **none** |
| `rv-platform` | — | — | 20 unchanged | **none** |
| `aperv-tool` | — | — | 44 unchanged | **none** |
| `rv-android-core` | — | — | 49 unchanged | **none** |
| `rv-experiment` | — | — | `src/rv_experiment/config.py` reformatted | 1 |

The single reformat is black closing one line of task 10.0's own new code. Four of the five modules
were already clean for all three auto-fixers, so the group introduced no formatting drift.

## 10.3 — `/rv-verify`

The `/rv-qa-lint-fix` skill runs `/rv-verify` as its verification step, so five of the six modules
carry a full verification table from the same tree state as their lint pass;
`rv-instrumentation-dexlib2` was given its own explicit pass.

| module | tests | format | lint | complexity / MI |
|---|---|---|---|---|
| `rv-coverage` | **296 passed**, coverage 98% | PASS | 14 × E501 | avg 4.49 (A); peak CC 21 in `_parse_error_message` |
| `rv-platform` | **336 passed**, 1 skipped | PASS | 32 × E501 | avg 3.0 (A); all 20 files MI A |
| `aperv-tool` | **715 passed**, 22 skipped | PASS | 42 × E501 | avg 4.29 (A); two CC-31 functions |
| `rv-android-core` | **1079 passed** | PASS | 134 (120 E501, 9 E402) | avg 2.77 (A); all MI A |
| `rv-experiment` | **255 passed** | PASS | 94 × E501 | — |
| `rv-instrumentation-dexlib2` | **26 passed**, coverage 91% | PASS | 3 × E501 | avg 3.6 (A), max B |

**Zero test failures across 2,707 tests.** Every lint failure is `E501` (or, in `rv-android-core`,
nine deliberate late imports flagged `E402`), all of it pre-existing: black at line-length 88 does not
reflow comments or string literals, and flake8 at 88 counts them. This is the standing black-vs-flake8
mismatch in this repository, not drift this change introduced — `rv-verify` cross-checked the hunks
task 10.0 added and found no new debt.

`mypy` is not configured for any of these modules; run opportunistically it reports `import-untyped`
against sibling workspace modules that publish no `py.typed`. `safety` reports 60–61 advisories, all
of them transitive dependencies of the shared workspace `.venv` (the LLM stack, pillow, nltk), none in
any of these modules' declared dependencies.

## Two findings recorded and not repaired

Both are outside this change's scope; they are written here so they are not lost.

1. **`rv-instrumentation-dexlib2` ships a dangling console script.**
   `modules/rv-instrumentation-dexlib2/pyproject.toml:15` declares
   `rv-instrumentation-dexlib2 = "rv_instrumentation_dexlib2.__main__:main"`, but the package has no
   `__main__.py` — the installed command raises `ModuleNotFoundError` on invocation. The module is
   consumed as a library through `get_instrumenter()`, so under P3 the `[project.scripts]` block is
   what should go. Deleting it changes the installed console-script set and needs a `uv sync`, which
   is why it is reported rather than done here.
2. **`rv-android-core` `coverage.py:720` takes a `restrict_to_static` parameter it never reads**,
   with a docstring that still promises it filters. No caller passes it.
