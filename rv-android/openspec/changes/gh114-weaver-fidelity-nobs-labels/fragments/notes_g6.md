# G6 hand-over notes (TLS cluster)

Files: `TrustManagerFactorySpec.mop`, `KeyManagerFactorySpec.mop`, `SSLContextSpec.mop`.

## Divergence record (G13b)

Every hunk of the three files is either `message` (label codes, evidence keys, the
`creationObserved` field and its writes, the `@fail` split, comment rewrites) or
`predicate-store` (the per-element credit). The hunks of kind `predicate-store`:

- `TrustManagerFactorySpec.gtm1`: after the existing `GENERATED_TRUST_MANAGER` write over the
  returned array, a loop writes `GENERATED_TRUST_MANAGERS` over each non-null element (reason:
  per-element credit; the rule constrains the managers and the factory returns a fresh array
  around the same manager instances on every call, measured on Temurin 21).
- `SSLContextSpec.init`: a loop reads `GENERATED_TRUST_MANAGERS` over each element of `tms`; the
  trust-manager verdict becomes `SATISFIED` when the array read is `NOT_OBSERVED` and `tms` is
  non-empty and every element is marked. The same loop computes `Evidence.isApplicationDefined`
  for the `application-manager` label (no store access, `message` kind).

## Predicate graph and census (G13c)

- New write: `TrustManagerFactorySpec.mop`, event `gtm1`, body, `ensure`,
  `GENERATED_TRUST_MANAGERS`, bound `manager` (a for-each variable of type `TrustManager`; the
  `_DECLARATION` pattern of `gh105_predicate_graph.py` does not see a for-each declaration, so the
  bound type may come out unresolved).
- New read: `SSLContextSpec.mop`, event `init`, body, `validate`, `GENERATED_TRUST_MANAGERS`, bound
  `manager` (same for-each shape), clause `SSLContext.crysl:33 generatedTrustManagers[tm]`
  (the same clause the array read answers).
- `Property.GENERATED_TRUST_MANAGERS` gains its first producer and consumer in `jca_android`.

## Decision not settled by the artifacts

The per-element credit is applied only when the array read answers `NOT_OBSERVED`, never over a
`VIOLATED` answer. The spec sentence ("answers SATISFIED when the array itself is marked, or when
the array is non-empty and every element is marked") does not say what happens to a withdrawn
array whose elements are marked; `GENERATED_TRUST_MANAGER` is withdrawn nowhere today, so the two
readings do not differ on any program.

## Stale line references outside G6's files

- `rvsec-core/.../Property.java` javadoc: `KeyManagerFactorySpec.mop:220` (now `:244`),
  `:176` (now `:191`), `SSLContextSpec.mop:222` (now `:249`), `TrustManagerFactorySpec.mop:256`
  (now `:287`), `:218` (now `:235`), `SSLContextSpec.mop:231` (now `:262`).
- `KeyManagerFactorySpec.mop:87-90` (the harness-wildcard paragraph, now `:94-97`) is cited by
  `AlgorithmParametersSpec.mop:76`, `ECParameterSpecSpec.mop:44`, `KeyStoreSpec.mop:92`,
  `SignatureSpec.mop:95`, `MacSpec.mop:94`, `KeyPairGeneratorSpec.mop:115`; the citation in
  `SSLContextSpec.mop` was updated. `AlgorithmParametersSpec.mop:198` cites
  `KeyManagerFactorySpec.mop:196-200` (the `taken` state and aliases, now `:211-215`).

## Harness expectations that move on existing traces (G13a)

Replayed locally with `TraceRunner` against a monitor generated from the three files plus the
HEAD `KeyStoreSpec` and `SecureRandomSpec`, before and after. The (spec, event) sites are the same
on every existing trace; only codes move, each within its family:

- `TRUSTMANAGERFACTORY-NOBS-00` -> `-NOBS-02` on every trace that calls `tmf.init(null)`
  (`TrustManagerFactorySpec.txt`, `-pkix-init`, `-x509`, `-sunx509`, `-d15-sunx509`,
  `-guard-on-field`); `-unloaded-keystore` keeps `-NOBS-00`.
- `TRUSTMANAGERFACTORY-ORDER-00` -> `-ORDER-01` on `-d15-sunx509` and `-guard-on-field`
  (factory bound, `getInstance` not dispatched); `-managers-taken-twice` keeps `-ORDER-00`.
- `KEYMANAGERFACTORY-NOBS-00` -> `-NOBS-02` and `-ORDER-00` -> `-ORDER-01` on
  `KeyManagerFactorySpec.txt`, `-d15-sunx509`, `-guard-on-field`; `-managers-taken-twice` keeps
  `-ORDER-00`.
- `SSLCONTEXT-NOBS-00/-01/-02` -> `-NOBS-03/-04/-06` on every trace calling
  `ctx.init(null, null, null)`; `SSLContextSpec-tls-chain` moves `-NOBS-02` -> `-NOBS-06`.
- `SSLCONTEXT-ORDER-00` -> `-ORDER-01` on `-d15-ssl`, `-d15-tlsv1`, `-guard-on-field` (context
  bound); `-getdefault-engine` keeps `-ORDER-00` (label `sequence`), as task 13.2 pins.

`SSLContextSpec-tls_mixed_array.txt` has no call lines: the trace grammar cannot build an array
from bound objects and the test classpath has no application-defined `TrustManager`. Its
expectation (`SSLCONTEXT-NOBS-05` with `vcls` naming both classes in order) was confirmed by
calling the generated dispatchers directly from a scratch Java program.
