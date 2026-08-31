# Base-spec references the merge engine cannot deliver

Task 4.9 records them; **task 8.17 executes them**, alongside the invariants hand-sync.

`openspec sync` / `openspec archive` rebuilds only the `## Requirements` section of a base
spec — verified 30/08 by executing the tool's `buildUpdatedSpec`, and gh104's task 10.8
recorded the same limitation. All four targets below sit outside that section, so no amount
of correct delta authoring reaches them: they are hand-edits or they do not happen.

Line numbers are as of 30/08/2026 and are a locator, not an identity — match on the quoted
text.

## The four

### 1. `openspec/specs/core/spec.md:43` — `## Purpose`, directory tree

```
|   |   +-- signature_normalizer.py Inner class notation
```

The file is deleted (task 4.4). Replace the line with the module that took its place in the
same directory, so the tree keeps describing what is there:

```
|   |   +-- build_type_suffix.py    Build-type suffix policy
```

`package_detector.py` on the line above is unaffected.

### 2. `openspec/specs/analysis/spec.md:96` — `## Purpose`, key concept 5

The bullet states the inverted diagnosis as fact:

> **SignatureNormalizer for inner class notation**: Static analysis tools (Soot) use `$` for
> inner classes (`OuterClass$InnerClass`), but the analysis JSON may use `.` notation
> (`OuterClass.InnerClass`). The `StaticAnalysisParser` uses `SignatureNormalizer` to convert
> `.` to `$` based on Java naming convention heuristics (uppercase after separator indicates
> inner class).

Every clause of it is wrong about this pipeline. The analysis JSON does **not** "use `.`
notation": it is written by `SootClass.getName()`, so a dot between two capitalized segments
is a package boundary. The heuristic named as the mechanism is what *introduced* the dollar,
on 465 classes across 7 of the 162 corpus artefacts. Replace with the rule that now holds:

> **Identifiers cross the parser untouched (INV-ANA-67)**: every producer in the chain emits
> the JVM binary name — GATOR through `SootClass.getName()`, both weavers through the same
> convention — so class names, window names and signatures are stored exactly as the artefact
> spells them. The parser formerly rewrote a dot to a `$` whenever both sides were
> capitalized; because it was applied to one side of an equality test whose other side is the
> raw logcat, every firing broke a match. Renumber the following bullet accordingly.

### 3. `openspec/specs/analysis/spec.md:329` — `## Invariants`, INV-ANA-02

Delete the invariant outright. It mandates the behaviour INV-ANA-67 forbids, and it is
additionally unenforceable as written: it claims the normalizer is applied "in all three JSON
sections (`windows`, `transitions`, `reachability`)" and to "method signatures", while the
implementation applied it to two sections and to no signature.

Deletion, not amendment: there is no residue of it that survives. The `## Invariants` bullet
list is not rebuilt by the merge engine, so this line stays until removed by hand.

### 4. `openspec/specs/analysis/spec.md:394` — `## Invariants`, INV-ANA-60

Clause-level amendment. The invariant reads:

> an `ACTIVITY` window MUST be admitted if and only if its **normalized** class name is
> present there

Strike the word *normalized*. Both sides of that membership test are compared in the
artefact's own spelling; nothing else in INV-ANA-60 changes — the unconditional admission of
non-`ACTIVITY` types and the "no package key participates" clause stand as written. Left
alone, INV-ANA-60 and INV-ANA-67 contradict each other in the merged specification.

## Verification after applying

```bash
grep -n "signature_normalizer" openspec/specs/core/spec.md      # → no output
grep -n "SignatureNormalizer" openspec/specs/analysis/spec.md   # → no output
grep -n "INV-ANA-02" openspec/specs/analysis/spec.md            # → no output
grep -n "normalized class name" openspec/specs/analysis/spec.md # → no output
grep -c "INV-ANA-67" openspec/specs/analysis/spec.md            # → non-zero
```
