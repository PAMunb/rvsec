# Limitations — gh52 DEX-native weaver

Every AspectJ / instrumentation concern that the weaver intentionally does
NOT support, with the empirical evidence that justifies the scope decision
and the reviewer scrutiny the concession invites.

## Out-of-scope AspectJ constructs

All eight items below have **zero empirical usages** across
`rvsec/rvsec-mop/src/main/resources/{jca,generic,generic_new,aspect}/`
(JCA + Generic spec sets, both spec sets in active use across experiments).
The scope decision is empirical, not philosophical; each will be
re-evaluated if a future spec introduces it.

| Construct | Why not implemented |
|---|---|
| `around(...)` | Full control-flow substitution requires wrapping the matched call in a synthetic method that executes the advice body + optionally forwards. The typed AST accommodates it (`CombinedPC.op()` could extend), but the runtime semantics (proceed handling, return-value threading, exception transparency) would roughly double the dex-mutator's implementation surface. Zero usages in JCA/Generic so the cost never paid for itself. |
| `cflow(...)` / `cflowbelow(...)` | Stack-based dynamic scoping needs a thread-local shadow stack maintained at every matched entry/exit. Runtime overhead + static analysis complexity outweighs the value at zero usages. |
| `handler(...)` | Matches catch-block entries; structurally distinct from call-site matching and requires extra DEX analysis (catch-handler label walk). Deferred. |
| `get(...)` / `set(...)` | Field access joinpoints; each field-read / field-write would need a matcher pass, and the pointcut-engine is call-site oriented today. Zero usages. |
| `initialization(...)` | Object-creation joinpoint distinct from `call(.new(...))`; would need an additional advice-emitter for constructor-execution entry. |
| `preinitialization(...)` | Even narrower — before-super-call joinpoint; rarely used in practice. |
| `adviceexecution()` | JavaMOP-synthesized construct that pointcuts over the EXECUTION of advice itself (used by some specs to chain meta-advice). Surfaces 71 times in `MultiSpec_1MonitorAspect.aj` and `*.mop.aj` files but always in self-referential `!within(<RuntimeMonitor>) && !adviceexecution()` form whose **purpose is to filter OUT advice executions from being matched again** — i.e., it appears as a guard, not as a primary pointcut. The dex-mutator's app-side weaving never matches against the synthesized advice methods (they live in `mop/<RuntimeMonitor>` namespace which is filtered by the canonical package filter), so this filter is a structural no-op for our weaver. Treated as a parser-acknowledged tombstone: the AST has a sentinel that always-matches; the matcher never produces a positive result against it. |

**Review scrutiny invited**: any spec author who needs one of these eight
should open a task to extend this doc + the mapping + the emitter, then
provide at least one concrete usage that motivates the extension.

## Partial Kotlin `suspend` coverage (INV-INS-24)

The CPS-aware matcher recognizes three common state-machine shapes:

1. Superclass `BaseContinuationImpl` / `ContinuationImpl` / `SuspendLambda`.
2. `@DebugMetadata` annotation presence (kotlinc 1.4+).
3. `Outer$<digit>` naming convention.

Shapes known to slip through:

- **Anonymous/inline suspend bodies lowered without `@DebugMetadata`** —
  kotlinc can emit state machines without the metadata annotation under
  some `-Xjvm-default=all` configurations. Mitigation: rely on the naming
  suffix heuristic; when that also fails the advice is skipped and
  reported in the weave log.
- **Heavy continuation captures with reference indirection** — state
  machines that invoke the user-facing method through an intermediate
  lambda may hide the declaring type at the DEX level; the matcher's
  owner-resolution fallback (via `@DebugMetadata.c`) covers the common
  case but not every lowering.

Any concrete failing case should land here with a smali reproducer; when
`advice-emitter/src/test/KotlinSuspendFixtureTest` gets a `@Disabled`
case, this doc MUST gain the matching entry (per task 5.11).

## Unverified bytecode profiles

The Phase-5 ratification gate requires three oracle APKs covering
distinct bytecode profiles (INV-INS-22). Any profile not yet carried by a
committed oracle is "unverified" until the third oracle is selected and
its `validator/oracles/<name>-oracle.yaml` lands:

- Multidex real-world APK from JCA-400 — **PENDING** (task 10.14).

## Unmapped specification-set-specific constructs

At time of writing, neither JCA nor Generic specs use the eight
out-of-scope constructs. The empirical scan will re-run before Phase 5;
any new usage surfaced there bumps this doc before the gate is allowed
to proceed.
