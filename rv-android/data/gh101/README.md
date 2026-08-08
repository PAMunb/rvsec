# The records the JCA specification sets are checked against (gh101)

Seven data files here, all committed. Six are regenerable from the specifications;
the seventh, the omission list, is written by hand and checked against them. They
exist because the two JCA
specification sets stopped being interchangeable: `jca` produced published
measurements and is frozen at commit `7e7acb69`, so every correction lands in
`jca_android` alone and the sets now diverge outside their allow-lists on
purpose. What that costs is the property the sets used to have — a difference in
outcome between them was once attributable to the platform allow-list and nothing
else. These records are what keeps the difference at least *nameable*.

| file | what it holds | produced by |
|---|---|---|
| `predicate_inventory_jca.csv` | every `ExecutionContext` site in the frozen set — the freeze baseline | `scripts/gh101_predicate_inventory.py` |
| `predicate_inventory_jca_android.csv` | the same for the derived set — the working baseline | same |
| `predicate_edges.csv` | one row per CrySL predicate clause, with whether the set implemented it **before the repairs** — the yardstick Groups 3 to 5 were counted against, kept as authored | `scripts/gh101_predicate_edges.py` |
| `edge_counts_per_file.csv` | per `.mop`, how many edges it had to close — same baseline | same |
| `conformance_record.csv` | the verdict of each of the 23 derived specifications against its generated API 30 rule | `scripts/gh101_conformance_check.py` |
| `divergence_record.csv` | every hunk by which the sets differ, with its reason | `scripts/gh101_divergence_record.py` |
| `predicate_omissions.csv` | every edge the derived set leaves open, with the reason it is not closable here | written by hand, checked by `scripts/gh101_predicate_pairing_check.py` |

The gates that consume them live in `tests/parity/test_gh101_specset_gates.py`.

Two prose records sit beside them. `frozen_set_debt.md` lists what the `jca` set
knowingly retains — each entry a repair made in the derived set and deliberately
not made there — so a set kept reproducible is not mistaken for a set kept
correct. Its section "What Group 8 measured" carries the one measurement in this
change that was taken on a device: two arms differing only in the specification
set, and the correction it forced to an attribution the record had been making
since Group 3.

`algorithm_naming.md` is the other, and is prose rather than data: it records
the gap between what a specification compares and what the platform resolves —
case, spelling variants and provider aliases — measured from the campaign and
from the corpus sources, together with the two rule defects the same sweep
surfaced and the design that would close the gap properly. Only its smallest part
is repaired in this change.

## The predicate inventory, before the repairs

85 sites in each set — 49 writes, 27 reads, 9 removals — all in `.mop`, none in
Java. The two inventories are identical in every column but `line`: the same
properties, in the same events, with the same snippets. Line numbers shift only
because the derivation's allow-list edits changed the length of ten files. (Task
1.2 anticipated the two differing "modulo the directory prefix"; the `file`
column carries no prefix, so the actual difference is line numbering, and the
substantive claim — the derivation did not touch the predicate graph — holds
exactly.)

Sorting the 23 `Property` constants by how they are used reproduces §4.2 of
`docs/20260806_grafo_predicados_e_pcd_dexlib2.md` independently:

| class | n | constants |
|---|---:|---|
| written **and** read — a live edge | 3 | `GENERATED_KEY`, `GENERATED_PUBLIC_KEY`, `RANDOMIZED` |
| written, never read | 18 | `DIGESTED`, `ENCRYPTED`, `GENERATED_KEY_MANAGERS`, `GENERATED_KEY_PAIR`, `GENERATED_KEY_STORE`, `GENERATED_MAC`, `GENERATED_TRUST_MANAGER`, `GENERATE_SSL_CONTEXT`, `GENERATE_SSL_ENGINE`, `PREPARED_DH`, `PREPARED_GCM`, `PREPARED_HMAC`, `PREPARED_IV`, `PREPARED_PBE`, `SIGNED`, `SPECCED_KEY`, `VERIFIED`, `WRAPPED_KEY` |
| read, never written | 1 | `GENERATED_PRIVATE_KEY` |
| neither — only removed | 1 | `GENERATED_TRUST_MANAGERS` |

**20 of 23 constants do not function as an edge.** The inventory also confirms
the substitution the graph is supposed to lean on is half-built: 19
`setObjectAsInAcceptingState` and 6 `unsetObjectAsInAcceptingState` calls, and
zero readers of `isInAcceptingState` or `hasEnsuredPredicate` in any `.mop`.

## The predicate inventory, after the repairs (task 7.4)

Both inventories were regenerated once every edit had landed. The frozen one is
**identical to its Group 1 baseline byte for byte**, which is the freeze's second
witness: the specifications it inventories were not touched, so neither is the
record of them. The derived one grew from 85 sites to **127 — 58 writes, 56
reads, 13 removals** — and every difference belongs to a task of this change:

| difference | files | task |
|---|---|---|
| 29 reads added, closing a `REQUIRES` that had no site | `CipherSpec`, `MacSpec`, `SSLContextSpec`, `KeyManagerFactorySpec`, `TrustManagerFactorySpec`, `KeyPairSpec`, `KeyPairGeneratorSpec`, `KeyGeneratorSpec`, `SignatureSpec`, both stream specifications | 3.2, 4.1, 4.6, 4.7, 4.8, 4.9, 5.1, 5.1b |
| 12 writes added, closing an `ENSURES` | `CipherSpec`, `KeyManagerFactorySpec`, `KeyPairSpec`, `KeyStoreSpec`, `MacSpec`, `SecretKeySpecSpec`, `TrustManagerFactorySpec` | 4.1, 4.8, 4.9, 5.1, 5.1b |
| 4 removals added, closing a `NEGATES` | `KeyManagerFactorySpec`, `KeyStoreSpec`, `SecretKeySpec` | 4.1, 4.8 |
| 2 writes moved to the right constant | `KeyPairSpec` (`gpr` wrote the public-key constant), `TrustManagerFactorySpec` (`gtm1` wrote the key-manager one) | 4.1, 4.9 |
| 3 writes removed with the events that carried them | `CipherSpec` `u2`, `u4`, `f6` — dropped by the alphabet re-budget, their binding profiles duplicating `u1`, `u3` and `f5` (D-S11) | 4.6 |

Attribution is not a matter of reading: each of those sites lives inside a hunk
of the set diff, and every hunk carries an entry in `divergence_record.csv`
naming the task that introduced it (INV-INS-109 b).

Sorted the same way as the table above, the derived set's 25 constants now read:

| class | n | constants |
|---|---:|---|
| written **and** read — a live edge | 14 | `ENCRYPTED`, `GENERATED_CIPHER`, `GENERATED_KEY`, `GENERATED_KEY_MANAGERS`, `GENERATED_KEY_STORE`, `GENERATED_PRIVATE_KEY`, `GENERATED_PUBLIC_KEY`, `GENERATED_TRUST_MANAGERS`, `MACED`, `PREPARED_DH`, `PREPARED_GCM`, `PREPARED_HMAC`, `PREPARED_IV`, `RANDOMIZED` |
| written, never read — **each one recorded** | 11 | `DIGESTED`, `GENERATED_KEY_PAIR`, `GENERATED_MAC`, `GENERATED_TRUST_MANAGER`, `GENERATE_SSL_CONTEXT`, `GENERATE_SSL_ENGINE`, `PREPARED_PBE`, `SIGNED`, `SPECCED_KEY`, `VERIFIED`, `WRAPPED_KEY` |
| read, never written | 0 | — |
| neither — only removed | 0 | — |

3 live edges became 14. The two classes that were defects by construction are
empty: nothing is read without a writer, which would report on every conforming
call, and nothing is only removed.

## The omission list, and the guard that reads it (tasks 7.1, 7.2)

`predicate_omissions.csv` is the other half of INV-INS-111. A constant written
and never read is a silent defect — the `ENSURES` side of a clause transcribed
and the `REQUIRES` side not — unless there is a reason it cannot be paired here,
and then the reason is what the file holds. Two kinds of entry, because the
graph has two ways of leaving an edge open:

| kind | n | what it is |
|---|---:|---|
| `constant-write-no-read` | 11 | a `Property` constant that exists and is written, with no reader |
| `predicate-no-constant` | 9 | a CrySL predicate for which no constant was added at all — the eight of task 5.1d, plus `generatedMessageDigest` from task 4.3 |

Both kinds live in one file on purpose: they are omissions from the same graph,
and splitting them across two would let one drift from the other.

The eleven fall into three reasons, and none of them is taste:

- **Terminal in both anchors** (`DIGESTED`, `GENERATE_SSL_CONTEXT`,
  `GENERATE_SSL_ENGINE`, `SIGNED`, `VERIFIED`, `WRAPPED_KEY`,
  `GENERATED_KEY_PAIR`): the predicate is ensured and no rule in either CrySL
  corpus requires it. A reader would have to be invented rather than transcribed.
- **The consuming rule has no `.mop` here** (`PREPARED_PBE` — `AlgorithmParameters`;
  `SPECCED_KEY` — `SecretKeyFactory` and `KeyFactory`): D-S14's criterion seen
  from the producing side.
- **The clause makes the place anonymous** (`GENERATED_MAC`): the only consumer
  of `macced[M, D]` is the `Cipher` rule's `!macced[_, plainText]`, which reads
  the second place alone — `MACED`, which `CipherSpec` does read (D-S13).
  `GENERATED_TRUST_MANAGER` is the same shape one level up: the API 30 rule
  ensures `generatedTrustManager` of the factory *and* of the array it returns,
  and `SSLContext` requires only the array.

`scripts/gh101_predicate_pairing_check.py` is what makes the list load-bearing
rather than decorative. It recomputes the pairing from the `.mop` files — it does
not trust the committed inventory, and fails if that inventory has gone stale —
and then fails on a constant written, unread and unlisted; on a constant read
that nothing writes, which is the false-positive trap D-S14 turns on; and on an
entry that has stopped being true, either because nothing writes the constant any
more or because something now reads it. The list cannot quietly outlive the
defect it records.

```bash
uv run python scripts/gh101_predicate_pairing_check.py
# -> 25 constant(s) written: 14 read by another specification,
#    11 recorded as deliberate omissions
```

## The edge map, and what anchors it

`predicate_edges.csv` is anchored to the **CrySL 1.5.2** corpus, not to the
generated API 30 rules, and the two anchors answer different questions. A
membership constraint is what varies with API level, so the generated rules are
the anchor for allow-lists. `ORDER`, `REQUIRES`, `ENSURES` and `NEGATES` describe
API semantics and do not vary, so the predicate graph is checked against the
corpus the specifications were translated from — which is where a translation
defect is a defect.

22 of the 23 `.mop` have a CrySL counterpart (`RandomStringPassword` has none),
carrying **84 predicate clauses: 46 `ENSURES`, 36 `REQUIRES`, 2 `NEGATES`**.

| | n |
|---|---:|
| implemented, exact constant | 43 |
| implemented under a borrowed constant (`preparedKeyMaterial` → `RANDOMIZED`) | 2 |
| a site exists but names a neighbouring specification's constant | 2 |
| absent | 37 |

The 37 absent split exactly as §4.5 of the investigation reports them:

| bucket | n | what closing it takes |
|---|---:|---|
| translation defect | 23 | a read, a write or a removal in one `.mop` |
| capability absent | 11 | a new `Property` constant **and** its reader |
| deliberate omission | 2 | nothing — recorded with the reason |
| inexpressible | 1 | nothing — recorded with the reason |

**One accounting difference from the investigation, and it is only wording.** The
two wrong-constant sites (`KeyPairSpec.mop:38`, `TrustManagerFactorySpec.mop:65`)
are counted here as *not* implemented, because a write that names the wrong
constant is silent at runtime. §4.4 counts them among the 38 present `ENSURES`
and §4.5 also lists them inside bucket (i) — the two cannot both hold. Under
either convention the work is the same: **36 edges to close** (23 translation
defects + 11 capability-absent + the 2 wrong constants), and 3 recorded rather
than closed.

Per group, from `edge_counts_per_file.csv`:

- **Group 3**, the two hot specifications: 5 edges (`SSLContextSpec` 3, `TrustManagerFactorySpec` 2)
- **Group 4**, `.mop` only: 20 edges
- **Group 5**, new vocabulary: 11 edges over **9** distinct constants — `preparedAlg`, `preparedOAEP`, `generatedCipher`, `preparedRSA`, `preparedDSA`, `preparedEC`, `generatedManagerFactoryParameters`, `cipheredInputStream`, `cipheredOutputStream`. `generatedCipher` accounts for three of the eleven edges and `generatedManagerFactoryParameters` for two, which is why 11 edges need 9 constants and not 11.

## The conformance verdicts

All 23 carry one, against the generated API 30 rules (INV-INS-113):

| verdict | n | which |
|---|---:|---|
| `anchored` — the rule contradicted the inherited list and the list follows the rule | 10 | `KeyGeneratorSpec`, `KeyManagerFactorySpec`, `KeyPairGeneratorSpec`, `KeyStoreSpec`, `MacSpec`, `MessageDigestSpec`, `SSLContextSpec`, `SecureRandomSpec`, `SignatureSpec`, `TrustManagerFactorySpec` |
| `uncontradicted` — the rule was checked and imposes nothing the file violates | 11 | the parameter-spec and stream specifications, `KeyPairSpec`, `SecretKeySpec`, plus `GCMParameterSpecSpec` (its list already agrees) and `SecretKeySpecSpec` (the derived rule constrains nothing) |
| `no-anchor` — no rule constrains this file, with the reason | 2 | `CipherSpec` (the constraint lives in Java, closed by Group 2), `RandomStringPassword` (no CrySL counterpart at all) |

The ten `anchored` are exactly the ten §6.1 of the tier map lists as adapted, so
the derivation's own account and this re-derivation agree file for file. No file
is `contradicted` — that is, none was left unchanged while its rule contradicts
it.

**The verdict is about conformance, not about security.** `MessageDigestSpec` is
`anchored` because it follows a rule admitting `MD5` and `SHA-1`, which the
platform publishes. The derived profile models availability, not recommendation;
a fall in reported violations under the derived set is not evidence of better
analysed code.

## The spelling variants — open, and the user's to settle

The `.mop` compares algorithm names as strings where CrySL compares algorithm
identity, so the 2022 translation listed several spellings of the same algorithm.
They are carried over unchanged, declared as translation artefacts. Whether they
are legitimate Android provider names or accidental looseness is one of the two
open questions `design.md` leaves to the user:

| file | groups that fold to one algorithm |
|---|---|
| `KeyGeneratorSpec.mop` | `HmacSHA256` `HMAC-SHA256` `HMAC/SHA256` · `HmacSHA384` `HMAC-SHA384` `HMAC/SHA384` · `HmacSHA512` `HMAC-SHA512` `HMAC/SHA512` |
| `MacSpec.mop` | the same three groups |
| `SecretKeySpecSpec.mop` | `HMACSHA256` `HMAC-SHA256` `HMAC/SHA256` · `HMACSHA384` `HMAC-SHA384` `HMAC/SHA384` · `HMACSHA512` `HMAC-SHA512` `HMAC/SHA512` |
| `MessageDigestSpec.mop` | `SHA-256` `SHA256` · `SHA-384` `SHA384` · `SHA-512` `SHA512` |

Only the canonical spelling of each group appears in a generated rule. Six
literals in `KeyGeneratorSpec` and six in `MacSpec` are outside their rule but
fold onto a member of it; three are in `MessageDigestSpec`. `SecretKeySpecSpec`
cannot be measured that way — its derived rule constrains nothing — but its list
carries the same three groups of three, and there not even the canonical
`HmacSHA256` spelling is present: all nine literals are translation spellings.

`SSLContextSpec` is a separate case and needs no verdict: its whole list is held
uppercase because the specification compares `protocol.toUpperCase()`, so
`TLSV1.2` is a mechanical fold of the rule's `TLSv1.2`, not an added alias.

## The divergence record

106 hunks over the derived set. Each entry names the hunk by a digest of its
changed lines, so an edit elsewhere in the same file does not invalidate it,
while changing what the hunk contains does: the reason recorded for the old
content has not been shown to hold for the new.

| kind | n | what it is |
|---|---:|---|
| `allow-list` | 12 | the derivation acting as it may — platform membership constraints |
| `layer-2-repair` | 51 | authoring defects and the `CipherSpec` / `MacSpec` alphabet re-budgets |
| `predicate-graph` | 42 | an edge of the CrySL graph given a reader, a writer or a removal |
| `cipher-import` | 1 | `CipherSpec.mop`'s static import redirected to the derived tables |

The 12 `allow-list` hunks are the state before any of this change's edits; the
other 94 are repairs confined to the derived set, which is the whole reason the
parity check was replaced by an enumeration (D-S7).

## What identity keying changes in the frozen set (tasks 4b.3, 4b.4)

`ExecutionContext` is shared by both sets, and task 4b.1 re-keyed its three
stores by object identity so they agree with the monitor index, which has always
keyed by `System.identityHashCode` confirmed with `==`. That is a repair to the
runtime rather than to specification content, so it is admissible under the
freeze (D-S10) — but it changes what the **frozen** set reports, and the honest
form of that is an enumeration, not an assurance.

Of the frozen set's **27 reads**, **8 change their answer**. The dividing line is
whether the object's `equals` is value-based:

| read | site | object | why it changes |
|---|---|---|---|
| `CipherSpec.i2` ×3 | `CipherSpec.mop:70,71,72` | `java.security.Key` | `SecretKeySpec.equals` compares key material and algorithm |
| `MacSpec.i1` | `MacSpec.mop:47` | `java.security.Key` | same |
| `MacSpec.i2` | `MacSpec.mop:59` | `java.security.Key` | same |
| `SecretKeySpec.e1` | `SecretKeySpec.mop:25` | `SecretKey` | same |
| `RandomStringPasswordSpec.gb` | `RandomStringPassword.mop:21` | `String` | value equality |
| `RandomStringPasswordSpec.vo` | `RandomStringPassword.mop:14` | `Object` | statically `Object`; affected whenever the application passes something value-equal |

The remaining **19** are over `byte[]` or `char[]`, whose `equals` is already
identity, so they cannot move: `GCMParameterSpecSpec` 2, `IvParameterSpecSpec` 4,
`PBEKeySpecSpec` 4, `PBEParameterSpecSpec` 3, `SecretKeySpecSpec` 2 and
`SecureRandomSpec` 4.

**Two corrections to D-S10's table, both in the direction of it having been a
floor rather than a ceiling.** It types the `SecureRandomSpec` seed reads as a
boxed `long` and counts them among the affected; they are over `byte[]` —
`c2`, `c3`, `setSeed2` and `setSeed3` all bind `byte[] seed` — so they are
unaffected, and listing them alongside the other rows would have made the total
nine, not the eight the same decision states. The count of 8 is right; the
composition was not.

**The direction is uniform: all eight report more, not less.** Every one of the
eight is a positive `condition(...)` guard, so under `equals` keying an object
that no monitored sequence produced could satisfy it by being equal to one that
was. Identity keying makes the guard fail instead, and a failing guard takes no
transition — so the misuse surfaces on the call that follows, as a sequence
violation. The concrete case it closes: `SecretKeySpecSpec` marks the spec it
accepted, and an application that builds a second `SecretKeySpec` with the same
material through the *violating* branch had that second one validated at
`Cipher.init` by the first one's mark.

**No shared code branches on the active specification set**, which is what makes
the repair admissible at all. `grep -rn 'specification_set\|jca_android'` over
`rvsec-core/src` returns exactly one hit, and it is a Javadoc sentence in
`AndroidCipherTransformationUtil` naming the set that class serves — no `if`, no
lookup, no state read at runtime. Which tables apply is decided by *which class a
specification imports*, statically, which is D-S3's whole point: the frozen set's
verdict cannot be changed by state set elsewhere. The criterion D-S10 states is a
prohibition on branching, not on touching.

**And the limit of what the checks establish (task 4b.4).** After 4b.1 the freeze
check still passes — the frozen paths are byte-identical to `7e7acb69` — and the
monitor generated from `jca` is byte-identical to the one generated from the same
set at the base commit. Neither is evidence that the frozen set *behaves* as it
did. `ExecutionContext` is a separate class; the generated monitor calls into it
and does not carry its internals, so a repair inside it is invisible to both
checks by construction. That is the whole reason the eight reads above are
enumerated: byte-identity is what the checks can see, and the table is what they
cannot. Closing the gap would mean re-measuring the corpus, which is an explicit
non-goal.

## The deliberate omissions, and why one of them is now closed (tasks 4.3, 5.1)

The narrative below and the two sections that follow it are the *why*; the rows
the guard reads are in `predicate_omissions.csv`, and `generatedMessageDigest` is
one of them. Neither side may drift from the other: the file is where a reason
becomes checkable, and this is where it stays readable.

Two `ENSURES` clauses were recorded rather than closed, both of the same shape —
a predicate the rule ensures **of the object itself** after its construction.
Task 5.1 closed the first of them; the second stands:

| rule | clause | what the translation wrote instead | now |
|---|---|---|---|
| `Cipher` | `ENSURES generatedCipher[this]` | `setObjectAsInAcceptingState(cipher)` in the `@match1` handler | **closed** — `CipherSpec` writes `GENERATED_CIPHER` at each of its three init events, and both stream specifications read it |
| `MessageDigest` | `ENSURES generatedMessageDigest[this]` | `setObjectAsInAcceptingState(md)` in the `@match` handler | **stands** — its consumers would be the `DigestInputStream` and `DigestOutputStream` rules, and neither has a specification in this set |

The two verdicts come from one criterion, which is the point of them: a clause is
closable when the predicate's producer **and** its consumers are all modelled by
a `.mop` here. `generatedCipher` passes; `generatedMessageDigest` does not.

The accepting-state marker is left in place in both. It is the set-wide
convention — nineteen specifications write it — so removing it from `CipherSpec`
alone would make that one file the exception without changing any behaviour.
What task 5.1 adds is the real predicate beside it, not a replacement for it.

The substitution is defensible in principle: reaching the specification's
accepting state *is* the fact the rule wants ensured, and `ExecutionContext`
carries a separate store for it. What makes them omissions rather than
translations is that the substitution is **half-built, and inert at runtime**:

```bash
MOP=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources
grep -rn 'setObjectAsInAcceptingState'   $MOP/jca_android/*.mop | grep -vc unsetObject   # 19
grep -rn 'unsetObjectAsInAcceptingState' $MOP/jca_android/*.mop | wc -l                  #  6
grep -rn 'isInAcceptingState'            $MOP/jca_android/*.mop | wc -l                  #  0
grep -rn 'hasEnsuredPredicate'           $MOP/jca_android/*.mop | wc -l                  #  0
```

The same four counts hold for the frozen set, byte for byte. So 19 specifications
write into a store that **no specification in either set ever reads**. The two
clauses are not implemented by another mechanism; they are written into a
mechanism with no consumer, and the fact they ensure is unavailable to any
`REQUIRES` that would want it.

This is why the omissions were not absolutions. Under the CrySL 1.5.2 anchor,
`CipherInputStream` and `CipherOutputStream` both `REQUIRE generatedCipher`, so
the fact `CipherSpec` declined to write was one two other specifications needed
to read. Those two edges are counted separately, in the capability-absent bucket.
Closing them without closing the `ENSURES` would have been worse than leaving
them open: a read against the inert marker fails on every execution, so each
legitimate stream construction would have been reported. That is why task 5.1
took the three edges together rather than the bucket's two.

**Two of the nine predicates in that bucket exist in only one of the two anchors,
which had to be settled before anything was added.**

`grep -l 'generatedCipher\['` over the 33 generated API 30 rules returns
**nothing**. That release's `Cipher` rule ensures only the three `encrypted[…]`
predicates, and its `CipherInputStream` rule states **no `REQUIRES` at all**,
ensuring `cipheredInputStream[is, ciph]` and stopping there. In the CrySL 1.5.2
corpus both are present: `Cipher.crysl` ensures `generatedCipher[this] after
Inits` and `CipherInputStream.crysl` requires `generatedCipher[ciph]`.

Counted over the bucket's nine predicates, by how many rules of each anchor name
each one (reproduce with the loop in §"The eight predicates Group 5 does not add"):

| constant | api30 | 1.5.2 | note |
|---|---:|---:|---|
| `preparedAlg` | 2 | 3 | |
| `preparedRSA` | 2 | 2 | |
| `preparedDSA` | 2 | 3 | |
| `cipheredInputStream` | 1 | 1 | api30 *adds* this one |
| `cipheredOutputStream` | 1 | 1 | api30 *adds* this one |
| `generatedManagerFactoryParameters` | 2 | 4 | api30 keeps the producers and drops the two factory `REQUIRES` |
| `preparedEC` | 1 | 3 | api30 keeps the `REQUIRES` in `KeyPairGenerator` and has **no `ECGenParameterSpec` rule** to produce it |
| `preparedOAEP` | **0** | 3 | |
| `generatedCipher` | **0** | 3 | |

**A first pass at this comparison was one-sided and over-reported.** Diffing only
1.5.2-minus-api30 named twelve rules as "dropping" predicates, including
`SSLContext`. The symmetric comparison shows most of those are **renames**, not
drops — `generatedKeyManagers` → `generatedKeyManager`, `generatedTrustManagers`
→ `generatedTrustManager`, `generatedTrustAnchor` →
`generatedCertPathParameters`, `generatedMessageDigest` →
`digestedInputStream`/`digestedOutputStream` — and that api30 names **more**
predicates than 1.5.2 in most rules, not fewer. The genuine one-sided losses are
`generatedCipher`, `preparedOAEP`, `wrappedKey` (`Cipher`), `preparedPBE`
(`AlgorithmParameters`), `generatedKey` (`Mac`'s `REQUIRES`), and the two factory
`REQUIRES` of `generatedManagerFactoryParameters`.

`predicate_edges.csv` is anchored to 1.5.2 on purpose, and the reason is stated
in §"The edge map": `ORDER`, `REQUIRES`, `ENSURES` and `NEGATES` describe API
semantics and do not vary with API level, so a difference there is a translation
defect rather than a platform fact. That reasoning still holds, and the api30
corpus has 33 rules against 1.5.2's 47 — it omits `OAEPParameterSpec` and
`ECGenParameterSpec` entirely, which is coverage rather than platform.

The anchor looked load-bearing and turned out not to be. Of the two predicates no
API 30 rule names, `preparedOAEP` is excluded for a reason the anchor does not
touch — nothing in this set produces it — so the choice bears on `generatedCipher`
alone. It was added under the stated 1.5.2 anchor, and the fact that the
derivation's own oracle does not ask for it is recorded here rather than passed
over.

## The eight predicates Group 5 does not add (task 5.1d)

The eight are rows of `predicate_omissions.csv`, of kind `predicate-no-constant`
— the file the pairing guard reads. What follows is the derivation of the
criterion that put them there; the numbers below are counted over
`predicate_edges.csv`, which is the Group 1 baseline and is deliberately not
regenerated, so the bucket it names stays the one the decision was taken against.

The capability-absent bucket holds **11 edges over 9 predicates**. One predicate,
`generatedCipher`, gained a constant; the other eight did not, and the reason is
mechanical rather than a matter of taste. The test is whether both ends of the
edge are modelled by a `.mop` in this set of 23 — the producer that `ENSURES` the
predicate and the consumer that `REQUIRES` it.

```bash
# the bucket, per predicate
python3 -c "
import csv,collections
rows=[r for r in csv.DictReader(open('data/gh101/predicate_edges.csv')) if r['bucket']=='capability-absent']
print(len(rows),'edges'); print(dict(collections.Counter(r['predicate'] for r in rows)))"
# -> 11 edges
# -> {'generatedCipher': 2, 'generatedManagerFactoryParameters': 2, 'cipheredInputStream': 1,
#     'cipheredOutputStream': 1, 'preparedAlg': 1, 'preparedOAEP': 1, 'preparedRSA': 1,
#     'preparedDSA': 1, 'preparedEC': 1}

# who ENSURES and who REQUIRES each, in both anchors
RULES=$WS/MetaCrySL/generated/api30
CRYSL152=$WS/CryptoAnalysis/CryptoAnalysis/src/main/resources/JavaCryptographicArchitecture
for p in preparedAlg preparedRSA preparedDSA cipheredInputStream cipheredOutputStream \
         generatedManagerFactoryParameters preparedEC preparedOAEP generatedCipher; do
  for f in $RULES/*.cryptsl $CRYSL152/*.crysl; do
    awk '/^ENSURES/,0'  "$f" | grep -q "$p\[" && echo "ENSURES  $p  $(basename $f)"
    awk '/^REQUIRES/,0' "$f" | awk '/^ENSURES/{exit}1' | grep -q "$p\[" && echo "REQUIRES $p  $(basename $f)"
  done
done
```

Which gives, crossed against the 23 specifications that exist here:

| predicate | edges | producer rule | modelled? | consumer rule | modelled? | verdict |
|---|---:|---|---|---|---|---|
| `generatedCipher` | 2 | `Cipher` | **yes** | `CipherInputStream`, `CipherOutputStream` | **yes** | **added** |
| `preparedAlg` | 1 | `AlgorithmParameters` | no | `Cipher` | yes | no producer |
| `preparedRSA` | 1 | `RSAKeyGenParameterSpec` | no | `KeyPairGenerator` | yes | no producer |
| `preparedDSA` | 1 | `DSAGenParameterSpec` | no | `KeyPairGenerator` | yes | no producer |
| `preparedEC` | 1 | `ECGenParameterSpec` | no | `KeyPairGenerator` | yes | no producer |
| `preparedOAEP` | 1 | `OAEPParameterSpec` | no | `Cipher` | yes | no producer |
| `generatedManagerFactoryParameters` | 2 | `CertPathTrustManagerParameters`, `KeyStoreBuilderParameters` | no (neither) | `KeyManagerFactory`, `TrustManagerFactory` | yes | no producer |
| `cipheredInputStream` | 1 | `CipherInputStream` | yes | *none in either anchor* | — | no consumer |
| `cipheredOutputStream` | 1 | `CipherOutputStream` | yes | *none in either anchor* | — | no consumer |

**Why "no producer" forbids adding the reader, rather than merely weakening it.**
Every read this change adds sits in an event body, never in a `condition(...)`,
so that an unsatisfied requirement is *reported* instead of silently suppressing
the transition. That is the right design and it is what makes a producerless read
unacceptable: `validate(p, o)` over a predicate nothing writes returns false on
every execution, so the specification would report a misuse for every conforming
use of `Cipher.init`, `KeyPairGenerator.initialize` and the two factories. The
open edge is a gap; the reader would be a defect.

**Why "no consumer" forbids adding the writer.** INV-INS-111 requires every
constant written to be read somewhere or recorded. Neither anchor has any rule
requiring `cipheredInputStream` or `cipheredOutputStream`, so a writer could only
ever be a write with no reader — the same shape as `SPECCED_KEY`, which is
recorded for the same reason.

**What would close the six.** Seven specifications this set does not have:
`AlgorithmParameters`, `RSAKeyGenParameterSpec`, `DSAGenParameterSpec`,
`ECGenParameterSpec`, `OAEPParameterSpec`, `CertPathTrustManagerParameters` and
`KeyStoreBuilderParameters`. Writing them is a change of its own, not a task in
this one. Two of them have no api30 rule to derive from at all
(`ECGenParameterSpec`, `OAEPParameterSpec`), so those two would also need an
anchor decision before they could be written.

**Net effect on the bucket: 2 of 11 edges closed, 9 left open and attributable.**
The third edge task 5.1 closed — `ENSURES generatedCipher[this]` — is not in this
bucket; it was carried in the deliberate-omission bucket and is recorded above.

## `randomized[lSeed]` is inexpressible, and identity keying does not rescue it (task 4.4)

The `SecureRandom` rule states `REQUIRES randomized[lSeed]` of
`s2: setSeed(lSeed)`, where `lSeed` is a `long`. It asserts **provenance** — that
this number came from a CSPRNG — over a primitive, and the predicate store holds
object references. It is recorded as inexpressible, and the reason has changed
since the record was first written, because task 4b.1 re-keyed the store by
identity.

**Under the old `equals` keying** the read would have succeeded for any `long`
numerically equal to one previously marked, whatever produced it — provenance
collapsing into value.

**Under identity keying it fails in both directions, and which one depends on the
magnitude.** A `long` bound at the read site is autoboxed there, producing a
`Long` distinct from the box created at the write site, so for values outside the
cache the read can never succeed — a report on every call, including correct
ones. For values in `−128..127`, `Long.valueOf` returns the process-wide cached
instance, so identity and equality coincide and the read succeeds for *any* equal
small value from anywhere in the process, including one no CSPRNG produced.

**And a third fact settles it independently of boxing.** Nothing in the
specification ever marks a `long`. The two primitive writes are over `int` —
`next1` over the bound `randIntInRange` and `next3` over the returned `randInt` —
and an `Integer` is neither `==` nor `equals` to a `Long`. So the clause could not
be satisfied even by a store that got boxing right.

**The unsoundness on the write side stands, narrowed.** Writing `RANDOMIZED` over
an `int` marks whatever object the autoboxing produced. For a value in the
`Integer` cache that object is shared process-wide, so one small `nextInt()`
marks every equal literal in the program — `0`, `1`, `16` — as randomised.
Identity keying removed this for large values and left it exactly as it was
inside the cache, where identity and equality are the same thing. It is confined
to `SecureRandomSpec`'s two primitive writes, and it is in the direction of
reporting **less**: a value that was never randomised validates.

## The `Cipher` alphabet, and what it costs (tasks 4.6, 4.10, 4.13)

`CipherSpec` went from **17 events to 14**, and the reason it could not instead
go to the 24 a literal transcription of the rule needs is a hard limit in the
monitor generator. It is measured, not inferred, and reproducible.

Every `(state, event)` pair a specification does not declare is sent to `fail`,
and a `.mop` with an `@fail` handler makes `fail` a category, so `FSMCoenables`
walks backwards from a state to which everything is co-reachable and records the
**full powerset of the alphabet** — exactly `n × (2ⁿ − 1)` sets:

| events | coenable sets | outcome |
|---:|---:|---|
| 14 | 229,362 | generates, **6.9 s / 1.02 GB** (this change, measured) |
| 17 | 2,228,207 | generates, **53.5 s / 3.3 GB** (the form this change replaced) |
| 18 | 4,718,574 | **`StackOverflowError`** in `EnableSet.parseSets` — nested-quantifier regex over a 184 MB string |
| 24 | 402,653,160 | **cannot be built**: the coenable string exceeds Java's maximum `String` length |

The counts were confirmed to the unit at 17 and 18. `-Xss` cannot be raised past
the launcher's `1g` — the JVM refuses to start above it on the main thread. The
notation is not a way out either: the logic repository is a rewriting system, and
`EREPlugin` rewrites into `fsm`, so `ere`, `ltl` and `ptltl` all reach the same
`FSMCoenables` — measured identical automaton, identical counts, identical
wall-clock and the identical failure at 18. And states are not the cost: the
minimised automaton has 5 states at 14, 17 and 18 alike.

**`rv-monitor` is deliberately not repaired** (D-S12). The computation produces
nothing for this family of specifications — every one of the 23 has at most one
specification parameter, so all 2,228,207 sets collapsed to a single comment line
in the generated monitor — but repairing it would raise the ceiling only to
roughly 20 events, still short of 24, and it would move the machinery the frozen
set's numbers were produced on. The ceiling is recorded as a constraint on
specification design (INV-INS-115) and the alphabet is budgeted under it.

Effect on the whole derived set, same command before and after the re-budget:

| | wall clock | peak RSS |
|---|---:|---:|
| 23 specifications, `CipherSpec` at 17 events | 1 m 15.9 s | 2.98 GB |
| 23 specifications, `CipherSpec` at 14 events | **28.6 s** | **1.67 GB** |

No specification in the derived set exceeds the ceiling: the largest is
`SecureRandomSpec` at 15 events, then `CipherSpec` at 14.

Reproducing commands — the ceiling itself, one specification timed end to end,
and the whole set:

```bash
MOP=$RVSEC_HOME/rvsec/rvsec-mop/src/main/resources
S=<scratch>            # javamop writes the .rvm into the SOURCE directory

# one specification, timed
mkdir -p $S/one && cp $MOP/jca_android/CipherSpec.mop $S/one/ && cd $S/one
$RVSEC_HOME/javamop/bin/javamop -d $S/one CipherSpec.mop
/usr/bin/time -v $RVSEC_HOME/rv-monitor/bin/rv-monitor -d $S/one $S/one/CipherSpec.rvm

# the whole set
cp $MOP/jca_android/*.mop $S/gen/specs/
$RVSEC_HOME/javamop/bin/javamop -d $S/gen/out -merge $S/gen/specs/*.mop
mv $S/gen/specs/*.rvm $S/gen/out/
/usr/bin/time -v $RVSEC_HOME/rv-monitor/bin/rv-monitor -d $S/gen/out -merge $S/gen/out/*.rvm
```

The method and the two harnesses that produced every number above live in
`.claude/skills/rv-analyze-spec/` (commit `3d093592`): `CoenableProbe` prices a
property against the production `FSMCoenables` without generating code, and
`PointcutBudget` runs the production `PointcutMatcher` over a class's real
overloads and reports coverage, overlap and leakage. The 14-event alphabet was
verified with the second against all 28 members of `javax.crypto.Cipher`
published by `android-30/android.jar`: the three `init` candidates partition all
eight overloads, the five `doFinal` candidates partition all seven, the whole set
is pairwise disjoint, and nothing reaches `updateAAD`, `unwrap` or `getIV`.

## What the re-budget does *not* fix (task 4.12)

Two clauses stay unread after `CipherSpec`'s arguments are all bound, and neither
is a granularity problem, so neither is solved by having spent slots on it.

**`preparedAlg[param, part(0,"/",transformation)]`** — a *capability* gap. The
argument is now bound: the arity-3 and arity-4 `init` events both reach an
`java.security.AlgorithmParameters` in their third position. What is missing is a
`Property` constant for `preparedAlg` and the writer that would put anything in
it. Both arrive with Group 5, and the read is then one line in an existing
`instanceof` branch.

**`!macced[_, plainText]`** — a **missing predicate**, and the one thing the
re-budget was expected to fix and does not. The rule says a `Cipher` must not
encrypt data a monitored `Mac` computed a MAC over. `macced` is two-place:
`macced[M, D]` says *M is the MAC of D*, and the `Mac` rule ensures it three
times, always MAC first. `ExecutionContext` represents one-place predicates only
— a `Set<Object>` per `Property` — so the relation had to be projected onto one
place, and `MacSpec` projected it onto the **first**, writing `GENERATED_MAC`
over the MAC it produced. The `Cipher` clause quantifies over the **second**: its
first place is `_`, so it reads *this plaintext was never MACed*. With
`plainText` now bound in `f2` and `f5`, the argument is in hand and there is no
set of MACed data to compare it against.

**Resolved: transcribe it** (D-S13, decided by the user on 2026-08-07 after the
rule text, the store's shape and the measured cost were put to them). Done in
tasks 5.1b and 5.1c: a `MACED` constant holding the second place of `macced`,
written by `MacSpec` where a MAC is actually produced, read by `CipherSpec`'s
`f2` and `f5`. `MacSpec` went from **8 events to 11** — the fused `update(..)`
split into the three that partition android-30's four overloads, and the fused
`doFinal` into the rule's `f1`, `f2` and `f3` — verified pairwise disjoint with
`PointcutBudget` and generating with the rest of the set in 28.3 s. The whole
merged monitor compiles against `rvsec-core` and `rv-monitor-rt`.

What makes it a transcription rather than an approximation is that the clause's
first place is anonymous, so projecting onto the **second** argument is exactly
what it asks. A one-place store loses *which* MAC, and this clause does not ask
which. The reasoning does not generalise: a clause naming both places would still
be inexpressible, and `randomized[lSeed]` remains so for the separate reason
recorded above.

**Two residues it leaves, recorded rather than mitigated (task 5.1c).**

1. **`Mac.update(java.nio.ByteBuffer)` marks nothing.** The rule declares no
   ByteBuffer event — its `update` events are `u1: update(inp)` over a byte and
   `u2`/`u3`/`u4` over a `byte[]` — so data fed through the buffer overload is
   never marked and the `Cipher` clause is silent about it. The event still
   exists, because dropping it would take the overload out of the automaton and
   turn a legitimate call into a sequence violation; it simply writes nothing.
   A false negative, and a deliberate one.
2. **`update(byte)` marks a boxed primitive**, which carries exactly the
   unsoundness recorded above for `randomized`: inside the `Byte` cache identity
   and equality coincide, so one MACed byte marks every equal literal in the
   process. Every value a `byte` can take is inside that cache, so this is not a
   corner: byte-at-a-time MACing marks that byte value globally. It over-marks,
   and since the clause is negated it over-reports.

And the boundary of the argument, so it is not over-applied: the one-place
projection is faithful **for this clause**, because its first place is anonymous.
A clause naming both places would still be inexpressible in a store that holds
objects rather than pairs — `randomized[lSeed]` above stays inexpressible for its
own, different reason.

The two declined alternatives, recorded so the choice stays legible:

1. **Record it as inexpressible**, beside `randomized[lSeed]`. Cheaper, and wrong
   once the projection is seen to be faithful — it would have filed an
   expressible clause as impossible.
2. **Read `!validate(GENERATED_MAC, plainText)`**, which is cheap and already
   available. It states a **different** clause — "do not encrypt a MAC" rather
   than "do not encrypt what you MACed". It catches a real misuse; it is simply
   not this one, and presenting it as the rule's would have been the kind of
   silent substitution this change exists to find.

## Clauses the fusion destroyed and this change does not restore (task 4.11)

These are `CONSTRAINTS`, not predicate-graph edges, so they are outside the
scope this change measured itself against. They are recorded because the same
fusion that hid the predicate edges hid them too, and because the re-budget puts
one of them within reach without taking it.

| rule | clause | why it stays out |
|---|---|---|
| `Cipher` | `part(1,…) in {CFB,PCBC,OFB,CBC,CTS,CTR} && encmode != 1 => noCallTo(IWOIV)` | needs the rule's *named subset* of init events, not just their arguments |
| `Cipher` | `part(1,…) in {…} && encmode == 1 => callTo(iv)` | needs a `getIV()` event, which the specification does not declare at all — `PointcutBudget` reports `getIV` among the unmatched members for exactly this reason |
| `KeyManagerFactory` | `neverTypeOf(password, java.lang.String)` | a type constraint on an argument, expressible only where the argument is bound and the *static* type is known |
| `KeyStore` | `neverTypeOf(passwordIn/passwordOut/passwordKey, java.lang.String)` | same, three of them |
| `PBEKeySpec` | `neverTypeOf(password, java.lang.String)` | same — this one is **not** in the task's enumeration, which named two rules and not three |

**One note for whoever picks up `noCallTo(IWOIV)`.** The rule's aggregates split
the init overloads by whether they carry an IV: `IWOIV := i1 | i2 | i3 | i8` and
`IWIV := i4 | i5 | i6 | i7`. The re-budget's arity-3 event covers `i2`, `i4`,
`i5` and `i8` — members of **both** aggregates. The `instanceof` that already
selects the predicate in that event body is exactly what would recover the
distinction, so the clause is reachable; it is simply not reached here. Without
this note it looks unreachable, which is worse than knowing it needs recovering.
