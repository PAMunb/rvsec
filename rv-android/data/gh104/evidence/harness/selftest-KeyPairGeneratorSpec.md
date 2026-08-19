# KeyPairGeneratorSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/tmp-gh104/jca_mutant`
- traces: 4

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairGeneratorSpec-ec.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-no-init.txt` | unchanged | KeyPairGeneratorSpec.gen | KeyPairGeneratorSpec.gen |
| `KeyPairGeneratorSpec-rsa3072.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec.txt` | unchanged | — | — |

## Envelopes

- `KeyPairGeneratorSpec-no-init.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyPairGeneratorSpec-no-init.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=unknown`
