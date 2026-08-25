# The predicate ledger, derived against the sole oracle

**Task 11.1 of gh105 · design decision D-16 · derived 2026-08-25**

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
| `REQUIRES` | 57 | 25 wireable · 21 unmonitored-consumer · 8 unmonitored-producer · 2 unreachable-composition · 1 vacuous |
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
- **`vacuous`** — the rule's own `EVENTS` bind none of the variables the clause names, so
  the clause has no site to read at. This is a property of the rule, not of the world.

The fifth, **`unreachable-composition`**, cannot be derived from text: it says the two ends
exist and the platform refuses to compose them. D-16 carries those measurements over
("re-cited, never re-litigated"), so the script applies them as named overrides with their
citation — `KeyPairGenerator preparedDH` and `Mac preparedHMAC` — and prints them as
overrides rather than recomputing them. The same holds for the one `vacuous` row that
survives, `Mac !encrypted[output2,_]`, whose emptiness is a runtime fact: `f2` binds
`output2` only as a returned array and the JCA allocates it fresh on every call.

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

## Predicate names across the two catalogues

Two predicates are spelled differently for the same thing: the expert rule writes
`generatedKeyManagers` and `generatedTrustManagers` where the generated one writes the
singular. The pairing is resolved in the ledger, declared in `PREDICATE_ALIASES`, and
**not** in the specifications: the name a wired read uses in code is a `Property` enum
constant of the store, which answers to neither catalogue and needs no edit. Task 11.1
flagged this case explicitly; this is its resolution.
