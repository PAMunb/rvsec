# KeyPairGeneratorSpec — differential harness

- **A** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca`
- **B** `/home/pedro/.cache/gh104-tmp/jca_mutant`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `KeyPairGeneratorSpec-ec.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-no-init.txt` | unchanged | gen:? | gen:? |
| `KeyPairGeneratorSpec-rsa3072.txt` | unchanged | — | — |
| `KeyPairGeneratorSpec-sticky-fail.txt` | unchanged | gen:? | gen:? |
| `KeyPairGeneratorSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `KeyPairGeneratorSpec-sticky-fail.txt` — `kpg.initialize(2048)  (KeyPairGeneratorSpec.init1 raised java.lang.NullPointerException: Cannot invoke "String.hashCode()" because "<local2>" is null)`
- `KeyPairGeneratorSpec-sticky-fail.txt` — `kpg.initialize(2048)  (KeyPairGeneratorSpec.initError raised java.lang.NullPointerException: Cannot invoke "String.hashCode()" because "<local2>" is null)`
- `KeyPairGeneratorSpec-sticky-fail.txt` — `kpg.initialize(2048)  (KeyPairGeneratorSpec.init1 raised java.lang.NullPointerException: Cannot invoke "String.hashCode()" because "<local2>" is null)`
- `KeyPairGeneratorSpec-sticky-fail.txt` — `kpg.initialize(2048)  (KeyPairGeneratorSpec.initError raised java.lang.NullPointerException: Cannot invoke "String.hashCode()" because "<local2>" is null)`

## Envelopes

- `KeyPairGeneratorSpec-no-init.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyPairGeneratorSpec-no-init.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyPairGeneratorSpec-sticky-fail.txt` (A) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=unknown`
- `KeyPairGeneratorSpec-sticky-fail.txt` (B) `spec=KeyPairGeneratorSpec,ev=gen,type=InvalidSequenceOfMethodCalls,msg=unknown`
