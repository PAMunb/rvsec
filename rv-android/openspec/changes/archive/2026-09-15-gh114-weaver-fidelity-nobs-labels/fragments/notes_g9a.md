# G9a hand-over notes

## Record reasons

Every hunk G9a changed in its fourteen files is of one kind, `message` (label code, evidence key,
handler field). There are three kinds of hunk:

- the declaration `boolean creationObserved = false;` and its comment;
- `creationObserved = true;` as the first statement of each creation event;
- the `@fail` handler split into `-ORDER-01` (`creation-unobserved`) and `-ORDER-00`, and
  `Evidence.keysFor(<bound>)` appended to each `-NOBS-` envelope.

No hunk needs a `predicate-store` reason, and none needs a predicate-graph change: G9a adds no
`ensure`/`validate` site. `ECParameterSpecSpec.mop` also has a one-word comment edit ("`@fail` row
alone" became "`@fail` rows alone").

The creation events are:

| File | Creation event(s) |
|---|---|
| `AlgorithmParameterGeneratorSpec` | `get` |
| `AlgorithmParametersSpec` | `get` |
| `CertificateFactorySpec` | `get` |
| `CertPathTrustManagerParametersSpec` | `c1` |
| `CipherInputStreamSpec` | `c1` |
| `CipherOutputStreamSpec` | `c1` |
| `DHGenParameterSpecSpec` | `c1` |
| `DHParameterSpecSpec` | `c1`, `c2` |
| `DigestInputStreamSpec` | `c1` (`on` is bound through `target`, so it is not one) |
| `DigestOutputStreamSpec` | `c1` (same) |
| `DSAParameterSpecSpec` | `c1` |
| `ECGenParameterSpecSpec` | `c1` |
| `ECParameterSpecSpec` | `c1` |
| `HMACParameterSpecSpec` | `c` |

Every file has a creation event, so every file gets `-ORDER-01`.

In seven of these files the ORDER is the single creation event: `CertPathTrustManagerParameters`,
`DHGenParameterSpec`, `DHParameterSpec`, `DSAParameterSpec`, `ECGenParameterSpec`,
`ECParameterSpec` and `HMACParameterSpec`. There, `@fail` cannot fire, as the files' own comments
already say. Both of their `-ORDER-` codes are unreachable, and they exist only because of the
bijection.
