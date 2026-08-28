# What the frozen `jca` set knowingly retains

The `jca` specification set produced published measurements. That makes it an
experimental instrument rather than merely code: altering it after the fact
invalidates the reproduction of every result computed with it. It is frozen at
commit `7e7acb69`, and every correction this change makes lands in `jca_android`
alone.

A defect left standing for reproducibility is still a defect. This file is where
each one is written down, so the set stays reproducible without anyone being able
to mistake it for correct. Nothing here is a proposal — each entry is a repair
that was made in the derived set and deliberately **not** made here.

Three consequences follow — the first two from the freeze, the third from what
the derived set was derived against — and any report using either set has to
carry all three:

1. Results measured under `jca` reproduce exactly, and remain wrong in the ways
   listed below.
2. The two sets no longer differ along a single axis. A difference in outcome
   between them used to be attributable to the platform allow-list alone; it can
   now come from the allow-list **or** from a repair present only in the derived
   set. No measurement decomposes an observed difference after the fact. The
   divergence record keeps the differences named; it cannot make them separable.
3. The derived profile models **availability, not recommendation**. Its
   allow-lists come from rules generated against what Android API 30 publishes,
   and the platform publishes weak algorithms: the derived `MessageDigest` rule
   admits `MD5` and `SHA-1`, so `MessageDigestSpec` reports fewer violations than
   the frozen one on the same corpus while checking the same code no more
   strictly. A fall in the violation count across the sets is therefore not
   evidence of better analysed code, and the direction of the effect varies by
   specification — see the conformance verdicts in
   [`README.md`](README.md), where ten of the 23 are `anchored`.

---

## Cipher transformation tables (task 2.7)

`rvsec-core/.../mop/jca/util/CipherTransformationUtil.java`, which
`jca/CipherSpec.mop` calls through a static import, is inside the freeze. The
derived set gained `AndroidCipherTransformationUtil` beside it; the original was
not edited, so the following stand.

**The substantive gap.** The frozen tables cover two algorithm families, AES and
RSA, where the generated API 30 rule admits eight. The `jca` set therefore
contradicts itself in the same way the derived set did until this change:
`KeyGeneratorSpec` accepts `ChaCha20`, `DESede`, `BLOWFISH` and `ARC4`, while any
`Cipher.getInstance` over one of them is reported as a misuse. It also rejects
`AES/ECB/...` outright — its mode list carries no `ECB` — which the corpus
contains.

**Two hygiene defects, in the same file:**

| site | defect |
|---|---|
| `:35`, `:36` | `padding.put("CBC", …)` and `padding.put("PCBC", …)` each list `"PKCS5PADDING"` twice. Inert, since the list is only ever searched, but it misstates the table |
| `:50-53` | a commented-out `rsaECBPaddings` block duplicating the live code at `:55-62`, kept beside it |

**One behaviour that is not a defect and was carried into the derived class on
purpose:** the frozen utility folds the padding to upper case
(`pad(transformation).toUpperCase()`). One call site in the corpus,
`Cipher.getInstance("AES/CBC/PKCS5PADDING")`, is accepted only because of it. A
literal transcription of the generated rule would have regressed it, so the
derived class folds case on all three components — see
[`algorithm_naming.md`](algorithm_naming.md).

---

## Events that accuse unconditionally (task 3.5)

An event declared in a specification and absent from that specification's `fsm`
receives a transition row sending every state to `fail`. It does not go
unmodelled — it becomes an unconditional accuser, emitting
`InvalidSequenceOfMethodCalls` on a call that may be perfectly ordered.

Generating monitors from both sets and reading the transition tables gives the
exact count: **the frozen set has 18 such events**, not the two the change
originally named. `scripts/gh101_monitor_transition_check.py` is the check.

**The two the derived set repairs, and `jca` keeps:**

| specification | event | frozen row | derived row |
|---|---|---|---|
| `TrustManagerFactorySpec` | `g3` | `{3,3,3,3}` | `{0,3,3,3}` |
| `SSLContextSpec` | `unsafe_protocol` | `{3,3,3,3}` | `{0,3,3,3}` |

Both were inert in `jca` for a second reason — a binding defect kept them out of
the monitored object's parameter slice — so the frozen set does not currently
emit the spurious report from them. The empty label the campaign shows alongside
them (`but found .`: 51 `UnsafeProtocol` events for `SSLContextSpec`, 8,371
`UnsafeAlgorithm` events for `TrustManagerFactorySpec`) was long attributed to the
same binding defect. **Task 8.1 measured it and the attribution was wrong** — the
empty label came from the weaver, not from the specification. The section
"What Group 8 measured" below carries the measurement and the corrected account.

**The sixteen the derived set also repairs, in eight further specifications:**
`IvParameterSpecSpec.c3`/`c4`, `KeyPairGeneratorSpec.initError`,
`MessageDigestSpec.reset`, `PBEKeySpecSpec.f1`/`f2`/`err1`/`err2`/`err3`,
`PBEParameterSpecSpec.c3`, `SecretKeySpecSpec.c3`/`c4`,
`SecureRandomSpec.c3`/`g4`/`setSeed3`, `SignatureSpec.g3`.

Fifteen of them share one shape: the violating branch of an event the CrySL rule
states once — the translation split `c1: PBEKeySpec(password, salt,
iterationCount, keylength)` into a conforming `c1` and three violating `err1`,
`err2`, `err3`, and only the conforming half reached the automaton. Each reports
in its own body. Unlike the two above, most of them **do** bind the monitored
object, so in `jca` every one of them fires a real report *and* a sequence
violation on top of it.

The sixteenth, `MessageDigestSpec.reset`, is not of that shape. No generated rule
models `reset`: the API 30 `MessageDigest` rule declares `getInstance`, `update`
and `digest` and nothing else, so CogniCrypt ignores `reset()` calls entirely. Its
`.mop` event has an empty body and is absent from the `ere`, so the all-`fail` row
is the whole of its effect — a legitimate API call becomes a sequence violation
and the monitor is reset. The derived set deletes the event; `jca` keeps it.

What the specifications carrying these events are worth in the published dataset,
recomputed from `errors.csv` (the error type lives in `unique_msg`, not in
`message`):

| origin | `InvalidSequenceOfMethodCalls` events | of that category | of all 97,018 events |
|---|---:|---:|---:|
| the 8 specifications carrying the sixteen | 23,292 | 32.9% | 24.0% |
| the 2 repaired first | 26,525 | 37.5% | 27.3% |
| **together** | **49,817** | **70.4%** | **51.3%** |

**Read this as a ceiling, not as a cause.** 70.4% of every
`InvalidSequenceOfMethodCalls` in the published dataset comes from ten
specifications, and every one of those ten carries an unconditional accuser. It
does not follow that the eighteen events produced them: the `@fail` handler emits
no message naming the event that triggered it, so the published record cannot
separate an error caused by one of the eighteen from an error caused by the same
specification's language being left legitimately. `MessageDigestSpec` also accuses
`digest()` with no preceding `update()`, which is ordinary code and has nothing to
do with `reset`. Splitting the 49,817 would require re-measuring the corpus with
the repaired set, which no change has yet done.

What the number does establish is that the dominant error type of the dataset is
concentrated exactly where the defect is, which is the mechanism behind the
co-emission the investigation measured — all 454 misuse tuples carrying at least
one `InvalidSequenceOfMethodCalls` line for the same tuple.

The frozen set keeps all eighteen. Its `InvalidSequenceOfMethodCalls` counts stay
exactly reproducible, and an unknown but bounded majority of them are not evidence
of a sequence violation.

---

## What Group 8 measured (tasks 8.1, 8.2)

D-S6 put the empirical check last because the two repaired specifications compare
their allow-list against a variable the weaver's wrapper collision prevented from
being written. That collision is issue #100's task 5.3, landed in `48b57fc5`. This
section is what running the instrument after it says.

**Design.** Two arms, everything held fixed except the specification set: the same
four APKs, the same repaired `dexlib2` weaver, `monkey`, 180 s, one repetition,
static analysis skipped. The APKs were chosen from the published campaign's own
`errors.csv` as the apps that carry the symptom — `com.owncloud.android_48000100`
and `eu.opencloud.android_9` are the only two apps in the dataset that produce the
empty label for *both* specifications, `de.luhmer.owncloudnewsreader_196` is the
most reliable producer of a non-empty one, and `com.etesync.syncadapter_20700`
carries both shapes. `apks_examples/cryptoapp.apk` cannot serve here: its DEX
contains no reference to `SSLContext` or `TrustManagerFactory` at all.

Monkey is stochastic and one repetition is not a rate, so nothing below is read as
a count. What is read is the **shape of a message at a named site**.

| | frozen `jca` | derived `jca_android` |
|---|---|---|
| `but found .`, over all eight logcats | **0** | **0** |
| `TrustManagerFactorySpec` `UnsafeAlgorithm` at `MemorizingTrustManager.java:282` | `expecting one of PKIX,SunX509 but found X509.` | `expecting one of PKIX but found X509.` |
| `SSLContextSpec` at `HttpClient.getOkHttpClient` | no line | `UnsatisfiedConstraint — init() requires trust managers established by a monitored TrustManagerFactory sequence.` |
| `TrustManagerFactorySpec` at `AdvancedX509TrustManager.findX509TrustManager` | no line | `InvalidSequenceOfMethodCalls` |

`com.etesync.syncadapter_20700` reached no monitored call in either arm — its
`monkey` run spent the budget in a `WebViewActivity`. It is reported rather than
dropped.

**8.2 is answered, and not by the observable the plan predicted.** The corrected
allow-list is observable: the same app, at the same line, is told
`expecting one of PKIX` where the frozen set says `expecting one of PKIX,SunX509`.
That is the derived `TrustManagerFactory` rule reaching the report.

**8.1 corrected a recorded attribution.** The plan expected the repair to be
visible as the label ceasing to be empty. It does not distinguish the sets,
because the empty label is gone from the **frozen** arm too. The cause was never
the binding defect; it was the wrapper collision, and the campaign's own
distribution confirms it. Both specifications advise one call site twice —
`TrustManagerFactory.getInstance(String)` carries `g1` and `g3`,
`SSLContext.getInstance(String)` carries `g1` and `unsafe_protocol` — and the
pre-`48b57fc5` weaver emitted one wrapper per call site, so one of each pair was
discarded. Which one survived decides the label:

| what survived | what the label reads | campaign |
|---|---|---|
| `g3` / `unsafe_protocol`, on an argument outside the allow-list | the argument | 643 `X509`, 8,648 `TLS` |
| the same, on an argument *inside* the allow-list — nothing is written | empty | 8,371 + 51 |

That is the whole distribution, with nothing left over. With every advice emitted,
the frozen `SSLContextSpec` writes `currentProtocol` at these sites and finds it
admissible under `{TLSv1.2, TLSv1.3}` — which is why its arm shows no line at all
while the derived arm, whose `init` reads three predicates the translation dropped,
shows one.

**The binding defect is real and its cost is not the empty label.** `g3` binds `k`
and `unsafe_protocol` binds nothing, so both live in the empty parameter slice, and
the frozen arm still delivered `but found X509.` to a monitor indexed by the
factory. Parametric monitoring is what carries it: a monitor for `{mf}` is created
by copying the maximal ancestor, and the empty slice is that ancestor. The value
therefore arrives — but it is the *last* value any factory wrote, not this one's.
The defect surfaces with two live factories, not with one, which is why a
single-object app cannot see it and why the repair is still the right one.

**What this does not say.** Nothing here measures a violation rate, and nothing
here compares the two sets' totals — task 7.6 already records that such a
comparison confounds the platform allow-list with the layer-2 repairs. The claim
is exactly the four rows of the table above.

---

## The residue both sets keep: a violating branch does not absorb what follows it (task 3b.11b)

This one is **not** a debt of the frozen set alone. It is present in both sets,
before and after this change, and Group 3b deliberately neither widens nor narrows
it.

Giving a violating event a place in the automaton stops it accusing on its own
call. It does not make the state it lands in accept the calls that legitimately
follow. `TrustManagerFactorySpec`'s `unsafeAlg`, added by task 3.1, admits `g1`,
`g2` and `g3` and nothing else, so `getInstance` with an unlisted algorithm
followed by `init` still reaches `fail`. The same holds for the `unsafeAlg` of
`CipherSpec` and `KeyManagerFactorySpec`, for the `g3*` prefix of `MacSpec`,
`KeyGeneratorSpec`, `KeyStoreSpec` and `MessageDigestSpec`, and for the seven
prefixes Group 3b adds. The accusation moves from the violating call to the next
one; it is not removed.

Repairing it would mean an absorbing state — the object is poisoned and nothing
afterwards can accuse it — which an `fsm` can express and an `ere` cannot. That
was considered and rejected for Group 3b (D-S9), on two grounds. It is stricter
than the repair Group 3 had already landed, so adopting it for some files would
leave the set with two repair philosophies. And it trades a false positive for a
false negative: after poisoning, a genuine misuse of the same object — `sign()`
with no preceding `update()` — goes unreported.

It affects thirteen specifications and predates this change, so it is recorded
here rather than settled inside a change scoped to INV-INS-110, which asks only
that a bound event have a row that is not `fail` from every state. No issue has
been opened for it; that is the user's call, like the two rule gaps left open in
[`algorithm_naming.md`](algorithm_naming.md).

---

## A debt this file never recorded, now repaired in shared code (gh69, issue #69)

Every entry above is a repair made in the derived set and deliberately withheld
from the frozen one. This entry is the opposite shape, and it is written here
because a ledger that only ever grows stops describing the instrument.

**What was wrong.** The `jca` set declares constructor pointcuts —
`call(SecureRandom.new(..))`, `call(SecretKeySpec.new(..))`,
`call(IvParameterSpec.new(..))` and eight more. `rvsec-mop-extractor` emitted
them with the literal method name `new`, which the pointcut grammar writes and
which no Soot method can carry: Soot names every constructor `<init>`. Those
targets therefore matched nothing, and had matched nothing since the extractor
was written. Eighteen signature rows, collapsing into **11 of the set's 68
`(class, method)` pairs**, were dead in the static layer. The published ruler had
never counted a single constructor call site — `new SecretKeySpec(...)` and
`new IvParameterSpec(...)` included, which are central to the misuses the set
exists to find.

This was never entered in this file because nobody knew. It was found in 2026-08
while gh69 was teaching the extractor a different construction, and it is a
defect of the **extractor**, not of any `.mop` file. Nothing under
`rvsec/rvsec-mop/src/main/resources/jca` was touched.

**Why repairing it is admissible under the freeze.** The doctrine this file
serves permits a repair to shared code when it applies equally to both sets and
its effect on the frozen set is *enumerated* rather than assumed absent. Both
conditions hold. The change is a keyword mapping in
`visitor/UsedJcaMethodsVisitor` — `new` becomes `<init>` — with no branch on
which specification set is active, and no GATOR-side change at all
(`TargetResolver` already compares names by equality;
`SignatureFileTargetSource` already accepts `<init>`). Withholding it was not an
option that preserved anything: the same defect is live in `jca_android`, and
suppressing it on one side only would have manufactured an asymmetry between the
sets that did not previously exist — the failure mode consequence 2 of this
file's preamble warns about.

**The enumeration.** Measured on `cryptoapp.apk` (106 app methods) under the
spark call graph, which is what production and
`scripts/check_signature_file_subset.py` use:

| axis | before | after | what moved |
|---|---|---|---|
| `reachable` | 55 | 55 | nothing — the repair adds targets, not call-graph nodes |
| `reachesTarget` | 32 | 33 | `CryptoUtils.createSecretKeyFromBytes` |
| `directlyReachesTarget` | 21 | 23 | `CryptoUtils.createSecretKeyFromBytes`, `CryptographyActivity.executeSecretKeyOperation` |

The direct axis was predicted from a dexdump before the run and the prediction
held: 11 constructor call sites (`SecretKeySpec` ×5, `IvParameterSpec` ×4,
`SecureRandom` ×2) across 10 methods, 8 of which other targets already flagged,
leaving exactly two. The transitive movement was deliberately **not** predicted —
a new seed propagates to its callers — and measurement gives one method, the
caller of `createSecretKeyFromBytes`.

The extractor's own triple does **not** move: `jca` stays at 120 signatures / 68
pairs / 22 owners, because those eighteen rows already existed and only the
emitted name changed.

**What this means for a published figure.** Any `cov_directly_reaches_target` or
`cov_reaches_target` computed from the frozen set before this repair understates
the numerator wherever the corpus constructs a JCA object — which is most of it.
The figures reproduce exactly as published, and they remain wrong in that
direction. A campaign comparing across the repair boundary has to say which side
each figure comes from; the fixtures in
`modules/rv-static-analysis/tests/resources/` and
`rvsec-gator/client/src/test/resources/baseline/` were re-baselined with this
enumeration and are the post-repair reference.

**A second movement is coming from the same change and is not in this table.**
gh69 phase 5.6 repairs `RandomStringPassword.mop`'s unresolved `String` owner —
the one owner in the set the extractor never resolved, which left every published
`cov_reaches_target` computed over 22 of the set's 23 specifications. That repair
is also in the visitor, also enumerated, and gets its own entry here when it
lands. It is recorded now so this table is not read as the whole of what gh69
moves.

---

## The second gh69 movement: the owner the extractor never resolved (issue #69, phase 5.6)

Same change, same file it lives in, different defect — and it is the one that damaged a
published figure rather than a numerator.

**What was wrong.** `jca/RandomStringPassword.mop` names its owner `String` and imports
only `java.util.stream.IntStream` and three `br.unb.cic.mop.*` packages. `java.lang` is
implicit in Java but was not implicit for the extractor, whose owner resolution consulted
explicit imports and wildcard-import packages and nothing else — with no `else` branch and
no log (`UsedJcaMethodsVisitor:70-77`). Both of the spec's pointcuts vanished without a
trace. The spec is 1 of the 23 in `jca` and 1 of the 48 now in `jca_android`, and it was
**the only** unresolved owner in either set — re-enumerated 2026-08-28 rather than quoted,
because gh109 had grown `jca_android` in the interval: `jca` declares 23 `call()` owners and
emitted 22, `jca_android` declares 47 and emitted 46, `generic_new` declares 21 and emitted
21.

The woven aspect carries both pointcuts
(`rvsec/rvsec-mop/src/main/resources/jca/MultiSpec_1MonitorAspect.aj:874,879`), so the
monitor advised call sites the static layer never marked.

**What it cost, exactly.** No violation count is wrong: `RandomStringPasswordSpec` appears in
no `errors.csv` anywhere in the tree. The damage is in the denominator — every
`cov_reaches_target` and `cov_directly_reaches_target` ever published from the frozen ruler
was computed over **22 of its 23 specifications**, and nothing reported that.

**The repair, and why it is three parts rather than one.** Seeding the implicit `java.lang`
package alone would have been worse than the hole. MOP targets are emitted LENIENT — class
and name, signature ignored — so a resolved `String` target makes `String#valueOf` match
every overload: measured over 3 corpus APKs, 74 call sites of
`String.valueOf`/`toCharArray` of which only **17** are the woven signatures, the other 57
being `valueOf(int)`/`valueOf(long)` in `toString` and logging code. So the seed ships bound
to two other things: `MatchPolicy.STRICT` for any target whose owner resolved *only* through
the seed, and FQN resolution of pointcut parameter types, without which STRICT cannot be
expressed at all (`TargetResolver` compares against the Soot signature, which reads
`java.lang.Object` where the pointcut wrote `Object`).

The criterion is keyed on the **route** the owner resolved by, not on the package it lives
in. That distinction is what keeps the blast radius at two pointcuts in each JCA set and
zero elsewhere: `generic_new`'s `Object+`, `Comparable+` and `CharSequence+` owners are
`java.lang` classes too, but their specs import the package, so they resolve at the first
step and stay LENIENT — which they must, since they declare `(..)` parameters that STRICT
could never match.

Nothing under `rvsec/rvsec-mop/src/main/resources/jca` was touched. The repair could not
have been made from the spec side in any case: the visitor keys its import map by simple
name, so writing the owner as `java.lang.String` in the pointcut would not have resolved
either.

**The enumeration.** The extractor's own triple, measured before and after with the parameter
resolution landed first and separately so the two causes could be told apart:

| set | before | after | what moved |
|---|---|---|---|
| `jca` | 120 / 68 / 22 | **122 / 70 / 23** | exactly two rows — `java.lang.String#valueOf(java.lang.Object)` and `java.lang.String#toCharArray()` |
| `jca_android` | 209 | **211** | the same two rows |
| `generic_new` | 72 | 72 | nothing; every owner resolves before the seed is consulted |

No row was removed and no rows merged in any set — row count equals distinct-key count on
both sides, which is the check that matters, because the parameter list participates in
`MopMethod` identity and resolving it could in principle have collapsed two entries that
differed only in how two specs spelled a type. It did not: the FQN resolution, measured on
its own first, changed 1 parameter list in `jca` (`SSLContext.init`, where `KeyManager[]` and
`TrustManager[]` gained their `javax.net.ssl` prefix), 1 in `jca_android` and 16 in
`generic_new`, and added or removed no rows anywhere.

On the frozen `cryptoapp` fixture (106 app methods, spark):

| axis | before | after | what moved |
|---|---|---|---|
| `reachable` | 55 | 55 | nothing |
| `reachesTarget` | 33 | **37** | the default constructors of `MainActivity`, `CipherActivity`, `CryptographyActivity` and `MessageDigestActivity` |
| `directlyReachesTarget` | 23 | 23 | **nothing** |

The direct axis holding still is the repair working, not the repair being inert: `cryptoapp`
contains no app-level call site of either woven signature, so the two targets add no direct
caller — and under a *lenient* seed they would have added the false ones. The four methods
that move do so on the transitive axis, reaching `String.valueOf(Object)` through the
framework call graph. The movement was attributed by isolation rather than assumed: running
the same APK against a copy of `jca` with `RandomStringPassword.mop` removed reproduces the
old numbers exactly (120 signatures, 0 STRICT, 33 reaching, 23 direct), so the whole delta
belongs to that one specification and to nothing else.

**A defect the repair had to fix first, recorded because it changes shared behaviour.** The
bytecode scan that computes the direct axis reduced every resolved target to a
`className#methodName` key, which *is* the lenient policy — so a STRICT target's overloads
were readmitted there even when `resolveInScene` had correctly excluded them, and through the
reverse BFS (which the direct set seeds) they reached the transitive axis too. The scan now
matches a STRICT target per invoke against `SootMethodRef.parameterTypes()`, the descriptor
the call instruction itself carries. Measured on `cryptoapp` with a single `String.valueOf`
target: **24 direct callers under LENIENT, 9 under STRICT**. Before phase 5.6 no spec set
produced a STRICT target from a `.mop` directory at all, so this changes nothing for any
measurement published to date; it changes what a STRICT target means from here on.

**What this means for a published figure.** Any `cov_reaches_target` from the frozen set,
before this repair, was computed over 22 of 23 specifications. The published figures
reproduce exactly and remain wrong in that direction. As with the constructor repair above, a
campaign comparing across the boundary has to say which side each figure comes from.
