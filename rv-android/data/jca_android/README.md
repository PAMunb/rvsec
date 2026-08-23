# `jca_android` — the successor specification set

This directory holds the records of the specification set that `--specification-set jca_android`
resolves to from gh104 on: `rvsec/rvsec-mop/src/main/resources/jca_android/`, seeded from the frozen
`jca` Java set and shaped by one mechanical pass: every allow-list re-transcribed from
`MetaCrySL/generated/api30/`, read through the normalisation rule below. The seed's predicate
machinery travels with it untouched — see *What the successor set contains*.

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

Twenty-four `.mop` files and `codes.csv`, and nothing else. It was twenty-three until Group 5
added `IvChainJunction.mop`, the junction specification that carries a chain no single API's
rule states. `codes.csv` (header
`spec,code,error_type,site_kind,event,file_line`) is the table of failure codes the set's
envelopes emit; it is the **only** non-`.mop` file of the directory. The seed directory
`jca/` also holds `MultiSpec_1MonitorAspect.aj`, a gitignored leftover of a generation run
that is not tracked and does not travel with the seed.

That count includes `RandomStringPassword.mop` and `SecretKeySpec.mop`, the two pure
predicate propagators: `grep -c "new ErrorDescription("` returns 0 for both and neither has
a `@fail`, so each exists only to write a `Property` another specification's `condition()`
reads. An earlier revision of this change deleted them along with the predicate machinery
they feed; that decision is withdrawn (design D-11), so they still have work to do and
removing either would silently disarm a `condition()` elsewhere in the set.

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

An allow-list of this set is the `CONSTRAINTS` clause of its api30 rule and nothing else, so
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
idiom, `SecretKeySpecSpec`'s `.toUpperCase()`, needs no replacement: its list has no api30
clause behind it and leaves the set entirely (MOP-SEM-BASE).

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
149 rows are in services one of the 21 rule-paired specifications covers — 21, not 24: it is the
count of `.mop` files with a matching api30 rule, which is what `conformance_record.csv` keys on,
and not the size of the set. The other 9 rows are in services with no specification
(`AlgorithmParameters` 8, `SecretKeyFactory` 1) and are kept, with their flag, so the extraction
stays complete.

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

## Site census

Counted from the files with `scripts/gh104_mop_lint.py`'s own site parser:

| | three-argument | four-argument | commented | live total |
|---|---|---|---|---|
| frozen `jca` (the seed) | 25 | 25 | 1 | **50** |
| `jca_android` after Group 2 | 25 | 25 | 1 | **50** |
| `jca_android` today | 0 | **112** | 0 | **112** |

**Through Group 2 the census was the seed's, unchanged, and there was no difference to explain.**
That followed from D-11: the successor keeps every event the seed declares, predicates included,
and the allow-list re-transcription of task 2.4 changed which *values* a condition admits without
deleting a report site. The one site that could have been lost is `SecretKeySpecSpec.c3`, whose
condition had an allow-list half and a predicate half; `generated/api30/SecretKeySpec.cryptsl`
declares `length(keyMaterial) >= off + len` and nothing about the algorithm, so the algorithm half
left and the randomisation predicate — and with it the accusation and its report site — stayed.

**Groups 5 to 7 more than doubled it, and that is the difference to explain.** The successor now
holds **112** live sites against the seed's 50, and the growth is the predicate wiring itself: a
clause that was carried as an unread `setProperty` in the seed becomes, in the successor, a read
with a producer and an accusation of its own when the read answers *violated*. `IvChainJunction`
alone contributes 14 sites, `SignatureSpec` 11 and `KeyGeneratorSpec` 8. The three-argument form is
gone entirely: Group 7 gave every site an envelope, so all 112 are four-argument and the set holds
no commented report.

The five purely predicate-guarded accusers are likewise all alive: `IvParameterSpec` c3/c4,
`PBEKeySpecSpec` err2/err3 and `SecureRandomSpec` setSeed3. An earlier revision of this change
predicted 44 or 45 live sites by subtracting exactly those six; the prediction died with the
removal it assumed.

The 51st `new ErrorDescription(` of the seed was the commented `g4` report of `MessageDigestSpec`
(`:58` of the seed). It was counted apart because it emitted nothing, and it stayed commented
through Group 7. Group 8 task 8.14 revived it: the harness classified the change `introduced` on
`data/gh104/traces/MessageDigestSpec-unlisted-only.txt` and `unchanged` on the other 62 traces, so
the accusation it adds is measured rather than assumed. The set has no commented report site.

Of the seed's 50, the 25 three-argument sites were the 21 `@fail`/`@match1` handlers plus
`IvParameterSpec` c3/c4 and `PBEKeySpecSpec`'s two `FORBIDDEN` sites, and the 25 four-argument
sites were the value accusers. Group 7 gave every site an envelope, so the three-argument count is
zero and every one of the successor's 112 rows in `codes.csv` names a four-argument site.

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
**112 rows, 112 live sites**, and the message gate fails on either half of that going wrong. It
also checks the anchor: since task 7.2 a `code-anchor` check compares each row's `file_line` with
the line the code is actually emitted from, because the two times a batch re-anchored the file by
script it moved anchors nobody had noticed.

## Generating the set, and the heap it takes

The whole set generates through the real pipeline —
`uv run rv-monitor-generator generate --specs-dir <set> --output <dir>` — in **79 s** and **77 s**
over two runs, at a peak resident set of **5.4 GB** and **4.5 GB** across the process tree. The two
runs produced a byte-identical `MultiSpec_1RuntimeMonitor.java` of 17,087 lines, so the generation
is deterministic.

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
| `conformance_record.csv` | one row per specification against its api30 rule: transcription verdicts, deferred constants, declared costs, and the divergences measured but not repaired — including the nine `guard-on-field` rows Group 7 declares and Group 8 task 8.16 repairs. |
| `alias_table.csv` | the Conscrypt `android11-release` alias table (158 rows), carried as code by `ConscryptAliasTable`. |
| `constraint_table.csv` | one row per api30 `CONSTRAINTS` clause of the 21 paired rules plus one per `.mop` value test with no clause behind it. |
| `gate_allowlist.csv` | the remaining gate hits with a reason and the task that owns each. Since task 7.6 it also carries the nine ordering divergences the set keeps on purpose, and `gh105_order_gate.py` reads it: a row with an empty reason allows nothing. |
| `predicate_graph.csv` | one row per predicate site: the clause it serves, the mechanism, and the disposition. It is what replaced byte-equality against the seed as the successor's predicate accounting. |
| `order_alphabet_map.csv` | which `.mop` event is which symbol of the api30 rule, per specification. Never inferred: without a complete mapping G-ORDER skips and says so. |
