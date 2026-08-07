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
