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

## Known defects left unrepaired

Recorded rather than fixed. Both were found while implementing gh100 and both
were deliberately left alone; they are here so a later reader does not have to
rediscover them.

### The SDK platform jar is chosen by lexicographic order (gh100, 2026-08-07)

`ConfigResolver.resolveAndroidJarFromEnv` picks the platform jar by taking the
lexicographic maximum of the directory names under `$ANDROID_HOME/platforms/`:

```java
.max((a, b) -> a.getParent().getFileName().toString()
        .compareTo(b.getParent().getFileName().toString()))
```

With `android-4` through `android-37` installed, `"android-4"` wins over
`"android-37"` because `'4' > '3'` at the eighth character. The weaver then
resolves API level 4 — Android 1.6, from 2009 — as the platform it matches
pointcuts against. `latestUnder`, which picks `d8` / `zipalign` / `apksigner`
out of `build-tools/`, has the same shape and prefers `37.0.0-rc1` over
`37.0.0`.

The defect is observable because gh100 made the weaver log the resolved
`android.jar` at instrumentation start; that log line found it on its first
real use.

**Why it matters.** `AndroidClassIndex` is built from this jar, and it drives
overload expansion in `WrapperEmitter`. A target the index cannot resolve falls
through to the inline emission path — the path that truncates fused advices. So
a wrongly-resolved platform jar adds truncation from a second cause on top of
the one gh100 repairs.

**Why it was not repaired.** Measured, not assumed: weaving `cryptoapp.apk`
under `android-4` and under `android-37.0` differs only in `wrappersGenerated`
(90 against 96), and the six extra wrappers are for call targets the app never
invokes. `wrappersSubstituted` (74), `matchesApplied` (32) and
`constructorInlineApplied` (11) are identical, so the woven output is the same
and gh100's evidence baseline is unaffected. The comparison holds for this APK;
it is not a general result, and an APK exercising modern framework overloads
could well diverge.

**Current mitigation, and its shelf life.** On the development machine
`platforms/android-4` was moved aside, which makes the lexicographic maximum
land on `android-37.0` by accident of the remaining list. Installing any
single-digit platform (`android-8`, `android-9`) brings the defect straight
back. Nothing was changed in the resolver, in the Docker image, or on any other
machine. Pass `--android-jar` explicitly when the resolution matters.

### A root reactor build needs `-DskipMopAgent=true` (gh100, 2026-08-07)

`mvn install` from the `rvsec` root fails in `rvsec-agent` at
`mop-maven-plugin:agent-gen` with `aspectjrt.jar is missing from the classpath`.
`rvsec-agent` precedes `rvsec-android` in the reactor order, so the failure
stops the build before the dexlib2 CLI jar is produced at all.

`-DskipMopAgent=true` skips the failing mojo and the build completes, delivering
`instr-cli.jar` into `modules/rv-instrumentation-dexlib2/lib/`. The property is
the same one the `-Pcheck` profile sets (`rvsec/pom.xml:38`).

The JSE agent is not on the dexlib2 instrumentation path, so skipping it costs
that pipeline nothing. The failure itself is out of scope and was left
untouched by explicit decision.
