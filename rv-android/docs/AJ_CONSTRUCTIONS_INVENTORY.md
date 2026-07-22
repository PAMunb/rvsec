> **SUPERSEDED** — see `docs/aspectj_grammar_coverage.md` as the live contract for the dexlib2 AspectJ surface. This file is preserved as historical inventory only; entries here may diverge from the matrix and SHOULD NOT be cited in new tests, scenarios, or invariants. See gh62 D15 design rationale + INV-INS-102.

# AJ Constructions Inventory

**Purpose**: Enumerate every AspectJ construct that appears in the RVSEC
specification corpus (`rvsec/rvsec-mop/src/main/resources/{jca,generic,generic_new,aspect}/`)
and document, for each one, every file + line that uses it. Together with
[`AJ_TO_DEXLIB2_MAPPING.md`](AJ_TO_DEXLIB2_MAPPING.md) and
[`LIMITATIONS.md`](LIMITATIONS.md), it supports paper-grade defense of the
gh52 substitution per INV-INS-17.

**Generator**: `validator.ConstructionInventoryGenerator` (Group 10.2, not
yet implemented) will regenerate this file programmatically; the diff
between regenerated and committed must be empty in CI.

**Spec-set agnostic**: the inventory covers both JCA and Generic spec sets
— every `.mop` file under the scan directories is processed identically.

## Supported constructs (weaver covers these)

| Construct | JCA usages | Generic usages | Notes |
|---|---|---|---|
| `call(...)` | ✓ (pending auto-count) | ✓ | Covered by `CallPC` in the typed AST. |
| `execution(...)` | ✓ | ✓ | Used by Coverage catch-all. |
| `before(...)` | ✓ | ✓ | `BeforeEmitter`. |
| `after(...)` | ✓ | ✓ | `AfterEmitter`. |
| `after() returning(...)` | ✓ | ✓ | `AfterReturningEmitter` + `WrapperEmitter` for aliasing-safe cases. |
| `after() throwing(...)` | ✓ | ✓ | `AfterThrowingEmitter` — catch-any (Throwable) when unbound. |
| `args(...)` | ✓ | ✓ | Binding collector; merged during `CombinedPC AND`. |
| `target(...)` | ✓ | ✓ | Binding collector; `CallPC` extracts receiver register. |
| `!within(...)` | ✓ | ✓ | `NotWithinPC` filter. |
| `staticinitialization(T+)` | ✓ | ✓ | `StaticInitializationEmitter`. |
| `if(<expr>)` | ✓ | ✓ | `IfGuardEmitter`. |
| `thisJoinPoint` | ✓ | ✓ | `ThisJoinPointEmitter` pre-computes signature constant. |

## Out-of-scope constructs (LIMITATIONS.md documents them)

`around`, `cflow`, `cflowbelow`, `handler`, `get`, `set`, `initialization`,
`preinitialization` — zero usages empirically observed across the corpus.
See [`LIMITATIONS.md`](LIMITATIONS.md).

## File listing (pending auto-population)

The per-construct file:line listings will be auto-populated by
`validator.ConstructionInventoryGenerator` during Group 10.2. Manual audit
can happen meanwhile via:

```bash
grep -rnE "\b(call|execution|before|after|args|target|!within|staticinitialization|if|thisJoinPoint)\b" \
    rvsec/rvsec-mop/src/main/resources/
```
