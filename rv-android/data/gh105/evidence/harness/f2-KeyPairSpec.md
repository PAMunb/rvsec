# KeyPairSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairSpec-generated-cipher.txt` | unchanged | KeyPairSpec.gpu | KeyPairSpec.gpu |
| `KeyPairSpec-observed-halves.txt` | unchanged | KeyPairSpec.gpu, KeyPairSpec.gpr | KeyPairSpec.gpu, KeyPairSpec.gpr |
| `KeyPairSpec-private-cipher.txt` | introduced | — | KeyPairSpec.c1 |
| `KeyPairSpec-public-cipher.txt` | introduced | — | KeyPairSpec.c1 |
| `KeyPairSpec.txt` | introduced | — | KeyPairSpec.c1 |

## Envelopes

- `KeyPairSpec-generated-cipher.txt` (A) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyPairSpec-generated-cipher.txt` (B) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyPairSpec-observed-halves.txt` (A) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyPairSpec-observed-halves.txt` (A) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyPairSpec-observed-halves.txt` (B) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyPairSpec-observed-halves.txt` (B) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `KeyPairSpec-private-cipher.txt` (B) `spec=KeyPairSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=KEYPAIR-NOBS-01 ev=c1 obj=KeyPair val='' exp='a public key produced by one of the generators the rule names' msg='no generator of the public key given to the KeyPair constructor was observed'`
- `KeyPairSpec-public-cipher.txt` (B) `spec=KeyPairSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=KEYPAIR-NOBS-01 ev=c1 obj=KeyPair val='' exp='a public key produced by one of the generators the rule names' msg='no generator of the public key given to the KeyPair constructor was observed'`
- `KeyPairSpec.txt` (B) `spec=KeyPairSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=KEYPAIR-NOBS-01 ev=c1 obj=KeyPair val='' exp='a public key produced by one of the generators the rule names' msg='no generator of the public key given to the KeyPair constructor was observed'`
