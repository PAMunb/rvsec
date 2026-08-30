# KeyFactorySpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyFactorySpec-unobserved-spec.txt` | introduced | — | genPublic:KEYFACTORY-NOBS-01 |
| `KeyFactorySpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `KeyFactorySpec-unobserved-spec.txt` (A) `KeyFactory.getInstance("RSA") -> kf`
- `KeyFactorySpec-unobserved-spec.txt` (A) `kf.generatePublic(spec)`
- `KeyFactorySpec.txt` (A) `new X509EncodedKeySpec(material) -> spec`
- `KeyFactorySpec.txt` (A) `KeyFactory.getInstance("RSA") -> kf`
- `KeyFactorySpec.txt` (A) `kf.generatePublic(spec)`

## Envelopes

- `KeyFactorySpec-unobserved-spec.txt` (B) `spec=KeyFactorySpec,ev=genPublic,type=UnsatisfiedConstraint,msg=v=1 code=KEYFACTORY-NOBS-01 ev=genPublic obj=KeyFactory val='RSA' exp='a key spec this instrumentation observed being built from key material' msg='no construction of the key spec was observed'`
