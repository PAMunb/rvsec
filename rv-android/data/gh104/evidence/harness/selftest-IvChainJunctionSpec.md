# IvChainJunctionSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvChainJunctionSpec-decrypt.txt` | removed | c3:?, c3:? | — |
| `IvChainJunctionSpec-gcm-unprepared.txt` | unchanged | — | — |
| `IvChainJunctionSpec-gcm.txt` | unchanged | next2:? | next2:? |
| `IvChainJunctionSpec-rangen-unobserved.txt` | unchanged | i2:?, i2:? | i2:?, i2:? |
| `IvChainJunctionSpec-rangen.txt` | unchanged | i2:?, i2:? | i2:?, i2:? |
| `IvChainJunctionSpec-unprepared.txt` | removed | c3:?, c3:? | — |
| `IvChainJunctionSpec.txt` | unchanged | next2:? | next2:? |

## Envelopes

- `IvChainJunctionSpec-decrypt.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=unknown`
- `IvChainJunctionSpec-decrypt.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvChainJunctionSpec-gcm.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvChainJunctionSpec-gcm.txt` (B) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvChainJunctionSpec-rangen-unobserved.txt` (A) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `IvChainJunctionSpec-rangen-unobserved.txt` (A) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvChainJunctionSpec-rangen-unobserved.txt` (B) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `IvChainJunctionSpec-rangen-unobserved.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvChainJunctionSpec-rangen.txt` (A) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `IvChainJunctionSpec-rangen.txt` (A) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvChainJunctionSpec-rangen.txt` (B) `spec=CipherSpec,ev=i2,type=UnsafeAlgorithm,msg=expecting one of {AES/CBC/PKCS5Padding, AES/PCBC/ISO10126Padding, ...} but found AES/ECB/PKCS5Padding.`
- `IvChainJunctionSpec-rangen.txt` (B) `spec=CipherSpec,ev=i2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvChainJunctionSpec-unprepared.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=unknown`
- `IvChainJunctionSpec-unprepared.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvChainJunctionSpec.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `IvChainJunctionSpec.txt` (B) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=unknown`
