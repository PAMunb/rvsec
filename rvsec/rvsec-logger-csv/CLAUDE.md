# CLAUDE.md - rvsec-logger-csv

## Purpose
JSE/desktop logger: writes violations to `output/summary.csv`. Provides the `ErrorCollector` used by the **JSE path** (`-javaagent`, `rvsec-agent`), as opposed to the Android logcat path.

## Component (verified)
`src/main/java/br/unb/cic/mop/eh/ErrorCollector.java` — singleton (`instance()`); dedups via `Set<ErrorDescription>.add()`; on first-write creates `output/` and `output/summary.csv` with header `spec,class,className,method,location,error,expecting`; appends rows via `PrintWriter(new FileWriter(file, true))`.

## Relationships
- Mutually-exclusive pair with `rvsec-android/rvsec-logger-logcat/ErrorCollector` — same FQCN (`br.unb.cic.mop.eh.ErrorCollector`), swapped by classpath, never both present.
- Depends on `rvsec-core` (`ErrorType`, `ErrorDescription`, `ErrorSummary`).
- Used by `rvsec-agent` (JSE `-javaagent` runtime classpath).

## Build
`mvn clean install` — plain library jar.

## Gotchas
- `output/summary.csv` path is **relative to the process cwd**, not the module root.
- The file **appends across runs** — it is not truncated; delete it (or the `output/` dir) between clean test runs if you need a fresh CSV.
- Dedup subtlety: `ErrorDescription.equals()` only compares the derived `ErrorSummary` (spec/type/class/method/location), but its `hashCode()` also factors in `expecting` — an equals/hashCode contract violation in `rvsec-core`. Practical effect: two errors with the same summary but different `expecting` strings usually land in different `HashSet` buckets and are **not** deduped (both get written), even though `equals()` would say they're the same error.
