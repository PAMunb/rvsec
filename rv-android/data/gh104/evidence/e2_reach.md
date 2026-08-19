# E2 — the reach of `advicesExcludedByArity`

Group 4 of gh104. Written 2026-08-19 against
`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json`
(2026-08-08, 115 advices, byte-identical to `results/gh92_e2e2/monitors/`).

## Why this file exists

A counter named `advicesExcludedByArity` invites the reader to assume it covers every
arity-incompatible advice. It does not, on two grounds. First, `ArgsPC` is referenced only
inside `pointcut-engine` (`ArgsPC`, `PointcutExpression`, `NegationPC`, `PointcutMatcher`,
`PointcutExpressionParser`) — the entire `advice-emitter` package, `BeforeEmitter` /
`AfterEmitter` / `AfterReturningEmitter` / `AfterThrowingEmitter` included, never reads it.
Second, `PointcutMatcher.matchArgs` returns `Match.empty(ap)` unconditionally when
`!ap.hasTypeConstraint()`, and the binding form (`args(alg)`, `args(alg, *)`) is exactly that
case, so nothing constrains those advices at match time either. The grouping loop where the
counter lives admits only `shouldWrap(a)` = `"after".equals(a.getPosition())`
(`WrapperEmitter.java:161-163`) and drops constructors with an explicit `continue` (`:251-256`).

## The four-class partition of the frozen descriptor's 115 advices

| class | count | seen by the counter? |
|---|---|---|
| `after`, non-constructor, with `args()` | **48** | yes — this is the denominator of `advicesExcludedByArity` |
| any position, no `args()` | **44** | no — clause 1: no positional constraint |
| `before`, with `args()` | **9** | no — bypasses wrappers entirely |
| `after`, constructor, with `args()` | **14** | no — dropped to the inline path by `:251-256` |

48 / 44 / 9 / 14 = 115. The 44 without `args()` are 31 `after` non-constructor + 4
`after`-on-constructor + 9 `before`.

Reading `advicesExcludedByArity` therefore requires reading this table: it is a count over 48
advices, not over 115.

## The recount that D-6 records: 25, none of them a constructor advice

The lineage's *first* rule ("drop an advice whose `args` list has no trailing `..` and whose
length ≠ `cc.paramFqns.size()`") is the one to avoid even as a counter: it would have counted
every `after` advice that has parameters and no `args()`. The lineage put that population at
16, of which 3 were said to be constructor advices. **Counted on the frozen descriptor's 115
advices the figure is 25, and none of the 25 is a constructor advice** — a constructor advice
carries an empty parameter list, so it was never in this population at all. The four-class
partition above is unaffected: the 25 are the parameter-carrying subset of the 31 `after`
non-constructor advices that declare no `args()`.

The 25 (`after`, non-constructor, no `args()`, non-empty parameter list):

`CipherSpec_f1`, `CipherSpec_f2`, `CipherSpec_wkb1`, `KeyGeneratorSpec_gk1`,
`KeyManagerFactorySpec_gkm1`, `KeyPairGeneratorSpec_gen`, `KeyPairSpec_gpr`, `KeyPairSpec_gpu`,
`KeyStoreSpec_gk1`, `MacSpec_f1`, `MacSpec_update`, `MessageDigestSpec_d1`,
`MessageDigestSpec_d2`, `MessageDigestSpec_update`, `PBEKeySpecSpec_c2`,
`RandomStringPasswordSpec_gb`, `SSLContextSpec_engine`, `SSLContextSpec_init`,
`SecretKeySpec_e1`, `SecureRandomSpec_genSeed`, `SecureRandomSpec_ints`,
`SecureRandomSpec_next3`, `SecureRandomSpec_setSeed1`, `SignatureSpec_s1`,
`TrustManagerFactorySpec_gtm1`.

Two of the 25 — `RandomStringPasswordSpec_gb` and `SecretKeySpec_e1` — belong to the two
specifications Group 2 task 2.2 deletes, so they do not exist in `jca_android` at all: the same
population there is 23, and any report of this measurement must name the set it was taken on.

The 9 `before` with `args()`: `CipherSpec_i1`, `CipherSpec_i2`, `MacSpec_i1`,
`SecureRandomSpec_next1`, `SecureRandomSpec_next2`, `SignatureSpec_i1`, `SignatureSpec_i2`,
`SignatureSpec_i3`, `SignatureSpec_i4`.

The 14 `after`-on-constructor with `args()`: `DHGenParameterSpecSpec_c1`,
`GCMParameterSpecSpec_c1_3`, `GCMParameterSpecSpec_c1_4`, `IvParameterSpecSpec_c1`,
`IvParameterSpecSpec_c2`, `KeyPairSpec_c1`, `PBEKeySpecSpec_f1`, `PBEKeySpecSpec_f2`,
`PBEKeySpecSpec_c1`, `PBEParameterSpecSpec_c1`, `PBEParameterSpecSpec_c2`,
`SecretKeySpecSpec_c1`, `SecretKeySpecSpec_c2`, `SecureRandomSpec_c2`. Typical shape:
`call(public DHGenParameterSpec.new(int, int)) && args(primeSize, exponentSize)`.

## The four constructor advices that sit on report sites — and why they are unrelated

Four of the fourteen — `IvParameterSpecSpec_c1/c2` and `PBEKeySpecSpec_f1/f2` — sit on report
sites: `PBEKeySpecSpec.mop:24,30`, which Group 7 makes legible as `ForbiddenMethod`; and, at
**advice** level, `IvParameterSpecSpec_c1`'s `monitorCalls` fires `c1Event` and `c3Event`
(`.aj:305-310`), so that advice sits on the c3/c4 report sites (`IvParameterSpec.mop:48,55`,
which **disappear** with the predicates in Group 2) while the **events** `c1`/`c2` themselves
are guards (design D-6 §179) — advice and event are different units, and the sentence is about
the advice. A reader seeing `advicesExcludedByArity > 0` next to a legible `PBEKeySpecSpec`
report must be able to learn from this file that the two are unrelated: none of those four
advices ever reaches the grouping loop, so none of them can contribute to the number.

## Reproduction

```bash
python3 - <<'EOF'
import json, re, collections
d = json.load(open('results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json'))
c = collections.Counter()
for a in d['advices']:
    e = a.get('expression', '') or ''
    c[(a.get('position'), re.search(r'\bargs\s*\(', e) is not None, '.new(' in e)] += 1
for k, v in sorted(c.items(), key=lambda x: -x[1]):
    print(f"position={k[0]:<7} args()={k[1]!s:<5} ctor={k[2]!s:<5} -> {v}")
EOF
```

Output on 2026-08-19:

```
position=after   args()=True  ctor=False -> 48
position=after   args()=False ctor=False -> 31
position=after   args()=True  ctor=True  -> 14
position=before  args()=True  ctor=False -> 9
position=before  args()=False ctor=False -> 9
position=after   args()=False ctor=True  -> 4
```

31 + 4 + 9 = 44 without `args()`; 48 + 44 + 9 + 14 = 115. The 25 are the subset of the first
`after`/no-`args()` row whose `parameters` list is non-empty:

```bash
python3 - <<'EOF'
import json, re
d = json.load(open('results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json'))
n = [a['name'] for a in d['advices']
     if a.get('position') == 'after'
     and not re.search(r'\bargs\s*\(', a.get('expression', '') or '')
     and '.new(' not in (a.get('expression') or '')
     and a.get('parameters')]
print(len(n)); print('\n'.join(sorted(n)))
EOF
```

If the count is not 25, the descriptor loaded was not
`results/gh101_group8_jca_frozen_control/monitors/MultiSpec_1MonitorAspect.json`.

## The measurement itself, on this descriptor

Measured 2026-08-19 by running `WrapperEmitter.generate` directly against the frozen descriptor
(no APK, no device — the emitter is a pure function of descriptor + `android.jar`):

| `android.jar` | `wrappersGenerated` | `advicesExcludedByArity` | per-advice | `mop/MonitorWrappers.java` vs the frozen control |
|---|---|---|---|---|
| android-28 … android-34 | 81 | **5** | TMF_g2 ×1, KMF_g2 ×1, SR_g2 ×1, SR_g4 ×2 | differs (3 wrappers absent) |
| android-35, android-36 | 84 | **10** | TMF_g2 ×1, KMF_g2 ×1, SR_g2 ×3, SR_g4 ×5 | differs only in the order of two `MessageDigest.update` wrappers |
| android-36.1, android-37, android-37.0 | 84 | **10** | TMF_g2 ×1, KMF_g2 ×1, SR_g2 ×3, SR_g4 ×5 | **byte-identical** (sha256 `6a219bb2…dbe723ab`) |

**The number depends on the `android.jar`, not only on the descriptor.** The unit is
advice/overload pairs, and the overloads come from overload expansion against `android.jar`.
`SecureRandom.getInstance(String, ..)` resolves to three overloads up to API 34 and to six from
API 35 on, where `SecureRandomParameters` arrives; `SecureRandomSpec_g2` (`args(alg, *)`, arity
exactly 2) and `_g4` (`args(alg)`, arity exactly 1) each gain incompatible pairs accordingly.
The frozen control was woven against a jar of the 36.1/37 family — the default
`ConfigResolver.resolveAndroidJarFromEnv()` picks the lexicographic maximum under
`$ANDROID_HOME/platforms`, which on this machine is `android-37.0`. Any re-weave meant to
reproduce the predicted **10** must use that jar; `--android-jar $ANDROID_HOME/platforms/android-30/android.jar`
measures **5** on the same descriptor, and produces 81 wrappers instead of 84.

The four advices are the same in every case, and they are exactly the four predicted:
`TrustManagerFactorySpec_g2`, `KeyManagerFactorySpec_g2`, `SecureRandomSpec_g2`,
`SecureRandomSpec_g4`.

## Two sentences to close on

(i) In counter mode the number is a **diagnosis**, not a change: every advice that fired before
this group still fires after it, and `wrappersGenerated` is unchanged.

(ii) The positive case the counter should catch on this descriptor is
`TrustManagerFactory_getInstance(String p0)`, which today fires `g1Event`, `g2Event`, `g3Event`
(`results/gh101_group8_jca_frozen_control/monitors/mop/MonitorWrappers.java:538-544`) — `g2`
carries `args(alg, *)` (arity 2) over a one-parameter call, so it must appear in the count and
must still fire. It does both: the emitter run above counts it and emits a `MonitorWrappers.java`
byte-identical to the frozen control.

`ResultsJsonReportingTest` builds `counts` by hand (its javadoc says why), so it proves
serialisation only; the re-weave of task 4.6 is what validates the origin of the count, and its
table lives in `e2_reweave.md`.
