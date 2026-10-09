## Purpose

Before a task loads its static data, `StaticAnalysisComponent.copy_static_analysis_files` (`modules/rv-platform/src/rv_platform/components/static_analysis.py`) copies the analysis document co-located with the APK in `apks_dir` into the task's per-APK results directory (`<results>/<apk_name>/`). The copy is what lets resume and result processing find the document without the original `apks_dir` (INV-PLT-15, "Orchestrated Resume Skips Static Analysis but Reuses Persisted JSON").

Every task of an APK shares that directory, and every task copied the document again with `shutil.copy`. With gh120 documents of up to 9.34 GB, one copy took 100 s in the `e03mini-smoke` run of 2026-10-09; an APK runs 12 tasks in the e03mini comparison, so the same bytes were copied twelve times per container. This delta makes the copy preserve the source's modification time and skips it when the destination already holds a file of the same size and modification time — the case of every task after the first. The document stays in the results directory exactly as before, so no reader of it changes.

The parse that follows the copy is governed by the `analysis` capability (streaming read and parsed-document cache, INV-ANA-80..84). `read_static_analysis_files` keeps its signature, so INV-PLT-05, INV-PLT-15 and INV-PLT-38 hold as written.

## Data Contracts

### Input
- `<apks_dir>/<apk_name>.json`, `<apks_dir>/<apk_name>.methods` — optional files co-located with the APK (source: the static-analysis pre-processing, or a corpus that ships them)

### Output
- `<results>/<apk_name>/<apk_name>.json`, `.methods` — copies with the source's modification time (destination: `read_static_analysis_files`, `aperv-tool` derive, resume, result processing)

### Side-Effects
- **[Host filesystem]**: a copy is written only when the destination is absent or differs from the source in size or modification time

### Error
- No new error. A failed copy keeps today's behaviour: logged, and the task continues without static data (INV-PLT-05).

## Invariants

- **INV-PLT-39**: `copy_static_analysis_files` SHALL copy with `shutil.copy2` and SHALL skip a file whose destination exists with the same size in bytes and the same `st_mtime_ns` as the source. A skipped file SHALL count as copied for the method's return value.

## ADDED Requirements

### Requirement: The Static-Analysis Copy Is Skipped When the Destination Is Identical (NFR04)

`StaticAnalysisComponent.copy_static_analysis_files` SHALL, for each co-located extension (`.methods`, `.json`):

1. leave the file alone when the source does not exist (unchanged);
2. skip the copy when the destination exists and has the same size and the same `st_mtime_ns` as the source, logging the skip at debug level;
3. otherwise copy it with `shutil.copy2`, which carries the modification time over (INV-PLT-39).

Size and modification time are the comparison because the copy is local and its source is a read-only corpus: a file that changes in place keeps neither, and hashing a 9 GB document only to decide whether to copy it would cost as much as copying it. Whether the *content* is current is decided later, by the digest that keys the parsed copy and the MOP artifact (INV-ANA-82, INV-APV-47).

#### Scenario: the second task of an APK does not copy its document again
- **WHEN** the first task of `eu.darken.sdmse_10705000.apk` has copied its 9.34 GB document to `results/e03mini_02/eu.darken.sdmse_10705000.apk/`
- **AND** the second task of the same APK runs `copy_static_analysis_files`
- **THEN** the document SHALL NOT be copied again
- **AND** the method SHALL return `True`

#### Scenario: a replaced source is copied again
- **WHEN** the destination exists but the source in `apks_dir` has a different size or modification time
- **THEN** the source SHALL be copied over it with `shutil.copy2`
- **AND** the destination's `st_mtime_ns` SHALL equal the source's afterwards

#### Scenario: a first copy preserves the modification time
- **WHEN** no destination exists
- **THEN** the copy SHALL be made with `shutil.copy2`
- **AND** the destination's size and `st_mtime_ns` SHALL equal the source's
