# G9b hand-over notes (tasks 9.3, 9.4, 9.5)

## Hunks that need a record reason beyond "label code / evidence key / handler field"

- **`RSAKeyGenParameterSpecSpec.mop`, the `keySizes` declaration and its comment (around :33-50).**
  The list is now `Arrays.asList(2048, 3072, 4096)`. The comment names both expert clauses
  (`RSAKeyGenParameterSpec.crysl:15` {1024, 2048, 4096}, `KeyPairGenerator.crysl:29`
  {4096, 3072, 2048}), NIST SP 800-57 Part 1 (3072 → 128 bits, 2048 → 112, 1024 → 80), D-20.4 and
  D-21. For G13b: `divergence_record.csv:376` rewritten in place (task `gh109:6.3;gh114:9.4`), the
  addendum on `:269` (whose reason still says "1024 stays in the list"), the new key-size row of
  `conformance_record.csv`, and the re-emitted `coverage_matrix.csv`. The `exp` of
  `RSAKEYGENPARAMETERSPEC-KEYSIZE-00` still derives from the list (`q(keySizes.toString())`); measured
  in the harness it reads `exp='[2048, 3072, 4096]'`.
- **`KeyPairSpec.mop`, two comment hunks (around :124-128 and :178-186).** The measurement they
  quote named `KEYPAIR-ORDER-00`; they now say "ordering report" and state that a generated pair's
  report carries `KEYPAIR-ORDER-01` (`creation-unobserved`). Kind `message`, same as the handler edit.

Every other hunk in the fourteen files is a label code, an evidence key or the `creationObserved`
field and its writes (kind `message`).

## Creation events per file (design D7)

| File | Creation events | `-ORDER-01` |
|---|---|---|
| KeyPairGeneratorSpec | g1, g2, g3, g4 | yes |
| KeyPairSpec | c1 | yes |
| KeyStoreBuilderParametersSpec | c1 | yes |
| KeyStoreSpec | g1, g2, g3 | yes |
| MessageDigestSpec | g1, g2, g3, g4 | yes |
| MGF1ParameterSpecSpec | c1 | yes |
| OAEPParameterSpecSpec | c1 | yes |
| PBEParameterSpecSpec | c1, c2 | yes |
| PKIXBuilderParametersSpec | c1, c2 | yes |
| PKIXParametersSpec | c1, c2 | yes |
| RSAKeyGenParameterSpecSpec | c1 | yes |
| SSLEngineSpec | none (ec1, ep1 are `target`-bound) | no; file unchanged (it has no `-NOBS-` site either) |
| SSLParametersSpec | c1, c2, c3 | yes |
| TrustAnchorSpec | c1, c2, c3 | yes |

No file other than `SSLEngineSpec` lacks a creation event.

## KeyStoreSpec and monitor copies

`KeyStoreSpec` is declared `KeyStoreSpec(KeyStore k)`: one specification parameter. `gk1` binds a
`Key` through `returning(Key key)`, but `key` is not a specification parameter, so the generator
never extends a binding and never copies a monitor for this specification. The risk named in design
"Risks" does not arise here, and `KEYSTORE-ORDER-01` is emitted like everywhere else. All fourteen
files of this group are single-parameter.

## Decision the artefacts did not settle: creation routes filtered by a guard

A `condition(...)` that is false runs no event body, so a creation call that matches only a
positively guarded event leaves `creationObserved` false, and the later failure is labelled
`creation-unobserved` rather than `sequence`:

- `KeyStoreSpec`: `KeyStore.getInstance(type, provider)` with a type the list refuses (`g3` is
  positive and has no negated two-argument twin).
- `MessageDigestSpec`: `MessageDigest.getInstance(alg, provider)` (both overloads) with an algorithm
  the list refuses (`g2`/`g3` are positive; the negated `g4` is one-argument only). The value report
  (`MESSAGEDIGEST-ALG-00/01/03/04`) is unchanged; only the ordering code beside it becomes `-ORDER-01`.

D7 says "a refused creation followed by use is labelled `sequence`", but that sentence presumes a
refused twin event; on these routes the monitor really does not observe the creation. Both files'
declaration comments state it. Adding the negated two-argument twins would change the event
alphabet and the reports, so it was not done; flagged for the researcher.

## Unreachable handlers

In `KeyStoreBuilderParametersSpec`, `MGF1ParameterSpecSpec`, `OAEPParameterSpecSpec`,
`RSAKeyGenParameterSpecSpec` (`ere : c1`) and `PBEParameterSpecSpec`, `PKIXBuilderParametersSpec`,
`PKIXParametersSpec`, `TrustAnchorSpec` (`ere : c1 | c2 [| c3]`), the files already record that
`@fail` cannot fire. `-ORDER-01` there is unreachable in the same way `-ORDER-00` is; it was added
because task 9.3 applies the label to every file with a creation event.

## Evidence keys

`Evidence.keysFor(<bound>)` is on all eleven `-NOBS-` envelopes. Only the `PBEParameterSpecSpec`
salt is a `byte[]` (measured: `vfp='sha256:…'`); the other bound objects (`AlgorithmParameterSpec`,
`PrivateKey`/`PublicKey`, `KeyStore`, `mgfSpec`) yield no key.

## Harness check run by G9b (for G13a)

The fourteen files at `HEAD` (A) and in the working tree (B) were generated in scratch and replayed
with `TraceRunner` (a locally compiled `Evidence` ahead of the classpath, because the installed
`rvsec-core` jar still had `suffix`) over the three new traces plus the 61 existing traces of these
specifications and `SignatureSpec-generated-*`. The `(spec, event)` sets are identical on every
trace except the two RSA traces. The code differences:

- `RSAKeyGenParameterSpecSpec-rsa_3072`: A `c1 KEYSIZE-00`, B nothing (removed).
- `RSAKeyGenParameterSpecSpec-rsa_1024`: A nothing, B `c1 KEYSIZE-00` with `val='1024'` (introduced).
- `-ORDER-00` → `-ORDER-01`, same event: `MessageDigestSpec-digest_clone_update` (update),
  `MessageDigestSpec-guard-on-field` (update, d1), `KeyStoreSpec-guard-on-field` (load, gk1),
  `KeyPairSpec-generated` (gpu, gpr), `KeyPairSpec-generated-cipher` (gpu),
  `KeyPairSpec-observed-halves` (gpu, gpr), `SignatureSpec-generated-pubkey` (gpu),
  `SignatureSpec-generated-privkey` (gpr), `KeyPairGeneratorSpec-init3-no-clause-applies` (init3),
  `KeyPairGeneratorSpec-sticky-fail` (gen).
- `MessageDigestSpec-md5` (to be pinned `sequence` in task 13.2) is unchanged.

The comment of `data/gh104/traces/RSAKeyGenParameterSpecSpec.txt` still says the rule admits
{1024, 2048, 4096}; the trace still passes (2048), but its comment is stale after 9.4 (G13a owns it).
