# Green evidence — what the repair changed (gh100 tasks 6.1–6.4)

Recorded 2026-08-07, against the same pinned inputs the red run used
(`v2_pinned_inputs.md`). The only input that differs is the weaver itself.

| | red | green |
|---|---|---|
| `instr-cli.jar` sha256 | `77cbd6e71e3a3563bc0a41221fa11075a9d78ac9b0e5304af81a1118237ce25e` | `f8a6a49caba13f776e5180729e9ddeddf519832e1da539529616385db7cc3677` (reactor build 2026-08-07 18:57) |
| descriptor sha256 | `e53f0af1…` | `e53f0af1…` — unchanged |
| monitor source sha256 | `03fe08f0…` | `03fe08f0…` — unchanged |

## 6.1 — V0

5 of 5 assertions pass, where 4 of 5 failed in `e29c3694`. The one that passed
before is the negative control and still passes, so the suite did not go green
by weakening.

The INV-INS-104 source scan over `advice-emitter` also passes: no emitter source
reduces `monitorCalls` to its first element.

## 6.2 — V2

Verdict **PASS**, against **FAIL** in the red run. Both reachable events appear,
and they appear exactly as often as the sibling the truncating path was already
emitting:

| dropped event | red | green | kept sibling |
|---|---|---|---|
| `IvParameterSpecSpec_c3Event` | ×0 | **×4** | ×4 |
| `SecretKeySpecSpec_c3Event` | ×0 | **×5** | ×5 |

One invoke per site, which is what "N monitor calls emit N invokes" means at
this scale. `SecretKeySpecSpec` / `UnsatisfiedConstraint` is the case the delta
spec names by hand — the category that read zero across 97,018 events.

The other 7 of the 9 stay `n/a` in both runs: their advices matched no call site
in `cryptoapp`, so the APK is silent about them either way. The descriptor-level
statement about all 9 is the census's, below.

## 6.3 — Census

Same script, same descriptor, same monitor source as `census_pre_repair.json`.
Only the weaver sources it reads have changed.

| | pre | post |
|---|---|---|
| emission model | INLINE PATH TRUNCATES | **INLINE PATH ITERATES** |
| truncation sites | 3 | **0** |
| advices total | 115 | 115 |
| advices with N > 1 | 17 | 17 |
| routed to the wrapper path | 10 | 10 |
| routed to the inline path | 7 | 7 |
| **events dropped** | **9** | **0** |
| of which error emitters | 8 | 0 |
| `UnsatisfiedConstraint` dropped | 7 | 0 |
| `UnsafeAlgorithm` dropped | 1 | 0 |

The descriptor did not move; the routing did not move. What moved is that the
inline path now emits what it routes.

## 6.4 — Weaver counters, and the register-pressure question

Same APK, same descriptor, per-APK counters from the production Python path.

| counter | red | green | |
|---|---|---|---|
| `advices` | 115 | 115 | |
| `matchesApplied` | 32 | 32 | |
| `wrappersGenerated` | 96 | **84** | the merge, exactly the 12 that used to be discarded |
| `wrappersSubstituted` | 74 | 74 | unchanged — no call site lost its wrapper |
| `constructorInlineApplied` | 11 | 11 | |
| `plansSkippedAliasing` | 3 | 3 | |
| **`plansSkippedHighRegister`** | **0** | **0** | |
| `plansSkippedUnresolvedBinding` | 0 | 0 | |
| `plansSkipped` | 0 | 0 | |
| `coverageInstrumented` | 118 | 118 | |
| `wovenDexes` / `monitorDexes` | 6 / 1 | 6 / 1 | |

**No increase in register-pressure discards.** The pre-repair baseline was 0 and
it is still 0, so there is no follow-up issue to open on this APK. That is a
statement about `cryptoapp`, not about the corpus: the repair splices one extra
invoke at 4 + 5 = 9 sites here, and an APK whose methods sit closer to their
register budget could still discard. The counter is now on the production path
(INV-INS-105) precisely so the next corpus run answers this without being asked.

`wrappersGenerated` falling by 12 is the wrapper merge, not a loss:
96 wrappers over 84 distinct registry keys became 84 wrappers over 84 keys, and
`wrappersSubstituted` is unchanged at 74, so every call site that was being
rewritten still is. Before the merge those 12 were emitted, registered, and
immediately overwritten.

## What these verdicts do not say

V0 and V2 prove **emission and arrival in the woven DEX**, not arrival in logcat
at runtime. The runtime arm of Layer 3 (L3-a) needs a UI driver inside the
platform's emulator session and did not run; no emulator was started for any
part of this. A violation that is emitted can still fail to fire if the site is
never executed, and nothing here speaks to that.
