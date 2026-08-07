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
- **The rows are signature-distinct, but every consumer matches on `(class, method)` only.
  Do not count or diff them by signature.** `UsedJcaMethodsVisitor` builds one `MopMethod`
  per pointcut and `MopMethod.equals/hashCode` include `parameters` and `signature`, so
  overloads produce separate rows. The GATOR client wraps each one `MatchPolicy.LENIENT`
  (`MopSpecsTargetSource.java:38`) and `TargetResolver.resolveInScene` then compares
  **only `(className, methodName)`** — parameters and signature are never read. Runtime
  agrees: `rv-monitor` locates a violation from a `StackTraceElement`, which carries no
  descriptor. Measured over the 23 specs: `jca` yields **120 rows → 68 distinct
  `(class, method)`**; `jca_android` yields **119 → 67**. Fifty-two of the 120 are
  overloads that add nothing to the analysis. When comparing spec sets, or gating on
  "did the target set change", collapse to `(class, method)` first.
- **`visit(ImportDeclaration)` skips asterisk imports** (`UsedJcaMethodsVisitor.java:38-40`),
  and a pointcut whose owner is not in the resulting simple-name→FQN map is dropped
  entirely. Editing a `import static ...Util.*;` line therefore cannot change the output —
  a fact worth checking before attributing a target-set change to such an edit.
- `WRITER` enum only has `CSV` implemented — `Writer` interface exists but no other writer is wired.
- `--type METHODS_PARAMS` maps to `writeMethods(..., withParameters=true)` in `CsvWriter`; check its output format before relying on it (README calls this format a TODO area).
