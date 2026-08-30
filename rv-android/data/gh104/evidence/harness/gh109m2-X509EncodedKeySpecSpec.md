# X509EncodedKeySpecSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `X509EncodedKeySpecSpec-unobserved-material.txt` | introduced | — | c1:X509ENCODEDKEYSPEC-NOBS-00 |
| `X509EncodedKeySpecSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `X509EncodedKeySpecSpec-unobserved-material.txt` (A) `new X509EncodedKeySpec(material) -> spec`
- `X509EncodedKeySpecSpec.txt` (A) `new X509EncodedKeySpec(material) -> spec`

## Envelopes

- `X509EncodedKeySpecSpec-unobserved-material.txt` (B) `spec=X509EncodedKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=X509ENCODEDKEYSPEC-NOBS-00 ev=c1 obj=X509EncodedKeySpec val='' exp='key material the monitor observed being prepared' msg='no preparation of the encoded key material was observed'`
