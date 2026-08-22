# IvChainJunctionSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvChainJunctionSpec-decrypt.txt` | moved | IvParameterSpecSpec.c3 | IvParameterSpecSpec.c1 |
| `IvChainJunctionSpec-unprepared.txt` | moved | IvParameterSpecSpec.c3 | IvParameterSpecSpec.c1, IvChainJunctionSpec.use |
| `IvChainJunctionSpec.txt` | removed | SecureRandomSpec.next2 | — |

## Envelopes

- `IvChainJunctionSpec-decrypt.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `IvChainJunctionSpec-decrypt.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `IvChainJunctionSpec-unprepared.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `IvChainJunctionSpec-unprepared.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `IvChainJunctionSpec-unprepared.txt` (B) `spec=IvChainJunctionSpec,ev=use,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-NOBS-00 ev=use obj=Cipher val='AES/CBC/PKCS5Padding' exp='an IvParameterSpec built over an observed randomized iv' msg='no preparation of the AlgorithmParameterSpec given to Cipher.init was observed'`
- `IvChainJunctionSpec.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
