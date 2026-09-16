# Artifact updates owed to /opsx:update (collected during apply)

1. `Evidence.suffix(Object)` renamed to `Evidence.keysFor(Object)`: `suffix` is a reserved token of
   the JavaMOP grammar (`javamop.jj`, `<SUFFIX: "suffix">`, a specification modifier), so a `.mop`
   calling `Evidence.suffix(` does not parse. Update design D10, API Design (`br.unb.cic.mop.eh.Evidence`),
   the Key Components table and the instrumentation delta spec wherever the helper is named.

# Decisions to put to the researcher (collected during apply)

1. (G9b) A creation route guarded by `condition(...)` with no refused twin event (`KeyStore.getInstance(type, provider)`
   with a refused type, `MessageDigest.getInstance(alg, provider)` with a refused algorithm) runs no event body, so
   `creationObserved` stays false and a later failure is labelled `creation-unobserved`, not `sequence` as D7 intends
   for refused creations. Adding twin events changes what is reported.
2. (G9a, G9b) In fifteen specifications the automaton is a single constructor, so `@fail` cannot fire; their
   `-ORDER-01` rows (like the existing `-ORDER-00`) are unreachable and exist only for the bijection.

# Main-window closing checklist for the specification wave

- `Property.java` javadoc line references moved (G6): KMF `:220`→`:244`, `:176`→`:191`; TMF `:256`→`:287`,
  `:218`→`:235`; SSLContext `:222`→`:249`, `:231`→`:262`. Re-measure after the last `.mop` edit.
- `KeyManagerFactorySpec.mop:87-90` is now `:94-97`; cited in AlgorithmParametersSpec, ECParameterSpecSpec,
  KeyStoreSpec, SignatureSpec, MacSpec, KeyPairGeneratorSpec; `AlgorithmParametersSpec.mop:198` cites `:196-200`,
  now `:211-215`. Re-measure after the last `.mop` edit.
- `data/gh104/traces/RSAKeyGenParameterSpecSpec.txt` comment still says {1024, 2048, 4096} (G13a).
- `tls_mixed_array` (G6) cannot replay: TraceRunner has no array token nor a test-scope TrustManager class (G13a decides).
- Predicate-graph declaration pattern does not recognise the for-each variable of the per-element read/write (G13c).
- Line references into G8 files moved (`GCMParameterSpecSpec.mop:134-146`, `PBEKeySpecSpec.mop:160`, `:183-189`,
  `IvParameterSpec.mop:108-111`, `CipherSpec.mop:199`), cited from G9a/G9b files. Re-measure with the rest.
- Decision candidates (G8): `MacSpec.i2` key read is not a consumer of REPORTED_UPSTREAM (spec lists only `i1`);
  `PBEKeySpecSpec.f1`/`f2` (FORB on product) do not mark (spec lists only `c1`); `MacSpec.getInstance(unsafe, provider)`
  has no event, so such a Mac is labelled `creation-unobserved` (same shape as G9b's decision 1).
- (G7) `SecretKeySpecSpec.c1`/`c2` add `validate(RANDOMIZED, keyMaterial)` reads for `random-key-material`;
  `SecretKeySpec.crysl` does not require `randomized` — ledger/graph gates may need a reason row (G13c).
- (G7) No trace for "constant key material carries a stable fingerprint": the trace grammar has no byte-array literal.
- (G4) Existing behaviour: a method whose register frame grows or whose try ranges are rebuilt (after-throwing,
  `!holdsLock` guards, ctor after-finally) loses all its line numbers, so INV-INS-161's line move has no effect there.
- (G4) Framework-subtype alias reuses the most specific supertype wrapper; unrelated owners sharing a method are
  counted in `WeaveReport.wrapperAliasesUnmerged` and left unwoven (0 expected in jca_android). G12 publishes it.
- (G4) Ctor after-finally applies only to plain `after`; every ctor event of jca_android uses `returning`, so the path
  weaves nothing in that set today.
- (G13b) `scripts/gh105_expert_conformance.py --check` exits 1 with 24 findings (Digest and RSAKeyGenParameterSpec
  clauses no row anchors); G13b says it already failed before its edits. Verify against a HEAD checkout in 13.6
  (was it red at 325c2a38?) before attributing it.
- (G14) `data/jca_android/README.md` still says "Twenty-four `.mop` files" (the set has 47); doc line references into
  `.mop` files (NEW_SPEC_CONVENTIONS/README/architecture) need a re-measure after the last `.mop` edit.
- (G16a rv-platform) Pre-existing bug outside the change: `TaskStorage.get_pending_tasks()` uses the non-existent
  `TaskState.ARCHIVED`; nothing calls it; a skipped test hides it.
