# KeyPairGeneratorSpec — differential harness

- **A** `../rvsec/rvsec-mop/src/main/resources/jca`
- **B** `../rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairGeneratorSpec-ec.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-no-init.txt` | unchanged | KeyPairGeneratorSpec.gen | KeyPairGeneratorSpec.gen |
| `KeyPairGeneratorSpec-rsa3072.txt` | introduced | — | KeyPairGeneratorSpec.initError |
| `KeyPairGeneratorSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyPairGeneratorSpec-no-init.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyPairGeneratorSpec-no-init.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyPairGeneratorSpec-rsa3072.txt` (B) `spec=KeyPairGeneratorSpec,ev=initError,type=InvalidKeySize,msg=invalid key size for algorithm RSA.`
