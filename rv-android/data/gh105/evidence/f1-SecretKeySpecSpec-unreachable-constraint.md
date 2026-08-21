# SecretKeySpecSpec — the two twins, measured (gh105 task 3.4)

Two results, one per fused pair. The first is the payoff; the second is the reason
this task closes without the INV-INS-144 violate trace its sibling tasks all have.

## `c3` → `c1`: two reports become one

The harness classified `SecretKeySpecSpec-badalg.txt` as `moved` — the accusation
changes event, `c3` → `c1`, and keeps `SECRETKEYSPEC-CONSTR-00`. As in task 3.3, that
undercounts: `gh104_diff_harness.py` records one envelope per dispatcher call, and both
of the pre-image's reports come from the same call to `SecretKeySpecSpec_c3Event`.
Counting the whole `ErrorCollector` against the two snapshots the harness generated:

| construction | A (pre-image) | B (fused) |
|---|---|---|
| `new SecretKeySpec(km, "AES")` with unrandomised `km` | **2** — `SECRETKEYSPEC-CONSTR-00 ev=c3` and `SECRETKEYSPEC-ORDER-00 ev=c3` | **1** — `SECRETKEYSPEC-CONSTR-00 ev=c1` |

The second report was an `InvalidSequenceOfMethodCalls` about a call sequence the api30
rule accepts — `ORDER Cons`, and `Cons := c1 | c2` — emitted because `c3` sat outside
the `ere` and the generator gives an absent event a transition row into the fail state.
The method is the one in
`data/gh105/evidence/f1-IvParameterSpec-report-count.md`, which also carries the
program.

## `c4` → `c2`: the accusing half is unreachable

`c4` was the exact complement of `c2` over the rule's only CONSTRAINTS clause,
`length(keyMaterial) >= off + len`. It can never fire. The events are
`after ... returning` advices, and `SecretKeySpec(byte[], int, int, String)` rejects
every combination the clause rejects, by throwing, before it can return — JDK 21
`java.base/javax/crypto/spec/SecretKeySpec.java:148-168` checks `offset < 0`,
`len < 0` and `key.length - offset < len`, in that order. Executed against a 32-byte
array:

| `offset` | `len` | outcome |
|---|---|---|
| 0 | 33 | `IllegalArgumentException` |
| 16 | 32 | `IllegalArgumentException` |
| -1 | 32 | `ArrayIndexOutOfBoundsException` |
| 0 | -1 | `ArrayIndexOutOfBoundsException` |
| 33 | 1 | `IllegalArgumentException` |

```java
new SecretKeySpec(new byte[32], offset, len, "AES");   // one call per row
```

So `SECRETKEYSPEC-CONSTR-01` is a code in `codes.csv` that no execution emits, and no
trace can be written that exercises it. Task 3.4 therefore closes with the satisfying
half of the pair (`SecretKeySpecSpec-offset.txt`) and this stated impossibility in
place of the violating half — an exception to INV-INS-144 that is measured rather than
assumed. The fusion's behavioural delta on that pair is zero by construction; what
changes is that a call the clause would reject is now inside the automaton instead of
outside it.

Two things follow, and neither is repaired here. `IvParameterSpec` carries the same
shape (task 3.3, where the offset/length half of `c2`'s guard is unreachable for the
same reason), so this is a property of transcribing an API's own argument validation
as a CrySL constraint, not a one-off. And a code that can never be emitted is worth
knowing about when the set's codes are audited: it is not dead specification text —
it states a clause the oracle states — but it will never appear in any measurement.
