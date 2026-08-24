# 10.7 — documentation sync

What this records: the `/rv-docs-sync` passes of 2026-08-24 and the two hand edits the task names.

## `/rv-docs-sync` per module

| module | why it needed the pass | what changed |
|---|---|---|
| `rv-coverage` | `2e3904ba` rewrote the parser: `ParserDiagnostics`, the v1 envelope, `UNSPECIFIED` sentinels, `unique_msg` 5 → 7 parts | CLAUDE.md, architecture.md, ADR-001 status note, README.md |
| `rv-instrumentation-dexlib2` | five commits since `51527537`, including `advicesExcludedByArity` reaching Python (INV-INS-122) | CLAUDE.md, architecture.md, README.md, one docstring path |
| `aperv-tool` | `05a4bb8d` added `violations.py` and consolidated the payload parser | CLAUDE.md, architecture.md, README.md, one docstring |
| `rv-platform` | `errors.csv` 11 → 13 columns; `architecture.md` described the file with no column contract at all | CLAUDE.md, architecture.md (new **Output Column Contracts**), README.md, one docstring |

`rv-platform` was not on the task's list. It was added because the `rv-coverage` pass surfaced that the
13-column `errors.csv` had no column contract written anywhere in the module that writes it — which is
what task 10.8 then has to lift into the platform spec's Data Contracts.

## Four stale claims the passes corrected in code

All four were docstrings or docs asserting something the code had stopped doing:

- `aperv_tool/analysis/violations.py:163` — `unique_msg_unparsed` said **five** `:::`-joined fields;
  `_UNIQUE_FIELDS` has been 7 since `05a4bb8d`.
- `rv_platform/components/result_processor.py:578` — "The header carries 11 columns"; the writer emits
  the 13 of `ERRORS_CSV_COLUMNS`.
- `rv-coverage` README named the metric key `methods_jca_reachable_coverage`, renamed back in
  `0572f811` and never propagated — the last occurrence in the repo outside `constants.py`.
- `rv-instrumentation-dexlib2` `architecture.md` documented a **fabricated ABC**: three
  `@abstractmethod`s where the real `Instrumenter` declares only `instrument_apks`.

## The two hand edits

- **`CLAUDE.md`**, specification-set paragraph. It described `jca_android` as "the same 23
  specifications derived against generated CrySL rules for a declared Android API level" — that
  describes the set that was reproved and is now archived at `jca_android_bug_predicate/`. It now says
  what the set is: seeded byte-for-byte from the frozen `jca`, value clauses anchored in the
  expert-validated CrySL rules (D-15), alphabets/`ORDER`/predicates anchored in
  `MetaCrySL/generated/api30/`, and the archived predecessor named as unselectable.
- **`openspec/specs/experiment/spec.md:87`**, the sample comment `# "jca", "generic", or "custom"`,
  which omitted `jca_android`. It sits under `### Data Models`, not inside a Requirement block, so the
  archive sync would never have reached it.

`openspec/specs/platform/spec.md:192` still carries the 11-column `INV-PLT-19`. That is left alone on
purpose: it is task 10.8's, which applies the deltas' `## Invariants` and Data Contracts by hand.
