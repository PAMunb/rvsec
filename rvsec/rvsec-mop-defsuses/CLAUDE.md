# CLAUDE.md - rvsec-mop-defsuses

## Purpose
Dev utility: computes def/use of `Property` values per `.mop` spec and prints a PlantUML class diagram to stdout.

## Role
**ORPHAN / dev-only — referenced by no one else in the monorepo.** Not consumed by `rvsec-mop-extractor`, `rvsec-agent`, `rv-android`, or any script; only appears in the parent `rvsec/pom.xml` module list. `DefsUsesGraph.main()` has a **hardcoded absolute path** and only `System.out.println`s the PlantUML text — no file output, no packaging/assembly plugin.

⚠ The hardcoded path (`.../rvsec-mop/src/main/resources`) points at the **resources root**, not a leaf spec dir — `File.listFiles()` only lists immediate children, and the specs live one level deeper in `jca/`, `generic/`, `generic_new/`. As written, `main()` finds zero `.mop` files and silently prints an empty diagram; edit the path to a leaf dir before running.

## Components (verified)
- `src/main/java/br/unb/cic/mop/defsuses/DefsUsesGraph.java` — `main()`, `execute()`, `getDefsUses()`, PlantUML rendering.
- `UseDefVisitor.java` — AST visitor collecting defs/uses per spec.
- `PropertyExtractor.java` — extracts `Property` references.
- `MOPSpecDefsUses.java` — per-spec defs/uses model.

## Dependencies
`br.unb.cic.javamop:javamop`, `com.github.javaparser:javaparser-core`, `javaparser-symbol-solver-core` (symbol-solver present in `pom.xml` but unused in code).

## Gotchas
- Explicitly orphan status: no CI, no invocation from scripts, no downstream consumer.
- Fix the hardcoded path in `DefsUsesGraph.main()` (and point it at a leaf spec dir, e.g. `.../rvsec-mop/src/main/resources/jca`) before running.
- README's "supports the static analysis pipeline" / "dependency on rvsec-mop-extractor" claim is not reflected in the `pom.xml` (no such dependency declared) or in any consumer code — treat as aspirational, not current state.
