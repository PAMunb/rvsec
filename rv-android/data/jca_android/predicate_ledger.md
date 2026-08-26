# The predicate ledger, derived against the sole oracle

**Tasks 11.1, 11.9 and 11.5 of gh105 · design decision D-16 · derived 2026-08-25, re-derived 2026-08-26**

This is the record of `predicate_ledger.csv` and `predicate_ledger_delta.csv`, and it
supersedes *The 36-Clause Ledger (REQUIRES, api30)* of `design.md:483` as the ledger this
set answers to. Both tables are produced by `scripts/gh105_expert_ledger.py`, which sweeps
the rule text and derives every column; re-run it and the tables come back identical:

```bash
python scripts/gh105_expert_ledger.py --check
python scripts/gh105_expert_ledger.py --emit ledger --out data/jca_android/predicate_ledger.csv
python scripts/gh105_expert_ledger.py --emit delta  --out data/jca_android/predicate_ledger_delta.csv
```

The oracle is the pinned expert copy `RVSec-replication-package/tools/rules/` (49 rules,
sha256 `d7bcc019…`). `MetaCrySL/generated/api30/` appears in exactly one place — the delta
table — and in exactly one role: the historical input whose records the supersession
adenda of task 11.4 have to name. It is not an authority in any column of the ledger.

## What the sweep covers

The api30 ledger held 36 rows and covered `REQUIRES` only. This one covers all three
predicate sections, because a produced predicate nobody consumes breaks the chain exactly
as a consumed one nobody produces, and only the two halves together let the arithmetic
close:

| Section | Clauses | Dispositions |
|---|---:|---|
| `REQUIRES` | 57 | 24 wireable · 21 unmonitored-consumer · 9 unmonitored-producer · 2 vacuous · 1 unreachable-composition |
| `ENSURES` | 76 | 31 unmonitored-producer-side · 28 producible · 13 unread · 4 unmonitored-consumer-side |
| `NEGATES` | 2 | 1 unmonitored-producer-side · 1 unmonitored-consumer-side |
| **total** | **135** | |

**Pairing**: 21 of the 49 rules have a `.mop` in the set. Three files of the set pair with
no rule and are declared as such in the script rather than inferred from their names —
`SecretKeySpec.mop` (the propagator; it realises `SecretKey.crysl`'s ENSURES without
specifying the rule), `RandomStringPassword.mop` and `IvChainJunction.mop`. Without that
declaration a rule named `SecretKey` claims `SecretKeySpec.mop` on spelling alone and the
pairing count comes out 22.

## The dispositions, and where they come from

Four of the five are derived from rule text alone:

- **`wireable`** — the consuming rule and at least one producing rule both have a `.mop`.
- **`unmonitored-consumer`** — no `.mop` specifies the consuming rule.
- **`unmonitored-producer`** — the predicate is ensured, but by no rule the set specifies.
- **`vacuous`** — the clause can never hold. It has two grounds, and the script keeps them
  apart because only one of them is readable in the rule: *by text*, when the rule's own
  `EVENTS` bind none of the variables the clause names, so there is no site to read at; and
  *by runtime*, when the site exists and the object that reaches it can never carry the
  predicate. No clause carries the textual form today; both rows of the ledger carry the
  runtime one, as named overrides with their measurement.

The fifth, **`unreachable-composition`**, cannot be derived from text either: it says the
two ends exist and the platform refuses to compose them. Two clauses carried it —
`KeyPairGenerator preparedDH` and `Mac preparedHMAC` — and the script applies both as named
overrides with their citation, printing them as overrides rather than recomputing them.

The two runtime-`vacuous` rows are `Mac !encrypted[output2,_]`, whose `f2` binds `output2`
only as a returned array the JCA allocates fresh on every call, and
`SecureRandom randomized[lSeed]`, which task 11.5(d) derived and which the section below
states in full.

**Task 11.9 re-derived both overrides against the oracle rather than copying them, and
exactly one moved.** That asymmetry is the point: two rows moving, or none, would mean the
sweep was answering a different question than the one 11.1 asked of it.

- **`KeyPairGenerator preparedDH` (row 34) moves to `unmonitored-producer`.** The
  measurement stands and is re-cited, not repeated: the JCA raises
  `InvalidAlgorithmParameterException: Inappropriate parameter type` for
  `KeyPairGenerator.getInstance("DH").initialize(new DHGenParameterSpec(2048, 0))`, on
  Temurin 21. What falls is the sentence it rested on — *a DH key pair is initialised from a
  `DHParameterSpec`, which no rule ensures*. The generated catalogue stated no
  `DHParameterSpec` rule at all; the oracle states `DHParameterSpec.crysl:21 ENSURES
  preparedDH[this]`, and that is the type `initialize` accepts —
  `initialize(new DHParameterSpec(p, g))` over an RFC 3526 group runs. The row already
  carried the evidence in its own columns: `counterparts` reads
  `DHGenParameterSpec|DHParameterSpec` and `counterparts_with_mop` reads `DHGenParameterSpec`
  alone. Still not wired, and the reason is now the honest one — a read at
  `KeyPairGeneratorSpec.init3/init4` answers `NOT_OBSERVED` for every conforming DH program
  because the producer that program uses is unmonitored, not because no producer could exist.
  What would close the clause is a `.mop` for `DHParameterSpec`, and writing one is a new
  accusation class, which D-16 keeps out of this change.
- **`Mac preparedHMAC` (row 38) survives verbatim**, and is re-cited against the expert
  lines. Its producer is `javax.xml.crypto.dsig.spec.HMACParameterSpec`
  (`HMACParameterSpec.crysl:14`), of the `java.xml.crypto` module, and the android-30
  `android.jar` carries no entry whatever under `javax/xml/crypto` — a fact about the
  platform and not about a catalogue, which is why the substitution of oracle cannot touch
  it. The JVM half of the measurement was re-made over the oracle's own allow-list, because
  the old one ran over the twelve names of the withdrawn catalogue: on Temurin 21 over the
  nine of `Mac.crysl:44`, `HmacSHA256`, `HmacSHA384` and `HmacSHA512` answer *HMAC does not
  use parameters* and `HmacPBESHA1` with the five `PBEWithHmac*` answer *PBEParameterSpec
  type required*. All nine resolve, which is the one way the measurement differs — the old
  list named `PBEwithHmacSHA`, which no provider has.

**The arithmetic does not move.** 135 clauses before and after; the two counts that change
are `unmonitored-producer` 8 → 9 and `unreachable-composition` 2 → 1, which is one row
crossing between them and not a row appearing or leaving.

Task 11.5(d) later moved a second row the same way — `wireable` 25 → 24 and `vacuous`
1 → 2 — and it is a decision rather than a re-derivation, which is why it is recorded in
its own section below and not here.

## The delta against the api30 derivation

Forty-six rows, in four kinds. The three that change a disposition are the ones that move
work:

| Kind | Clause | api30 | expert | What it means |
|---|---|---|---|---|
| changed | `SSLContext.randomized` | `vacuous` | **`wireable`** | `bindable api30=False expert=True`. The api30 rule declares `Init: init(kms, tms, _)` — the third position is anonymous, so `sr` is bound by no event and the clause it also declares had no site. The expert rule declares `i1: init(km, tm, random)` and binds it. **The vacuity was an artefact of the generated rule.** This is the derivation task 11.5b was waiting for. |
| changed | `KeyPairGenerator.preparedEC` | `unclosable` | **`unmonitored-producer`** | In the api30 catalogue nothing ensures `preparedEC`, so the clause could never be closed by anything. In the expert catalogue two rules ensure it — `ECGenParameterSpec:25` and `ECParameterSpec:17` — and neither has a `.mop`. The diagnosis changes and so does the remedy: the clause is not unclosable, it is orphaned by the pairing gap, and specifying `ECGenParameterSpec` would close it. **`unclosable` disappears from the ledger entirely.** |
| changed | `PBEParameterSpec.preparedPBE` | `unread` | `unmonitored-consumer-side` | The expert catalogue has a consumer for it (`AlgorithmParameters`), which the api30 catalogue did not; that consumer has no `.mop`, so nothing is wired, but the predicate is no longer produced into the void. |
| reshaped | `Signature.verified` (ENSURES) | arity 1 | arity 2 | Same clause, wider shape. |
| reshaped | `AlgorithmParameters.preparedAlg` (REQUIRES) | arity 1 | arity 2 | Same clause, wider shape. Consumer has no `.mop` either way. |

The remaining 41 rows are `expert-only`: clauses the expert catalogue declares and the
generated one never did. Most land on rules with no `.mop` and change nothing. **Three of
them are `wireable`**, which is to say they are wirings the sole oracle opens and that no
task of this change had listed:

| Clause | Producers with a `.mop` | Task |
|---|---|---|
| `Mac.generatedKey[key,_]` (`Mac.crysl:54`) | `KeyGenerator`, `KeyStore`, `SecretKeySpec` | 11.5a — the clause task 4.9 deleted for a reason D-16 voids |
| `CipherInputStream.generatedCipher[cipher]` (`CipherInputStream.crysl:31`) | `Cipher` (`Cipher.crysl:144`) | **new — 11.5e** |
| `CipherOutputStream.generatedCipher[cipher]` (`CipherOutputStream.crysl:32`) | `Cipher` (`Cipher.crysl:144`) | **new — 11.5e** |

The two `generatedCipher` clauses are one chain: `Cipher` ensures the predicate and the two
stream specifications consume it, and all three files exist in the set. Neither end was
ever wired, because the generated catalogue declared neither the ENSURES nor the two
REQUIRES. They enter 11.5 under the 9.B discipline like the rest — harness pair, divergence
row, go/no-go per clause — and nothing moves on this record's strength alone.

## What the set requires and cannot observe, and the reciprocal half

**Task 11.9(c) and (d).** Both halves are *derived by enumeration from the ledger* and never
listed by hand, which is the difference between a record and a backlog: a hand-typed list
cannot move when the ledger moves, and it can omit a row in silence. The command is

```bash
python scripts/gh105_expert_ledger.py --emit census
```

and its output is reproduced below verbatim.

A `REQUIRES` row of a rule the set specifies is **unobservable** unless its disposition is
`wireable`; every other disposition names a different way the producing end is out of reach.
`vacuous` counts there only for a **positive** clause: a requirement that can never be met
is a requirement the set cannot observe, while for a negated `!pred[..]` absence *is*
conformance, so a clause nothing can satisfy is one nothing can violate and listing it as a
gap would read as work owed where none is. An `ENSURES` or `NEGATES` row of a specified rule
is **unreadable** when nothing the set can observe requires it — `unread` if no rule of the
49 requires it at all, `unmonitored-consumer-side` if the rules that do have no `.mop`.

```
REQUIRED AND NOT OBSERVABLE
  11 clause(s), 10 predicate(s)
  preparedAlg                        Cipher                 Cipher.crysl:136                 unmonitored-producer
  preparedOAEP                       Cipher                 Cipher.crysl:140                 unmonitored-producer
  generatedManagerFactoryParameters  KeyManagerFactory      KeyManagerFactory.crysl:32       unmonitored-producer
  preparedRSA                        KeyPairGenerator       KeyPairGenerator.crysl:35        unmonitored-producer
  preparedDSA                        KeyPairGenerator       KeyPairGenerator.crysl:36        unmonitored-producer
  preparedDH                         KeyPairGenerator       KeyPairGenerator.crysl:37        unmonitored-producer
  preparedEC                         KeyPairGenerator       KeyPairGenerator.crysl:38        unmonitored-producer
  preparedHMAC                       Mac                    Mac.crysl:53                     unreachable-composition
  preparedKeyMaterial                SecretKeySpec          SecretKeySpec.crysl:23           unmonitored-producer
  randomized                         SecureRandom           SecureRandom.crysl:46            vacuous
  generatedManagerFactoryParameters  TrustManagerFactory    TrustManagerFactory.crysl:29     unmonitored-producer

ENSURED AND NOT READABLE
  18 clause(s), 12 predicate(s)
  wrappedKey                         Cipher                 Cipher.crysl:148                 unread
  cipheredInputStream                CipherInputStream      CipherInputStream.crysl:34       unread
  cipheredOutputStream               CipherOutputStream     CipherOutputStream.crysl:35      unread
  generatedKeypair                   KeyPair                KeyPair.crysl:27                 unread
  generatedKeypair                   KeyPairGenerator       KeyPairGenerator.crysl:41        unread
  generatedMessageDigest             MessageDigest          MessageDigest.crysl:46           unmonitored-consumer-side
  digested                           MessageDigest          MessageDigest.crysl:47           unread
  digested                           MessageDigest          MessageDigest.crysl:48           unread
  speccedKey                         PBEKeySpec             PBEKeySpec.crysl:32              unmonitored-consumer-side
  speccedKey                         PBEKeySpec             PBEKeySpec.crysl:35              unmonitored-consumer-side
  preparedPBE                        PBEParameterSpec       PBEParameterSpec.crysl:23        unmonitored-consumer-side
  generatedSSLContext                SSLContext             SSLContext.crysl:37              unread
  generatedSSLEngine                 SSLContext             SSLContext.crysl:38              unread
  speccedKey                         SecretKeySpec          SecretKeySpec.crysl:26           unmonitored-consumer-side
  signed                             Signature              Signature.crysl:58               unread
  signed                             Signature              Signature.crysl:59               unread
  signed                             Signature              Signature.crysl:60               unread
  verified                           Signature              Signature.crysl:61               unread
```

**The derivation is wider than the sketch the task carried, and that is what emitting it was
for.** Task 11.9(c) named six predicates — `preparedRSA`, `preparedDSA`, `preparedEC`,
`preparedOAEP`, `preparedAlg` and `generatedManagerFactoryParameters`. The sweep found nine,
over ten clauses, and task 11.5(d) added the tenth (`randomized[lSeed]`, eleven clauses): `generatedManagerFactoryParameters` is required by two rules and not one,
and three predicates the sketch did not name belong in the class — `preparedDH`, which 11.9(a)
moved into it; `preparedHMAC`, whose `unreachable-composition` is a different way of being
unobservable and not an exemption from it; and `preparedKeyMaterial`, whose producer
(`SecretKey.crysl:17`) has no `.mop` because `SecretKeySpec.mop` is the propagator and
specifies no rule. Task 11.9(d)'s six become twelve the same way: `wrappedKey`,
`cipheredInputStream`, `cipheredOutputStream`, `generatedSSLContext`, `generatedSSLEngine`
and `generatedMessageDigest` join the list the sketch drew.

One entry of the sketch was already settled before this task: `preparedEC` is described there
as `unclosable`, which it was against the generated catalogue and has not been since 11.1 —
the oracle ensures it in `ECGenParameterSpec` and `ECParameterSpec`, neither with a `.mop`,
so it is `unmonitored-producer` and `unclosable` no longer appears in the ledger at all. The
delta table above records that move.

**The standing conclusion, unchanged by the widening**: closing any of these means a
specification for a rule the set does not have, which D-16 keeps out of this change. The one
row of the list that conclusion does *not* fit is `SecureRandom randomized[lSeed]`, and the
difference is worth naming rather than smoothing over: the other ten name a producing rule
that exists in the oracle and lacks a `.mop`, so a specification would close them, while
that one names a producer the oracle does not have at any type a `long` could carry. No
specification closes it, which is why its disposition is `vacuous` and not
`unmonitored-producer`. The
reciprocal half is here so the requiring half cannot be read as one-sided — `preparedPBE`,
`speccedKey` and `generatedMessageDigest` are required only by rules with no `.mop`, while
`digested`, `signed`, `verified`, `generatedKeypair`, `wrappedKey`, `cipheredInputStream`,
`cipheredOutputStream`, `generatedSSLContext` and `generatedSSLEngine` are required by **no
rule of the 49 at all**. Those nine are dead ends of the oracle and not of this set, and
saying so is what keeps a future reader from proposing a wiring for them.

## The clauses task 11.5 records instead of wiring

Three clauses of the sole oracle reached task 11.5 as candidates for a wiring and leave it
as records. The task exists so that each conclusion is **derived** under the expert oracle
rather than assumed, and one of the three moved a disposition because of it.

**`TrustManagerFactory generatedManagerFactoryParameters[params]`** (`:29`, ledger clause
#56) — `unmonitored-producer`, derived. The predicate is ensured by exactly two rules,
`CertPathTrustManagerParameters.crysl:17` and `KeyStoreBuilderParameters.crysl:14` (ledger
#61 and #98), and neither has a `.mop`. The site would be cheap — `TrustManagerFactorySpec`
already fuses `init(KeyStore)` and `init(ManagerFactoryParameters)` into one event and
discriminates by runtime type, so the read would go in the branch the `instanceof KeyStore`
test already leaves empty — and that is precisely why the conclusion had to be derived: a
read placed there can answer `NOT_OBSERVED` and nothing else, which is the shape of the
seventeen orphan accusers group 3 removed. The twin clause at `KeyManagerFactory.crysl:32`
(#29) carries the same disposition for the same reason, and the symmetry is not a
coincidence to be tidied away: it is the same two producing rules.

**`SecureRandom randomized[lSeed]`** (`:46`, clause #51) — **`wireable` → `vacuous`**, and
this is the one disposition task 11.5 moves. Two independent grounds, either sufficient.
*By type*: swept over the 49 rules, `randomized` is ENSURED five times and never over a
`long` — `SecureRandom` carries it on `this`, on the `byte[]` of `generateSeed` and of
`nextBytes`, and on the `int` of `nextInt` and `nextInt(range)`. No producer of the
catalogue could mark a `long`. *By substrate*: `PredicateStore` keys the bound object by
identity, and a `long` reaches an advice boxed. Measured on Temurin 21, the `Long` cache
spans `-128..127` exactly as `Integer`'s does, so the boxing is wrong in both directions —
outside the range every call boxes a fresh object no write can have named, and inside it two
unrelated `setSeed(5L)` calls share one object, so a mark made for either would answer for
the other. This is the Integer-cache measurement of the earlier groups, extended to `Long`
and re-derived rather than carried over.

**`Cipher wrappedKey[wrappedKeyBytes, wrappedKey]`** (`:148`, clause #67) — `unread`,
derived, and the row that shows the reciprocal half of the census is not decoration. The
oracle *does* state the clause where the generated catalogue stated none, which is why the
site was reopened at all; no rule of the 49 REQUIRES `wrappedKey`, so a write at
`CipherSpec.wkb1` would produce something nothing can consume. Task 4.1 deleted that write
and the deletion stands, now on the oracle's own ground rather than on the withdrawn
catalogue's silence.

**No harness pair is owed for any of the three**: no `.mop` gains or loses a site, no
accusation changes class, and the only artefacts that move are this file, the ledger CSV and
the comments that name the decision beside each site.

## Predicate names across the two catalogues

Two predicates are spelled differently for the same thing: the expert rule writes
`generatedKeyManagers` and `generatedTrustManagers` where the generated one writes the
singular. The pairing is resolved in the ledger, declared in `PREDICATE_ALIASES`, and
**not** in the specifications: the name a wired read uses in code is a `Property` enum
constant of the store, which answers to neither catalogue and needs no edit. Task 11.1
flagged this case explicitly; this is its resolution.
