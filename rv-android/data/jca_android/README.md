# `jca_android` — the successor specification set

This directory holds the records of the specification set that `--specification-set jca_android`
resolves to from gh104 on: `rvsec/rvsec-mop/src/main/resources/jca_android/`, seeded from the frozen
`jca` Java set and shaped by three mechanical passes (two pure predicate propagators deleted, every
use of `ExecutionContext` removed, every allow-list re-transcribed from `MetaCrySL/generated/api30/`).

The oracle of the set is the already-generated MetaCrySL api30 rules under
`MetaCrySL/generated/api30/`. MetaCrySL is read-only in gh104: where a generated rule is judged
defective, the judgement is a row of `divergence_record.csv`, never an edit upstream.

## Freeze items

| item | value | what it pins |
|---|---|---|
| `pre-rename-head` | `a3e6a1651cc63d83525fcbb42c0cd5f659ef463e` | the Java tree's `HEAD` immediately before the `git mv` of task 2.1. Task 10.1 asserts the archival is a pure rename **against this SHA**, and it is also the read-only base of `AndroidCipherTransformationUtil.java`, which does not exist at `7e7acb69` (gh101 added it). |
| `jca` freeze base | `7e7acb69` | `rvsec-mop/src/main/resources/jca/` and `CipherTransformationUtil.java` are byte-identical to it and stay so (gh101 D-S0, INV-INS-109). |

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

Twenty-one `.mop` files and `codes.csv`, and nothing else. `codes.csv` (header
`spec,code,error_type,site_kind,event,file_line`) is the table of failure codes the set's
envelopes emit; it is the **only** non-`.mop` file of the directory. The seed directory
`jca/` also holds `MultiSpec_1MonitorAspect.aj`, a gitignored leftover of a generation run
that is not tracked and does not travel with the seed.

The two files that leave are `RandomStringPassword.mop` and `SecretKeySpec.mop`, pure
predicate propagators: `grep -c "new ErrorDescription("` returns 0 for both and neither has
a `@fail`, so each existed only to write a `Property` another specification read. With
predicates gone they detect nothing, and deleting them costs zero report sites.

The `ExecutionContext` keying ruling of gh101 (equality, `e204e2a4`) is **moot for this
set**: it references `ExecutionContext` at no site at all, which the G-PRED gate
(`tests/parity/test_gh104_specset_gates.py::test_jca_android_has_no_execution_context`)
checks as a grep over the 21 files, with the frozen `jca`'s 134 occurrences as the negative
control.

## The normalisation rule

An allow-list of this set is the `CONSTRAINTS` clause of its api30 rule and nothing else, so
a value the application spells differently would not match it. The set therefore declares
**one** normalisation rule and applies it uniformly across the 21:

> **Comparison is case-insensitive, and an observed value matches a list entry when a row of
> `alias_table.csv` maps it to that entry.**

Both halves go through a single call to `ConscryptAliasTable`
(`rvsec-core/src/main/java/br/unb/cic/mop/jca/util/`), which every `jca_android`
specification names in its check. That one call replaces two inconsistent idioms the seed
carried by accident: case-sensitive `contains()` in `Mac`, `Signature`, `SecureRandom`,
`KeyGenerator`, `TrustManagerFactory`, `KeyManagerFactory`, `KeyStore` and
`KeyPairGenerator`, and `.toUpperCase()` in `MessageDigest`, `SSLContext` and
`SecretKeySpec` — under which the same string was a misuse in one specification and not in
another.

The table is **not read at run time**. A monitor woven into an APK has no filesystem
contract with this repository, so `ConscryptAliasTable` carries the table as code and
`alias_table.csv` is the auditable registry of the same rows.
`ConscryptAliasTableTest` asserts the two are equal row for row — all 158 rows, every
column — so the record and the instrument cannot drift. No `.mop` of the frozen `jca` names
that class, which is what keeps the published measurements reproducible: nothing here can
move a `jca` verdict.

### `alias_table.csv`

158 rows, extracted from Conscrypt branch `android11-release`, path
`common/src/main/java/org/conscrypt/OpenSSLProvider.java` (607 lines, 175 `Alg.Alias.*`
registrations), kept locally and gitignored at `backup/gh104-analise/OpenSSLProvider.java`.
149 rows are in services one of the 21 specifications covers; 9 are in services with no
specification (`AlgorithmParameters` 8, `SecretKeyFactory` 1) and are kept, with their flag,
so the extraction stays complete.

`in_api30_allowlist` has exactly one definition: **`yes` when the row's canonical name is an
entry of the successor set's allow-list for that service, after the two recorded divergences
(`EC` kept in `KeyPairGenerator`, the four `SHA*withECDSA` added to `Signature`).** Counts
under that definition:

| | rows |
|---|---|
| `yes` | **124** |
| of which in services the set covers | **124** (all of them) |
| `no` | **34** |

The `no` rows are the 8 `AlgorithmParameters` rows, the 1 `SecretKeyFactory` row and 25 of
the 29 `Cipher` rows. A service the set does not cover has no allow-list for a canonical to
be an entry of, so its rows are `no` by construction — which is why the six rows the backup
extraction flagged `yes` there (`AlgorithmParameters` → `AES` ×3 and → `DESEDE` ×2,
`SecretKeyFactory` → `DESEDE`) are `no` here. Sixteen `SHA*withECDSA` rows go the other way,
`no` → `yes`, because task 2.7 adds that family.

For `Cipher`, "the allow-list" means the algorithm set
`part(0,"/",transformation) in {…}` of `Cipher.cryptsl:121`, transcribed as `ALGORITHMS` in
`Api30CipherTransformationUtil`. A canonical that names a bare algorithm of that set is
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
1 app, 1 misuse) carries no hyphen in `SHA1`; api30 declares
`OAEPwithSHA-1andMGF1Padding`, Conscrypt registers
`RSA/ECB/OAEPWithSHA-1AndMGF1Padding` (`:338`) and the alias
`RSA/None/OAEPWithSHA-1AndMGF1Padding` (`:339-340`), both hyphenated, and the unhyphenated
spelling appears in no registration of that file. There is therefore no provider line a row
could cite, and a row without one would break the per-entry pointer requirement of
INV-INS-127 for one value. The case is a `behavioural` entry of `divergence_record.csv`
instead, and `Api30CipherTransformationUtil` deliberately does not fold the hyphen.

## The api30 transcription, and the three departures from it

Every allow-list is the `CONSTRAINTS` clause of the matching rule in
`MetaCrySL/generated/api30/`, transcribed literally. One oracle, one anchor, no per-clause
judgement: where a value used to be rejected on a "recommendation" reading, the rejection
goes. Exactly three kinds of departure are admissible, and each is recorded:

1. **An entry of the normalisation table** — `alias_table.csv`, and nowhere else.
2. **A value the rule omits that the platform provably carries** — `divergence_record.csv`,
   kind `api30-omits`, cited to a platform source. Exactly two exist: `EC` in
   `KeyPairGenerator` (kept from the seed against the literal rule) and the four
   `SHA*withECDSA` in `Signature` (added). A third candidate found later is a question for
   the researcher, not a third entry.
3. **A clause the rule declares and this change does not begin to check** —
   `conformance_record.csv`, verdict `deferred-constant`. There are **30** of them, one per
   `CRYSL-NAO-IMPLEMENTADO` row of `constraint_table.csv`.

A constant that is neither transcribed nor deferred is a defect, and G-CONF fails on it.

`constraint_table.csv` holds **59 rows**: 55 api30 `CONSTRAINTS` clauses of the 21 paired
rules plus 4 `.mop` value tests with no clause behind them. Its verdict totals — 30
`CRYSL-NAO-IMPLEMENTADO`, 9 `MOP-MAIS-PERMISSIVO`, 8 `IGUAL`, 5 `DIVERGENTE`, 4
`MOP-SEM-BASE`, 3 `MOP-MAIS-RESTRITIVO` — **replace the 74 = 30/14/13/7/7/3 summary**
wherever that summary is quoted. That summary had no committed row table behind it and an
independent reconstruction reached 65; this table is the one G-CONF reproduces on the frozen
`jca`.

Two consequences of the single oracle are decisions, recorded in `conformance_record.csv`
and not open questions. `MessageDigest`: api30 admits `MD5` and `SHA-1`, so **5,892** of the
published dataset's 6,048 `MessageDigestSpec`/`UnsafeAlgorithm` rows stop being reported
(3,552 `MD5`, 2,340 `SHA-1`/`SHA1`/`SHA`) — 97.4 % of that specification's `UnsafeAlgorithm`
reports and 6.1 % of the 97,018-row corpus. `Signature`: the same rule accepts `MD5withRSA`,
`SHA1withRSA` and `SHA1withDSA`. In `jca_android` the `ErrorType` `UnsafeAlgorithm`
therefore means "value outside the api30 allow-list of the platform", not "cryptographically
insecure"; the name is kept for continuity with `jca` and the meaning shift is declared.

## Records in this directory

| file | what it records |
|---|---|
| `divergence_record.csv` | one entry per hunk of the successor set against the frozen `jca` seed, plus the two registered exceptions to literal transcription (`EC`, the four `SHA*withECDSA`). |
| `conformance_record.csv` | one row per specification against its api30 rule: transcription verdicts, deferred constants, declared costs, and the divergences measured but not repaired. |
| `alias_table.csv` | the Conscrypt `android11-release` alias table (158 rows), carried as code by `ConscryptAliasTable`. |
| `predicate_removal.csv` | the 55 sites the predicate removal deleted, with the accusation each used to raise. Not to be confused with gh101's `predicate_omissions.csv`, which records a different thing — a `Property` written and never read. This set writes none (INV-INS-128). |
| `constraint_table.csv` | one row per api30 `CONSTRAINTS` clause of the 21 paired rules plus one per `.mop` value test with no clause behind it. |
| `gate_allowlist.csv` | the remaining gate hits with a reason and the task that owns each. |
