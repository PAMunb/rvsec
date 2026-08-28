# gh69 — measured before/after of the extractor

Measured 2026-08-28. The **before** side is not a reconstruction from memory: the three
pre-change source files (`MopMethod.java`, `UsedJcaMethodsVisitor.java`, `JavamopFacade.java`)
were restored from `git show HEAD:` into a scratch tree, compiled against the same dependency
set, and placed ahead of the rebuilt fat jar on the classpath so they shadow the new classes.
Both sides therefore parse the same corpus with the same parser, and differ only in the visitor.

`before_*.csv` carries `className,name,parameters,signature`; `after_*.csv` adds the two new
flag columns.

## Totals

| spec set | before (sig / pairs / owners) | after (sig / pairs / owners) |
|---|---|---|
| `jca` (frozen ruler) | 120 / 68 / 22 | **120 / 68 / 22** — unmoved |
| `jca_android` (production successor) | 207 / 113 / 44 | 209 / 115 / 46 |
| `generic_new` (verification fixture) | **0 / 0 / 0** | 72 / 68 / 21 |

`generic_new` under the `+`-aware owner key `(className, includeSubtypes, methodName)` holds
**69** pairs; 68 is the `+`-blind count, where `Iterator.next` and `Iterator+.next` collapse.
The change artefacts quote 67 for the `+`-blind key — an arithmetic slip: the pre-constructor
figure was 66 and the two constructor pairs add 2, so 68. The `ServerSocket` constructor pair
does not merge with the `ServerSocket+` entries, whose method names are `accept`, `bind` and
`setSoTimeout`.

## `jca`: the delta is exactly `new` → `<init>`, and nothing else

Verified row-by-row: applying `new → <init>` to the 120 before-rows yields a set **equal** to
the 120 after-rows. Every parameter list and every signature string is unchanged. The 11 owners
that flip are exactly the ones enumerated in the change:

```
java.security.KeyPair                        javax.crypto.spec.IvParameterSpec
java.security.SecureRandom                   javax.crypto.spec.PBEKeySpec
javax.crypto.CipherInputStream               javax.crypto.spec.PBEParameterSpec
javax.crypto.CipherOutputStream              javax.crypto.spec.SecretKeySpec
javax.crypto.spec.DHGenParameterSpec         javax.xml.crypto.dsig.spec.HMACParameterSpec
javax.crypto.spec.GCMParameterSpec
```

Those 18 signature rows had been emitted all along under the name `new`, which no Soot method
carries — so the frozen ruler had never counted a constructor call site, `new SecretKeySpec(...)`
included.

## `jca_android`: +2, both of them the subtype owners

After normalising `new → <init>` on the before side, the diff is two added rows and none
removed:

```
java.security.Key#getEncoded        "public byte[] Key+.getEncoded()"
javax.crypto.SecretKey#getEncoded   "public byte[] SecretKey+.getEncoded()"
```

These are the two `+` pointcuts the production set declares. They loaded zero targets before.

## `generic_new`: 0 → 72, with 0 unresolved owners

The headline claim, measured rather than asserted. Zero owners are skipped, which holds only
because `CharSequence_NotInSet.mop` gained its `import java.util.*;` (task 1.0b) — without it
its `Set+` owner resolves to nothing and coverage drops to 23/27 specs.

## Unresolved owners

`String` remains skipped in both JCA sets and is now **logged** by name rather than dropped in
silence (RISK-013 scope boundary (c)). It is the only unresolved owner in either set.
