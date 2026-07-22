> **SUPERSEDED** — see `docs/aspectj_grammar_coverage.md` as the live contract for the dexlib2 AspectJ surface. This file is preserved as historical inventory only; entries here may diverge from the matrix and SHOULD NOT be cited in new tests, scenarios, or invariants. See gh62 D15 design rationale + INV-INS-102.

# AspectJ → dexlib2 Mapping

**Purpose**: For every AspectJ construct enumerated in
[`AJ_CONSTRUCTIONS_INVENTORY.md`](AJ_CONSTRUCTIONS_INVENTORY.md), document
the concrete dexlib2 component that realizes it, the smali/DEX shape emitted,
and the test that proves the mapping.

**Spec-set agnostic**: the mapping covers both JCA and Generic specifications
with identical code paths.

## Mapping table

| AspectJ construct | Maven submodule / class | Emitted smali shape | Test reference |
|---|---|---|---|
| `call(<sig>)` | `pointcut-engine.CallPC` + `dex-mutator.DexWeaver` | no new instruction; matches `invoke-*` and drives injection | `PointcutExpressionParserTest` + IT (task 9.5) |
| `execution(* *.*(..))` | `coverage-weaver.CoverageWeaver` | `const-string vS, "<sig>"` + `invoke-static {vS}, Lmop/Coverage;->log` at method entry | `PackageFilterTest`, `SignatureFormatterTest` |
| `before(...)` | `advice-emitter.BeforeEmitter` | `invoke-static {args}, Lmop/<RuntimeMonitor>;-><event>(...)V` **before** the matched invoke | `EmitPlanShapeTest#beforeEmitterTargetsBeforeInsertionPoint` |
| `after(...)` | `advice-emitter.AfterEmitter` | same invoke shape, **after** the matched call | `EmitPlanShapeTest#afterEmitterTargetsAfterInsertionPoint` |
| `after() returning(R r)` | `advice-emitter.AfterReturningEmitter` + (aliasing case) `WrapperEmitter` | scratch-reg `move-result-object` captures `r`; wrapper routes through `Lmop/MonitorWrappers;` when aliasing | `EmitPlanShapeTest#afterReturningEmitterAsksForScratchRegister` |
| `after() throwing(T t)` | `advice-emitter.AfterThrowingEmitter` | `try ... catch (T t)` around the matched invoke; handler invokes monitor and rethrows | `EmitPlanShapeTest#afterThrowingEmitterProducesTryCatchSpec` |
| `args(a, b)` | `pointcut-engine.ArgsPC` + `dex-mutator` register extraction | binds invoke operand regs as `argNN` keys on `Match` | `PointcutExpressionParserTest#parsesArgs` |
| `target(t)` | `pointcut-engine.TargetPC` + receiver-reg extraction | receiver register of the matched invoke becomes `targetRegister` on `Match` | `PointcutExpressionParserTest#parsesTarget` |
| `within(<pattern>)` / `!within(<pattern>)` | `pointcut-engine.WithinPC` + `NotWithinPC` + `PointcutMatcher.matchesTypePattern` | no emission; positive `within` whitelists callers (matched as a no-op AND-clause that constrains where the joinpoint may live), negated form blacklists. The `WithinPC` AST node is treated as always-match in `PointcutMatcher` because the descriptor's `within(<RuntimeMonitor>)` self-references already bound the pointcut's host class — for app-side weaving this filter is a no-op | `PointcutMatcherTest#typePattern*` |
| `staticinitialization(T+)` | `advice-emitter.StaticInitializationEmitter` + `pointcut-engine.InheritanceResolver` | invoke at `<clinit>` entry; `<clinit>` synthesized by the dex-mutator executor when absent | `EmitPlanShapeTest#staticInitEmitterTargetsMethodEntry` |
| `if(<expr>)` | `advice-emitter.IfGuardEmitter` | `if-eqz vGuard, :skip` before the monitor invoke; `:skip` after it | `EmitPlanShapeTest#ifGuardEmitterAddsScratchOnTopOfDelegate` |
| `thisJoinPoint.getSignature()` | `advice-emitter.ThisJoinPointEmitter` + `coverage-weaver.SignatureFormatter` | pre-computed `const-string "<FQN: ReturnType method(params)>"` threaded as an extra arg | `SignatureFormatterTest` |
| `thisJoinPoint` | `advice-emitter.ThisJoinPointEmitter` (signature-only path) | only `.getSignature()` is supported; bare `thisJoinPoint` references in the corpus all resolve to that single accessor at parse time. Other reflective members (`getKind()`, `getArgs()`, `getThis()`, `getTarget()`) are out of scope and would land in `LIMITATIONS.md` if encountered | `SignatureFormatterTest` |

## Monitor owner convention

Every emitted invoke-static targets `Lmop/<shortName>RuntimeMonitor;` where
`shortName` comes from the descriptor JSON's `shortName` field. For the
JCA merge fixture this resolves to `Lmop/MultiSpec_1RuntimeMonitor;`.
Generic fixtures resolve to their own per-set short names without any
code change.

## Kotlin `suspend` / coroutines (INV-INS-24)

CPS-aware matching lives in `pointcut-engine.CpsDetector` +
`PointcutMatcher.cpsAwareOwnerMatch`. When the enclosing class is a Kotlin
state machine (extends `BaseContinuationImpl` / `SuspendLambda`, or class
name ends with `$<digit>`, or carries `@DebugMetadata`), the matcher
accepts the call even if the literal owner in the DEX points at the
state-machine class — it consults `@DebugMetadata.c` to recover the source
owner. Shapes the detector cannot lower are left unmatched and documented
in `LIMITATIONS.md`.
