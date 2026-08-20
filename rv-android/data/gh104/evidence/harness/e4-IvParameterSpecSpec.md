# IvParameterSpecSpec — differential harness

- **A** `/home/pedro/tmp-gh104/e4-a/jca_android`
- **B** `/home/pedro/tmp-gh104/e4-b815a`
- traces: 2

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `IvParameterSpecSpec-unrandomised.txt` | unchanged | IvParameterSpecSpec.c3 | IvParameterSpecSpec.c3 |
| `IvParameterSpecSpec.txt` | unchanged | — | — |

## Envelopes

- `IvParameterSpecSpec-unrandomised.txt` (A) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
- `IvParameterSpecSpec-unrandomised.txt` (B) `spec=IvParameterSpecSpec,ev=c3,type=UnsatisfiedConstraint,msg=v=1 code=IVPARAMETERSPEC-CONSTR-00 ev=c3 obj=IvParameterSpec val='' exp='a randomized byte[]' msg='the iv given to IvParameterSpec(byte[]) was not observed to come from a randomized source'`
