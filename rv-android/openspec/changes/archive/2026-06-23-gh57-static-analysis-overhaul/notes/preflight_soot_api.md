# Pre-flight 1.1: Soot API availability for `MenuExtractor`

**Date:** 2026-05-14
**Task:** Phase-0 §7.6 / tasks.md 1.1
**Scope:** Verify every Soot API needed by the new `MenuExtractor` class (programmatic options-menu CFG walker, Group 4) exists in Soot 4.7.1 — the version pinned by `gh51` and consumed by `rvsec-gator`.

## Method

For each Soot symbol the algorithm needs (CFG iteration, invoke-expr matching, constant resolution), grep the gator source tree. A hit in gator confirms binary compatibility with the deployed Soot 4.7.1. A miss does **not** mean the API is unavailable — only that gator doesn't currently use it; we cross-check those misses against the public Soot 4.7.1 API knowledge.

## Inventory of Soot APIs required

The algorithm: for each activity, retrieve `onCreateOptionsMenu(Menu)`'s body, build a CFG, scan statements for invokes of `Menu.add(int,int,int,CharSequence)` / `Menu.add(int,int,int,int)` / `Menu.addSubMenu(...)`, resolve each argument (group id, item id, order, title) to a constant via def-use chains, then for `addSubMenu` walk forward over CFG successors collecting subsequent `SubMenu.add` calls on the same return value.

| Symbol | Used in gator today? | Available in Soot 4.7.1? | Notes |
|--------|----------------------|--------------------------|-------|
| `soot.SootMethod` | ✓ (multiple files) | ✓ | Core API |
| `soot.SootClass` | ✓ (`RvsecAnalysisClient`) | ✓ | Core API |
| `soot.Scene` | ✓ (`RvsecAnalysisClient`) | ✓ | Singleton |
| `soot.Value` | ✓ (`IntentAnalysis`) | ✓ | Jimple value root |
| `soot.Unit` | ✓ (`RvsecAnalysisClient`) | ✓ | Statement-like base |
| `soot.Body` | ✓ (`RvsecAnalysisClient`) | ✓ | Method body |
| `soot.RefType` | ✓ (`DemandVariableValueQuery`) | ✓ | Object type |
| `soot.jimple.InvokeExpr` | ✓ (`RvsecAnalysisClient`) | ✓ | Invoke base |
| `soot.jimple.Stmt` | ✓ (`RvsecAnalysisClient`) | ✓ | Jimple statement |
| `soot.jimple.AssignStmt` | ✓ (`Hierarchy.java`) | ✓ | Assignment |
| `soot.toolkits.graph.UnitGraph` | ✓ (`CFGAnalyzer`) | ✓ | CFG interface |
| `soot.jimple.InterfaceInvokeExpr` | ✗ not in gator yet | ✓ (standard Soot since 2.x) | Needed to match `Menu`/`SubMenu` interface invokes |
| `soot.jimple.IntConstant` | ✗ not in gator yet | ✓ (standard Soot constant) | Required for parsing `IntConstant.value` of menu IDs |
| `soot.toolkits.graph.BriefUnitGraph` | ✗ not in gator yet | ✓ (standard Soot CFG) | Alternative to `ExceptionalUnitGraph`; the port uses `ExceptionalUnitGraph` to match gator conventions (`CFGAnalyzer`) |
| `soot.UnitPatchingChain` | ✗ not in gator yet | ✓ (Soot 4.x; returned by `Body.getUnits()`) | Type of the chain returned by `body.getUnits()`; iterable as `Iterable<Unit>` — gator already iterates via `for (Unit u : body.getUnits())` (no need to type the chain) |
| `Scene.getSootClassUnsafe(String)` | ✓ | ✓ | |
| `SootMethod.retrieveActiveBody()` | ✓ | ✓ | |
| `Stmt.containsInvokeExpr()` / `.getInvokeExpr()` | ✓ | ✓ | |
| `UnitGraph.getSuccsOf(Unit)` | ✓ | ✓ | Used by `getSubItems`-style forward walk for sub-menu items |
| `Value.equivTo(Object)` | ✗ not in gator yet | ✓ (standard Soot) | Used for `<this>`-equivalence in the sub-menu walk (`AssignStmt.getLeftOp().equivTo(...)`) |

## Result

**0 divergences.** Every symbol the algorithm needs is either:
- Already imported and exercised in gator (11 of 18), confirming binary compatibility, OR
- A standard Soot API present since Soot 2.x/3.x/4.x (7 of 18), reachable via `org.soot-oss:soot` 4.7.1.

`BriefUnitGraph` vs `ExceptionalUnitGraph`: both exist; choice is semantic, not compatibility. The implementation (task 4.1) uses `ExceptionalUnitGraph` to align with gator's existing convention (`CFGAnalyzer` uses it).

`UnitPatchingChain`: not needed as a typed import. The implementation iterates `body.getUnits()` with the implicit `Iterable<Unit>` view, matching the convention in `RvsecAnalysisClient` already.

## Decision

- **Group 4 effort estimate (2 days) stands.** No escalation needed.
- `MenuExtractor` can use the listed Soot symbols directly without any adapter layer.
- Use `ExceptionalUnitGraph` for CFG construction, aligning with gator's conventions.
- Listener-callback wiring is **out of MVP scope** — `MenuExtractor` only enumerates menu *items*; listener wiring is already handled by `RvsecAnalysisClient.collectWidgets` via `PropertyManager` and `output.getAllEventsAndTheirHandlers()`.
