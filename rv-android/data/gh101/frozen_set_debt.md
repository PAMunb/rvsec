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

The two consequences that follow from the freeze, and that any report using
either set has to carry:

1. Results measured under `jca` reproduce exactly, and remain wrong in the ways
   listed below.
2. The two sets no longer differ along a single axis. A difference in outcome
   between them used to be attributable to the platform allow-list alone; it can
   now come from the allow-list **or** from a repair present only in the derived
   set. No measurement decomposes an observed difference after the fact. The
   divergence record keeps the differences named; it cannot make them separable.

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
emit the spurious report from them. It emits a different symptom instead: because
`unsafe_protocol` never fires, `currentProtocol` keeps the empty string, and the
campaign's `UnsafeProtocol` for this specification reads `but found .` — 51
events. `TrustManagerFactorySpec` does the same for `UnsafeAlgorithm`, 8,371
events. The frozen set therefore keeps both the dead event and the empty label.

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
