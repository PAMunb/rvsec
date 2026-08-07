# From a CrySL rule to a `.mop`, under a budget

## Contents

- [Reading the rule](#reading-the-rule)
- [The binding profile](#the-binding-profile)
- [The alphabet-budget method](#the-alphabet-budget-method)
- [A full worked example: `Cipher`, 24 → 14](#a-full-worked-example-cipher-24--14)
- [What the budget does not fix](#what-the-budget-does-not-fix)

## Reading the rule

A generated CrySL rule (`$WS/MetaCrySL/generated/api30/*.cryptsl`) has five parts that matter
here.

**`OBJECTS`** names and types every argument the rule will refer to. The names are load-bearing
and are not interchangeable: in the `Cipher` rule, `params` is an `AlgorithmParameterSpec` and
`param` is an `AlgorithmParameters`, and the `REQUIRES` gives each a *different* predicate.

**`EVENTS`** declares one event per method signature, then defines aggregates over them:

```
i4: init(encmode, key, params);
IWOIV := i1 | i2 | i3 | i8;
Inits := IWOIV | IWIV;
```

Two habits here. First, **an `_` is an anonymous argument** — `g2: getInstance(transformation, _)`
means the rule does not distinguish the overloads, so a wildcard pointcut is the *faithful*
translation and must not be flagged as a divergence. Second, note which events the rest of the
rule actually quantifies over.

**`ORDER`** is the sequencing property, and it almost always mentions only the *aggregates*.
`Gets, Inits+, w+ | (FINWOU | (updates+, DOFINALS))+` never says `i4`. This is why fusing
events is lossless for the automaton: what fusion costs is always the bindings, never the
language.

**`REQUIRES` / `ENSURES` / `NEGATES`** are the predicate clauses. Each names an argument, and
that argument is what the `.mop` event must bind. These are the clauses that make an event
worth its slot.

**`CONSTRAINTS`** are value constraints — allow-lists over transformation parts, `noCallTo`,
`callTo`. Some are expressible as conditions, some are not; record the ones you leave out.

## The binding profile

The central artefact of the analysis. One row per rule event: which clauses mention it, and
which arguments those clauses need bound.

For `Cipher`:

| clause | argument | rule events that bind it |
|---|---|---|
| `REQUIRES generatedKey[key, …]` | `key` | i3 i4 i5 i6 i7 i8 |
| `REQUIRES randomized[ranGen]` | `ranGen` | i2 i6 i7 i8 |
| `REQUIRES preparedIV[params]` / `preparedGCM[params]` | `params` (`AlgorithmParameterSpec`) | i4 i6 |
| `REQUIRES preparedAlg[param, …]` | `param` (`AlgorithmParameters`) | i5 i7 |
| `REQUIRES !macced[_, plainText]` | `plainText` | f2 f4 f5 f6 |
| `ENSURES encrypted[…]` | output + input | u1–u5, f1–f7 |

Collapse the rows. Eight `init` events, but only **five distinct binding profiles**: nothing,
`{ranGen}`, `{key}`, `{key, params}`, `{key, param}`, and the combinations with `ranGen`. That
collapse is where the budget comes from.

The rule for fusion follows directly:

> Two events may share a slot when one pointcut matches exactly their overloads and binds
> every argument each of them needs, **at the same position**. Where the clause differs, an
> `instanceof` in the body recovers it.

And the hard limit: **fusion across arities is impossible when you need a positional binding.**
`args(a, b, third, ..)` requires arity ≥ 3, so a two-argument overload stops matching. Group
candidates by arity first.

## The alphabet-budget method

1. **Count and price.** Current `n`, and `n` for a literal 1:1 transcription. Apply
   `n × (2ⁿ − 1)` and compare against the ceiling of 17 (see `generator-pipeline.md`). If the
   literal transcription is over, say so at once — it is not a matter of patience.

2. **Get the real API.** From `android.jar`, not from the rule and not from memory:

   ```bash
   javap -classpath $ANDROID_HOME/platforms/android-30/android.jar javax.crypto.Cipher \
     | grep -E 'getInstance|init|update|doFinal|wrap|getIV'
   ```

3. **Build the binding-profile table** and collapse identical rows.

4. **Group by arity, then propose an alphabet.** Within an arity, positions that vary in type
   become `Object+`; the return type keeps unrelated overloads out; a trailing `..` collapses a
   shared head.

5. **Verify every candidate against the real API** with `scripts/PointcutBudget.java`. Two
   properties must hold: the union covers every overload the rule names, and the candidates are
   **pairwise disjoint**.

6. **Check for leakage** — include the neighbouring members (`updateAAD`, `unwrap`, `getIV`) in
   the fixture set and confirm nothing matches them.

7. **Generate end to end and measure.** Placeholder bodies are fine; say so when reporting.

## A full worked example: `Cipher`, 24 → 14

The rule declares 8 `init` events and 7 `doFinal` events. A literal transcription is **24
events**, which cannot be generated at all. The specification as it stood was **17** — exactly
at the ceiling, with no room for the one event needed to fix a known defect.

The budget produced this alphabet, every line verified with the matcher against all 28 members
of `javax.crypto.Cipher` in `android-30/android.jar`:

| # | pointcut | covers | binds |
|---|---|---|---|
| 1–2 | `Cipher getInstance(String, ..)` | g1, g2 (all 3 overloads) | `transformation`; two events, one for a valid transformation and one for an invalid one |
| 3 | `void init(int, Object+)` | i1, i3 | `key` via `instanceof` |
| 4 | `void init(int, Object+, Object+)` | i2, i4, i5, i8 | `key`, plus `ranGen` / `params` / `param` via `instanceof` on the third |
| 5 | `void init(int, Key, Object+, SecureRandom)` | i6, i7 | `key`, `ranGen`, and `params`/`param` via `instanceof` |
| 6 | `byte[] update(byte[], ..)` | u1, u2 | output = return value |
| 7 | `int update(byte[], int, int, byte[], ..)` | u3, u4 | output = arg 3 |
| 8 | `int update(ByteBuffer, ByteBuffer)` | u5 | |
| 9 | `byte[] wrap(Key)` | w | |
| 10 | `byte[] doFinal()` | f1 | |
| 11 | `byte[] doFinal(byte[], ..)` | f2, f4 | `plainText` |
| 12 | `int doFinal(byte[], int)` | f3 | |
| 13 | `int doFinal(byte[], int, int, byte[], ..)` | f5, f6 | `plainText`, output |
| 14 | `int doFinal(ByteBuffer, ByteBuffer)` | f7 | |

**14 events against a ceiling of 17**, generated end to end in 6.1 s and 1.0 GB — against 53.5 s
and 3.3 GB for the 17-event version it replaces. And it binds *every* argument the rule's
clauses quantify over, so nothing is unreachable for reasons of granularity any more.

Two defects fall out of the same table without costing a slot:

- The old `byte[] doFinal(..)` matched `f1`, `f2` **and** `f4` — a plain `doFinal()` took two
  transitions, and the rule's `f4` had no event of its own. Candidates 10 and 11 are disjoint.
- The old invalid-transformation event was `getInstance(String)`, arity 1, so
  `getInstance("DES/ECB/NoPadding", provider)` fired nothing at all and the unsafe algorithm was
  later misreported as a sequence violation. `getInstance(String, ..)` closes it.

The cost, and it is a real design decision rather than a free win: discrimination between
overloads moves out of the pointcut and into an `instanceof` in the event body. The predicate
reads are identical and the `ORDER` never distinguished the events anyway — but a design
principle that says "one event per rule event" has to be restated as "one event per binding
profile" for this to be legitimate. Make that explicit rather than quietly assuming it.

## What the budget does not fix

Keep these separate from granularity when reporting, or the budget will look like it solved
more than it did:

- **A missing `Property` constant** is a capability gap, not a granularity gap. `preparedAlg`
  needs a constant and a reader regardless of how the alphabet is spent.
- **A predicate written over the wrong argument** stays broken. `!macced[_, plainText]` asks
  about the data that was MACed; if the `Mac` specification records only the output, the clause
  is unreadable even once `plainText` is bound. Binding was never the whole problem.
- **Value constraints** (`noCallTo`, `callTo`, `neverTypeOf`) are a different mechanism
  entirely. Record them as out of scope explicitly.
- **Aggregate membership.** If a fused event spans two of the rule's aggregates — one candidate
  above covers both `IWOIV` and `IWIV` members — note it. It is recoverable with the same
  `instanceof`, but only if someone knows it needs recovering.
