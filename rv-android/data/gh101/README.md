# The records the JCA specification sets are checked against (gh101)

Six data files here, all regenerable, all committed. They exist because the two JCA
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
| `predicate_edges.csv` | one row per CrySL predicate clause, with whether the set implements it | `scripts/gh101_predicate_edges.py` |
| `edge_counts_per_file.csv` | per `.mop`, how many edges it must close | same |
| `conformance_record.csv` | the verdict of each of the 23 derived specifications against its generated API 30 rule | `scripts/gh101_conformance_check.py` |
| `divergence_record.csv` | every hunk by which the sets differ, with its reason | `scripts/gh101_divergence_record.py` |

The gates that consume them live in `tests/parity/test_gh101_specset_gates.py`.

Two prose records sit beside them. `frozen_set_debt.md` lists what the `jca` set
knowingly retains — each entry a repair made in the derived set and deliberately
not made there — so a set kept reproducible is not mistaken for a set kept
correct.

`algorithm_naming.md` is the other, and is prose rather than data: it records
the gap between what a specification compares and what the platform resolves —
case, spelling variants and provider aliases — measured from the campaign and
from the corpus sources, together with the two rule defects the same sweep
surfaced and the design that would close the gap properly. Only its smallest part
is repaired in this change.

## The predicate inventory

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

13 hunks over 10 files, every one of them `allow-list` — the state before any of
this change's edits. Each entry names the hunk by a digest of its changed lines,
so an edit elsewhere in the same file does not invalidate it, while changing what
the hunk contains does: the reason recorded for the old content has not been
shown to hold for the new.
