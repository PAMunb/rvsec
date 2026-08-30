# SecretKeyFactorySpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/7d1ffd13-9ceb-471d-8809-05cd37449300/scratchpad/preGh109/rvsec/rvsec-mop/src/main/resources/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeyFactorySpec-unobserved-spec.txt` | introduced | — | gen:SECRETKEYFACTORY-NOBS-00 |
| `SecretKeyFactorySpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `SecretKeyFactorySpec-unobserved-spec.txt` (A) `SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256") -> skf`
- `SecretKeyFactorySpec-unobserved-spec.txt` (A) `skf.generateSecret(spec)`
- `SecretKeyFactorySpec.txt` (A) `SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256") -> skf`
- `SecretKeyFactorySpec.txt` (A) `skf.generateSecret(spec)`

## Envelopes

- `SecretKeyFactorySpec-unobserved-spec.txt` (B) `spec=SecretKeyFactorySpec,ev=gen,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYFACTORY-NOBS-00 ev=gen obj=SecretKeyFactory val='PBKDF2WithHmacSHA256' exp='a key spec this instrumentation observed being built from key material' msg='no construction of the key spec was observed'`
