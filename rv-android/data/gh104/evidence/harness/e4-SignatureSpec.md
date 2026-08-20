# SignatureSpec — differential harness

- **A** `/home/pedro/tmp-gh104/e4-a/jca_android`
- **B** `/home/pedro/tmp-gh104/e4-b815a`
- traces: 5

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SignatureSpec-ecdsa.txt` | unchanged | — | — |
| `SignatureSpec-guard-on-field.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |
| `SignatureSpec-initsign-after-sign.txt` | removed | SignatureSpec.i1 | — |
| `SignatureSpec-sign-unobserved.txt` | introduced | — | SignatureSpec.s1 |
| `SignatureSpec.txt` | unchanged | — | — |

## Lines no pointcut resolved

- `SignatureSpec-ecdsa.txt` — `s.sign() -> out`
- `SignatureSpec-initsign-after-sign.txt` — `s.sign() -> out`
- `SignatureSpec-sign-unobserved.txt` — `s.sign() -> out`
- `SignatureSpec.txt` — `s.sign() -> out`

## Envelopes

- `SignatureSpec-guard-on-field.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-initsign-after-sign.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sign-unobserved.txt` (B) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
