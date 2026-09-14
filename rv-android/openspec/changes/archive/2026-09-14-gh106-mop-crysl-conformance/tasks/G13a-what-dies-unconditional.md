# G13a · what dies, unconditional part

**Depends on:** nothing. Runs from day one, in parallel with everything.
**Blocks:** nothing.
**Size:** 13 files moved, plus a grep gate. Mechanical, and independent of every line of Java.

Nothing in CI depends on these files: they are a photograph of an audit that closed. Moving them
early keeps the change's final diff about the component rather than about deletions.

## Reference
- `specs/conformance/spec.md` — "Retirement of Superseded Ad-Hoc Comparators"
- `design.md` D-14 (two stages, written criterion)
- **P3**: complete deletion, backup first (`backup/` is tracked in git, not ignored), all callers updated, no shims or `_unused` renames

## Tasks

- [x] 13a.1 Confirm the census at the current HEAD before moving anything, under the declared rules — *comparator* = a Python file that parses an `ORDER` or an `ere`/`fsm` and decides on it; *reader* = a Python file that opens a `.crysl`/`.cryptsl`. Expected: 6 comparators (1 530 lines) and 7 readers (2 377 lines) under `audit/20260808_*`, with `audit/…/batchD/alfa_language_check.py` counting in **both**. If the census differs from this, stop and report — the tree moved.
- [x] 13a.2 Move the six `ORDER` comparators under `audit/20260808_*` to `backup/20260824-gh106-audit-comparators/`: `alfa_automata_check` ×3, `alfa_language_check` ×2, `juiz_walk_batchB`.
- [x] 13a.3 Move the seven CrySL readers under `audit/` to `backup/20260824-gh106-audit-crysl-readers/`.
- [x] 13a.4 Write a `README.md` in each backup directory: what the files were, which audit they belong to, when and why they were retired, and the criterion that retired them (*the ad-hoc dies when the component reproduces its verdict, not when it compiles* — here it applies vacuously, since nothing consumes them).
- [x] 13a.5 Grep for references to the moved module paths across the repository and update or delete every one. P3 requires no dangling references, and a dangling import in a script nobody runs is still a dangling import.
- [x] 13a.6 `tests/parity/test_gh106_retirement.py` — asserts the 13 files are **absent from `audit/`** and that a repository-wide grep for their module paths returns nothing outside `backup/`. Run it with the CI contract: `uv run pytest --import-mode=importlib -o "addopts=" tests/parity/test_gh106_retirement.py`.

  **The "present under `backup/`" half must be conditional.** The CI workflow does `rm -rf rv-android/backup/ …` at `.github/workflows/ci.yml:20`, so asserting presence would fail in CI for a reason that has nothing to do with the retirement. Assert absence-from-`audit/` unconditionally, and presence-under-`backup/` only when the tree exists. `risk-register.md` RISK-012.
- [x] 13a.7 Confirm the five surviving gates stay green. **Run them locally and say so** — `tests/parity/` and the four `gh10*.py` scripts appear nowhere in `.github/workflows/`, so "no CI job changes status" is vacuous as a check: no CI job runs them in the first place. Record the local invocation and its output as the evidence. `risk-register.md` RISK-012.
- [x] 13a.7-bis Decide and record the disposition of comparators and readers **outside** `audit/20260808_*`, if the census finds any. The rule this group applies is scoped to that directory; a file that meets the definition elsewhere has no disposition, and P3 wants the sweep complete rather than convenient. `risk-register.md` RISK-013.
- [x] 13a.8 Run `/rv-qa-lint-fix tests/parity`.

## Closing
G13a closes when 13a.1–13a.8 are `[x]`.
