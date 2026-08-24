# SignatureSpec — differential harness

- **A** `/tmp/claude-1000/-pedro-desenvolvimento-workspaces-workspaces-doutorado-workspace-rv-rvsec-rv-android/4ee1da1c-15d4-4c75-8a60-fdfffb00219b/scratchpad/jca_android.before`
- **B** `/home/pedro/desenvolvimento/workspaces/workspaces-doutorado/workspace-rv/rvsec/rvsec/rvsec-mop/src/main/resources/jca_android`
- traces: 9

| trace | class | A accuses | B accuses |
|---|---|---|---|
| `SignatureSpec-ecdsa.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |
| `SignatureSpec-generated-privkey.txt` | unchanged | KeyPairSpec.gpr | KeyPairSpec.gpr |
| `SignatureSpec-generated-pubkey.txt` | unchanged | KeyPairSpec.gpu | KeyPairSpec.gpu |
| `SignatureSpec-guard-on-field.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |
| `SignatureSpec-initsign-after-sign.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |
| `SignatureSpec-sha512withdsa-no-init.txt` | unchanged | — | — |
| `SignatureSpec-sha512withdsa.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |
| `SignatureSpec-sign-unobserved.txt` | unchanged | SignatureSpec.s1 | SignatureSpec.s1 |
| `SignatureSpec.txt` | unchanged | SignatureSpec.i1 | SignatureSpec.i1 |

## Envelopes

- `SignatureSpec-ecdsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withECDSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-ecdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withECDSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-generated-privkey.txt` (A) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpr obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `SignatureSpec-generated-privkey.txt` (B) `spec=KeyPairSpec,ev=gpr,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpr obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `SignatureSpec-generated-pubkey.txt` (A) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `SignatureSpec-generated-pubkey.txt` (B) `spec=KeyPairSpec,ev=gpu,type=InvalidSequenceOfMethodCalls,msg=v=1 code=KEYPAIR-ORDER-00 ev=gpu obj=KeyPair val='' exp='' msg='the observed call sequence is not one KeyPairSpec accepts'`
- `SignatureSpec-guard-on-field.txt` (A) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-guard-on-field.txt` (B) `spec=SignatureSpec,ev=i1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=i1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-initsign-after-sign.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withRSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-initsign-after-sign.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withRSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-sha512withdsa.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA512withDSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-sha512withdsa.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA512withDSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec-sign-unobserved.txt` (A) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec-sign-unobserved.txt` (B) `spec=SignatureSpec,ev=s1,type=InvalidSequenceOfMethodCalls,msg=v=1 code=SIGNATURE-ORDER-00 ev=s1 obj=Signature val='' exp='' msg='the observed call sequence is not one SignatureSpec accepts'`
- `SignatureSpec.txt` (A) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withRSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
- `SignatureSpec.txt` (B) `spec=SignatureSpec,ev=i1,type=UnsatisfiedConstraint,msg=v=1 code=SIGNATURE-NOBS-00 ev=i1 obj=Signature val='SHA256withRSA' exp='a private key produced by one of the generators the rule names' msg='no generator of the private key given to initSign was observed'`
