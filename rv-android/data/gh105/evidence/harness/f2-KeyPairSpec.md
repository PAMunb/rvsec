# KeyPairSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairSpec-generated-cipher.txt` | unchanged | KeyPairSpec.gpu | KeyPairSpec.gpu |
| `KeyPairSpec-private-cipher.txt` | unchanged | — | — |
| `KeyPairSpec-public-cipher.txt` | unchanged | — | — |
| `KeyPairSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyPairSpec-generated-cipher.txt` (A) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyPairSpec-generated-cipher.txt` (B) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
