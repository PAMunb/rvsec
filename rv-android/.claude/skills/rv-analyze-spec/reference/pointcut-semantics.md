# What the weaver actually matches

## Contents

- [Why this file exists](#why-this-file-exists)
- [The matching rules, one by one](#the-matching-rules-one-by-one)
- [What follows from all this](#what-follows-from-all-this)
- [Fusion patterns, and the one that is impossible](#fusion-patterns-and-the-one-that-is-impossible)
- [Verifying a pointcut instead of asserting it](#verifying-a-pointcut-instead-of-asserting-it)
- [A worked verification](#a-worked-verification)

Paths are relative to
`$RVSEC_HOME/rvsec/rvsec-android/rvsec-instrumentation-dexlib2/pointcut-engine/`.

## Why this file exists

The `.mop` files are written in AspectJ syntax, but on Android they are not woven by AspectJ.
The DEX-native instrumenter reimplements a subset of the pointcut language in
`PointcutMatcher`, and what that subset does and does not cover determines which
specifications are expressible at all.

The subset is larger than people assume. That matters, because the generator's event ceiling
(see `generator-pipeline.md`) makes every event expensive, and a pointcut that can cover
several method overloads exactly is the main way to buy headroom.

## The matching rules, one by one

All in `src/main/java/br/unb/cic/rv/pointcut/PointcutMatcher.java`, method `matchCall`.

**Owner** (`:324-347`). Exact descriptor equality by default. Written `T+`, it matches `T` or
any subtype, resolved through `InheritanceResolver`. There is also a CPS-aware fallback for
Kotlin state machines, where the call was lifted into a continuation class.

**Method name** (`:349-351`). Exact equality, unless the pattern ends in `*`, which makes it a
prefix glob (`nameMatches`, `:538-543`). This is why `update` never matches `updateAAD`.

**Return type** (`:353-368`). Exact descriptor equality, unless the pattern is `*`, which
matches anything. **This discriminates overloads** — it is what separates
`byte[] doFinal(byte[], int, int)` from `int doFinal(byte[], int, int, byte[])` — and it is
the most under-used lever in the whole language.

**Parameter types** (`:370-397`). Positional. For each position, either exact descriptor
equality, or — when the position carries a trailing `+` — `InheritanceResolver.isAssignableFrom`.

**Arity** (`:371-375`). Exact, equal to the pattern's head. If the pattern ends in `..`
(`cp.varargs()`), the actual arity must merely be *at least* the head size.

**`Object+`** deserves its own note. `InheritanceResolver.isAssignableFrom`
(`InheritanceResolver.java:63-72`) has a fast path: when the supertype is `java.lang.Object`,
it returns `!isPrimitive(subFqn)`. So `Object+` matches **any reference type and rejects
primitives**. This is covered by a named invariant, **INV-INS-86**, with tests in
`src/test/java/br/unb/cic/rv/pointcut/PointcutMatcherTest.java`:

- `callParamSubtypeMarkerMatchesSubclass` — `getInstance(String, Object+)` must match
  `getInstance(String, Provider)`.
- `callParamSubtypeMarkerRejectsPrimitive` — the same pattern must reject
  `getInstance(String, int)`.

`args(...)` is matched separately (`matchArgs`, `:269-306`) with the same positional,
subtype-aware semantics; a `null` position (a binding name) or `*` accepts any single
argument, and a trailing `..` accepts any tail.

## What follows from all this

> **Overload granularity is free at weave time.** A single pointcut can cover several
> overloads exactly, and the matcher will resolve them for you. So an event earns a slot in
> the alphabet only if it carries a **distinct binding** or a **distinct body**. Splitting
> purely by method signature buys nothing and costs a bit of the exponent.

Two consequences worth stating explicitly, because both have been got wrong before.

A wildcard pointcut is not automatically a fidelity defect. When the CrySL rule itself writes
an anonymous argument — `g2: getInstance(transformation, _)` — the wildcard is the *faithful*
translation. Read the rule before flagging the `.mop`.

And a fused pointcut is not automatically sloppiness. It may be a deliberate workaround for
the event ceiling. `git log --follow` on the specification, and compare event counts across
revisions.

## Fusion patterns, and the one that is impossible

**Fuse within an arity with `Object+`.** Positions that vary in type across the overloads
become `Object+`; the event body discriminates with `instanceof`. The body is ordinary Java,
so this is entirely legal.

```java
// init(int, Object+, Object+)  covers  (int, Key, SecureRandom),
//                                      (int, Key, AlgorithmParameterSpec),
//                                      (int, Key, AlgorithmParameters),
//                                      (int, Certificate, SecureRandom)
if (third instanceof SecureRandom)                 { /* randomized[ranGen]  */ }
else if (third instanceof AlgorithmParameterSpec)  { /* preparedIV / GCM    */ }
else if (third instanceof AlgorithmParameters)     { /* preparedAlg         */ }
```

**Fuse a tail with `..`.** When the overloads share a positional head and every clause reads
only that head, a trailing `..` collapses them.

```java
// byte[] doFinal(byte[], ..)   covers  doFinal(byte[])  and  doFinal(byte[], int, int)
// and NOT doFinal(), because varargs still requires arity >= 1
```

**Use the return type to keep neighbours out.** `int update(byte[], int, int, byte[], ..)`
covers exactly the two `int`-returning updates and cannot reach the `byte[]`-returning ones.

**What is impossible: fusing across arities when you need to bind a positional argument.**
To bind a third argument the pointcut must be `args(a, b, third, ..)`, which requires arity
≥ 3 — so a two-argument overload stops matching and falls out of the automaton entirely. A
disjunctive pointcut where one branch leaves a binding unbound is illegal. And you cannot
recover the argument in the body, because the event body is compiled out of the advice into a
static method of the monitor, so `thisJoinPoint` is not available (see
`generated-artifacts.md`).

So: binding anything new costs at least one new event. Plan the alphabet accordingly.

## Verifying a pointcut instead of asserting it

Never state what a pointcut matches. Run it.

`scripts/PointcutBudget.java` builds a synthetic DEX call site for every member of a real
class — taken from `android.jar`, not from memory — and runs the production `PointcutMatcher`
against each candidate pointcut, printing the matched set. `scripts/README.md` has the compile
and run recipe.

Two properties to check on the result:

- **Coverage** — the union of the candidates covers every overload the rule names.
- **Disjointness** — no overload is matched by two candidates. Overlap is exactly what makes
  one call take two transitions.

And always include the *neighbouring* members in the fixture set — the ones with similar names
or shapes (`updateAAD`, `unwrap`, `getIV`) — to confirm nothing leaks.

## A worked verification

Candidate alphabet for `javax.crypto.Cipher`, checked against all 28 members published by
`android-30/android.jar`. Output of `PointcutBudget`, verbatim:

```
CURRENT g1/g3  public static Cipher Cipher.getInstance(String)            -> [G1]
CURRENT g2     public static Cipher Cipher.getInstance(String, Object+)   -> [G2, G3]
CURRENT i1     public void Cipher.init(int, Certificate, ..)              -> [i1, i2]
CURRENT i2     public void Cipher.init(int, Key, ..)                      -> [i3, i8, i4, i6, i5, i7]
CURRENT f2     public byte[] Cipher.doFinal(..)                           -> [f1, f2, f4]

PROP  G        public static Cipher Cipher.getInstance(String, ..)        -> [G1, G2, G3]
PROP  I2       public void Cipher.init(int, Object+)                      -> [i3, i1]
PROP  I3       public void Cipher.init(int, Object+, Object+)             -> [i8, i4, i5, i2]
PROP  I4       public void Cipher.init(int, Key, Object+, SecureRandom)   -> [i6, i7]
PROP  U12      public byte[] Cipher.update(byte[], ..)                    -> [u1, u2]
PROP  U34      public int Cipher.update(byte[], int, int, byte[], ..)     -> [u3, u4]
PROP  U5       public int Cipher.update(ByteBuffer, ByteBuffer)           -> [u5]
PROP  W        byte[] Cipher.wrap(Key)                                    -> [w]
PROP  F1       public byte[] Cipher.doFinal()                             -> [f1]
PROP  F24      public byte[] Cipher.doFinal(byte[], ..)                   -> [f2, f4]
PROP  F3       public int Cipher.doFinal(byte[], int)                     -> [f3]
PROP  F56      public int Cipher.doFinal(byte[], int, int, byte[], ..)    -> [f5, f6]
PROP  F7       public int Cipher.doFinal(ByteBuffer, ByteBuffer)          -> [f7]
```

Read the two halves against each other. The `CURRENT` rows are a diagnosis: `doFinal(..)`
matches `f1`, `f2` **and** `f4`, so a plain `doFinal()` call takes two transitions (its own
`f1` event and this one) and the rule's `f4` has no event of its own — one pointcut, two
defects, neither visible in the `.mop`.

The `PROP` rows are a design, verified: the three `init` candidates partition all eight
overloads with no overlap; the five `doFinal` candidates partition all seven; nothing reaches
`updateAAD`, `unwrap` or `getIV`. Thirteen pointcuts, fourteen events (`G` carries two, one
for a valid transformation and one for an invalid one), covering an API that the rule
describes with twenty-four.
