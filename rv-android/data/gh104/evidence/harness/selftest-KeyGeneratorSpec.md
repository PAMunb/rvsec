# KeyGeneratorSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyGeneratorSpec-unsafe.txt` | unchanged | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 | KeyGeneratorSpec.init, KeyGeneratorSpec.gk1 |
| `KeyGeneratorSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyGeneratorSpec-unsafe.txt` (A) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofAES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found DES.`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=init,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyGeneratorSpec-unsafe.txt` (B) `spec=KeyGeneratorSpec,ev=gk1,type=UnsafeAlgorithm,msg=expecting one ofAES,HmacSHA256,HmacSHA384,HmacSHA512,HMAC-SHA256,HMAC/SHA256,HMAC-SHA384,HMAC/SHA384,HMAC/SHA512,HMAC-SHA512 but found DES.`
