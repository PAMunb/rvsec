# CipherSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 3

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `CipherSpec-guard-on-field.txt` | unchanged | CipherSpec.i1 | CipherSpec.i1 |
| `CipherSpec-unsafe.txt` | unchanged | CipherSpec.i1, CipherSpec.f2 | CipherSpec.i1, CipherSpec.f2 |
| `CipherSpec.txt` | unchanged | — | — |

## Envelopes

- `CipherSpec-guard-on-field.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-guard-on-field.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (A) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
- `CipherSpec-unsafe.txt` (B) `spec=CipherSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=CIPHER-ORDER-00 ev=i1 obj=Cipher val='' exp='' msg='the observed call sequence is not one CipherSpec accepts'`
