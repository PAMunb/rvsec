# A6 — parse once, resolve once: identity and cost (task 17.5)

The repair is accepted on the woven output, not on the clock: the same APK, woven with the same
descriptor by the weaver without the memo and with it, must give the same DEXes and the same
counters (INV-INS-168). The wall time is reported beside that identity, because the measurement is
the reason the repair exists.

## What was measured

| | before (no memo) | after (memo) |
|---|---|---|
| commit of the weaver | `5d304834` (reactor built 2026-09-15 19:28) | this change's group 17 (reactor built 2026-09-15 20:25) |
| APK | `de.markusfisch.android.binaryeye_174.apk` (19 MB, 18 input DEX) | the same file |
| descriptor | `MultiSpec_1MonitorAspect.json` of the `jca_android` monitor generated at 19:39 | the same file, reused through `--skip-monitors` |
| `instr-cli` wall time | **659.9 s** | **103.7 s** |

Both runs went through the production path (`rv-experiment run … --instrumentation-variant dexlib2`),
one JVM for the APK, on an otherwise idle host.

## Identity

- Every `classes*.dex` of the two instrumented APKs has the same SHA-256: **19 entries, no
  difference** (18 woven DEXes plus the monitor DEX).
- `instrument_results.json` for the APK is identical, counter by counter: `advices=193`,
  `wrappersGenerated=141`, `advicesExcludedByArity=10`, `wrapperTargetsUnresolved=0`,
  `matchesApplied=940`, `plansSkipped=0`, `wrappersSubstituted=869`, `wrappersAliasedToSubtype=1895`,
  `wrapperAliasesUnmerged=0`, `constructorInlineApplied=486`, `coverageInstrumented=49932`,
  `wovenDexes=18`, `monitorDexes=1`.

The APK file itself is not compared byte for byte: the signature block carries a timestamp, so two
signings of identical DEXes differ. The DEXes are what the weaver produces.

## Where the time went

Fifteen thread dumps of `instr-cli` taken during the run without the memo, over
`app.pachli_50.apk`, put about nine frames in ten in `PointcutExpressionParser`, reached from
`DexWeaver.parseCached` at `DexWeaver.weave`, and the rest in `TypeResolver.toDescriptor` →
`lookupFqn`. That is the shape the three memos of D19 address: one parse per advice expression per
weave, one composition per class and advice instead of one per instruction, one resolution per type
name per resolver.
