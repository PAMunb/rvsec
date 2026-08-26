# `jca_android` — the successor specification set

This directory holds the records of the specification set that `--specification-set jca_android`
resolves to from gh104 on: `rvsec/rvsec-mop/src/main/resources/jca_android/`, seeded from the frozen
`jca` Java set and shaped by one mechanical pass: every allow-list re-transcribed from a CrySL catalogue,
read through the normalisation rule below. The seed's predicate machinery travels with it
untouched — see *What the successor set contains*.

**The set answers to one oracle** (design D-16, 2026-08-25): the pinned expert copy
`RVSec-replication-package/tools/rules/` — 49 expert-validated CogniCrypt rules, sha256
`d7bcc019…`, a freeze item below — for **every** dimension alike: values, `ORDER`, event
alphabets and predicate clauses. It is read-only: where a rule is judged defective the
judgement is a row of `divergence_record.csv`, never an edit upstream.

The generated catalogue `MetaCrySL/generated/api30/` was that oracle until D-15 took its
value dimension (2026-08-24) and D-16 took the rest. It keeps **no** oracle role in any
dimension. It stays on disk as the historical input the pre-D-16 records were written
against, and is named only inside supersession adenda — a citation of it anywhere else is
a defect, which is what the grep gate of task 11.4 asserts.

## Freeze items

| item | value | what it pins |
|---|---|---|
| `pre-rename-head` | `a3e6a1651cc63d83525fcbb42c0cd5f659ef463e` | the Java tree's `HEAD` immediately before the `git mv` of task 2.1. Task 10.1 asserts the archival is a pure rename **against this SHA**, and it is also the read-only base of `AndroidCipherTransformationUtil.java`, which does not exist at `7e7acb69` (gh101 added it). |
| `jca` freeze base | `7e7acb69` | `rvsec-mop/src/main/resources/jca/` and `CipherTransformationUtil.java` are byte-identical to it and stay so (gh101 D-S0, INV-INS-109). |
| expert value oracle | `d7bcc01938150ae5e560cb3bcb6796af9cba05887df7b93e3f67a80bc3f3b033` | the 49 `.crysl` rules of `RVSec-replication-package/tools/rules/`, the oracle of every **value** clause of this set from D-15 (2026-08-24). The hash is of the sorted per-file manifest `oracle/expert_rules.sha256`; recompute with `cd <pkg>/tools/rules && sha256sum $(ls *.crysl \| sort) \| sha256sum`. |

### Why the value oracle is a pinned copy and not a branch

Three local copies of the 49 expert rules exist, and the audit of 2026-08-24 measured them.
The upstream CogniCrypt checkout (`Crypto-API-Rules`, `master` at `6d844ab`, 2022-05-12) and
`rvsec-cognicrypt/CrySL-Rules` are byte-identical. The replication-package copy — the one
pinned above — differs from them in exactly one value: it adds `"CCM"` to the AES modes of
`Cipher.crysl:97,113`. That addition is **local to RVSec**, not upstream: the *current*
upstream `master`, checked on 2026-08-24, still carries no `CCM`. It is recorded as an
`oracle-wart` row rather than removed, because the pinned copy is the one the published
numbers were measured against.

The same check is the reason the oracle is pinned at all. Today's upstream `master` has moved
in the opposite direction and **dropped `CBC` and `PCBC` from the AES modes**. Re-anchoring on
a live branch would therefore start accusing `AES/CBC/PKCS5Padding` — the most common
transformation in the corpus — on nobody's decision, in a run nobody asked for. A value oracle
has to be a copy with a hash.


## The archived derived set

`rvsec/rvsec-mop/src/main/resources/jca_android/` used to name the set gh101 derived against
generated CrySL rules. The 2026-08-08 audit (`audit/20260808_validacao_jca_android/`) reproved it on
its predicate machinery: 22 of the 23 files were in the audit's scope — `RandomStringPassword`, the
`@fail`-less propagator, was outside it — and every one of the 22 was reproved.

Task 2.1 moved that set unchanged to
`rvsec/rvsec-mop/src/main/resources/jca_android_bug_predicate/` (23 `.mop`, `R100`, zero content
hunks). The name states why it is archived rather than what it used to be called, per P4.

**It is not selectable.** No `--specification-set` value points at it and none is added: the
enumeration keeps its four values (`jca`, `jca_android`, `generic`, `custom`), and the archived
directory name is rejected exactly like any other unknown string (task 2.9). Regenerating it is a
deliberate act — `--specification-set custom --custom-specs-dir <path to the archive>` — and that
deliberateness is the point.

It is a record, not an instrument: no gh104 task edits it, regenerates it or replays it. It is read
by the gh101 gate scripts, which task 2.13 repoints at it so gh101's freeze and divergence records
keep resolving (INV-INS-118), and by the identity checks of tasks 2.11 and 10.1.

## What the successor set contains

Twenty-four `.mop` files and `codes.csv`, and nothing else. It was twenty-three until Group 5
added `IvChainJunction.mop`, the junction specification that carries a chain no single API's
rule states. `codes.csv` (header
`spec,code,error_type,site_kind,event,file_line`) is the table of failure codes the set's
envelopes emit; it is the **only** non-`.mop` file of the directory. The seed directory
`jca/` also holds `MultiSpec_1MonitorAspect.aj`, a gitignored leftover of a generation run
that is not tracked and does not travel with the seed.

That count includes `RandomStringPassword.mop` and `SecretKeySpec.mop`, the two files that accuse
nothing: `grep -c "new ErrorDescription("` returns 0 for both and neither has a `@fail`. They are
no longer the same case. `SecretKeySpec.mop` is still the propagator the description fits -- it
reads `GENERATED_KEY` over the key it observes and writes `PREPARED_KEY_MATERIAL` for the
constructor that copies the bytes, so deleting it would silently disarm a read elsewhere in the
set, which is the reason design D-11 withdrew the deletion an earlier revision of this change had
planned.

`RandomStringPassword.mop` writes nothing since `5f64c8de`, and no `condition()` reads it. It was
the set's only dataflow bridge, carrying `randomized` across `Object -> String -> char[]` so that
`PBEKeySpecSpec.c1`'s read over a `char[]` could be met, and its four predicate sites went because
the bridge does not carry what it stamps -- measured over each of the three source types the set
can hand it (researcher, 2026-08-21): a `byte[]` converts to its identity string, `"[B@726f3b58"`,
which holds a heap identity hash and not one bit of the array; a `SecureRandom` converts to the
constant `"SecureRandom"`, the same text in every program; and an `Integer` converts faithfully but
does not survive the store's identity keying outside the `-128..127` cache, where for
`nextInt(int)` the marked value is the bound and not the result. So the two source types that
propagate carry no randomness and the one that carries randomness does not propagate. The file
stays for what deleting it would cost -- its two events keep the calls modelled rather than
unmarked -- and it stands in this directory as the negative record of that measurement: the reason
the set does not launder a predicate across those conversions is written in the file itself, where
the next reader tempted to rebuild the bridge will find it.

The predicates were carried over **byte-for-byte** until gh105 migrated the substrate. The seed
still holds its 134 `ExecutionContext` lines (23 `import`, 27 `validate(`, 49 `setProperty(`,
9 `remove(`, 25 accepting-state calls and 1 comment at `MessageDigestSpec.mop:25`) and is frozen
that way. `jca_android` holds **none** of them: the set names `ExecutionContext` **0** times, calls
`setProperty(` **0** times and `.remove(` **0** times, and reads its predicates through **38**
`validate(` calls against the new store. Group 4 did the migration and INV-INS-130 is the check —
a whole-word grep over the set, so a mention in a comment or a string counts like one in code.

What the seed-versus-successor comparison still means is therefore narrower, and the two gates that
make it say so are worth naming apart. `tests/parity/test_gh104_specset_gates.py::test_the_frozen_seed_still_carries_every_predicate_site_it_was_frozen_with`
runs G-PRED against the **seed itself**, which is what keeps the frozen control frozen; its
docstring records that gh105 supersedes it for `jca_android` alone. For the successor the
accounting is `predicate_graph.csv` and the four gates that decide against it: every predicate site
has a row with its clause, its mechanism and its disposition, which is a stronger statement than
byte-equality ever was — byte-equality could only say the lines had not moved, not that each read
has a producer and each write a reader. The `ExecutionContext` keying ruling of gh101 (equality,
`e204e2a4`) still governs the seed; the successor's store is keyed by identity.

## The normalisation rule

An allow-list of this set is the `CONSTRAINTS` clause of its expert rule and nothing else, so
a value the application spells differently would not match it. The set therefore declares
**one** normalisation rule and applies it uniformly at every value test it has:

> **Comparison is case-insensitive, and an observed value matches a list entry when a row of
> `alias_table.csv` maps it to that entry.**

Both halves go through a single call to `ConscryptAliasTable`
(`rvsec-core/src/main/java/br/unb/cic/mop/jca/util/`), which each of the ten specifications
that still carries an allow-list names in its check. That one call replaces two inconsistent
idioms the seed carried by accident: case-sensitive `contains()` in `Mac`, `Signature`,
`SecureRandom`, `KeyGenerator`, `TrustManagerFactory`, `KeyManagerFactory`, `KeyStore` and
`KeyPairGenerator`, and `.toUpperCase()` in `MessageDigest` and `SSLContext` — under which
the same string was a misuse in one specification and not in another. The seed's eleventh
idiom, `SecretKeySpecSpec`'s `.toUpperCase()`, became a `ConscryptAliasTable.matches` call
like the rest when D-15 restored that specification's list: the generated rule stated no
algorithm clause, so the transcription made against it had deleted the list outright, and
`SecretKeySpec.crysl:18` states one.

The table is **not read at run time**. A monitor woven into an APK has no filesystem
contract with this repository, so `ConscryptAliasTable` carries the table as code and
`alias_table.csv` is the auditable registry of the same rows.
`ConscryptAliasTableTest` asserts the two are equal row for row — all 175 rows, every
column — so the record and the instrument cannot drift. No `.mop` of the frozen `jca` names
that class, which is what keeps the published measurements reproducible: nothing here can
move a `jca` verdict.

### `alias_table.csv`

175 rows, extracted from Conscrypt branch `android11-release`, path
`common/src/main/java/org/conscrypt/OpenSSLProvider.java` (607 lines, 175 `Alg.Alias.*`
registrations), kept locally and gitignored at `backup/gh104-analise/OpenSSLProvider.java`.
The row count and the registration count are now the same number, which is the point of gh105
task 9.8: the table was 169 rows and the completeness claim above was a promise rather than a
measurement. The six that were missing are missing by service, not by syntax — five
`KeyFactory` OIDs (`:195-197`, `:200-201`) and `CertificateFactory X.509 → X509` (`:500`) —
and no `.mop` resolves either service, so adding them moved no verdict.
160 rows are in services one of the 21 rule-paired specifications covers — 21, not 24: it is the
count of `.mop` files with a matching expert rule, which is what `conformance_record.csv` keys on,
and not the size of the set. The other 15 rows are in services with no specification
(`AlgorithmParameters` 8, `KeyFactory` 5, `SecretKeyFactory` 1, `CertificateFactory` 1) and are
kept, with their flag, so the extraction stays complete.

`in_api30_allowlist` has exactly one definition: **`yes` when the row's canonical name is an
entry of the successor set's allow-list for that service, after the recorded departures.** The
column keeps its name for continuity, but from D-15 the lists it is computed against are the
expert ones, so the flag was recomputed and 65 of the rows changed: the aliases resolving to
`SHA-1`, `MD5withRSA`, `ARC4` and their relatives now read `no`. That is the direction that
matters -- such a row makes the accusation reach the calls that spell the value otherwise,
rather than excusing them. Counts under that definition:

| service | `yes` | `no` |
|---|---:|---:|
| `Signature` | 28 | 33 |
| `Mac` | 13 | 11 |
| `KeyGenerator` | 10 | 13 |
| `MessageDigest` | 6 | 6 |
| `KeyPairGenerator` | 5 | 0 |
| `Cipher` | 4 | 30 |
| `TrustManagerFactory` | 1 | 0 |
| `AlgorithmParameters` (no specification) | 0 | 8 |
| `KeyFactory` (no specification) | 0 | 5 |
| `SecretKeyFactory` (no specification) | 0 | 1 |
| `CertificateFactory` (no specification) | 0 | 1 |
| **total** | **67** | **108** |

A service the set does not cover has no allow-list for a canonical to be an entry of, so its
rows are `no` by construction — which is why the six rows task 9.8 added are all `no` and the
`yes` column did not move. Under the api30 anchor the split was 124 `yes` / 34 `no` over
158 rows; the 11 rows task 11.6 added and the recomputation against the expert lists moved 65
flags, nearly all of them `yes` → `no`. That is the measure of the anchor change, read off the
table: an alias whose canonical name is `SHA-1`, `MD5withRSA`, `ARC4`, `HmacMD5` or a
`SHA1withECDSA` used to resolve into a list that admitted it, and now resolves into one that
does not.


For `Cipher`, "the allow-list" means the algorithm set the rule states — under the oracle
`noCallTo[Init] => alg(transformation) in {…}` of `Cipher.crysl:94`, which names `AES`, `RSA`
and the eight `PBEWithHmacSHA{224,256,384,512}AndAES_{128,256}` transformations. Until D-15
it meant `part(0,"/",transformation) in {…}` of `Cipher.cryptsl:121`, eight families wide,
transcribed as `ALGORITHMS` in `Api30CipherTransformationUtil`; that clause is **withdrawn**
and that class has had no caller since task 11.3. The counts in the table above were computed
against the expert lists and are unaffected. A canonical that names a bare algorithm of that set is
`yes` — the four `ARC4` rows — and a canonical that names a whole transformation is `no`,
because a transformation is not an entry of any list; it is validated clause by clause.
**`Cipher.GCM -> AES/GCM/NoPadding` is therefore `no`**, and it would be wrong to read it as
`yes` on the ground that `GCM` occurs in the `Cipher` rule: it occurs there as a mode of
operation, not as an algorithm, and the alias names a whole transformation, so a match on it
would be spurious. That is written down here so that nobody re-derives the count later and
concludes the table changed.

The flag is a property of the record and never an input to resolution: `matches()` does not
consult it, so a row flagged `no` still resolves when a list happens to carry its canonical.

**Two corrected pointers.** The pivot brief inherited two wrong line references from the
ase-journal report, and the corrected values are the ones every artefact of this change
carries:

| alias | brief said | correct, verified in `OpenSSLProvider.java` |
|---|---|---|
| `SHA1`/`SHA` → `SHA-1` | `:131-132,140` | **`:115-116`** — `:131-132` is `SHA-512`/`SHA512`, and `:140` is `KeyGenerator.ARC4`, which is a registration and not an alias at all |
| `X509` → `PKIX` | `:101-107` | **`:89-90`** — `:101-102` is `AlgorithmParameters` DESEDE/TDEA |

**Rows sampled against the source**, at least one per alias form, each opened at its cited
line and found to match:

| row | line | form |
|---|---|---|
| `TrustManagerFactory` `X509` → `PKIX` | 90 | historic name (and the corrected pointer; `:89` is the `PKIX` registration it points at) |
| `MessageDigest` `SHA1` → `SHA-1` | 115 | unhyphenated spelling (corrected pointer) |
| `MessageDigest` `SHA` → `SHA-1` | 116 | unhyphenated spelling (corrected pointer) |
| `MessageDigest` `1.3.14.3.2.26` → `SHA-1` | 117 | bare OID |
| `KeyGenerator` `HMAC/SHA256` → `HmacSHA256` | 171 | alternate separator |
| `Signature` `MD5withRSAEncryption` → `MD5withRSA` | 212 | `Encryption` suffix |
| `Signature` `OID.1.2.840.113549.1.1.11` → `SHA256withRSA` | 243 | `OID.` prefix |
| `Signature` `2.16.840.1.101.3.4.2.1with1.2.840.10045.2.1` → `SHA256withECDSA` | 290 | composite OID |
| `Signature` `SHA256withRSAandMGF1` → `SHA256withRSA/PSS` | 313 | `andMGF1` |
| `Cipher` `ARCFOUR` → `ARC4` | 424 | historic name |
| `Mac` `PBEWITHHMACSHA256` → `HmacSHA256` | 481 | `PBEWITHHMACSHA<n>` |

**Two declared limits**, stated because a table that hides them invites false confidence:

1. **`KeyStore` has no alias coverage here.** `AndroidKeyStore` comes from
   `AndroidKeyStoreProvider` and `BKS`/`BouncyCastle` from Bouncy Castle, and
   `OpenSSLProvider.java` registers no `KeyStore` alias at all. That is a limit of the
   table, not evidence that none is needed.
2. **`SSLContext.SSL` and `SSLContext.TLS` (`:80-81`) are not rows.** They point at the same
   implementation class but are not `Alg.Alias` registrations, so they are behavioural
   equivalence rather than table entries.

**One spelling deliberately has no row.** `RSA/ECB/OAEPWithSHA1AndMGF1Padding` (109 events,
1 app, 1 misuse) carries no hyphen in `SHA1`; the withdrawn api30 catalogue declared
`OAEPwithSHA-1andMGF1Padding` and the expert rule carries no SHA-1 OAEP variant at all, Conscrypt registers
`RSA/ECB/OAEPWithSHA-1AndMGF1Padding` (`:338`) and the alias
`RSA/None/OAEPWithSHA-1AndMGF1Padding` (`:339-340`), both hyphenated, and the unhyphenated
spelling appears in no registration of that file. There is therefore no provider line a row
could cite, and a row without one would break the per-entry pointer requirement of
INV-INS-127 for one value. The case is a `behavioural` entry of `divergence_record.csv`
instead, and `Api30CipherTransformationUtil` deliberately does not fold the hyphen.

## The expert transcription, and the five departures from it

**Superseded on 2026-08-24 (design D-15).** Until then this section read "the api30
transcription, and the three departures from it", and every allow-list was the `CONSTRAINTS`
clause of the matching rule in `MetaCrySL/generated/api30/`. That anchor is **withdrawn for
value clauses**, for a measured reason: the Android tier `.ref` files those rules are refined
from were derived from **provider registries**, so a refined list answers "what does the
platform offer" and never "what is safe to use". Transcribed into a clause whose purpose is
security, that answer inverts the rule while leaving its syntax untouched — `in {...}`
identical, set replaced. The audit `docs/20260824_auditoria_specs_jca_android.md` measured
what it cost, and the sharpest case had no published number behind it at all:
`Api30CipherTransformationUtil` admits **`AES/ECB/PKCS5Padding`**.

Every allow-list and value test is now a literal transcription of the `CONSTRAINTS` clause of
the matching rule in **`RVSec-replication-package/tools/rules/`** — the 49 expert-validated
CogniCrypt rules, pinned by sha256 as a freeze item above, and the copy the published RVSec
numbers were measured against. In practice the list carried is the frozen `jca`'s own list,
checked entry by entry against that clause: the frozen list *is* the expert transcription, so
re-transcribing from the rule text would risk a second hand-copy of the kind this decision
exists to undo.

**The scope was values only for one day.** Until D-16 (2026-08-25) this paragraph read that
`ORDER`, event alphabets and the predicate clauses kept the generated api30 rules as their
oracle, on the ground that the protocol dimension survives the MetaCrySL chain nearly
intact. **That is withdrawn.** A chain that inverts the semantics of a value clause earns no
oracle role in any dimension — and task 11.4 then measured the same inversion in the
arithmetic: `Cipher.cryptsl:131`, `:133` and `:135` state the `update`/`doFinal` buffer
bounds with the comparison reversed against `Cipher.crysl:123`, `:127` and `:128`, satisfied
exactly where the oracle is violated, while the fourth clause of the same family is not
reversed. There is one oracle for every dimension, and it is the expert copy.

What that cost, and where each record now stands:

* **`predicate_ledger.csv` and `predicate_ledger_delta.csv`** — the predicate clauses,
  re-derived clause by clause from the 49 expert rules by `scripts/gh105_expert_ledger.py`
  (task 11.1). Every disposition is re-derived against the expert text, never copied.
* **`order_alphabet_map_expert.csv` and `order_alphabet_map_delta.csv`** — the `ORDER` and
  event alphabets, re-derived by `scripts/gh105_expert_alphabet.py` (task 11.2), matching
  **by signature and never by name**, because the two catalogues permute names over the same
  calls. `order_alphabet_map.csv` is kept on disk and **nothing reads it** (INV-INS-118); it
  is not a fallback.
* **`conformance_record.csv` and `conformance_record_delta.csv`** — one `rule` column with
  one meaning, the expert rule, with the census of what the substitution moved derived by
  `scripts/gh105_expert_conformance.py` (task 11.4). Its `--check` refuses a `rule` cell
  naming a `.cryptsl`, a row that names the withdrawn catalogue without a supersession
  adendum, and a census that does not close.
* **`divergence_record.csv`** — every row whose reason cites the withdrawn catalogue carries
  the D-16 adendum, and the twelve whose reason rested on a sentence the oracle makes false
  carry a tail of their own saying which sentence fell. None of them reverses a decision:
  where the oracle opens a wiring or tightens an ordering, that is decided per clause at
  tasks 11.5 and 11.6, with a harness pair and a divergence row.
* **`constraint_table.csv`** and the value records were already re-anchored by D-15 and are
  unchanged by D-16.

Every record derived against the generated catalogue keeps its sentences and gains an
adendum, rather than being rewritten: a row rewritten without them would make the api30 era
unreadable, and the era is what the published measurements answer to.

In `jca_android` the `ErrorType` `UnsafeAlgorithm` therefore means again what it meant in the
published `jca`: **cryptographically insecure per the expert rule**. Any report comparing
counts across `jca`, the archived `jca_android_bug_predicate`, the pre-D-15 `jca_android` and
this set must say which oracle each answers to.

Five kinds of departure from a literal transcription are admissible, and each is recorded:

1. **An entry of the normalisation table** — `alias_table.csv`, and nowhere else.
2. **`platform-value`** — a value the expert rule omits whose rejection would accuse a
   practice the platform itself recommends, in `divergence_record.csv` with a primary-source
   citation. The set is **closed**: `TLS` in `SSLContextSpec`, and
   `{AndroidKeyStore, AndroidCAStore, BKS, BouncyCastle}` in `KeyStoreSpec`. A candidate
   without a citation is dropped and stays accused. `X509` needs no entry (the alias table
   maps it to `PKIX`, an expert entry); `SHA256WITHRSA` needs none (case folding covers it);
   **`SSL` deliberately gets none** — Conscrypt binds it to the same implementation as `TLS`
   (`OpenSSLProvider.java:80-81`) but through a `put`, not an `Alg.Alias`, so it earns no
   alias row either, and asking a provider for `"SSL"` is the misuse the rule is about.
3. **`oracle-wart`** — a measured quirk of the expert rule, transcribed faithfully rather
   than fixed, with the quirk named: `Cipher` admits `OAEPWithMD5AndMGF1Padding` and no SHA-1
   OAEP variant; `MessageDigest` omits `SHA-224`; `Signature` omits `SHA224withECDSA` and
   `SHA1withECDSA`; the pinned copy adds `CCM` where upstream never did.
4. **`spelling-variant`** — a frozen-set list entry that duplicates an expert entry under
   case folding or an alias row. Kept, not stripped: it changes no verdict, so removing it is
   an unvalidated edit that can only cost.
5. **`deferred-constant`** — a clause the expert rule declares and this set does not check,
   in `conformance_record.csv`, quoting the **expert** clause text. Never an api30
   reconstruction of it: the audit proved two such reconstructions (`pre_len > pre_off`,
   `len > off`) are mangled, and a row quoting them would license implementing a bug.

A value difference that is none of the five is a defect, and G-CONF fails on it. So is a
clause neither transcribed nor deferred.

**No narrowing on preference.** Values the expert lists carry that Android does not offer —
`SunX509`, `NativePRNG*`, `Windows-PRNG`, `PKCS11`, `JKS`, `JCEKS`, `DKS` — stay in the
lists. They are inert (no application can obtain them, so no verdict depends on them), and
removing an entry from an expert-validated list because the local platform lacks it is
exactly the unvalidated narrowing this decision forbids. This reverses three narrowings the
api30 anchor had taken.

**No new accusation classes either.** An expert clause the frozen `jca` left unimplemented
stays unimplemented as a `deferred-constant`. The re-anchoring restores the lists the experts
wrote; it does not enlarge the set of clauses the instrument checks, since a new class would
carry an unmeasured false-positive rate on the corpus. The measured case is
`KeyGenerator.crysl`'s `algorithm in {"AES"} => keysize in {128, 192, 256}`.

`constraint_table.csv` now holds **80 rows**, derived against the expert anchor and
reproduced by G-CONF on the frozen `jca` (`agree 66, disagree 0, not-derived 14,
unrecorded 0`). Verdict totals: 42 `CRYSL-NAO-IMPLEMENTADO`, 22 `IGUAL`, 14 `NAO-DERIVADO`,
2 `MOP-MAIS-PERMISSIVO`. These **replace the 59-row api30 table and its 30/9/8/5/4/3
totals** wherever those are quoted, which in turn had replaced a 74-row summary. The two
`MOP-MAIS-PERMISSIVO` rows are the frozen set's own spelling variants
(`MacSpec.mop:12`, `SecretKeySpecSpec.mop:19`), recorded as such.

The acceptance measurement of the re-anchoring — both sides of it — is
`evidence/d15_c5_replay.md`: the 5,892 `MD5`/`SHA-1` rows, the 103 `SSL` and the 4
`NONEwithRSA` of the published corpus are accused again, **and** the `TLS` 8,648,
`AndroidKeyStore` 2,005, `X509` 643 and `SHA256WITHRSA` 4 stay silent.


## Site census

Counted from the files with `scripts/gh104_mop_lint.py`'s own site parser:

| | three-argument | four-argument | commented | live total |
|---|---|---|---|---|
| frozen `jca` (the seed) | 25 | 25 | 1 | **50** |
| `jca_android` after Group 2 | 25 | 25 | 1 | **50** |
| `jca_android` today | 0 | **115** | 0 | **115** |

**Through Group 2 the census was the seed's, unchanged, and there was no difference to explain.**
That followed from D-11: the successor keeps every event the seed declares, predicates included,
and the allow-list re-transcription of task 2.4 changed which *values* a condition admits without
deleting a report site. The one site that could have been lost is `SecretKeySpecSpec.c3`, whose
condition had an allow-list half and a predicate half; `generated/api30/SecretKeySpec.cryptsl`
declares `length(keyMaterial) >= off + len` and nothing about the algorithm, so the algorithm half
left and the randomisation predicate — and with it the accusation and its report site — stayed.
(D-15 restored that half against `SecretKeySpec.crysl:18`, and the census above is the Group-2
one, read as history.)

**Groups 5 to 7 more than doubled it, and that is the difference to explain.** The successor now
holds **115** live sites against the seed's 50, and the growth is the predicate wiring itself: a
clause that was carried as an unread `setProperty` in the seed becomes, in the successor, a read
with a producer and an accusation of its own when the read answers *violated*. `IvChainJunction`
alone contributes 14 sites, `SignatureSpec` 11 and `KeyGeneratorSpec` 8. The three-argument form is
gone entirely: Group 7 gave every site an envelope, so all 115 are four-argument and the set holds
no commented report.

**The count moved twice after Group 7, and both moves were accusations the set was missing.** It
stood at 112 through Group 8. `5bc5c893` took it to 114: repairing the value lists put back the
`SecretKeySpec` construction accusers `SECRETKEYSPEC-ALG-00` and `SECRETKEYSPEC-ALG-01`, which the
generated lists had admitted. `cc6d64bc` took it to 115 with `SSLCONTEXT-FORB-00`, task 9.9's
accuser for `SSLContext.getDefault()` -- FORBIDDEN in both oracles, and until then a call this set
watched in silence from end to end. Nothing was removed on either side of those two, so 115 is the
seed's 50 plus the wiring plus these two repairs, and every one of the three numbers above can be
recounted from the files.

The five purely predicate-guarded accusers -- `IvParameterSpec` c3/c4, `PBEKeySpecSpec` err2/err3
and `SecureRandomSpec` setSeed3 -- kept their accusations and lost their events. An earlier revision
of this change predicted 44 or 45 live sites by subtracting exactly those five; the prediction died
with the removal it assumed, and then Group 3 fused rather than deleted them (INV-INS-135), which
is a different thing: each was a twin matching the same call as a legitimate event with the guard
negated, so it sat outside the automaton with an all-`fail` transition row and one bad call fired
up to three accusers at once. The fusion moves the guard into the surviving event's body, where it
decomposes per clause -- one report per violated clause, which is what the twins emitted between
them -- and takes the ordering noise away with it. Where each landed can be read off `codes.csv`:
`SECURERANDOM-CONSTR-00`/`-NOBS-00` are emitted from `setSeed2` and not from a `setSeed3`,
`PBEKEYSPEC-CONSTR-00`/`-CONSTR-02`/`-NOBS-01` from `c1`, and `IvParameterSpec`'s two pairs from
`c1` and `c2`. The `-NOBS-` half of each pair is the other thing that changed: a predicate read
that answers *not observed* is a different claim from one that answers *violated*, and since
Group 4 the set says which of the two it saw instead of merging them into one accusation.

The 51st `new ErrorDescription(` of the seed was the commented `g4` report of `MessageDigestSpec`
(`:58` of the seed). It was counted apart because it emitted nothing, and it stayed commented
through Group 7. Group 8 task 8.14 revived it: the harness classified the change `introduced` on
`data/gh104/traces/MessageDigestSpec-unlisted-only.txt` and `unchanged` on the other 62 traces, so
the accusation it adds is measured rather than assumed. The set has no commented report site.

Of the seed's 50, the 25 three-argument sites were the 21 `@fail`/`@match1` handlers plus
`IvParameterSpec` c3/c4 and `PBEKeySpecSpec`'s two `FORBIDDEN` sites, and the 25 four-argument
sites were the value accusers. Group 7 gave every site an envelope, so the three-argument count is
zero and every one of the successor's 115 rows in `codes.csv` names a four-argument site.

**Group 8 left the seed-inherited total where it found it, by two changes that cancel.** Task 8.6 removes the
`UnsafeAlgorithm` report inside `KeyPairGeneratorSpec`'s `init1`, whose branch is unreachable — the
`condition(validate(keySize))` compiles to an early return and `validate` accepts exactly the
members of `safeAlgorithms`, so the guarded `!matches(...)` is false whenever it is evaluated — and
`KEYPAIRGENERATOR-ALG-00` leaves `codes.csv` with it. Task 8.14 revives the commented `g4` report of
`MessageDigestSpec` in the envelope form, which adds `MESSAGEDIGEST-ALG-02`. So the four-argument
count is 25 either way, the commented count falls to **zero**, and the set holds no report it does
not emit. Task 8.3 deletes `MessageDigestSpec`'s `reset` event, which had an empty body and so no
row to move.

### `codes.csv`, the set's failure codes

The set's report sites carry a failure code from Group 7 on, and `codes.csv` (inside the
specification directory, not here) is the table of them: one row per live site, header
`spec,code,error_type,site_kind,event,file_line`. A code is `<SPEC>-<KIND>-<NN>`, where `<SPEC>` is
the specification's name without its `Spec` suffix in upper case (`MESSAGEDIGEST`,
`TRUSTMANAGERFACTORY`, `PBEKEYSPEC`) — derived mechanically, so no abbreviation table exists for two
readers to disagree over — and `<KIND>` is the clause family the `ErrorType` implies: `ORDER`,
`ALG`, `CONSTR`, `KEYSIZE`, `KSTYPE`, `PROTO`, `FORB`. The table is bijective with the census above:
**115 rows, 115 live sites**, and the message gate fails on either half of that going wrong. It
also checks the anchor: since task 7.2 a `code-anchor` check compares each row's `file_line` with
the line the code is actually emitted from, because the two times a batch re-anchored the file by
script it moved anchors nobody had noticed.

## Generating the set, and the heap it takes

The whole set generates through the real pipeline —
`uv run rv-monitor-generator generate --specs-dir <set> --output <dir>` — in **79 s** and **77 s**
over two runs, at a peak resident set of **5.4 GB** and **4.5 GB** across the process tree. The two
runs produced a byte-identical `MultiSpec_1RuntimeMonitor.java` of 17,087 lines, so the generation
is deterministic.

**The gates read the monitor; only the harness compiles it.** Every structural gate, G-CONF
and G-ORDER included, reads `MultiSpec_1RuntimeMonitor.java` as text — transition tables,
event names, list literals. None of them invokes a compiler, so a set can pass all of them
and still produce a monitor that does not build. Task 11.9 hit this twice in a row, both times
on the same mechanism: **the generator merges every specification into one file and dedupes
imports by class name, keeping the first form it sees.** `CipherSpec.mop` written with both
`import br.unb.cic.mop.jca.util.CipherTransformationUtil;` and
`import static ...CipherTransformationUtil.*;` lost the static one and failed on `isValid`;
fixing that in `CipherSpec.mop` alone then broke `IvChainJunction.mop`, which imported the
same class plainly and called `CipherTransformationUtil.mode(...)` qualified. Both files now
use the static form and bare calls.

Two things follow. **Every `.mop` of a set that names the same utility must import it the same
way** — the constraint is set-wide, not per file, because the output is one file. And
INV-INS-124's rule that no allow-list, automaton or message task closes without committed
harness output is not bureaucracy: the harness is the only instrument in the set that compiles
what it generates. A green gate suite proves the gate's own link and no other.

**And the harness only sees what it compares.** The instrument has the same failure mode one
level up, and D-15 walked into it. Its first run reported `unchanged 132 · moved 9` and the
right answer over the same two snapshots is `unchanged 119 · moved 22`; thirteen traces were
called unchanged by a comparison that could not represent the difference. Two causes, both
repaired in task 11.11. `TraceRunner.envelope()` scanned the accumulated `ErrorCollector` set —
unordered, and accumulated over the whole trace — and returned the *first* error of the
specification, so a second accusation at one event was dropped and the envelope written could
belong to an event that had already fired; the symptom sat in plain sight in the committed
evidence, where all four `MacSpec-hmacpbesha1` envelopes carry `ev=i1` inside the message while
the outer `ev=` reads `update`, `updateBytes`, `f1`. And `classify()` compared accusing event
*names*, so a repair that adds an accusation at an already-accused event — `SignatureSpec.i1`
raises `SIGNATURE-ALG-00` and `SIGNATURE-NOBS-00` from two independent `if`s — was invisible by
construction. The comparison is now over `(event, code)` pairs, which is the accusation's
identity without being its prose.

The general form is the one this file keeps arriving at from different directions: **an
instrument that has stopped distinguishing must say so rather than answer "no difference".**
`unrecorded` became a finding for the same reason when the constraint-table keys moved. What
makes this instance worth writing down is that the harness self-test did not catch it and could
not: each of its three mutations moves an accusation to an event that was previously *silent*,
which is exactly the case a name-only comparison still gets right.

**No launcher passes `-Xmx`.** `javamop/target/release/javamop/javamop/bin/javamop:18` invokes a
bare `java`; `rv-monitor`'s launcher and the child that `LogicRepositoryConnector.java:149-154`
spawns each pass `-Xss1g` and nothing else. Both JVMs therefore run at the default ergonomic heap,
which on a machine of this size is a quarter of physical memory and is far more than the set needs.

**And there is no environment lever for it, measured.** `_JAVA_OPTIONS=-Xmx4g` does reach both
JVMs — `command.py:180` calls `Popen` with no `env=`, and the child is spawned with `envp=null` —
but it aborts the generation: the JVM prints `Picked up _JAVA_OPTIONS: -Xmx4g` on **stderr**, and
`rv_android_core.util.utils.execute_command` raises whenever stderr is non-empty, even at `code=0`.
The run fails after JavaMOP has written its `.aj` and before the `.rvm` files are moved, which
leaves 24 generated `.rvm` inside the specification directory; a successful run moves them out
again. This is INV-INS-145 turned around — there the exit code is falsely green, here it is falsely
red — and it is recorded rather than repaired, because widening `execute_command` would blind the
generator to the masked child OOM the invariant exists for (researcher decision, 2026-08-23).

**Inspect the artifact, never the exit code** (INV-INS-145). The set's alphabet ceiling is
`CipherSpec`, at exactly **17 events** and therefore at zero headroom: eighteen raise
`StackOverflowError` in the parent's enable-set parser at any heap. The next largest is
`SecureRandomSpec` at 13, and the junction `IvChainJunction` entered at 7.

## Records in this directory

| file | what it records |
|---|---|
| `divergence_record.csv` | one entry per hunk of the successor set against the frozen `jca` seed, plus the two registered exceptions to literal transcription (`EC`, the four `SHA*withECDSA`). Group 7 added the kind `message`: a report site rewritten as a `v=1` envelope. |
| `conformance_record.csv` | one row per specification against **the** expert rule (one `rule` column, one meaning, since task 11.4): transcription verdicts, withdrawals, deferred constants, declared costs, and the divergences measured but not repaired — including the nine `guard-on-field` rows Group 7 declares and Group 8 task 8.16 repairs. |
| `alias_table.csv` | the Conscrypt `android11-release` alias table (175 rows, one per `Alg.Alias` registration of the pinned provider file), carried as code by `ConscryptAliasTable`. |
| `constraint_table.csv` | one row per expert `CONSTRAINTS` clause of the paired rules plus one per `.mop` value test with no clause behind it (80 rows since D-15). |
| `gate_allowlist.csv` | the remaining gate hits with a reason and the task that owns each. Since task 7.6 it also carries the ordering divergences the set keeps on purpose -- nine when 7.6 wrote them, **eight** today: task 9.11 repaired `KeyPairSpec`'s, and task 9.16 replaced `KeyStoreSpec`'s witness with one the set really rejects. `gh105_order_gate.py` reads the same file, and a row with an empty reason allows nothing. |
| `predicate_graph.csv` | one row per predicate site: the clause it serves, the mechanism, and the disposition. It is what replaced byte-equality against the seed as the successor's predicate accounting. |
| `order_alphabet_map_expert.csv` | which `.mop` event is which symbol of the **expert** rule, per specification, matched by signature and never by name (task 11.2). This is the file `gh105_order_gate.py` reads. Never inferred: without a complete mapping G-ORDER skips and says so. |
| `order_alphabet_map.csv` | the same associations against the withdrawn api30 rules. **Nothing reads it** (INV-INS-118); it is kept as the pre-D-16 record and is not a fallback. |
| `order_alphabet_map_delta.csv` | what the substitution of oracle cost the map, association by association (task 11.2). |
| `conformance_record_delta.csv` | the clause-by-clause census of the two catalogues: 35 pairs, 17 withdrawals, 43 restorations, and the three inverted comparisons (task 11.4). |
| `predicate_ledger.csv`, `predicate_ledger_delta.csv` | the predicate clauses of the 49 expert rules with their dispositions, and the delta against the api30-derived ledger (task 11.1). |
