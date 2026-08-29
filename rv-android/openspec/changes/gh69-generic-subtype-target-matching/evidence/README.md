# gh69 — measured before/after of the extractor

Measured 2026-08-28. The **before** side is not a reconstruction from memory: the three
pre-change source files (`MopMethod.java`, `UsedJcaMethodsVisitor.java`, `JavamopFacade.java`)
were restored from `git show HEAD:` into a scratch tree, compiled against the same dependency
set, and placed ahead of the rebuilt fat jar on the classpath so they shadow the new classes.
Both sides therefore parse the same corpus with the same parser, and differ only in the visitor.

`before_*.csv` carries `className,name,parameters,signature`. `after_*.csv` adds the three flag
columns the change introduces: `includeSubtypes`, `nameIsPattern`, `ownerFromImplicitSeed` (the
last one is what `MopSpecsTargetSource` turns into `MatchPolicy.STRICT`).

**The `after_*.csv` in this directory are the final state of the change** — the extractor as it
stands after phase 5.6, i.e. after all three parts of the scope-boundary-(c) repair (the implicit
`java.lang` seed, the STRICT bound on it, and the FQN resolution of pointcut parameter types).
An earlier revision of this directory captured the intermediate D9 state (`jca` still at 120,
parameters still unqualified) and was refreshed on 2026-08-28 by the `/opsx:verify` pass, which
found it contradicting the shipped gates.

## Totals

| spec set | before (sig / pairs / owners) | after (sig / pairs / owners) |
|---|---|---|
| `jca` (frozen ruler) | 120 / 68 / 22 | **122 / 70 / 23** |
| `jca_android` (production successor) | 207 / 113 / 44 | **211 / 117 / 47** |
| `generic_new` (verification fixture) | **0 / 0 / 0** | **72 / 68 / 21** |

`generic_new` under the `+`-aware owner key `(className, includeSubtypes, methodName)` holds
**69** pairs; **68** is the `+`-blind count, where `Iterator.next` and `Iterator+.next` collapse.
That single collapse is the whole of the 69 → 68 difference: the `ServerSocket` constructor pair
does **not** merge with the `ServerSocket+` entries, whose method names are `accept`, `bind` and
`setSoTimeout`. Some artefact prose quoted 67 for the `+`-blind key; that was an arithmetic slip
(the pre-constructor figure was 66 and the two constructor pairs add 2, so 68) and was corrected
on 2026-08-28.

**Zero unresolved owners in all three sets** (`JavamopFacade.getSkippedOwners()` empty), which is
the state the `java.lang` seed produces. Before the seed, `String` was the single skipped owner in
both JCA sets.

## `jca`: 120 → 122, and the two added rows are the whole difference

Applying `new → <init>` to the 120 before-rows and adding the two rows below yields a set equal to
the 122 after-rows. **No row was removed and none merged** — 122 rows against 122 distinct
`MopMethod` identity keys, which is the check that matters, since the parameter list participates
in that identity. Same for `jca_android` (211/211) and `generic_new` (72/72). The merge hazard
that motivated measuring part (iii) in isolation is therefore measured absent, not assumed absent.

The two added rows, both from `RandomStringPassword.mop`, both `ownerFromImplicitSeed=true` and
therefore STRICT downstream:

```
java.lang.String,valueOf,(java.lang.Object)   "public static String String.valueOf(Object)"
java.lang.String,toCharArray,()               "public char[] String.toCharArray()"
```

They are the only two seeded rows in either JCA set, and there are none in `generic_new` — its
seven `java.lang`-owner specs declare `import java.lang.*;` and resolve at the first step, keeping
the LENIENT policy their `(..)` parameter lists require.

## The `new` → `<init>` flip

`jca`: 18 signature rows over 11 owners had been emitted all along under the name `new`, which no
Soot method carries — so the frozen ruler had never counted a constructor call site,
`new SecretKeySpec(...)` included. The 11 owners:

```
java.security.KeyPair                        javax.crypto.spec.IvParameterSpec
java.security.SecureRandom                   javax.crypto.spec.PBEKeySpec
javax.crypto.CipherInputStream               javax.crypto.spec.PBEParameterSpec
javax.crypto.CipherOutputStream              javax.crypto.spec.SecretKeySpec
javax.crypto.spec.DHGenParameterSpec         javax.xml.crypto.dsig.spec.HMACParameterSpec
javax.crypto.spec.GCMParameterSpec
```

`jca_android`: 41 rows over 27 owners. `generic_new`: 3 rows over 2 owners
(`java.net.ServerSocket`, `java.util.TreeMap`) — and `TreeMap` appears **only** in a constructor
pointcut, which is why the owner count is 21 and not the pre-D9 20.

## FQN resolution of parameter types (part iii)

Between the D9 stage and the state dumped here, the parameter list of **28** rows changed in `jca`,
**58** in `jca_android` and **18** in `generic_new`, with no row added or removed by the resolution
itself. That total has **two** causes and they must not be conflated, which is the whole reason
D11 required part (iii) to be measured alone:

| | part (iii) alone (import-driven routes) | the `java.lang` seed of part (i) | total |
|---|---|---|---|
| `jca` | **1** (`SSLContext.init`) | 27 | 28 |
| `jca_android` | **1** (`SSLContext.init`) | 57 | 58 |
| `generic_new` | **16** | 2 | 18 |

Part (iii) resolves a parameter type through the spec's own explicit and wildcard imports, so a
`jca` spec — which imports no `java.lang` — kept writing `(String)` after it. Only
`javax.net.ssl.SSLContext.init` moved there, its `KeyManager[]`/`TrustManager[]` gaining the
`javax.net.ssl` prefix. `generic_new` moved 16 because its specs *do* declare `import java.lang.*;`
alongside `java.util`/`java.net`. The remaining `(String)` → `(java.lang.String)` rewrites arrived
later, with the seed, and are the seed's effect rather than (iii)'s — the two `generic_new` rows in
that column are `URLDecoder.decode` and `URLEncoder.encode`, whose spec imports only `java.net.*`.

This part is a prerequisite of the STRICT bound rather than an end in itself: a STRICT target is
compared against the signature Soot reports at the call site, and `Object` never equals the
`java.lang.Object` Soot writes there.

## `jca_android`: the two `+` owners it declares

After normalising `new → <init>`, the before→after diff on the subtype axis is two rows that had
loaded nothing:

```
java.security.Key#getEncoded        "public byte[] Key+.getEncoded()"
javax.crypto.SecretKey#getEncoded   "public byte[] SecretKey+.getEncoded()"
```

They are the production set's only `+` pointcuts, and the only assertion in this change that proves
the subtype repair against a set that is actually in production. The remaining before→after growth
of that set (207 → 209 rows before the seed) belongs to gh109, which is adding specs to the
directory concurrently — which is why every `jca_android` gate derives its count by enumeration and
none pins a literal.

## `generic_new`: 0 → 72, with 0 unresolved owners

The headline claim, measured rather than asserted. Zero owners are skipped, which holds only
because `CharSequence_NotInSet.mop` gained its `import java.util.*;` (task 1.0b) — without it its
`Set+` owner resolves to nothing and coverage drops to 23/27 specs.

## How to reproduce

There is no script in the repo for this. Build the extractor's classpath and run a `main` that
calls `JavamopFacade.listUsedMethods(dir, false)`:

```bash
R=<reactor-root>
cd $R/rvsec/rvsec-mop-extractor && mvn -q -DskipMopAgent dependency:build-classpath \
  -Dmdep.outputFile=/tmp/cp.txt -o
# then compile a main printing
# className,name,parameters,signature,includeSubtypes,nameIsPattern,ownerFromImplicitSeed
```

**Parsing caveat**: `parameters` contains commas and is *not* quoted, so `csv.DictReader` breaks.
Use a line regex:
`^([^,]+),([^,]+),(\([^)]*\)),"(.*)",(true|false),(true|false),(true|false)$`.
