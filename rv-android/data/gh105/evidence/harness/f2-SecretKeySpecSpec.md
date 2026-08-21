# SecretKeySpecSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SecretKeySpecSpec-badalg.txt` | moved | SecretKeySpecSpec.c3 | SecretKeySpecSpec.c1 |
| `SecretKeySpecSpec-cipher-chain.txt` | unchanged | — | — |
| `SecretKeySpecSpec-offset.txt` | unchanged | — | — |
| `SecretKeySpecSpec.txt` | unchanged | — | — |

## Envelopes

- `SecretKeySpecSpec-badalg.txt` (A) `spec=SecretKeySpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-CONSTR-00 ev=c3 obj=SecretKeySpec val='' exp='a randomized byte[]' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to come from a randomized source'`
- `SecretKeySpecSpec-badalg.txt` (B) `spec=SecretKeySpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=SECRETKEYSPEC-NOBS-00 ev=c1 obj=SecretKeySpec val='' exp='a randomized byte[]' msg='the keyMaterial given to SecretKeySpec(byte[], String) was not observed to come from a randomized source'`
