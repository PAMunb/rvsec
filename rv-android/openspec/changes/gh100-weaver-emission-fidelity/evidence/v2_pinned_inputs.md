# V2 — the inputs the red run used, pinned (gh100 task 4.3)

The green run of task 6.2 MUST weave from exactly these bytes. Issue #101 is
editing the `jca_android` `.mop` sources in parallel — seven of the twenty-three
files were touched on 2026-08-07 between 13:55 and 15:28 — so a green run over
regenerated monitors would not answer the red one, and INV-INS-108 would prove
nothing.

Recorded 2026-08-07.

## The pin

| what | path | sha256 |
|---|---|---|
| descriptor | `results/gh99_jca_android_monitors/monitors/MultiSpec_1MonitorAspect.json` | `e53f0af17f119e083d12cf779f5ad88ee488e4d969e359a9d6d243b2d7324b4f` |
| generated monitor | `results/gh99_jca_android_monitors/monitors/MultiSpec_1RuntimeMonitor.java` | `03fe08f07f40f99adc9a8f4e75aab0fd8e54627d65a3e46458ff8ec7aa93ba04` |
| generated aspect | `results/gh99_jca_android_monitors/monitors/MultiSpec_1MonitorAspect.aj` | `d0825369c933bd63ec35daac4cafb757134a4e1f7fe69b41e19062a5893bee5e` |
| coverage aspect | `results/gh99_jca_android_monitors/monitors/Coverage.aj` | `66983f69269e2c63cd8a3b237a3fa764fdf6aaf91c2c19d0ef50ee5001ca3fc0` |
| input APK | `apks_examples/cryptoapp.apk` | `6b1076696c7e2f8860c971e964333bf0e18449befb49d91a5d5fb5b0b5cb6d0d` |
| woven APK (red) | run artefact, not committed | `8a20c2f4665652d585fb55d25d10489b3674269f46804ee87d7815ce4a14f490` |
| weaver under test (red) | `modules/rv-instrumentation-dexlib2/lib/instr-cli.jar` | `77cbd6e71e3a3563bc0a41221fa11075a9d78ac9b0e5304af81a1118237ce25e` |

The weaver jar's hash is recorded because it is the one input that *must* differ
between the red and the green run. Everything above it must not.

These monitors were generated on 2026-08-06 18:37–18:40, before any of the
2026-08-07 specification edits, so the pin costs nothing: regenerating now would
have frozen a mid-flight state of issue #101's work and bought no fidelity.

## The descriptor is byte-identical to task 1.4's

`results/gh99_jca_android_monitors/monitors/MultiSpec_1MonitorAspect.json` and
`results/gh92_e2e2/monitors/MultiSpec_1MonitorAspect.json` have the same sha256,
`e53f0af1…`, while their generated `MultiSpec_1RuntimeMonitor.java` files differ
(`03fe08f0…` against `78b1fcf5…`).

Task 1.4 assumed the `jca` and `jca_android` runs would need separate censuses.
For the weaver they do not: the aspect descriptor is what the weaver reads, and
the two sets produce the same one. The census over `jca_android` reports the same
7 inline-routed advices and the same 9 dropped events, which is why V2's expected
set below matches the committed `census_pre_repair.json` exactly. What differs
between the sets lives in the generated monitor — the state machines and the
`expecting` texts — and none of it reaches the emission decision.

## What V2 can and cannot conclude from one APK

`cryptoapp` exercises 2 of the 9 dropped events. The other 7 belong to advices
whose pointcuts matched no call site in this APK, so they are reported `n/a` and
are not evidence in either direction: a silent APK and a truncating weaver look
identical there.

| dropped event | advice wove? | kept sibling | dropped |
|---|---|---|---|
| `IvParameterSpecSpec_c3Event` | yes | ×4 | **×0** |
| `SecretKeySpecSpec_c3Event` | yes | ×5 | **×0** |
| the other 7 | no | ×0 | ×0 |

The two that do resolve are the discriminating pair: their advices demonstrably
wove — the kept `get(0)` sibling is in the DEX four and five times — and the
second call of each is absent. `SecretKeySpecSpec` / `UnsatisfiedConstraint` is
the case the delta spec names by hand.

This is narrower than the delta spec's scenario, which asks for all 9. Covering
the remaining 7 needs APKs that construct `PBEKeySpec`, `PBEParameterSpec`,
`SecureRandom` and the second `IvParameterSpec` shape, i.e. more weaves rather
than a different method. The descriptor-level statement about all 9 is the
census's (tasks 1.4 and 6.3); V2's is the end-to-end statement about the subset
one APK can reach, and the change reports it as that.

## A side effect worth knowing about

The weave writes `mop/MonitorWrappers.java` and `mop/Coverage.java` **into**
`--monitor-src-dir`, so the pinned directory is not read-only in practice. The
four pinned files are untouched — their hashes above were taken after the red run
— and the green run regenerates `mop/` from the same descriptor, so the pin
holds. It is recorded here because a reader checking the directory will find
files the pin does not list.
