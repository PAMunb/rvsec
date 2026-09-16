# Code review of the change and what was done with it (task 16.3)

`/rv-code-reviewer` over `325c2a38..HEAD` (25 commits, the weaver, `rvsec-core`, the `jca_android`
set, the conformance component, four Python modules and the sweep script). It reported five findings
as critical. Each was adjudicated against the code before anything was changed; three were repaired,
one is a decision this change already recorded, and one is latent by the same measurement that makes
its sibling latent.

## Repaired (commit of 2026-09-15, `fix(gh114)`)

**The after-finally handler of the inline constructor path caught all exceptions.** The advice
handler is listed first on the matched range, and a DEX code unit carries at most one catch-all
entry, so a constructor inside a user `finally` — or `catch (Throwable)` — made the method unwritable
and failed the whole APK at `DexPool.writeTo`. The handler now catches `java.lang.Throwable`, a typed
entry that can be listed beside the user's and catches the same exceptions.
`DexWeaverCtorAfterFinallyTest` gained the case with a user `finally` over the constructor invoke.

**`AndroidClassIndex` was never closed.** It is `AutoCloseable`, holds the `android.jar` zip open,
and `BatchRunner.runPipeline` builds one per APK — which the `batch` subcommand calls in one JVM. It
is released in a `finally` on every exit of the method.

**`_add_results_entry` was the only writer of the single pass without a guard.** It reads the task's
configuration outside `_extract_task_data`'s own handler, so a task whose configuration could not be
read would abort the pass, truncate the four CSVs and leave `results.json` and `performance.csv`
unwritten — against this change's own scenario "results.json Extraction Failure Is Counted, Not
Swallowed". It now counts the failure and logs it, like the four row writers (INV-PLT-32).

## Not repaired, and why

**A plain `after` binding an object under construction (reported as a `VerifyError` waiting to
happen).** Reachable only through the same inline constructor path, and only for a plain `after` on a
constructor. Measured on the set: of the 41 constructor events of `jca_android`, **zero** are plain
`after` — every one is `after … returning`, which is what INV-INS-163 already states. Left as a
property of a path the set does not reach, not repaired inside this change.

**`PointcutExpander.withArity` returning no signature for a contradicted arity** is not a defect
found by the review: it is the rule D17 decides, and the six `generic` events it affects are
enumerated there. Turning it into a typed refusal changes what the conformance component publishes
and belongs to a change of its own.

## The weaver moved after the smoke, and the woven output did not

The typed handler is a change of the weaver, and the smoke of task 15.4 ran before it. One APK
(`de.markusfisch.android.binaryeye_174.apk`) was instrumented again with the repaired weaver and
compared with the APK the smoke ran on: **all 19 `classes*.dex` have the same SHA-256**. The smoke's
evidence therefore still describes the current weaver.

## Warnings and suggestions

The review also lists warnings (counter semantics of `wrappersAliasedToSubtype`, `insertAfter` and
the try `end` label, a non-trailing `..` in `args`, nested types of APK-defined classes, the host
class loader in `PointcutExpander.binaryName`, a truncated envelope leaving a partial `vfp` inside
`unique_msg`) and suggestions (P3/P4 violations in `WrapperEmitter` and `DexWeaver`, the dead loops
of the retired file-major path, the complexity of `resolve_invokes`). None was verified in this
session, and none is repaired here: they are the researcher's to schedule, each against its own
measurement.
