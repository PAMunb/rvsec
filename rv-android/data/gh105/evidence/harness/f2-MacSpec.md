# MacSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 8

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `MacSpec-decrypt-buffer.txt` | moved | SecureRandomSpec.next2, MacSpec.f2 | MacSpec.f2 |
| `MacSpec-encrypted-buffer.txt` | moved | SecureRandomSpec.next2, MacSpec.f2 | MacSpec.f2 |
| `MacSpec-fresh-buffer.txt` | removed | SecureRandomSpec.next2, MacSpec.f2 | — |
| `MacSpec-guard-on-field.txt` | introduced | — | MacSpec.i1 |
| `MacSpec-hmacpbesha1.txt` | moved | MacSpec.f1 | MacSpec.i1, MacSpec.f1 |
| `MacSpec-ungenerated-key.txt` | removed | MacSpec.f1 | — |
| `MacSpec-unsafe-generated-key.txt` | unchanged | MacSpec.i1, MacSpec.f1 | MacSpec.i1, MacSpec.f1 |
| `MacSpec.txt` | unchanged | — | — |

## Envelopes

- `MacSpec-decrypt-buffer.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `MacSpec-decrypt-buffer.txt` (A) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f2 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-decrypt-buffer.txt` (B) `spec=MacSpec,ev=f2,type=UnsatisfiedConstraint,msg=v=1 code=MAC-CONSTR-00 ev=f2 obj=Mac val='encrypted' exp='not encrypted' msg='the buffer the mac is written into already holds ciphertext'`
- `MacSpec-encrypted-buffer.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `MacSpec-encrypted-buffer.txt` (A) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f2 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-encrypted-buffer.txt` (B) `spec=MacSpec,ev=f2,type=UnsatisfiedConstraint,msg=v=1 code=MAC-CONSTR-00 ev=f2 obj=Mac val='encrypted' exp='not encrypted' msg='the buffer the mac is written into already holds ciphertext'`
- `MacSpec-fresh-buffer.txt` (A) `spec=SecureRandomSpec,ev=next2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SECURERANDOM-ORDER-00 ev=next2 obj=SecureRandom val='' exp='' msg='the observed call sequence is not one SecureRandomSpec accepts'`
- `MacSpec-fresh-buffer.txt` (A) `spec=MacSpec,ev=f2,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f2 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-guard-on-field.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-hmacpbesha1.txt` (B) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-ungenerated-key.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=f1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (A) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (A) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (B) `spec=MacSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
- `MacSpec-unsafe-generated-key.txt` (B) `spec=MacSpec,ev=f1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=MAC-ORDER-00 ev=i1 obj=Mac val='' exp='' msg='the observed call sequence is not one MacSpec accepts'`
