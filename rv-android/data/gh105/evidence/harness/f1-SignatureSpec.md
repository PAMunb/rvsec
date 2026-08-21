# SignatureSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 7

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SignatureSpec-ecdsa.txt` | unchanged | — | — |
| `SignatureSpec-guard-on-field.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |
| `SignatureSpec-initsign-after-sign.txt` | unchanged | — | — |
| `SignatureSpec-sha512withdsa-no-init.txt` | removed | SignatureSpec.g3 | — |
| `SignatureSpec-sha512withdsa.txt` | moved | SignatureSpec.g3, SignatureSpec.i1, SignatureSpec.update, SignatureSpec.s1 | SignatureSpec.i1 |
| `SignatureSpec-sign-unobserved.txt` | unchanged | SignatureSpec.s1 | SignatureSpec.s1 |
| `SignatureSpec.txt` | unchanged | — | — |

## Envelopes

- `SignatureSpec-guard-on-field.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa-no-init.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=g3 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=g3 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=v=1 code=SIGNATURE-ALG-00 ev=i1 obj=Signature val='SHA512withDSA' exp='NONEwithRSA,SHA1withDSA,SHA224withECDSA,MD5withRSA,SHA256withDSA,SHA384withRSA/PSS,DSAwithSHA1,SHA384withRSA,SHA512withRSA/PSS,SHA1withRSA/PSS,SHA512withRSA,SHA1withRSA,NONEwithDSA,SHA256withRSA/PSS,SHA224withRSA/PSS,SHA256withRSA,DSA,SHA224withRSA,SHA224withDSA,DSS,SHA1withECDSA,SHA256withECDSA,SHA384withECDSA,SHA512withECDSA' msg='expecting one of NONEwithRSA,SHA1withDSA,SHA224withECDSA,MD5withRSA,SHA256withDSA,SHA384withRSA/PSS,DSAwithSHA1,SHA384withRSA,SHA512withRSA/PSS,SHA1withRSA/PSS,SHA512withRSA,SHA1withRSA,NONEwithDSA,SHA256withRSA/PSS,SHA224withRSA/PSS,SHA256withRSA,DSA,SHA224withRSA,SHA224withDSA,DSS,SHA1withECDSA,SHA256withECDSA,SHA384withECDSA,SHA512withECDSA but found SHA512withDSA'`
- `SignatureSpec-sign-unobserved.txt` (A) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sign-unobserved.txt` (B) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
