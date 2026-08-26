# SignatureSpec — differential harness

- **A** `backup/gh105-preimage/jca_android`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 12

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SignatureSpec-d15-md5withrsa.txt` | introduced | — | i1:SIGNATURE-ALG-00, i1:SIGNATURE-NOBS-00 |
| `SignatureSpec-d15-nonewithrsa.txt` | introduced | — | i1:SIGNATURE-ALG-00, i1:SIGNATURE-NOBS-00 |
| `SignatureSpec-d15-sha1withdsa.txt` | introduced | — | i1:SIGNATURE-ALG-00, i1:SIGNATURE-NOBS-00 |
| `SignatureSpec-ecdsa.txt` | introduced | — | i1:SIGNATURE-NOBS-00 |
| `SignatureSpec-generated-privkey.txt` | removed | gpr:KEYPAIR-ORDER-00 | — |
| `SignatureSpec-generated-pubkey.txt` | removed | gpu:KEYPAIR-ORDER-00 | — |
| `SignatureSpec-guard-on-field.txt` | moved | i1:SIGNATURE-ORDER-00 | i1:SIGNATURE-NOBS-00, i1:SIGNATURE-ORDER-00 |
| `SignatureSpec-initsign-after-sign.txt` | introduced | — | i1:SIGNATURE-NOBS-00 |
| `SignatureSpec-sha512withdsa-no-init.txt` | removed | g3:SIGNATURE-ORDER-00 | — |
| `SignatureSpec-sha512withdsa.txt` | moved | g3:SIGNATURE-ORDER-00, i1:SIGNATURE-ALG-00, i1:SIGNATURE-ORDER-00, s1:SIGNATURE-ORDER-00, update:SIGNATURE-ORDER-00 | i1:SIGNATURE-ALG-00, i1:SIGNATURE-NOBS-00 |
| `SignatureSpec-sign-unobserved.txt` | unchanged | s1:SIGNATURE-ORDER-00 | s1:SIGNATURE-ORDER-00 |
| `SignatureSpec.txt` | introduced | — | i1:SIGNATURE-NOBS-00 |

## Envelopes

- `SignatureSpec-d15-md5withrsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=v=1 code=SIGNATURE-ALG-00 ev=i1 obj=Signature val='MD5withRSA' exp='SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA' msg='expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found MD5withRSA'`
- `SignatureSpec-d15-md5withrsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='MD5withRSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-d15-nonewithrsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=v=1 code=SIGNATURE-ALG-00 ev=i1 obj=Signature val='NONEwithRSA' exp='SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA' msg='expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found NONEwithRSA'`
- `SignatureSpec-d15-nonewithrsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='NONEwithRSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-d15-sha1withdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=v=1 code=SIGNATURE-ALG-00 ev=i1 obj=Signature val='SHA1withDSA' exp='SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA' msg='expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found SHA1withDSA'`
- `SignatureSpec-d15-sha1withdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA1withDSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-ecdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withECDSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-generated-privkey.txt` (A) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpr obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `SignatureSpec-generated-pubkey.txt` (A) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `SignatureSpec-guard-on-field.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withRSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-initsign-after-sign.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withRSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-sha512withdsa-no-init.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=g3 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=g3,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=g3 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=v=1 code=SIGNATURE-ALG-00 ev=i1 obj=Signature val='SHA512withDSA' exp='NONEwithRSA,SHA1withDSA,SHA224withECDSA,MD5withRSA,SHA256withDSA,SHA384withRSA/PSS,DSAwithSHA1,SHA384withRSA,SHA512withRSA/PSS,SHA1withRSA/PSS,SHA512withRSA,SHA1withRSA,NONEwithDSA,SHA256withRSA/PSS,SHA224withRSA/PSS,SHA256withRSA,DSA,SHA224withRSA,SHA224withDSA,DSS,SHA1withECDSA,SHA256withECDSA,SHA384withECDSA,SHA512withECDSA' msg='expecting one of NONEwithRSA,SHA1withDSA,SHA224withECDSA,MD5withRSA,SHA256withDSA,SHA384withRSA/PSS,DSAwithSHA1,SHA384withRSA,SHA512withRSA/PSS,SHA1withRSA/PSS,SHA512withRSA,SHA1withRSA,NONEwithDSA,SHA256withRSA/PSS,SHA224withRSA/PSS,SHA256withRSA,DSA,SHA224withRSA,SHA224withDSA,DSS,SHA1withECDSA,SHA256withECDSA,SHA384withECDSA,SHA512withECDSA but found SHA512withDSA'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=update,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=update obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sha512withdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsafeAlgorithm,msg=v=1 code=SIGNATURE-ALG-00 ev=i1 obj=Signature val='SHA512withDSA' exp='SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA' msg='expecting one of SHA256withRSA,SHA256withECDSA,SHA256withDSA,SHA384withRSA,SHA512withRSA,SHA384withECDSA,SHA512withECDSA but found SHA512withDSA'`
- `SignatureSpec-sha512withdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA512withDSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-sign-unobserved.txt` (A) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sign-unobserved.txt` (B) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withRSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
