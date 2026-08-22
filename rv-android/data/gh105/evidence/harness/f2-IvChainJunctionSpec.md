# IvChainJunctionSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvChainJunctionSpec-decrypt.txt` | moved | IvParameterSpecSpec.c3 | IvParameterSpecSpec.c1 |
| `IvChainJunctionSpec-gcm-unprepared.txt` | introduced | — | GCMParameterSpecSpec.c1, IvChainJunctionSpec.use |
| `IvChainJunctionSpec-gcm.txt` | removed | SecureRandomSpec.next2 | — |
| `IvChainJunctionSpec-rangen-unobserved.txt` | moved | SecureRandomSpec.g4 | SecureRandomSpec.g4, IvChainJunctionSpec.useRandomKey |
| `IvChainJunctionSpec-rangen.txt` | unchanged | — | — |
| `IvChainJunctionSpec-unprepared.txt` | moved | IvParameterSpecSpec.c3 | IvParameterSpecSpec.c1, IvChainJunctionSpec.use |
| `IvChainJunctionSpec.txt` | removed | SecureRandomSpec.next2 | — |

## Envelopes

- `IvChainJunctionSpec-decrypt.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `IvChainJunctionSpec-decrypt.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `IvChainJunctionSpec-gcm-unprepared.txt` (B) `spec=GCMParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=GCMPARAMETERSPEC-NOBS-00 ev=c1 obj=GCMParameterSpec val='' exp='a randomized byte[]' msg='the IV material was not observed to come from a randomized source'`
- `IvChainJunctionSpec-gcm-unprepared.txt` (B) `spec=IvChainJunctionSpec,ev=use,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-NOBS-01 ev=use obj=Cipher val='AES/GCM/NoPadding' exp='a GCMParameterSpec built over an observed randomized source' msg='no preparation of the AlgorithmParameterSpec given to Cipher.init was observed'`
- `IvChainJunctionSpec-gcm.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `IvChainJunctionSpec-rangen-unobserved.txt` (A) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `IvChainJunctionSpec-rangen-unobserved.txt` (B) `spec=SecureRandomSpec,ev=g4,type=UnsafeAlgorithm,msg=v=1 code=SECURERANDOM-ALG-00 ev=g4 obj=SecureRandom val='NativePRNG' exp='SHA1PRNG' msg='expecting one of SHA1PRNG but found NativePRNG'`
- `IvChainJunctionSpec-rangen-unobserved.txt` (B) `spec=IvChainJunctionSpec,ev=useRandomKey,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-NOBS-02 ev=useRandomKey obj=Cipher val='AES/ECB/PKCS5Padding' exp='a SecureRandom this instrumentation observed being constructed' msg='the SecureRandom given to Cipher.init was not observed to come from an observed construction'`
- `IvChainJunctionSpec-unprepared.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `IvChainJunctionSpec-unprepared.txt` (B) `spec=IvParameterSpecSpec,ev=c1,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-NOBS-00 ev=c1 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='no randomized source of the iv given to IvParameterSpec(byte[]) was observed'`
- `IvChainJunctionSpec-unprepared.txt` (B) `spec=IvChainJunctionSpec,ev=use,type=UnsatisfiedConstraint,msg=v=1 code=IVCHAINJUNCTION-NOBS-00 ev=use obj=Cipher val='AES/CBC/PKCS5Padding' exp='an IvParameterSpec built over an observed randomized iv' msg='no preparation of the AlgorithmParameterSpec given to Cipher.init was observed'`
- `IvChainJunctionSpec.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
