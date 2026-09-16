# Hand-over notes of G7 (key-material cluster)

Files edited: `SecretKeySpecSpec.mop`, `SecretKeySpec.mop`, `KeySpec.mop`, `X509EncodedKeySpecSpec.mop`,
`KeyFactorySpec.mop`, `SecretKeyFactorySpec.mop`, `KeyAgreementSpec.mop`, `KeyGeneratorSpec.mop`,
`SignatureSpec.mop`. New codes and moved anchors: `codes_g7.csv`. Traces: `traces_g7/`.

## For G13b — reasons of the edited hunks (`divergence_record.csv`)

Only the two existing kinds are needed.

- `message` (label code / evidence key / handler field): every `@fail` of `SecretKeySpecSpec`,
  `X509EncodedKeySpecSpec`, `KeyFactorySpec`, `SecretKeyFactorySpec`, `KeyAgreementSpec`,
  `KeyGeneratorSpec`, `SignatureSpec` (the `creationObserved` field, its assignment as the first
  statement of each creation event, and the `-ORDER-01` branch); every `-NOBS-` site of those files
  (`Evidence.keysFor` appended after `msg`).
- `predicate-store` (upstream mark): the `upstream-refused` branches and the `REPORTED_UPSTREAM`
  writes of `SecretKeySpecSpec.c1`/`c2`, `X509EncodedKeySpecSpec.c1`, `KeyFactorySpec.genPrivate`/
  `genPublic`, `SecretKeyFactorySpec.gen`, `KeyAgreementSpec.dophase`/`gs1`/`gs2`,
  `SignatureSpec.i4`, and the bridges `SecretKeySpec.e1` and `KeySpec.ge1`.
- `predicate-store`, one hunk that is not the mark: the `random-key-material` branch of
  `SecretKeySpecSpec.c1` and `c2` reads `Property.RANDOMIZED` over `keyMaterial`
  (`validate(RANDOMIZED, keyMaterial) == SATISFIED`, arity 1, the shape of the existing
  `RANDOMIZED` readers). The read selects the code only; whether the site reports is still decided
  by `PREPARED_KEY_MATERIAL` alone. `SecretKeySpec.crysl` does not require `randomized`, so if a
  ledger or graph gate pairs every read with a clause of the site's own rule, this read needs the
  same "label selection, no verdict" reason there (or an allowlist row).

## For G13c — new predicate-store sites (census pins, `predicate_graph.csv`)

- `ensure(Property.REPORTED_UPSTREAM, …)`: 10 sites — `SecretKeySpecSpec.c1`, `.c2`;
  `X509EncodedKeySpecSpec.c1`; `KeyFactorySpec.genPrivate`, `.genPublic`; `SecretKeyFactorySpec.gen`;
  `KeyAgreementSpec.gs1`, `.gs2`; `SecretKeySpec.e1`; `KeySpec.ge1`.
- `validateAny(Property.REPORTED_UPSTREAM, …)`: 10 sites — `SecretKeySpecSpec.c1`, `.c2`;
  `X509EncodedKeySpecSpec.c1`; `KeyFactorySpec.genPrivate`, `.genPublic`; `SecretKeyFactorySpec.gen`;
  `KeyAgreementSpec.dophase`; `SignatureSpec.i4`; `SecretKeySpec.e1`; `KeySpec.ge1`.
- `validate(Property.RANDOMIZED, …)`: 2 new sites — `SecretKeySpecSpec.c1`, `.c2`.
- `KeyGeneratorSpec` has no new store site (no upstream mark, by decision).

## For G13a — harness expectations

Measured with `TraceRunner` over all of `data/gh104/traces` plus `traces_g7/`, side A = HEAD set,
side B = HEAD set with only the nine G7 files replaced (other groups' files at HEAD). In every
trace the set of reported `(spec, event)` is identical on both sides and every changed code stays
in its family. The traces whose codes change:

- `SECRETKEYSPEC-NOBS-00` → `SECRETKEYSPEC-NOBS-03` (`random-key-material`): `SecretKeySpecSpec`,
  `SecretKeySpecSpec-cipher-chain`, `SecretKeySpec-encoded-iv`, `CipherInputStreamSpec-initialised-cipher`,
  `CipherOutputStreamSpec-initialised-cipher`, `IvChainJunctionSpec`, `IvChainJunctionSpec-decrypt`,
  `IvChainJunctionSpec-gcm`, `IvChainJunctionSpec-gcm-unprepared`, `IvChainJunctionSpec-rangen`,
  `IvChainJunctionSpec-rangen-unobserved`, `IvChainJunctionSpec-unprepared`, `MacSpec-decrypt-buffer`,
  `MacSpec-decrypt-buffer-updated`, `MacSpec-encrypted-buffer`, `MacSpec-encrypted-buffer-updated`,
  `MacSpec-fresh-buffer`, `MacSpec-fresh-buffer-updated`, `MacSpec-mac-then-encrypt`,
  `MacSpec-update-then-encrypt`, and the new `SecretKeySpecSpec-random_bytes_as_key`.
- `SECRETKEYSPEC-NOBS-01` → `SECRETKEYSPEC-NOBS-05` (`random-key-material`): `SecretKeySpecSpec-offset`.
- `KEYGENERATOR-ORDER-00` → `KEYGENERATOR-ORDER-01` (`creation-unobserved`, generator bound
  silently): `KeyGeneratorSpec-d15-arc4`, `-d15-desede`, `-d15-hmacmd5`, `-guard-on-field`.
- `SIGNATURE-ORDER-00` → `SIGNATURE-ORDER-01` (`creation-unobserved`, signature bound silently):
  `SignatureSpec-guard-on-field`, `SignatureSpec-sign-unobserved`.
- `KeyAgreementSpec-ecdh_remote_peer_chain` (new): side B reports `X509ENCODEDKEYSPEC-NOBS-00`,
  `KEYFACTORY-NOBS-03`, `KEYAGREEMENT-NOBS-09`, `SECRETKEYSPEC-NOBS-02`, plus `KEYPAIR-ORDER-00`
  at `gpr` (G9b's file; its label code replaces it once G9b lands).
- `KeyPairSpec-keypair_generated_getpublic` (new): only `KEYPAIR-ORDER-00` at `gpu` and `gpr` on
  side B; the `creation-unobserved` code comes from G9b's `KeyPairSpec.mop`; no `SIGNATURE` code.

Interaction with G8, expected once both land: every trace above in which a `SecretKeySpec` built
from SecureRandom-filled material reaches `Cipher.init` or `Mac.init` now carries
`REPORTED_UPSTREAM` on the spec, so `CipherSpec.i2` / `MacSpec.i1` move from their `not-observed`
code to their `upstream-refused` code in those traces. That is the chain the specification
describes (the first link, `random-key-material`, is reported where it happens), not a regression.

Extra checks run on side B (scratch traces, not delivered): a marked `SecretKeySpec` re-wrapped
through `getEncoded()` draws `SECRETKEYSPEC-NOBS-02` (bridge `SecretKeySpec.e1`), and the same spec
given to `SecretKeyFactory.generateSecret` draws `SECRETKEYFACTORY-NOBS-01`; a public key from
`KeyFactory.generatePublic` over an unobserved `X509EncodedKeySpec` draws `SIGNATURE-NOBS-03` at
`initVerify` and, re-wrapped through `getEncoded()`, `SECRETKEYSPEC-NOBS-02` (bridge `KeySpec.ge1`);
`KeyAgreement.getInstance` followed by two `generateSecret()` draws `KEYAGREEMENT-ORDER-00`
(creation observed). The `vfp` key follows `msg` on the byte-array `-NOBS-` envelopes.

## Decisions the artifacts did not settle

- `KeyAgreementSpec.gs1`/`gs2` mark the buffer in an `else` of the existing `if (conforms)`, as the
  specification words it ("when `conforms` is false"), instead of a local `reported` flag: these
  events emit no report of their own, and every site that clears `conforms` is an `ALG`, `CONSTR`,
  `NOBS` or `FORB` report.
- The bridges write the mark in the event body, not in `@match`: the mark is not a CrySL predicate
  and the returned array is visible only in the body.
- `SecretKeySpecSpec` and `X509EncodedKeySpecSpec` get `-ORDER-01` although their `@fail` has no
  execution path (constructor-only automata); the file comments say so.
- No trace is written for the scenario "a constant key material carries a stable fingerprint": the
  grammar has no literal byte-array token, and the fingerprint itself is covered by `EvidenceTest`.
