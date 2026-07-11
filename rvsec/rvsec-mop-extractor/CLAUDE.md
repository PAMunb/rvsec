# CLAUDE.md - rvsec-mop-extractor

## Purpose
CLI that parses `.mop` specification files and lists the JCA classes/methods they monitor — i.e. computes the API surface of a spec set, for use by static analysis.

## Role in pipeline
Bridges `rvsec-mop` (specs) and static analysis: extracts the concrete `Class.method(args)` signatures a spec set touches, so downstream tools know which reachability targets/signatures to check for.

## Relationships
- ⟵ consumes `.mop` files from `rvsec-mop` (any of `jca/`, `generic/`, `generic_new/`).
- ⟶ packaged as `mop-extractor.jar`, **copied on `mvn install`** (via `maven-resources-plugin`, `copy-resources` execution) to `rv-android/lib/mop-extractor/mop-extractor.jar`.
- ⟶ consumed by `rv-android/scripts/check_signature_file_subset.py` and `rv-android/scripts/check_no_legacy_mop.py`.
- ⟶ consumed by `rvsec-gator` (GATOR client) via `JavamopFacade.listUsedMethods` / `MopMethod` for MOP-reachability analysis.

## Key components (verified paths)
- `src/main/java/br/unb/cic/mop/extractor/Main.java` — entry point, dispatches CLASSES vs METHODS/METHODS_PARAMS.
- `src/main/java/br/unb/cic/mop/extractor/JavamopFacade.java` — loads `.mop` files (`listUsedClasses`, `listUsedMethods`).
- `src/main/java/br/unb/cic/mop/extractor/cli/CommandLineArgs.java` — jcommander args: `--specs-dir/-d` (required), `--output/-o` (required), `--type` (`CLASSES|METHODS|METHODS_PARAMS`, default `METHODS`), `--writer` (`CSV`, default), `-debug`.
- `src/main/java/br/unb/cic/mop/extractor/visitor/{UsedJcaClassesVisitor,UsedJcaMethodsVisitor}.java` — AST visitors over parsed `.mop`.
- `src/main/java/br/unb/cic/mop/extractor/model/MopMethod.java` — class/method/param-types model.
- `src/main/java/br/unb/cic/mop/extractor/writer/{Writer.java,CsvWriter.java}` — output writer interface + CSV impl.

## Build
`maven-assembly-plugin` (`jar-with-dependencies`) produces `mop-extractor.jar`, `mainClass=br.unb.cic.mop.extractor.Main`. Deps: `br.unb.cic.javamop:javamop`, `com.beust:jcommander`.

## Gotchas
- `WRITER` enum only has `CSV` implemented — `Writer` interface exists but no other writer is wired.
- `--type METHODS_PARAMS` maps to `writeMethods(..., withParameters=true)` in `CsvWriter`; check its output format before relying on it (README calls this format a TODO area).
