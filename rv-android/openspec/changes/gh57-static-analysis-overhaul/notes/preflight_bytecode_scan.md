# Pre-flight 1.3: Bytecode-scan refactor — `scanInvokesByPattern` API

**Date:** 2026-05-14
**Task:** Phase-0 §7.8 / tasks.md 1.3
**Scope:** Confirm `findDirectMopCallersByBytecodeScan` (RvsecAnalysisClient.java:465–523) can be refactored into a generic helper `scanInvokesByPattern(appClasses, predicate)` without breaking the existing MOP-scan contract (BUG-INV-ANA-19).

## Existing method shape

```java
private Set<SootMethod> findDirectMopCallersByBytecodeScan(
        Map<SootClass, List<SootMethod>> appClasses,
        Set<MopMethod> mopSignatures) {
    Set<SootMethod> result = new HashSet<>();
    if (mopSignatures.isEmpty()) return result;
    Set<String> mopKeys = buildMopKeys(mopSignatures);  // helper, FQN#name

    int methodsScanned = 0, bodiesSkipped = 0;
    for (entry in appClasses) for (method in entry.value) {
        methodsScanned++;
        if (!method.isConcrete()) continue;

        Body body;
        try { body = method.retrieveActiveBody(); }
        catch (RuntimeException | OutOfMemoryError ex) {
            bodiesSkipped++; log WARN; continue;
        }
        if (body == null) continue;

        for (Unit unit : body.getUnits()) {
            if (!(unit instanceof Stmt)) continue;
            Stmt stmt = (Stmt) unit;
            if (!stmt.containsInvokeExpr()) continue;
            InvokeExpr ie = stmt.getInvokeExpr();
            SootMethodRef ref = ie.getMethodRef();
            if (ref == null) continue;
            if (matchesMopSignature(ref.getDeclaringClass().getName(), ref.getName(), mopKeys)) {
                result.add(method);
                break;  // ← short-circuit: one match per caller
            }
        }
    }
    log stats;
    return result;
}
```

## Generic refactor

Extract the walker into a **callback-driven** loop. Two views over the same walker:

### Core helper

```java
/**
 * Walk every InvokeExpr in every concrete method of {@code appClasses};
 * for each, invoke {@code visitor.accept(caller, stmt, invokeRef)}.
 *
 * Body retrieval is wrapped in try-catch (RuntimeException, OutOfMemoryError)
 * — same resilience as Flowgraph.java FIX 2 / INV-ANA-17.
 *
 * @return scan statistics (methods scanned, bodies skipped)
 */
private ScanStats scanInvokesInAppClasses(
        Map<SootClass, List<SootMethod>> appClasses,
        InvokeVisitor visitor) {
    int scanned = 0, skipped = 0;
    for (...) for (method in ...) {
        scanned++;
        if (!method.isConcrete()) continue;
        Body body; try { body = method.retrieveActiveBody(); }
        catch (RuntimeException | OutOfMemoryError ex) {
            skipped++; log WARN; continue;
        }
        if (body == null) continue;
        for (Unit unit : body.getUnits()) {
            if (!(unit instanceof Stmt)) continue;
            Stmt stmt = (Stmt) unit;
            if (!stmt.containsInvokeExpr()) continue;
            SootMethodRef ref = stmt.getInvokeExpr().getMethodRef();
            if (ref == null) continue;
            visitor.visit(method, stmt, ref);
        }
    }
    return new ScanStats(scanned, skipped);
}

@FunctionalInterface
private interface InvokeVisitor {
    void visit(SootMethod caller, Stmt stmt, SootMethodRef ref);
}
```

### View 1 — MOP caller set (preserves BUG-INV-ANA-19)

```java
private Set<SootMethod> findDirectMopCallersByBytecodeScan(
        Map<SootClass, List<SootMethod>> appClasses,
        Set<MopMethod> mopSignatures) {
    Set<SootMethod> result = new HashSet<>();
    if (mopSignatures.isEmpty()) return result;
    Set<String> mopKeys = buildMopKeys(mopSignatures);
    Set<SootMethod> shortCircuit = new HashSet<>();  // emulate "break" per method

    ScanStats stats = scanInvokesInAppClasses(appClasses, (caller, stmt, ref) -> {
        if (shortCircuit.contains(caller)) return;
        if (matchesMopSignature(ref.getDeclaringClass().getName(), ref.getName(), mopKeys)) {
            result.add(caller);
            shortCircuit.add(caller);
        }
    });
    log "Bytecode scan: " + stats.scanned + " scanned, " + stats.skipped + " skipped, "
        + result.size() + " direct MOP callers detected";
    return result;
}
```

### View 2 — WTG edge set (new for INV-ANA-22)

For the WTG complement, the predicate matches **library classes quarantined by SPARK** (`IGNORED_CLASSES`). The return type is a `Set<Edge>` where each `Edge` carries `(caller, callee, stmt)`.

```java
private Set<Edge> scanWtgComplementEdges(
        Map<SootClass, List<SootMethod>> appClasses,
        Predicate<String> isIgnoredClass) {
    Set<Edge> edges = new HashSet<>();
    scanInvokesInAppClasses(appClasses, (caller, stmt, ref) -> {
        String calleeClass = ref.getDeclaringClass().getName();
        if (!isIgnoredClass.test(calleeClass)) return;
        SootMethod callee = Scene.v().getMethodUnsafe(ref);  // may be null
        if (callee == null) return;
        edges.add(new Edge(caller, stmt, callee));
    });
    return edges;
}
```

`Edge` is `soot.jimple.toolkits.callgraph.Edge` (already a transitive dep of gator via Soot). Constructor `new Edge(SootMethod src, Stmt stmt, SootMethod tgt)` exists in Soot 4.7.1.

## Contract preservation (BUG-INV-ANA-19)

The refactor preserves every observable behavior of the original method:

| Property | Original | Refactor | Preserved? |
|----------|----------|----------|------------|
| Inputs | `(appClasses, mopSignatures)` | same wrapper | ✓ |
| Output | `Set<SootMethod>` | same wrapper | ✓ |
| FQN+name match policy | `matchesMopSignature(clsName, methodName, mopKeys)` | same call, same args | ✓ |
| Short-circuit per caller | `break` after first match | `shortCircuit` set used by visitor | ✓ (semantic equivalent) |
| Body retrieval resilience | try-catch (RuntimeException \| OOM), WARN log, continue | same code, moved into core helper | ✓ |
| Skip non-concrete methods | `!method.isConcrete()` continue | same in core helper | ✓ |
| Log statistics | "X scanned, Y skipped, Z direct MOP callers" | same string format, wrapper composes from `ScanStats` + `result.size()` | ✓ |
| Iteration order | `appClasses` LinkedHashMap → `entry.getValue()` list | unchanged | ✓ |

## Conclusion

Refactor is **safe**, **mechanical**, and **isomorphic** to the original on the MOP-scan side. The WTG complement (view 2) shares the same walker, so the resilience policy (INV-ANA-22) is inherited automatically. No risk of breaking `BUG-INV-ANA-19` semantics.

Implementation lands in Group 6 task 6.2 — the helper is introduced when item 6 (Opção A) needs it. Item 6 also calls `scanWtgComplementEdges` from inside the new `cgDelegation=true` branch of `FlowgraphRebuilder.buildCallGraph()`.

## Decision

- **No estimate change** for Group 6.
- API signature: `scanInvokesInAppClasses(appClasses, InvokeVisitor) -> ScanStats` + thin wrappers per use case.
- Place the helper as a `private` method on `RvsecAnalysisClient` initially (single owner); promote to package-private if a third caller emerges.
- The `Edge` type is `soot.jimple.toolkits.callgraph.Edge`; no new model classes needed.
